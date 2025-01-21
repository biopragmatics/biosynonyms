"""Test the data model."""

import unittest

from curies import NamedReference
from curies import vocabulary as v

from biosynonyms.model import DEFAULT_PREDICATE, LiteralMapping

TEST_REFERENCE = NamedReference.from_curie("test:1", "test")


class TestModel(unittest.TestCase):
    """Test the data model."""

    def test_gilda_synonym(self) -> None:
        """Test getting gilda terms."""
        literal_mapping = LiteralMapping(
            text="tests",
            predicate=v.has_exact_synonym,
            type=v.plural_form,
            reference=TEST_REFERENCE,
        )
        gilda_term = literal_mapping.to_gilda()
        self.assertEqual("synonym", gilda_term.status)

        # the predicate and plural form information gets lost in the round trio
        literal_mapping_expected = LiteralMapping(
            text="tests", predicate=DEFAULT_PREDICATE, reference=TEST_REFERENCE
        )
        self.assertEqual(literal_mapping_expected, LiteralMapping.from_gilda(gilda_term))

    def test_gilda_name(self) -> None:
        """Test getting gilda terms."""
        literal_mapping = LiteralMapping(
            text="test", predicate=v.has_label, reference=TEST_REFERENCE
        )
        gilda_term = literal_mapping.to_gilda()
        self.assertEqual("name", gilda_term.status)

        self.assertEqual(literal_mapping, LiteralMapping.from_gilda(gilda_term))

    def test_gilda_former_name(self) -> None:
        """Test getting gilda terms."""
        self.maxDiff = None
        literal_mapping = LiteralMapping(
            text="old test",
            predicate=v.has_exact_synonym,
            reference=TEST_REFERENCE,
            type=v.previous_name,
        )
        gilda_term = literal_mapping.to_gilda()
        self.assertEqual("former_name", gilda_term.status)

        # the predicate gets lost in round trip
        literal_mapping_expected = LiteralMapping(
            text="old test",
            predicate=DEFAULT_PREDICATE,
            type=v.previous_name,
            reference=TEST_REFERENCE,
        )
        self.assertEqual(literal_mapping_expected, LiteralMapping.from_gilda(gilda_term))
