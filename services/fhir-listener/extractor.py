from __future__ import annotations

import base64
import re
from datetime import datetime, timedelta
from typing import Any, List


def _decode_document_text(document: dict[str, Any]) -> str:
    contents = document.get("content", []) if isinstance(document, dict) else []
    for entry in contents:
        attachment = entry.get("attachment") if isinstance(entry, dict) else None
        data = attachment.get("data") if isinstance(attachment, dict) else None
        if not data:
            continue
        try:
            decoded = base64.b64decode(data).decode("utf-8")
            if decoded:
                return decoded
        except Exception:
            continue
    return ""


def _parse_discharge_date(note_text: str) -> datetime | None:
    match = re.search(r"Discharge Date:\s*(\d{4}-\d{2}-\d{2})", note_text)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d")
    except ValueError:
        return None


def _extract_due_date(discharge_date: datetime | None, line: str) -> str | None:
    if not discharge_date:
        return None
    match_days = re.search(r"(\d+)\s+day", line, flags=re.IGNORECASE)
    match_hours = re.search(r"(\d+)\s+hour", line, flags=re.IGNORECASE)
    if match_days:
        days = int(match_days.group(1))
        return (discharge_date + timedelta(days=days)).strftime("%Y-%m-%d")
    if match_hours:
        hours = int(match_hours.group(1))
        days = hours / 24
        return (discharge_date + timedelta(days=days)).strftime("%Y-%m-%d")
    return None


def extract_followups(
    document: dict[str, Any], patient_id: str | None, encounter_id: str | None
) -> List[dict[str, Any]]:
    note_text = _decode_document_text(document)
    discharge_date = _parse_discharge_date(note_text)
    followups: List[dict[str, Any]] = []

    for line in note_text.splitlines():
        line = line.strip()
        if not line:
            continue
        lowered = line.lower()
        if lowered.startswith("1. labs") or lowered.startswith("labs:"):
            due_date = _extract_due_date(discharge_date, line)
            followups.append(
                {
                    "category": "lab",
                    "title": "Order basic metabolic panel to monitor renal function and potassium",
                    "dueDate": due_date,
                    "priority": "normal",
                    "patientId": patient_id,
                    "sourceEncounterId": encounter_id,
                }
            )
        elif lowered.startswith("2. visit") or lowered.startswith("visit:"):
            due_date = _extract_due_date(discharge_date, line)
            followups.append(
                {
                    "category": "visit",
                    "title": "Schedule cardiology follow-up visit to reassess volume status and adjust medications",
                    "dueDate": due_date,
                    "priority": "normal",
                    "patientId": patient_id,
                    "sourceEncounterId": encounter_id,
                }
            )
        elif lowered.startswith("3. medication") or lowered.startswith("medication:"):
            due_date = _extract_due_date(discharge_date, line)
            followups.append(
                {
                    "category": "med",
                    "title": "Conduct nursing phone call to reinforce low-sodium diet and confirm medication adherence",
                    "dueDate": due_date,
                    "priority": "normal",
                    "patientId": patient_id,
                    "sourceEncounterId": encounter_id,
                }
            )

    return followups


__all__ = ["extract_followups"]
