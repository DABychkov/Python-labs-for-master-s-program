"""Разбор и валидация схемы внешних полезных нагрузок со сдачами"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from .errors import IntakeIssue, ParseError, ValidationError
from .models import AiDeclaration, Submission

_FIELDS = {
    "submission_id",
    "assignment_id",
    "student_id",
    "submitted_at",
    "text",
    "code",
    "ai_declaration",
}
_AI_FIELDS = {"used", "description"}
_IDENTIFIER_FIELDS = {"submission_id", "assignment_id", "student_id"}


def parse_submission_line(line: str) -> Submission:
    """Parse one JSONL line into a validated immutable submission."""
    try:
        payload = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ParseError(
            IntakeIssue("invalid_json", None, f"invalid JSON: {exc.msg}")
        ) from exc
    if not isinstance(payload, dict):
        raise ParseError(
            IntakeIssue("invalid_format", None, "submission must be a JSON object")
        )
    return parse_submission(payload)


def parse_submission(payload: dict[str, Any]) -> Submission:
    unknown = sorted(set(payload) - _FIELDS)
    if unknown:
        raise ValidationError(
            IntakeIssue(
                "unknown_field",
                unknown[0],
                f"unknown field: {unknown[0]}",
            )
        )
    missing = sorted(_FIELDS - set(payload))
    if missing:
        raise ValidationError(
            IntakeIssue("missing_field", missing[0], f"required field is missing: {missing[0]}")
        )

    values: dict[str, str] = {}
    for field in _IDENTIFIER_FIELDS | {"text", "code"}:
        value = payload[field]
        if not isinstance(value, str):
            raise ValidationError(
                IntakeIssue("invalid_type", field, f"{field} must be a string")
            )
        if field in _IDENTIFIER_FIELDS and not value.strip():
            raise ValidationError(
                IntakeIssue("empty_value", field, f"{field} must not be empty")
            )
        values[field] = value

    submitted_at = _parse_timestamp(payload["submitted_at"])
    declaration = _parse_ai_declaration(payload["ai_declaration"])
    canonical = {
        **values,
        "submitted_at": submitted_at.isoformat(),
        "ai_declaration": declaration.as_dict(),
    }
    content_hash = hashlib.sha256(
        json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    return Submission(
        **values,
        submitted_at=submitted_at,
        ai_declaration=declaration,
        content_hash=content_hash,
    )


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValidationError(
            IntakeIssue("invalid_type", "submitted_at", "submitted_at must be an ISO-8601 string")
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(
            IntakeIssue("invalid_timestamp", "submitted_at", "submitted_at must be a valid ISO-8601 timestamp")
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValidationError(
            IntakeIssue("timezone_required", "submitted_at", "submitted_at must include a timezone")
        )
    return parsed


def _parse_ai_declaration(value: Any) -> AiDeclaration:
    if not isinstance(value, dict):
        raise ValidationError(
            IntakeIssue("invalid_type", "ai_declaration", "ai_declaration must be an object")
        )
    unknown = sorted(set(value) - _AI_FIELDS)
    if unknown:
        raise ValidationError(
            IntakeIssue("unknown_field", f"ai_declaration.{unknown[0]}", f"unknown field: {unknown[0]}")
        )
    if "used" not in value or "description" not in value:
        missing = "used" if "used" not in value else "description"
        raise ValidationError(
            IntakeIssue("missing_field", f"ai_declaration.{missing}", f"required field is missing: {missing}")
        )
    if not isinstance(value["used"], bool):
        raise ValidationError(
            IntakeIssue("invalid_type", "ai_declaration.used", "used must be a boolean")
        )
    if not isinstance(value["description"], str):
        raise ValidationError(
            IntakeIssue("invalid_type", "ai_declaration.description", "description must be a string")
        )
    if value["used"] and not value["description"].strip():
        raise ValidationError(
            IntakeIssue(
                "ai_declaration_required",
                "ai_declaration.description",
                "description must not be empty when used is true",
            )
        )
    return AiDeclaration(used=value["used"], description=value["description"])
