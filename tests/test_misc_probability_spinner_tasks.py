"""Contract tests for spinner probability puzzle tasks."""

from __future__ import annotations

from math import gcd

from trace.tasks import TASK_REGISTRY
from trace.tasks.misc.probability.spinner import (
    MULTI_ATTRIBUTE_AND_QUERY_IDS,
    MULTI_ATTRIBUTE_OR_QUERY_IDS,
    PAIR_QUERY_IDS,
    SINGLE_ATTRIBUTE_QUERY_IDS,
    MiscProbabilitySpinnerMultiAttributeAndProbabilityTask,
    MiscProbabilitySpinnerMultiAttributeOrProbabilityTask,
    MiscProbabilitySpinnerPairEventValueTask,
    MiscProbabilitySpinnerSingleAttributeProbabilityTask,
)


TASKS = (
    (
        "task_misc__spinner_probability__single_attribute_probability",
        MiscProbabilitySpinnerSingleAttributeProbabilityTask,
        set(SINGLE_ATTRIBUTE_QUERY_IDS),
    ),
    (
        "task_misc__spinner_probability__multi_attribute_and_probability",
        MiscProbabilitySpinnerMultiAttributeAndProbabilityTask,
        set(MULTI_ATTRIBUTE_AND_QUERY_IDS),
    ),
    (
        "task_misc__spinner_probability__multi_attribute_or_probability",
        MiscProbabilitySpinnerMultiAttributeOrProbabilityTask,
        set(MULTI_ATTRIBUTE_OR_QUERY_IDS),
    ),
    (
        "task_misc__spinner_probability__spinner_pair_event_value",
        MiscProbabilitySpinnerPairEventValueTask,
        set(PAIR_QUERY_IDS),
    ),
)


def _reduced_fraction(numerator: int, denominator: int) -> str:
    common = gcd(abs(int(numerator)), abs(int(denominator)))
    return f"{int(numerator) // common}/{int(denominator) // common}"


def test_spinner_probability_tasks_are_registered() -> None:
    for task_id, task_cls, _queries in TASKS:
        assert TASK_REGISTRY[task_id] is task_cls
        task = task_cls()
        assert task.domain == "misc"
        assert task.task_group == "probability"


def test_spinner_probability_tasks_emit_contracts() -> None:
    for index, (_task_id, task_cls, queries) in enumerate(TASKS):
        out = task_cls().generate(2026052500 + index, params={}, max_attempts=30)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        event = execution["event"]

        assert out.scene_id == "spinner_probability"
        assert out.query_id in queries
        assert out.answer_gt.type == "string"
        assert out.annotation_gt.type == "bbox_set"
        assert trace["query_spec"]["params"]["query_id"] == out.query_id
        assert trace["render_spec"]["scene_id"] == "spinner_probability"
        assert trace["render_map"]["annotation_source"] == "panel_bboxes_px"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
        assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
        assert out.image.size == (
            int(trace["render_spec"]["canvas_width"]),
            int(trace["render_spec"]["canvas_height"]),
        )
        assert str(out.answer_gt.value) == _reduced_fraction(
            int(event["favorable_outcome_count"]),
            int(event["total_outcome_count"]),
        )
        assert 0 < int(event["favorable_outcome_count"]) < int(event["total_outcome_count"])
        assert len(out.annotation_gt.value) == len(execution["annotation_item_ids"])
        if execution["mode"] == "single":
            assert execution["annotation_item_ids"] == ["spinner_panel"]
            assert len(out.annotation_gt.value) == 1
        else:
            assert execution["annotation_item_ids"] == ["spinner_a_panel", "spinner_b_panel"]
            assert len(out.annotation_gt.value) == 2
        assert execution["calculation_supporting_item_ids"]
        for bbox in out.annotation_gt.value:
            assert len(bbox) == 4
            assert 0 <= float(bbox[0]) < float(bbox[2]) <= out.image.size[0]
            assert 0 <= float(bbox[1]) < float(bbox[3]) <= out.image.size[1]


def test_spinner_probability_generation_is_deterministic() -> None:
    task = MiscProbabilitySpinnerPairEventValueTask()
    params = {"scene_variant": "spinner_card", "query_id": "pair_same_color_probability"}
    out_a = task.generate(2026052599, params=params, max_attempts=30)
    out_b = task.generate(2026052599, params=params, max_attempts=30)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
