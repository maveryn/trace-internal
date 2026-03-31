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
        "task_complexity": {
            "complexity_score": 0.6,
            "complexity_components": {"reasoning_load": 0.6},
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
    assert row["complexity_score"] == 0.6
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
    assert jsonl_rows[0]["complexity_score"] == 0.6
    assert jsonl_rows[0]["difficulty_bin"] == 0
    assert jsonl_rows[0]["bucket_id_str"] == "task_geometry_coordinate_relation::q0"
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
        parquet_cpu_count=1,
    )
    assert parquet_result.output_path == parquet_path.resolve()
    table = pq.read_table(parquet_result.output_path)
    parquet_rows = table.to_pylist()
    assert len(parquet_rows) == 1
    assert parquet_rows[0]["prompt"] == "active prompt"
    assert parquet_rows[0]["complexity_score"] == 0.6
    assert parquet_rows[0]["difficulty_bin"] == 0
    assert parquet_rows[0]["bucket_id_str"] == "task_geometry_coordinate_relation::q0"
    assert json.loads(parquet_rows[0]["answer_gt"]) == {
        "type": "integer",
        "value": 3,
    }
    assert json.loads(parquet_rows[0]["evidence_gt"]) == {
        "type": "graph_point_set",
        "value": [[1, 2], [3, 4], [5, 6]],
    }
    assert json.loads(parquet_rows[0]["reward_contract"]) == {
        "reward_contract_version": "v1",
        "answer": {"id": "answer_exact_match_v1", "type": "integer"},
        "evidence": {"id": "point_set_match_v1", "type": "graph_point_set"},
    }
    assert json.loads(parquet_rows[0]["trace_ref"]) == {
        "shard_id": "trace-0001",
        "line_index": 0,
        "trace_record_hash": "trace-hash",
    }
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


def test_export_trace_dataset_to_rlvr_parquet_supports_mixed_trace_contract_types(tmp_path: Path) -> None:
    dataset_root = tmp_path / "trace_dataset_mixed"
    image_dir = dataset_root / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    image_a = image_dir / "a.png"
    image_b = image_dir / "b.png"
    image_a.write_bytes(b"a")
    image_b.write_bytes(b"b")

    records = [
        {
            "instance_id": "inst-a",
            "domain": "geometry",
            "task_group": "coordinate",
            "task": "task_geometry_coordinate_relation",
            "prompt": "prompt a",
            "images": [{"path": "images/a.png"}],
            "answer_gt": {"type": "integer", "value": 3},
            "evidence_gt": {"type": "graph_point_set", "value": [[1, 2], [3, 4]]},
            "reward_contract": {
                "reward_contract_version": "v1",
                "answer": {"id": "answer_exact_match_v1", "type": "integer"},
                "evidence": {"id": "point_set_match_v1", "type": "graph_point_set"},
            },
            "task_complexity": {"complexity_score": 0.4, "complexity_components": {}},
            "trace_ref": {"shard_id": "trace", "line_index": 0, "trace_record_hash": "ha"},
        },
        {
            "instance_id": "inst-b",
            "domain": "puzzles",
            "task_group": "logic",
            "task": "task_puzzles_logic_grid_completion_label",
            "prompt": "prompt b",
            "images": [{"path": "images/b.png"}],
            "answer_gt": {"type": "option_letter", "value": "K"},
            "evidence_gt": {"type": "bbox_set", "value": [[10, 10, 20, 20]]},
            "reward_contract": {
                "reward_contract_version": "v1",
                "answer": {"id": "answer_exact_match_v1", "type": "option_letter"},
                "evidence": {"id": "bbox_set_iou_v1", "type": "bbox_set"},
            },
            "task_complexity": {"complexity_score": 0.7, "complexity_components": {}},
            "trace_ref": {"shard_id": "trace", "line_index": 1, "trace_record_hash": "hb"},
        },
    ]
    (dataset_root / "train_instances.jsonl").write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )

    result = export_trace_dataset_to_rlvr(
        dataset_root,
        tmp_path / "mixed.parquet",
        output_format="parquet",
        parquet_cpu_count=1,
    )
    rows = pq.read_table(result.output_path).to_pylist()
    assert len(rows) == 2
    assert json.loads(rows[0]["answer_gt"])["type"] == "integer"
    assert json.loads(rows[1]["answer_gt"])["type"] == "option_letter"
    assert json.loads(rows[1]["answer_gt"])["value"] == "K"


