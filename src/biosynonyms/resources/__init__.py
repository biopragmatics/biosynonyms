"""Resources for Biosynonyms."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, cast

from biosynonyms.model import Synonym, grounder_from_synonyms, parse_synonyms

if TYPE_CHECKING:
    import gilda

__all__ = [
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

SYNONYM_SCOPES = {
    "oboInOwl:hasExactSynonym",
    "oboInOwl:hasNarrowSynonym",
    "oboInOwl:hasBroadSynonym",
    "oboInOwl:hasRelatedSynonym",
    "oboInOwl:hasSynonym",
}


def load_unentities() -> set[str]:
    """Load all strings that are known not to be named entities."""
    return {line[0] for line in _load_unentities()}


def _load_unentities() -> Iterable[tuple[str, str]]:
    with UNENTITIES_PATH.open() as file:
        next(file)  # throw away header
        for line in file:
            yield cast(tuple[str, str], line.strip().split("\t"))


def _unentities_key(row: Sequence[str]) -> str:
    return row[0].casefold()


def write_unentities(rows: Iterable[tuple[str, str]]) -> None:
    """Write all strings that are known not to be named entities."""
    with UNENTITIES_PATH.open("w") as file:
        print("text", "curator_orcid", sep="\t", file=file)
        for row in sorted(rows, key=_unentities_key):
            print(*row, sep="\t", file=file)


def get_positive_synonyms() -> list[Synonym]:
    """Get positive synonyms curated in Biosynonyms."""
    return parse_synonyms(POSITIVES_PATH)


def get_negative_synonyms() -> list[Synonym]:
    """Get negative synonyms curated in Biosynonyms."""
    return parse_synonyms(NEGATIVES_PATH)


def get_gilda_terms() -> list[gilda.Term]:
    """Get Gilda terms for all positive synonyms."""
    return [synonym.to_gilda() for synonym in get_positive_synonyms()]


def get_grounder() -> gilda.Groudner:
    """Get a grounder from all positive synonyms."""
    return grounder_from_synonyms(get_positive_synonyms())
