"""Contract tests for misc music-staff notation tasks."""

from __future__ import annotations

import pytest

from trace.tasks import TASK_REGISTRY
from trace.tasks.misc.notation.music_staff import (
    ARTICULATION_SYMBOL_TASK_ID,
    CHORD_HARMONY_QUERY_IDS,
    CHORD_HARMONY_TASK_ID,
    INTERVAL_NAME_TASK_ID,
    KEY_SIGNATURE_TASK_ID,
    METER_TYPE_TASK_ID,
    NOTE_NAME_TASK_ID,
    SCENE_ID,
    SCALE_DEGREE_FUNCTION_TASK_ID,
    SCALE_VALIDATION_TRUTH_TASK_ID,
    SAME_PITCH_TRUTH_TASK_ID,
    TIME_SIGNATURE_TASK_ID,
    TRANSPOSED_PITCH_TRUTH_TASK_ID,
    MiscArticulationSymbolLabelTask,
    MiscChordHarmonyLabelTask,
    MiscIntervalNameLabelTask,
    MiscKeySignatureLabelTask,
    MiscMeterTypeLabelTask,
    MiscNoteNameLabelTask,
    MiscScaleDegreeFunctionLabelTask,
    MiscScaleValidationTruthLabelTask,
    MiscSamePitchTruthLabelTask,
    MiscTimeSignatureLabelTask,
    MiscTransposedPitchTruthLabelTask,
)


TASKS = (
    (NOTE_NAME_TASK_ID, MiscNoteNameLabelTask, ("note_name_label",)),
    (INTERVAL_NAME_TASK_ID, MiscIntervalNameLabelTask, ("interval_name_label",)),
    (SAME_PITCH_TRUTH_TASK_ID, MiscSamePitchTruthLabelTask, ("same_pitch_truth_label",)),
    (TRANSPOSED_PITCH_TRUTH_TASK_ID, MiscTransposedPitchTruthLabelTask, ("transposed_pitch_truth_label",)),
    (KEY_SIGNATURE_TASK_ID, MiscKeySignatureLabelTask, ("key_signature_label",)),
    (SCALE_VALIDATION_TRUTH_TASK_ID, MiscScaleValidationTruthLabelTask, ("scale_validation_truth_label",)),
    (SCALE_DEGREE_FUNCTION_TASK_ID, MiscScaleDegreeFunctionLabelTask, ("scale_degree_function_label",)),
    (CHORD_HARMONY_TASK_ID, MiscChordHarmonyLabelTask, CHORD_HARMONY_QUERY_IDS),
    (TIME_SIGNATURE_TASK_ID, MiscTimeSignatureLabelTask, ("time_signature_label",)),
    (METER_TYPE_TASK_ID, MiscMeterTypeLabelTask, ("meter_type_label",)),
    (ARTICULATION_SYMBOL_TASK_ID, MiscArticulationSymbolLabelTask, ("articulation_symbol_label",)),
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
        assert task.domain == "misc"
        assert task.task_group == "notation"


@pytest.mark.parametrize("task_cls, query_id", QUERY_CASES)
def test_notation_query_ids_emit_public_contract(task_cls, query_id: str) -> None:
    out = task_cls().generate(
        2026052401,
        params={"query_id": query_id, "scene_variant": "engraved_sheet"},
        max_attempts=60,
    )
    trace = out.trace_payload

    assert out.scene_id == SCENE_ID
    assert out.query_id == query_id
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) >= 1
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
    assert '"answer"' in out.prompt_variants["answer_only"]
    assert "annotation" in out.prompt_variants["answer_and_annotation"].lower()

    assert trace["query_spec"]["params"]["scene_id"] == SCENE_ID
    assert trace["query_spec"]["params"]["query_id"] == query_id
    assert trace["query_spec"]["params"]["query_id"] == query_id
    assert trace["render_spec"]["scene_id"] == SCENE_ID
    assert trace["render_spec"]["scene_style"]
    assert trace["render_spec"]["music_style"]
    assert trace["render_map"]["annotation_source"] == "item_bboxes_px"
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert trace["execution_trace"]["answer_value"] == out.answer_gt.value
    assert trace["execution_trace"]["answer_type"] == out.answer_gt.type

    width, height = out.image.size
    assert width == int(trace["render_spec"]["canvas_width"])
    assert height == int(trace["render_spec"]["canvas_height"])
    for bbox in out.annotation_gt.value:
        assert len(bbox) == 4
        assert 0 <= float(bbox[0]) < float(bbox[2]) <= width
        assert 0 <= float(bbox[1]) < float(bbox[3]) <= height


@pytest.mark.parametrize(
    "task_cls, query_id",
    (
        (MiscNoteNameLabelTask, "note_name_label"),
        (MiscKeySignatureLabelTask, "key_signature_label"),
        (MiscChordHarmonyLabelTask, CHORD_HARMONY_QUERY_IDS[0]),
        (MiscTimeSignatureLabelTask, "time_signature_label"),
    ),
)
def test_notation_generation_is_deterministic(task_cls, query_id: str) -> None:
    params = {"query_id": query_id, "scene_variant": "notebook_staff"}
    out_a = task_cls().generate(2026052499, params=params, max_attempts=60)
    out_b = task_cls().generate(2026052499, params=params, max_attempts=60)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.annotation_gt == out_b.annotation_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()
