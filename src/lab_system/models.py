"""Неизменяемые доменные модели сдач"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class AiDeclaration:
    used: bool
    description: str

    def as_dict(self) -> dict[str, Any]:
        return {"used": self.used, "description": self.description}


@dataclass(frozen=True)
class Submission:
    submission_id: str
    assignment_id: str
    student_id: str
    submitted_at: datetime
    text: str
    code: str
    ai_declaration: AiDeclaration
    content_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "submission_id": self.submission_id,
            "assignment_id": self.assignment_id,
            "student_id": self.student_id,
            "submitted_at": self.submitted_at.isoformat(),
            "text": self.text,
            "code": self.code,
            "ai_declaration": self.ai_declaration.as_dict(),
        }
