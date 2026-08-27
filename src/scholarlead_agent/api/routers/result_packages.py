"""Result Package API routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from scholarlead_agent.api.dependencies import get_database
from scholarlead_agent.api.errors import ApiError, api_success
from scholarlead_agent.api.schemas.result_package import CreateResultPackageRequest
from scholarlead_agent.result_package import build_result_package_from_database_task


router = APIRouter(prefix="/api/result-packages", tags=["result-packages"])


@router.post("")
def create_result_package(
    request: CreateResultPackageRequest,
    connection=Depends(get_database),
) -> dict[str, object]:
    try:
        package = build_result_package_from_database_task(
            connection,
            task_id=request.task_id,
            output_dir=request.output_dir or "data/processed/result_packages",
        )
    except ValueError as error:
        raise ApiError("RESULT_PACKAGE_TASK_NOT_FOUND", str(error), 404) from error
    return api_success(
        {
            "package_id": package.package_id,
            "task_id": package.task_id,
            "status": package.status,
            "package_dir": str(package.paths.package_dir),
            "workbook_path": str(package.paths.workbook_xlsx),
            "row_counts": package.row_counts,
        }
    )


@router.get("/{package_id}")
def get_result_package(package_id: str) -> dict[str, object]:
    package_dir = Path("data/processed/result_packages") / package_id
    summary_path = package_dir / "task_summary.json"
    if not summary_path.exists():
        raise ApiError("RESULT_PACKAGE_NOT_FOUND", "Result Package not found", 404)
    return api_success(
        {
            "package_id": package_id,
            "package_dir": str(package_dir),
            "summary_path": str(summary_path),
            "files": sorted(path.name for path in package_dir.iterdir() if path.is_file()),
        }
    )


@router.get("/{package_id}/download")
def download_result_package(package_id: str) -> FileResponse:
    package_dir = Path("data/processed/result_packages") / package_id
    workbook_path = package_dir / "scholarlead_results.xlsx"
    if not workbook_path.exists():
        raise ApiError("RESULT_PACKAGE_NOT_FOUND", "Result Package workbook not found", 404)
    return FileResponse(
        workbook_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="scholarlead_results.xlsx",
    )
