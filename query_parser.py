# -*- coding: utf-8 -*-
"""
Robust, safe Boolean Query Parser for Academic Search.
Supports: AND, OR, NOT, parentheses nesting (...), and quoted phrases "...".
No use of eval(). Uses recursive-descent token parsing into an AST.
"""

import re
from typing import List, Optional

def normalize_boolean_query(query: str) -> str:
    """
    Normalizes standalone lowercase or mixed-case boolean operators (and, or, not)
    to standard uppercase (AND, OR, NOT), while strictly preserving everything inside quotes.
    Example: 'cancer or "rock and roll" and tumor' -> 'cancer OR "rock and roll" AND tumor'
    """
    if not query or not query.strip():
        return query or ""
    parts = re.split(r'("[^"]*")', query)
    for i in range(0, len(parts), 2):
        parts[i] = re.sub(r'\b(and|or|not)\b', lambda m: m.group(1).upper(), parts[i], flags=re.IGNORECASE)
    return ''.join(parts)

class ASTNode:
    def evaluate(self, target_text: str) -> bool:
        raise NotImplementedError

    def matches(self, target_text: str) -> bool:
        return self.evaluate(target_text)

class TermNode(ASTNode):
    def __init__(self, term: str):
        self.term = term.lower().strip()

    def evaluate(self, target_text: str) -> bool:
        t_low = target_text.lower()
        if not self.term:
            return True
        if self.term in t_low:
            return True
        # Flexible prefix match for longer terms (>= 7 chars)
        if len(self.term) >= 7 and self.term[:6] in t_low:
            return True
        return False

    def __repr__(self):
        return f"Term({self.term!r})"

class PhraseNode(ASTNode):
    def __init__(self, phrase: str):
        self.phrase = phrase.lower().strip()

    def evaluate(self, target_text: str) -> bool:
        t_low = target_text.lower()
        return self.phrase in t_low

    def __repr__(self):
        return f"Phrase({self.phrase!r})"

class AndNode(ASTNode):
    def __init__(self, left: ASTNode, right: ASTNode):
        self.left = left
        self.right = right

    def evaluate(self, target_text: str) -> bool:
        return self.left.evaluate(target_text) and self.right.evaluate(target_text)

    def __repr__(self):
        return f"({self.left!r} AND {self.right!r})"

class OrNode(ASTNode):
    def __init__(self, left: ASTNode, right: ASTNode):
        self.left = left
        self.right = right

    def evaluate(self, target_text: str) -> bool:
        return self.left.evaluate(target_text) or self.right.evaluate(target_text)

    def __repr__(self):
        return f"({self.left!r} OR {self.right!r})"

class NotNode(ASTNode):
    def __init__(self, child: ASTNode):
        self.child = child

    def evaluate(self, target_text: str) -> bool:
        return not self.child.evaluate(target_text)

    def __repr__(self):
        return f"(NOT {self.child!r})"


# Tokenizer: Strict uppercase for operators to prevent natural language conjunctions from breaking search
TOKEN_RE = re.compile(
    r'\s*(?:'
    r'(?P<LPAREN>\()'
    r'|(?P<RPAREN>\))'
    r'|(?P<AND>\bAND\b)'
    r'|(?P<OR>\bOR\b)'
    r'|(?P<NOT>\bNOT\b)'
    r'|"(?P<PHRASE>[^"]+)"'
    r'|(?P<TERM>[^\s()"]+)'
    r')'
)

class BooleanQueryParser:
    def __init__(self, query: str):
        self.raw_query = normalize_boolean_query(query)
        self.tokens = self._tokenize(self.raw_query)
        self.pos = 0

    def _tokenize(self, query: str) -> List[tuple]:
        tokens = []
        for match in TOKEN_RE.finditer(query):
            kind = match.lastgroup
            val = match.group(kind)
            if kind == "AND":
                tokens.append(("AND", "AND"))
            elif kind == "OR":
                tokens.append(("OR", "OR"))
            elif kind == "NOT":
                tokens.append(("NOT", "NOT"))
            elif kind == "LPAREN":
                tokens.append(("LPAREN", "("))
            elif kind == "RPAREN":
                tokens.append(("RPAREN", ")"))
            elif kind == "PHRASE":
                tokens.append(("PHRASE", val))
            elif kind == "TERM":
                tokens.append(("TERM", val))
        return tokens

    def parse(self) -> Optional[ASTNode]:
        if not self.tokens:
            return None
        self.pos = 0
        try:
            node = self._parse_or()
            return node
        except Exception:
            return None

    def _current_token(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def _consume(self, expected_kind=None):
        tok = self._current_token()
        if tok and (expected_kind is None or tok[0] == expected_kind):
            self.pos += 1
            return tok
        return None

    def _parse_or(self) -> Optional[ASTNode]:
        node = self._parse_and()
        while True:
            tok = self._current_token()
            if tok and tok[0] == "OR":
                self._consume("OR")
                right = self._parse_and()
                if right:
                    node = OrNode(node, right) if node else right
            else:
                break
        return node

    def _parse_and(self) -> Optional[ASTNode]:
        node = self._parse_not()
        while True:
            tok = self._current_token()
            if tok and tok[0] == "AND":
                self._consume("AND")
                right = self._parse_not()
                if right:
                    node = AndNode(node, right) if node else right
            elif tok and tok[0] not in ("OR", "RPAREN"):
                # Implicit AND between terms
                right = self._parse_not()
                if right:
                    node = AndNode(node, right) if node else right
                else:
                    break
            else:
                break
        return node

    def _parse_not(self) -> Optional[ASTNode]:
        tok = self._current_token()
        if tok and tok[0] == "NOT":
            self._consume("NOT")
            child = self._parse_primary()
            return NotNode(child) if child else None
        return self._parse_primary()

    def _parse_primary(self) -> Optional[ASTNode]:
        tok = self._current_token()
        if not tok:
            return None
        kind, val = tok

        if kind == "LPAREN":
            self._consume("LPAREN")
            node = self._parse_or()
            self._consume("RPAREN")
            return node
        elif kind == "PHRASE":
            self._consume("PHRASE")
            return PhraseNode(val)
        elif kind == "TERM":
            self._consume("TERM")
            return TermNode(val)
        else:
            self._consume()
            return None


def is_explicit_boolean_query(query: str) -> bool:
    """Checks if user explicitly included uppercase Boolean operators (AND, OR, NOT) or grouping."""
    if not query or not query.strip():
        return False
    return bool(re.search(r'\b(AND|OR|NOT)\b|[()"]', query))

def matches_boolean_query(query: str, target_text: str) -> bool:
    """
    Parses and evaluates a query against target_text using Boolean logic.
    Returns True if target_text satisfies the boolean expression.
    """
    if not query or not query.strip():
        return True
    if not target_text:
        return False

    norm_query = normalize_boolean_query(query)
    parser = BooleanQueryParser(norm_query)
    ast = parser.parse()
    if ast is None:
        # Fallback to simple containment if syntax malformed
        clean_terms = [t for t in query.lower().split() if len(t) >= 2]
        return any(t in target_text.lower() for t in clean_terms) if clean_terms else True

    return ast.evaluate(target_text)


def parse_query(query: str) -> Optional[ASTNode]:
    """Parses a search query into an ASTNode."""
    if not query or not query.strip():
        return None
    return BooleanQueryParser(query).parse()
