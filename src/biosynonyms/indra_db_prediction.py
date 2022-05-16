import gzip
import json
import logging
from itertools import permutations
from pathlib import Path
from typing import cast

import click
import networkx as nx
from tqdm import tqdm

import bioregistry
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
from more_node2vec import Model, fit_model, process_graph, echo

logger = logging.getLogger(__name__)

INPUT_PATH = Path("/Users/cthoyt/Downloads/processed_statements-2022-03-31.tsv.gz")
OUTPUT_PATH = Path("/Users/cthoyt/Downloads/processed_statements-2022-03-31-pairs.tsv")
MODEL_DIR = Path("/Users/cthoyt/Downloads/processed_statements-2022-03-31-model/")
MODEL_DIR.mkdir(exist_ok=True, parents=True)


def get_agent_curie_tuple(agent: Agent) -> tuple[str, str]:
    """Return a tuple of name space, id from an Agent's db_refs."""
    for prefix in NS_PRIORITY_LIST:
        if prefix in agent.db_refs:
            return bioregistry.normalize_parsed_curie(prefix, agent.db_refs[prefix])
    return "text", normalize(agent.name)


@click.command()
def main():
    if Model.is_loadable(MODEL_DIR):
        model = Model.load(MODEL_DIR)
    else:
        pairs = get_pairs()
        echo("building graph")
        graph = nx.Graph(pairs)
        # Get biggest connected component
        # graph = process_graph(graph)
        model = fit_model(graph)
        model.save(MODEL_DIR)

    fig, axes = model.plot_pca()
    fig.savefig(MODEL_DIR.joinpath("pca.pdf"))


def get_pairs(force: bool = False) -> list[tuple[str, str]]:
    if OUTPUT_PATH.exists() and not force:
        with OUTPUT_PATH.open() as file:
            return cast(list[tuple[str, str]], [
                line.strip().split("\t", 1)  # this will always be exactly two
                for line in tqdm(file, desc="reading pairs", unit_scale=True)
            ])

    rows: set[tuple[str, str]] = set()
    with gzip.open(INPUT_PATH, "rt") as file:
        it = tqdm(file, desc="loading INDRA db", unit="statement", unit_scale=True, total=65_102_088)
        for line in it:
            _assembled_hash, stmt_json_str = line.split("\t", 1)
            # why won't it strip the extra?!?!
            stmt_json_str = stmt_json_str.replace('""', '"').strip('"')[:-2]
            stmt = Statement._from_json(json.loads(stmt_json_str))
            rows.update(_rows_from_stmt(stmt))

    sorted_rows = sorted(rows)
    with OUTPUT_PATH.open("w") as file:
        for pair in tqdm(sorted_rows, desc="writing", unit_scale=True):
            print(*pair, sep="\t", file=file)
    return sorted_rows


def _rows_from_stmt(
    stmt: Statement,
    complex_members=3,
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
