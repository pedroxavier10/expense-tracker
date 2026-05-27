"""Tests for chat_service helpers (system prompt assembly)."""

from app.models.category import Category
from app.services.chat_service import _build_system_prompt


def _sample_categories() -> list[Category]:
    return [
        Category(slug="food", name="Food", icon="🍔"),
        Category(slug="transport", name="Transport", icon="🚌"),
    ]


def test_build_system_prompt_pt_uses_portuguese_instruction() -> None:
    prompt = _build_system_prompt(_sample_categories(), language="pt")
    assert "European Portuguese" in prompt
    assert "12,50" in prompt
    assert "English" not in prompt


def test_build_system_prompt_en_uses_english_instruction() -> None:
    prompt = _build_system_prompt(_sample_categories(), language="en")
    assert "English" in prompt
    assert "€12.50" in prompt
    assert "European Portuguese" not in prompt


def test_build_system_prompt_unknown_language_falls_back_to_english() -> None:
    prompt = _build_system_prompt(_sample_categories(), language="xx")
    assert "English" in prompt


def test_build_system_prompt_lists_categories() -> None:
    prompt = _build_system_prompt(_sample_categories(), language="en")
    assert "food" in prompt
    assert "transport" in prompt
