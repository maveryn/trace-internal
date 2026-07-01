from __future__ import annotations

from pathlib import Path
import sqlite3

from scripts.reset_scalar_annotation_review import reset_annotation_reviews
from trace.review_app.feedback import FeedbackStore


TARGET_TASK_ID = "task_charts__contour_density__reference_distance_extremum_label"
TARGET_TASK_ID_2 = "task_charts__curve_panels__endpoint_rank_panel_label"
NON_TARGET_TASK_ID = "task_charts__population_pyramid__side_gap_extremum_label"


def _write_inventory(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "# Active Task Inventory",
                "",
                "### charts",
                "",
                "#### contour_density (1)",
                "",
                f"- `{TARGET_TASK_ID}`",
                "",
                "#### curve_panels (1)",
                "",
                f"- `{TARGET_TASK_ID_2}`",
                "",
                "#### population_pyramid (1)",
                "",
                f"- `{NON_TARGET_TASK_ID}`",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _audit_row(db_path: Path, task_id: str) -> dict | None:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM task_audit WHERE task_id = ?", (task_id,)).fetchone()
    return None if row is None else {key: row[key] for key in row.keys()}


def test_stage4_reset_dry_run_preserves_database(tmp_path: Path) -> None:
    inventory = tmp_path / "ACTIVE_TASK_INVENTORY.md"
    db_path = tmp_path / "review_feedback.sqlite"
    _write_inventory(inventory)
    store = FeedbackStore(db_path)
    store.update_task_audit(
        domain="charts",
        scene_id="contour_density",
        task_id=TARGET_TASK_ID,
        prompt_pass=True,
        image_pass=True,
        annotation_pass=True,
        distribution_pass=True,
        code_review_pass=True,
        taxonomy_review_pass=True,
        solve_rate_pass=False,
        notes="keep me",
        updated_by="reviewer",
    )

    report = reset_annotation_reviews(
        active_inventory=inventory,
        feedback_db=db_path,
        output_root=tmp_path / "scalar-annotation",
        apply=False,
    )

    assert report["target_task_count"] == 2
    assert report["reset_count"] == 1
    assert report["missing_row_count"] == 1
    row = _audit_row(db_path, TARGET_TASK_ID)
    assert row is not None
    assert row["annotation_pass"] == 1
    assert row["notes"] == "keep me"


def test_stage4_reset_flips_only_existing_target_annotation_gate(tmp_path: Path) -> None:
    inventory = tmp_path / "ACTIVE_TASK_INVENTORY.md"
    db_path = tmp_path / "review_feedback.sqlite"
    _write_inventory(inventory)
    store = FeedbackStore(db_path)
    store.update_task_audit(
        domain="charts",
        scene_id="contour_density",
        task_id=TARGET_TASK_ID,
        prompt_pass=True,
        image_pass=True,
        annotation_pass=True,
        distribution_pass=True,
        code_review_pass=True,
        taxonomy_review_pass=True,
        solve_rate_pass=False,
        notes="target notes",
        updated_by="reviewer",
    )
    store.update_task_audit(
        domain="charts",
        scene_id="population_pyramid",
        task_id=NON_TARGET_TASK_ID,
        prompt_pass=True,
        image_pass=True,
        annotation_pass=True,
        distribution_pass=True,
        code_review_pass=True,
        taxonomy_review_pass=True,
        solve_rate_pass=True,
        notes="non-target notes",
        updated_by="reviewer",
    )

    report = reset_annotation_reviews(
        active_inventory=inventory,
        feedback_db=db_path,
        output_root=tmp_path / "scalar-annotation",
        apply=True,
        backup=True,
    )

    assert report["target_task_count"] == 2
    assert report["reset_count"] == 1
    assert report["missing_row_count"] == 1
    assert Path(report["backup_path"]).exists()

    target = _audit_row(db_path, TARGET_TASK_ID)
    assert target is not None
    assert target["prompt_pass"] == 1
    assert target["image_pass"] == 1
    assert target["annotation_pass"] == 0
    assert target["distribution_pass"] == 1
    assert target["code_review_pass"] == 1
    assert target["taxonomy_review_pass"] == 1
    assert target["solve_rate_pass"] == 0
    assert target["notes"] == "target notes"
    assert target["updated_by"] == "scalar_annotation_stage4"

    assert _audit_row(db_path, TARGET_TASK_ID_2) is None
    non_target = _audit_row(db_path, NON_TARGET_TASK_ID)
    assert non_target is not None
    assert non_target["annotation_pass"] == 1
    assert non_target["notes"] == "non-target notes"
