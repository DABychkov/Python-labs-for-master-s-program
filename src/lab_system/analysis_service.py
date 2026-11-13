"""Центральная точка запуска анализатора через реестр."""

from .analysis import AnalysisContext, AnalysisReport
from .models import Submission
from .registry import AnalyzerRegistry, default_registry


class AnalysisService:
    def __init__(self, registry: AnalyzerRegistry | None = None) -> None:
        self._registry = registry or default_registry()

    def analyze(
        self,
        submission: Submission,
        analyzer_id: str,
        context: AnalysisContext,
    ) -> AnalysisReport:
        analyzer = self._registry.create(analyzer_id)
        return analyzer.analyze(submission, context)
