from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Optional
from uuid import uuid4


class TaskStore:
    """SQLite-backed stub that mimics Azure SQL upsert behaviour."""

    def __init__(self, db_path: str | Path) -> None:
        self.path = Path(db_path)
        if self.path.is_dir():
            raise ValueError(f"task store path must be a file, got directory: {self.path}")
        if not self.path.parent.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists care_tasks (
                  task_id text primary key,
                  patient_id text not null,
                  category text not null,
                  title text not null,
                  due_date text,
                  priority text not null,
                  source_encounter_id text,
                  status text not null,
                  created_utc text not null,
                  updated_utc text not null
                )
                """
            )
            conn.execute(
                """
                create table if not exists task_audit (
                  audit_id integer primary key autoincrement,
                  task_id text not null,
                  action text not null,
                  actor text not null,
                  timestamp_utc text not null,
                  payload_json text
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.execute("pragma journal_mode = wal")
        return conn

    def upsert(self, task_json: dict[str, Any]) -> dict[str, str]:
        patient_id = task_json.get("patientId") or task_json.get("patient_id")
        if not patient_id:
            raise ValueError("taskJson.patientId is required")
        category = task_json.get("category") or "other"
        title = task_json.get("title")
        if not title:
            raise ValueError("taskJson.title is required")
        due_date = task_json.get("dueDate") or None
        priority = task_json.get("priority") or "normal"
        source_encounter = task_json.get("sourceEncounterId") or task_json.get("source_encounter_id")
        task_id = (
            task_json.get("taskId")
            or task_json.get("task_id")
            or f"T{uuid4().hex[:10]}"
        )
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                insert into care_tasks(
                  task_id, patient_id, category, title, due_date, priority,
                  source_encounter_id, status, created_utc, updated_utc
                ) values (?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)
                on conflict(task_id) do update set
                  patient_id=excluded.patient_id,
                  category=excluded.category,
                  title=excluded.title,
                  due_date=excluded.due_date,
                  priority=excluded.priority,
                  source_encounter_id=excluded.source_encounter_id,
                  updated_utc=excluded.updated_utc
                """,
                (
                    task_id,
                    patient_id,
                    category,
                    title,
                    due_date,
                    priority,
                    source_encounter,
                    now,
                    now,
                ),
            )
            conn.execute(
                """
                insert into task_audit(task_id, action, actor, timestamp_utc, payload_json)
                values (?, 'upsert', 'mcp-server', ?, ?)
                """,
                (
                    task_id,
                    now,
                    json.dumps(task_json, default=str),
                ),
            )
            conn.commit()
        return {"taskId": task_id}


__all__ = ["TaskStore"]
