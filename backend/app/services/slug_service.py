"""Category slug generation.

The slug is a short, English, machine-friendly identifier used by the LLM
prompt and by filters. It is generated when a category is created and
regenerated when its name changes, so it stays aligned with the (possibly
localized) display name while remaining English for the English LLM prompt.

Strategy:
1. Ask the LLM for an English slug, telling it which slugs the user already
   has so it avoids them up front.
2. Sanitize and validate the result.
3. Fall back to a local accent-stripping slugify if the LLM is unavailable or
   returns nothing usable (e.g. offline / tests).
4. Guarantee per-user uniqueness by suffixing -2, -3, ... — this always runs,
   so the DB unique constraint never surfaces as an error to the user.
"""

import logging
import re
import unicodedata
from uuid import UUID

from sqlmodel import Session, select

from app.core.config import get_settings
from app.llm.client import get_llm_client
from app.models.category import Category

logger = logging.getLogger(__name__)

_MAX_SLUG_LEN = 50
_SLUG_RE = re.compile(r"^[a-z0-9_-]+$")


def _slugify(value: str) -> str:
    """Local fallback: transliterate accents and reduce to a-z0-9 + hyphens."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_only.lower()).strip("-")
    return slug[:_MAX_SLUG_LEN]


def _sanitize(raw: str) -> str:
    """Coerce an LLM response into a valid slug, or '' if nothing usable."""
    candidate = raw.strip().splitlines()[0].strip() if raw.strip() else ""
    candidate = re.sub(r"[^a-z0-9]+", "-", candidate.lower()).strip("-")
    candidate = candidate[:_MAX_SLUG_LEN]
    return candidate if candidate and _SLUG_RE.match(candidate) else ""


def _existing_slugs(session: Session, user_id: UUID, exclude_category_id: UUID | None) -> set[str]:
    stmt = select(Category.slug).where(Category.user_id == user_id)
    if exclude_category_id is not None:
        stmt = stmt.where(Category.id != exclude_category_id)
    return set(session.exec(stmt).all())


async def _llm_suggest_slug(name: str, existing: set[str]) -> str:
    """Ask the LLM for an English slug; return '' on any failure."""
    settings = get_settings()
    model = settings.llm_utility_model or settings.llm_model
    avoid = ", ".join(sorted(existing)) or "(none)"
    try:
        client = get_llm_client()
        response = await client.chat.completions.create(
            model=model,
            temperature=0,
            stream=False,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You generate a short English slug for an expense category. "
                        "Output ONLY the slug: lowercase, a-z 0-9 and hyphens, no "
                        "spaces, max 30 chars. ALWAYS translate to English first, "
                        "then slugify. Never output accented or non-ASCII characters."
                    ),
                },
                {
                    "role": "user",
                    "content": "Category name: Alimentação\nMust be different from: (none)",
                },
                {"role": "assistant", "content": "food"},
                {
                    "role": "user",
                    "content": "Category name: Saúde\nMust be different from: (none)",
                },
                {"role": "assistant", "content": "health"},
                {
                    "role": "user",
                    "content": "Category name: Transporte\nMust be different from: (none)",
                },
                {"role": "assistant", "content": "transport"},
                {
                    "role": "user",
                    "content": "Category name: Lazer\nMust be different from: (none)",
                },
                {"role": "assistant", "content": "leisure"},
                {
                    "role": "user",
                    "content": (
                        f"Category name: {name}\n"
                        f"Must be different from these existing slugs: {avoid}"
                    ),
                },
            ],
        )
        raw = response.choices[0].message.content or ""
        slug = _sanitize(raw)
        logger.debug("LLM slug suggestion for %r: raw=%r sanitized=%r", name, raw, slug)
        return slug
    except Exception:  # noqa: BLE001 - network/LLM errors fall back to local slugify
        logger.exception("LLM slug generation failed for %r; using local fallback", name)
        return ""


async def generate_category_slug(
    session: Session,
    user_id: UUID,
    name: str,
    exclude_category_id: UUID | None = None,
) -> str:
    """Return a unique English slug for `name` within the user's categories."""
    existing = _existing_slugs(session, user_id, exclude_category_id)

    base = await _llm_suggest_slug(name, existing)
    if not base:
        base = _slugify(name)
    if not base:
        base = "category"

    if base not in existing:
        return base

    # Guarantee uniqueness (covers LLM collisions and fallback collisions).
    suffix = 2
    while True:
        candidate = f"{base[: _MAX_SLUG_LEN - len(str(suffix)) - 1]}-{suffix}"
        if candidate not in existing:
            return candidate
        suffix += 1
