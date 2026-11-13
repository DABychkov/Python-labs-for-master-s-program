import json
from pathlib import Path

import pytest

from lab_system.analysis import AnalysisReport, Assignment
from lab_system.analysis_service import AnalysisService
from lab_system.analyzers import LengthAnalyzer, TemplateAnalyzer
from lab_system.errors import ParseError, ValidationError
from lab_system.parser import parse_submission
from lab_system.registry import default_registry
from lab_system.sources import (
    InMemoryAnalysisContext,
    InMemorySubmissionSource,
    JsonlSubmissionSource,
)


def submission(code="print(1)\n\nvalue = 2\n"):
    return parse_submission(
        {
            "submission_id": "sub-1",
            "assignment_id": "lab-1",
            "student_id": "student-1",
            "submitted_at": "2026-11-12T12:00:00+03:00",
            "text": "first\n\nsecond",
            "code": code,
            "ai_declaration": {"used": False, "description": ""},
        }
    )


def context():
    return InMemoryAnalysisContext(
        [Assignment("lab-1", "Lab 1", ("print(1)", "print(2)"))]
    )


@pytest.mark.parametrize(("analyzer", "expected_id", "expected_version"), [
    (LengthAnalyzer(), "length", "1.0"),
    (TemplateAnalyzer(), "template", "1.0"),
])
def test_analyzer_identity(analyzer, expected_id, expected_version):
    report = analyzer.analyze(submission(), context())
    assert report.analyzer_id == expected_id
    assert report.analyzer_version == expected_version


def test_length_analyzer_uses_non_empty_lines_and_no_score():
    report = LengthAnalyzer().analyze(submission(), context())
    assert report.score is None
    assert report.similarity is None
    assert report.rubric_feedback == (
        "Непустых строк в тексте: 2.",
        "Непустых строк в коде: 2.",
    )
    assert report.evidence[0].line_start == 1
    assert report.evidence[0].line_end == 3


def test_template_analyzer_reports_allowed_exact_lines_only():
    report = TemplateAnalyzer().analyze(submission(), context())
    assert report.similarity == 1.0
    assert len(report.evidence) == 1
    assert report.evidence[0].line_start == 1
    assert report.evidence[0].line_end == 1
    assert "разрешённое" in report.rubric_feedback[0]


def test_template_analyzer_returns_zero_without_match():
    report = TemplateAnalyzer().analyze(submission("value = 2\n"), context())
    assert report.similarity == 0.0
    assert report.evidence == ()
    assert "не найдено" in report.rubric_feedback[0]


def test_registry_and_service_allow_new_analyzer_without_service_branching():
    registry = default_registry()
    assert registry.ids() == ("length", "template")
    report = AnalysisService(registry).analyze(submission(), "length", context())
    assert report.analyzer_id == "length"


def test_both_submission_sources_share_the_same_contract(tmp_path: Path):
    item = submission()
    jsonl = tmp_path / "submissions.jsonl"
    jsonl.write_text(json.dumps(item.as_dict()) + "\n", encoding="utf-8")
    memory_source = InMemorySubmissionSource([item])
    with JsonlSubmissionSource(jsonl) as source:
        for current_source in (memory_source, source):
            received = list(current_source.submissions())
            assert received == [item]
            assert LengthAnalyzer().analyze(received[0], context()).analyzer_id == "length"
            assert TemplateAnalyzer().analyze(received[0], context()).analyzer_id == "template"


def test_jsonl_source_closes_file_on_early_stop(tmp_path: Path):
    jsonl = tmp_path / "submissions.jsonl"
    item = submission().as_dict()
    jsonl.write_text(json.dumps(item) + "\n" + json.dumps(item) + "\n", encoding="utf-8")
    source = JsonlSubmissionSource(jsonl)
    with source:
        iterator = source.submissions()
        next(iterator)
    assert source._file is None


def test_unknown_assignment_is_explicit():
    with pytest.raises(ValidationError) as error:
        TemplateAnalyzer().analyze(
            submission(), InMemoryAnalysisContext([])
        )
    assert error.value.issue.code == "unknown_assignment"
    assert error.value.issue.field == "assignment_id"


class _ThirdAnalyzer:
    analyzer_id = "ai_declaration"
    analyzer_version = "1.0"

    def analyze(self, submission, context):
        del submission, context
        return AnalysisReport(
            analyzer_id=self.analyzer_id,
            analyzer_version=self.analyzer_version,
            score=None,
            similarity=None,
            rubric_feedback=("third analyzer stub",),
            evidence=(),
        )


def test_third_analyzer_registered_without_service_change():
    registry = default_registry()
    registry.register("ai_declaration", _ThirdAnalyzer)
    assert "ai_declaration" in registry.ids()
    service = AnalysisService(registry)
    report = service.analyze(submission(), "ai_declaration", context())
    assert report.analyzer_id == "ai_declaration"


class _BrokenAnalyzer:
    analyzer_id = "broken"
    analyzer_version = "1.0"

    def analyze(self, submission, context):
        del submission, context
        raise RuntimeError("boom")


def test_analyzer_error_propagates():
    from lab_system.registry import AnalyzerRegistry

    registry = AnalyzerRegistry({"broken": _BrokenAnalyzer})
    service = AnalysisService(registry)
    with pytest.raises(RuntimeError, match="boom"):
        service.analyze(submission(), "broken", context())


def test_jsonl_source_closes_file_on_error(tmp_path: Path):
    jsonl = tmp_path / "bad.jsonl"
    jsonl.write_text("{bad json\n", encoding="utf-8")
    source = JsonlSubmissionSource(jsonl)
    with pytest.raises(ParseError):
        with source:
            list(source.submissions())
    assert source._file is None


def test_jsonl_source_reports_line_number_on_bad_json(tmp_path: Path):
    jsonl = tmp_path / "mixed.jsonl"
    good = submission().as_dict()
    jsonl.write_text(
        json.dumps(good) + "\n" + "{bad json\n",
        encoding="utf-8",
    )
    with JsonlSubmissionSource(jsonl) as source:
        with pytest.raises(ParseError) as error:
            list(source.submissions())
    assert error.value.issue.code == "invalid_json"
    assert "line 2" in error.value.issue.message


def test_create_unknown_analyzer_raises():
    registry = default_registry()
    with pytest.raises(KeyError, match="unknown analyzer"):
        registry.create("nope")


def test_register_duplicate_raises():
    registry = default_registry()
    with pytest.raises(ValueError, match="already registered"):
        registry.register("length", object)