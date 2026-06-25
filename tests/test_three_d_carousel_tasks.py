"""Tests for synthetic 3D carousel tasks."""

from __future__ import annotations

from pathlib import Path

from trace.core import task_review_distribution
from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks import create_task
from trace.tasks.three_d.carousel.belt_total_object_count import (
    QUERY_ID as TOTAL_QUERY_ID,
    TASK_ID as TOTAL_TASK_ID,
)
from trace.tasks.three_d.carousel.scoped_belt_object_count import (
    COLOR_QUERY_ID,
    OBJECT_TYPE_QUERY_ID,
    TASK_ID as SCOPED_TASK_ID,
)
from trace.tasks.three_d.carousel.scoped_color_type_count import (
    TASK_ID as COLOR_TYPE_TASK_ID,
)
from trace.tasks.three_d.carousel.shared.state import CONVEYOR_OBJECT_SHAPE_TYPES
from trace.tasks.three_d.shared.object_confusions import confusable_shape_names
from trace.tasks.three_d.shared.semantic_colors import confusable_color_names
from tests.three_d_canvas_helpers import assert_three_d_canvas_contract


def test_carousel_object_pool_excludes_cylinder_confusers() -> None:
    assert "cylinder" in CONVEYOR_OBJECT_SHAPE_TYPES
    assert "drum" not in CONVEYOR_OBJECT_SHAPE_TYPES
    assert "pencil" not in CONVEYOR_OBJECT_SHAPE_TYPES
    assert "ruler" not in CONVEYOR_OBJECT_SHAPE_TYPES


def _assert_count_output(output, *, expected_query_id: str) -> None:
    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    target_ids = [str(object_id) for object_id in trace["target_object_ids"]]

    assert output.scene_id == "carousel"
    assert output.query_id == expected_query_id
    assert output.answer_gt.type == "integer"
    assert output.annotation_gt.type == "bbox_set"
    assert int(output.answer_gt.value) == len(target_ids)
    assert len(output.annotation_gt.value) == len(target_ids)
    assert output.annotation_gt.value == [render_map["object_bboxes_px"][object_id] for object_id in target_ids]
    assert output.trace_payload["projected_annotation"]["bbox_set"] == output.annotation_gt.value
    assert output.trace_payload["projected_annotation"]["pixel_bbox_set"] == output.annotation_gt.value
    assert trace["layout_family"] == "elliptical_carousel"
    assert trace["target_belt_key"] in {"inner", "outer"}
    assert trace["target_belt_label"] in {"INNER", "OUTER"}
    assert trace["target_belt_object_ids"]
    assert set(render_map["belt_bboxes_px"]) == {"inner", "outer"}
    assert "{target_" not in output.prompt
    assert "unlettered" not in output.prompt.lower()
    assert "segment" not in output.prompt.lower()
    assert_three_d_canvas_contract(output)

    image_w, image_h = output.image.size
    for bbox in output.annotation_gt.value:
        x0, y0, x1, y1 = [float(value) for value in bbox]
        assert 0.0 <= x0 < x1 <= float(image_w)
        assert 0.0 <= y0 < y1 <= float(image_h)
        assert min(x1 - x0, y1 - y0) >= 24.0
    if trace["predicate_kind"] == "object_type":
        same_belt_distractors = [
            spec
            for spec in trace["object_specs"]
            if str(spec["belt_key"]) == str(trace["target_belt_key"]) and not bool(spec["matches_query"])
        ]
        assert same_belt_distractors
        assert any(str(spec["shape_type"]) != str(trace["target_shape_type"]) for spec in same_belt_distractors)
    if trace["predicate_kind"] == "color":
        same_belt_distractors = [
            spec
            for spec in trace["object_specs"]
            if str(spec["belt_key"]) == str(trace["target_belt_key"]) and not bool(spec["matches_query"])
        ]
        assert same_belt_distractors
        assert any(str(spec["color_name"]) != str(trace["target_color_name"]) for spec in same_belt_distractors)
    assert max(int(value) for value in trace["belt_counts"].values()) <= 12
    assert int(trace["belt_counts"].get("inner", 0)) <= 8
    assert int(trace["belt_counts"].get("outer", 0)) <= 12


