"""Tests for retired review task-audit cleanup."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.cleanup_retired_task_audit_rows import cleanup_retired_task_audit_rows
from trace.review_app.feedback import FeedbackStore


def _write_manifest(review_root: Path, *, domain: str, scene_id: str, task_id: str) -> None:
    task_dir = review_root / domain / scene_id / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "manifest.json").write_text(
        json.dumps({"domain": domain, "scene_id": scene_id, "task_id": task_id}),
        encoding="utf-8",
    )


def test_cleanup_retired_task_audit_rows_dry_run_and_apply(tmp_path: Path) -> None:
    feedback_db = tmp_path / "review_feedback.sqlite"
    review_root = tmp_path / "task-reviews"
    output_root = tmp_path / "cleanup-report"
    active_task = "task_games__scene__active_count"
    retired_task = "task_games__scene__retired_count"

    _write_manifest(
        review_root,
        domain="games",
        scene_id="scene",
        task_id=active_task,
    )
    store = FeedbackStore(feedback_db)
    store.update_task_audit(
        domain="games",
        scene_id="scene",
        task_id=active_task,
        prompt_pass=True,
        image_pass=True,
        annotation_pass=True,
        distribution_pass=True,
        code_review_pass=True,
        taxonomy_review_pass=True,
        updated_by="tester",
    )
    store.update_task_audit(
        domain="games",
        scene_id="scene",
        task_id=retired_task,
        prompt_pass=True,
        image_pass=True,
        annotation_pass=True,
        distribution_pass=True,
        code_review_pass=True,
        taxonomy_review_pass=True,
        updated_by="tester",
    )

    dry_run = cleanup_retired_task_audit_rows(
        domain="games",
        feedback_db=feedback_db,
        review_root=review_root,
        output_root=output_root,
        apply=False,
    )
    assert dry_run["stale_row_count_before"] == 1
    assert dry_run["deleted_row_count"] == 0
    assert store.get_task_audit(domain="games", scene_id="scene", task_id=retired_task).prompt_pass

    applied = cleanup_retired_task_audit_rows(
        domain="games",
        feedback_db=feedback_db,
        review_root=review_root,
        output_root=output_root,
        apply=True,
    )
    assert applied["stale_row_count_before"] == 1
    assert applied["deleted_row_count"] == 1
    assert applied["stale_row_count_after"] == 0
    assert applied["db_task_audit_rows_after"] == 1
    assert Path(str(applied["backup_path"])).exists()
    assert store.get_task_audit(domain="games", scene_id="scene", task_id=active_task).prompt_pass
    assert not store.get_task_audit(domain="games", scene_id="scene", task_id=retired_task).prompt_pass
    assert Path(str(applied["report_json"])).exists()
    assert Path(str(applied["report_md"])).exists()
