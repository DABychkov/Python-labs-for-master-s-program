import copy
import pytest

from lab_system.errors import ConflictError, ValidationError
from lab_system.parser import parse_submission, parse_submission_line
from lab_system.service import IntakeService
from lab_system.errors import ParseError


def payload(**changes):
    result = {
        "submission_id": "sub-1",
        "assignment_id": "lab-1",
        "student_id": "student-1",
        "submitted_at": "2026-11-12T12:00:00+03:00",
        "text": "Solution",
        "code": "print('ok')\n",
        "ai_declaration": {"used": False, "description": ""},
    }
    result.update(changes)
    return result


def test_valid_submission_is_accepted_and_input_is_unchanged():
    raw = payload()
    before = copy.deepcopy(raw)
    submission = parse_submission(raw)
    result = IntakeService().accept(submission)
    assert result.status == "accepted"
    assert raw == before
    assert submission.submitted_at.tzinfo is not None


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("student_id", 123, "invalid_type"),
        ("submitted_at", "2026-11-12T12:00:00", "timezone_required"),
        ("student_id", "", "empty_value"),
        ("unexpected", "value", "unknown_field"),
    ],
)
def test_invalid_schema_has_explainable_issue(field, value, code):
    with pytest.raises(ValidationError) as error:
        parse_submission(payload(**{field: value}))
    assert error.value.issue.code == code
    assert error.value.issue.field


def test_duplicate_is_idempotent_and_conflict_does_not_replace():
    service = IntakeService()
    first = parse_submission(payload())
    assert service.accept(first).status == "accepted"
    assert service.accept(parse_submission(payload())).status == "duplicate"
    changed = parse_submission(payload(code="print('changed')\n"))
    with pytest.raises(ConflictError) as error:
        service.accept(changed)
    assert error.value.issue.code == "submission_id_conflict"
    assert service.count() == 1


def test_conflict_preserves_original_content():
    service = IntakeService()
    first = parse_submission(payload(code="print('ok')\n"))
    service.accept(first)
    changed = parse_submission(payload(code="print('changed')\n"))
    with pytest.raises(ConflictError):
        service.accept(changed)
    assert service._repository.get("sub-1").code == "print('ok')\n"


def test_broken_json_is_reported_as_parse_error():
    with pytest.raises(ParseError) as error:
        parse_submission_line("{broken")
    assert error.value.issue.code == "invalid_json"


@pytest.mark.parametrize(
    ("declaration", "code", "field"),
    [
        ("not-an-object", "invalid_type", "ai_declaration"),
        ({"used": False, "description": "", "extra": "x"}, "unknown_field", "ai_declaration.extra"),
        ({"used": "true", "description": ""}, "invalid_type", "ai_declaration.used"),
        ({"used": False, "description": 123}, "invalid_type", "ai_declaration.description"),
        ({"used": True, "description": "   "}, "ai_declaration_required", "ai_declaration.description"),
    ],
)
def test_invalid_ai_declaration_has_explainable_issue(declaration, code, field):
    with pytest.raises(ValidationError) as error:
        parse_submission(payload(ai_declaration=declaration))
    assert error.value.issue.code == code
    assert error.value.issue.field == field
