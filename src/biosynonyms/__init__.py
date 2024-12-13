"""Code for biosynonyms."""

from .resources import (
    Synonym,
    get_gilda_terms,
    get_negative_synonyms,
    get_positive_synonyms,
    group_synonyms,
    load_unentities,
    parse_synonyms,
)

__all__ = [
    "Synonym",
    "get_gilda_terms",
    "get_negative_synonyms",
    "get_positive_synonyms",
    "group_synonyms",
    "load_unentities",
    "parse_synonyms",
]
