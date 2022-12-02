"""Resources for biosynonyms."""

from pathlib import Path

from gilda.process import normalize

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
UNENTITIES_PATH = HERE.joinpath("unentities.txt")


def sort_key(row):
    """Return a key for sorting a row."""
    return row[0].casefold(), row[0], row[1].casefold(), row[1]


def load_unentities() -> set[str]:
    # TODO check these are stripped and have no tabs in unit tests
    return set(UNENTITIES_PATH.read_text().splitlines())
