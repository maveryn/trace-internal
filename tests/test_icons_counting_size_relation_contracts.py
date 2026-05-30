"""Contract tests for icon counting size-relation task."""

from __future__ import annotations

import json
from pathlib import Path

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.icons.counting.size_relation import IconsCountingSizeRelationTask
from tests.helpers import read_jsonl


def test_icons_counting_size_relation_deterministic() -> None:
    task = IconsCountingSizeRelationTask()
    out_a = task.generate(14620, params={}, max_attempts=200)
    out_b = task.generate(14620, params={}, max_attempts=200)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()
    assert sorted(out_a.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert out_a.prompt == out_a.prompt_variants["answer_and_evidence"]
    assert out_a.answer_gt.type == "integer"
    assert out_a.evidence_gt.type == "bbox_set"
    assert out_a.trace_payload["projected_evidence"]["type"] == "bbox_set"
    assert out_a.trace_payload["projected_evidence"]["bbox_set"] == out_a.evidence_gt.value
    assert out_a.trace_payload["projected_evidence"]["pixel_bbox_set"] == out_a.evidence_gt.value
    assert len(out_a.trace_payload["projected_evidence"]["pixel_point_set"]) == len(out_a.evidence_gt.value)


def test_icons_counting_size_relation_build_smoke(tmp_path: Path) -> None:
    task_id = "task_icons__reference_canvas__reference_predicate_count"
    output_root = tmp_path / task_id
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name=f"build_smoke_{task_id}",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id=task_id,
                count=4,
                params={"query_id": "size_larger"},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=200,
        sampling_seed=31,
    )
    final_path = build_dataset(config, code_hash="icons-counting-size-relation-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "icons" for record in train_records)
    assert all(record["task_group"] == "counting" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"][task_id]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
