from __future__ import annotations

import pytest

from trace.core.task_supervision_runtime import (
    normalize_trace_output_mode,
    resolve_trace_reward_mode,
    resolve_trace_row_output_mode,
)


def test_task_conditioned_resolves_each_concrete_row_contract() -> None:
    assert normalize_trace_output_mode("task_conditioned") == "task_conditioned"
    assert (
        resolve_trace_row_output_mode(
            "task_conditioned",
            trace_supervision_mode="answer",
        )
        == "answer"
    )
    assert (
        resolve_trace_row_output_mode(
            "task_conditioned",
            trace_supervision_mode="answer_and_annotation",
        )
        == "answer_and_annotation"
    )
    assert (
        resolve_trace_reward_mode(
            "task_conditioned",
            trace_output_mode="task_conditioned",
            trace_effective_output_mode="answer_and_annotation",
        )
        == "answer_and_annotation"
    )


def test_task_conditioned_rejects_missing_or_invalid_row_contract() -> None:
    with pytest.raises(ValueError, match="trace_supervision_mode"):
        resolve_trace_row_output_mode("task_conditioned")
    with pytest.raises(ValueError, match="trace_supervision_mode"):
        resolve_trace_row_output_mode(
            "task_conditioned",
            trace_supervision_mode="manual_decision",
        )
