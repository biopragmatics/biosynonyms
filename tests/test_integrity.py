"""Tests for data integrity of biosynoynms database."""

import tempfile
import unittest
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

import bioregistry
import ssslm
from curies import ReferenceTuple
from ssslm import Repository

import biosynonyms
from biosynonyms.resources import NEGATIVES_PATH, POSITIVES_PATH, UNENTITIES_PATH

SYNONYM_PREDICATE_CURIES: set[str] = {p.curie for p in ssslm.PREDICATES}


def _sort_key(row: Sequence[str]) -> tuple[str, str, str, str]:
    """Return a key for sorting a row."""
    return row[0].casefold(), row[0], row[1].casefold(), row[1]


class TestIntegrity(unittest.TestCase):
    """Test case for data integrity tests."""

    def assert_curie(self, curie: str):
        """Assert a CURIE is standardized against the Bioregistry.

        :param curie: A compact uniform resource identifier of the form
            ``<prefix>:<identifier>``.
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
            _, *rows = (tuple(line.strip().split("\t")) for line in file)

        for row_index, row in enumerate(rows, start=1):
            with self.subTest(row=row_index):
                self.assertEqual(11, len(row))
                (
                    text,
                    curie,
                    name,
                    predicate,
                    synonym_type,
                    references,
                    contributor_curie,
                    date,
                    _lang,
                    _comment,
                    _src,
                ) = row
                self.assertTrue(name, msg="name must be filled in")
                self.assertLess(1, len(text), msg="can not have 1 letter synonyms")
                self.assert_curie(curie)
                self.assertIn(predicate, SYNONYM_PREDICATE_CURIES)
                if synonym_type:
                    self.assertTrue(synonym_type.startswith("OMO:"))
                for reference in references.split(",") if references else []:
                    reference = reference.strip()
                    self.assert_curie(reference)
                self.assert_curie(contributor_curie)
                if date:
                    self.assertRegex(date, "\\d{4}-\\d{2}-\\d{2}")

        # test sorted
        self.assertEqual(sorted(rows, key=_sort_key), rows, msg="synonyms are not properly sorted")

        # test no duplicates
        c = Counter(row[:2] for row in rows)
        duplicated = {key: count for key, count in c.items() if count > 1}
        self.assertEqual(0, len(duplicated), msg=f"duplicated entries: {duplicated}")

    def test_negatives(self):
        """Test each row in the negatives file."""
        with NEGATIVES_PATH.open() as file:
            _, *rows = (tuple(line.strip().split("\t")) for line in file)

        for row_index, row in enumerate(rows, start=1):
            with self.subTest(row=row_index):
                self.assertEqual(5, len(row))
                text, curie, _name, references, contributor_curie = row
                self.assertLess(1, len(text), msg="can not have 1 letter synonyms")
                self.assert_curie(curie)
                for reference in references.split(","):
                    reference = reference.strip()
                    self.assert_curie(reference)
                self.assert_curie(contributor_curie)

        # test sorted
        self.assertEqual(
            sorted(rows, key=_sort_key),
            rows,
            msg="negative synonyms are not properly sorted",
        )

        # test no duplicates
        c = Counter(row[:2] for row in rows)
        duplicated = {key: count for key, count in c.items() if count > 1}
        self.assertEqual(0, len(duplicated), msg=f"duplicated entries: {duplicated}")

    def test_non_entities(self):
        """Test each row of the non-entities file."""
        with UNENTITIES_PATH.open() as file:
            _header, *rows = (line.strip().split("\t") for line in file)
        self.assertEqual(sorted(rows, key=Repository._stop_words_key), rows)
        for line_number, line in enumerate(rows, start=1):
            with self.subTest(line_number=line_number):
                self.assertEqual(2, len(line))
                text, orcid = line
                self.assertEqual(text.strip(), text)
                self.assertTrue(bioregistry.is_valid_identifier("orcid", orcid))

    def test_gilda(self):
        """Test getting gilda terms."""
        grounder = biosynonyms.make_grounder()
        matches = grounder.get_matches("YAL021C")
        self.assertEqual(1, len(matches))
        self.assertEqual("sgd", matches[0].prefix)
        self.assertEqual("S000000019", matches[0].identifier)

    def test_model(self):
        """Test loading the data model."""
        biosynonyms.get_positive_synonyms()
        biosynonyms.get_negative_synonyms()

    def test_io_roundtrip(self) -> None:
        """Test IO roundtrip."""
        synonyms = biosynonyms.get_positive_synonyms()[:3]  # sample just a few

        with tempfile.TemporaryDirectory() as d:
            path = Path(d).joinpath("test.tsv")
            ssslm.write_literal_mappings(synonyms, path)
            reloaded_synonyms = ssslm.read_literal_mappings(path)

        self.assertEqual(synonyms, reloaded_synonyms)

    def test_df_roundtrip(self) -> None:
        """Test df roundtrip."""
        synonyms = biosynonyms.get_positive_synonyms()[:3]  # sample just a few
        df = ssslm.literal_mappings_to_df(synonyms)
        reconstituted = ssslm.df_to_literal_mappings(df)
        self.assertEqual(synonyms, reconstituted)
