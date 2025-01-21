"""Test the data model."""

import unittest

from curies import NamedReference
from curies import vocabulary as v

from biosynonyms.model import Synonym

TEST_REFERENCE = NamedReference.from_curie("test:1", "test")


class TestModel(unittest.TestCase):
    """Test the data model."""

    def test_gilda_synonym(self) -> None:
        """Test getting gilda terms."""
        synonym = Synonym(
            text="tests",
            predicate=v.has_exact_synonym,
            type=v.plural_form,
            reference=TEST_REFERENCE,
        )
        gilda_term = synonym.to_gilda()
        self.assertEqual("synonym", gilda_term.status)

        # the predicate and plural form information gets lost in the round trio
        synonym_re_expected = Synonym(
            text="tests", predicate=v.has_related_synonym, reference=TEST_REFERENCE
        )
        self.assertEqual(synonym_re_expected, Synonym.from_gilda(gilda_term))

    def test_gilda_name(self) -> None:
        """Test getting gilda terms."""
        synonym = Synonym(text="test", predicate=v.has_label, reference=TEST_REFERENCE)
        gilda_term = synonym.to_gilda()
        self.assertEqual("name", gilda_term.status)

        self.assertEqual(synonym, Synonym.from_gilda(gilda_term))

    def test_gilda_former_name(self) -> None:
        """Test getting gilda terms."""
        synonym = Synonym(
            text="old test",
            predicate=v.has_exact_synonym,
            reference=TEST_REFERENCE,
            type=v.previous_name,
        )
        gilda_term = synonym.to_gilda()
        self.assertEqual("former_name", gilda_term.status)

        # the predicate gets lost in round trip
        synonym_re_expected = Synonym(
            text="tests", predicate=v.has_related_synonym, reference=TEST_REFERENCE
        )
        self.assertEqual(synonym_re_expected, Synonym.from_gilda(gilda_term))
