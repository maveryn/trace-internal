"""Contract tests for clock-readout task."""

from __future__ import annotations

import json
from pathlib import Path

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.puzzles.clock.readout import PuzzlesClockOffsetReadoutTask
from tests.helpers import read_jsonl


def test_puzzles_clock_readout_deterministic() -> None:
    task = PuzzlesClockOffsetReadoutTask()
    params = {
        "offset_unit": "minutes",
        "offset_direction": "after",
        "scene_variant": "minimal",
        "style_variant": "accented",
        "accent_color_name": "purple",
        "delta_minutes": 30,
    }
    out_a = task.generate(20440, params=params, max_attempts=20)
    out_b = task.generate(20440, params=params, max_attempts=20)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
    assert out_a.answer_gt.type == "string"
    assert out_a.evidence_gt.type == "bbox_set"


def test_puzzles_clock_offset_readout_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_puzzles__analog_clock__offset_readout"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_puzzles__analog_clock__offset_readout",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_puzzles__analog_clock__offset_readout",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=20,
        sampling_seed=29,
    )
    final_path = build_dataset(config, code_hash="puzzles-clock-offset-readout-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "puzzles" for record in train_records)
    assert all(record["task_group"] == "clock" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_puzzles__analog_clock__offset_readout"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
