"""Sort the synonyms file."""

from biosynonyms.model import lint_synonyms

from .resources import (
    NEGATIVES_PATH,
    POSITIVES_PATH,
    _load_unentities,
    write_unentities,
)


def _main() -> None:
    lint_synonyms(POSITIVES_PATH)
    lint_synonyms(NEGATIVES_PATH)
    write_unentities(list(_load_unentities()))


if __name__ == "__main__":
    _main()
