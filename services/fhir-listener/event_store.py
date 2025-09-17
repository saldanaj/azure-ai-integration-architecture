from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Optional


class EventStore:
    """Lightweight SQLite-backed store for processed Event Grid IDs."""

    def __init__(self, db_path: str | Path) -> None:
        self.path = Path(db_path)
        if self.path.is_dir():
            raise ValueError(f"event store path must be a file, got directory: {self.path}")
        if not self.path.parent.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists processed_events (
                  event_id text primary key,
                  event_type text not null,
                  patient_id text,
                  processed_utc text not null
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.execute("pragma journal_mode = wal")
        return conn

    def has_seen(self, event_id: str) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "select 1 from processed_events where event_id = ? limit 1", (event_id,)
            )
            return cur.fetchone() is not None

    def record(self, event_id: str, event_type: str, patient_id: Optional[str]) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                insert into processed_events(event_id, event_type, patient_id, processed_utc)
                values (?, ?, ?, ?)
                on conflict(event_id) do update set
                  event_type=excluded.event_type,
                  patient_id=excluded.patient_id,
                  processed_utc=excluded.processed_utc
                """,
                (event_id, event_type, patient_id, timestamp),
            )
            conn.commit()


__all__ = ["EventStore"]
