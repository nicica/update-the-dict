"""Positional inverted index implementation.

A standard inverted index stores, for each term, the list of documents in which
that term appears. To support phrase queries, this implementation stores the
positions of each term inside each document as well.

Index structure:

    term -> doc_id -> [positions]

Example:

    "information" -> "A1" -> [0, 15]
    "retrieval"   -> "A1" -> [1, 16]

The phrase "information retrieval" matches document A1 because there exists a
position p for "information" such that "retrieval" appears at p + 1.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Dict, Iterable, List, Mapping, MutableMapping, Set

from .tokenizer import tokenize


@dataclass(frozen=True)
class Document:
    """Simple representation of a document in the collection.

    Attributes
    ----------
    doc_id:
        Stable unique identifier for the document.
    title:
        Human-readable title, used only for displaying results.
    text:
        Full document text that will be indexed.
    split:
        Dataset split label: usually "A", "B", or "C" for this project.
    """

    doc_id: str
    title: str
    text: str
    split: str

    def to_dict(self) -> dict:
        """Serialize the document to a JSON-compatible dictionary."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Mapping[str, str]) -> "Document":
        """Create a Document from a dictionary produced by :meth:`to_dict`."""
        return Document(
            doc_id=str(data["doc_id"]),
            title=str(data.get("title", "")),
            text=str(data["text"]),
            split=str(data.get("split", "")),
        )


class PositionalInvertedIndex:
    """A positional inverted index.

    The index only stores postings and document lengths. It does not know which
    documents are active or deleted. Dynamic update logic is handled by
    ``BooleanIRSystem`` using a main index, an auxiliary index, and a deletion
    set.
    """

    def __init__(self) -> None:
        self.postings: MutableMapping[str, MutableMapping[str, List[int]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self.doc_lengths: Dict[str, int] = {}

    def __len__(self) -> int:
        """Return the number of distinct terms in the index vocabulary."""
        return len(self.postings)

    def add_document(self, document: Document) -> None:
        """Add one document to the positional index.

        If a document with the same id is indexed again, the old postings are
        first removed from this index to avoid duplicate positions.
        """
        if document.doc_id in self.doc_lengths:
            self.remove_document(document.doc_id)

        tokens = tokenize(document.text)
        self.doc_lengths[document.doc_id] = len(tokens)

        for position, term in enumerate(tokens):
            self.postings[term][document.doc_id].append(position)

    def build(self, documents: Iterable[Document]) -> None:
        """Build this index from an iterable of documents.

        Existing postings are cleared first.
        """
        self.clear()
        for document in documents:
            self.add_document(document)

    def clear(self) -> None:
        """Remove all postings from the index."""
        self.postings = defaultdict(lambda: defaultdict(list))
        self.doc_lengths = {}

    def remove_document(self, doc_id: str) -> None:
        """Physically remove one document from this index.

        The dynamic IR system normally uses lazy deletion instead of calling
        this method for every deletion. This method is still useful when
        rebuilding or cleaning an index.
        """
        for term in list(self.postings.keys()):
            self.postings[term].pop(doc_id, None)
            if not self.postings[term]:
                del self.postings[term]
        self.doc_lengths.pop(doc_id, None)

    def docs_for_term(self, term: str) -> Set[str]:
        """Return the set of document ids containing *term*."""
        normalized_terms = tokenize(term)
        if not normalized_terms:
            return set()
        normalized = normalized_terms[0]
        return set(self.postings.get(normalized, {}).keys())

    def positions(self, term: str, doc_id: str) -> List[int]:
        """Return the positions of *term* inside *doc_id*."""
        normalized_terms = tokenize(term)
        if not normalized_terms:
            return []
        normalized = normalized_terms[0]
        return list(self.postings.get(normalized, {}).get(doc_id, []))

    def phrase_query(self, phrase_terms: List[str]) -> Set[str]:
        """Return documents that contain the exact phrase represented by terms.

        Parameters
        ----------
        phrase_terms:
            Already tokenized phrase terms, for example
            ``["information", "retrieval"]``.

        Returns
        -------
        set[str]
            Document ids where the terms occur consecutively in the same order.
        """
        if not phrase_terms:
            return set()
        if len(phrase_terms) == 1:
            return self.docs_for_term(phrase_terms[0])

        candidate_docs = self.docs_for_term(phrase_terms[0])
        for term in phrase_terms[1:]:
            candidate_docs &= self.docs_for_term(term)
            if not candidate_docs:
                return set()

        matching_docs: Set[str] = set()

        for doc_id in candidate_docs:
            possible_starts = set(self.positions(phrase_terms[0], doc_id))

            for offset, term in enumerate(phrase_terms[1:], start=1):
                shifted_positions = {pos - offset for pos in self.positions(term, doc_id)}
                possible_starts &= shifted_positions
                if not possible_starts:
                    break

            if possible_starts:
                matching_docs.add(doc_id)

        return matching_docs

    def vocabulary(self) -> Set[str]:
        """Return the set of indexed terms."""
        return set(self.postings.keys())

    def to_dict(self) -> dict:
        """Serialize the index to a JSON-compatible dictionary."""
        return {
            "postings": {
                term: {doc_id: positions for doc_id, positions in doc_postings.items()}
                for term, doc_postings in self.postings.items()
            },
            "doc_lengths": dict(self.doc_lengths),
        }

    @staticmethod
    def from_dict(data: Mapping[str, object]) -> "PositionalInvertedIndex":
        """Load an index previously created by :meth:`to_dict`."""
        index = PositionalInvertedIndex()
        raw_postings = data.get("postings", {})
        raw_doc_lengths = data.get("doc_lengths", {})

        index.postings = defaultdict(lambda: defaultdict(list))
        for term, doc_postings in raw_postings.items():
            for doc_id, positions in doc_postings.items():
                index.postings[str(term)][str(doc_id)] = [int(pos) for pos in positions]

        index.doc_lengths = {str(doc_id): int(length) for doc_id, length in raw_doc_lengths.items()}
        return index

    def stats(self) -> dict:
        """Return basic statistics useful for the demo and report."""
        posting_entries = sum(len(doc_postings) for doc_postings in self.postings.values())
        total_positions = sum(
            len(positions)
            for doc_postings in self.postings.values()
            for positions in doc_postings.values()
        )
        return {
            "documents_in_index": len(self.doc_lengths),
            "vocabulary_size": len(self.postings),
            "posting_entries": posting_entries,
            "stored_positions": total_positions,
        }
