from __future__ import annotations

import importlib
import numpy as np
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


def test_strict_score_response_can_match_mcq_option_text_via_prompt() -> None:
    prompt = """Question text.
A. giraffe
B. elephant
C. rabbit
D. dog
"""
    score, extracted, answer, method = strict_score_response(response=r"\boxed{dog}", ground_truth=["D"], prompt_text=prompt)
    assert score == 1.0
    assert extracted is True
    assert answer == "dog"
    assert method == "boxed"


def test_strict_score_response_can_match_yes_no_option_text_via_prompt() -> None:
    prompt = """Please answer the question.
A. Yes
B. No
"""
    score, extracted, answer, method = strict_score_response(response="Yes", ground_truth=["A"], prompt_text=prompt)
    assert score == 1.0
    assert extracted is True
    assert answer == "Yes"
    assert method == "last_line"


def test_strict_score_response_accepts_numpy_object_array_letter_gt() -> None:
    score, extracted, answer, method = strict_score_response(
        response=r"\boxed{A}",
        ground_truth=np.array(["A"], dtype=object),
        prompt_text="A. giraffe\nB. dog\nC. cat\nD. rabbit",
    )
    assert score == 1.0
    assert extracted is True
    assert answer == "A"
    assert method == "boxed"


def test_strict_score_response_accepts_numpy_object_array_open_gt() -> None:
    score, extracted, answer, method = strict_score_response(
        response=r"\boxed{small}",
        ground_truth=np.array(["small"], dtype=object),
    )
    assert score == 1.0
    assert extracted is True
    assert answer == "small"
    assert method == "boxed"


def test_strict_score_response_accepts_mixed_text_numeric_label_against_list_ground_truth() -> None:
    score, extracted, answer, method = strict_score_response(
        response=(
            "The largest difference is $0.0049$, which occurs for the "
            r"\boxed{2-layer (64 neurons)}"
        ),
        ground_truth=["2-layer (64 neurons)"],
    )
    assert score == 1.0
    assert extracted is True
    assert answer == "2-layer (64 neurons)"
    assert method == "boxed"


def test_strict_score_response_accepts_markdown_emphasis_around_boxed_label() -> None:
    score, extracted, answer, method = strict_score_response(
        response=r"\boxed{**2-layer (64 neurons)**}",
        ground_truth=["2-layer (64 neurons)"],
    )
    assert score == 1.0
    assert extracted is True
    assert answer == "**2-layer (64 neurons)**"
    assert method == "boxed"
