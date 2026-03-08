"""Behavior tests for single-object geometry measurement tasks."""

from __future__ import annotations

import json
from collections import Counter
from math import hypot

from trace.core.seed import hash64
from trace.tasks.geometry.measurement.angle import GeometryAngleMeasure2DTask
from trace.tasks.geometry.measurement.area import GeometryAreaMeasure2DTask
from trace.tasks.geometry.measurement.length import GeometryLengthMeasure2DTask
from trace.tasks.geometry.measurement.perimeter import GeometryPerimeterMeasure2DTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def _graph_origin_and_spacing(trace_payload):
    frame = trace_payload["render_spec"]["graph_coordinate_frame"]
    origin_x, origin_y = (int(frame["origin_pixel"][0]), int(frame["origin_pixel"][1]))
    spacing = int(frame["spacing_px"])
    return origin_x, origin_y, spacing


def _graph_point(point, *, origin_x: int, origin_y: int, spacing: int) -> tuple[float, float]:
    return (
        (float(point[0]) - float(origin_x)) / float(spacing),
        (float(origin_y) - float(point[1])) / float(spacing),
    )


def _assert_grid_point_map(value: object, *, expected_len: int) -> dict[str, list[int]]:
    assert isinstance(value, dict)
    assert len(value) == int(expected_len)
    for key, point in value.items():
        assert str(key).strip()
        assert isinstance(point, list) and len(point) == 2
        assert all(isinstance(coord, int) for coord in point)
    return dict(value)


def test_angle_measure_outputs_expected_contract() -> None:
    task = GeometryAngleMeasure2DTask()
    cases = [
        ("primitive_angle", "primitive_angle"),
        ("triangle", "polygon_angle"),
        ("quadrilateral", "polygon_angle"),
        ("intersection_lines", "intersection_angle"),
    ]
    for idx, (source_kind, scene_variant) in enumerate(cases):
        out = task.generate(
            2200 + idx,
            params={"query_type": "measure", "source_kind": source_kind, "angle_step": 1, "min_angle": 30, "max_angle": 150},
            max_attempts=180,
        )
        trace = out.trace_payload
        assert out.query_type == "measure"
        assert out.answer_gt.type == "option_letter"
        assert str(out.answer_gt.value) in {"A", "B", "C", "D", "E"}
        assert out.evidence_gt.type == "grid_point_map"
        evidence_map = _assert_grid_point_map(out.evidence_gt.value, expected_len=3)
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert trace["query_spec"]["prompt_variant_active_key"] == "answer_and_evidence"
        assert trace["execution_trace"]["scene_variant"] == scene_variant
        assert trace["execution_trace"]["source_kind"] == source_kind
        assert str(trace["execution_trace"]["correct_option_letter"]) == str(out.answer_gt.value)
        assert str(trace["execution_trace"]["answer_option_letter"]) == str(out.answer_gt.value)
        target_angle = int(trace["execution_trace"]["target_angle"])
        assert 30 <= int(target_angle) <= 150
        assert abs(float(trace["execution_trace"]["raw_angle_degrees"]) - float(target_angle)) <= 0.05 + 1e-9
        assert trace["execution_trace"]["question_format"] == "mcq"
        assert len(trace["execution_trace"]["choices"]) == 5
        assert int(trace["execution_trace"]["correct_option_value"]) == int(target_angle)
        assert 0 <= int(trace["execution_trace"]["correct_option_index"]) <= 4
        assert "option letter" in out.prompt.lower()
        assert "A." in out.prompt and "B." in out.prompt

        origin_x, origin_y, spacing = _graph_origin_and_spacing(trace)
        projected = trace["projected_evidence"]["point_map"]
        projected_grid = trace["projected_evidence"]["grid_point_map"]
        assert set(projected.keys()) == set(evidence_map.keys())
        assert set(projected_grid.keys()) == set(evidence_map.keys())
        for label in projected:
            pixel_point = projected[label]
            graph_point = projected_grid[label]
            expected_x = int(round((float(pixel_point[0]) - float(origin_x)) / float(spacing)))
            expected_y = int(round((float(origin_y) - float(pixel_point[1])) / float(spacing)))
            assert graph_point == [expected_x, expected_y]

        attrs = trace["scene_ir"]["entities"][0]["attrs"]
        if source_kind == "primitive_angle":
            arm_a = attrs["points"]["arm_a"]
            vertex = attrs["points"]["vertex"]
            arm_b = attrs["points"]["arm_b"]
        elif source_kind in {"triangle", "quadrilateral"}:
            vertices = attrs["vertices"]
            prev_idx, vertex_idx, next_idx = attrs["target_triplet_indices"]
            arm_a = vertices[int(prev_idx)]
            vertex = vertices[int(vertex_idx)]
            arm_b = vertices[int(next_idx)]
        else:
            target_points = attrs["points"]["target"]
            arm_a = target_points["arm_a"]
            vertex = target_points["vertex"]
            arm_b = target_points["arm_b"]
        target_labels = [str(label) for label in trace["execution_trace"]["target_labels"]]
        expected_graph_evidence = {
            str(target_labels[0]): [
                int(round((float(arm_a[0]) - float(origin_x)) / float(spacing))),
                int(round((float(origin_y) - float(arm_a[1])) / float(spacing))),
            ],
            str(target_labels[1]): [
                int(round((float(vertex[0]) - float(origin_x)) / float(spacing))),
                int(round((float(origin_y) - float(vertex[1])) / float(spacing))),
            ],
            str(target_labels[2]): [
                int(round((float(arm_b[0]) - float(origin_x)) / float(spacing))),
                int(round((float(origin_y) - float(arm_b[1])) / float(spacing))),
            ],
        }
        assert evidence_map == expected_graph_evidence
        arm_a_graph = _graph_point(arm_a, origin_x=origin_x, origin_y=origin_y, spacing=spacing)
        vertex_graph = _graph_point(vertex, origin_x=origin_x, origin_y=origin_y, spacing=spacing)
        arm_b_graph = _graph_point(arm_b, origin_x=origin_x, origin_y=origin_y, spacing=spacing)
        assert hypot(arm_a_graph[0] - vertex_graph[0], arm_a_graph[1] - vertex_graph[1]) >= 2.0 - 1e-6
        assert hypot(arm_b_graph[0] - vertex_graph[0], arm_b_graph[1] - vertex_graph[1]) >= 2.0 - 1e-6


