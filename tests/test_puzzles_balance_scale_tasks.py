"""Contracts for balance-scale logic puzzle tasks."""

from __future__ import annotations

from trace.tasks import TASK_REGISTRY
from trace.tasks.puzzles.logic.balance_scale import (
    EQUIVALENT_OBJECT_COUNT_QUERY_ID,
    EQUIVALENT_OBJECT_COUNT_TASK_ID,
    HEAVIEST_OBJECT_LABEL_QUERY_ID,
    LIGHTEST_OBJECT_LABEL_QUERY_ID,
    MISSING_OBJECT_WEIGHT_QUERY_ID,
    MISSING_OBJECT_WEIGHT_TASK_ID,
    QUERY_ID,
    SCENE_ID,
    SUPPORTED_QUERY_IDS,
    TASK_ID,
    WEIGHT_ORDER_QUERY_IDS,
    WEIGHT_ORDER_TASK_ID,
    PuzzlesLogicEquivalentObjectCountValueTask,
    PuzzlesLogicMissingObjectWeightValueTask,
    PuzzlesLogicWeightOrderLabelTask,
    _unique_equivalent_counts,
    _unique_target_values,
    _unique_weight_order_labels,
)


def test_balance_scale_task_is_registered() -> None:
    assert TASK_REGISTRY[TASK_ID] is PuzzlesLogicMissingObjectWeightValueTask
    assert TASK_REGISTRY[MISSING_OBJECT_WEIGHT_TASK_ID] is PuzzlesLogicMissingObjectWeightValueTask
    assert TASK_REGISTRY[EQUIVALENT_OBJECT_COUNT_TASK_ID] is PuzzlesLogicEquivalentObjectCountValueTask
    assert TASK_REGISTRY[WEIGHT_ORDER_TASK_ID] is PuzzlesLogicWeightOrderLabelTask


def test_balance_scale_task_emits_public_contract() -> None:
    task = PuzzlesLogicMissingObjectWeightValueTask()
    out = task.generate(2026060401, params={}, max_attempts=80)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == SCENE_ID
    assert out.query_id == QUERY_ID
    assert out.query_id == MISSING_OBJECT_WEIGHT_QUERY_ID
    assert out.query_id in SUPPORTED_QUERY_IDS
    assert out.answer_gt.type == "integer"
    assert 1 <= int(out.answer_gt.value) <= 20
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert sorted(out.annotation_gt.value) == ["missing_value_box", "query_object"]
    assert sorted(out.prompt_variants) == ["answer_and_annotation", "answer_only"]
    assert trace["query_spec"]["params"]["query_id"] == QUERY_ID
    assert trace["render_spec"]["scene_id"] == SCENE_ID
    assert trace["render_spec"]["text_style"]["font"]["font_family"]
    assert trace["render_map"]["annotation_source"] == "keyed_item_bboxes_px"
    assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
    assert execution["scene_id"] == SCENE_ID
    assert execution["query_id"] == QUERY_ID
    assert execution["supporting_role_item_ids"] == {
        "query_object": "query_object",
        "missing_value_box": "missing_value_box",
    }
    assert out.image.size == (
        int(trace["render_spec"]["canvas_width"]),
        int(trace["render_spec"]["canvas_height"]),
    )
    for bbox in out.annotation_gt.value.values():
        assert len(bbox) == 4
        assert 0 <= float(bbox[0]) < float(bbox[2]) <= out.image.size[0]
        assert 0 <= float(bbox[1]) < float(bbox[3]) <= out.image.size[1]