def test_export_trace_dataset_to_rlvr_adds_task_local_curriculum_buckets(tmp_path: Path) -> None:
    dataset_root = tmp_path / "trace_dataset_multi"
    dataset_root.mkdir(parents=True, exist_ok=True)
    image_dir = dataset_root / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    records = []
    for index, score in enumerate((0.1, 0.2, 0.3, 0.7, 0.8, 0.9), start=1):
        image_path = image_dir / f"a_{index:02d}.png"
        image_path.write_bytes(b"img")
        records.append(
            {
                "instance_id": f"task-a-{index}",
                "domain": "games",
                "task_group": "cards",
                "task": "task_games_cards_hand_count",
                "prompt": f"prompt {index}",
                "images": [{"path": f"images/{image_path.name}"}],
                "answer_gt": {"type": "integer", "value": index},
                "evidence_gt": {"type": "bbox_set", "value": []},
                "reward_contract": {
                    "reward_contract_version": "v1",
                    "answer": {"id": "answer_exact_match_v1", "type": "integer"},
                    "evidence": {"id": "bbox_set_iou_v1", "type": "bbox_set"},
                },
                "task_complexity": {"complexity_score": score, "complexity_components": {}},
                "trace_ref": {"shard_id": "trace", "line_index": index, "trace_record_hash": f"h{index}"},
            }
        )
    for index, score in enumerate((0.2, 0.2, 0.8), start=1):
        image_path = image_dir / f"b_{index:02d}.png"
        image_path.write_bytes(b"img")
        records.append(
            {
                "instance_id": f"task-b-{index}",
                "domain": "games",
                "task_group": "dominoes",
                "task": "task_games_dominoes_chain_count",
                "prompt": f"prompt-b {index}",
                "images": [{"path": f"images/{image_path.name}"}],
                "answer_gt": {"type": "integer", "value": index},
                "evidence_gt": {"type": "bbox_set", "value": []},
                "reward_contract": {
                    "reward_contract_version": "v1",
                    "answer": {"id": "answer_exact_match_v1", "type": "integer"},
                    "evidence": {"id": "bbox_set_iou_v1", "type": "bbox_set"},
                },
                "task_complexity": {"complexity_score": score, "complexity_components": {}},
                "trace_ref": {"shard_id": "trace", "line_index": 100 + index, "trace_record_hash": f"hb{index}"},
            }
        )

    (dataset_root / "train_instances.jsonl").write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )

    result = export_trace_dataset_to_rlvr(dataset_root, tmp_path / "out.jsonl")
    rows = [
        json.loads(line)
        for line in result.output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows_by_id = {row["instance_id"]: row for row in rows}

    assert {rows_by_id[f"task-a-{index}"]["bucket_id_str"] for index in (1, 2)} == {
        "task_games_cards_hand_count::q0"
    }
    assert {rows_by_id[f"task-a-{index}"]["bucket_id_str"] for index in (3, 4)} == {
        "task_games_cards_hand_count::q1"
    }
    assert {rows_by_id[f"task-a-{index}"]["bucket_id_str"] for index in (5, 6)} == {
        "task_games_cards_hand_count::q2"
    }

    assert rows_by_id["task-b-1"]["bucket_id_str"] == "task_games_dominoes_chain_count::q0"
    assert rows_by_id["task-b-2"]["bucket_id_str"] == "task_games_dominoes_chain_count::q0"
    assert rows_by_id["task-b-3"]["bucket_id_str"] == "task_games_dominoes_chain_count::q1"
    assert rows_by_id["task-b-1"]["difficulty_bin"] == 0
    assert rows_by_id["task-b-3"]["difficulty_bin"] == 1
