"""Behavior tests for annotated-series chart tasks."""

from __future__ import annotations

from trace.tasks.charts.annotated_series.event_window_query import (
    ChartsAnnotatedSeriesCalloutEndpointChangeValueTask,
    ChartsAnnotatedSeriesEventWindowExtremumLabelTask,
    ChartsAnnotatedSeriesEventWindowThresholdCountTask,
)


def _assert_point_set_contract(out: object) -> None:
    trace = out.trace_payload
    annotation_points = [list(point) for point in out.annotation_gt.value]
    assert out.annotation_gt.type == "point_set"
    assert trace["projected_annotation"] == {
        "type": "point_set",
        "point_set": annotation_points,
        "pixel_point_set": annotation_points,
    }
    assert trace["witness_symbolic"] == {"type": "point_set", "count": len(annotation_points)}
    assert "annotation_bboxes" in trace["render_map"]
    assert "annotation_bboxes" in trace["render_spec"]
    assert all(len(point) == 2 for point in annotation_points)
    answer_and_annotation_prompt = str(out.prompt_variants["answer_and_annotation"])
    assert "annotation" in answer_and_annotation_prompt
    assert "[x,y] pixel points" in answer_and_annotation_prompt


def _assert_keyed_point_map_contract(out: object) -> None:
    trace = out.trace_payload
    annotation_points = {str(key): list(point) for key, point in out.annotation_gt.value.items()}
    assert out.annotation_gt.type == "keyed_point_map"
    assert trace["projected_annotation"] == {
        "type": "keyed_point_map",
        "keyed_point_map": annotation_points,
        "pixel_keyed_point_map": annotation_points,
    }
    assert trace["witness_symbolic"]["type"] == "object_key_map"
    assert set(trace["witness_symbolic"]["keys"]) == {"callout_mark", "endpoint_mark"}
    assert "annotation_bboxes" in trace["render_map"]
    assert "annotation_bboxes" in trace["render_spec"]
    assert set(annotation_points) == {"callout_mark", "endpoint_mark"}
    assert all(len(point) == 2 for point in annotation_points.values())
    answer_and_annotation_prompt = str(out.prompt_variants["answer_and_annotation"])
    assert "callout_mark" in answer_and_annotation_prompt
    assert "endpoint_mark" in answer_and_annotation_prompt


def test_annotated_series_event_window_extremum_uses_answer_mark_point() -> None:
    task = ChartsAnnotatedSeriesEventWindowExtremumLabelTask()
    out = task.generate(24010, params={"scene_variant": "dot_plot"}, max_attempts=10)
    trace = out.trace_payload
    answer_label = str(out.answer_gt.value)

    _assert_point_set_contract(out)
    assert out.answer_gt.type == "string"
    assert len(out.annotation_gt.value) == 1
    assert out.annotation_gt.value[0] == trace["render_map"]["mark_center_by_label"][answer_label]
    assert answer_label in set(trace["execution_trace"]["window_labels"])


def test_annotated_series_event_window_threshold_uses_matching_mark_points() -> None:
    task = ChartsAnnotatedSeriesEventWindowThresholdCountTask()
    out = task.generate(24011, params={"scene_variant": "bar"}, max_attempts=10)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    annotation_labels = [str(label) for label in execution["annotation_labels"]]

    _assert_point_set_contract(out)
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == len(annotation_labels)
    assert out.annotation_gt.value == [
        trace["render_map"]["mark_center_by_label"][label] for label in annotation_labels
    ]


def test_annotated_series_callout_change_uses_anchor_and_endpoint_points() -> None:
    task = ChartsAnnotatedSeriesCalloutEndpointChangeValueTask()
    out = task.generate(24012, params={"scene_variant": "line"}, max_attempts=10)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    anchor_label = str(execution["anchor_label"])
    endpoint_label = str(execution["endpoint_label"])

    _assert_keyed_point_map_contract(out)
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.value == {
        "callout_mark": trace["render_map"]["mark_center_by_label"][anchor_label],
        "endpoint_mark": trace["render_map"]["mark_center_by_label"][endpoint_label],
    }
