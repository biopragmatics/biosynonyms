import gzip
import json
import logging
from itertools import permutations
from pathlib import Path

import bioregistry
import click
import matplotlib.pyplot as plt
from embiggen import GraphVisualizer
from embiggen.embedders import SecondOrderLINEEnsmallen
from ensmallen import Graph
from gilda.process import normalize
from indra.assemblers.indranet.assembler import NS_PRIORITY_LIST
from indra.statements import (
    Agent,
    Association,
    Complex,
    Conversion,
    Influence,
    Statement,
)
from tqdm import tqdm

logger = logging.getLogger(__name__)

FOLDER = Path("/Users/cthoyt/.data/indra/db")
INPUT_PATH = FOLDER.joinpath("processed_statements-2022-03-31.tsv.gz")
PAIRS_PATH = FOLDER.joinpath("processed_statements-2022-03-31-pairs.tsv")
EMBEDDINGS_PATH = FOLDER.joinpath("processed_statements-2022-03-31-embeddings.tsv.gz")
PLOT_PATH = FOLDER.joinpath("plot.png")


def get_agent_curie_tuple(agent: Agent) -> tuple[str, str]:
    """Return a tuple of name space, id from an Agent's db_refs."""
    for prefix in NS_PRIORITY_LIST:
        if prefix in agent.db_refs:
            return bioregistry.normalize_parsed_curie(prefix, agent.db_refs[prefix])
    return "text", normalize(agent.name)


@click.command()
def main():
    if not EMBEDDINGS_PATH.is_file():
        graph = get_graph()
        embedding = SecondOrderLINEEnsmallen(embedding_size=32).fit_transform(graph)
        df = embedding.get_all_node_embedding()[0].sort_index()
        df.index.name = "node"
        df.to_csv(EMBEDDINGS_PATH, sep="\t")

        visualizer = GraphVisualizer(graph)
        fig, *_ = visualizer.fit_and_plot_all(embedding)
        plt.savefig(PLOT_PATH, dpi=300)
        plt.close(fig)


def get_graph(force: bool = False) -> Graph:
    if not PAIRS_PATH.exists() or force:
        rows: set[tuple[str, str]] = set()
        with gzip.open(INPUT_PATH, "rt") as file:
            it = tqdm(
                file, desc="loading INDRA db", unit="statement", unit_scale=True, total=65_102_088
            )
            for line in it:
                _assembled_hash, stmt_json_str = line.split("\t", 1)
                # why won't it strip the extra?!?!
                stmt_json_str = stmt_json_str.replace('""', '"').strip('"')[:-2]
                stmt = Statement._from_json(json.loads(stmt_json_str))
                rows.update(_rows_from_stmt(stmt))

        sorted_rows = sorted(rows)
        with PAIRS_PATH.open("w") as file:
            for pair in tqdm(sorted_rows, desc="writing", unit_scale=True):
                print(*pair, sep="\t", file=file)

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


def _rows_from_stmt(
    stmt: Statement,
    complex_members: int = 3,
) -> list[tuple[str, str]]:
    rv = []
    not_none_agents = stmt.real_agent_list()
    if len(not_none_agents) < 2:
        # Exclude statements with less than 2 agents
        return rv

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
            return rv
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
        return rv
    else:
        edges = [(not_none_agents[0], not_none_agents[1], None)]
    for agent_a, agent_b, sign in edges:
        if agent_a.name == agent_b.name:
            continue
        source_prefix, source_id = get_agent_curie_tuple(agent_a)
        target_prefix, target_id = get_agent_curie_tuple(agent_b)
        # stmt_type = type(stmt).__name__
        row = (
            f"{source_prefix}:{source_id}",
            # stmt_type,
            f"{target_prefix}:{target_id}",
        )
        rv.append(row)
    return rv


if __name__ == "__main__":
    main()
