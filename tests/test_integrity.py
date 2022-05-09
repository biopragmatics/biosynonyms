"""Tests for data integrity of biosynoynms database."""

import unittest
from pathlib import Path

import bioregistry

HERE = Path(__file__).parent.resolve()
ROOT = HERE.parent.resolve()
PATH = ROOT.joinpath("synonyms.tsv")


class TestIntegrity(unittest.TestCase):
    """Test case for data integrity tests."""

    def setUp(self):
        """Set up the test case by loading the synonyms file."""
        with PATH.open() as file:
            self.header, *self.rows = [line.strip().split("\t") for line in file]

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

    def test_rows(self):
        """Test each row."""
        # TODO check duplicates
        # TODO check canonical sort order
        for row_index, row in enumerate(self.rows, start=1):
            with self.subTest(row=row_index):
                self.assertEquals(4, len(row))
                self.assert_curie(row[0])
                for reference in row[3].split(","):
                    reference = reference.strip()
                    self.assert_curie(reference)
