"""Contract tests for Sokoban-style grid puzzle tasks."""

from __future__ import annotations

import json

from trace.tasks import TASK_REGISTRY
from trace.tasks.puzzles.shared.sokoban_scene import (
    SOKOBAN_BOX_TARGET_RELATION_QUERY_IDS,
    SOKOBAN_PATH_SEQUENCE_QUERY_IDS,
)
from trace.tasks.puzzles.spatial.sokoban_grid import (
    PuzzlesSpatialSokobanBoxTargetRelationLabelTask,
    PuzzlesSpatialSokobanPathSequenceLabelTask,
)


TASKS = (
    (
        "task_puzzles__sokoban__sokoban_path_sequence_label",
        PuzzlesSpatialSokobanPathSequenceLabelTask,
        set(SOKOBAN_PATH_SEQUENCE_QUERY_IDS),
    ),
    (
        "task_puzzles__sokoban__sokoban_box_target_relation_label",
        PuzzlesSpatialSokobanBoxTargetRelationLabelTask,
        set(SOKOBAN_BOX_TARGET_RELATION_QUERY_IDS),
    ),
)


def test_sokoban_tasks_are_registered() -> None:
    for task_id, task_cls, _queries in TASKS:
        assert TASK_REGISTRY[task_id] is task_cls
        task = task_cls()
        assert task.domain == "puzzles"
        assert task.task_group == "spatial"


def test_sokoban_tasks_emit_public_contracts() -> None:
    for task_index, (_task_id, task_cls, queries) in enumerate(TASKS):
        for query_index, query_id in enumerate(sorted(queries)):
            out = task_cls().generate(
                2026052300 + (task_index * 30) + query_index,
                params={"query_id": query_id},
                max_attempts=30,
            )
            trace = out.trace_payload
            execution = trace["execution_trace"]

            json.dumps(trace)
            assert out.scene_id == "sokoban"
            assert out.query_id == "default"
            assert out.query_id == query_id
            assert execution["query_id"] == "default"
            assert execution["query_id"] == query_id
            assert trace["query_spec"]["query_id"] == query_id
            assert trace["render_spec"]["scene_id"] == "sokoban"
            assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
            assert out.answer_gt.type == "option_letter"
            assert out.evidence_gt.type == "bbox_set"
            if task_cls is PuzzlesSpatialSokobanBoxTargetRelationLabelTask:
                assert 1 <= len(out.evidence_gt.value) <= 2
                assert trace["render_map"]["evidence_source"] == "cell_bboxes_px"
            else:
                assert len(out.evidence_gt.value) == 1
                assert trace["render_map"]["evidence_source"] == "option_panel_bboxes_px"
            assert str(out.answer_gt.value) == str(execution["answer_option_label"])
            assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
            assert out.image.size == (
                int(trace["render_spec"]["canvas_width"]),
                int(trace["render_spec"]["canvas_height"]),
            )
            assert execution["option_count"] == 6
            assert len(execution["option_specs"]) == 6
            assert execution["walls"]
            assert execution["boxes_start"]
            assert execution["targets"]

            for bbox in out.evidence_gt.value:
                assert len(bbox) == 4
                assert 0 <= float(bbox[0]) < float(bbox[2]) <= out.image.size[0]
                assert 0 <= float(bbox[1]) < float(bbox[3]) <= out.image.size[1]


def test_sokoban_generation_is_deterministic() -> None:
    task = PuzzlesSpatialSokobanPathSequenceLabelTask()
    params = {
        "query_id": "shortest_path_sequence_label",
        "scene_variant": "paper_grid",
    }
    out_a = task.generate(2026052399, params=params, max_attempts=30)
    out_b = task.generate(2026052399, params=params, max_attempts=30)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
