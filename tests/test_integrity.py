"""Tests for data integrity of biosynoynms database."""

import unittest
from collections import Counter

import bioregistry
import gilda
from curies import ReferenceTuple

import biosynonyms
from biosynonyms.resources import (
    NEGATIVES_PATH,
    POSITIVES_PATH,
    SYNONYM_SCOPES,
    UNENTITIES_PATH,
    _unentities_key,
    sort_key,
)


class TestIntegrity(unittest.TestCase):
    """Test case for data integrity tests."""

    def assert_curie(self, curie: str):
        """Assert a CURIE is standardized against the Bioregistry.

        :param curie: A compact uniform resource identifier
            of the form ``<prefix>:<identifier>``.
        """
        prefix, identifier = ReferenceTuple.from_curie(curie)

        norm_prefix = bioregistry.normalize_prefix(prefix)
        self.assertIsNotNone(norm_prefix)
        self.assertEqual(norm_prefix, prefix)

        pattern = bioregistry.get_pattern(prefix)
        if pattern:
            self.assertRegex(identifier, pattern)

    def test_positives(self):
        """Test each row in the positives file."""
        with POSITIVES_PATH.open() as file:
            _, *rows = [tuple(line.strip().split("\t")) for line in file]

        for row_index, row in enumerate(rows, start=1):
            with self.subTest(row=row_index):
                self.assertEqual(7, len(row))
                text, curie, _name, scope, synonym_type, references, orcid = row
                self.assertLess(1, len(text), msg="can not have 1 letter synonyms")
                self.assert_curie(curie)
                self.assertIn(scope, SYNONYM_SCOPES)
                if synonym_type:
                    self.assertTrue(synonym_type.startswith("OMO:"))
                for reference in references.split(",") if references else []:
                    reference = reference.strip()
                    self.assert_curie(reference)
                self.assert_curie(f"orcid:{orcid}")

        # test sorted
        self.assertEqual(sorted(rows, key=sort_key), rows, msg="synonyms are not properly sorted")

        # test no duplicates
        c = Counter(row[:2] for row in rows)
        duplicated = {key: count for key, count in c.items() if count > 1}
        self.assertEqual(0, len(duplicated), msg=f"duplicated entries: {duplicated}")

    def test_negatives(self):
        """Test each row in the negatives file."""
        with NEGATIVES_PATH.open() as file:
            _, *rows = [tuple(line.strip().split("\t")) for line in file]

        for row_index, row in enumerate(rows, start=1):
            with self.subTest(row=row_index):
                self.assertEquals(5, len(row))
                text, curie, _name, references, orcid = row
                self.assertLess(1, len(text), msg="can not have 1 letter synonyms")
                self.assert_curie(curie)
                for reference in references.split(","):
                    reference = reference.strip()
                    self.assert_curie(reference)
                self.assert_curie(f"orcid:{orcid}")

        # test sorted
        self.assertEqual(
            sorted(rows, key=sort_key), rows, msg="negative synonyms are not properly sorted"
        )

        # test no duplicates
        c = Counter(row[:2] for row in rows)
        duplicated = {key: count for key, count in c.items() if count > 1}
        self.assertEqual(0, len(duplicated), msg=f"duplicated entries: {duplicated}")

    def test_non_entities(self):
        """Test each row of the non-entities file."""
        with UNENTITIES_PATH.open() as file:
            _header, *rows = (line.strip().split("\t") for line in file)
        self.assertEqual(sorted(rows, key=_unentities_key), rows)
        for line_number, line in enumerate(rows, start=1):
            with self.subTest(line_number=line_number):
                self.assertEqual(2, len(line))
                text, orcid = line
                self.assertEqual(text.strip(), text)
                self.assertTrue(bioregistry.is_valid_identifier("orcid", orcid))

    def test_gilda(self):
        """Test getting tilda terms."""
        grounder = gilda.Grounder(list(biosynonyms.get_gilda_terms()))
        scored_matches = grounder.ground("YAL021C")
        self.assertEqual(1, len(scored_matches))
        self.assertEqual("sgd", scored_matches[0].term.db)
        self.assertEqual("S000000019", scored_matches[0].term.id)

    def test_model(self):
        """Test loading the data model."""
        biosynonyms.get_positive_synonyms()
        biosynonyms.get_negative_synonyms()
