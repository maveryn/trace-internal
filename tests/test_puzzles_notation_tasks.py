"""Contract tests for music-staff notation puzzle tasks."""

from __future__ import annotations

import pytest

from trace.tasks import TASK_REGISTRY
from trace.tasks.puzzles.notation.music_staff import (
    CHORD_HARMONY_QUERY_IDS,
    CHORD_HARMONY_TASK_ID,
    KEY_SCALE_QUERY_IDS,
    KEY_SCALE_TASK_ID,
    METER_RHYTHM_QUERY_IDS,
    METER_RHYTHM_TASK_ID,
    PITCH_INTERVAL_QUERY_IDS,
    PITCH_INTERVAL_TASK_ID,
    SCENE_ID,
    PuzzlesNotationChordHarmonyLabelTask,
    PuzzlesNotationKeyScaleLabelTask,
    PuzzlesNotationMeterRhythmLabelTask,
    PuzzlesNotationPitchIntervalLabelTask,
)


TASKS = (
    (PITCH_INTERVAL_TASK_ID, PuzzlesNotationPitchIntervalLabelTask, PITCH_INTERVAL_QUERY_IDS),
    (KEY_SCALE_TASK_ID, PuzzlesNotationKeyScaleLabelTask, KEY_SCALE_QUERY_IDS),
    (CHORD_HARMONY_TASK_ID, PuzzlesNotationChordHarmonyLabelTask, CHORD_HARMONY_QUERY_IDS),
    (METER_RHYTHM_TASK_ID, PuzzlesNotationMeterRhythmLabelTask, METER_RHYTHM_QUERY_IDS),
)


QUERY_CASES = tuple(
    (task_cls, query_id)
    for _task_id, task_cls, query_ids in TASKS
    for query_id in query_ids
)


def test_notation_tasks_are_registered() -> None:
    for task_id, task_cls, _query_ids in TASKS:
        assert TASK_REGISTRY[task_id] is task_cls
        task = task_cls()
        assert task.domain == "puzzles"
        assert task.task_group == "notation"


@pytest.mark.parametrize("task_cls, query_id", QUERY_CASES)
def test_notation_query_variants_emit_public_contract(task_cls, query_id: str) -> None:
    out = task_cls().generate(
        2026052401,
        params={"query_variant": query_id, "scene_variant": "engraved_sheet"},
        max_attempts=60,
    )
    trace = out.trace_payload

    assert out.scene_id == SCENE_ID
    assert out.query_variant == "default"
    assert out.query_id == query_id
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) >= 1
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert '"answer"' in out.prompt_variants["answer_only"]
    assert "evidence" in out.prompt_variants["answer_and_evidence"].lower()

    assert trace["query_spec"]["params"]["scene_id"] == SCENE_ID
    assert trace["query_spec"]["params"]["query_id"] == query_id
    assert trace["query_spec"]["params"]["query_variant"] == query_id
    assert trace["render_spec"]["scene_id"] == SCENE_ID
    assert trace["render_spec"]["scene_style"]
    assert trace["render_spec"]["music_style"]
    assert trace["render_map"]["evidence_source"] == "item_bboxes_px"
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert trace["execution_trace"]["answer_value"] == out.answer_gt.value
    assert trace["execution_trace"]["answer_type"] == out.answer_gt.type

    width, height = out.image.size
    assert width == int(trace["render_spec"]["canvas_width"])
    assert height == int(trace["render_spec"]["canvas_height"])
    for bbox in out.evidence_gt.value:
        assert len(bbox) == 4
        assert 0 <= float(bbox[0]) < float(bbox[2]) <= width
        assert 0 <= float(bbox[1]) < float(bbox[3]) <= height


@pytest.mark.parametrize(
    "task_cls, query_id",
    (
        (PuzzlesNotationPitchIntervalLabelTask, PITCH_INTERVAL_QUERY_IDS[0]),
        (PuzzlesNotationKeyScaleLabelTask, KEY_SCALE_QUERY_IDS[0]),
        (PuzzlesNotationChordHarmonyLabelTask, CHORD_HARMONY_QUERY_IDS[0]),
        (PuzzlesNotationMeterRhythmLabelTask, METER_RHYTHM_QUERY_IDS[0]),
    ),
)
def test_notation_generation_is_deterministic(task_cls, query_id: str) -> None:
    params = {"query_variant": query_id, "scene_variant": "notebook_staff"}
    out_a = task_cls().generate(2026052499, params=params, max_attempts=60)
    out_b = task_cls().generate(2026052499, params=params, max_attempts=60)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.evidence_gt == out_b.evidence_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()
