"""Code for biosynonyms."""

from .resources import (
    Synonym,
    get_gilda_terms,
    get_negative_synonyms,
    get_positive_synonyms,
    load_unentities,
    parse_synonyms,
)

__all__ = [
    "Synonym",
    "get_positive_synonyms",
    "get_negative_synonyms",
    "parse_synonyms",
    "get_gilda_terms",
    "load_unentities",
]
