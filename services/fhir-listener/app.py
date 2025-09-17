from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List

import requests
from flask import Flask, jsonify, request

from event_store import EventStore
from extractor import extract_followups

app = Flask(__name__)

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("fhir_listener")

SAFE_MODE = os.environ.get("SAFE_MODE", "true").lower() != "false"
MCP_URL = os.environ.get("MCP_URL", "http://mcp-server:9000/mcp")
EVENT_STORE_PATH = os.environ.get(
    "EVENT_STORE_PATH",
    str(Path(__file__).resolve().parent / "data" / "listener.db"),
)
EVENT_STORE = EventStore(EVENT_STORE_PATH)
DEFAULT_RETRIES = int(os.environ.get("MCP_RETRIES", "3"))
DEFAULT_TIMEOUT = int(os.environ.get("MCP_TIMEOUT_SECONDS", "10"))


def _as_event_list(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [evt for evt in payload if isinstance(evt, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


def _log_safe(message: str, **fields: Any) -> None:
    safe_fields = {k: v for k, v in fields.items() if v is not None}
    if SAFE_MODE:
        safe_fields.pop("raw", None)
    if safe_fields:
        logger.info("%s %s", message, safe_fields)
    else:
        logger.info(message)


def mcp_call(method: str, params: Dict[str, Any], retries: int = DEFAULT_RETRIES) -> Dict[str, Any]:
    payload = {"jsonrpc": "2.0", "id": "1", "method": f"tools/{method}", "params": params}
    delay = 0.5
    for attempt in range(retries):
        try:
            response = requests.post(MCP_URL, json=payload, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            body = response.json()
        except Exception as exc:  # network failure or decode error
            if attempt == retries - 1:
                _log_safe("mcp call failed", method=method)
                raise
            time.sleep(delay)
            delay *= 2
            continue
        if "error" in body:
            error = body["error"]
            raise RuntimeError(f"mcp error {method}: {json.dumps(error)}")
        return body.get("result", {})
    return {}


def handle_discharge_created(evt: Dict[str, Any]) -> None:
    event_id = evt.get("id")
    event_type = evt.get("eventType", "DischargeCreated")
    data = evt.get("data") or {}
    patient_id = data.get("patientId")

    if not event_id:
        _log_safe("ignoring event without id", event_type=event_type)
        return

    if EVENT_STORE.has_seen(event_id):
        _log_safe("duplicate event skipped", event_id=event_id, event_type=event_type, patient_id=patient_id)
        return

    try:
        document = mcp_call(
            "get_fhir_document",
            {
                "patientId": patient_id,
                "encounterId": data.get("encounterId"),
                "documentId": data.get("documentId"),
            },
        )
        if not isinstance(document, dict):
            raise ValueError("Unexpected document payload from MCP")

        followups = extract_followups(document, patient_id, data.get("encounterId"))
        if not followups:
            followups = [
                {
                    "category": "other",
                    "title": "Follow up required",
                    "dueDate": None,
                    "priority": "normal",
                    "patientId": patient_id,
                    "sourceEncounterId": data.get("encounterId"),
                }
            ]

        for followup in followups:
            task_response = mcp_call("upsert_task", {"taskJson": followup})
            task_id = task_response.get("taskId")
            mcp_call(
                "emit_eventgrid",
                {
                    "eventType": "TaskCreated",
                    "subject": f"patients/{patient_id}/tasks/{task_id}",
                    "data": {
                        "patientId": patient_id,
                        "taskId": task_id,
                        "category": followup["category"],
                        "title": followup["title"],
                    },
                },
            )

        EVENT_STORE.record(event_id, event_type, patient_id)
        _log_safe("event processed", event_id=event_id, event_type=event_type, patient_id=patient_id)
    except Exception:
        _log_safe("processing error", event_id=event_id, event_type=event_type)
        raise


@app.route("/events", methods=["POST", "OPTIONS"])
def events() -> tuple[str, int]:
    payload = request.get_json(force=True, silent=True)
    if payload is None:
        return ("", 400)

    if isinstance(payload, dict) and payload.get("validationCode"):
        return jsonify({"validationResponse": payload["validationCode"]})

    events = _as_event_list(payload)
    if events:
        first = events[0]
        if first.get("eventType") == "Microsoft.EventGrid.SubscriptionValidationEvent":
            validation_code = first.get("data", {}).get("validationCode")
            return jsonify({"validationResponse": validation_code})

    for evt in events:
        if evt.get("eventType") == "DischargeCreated":
            handle_discharge_created(evt)

    return ("", 204)


@app.route("/healthz")
def healthz() -> tuple[str, int]:
    return "ok", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7001)
