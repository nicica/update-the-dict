"""Boolean query tokenizer, parser, and evaluator.

Supported syntax
----------------
- terms: information
- phrases: "information retrieval"
- Boolean operators: AND, OR, NOT
- parentheses: (information OR retrieval) AND NOT web

Operator precedence follows the usual Boolean IR convention:

    NOT > AND > OR

The parser produces a small abstract syntax tree (AST). Each AST node evaluates
to a set of document ids by calling lookup functions supplied by the IR system.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence, Set

from .tokenizer import tokenize


class QuerySyntaxError(ValueError):
    """Raised when a user query cannot be parsed."""


@dataclass(frozen=True)
class QueryToken:
    """Token produced from the raw query string."""

    kind: str
    value: str



class QueryNode:
    """Base class for all query AST nodes."""

    def evaluate(self, context: "EvaluationContext") -> Set[str]:
        raise NotImplementedError


@dataclass(frozen=True)
class TermNode(QueryNode):
    """Single-term query node."""

    term: str

    def evaluate(self, context: "EvaluationContext") -> Set[str]:
        return context.lookup_term(self.term)


@dataclass(frozen=True)
class PhraseNode(QueryNode):
    """Exact phrase query node."""

    phrase: str

    def evaluate(self, context: "EvaluationContext") -> Set[str]:
        return context.lookup_phrase(self.phrase)


@dataclass(frozen=True)
class NotNode(QueryNode):
    """Boolean NOT query node."""

    child: QueryNode

    def evaluate(self, context: "EvaluationContext") -> Set[str]:
        return context.all_docs() - self.child.evaluate(context)


@dataclass(frozen=True)
class BinaryNode(QueryNode):
    """Boolean AND/OR query node."""

    operator: str
    left: QueryNode
    right: QueryNode

    def evaluate(self, context: "EvaluationContext") -> Set[str]:
        left_result = self.left.evaluate(context)
        right_result = self.right.evaluate(context)

        if self.operator == "AND":
            return left_result & right_result
        if self.operator == "OR":
            return left_result | right_result

        raise QuerySyntaxError(f"Unknown operator: {self.operator}")


@dataclass(frozen=True)
class EvaluationContext:
    """Functions needed by query nodes during evaluation."""

    lookup_term: Callable[[str], Set[str]]
    lookup_phrase: Callable[[str], Set[str]]
    all_docs: Callable[[], Set[str]]



def lex_query(query: str) -> List[QueryToken]:
    """Convert a query string into Boolean query tokens.

    This lexer recognizes quoted phrases and parentheses before applying simple
    whitespace splitting. Boolean operators are case-insensitive.
    """
    tokens: List[QueryToken] = []
    i = 0

    while i < len(query):
        char = query[i]

        if char.isspace():
            i += 1
            continue

        if char == '"':
            end = query.find('"', i + 1)
            if end == -1:
                raise QuerySyntaxError("Unclosed phrase quote in query")
            phrase = query[i + 1 : end].strip()
            if not phrase:
                raise QuerySyntaxError("Empty phrase query is not allowed")
            tokens.append(QueryToken("PHRASE", phrase))
            i = end + 1
            continue

        if char == "(":
            tokens.append(QueryToken("LPAREN", char))
            i += 1
            continue

        if char == ")":
            tokens.append(QueryToken("RPAREN", char))
            i += 1
            continue

       
        j = i
        while j < len(query) and not query[j].isspace() and query[j] not in "()\"":
            j += 1
        raw = query[i:j]
        upper = raw.upper()

        if upper in {"AND", "OR", "NOT"}:
            tokens.append(QueryToken(upper, upper))
        else:
            normalized_terms = tokenize(raw)
            if not normalized_terms:
                raise QuerySyntaxError(f"Invalid query token: {raw!r}")
            if len(normalized_terms) > 1:
                
                raise QuerySyntaxError(
                    f"Token {raw!r} becomes multiple terms; use quotes for phrases"
                )
            tokens.append(QueryToken("TERM", normalized_terms[0]))

        i = j

    if not tokens:
        raise QuerySyntaxError("Empty query")

    return tokens



class QueryParser:
    """Parse Boolean queries using recursive descent.

    Grammar:

        expr      := or_expr
        or_expr   := and_expr (OR and_expr)*
        and_expr  := not_expr (AND not_expr)*
        not_expr  := NOT not_expr | atom
        atom      := TERM | PHRASE | '(' expr ')'
    """

    def __init__(self, tokens: Sequence[QueryToken]) -> None:
        self.tokens = list(tokens)
        self.position = 0

    def parse(self) -> QueryNode:
        """Parse the full token sequence and return the AST root."""
        node = self._parse_or()
        if self._peek() is not None:
            token = self._peek()
            raise QuerySyntaxError(f"Unexpected token at end of query: {token.value!r}")
        return node

    def _peek(self) -> Optional[QueryToken]:
        if self.position >= len(self.tokens):
            return None
        return self.tokens[self.position]

    def _accept(self, kind: str) -> Optional[QueryToken]:
        token = self._peek()
        if token is not None and token.kind == kind:
            self.position += 1
            return token
        return None

    def _expect(self, kind: str) -> QueryToken:
        token = self._accept(kind)
        if token is None:
            found = self._peek().value if self._peek() is not None else "end of query"
            raise QuerySyntaxError(f"Expected {kind}, found {found!r}")
        return token

    def _parse_or(self) -> QueryNode:
        node = self._parse_and()
        while self._accept("OR") is not None:
            right = self._parse_and()
            node = BinaryNode("OR", node, right)
        return node

    def _parse_and(self) -> QueryNode:
        node = self._parse_not()
        while self._accept("AND") is not None:
            right = self._parse_not()
            node = BinaryNode("AND", node, right)
        return node

    def _parse_not(self) -> QueryNode:
        if self._accept("NOT") is not None:
            return NotNode(self._parse_not())
        return self._parse_atom()

    def _parse_atom(self) -> QueryNode:
        term = self._accept("TERM")
        if term is not None:
            return TermNode(term.value)

        phrase = self._accept("PHRASE")
        if phrase is not None:
            return PhraseNode(phrase.value)

        if self._accept("LPAREN") is not None:
            node = self._parse_or()
            self._expect("RPAREN")
            return node

        found = self._peek().value if self._peek() is not None else "end of query"
        raise QuerySyntaxError(f"Expected term, phrase, or '(', found {found!r}")


def parse_query(query: str) -> QueryNode:
    """Convenience function: lex and parse one query string."""
    return QueryParser(lex_query(query)).parse()
