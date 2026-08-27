"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from scholarlead_agent.api.errors import (
    ApiError,
    api_error_handler,
    api_success,
    unhandled_error_handler,
)
from scholarlead_agent.api.routers import (
    conversations,
    email_batches,
    jobs,
    leads,
    pubmed,
    result_packages,
    tasks,
)


def create_app() -> FastAPI:
    """Create the ScholarLead Agent FastAPI app."""

    app = FastAPI(
        title="ScholarLead Agent API",
        version="0.1.0",
        description="Thin API boundary over existing ScholarLead Agent services.",
    )
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
    app.include_router(conversations.router)
    app.include_router(tasks.router)
    app.include_router(pubmed.router)
    app.include_router(leads.router)
    app.include_router(email_batches.router)
    app.include_router(jobs.router)
    app.include_router(result_packages.router)

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return api_success({"status": "ok"})

    return app


app = create_app()
