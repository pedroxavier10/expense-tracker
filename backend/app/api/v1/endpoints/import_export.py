"""CSV import/export endpoints.

Import is two calls on the same file: `/import/preview` (read-only report) and
`/import` (commits). The server keeps no state between them; the client
re-uploads the file to confirm.

File-level problems return a short machine-readable `detail` code (e.g.
`csv_missing_amount_column`) that the frontend translates.
"""

from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, Response, UploadFile, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.import_export import DuplicateMode, ImportPreview, ImportResult
from app.services import csv_service

router = APIRouter(prefix="/import-export", tags=["import-export"])

_MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"
_CSV_MEDIA_TYPE = "text/csv; charset=utf-8"


def _csv_response(content: str, filename: str) -> Response:
    return Response(
        content=content.encode("utf-8"),
        media_type=_CSV_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _default_month(value: str | None) -> date:
    if not value:
        return datetime.now(UTC).date().replace(day=1)
    year, month = (int(p) for p in value.split("-"))
    return date(year, month, 1)


async def _parse_upload(file: UploadFile, default_month: str | None) -> csv_service.ParsedCsv:
    raw = await file.read(csv_service.MAX_FILE_BYTES + 1)
    if len(raw) > csv_service.MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="csv_too_large")
    try:
        return csv_service.parse_csv(raw, _default_month(default_month))
    except csv_service.CsvFormatError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.code) from exc


@router.get("/template", summary="Download the CSV import template")
def download_template(current_user: CurrentUser) -> Response:
    return _csv_response(csv_service.template_csv(current_user.language), "expenses_template.csv")


@router.get("/export", summary="Export expenses in a date range as CSV")
def export_expenses(
    session: SessionDep,
    current_user: CurrentUser,
    date_from: Annotated[date | None, Query(description="Inclusive; default Jan 1")] = None,
    date_to: Annotated[date | None, Query(description="Inclusive; default Dec 31")] = None,
) -> Response:
    year = datetime.now(UTC).year
    start = date_from or date(year, 1, 1)
    end = date_to or date(year, 12, 31)
    if start > end:
        raise HTTPException(
            status_code=422,
            detail="date_from must be on or before date_to",
        )
    content = csv_service.export_csv(session, current_user.id, start, end)
    return _csv_response(content, f"expenses_{start.isoformat()}_{end.isoformat()}.csv")


@router.post(
    "/import/preview",
    response_model=ImportPreview,
    summary="Validate a CSV and report what an import would do (writes nothing)",
)
async def preview_import(
    session: SessionDep,
    current_user: CurrentUser,
    file: Annotated[UploadFile, File(description="CSV file")],
    default_month: Annotated[
        str | None, Form(pattern=_MONTH_PATTERN, description="YYYY-MM for rows without a date")
    ] = None,
) -> ImportPreview:
    parsed = await _parse_upload(file, default_month)
    return csv_service.build_preview(session, current_user, parsed)


@router.post(
    "/import",
    response_model=ImportResult,
    status_code=status.HTTP_201_CREATED,
    summary="Import expenses from a CSV (creates missing categories)",
)
async def import_expenses(
    session: SessionDep,
    current_user: CurrentUser,
    file: Annotated[UploadFile, File(description="CSV file")],
    default_month: Annotated[
        str | None, Form(pattern=_MONTH_PATTERN, description="YYYY-MM for rows without a date")
    ] = None,
    duplicate_mode: Annotated[DuplicateMode, Form()] = "import",
    confirm_duplicates: Annotated[bool, Form()] = False,
) -> ImportResult:
    parsed = await _parse_upload(file, default_month)
    preview = csv_service.build_preview(session, current_user, parsed)
    if preview.requires_confirmation and not confirm_duplicates:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="duplicates_confirmation_required"
        )
    return await csv_service.run_import(session, current_user, parsed, duplicate_mode)
