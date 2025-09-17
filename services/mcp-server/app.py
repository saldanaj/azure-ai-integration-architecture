from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
from fastmcp import MCP, tool

from task_store import TaskStore

MCP_APP = MCP("discharge-mcp")

FHIR_BASE_URL = os.environ.get("FHIR_BASE_URL", "http://mock-fhir:8080/fhir")
TASK_DB_PATH = os.environ.get(
    "TASK_DB_PATH",
    str(Path(__file__).resolve().parent / "data" / "tasks.db"),
)
TASK_STORE = TaskStore(TASK_DB_PATH)
SAFE_MODE = os.environ.get("SAFE_MODE", "true").lower() != "false"


def _fetch_json(url: str) -> dict[str, Any]:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


@tool
def get_fhir_document(patientId: str, encounterId: str | None, documentId: str) -> dict[str, Any]:
    """Fetch a DocumentReference payload from the mock FHIR service."""
    url = f"{FHIR_BASE_URL}/DocumentReference/{documentId}"
    document = _fetch_json(url)
    # No PHI logging; rely on caller to mask if needed.
    return document


@tool
def upsert_task(taskJson: dict[str, Any]) -> dict[str, str]:
    """Insert or update a care task using the local SQLite store."""
    return TASK_STORE.upsert(taskJson)


@tool
def emit_eventgrid(eventType: str, subject: str, data: dict[str, Any]) -> dict[str, bool]:
    """Stub that records an Event Grid publish; prints sanitized fields for local dev."""
    if SAFE_MODE:
        print(f"[eventgrid] {eventType} subject={subject}")
    else:
        print(f"[eventgrid] {eventType} subject={subject} data={data}")
    return {"published": True}


@tool
def phi_scrub(text: str) -> str:
    """Light PII/PHI scrubbing (demo-grade)."""
    return text.replace("MRN:", "MRN:***")


if __name__ == "__main__":
    MCP_APP.run(host="0.0.0.0", port=9000)
