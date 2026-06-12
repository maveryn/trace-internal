"""Contract tests for symbolic music-staff notation tasks."""

from __future__ import annotations

import pytest

from trace.tasks import TASK_REGISTRY
from trace.tasks.symbolic.notation.music_staff import (
    ARTICULATION_SYMBOL_TASK_ID,
    CHORD_HARMONY_QUERY_IDS,
    CHORD_HARMONY_TASK_ID,
    DOMINANT_CHORD_COUNT_TASK_ID,
    INTERVAL_NAME_TASK_ID,
    KEY_SIGNATURE_TASK_ID,
    METER_TYPE_TASK_ID,
    NOTE_NAME_TASK_ID,
    SCENE_ID,
    SCALE_DEGREE_FUNCTION_TASK_ID,
    SCALE_VALIDATION_COUNT_TASK_ID,
    SAME_PITCH_PAIR_COUNT_TASK_ID,
    TRANSPOSED_PITCH_PAIR_COUNT_TASK_ID,
    SymbolicArticulationSymbolLabelTask,
    SymbolicChordHarmonyLabelTask,
    SymbolicDominantChordCountTask,
    SymbolicIntervalNameLabelTask,
    SymbolicKeySignatureLabelTask,
    SymbolicMeterTypeCountTask,
    SymbolicNoteNameLabelTask,
    SymbolicScaleDegreeFunctionLabelTask,
    SymbolicScaleValidationCountTask,
    SymbolicSamePitchPairCountTask,
    SymbolicTransposedPitchPairCountTask,
)


