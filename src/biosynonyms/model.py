"""A data model for synonyms."""

from __future__ import annotations

import csv
import datetime
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

import requests
from curies import NamedReference, Reference
from pydantic import BaseModel, Field
from pydantic_extra_types.language_code import LanguageAlpha2
from tqdm import tqdm

if TYPE_CHECKING:
    import gilda

__all__ = [
    "Synonym",
    "append_synonym",
    "group_synonyms",
    "lint_synonyms",
    "parse_synonyms",
]


class Synonym(BaseModel):
    """A data model for synonyms."""

    text: str
    language: LanguageAlpha2 | None = Field(
        None,
        description="The language of the synonym. If not given, typically "
        "assumed to be american english.",
    )
    reference: NamedReference
    scope: Reference = Field(
        default=Reference.from_curie("oboInOwl:hasSynonym"),
        description="The predicate that connects the term (as subject) "
        "to the textual synonym (as object)",
    )
    type: Reference | None = Field(
        default=None,
        title="Synonym type",
        description="See the OBO Metadata Ontology for valid values",
    )

    provenance: list[Reference] = Field(
        default_factory=list,
        description="A list of articles (e.g., from PubMed, PMC, arXiv) where this synonym appears",
    )
    contributor: Reference | None = Field(
        None, description="The contributor, usually given as a reference to ORCID"
    )
    comment: str | None = Field(
        None, description="An optional comment on the synonym curation or status"
    )
    source: str | None = Field(
        None, description="The name of the resource where the synonym was curated"
    )
    date: datetime.datetime | None = Field(None, description="The date of initial curation")

    def get_all_references(self) -> set[Reference]:
        """Get all references made by this object."""
        rv: set[Reference] = {self.reference, self.scope, *self.provenance}
        if self.type:
            rv.add(self.type)
        if self.contributor:
            rv.add(self.contributor)
        return rv

    @property
    def name(self) -> str:
        """Get the reference's name."""
        return self.reference.name

    @property
    def curie(self) -> str:
        """Get the reference's CURIE."""
        return self.reference.curie

    @property
    def date_str(self) -> str:
        """Get the date as a string."""
        if self.date is None:
            raise ValueError("date is not set")
        return self.date.strftime("%Y-%m-%d")

    @classmethod
    def from_row(
        cls, row: dict[str, Any], *, names: Mapping[Reference, str] | None = None
    ) -> Synonym:
        """Parse a dictionary representing a row in a TSV."""
        reference = Reference.from_curie(row["curie"])
        name = (names or {}).get(reference) or row.get("name") or row["text"]
        data = {
            "text": row["text"],
            "reference": NamedReference(
                prefix=reference.prefix, identifier=reference.identifier, name=name
            ),
            "scope": (
                Reference.from_curie(scope_curie.strip())
                if (scope_curie := row.get("scope"))
                else Reference.from_curie("oboInOwl:hasSynonym")
            ),
            "type": _safe_parse_curie(row["type"]) if "type" in row else None,
            "provenance": [
                Reference.from_curie(provenance_curie.strip())
                for provenance_curie in (row.get("provenance") or "").split(",")
                if provenance_curie.strip()
            ],
            # get("X") or None protects against empty strings
            "language": row.get("language") or None,
            "comment": row.get("comment") or None,
            "source": row.get("source") or None,
        }
        if contributor_curie := (row.get("contributor") or "").strip():
            data["contributor"] = Reference.from_curie(contributor_curie)
        if date := (row.get("date") or "").strip():
            data["date"] = datetime.datetime.strptime(date, "%Y-%m-%d")

        return cls.model_validate(data)

    @classmethod
    def from_gilda(cls, term: gilda.Term) -> Synonym:
        """Get this synonym as a gilda term.

        :param term: A Gilda term
        :returns: A synonym object

        .. warning::

            Gilda's data model is less complete, so resulting synonym objects
            will not have detailed curation provenance
        """
        data = {
            "text": term.text,
            # TODO standardize?
            "reference": NamedReference(prefix=term.db, identifier=term.id, name=term.entry_name),
            "source": term.source,
        }
        return cls.model_validate(data)

    def to_gilda(self) -> gilda.Term:
        """Get this synonym as a gilda term."""
        if not self.name:
            raise ValueError("can't make a Gilda term without a label")
        return _gilda_term(
            text=self.text,
            reference=self.reference,
            name=self.name,
            # TODO is Gilda's status vocabulary worth building an OMO map to/from?
            status="synonym",
            source=self.source or "biosynonyms",
        )


