"""Resources for Biosynonyms."""

import csv
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
    cast,
)

import pandas as pd
from curies import Reference
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    import gilda

__all__ = [
    # Data model
    "Synonym",
    # Get at the data
    "get_positive_synonyms",
    "get_negative_synonyms",
    "load_unentities",
    "write_unentities",
    # Utilities
    "get_gilda_terms",
    "parse_synonyms",
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


def sort_key(row: Sequence[str]) -> Tuple[str, str, str, str]:
    """Return a key for sorting a row."""
    return row[0].casefold(), row[0], row[1].casefold(), row[1]


def load_unentities() -> Set[str]:
    """Load all strings that are known not to be named entities."""
    return {line[0] for line in _load_unentities()}


def _load_unentities() -> Iterable[Tuple[str, str]]:
    with UNENTITIES_PATH.open() as file:
        next(file)  # throw away header
        for line in file:
            yield cast(Tuple[str, str], line.strip().split("\t"))


def _unentities_key(row: Sequence[str]) -> str:
    return row[0].casefold()


def write_unentities(rows: Iterable[Tuple[str, str]]) -> None:
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
    scope: Reference = Field(default=Reference.from_curie("oboInOwl:hasSynonym"))
    type: Optional[Reference] = Field(
        default=None,
        title="Synonym type",
        description="See the OBO Metadata Ontology for valid values",
    )
    provenance: List[Reference] = Field(default_factory=list)
    contributor: Reference

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "Synonym":
        """Parse a dictionary representing a row in a TSV."""
        return cls(
            text=row["text"],
            reference=Reference.from_curie(row["curie"]),
            name=row["name"],
            scope=(
                Reference.from_curie(row["scope"])
                if "scope" in row
                else Reference.from_curie("oboInOwl:hasSynonym")
            ),
            type=_safe_parse_curie(row["type"]) if "type" in row else None,
            provenance=[
                Reference.from_curie(provenance_curie)
                for provenance_curie in (row.get("provenance") or "").split(",")
                if provenance_curie.strip()
            ],
            contributor=Reference(prefix="orcid", identifier=row["contributor"]),
        )

    def as_gilda_term(self) -> "gilda.Term":
        """Get this synonym as a gilda term."""
        if not self.name:
            raise ValueError("can't make a Gilda term without a label")

        import gilda
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


def _safe_parse_curie(x) -> Optional[Reference]:  # type:ignore
    if pd.isna(x) or not x.strip():
        return None
    return Reference.from_curie(x.strip())


def get_positive_synonyms() -> List[Synonym]:
    """Get positive synonyms curated in Biosynonyms."""
    return parse_synonyms(POSITIVES_PATH)


def get_negative_synonyms() -> List[Synonym]:
    """Get negative synonyms curated in Biosynonyms."""
    return parse_synonyms(NEGATIVES_PATH)


def parse_synonyms(path: Union[str, Path]) -> List[Synonym]:
    """Load synonyms from a file."""
    path = Path(path).resolve()
    with path.open() as file:
        return [Synonym.from_row(d) for d in csv.DictReader(file, delimiter="\t")]


def get_gilda_terms() -> Iterable["gilda.Term"]:
    """Get Gilda terms for all positive synonyms."""
    for synonym in parse_synonyms(POSITIVES_PATH):
        yield synonym.as_gilda_term()
