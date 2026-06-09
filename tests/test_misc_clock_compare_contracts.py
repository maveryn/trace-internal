"""Contract tests for clock-compare task."""

from __future__ import annotations

import json
from pathlib import Path

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.misc.clock.compare import MiscClockCompareTask
from tests.helpers import read_jsonl


def test_misc_clock_compare_deterministic() -> None:
    task = MiscClockCompareTask()
    params = {
        "query_id": "earliest_time",
        "scene_variant": "minimal",
        "style_variant": "accented",
        "accent_color_name": "purple",
    }
    out_a = task.generate(20640, params=params, max_attempts=20)
    out_b = task.generate(20640, params=params, max_attempts=20)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_misc_clock_compare_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_misc__clock_collection__compare"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_misc__clock_collection__compare",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_misc__clock_collection__compare",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=20,
        sampling_seed=31,
    )
    final_path = build_dataset(config, code_hash="misc-clock-compare-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "misc" for record in train_records)
    assert all(record["task_group"] == "clock" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_misc__clock_collection__compare"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
