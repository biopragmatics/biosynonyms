"""A data model for synonyms."""

from __future__ import annotations

import csv
import datetime
import importlib.util
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, NamedTuple, TypeAlias

import requests
from curies import NamableReference, NamedReference, Reference
from curies import vocabulary as v
from pydantic import BaseModel, Field
from pydantic_extra_types.language_code import LanguageAlpha2
from tqdm import tqdm

if TYPE_CHECKING:
    import gilda
    import pandas

__all__ = [
    "LiteralMapping",
    "LiteralMappingTuple",
    "append_literal_mapping",
    "df_to_literal_mappings",
    "group_literal_mappings",
    "lint_literal_mappings",
    "literal_mappings_to_df",
    "read_literal_mappings",
    "write_literal_mappings",
]


class LiteralMappingTuple(NamedTuple):
    """Represents rows in a spreadsheet."""

    text: str
    curie: str
    name: str | None
    predicate: str
    type: str | None
    provenance: str | None
    contributor: str | None
    date: str | None
    language: str | None
    comment: str | None
    source: str | None


SynonymTuple = LiteralMappingTuple

#: The header for the spreadsheet
HEADER = list(LiteralMappingTuple._fields)

#: A set of permissible predicates
PREDICATES = [v.has_label, *v.synonym_scopes.values()]

#: The default synonym type predicate was chosen based on the OBO
#: standard - when you don't specify a scope, this is what it infers
DEFAULT_PREDICATE = v.has_related_synonym


