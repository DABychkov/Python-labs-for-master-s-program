import json

from lab_system.cli import import_jsonl
from lab_system.service import IntakeService


def test_import_continues_after_corrupt_line(tmp_path):
    path = tmp_path / "submissions.jsonl"
    valid = {
        "submission_id": "sub-1",
        "assignment_id": "lab-1",
        "student_id": "student-1",
        "submitted_at": "2026-11-12T12:00:00Z",
        "text": "text",
        "code": "code",
        "ai_declaration": {"used": False, "description": ""},
    }
    path.write_text(json.dumps(valid) + "\n{bad json\n" + json.dumps(valid) + "\n", encoding="utf-8")
    report = import_jsonl(path, IntakeService())
    assert report["accepted"] == 1
    assert report["duplicate"] == 1
    assert report["errors"] == [
        {
            "line": 2,
            "code": "invalid_json",
            "field": None,
            "message": "invalid JSON: Expecting property name enclosed in double quotes",
        }
    ]
