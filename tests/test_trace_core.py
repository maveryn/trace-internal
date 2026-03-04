"""Core TRACE regression tests for determinism and build contracts."""

from __future__ import annotations

import json
from pathlib import Path

from trace.core.canonical import CanonicalizationError, canonical_json_bytes
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.identity import compute_instance_id
from trace.core.builder import build_dataset
from trace.tasks.tile_shortest_path import TileShortestPathTask


def _read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_canonical_non_finite_rejected() -> None:
    try:
        canonical_json_bytes({"x": float("inf")})
        assert False, "expected canonicalization failure"
    except CanonicalizationError as exc:
        assert exc.code == "schema_non_finite_number"


def test_tile_shortest_path_deterministic() -> None:
    task = TileShortestPathTask()
    params = {"rows": 7, "cols": 7, "min_shortest_len": 5, "evidence_type": "point_path"}

    out_a = task.generate(123456, params=params, max_attempts=120)
    out_b = task.generate(123456, params=params, max_attempts=120)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["witness_symbolic"] == out_b.trace_payload["witness_symbolic"]
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_instance_id_ignores_image_path() -> None:
    base = {
        "instance_version": "v1",
        "instance_seed": 42,
        "domain": "tile",
        "task_group": "path",
        "task": "tile_shortest_path",
        "prompt": "p",
        "images": [{"image_id": "img0", "format": "png", "image_hash": "blake3:abc", "path": "a.png"}],
        "answer_gt": {"type": "integer", "value": 5},
        "evidence_gt": {"type": "point_path", "value": [[1.0, 2.0]]},
        "versions": {"dsl_spec_version": "v1"},
    }
    variant = dict(base)
    variant["images"] = [{"image_id": "img0", "format": "png", "image_hash": "blake3:abc", "path": "other/path.png"}]
    assert compute_instance_id(base) == compute_instance_id(variant)


def test_build_dataset_end_to_end(tmp_path: Path) -> None:
    output_root = tmp_path / "out"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="test_build",
        instance_version="v1",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="tile_shortest_path",
                count=4,
                params={"rows": 7, "cols": 7, "min_shortest_len": 5, "evidence_type": "point_path"},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=120,
        sampling_seed=7,
    )

    final_path = build_dataset(config, code_hash="test")
    assert final_path.exists()

    train_instances = _read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_instances) == 4
    for instance in train_instances:
        assert instance["trace_ref"]["shard_id"] == "trace_shard_0001.jsonl.zst"
        assert not Path(instance["images"][0]["path"]).is_absolute()
        assert instance["answer_gt"]["type"] == "integer"
        assert instance["evidence_gt"]["type"] == "point_path"

    validation_report = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation_report["total_errors"] == 0

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert build_report["dataset_id"].startswith("blake3:")
    assert build_report["accepted_counts_by_task"]["tile_shortest_path"] == 4
