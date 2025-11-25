"""Resources for Biosynonyms."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import ssslm
from ssslm import LiteralMapping, Metadata, Repository

if TYPE_CHECKING:
    import gilda

__all__ = [
    "REPOSITORY",
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

METADATA = Metadata(
    uri="https://w3id.org/biopragmatics/resources/biosynonyms.ttl",
    title="Biosynonyms in OWL",
    description="An ontology representation of community curated synonyms in Biosynonyms",
    license="https://creativecommons.org/publicdomain/zero/1.0/",
    comments=[
        "Built by https://github.com/biopragmatics/biosynonyms",
    ],
)

REPOSITORY = Repository(
    POSITIVES_PATH, NEGATIVES_PATH, UNENTITIES_PATH, metadata=METADATA, owl_ttl_path=TTL_PATH
)


def load_unentities() -> set[str]:
    """Load all strings that are known not to be named entities."""
    return REPOSITORY.load_stop_words()


def write_unentities(rows: Iterable[tuple[str, str]]) -> None:
    """Write all strings that are known not to be named entities."""
    REPOSITORY.write_stop_words(rows)


def get_positive_synonyms() -> list[LiteralMapping]:
    """Get positive synonyms curated in Biosynonyms."""
    return REPOSITORY.get_positive_synonyms()


def get_negative_synonyms() -> list[LiteralMapping]:
    """Get negative synonyms curated in Biosynonyms."""
    return REPOSITORY.get_negative_synonyms()


def make_grounder(**kwargs: Any) -> ssslm.Grounder:
    """Get a grounder from all positive synonyms."""
    return REPOSITORY.make_grounder()


def get_gilda_terms() -> list[gilda.Term]:
    """Get Gilda terms for all positive synonyms."""
    return ssslm.literal_mappings_to_gilda(REPOSITORY.get_positive_synonyms())


def get_grounder() -> gilda.Grounder:
    """Get a grounder from all positive synonyms."""
    grounder = ssslm.GildaGrounder.from_literal_mappings(get_positive_synonyms())
    return grounder._grounder
