from __future__ import annotations

import json
from pathlib import Path

import pyarrow.parquet as pq

from trace.core.rlvr_export import build_rlvr_row, export_trace_dataset_to_rlvr


def _write_trace_dataset(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    dataset_root = tmp_path / "trace_dataset"
    image_path = dataset_root / "images" / "geometry" / "task_geometry_coordinate_relation" / "000000.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"fake-image")

    train_record = {
        "instance_id": "inst-001",
        "domain": "geometry",
        "task_group": "coordinate",
        "task": "task_geometry_coordinate_relation",
        "prompt": "active prompt",
        "prompt_variants": {
            "answer_only": "answer only prompt",
            "answer_and_evidence": "answer and evidence prompt",
        },
        "images": [
            {
                "image_id": "img-001",
                "format": "png",
                "image_hash": "hash-001",
                "path": "images/geometry/task_geometry_coordinate_relation/000000.png",
            }
        ],
        "answer_gt": {"type": "integer", "value": 3},
        "evidence_gt": {"type": "graph_point_set", "value": [[1, 2], [3, 4], [5, 6]]},
        "reward_contract": {
            "reward_contract_version": "v1",
            "answer": {"id": "answer_exact_match_v1", "type": "integer"},
            "evidence": {"id": "point_set_match_v1", "type": "graph_point_set"},
        },
        "trace_ref": {"shard_id": "trace-0001", "line_index": 0, "trace_record_hash": "trace-hash"},
    }
    train_instances_path = dataset_root / "train_instances.jsonl"
    train_instances_path.parent.mkdir(parents=True, exist_ok=True)
    train_instances_path.write_text(json.dumps(train_record) + "\n", encoding="utf-8")
    return dataset_root, train_record


def test_build_rlvr_row_uses_requested_prompt_variant_and_relative_image_paths(tmp_path: Path) -> None:
    dataset_root, train_record = _write_trace_dataset(tmp_path)
    export_parent = tmp_path / "exports" / "jsonl"
    export_parent.mkdir(parents=True, exist_ok=True)

    row = build_rlvr_row(
        train_record,
        dataset_root=dataset_root,
        output_parent=export_parent,
        prompt_variant="answer_only",
        image_path_mode="relative",
    )

    assert row["uid"] == "inst-001"
    assert row["instance_id"] == "inst-001"
    assert row["prompt"] == "answer only prompt"
    assert row["prompt_mode"] == "answer_only"
    assert row["images"] == [
        {"path": "../../trace_dataset/images/geometry/task_geometry_coordinate_relation/000000.png"}
    ]
    assert row["answer_gt"] == train_record["answer_gt"]
    assert row["evidence_gt"] == train_record["evidence_gt"]
    assert row["reward_contract"] == train_record["reward_contract"]


def test_export_trace_dataset_to_rlvr_jsonl_and_parquet(tmp_path: Path) -> None:
    dataset_root, _ = _write_trace_dataset(tmp_path)

    jsonl_path = tmp_path / "rlvr_jsonl"
    jsonl_result = export_trace_dataset_to_rlvr(
        dataset_root,
        jsonl_path,
        prompt_variant="answer_and_evidence",
        image_path_mode="relative",
    )
    assert jsonl_result.output_path.name == "train.jsonl"
    jsonl_rows = [
        json.loads(line)
        for line in jsonl_result.output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(jsonl_rows) == 1
    assert jsonl_rows[0]["prompt"] == "answer and evidence prompt"
    assert jsonl_rows[0]["images"] == [
        {"path": "../trace_dataset/images/geometry/task_geometry_coordinate_relation/000000.png"}
    ]

    parquet_path = tmp_path / "exports" / "trace_train.parquet"
    parquet_result = export_trace_dataset_to_rlvr(
        dataset_root,
        parquet_path,
        output_format="parquet",
        prompt_variant="active",
        image_path_mode="absolute",
    )
    assert parquet_result.output_path == parquet_path.resolve()
    table = pq.read_table(parquet_result.output_path)
    parquet_rows = table.to_pylist()
    assert len(parquet_rows) == 1
    assert parquet_rows[0]["prompt"] == "active prompt"
    assert parquet_rows[0]["images"] == [
        {
            "path": str(
                (
                    dataset_root
                    / "images"
                    / "geometry"
                    / "task_geometry_coordinate_relation"
                    / "000000.png"
                ).resolve()
            )
        }
    ]
