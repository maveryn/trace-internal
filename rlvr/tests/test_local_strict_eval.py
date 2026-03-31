from __future__ import annotations

import importlib
import re
import sys
import types


def _extract_boxed_content(text: str) -> str | None:
    match = re.search(r"\\boxed\{(.+?)\}", text)
    return match.group(1) if match else None


grader = types.SimpleNamespace(
    extract_boxed_content=_extract_boxed_content,
    grade_answer=lambda pred, gt: str(pred).strip().lower() == str(gt).strip().lower(),
)
sys.modules["mathruler"] = types.SimpleNamespace(grader=grader)
sys.modules["mathruler.grader"] = grader

import verl.utils.local_strict_eval as local_strict_eval

local_strict_eval = importlib.reload(local_strict_eval)
strict_score_response = local_strict_eval.strict_score_response


def test_strict_score_response_accepts_boxed_mcq_against_list_ground_truth() -> None:
    score, extracted, answer, method = strict_score_response(response=r"\boxed{A}", ground_truth=["A"])
    assert score == 1.0
    assert extracted is True
    assert answer == "A"
    assert method == "boxed"


def test_strict_score_response_accepts_prefixed_mcq_against_list_ground_truth() -> None:
    score, extracted, answer, method = strict_score_response(response="D. dog.", ground_truth=["D"])
    assert score == 1.0
    assert extracted is True
    assert answer == "D"
    assert method == "last_line"


def test_strict_score_response_accepts_open_answer_against_singleton_list_ground_truth() -> None:
    score, extracted, answer, method = strict_score_response(response=r"\boxed{Experience}", ground_truth=["EXPERIENCE"])
    assert score == 1.0
    assert extracted is True
    assert answer == "Experience"
    assert method == "boxed"
