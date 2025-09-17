import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLES_DIR = BASE_DIR / "ai" / "samples"

FOLLOWUPS_SCHEMA = {
    "type": "object",
    "required": ["followUps"],
    "properties": {
        "followUps": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["category", "title", "dueDate", "priority"],
                "properties": {
                    "category": {"type": "string", "enum": ["lab", "med", "visit", "other"]},
                    "title": {"type": "string", "minLength": 5},
                    "dueDate": {"type": ["string", "null"]},
                    "priority": {"type": "string", "enum": ["low", "normal", "high"]},
                },
                "additionalProperties": True,
            },
        }
    },
    "additionalProperties": True,
}

validator = Draft7Validator(FOLLOWUPS_SCHEMA)


def load_sample(name: str) -> tuple[str, dict]:
    note_path = SAMPLES_DIR / f"{name}.txt"
    expected_path = SAMPLES_DIR / f"{name}.expected.json"
    assert note_path.exists(), f"missing note fixture: {note_path}"
    assert expected_path.exists(), f"missing expected fixture: {expected_path}"
    with note_path.open("r", encoding="utf-8") as note_file:
        note_text = note_file.read().strip()
    with expected_path.open("r", encoding="utf-8") as expected_file:
        payload = json.load(expected_file)
    return note_text, payload


def assert_schema(payload: dict) -> None:
    errors = sorted(validator.iter_errors(payload), key=lambda err: err.path)
    if not errors:
        return
    lines = []
    for err in errors:
        path = ".".join(str(p) for p in err.path) or "<root>"
        lines.append(f"{path}: {err.message}")
    formatted = "\n".join(lines)
    pytest.fail(f"followUps schema validation failed:\n{formatted}")


@pytest.mark.parametrize("sample", ["note1"])
def test_expected_followups_match_schema(sample: str):
    note_text, payload = load_sample(sample)
    assert note_text, "fixture note text is empty"
    assert_schema(payload)
