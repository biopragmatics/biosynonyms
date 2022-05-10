"""Resources for biosynonyms."""

from pathlib import Path

__all__ = [
    "POSITIVES_PATH",
    "NEGATIVES_PATH",
]

HERE = Path(__file__).parent.resolve()
POSITIVES_PATH = HERE.joinpath("positives.tsv")
NEGATIVES_PATH = HERE.joinpath("negatives.tsv")
