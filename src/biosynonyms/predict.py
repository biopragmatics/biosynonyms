"""Predict synonyms based on similarity.

Does the following:

- [ ] Automate acquisition of INDRA DB processed statements
- [x] Convert processed (including ungrounded statements) into triples
- [ ] Calculate graph embedding
- [ ] Calculate nearest neighbors for top K entities with text to all entities with grounding

Run with ``python -m biosynonyms.predict``
"""

import gzip
import itertools as itt
import json
import logging
from collections import Counter
from functools import partial
from itertools import permutations
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, List, Set, Tuple, cast

import bioregistry
import click
import gilda
import pandas as pd
import pystow
from curies import ReferenceTuple
from indra.assemblers.indranet.assembler import NS_PRIORITY_LIST
from indra.statements import (
    Agent,
    Association,
    Complex,
    Conversion,
    Influence,
    Statement,
)
from more_click import force_option
from tqdm import tqdm

from biosynonyms.resources import load_unentities

if TYPE_CHECKING:
    import ensmallen


logger = logging.getLogger(__name__)

MODULE = pystow.module("indra", "db")
PAIRS_PATH = MODULE.join(name="biosynonyms_pairs.tsv")
COUNTER_PATH = MODULE.join(name="biosynonyms_counter.tsv")
COUNTER_TOP_PATH = MODULE.join(name="biosynonyms_counter_top_1000.tsv")
EMBEDDINGS_PATH = MODULE.join(name="biosynonyms_embeddings.parquet")
PLOT_PATH = MODULE.join(name="plot.png")
TEXT_PREFIX = "text"

Row = Tuple[ReferenceTuple, ReferenceTuple]
Rows = List[Row]


def ensure_procesed_statements() -> Path:
    """Ensure the latest processed INDRA statements file is downloaded from S3."""
    # s3://bigmech/indra-db/dumps/principal/2023-05-05/processed_statements.tsv.gz
    bucket = "bigmech"
    key = "indra-db/dumps/principal/2023-05-05/processed_statements.tsv.gz"
    return cast(
        Path, MODULE.ensure_from_s3("principal", "2023-05-05", s3_bucket=bucket, s3_key=key)
    )


def norm(s: str) -> str:
    """Normalize a string."""
    return s.strip().replace("\t", " ").replace("\n", " ").replace("  ", " ")


def _norm_strict(prefix: str, identifier: str) -> ReferenceTuple:
    norm_prefix, norm_identifier = bioregistry.normalize_parsed_curie(prefix, identifier)
    if not norm_prefix or not norm_identifier:
        raise ValueError
    return ReferenceTuple(norm_prefix, norm_identifier)


def get_agent_curie_tuple(agent: Agent, *, grounder: gilda.Grounder) -> ReferenceTuple:
    """Return a tuple of name space, id from an Agent's db_refs."""
    for prefix in NS_PRIORITY_LIST:
        if prefix in agent.db_refs:
            return _norm_strict(prefix, agent.db_refs[prefix])

    norm_agent_name = norm(agent.name)
    scored_matches = grounder.ground(norm_agent_name)
    if not scored_matches:
        return ReferenceTuple(TEXT_PREFIX, norm_agent_name)

    scored_match = scored_matches[0]
    return _norm_strict(scored_match.term.db, scored_match.term.id)


@click.command()  # type:ignore
@click.option("--size", type=int, default=32)  # type:ignore
@force_option  # type:ignore
def main(size: int, force: bool) -> None:
    """Generate synonym predictions."""
    if not EMBEDDINGS_PATH.is_file() or force:
        graph = get_graph(force=force)
        graph = graph.remove_disconnected_nodes()

        from embiggen.embedders.ensmallen_embedders.second_order_line import (
            SecondOrderLINEEnsmallen,
        )

        click.echo("Fitting Second Order LINE")
        embedding = SecondOrderLINEEnsmallen(embedding_size=size).fit_transform(graph)
        df: pd.DataFrame = embedding.get_all_node_embedding()[0].sort_index()
        df.index.name = "node"
        df.columns = [str(c) for c in df.columns]
        click.echo(f"Writing Parquet to {EMBEDDINGS_PATH}")
        df.to_parquet(EMBEDDINGS_PATH)
        # TODO output index of all synonyms
        # TODO calculate closest neighbors for synonyms (that aren't already in predictions)

        # from embiggen import GraphVisualizer
        #
        # visualizer = GraphVisualizer(graph)
        # fig, axes = visualizer.fit_and_plot_all(embedding)
        # click.echo(f"Outputting plots to {PLOT_PATH}")
        # plt.savefig(PLOT_PATH, dpi=300)
        # plt.close(fig)


def get_grounder() -> gilda.Grounder:
    """Get a Gilda grounder."""
    # TODO get both gilda built in plus extras from positives
    raise NotImplementedError


