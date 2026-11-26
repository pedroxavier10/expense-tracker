"""Text normalization for matching expense descriptions.

Shared by features that compare free-text descriptions written by the user
(category learning, recurring-expense detection, CSV import lookups). Pure
functions, no DB, so they behave identically on PostgreSQL and SQLite.

Pipeline for descriptions:
1. ``fold_text``: case- and accent-insensitive, whitespace collapsed.
2. ``tokens``: split on non-alphanumerics, drop amounts/currency, PT/EN
   stopwords and naive plural ``s`` so "Consulta de pés 35€" and
   "consultas aos pés" yield the same tokens.
3. ``description_key``: sorted unique tokens joined by spaces — an
   order-insensitive key suitable for exact lookups and grouping.
"""

import re
import unicodedata

_BOM = "﻿"

# Pure numbers, decimals and numbers glued to a currency marker ("35eur", "12e").
_AMOUNT_TOKEN = re.compile(r"^\d+(?:eur|euro|euros|e|usd)?$")
_SPLIT = re.compile(r"[^a-z0-9]+")

# Kept small on purpose: only function words that never distinguish expenses.
_STOPWORDS = frozenset(
    {
        # Portuguese
        "a", "o", "as", "os", "ao", "aos", "um", "uma", "uns", "umas",
        "de", "da", "do", "das", "dos", "d",
        "em", "no", "na", "nos", "nas", "num", "numa",
        "para", "pra", "pro", "por", "pelo", "pela", "pelos", "pelas",
        "com", "e", "ou", "que",
        # English
        "the", "an", "of", "for", "and", "or", "at", "in", "on", "to", "with",
        # Currency words (amounts are dropped, so are their units)
        "eur", "euro", "euros", "usd",
    }
)  # fmt: skip


def fold_text(value: str) -> str:
    """Case- and accent-insensitive comparison key with collapsed whitespace."""
    normalized = unicodedata.normalize("NFKD", value.replace(_BOM, ""))
    ascii_only = "".join(c for c in normalized if not unicodedata.combining(c))
    return " ".join(ascii_only.casefold().split())


def _singular(token: str) -> str:
    # Naive plural stripping; applied symmetrically, so consistency matters
    # more than linguistic accuracy ("pes" -> "pe", "consultas" -> "consulta").
    if len(token) >= 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokens(description: str) -> list[str]:
    """Meaningful tokens of a description, in original order, without duplicates."""
    result: list[str] = []
    for raw in _SPLIT.split(fold_text(description)):
        if not raw or raw in _STOPWORDS or _AMOUNT_TOKEN.match(raw):
            continue
        token = _singular(raw)
        if token not in result:
            result.append(token)
    return result


def description_key(description: str) -> str:
    """Order-insensitive key for exact matching/grouping. Empty if nothing meaningful."""
    return " ".join(sorted(tokens(description)))


def jaccard(a: set[str] | list[str], b: set[str] | list[str]) -> float:
    """Jaccard similarity of two token collections (0.0 when both are empty)."""
    set_a, set_b = set(a), set(b)
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)
