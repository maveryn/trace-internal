"""Tests for geometry_angle_value_query task behavior."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.shared.layout_constraints import mapping_entities_have_min_clearance
from trace.tasks.shared.value_query_sampling import feasible_answer_values
from trace.tasks.shared.value_queries import run_value_query
from trace.tasks.geometry.measurement.angle_value_query import GeometryAngleValueQueryTask
from tests.helpers import read_jsonl


def test_query_variants_emit_expected_answer_and_evidence() -> None:
    task = GeometryAngleValueQueryTask()
    query_types = task.supported_query_types({})

    for idx, query_type in enumerate(query_types):
        out = task.generate(
            9000 + idx,
            params={
                "query_type": query_type,
                "candidate_count": 7,
                "angle_step": 15,
                "target_x": 90,
            },
            max_attempts=200,
        )
        trace = out.trace_payload
        values_by_id = trace["execution_trace"]["candidate_values_by_id"]
        expected = run_value_query(
            values_by_id,
            query_type=query_type,
            target_x=90,
            require_unique_values=False,
        )
        prompt_variant = trace["query_spec"]["prompt_variant"]
        sampling_meta = trace["execution_trace"]

        assert out.query_type == query_type
        assert out.answer_gt.type == "integer"
        assert isinstance(out.answer_gt.value, int)
        assert int(out.answer_gt.value) == int(expected.answer_value)
        assert sampling_meta["answer_sampling_policy"] == "uniform_feasible_by_query"
        assert int(sampling_meta["answer_target"]) == int(out.answer_gt.value)
        assert int(out.answer_gt.value) in [int(value) for value in sampling_meta["feasible_answer_values"]]
        for selected_value in expected.selected_values:
            num_matches = sum(1 for value in values_by_id.values() if int(value) == int(selected_value))
            assert num_matches == 1
        assert prompt_variant["prompt_bundle_id"] == "geometry_measurement_v1"
        assert prompt_variant["task_type_key"] == "measurement_value_query"
        assert prompt_variant["query_type_key"] == query_type
        assert "integer answer" in out.prompt
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert out.prompt == out.prompt_variants["answer_and_evidence"]
        prompt_variants_meta = trace["query_spec"]["prompt_variants"]
        assert sorted(prompt_variants_meta.keys()) == ["answer_and_evidence", "answer_only"]
        assert trace["query_spec"]["prompt_variant_active_key"] == "answer_and_evidence"

        background_meta = trace["render_spec"]["background_style"]
        assert background_meta["selected_style"] == "graph_paper"
        style_spec = background_meta["style_spec"]
        assert list(style_spec["base_color"]) == [255, 255, 255]
        assert bool(style_spec["axis_enabled"]) is True
        assert list(style_spec["axis_color"]) == [176, 184, 198]
        assert int(style_spec["axis_line_width"]) >= 2
        assert bool(style_spec["center_point_enabled"]) is True
        assert int(style_spec["center_point_radius"]) >= 1
        spacing = int(style_spec["spacing"])
        canvas_size = int(trace["render_spec"]["canvas_size"])
        assert 512 <= canvas_size <= 1024
        assert spacing >= 4
        graph_frame = trace["render_spec"]["graph_coordinate_frame"]
        assert graph_frame["coord_space"] == "graph_unit"
        assert graph_frame["x_positive"] == "right"
        assert graph_frame["y_positive"] == "up"
        origin_x, origin_y = (int(graph_frame["origin_pixel"][0]), int(graph_frame["origin_pixel"][1]))
        assert int(graph_frame["spacing_px"]) == spacing
        assert 12 <= int(graph_frame["target_cells_x"]) <= 24
        assert 12 <= int(graph_frame["target_cells_y"]) <= 24
        assert int(graph_frame["target_cells_x"]) == int(graph_frame["target_cells_y"])
        assert int(graph_frame["full_cells_x"]) == int(canvas_size // spacing)
        assert int(graph_frame["full_cells_y"]) == int(canvas_size // spacing)
        assert bool(graph_frame["partial_edge_cells"]) is bool(int(canvas_size) % int(spacing))
        assert origin_x % spacing == 0
        assert origin_y % spacing == 0
        grid_meta = trace["render_spec"]["graph_paper_grid"]
        assert int(grid_meta["target_cells_x"]) == int(graph_frame["target_cells_x"])
        assert int(grid_meta["target_cells_y"]) == int(graph_frame["target_cells_y"])
        assert int(grid_meta["full_cells_x"]) == int(graph_frame["full_cells_x"])
        assert int(grid_meta["full_cells_y"]) == int(graph_frame["full_cells_y"])
        assert bool(grid_meta["partial_edge_cells"]) is bool(graph_frame["partial_edge_cells"])
        assert int(grid_meta["spacing_px"]) == int(graph_frame["spacing_px"])
        for entity in trace["scene_ir"]["entities"]:
            attrs = entity["attrs"]
            vertex = attrs["vertex"]
            assert float(vertex[0]) % float(spacing) == pytest.approx(0.0, abs=1e-6)
            assert float(vertex[1]) % float(spacing) == pytest.approx(0.0, abs=1e-6)
            ray_1 = attrs["ray_1"]
            ray_2 = attrs["ray_2"]
            axis_eps = 1e-6
            ray_1_axis_aligned = (
                abs(float(ray_1[0]) - float(vertex[0])) <= axis_eps
                or abs(float(ray_1[1]) - float(vertex[1])) <= axis_eps
            )
            ray_2_axis_aligned = (
                abs(float(ray_2[0]) - float(vertex[0])) <= axis_eps
                or abs(float(ray_2[1]) - float(vertex[1])) <= axis_eps
            )
            assert ray_1_axis_aligned or ray_2_axis_aligned
        entity_map = {entity["entity_id"]: entity["attrs"] for entity in trace["scene_ir"]["entities"]}
        assert mapping_entities_have_min_clearance(
            entity_map,
            point_keys=("vertex", "ray_1", "ray_2"),
            segment_keys=(("vertex", "ray_1"), ("vertex", "ray_2")),
            min_clearance=float(spacing),
        )
        projected = trace["projected_evidence"]
        for pixel_point, graph_point in zip(projected["point_set"], projected["grid_point_set"]):
            expected_x = int(round((float(pixel_point[0]) - float(origin_x)) / float(spacing)))
            expected_y = int(round((float(origin_y) - float(pixel_point[1])) / float(spacing)))
            assert graph_point == [expected_x, expected_y]
            assert all(isinstance(coord, int) for coord in graph_point)

        if query_type == "difference_max_min":
            assert out.evidence_gt.type == "grid_point_path"
            assert len(out.evidence_gt.value) == 2
            assert out.evidence_gt.value == projected["grid_point_path"]
            assert trace["witness_symbolic"]["type"] == "id_path"
        else:
            assert out.evidence_gt.type == "grid_point_set"
            assert len(out.evidence_gt.value) == 1
            assert out.evidence_gt.value == projected["grid_point_set"][:1]
            assert trace["witness_symbolic"]["type"] == "id_set"


def test_feasible_answer_values_with_duplicate_distractors() -> None:
    candidates = list(range(15, 166, 15))
    expected_by_query = {
        "min": [15, 30, 45, 60, 75, 90, 105, 120, 135, 150],
        "max": [30, 45, 60, 75, 90, 105, 120, 135, 150, 165],
        "median": [30, 45, 60, 75, 90, 105, 120, 135, 150],
        "closest_to_x": [30, 45, 60, 75, 90, 105, 120, 135, 150],
        "smallest_above_x": [105, 120, 135, 150, 165],
        "largest_below_x": [15, 30, 45, 60, 75],
        "difference_max_min": [30, 45, 60, 75, 90, 105, 120, 135, 150],
    }
    for query_type, expected in expected_by_query.items():
        feasible = feasible_answer_values(
            query_type=query_type,
            candidates=candidates,
            candidate_count=7,
            target_x=90,
            allow_duplicate_distractors=True,
        )
        assert feasible == expected


def test_geometry_angle_task_deterministic_for_fixed_seed() -> None:
    task = GeometryAngleValueQueryTask()
    params = {
        "query_type": "closest_to_x",
        "angle_step": 15,
        "target_x": 90,
    }
    out_a = task.generate(12345, params=params, max_attempts=200)
    out_b = task.generate(12345, params=params, max_attempts=200)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()
    candidate_count = int(out_a.trace_payload["query_spec"]["params"]["candidate_count"])
    assert 3 <= candidate_count <= 7
    canvas_size = int(out_a.trace_payload["render_spec"]["canvas_size"])
    assert 512 <= canvas_size <= 1024


def test_geometry_angle_build_integration(tmp_path: Path) -> None:
    output_root = tmp_path / "out"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="geometry_angle_build",
        instance_version="v1",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="geometry_angle_value_query",
                count=10,
                params={"candidate_count": 7, "angle_step": 15, "target_x": 90},
                query_weights={
                    "min": 1.0,
                    "max": 1.0,
                    "median": 1.0,
                    "closest_to_x": 1.0,
                    "smallest_above_x": 1.0,
                    "largest_below_x": 1.0,
                    "difference_max_min": 1.0,
                },
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=200,
        sampling_seed=13,
    )

    final_path = build_dataset(config, code_hash="geom-test")
    assert final_path.exists()

    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 10
    assert all(record["task_group"] == "measurement" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    query_counts = build_report["query_type_accepted_counts_by_task"]["geometry_angle_value_query"]
    assert sum(int(v) for v in query_counts.values()) == 10

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0


def test_geometry_angle_failure_edge_conditions() -> None:
    task = GeometryAngleValueQueryTask()
    failure_cases = [
        (
            321,
            {
                "query_type": "smallest_above_x",
                "candidate_count": 5,
                "min_angle": 15,
                "max_angle": 75,
                "angle_step": 15,
                "target_x": 200,
            },
        ),
        (
            654,
            {
                "query_type": "closest_to_x",
                "candidate_count": 2,
                "min_angle": 45,
                "max_angle": 135,
                "angle_step": 90,
                "target_x": 90,
            },
        ),
    ]
    for instance_seed, params in failure_cases:
        with pytest.raises(RuntimeError, match="failed to generate geometry_angle_value_query instance"):
            task.generate(
                instance_seed,
                params=params,
                max_attempts=25,
            )
