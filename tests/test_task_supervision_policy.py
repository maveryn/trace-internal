from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

from trace.core.source_layout_policy import parse_public_task_id
from trace.core.task_supervision_policy import (
    TASK_SUPERVISION_POLICY_REL_PATH,
    VALID_ANNOTATION_SUPERVISION_RATIONALES,
    VALID_ANSWER_SUPERVISION_RATIONALES,
    VALID_TASK_SUPERVISION_MODES,
    VALID_TASK_SUPERVISION_RATIONALES_BY_MODE,
    load_task_supervision_policy,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
ACTIVE_TASK_IDS = frozenset(
    re.findall(
        r"^- `(task_[^`]+)`$",
        (REPO_ROOT / "docs" / "ACTIVE_TASK_INVENTORY.md").read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
)


def _scene_task_ids(domain: str, scene_id: str) -> set[str]:
    return {
        task_id
        for task_id in ACTIVE_TASK_IDS
        if (parts := parse_public_task_id(task_id)).domain == domain
        and parts.scene_id == scene_id
    }


def test_task_supervision_policy_covers_every_task_in_each_reviewed_scene() -> None:
    policy = load_task_supervision_policy(REPO_ROOT)

    assert policy.policy_id == "task_conditioned_v1"
    assert policy.status == "draft"
    assert policy.mode_field == "trace_supervision_mode"
    assert policy.reviewed_scenes == tuple(sorted(set(policy.reviewed_scenes)))

    for scene_key in policy.reviewed_scenes:
        domain, scene_id = scene_key.split("/", 1)
        expected = _scene_task_ids(domain, scene_id)
        assigned = {
            task_id
            for task_id in policy.assignments
            if (parts := parse_public_task_id(task_id)).domain == domain
            and parts.scene_id == scene_id
        }
        assert assigned == expected, scene_key


def test_task_supervision_policy_covers_the_complete_active_inventory() -> None:
    policy = load_task_supervision_policy(REPO_ROOT)
    expected_task_ids = set(ACTIVE_TASK_IDS)
    assigned_task_ids = set(policy.assignments)
    expected_scene_keys = {
        f"{parse_public_task_id(task_id).domain}/{parse_public_task_id(task_id).scene_id}"
        for task_id in expected_task_ids
    }

    assert len(expected_task_ids) == 1000
    assert assigned_task_ids == expected_task_ids
    assert set(policy.reviewed_scenes) == expected_scene_keys


def test_task_supervision_policy_assignments_are_reviewed_and_resolved() -> None:
    policy = load_task_supervision_policy(REPO_ROOT)
    reviewed_scenes = set(policy.reviewed_scenes)

    for task_id, assignment in policy.assignments.items():
        parts = parse_public_task_id(task_id)
        assert f"{parts.domain}/{parts.scene_id}" in reviewed_scenes
        assert assignment.mode in VALID_TASK_SUPERVISION_MODES
        assert assignment.rationale in VALID_TASK_SUPERVISION_RATIONALES_BY_MODE[assignment.mode]
        assert assignment.notes

    assert {
        assignment.rationale
        for assignment in policy.assignments.values()
        if assignment.mode == "answer"
    } <= VALID_ANSWER_SUPERVISION_RATIONALES
    assert {
        assignment.rationale
        for assignment in policy.assignments.values()
        if assignment.mode == "answer_and_annotation"
    } <= VALID_ANNOTATION_SUPERVISION_RATIONALES


@pytest.mark.parametrize(
    ("mode", "rationale"),
    [
        ("answer", "target_grounding"),
        ("answer_and_annotation", "derived_reasoning"),
        ("answer_and_annotation", "direct_grounding"),
        ("answer", "manual_decision"),
    ],
)
def test_task_supervision_policy_rejects_cross_mode_and_legacy_rationales(
    tmp_path: Path,
    mode: str,
    rationale: str,
) -> None:
    policy_path = tmp_path / TASK_SUPERVISION_POLICY_REL_PATH
    policy_path.parent.mkdir(parents=True)
    policy_path.write_text(
        json.dumps(
            {
                "schema": "trace_task_supervision_policy_v1",
                "policy_id": "task_conditioned_v1",
                "status": "draft",
                "mode_field": "trace_supervision_mode",
                "reviewed_scenes": ["charts/example"],
                "assignments": {
                    "task_charts__example__objective": {
                        "mode": mode,
                        "rationale": rationale,
                        "notes": "test assignment",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid supervision rationale"):
        load_task_supervision_policy(tmp_path)
