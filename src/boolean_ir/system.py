"""Dynamic Boolean Information Retrieval system.

This module connects the positional index and the Boolean query parser

Design used for efficient updates
---------------------------------
The system uses three structures:

1. main_index
   Contains the initial collection, in this project documents from splits A+B.

2. auxiliary_index
   Contains newly added documents, in this project split C. This avoids
   rebuilding the entire main index every time a document is added.

3. deleted_docs / active_docs
   Deletions are lazy. When a document is deleted, the system records its id in
   the deletion set and removes it from active_docs. Query results are always
   filtered through active_docs, so deleted documents are not returned.

Merging
-------
The merge operation rebuilds the main index from active documents only,
incorporates all documents from the auxiliary index, and permanently removes
previously deleted documents from the searchable index.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Set

from .index import Document, PositionalInvertedIndex
from .query_parser import EvaluationContext, QuerySyntaxError, parse_query
from .tokenizer import tokenize


class BooleanIRSystem:
    """A Boolean IR system with phrase queries and dynamic updates."""

    SERIALIZATION_VERSION = 1

    def __init__(self) -> None:
        self.main_index = PositionalInvertedIndex()
        self.auxiliary_index = PositionalInvertedIndex()

        self.documents: Dict[str, Document] = {}

        self.active_docs: Set[str] = set()
        self.deleted_docs: Set[str] = set()


    def build_initial_index(self, documents: Iterable[Document]) -> None:
        """Create the initial main index from a collection of documents.

        This should be used for the starting collection A+B in the assignment.
        It clears any previous state.
        """
        document_list = list(documents)
        self.documents = {document.doc_id: document for document in document_list}
        self.active_docs = {document.doc_id for document in document_list}
        self.deleted_docs = set()

        self.main_index.build(document_list)
        self.auxiliary_index.clear()

    def add_documents(self, documents: Iterable[Document]) -> None:
        """Add new documents to the auxiliary index.

        Adding to the auxiliary index is efficient because only the new
        documents are tokenized and indexed. The main index remains unchanged
        until ``merge_indexes`` is called.
        """
        for document in documents:
            if document.doc_id in self.active_docs:
                raise ValueError(f"Document {document.doc_id!r} already exists and is active")

            self.documents[document.doc_id] = document
            self.active_docs.add(document.doc_id)
            self.deleted_docs.discard(document.doc_id)
            self.auxiliary_index.add_document(document)

    def delete_document(self, doc_id: str) -> None:
        """Delete one document using lazy deletion.

        The postings are not physically removed immediately. This avoids
        scanning all posting lists. The document simply stops being active.
        """
        if doc_id not in self.documents:
            raise KeyError(f"Unknown document id: {doc_id!r}")

        self.active_docs.discard(doc_id)
        self.deleted_docs.add(doc_id)

    def delete_documents(self, doc_ids: Iterable[str]) -> None:
        """Delete multiple documents using lazy deletion."""
        for doc_id in doc_ids:
            self.delete_document(doc_id)

    def merge_indexes(self) -> None:
        """Merge the auxiliary index into the main index and clean deletions.

        For a compact exam project, rebuilding from active documents is simple,
        correct, and easy to verify. It still demonstrates the dynamic indexing
        idea: additions are first placed in an auxiliary index and deletions are
        first represented as tombstones; merging consolidates the state.
        """
        active_documents = [
            document for doc_id, document in self.documents.items() if doc_id in self.active_docs
        ]
        self.main_index.build(active_documents)
        self.auxiliary_index.clear()
        self.deleted_docs.clear()

    def search(self, query: str) -> List[Document]:
        """Run a Boolean query and return matching active documents.

        Results are sorted by document id for deterministic display. This is not
        ranking; Boolean IR returns a set of matching documents.
        """
        matching_ids = self.search_ids(query)
        return [self.documents[doc_id] for doc_id in sorted(matching_ids)]

    def search_ids(self, query: str) -> Set[str]:
        """Run a Boolean query and return matching active document ids."""
        ast = parse_query(query)
        context = EvaluationContext(
            lookup_term=self._lookup_term,
            lookup_phrase=self._lookup_phrase,
            all_docs=lambda: set(self.active_docs),
        )
        return ast.evaluate(context) & self.active_docs

    def _lookup_term(self, term: str) -> Set[str]:
        """Return active documents containing a term in either index."""
        result = self.main_index.docs_for_term(term) | self.auxiliary_index.docs_for_term(term)
        return result & self.active_docs

    def _lookup_phrase(self, phrase: str) -> Set[str]:
        """Return active documents containing an exact phrase in either index."""
        phrase_terms = tokenize(phrase)
        result = self.main_index.phrase_query(phrase_terms) | self.auxiliary_index.phrase_query(
            phrase_terms
        )
        return result & self.active_docs


    def save(self, path: str | Path) -> None:
        """Save the entire searchable state to disk as JSON.

        This satisfies the guideline that the program should be able to load an
        existing index without re-indexing the collection at startup.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": self.SERIALIZATION_VERSION,
            "documents": [document.to_dict() for document in self.documents.values()],
            "active_docs": sorted(self.active_docs),
            "deleted_docs": sorted(self.deleted_docs),
            "main_index": self.main_index.to_dict(),
            "auxiliary_index": self.auxiliary_index.to_dict(),
        }

        path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "BooleanIRSystem":
        """Load a system previously saved with :meth:`save`."""
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))

        version = int(data.get("version", -1))
        if version != cls.SERIALIZATION_VERSION:
            raise ValueError(f"Unsupported index version: {version}")

        system = cls()
        documents = [Document.from_dict(doc) for doc in data.get("documents", [])]
        system.documents = {document.doc_id: document for document in documents}
        system.active_docs = {str(doc_id) for doc_id in data.get("active_docs", [])}
        system.deleted_docs = {str(doc_id) for doc_id in data.get("deleted_docs", [])}
        system.main_index = PositionalInvertedIndex.from_dict(data.get("main_index", {}))
        system.auxiliary_index = PositionalInvertedIndex.from_dict(
            data.get("auxiliary_index", {})
        )
        return system

    def documents_by_split(self, split: str) -> List[Document]:
        """Return known documents belonging to a split label."""
        return [document for document in self.documents.values() if document.split == split]

    def stats(self) -> dict:
        """Return useful system statistics."""
        return {
            "known_documents": len(self.documents),
            "active_documents": len(self.active_docs),
            "deleted_documents": len(self.deleted_docs),
            "main_index": self.main_index.stats(),
            "auxiliary_index": self.auxiliary_index.stats(),
        }

    def describe_results(self, query: str, limit: Optional[int] = None) -> str:
        """Return a human-readable result string for one query."""
        try:
            results = self.search(query)
        except QuerySyntaxError as exc:
            return f"Query error: {exc}"

        if limit is not None:
            results = results[:limit]

        if not results:
            return "No matching active documents."

        lines = []
        for document in results:
            lines.append(f"{document.doc_id} [{document.split}] - {document.title}")
        return "\n".join(lines)
