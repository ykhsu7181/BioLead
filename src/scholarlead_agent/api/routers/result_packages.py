"""Result Package API routes."""

from __future__ import annotations

from pathlib import Path
import json
import re

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from scholarlead_agent.api.dependencies import get_database
from scholarlead_agent.api.errors import ApiError, api_success
from scholarlead_agent.api.schemas.result_package import CreateResultPackageRequest
from scholarlead_agent.result_package import (
    DEFAULT_RESULT_PACKAGE_DIR,
    build_result_package_from_database_task,
)


router = APIRouter(prefix="/api/result-packages", tags=["result-packages"])
RESULT_PACKAGE_ROOT = DEFAULT_RESULT_PACKAGE_DIR
_PACKAGE_ID_PATTERN = re.compile(r"^TASK_[a-zA-Z0-9_]+$")


@router.post("")
def create_result_package(
    request: CreateResultPackageRequest,
    connection=Depends(get_database),
) -> dict[str, object]:
    try:
        package = build_result_package_from_database_task(
            connection,
            task_id=request.task_id,
            output_dir=RESULT_PACKAGE_ROOT,
        )
    except ValueError as error:
        raise ApiError("RESULT_PACKAGE_TASK_NOT_FOUND", str(error), 404) from error
    return api_success(
        {
            "package_id": package.package_id,
            "task_id": package.task_id,
            "status": "completed",
            "row_counts": package.row_counts,
            "download_available": package.paths.workbook_xlsx.is_file(),
        }
    )


@router.get("/{package_id}")
def get_result_package(package_id: str) -> dict[str, object]:
    package_dir = _safe_package_dir(package_id)
    summary_path = _safe_package_file(package_dir, "task_summary.json")
    if not summary_path.exists():
        raise ApiError("RESULT_PACKAGE_NOT_FOUND", "Result Package not found", 404)
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ApiError(
            "RESULT_PACKAGE_INVALID",
            "Result Package summary is invalid",
            500,
        ) from error
    return api_success(
        {
            "package_id": package_id,
            "task_id": summary.get("task_id"),
            "status": "completed",
            "row_counts": summary.get("row_counts") or {},
            "download_available": _safe_package_file(
                package_dir,
                "scholarlead_results.xlsx",
            ).is_file(),
            "files": sorted(path.name for path in package_dir.iterdir() if path.is_file()),
        }
    )


@router.get("/{package_id}/download")
def download_result_package(package_id: str) -> FileResponse:
    package_dir = _safe_package_dir(package_id)
    workbook_path = _safe_package_file(package_dir, "scholarlead_results.xlsx")
    if not workbook_path.exists():
        raise ApiError("RESULT_PACKAGE_NOT_FOUND", "Result Package workbook not found", 404)
    return FileResponse(
        workbook_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="scholarlead_results.xlsx",
    )


def _safe_package_dir(package_id: str) -> Path:
    if not _PACKAGE_ID_PATTERN.fullmatch(package_id):
        raise ApiError("INVALID_RESULT_PACKAGE_ID", "Invalid Result Package ID", 400)
    root = Path(RESULT_PACKAGE_ROOT).resolve()
    candidate = (root / package_id).resolve()
    if candidate.parent != root:
        raise ApiError("INVALID_RESULT_PACKAGE_ID", "Invalid Result Package ID", 400)
    return candidate


def _safe_package_file(package_dir: Path, filename: str) -> Path:
    candidate = (package_dir / filename).resolve()
    if candidate.parent != package_dir:
        raise ApiError("INVALID_RESULT_PACKAGE_PATH", "Invalid Result Package path", 400)
    return candidate
