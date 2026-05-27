"""Tests for current-task random-baseline analysis helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "analyze_current_task_random_baselines.py"
_SPEC = importlib.util.spec_from_file_location("analyze_current_task_random_baselines", _SCRIPT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
analysis = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = analysis
_SPEC.loader.exec_module(analysis)


def _sample(
    *,
    answer_type: str,
    answer_value: object,
    query_variant: str = "variant",
    execution_trace: dict[str, object] | None = None,
    query_params: dict[str, object] | None = None,
) -> analysis.ReviewSample:
    payload = {
        "answer_gt": {"type": answer_type, "value": answer_value},
        "query_variant": query_variant,
        "query_spec": {"params": dict(query_params or {})},
        "execution_trace": dict(execution_trace or {}),
    }
    return analysis.ReviewSample(
        task_id="task_dummy",
        query_variant=query_variant,
        answer_type=answer_type,
        answer_value=answer_value,
        payload=payload,
        path=Path("dummy.json"),
    )


def test_split_markdown_row_preserves_pipes_inside_backticks() -> None:
    row = "| `task_x` | accepted | variants `a|b|c` | 0.1 |"
    assert analysis._split_markdown_row(row) == [
        "`task_x`",
        "accepted",
        "variants `a|b|c`",
        "0.1",
    ]


def test_mcq_option_count_baseline() -> None:
    result = analysis.estimate_random_baseline(
        [
            _sample(answer_type="option_letter", answer_value="A", execution_trace={"option_count": 5}),
            _sample(answer_type="option_letter", answer_value="B", execution_trace={"option_count": 5}),
        ],
        split_by_variant=False,
    )
    assert result.random_baseline == 0.2
    assert result.method == "mcq"
    assert result.confidence == "high"
    assert result.support == "5"


def test_integer_explicit_support_baseline() -> None:
    result = analysis.estimate_random_baseline(
        [
            _sample(
                answer_type="integer",
                answer_value=3,
                query_params={"target_answer_support": [1, 2, 3, 4]},
            ),
            _sample(
                answer_type="integer",
                answer_value=4,
                query_params={"target_answer_support": [1, 2, 3, 4]},
            ),
        ],
        split_by_variant=False,
    )
    assert result.random_baseline == 0.25
    assert result.method == "numeric_support"
    assert result.confidence == "high"


def test_integer_semantic_answer_range_baseline() -> None:
    result = analysis.estimate_random_baseline(
        [
            _sample(
                answer_type="integer",
                answer_value=1,
                execution_trace={"target_count_range": [1, 5]},
            ),
            _sample(
                answer_type="integer",
                answer_value=5,
                execution_trace={"target_count_range": [1, 5]},
            ),
        ],
        split_by_variant=False,
    )
    assert result.random_baseline == 0.2
    assert result.method == "numeric_support"
    assert result.confidence == "high"
    assert result.support == "5"


def test_integer_coordinate_lists_are_not_candidate_sets() -> None:
    result = analysis.estimate_random_baseline(
        [
            _sample(
                answer_type="integer",
                answer_value=2,
                execution_trace={"final_coord": [1, 0]},
            ),
            _sample(
                answer_type="integer",
                answer_value=4,
                execution_trace={"final_coord": [2, 1]},
            ),
        ],
        split_by_variant=False,
    )
    assert result.random_baseline == 1 / 3
    assert result.method == "empirical_integer_range"
    assert result.confidence == "low"


def test_integer_empirical_range_fallback() -> None:
    result = analysis.estimate_random_baseline(
        [
            _sample(answer_type="integer", answer_value=2),
            _sample(answer_type="integer", answer_value=4),
            _sample(answer_type="integer", answer_value=5),
        ],
        split_by_variant=False,
    )
    assert result.random_baseline == 0.25
    assert result.method == "empirical_integer_range"
    assert result.confidence == "low"
    assert result.support == "2..5"


def test_string_candidate_set_baseline_from_row_labels() -> None:
    result = analysis.estimate_random_baseline(
        [
            _sample(
                answer_type="string",
                answer_value="Mira",
                execution_trace={"row_labels": ["Ari", "Mira", "Sol", "Tao"]},
            ),
            _sample(
                answer_type="string",
                answer_value="Sol",
                execution_trace={"row_labels": ["Ari", "Mira", "Sol", "Tao"]},
            ),
        ],
        split_by_variant=False,
    )
    assert result.random_baseline == 0.25
    assert result.method == "candidate_set"
    assert result.confidence == "high"
    assert result.support == "4"


def test_string_empirical_fallback_reports_uniform_and_prior() -> None:
    result = analysis.estimate_random_baseline(
        [
            _sample(answer_type="string", answer_value="A"),
            _sample(answer_type="string", answer_value="A"),
            _sample(answer_type="string", answer_value="B"),
        ],
        split_by_variant=False,
    )
    assert result.random_baseline == 0.5
    assert result.empirical_uniform_baseline == 0.5
    assert round(float(result.empirical_prior_baseline), 6) == round((2 / 3) ** 2 + (1 / 3) ** 2, 6)
    assert result.method == "empirical_unique_answers"
    assert result.confidence == "low"


def test_task_level_baseline_is_weighted_by_variant() -> None:
    result = analysis.estimate_random_baseline(
        [
            _sample(
                answer_type="integer",
                answer_value=1,
                query_variant="small",
                query_params={"target_answer_support": [1, 2]},
            ),
            _sample(
                answer_type="integer",
                answer_value=4,
                query_variant="large",
                query_params={"target_answer_support": [1, 2, 3, 4]},
            ),
            _sample(
                answer_type="integer",
                answer_value=3,
                query_variant="large",
                query_params={"target_answer_support": [1, 2, 3, 4]},
            ),
        ],
        split_by_variant=True,
    )
    assert round(float(result.random_baseline), 6) == round(((1 / 2) + (1 / 4) + (1 / 4)) / 3, 6)
    assert result.method == "weighted_by_query_variant"
