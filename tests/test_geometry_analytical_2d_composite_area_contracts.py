"""Contract tests for geometry analytical_2d composite-area task."""

from __future__ import annotations

import json
from pathlib import Path

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.geometry.analytical_2d.composite_area import GeometryAnalyticalCompositeArea2DTask
from tests.helpers import read_jsonl


def test_geometry_analytical_composite_area_deterministic() -> None:
    task = GeometryAnalyticalCompositeArea2DTask()
    out_a = task.generate(74251, params={}, max_attempts=360)
    out_b = task.generate(74251, params={}, max_attempts=360)
    assert str(out_a.task_variant).strip()
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()
    assert sorted(out_a.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert out_a.prompt == out_a.prompt_variants["answer_and_evidence"]
    assert out_a.answer_gt.type == "integer"
    assert out_a.evidence_gt.type == "measurement_ref_map"


def test_geometry_analytical_composite_area_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_geometry_analytical_2d_composite_area"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_geometry_analytical_2d_composite_area",
        instance_version="v1",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_geometry_analytical_2d_composite_area",
                count=5,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=360,
        sampling_seed=31,
    )
    final_path = build_dataset(config, code_hash="geometry-analytical-composite-area-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 5
    assert all(record["task_group"] == "analytical_2d" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_geometry_analytical_2d_composite_area"]) == 5

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
