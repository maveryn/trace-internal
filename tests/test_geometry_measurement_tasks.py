"""Behavior tests for single-object geometry measurement tasks."""

from __future__ import annotations

from collections import Counter
from math import hypot

from trace.core.seed import hash64
from trace.tasks.geometry.measurement.angle import GeometryAngleMeasureTask
from trace.tasks.geometry.measurement.polygon_area import GeometryPolygonAreaMeasureTask
from trace.tasks.geometry.measurement.polygon_perimeter import GeometryPolygonPerimeterMeasureTask


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


def test_angle_measure_outputs_expected_contract() -> None:
    task = GeometryAngleMeasureTask()
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
        assert out.evidence_gt.type == "grid_point_set"
        assert len(out.evidence_gt.value) == 3
        assert all(
            isinstance(point, list) and len(point) == 2 and all(isinstance(coord, int) for coord in point)
            for point in out.evidence_gt.value
        )
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
        projected = trace["projected_evidence"]["point_set"]
        projected_grid = trace["projected_evidence"]["grid_point_set"]
        for pixel_point, graph_point in zip(projected, projected_grid):
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
        expected_graph_evidence = [
            [
                int(round((float(arm_a[0]) - float(origin_x)) / float(spacing))),
                int(round((float(origin_y) - float(arm_a[1])) / float(spacing))),
            ],
            [
                int(round((float(vertex[0]) - float(origin_x)) / float(spacing))),
                int(round((float(origin_y) - float(vertex[1])) / float(spacing))),
            ],
            [
                int(round((float(arm_b[0]) - float(origin_x)) / float(spacing))),
                int(round((float(origin_y) - float(arm_b[1])) / float(spacing))),
            ],
        ]
        assert out.evidence_gt.value == expected_graph_evidence
        arm_a_graph = _graph_point(arm_a, origin_x=origin_x, origin_y=origin_y, spacing=spacing)
        vertex_graph = _graph_point(vertex, origin_x=origin_x, origin_y=origin_y, spacing=spacing)
        arm_b_graph = _graph_point(arm_b, origin_x=origin_x, origin_y=origin_y, spacing=spacing)
        assert hypot(arm_a_graph[0] - vertex_graph[0], arm_a_graph[1] - vertex_graph[1]) >= 2.0 - 1e-6
        assert hypot(arm_b_graph[0] - vertex_graph[0], arm_b_graph[1] - vertex_graph[1]) >= 2.0 - 1e-6


def test_angle_measure_label_font_scales_with_canvas() -> None:
    task = GeometryAngleMeasureTask()
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


def test_polygon_area_quadrilateral_structural_diversity() -> None:
    task = GeometryPolygonAreaMeasureTask()
    template_ids = set()
    for index in range(16):
        out = task.generate(
            5100 + index,
            params={"query_type": "measure", "allowed_sides": [4]},
            max_attempts=220,
        )
        template_ids.add(str(out.trace_payload["execution_trace"]["template_id"]))
    assert len(template_ids) >= 4


def test_angle_measure_balanced_sampling_defaults_and_index() -> None:
    task = GeometryAngleMeasureTask()
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
        (GeometryPolygonAreaMeasureTask, "task_geometry_measurement_polygon_area", "area_square_units"),
        (GeometryPolygonPerimeterMeasureTask, "task_geometry_measurement_polygon_perimeter", "perimeter_units"),
    ]
    for task_cls, task_id, answer_attr in cases:
        task = task_cls()
        out = task.generate(
            3300,
            params={"query_type": "measure", "allowed_sides": [3, 4, 5]},
            max_attempts=180,
        )
        trace = out.trace_payload
        assert out.query_type == "measure"
        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "grid_point_set"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert trace["query_spec"]["prompt_variant_active_key"] == "answer_and_evidence"

        entity = trace["scene_ir"]["entities"][0]
        attrs = entity["attrs"]
        assert str(task_id).startswith("task_geometry_measurement_polygon_")
        assert int(out.answer_gt.value) == int(attrs[answer_attr])
        assert len(out.evidence_gt.value) == int(attrs["polygon_sides"])

        origin_x, origin_y, spacing = _graph_origin_and_spacing(trace)
        point_set = trace["projected_evidence"]["point_set"]
        grid_point_set = trace["projected_evidence"]["grid_point_set"]
        for pixel_point, graph_point in zip(point_set, grid_point_set):
            expected_x = int(round((float(pixel_point[0]) - float(origin_x)) / float(spacing)))
            expected_y = int(round((float(origin_y) - float(pixel_point[1])) / float(spacing)))
            assert graph_point == [expected_x, expected_y]
