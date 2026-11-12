"""Ошибки, которые отдаёт граница приёма сдач"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IntakeIssue:
    code: str
    field: str | None
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "field": self.field, "message": self.message}


class IntakeError(Exception):
    """Base class for expected intake failures."""

    def __init__(self, issue: IntakeIssue) -> None:
        super().__init__(issue.message)
        self.issue = issue



#Неправильный формат(или поврежденный JSON)
class ParseError(IntakeError):
    """The input is not a JSON object or is not valid JSON."""


#Нарушение схемы
class ValidationError(IntakeError):
    """The JSON object does not satisfy the submission schema."""


#Конфликт идентификатора
class ConflictError(IntakeError):
    """The identifier is already used by different content."""
