"""
Agent 1 — Bulk Company Enrichment Agent
Application entrypoint.
"""

from fastapi import FastAPI

from src.api.routes import router
from src.db.database import init_db


init_db()

app = FastAPI(title="Agent 1 — Bulk Company Enrichment Agent")
app.include_router(router)


@app.get("/health")
def health_check():
    return {"status": "ok"}