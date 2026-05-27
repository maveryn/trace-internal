"""Contract tests for graph source/sink counting task."""

from __future__ import annotations

import json
from pathlib import Path

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.graph.counting.source_sink_count import GraphCountingSourceSinkCountTask
from tests.helpers import read_jsonl


def test_graph_counting_source_sink_count_deterministic() -> None:
    task = GraphCountingSourceSinkCountTask()
    out_a = task.generate(20520, params={}, max_attempts=200)
    out_b = task.generate(20520, params={}, max_attempts=200)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()
    assert sorted(out_a.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert out_a.prompt == out_a.prompt_variants["answer_and_evidence"]
    assert out_a.answer_gt.type == "integer"
    assert out_a.evidence_gt.type == "point_set"


def test_graph_counting_source_sink_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "graph_source_sink_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_graph_source_sink_count",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_graph__node_link__degree_predicate_count",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=200,
        sampling_seed=31,
    )
    final_path = build_dataset(config, code_hash="graph-counting-source-sink-count-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "graph" for record in train_records)
    assert all(record["task_group"] == "counting" for record in train_records)
    assert all(record["scene_id"] == "node_link" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_graph__node_link__degree_predicate_count"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
