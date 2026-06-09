"""Contract tests for icon reference-predicate counting."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.icons.counting.reference_match_count import IconsReferenceCanvasReferenceAttributeMatchCountTask
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("task_cls", "query_id"),
    (
        (IconsReferenceCanvasReferenceAttributeMatchCountTask, "match_type"),
        (IconsReferenceCanvasReferenceAttributeMatchCountTask, "match_color"),
        (IconsReferenceCanvasReferenceAttributeMatchCountTask, "match_rotation"),
        (IconsReferenceCanvasReferenceAttributeMatchCountTask, "match_type_color_rotation"),
    ),
)
def test_icons_counting_attribute_match_count_is_deterministic(task_cls, query_id: str) -> None:
    task = task_cls()
    params = {"query_id": query_id, "object_count": 8, "target_count": 3}
    out_a = task.generate(24020, params=params, max_attempts=200)
    out_b = task.generate(24020, params=params, max_attempts=200)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
    assert out_a.query_id == query_id
    assert sorted(out_a.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]


@pytest.mark.parametrize(
    "task_id",
    ("task_icons__reference_canvas__reference_attribute_match_count",),
)
def test_icons_counting_attribute_match_count_build_smoke(tmp_path: Path, task_id: str) -> None:
    output_root = tmp_path / task_id
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name=f"build_smoke_{task_id}",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id=str(task_id),
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=200,
        sampling_seed=31,
    )
    final_path = build_dataset(config, code_hash="icons-counting-reference-match-count-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "icons" for record in train_records)
    assert all(record["task_group"] == "counting" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"][str(task_id)]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
