"""Потоковый baseline сходства сдач для лабораторной работы 2."""

from __future__ import annotations

import ast
import io
import tokenize
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from token import (
    NAME,
    NUMBER,
    OP,
    STRING,
)

from .analysis import Assignment, Evidence
from .models import Submission

TOKEN_ANALYZER_VERSION = "1.0"
AST_ANALYZER_VERSION = "1.0"


@dataclass(frozen=True)
class CodeFeatures:

    token_trigrams: frozenset[tuple[str, str, str]]
    template_lines: tuple[int, ...]
    token_error: str | None = None


@dataclass(frozen=True)
class AstFeatures:

    structure: tuple[object, ...] | None
    syntax_error: str | None = None


@dataclass(frozen=True)
class SimilarityResult:

    left_submission_id: str
    right_submission_id: str
    assignment_id: str
    method: str
    score: float | None
    status: str
    template_only: bool
    same_student: bool
    evidence: tuple[Evidence, ...]
    error: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "left_submission_id": self.left_submission_id,
            "right_submission_id": self.right_submission_id,
            "assignment_id": self.assignment_id,
            "method": self.method,
            "score": self.score,
            "status": self.status,
            "template_only": self.template_only,
            "same_student": self.same_student,
            "evidence": [item.as_dict() for item in self.evidence],
            "error": self.error,
        }


def extract_code_features(
    code: str, allowed_templates: Iterable[str] = ()
) -> CodeFeatures:
    template_set = set(allowed_templates)
    template_lines = tuple(
        line_number
        for line_number, line in enumerate(code.splitlines(), start=1)
        if line in template_set
    )
    try:
        tokens = [
            token.string
            for token in tokenize.generate_tokens(io.StringIO(code).readline)
            if token.type in {NAME, NUMBER, STRING, OP}
        ]
    except (tokenize.TokenError, IndentationError) as error:
        return CodeFeatures(frozenset(), template_lines, str(error))
    trigrams = frozenset(zip(tokens, tokens[1:], tokens[2:]))
    return CodeFeatures(trigrams, template_lines)


def extract_ast_features(code: str) -> AstFeatures:
    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        return AstFeatures(None, f"SyntaxError: {error.msg} (line {error.lineno})")

    names: dict[str, str] = {}

    class NameNormalizer(ast.NodeTransformer):
        def _normalize(self, name: str) -> str:
            return names.setdefault(name, f"name_{len(names)}")

        def visit_Name(self, node: ast.Name) -> ast.AST:
            node.id = self._normalize(node.id)
            return node

        def visit_arg(self, node: ast.arg) -> ast.AST:
            node.arg = self._normalize(node.arg)
            return node

        def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
            node.name = self._normalize(node.name)
            return self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
            node.name = self._normalize(node.name)
            return self.generic_visit(node)

        def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
            node.name = self._normalize(node.name)
            return self.generic_visit(node)

    normalized_tree = NameNormalizer().visit(tree)
    ast.fix_missing_locations(normalized_tree)
    return AstFeatures(_freeze_ast(normalized_tree))


def compare_submissions(
    left: Submission,
    right: Submission,
    assignment: Assignment,
    method: str = "token",
) -> SimilarityResult:
    if left.assignment_id != right.assignment_id:
        raise ValueError("submissions must belong to the same assignment")

    template_lines_left = extract_code_features(
        left.code, assignment.allowed_templates
    ).template_lines
    template_lines_right = extract_code_features(
        right.code, assignment.allowed_templates
    ).template_lines
    template_evidence = _template_evidence(
        left, right, template_lines_left, template_lines_right
    )
    template_only = bool(template_evidence)

    if method == "token":
        left_features = extract_code_features(left.code, assignment.allowed_templates)
        right_features = extract_code_features(right.code, assignment.allowed_templates)
        if left_features.token_error or right_features.token_error:
            error = left_features.token_error or right_features.token_error
            return _insufficient_result(
                left, right, method, template_only, template_evidence, error
            )
        score = _jaccard(left_features.token_trigrams, right_features.token_trigrams)
    elif method == "ast":
        left_features = extract_ast_features(left.code)
        right_features = extract_ast_features(right.code)
        if left_features.syntax_error or right_features.syntax_error:
            error = left_features.syntax_error or right_features.syntax_error
            return _insufficient_result(
                left, right, method, template_only, template_evidence, error
            )
        score = _structure_similarity(left_features.structure, right_features.structure)
    else:
        raise ValueError(f"unknown similarity method: {method}")

    evidence = (
        template_evidence + _similarity_evidence(left, right, method)
        if score is not None
        else template_evidence
    )

    return SimilarityResult(
        left_submission_id=left.submission_id,
        right_submission_id=right.submission_id,
        assignment_id=left.assignment_id,
        method=method,
        score=score,
        status="ok" if score is not None else "insufficient_evidence",
        template_only=template_only,
        same_student=left.student_id == right.student_id,
        evidence=evidence,
    )


