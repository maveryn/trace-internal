"""Tests for named-shape closer-to-reference icon counting."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks import create_task
from trace.tasks.icons.counting.named_shape_closer_to_reference_count import QUERY_IDS


TASK_ID = "task_icons__named_field__closer_to_reference_count"


def _distance(entity: dict[str, object], reference: dict[str, object]) -> float:
    ex, ey = entity["center_xy"]
    rx, ry = reference["center_xy"]
    return ((float(ex) - float(rx)) ** 2 + (float(ey) - float(ry)) ** 2) ** 0.5


def test_icons_counting_named_shape_closer_to_reference_contract_all_queries() -> None:
    task = create_task(TASK_ID)
    for index, query_id in enumerate(QUERY_IDS):
        out = task.generate(
            hash64(20260524, "named-shape-closer-reference-contract", index),
            params={
                "query_id": query_id,
                "target_shape_id": "star",
                "reference_a_shape_id": "circle",
                "reference_b_shape_id": "square",
                "reference_a_color_name": "red",
                "reference_b_color_name": "blue",
                "target_answer": 3,
                "target_icon_count": 7,
                "reference_axis_degrees_selected": 0,
            },
            max_attempts=300,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        entities = trace["scene_ir"]["entities"]
        references = {str(entity["label"]): entity for entity in entities if str(entity["role"]) == "reference"}
        targets = [entity for entity in entities if str(entity["role"]) == "target"]
        queried = str(execution["queried_reference_label"])
        other = "B" if queried == "A" else "A"
        counted = [
            entity
            for entity in targets
            if _distance(entity, references[queried]) < _distance(entity, references[other])
        ]

        assert out.scene_id == "named_field"
        assert out.query_id == query_id
        assert out.answer_gt.type == "integer"
        assert out.answer_gt.value == 3
        assert out.evidence_gt.type == "bbox_set"
        assert len(references) == 2
        assert set(references) == {"A", "B"}
        assert len(targets) == 7
        assert all(str(entity["shape_id"]) == "star" for entity in targets)
        assert all(str(entity["shape_id"]) != "star" for entity in references.values())
        assert len(counted) == 3
        assert len(out.evidence_gt.value) == 3
        assert set(trace["render_map"]["counted_instance_ids"]) == {str(entity["instance_id"]) for entity in counted}
        assert sorted(out.evidence_gt.value) == sorted(entity["bbox_xyxy"] for entity in counted)
        assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
        assert trace["projected_evidence"]["type"] == "bbox_set"
        assert trace["projected_evidence"]["pixel_bbox_set"] == out.evidence_gt.value
        assert trace["render_spec"]["style"]["text_legibility"]["required_role_count"] >= 2
        assert trace["render_spec"]["style"]["text_legibility"]["failure_count"] == 0
        assert "reference_label_stroke_rgb" in trace["render_spec"]["style"]
        assert "reference A" in out.prompt
        assert "reference B" in out.prompt
        assert "star icons" in out.prompt


def test_icons_counting_named_shape_closer_to_reference_supports_zero_answer() -> None:
    task = create_task(TASK_ID)
    out = task.generate(
        hash64(20260524, "named-shape-closer-reference-zero", 0),
        params={
            "query_id": "closer_to_reference_a_count",
            "target_shape_id": "triangle",
            "target_answer": 0,
            "target_icon_count": 5,
            "reference_axis_degrees_selected": 90,
        },
        max_attempts=300,
    )
    trace = out.trace_payload
    assert out.answer_gt.value == 0
    assert len(out.evidence_gt.value) == 0
    assert trace["execution_trace"]["closer_count_by_reference"]["A"] == 0
    assert trace["execution_trace"]["target_icon_count"] == 5


def test_icons_counting_named_shape_closer_to_reference_sampling_distribution() -> None:
    task = create_task(TASK_ID)
    query_counts: Counter[str] = Counter()
    answer_counts: Counter[int] = Counter()
    axes: set[int] = set()
    for index in range(120):
        out = task.generate(
            hash64(20260524, "named-shape-closer-reference-sampling", index),
            params={},
            max_attempts=300,
        )
        execution = out.trace_payload["execution_trace"]
        query_counts[str(out.query_id)] += 1
        answer_counts[int(out.answer_gt.value)] += 1
        axes.add(int(execution["reference_axis_degrees"]))
        assert 4 <= int(execution["target_icon_count"]) <= 8
        assert 0 <= int(out.answer_gt.value) <= 4
        assert len(out.evidence_gt.value) == int(out.answer_gt.value)

    assert set(query_counts) == set(QUERY_IDS)
    assert set(answer_counts).issubset(set(range(0, 5)))
    assert len(answer_counts) >= 5
    assert axes.issubset({0, 35, 90, 145})
    assert axes
