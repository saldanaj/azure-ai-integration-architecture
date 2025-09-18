"""Golden tests for the structured follow-up extraction prompt."""

from __future__ import annotations

import json
import re
import textwrap
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLES_DIR = BASE_DIR / "ai" / "samples"

VALID_CATEGORIES = {"lab", "med", "visit", "other"}
VALID_PRIORITIES = {"low", "normal", "high"}
VALID_KEYS = {"category", "title", "priority", "dueDate"}
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_sample(name: str) -> tuple[str, dict]:
    note_path = SAMPLES_DIR / f"{name}.txt"
    expected_path = SAMPLES_DIR / f"{name}.expected.json"
    with note_path.open("r", encoding="utf-8") as note_file:
        note_text = note_file.read().strip()
    with expected_path.open("r", encoding="utf-8") as expected_file:
        payload = json.load(expected_file)
    return note_text, payload


def _format_errors(errors: list[str]) -> str:
    prefix = "schema validation failed:\n"
    return prefix + "\n".join(textwrap.indent(err, "- ") for err in errors)


def _validate_payload(payload: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return [f"payload must be an object, got {type(payload).__name__}"]

    followups = payload.get("followUps")
    if not isinstance(followups, list):
        errors.append("followUps must be a list")
        return errors

    if not followups:
        errors.append("followUps list cannot be empty")
        return errors

    for idx, item in enumerate(followups):
        if not isinstance(item, dict):
            errors.append(f"followUps[{idx}] must be an object")
            continue

        extra_keys = set(item) - VALID_KEYS
        missing_keys = VALID_KEYS - set(item)
        if missing_keys:
            errors.append(f"followUps[{idx}] missing keys: {sorted(missing_keys)}")
        if extra_keys:
            errors.append(f"followUps[{idx}] has unexpected keys: {sorted(extra_keys)}")

        category = item.get("category")
        if category not in VALID_CATEGORIES:
            errors.append(f"followUps[{idx}].category invalid: {category!r}")

        title = item.get("title")
        if not isinstance(title, str) or len(title.strip()) < 5:
            errors.append(f"followUps[{idx}].title must be >=5 chars")

        priority = item.get("priority")
        if priority not in VALID_PRIORITIES:
            errors.append(f"followUps[{idx}].priority invalid: {priority!r}")

        due_date = item.get("dueDate")
        if due_date is not None:
            if not isinstance(due_date, str) or not DATE_PATTERN.match(due_date):
                errors.append(f"followUps[{idx}].dueDate invalid: {due_date!r}")

    return errors


class GoldenExtractionTests(unittest.TestCase):
    def test_note1_schema(self) -> None:
        note_text, payload = load_sample("note1")
        self.assertTrue(note_text, "fixture note text is empty")

        errors = _validate_payload(payload)
        if errors:
            self.fail(_format_errors(errors))


if __name__ == "__main__":
    unittest.main()
