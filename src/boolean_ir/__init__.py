"""Boolean Information Retrieval project package."""

from .index import Document, PositionalInvertedIndex
from .query_parser import QuerySyntaxError, parse_query
from .system import BooleanIRSystem

__all__ = [
    "BooleanIRSystem",
    "Document",
    "PositionalInvertedIndex",
    "QuerySyntaxError",
    "parse_query",
]
