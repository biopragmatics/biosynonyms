"""Sort the synonyms file."""

from pathlib import Path

HERE = Path(__file__).parent.resolve()
ROOT = HERE.parent.parent.resolve()


def _sort(path: Path):
    with path.open() as file:
        header, *rows = [
            line.strip().split("\t")
            for line in file
        ]
    rows = sorted(rows)
    with path.open("w") as file:
        print(*header, sep='\t', file=file)
        for row in rows:
            print(*row, sep='\t', file=file)


def _main():
    _sort(ROOT.joinpath("synonyms.tsv"))
    _sort(ROOT.joinpath("negatives.tsv"))


if __name__ == '__main__':
    _main()
