"""SQLite-backed reviewer feedback store."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, Iterable, Mapping
from uuid import uuid4

from .models import FeedbackCommentRecord, FeedbackNoteRecord, FeedbackRecord, SampleRecord, TaskAuditRecord


VALID_CATEGORIES = {"prompt", "evidence", "rendering", "answer", "calibration", "other"}
VALID_SEVERITIES = {"note", "issue", "blocker"}
VALID_STATUSES = {"open", "resolved"}


class FeedbackStore:
    """Persist task-review comments keyed to stable sample identities."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def add_feedback(
        self,
        *,
        sample: SampleRecord,
        comment: str,
        author: str = "",
        category: str = "other",
        severity: str = "issue",
    ) -> FeedbackRecord:
        text = str(comment).strip()
        if not text:
            raise ValueError("feedback comment must not be empty")
        category = _normalize_choice(category, VALID_CATEGORIES, "other")
        severity = _normalize_choice(severity, VALID_SEVERITIES, "issue")
        now = _now()
        record_id = uuid4().hex
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO feedback (
                    id, sample_uid, domain, scene_id, task_id, query_id,
                    data_rel_path, image_rel_path, instance_seed, sample_content_hash,
                    created_at, updated_at, author, category, severity, status, comment
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    sample.uid,
                    sample.domain,
                    sample.scene_id,
                    sample.task_id,
                    sample.query_id,
                    sample.data_rel_path,
                    sample.image_rel_path,
                    sample.instance_seed,
                    sample.content_hash,
                    now,
                    now,
                    str(author).strip(),
                    category,
                    severity,
                    "open",
                    text,
                ),
            )
        return self.get_feedback(record_id)

    def add_task_feedback(
        self,
        *,
        domain: str,
        scene_id: str,
        task_id: str,
        comment: str,
        author: str = "",
        category: str = "other",
        severity: str = "issue",
    ) -> FeedbackRecord:
        text = str(comment).strip()
        if not text:
            raise ValueError("feedback comment must not be empty")
        category = _normalize_choice(category, VALID_CATEGORIES, "other")
        severity = _normalize_choice(severity, VALID_SEVERITIES, "issue")
        now = _now()
        record_id = uuid4().hex
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO feedback (
                    id, sample_uid, domain, scene_id, task_id, query_id,
                    data_rel_path, image_rel_path, instance_seed, sample_content_hash,
                    created_at, updated_at, author, category, severity, status, comment
                )
                VALUES (?, '', ?, ?, ?, '', '', '', 0, '', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    str(domain),
                    str(scene_id),
                    str(task_id),
                    now,
                    now,
                    str(author).strip(),
                    category,
                    severity,
                    "open",
                    text,
                ),
            )
        return self.get_feedback(record_id)

    def update_feedback(
        self,
        feedback_id: str,
        *,
        comment: str | None = None,
        category: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        author: str | None = None,
    ) -> FeedbackRecord:
        existing = self.get_feedback(feedback_id)
        updates: Dict[str, Any] = {}
        if comment is not None:
            text = str(comment).strip()
            if not text:
                raise ValueError("feedback comment must not be empty")
            updates["comment"] = text
        if category is not None:
            updates["category"] = _normalize_choice(category, VALID_CATEGORIES, existing.category)
        if severity is not None:
            updates["severity"] = _normalize_choice(severity, VALID_SEVERITIES, existing.severity)
        if status is not None:
            updates["status"] = _normalize_choice(status, VALID_STATUSES, existing.status)
        if author is not None:
            updates["author"] = str(author).strip()
        if not updates:
            return existing
        updates["updated_at"] = _now()
        columns = ", ".join(f"{name} = ?" for name in updates)
        values = list(updates.values()) + [feedback_id]
        with self._connect() as conn:
            conn.execute(f"UPDATE feedback SET {columns} WHERE id = ?", values)
        return self.get_feedback(feedback_id)

    def add_feedback_note(
        self,
        feedback_id: str,
        *,
        note: str,
        author: str = "",
    ) -> FeedbackNoteRecord:
        """Append an agent repair note to an existing feedback item."""

        text = str(note).strip()
        if not text:
            raise ValueError("feedback note must not be empty")
        parent = self.get_feedback(feedback_id)
        now = _now()
        record_id = uuid4().hex
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO feedback_notes (
                    id, feedback_id, sample_uid, domain, scene_id, task_id, query_id,
                    created_at, author, note
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    parent.id,
                    parent.sample_uid,
                    parent.domain,
                    parent.scene_id,
                    parent.task_id,
                    parent.query_id,
                    now,
                    str(author).strip(),
                    text,
                ),
            )
        return self.get_feedback_note(record_id)

    def get_feedback_note(self, note_id: str) -> FeedbackNoteRecord:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM feedback_notes WHERE id = ?", (str(note_id),)).fetchone()
        if row is None:
            raise KeyError(f"unknown feedback note id: {note_id}")
        return FeedbackNoteRecord.from_row(dict(row))

    def add_feedback_comment(
        self,
        feedback_id: str,
        *,
        comment: str,
        author: str = "",
    ) -> FeedbackCommentRecord:
        """Append a reviewer follow-up comment to an existing feedback item."""

        text = str(comment).strip()
        if not text:
            raise ValueError("feedback comment must not be empty")
        parent = self.get_feedback(feedback_id)
        now = _now()
        record_id = uuid4().hex
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO feedback_comments (
                    id, feedback_id, sample_uid, domain, scene_id, task_id, query_id,
                    created_at, author, comment
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    parent.id,
                    parent.sample_uid,
                    parent.domain,
                    parent.scene_id,
                    parent.task_id,
                    parent.query_id,
                    now,
                    str(author).strip(),
                    text,
                ),
            )
            conn.execute("UPDATE feedback SET updated_at = ? WHERE id = ?", (now, parent.id))
        return self.get_feedback_comment(record_id)

    def get_feedback_comment(self, comment_id: str) -> FeedbackCommentRecord:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM feedback_comments WHERE id = ?", (str(comment_id),)).fetchone()
        if row is None:
            raise KeyError(f"unknown feedback comment id: {comment_id}")
        return FeedbackCommentRecord.from_row(dict(row))

    def list_comments_for_feedback(self, feedback_id: str) -> list[FeedbackCommentRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM feedback_comments
                WHERE feedback_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (str(feedback_id),),
            ).fetchall()
        return [FeedbackCommentRecord.from_row(dict(row)) for row in rows]

    def comments_by_feedback(self, feedback_ids: Iterable[str]) -> Dict[str, list[FeedbackCommentRecord]]:
        ids = [str(feedback_id) for feedback_id in feedback_ids if str(feedback_id)]
        if not ids:
            return {}
        placeholders = ", ".join("?" for _ in ids)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM feedback_comments
                WHERE feedback_id IN ({placeholders})
                ORDER BY created_at ASC, id ASC
                """,
                tuple(ids),
            ).fetchall()
        comments: Dict[str, list[FeedbackCommentRecord]] = {feedback_id: [] for feedback_id in ids}
        for row in rows:
            record = FeedbackCommentRecord.from_row(dict(row))
            comments.setdefault(record.feedback_id, []).append(record)
        return comments

    def list_notes_for_feedback(self, feedback_id: str) -> list[FeedbackNoteRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM feedback_notes
                WHERE feedback_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (str(feedback_id),),
            ).fetchall()
        return [FeedbackNoteRecord.from_row(dict(row)) for row in rows]

    def notes_by_feedback(self, feedback_ids: Iterable[str]) -> Dict[str, list[FeedbackNoteRecord]]:
        ids = [str(feedback_id) for feedback_id in feedback_ids if str(feedback_id)]
        if not ids:
            return {}
        placeholders = ", ".join("?" for _ in ids)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM feedback_notes
                WHERE feedback_id IN ({placeholders})
                ORDER BY created_at ASC, id ASC
                """,
                tuple(ids),
            ).fetchall()
        notes: Dict[str, list[FeedbackNoteRecord]] = {feedback_id: [] for feedback_id in ids}
        for row in rows:
            record = FeedbackNoteRecord.from_row(dict(row))
            notes.setdefault(record.feedback_id, []).append(record)
        return notes

    def get_feedback(self, feedback_id: str) -> FeedbackRecord:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM feedback WHERE id = ?", (str(feedback_id),)).fetchone()
        if row is None:
            raise KeyError(f"unknown feedback id: {feedback_id}")
        return FeedbackRecord.from_row(dict(row))

    def list_for_sample(self, sample_uid: str) -> list[FeedbackRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM feedback WHERE sample_uid = ? ORDER BY created_at DESC, id DESC",
                (str(sample_uid),),
            ).fetchall()
        return [FeedbackRecord.from_row(dict(row)) for row in rows]

    def list_open_feedback(self) -> list[FeedbackRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM feedback
                WHERE status = 'open'
                ORDER BY domain, scene_id, task_id, sample_uid, created_at DESC, id DESC
                """
            ).fetchall()
        return [FeedbackRecord.from_row(dict(row)) for row in rows]

    def counts_by_sample(self) -> Dict[str, Dict[str, int]]:
        return self._counts_by(["sample_uid"], where="sample_uid != ''")

    def list_task_feedback(self, *, domain: str, scene_id: str, task_id: str) -> list[FeedbackRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM feedback
                WHERE sample_uid = '' AND domain = ? AND scene_id = ? AND task_id = ?
                ORDER BY created_at DESC, id DESC
                """,
                (str(domain), str(scene_id), str(task_id)),
            ).fetchall()
        return [FeedbackRecord.from_row(dict(row)) for row in rows]

    def counts_by_task(self) -> Dict[str, Dict[str, int]]:
        raw = self._counts_by(["domain", "scene_id", "task_id"])
        return {"/".join(key.split("\x1f")): value for key, value in raw.items()}

    def counts_by_scene(self) -> Dict[str, Dict[str, int]]:
        raw = self._counts_by(["domain", "scene_id"])
        return {"/".join(key.split("\x1f")): value for key, value in raw.items()}

    def counts_by_domain(self) -> Dict[str, Dict[str, int]]:
        return self._counts_by(["domain"])

    def get_task_audit(self, *, domain: str, scene_id: str, task_id: str) -> TaskAuditRecord:
        """Return the persisted manual audit status for one task."""

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM task_audit
                WHERE domain = ? AND scene_id = ? AND task_id = ?
                """,
                (str(domain), str(scene_id), str(task_id)),
            ).fetchone()
        if row is None:
            return TaskAuditRecord.empty(domain=str(domain), scene_id=str(scene_id), task_id=str(task_id))
        return TaskAuditRecord.from_row(dict(row))

    def task_audits_by_task(self) -> Dict[str, TaskAuditRecord]:
        """Return persisted manual audit statuses keyed by domain/scene/task."""

        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM task_audit ORDER BY domain, scene_id, task_id").fetchall()
        return {
            "/".join([str(row["domain"]), str(row["scene_id"]), str(row["task_id"])]): TaskAuditRecord.from_row(dict(row))
            for row in rows
        }

    def update_task_audit(
        self,
        *,
        domain: str,
        scene_id: str,
        task_id: str,
        prompt_pass: bool,
        image_pass: bool,
        evidence_pass: bool,
        distribution_pass: bool,
        solve_rate_pass: bool = False,
        notes: str = "",
        updated_by: str = "",
    ) -> TaskAuditRecord:
        """Upsert one task's manual audit status."""

        now = _now()
        values = (
            str(domain),
            str(scene_id),
            str(task_id),
            int(bool(prompt_pass)),
            int(bool(image_pass)),
            int(bool(evidence_pass)),
            int(bool(distribution_pass)),
            int(bool(solve_rate_pass)),
            str(notes).strip(),
            now,
            str(updated_by).strip(),
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO task_audit (
                    domain, scene_id, task_id, prompt_pass, image_pass,
                    evidence_pass, distribution_pass, solve_rate_pass, notes, updated_at, updated_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(domain, scene_id, task_id) DO UPDATE SET
                    prompt_pass = excluded.prompt_pass,
                    image_pass = excluded.image_pass,
                    evidence_pass = excluded.evidence_pass,
                    distribution_pass = excluded.distribution_pass,
                    solve_rate_pass = excluded.solve_rate_pass,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at,
                    updated_by = excluded.updated_by
                """,
                values,
            )
        return self.get_task_audit(domain=domain, scene_id=scene_id, task_id=task_id)

    def export_records(self, *, include_resolved: bool = True) -> Iterable[Dict[str, Any]]:
        sql = "SELECT * FROM feedback"
        params: tuple[Any, ...] = ()
        if not include_resolved:
            sql += " WHERE status != ?"
            params = ("resolved",)
        sql += " ORDER BY created_at ASC, id ASC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        feedback = [FeedbackRecord.from_row(dict(row)) for row in rows]
        notes_by_feedback = self.notes_by_feedback(record.id for record in feedback)
        comments_by_feedback = self.comments_by_feedback(record.id for record in feedback)
        for record in feedback:
            payload = asdict(record)
            payload["reviewer_comments"] = [asdict(comment) for comment in comments_by_feedback.get(record.id, [])]
            payload["agent_notes"] = [asdict(note) for note in notes_by_feedback.get(record.id, [])]
            yield payload

    def export_jsonl(self, *, include_resolved: bool = True) -> str:
        return "\n".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True)
            for record in self.export_records(include_resolved=include_resolved)
        )

    def _counts_by(self, columns: list[str], *, where: str = "") -> Dict[str, Dict[str, int]]:
        select_cols = ", ".join(columns)
        group_cols = ", ".join(columns)
        query = f"""
            SELECT {select_cols}, status, COUNT(*) AS count
            FROM feedback
            {f"WHERE {where}" if where else ""}
            GROUP BY {group_cols}, status
        """
        counts: Dict[str, Dict[str, int]] = {}
        with self._connect() as conn:
            rows = conn.execute(query).fetchall()
        for row in rows:
            key = "\x1f".join(str(row[column]) for column in columns)
            entry = counts.setdefault(key, {"total": 0, "open": 0, "resolved": 0})
            count = int(row["count"] or 0)
            entry["total"] += count
            if str(row["status"]) == "resolved":
                entry["resolved"] += count
            else:
                entry["open"] += count
        return counts

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    id TEXT PRIMARY KEY,
                    sample_uid TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    scene_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    query_id TEXT NOT NULL,
                    data_rel_path TEXT NOT NULL,
                    image_rel_path TEXT NOT NULL,
                    instance_seed INTEGER NOT NULL,
                    sample_content_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    author TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    comment TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_sample ON feedback(sample_uid)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_task ON feedback(domain, scene_id, task_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_status ON feedback(status)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback_notes (
                    id TEXT PRIMARY KEY,
                    feedback_id TEXT NOT NULL,
                    sample_uid TEXT NOT NULL DEFAULT '',
                    domain TEXT NOT NULL,
                    scene_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    query_id TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    author TEXT NOT NULL DEFAULT '',
                    note TEXT NOT NULL,
                    FOREIGN KEY(feedback_id) REFERENCES feedback(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_notes_feedback ON feedback_notes(feedback_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_notes_task ON feedback_notes(domain, scene_id, task_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback_comments (
                    id TEXT PRIMARY KEY,
                    feedback_id TEXT NOT NULL,
                    sample_uid TEXT NOT NULL DEFAULT '',
                    domain TEXT NOT NULL,
                    scene_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    query_id TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    author TEXT NOT NULL DEFAULT '',
                    comment TEXT NOT NULL,
                    FOREIGN KEY(feedback_id) REFERENCES feedback(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_comments_feedback ON feedback_comments(feedback_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_comments_task ON feedback_comments(domain, scene_id, task_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS task_audit (
                    domain TEXT NOT NULL,
                    scene_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    prompt_pass INTEGER NOT NULL DEFAULT 0,
                    image_pass INTEGER NOT NULL DEFAULT 0,
                    evidence_pass INTEGER NOT NULL DEFAULT 0,
                    distribution_pass INTEGER NOT NULL DEFAULT 0,
                    solve_rate_pass INTEGER NOT NULL DEFAULT 0,
                    notes TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL,
                    updated_by TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (domain, scene_id, task_id)
                )
                """
            )
            columns = {str(row["name"]) for row in conn.execute("PRAGMA table_info(task_audit)").fetchall()}
            if "solve_rate_pass" not in columns:
                conn.execute("ALTER TABLE task_audit ADD COLUMN solve_rate_pass INTEGER NOT NULL DEFAULT 0")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize_choice(value: str, allowed: set[str], fallback: str) -> str:
    text = str(value).strip().lower()
    return text if text in allowed else fallback
