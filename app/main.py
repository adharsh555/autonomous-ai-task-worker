from __future__ import annotations
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .agent import Agent, Run
from .config import settings
from .db import init_db, connect

app = FastAPI(title="Autonomous AI Task Worker", version="1.0.0")
AGENT = Agent()
RUNS: dict[str, Run] = {}


class RunRequest(BaseModel):
    task: str = Field(min_length=5, max_length=1000)


class ApprovalRequest(BaseModel):
    approved: bool


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/")
def home() -> FileResponse:
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "model": settings.gemini_model, "max_steps": settings.max_agent_steps}


@app.post("/api/run")
def run_task(payload: RunRequest) -> dict[str, Any]:
    run = AGENT.start(payload.task)
    RUNS[run.id] = run
    return serialize(run)


@app.post("/api/runs/{run_id}/approval")
def approval(run_id: str, payload: ApprovalRequest) -> dict[str, Any]:
    run = RUNS.get(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    run = AGENT.approve(run, payload.approved)
    return serialize(run)


@app.get("/api/billing/{invoice_id}")
def billing(invoice_id: str) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM billing_records WHERE invoice_id=?", (invoice_id,)).fetchone()
    return dict(row) if row else {"found": False, "invoice_id": invoice_id}


def serialize(run: Run) -> dict[str, Any]:
    return {
        "run_id": run.id,
        "status": run.status,
        "final": run.final,
        "trace": run.trace,
        "pending_approval": run.pending_approval,
        "steps": run.steps,
    }
