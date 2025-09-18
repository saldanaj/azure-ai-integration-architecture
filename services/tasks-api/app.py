from __future__ import annotations

import os
import sqlite3
from typing import Any

from flask import Flask, jsonify, request

app = Flask(__name__)

TASK_DB_PATH = os.environ.get("TASK_DB_PATH", "/data/tasks.db")
VALID_STATUS = {"open", "done", "cancelled"}


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(TASK_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "taskId": row["task_id"],
        "patientId": row["patient_id"],
        "category": row["category"],
        "title": row["title"],
        "dueDate": row["due_date"],
        "priority": row["priority"],
        "status": row["status"],
        "sourceEncounterId": row["source_encounter_id"],
        "createdUtc": row["created_utc"],
        "updatedUtc": row["updated_utc"],
    }


@app.get("/patients/<patient_id>/tasks")
def get_tasks(patient_id: str):
    status = request.args.get("status")
    if status and status not in VALID_STATUS:
        return jsonify({"error": "invalid status"}), 400

    query = "select * from care_tasks where patient_id = ?"
    params: list[Any] = [patient_id]
    if status:
        query += " and status = ?"
        params.append(status)

    query += " order by due_date is null, due_date"

    with _get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    tasks = [_row_to_dict(row) for row in rows]
    return jsonify(tasks)


@app.get("/healthz")
def health() -> tuple[str, int]:
    return "ok", 200


if __name__ == "__main__":
    os.makedirs(os.path.dirname(TASK_DB_PATH), exist_ok=True)
    app.run(host="0.0.0.0", port=7100)