def get_graph(force: bool = False) -> "ensmallen.Graph":
    """Get a the undirected INDRA graph."""
    if not PAIRS_PATH.exists() or force:
        click.echo("loading non-entities")
        unentities = load_unentities()

        click.echo("Getting up Gilda grounder")
        grounder = get_grounder()
        click.echo("Warming up grounder")
        grounder.ground("k-ras")

        func = partial(_line_to_rows, unentities=unentities, grounder=grounder)

        click.echo("Ensuring INDRA statements from S3")
        input_path = ensure_procesed_statements()
        tqdm_kwargs = dict(
            desc="loading INDRA db",
            unit="statement",
            unit_scale=True,
            total=65_102_088,
        )
        click.echo("Reading INDRA statements")
        with gzip.open(input_path, "rt") as file:
            click.echo(f"Opened {file.name}")
            rows: Set[Row] = set(
                itt.chain.from_iterable(func(line) for line in tqdm(file, **tqdm_kwargs))
            )
            # groups = process_map(
            #     func,
            #     file,
            #     **tqdm_kwargs,
            #     max_workers=4,
            #     chunksize=300_000,
            # )
            # rows: Set[Row] = set(itt.chain.from_iterable(groups))

        sorted_rows = sorted(rows)

        click.echo("Tabulating entity counts")
        counter = Counter(_iter_names_from_rows(sorted_rows))
        counter_df = pd.DataFrame(counter.most_common(), columns=["synonym", "count"])
        counter_df.to_csv(COUNTER_PATH, sep="\t", index=False)
        counter_df.head(1000).to_csv(COUNTER_TOP_PATH, sep="\t", index=False)

        click.echo(f"Writing graph to {PAIRS_PATH}")
        # this can't be gzipped or else GRAPE doesn't work
        with PAIRS_PATH.open("w") as file:
            for source, target in tqdm(sorted_rows, desc="writing", unit_scale=True):
                print(  # noqa:T201
                    source.curie,
                    target.curie,
                    sep="\t",
                    file=file,
                )

    from ensmallen import Graph

    click.echo(f"Loading graph from {PAIRS_PATH}")
    return Graph.from_csv(
        edge_path=str(PAIRS_PATH),
        edge_list_separator="\t",
        sources_column_number=0,
        destinations_column_number=1,
        edge_list_numeric_node_ids=False,
        directed=True,
        name="INDRA Database",
        verbose=True,
    )


def _iter_names_from_rows(sorted_rows: Iterable[Row]) -> Iterable[str]:
    it = tqdm(sorted_rows, unit_scale=True, desc="counting occurrences")
    for source, target in it:
        if source.prefix == TEXT_PREFIX:
            yield source.identifier
        if target.prefix == TEXT_PREFIX:
            yield target.identifier


def _line_to_rows(line: str, unentities: Set[str], grounder: gilda.Grounder) -> Rows:
    _assembled_hash, stmt_json_str = line.split("\t", 1)
    # why won't it strip the extra?!?!
    stmt_json_str = stmt_json_str.replace('""', '"').strip('"')[:-2]
    stmt = Statement._from_json(json.loads(stmt_json_str))
    return _rows_from_stmt(stmt, unentities=unentities, grounder=grounder)


def _rows_from_stmt(
    stmt: Statement,
    *,
    unentities: Set[str],
    grounder: gilda.Grounder,
    complex_members: int = 3,
) -> Rows:
    not_none_agents = stmt.real_agent_list()
    if len(not_none_agents) < 2:
        # Exclude statements with less than 2 agents
        return []

    if isinstance(stmt, (Influence, Association)):
        # Special handling for Influences and Associations
        stmt_pol = stmt.overall_polarity()
        if stmt_pol == 1:
            sign = 0
        elif stmt_pol == -1:
            sign = 1
        else:
            sign = None
        if isinstance(stmt, Influence):
            edges = [(stmt.subj.concept, stmt.obj.concept, sign)]
        else:
            edges = [(a, b, sign) for a, b in permutations(not_none_agents, 2)]
    elif isinstance(stmt, Complex):
        # Handle complexes by creating pairs of their
        # not-none-agents.

        # Do not add complexes with more members than complex_members
        if len(not_none_agents) > complex_members:
            logger.debug(f"Skipping a complex with {len(not_none_agents)} members.")
            return []
        else:
            # add every permutation with a neutral polarity
            edges = [(a, b, None) for a, b in permutations(not_none_agents, 2)]
    elif isinstance(stmt, Conversion):
        edges = []
        if stmt.subj:
            for obj in stmt.obj_from:
                edges.append((stmt.subj, obj, 1))
            for obj in stmt.obj_to:
                edges.append((stmt.subj, obj, 0))
    elif len(not_none_agents) > 2:
        # This is for any remaining statement type that may not be
        # handled above explicitly but somehow has more than two
        # not-none-agents at this point
        return []
    else:
        edges = [(not_none_agents[0], not_none_agents[1], None)]

    def _is_unentity(r: ReferenceTuple) -> bool:
        return r.prefix == TEXT_PREFIX and r.identifier in unentities

    rows = []
    for agent_a, agent_b, _sign in edges:
        if agent_a.name == agent_b.name:
            continue
        source = get_agent_curie_tuple(agent_a, grounder=grounder)
        target = get_agent_curie_tuple(agent_b, grounder=grounder)
        if _is_unentity(source) or _is_unentity(target):
            continue

        # stmt_type = type(stmt).__name__
        row = (source, target)
        rows.append(row)
    return rows


# TODO open up pairs file and clean it to remove any row where either the source or target are in the unentities list


if __name__ == "__main__":
    main()
