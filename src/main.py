"""
Agent 1 — Bulk Company Enrichment Agent
Application entrypoint.
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.api.routes import router

app = FastAPI(title="Agent 1 — Bulk Company Enrichment Agent")
app.include_router(router)


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
