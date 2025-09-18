from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import requests
from azure.identity import DefaultAzureCredential
from fastmcp import MCP, tool

from task_store import create_task_store

MCP_APP = MCP("discharge-mcp")

FHIR_BASE_URL = os.environ.get("FHIR_BASE_URL", "http://mock-fhir:8080/fhir")
TASK_DB_PATH = os.environ.get("TASK_DB_PATH", "/data/tasks.db")
SAFE_MODE = os.environ.get("SAFE_MODE", "true").lower() != "false"
TASK_DB_MODE = os.environ.get("TASK_DB_MODE", "sqlite")
SQL_SERVER = os.environ.get("SQL_SERVER")
SQL_DATABASE = os.environ.get("SQL_DATABASE")
SQL_USERNAME = os.environ.get("SQL_USERNAME")
SQL_PASSWORD = os.environ.get("SQL_PASSWORD")
SQL_CONNECTION_STRING = os.environ.get("SQL_CONNECTION_STRING")
AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID")

EVENTGRID_TOPIC_URL = os.environ.get("EVENTGRID_TOPIC_URL")
EVENTGRID_KEY = os.environ.get("EVENTGRID_KEY")
EVENTGRID_SCOPE = os.environ.get("EVENTGRID_SCOPE", "https://eventgrid.azure.net/.default")
EVENTGRID_DATA_VERSION = os.environ.get("EVENTGRID_DATA_VERSION", "1.0")

_CREDENTIAL: DefaultAzureCredential | None = None


def _get_default_credential() -> DefaultAzureCredential:
    global _CREDENTIAL
    if _CREDENTIAL is None:
        _CREDENTIAL = DefaultAzureCredential(
            managed_identity_client_id=AZURE_CLIENT_ID,
            exclude_interactive_browser_credential=True,
        )
    return _CREDENTIAL


TASK_STORE = create_task_store(
    mode=TASK_DB_MODE,
    sqlite_path=TASK_DB_PATH,
    sql_server=SQL_SERVER,
    sql_database=SQL_DATABASE,
    sql_username=SQL_USERNAME,
    sql_password=SQL_PASSWORD,
    sql_connection_string=SQL_CONNECTION_STRING,
    managed_identity_client_id=AZURE_CLIENT_ID,
)


def _fetch_json(url: str) -> dict[str, Any]:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


@tool
def get_fhir_document(patientId: str, encounterId: str | None, documentId: str) -> dict[str, Any]:
    """Fetch a DocumentReference payload from the mock FHIR service."""
    url = f"{FHIR_BASE_URL}/DocumentReference/{documentId}"
    document = _fetch_json(url)
    return document


@tool
def upsert_task(taskJson: dict[str, Any]) -> dict[str, str]:
    """Insert or update a care task using the configured task store."""
    return TASK_STORE.upsert(taskJson)


def _build_eventgrid_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if EVENTGRID_KEY:
        headers["aeg-sas-key"] = EVENTGRID_KEY
    else:
        credential = _get_default_credential()
        token = credential.get_token(EVENTGRID_SCOPE)
        headers["Authorization"] = f"Bearer {token.token}"
    return headers


@tool
def emit_eventgrid(eventType: str, subject: str, data: dict[str, Any]) -> dict[str, Any]:
    """Publish an Event Grid event either to Azure or log locally when not configured."""
    if not EVENTGRID_TOPIC_URL:
        if SAFE_MODE:
            print(f"[eventgrid] {eventType} subject={subject}")
        else:
            print(f"[eventgrid] {eventType} subject={subject} data={json.dumps(data)}")
        return {"published": False, "reason": "topic-not-configured"}

    event_id = str(uuid4())
    event = {
        "id": event_id,
        "eventType": eventType,
        "subject": subject,
        "eventTime": datetime.now(timezone.utc).isoformat(),
        "data": data,
        "dataVersion": EVENTGRID_DATA_VERSION,
    }
    headers = _build_eventgrid_headers()
    response = requests.post(
        EVENTGRID_TOPIC_URL,
        json=[event],
        headers=headers,
        timeout=10,
    )
    response.raise_for_status()
    if SAFE_MODE:
        print(f"[eventgrid] {eventType} subject={subject} id={event_id}")
    else:
        print(f"[eventgrid] published {json.dumps(event)}")
    return {"published": True, "eventId": event_id}


@tool
def phi_scrub(text: str) -> str:
    """Light PII/PHI scrubbing (demo-grade)."""
    return text.replace("MRN:", "MRN:***")


if __name__ == "__main__":
    MCP_APP.run(host="0.0.0.0", port=9000)
