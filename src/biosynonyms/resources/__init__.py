"""Resources for Biosynonyms."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import ssslm
import ssslm.ontology
from ssslm import LiteralMapping
import warnings
from biosynonyms.app import SynonymCurator

if TYPE_CHECKING:
    import gilda

__all__ = [
    "CURATOR",
    "get_gilda_terms",
    "get_grounder",
    "get_negative_synonyms",
    "get_positive_synonyms",
    "load_unentities",
    "write_unentities",
]

HERE = Path(__file__).parent.resolve()

POSITIVES_PATH = HERE.joinpath("positives.tsv")
NEGATIVES_PATH = HERE.joinpath("negatives.tsv")
UNENTITIES_PATH = HERE.joinpath("unentities.tsv")

EXPORT = HERE.parent.parent.joinpath("exports")
EXPORT.mkdir(exist_ok=True)
TTL_PATH = EXPORT.joinpath("biosynonyms.ttl")

URI = "https://w3id.org/biopragmatics/resources/biosynonyms.ttl"
METADATA = ssslm.ontology.Metadata(
    uri=URI,
    title="Biosynonyms in OWL",
    description="An ontology representation of community curated synonyms in Biosynonyms",
    license="https://creativecommons.org/publicdomain/zero/1.0/",
    comments=[
        "Built by https://github.com/biopragmatics/biosynonyms",
    ],
)

CURATOR = SynonymCurator(POSITIVES_PATH, NEGATIVES_PATH, UNENTITIES_PATH, METADATA, owl_ttl_path=TTL_PATH)


def load_unentities() -> set[str]:
    """Load all strings that are known not to be named entities."""
    return CURATOR.load_stop_words()


def write_unentities(rows: Iterable[tuple[str, str]]) -> None:
    """Write all strings that are known not to be named entities."""
    CURATOR.write_stop_words(rows)


def get_positive_synonyms() -> list[LiteralMapping]:
    """Get positive synonyms curated in Biosynonyms."""
    return CURATOR.get_positive_synonyms()


def get_negative_synonyms() -> list[LiteralMapping]:
    """Get negative synonyms curated in Biosynonyms."""
    return CURATOR.get_negative_synonyms()


def make_grounder(**kwargs: Any) -> ssslm.Grounder:
    """Get a grounder from all positive synonyms."""
    return CURATOR.make_grounder()


def get_gilda_terms() -> list[gilda.Term]:
    """Get Gilda terms for all positive synonyms."""
    return ssslm.literal_mappings_to_gilda(CURATOR.get_positive_synonyms())


def get_grounder() -> gilda.Grounder:
    """Get a grounder from all positive synonyms."""
    grounder = ssslm.GildaGrounder.from_literal_mappings(get_positive_synonyms())
    return grounder._grounder
