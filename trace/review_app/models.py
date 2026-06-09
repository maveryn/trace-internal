"""Data models for the task-review web app."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping


@dataclass(frozen=True)
class SolveStats:
    """One model calibration summary attached to a task."""

    model: str
    model_id: str
    status: str
    combined_status: str
    reasons: str = ""
    mean_solve_rate: float | None = None
    hard_frac: float | None = None
    easy_frac: float | None = None
    band_frac: float | None = None
    response_cap_rate: float | None = None
    prompt_count: int | None = None
    rollout_count: int | None = None
    solve_workbook: str = ""
    calibration_stats: str = ""
    output_dir: str = ""


@dataclass(frozen=True)
class SampleRecord:
    """One generated review sample."""

    uid: str
    content_hash: str
    domain: str
    scene_id: str
    task_id: str
    query_id: str
    instance_seed: int
    data_rel_path: str
    image_rel_path: str
    media_id: str
    image_exists: bool
    image_mtime_ns: int
    prompt: str
    prompt_answer_only: str
    prompt_answer_and_annotation: str
    answer_type: str
    answer_value: Any
    annotation_type: str
    annotation_value: Any

    @property
    def answer_label(self) -> str:
        return "" if self.answer_value is None else str(self.answer_value)


@dataclass
class TaskRecord:
    """One public task under a scene."""

    domain: str
    scene_id: str
    task_id: str
    manifest_rel_path: str = ""
    workbook_rel_path: str = ""
    distribution_rel_path: str = ""
    random_review_rel_path: str = ""
    query_counts: Dict[str, int] = field(default_factory=dict)
    workbook_sheets: Dict[str, str] = field(default_factory=dict)
    sample_count: int = 0
    preview_uid: str = ""
    distribution_mode: str = ""
    distribution_pass: bool | None = None
    distribution_summary: Dict[str, Any] = field(default_factory=dict)
    solve_stats: List[SolveStats] = field(default_factory=list)

    @property
    def solve_pass(self) -> bool:
        """Whether any current solve-rate summary marks this task accepted."""

        for stats in self.solve_stats:
            status = str(stats.combined_status or stats.status).strip().lower()
            if status == "accepted":
                return True
        return False


@dataclass(frozen=True)
class TaskAuditRecord:
    """Persisted manual audit status for one task."""

    domain: str
    scene_id: str
    task_id: str
    prompt_pass: bool = False
    image_pass: bool = False
    annotation_pass: bool = False
    distribution_pass: bool = False
    solve_rate_pass: bool = False
    notes: str = ""
    updated_at: str = ""
    updated_by: str = ""

    @property
    def review_pass(self) -> bool:
        """Whether the non-solve-rate manual review gates are all checked."""

        return (
            self.prompt_pass
            and self.image_pass
            and self.annotation_pass
            and self.distribution_pass
        )

    @property
    def review_count(self) -> int:
        return (
            int(self.prompt_pass)
            + int(self.image_pass)
            + int(self.annotation_pass)
            + int(self.distribution_pass)
        )

    @property
    def review_total(self) -> int:
        return 4

    @property
    def solve_rate_review_pass(self) -> bool:
        return bool(self.solve_rate_pass)

    @property
    def manual_pass(self) -> bool:
        """Backward-compatible name for non-solve-rate review completion."""

        return self.review_pass

    @property
    def passed_count(self) -> int:
        """Total checked manual gates, including the separate solve-rate gate."""

        return self.review_count + int(self.solve_rate_pass)

    @property
    def total_count(self) -> int:
        return 5

    @classmethod
    def empty(cls, *, domain: str, scene_id: str, task_id: str) -> "TaskAuditRecord":
        return cls(domain=domain, scene_id=scene_id, task_id=task_id)

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "TaskAuditRecord":
        return cls(
            domain=str(row["domain"]),
            scene_id=str(row["scene_id"]),
            task_id=str(row["task_id"]),
            prompt_pass=bool(int(row["prompt_pass"] or 0)),
            image_pass=bool(int(row["image_pass"] or 0)),
            annotation_pass=bool(int(row["annotation_pass"] or 0)),
            distribution_pass=bool(int(row["distribution_pass"] or 0)),
            solve_rate_pass=bool(int(row.get("solve_rate_pass", 0) or 0)),
            notes=str(row["notes"] or ""),
            updated_at=str(row["updated_at"] or ""),
            updated_by=str(row["updated_by"] or ""),
        )


@dataclass(frozen=True)
class TaxonomyDecisionReviewRecord:
    """Persisted reviewer approval for one taxonomy task-boundary decision."""

    round_id: str
    domain: str
    scene_id: str
    task_id: str
    approved: bool = False
    notes: str = ""
    updated_at: str = ""
    updated_by: str = ""

    @property
    def task_key(self) -> str:
        return ReviewIndex.task_key(self.domain, self.scene_id, self.task_id)

    @classmethod
    def empty(
        cls,
        *,
        round_id: str,
        domain: str,
        scene_id: str,
        task_id: str,
    ) -> "TaxonomyDecisionReviewRecord":
        return cls(round_id=round_id, domain=domain, scene_id=scene_id, task_id=task_id)

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "TaxonomyDecisionReviewRecord":
        return cls(
            round_id=str(row["round_id"]),
            domain=str(row["domain"]),
            scene_id=str(row["scene_id"]),
            task_id=str(row["task_id"]),
            approved=bool(int(row["approved"] or 0)),
            notes=str(row["notes"] or ""),
            updated_at=str(row["updated_at"] or ""),
            updated_by=str(row["updated_by"] or ""),
        )


@dataclass(frozen=True)
class ThreeDObjectReviewRecord:
    """Persisted reviewer decision for one canonical three_d object profile."""

    profile_id: str
    canonical_id: str = ""
    object_type: str = ""
    renderer: str = ""
    source_scene: str = ""
    decision: str = ""
    notes: str = ""
    updated_at: str = ""
    updated_by: str = ""

    @property
    def reviewed(self) -> bool:
        return bool(str(self.decision).strip())

    @classmethod
    def empty(cls, *, profile_id: str) -> "ThreeDObjectReviewRecord":
        return cls(profile_id=str(profile_id))

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "ThreeDObjectReviewRecord":
        return cls(
            profile_id=str(row["profile_id"]),
            canonical_id=str(row["canonical_id"] or ""),
            object_type=str(row["object_type"] or ""),
            renderer=str(row["renderer"] or ""),
            source_scene=str(row["source_scene"] or ""),
            decision=str(row["decision"] or ""),
            notes=str(row["notes"] or ""),
            updated_at=str(row["updated_at"] or ""),
            updated_by=str(row["updated_by"] or ""),
        )


@dataclass(frozen=True)
class IllustrationObjectReviewRecord:
    """Persisted reviewer decision for one illustration object renderer preview."""

    item_id: str
    renderer_style: str = ""
    category: str = ""
    object_type: str = ""
    label: str = ""
    decision: str = ""
    notes: str = ""
    updated_at: str = ""
    updated_by: str = ""

    @property
    def reviewed(self) -> bool:
        return bool(str(self.decision).strip())

    @classmethod
    def empty(cls, *, item_id: str) -> "IllustrationObjectReviewRecord":
        return cls(item_id=str(item_id))

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "IllustrationObjectReviewRecord":
        return cls(
            item_id=str(row["item_id"]),
            renderer_style=str(row["renderer_style"] or ""),
            category=str(row["category"] or ""),
            object_type=str(row["object_type"] or ""),
            label=str(row["label"] or ""),
            decision=str(row["decision"] or ""),
            notes=str(row["notes"] or ""),
            updated_at=str(row["updated_at"] or ""),
            updated_by=str(row["updated_by"] or ""),
        )


@dataclass
class SceneRecord:
    """One public scene under a domain."""

    domain: str
    scene_id: str
    manifest_rel_path: str = ""
    workbook_rel_path: str = ""
    task_count: int = 0
    sample_count: int = 0
    preview_uid: str = ""
    tasks: List[str] = field(default_factory=list)
    model_stats_count: int = 0


@dataclass
class DomainRecord:
    """One review domain."""

    domain: str
    scenes: List[str] = field(default_factory=list)
    task_count: int = 0
    sample_count: int = 0
    preview_uid: str = ""


@dataclass
class ReviewIndex:
    """In-memory index built from review/task-reviews."""

    root: Path
    repo_root: Path
    built_at: str
    domains: Dict[str, DomainRecord] = field(default_factory=dict)
    scenes: Dict[str, SceneRecord] = field(default_factory=dict)
    tasks: Dict[str, TaskRecord] = field(default_factory=dict)
    samples: Dict[str, SampleRecord] = field(default_factory=dict)
    samples_by_task: Dict[str, List[str]] = field(default_factory=dict)
    samples_by_query: Dict[str, List[str]] = field(default_factory=dict)
    media: Dict[str, Path] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    @staticmethod
    def scene_key(domain: str, scene_id: str) -> str:
        return f"{domain}/{scene_id}"

    @staticmethod
    def task_key(domain: str, scene_id: str, task_id: str) -> str:
        return f"{domain}/{scene_id}/{task_id}"

    @staticmethod
    def query_key(domain: str, scene_id: str, task_id: str, query_id: str) -> str:
        return f"{domain}/{scene_id}/{task_id}/{query_id}"

    def as_summary(self) -> Dict[str, Any]:
        """Return a compact JSON-serializable index summary."""

        return {
            "root": str(self.root),
            "repo_root": str(self.repo_root),
            "built_at": self.built_at,
            "domain_count": len(self.domains),
            "scene_count": len(self.scenes),
            "task_count": len(self.tasks),
            "sample_count": len(self.samples),
            "errors": list(self.errors),
            "domains": {key: asdict(value) for key, value in sorted(self.domains.items())},
        }


@dataclass(frozen=True)
class FeedbackRecord:
    """One persisted reviewer comment."""

    id: str
    sample_uid: str
    domain: str
    scene_id: str
    task_id: str
    query_id: str
    data_rel_path: str
    image_rel_path: str
    instance_seed: int
    sample_content_hash: str
    created_at: str
    updated_at: str
    author: str
    category: str
    severity: str
    status: str
    comment: str

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "FeedbackRecord":
        return cls(
            id=str(row["id"]),
            sample_uid=str(row["sample_uid"]),
            domain=str(row["domain"]),
            scene_id=str(row["scene_id"]),
            task_id=str(row["task_id"]),
            query_id=str(row["query_id"]),
            data_rel_path=str(row["data_rel_path"]),
            image_rel_path=str(row["image_rel_path"]),
            instance_seed=int(row["instance_seed"] or 0),
            sample_content_hash=str(row["sample_content_hash"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            author=str(row["author"]),
            category=str(row["category"]),
            severity=str(row["severity"]),
            status=str(row["status"]),
            comment=str(row["comment"]),
        )


@dataclass(frozen=True)
class FeedbackNoteRecord:
    """One agent repair note attached to a feedback item."""

    id: str
    feedback_id: str
    sample_uid: str
    domain: str
    scene_id: str
    task_id: str
    query_id: str
    created_at: str
    author: str
    note: str

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "FeedbackNoteRecord":
        return cls(
            id=str(row["id"]),
            feedback_id=str(row["feedback_id"]),
            sample_uid=str(row["sample_uid"]),
            domain=str(row["domain"]),
            scene_id=str(row["scene_id"]),
            task_id=str(row["task_id"]),
            query_id=str(row["query_id"]),
            created_at=str(row["created_at"]),
            author=str(row["author"]),
            note=str(row["note"]),
        )


@dataclass(frozen=True)
class FeedbackCommentRecord:
    """One reviewer follow-up comment attached to a feedback item."""

    id: str
    feedback_id: str
    sample_uid: str
    domain: str
    scene_id: str
    task_id: str
    query_id: str
    created_at: str
    author: str
    comment: str

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "FeedbackCommentRecord":
        return cls(
            id=str(row["id"]),
            feedback_id=str(row["feedback_id"]),
            sample_uid=str(row["sample_uid"]),
            domain=str(row["domain"]),
            scene_id=str(row["scene_id"]),
            task_id=str(row["task_id"]),
            query_id=str(row["query_id"]),
            created_at=str(row["created_at"]),
            author=str(row["author"]),
            comment=str(row["comment"]),
        )


@dataclass(frozen=True)
class FeedbackThreadEvent:
    """One chronological event in a reviewer/agent feedback thread."""

    kind: str
    created_at: str
    author: str
    text: str
    label: str
