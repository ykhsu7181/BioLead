"""Dashboard summary API routes."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from scholarlead_agent.api.dependencies import get_database
from scholarlead_agent.api.errors import api_success
from scholarlead_agent.services.dashboard_service import get_dashboard_summary


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    """Return the real database-backed homepage summary."""

    return api_success(get_dashboard_summary(connection).to_dict())