def test_angle_measure_label_font_scales_with_canvas() -> None:
    task = GeometryAngleMeasure2DTask()
    small = task.generate(
        4010,
        params={"query_type": "measure", "source_kind": "primitive_angle", "canvas_size": 256, "graph_cells": 16},
        max_attempts=180,
    )
    large = task.generate(
        4010,
        params={"query_type": "measure", "source_kind": "primitive_angle", "canvas_size": 512, "graph_cells": 16},
        max_attempts=180,
    )
    small_style = small.trace_payload["render_spec"]["text_style"]
    large_style = large.trace_payload["render_spec"]["text_style"]
    assert int(small_style["font_size_px"]) >= 6
    assert int(large_style["font_size_px"]) > int(small_style["font_size_px"])
    assert int(small_style["stroke_width_px"]) >= 1


def test_angle_measure_balanced_sampling_defaults_and_index() -> None:
    task = GeometryAngleMeasure2DTask()
    source_counts: Counter[str] = Counter()
    answer_counts: Counter[int] = Counter()
    feasible_union: set[int] = set()
    for index in range(160):
        out = task.generate(
            hash64(7000, "angle_cycle_seed", index),
            params={"query_type": "measure", "_sampling_index": index},
            max_attempts=220,
        )
        source_kind = str(out.trace_payload["execution_trace"]["source_kind"])
        feasible = {
            int(value)
            for value in out.trace_payload["execution_trace"]["feasible_answer_values"]
        }
        feasible_union.update(feasible)
        answer_value = int(out.trace_payload["execution_trace"]["target_angle"])
        source_counts[source_kind] += 1
        answer_counts[answer_value] += 1
        assert answer_value in feasible
        assert len(feasible) >= 9

    assert max(source_counts.values()) - min(source_counts.values()) <= 1
    coverage_floor = max(9, int(0.75 * float(len(feasible_union))))
    assert len(answer_counts) >= coverage_floor

    sources = []
    for index in range(8):
        out = task.generate(
            hash64(4040, "angle_measure_seed", index),
            params={"query_type": "measure", "_sampling_index": index},
            max_attempts=220,
        )
        sources.append(str(out.trace_payload["execution_trace"]["source_kind"]))
    assert sources[:4] == sources[4:]

    answers = []
    primitive_feasible_count = None
    for index in range(30):
        out = task.generate(
            hash64(4404, "angle_measure_seed", index),
            params={"query_type": "measure", "_sampling_index": index, "source_kind": "primitive_angle"},
            max_attempts=220,
        )
        if primitive_feasible_count is None:
            primitive_feasible_count = len(
                {
                    int(value)
                    for value in out.trace_payload["execution_trace"]["feasible_answer_values"]
                }
            )
        answers.append(int(out.trace_payload["execution_trace"]["target_angle"]))
    assert primitive_feasible_count is not None
    assert len(set(answers)) == min(len(answers), int(primitive_feasible_count))


