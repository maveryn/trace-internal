"""Contract tests for consolidated icon structured-violation task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.icons.pattern.structured_violation import IconsPatternStructuredViolationTask
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    "task_variant",
    ("row_rotation_violation", "grid_rotation_violation", "grid_size_violation"),
)
def test_icons_pattern_structured_violation_is_deterministic(task_variant: str) -> None:
    task = IconsPatternStructuredViolationTask()
    out_a = task.generate(24120, params={"task_variant": task_variant}, max_attempts=200)
    out_b = task.generate(24120, params={"task_variant": task_variant}, max_attempts=200)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
    assert out_a.task_variant == task_variant


def test_icons_pattern_structured_violation_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_icons_pattern_structured_violation"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_icons_pattern_structured_violation",
        instance_version="v1",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_icons_pattern_structured_violation",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=200,
        sampling_seed=31,
    )
    final_path = build_dataset(config, code_hash="icons-pattern-structured-violation-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "icons" for record in train_records)
    assert all(record["task_group"] == "pattern" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_icons_pattern_structured_violation"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
