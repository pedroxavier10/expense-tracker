"""CSV import/export of expenses.

One file format is used for import, export and the downloadable template:

    date;description;amount;category

- Reading is lenient: UTF-8 (with or without BOM) falling back to Windows-1252,
  `;` / `,` / tab delimiter auto-detected, English or Portuguese headers, decimal
  comma or point, full dates or month-only dates (day 1).
- Writing targets Excel in a Portuguese locale: UTF-8 with BOM, `;` delimiter,
  decimal comma, ISO dates.

Import is split in two steps that share `_plan_import`: `build_preview` (read
only) and `run_import` (single commit, so an import is all-or-nothing).
"""

import codecs
import csv
import io
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlmodel import Session, col, select

from app.models.category import Category
from app.models.expense import Expense
from app.models.user import User
from app.schemas.category import CategoryRead
from app.schemas.import_export import (
    DuplicateMode,
    ImportPreview,
    ImportResult,
    ImportRowError,
    RowErrorCode,
)
from app.services import slug_service
from app.services.text_normalization import fold_text

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_ROWS = 5000
DUPLICATE_CONFIRM_THRESHOLD = 10

CSV_HEADER = ["date", "description", "amount", "category"]
OTHER_SLUG = "other"
_OTHER_NAMES = {"pt": "Outros", "en": "Other"}
_OTHER_KEYS = ("other", "outros")

_MAX_DESCRIPTION_LEN = 500
_MAX_CATEGORY_LEN = 100
_MAX_AMOUNT = Decimal("10000000000")  # Numeric(12, 2) upper bound (exclusive)
_CENT = Decimal("0.01")

# Normalized header -> canonical column.
_HEADER_ALIASES: dict[str, str] = {
    "date": "date",
    "data": "date",
    "description": "description",
    "descricao": "description",
    "despesa": "description",
    "amount": "amount",
    "valor": "amount",
    "category": "category",
    "categoria": "category",
}

