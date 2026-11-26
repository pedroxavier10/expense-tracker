"""Unit tests for `csv_service.parse_csv` (pure parsing, no DB)."""

from datetime import date
from decimal import Decimal

import pytest

from app.services import csv_service
from app.services.csv_service import CsvFormatError, parse_csv

DEFAULT_MONTH = date(2026, 3, 1)


def _parse(text: str, encoding: str = "utf-8") -> csv_service.ParsedCsv:
    return parse_csv(text.encode(encoding), DEFAULT_MONTH)


def test_semicolon_and_decimal_comma() -> None:
    parsed = _parse("date;description;amount;category\n2026-01-15;Café;1,20;Food\n")
    assert parsed.errors == []
    [row] = parsed.rows
    assert row.expense_date == date(2026, 1, 15)
    assert row.amount == Decimal("1.20")
    assert row.description == "Café"
    assert row.category == "Food"
    assert row.line == 2


def test_comma_delimiter_and_decimal_point() -> None:
    parsed = _parse('date,description,amount,category\n2026-01-15,"Lunch, team",12.5,Food\n')
    [row] = parsed.rows
    assert row.amount == Decimal("12.50")
    assert row.description == "Lunch, team"


def test_tab_delimiter() -> None:
    parsed = _parse("date\tdescription\tamount\n2026-01-15\tX\t3\n")
    assert parsed.rows[0].amount == Decimal("3.00")


def test_portuguese_headers_any_order_and_accents() -> None:
    parsed = _parse("Valor;Categoria;Descrição;Data\n10,00;Saúde;Farmácia;05/02/2026\n")
    [row] = parsed.rows
    assert (row.amount, row.category, row.description) == (Decimal("10.00"), "Saúde", "Farmácia")
    assert row.expense_date == date(2026, 2, 5)


def test_windows_1252_encoding() -> None:
    parsed = _parse("data;despesa;valor\n2026-01-01;prestação da casa;490,42\n", "cp1252")
    assert parsed.rows[0].description == "prestação da casa"


def test_utf8_bom() -> None:
    raw = "﻿date;amount\n2026-01-01;5\n".encode()
    parsed = parse_csv(raw, DEFAULT_MONTH)
    assert parsed.rows[0].amount == Decimal("5.00")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-01-15", date(2026, 1, 15)),
        ("15/01/2026", date(2026, 1, 15)),
        ("15-01-2026", date(2026, 1, 15)),
        ("2026-01-15 00:00:00", date(2026, 1, 15)),
        ("2026-02", date(2026, 2, 1)),
        ("02/2026", date(2026, 2, 1)),
        ("", DEFAULT_MONTH),
    ],
)
def test_date_formats(value: str, expected: date) -> None:
    parsed = _parse(f"date;amount\n{value};1\n")
    assert parsed.errors == []
    assert parsed.rows[0].expense_date == expected


def test_missing_date_column_uses_default_month() -> None:
    parsed = _parse("description;amount\nX;1\n")
    assert parsed.rows[0].expense_date == date(2026, 3, 1)


@pytest.mark.parametrize(
    ("value", "code"),
    [
        ("-71,00", "non_positive_amount"),
        ("0", "non_positive_amount"),
        ("1,234", "too_many_decimals"),
        ("abc", "invalid_amount"),
        ("", "missing_amount"),
        ("10000000000", "amount_too_large"),
    ],
)
def test_invalid_amounts(value: str, code: str) -> None:
    parsed = _parse(f"date;amount\n2026-01-01;{value}\n")
    assert parsed.rows == []
    [error] = parsed.errors
    assert (error.line, error.code, error.value) == (2, code, value)


@pytest.mark.parametrize("value", ["1.234,56 €", "1,234.56", "€1234.56"])
def test_amount_with_thousands_and_currency(value: str) -> None:
    parsed = _parse(f'date;amount\n2026-01-01;"{value}"\n')
    assert parsed.rows[0].amount == Decimal("1234.56")


@pytest.mark.parametrize("value", ["2026-02-30", "13/2026", "ontem"])
def test_invalid_dates(value: str) -> None:
    parsed = _parse(f"date;amount\n{value};1\n")
    assert parsed.errors[0].code == "invalid_date"


def test_invalid_rows_do_not_block_valid_ones_and_blank_rows_ignored() -> None:
    parsed = _parse("date;amount\n2026-01-01;1\n;;\n\n2026-01-02;-1\n2026-01-03;2\n")
    assert parsed.total_rows == 3
    assert [r.amount for r in parsed.rows] == [Decimal("1.00"), Decimal("2.00")]
    assert [(e.line, e.code) for e in parsed.errors] == [(5, "non_positive_amount")]


def test_formula_guard_is_stripped() -> None:
    parsed = _parse("description;amount\n'=SUM(A1);1\n")
    assert parsed.rows[0].description == "=SUM(A1)"


def test_description_too_long() -> None:
    parsed = _parse(f"description;amount\n{'x' * 501};1\n")
    assert parsed.errors[0].code == "description_too_long"


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("", "csv_empty"),
        ("   \n\n", "csv_empty"),
        ("date;description\n2026-01-01;X\n", "csv_missing_amount_column"),
    ],
)
def test_file_level_errors(text: str, code: str) -> None:
    with pytest.raises(CsvFormatError) as exc:
        _parse(text)
    assert exc.value.code == code


def test_too_many_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(csv_service, "MAX_ROWS", 2)
    with pytest.raises(CsvFormatError) as exc:
        _parse("amount\n1\n2\n3\n")
    assert exc.value.code == "csv_too_many_rows"


def test_template_round_trips() -> None:
    parsed = parse_csv(csv_service.template_csv("pt").encode(), DEFAULT_MONTH)
    assert parsed.errors == []
    assert [r.expense_date for r in parsed.rows] == [
        date(2026, 1, 15),
        date(2026, 2, 1),
        DEFAULT_MONTH,
    ]