def test_equivalent_object_count_task_emits_public_contract() -> None:
    task = PuzzlesLogicEquivalentObjectCountValueTask()
    out = task.generate(2026060501, params={}, max_attempts=80)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == SCENE_ID
    assert out.query_id == EQUIVALENT_OBJECT_COUNT_QUERY_ID
    assert out.query_id in SUPPORTED_QUERY_IDS
    assert out.answer_gt.type == "integer"
    assert 2 <= int(out.answer_gt.value) <= 8
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert sorted(out.annotation_gt.value) == ["missing_count_box", "repeated_object", "source_object"]
    assert trace["query_spec"]["params"]["query_id"] == EQUIVALENT_OBJECT_COUNT_QUERY_ID
    assert trace["render_spec"]["scene_id"] == SCENE_ID
    assert trace["render_map"]["annotation_source"] == "keyed_item_bboxes_px"
    assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
    assert execution["scene_id"] == SCENE_ID
    assert execution["query_id"] == EQUIVALENT_OBJECT_COUNT_QUERY_ID
    assert execution["supporting_role_item_ids"] == {
        "source_object": "source_object",
        "repeated_object": "repeated_object",
        "missing_count_box": "missing_count_box",
    }
    assert out.image.size == (
        int(trace["render_spec"]["canvas_width"]),
        int(trace["render_spec"]["canvas_height"]),
    )
    for bbox in out.annotation_gt.value.values():
        assert len(bbox) == 4
        assert 0 <= float(bbox[0]) < float(bbox[2]) <= out.image.size[0]
        assert 0 <= float(bbox[1]) < float(bbox[3]) <= out.image.size[1]


