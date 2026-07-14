"""Load and validate the versioned RLVR task-supervision policy."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping


TASK_SUPERVISION_POLICY_REL_PATH = Path("rlvr/task_supervision/trace_supervision_policy_v1.json")
TASK_SUPERVISION_POLICY_SCHEMA = "trace_task_supervision_policy_v1"
VALID_TASK_SUPERVISION_MODES = frozenset({"answer", "answer_and_annotation"})
VALID_ANSWER_SUPERVISION_RATIONALES = frozenset(
    {
        "conservative_answer_default",
        "derived_reasoning",
        "redundant_context_annotation",
        "redundant_option_annotation",
    }
)
VALID_ANNOTATION_SUPERVISION_RATIONALES = frozenset(
    {
        "target_grounding",
        "visible_enumeration",
    }
)
VALID_TASK_SUPERVISION_RATIONALES_BY_MODE = {
    "answer": VALID_ANSWER_SUPERVISION_RATIONALES,
    "answer_and_annotation": VALID_ANNOTATION_SUPERVISION_RATIONALES,
}


@dataclass(frozen=True)
class TaskSupervisionAssignment:
    """One task's fixed RLVR supervision decision."""

    task_id: str
    mode: str
    rationale: str
    notes: str = ""


@dataclass(frozen=True)
class TaskSupervisionPolicy:
    """Validated task-conditioned supervision policy."""

    policy_id: str
    status: str
    mode_field: str
    reviewed_scenes: tuple[str, ...]
    assignments: Mapping[str, TaskSupervisionAssignment]
    path: Path

    def assignment_for(self, task_id: str) -> TaskSupervisionAssignment | None:
        return self.assignments.get(str(task_id))


def load_task_supervision_policy(
    repo_root: Path | str,
    *,
    required: bool = True,
) -> TaskSupervisionPolicy:
    """Return the validated supervision policy rooted at ``repo_root``."""

    path = Path(repo_root).resolve() / TASK_SUPERVISION_POLICY_REL_PATH
    if not path.exists():
        if required:
            raise FileNotFoundError(path)
        return TaskSupervisionPolicy(
            policy_id="",
            status="missing",
            mode_field="trace_supervision_mode",
            reviewed_scenes=(),
            assignments={},
            path=path,
        )

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError(f"task supervision policy must be a JSON object: {path}")
    if str(payload.get("schema", "")) != TASK_SUPERVISION_POLICY_SCHEMA:
        raise ValueError(
            f"task supervision policy schema must be {TASK_SUPERVISION_POLICY_SCHEMA!r}: {path}"
        )

    raw_assignments = payload.get("assignments", {})
    if not isinstance(raw_assignments, Mapping):
        raise ValueError(f"task supervision policy assignments must be an object: {path}")

    assignments: dict[str, TaskSupervisionAssignment] = {}
    for raw_task_id, raw_assignment in raw_assignments.items():
        task_id = str(raw_task_id).strip()
        if not task_id:
            raise ValueError(f"task supervision policy contains an empty task id: {path}")
        if not isinstance(raw_assignment, Mapping):
            raise ValueError(f"task supervision assignment for {task_id!r} must be an object")
        mode = str(raw_assignment.get("mode", "")).strip()
        if mode not in VALID_TASK_SUPERVISION_MODES:
            raise ValueError(f"invalid supervision mode {mode!r} for {task_id!r}")
        rationale = str(raw_assignment.get("rationale", "")).strip()
        valid_rationales = VALID_TASK_SUPERVISION_RATIONALES_BY_MODE[mode]
        if rationale not in valid_rationales:
            raise ValueError(
                f"invalid supervision rationale {rationale!r} for {task_id!r} "
                f"in mode {mode!r}; expected one of {sorted(valid_rationales)!r}"
            )
        assignments[task_id] = TaskSupervisionAssignment(
            task_id=task_id,
            mode=mode,
            rationale=rationale,
            notes=str(raw_assignment.get("notes", "")).strip(),
        )

    raw_reviewed_scenes = payload.get("reviewed_scenes", [])
    if not isinstance(raw_reviewed_scenes, list):
        raise ValueError(f"task supervision policy reviewed_scenes must be an array: {path}")
    reviewed_scenes = tuple(str(item).strip() for item in raw_reviewed_scenes if str(item).strip())

    return TaskSupervisionPolicy(
        policy_id=str(payload.get("policy_id", "")).strip(),
        status=str(payload.get("status", "")).strip(),
        mode_field=str(payload.get("mode_field", "trace_supervision_mode")).strip(),
        reviewed_scenes=reviewed_scenes,
        assignments=assignments,
        path=path,
    )


__all__ = [
    "TASK_SUPERVISION_POLICY_REL_PATH",
    "TASK_SUPERVISION_POLICY_SCHEMA",
    "VALID_ANNOTATION_SUPERVISION_RATIONALES",
    "VALID_ANSWER_SUPERVISION_RATIONALES",
    "VALID_TASK_SUPERVISION_MODES",
    "VALID_TASK_SUPERVISION_RATIONALES_BY_MODE",
    "TaskSupervisionAssignment",
    "TaskSupervisionPolicy",
    "load_task_supervision_policy",
]
