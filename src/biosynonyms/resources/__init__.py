"""Resources for Biosynonyms."""

from pathlib import Path
from typing import Iterable, Sequence, cast, TYPE_CHECKING
from pydantic import BaseModel, Field
import pandas as pd
from curies import Reference

import csv

if TYPE_CHECKING:
    import gilda

__all__ = [
    "load_unentities",
    "get_gilda_terms",
    "get_synonyms",
    "write_unentities",
    "Synonym",
]

HERE = Path(__file__).parent.resolve()
POSITIVES_PATH = HERE.joinpath("positives.tsv")
NEGATIVES_PATH = HERE.joinpath("negatives.tsv")
UNENTITIES_PATH = HERE.joinpath("unentities.tsv")


def sort_key(row: Sequence[str]) -> tuple[str, str, str, str]:
    """Return a key for sorting a row."""
    return row[0].casefold(), row[0], row[1].casefold(), row[1]


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
        print("text", "curator_orcid", sep="\t", file=file)  # noqa:T201
        for row in sorted(rows, key=_unentities_key):
            print(*row, sep="\t", file=file)  # noqa:T201


class Synonym(BaseModel):
    """A data model for synonyms."""

    text: str
    reference: Reference
    name: str
    scope: Reference
    type: Reference | None = Field(
        default=None,
        title="Synonym type",
        description="See the OBO Metadata Ontology for valid values",
    )
    provenance: list[Reference] = Field(default_factory=list)
    contributor: Reference

    def as_gilda_term(self) -> "gilda.Term":
        """Get this synonym as a gilda term."""
        from gilda.process import normalize

        return gilda.Term(
            normalize(self.text),
            text=self.text,
            db=self.reference.prefix,
            id=self.reference.identifier,
            entry_name=self.name,
            status="synonym",
            source="biosynonyms",
        )


def _safe_parse_curie(x) -> Reference | None:
    if pd.isna(x):
        return None
    return Reference.from_curie(x)


def get_synonyms(path: str | Path) -> list[Synonym]:
    """Load synonyms from a file."""
    path = Path(path).resolve()
    with path.open() as file:
        reader = csv.reader(file, delimiter="\t")
        return [
            Synonym(
                text=text,
                reference=Reference.from_curie(curie),
                name="",  # FIXME - include this in datamodel
                scope=Reference.from_curie(scope),
                type=_safe_parse_curie(scope),
                provenance=[Reference.from_curie(x) for x in provenance.split(",")],
                contributor=Reference(prefix="orcid", identifier=contributor),
            )
            for text, curie, scope, type, provenance, contributor in reader
        ]


def get_gilda_terms() -> Iterable["gilda.Term"]:
    """Get Gilda terms for all positive synonyms."""
    for synonym in get_synonyms(POSITIVES_PATH):
        yield synonym.as_gilda_term()
