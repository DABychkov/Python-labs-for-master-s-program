"""Сервис приложения для приёма провалидированных сдач"""

from dataclasses import dataclass

from .errors import ConflictError, IntakeIssue
from .models import Submission
from .repository import InMemorySubmissionRepository, SubmissionRepository


@dataclass(frozen=True)
class AcceptanceResult:
    status: str
    submission: Submission | None = None
    issue: IntakeIssue | None = None

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {"status": self.status}
        if self.submission is not None:
            result["submission_id"] = self.submission.submission_id
            result["content_hash"] = self.submission.content_hash
        if self.issue is not None:
            result["error"] = self.issue.as_dict()
        return result


class IntakeService:
    def __init__(self, repository: SubmissionRepository | None = None) -> None:
        self._repository = repository or InMemorySubmissionRepository()

    def accept(self, submission: Submission) -> AcceptanceResult:
        existing = self._repository.get(submission.submission_id)
        if existing is not None:
            if existing.content_hash == submission.content_hash:
                return AcceptanceResult("duplicate", existing)
            issue = IntakeIssue(
                "submission_id_conflict",
                "submission_id",
                "submission_id already belongs to different content",
            )
            raise ConflictError(issue)
        self._repository.save(submission)
        return AcceptanceResult("accepted", submission)

    def count(self) -> int:
        return self._repository.count()
