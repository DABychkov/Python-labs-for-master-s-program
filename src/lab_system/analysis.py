"""Контракты и модели синхронного анализа сдач."""

from dataclasses import dataclass
from typing import Protocol

from .models import Submission


@dataclass(frozen=True)
class Assignment:
    assignment_id: str
    title: str
    allowed_templates: tuple[str, ...] = ()


@dataclass(frozen=True)
class Evidence:
    source: str
    line_start: int
    line_end: int
    explanation: str

    def as_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "explanation": self.explanation,
        }


@dataclass(frozen=True)
class AnalysisReport:
    analyzer_id: str
    analyzer_version: str
    score: float | None
    similarity: float | None
    rubric_feedback: tuple[str, ...]
    evidence: tuple[Evidence, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "analyzer_id": self.analyzer_id,
            "analyzer_version": self.analyzer_version,
            "score": self.score,
            "similarity": self.similarity,
            "rubric_feedback": list(self.rubric_feedback),
            "evidence": [item.as_dict() for item in self.evidence],
        }


class AnalysisContext(Protocol):
    def get_assignment(self, assignment_id: str) -> Assignment: ...


class Analyzer(Protocol):
    analyzer_id: str
    analyzer_version: str

    def analyze(
        self, submission: Submission, context: AnalysisContext
    ) -> AnalysisReport: ...
