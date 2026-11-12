"""Порты хранилища и in-memory реализация"""

from typing import Protocol

from .models import Submission


class SubmissionRepository(Protocol):
    def get(self, submission_id: str) -> Submission | None: ...

    def save(self, submission: Submission) -> None: ...

    def count(self) -> int: ...


class InMemorySubmissionRepository:
    def __init__(self) -> None:
        self._submissions: dict[str, Submission] = {}

    def get(self, submission_id: str) -> Submission | None:
        return self._submissions.get(submission_id)

    def save(self, submission: Submission) -> None:
        self._submissions[submission.submission_id] = submission

    def count(self) -> int:
        return len(self._submissions)
