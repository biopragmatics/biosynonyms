"""Code for biosynonyms."""

from .model import (
    LiteralMapping,
    LiteralMappingTuple,
    Synonym,
    SynonymTuple,
    grounder_from_synonyms,
    group_synonyms,
    parse_synonyms,
    write_synonyms,
)
from .resources import (
    get_gilda_terms,
    get_grounder,
    get_negative_synonyms,
    get_positive_synonyms,
    load_unentities,
)

__all__ = [
    "LiteralMapping",
    "LiteralMappingTuple",
    "Synonym",
    "SynonymTuple",
    "get_gilda_terms",
    "get_grounder",
    "get_negative_synonyms",
    "get_positive_synonyms",
    "grounder_from_synonyms",
    "group_synonyms",
    "load_unentities",
    "parse_synonyms",
    "write_synonyms",
]
