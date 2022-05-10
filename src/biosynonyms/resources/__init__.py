"""Resources for biosynonyms."""

from pathlib import Path

__all__ = [
    "POSITIVES_PATH",
    "NEGATIVES_PATH",
    "sort_key",
]

HERE = Path(__file__).parent.resolve()
POSITIVES_PATH = HERE.joinpath("positives.tsv")
NEGATIVES_PATH = HERE.joinpath("negatives.tsv")


def sort_key(row):
    """Return a key for sorting a row."""
    return (row[0].casefold(), row[0], row[1].casefold(), row[1])
