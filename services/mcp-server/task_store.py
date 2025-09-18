from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Optional
from uuid import uuid4

from typing import TYPE_CHECKING

try:
    import pyodbc  # type: ignore
except ImportError:  # pragma: no cover - optional dependency for local tests
    pyodbc = None  # type: ignore

try:
    from azure.identity import DefaultAzureCredential
except ImportError:  # pragma: no cover - optional dependency for local tests
    DefaultAzureCredential = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover
    from pyodbc import Connection as PyodbcConnection
else:  # pragma: no cover
    PyodbcConnection = Any  # type: ignore

SQL_COPT_SS_ACCESS_TOKEN = 1256
SQL_SCOPE = "https://database.windows.net/.default"


class AzureSqlConfig:
    """Container for Azure SQL configuration options."""

    def __init__(
        self,
        *,
        server: Optional[str],
        database: Optional[str],
        username: Optional[str] = None,
        password: Optional[str] = None,
        connection_string: Optional[str] = None,
        managed_identity_client_id: Optional[str] = None,
    ) -> None:
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.connection_string = connection_string
        self.managed_identity_client_id = managed_identity_client_id


def _normalize_task(task_json: dict[str, Any]) -> dict[str, Any]:
    patient_id = task_json.get("patientId") or task_json.get("patient_id")
    if not patient_id:
        raise ValueError("taskJson.patientId is required")

    category = (task_json.get("category") or "other").lower()
    title = task_json.get("title")
    if not title:
        raise ValueError("taskJson.title is required")

    due_date = task_json.get("dueDate") or task_json.get("due_date")
    priority = (task_json.get("priority") or "normal").lower()
    source_encounter = task_json.get("sourceEncounterId") or task_json.get("source_encounter_id")
    task_id = (
        task_json.get("taskId")
        or task_json.get("task_id")
        or f"T{uuid4().hex[:10]}"
    )
    now = datetime.now(timezone.utc).isoformat()

    return {
        "task_id": task_id,
        "patient_id": patient_id,
        "category": category,
        "title": title,
        "due_date": due_date,
        "priority": priority,
        "source_encounter_id": source_encounter,
        "timestamp": now,
        "raw_json": json.dumps(task_json, default=str),
    }


class SqliteTaskStore:
    """SQLite-backed store retained for local development."""

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
        payload = _normalize_task(task_json)
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
                    payload["task_id"],
                    payload["patient_id"],
                    payload["category"],
                    payload["title"],
                    payload["due_date"],
                    payload["priority"],
                    payload["source_encounter_id"],
                    payload["timestamp"],
                    payload["timestamp"],
                ),
            )
            conn.execute(
                """
                insert into task_audit(task_id, action, actor, timestamp_utc, payload_json)
                values (?, 'upsert', 'mcp-server', ?, ?)
                """,
                (
                    payload["task_id"],
                    payload["timestamp"],
                    payload["raw_json"],
                ),
            )
            conn.commit()
        return {"taskId": payload["task_id"]}


SQL_CREATE_PATIENTS = """
if object_id(N'dbo.patients', N'U') is null begin
  create table dbo.patients (
    patient_id varchar(64) primary key,
    mrn varchar(64) unique,
    name nvarchar(200),
    dob date,
    last_encounter_id varchar(64),
    created_utc datetime2 default sysutcdatetime()
  );
end
"""

SQL_CREATE_CARE_TASKS = """
if object_id(N'dbo.care_tasks', N'U') is null begin
  create table dbo.care_tasks (
    task_id varchar(64) primary key,
    patient_id varchar(64) not null,
    category varchar(32) not null,
    title nvarchar(500) not null,
    due_date date null,
    priority varchar(16) not null,
    source_encounter_id varchar(64),
    status varchar(16) not null default 'open',
    created_utc datetime2 not null default sysutcdatetime(),
    updated_utc datetime2 not null default sysutcdatetime()
  );
end
"""

SQL_ADD_FK = """
if object_id(N'dbo.care_tasks', N'U') is not null
  and object_id(N'dbo.patients', N'U') is not null
  and not exists (
    select 1 from sys.foreign_keys where name = 'fk_care_tasks_patients'
  ) begin
  alter table dbo.care_tasks
    add constraint fk_care_tasks_patients foreign key(patient_id)
    references dbo.patients(patient_id);
end
"""

SQL_CREATE_TASK_AUDIT = """
if object_id(N'dbo.task_audit', N'U') is null begin
  create table dbo.task_audit (
    audit_id bigint identity primary key,
    task_id varchar(64) not null,
    action varchar(32) not null,
    actor varchar(128) not null,
    timestamp_utc datetime2 not null default sysutcdatetime(),
    payload_json nvarchar(max)
  );
end
"""

SQL_CREATE_TASK_INDEX = """
if object_id(N'dbo.care_tasks', N'U') is not null
  and not exists (
    select 1
    from sys.indexes
    where name = 'ix_care_tasks_patient_open'
      and object_id = object_id(N'dbo.care_tasks')
  ) begin
  create index ix_care_tasks_patient_open on dbo.care_tasks(patient_id, status);
end
"""

