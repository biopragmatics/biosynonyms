"""Code for biosynonyms."""

from .model import (
    LiteralMapping,
    LiteralMappingTuple,
    grounder_from_literal_mappings,
    group_literal_mappings,
    read_literal_mappings,
    write_literal_mappings,
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
    "get_gilda_terms",
    "get_grounder",
    "get_negative_synonyms",
    "get_positive_synonyms",
    "grounder_from_literal_mappings",
    "group_literal_mappings",
    "load_unentities",
    "read_literal_mappings",
    "write_literal_mappings",
]