def test_carousel_scoped_belt_count_query_ids() -> None:
    task = create_task(SCOPED_TASK_ID)
    cases = (
        (OBJECT_TYPE_QUERY_ID, 2026062401),
        (COLOR_QUERY_ID, 2026062402),
    )
    for query_id, seed in cases:
        output = task.generate(
            seed,
            params={"query_id": query_id, "post_image_noise_apply_prob": 0.0},
            max_attempts=120,
        )
        _assert_count_output(output, expected_query_id=query_id)
        assert 0 <= int(output.answer_gt.value) <= 5


def test_carousel_scoped_belt_count_supports_zero_and_five() -> None:
    task = create_task(SCOPED_TASK_ID)
    cases = (
        (OBJECT_TYPE_QUERY_ID, "inner", 0, 2026062511),
        (OBJECT_TYPE_QUERY_ID, "outer", 5, 2026062512),
        (COLOR_QUERY_ID, "inner", 0, 2026062513),
        (COLOR_QUERY_ID, "outer", 5, 2026062514),
    )
    for query_id, belt_key, target_count, seed in cases:
        output = task.generate(
            seed,
            params={
                "query_id": query_id,
                "target_belt_key": belt_key,
                "target_count": target_count,
                "post_image_noise_apply_prob": 0.0,
            },
            max_attempts=120,
        )
        _assert_count_output(output, expected_query_id=query_id)
        assert int(output.answer_gt.value) == int(target_count)
        if int(target_count) == 0:
            assert output.annotation_gt.value == []


def test_carousel_scoped_color_type_count_uses_conjunction_distractors() -> None:
    task = create_task(COLOR_TYPE_TASK_ID)
    cases = (
        ("inner", 0, 2026062601),
        ("outer", 5, 2026062602),
    )
    for belt_key, target_count, seed in cases:
        output = task.generate(
            seed,
            params={
                "target_belt_key": belt_key,
                "target_count": target_count,
                "post_image_noise_apply_prob": 0.0,
            },
            max_attempts=120,
        )
        _assert_count_output(output, expected_query_id=SINGLE_QUERY_ID)
        trace = output.trace_payload["execution_trace"]
        target_ids = [str(object_id) for object_id in trace["target_object_ids"]]
        target_shape = str(trace["target_shape_type"])
        target_color = str(trace["target_color_name"])
        target_belt = str(trace["target_belt_key"])
        confusable_shapes = set(confusable_shape_names(target_shape))

        assert trace["predicate_kind"] == "color_type"
        assert int(output.answer_gt.value) == int(target_count)
        assert len(target_ids) == int(target_count)
        assert output.trace_payload["query_spec"]["internal_query_id"] == SINGLE_QUERY_ID
        for spec in trace["object_specs"]:
            is_target = str(spec["object_id"]) in set(target_ids)
            if is_target:
                assert str(spec["belt_key"]) == target_belt
                assert str(spec["shape_type"]) == target_shape
                assert str(spec["color_name"]) == target_color
        same_belt_roles = {
            str(spec["count_role"])
            for spec in trace["object_specs"]
            if str(spec["belt_key"]) == target_belt and not bool(spec["matches_query"])
        }
        assert all(
            str(spec["shape_type"]) not in confusable_shapes
            for spec in trace["object_specs"]
            if str(spec["shape_type"]) != target_shape
        )
        assert "same_belt_same_color_wrong_type" in same_belt_roles
        assert "same_belt_same_type_wrong_color" in same_belt_roles
        assert any(
            str(spec["belt_key"]) != target_belt
            and str(spec["shape_type"]) == target_shape
            and str(spec["color_name"]) == target_color
            for spec in trace["object_specs"]
        )
        if int(target_count) == 0:
            assert output.annotation_gt.value == []


