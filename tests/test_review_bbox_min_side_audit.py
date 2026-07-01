from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from scripts.audit_review_bbox_min_side import collect_bbox_min_side_audit, flatten_bbox_annotation


def test_flatten_bbox_annotation_handles_all_bbox_public_shapes() -> None:
    cases = [
        ("bbox", [1, 2, 3, 4], 1),
        ("bbox_set", [[1, 2, 3, 4], [5, 6, 7, 8]], 2),
        ("bbox_sequence", [[1, 2, 3, 4]], 1),
        ("bbox_map", {"target": [1, 2, 3, 4]}, 1),
        ("bbox_set_map", {"target": [[1, 2, 3, 4], [5, 6, 7, 8]]}, 2),
    ]

    for annotation_type, value, expected_count in cases:
        witnesses, errors = flatten_bbox_annotation(annotation_type, value)
        assert errors == []
        assert len(witnesses) == expected_count


def test_review_bbox_min_side_audit_reads_existing_artifacts_only(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs" / "tasks"
    review_root = tmp_path / "review" / "task-reviews"
    task_id = "task_games__2048__max_tile_value"
    task_dir = review_root / "games" / "2048" / task_id
    data_dir = task_dir / "data" / "single"
    image_dir = task_dir / "images" / "single"
    data_dir.mkdir(parents=True)
    image_dir.mkdir(parents=True)
    (docs_root / "games" / "2048").mkdir(parents=True)
    (docs_root / "games" / "2048" / f"{task_id}.md").write_text(
        "## Program Contract\n\nAnnotation schema: `bbox_set`\n",
        encoding="utf-8",
    )
    Image.new("RGB", (100, 100), (255, 255, 255)).save(image_dir / "0000.png")
    (data_dir / "0000.json").write_text(
        json.dumps(
            {
                "task_id": task_id,
                "query_id": "single",
                "annotation_gt": {"type": "bbox_set", "value": [[10, 20, 40, 45], [50, 50, 70, 80]]},
                "image": {"path": f"games/2048/{task_id}/images/single/0000.png"},
            }
        ),
        encoding="utf-8",
    )

    report = collect_bbox_min_side_audit(
        review_root=review_root,
        docs_root=docs_root,
        domains=("games",),
        min_side_px=24,
    )

    records = [record for record in report["records"] if record["task_id"] == task_id]
    assert len(records) == 1
    record = records[0]
    assert record["bbox_count"] == 2
    assert record["min_width_px_observed"] == 20.0
    assert record["min_height_px_observed"] == 25.0
    assert record["min_side_px_observed"] == 20.0
    assert record["failure_count"] == 1
