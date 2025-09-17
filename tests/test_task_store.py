from importlib import util
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
TASK_STORE_MODULE = BASE_DIR / "services" / "mcp-server" / "task_store.py"

spec = util.spec_from_file_location("task_store", TASK_STORE_MODULE)
assert spec and spec.loader
module = util.module_from_spec(spec)
spec.loader.exec_module(module)
TaskStore = module.TaskStore


def test_upsert_creates_and_updates(tmp_path: Path):
    db_path = tmp_path / "tasks.db"
    store = TaskStore(db_path)

    payload = {
        "patientId": "P123",
        "category": "lab",
        "title": "BMP in 3 days",
        "dueDate": "2024-02-15",
        "priority": "normal",
        "sourceEncounterId": "E456",
    }

    result = store.upsert(payload)
    assert "taskId" in result

    payload_update = dict(payload)
    payload_update["taskId"] = result["taskId"]
    payload_update["title"] = "BMP in 2 days"

    second = store.upsert(payload_update)
    assert second["taskId"] == result["taskId"]

    import sqlite3

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "select title, priority from care_tasks where task_id = ?", (result["taskId"],)
        ).fetchone()
    assert row == ("BMP in 2 days", "normal")


if __name__ == "__main__":
    pytest.main([__file__])
