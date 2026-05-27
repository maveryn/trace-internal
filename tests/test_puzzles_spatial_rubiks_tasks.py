"""Contract tests for Rubik-style cube-net puzzle tasks."""

from __future__ import annotations

import json

from trace.tasks import TASK_REGISTRY
from trace.tasks.puzzles.spatial.rubiks_cube import (
    PuzzlesSpatialRubiksFaceColorCountLabelTask,
    PuzzlesSpatialRubiksMoveResultLabelTask,
    PuzzlesSpatialRubiksStickerColorLabelTask,
)
from trace.tasks.puzzles.shared.rubiks_scene import (
    FACE_COLOR_COUNT_QUERY_IDS,
    MOVE_RESULT_QUERY_IDS,
    STICKER_COLOR_QUERY_IDS,
)


TASKS = (
    (
        "task_puzzles__rubiks_net__rubiks_sticker_color_label",
        PuzzlesSpatialRubiksStickerColorLabelTask,
        set(STICKER_COLOR_QUERY_IDS),
    ),
    (
        "task_puzzles__rubiks_net__rubiks_face_color_count_label",
        PuzzlesSpatialRubiksFaceColorCountLabelTask,
        set(FACE_COLOR_COUNT_QUERY_IDS),
    ),
    (
        "task_puzzles__rubiks_net__rubiks_move_result_label",
        PuzzlesSpatialRubiksMoveResultLabelTask,
        set(MOVE_RESULT_QUERY_IDS),
    ),
)


def test_rubiks_tasks_are_registered() -> None:
    for task_id, task_cls, _queries in TASKS:
        assert TASK_REGISTRY[task_id] is task_cls
        task = task_cls()
        assert task.domain == "puzzles"
        assert task.task_group == "spatial"


def test_rubiks_tasks_emit_public_contracts() -> None:
    for task_index, (_task_id, task_cls, queries) in enumerate(TASKS):
        for query_index, query_id in enumerate(sorted(queries)):
            out = task_cls().generate(
                2026052200 + (task_index * 20) + query_index,
                params={"query_variant": query_id},
                max_attempts=30,
            )
            trace = out.trace_payload
            execution = trace["execution_trace"]

            json.dumps(trace)
            assert out.scene_id == "rubiks_net"
            assert out.query_variant == "default"
            assert out.query_id == query_id
            assert execution["query_variant"] == "default"
            assert execution["query_id"] == query_id
            assert trace["query_spec"]["query_id"] == query_id
            assert trace["render_spec"]["scene_id"] == "rubiks_net"
            assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
            assert out.answer_gt.type == "option_letter"
            assert out.evidence_gt.type == "bbox_set"
            assert len(out.evidence_gt.value) == 1
            assert str(out.answer_gt.value) == str(execution["answer_option_label"])
            assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
            assert out.image.size == (
                int(trace["render_spec"]["canvas_width"]),
                int(trace["render_spec"]["canvas_height"]),
            )
            assert execution["option_count"] == 6
            assert len(execution["option_specs"]) == 6
            assert execution["start_state"]
            assert execution["final_state"]

            for bbox in out.evidence_gt.value:
                assert len(bbox) == 4
                assert 0 <= float(bbox[0]) < float(bbox[2]) <= out.image.size[0]
                assert 0 <= float(bbox[1]) < float(bbox[3]) <= out.image.size[1]


def test_rubiks_generation_is_deterministic() -> None:
    task = PuzzlesSpatialRubiksMoveResultLabelTask()
    params = {
        "query_variant": "two_move_result_label",
        "scene_variant": "paper_net",
    }
    out_a = task.generate(2026052299, params=params, max_attempts=30)
    out_b = task.generate(2026052299, params=params, max_attempts=30)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