def test_carousel_color_type_distractors_avoid_visually_confusable_shapes() -> None:
    output = create_task(COLOR_TYPE_TASK_ID).generate(
        2026062621,
        params={
            "target_shape_type": "card",
            "target_color_name": "red",
            "target_count": 3,
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=120,
    )
    trace = output.trace_payload["execution_trace"]
    confusable_shapes = set(confusable_shape_names("card"))

    assert trace["target_shape_type"] == "card"
    assert trace["target_color_name"] == "red"
    assert all(
        str(spec["shape_type"]) not in confusable_shapes
        for spec in trace["object_specs"]
        if str(spec["shape_type"]) != "card"
    )


def test_carousel_color_readout_excludes_target_confusable_colors() -> None:
    cases = (
        (SCOPED_TASK_ID, {"query_id": COLOR_QUERY_ID, "target_color_name": "red"}, 2026062611),
        (COLOR_TYPE_TASK_ID, {"target_color_name": "red"}, 2026062612),
    )
    for task_id, params, seed in cases:
        output = create_task(task_id).generate(
            seed,
            params={**params, "post_image_noise_apply_prob": 0.0},
            max_attempts=120,
        )
        trace = output.trace_payload["execution_trace"]
        colors = {str(spec["color_name"]) for spec in trace["object_specs"]}
        assert str(trace["target_color_name"]) == "red"
        assert colors.isdisjoint(set(confusable_color_names("red")))


def test_carousel_belt_total_count_uses_belt_specific_support() -> None:
    task = create_task(TOTAL_TASK_ID)
    cases = (
        ("inner", 8, 2026062501),
        ("outer", 10, 2026062502),
    )
    for belt_key, target_count, seed in cases:
        output = task.generate(
            seed,
            params={
                "target_belt_key": belt_key,
                "target_count": target_count,
                "post_image_noise_apply_prob": 0.0,
            },
            max_attempts=120,
        )
        trace = output.trace_payload["execution_trace"]
        render_map = output.trace_payload["render_map"]
        target_ids = [str(object_id) for object_id in trace["target_object_ids"]]

        assert output.scene_id == "carousel"
        assert output.query_id == SINGLE_QUERY_ID
        assert output.trace_payload["query_spec"]["internal_query_id"] == TOTAL_QUERY_ID
        replay_row = task_review_distribution.random_collector(output, seed)
        assert replay_row["generation_params"]["query_id"] == SINGLE_QUERY_ID
        assert replay_row["generation_params"]["internal_query_id"] == TOTAL_QUERY_ID
        assert output.answer_gt.type == "integer"
        assert output.annotation_gt.type == "bbox_set"
        assert trace["target_belt_key"] == belt_key
        assert trace["predicate_kind"] == "belt_total"
        assert int(output.answer_gt.value) == int(target_count)
        assert int(output.answer_gt.value) == len(target_ids)
        assert target_ids == trace["target_belt_object_ids"]
        assert output.annotation_gt.value == [render_map["object_bboxes_px"][object_id] for object_id in target_ids]
        assert len({str(spec["shape_type"]) for spec in trace["object_specs"]}) == 1
        assert len({str(spec["color_name"]) for spec in trace["object_specs"]}) >= 2
        assert "{target_" not in output.prompt
        assert "color" not in output.prompt.lower()
        assert "type" not in output.prompt.lower()
        assert_three_d_canvas_contract(output)

        image_w, image_h = output.image.size
        for bbox in output.annotation_gt.value:
            x0, y0, x1, y1 = [float(value) for value in bbox]
            assert 0.0 <= x0 < x1 <= float(image_w)
            assert 0.0 <= y0 < y1 <= float(image_h)
            assert min(x1 - x0, y1 - y0) >= 24.0


def test_carousel_renderer_has_no_unqueried_gate_decoration() -> None:
    source = Path("trace/tasks/three_d/carousel/shared/rendering.py").read_text()

    assert "inspection_gate" not in source
    assert "three_d_conveyor_inspection_gate" not in source