def test_polygon_measure_tasks_match_scene_attrs() -> None:
    cases = [
        (
            GeometryAreaMeasure2DTask,
            "task_geometry_measurement_area",
            "triangle",
            "polygon",
            "integer",
            "area_square_units",
        ),
        (
            GeometryAreaMeasure2DTask,
            "task_geometry_measurement_area",
            "quadrilateral",
            "polygon",
            "integer",
            "area_square_units",
        ),
        (
            GeometryAreaMeasure2DTask,
            "task_geometry_measurement_area",
            "ellipse",
            "ellipse",
            "pi_expression",
            "area_pi_coefficient",
        ),
        (
            GeometryPerimeterMeasure2DTask,
            "task_geometry_measurement_perimeter",
            "triangle",
            "polygon",
            "integer",
            "perimeter_units",
        ),
        (
            GeometryPerimeterMeasure2DTask,
            "task_geometry_measurement_perimeter",
            "quadrilateral",
            "polygon",
            "integer",
            "perimeter_units",
        ),
        (
            GeometryPerimeterMeasure2DTask,
            "task_geometry_measurement_perimeter",
            "circle",
            "circle",
            "pi_expression",
            "circumference_pi_coefficient",
        ),
    ]
    for idx, (task_cls, task_id, shape_variant, entity_type, answer_type, answer_attr) in enumerate(cases):
        task = task_cls()
        out = task.generate(
            3300 + idx,
            params={"query_type": "measure", "shape_variant": str(shape_variant)},
            max_attempts=180,
        )
        trace = out.trace_payload
        assert out.query_type == "measure"
        assert out.answer_gt.type == str(answer_type)
        assert out.evidence_gt.type == "grid_point_map"
        evidence_map = _assert_grid_point_map(
            out.evidence_gt.value,
            expected_len=len(trace["execution_trace"]["required_evidence_labels"]),
        )
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert trace["query_spec"]["prompt_variant_active_key"] == "answer_and_evidence"

        entity = trace["scene_ir"]["entities"][0]
        attrs = entity["attrs"]
        assert str(task_id).startswith("task_geometry_measurement_")
        assert str(trace["execution_trace"]["shape_variant"]) == str(shape_variant)
        assert str(entity["entity_type"]) == str(entity_type)

        if str(answer_type) == "integer":
            assert int(out.answer_gt.value) == int(attrs[str(answer_attr)])
            assert len(evidence_map) == int(attrs["polygon_sides"])
            example = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
            assert list(example.keys()) == ["evidence", "answer"]
            assert isinstance(example["evidence"], dict)
            assert len(example["evidence"]) == int(attrs["polygon_sides"])
        else:
            answer_scalar = int(trace["execution_trace"]["answer_scalar"])
            expected_text = "π" if answer_scalar == 1 else f"{answer_scalar}π"
            assert str(out.answer_gt.value) == expected_text
            assert int(answer_scalar) == int(attrs[str(answer_attr)])
            if str(shape_variant) == "ellipse":
                assert len(evidence_map) == 3
            else:
                assert len(evidence_map) == 2

        origin_x, origin_y, spacing = _graph_origin_and_spacing(trace)
        point_map = trace["projected_evidence"]["point_map"]
        grid_point_map = trace["projected_evidence"]["grid_point_map"]
        assert set(point_map.keys()) == set(evidence_map.keys())
        assert set(grid_point_map.keys()) == set(evidence_map.keys())
        for label in point_map:
            pixel_point = point_map[label]
            graph_point = grid_point_map[label]
            expected_x = int(round((float(pixel_point[0]) - float(origin_x)) / float(spacing)))
            expected_y = int(round((float(origin_y) - float(pixel_point[1])) / float(spacing)))
            assert graph_point == [expected_x, expected_y]