class LiteralMapping(BaseModel):
    """A data model for literal mappings."""

    # the first four fields are the core of the literal mapping
    reference: NamableReference = Field(..., description="The subject of the literal mapping")
    predicate: Reference = Field(
        default=DEFAULT_PREDICATE,
        description="The predicate that connects the term (as subject) "
        "to the textual synonym (as object)",
        examples=PREDICATES,
    )
    text: str = Field(..., description="The object of the literal mapping")
    language: LanguageAlpha2 | None = Field(
        None,
        description="The language of the synonym. If not given, typically "
        "assumed to be american english.",
    )

    type: Reference | None = Field(
        default=None,
        title="Synonym type",
        description="A qualification for the type of mapping",
        examples=list(v.synonym_types),
    )
    provenance: list[Reference] = Field(
        default_factory=list,
        description="A list of articles (e.g., from PubMed, PMC, arXiv) where this synonym appears",
    )
    contributor: Reference | None = Field(
        None,
        description="The contributor, usually given as a reference to ORCID",
        examples=[v.charlie],
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
        rv: set[Reference] = {self.reference, self.predicate, *self.provenance}
        if self.type:
            rv.add(self.type)
        if self.contributor:
            rv.add(self.contributor)
        return rv

    @property
    def name(self) -> str | None:
        """Get the reference's (optional) name."""
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
    ) -> LiteralMapping:
        """Parse a dictionary representing a row in a TSV."""
        reference = Reference.from_curie(row["curie"])
        name = (names or {}).get(reference) or row.get("name")
        data = {
            "text": row["text"],
            "reference": NamableReference(
                prefix=reference.prefix, identifier=reference.identifier, name=name
            ),
            "predicate": (
                Reference.from_curie(predicate_curie.strip())
                if (predicate_curie := row.get("predicate"))
                else DEFAULT_PREDICATE
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

    def _as_row(self) -> LiteralMappingTuple:
        """Get the synonym as a row for writing."""
        return LiteralMappingTuple(
            text=self.text,
            curie=self.curie,
            name=self.name,
            predicate=self.predicate.curie,
            type=self.type.curie if self.type else None,
            provenance=",".join(p.curie for p in self.provenance) if self.provenance else None,
            contributor=self.contributor.curie if self.contributor is not None else None,
            date=self.date_str if self.date is not None else None,
            language=self.language or None,
            comment=self.comment or None,
            source=self.source or None,
        )

    @staticmethod
    def _predicate_type_from_gilda(status: GildaStatus) -> tuple[Reference, Reference | None]:
        if status == "name":
            return v.has_label, None
        elif status == "former_name":
            return DEFAULT_PREDICATE, v.previous_name
        elif status == "synonym":
            return DEFAULT_PREDICATE, None
        elif status == "curated":
            # assume higher confidence in exact synonym
            return v.has_exact_synonym, None
        raise ValueError(f"unhandled gilda status: {status}")

    @classmethod
    def from_gilda(cls, term: gilda.Term) -> LiteralMapping:
        """Construct a synonym from a :mod:`gilda` term.

        :param term: A Gilda term
        :returns: A synonym object

        .. warning::

            Gilda's data model is less detailed, so resulting synonym objects
            will not have detailed curation provenance
        """
        predicate, synonym_type = cls._predicate_type_from_gilda(term.status)
        data = {
            "reference": NamedReference(prefix=term.db, identifier=term.id, name=term.entry_name),
            "predicate": predicate,
            "text": term.text,
            "type": synonym_type,
            "source": term.source,
        }
        return cls.model_validate(data)

    def _get_gilda_status(self) -> GildaStatus:
        """Get the Gilda status for a synonym."""
        if self.predicate and self.predicate.pair == v.has_label.pair:
            return "name"
        if self.type and self.type.pair == v.previous_name.pair:
            return "former_name"
        return "synonym"

    def to_gilda(self, organism: str | None = None) -> gilda.Term:
        """Get this synonym as a :mod:`gilda` term.

        :param organism:
            If this is a species-specific term, the NCBI Taxonomy identifier can be passed.
            e.g., '9606' for human.
        :return:
            An object that can be indexed by Gilda for NER and grounding
        """
        if not self.name:
            raise ValueError("can't make a Gilda term without a label")
        return _gilda_term(
            text=self.text,
            reference=self.reference,
            name=self.name,
            status=self._get_gilda_status(),
            source=self.source,
            organism=organism,
        )


Synonym = LiteralMapping

#: See https://github.com/gyorilab/gilda/blob/ea328734f26c91189438e6d3408562f990f38644/gilda/term.py#L167C1-L167C69
GildaStatus: TypeAlias = Literal["name", "synonym", "curated", "former_name"]


def _gilda_term(
    *,
    text: str,
    reference: Reference,
    name: str | None = None,
    status: GildaStatus,
    source: str | None,
    organism: str | None = None,
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
        organism=organism,
    )


def _safe_parse_curie(x) -> Reference | None:  # type:ignore
    if not isinstance(x, str) or not x.strip():
        return None
    return Reference.from_curie(x.strip())


def literal_mappings_to_df(literal_mappings: Iterable[LiteralMapping]) -> pandas.DataFrame:
    """Get a pandas dataframe from the literal mappings."""
    import pandas as pd

    df = pd.DataFrame(
        (literal_mapping._as_row() for literal_mapping in literal_mappings), columns=HEADER
    )

    # remove any columns that are fully blank
    for col in df.columns:
        if df[col].isna().all():
            del df[col]

    return df


def df_to_literal_mappings(
    df: pandas.DataFrame,
    *,
    names: Mapping[Reference, str] | None = None,
) -> list[LiteralMapping]:
    """Get mapping objects from a dataframe."""
    return _from_dicts((row for _, row in df.iterrows()), names=names)


def write_literal_mappings(path: str | Path, literal_mappings: Iterable[LiteralMapping]) -> None:
    """Write literal mappings to a path."""
    path = Path(path).expanduser().resolve()
    if importlib.util.find_spec("pandas"):
        _write_pandas(path, literal_mappings)
    else:
        _write_builtin(path, literal_mappings)


def _write_builtin(path: Path, literal_mappings: Iterable[LiteralMapping]) -> None:
    with path.open("w") as file:
        writer = csv.writer(file, delimiter="\t")
        writer.writerow(HEADER)
        writer.writerows(literal_mapping._as_row() for literal_mapping in literal_mappings)


def _write_pandas(path: Path, literal_mappings: Iterable[LiteralMapping]) -> None:
    df = literal_mappings_to_df(literal_mappings)
    df.to_csv(path, index=False, sep="\t")


def append_literal_mapping(path: str | Path, literal_mapping: LiteralMapping) -> None:
    """Append a literal mapping to an existing file."""
    raise NotImplementedError


def read_literal_mappings(
    path: str | Path,
    *,
    delimiter: str | None = None,
    names: Mapping[Reference, str] | None = None,
) -> list[LiteralMapping]:
    """Load literal mappings from a file.

    :param path: A local file path or URL for a biosynonyms-flavored CSV/TSV file
    :param delimiter: The delimiter for the CSV/TSV file. Defaults to tab
    :param names: A pre-parsed dictionary from references
        (i.e., prefix-luid pairs) to default labels
    :returns: A list of literal mappings parsed from the table
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
) -> list[LiteralMapping]:
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
) -> list[LiteralMapping]:
    return _from_dicts(csv.DictReader(lines, delimiter=delimiter or "\t"), names=names)


def _from_dicts(
    dicts: Iterable[dict[str, Any]],
    *,
    names: Mapping[Reference, str] | None = None,
) -> list[LiteralMapping]:
    rv = []
    for i, record in enumerate(dicts, start=2):
        record = {k: v for k, v in record.items() if k and v and k.strip() and v.strip()}
        if record:
            try:
                literal_mapping = LiteralMapping.from_row(record, names=names)
            except ValueError as e:
                raise ValueError(f"failed on row {i}: {record}") from e
            rv.append(literal_mapping)
    return rv


def group_literal_mappings(
    literal_mappings: Iterable[LiteralMapping],
) -> dict[NamableReference, list[LiteralMapping]]:
    """Aggregate literal mappings by reference."""
    dd: defaultdict[NamableReference, list[LiteralMapping]] = defaultdict(list)
    for literal_mapping in tqdm(
        literal_mappings, unit="literal mapping", unit_scale=True, leave=False
    ):
        dd[literal_mapping.reference].append(literal_mapping)
    return dict(dd)


def grounder_from_literal_mappings(literal_mappings: Iterable[LiteralMapping]) -> gilda.Grounder:
    """Get a Gilda grounder from literal mappings."""
    import gilda

    rv = gilda.Grounder([literal_mapping.to_gilda() for literal_mapping in literal_mappings])
    return rv


def lint_literal_mappings(path: Path) -> None:
    """Lint a literal mappings file."""
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
