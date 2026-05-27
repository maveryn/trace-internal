"""Tests for paired-canvas icon tasks."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks import create_task


PAIRED_TASKS = (
    "task_icons__paired_canvas__panel_exact_match_count",
    "task_icons__paired_canvas__panel_difference_count",
    "task_icons__paired_canvas__panel_attribute_change_count",
    "task_icons__paired_canvas__panel_movement_direction_count",
)


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    return json.loads(str(prompt).split(marker, 1)[1].strip())


def _panel_entities(out, panel: str) -> list[dict]:
    return [
        dict(entity)
        for entity in out.trace_payload["scene_ir"]["entities"]
        if str(entity.get("panel")) == str(panel)
    ]


def test_icons_paired_canvas_exact_match_contract() -> None:
    out = create_task("task_icons__paired_canvas__panel_exact_match_count").generate(
        20260519001,
        params={"target_count": 2, "distractor_count": 3},
        max_attempts=200,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    right = _panel_entities(out, "right")
    assert out.scene_id == "paired_canvas"
    assert out.query_variant == "default"
    assert out.query_id == "right_exact_match_count"
    assert execution["question_format"] == "count_right_icons_with_exact_left_match"
    assert int(out.answer_gt.value) == 2
    assert len(out.evidence_gt.value) == 2
    expected = [right[index]["bbox_xyxy"] for index in execution["matching_right_indices"]]
    assert sorted(out.evidence_gt.value) == sorted(expected)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert 0.0 <= float(out.complexity.complexity_score) <= 1.0


def test_icons_paired_canvas_added_removed_contracts() -> None:
    for query_id, evidence_panel in (
        ("added_in_right_count", "right"),
        ("missing_from_right_count", "left"),
    ):
        out = create_task("task_icons__paired_canvas__panel_difference_count").generate(
            hash64(20260519002, query_id),
            params={"query_id": query_id, "target_count": 2, "distractor_count": 2},
            max_attempts=200,
        )
        execution = out.trace_payload["execution_trace"]
        panel_entities = _panel_entities(out, evidence_panel)
        indices = execution["matching_right_indices"] if evidence_panel == "right" else execution["matching_left_indices"]
        assert out.query_id == query_id
        assert execution["evidence_panel"] == evidence_panel
        assert int(out.answer_gt.value) == 2
        assert len(out.evidence_gt.value) == 2
        assert sorted(out.evidence_gt.value) == sorted([panel_entities[index]["bbox_xyxy"] for index in indices])


def test_icons_paired_canvas_attribute_change_contracts() -> None:
    query_to_attribute = {
        "color_changed_count": "color",
        "size_changed_count": "size",
        "rotation_changed_count": "rotation",
    }
    for query_id, attribute in query_to_attribute.items():
        out = create_task("task_icons__paired_canvas__panel_attribute_change_count").generate(
            hash64(20260519003, query_id),
            params={"query_id": query_id, "target_count": 2, "distractor_count": 3},
            max_attempts=200,
        )
        execution = out.trace_payload["execution_trace"]
        right = _panel_entities(out, "right")
        assert out.query_id == query_id
        assert execution["active_attribute"] == attribute
        assert int(out.answer_gt.value) == 2
        assert len(out.evidence_gt.value) == 2
        for index, entity in enumerate(right):
            has_attribute = attribute in set(str(value) for value in entity.get("changed_attributes", []))
            assert has_attribute is (index in set(execution["matching_right_indices"]))


def test_icons_paired_canvas_movement_contracts() -> None:
    query_to_direction = {
        "moved_left_count": "left",
        "moved_right_count": "right",
        "moved_up_count": "up",
        "moved_down_count": "down",
    }
    for query_id, direction in query_to_direction.items():
        out = create_task("task_icons__paired_canvas__panel_movement_direction_count").generate(
            hash64(20260519004, query_id),
            params={"query_id": query_id, "target_count": 2, "distractor_count": 3},
            max_attempts=200,
        )
        execution = out.trace_payload["execution_trace"]
        right = _panel_entities(out, "right")
        assert out.query_id == query_id
        assert execution["active_direction"] == direction
        assert int(out.answer_gt.value) == 2
        assert len(out.evidence_gt.value) == 2
        for index, entity in enumerate(right):
            is_target = str(entity.get("movement_direction")) == direction
            assert is_target is (index in set(execution["matching_right_indices"]))


def test_icons_paired_canvas_prompt_examples_and_balanced_queries() -> None:
    out = create_task("task_icons__paired_canvas__panel_exact_match_count").generate(20260519005, params={}, max_attempts=200)
    assert _extract_prompt_json_example(out.prompt_variants["answer_only"]) == {"answer": 2}
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert isinstance(answer_and_evidence["evidence"], list)
    assert isinstance(answer_and_evidence["answer"], int)

    expected_queries = {
        "task_icons__paired_canvas__panel_difference_count": {"added_in_right_count", "missing_from_right_count"},
        "task_icons__paired_canvas__panel_attribute_change_count": {
            "color_changed_count",
            "size_changed_count",
            "rotation_changed_count",
        },
        "task_icons__paired_canvas__panel_movement_direction_count": {
            "moved_left_count",
            "moved_right_count",
            "moved_up_count",
            "moved_down_count",
        },
    }
    for task_id, expected in expected_queries.items():
        counts: Counter[str] = Counter()
        for index in range(24):
            out = create_task(task_id).generate(
                hash64(20260519006, task_id, index),
                params={},
                max_attempts=200,
            )
            counts[str(out.query_id)] += 1
            assert out.scene_id == "paired_canvas"
            assert out.query_variant == "default"
        assert set(counts) == expected
        assert sum(counts.values()) == 24
