"""Доменный пакет системы приёма лабораторных работ"""

from .errors import ConflictError, IntakeError, ParseError, ValidationError
from .models import AiDeclaration, Submission
from .analysis import AnalysisContext, AnalysisReport, Assignment, Evidence
from .analysis_service import AnalysisService
from .registry import AnalyzerRegistry
from .service import AcceptanceResult, IntakeService

__all__ = [
    "AcceptanceResult",
    "AnalysisContext",
    "AnalysisReport",
    "AnalysisService",
    "AiDeclaration",
    "AnalyzerRegistry",
    "Assignment",
    "ConflictError",
    "IntakeError",
    "IntakeService",
    "ParseError",
    "Submission",
    "ValidationError",
    "Evidence",
]
