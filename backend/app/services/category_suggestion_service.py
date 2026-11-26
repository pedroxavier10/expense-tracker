"""Category learning: remember user corrections and suggest categories.

Two sources, in priority order:
1. **Learned hints** (`CategoryHint`) — written when the user changes the
   category of an existing expense. One correction is enough to win.
2. **History** — categories of the user's own past expenses whose
   descriptions are similar (token Jaccard), weighted by recency.

Matching is lexical (see `text_normalization`), runs in Python and works on
both PostgreSQL and SQLite. All functions are scoped by `user_id`.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Literal
from uuid import UUID

from sqlmodel import Session, col, select

from app.models.category import Category
from app.models.category_hint import CategoryHint
from app.models.expense import Expense
from app.services.text_normalization import description_key, jaccard, tokens

# History matching tuning. Personal-scale data: scanning the most recent
# expenses in Python is cheap and keeps the query portable.
HISTORY_SCAN_LIMIT = 1000
HISTORY_MIN_SIMILARITY = 0.5
HISTORY_HALF_LIFE_DAYS = 180
MIN_CONFIDENCE = 0.5
# A hint whose tokens are all contained in a longer description still applies
# ("consulta pe" inside "consulta pe clinica x"), with slightly lower confidence.
CONTAINED_HINT_CONFIDENCE = 0.9
# Learned hints shown to the chat model.
PROMPT_HINTS_LIMIT = 30


@dataclass(frozen=True)
class CategorySuggestion:
    category: Category
    confidence: float
    source: Literal["learned", "history"]


# ---------------------------------------------------------------------------
# Learning
# ---------------------------------------------------------------------------


def record_correction(
    session: Session, user_id: UUID, description: str, category_id: UUID
) -> CategoryHint | None:
    """Upsert the hint "this description -> this category".

    Does NOT commit: called from inside other services' transactions (e.g.
    `expense_service.update_expense`), which commit once. Returns None when
    the description has no meaningful tokens (e.g. only an amount).
    """
    key = description_key(description)
    if not key:
        return None

    hint = session.exec(
        select(CategoryHint).where(
            CategoryHint.user_id == user_id, CategoryHint.description_key == key
        )
    ).first()
    now = datetime.now(UTC)
    if hint is None:
        hint = CategoryHint(
            user_id=user_id,
            category_id=category_id,
            description_key=key,
            description=description,
            last_used_at=now,
            created_at=now,
        )
    else:
        # Same category again strengthens it; a different one replaces it
        # (the most recent correction is what the user means now).
        hint.hit_count = hint.hit_count + 1 if hint.category_id == category_id else 1
        hint.category_id = category_id
        hint.description = description
        hint.last_used_at = now
    session.add(hint)
    return hint


# ---------------------------------------------------------------------------
# Suggesting
# ---------------------------------------------------------------------------


def _active_hints(session: Session, user_id: UUID) -> list[tuple[CategoryHint, Category]]:
    rows = session.exec(
        select(CategoryHint, Category)
        .join(Category, col(Category.id) == CategoryHint.category_id)
        .where(CategoryHint.user_id == user_id, Category.is_active == True)  # noqa: E712
        .order_by(col(CategoryHint.last_used_at).desc())
    ).all()
    return list(rows)


class CategorySuggester:
    """Loads the user's hints and recent history once, then answers many
    `suggest()` calls without further queries (used per row by CSV import)."""

    def __init__(self, session: Session, user_id: UUID, today: date | None = None) -> None:
        self._today = today or datetime.now(UTC).date()
        self._hints = [
            (hint.description_key, set(hint.description_key.split()), category)
            for hint, category in _active_hints(session, user_id)
        ]
        rows = session.exec(
            select(col(Expense.description), col(Expense.expense_date), Category)
            .join(Category, col(Category.id) == Expense.category_id)
            .where(Expense.user_id == user_id, Category.is_active == True)  # noqa: E712
            .order_by(col(Expense.expense_date).desc(), col(Expense.created_at).desc())
            .limit(HISTORY_SCAN_LIMIT)
        ).all()
        self._history = [
            (set(tokens(description)), expense_date, category)
            for description, expense_date, category in rows
        ]

    def suggest(self, description: str) -> CategorySuggestion | None:
        """Best category for a description, or None when there is no confident match."""
        desc_tokens = tokens(description)
        if not desc_tokens:
            return None
        return self._from_hints(desc_tokens) or self._from_history(desc_tokens)

    def _from_hints(self, desc_tokens: list[str]) -> CategorySuggestion | None:
        key = " ".join(sorted(desc_tokens))
        token_set = set(desc_tokens)
        best: tuple[int, Category] | None = None
        for hint_key, hint_tokens, category in self._hints:
            if hint_key == key:
                return CategorySuggestion(category=category, confidence=1.0, source="learned")
            # Most specific contained hint wins; ties keep the most recent (hints
            # are ordered by last_used_at desc).
            if hint_tokens <= token_set and (best is None or len(hint_tokens) > best[0]):
                best = (len(hint_tokens), category)
        if best is not None:
            return CategorySuggestion(
                category=best[1], confidence=CONTAINED_HINT_CONFIDENCE, source="learned"
            )
        return None

    def _from_history(self, desc_tokens: list[str]) -> CategorySuggestion | None:
        weights: dict[UUID, float] = {}
        categories: dict[UUID, Category] = {}
        for expense_tokens, expense_date, category in self._history:
            similarity = jaccard(desc_tokens, expense_tokens)
            if similarity < HISTORY_MIN_SIMILARITY:
                continue
            age_days = max((self._today - expense_date).days, 0)
            recency = 0.5 ** (age_days / HISTORY_HALF_LIFE_DAYS)
            weights[category.id] = weights.get(category.id, 0.0) + similarity * recency
            categories[category.id] = category

        if not weights:
            return None
        best_id = max(weights, key=lambda cid: weights[cid])
        confidence = weights[best_id] / sum(weights.values())
        if confidence < MIN_CONFIDENCE:
            return None
        return CategorySuggestion(
            category=categories[best_id], confidence=round(confidence, 2), source="history"
        )


def suggest_category(
    session: Session, user_id: UUID, description: str, today: date | None = None
) -> CategorySuggestion | None:
    """Best category for a single description, or None when there is no confident match."""
    if not tokens(description):
        return None
    return CategorySuggester(session, user_id, today).suggest(description)


def hints_for_prompt(
    session: Session, user_id: UUID, message: str, limit: int = PROMPT_HINTS_LIMIT
) -> list[tuple[CategoryHint, Category]]:
    """Learned hints to inject into the chat system prompt.

    Hints sharing tokens with the user's latest message come first (most
    overlap first), then the most recently used ones, up to `limit`. This is
    the retrieval step that keeps the prompt small when there are many hints.
    """
    message_tokens = set(tokens(message))
    hints = _active_hints(session, user_id)  # already most-recent first
    ranked = sorted(
        enumerate(hints),
        key=lambda item: (
            -len(set(item[1][0].description_key.split()) & message_tokens),
            item[0],
        ),
    )
    return [pair for _, pair in ranked[:limit]]