def test_length_measure_variants_match_scene_and_evidence() -> None:
    task = GeometryLengthMeasure2DTask()
    variants = (
        "segment",
        "triangle",
        "quadrilateral",
        "pentagon",
        "circle_radius",
        "circle_diameter",
        "ellipse_major_axis",
        "ellipse_minor_axis",
    )
    for idx, variant in enumerate(variants):
        out = task.generate(
            7400 + idx,
            params={"query_type": "measure", "shape_variant": str(variant)},
            max_attempts=220,
        )
        trace = out.trace_payload
        assert out.query_type == "measure"
        assert out.answer_gt.type == "integer"
        assert 2 <= int(out.answer_gt.value) <= 8
        assert out.evidence_gt.type == "grid_point_map"
        evidence_map = _assert_grid_point_map(
            out.evidence_gt.value,
            expected_len=len(trace["execution_trace"]["required_evidence_labels"]),
        )
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert trace["query_spec"]["prompt_variant_active_key"] == "answer_and_evidence"
        assert str(trace["execution_trace"]["shape_variant"]) == str(variant)

        entity = trace["scene_ir"]["entities"][0]
        attrs = entity["attrs"]
        required_labels = [str(label) for label in trace["execution_trace"]["required_evidence_labels"]]
        if variant == "segment":
            assert len(evidence_map) == 2
            graph_a = evidence_map[required_labels[0]]
            graph_b = evidence_map[required_labels[1]]
            graph_len = hypot(
                float(graph_b[0]) - float(graph_a[0]),
                float(graph_b[1]) - float(graph_a[1]),
            )
            assert abs(float(graph_len) - float(out.answer_gt.value)) <= 1e-6
            assert str(entity["entity_type"]) == "segment"
            assert int(attrs["length_units"]) == int(out.answer_gt.value)
        elif variant in {"triangle", "quadrilateral", "pentagon"}:
            assert len(evidence_map) == 2
            graph_a = evidence_map[required_labels[0]]
            graph_b = evidence_map[required_labels[1]]
            graph_len = hypot(
                float(graph_b[0]) - float(graph_a[0]),
                float(graph_b[1]) - float(graph_a[1]),
            )
            assert abs(float(graph_len) - float(out.answer_gt.value)) <= 1e-6
            assert str(entity["entity_type"]) == "polygon"
            assert int(attrs["target_side_length_units"]) == int(out.answer_gt.value)
        elif variant in {"circle_radius", "circle_diameter"}:
            assert len(evidence_map) == 1
            assert str(entity["entity_type"]) == "circle"
            expected_kind = "radius" if variant == "circle_radius" else "diameter"
            assert str(attrs["measurement_kind"]) == expected_kind
            origin_x, origin_y, spacing = _graph_origin_and_spacing(trace)
            center = attrs["center"]
            center_grid = [
                int(round((float(center[0]) - float(origin_x)) / float(spacing))),
                int(round((float(origin_y) - float(center[1])) / float(spacing))),
            ]
            assert evidence_map[required_labels[0]] == center_grid
        else:
            assert len(evidence_map) == 2
            graph_a = evidence_map[required_labels[0]]
            graph_b = evidence_map[required_labels[1]]
            graph_len = hypot(
                float(graph_b[0]) - float(graph_a[0]),
                float(graph_b[1]) - float(graph_a[1]),
            )
            assert abs(float(graph_len) - float(out.answer_gt.value)) <= 1e-6
            assert str(entity["entity_type"]) == "ellipse"
            expected_kind = "major_axis" if variant == "ellipse_major_axis" else "minor_axis"
            assert str(attrs["measurement_kind"]) == expected_kind


def test_measurement_shape_variant_balancing_defaults() -> None:
    cases = [
        (
            GeometryAreaMeasure2DTask,
            {"triangle", "quadrilateral", "ellipse"},
            "area_cycle_seed",
        ),
        (
            GeometryPerimeterMeasure2DTask,
            {"triangle", "quadrilateral", "circle"},
            "perimeter_cycle_seed",
        ),
        (
            GeometryLengthMeasure2DTask,
            {
                "segment",
                "triangle",
                "quadrilateral",
                "pentagon",
                "circle_radius",
                "circle_diameter",
                "ellipse_major_axis",
                "ellipse_minor_axis",
            },
            "length_cycle_seed",
        ),
    ]
    for task_cls, expected_variants, seed_ns in cases:
        task = task_cls()
        counts: Counter[str] = Counter()
        for index in range(80):
            out = task.generate(
                hash64(9090, str(seed_ns), index),
                params={"query_type": "measure", "_sampling_index": index},
                max_attempts=220,
            )
            counts[str(out.trace_payload["execution_trace"]["shape_variant"])] += 1
        assert set(counts.keys()) == set(expected_variants)
        assert max(counts.values()) - min(counts.values()) <= 1
