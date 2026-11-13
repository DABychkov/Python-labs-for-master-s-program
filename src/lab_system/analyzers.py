"""Базовые заменяемые анализаторы этапа Б."""

from .analysis import AnalysisContext, AnalysisReport, Evidence
from .models import Submission


class LengthAnalyzer:
    analyzer_id = "length"
    analyzer_version = "1.0"

    def analyze(
        self, submission: Submission, context: AnalysisContext
    ) -> AnalysisReport:
        del context
        text_lines = _non_empty_lines(submission.text)
        code_lines = _non_empty_lines(submission.code)
        return AnalysisReport(
            analyzer_id=self.analyzer_id,
            analyzer_version=self.analyzer_version,
            score=None,
            similarity=None,
            rubric_feedback=(
                f"Непустых строк в тексте: {len(text_lines)}.",
                f"Непустых строк в коде: {len(code_lines)}.",
            ),
            evidence=tuple(
                evidence
                for evidence in (
                    _whole_content_evidence("text", text_lines, "Непустые строки текста."),
                    _whole_content_evidence("code", code_lines, "Непустые строки кода."),
                )
                if evidence is not None
            ),
        )


class TemplateAnalyzer:
    analyzer_id = "template"
    analyzer_version = "1.0"

    def analyze(
        self, submission: Submission, context: AnalysisContext
    ) -> AnalysisReport:
        assignment = context.get_assignment(submission.assignment_id)
        allowed = set(assignment.allowed_templates)
        evidence: list[Evidence] = []
        for line_number, line in enumerate(submission.code.splitlines(), start=1):
            if line in allowed:
                evidence.append(
                    Evidence(
                        source="code",
                        line_start=line_number,
                        line_end=line_number,
                        explanation="Точная строка совпадает с разрешённым шаблоном.",
                    )
                )
        similarity = 1.0 if evidence else 0.0
        feedback = (
            "Найдено разрешённое совпадение с шаблоном."
            if evidence
            else "Совпадений с разрешённым шаблоном не найдено."
        )
        return AnalysisReport(
            analyzer_id=self.analyzer_id,
            analyzer_version=self.analyzer_version,
            score=None,
            similarity=similarity,
            rubric_feedback=(feedback,),
            evidence=tuple(evidence),
        )


def _non_empty_lines(content: str) -> list[int]:
    return [
        line_number
        for line_number, line in enumerate(content.splitlines(), start=1)
        if line.strip()
    ]


def _whole_content_evidence(
    source: str, line_numbers: list[int], explanation: str
) -> Evidence | None:
    if not line_numbers:
        return None
    return Evidence(
        source=source,
        line_start=line_numbers[0],
        line_end=line_numbers[-1],
        explanation=explanation,
    )