SQL_MERGE_TASK = """
merge dbo.care_tasks as target
using (values (?, ?, ?, ?, ?, ?, ?, ?)) as source(
  task_id, patient_id, category, title, due_date, priority, source_encounter_id, updated_utc
)
on target.task_id = source.task_id
when matched then
  update set
    patient_id = source.patient_id,
    category = source.category,
    title = source.title,
    due_date = source.due_date,
    priority = source.priority,
    source_encounter_id = source.source_encounter_id,
    updated_utc = source.updated_utc
when not matched then
  insert (task_id, patient_id, category, title, due_date, priority, source_encounter_id, status, created_utc, updated_utc)
  values (source.task_id, source.patient_id, source.category, source.title, source.due_date, source.priority, source.source_encounter_id, 'open', source.updated_utc, source.updated_utc);
"""

SQL_INSERT_AUDIT = """
insert into dbo.task_audit(task_id, action, actor, timestamp_utc, payload_json)
values (?, 'upsert', 'mcp-server', ?, ?);
"""


class AzureSqlTaskStore:
    """Azure SQL-backed store using pyodbc with Managed Identity or SQL auth."""

    def __init__(self, config: AzureSqlConfig) -> None:
        if not config.connection_string and (not config.server or not config.database):
            raise ValueError("AzureSqlTaskStore requires server and database when connection_string is not provided")
        if pyodbc is None:
            raise ImportError("pyodbc is required for Azure SQL mode")
        if DefaultAzureCredential is None:
            raise ImportError("azure-identity is required for Azure SQL mode")
        self._config = config
        self._lock = Lock()
        self._credential: DefaultAzureCredential | None = None
        ensure_schema = os.environ.get("TASK_DB_INIT_SCHEMA", "true").lower() != "false"
        if ensure_schema:
            self._ensure_schema()

    def _ensure_schema(self) -> None:
        statements = [
            SQL_CREATE_PATIENTS,
            SQL_CREATE_CARE_TASKS,
            SQL_CREATE_TASK_AUDIT,
            SQL_ADD_FK,
            SQL_CREATE_TASK_INDEX,
        ]
        with self._connect() as conn:
            cursor = conn.cursor()
            for statement in statements:
                cursor.execute(statement)
            conn.commit()

    def _build_connection_string(self) -> str:
        if self._config.connection_string:
            return self._config.connection_string

        parts = [
            "Driver={ODBC Driver 18 for SQL Server};",
            f"Server=tcp:{self._config.server},1433;",
            f"Database={self._config.database};",
            "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;",
        ]
        if self._config.username and self._config.password:
            parts.append(f"Uid={self._config.username};")
            parts.append(f"Pwd={self._config.password};")
        return "".join(parts)

    def _get_token_bytes(self) -> bytes:
        credential = self._get_credential()
        token = credential.get_token(SQL_SCOPE)
        return token.token.encode("utf-16-le")

    def _get_credential(self) -> DefaultAzureCredential:
        if self._credential is None:
            self._credential = DefaultAzureCredential(
                managed_identity_client_id=self._config.managed_identity_client_id,
                exclude_interactive_browser_credential=True,
            )
        return self._credential

    def _connect(self) -> PyodbcConnection:
        connection_string = self._build_connection_string()
        kwargs: dict[str, Any] = {}
        if not (self._config.username and self._config.password):
            kwargs["attrs_before"] = {SQL_COPT_SS_ACCESS_TOKEN: self._get_token_bytes()}
        conn = pyodbc.connect(connection_string, **kwargs)
        conn.autocommit = False
        return conn

    def upsert(self, task_json: dict[str, Any]) -> dict[str, str]:
        payload = _normalize_task(task_json)
        with self._lock, self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                SQL_MERGE_TASK,
                (
                    payload["task_id"],
                    payload["patient_id"],
                    payload["category"],
                    payload["title"],
                    payload["due_date"],
                    payload["priority"],
                    payload["source_encounter_id"],
                    payload["timestamp"],
                ),
            )
            cursor.execute(
                SQL_INSERT_AUDIT,
                (
                    payload["task_id"],
                    payload["timestamp"],
                    payload["raw_json"],
                ),
            )
            conn.commit()
        return {"taskId": payload["task_id"]}


def create_task_store(
    *,
    mode: str | None = None,
    sqlite_path: str | Path,
    sql_server: str | None = None,
    sql_database: str | None = None,
    sql_username: str | None = None,
    sql_password: str | None = None,
    sql_connection_string: str | None = None,
    managed_identity_client_id: str | None = None,
) -> SqliteTaskStore | AzureSqlTaskStore:
    resolved_mode = (mode or "sqlite").lower()
    if resolved_mode in {"sqlite", "local"}:
        return SqliteTaskStore(sqlite_path)
    if resolved_mode in {"azure-sql", "sql", "mssql"}:
        config = AzureSqlConfig(
            server=sql_server,
            database=sql_database,
            username=sql_username,
            password=sql_password,
            connection_string=sql_connection_string,
            managed_identity_client_id=managed_identity_client_id,
        )
        return AzureSqlTaskStore(config)
    raise ValueError(f"Unsupported TASK_DB_MODE: {resolved_mode}")


# Backwards compatibility for tests importing TaskStore directly.
TaskStore = SqliteTaskStore


__all__ = [
    "SqliteTaskStore",
    "AzureSqlTaskStore",
    "AzureSqlConfig",
    "create_task_store",
    "TaskStore",
]