_FULL_DATE_PATTERNS: list[tuple[re.Pattern[str], tuple[str, str, str]]] = [
    (re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$"), ("y", "m", "d")),
    (re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})$"), ("y", "m", "d")),
    (re.compile(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$"), ("d", "m", "y")),
]
_MONTH_PATTERNS: list[tuple[re.Pattern[str], tuple[str, str]]] = [
    (re.compile(r"^(\d{4})[-/](\d{1,2})$"), ("y", "m")),
    (re.compile(r"^(\d{1,2})[/.-](\d{4})$"), ("m", "y")),
]

# Spreadsheet formula prefixes (OWASP "CSV injection").
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


class CsvFormatError(ValueError):
    """The file as a whole cannot be read. `code` is sent to the client."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class _RowError(Exception):
    def __init__(self, code: RowErrorCode, value: str) -> None:
        self.code = code
        self.value = value


@dataclass
class ParsedRow:
    line: int
    expense_date: date
    amount: Decimal
    description: str  # may be empty: filled with the category name on import
    category: str  # raw CSV value, may be empty: falls back to "Other"


@dataclass
class ParsedCsv:
    total_rows: int
    rows: list[ParsedRow] = field(default_factory=list)
    errors: list[ImportRowError] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parsing (pure, no DB)
# ---------------------------------------------------------------------------


def normalize_key(value: str) -> str:
    """Case- and accent-insensitive comparison key."""
    return fold_text(value)


def _decode(raw: bytes) -> str:
    if raw.startswith(codecs.BOM_UTF8):
        return raw[len(codecs.BOM_UTF8) :].decode("utf-8", errors="replace")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        # Excel "CSV (separated by semicolons)" on Windows saves as cp1252.
        return raw.decode("cp1252", errors="replace")


def _detect_delimiter(text: str) -> str:
    first_line = next((line for line in text.splitlines() if line.strip()), "")
    counts = {d: first_line.count(d) for d in (";", ",", "\t")}
    best = max(counts, key=lambda d: counts[d])
    return best if counts[best] > 0 else ";"


def _strip_formula_guard(value: str) -> str:
    """Undo the `'` prefix that `export_csv` adds before formula characters."""
    if len(value) > 1 and value[0] == "'" and value[1].startswith(_FORMULA_PREFIXES):
        return value[1:]
    return value


def _parse_amount(value: str) -> Decimal:
    cleaned = re.sub(r"[\s €]", "", value)
    if not cleaned:
        raise _RowError("missing_amount", value)
    if "," in cleaned and "." in cleaned:
        # The right-most separator is the decimal one; the other groups thousands.
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        amount = Decimal(cleaned)
    except InvalidOperation as exc:
        raise _RowError("invalid_amount", value) from exc
    if not amount.is_finite():
        raise _RowError("invalid_amount", value)
    if amount <= 0:
        raise _RowError("non_positive_amount", value)
    if amount != amount.quantize(_CENT):
        raise _RowError("too_many_decimals", value)
    amount = amount.quantize(_CENT)
    if amount >= _MAX_AMOUNT:
        raise _RowError("amount_too_large", value)
    return amount


def _parse_date(value: str, default_month: date) -> date:
    text = value.strip()
    if not text:
        return default_month.replace(day=1)
    # Excel sometimes appends a time ("2026-01-15 00:00:00").
    text = re.split(r"[ T]", text, maxsplit=1)[0]
    try:
        for pattern, order in _FULL_DATE_PATTERNS:
            match = pattern.match(text)
            if match:
                parts = dict(zip(order, (int(g) for g in match.groups()), strict=True))
                return date(parts["y"], parts["m"], parts["d"])
        for pattern, month_order in _MONTH_PATTERNS:
            match = pattern.match(text)
            if match:
                parts = dict(zip(month_order, (int(g) for g in match.groups()), strict=True))
                return date(parts["y"], parts["m"], 1)
    except ValueError as exc:  # e.g. 2026-02-30 or month 13
        raise _RowError("invalid_date", value) from exc
    raise _RowError("invalid_date", value)


def parse_csv(raw: bytes, default_month: date) -> ParsedCsv:
    """Parse and validate an uploaded CSV. Raises `CsvFormatError` for
    file-level problems; row-level problems are collected in `errors`."""
    text = _decode(raw)
    if not text.strip():
        raise CsvFormatError("csv_empty")

    reader = csv.reader(io.StringIO(text, newline=""), delimiter=_detect_delimiter(text))
    try:
        header: list[str] | None = None
        for cells in reader:
            if any(c.strip() for c in cells):
                header = cells
                break
        if header is None:
            raise CsvFormatError("csv_empty")

        columns: dict[str, int] = {}
        for index, name in enumerate(header):
            canonical = _HEADER_ALIASES.get(normalize_key(name))
            if canonical and canonical not in columns:
                columns[canonical] = index
        if "amount" not in columns:
            raise CsvFormatError("csv_missing_amount_column")

        def cell(cells: list[str], column: str) -> str:
            index = columns.get(column)
            if index is None or index >= len(cells):
                return ""
            return _strip_formula_guard(cells[index].strip())

        parsed = ParsedCsv(total_rows=0)
        for cells in reader:
            if not any(c.strip() for c in cells):
                continue
            parsed.total_rows += 1
            if parsed.total_rows > MAX_ROWS:
                raise CsvFormatError("csv_too_many_rows")
            line = reader.line_num
            try:
                amount = _parse_amount(cell(cells, "amount"))
                expense_date = _parse_date(cell(cells, "date"), default_month)
                description = cell(cells, "description")
                if len(description) > _MAX_DESCRIPTION_LEN:
                    raise _RowError("description_too_long", description[:50])
                category = cell(cells, "category")
                if len(category) > _MAX_CATEGORY_LEN:
                    raise _RowError("category_too_long", category[:50])
            except _RowError as err:
                parsed.errors.append(ImportRowError(line=line, code=err.code, value=err.value))
                continue
            parsed.rows.append(
                ParsedRow(
                    line=line,
                    expense_date=expense_date,
                    amount=amount,
                    description=description,
                    category=category,
                )
            )
    except csv.Error as exc:
        raise CsvFormatError("csv_unreadable") from exc
    return parsed


# ---------------------------------------------------------------------------
# Import planning (read-only DB access)
# ---------------------------------------------------------------------------


@dataclass
class _PlannedRow:
    row: ParsedRow
    # Exactly one of these identifies the target category.
    category: Category | None = None
    new_category_key: str | None = None
    is_duplicate: bool = False


@dataclass
class _ImportPlan:
    rows: list[_PlannedRow]
    # normalized key -> display name (first spelling seen in the CSV)
    new_categories: dict[str, str]
    reactivate: list[Category]


def _other_display_name(user: User) -> str:
    return _OTHER_NAMES.get(user.language, _OTHER_NAMES["en"])


def _plan_import(session: Session, user: User, parsed: ParsedCsv) -> _ImportPlan:
    categories = list(session.exec(select(Category).where(Category.user_id == user.id)).all())

    # Active categories win over archived ones with the same name/slug.
    lookup: dict[str, Category] = {}
    for category in sorted(categories, key=lambda c: c.is_active):
        lookup[normalize_key(category.name)] = category
        lookup[normalize_key(category.slug)] = category

    other = next((c for c in categories if c.slug == OTHER_SLUG), None) or next(
        (lookup[k] for k in _OTHER_KEYS if k in lookup), None
    )
    other_key = normalize_key(_other_display_name(user))

    plan = _ImportPlan(rows=[], new_categories={}, reactivate=[])
    for row in parsed.rows:
        planned = _PlannedRow(row=row)
        key = normalize_key(row.category) if row.category else ""
        if key and key in lookup:
            planned.category = lookup[key]
        elif not key or key in _OTHER_KEYS:
            # No category (or an explicit "Other"/"Outros" that doesn't exist).
            if other is not None:
                planned.category = other
            else:
                planned.new_category_key = other_key
                plan.new_categories.setdefault(other_key, _other_display_name(user))
        else:
            planned.new_category_key = key
            plan.new_categories.setdefault(key, row.category)
        if (
            planned.category is not None
            and not planned.category.is_active
            and planned.category not in plan.reactivate
        ):
            plan.reactivate.append(planned.category)
        plan.rows.append(planned)

    _mark_duplicates(session, user, plan.rows)
    return plan


def _mark_duplicates(session: Session, user: User, rows: list[_PlannedRow]) -> None:
    """Flag rows whose (date, amount, category) already exists in the DB.
    Rows going to a new category cannot be duplicates. One query."""
    candidates = [r for r in rows if r.category is not None]
    if not candidates:
        return
    dates = [r.row.expense_date for r in candidates]
    category_ids = {r.category.id for r in candidates if r.category is not None}
    existing = session.exec(
        select(Expense.expense_date, Expense.amount, Expense.category_id).where(
            Expense.user_id == user.id,
            Expense.expense_date >= min(dates),
            Expense.expense_date <= max(dates),
            col(Expense.category_id).in_(category_ids),
        )
    ).all()
    keys = {(d, Decimal(a).quantize(_CENT), cid) for d, a, cid in existing}
    for r in candidates:
        assert r.category is not None
        r.is_duplicate = (r.row.expense_date, r.row.amount, r.category.id) in keys


def build_preview(session: Session, user: User, parsed: ParsedCsv) -> ImportPreview:
    plan = _plan_import(session, user, parsed)
    duplicates = sum(1 for r in plan.rows if r.is_duplicate)
    return ImportPreview(
        total_rows=parsed.total_rows,
        valid_rows=len(parsed.rows),
        invalid_rows=parsed.errors,
        duplicates=duplicates,
        new_categories=sorted(plan.new_categories.values(), key=normalize_key),
        reactivated_categories=sorted((c.name for c in plan.reactivate), key=normalize_key),
        total_amount=sum((r.amount for r in parsed.rows), Decimal("0.00")),
        requires_confirmation=duplicates >= DUPLICATE_CONFIRM_THRESHOLD,
    )


# ---------------------------------------------------------------------------
# Import (single commit)
# ---------------------------------------------------------------------------


async def run_import(
    session: Session, user: User, parsed: ParsedCsv, duplicate_mode: DuplicateMode
) -> ImportResult:
    plan = _plan_import(session, user, parsed)
    other_key = normalize_key(_other_display_name(user))
    try:
        created: dict[str, Category] = {}
        # "Other" first so it claims the `other` slug before any generated slug.
        for key in sorted(plan.new_categories, key=lambda k: k != other_key):
            name = plan.new_categories[key]
            icon: str | None
            if key == other_key:
                # Planning only creates "Other" when no category has that slug.
                slug, icon = OTHER_SLUG, "📦"
            else:
                slug = await slug_service.generate_category_slug(session, user.id, name)
                icon = None
            category = Category(user_id=user.id, slug=slug, name=name, icon=icon)
            session.add(category)
            # Flush so the next slug lookup sees this one (per-user uniqueness).
            session.flush()
            created[key] = category

        for category in plan.reactivate:
            category.is_active = True
            session.add(category)

        imported = skipped = 0
        for planned in plan.rows:
            if planned.is_duplicate and duplicate_mode == "skip":
                skipped += 1
                continue
            category = planned.category or created[planned.new_category_key or ""]
            session.add(
                Expense(
                    user_id=user.id,
                    category_id=category.id,
                    amount=planned.row.amount,
                    expense_date=planned.row.expense_date,
                    description=planned.row.description or category.name,
                )
            )
            imported += 1
        session.commit()
    except Exception:
        session.rollback()
        raise

    for category in created.values():
        session.refresh(category)
    return ImportResult(
        imported=imported,
        skipped_duplicates=skipped,
        skipped_invalid=len(parsed.errors),
        created_categories=[CategoryRead.model_validate(c) for c in created.values()],
    )


# ---------------------------------------------------------------------------
# Export / template
# ---------------------------------------------------------------------------


def _guard_formula(value: str) -> str:
    """Prefix spreadsheet formula characters with `'` (OWASP CSV injection)."""
    return f"'{value}" if value.startswith(_FORMULA_PREFIXES) else value


def _format_amount(amount: Decimal) -> str:
    return f"{Decimal(amount).quantize(_CENT)}".replace(".", ",")


def _write_csv(rows: Iterable[list[str]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(CSV_HEADER)
    writer.writerows(rows)
    # BOM so Excel detects UTF-8 (accents) when opening by double-click.
    return "﻿" + buffer.getvalue()


def export_csv(session: Session, user_id: UUID, date_from: date, date_to: date) -> str:
    results = session.exec(
        select(Expense.expense_date, Expense.description, Expense.amount, Category.name)
        .join(Category, col(Category.id) == Expense.category_id)
        .where(
            Expense.user_id == user_id,
            Expense.expense_date >= date_from,
            Expense.expense_date <= date_to,
        )
        .order_by(col(Expense.expense_date), col(Expense.created_at))
    ).all()
    return _write_csv(
        [
            expense_date.isoformat(),
            _guard_formula(description),
            _format_amount(amount),
            _guard_formula(category_name),
        ]
        for expense_date, description, amount, category_name in results
    )


_TEMPLATE_ROWS: dict[str, list[list[str]]] = {
    "pt": [
        ["2026-01-15", "Supermercado", "23,45", "Alimentação"],
        ["2026-02", "Ginásio", "42,19", "Mensalidades"],
        ["", "Café", "1,20", ""],
    ],
    "en": [
        ["2026-01-15", "Groceries", "23,45", "Food"],
        ["2026-02", "Gym", "42,19", "Subscriptions"],
        ["", "Coffee", "1,20", ""],
    ],
}


def template_csv(language: str) -> str:
    return _write_csv(_TEMPLATE_ROWS.get(language, _TEMPLATE_ROWS["en"]))
