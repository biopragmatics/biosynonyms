"""Predict synonyms based on similarity."""

import gzip
import itertools as itt
import json
import logging
from collections import Counter
from functools import partial
from itertools import permutations
from pathlib import Path
from typing import Iterable

import bioregistry
import click
import gilda
import matplotlib.pyplot as plt
import pandas as pd
from embiggen import GraphVisualizer
from embiggen.embedders import SecondOrderLINEEnsmallen
from ensmallen import Graph
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
from tqdm.contrib.concurrent import process_map

from biosynonyms.resources import load_unentities

logger = logging.getLogger(__name__)

FOLDER = Path("/Users/cthoyt/.data/indra/db")
INPUT_PATH = FOLDER.joinpath("processed_statements-2022-03-31.tsv.gz")
PAIRS_PATH = FOLDER.joinpath("biosynonyms_pairs.tsv")
COUNTER_PATH = FOLDER.joinpath("biosynonyms_counter.tsv")
EMBEDDINGS_PATH = FOLDER.joinpath("biosynonyms_embeddings.parquet")
PLOT_PATH = FOLDER.joinpath("plot.png")
TEXT_PREFIX = "text"

Row = tuple[str, str, str, str]
Rows = list[Row]


def get_agent_curie_tuple(agent: Agent) -> tuple[str, str]:
    """Return a tuple of name space, id from an Agent's db_refs."""
    for prefix in NS_PRIORITY_LIST:
        if prefix in agent.db_refs:
            return bioregistry.normalize_parsed_curie(prefix, agent.db_refs[prefix])

    scored_matches = gilda.ground(agent.name)
    if not scored_matches:
        return TEXT_PREFIX, agent.name.strip().replace("\t", " ").replace("\n", " ").replace(
            "  ", " "
        )

    scored_match = scored_matches[0]
    return bioregistry.normalize_parsed_curie(scored_match.term.db, scored_match.term.id)


@click.command()
@click.option("--size", type=int, default=32)
@force_option
@click.option("--test", is_flag=True)
def main(size: int, force: bool, test: bool):
    if not EMBEDDINGS_PATH.is_file() or force:
        graph = get_graph(force=force, test=test)
        embedding = SecondOrderLINEEnsmallen(embedding_size=size).fit_transform(graph)
        df: pd.DataFrame = embedding.get_all_node_embedding()[0].sort_index()
        df.index.name = "node"
        df.columns = [str(c) for c in df.columns]
        df.to_parquet(EMBEDDINGS_PATH)
        # TODO use more efficient storage format, this is like 3.5GB as gzipped text
        # TODO output index of all synonyms
        # TODO calculate closest neighbors for synonyms (that aren't already in predictions)

        visualizer = GraphVisualizer(graph)
        fig, *_ = visualizer.fit_and_plot_all(embedding)
        plt.savefig(PLOT_PATH, dpi=300)
        plt.close(fig)


def get_graph(force: bool = False) -> Graph:
    if not PAIRS_PATH.exists() or force:
        unentities = load_unentities()
        func = partial(_line_to_rows, unentities=unentities)

        with gzip.open(INPUT_PATH, "rt") as file:
            groups = process_map(
                func,
                file,
                desc="loading INDRA db",
                unit="statement",
                unit_scale=True,
                total=65_102_088,
                chunksize=300_000,
            )
            rows: set[tuple[str, str, str, str]] = set(itt.chain.from_iterable(groups))

        sorted_rows = sorted(rows)

        counter = Counter(_iter(sorted_rows))
        counter_df = pd.DataFrame(counter.most_common(), columns=["synonym", "count"])
        counter_df.to_csv(COUNTER_PATH, sep="\t", index=False)

        # this can't be gzipped or else GRAPE doesn't work
        with PAIRS_PATH.open("w") as file:
            for source_prefix, source_id, target_prefix, target_id in tqdm(
                sorted_rows, desc="writing", unit_scale=True
            ):
                print(
                    f"{source_prefix}:{source_id}",
                    f"{target_prefix}:{target_id}",
                    sep="\t",
                    file=file,
                )

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


def _iter(sorted_rows: Iterable[tuple[str, str, str, str]]):
    it = tqdm(sorted_rows, unit_scale=True, desc="counting occurrences")
    for source_prefix, source_id, target_prefix, target_id in it:
        if source_prefix == TEXT_PREFIX:
            yield source_id
        if target_prefix == TEXT_PREFIX:
            yield target_id


def _line_to_rows(line: str, unentities: set[str]) -> Rows:
    _assembled_hash, stmt_json_str = line.split("\t", 1)
    # why won't it strip the extra?!?!
    stmt_json_str = stmt_json_str.replace('""', '"').strip('"')[:-2]
    stmt = Statement._from_json(json.loads(stmt_json_str))
    return _rows_from_stmt(stmt, unentities)


def _rows_from_stmt(
    stmt: Statement,
    unentities: set[str],
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

    rows = []
    for agent_a, agent_b, sign in edges:
        if agent_a.name == agent_b.name:
            continue
        source_prefix, source_id = get_agent_curie_tuple(agent_a)
        target_prefix, target_id = get_agent_curie_tuple(agent_b)
        if source_id in unentities or target_id in unentities:
            continue
        # stmt_type = type(stmt).__name__
        row = (
            source_prefix,
            source_id,
            # stmt_type,
            target_prefix,
            target_id,
        )
        rows.append(row)
    return rows


if __name__ == "__main__":
    main()
