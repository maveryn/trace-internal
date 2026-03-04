"""Tests for geometry_angle_value_query task behavior."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.geometry.measurement.angle_value_query import GeometryAngleValueQueryTask
from trace.tasks.geometry.shared.value_queries import run_value_query


def _read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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
        expected = run_value_query(values_by_id, query_type=query_type, target_x=90)
        prompt_variant = trace["query_spec"]["prompt_variant"]

        assert out.query_type == query_type
        assert out.answer_gt.type == "integer"
        assert int(out.answer_gt.value) == int(expected.answer_value)
        assert prompt_variant["prompt_bundle_id"] == "geometry_measurement_v1"
        assert prompt_variant["task_type_key"] == "angle_measurement"
        assert prompt_variant["query_type_key"] == query_type

        if query_type == "difference_max_min":
            assert out.evidence_gt.type == "point_path"
            assert len(out.evidence_gt.value) == 2
            assert trace["witness_symbolic"]["type"] == "id_path"
        else:
            assert out.evidence_gt.type == "point_set"
            assert len(out.evidence_gt.value) == 1
            assert trace["witness_symbolic"]["type"] == "id_set"


def test_geometry_angle_task_deterministic_for_fixed_seed() -> None:
    task = GeometryAngleValueQueryTask()
    params = {
        "query_type": "closest_to_x",
        "candidate_count": 7,
        "angle_step": 15,
        "target_x": 90,
    }
    out_a = task.generate(12345, params=params, max_attempts=200)
    out_b = task.generate(12345, params=params, max_attempts=200)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()


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

    train_records = _read_jsonl(final_path / "train_instances.jsonl")
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
