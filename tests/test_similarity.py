import pytest

from lab_system.analysis import Assignment
from lab_system.models import Submission
from lab_system.parser import parse_submission
from lab_system.similarity import (
    compare_submissions,
    extract_code_features,
    top_k_similar,
)


def submission(
    submission_id: str,
    student_id: str,
    code: str,
    assignment_id: str = "lab-1",
) -> Submission:
    return parse_submission(
        {
            "submission_id": submission_id,
            "assignment_id": assignment_id,
            "student_id": student_id,
            "submitted_at": "2026-11-12T12:00:00+03:00",
            "text": "solution",
            "code": code,
            "ai_declaration": {"used": False, "description": ""},
        }
    )


def assignment() -> Assignment:
    return Assignment("lab-1", "Lab 1", ("print(1)",))


def test_token_features_ignore_comments_and_service_tokens():
    features = extract_code_features("x = 1  # comment\n\nprint(x)\n")
    assert ("x", "=", "1") in features.token_trigrams
    assert all("comment" not in trigram for trigram in features.token_trigrams)


def test_identical_code_has_maximum_non_empty_jaccard():
    left = submission("sub-1", "student-1", "value = 1\nprint(value)\n")
    right = submission("sub-2", "student-2", "value = 1\nprint(value)\n")
    result = compare_submissions(left, right, assignment())
    assert result.score == 1.0
    assert result.status == "ok"
    assert result.evidence
    assert result.evidence[0].line_start == 1


def test_empty_features_return_insufficient_evidence():
    left = submission("sub-1", "student-1", "")
    right = submission("sub-2", "student-2", "")
    result = compare_submissions(left, right, assignment())
    assert result.score is None
    assert result.status == "insufficient_evidence"


def test_syntax_error_is_explicit_for_token_and_ast_methods():
    left = submission("sub-1", "student-1", "x = (1\n")
    right = submission("sub-2", "student-2", "x = (1\n")
    token_result = compare_submissions(left, right, assignment(), "token")
    ast_result = compare_submissions(left, right, assignment(), "ast")
    assert token_result.status == "insufficient_evidence"
    assert token_result.error is not None
    assert ast_result.status == "insufficient_evidence"
    assert ast_result.error.startswith("SyntaxError:")


def test_ast_normalizes_names_in_order_of_first_appearance():
    left = submission("sub-1", "student-1", "alpha = 1\nprint(alpha)\n")
    right = submission("sub-2", "student-2", "beta = 1\nprint(beta)\n")
    result = compare_submissions(left, right, assignment(), "ast")
    assert result.score == 1.0


def test_ast_different_structures_give_zero():
    left = submission("sub-1", "student-1", "x = 1\n")
    right = submission("sub-2", "student-2", "x = 1 + 2\n")
    result = compare_submissions(left, right, assignment(), "ast")
    assert result.score == 0.0    


def test_allowed_template_is_explained_and_marked_template_only():
    left = submission("sub-1", "student-1", "print(1)\n")
    right = submission("sub-2", "student-2", "print(1)\n")
    result = compare_submissions(left, right, assignment())
    assert result.template_only is True
    assert result.same_student is False
    assert result.evidence
    assert "не является доказательством" in result.evidence[0].explanation


def test_top_k_filters_assignment_and_self_match_but_keeps_same_student_versions():
    target = submission("sub-1", "student-1", "value = 1\nprint(value)\n")
    same_student_version = submission(
        "sub-2", "student-1", "value = 1\nprint(value)\n"
    )
    other_assignment = submission(
        "sub-3", "student-2", "value = 1\nprint(value)\n", "lab-2"
    )
    result = top_k_similar(
        target,
        [target, same_student_version, other_assignment],
        {"lab-1": assignment()},
        top_k=10,
    )
    assert [item.right_submission_id for item in result] == ["sub-2"]
    assert result[0].same_student is True


def test_top_k_is_sorted_and_bounded():
    target = submission("sub-1", "student-1", "a = 1\nb = 2\n")
    exact = submission("sub-2", "student-2", "a = 1\nb = 2\n")
    partial = submission("sub-3", "student-3", "a = 1\nc = 3\n")
    result = top_k_similar(
        target, [target, partial, exact], {"lab-1": assignment()}, top_k=1
    )
    assert len(result) == 1
    assert result[0].right_submission_id == "sub-2"


def test_unknown_method_and_negative_top_k_are_rejected():
    left = submission("sub-1", "student-1", "x = 1\n")
    right = submission("sub-2", "student-2", "x = 1\n")
    with pytest.raises(ValueError, match="unknown similarity method"):
        compare_submissions(left, right, assignment(), "unknown")
    with pytest.raises(ValueError, match="non-negative"):
        top_k_similar(left, [right], {"lab-1": assignment()}, top_k=-1)


def test_comparison_rejects_different_assignments():
    left = submission("sub-1", "student-1", "x = 1\n", "lab-1")
    right = submission("sub-2", "student-2", "x = 1\n", "lab-2")
    with pytest.raises(ValueError, match="same assignment"):
        compare_submissions(left, right, assignment())


def test_ast_normalizes_function_names():
    left = submission("sub-1", "student-1", "def first(value):\n return value\n")
    right = submission("sub-2", "student-2", "def second(item):\n return item\n")
    result = compare_submissions(left, right, assignment(), "ast")
    assert result.score == 1.0


def test_top_k_puts_zero_score_above_none():
    target = submission("sub-1", "student-1", "a = 1\n")
    other = submission("sub-2", "student-2", "b = 2\nc = 3\nd = 4\n")
    broken = submission("sub-3", "student-3", "x = (1\n")
    result = top_k_similar(target, [target, broken, other], {"lab-1": assignment()}, top_k=10)
    ids = [r.right_submission_id for r in result]
    assert ids.index("sub-2") < ids.index("sub-3")