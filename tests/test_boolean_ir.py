"""
Run from the project root:

    python -m unittest discover -s tests
"""

from __future__ import annotations

import tempfile
import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from boolean_ir.io_utils import load_jsonl_documents, split_documents
from boolean_ir.query_parser import QuerySyntaxError
from boolean_ir.system import BooleanIRSystem


DATA_PATH = PROJECT_ROOT / "data" / "raw" / "sample_corpus.jsonl"


class BooleanIRSystemTests(unittest.TestCase):
    """Tests for Boolean retrieval, phrases, updates, merge, and persistence."""

    def setUp(self) -> None:
        self.documents = load_jsonl_documents(DATA_PATH)
        self.split_a = split_documents(self.documents, "A")
        self.split_b = split_documents(self.documents, "B")
        self.split_c = split_documents(self.documents, "C")

        self.system = BooleanIRSystem()
        self.system.build_initial_index(self.split_a + self.split_b)

    def test_term_and_boolean_queries(self) -> None:
        self.assertEqual(self.system.search_ids("information AND retrieval"), {"A1", "B2"})
        self.assertEqual(self.system.search_ids("model AND NOT vector"), {"A2", "B1"})
        self.assertEqual(
            self.system.search_ids("(information OR probabilistic) AND retrieval"), {"A1", "B2"}
        )

    def test_phrase_query(self) -> None:
        self.assertEqual(self.system.search_ids('"inverted index"'), {"A3", "A4"})
        self.assertEqual(self.system.search_ids('"vector space model"'), {"A5"})

    def test_add_documents_to_auxiliary_index(self) -> None:
        self.assertEqual(self.system.search_ids('"auxiliary index"'), set())
        self.system.add_documents(self.split_c)
        self.assertEqual(self.system.search_ids('"auxiliary index"'), {"C1"})
        self.assertEqual(self.system.search_ids("boolean AND phrase"), {"C3"})

    def test_lazy_deletion(self) -> None:
        self.assertEqual(self.system.search_ids('"dynamic indexing"'), {"B4"})
        self.system.delete_documents(document.doc_id for document in self.split_b)
        self.assertEqual(self.system.search_ids('"dynamic indexing"'), set())
        self.assertNotIn("B4", self.system.active_docs)
        self.assertIn("B4", self.system.deleted_docs)

    def test_merge_preserves_results_and_cleans_state(self) -> None:
        self.system.add_documents(self.split_c)
        self.system.delete_documents(document.doc_id for document in self.split_b)

        before_merge = self.system.search_ids("index OR documents")
        self.system.merge_indexes()
        after_merge = self.system.search_ids("index OR documents")

        self.assertEqual(before_merge, after_merge)
        self.assertEqual(len(self.system.deleted_docs), 0)
        self.assertEqual(self.system.auxiliary_index.stats()["documents_in_index"], 0)
        self.assertTrue(all(not doc_id.startswith("B") for doc_id in self.system.active_docs))

    def test_save_and_load(self) -> None:
        self.system.add_documents(self.split_c)
        self.system.delete_documents(document.doc_id for document in self.split_b)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "index.json"
            self.system.save(path)
            loaded = BooleanIRSystem.load(path)

        self.assertEqual(loaded.search_ids('"auxiliary index"'), {"C1"})
        self.assertEqual(loaded.search_ids('"dynamic indexing"'), set())
        self.assertEqual(loaded.active_docs, self.system.active_docs)
        self.assertEqual(loaded.deleted_docs, self.system.deleted_docs)

    def test_invalid_query(self) -> None:
        with self.assertRaises(QuerySyntaxError):
            self.system.search_ids("information AND")

        with self.assertRaises(QuerySyntaxError):
            self.system.search_ids('"unclosed phrase')


if __name__ == "__main__":
    unittest.main()
