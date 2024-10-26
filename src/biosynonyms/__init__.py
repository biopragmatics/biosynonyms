"""Code for biosynonyms."""

from .resources import (
    Synonym,
    get_negative_synonyms,
    get_positive_synonyms,
    iter_gilda_terms,
    load_unentities,
    parse_synonyms,
)

__all__ = [
    "Synonym",
    "get_positive_synonyms",
    "get_negative_synonyms",
    "parse_synonyms",
    "iter_gilda_terms",
    "load_unentities",
]
