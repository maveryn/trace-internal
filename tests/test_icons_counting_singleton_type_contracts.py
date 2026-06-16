"""Contract tests for icon singleton-type counting task."""

from __future__ import annotations

import json
from pathlib import Path

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.icons.icon_field.type_frequency_count import IconsIconFieldTypeFrequencyCountTask
from tests.helpers import read_jsonl


def test_icons_counting_singleton_type_deterministic() -> None:
    task = IconsIconFieldTypeFrequencyCountTask()
    params = {"query_id": "singleton_type_count"}
    out_a = task.generate(18320, params=params, max_attempts=200)
    out_b = task.generate(18320, params=params, max_attempts=200)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()
    assert sorted(out_a.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
    assert out_a.prompt == out_a.prompt_variants["answer_and_annotation"]
    assert out_a.answer_gt.type == "integer"
    assert out_a.annotation_gt.type == "point_set"


def test_icons_counting_most_frequent_type_deterministic() -> None:
    task = IconsIconFieldTypeFrequencyCountTask()
    params = {"query_id": "most_frequent_type_count"}
    out_a = task.generate(18321, params=params, max_attempts=200)
    out_b = task.generate(18321, params=params, max_attempts=200)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()
    assert sorted(out_a.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
    assert out_a.prompt == out_a.prompt_variants["answer_and_annotation"]
    assert out_a.scene_id == "icon_field"
    assert out_a.query_id == "most_frequent_type_count"
    assert out_a.answer_gt.type == "integer"
    assert out_a.annotation_gt.type == "point_set"

    frequencies = out_a.trace_payload["execution_trace"]["type_frequencies"]
    max_frequency = max(int(value) for value in frequencies.values())
    assert int(out_a.answer_gt.value) == int(max_frequency)
    assert sum(1 for value in frequencies.values() if int(value) == int(max_frequency)) == 1
    assert len(out_a.annotation_gt.value) == int(out_a.answer_gt.value)


def test_icons_counting_singleton_type_build_smoke(tmp_path: Path) -> None:
    task_id = "task_icons__icon_field__type_frequency_count"
    output_root = tmp_path / task_id
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_icons__icon_field__type_frequency_count",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id=task_id,
                count=8,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=200,
        sampling_seed=31,
    )
    final_path = build_dataset(config, code_hash="icons-counting-frequency-type-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 8
    assert all(record["domain"] == "icons" for record in train_records)
    assert all(record["scene_id"] == "icon_field" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"][task_id]) == 8

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
