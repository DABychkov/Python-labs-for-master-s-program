"""Источники сдач и контекст анализа."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator, Protocol

from .analysis import Assignment
from .errors import IntakeIssue, ParseError, ValidationError
from .models import Submission
from .parser import parse_submission


class SubmissionSource(Protocol):
    def submissions(self) -> Iterator[Submission]: ...


class InMemorySubmissionSource:
    def __init__(self, submissions: list[Submission] | tuple[Submission, ...]) -> None:
        self._submissions = tuple(submissions)

    def submissions(self) -> Iterator[Submission]:
        yield from self._submissions


class JsonlSubmissionSource:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._file = None

    def __enter__(self) -> JsonlSubmissionSource:
        self._file = self._path.open("r", encoding="utf-8-sig")
        return self

    def __exit__(self, *args: object) -> None:
        del args
        if self._file is not None:
            self._file.close()
            self._file = None

    def submissions(self) -> Iterator[Submission]:
        if self._file is None:
            raise RuntimeError("JsonlSubmissionSource must be used as a context manager")
        for line_number, line in enumerate(self._file, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as error:
                raise ParseError(
                    IntakeIssue(
                        "invalid_json",
                        None,
                        f"line {line_number}: invalid JSON: {error.msg}",
                    )
                ) from error
            if not isinstance(payload, dict):
                raise ParseError(
                    IntakeIssue(
                        "invalid_format",
                        None,
                        f"line {line_number}: submission must be a JSON object",
                    )
                )
            try:
                yield parse_submission(payload)
            except ValidationError as error:
                issue = error.issue
                raise ValidationError(
                    IntakeIssue(
                        issue.code,
                        issue.field,
                        f"line {line_number}: {issue.message}",
                    )
                ) from error


class InMemoryAnalysisContext:
    def __init__(self, assignments: list[Assignment] | tuple[Assignment, ...]) -> None:
        self._assignments = {assignment.assignment_id: assignment for assignment in assignments}

    def get_assignment(self, assignment_id: str) -> Assignment:
        try:
            return self._assignments[assignment_id]
        except KeyError as error:
            raise ValidationError(
                IntakeIssue(
                    "unknown_assignment",
                    "assignment_id",
                    f"assignment not found: {assignment_id}",
                )
            ) from error
