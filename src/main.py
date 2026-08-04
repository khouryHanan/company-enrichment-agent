"""
Agent 1 — Bulk Company Enrichment Agent
Application entrypoint.
"""

from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from src.api.routes import router
from src.db.database import init_db

app = FastAPI(title="Agent 1 — Bulk Company Enrichment Agent")
app.include_router(router)


@app.on_event("startup")
def create_tables() -> None:
    # Idempotent — creates only tables that don't exist yet. Without
    # this the app only works if agent1.db already has tables (it's
    # gitignored, so fresh clones and deleted DBs crashed with
    # "no such table: batches").
    init_db()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Flattens Pydantic's nested error format into a simple, readable list —
    per Mission 4's "return clear errors for invalid input structure" and
    "the agent does not crash on malformed input."
    """
    errors = [
        {"field": ".".join(str(p) for p in err["loc"] if p != "body"), "message": err["msg"]}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Invalid request", "errors": errors},
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/demo", include_in_schema=False)
def demo_ui():
    """Client-facing demo UI (SCRUM-18) — a single self-contained page
    styled after the EYEjee platform this agent extends."""
    return FileResponse(Path(__file__).parent / "static" / "demo.html")
