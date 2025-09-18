import sqlite3
import unittest
from importlib import util
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TASK_STORE_MODULE = BASE_DIR / "services" / "mcp-server" / "task_store.py"

spec = util.spec_from_file_location("task_store", TASK_STORE_MODULE)
assert spec and spec.loader
module = util.module_from_spec(spec)
spec.loader.exec_module(module)
TaskStore = module.TaskStore
create_task_store = module.create_task_store


class TaskStoreTests(unittest.TestCase):
    def test_upsert_creates_and_updates(self) -> None:
        tmp_dir = Path(self._get_tempdir())
        db_path = tmp_dir / "tasks.db"
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
        self.assertIn("taskId", result)

        payload_update = dict(payload)
        payload_update["taskId"] = result["taskId"]
        payload_update["title"] = "BMP in 2 days"

        second = store.upsert(payload_update)
        self.assertEqual(second["taskId"], result["taskId"])

        with sqlite3.connect(db_path) as conn:
            row = conn.execute(
                "select title, priority from care_tasks where task_id = ?",
                (result["taskId"],),
            ).fetchone()
        self.assertEqual(row, ("BMP in 2 days", "normal"))

    def _get_tempdir(self) -> str:
        from tempfile import TemporaryDirectory

        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return tmp.name

    def test_create_task_store_requires_sql_coordinates(self) -> None:
        with self.assertRaises(ValueError):
            create_task_store(
                mode="azure-sql",
                sqlite_path="/tmp/placeholder.db",
                sql_database="caretasks",
            )


if __name__ == "__main__":
    unittest.main()
