"""Sort the synonyms file."""

from biosynonyms.model import lint_literal_mappings

from .resources import (
    NEGATIVES_PATH,
    POSITIVES_PATH,
    _load_unentities,
    write_unentities,
)


def _main() -> None:
    lint_literal_mappings(POSITIVES_PATH)
    lint_literal_mappings(NEGATIVES_PATH)
    write_unentities(list(_load_unentities()))


if __name__ == "__main__":
    _main()