def test_weight_order_task_emits_public_contract() -> None:
    task = PuzzlesLogicWeightOrderLabelTask()
    seen_query_ids = set()
    for index, forced_query_id in enumerate(WEIGHT_ORDER_QUERY_IDS):
        out = task.generate(
            2026060601 + index,
            params={"query_id": forced_query_id},
            max_attempts=80,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        seen_query_ids.add(out.query_id)

        assert out.scene_id == SCENE_ID
        assert out.query_id == forced_query_id
        assert out.query_id in SUPPORTED_QUERY_IDS
        assert out.answer_gt.type == "string"
        assert str(out.answer_gt.value) in execution["object_labels"]
        assert out.annotation_gt.type == "keyed_bbox_map"
        assert "selected_object" in out.annotation_gt.value
        assert "comparison_scale_1" in out.annotation_gt.value
        assert "comparison_scale_2" in out.annotation_gt.value
        assert trace["query_spec"]["params"]["query_id"] == forced_query_id
        assert trace["query_spec"]["params"]["answer_type"] == "string"
        assert trace["query_spec"]["params"]["target_cue_mode"] == "query_row_only"
        assert trace["render_spec"]["scene_id"] == SCENE_ID
        assert trace["render_map"]["annotation_source"] == "keyed_item_bboxes_px"
        assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
        assert execution["scene_id"] == SCENE_ID
        assert execution["query_id"] == forced_query_id
        assert execution["supporting_role_item_ids"]["selected_object"] == f"candidate_{out.answer_gt.value}"
        assert out.image.size == (
            int(trace["render_spec"]["canvas_width"]),
            int(trace["render_spec"]["canvas_height"]),
        )
        for bbox in out.annotation_gt.value.values():
            assert len(bbox) == 4
            assert 0 <= float(bbox[0]) < float(bbox[2]) <= out.image.size[0]
            assert 0 <= float(bbox[1]) < float(bbox[3]) <= out.image.size[1]

    assert seen_query_ids == {HEAVIEST_OBJECT_LABEL_QUERY_ID, LIGHTEST_OBJECT_LABEL_QUERY_ID}


def test_balance_scale_equations_are_balanced_and_unique() -> None:
    task = PuzzlesLogicMissingObjectWeightValueTask()
    for index, panel_count in enumerate((2, 3)):
        out = task.generate(
            2026060410 + index,
            params={
                "scale_panel_count_min": panel_count,
                "scale_panel_count_max": panel_count,
            },
            max_attempts=80,
        )
        execution = out.trace_payload["execution_trace"]
        support = [int(value) for value in execution["target_answer_support"]]

        assert int(out.answer_gt.value) == int(execution["answer_value"])
        assert len(execution["panels"]) == panel_count
        for panel in execution["panels"]:
            assert int(panel["left_total"]) == int(panel["right_total"])

        unique_values = _unique_target_values(
            equations=execution["equations"],
            labels=execution["object_labels"],
            target_label=str(execution["target_label"]),
            support=support,
        )
        assert unique_values == [int(out.answer_gt.value)]


def test_equivalent_object_count_equations_are_balanced_and_unique() -> None:
    task = PuzzlesLogicEquivalentObjectCountValueTask()
    for index, panel_count in enumerate((2, 3)):
        out = task.generate(
            2026060510 + index,
            params={
                "scale_panel_count_min": panel_count,
                "scale_panel_count_max": panel_count,
            },
            max_attempts=80,
        )
        execution = out.trace_payload["execution_trace"]
        support = [int(value) for value in execution["target_answer_support"]]
        weight_support = [int(value) for value in range(1, 81)]

        assert int(out.answer_gt.value) == int(execution["answer_value"])
        assert len(execution["panels"]) == panel_count
        for panel in execution["panels"]:
            assert int(panel["left_total"]) == int(panel["right_total"])

        unique_counts = _unique_equivalent_counts(
            equations=execution["equations"],
            labels=execution["object_labels"],
            source_label=str(execution["source_label"]),
            repeated_label=str(execution["repeated_label"]),
            count_support=support,
            weight_support=weight_support,
        )
        assert unique_counts == [int(out.answer_gt.value)]


def test_weight_order_comparisons_are_tilted_and_unique() -> None:
    task = PuzzlesLogicWeightOrderLabelTask()
    for index, query_id in enumerate(WEIGHT_ORDER_QUERY_IDS):
        out = task.generate(
            2026060610 + index,
            params={
                "query_id": query_id,
                "object_count_min": 4,
                "object_count_max": 4,
            },
            max_attempts=80,
        )
        execution = out.trace_payload["execution_trace"]

        assert len(execution["object_labels"]) == 4
        assert len(execution["panels"]) == 3
        assert len(execution["comparisons"]) == 3
        for panel in execution["panels"]:
            assert int(panel["left_total"]) != int(panel["right_total"])
            assert panel["balance_state"] in {"left_heavier", "right_heavier"}
            assert panel["heavier_side"] in {"left", "right"}

        unique_labels = _unique_weight_order_labels(
            comparisons=execution["comparisons"],
            labels=execution["object_labels"],
            query_id=str(query_id),
        )
        assert unique_labels == [str(out.answer_gt.value)]


def test_balance_scale_task_is_deterministic() -> None:
    task = PuzzlesLogicMissingObjectWeightValueTask()
    params = {
        "scene_variant": "balance_card",
        "target_cue_mode": "query_row_and_highlight",
        "scale_panel_count_min": 3,
        "scale_panel_count_max": 3,
    }
    out_a = task.generate(2026060499, params=params, max_attempts=80)
    out_b = task.generate(2026060499, params=params, max_attempts=80)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.annotation_gt == out_b.annotation_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_equivalent_object_count_task_is_deterministic() -> None:
    task = PuzzlesLogicEquivalentObjectCountValueTask()
    params = {
        "scene_variant": "balance_card",
        "target_cue_mode": "query_row_and_highlight",
        "scale_panel_count_min": 3,
        "scale_panel_count_max": 3,
    }
    out_a = task.generate(2026060599, params=params, max_attempts=80)
    out_b = task.generate(2026060599, params=params, max_attempts=80)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.annotation_gt == out_b.annotation_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_weight_order_task_is_deterministic() -> None:
    task = PuzzlesLogicWeightOrderLabelTask()
    params = {
        "query_id": HEAVIEST_OBJECT_LABEL_QUERY_ID,
        "scene_variant": "balance_card",
        "object_count_min": 4,
        "object_count_max": 4,
    }
    out_a = task.generate(2026060699, params=params, max_attempts=80)
    out_b = task.generate(2026060699, params=params, max_attempts=80)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.annotation_gt == out_b.annotation_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()
