from __future__ import annotations

import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
VLMEVAL_ROOT = REPO_ROOT / "external" / "VLMEvalKit"
if str(VLMEVAL_ROOT) not in sys.path:
    sys.path.insert(0, str(VLMEVAL_ROOT))


from vlmeval.dataset.utils.puzzlevqa import extract_answer as extract_puzzlevqa  # noqa: E402
from vlmeval.dataset.utils.trace_final25_answer_parsing import (  # noqa: E402
    unwrap_single_answer_block,
)
from vlmeval.dataset.utils.visualpuzzles import extract_answer as extract_visualpuzzles  # noqa: E402


def test_tablevqabench_unwraps_exactly_one_nonempty_answer_block() -> None:
    assert unwrap_single_answer_block("reasoning<answer>42</answer>") == "42"
    assert unwrap_single_answer_block("<answer>Answer: yes</answer>") == "Answer: yes"
    assert unwrap_single_answer_block("<answer></answer>") == "<answer></answer>"
    assert unwrap_single_answer_block("<answer>A</answer><answer>B</answer>") == (
        "<answer>A</answer><answer>B</answer>"
    )


@pytest.mark.parametrize("extract", [extract_puzzlevqa, extract_visualpuzzles])
def test_puzzle_parser_preserves_official_answer_marker_and_adds_final_wrappers(extract) -> None:
    assert extract("reasoning\nAnswer: A") == "A"
    assert extract("<answer>B</answer>") == "B"
    assert extract(r"reasoning \boxed{C}") == "C"
    assert extract(r"<answer>Answer: \( D \)</answer>") == "D"


@pytest.mark.parametrize("extract", [extract_puzzlevqa, extract_visualpuzzles])
def test_puzzle_parser_leaves_conflicting_or_implicit_choices_unresolved(extract) -> None:
    assert extract(r"Answer: A\n\boxed{B}") == "Z"
    assert extract("Answer: A\nreconsidered\nAnswer: B") == "Z"
    assert extract("The reasoning discusses A and B but has no final answer.") == "Z"
