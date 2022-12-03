"""Resources for biosynonyms."""

from pathlib import Path
from typing import Iterable, cast

__all__ = [
    "POSITIVES_PATH",
    "NEGATIVES_PATH",
    "UNENTITIES_PATH",
    "load_unentities",
    "sort_key",
]

HERE = Path(__file__).parent.resolve()
POSITIVES_PATH = HERE.joinpath("positives.tsv")
NEGATIVES_PATH = HERE.joinpath("negatives.tsv")
UNENTITIES_PATH = HERE.joinpath("unentities.tsv")


def sort_key(row):
    """Return a key for sorting a row."""
    return row[0].casefold(), row[0], row[1].casefold(), row[1]


def load_unentities() -> set[str]:
    return {line[0] for line in _load_unentities()}


def _load_unentities() -> Iterable[tuple[str, str]]:
    with UNENTITIES_PATH.open() as file:
        _header = next(file)
        for line in file:
            yield cast(tuple[str, str], line.strip().split("\t"))


def _unentities_key(row):
    return row[0].casefold()


def write_unentities(rows: Iterable[tuple[str, str]]) -> None:
    with UNENTITIES_PATH.open("w") as file:
        print("text", "curator_orcid", sep="\t", file=file)
        for row in sorted(rows, key=_unentities_key):
            print(*row, sep="\t", file=file)


def lint():
    write_unentities(list(_load_unentities()))


if __name__ == "__main__":
    lint()
