"""Generate OWL from the positive synonyms."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import ssslm.ontology

from biosynonyms.resources import get_positive_synonyms

__all__ = [
    "METADATA",
    "TTL_PATH",
    "write_owl_rdf",
]

HERE = Path(__file__).parent.resolve()
EXPORT = HERE.parent.parent.joinpath("exports")
EXPORT.mkdir(exist_ok=True)

TTL_PATH = EXPORT.joinpath("biosynonyms.ttl")
URI = "https://w3id.org/biopragmatics/resources/biosynonyms.ttl"

METADATA = ssslm.ontology.Metadata(
    uri=URI,
    title="Biosynonyms in OWL",
    description="An ontology representation of community curated synonyms in Biosynonyms",
    license="https://creativecommons.org/publicdomain/zero/1.0/",
    comments=[
        "Built by https://github.com/biopragmatics/biosynonyms",
    ],
)


def write_owl_rdf(**kwargs: Any) -> None:
    """Write OWL RDF in a Turtle file."""
    ssslm.ontology.write_owl_ttl(get_positive_synonyms(), TTL_PATH, metadata=METADATA, **kwargs)


if __name__ == "__main__":
    write_owl_rdf()
