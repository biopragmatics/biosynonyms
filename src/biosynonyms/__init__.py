"""Code for biosynonyms."""

from .model import Synonym, grounder_from_synonyms, group_synonyms, parse_synonyms
from .resources import (
    get_gilda_terms,
    get_grounder,
    get_negative_synonyms,
    get_positive_synonyms,
    load_unentities,
)

__all__ = [
    "Synonym",
    "get_gilda_terms",
    "get_grounder",
    "get_negative_synonyms",
    "get_positive_synonyms",
    "grounder_from_synonyms",
    "group_synonyms",
    "load_unentities",
    "parse_synonyms",
]
