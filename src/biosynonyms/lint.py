"""Sort the synonyms file."""

from pathlib import Path

from .resources import (
    NEGATIVES_PATH,
    POSITIVES_PATH,
    _load_unentities,
    sort_key,
    write_unentities,
)


def _sort(path: Path) -> None:
    with path.open() as file:
        header, *rows = [line.strip().split("\t") for line in file]
    rows = sorted(rows, key=sort_key)
    with path.open("w") as file:
        print(*header, sep="\t", file=file)  # noqa:T201
        for row in rows:
            print(*row, sep="\t", file=file)  # noqa:T201


def _main() -> None:
    _sort(POSITIVES_PATH)
    _sort(NEGATIVES_PATH)
    write_unentities(list(_load_unentities()))


if __name__ == "__main__":
    _main()
