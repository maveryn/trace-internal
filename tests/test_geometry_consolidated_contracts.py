"""Contract tests for consolidated geometry tasks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.geometry.graph_paper.angle_extremum_label import GeometryComparisonValueTask
from trace.tasks.geometry.graph_paper.angle_type_count import GeometryCountingValueTask
from trace.tasks.geometry.graph_paper.angle_value import GeometryMeasurementValueTask
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("task_cls", "params"),
    (
        (GeometryMeasurementValueTask, {"scene_variant": "circle", "query_id": "perimeter"}),
        (
            GeometryComparisonValueTask,
            {"scene_variant": "rectangle", "query_id": "area_extremum", "extremum_direction": "largest"},
        ),
        (
            GeometryCountingValueTask,
            {"scene_variant": "triangle", "query_id": "triangle_type_count", "triangle_type": "right"},
        ),
    ),
)
def test_geometry_consolidated_tasks_are_deterministic(task_cls, params) -> None:
    task = task_cls()
    out_a = task.generate(23101, params=params, max_attempts=40)
    out_b = task.generate(23101, params=params, max_attempts=40)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


@pytest.mark.parametrize(
    ("task_cls", "params"),
    (
        (GeometryMeasurementValueTask, {"scene_variant": "circle", "query_id": "perimeter"}),
        (GeometryComparisonValueTask, {"scene_variant": "rectangle", "query_id": "largest_area"}),
        (
            GeometryCountingValueTask,
            {"scene_variant": "triangle", "query_id": "triangle_type_count", "triangle_type": "right"},
        ),
    ),
)
def test_geometry_consolidated_tasks_accept_query_id_alias(task_cls, params) -> None:
    task = task_cls()
    out = task.generate(23121, params=params, max_attempts=40)
    expected_variant = "area_extremum" if params["query_id"] == "largest_area" else params["query_id"]
    assert out.query_id == expected_variant


@pytest.mark.parametrize(
    ("task_id", "scene_id"),
    (
        ("task_geometry__graph_paper__polygon_area_value", "measurement"),
        ("task_geometry__graph_paper__area_extremum_label", "comparison"),
        ("task_geometry__graph_paper__triangle_type_count", "counting"),
        ("task_geometry__function_panels__function_status_label", "analytical"),
        ("task_geometry__function_panels__intersection_property_label", "analytical"),
        ("task_geometry__circle_theorem__secant_secant_length_value", "circle"),
        ("task_geometry__coordinate_plane__segment_relation_count", "coordinate"),
        ("task_geometry__function_graph__extremum_count_turning_point_count", "graphing"),
        ("task_geometry__function_graph__reference_line_crossing_count", "graphing"),
        ("task_geometry__shape_gallery__congruent_count", "similarity"),
        ("task_geometry__shape_gallery__reflection_match", "transformation"),
    ),
)
def test_geometry_consolidated_build_smoke(task_id: str, scene_id: str, tmp_path: Path) -> None:
    output_root = tmp_path / task_id
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name=f"build_smoke_{task_id}",
        instance_version="v0",
        image_format="png",
        tasks=[BuildTaskConfig(task_id=task_id, count=3, params={})],
        strict_repro=False,
        max_attempts_per_instance=40,
        sampling_seed=31,
    )
    final_path = build_dataset(config, code_hash=f"{task_id}-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 3
    assert all(record["domain"] == "geometry" for record in train_records)
    assert all(record["scene_id"] == scene_id for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"][task_id]) == 3

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
