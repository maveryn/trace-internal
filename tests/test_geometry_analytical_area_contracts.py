"""Contract tests for geometry analytical_2d area task."""

from __future__ import annotations

import json
from pathlib import Path

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.geometry.analytical_2d.area import GeometryAnalyticalArea2DTask
from tests.helpers import read_jsonl


def test_geometry_analytical_area_deterministic() -> None:
    task = GeometryAnalyticalArea2DTask()
    out_a = task.generate(73011, params={"query_type": "measure"}, max_attempts=260)
    out_b = task.generate(73011, params={"query_type": "measure"}, max_attempts=260)
    assert out_a.query_type == "measure"
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()
    assert sorted(out_a.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert out_a.prompt == out_a.prompt_variants["answer_and_evidence"]
    assert out_a.evidence_gt.type == "measurement_ref_map"
    if out_a.answer_gt.type == "pi_expression":
        assert str(out_a.answer_gt.value).endswith("π")
    else:
        assert out_a.answer_gt.type == "integer"
        assert isinstance(out_a.answer_gt.value, int)


def test_geometry_analytical_area_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_geometry_analytical_2d_area"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_geometry_analytical_2d_area",
        instance_version="v1",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_geometry_analytical_2d_area",
                count=6,
                params={"query_type": "measure"},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=260,
        sampling_seed=23,
    )
    final_path = build_dataset(config, code_hash="geometry-analytical-area-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 6
    assert all(record["task_group"] == "analytical_2d" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    query_counts = build_report["query_type_accepted_counts_by_task"]["task_geometry_analytical_2d_area"]
    assert sum(int(value) for value in query_counts.values()) == 6
    assert set(query_counts.keys()) == {"measure"}

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
