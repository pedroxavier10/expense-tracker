"""Unit tests for `text_normalization` (pure, no DB)."""

import pytest

from app.services.text_normalization import description_key, fold_text, jaccard, tokens


def test_fold_text_is_case_accent_and_whitespace_insensitive() -> None:
    assert fold_text("  Saúde   e  Beleza ") == "saude e beleza"
    assert fold_text("﻿Café") == "cafe"


def test_tokens_drop_amounts_currency_and_stopwords() -> None:
    assert tokens("Consulta de pés 35€") == ["consulta", "pe"]
    assert tokens("Jantar com amigos 42,50 EUR") == ["jantar", "amigo"]
    assert tokens("Gym 35eur") == ["gym"]


def test_tokens_keep_alphanumeric_words_and_dedupe() -> None:
    assert tokens("Vodafone 5G Vodafone") == ["vodafone", "5g"]


def test_tokens_empty_when_nothing_meaningful() -> None:
    assert tokens("12,30 €") == []
    assert description_key("de 5") == ""


@pytest.mark.parametrize(
    "variant",
    [
        "consulta de pés 35€",
        "Consulta aos pés",
        "CONSULTAS PÉS",
        "pés - consulta",
        "consulta pé 40.00",
    ],
)
def test_description_key_groups_equivalent_descriptions(variant: str) -> None:
    assert description_key(variant) == description_key("Consulta de pés")


def test_description_key_distinguishes_different_expenses() -> None:
    assert description_key("Consulta de pés") != description_key("Consulta dentista")


def test_jaccard() -> None:
    assert jaccard(tokens("consulta de pés"), tokens("consulta pés")) == 1.0
    assert jaccard(["consulta", "pe"], ["consulta", "dentista"]) == pytest.approx(1 / 3)
    assert jaccard([], []) == 0.0