def _gilda_term(
    *,
    text: str,
    reference: Reference,
    name: str | None = None,
    status: str,
    source: str | None,
) -> gilda.Term:
    import gilda
    from gilda.process import normalize

    return gilda.Term(
        normalize(text),
        text=text,
        db=reference.prefix,
        id=reference.identifier,
        entry_name=name or text,
        status=status,
        source=source,
    )


def _safe_parse_curie(x) -> Reference | None:  # type:ignore
    if not isinstance(x, str) or not x.strip():
        return None
    return Reference.from_curie(x.strip())


def append_synonym(path: str | Path, synonym: Synonym) -> None:
    """Append a synonym to an existing file."""
    raise NotImplementedError


def parse_synonyms(
    path: str | Path,
    *,
    delimiter: str | None = None,
    names: Mapping[Reference, str] | None = None,
) -> list[Synonym]:
    """Load synonyms from a file.

    :param path: A local file path or URL for a biosynonyms-flavored CSV/TSV file
    :param delimiter: The delimiter for the CSV/TSV file. Defaults to tab
    :param names: A pre-parsed dictionary from references
        (i.e., prefix-luid pairs) to default labels
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
    path: str | Path,
    *,
    names: Mapping[Reference, str] | None = None,
) -> list[Synonym]:
    # code example from https://pypi.org/project/numbers-parser
    import numbers_parser

    doc = numbers_parser.Document(path)
    sheets = doc.sheets
    tables = sheets[0].tables
    header, *rows = tables[0].rows(values_only=True)
    return _from_dicts((dict(zip(header, row, strict=False)) for row in rows), names=names)


def _from_lines(
    lines: Iterable[str],
    *,
    delimiter: str | None = None,
    names: Mapping[Reference, str] | None = None,
) -> list[Synonym]:
    return _from_dicts(csv.DictReader(lines, delimiter=delimiter or "\t"), names=names)


def _from_dicts(
    dicts: Iterable[dict[str, Any]],
    *,
    names: Mapping[Reference, str] | None = None,
) -> list[Synonym]:
    rv = []
    for i, record in enumerate(dicts, start=2):
        record = {k: v for k, v in record.items() if k and v and k.strip() and v.strip()}
        if record:
            try:
                synonym = Synonym.from_row(record, names=names)
            except ValueError as e:
                raise ValueError(f"failed on row {i}: {record}") from e
            rv.append(synonym)
    return rv


def group_synonyms(synonyms: Iterable[Synonym]) -> dict[Reference, list[Synonym]]:
    """Aggregate synonyms by reference."""
    dd: defaultdict[Reference, list[Synonym]] = defaultdict(list)
    for synonym in tqdm(synonyms, unit="synonym", unit_scale=True, leave=False):
        dd[synonym.reference].append(synonym)
    return dict(dd)


def grounder_from_synonyms(synonyms: Iterable[Synonym]) -> gilda.Grounder:
    """Get a Gilda grounder from synonyms."""
    import gilda

    rv = gilda.Grounder([synonym.to_gilda() for synonym in synonyms])
    return rv


def lint_synonyms(path: Path) -> None:
    """Lint a synonyms file."""
    with path.open() as file:
        header, *rows = (line.strip().split("\t") for line in file)
    rows = sorted(rows, key=_sort_key)
    with path.open("w") as file:
        print(*header, sep="\t", file=file)
        for row in rows:
            print(*row, sep="\t", file=file)


def _sort_key(row: Sequence[str]) -> tuple[str, str, str, str]:
    """Return a key for sorting a row."""
    return row[0].casefold(), row[0], row[1].casefold(), row[1]
