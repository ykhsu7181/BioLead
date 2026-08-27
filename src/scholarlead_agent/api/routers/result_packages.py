"""Result Package API routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from scholarlead_agent.api.errors import ApiError, api_success
from scholarlead_agent.api.schemas.result_package import CreateResultPackageRequest


router = APIRouter(prefix="/api/result-packages", tags=["result-packages"])


@router.post("")
def create_result_package(request: CreateResultPackageRequest) -> dict[str, object]:
    # Stage 34B exposes the API boundary only. Building from a task id requires
    # the Stage 33 PubMedRunResult object or a later ResultPackage application
    # service that can reconstruct it from persisted artifacts.
    raise ApiError(
        "RESULT_PACKAGE_CREATE_NOT_READY",
        (
            "Result Package creation from task_id is reserved for the "
            "application service layer; use Stage 33 service directly for now."
        ),
        501,
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