TASKS = (
    (NOTE_NAME_TASK_ID, SymbolicNoteNameLabelTask, ("note_name_label",)),
    (INTERVAL_NAME_TASK_ID, SymbolicIntervalNameLabelTask, ("interval_name_label",)),
    (SAME_PITCH_PAIR_COUNT_TASK_ID, SymbolicSamePitchPairCountTask, ("same_pitch_pair_count",)),
    (TRANSPOSED_PITCH_PAIR_COUNT_TASK_ID, SymbolicTransposedPitchPairCountTask, ("transposed_pitch_pair_count",)),
    (KEY_SIGNATURE_TASK_ID, SymbolicKeySignatureLabelTask, ("key_signature_label",)),
    (SCALE_VALIDATION_COUNT_TASK_ID, SymbolicScaleValidationCountTask, ("scale_validation_count",)),
    (SCALE_DEGREE_FUNCTION_TASK_ID, SymbolicScaleDegreeFunctionLabelTask, ("scale_degree_function_label",)),
    (CHORD_HARMONY_TASK_ID, SymbolicChordHarmonyLabelTask, CHORD_HARMONY_QUERY_IDS),
    (DOMINANT_CHORD_COUNT_TASK_ID, SymbolicDominantChordCountTask, ("dominant_count_value",)),
    (METER_TYPE_TASK_ID, SymbolicMeterTypeCountTask, ("meter_type_count",)),
    (ARTICULATION_SYMBOL_TASK_ID, SymbolicArticulationSymbolLabelTask, ("articulation_symbol_label",)),
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
        assert task.domain == "symbolic"
        assert task.scene_id == "notation"


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
    if task_cls in {SymbolicDominantChordCountTask, SymbolicMeterTypeCountTask, SymbolicSamePitchPairCountTask, SymbolicScaleValidationCountTask, SymbolicTransposedPitchPairCountTask} and int(out.answer_gt.value) == 0:
        assert out.annotation_gt.value == []
    else:
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
        (SymbolicNoteNameLabelTask, "note_name_label"),
        (SymbolicKeySignatureLabelTask, "key_signature_label"),
        (SymbolicChordHarmonyLabelTask, CHORD_HARMONY_QUERY_IDS[0]),
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


def test_dominant_chord_count_annotation_contains_only_counted_chords() -> None:
    for target_answer in range(0, 5):
        out = SymbolicDominantChordCountTask().generate(
            2026060900 + int(target_answer),
            params={
                "query_id": "dominant_count_value",
                "scene_variant": "engraved_sheet",
                "target_answer": int(target_answer),
            },
            max_attempts=60,
        )
        assert out.answer_gt.value == int(target_answer)
        assert out.annotation_gt.type == "bbox_set"
        assert len(out.annotation_gt.value) == int(target_answer)
        assert out.trace_payload["execution_trace"]["annotation_item_ids"] == [
            f"chord_{position}"
            for position in out.trace_payload["execution_trace"]["notation_metadata"]["dominant_positions"]
        ]


def test_same_pitch_pair_count_annotation_contains_only_counted_pairs() -> None:
    for target_answer in range(0, 5):
        out = SymbolicSamePitchPairCountTask().generate(
            2026060920 + int(target_answer),
            params={
                "query_id": "same_pitch_pair_count",
                "scene_variant": "engraved_sheet",
                "target_answer": int(target_answer),
            },
            max_attempts=60,
        )
        assert out.answer_gt.value == int(target_answer)
        assert out.annotation_gt.type == "bbox_set"
        assert len(out.annotation_gt.value) == int(target_answer)
        assert out.trace_payload["execution_trace"]["annotation_item_ids"] == [
            f"pair_{position}"
            for position in out.trace_payload["execution_trace"]["notation_metadata"]["target_pair_indices_1based"]
        ]


def test_transposed_pitch_pair_count_annotation_contains_only_counted_pairs() -> None:
    for target_answer in range(0, 5):
        out = SymbolicTransposedPitchPairCountTask().generate(
            2026060940 + int(target_answer),
            params={
                "query_id": "transposed_pitch_pair_count",
                "scene_variant": "engraved_sheet",
                "target_answer": int(target_answer),
            },
            max_attempts=60,
        )
        assert out.answer_gt.value == int(target_answer)
        assert out.annotation_gt.type == "bbox_set"
        assert len(out.annotation_gt.value) == int(target_answer)
        assert out.trace_payload["execution_trace"]["annotation_item_ids"] == [
            f"pair_{position}"
            for position in out.trace_payload["execution_trace"]["notation_metadata"]["target_pair_indices_1based"]
        ]


def test_scale_validation_count_annotation_contains_only_counted_fragments() -> None:
    for target_answer in range(0, 5):
        out = SymbolicScaleValidationCountTask().generate(
            2026060930 + int(target_answer),
            params={
                "query_id": "scale_validation_count",
                "scene_variant": "engraved_sheet",
                "target_answer": int(target_answer),
            },
            max_attempts=60,
        )
        assert out.answer_gt.value == int(target_answer)
        assert out.annotation_gt.type == "bbox_set"
        assert len(out.annotation_gt.value) == int(target_answer)
        assert out.trace_payload["execution_trace"]["annotation_item_ids"] == [
            f"fragment_{position}"
            for position in out.trace_payload["execution_trace"]["notation_metadata"]["target_fragment_indices_1based"]
        ]


def test_meter_type_count_annotation_contains_only_counted_measures() -> None:
    for target_answer in range(0, 5):
        out = SymbolicMeterTypeCountTask().generate(
            2026060910 + int(target_answer),
            params={
                "query_id": "meter_type_count",
                "scene_variant": "engraved_sheet",
                "target_answer": int(target_answer),
                "target_meter_type": "compound",
            },
            max_attempts=60,
        )
        assert out.answer_gt.value == int(target_answer)
        assert out.annotation_gt.type == "bbox_set"
        assert len(out.annotation_gt.value) == int(target_answer)
        assert out.trace_payload["execution_trace"]["annotation_item_ids"] == [
            f"measure_{position}"
            for position in out.trace_payload["execution_trace"]["notation_metadata"]["target_measure_indices_1based"]
        ]