def top_k_similar(
    target: Submission,
    submissions: Iterable[Submission],
    assignments: dict[str, Assignment],
    *,
    method: str = "token",
    top_k: int = 5,
) -> list[SimilarityResult]:
    if top_k < 0:
        raise ValueError("top_k must be non-negative")
    try:
        assignment = assignments[target.assignment_id]
    except KeyError as error:
        raise ValueError(f"assignment not found: {target.assignment_id}") from error

    results = [
        compare_submissions(target, candidate, assignment, method)
        for candidate in submissions
        if candidate.submission_id != target.submission_id
        and candidate.assignment_id == target.assignment_id
    ]
    results.sort(
        key=lambda result: (
            result.score is not None,
            result.score if result.score is not None else -1.0,
        ),
        reverse=True,
    )
    return results[:top_k]


def _jaccard(
    left: frozenset[tuple[str, str, str]],
    right: frozenset[tuple[str, str, str]],
) -> float | None:
    union = left | right
    if not union:
        return None
    return len(left & right) / len(union)


def _freeze_ast(node: ast.AST) -> tuple[object, ...]:
    values: list[object] = [type(node).__name__]
    for field in ast.iter_fields(node):
        value = field[1]
        if isinstance(value, ast.AST):
            values.append(_freeze_ast(value))
        elif isinstance(value, list):
            values.append(
                tuple(_freeze_ast(item) if isinstance(item, ast.AST) else item for item in value)
            )
        elif field[0] not in {"lineno", "col_offset", "end_lineno", "end_col_offset"}:
            values.append(value)
    return tuple(values)


def _structure_similarity(
    left: tuple[object, ...] | None, right: tuple[object, ...] | None
) -> float | None:
    if not left or not right:
        return None
    return 1.0 if left == right else 0.0


def _template_evidence(
    left: Submission,
    right: Submission,
    left_lines: Sequence[int],
    right_lines: Sequence[int],
) -> tuple[Evidence, ...]:
    if not left_lines or not right_lines:
        return ()
    explanation = (
        "Строка совпадает с разрешённым шаблоном; "
        "это не является доказательством нарушения."
    )
    return (
        Evidence(
            source=f"{left.submission_id}:code",
            line_start=min(left_lines),
            line_end=max(left_lines),
            explanation=explanation,
        ),
        Evidence(
            source=f"{right.submission_id}:code",
            line_start=min(right_lines),
            line_end=max(right_lines),
            explanation=explanation,
        ),
    )


def _similarity_evidence(
    left: Submission, right: Submission, method: str
) -> tuple[Evidence, ...]:
    explanation = f"Исходный диапазон кода, использованный методом {method}."
    evidence: list[Evidence] = []
    for submission in (left, right):
        line_range = _non_empty_line_range(submission.code)
        if line_range is not None:
            evidence.append(
                Evidence(
                    source=f"{submission.submission_id}:code",
                    line_start=line_range[0],
                    line_end=line_range[1],
                    explanation=explanation,
                )
            )
    return tuple(evidence)


def _non_empty_line_range(code: str) -> tuple[int, int] | None:
    lines = [
        line_number
        for line_number, line in enumerate(code.splitlines(), start=1)
        if line.strip()
    ]
    return (lines[0], lines[-1]) if lines else None


def _insufficient_result(
    left: Submission,
    right: Submission,
    method: str,
    template_only: bool,
    evidence: tuple[Evidence, ...],
    error: str,
) -> SimilarityResult:
    return SimilarityResult(
        left_submission_id=left.submission_id,
        right_submission_id=right.submission_id,
        assignment_id=left.assignment_id,
        method=method,
        score=None,
        status="insufficient_evidence",
        template_only=template_only,
        same_student=left.student_id == right.student_id,
        evidence=evidence,
        error=error,
    )
