from __future__ import annotations

from pathlib import Path
import sqlite3

from scripts.reset_task_supervision_review import reset_supervision_reviews


def _write_inventory(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "- `task_charts__area__one`",
                "- `task_games__chess__two`",
                "- `task_games__go__three`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_feedback_db(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE task_audit (
                task_id TEXT PRIMARY KEY,
                prompt_pass INTEGER NOT NULL,
                supervision_review_pass INTEGER NOT NULL,
                notes TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by TEXT NOT NULL
            )
            """
        )
        conn.executemany(
            "INSERT INTO task_audit VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("task_charts__area__one", 1, 1, "charts note", "old", "reviewer"),
                ("task_games__chess__two", 1, 1, "games note", "old", "reviewer"),
            ],
        )


def test_supervision_review_reset_is_dry_run_by_default(tmp_path: Path) -> None:
    inventory = tmp_path / "inventory.md"
    feedback_db = tmp_path / "feedback.sqlite"
    _write_inventory(inventory)
    _write_feedback_db(feedback_db)

    report = reset_supervision_reviews(
        active_inventory=inventory,
        feedback_db=feedback_db,
        output_root=tmp_path / "reports",
    )

    assert report["applied"] is False
    assert report["active_task_count"] == 3
    assert report["reset_count"] == 2
    assert report["missing_audit_row_count"] == 1
    with sqlite3.connect(feedback_db) as conn:
        assert conn.execute(
            "SELECT supervision_review_pass FROM task_audit WHERE task_id = ?",
            ("task_charts__area__one",),
        ).fetchone() == (1,)


def test_supervision_review_reset_preserves_other_fields_and_supports_domain_filter(
    tmp_path: Path,
) -> None:
    inventory = tmp_path / "inventory.md"
    feedback_db = tmp_path / "feedback.sqlite"
    _write_inventory(inventory)
    _write_feedback_db(feedback_db)

    report = reset_supervision_reviews(
        active_inventory=inventory,
        feedback_db=feedback_db,
        output_root=tmp_path / "reports",
        domains=["games"],
        apply=True,
        backup=False,
        updated_by="policy_audit",
    )

    assert report["active_task_count"] == 2
    assert report["reset_task_ids"] == ["task_games__chess__two"]
    assert report["missing_task_ids"] == ["task_games__go__three"]
    with sqlite3.connect(feedback_db) as conn:
        chart_row = conn.execute(
            "SELECT prompt_pass, supervision_review_pass, notes, updated_by FROM task_audit WHERE task_id = ?",
            ("task_charts__area__one",),
        ).fetchone()
        game_row = conn.execute(
            "SELECT prompt_pass, supervision_review_pass, notes, updated_by FROM task_audit WHERE task_id = ?",
            ("task_games__chess__two",),
        ).fetchone()
    assert chart_row == (1, 1, "charts note", "reviewer")
    assert game_row == (1, 0, "games note", "policy_audit")
