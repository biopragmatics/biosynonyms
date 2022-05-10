"""Tests for data integrity of biosynoynms database."""

import unittest
from collections import Counter

import bioregistry

from biosynonyms.resources import NEGATIVES_PATH, POSITIVES_PATH

SYNONYM_TYPES = {
    "skos:exactMatch",
    "skos:broadMatch",
    "skos:narrowMatch",
}


class TestIntegrity(unittest.TestCase):
    """Test case for data integrity tests."""

    def assert_curie(self, curie: str):
        """Assert a CURIE is standardized against the Bioregistry.

        :param curie: A compact uniform resource identifier
            of the form ``<prefix>:<identifier>``.
        """
        prefix, identifier = curie.split(":", 1)

        norm_prefix = bioregistry.normalize_prefix(prefix)
        self.assertIsNotNone(norm_prefix)

        preferred_prefix = bioregistry.get_preferred_prefix(prefix) or norm_prefix
        self.assertEqual(preferred_prefix, prefix)

        pattern = bioregistry.get_pattern(prefix)
        if pattern:
            self.assertRegex(identifier, pattern)

    def test_positives(self):
        """Test each row in the positives file."""
        with POSITIVES_PATH.open() as file:
            _, *rows = [tuple(line.strip().split("\t")) for line in file]

        for row_index, row in enumerate(rows, start=1):
            with self.subTest(row=row_index):
                self.assertEquals(5, len(row))
                text, curie, stype, references, orcid = row
                self.assertLess(1, len(text), msg="can not have 1 letter synonyms")
                self.assert_curie(curie)
                self.assertIn(stype, SYNONYM_TYPES)
                for reference in references.split(","):
                    reference = reference.strip()
                    self.assert_curie(reference)
                self.assert_curie(f"orcid:{orcid}")

        # test sorted
        self.assertEqual(sorted(rows), rows, msg="synonyms are not properly sorted")

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
                self.assertEquals(4, len(row))
                text, curie, references, orcid = row
                self.assertLess(1, len(text), msg="can not have 1 letter synonyms")
                self.assert_curie(curie)
                for reference in references.split(","):
                    reference = reference.strip()
                    self.assert_curie(reference)
                self.assert_curie(f"orcid:{orcid}")

        # test sorted
        self.assertEqual(sorted(rows), rows, msg="negative synonyms are not properly sorted")

        # test no duplicates
        c = Counter(row[:2] for row in rows)
        duplicated = {key: count for key, count in c.items() if count > 1}
        self.assertEqual(0, len(duplicated), msg=f"duplicated entries: {duplicated}")
