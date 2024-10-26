"""Resources for Biosynonyms."""

from __future__ import annotations

import csv
import datetime
from collections import defaultdict
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
    cast,
)

import pandas as pd
import requests
from curies import Reference
from pydantic import BaseModel, Field
from pydantic_extra_types.language_code import LanguageAlpha2
from tqdm import tqdm

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
    "group_synonyms",
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


def _clean_str(s: str) -> str:
    return s


class Synonym(BaseModel):
    """A data model for synonyms."""

    text: str
    language: Optional[LanguageAlpha2] = Field(
        None,
        description="The language of the synonym. If not given, typically assumed to be american english.",
    )
    reference: Reference
    name: str
    scope: Reference = Field(
        default=Reference.from_curie("oboInOwl:hasSynonym"),
        description="The predicate that connects the term (as subject) to the textual synonym (as object)",
    )
    type: Optional[Reference] = Field(
        default=None,
        title="Synonym type",
        description="See the OBO Metadata Ontology for valid values",
    )

    provenance: List[Reference] = Field(
        default_factory=list,
        description="A list of articles (e.g., from PubMed, PMC, arXiv) where this synonym appears",
    )
    contributor: Optional[Reference] = Field(
        None, description="The contributor, usually given as a reference to ORCID"
    )
    comment: Optional[str] = Field(
        None, description="An optional comment on the synonym curation or status"
    )
    source: Optional[str] = Field(
        None, description="The name of the resource where the synonym was curated"
    )
    date: Optional[datetime.datetime] = Field(None, description="The date of initial curation")

    def get_all_references(self) -> Set[Reference]:
        """Get all references made by this object."""
        rv: Set[Reference] = {self.reference, self.scope, *self.provenance}
        if self.type:
            rv.add(self.type)
        if self.contributor:
            rv.add(self.contributor)
        return rv

    @property
    def curie(self) -> str:
        """Get the reference's CURIE."""
        return cast(str, self.reference.curie)

    @property
    def date_str(self) -> str:
        """Get the date as a string."""
        if self.date is None:
            raise ValueError("date is not set")
        return self.date.strftime("%Y-%m-%d")

    @property
    def text_for_turtle(self) -> str:
        """Get the text ready for an object slot in Turtle, with optional language tag."""
        tt = f'"{_clean_str(self.text)}"'
        if self.language:
            tt += f"@{self.language}"
        return tt

    @classmethod
    def from_row(
        cls, row: Dict[str, Any], *, names: Optional[Mapping[Reference, str]] = None
    ) -> "Synonym":
        """Parse a dictionary representing a row in a TSV."""
        reference = Reference.from_curie(row["curie"])
        name = (names or {}).get(reference) or row.get("name") or row["text"]
        data = dict(
            text=row["text"],
            reference=reference,
            name=name,
            scope=(
                Reference.from_curie(scope_curie.strip())
                if (scope_curie := row.get("scope"))
                else Reference.from_curie("oboInOwl:hasSynonym")
            ),
            type=_safe_parse_curie(row["type"]) if "type" in row else None,
            provenance=[
                Reference.from_curie(provenance_curie.strip())
                for provenance_curie in (row.get("provenance") or "").split(",")
                if provenance_curie.strip()
            ],
            language=row.get("language") or None,  # get("X") or None protects against empty strings
            comment=row.get("comment") or None,
            source=row.get("source") or None,
        )
        if contributor := (row.get("contributor") or "").strip():
            data["contributor"] = Reference(prefix="orcid", identifier=contributor)
        if date := (row.get("date") or "").strip():
            data["date"] = datetime.datetime.strptime(date, "%Y-%m-%d")

        return cls.model_validate(data)

    @classmethod
    def from_gilda_term(cls, term: "gilda.Term") -> "Synonym":
        """Get this synonym as a gilda term.

        :param term: A Gilda term
        :returns: A synonym object

        .. warning::

            Gilda's data model is less complete, so resulting synonym objects
            will not have detailed curation provenance
        """
        data = dict(
            text=term.text,
            # TODO standardize?
            reference=Reference(prefix=term.db, identifier=term.id),
            name=term.entry_name,
            source=term.source,
        )
        return cls.model_validate(data)

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
            # TODO is Gilda's status vocabulary worth building an OMO map to/from?
            status="synonym",
            source=self.source or "biosynonyms",
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


def parse_synonyms(
    path: Union[str, Path],
    *,
    delimiter: Optional[str] = None,
    names: Optional[Mapping[Reference, str]] = None,
) -> List[Synonym]:
    """Load synonyms from a file.

    :param path: A local file path or URL for a biosynonyms-flavored CSV/TSV file
    :param delimiter: The delimiter for the CSV/TSV file. Defaults to tab
    :param names: A pre-parsed dictionary from references (i.e., prefix-luid pairs) to default labels
    :returns: A list of synonym objects parsed from the table
    """
    if isinstance(path, str) and any(path.startswith(schema) for schema in ("https://", "http://")):
        res = requests.get(path, timeout=15)
        res.raise_for_status()
        return _from_lines(res.iter_lines(decode_unicode=True), delimiter=delimiter, names=names)

    path = Path(path).resolve()

    if path.suffix == ".numbers":
        return _parse_numbers(path, names=names)

    with path.open() as file:
        return _from_lines(file, delimiter=delimiter, names=names)


def _parse_numbers(
    path: Union[str, Path],
    *,
    names: Optional[Mapping[Reference, str]] = None,
) -> List[Synonym]:
    # code example from https://pypi.org/project/numbers-parser
    import numbers_parser

    doc = numbers_parser.Document(path)
    sheets = doc.sheets
    tables = sheets[0].tables
    header, *rows = tables[0].rows(values_only=True)
    return _from_dicts((dict(zip(header, row)) for row in rows), names=names)


def _from_lines(
    lines: Iterable[str],
    *,
    delimiter: Optional[str] = None,
    names: Optional[Mapping[Reference, str]] = None,
) -> List[Synonym]:
    return _from_dicts(csv.DictReader(lines, delimiter=delimiter or "\t"), names=names)


def _from_dicts(
    dicts: Iterable[Dict[str, Any]],
    *,
    names: Optional[Mapping[Reference, str]] = None,
) -> List[Synonym]:
    return [Synonym.from_row(record, names=names) for record in dicts if record]


def get_gilda_terms() -> Iterable["gilda.Term"]:
    """Get Gilda terms for all positive synonyms."""
    for synonym in parse_synonyms(POSITIVES_PATH):
        yield synonym.as_gilda_term()


def group_synonyms(synonyms: Iterable[Synonym]) -> dict[Reference, List[Synonym]]:
    """Aggregate synonyms by reference."""
    dd: defaultdict[Reference, List[Synonym]] = defaultdict(list)
    for synonym in tqdm(synonyms, unit="synonym", unit_scale=True, leave=False):
        dd[synonym.reference].append(synonym)
    return dict(dd)
