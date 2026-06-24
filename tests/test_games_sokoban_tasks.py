"""Contract tests for Sokoban-style game tasks."""

from __future__ import annotations

import json

from trace.tasks import TASK_REGISTRY
from trace.tasks.games.sokoban.box_goal_status_count import GamesSokobanBoxGoalStatusCountTask
from trace.tasks.games.sokoban.closest_box_goal_label import GamesSokobanClosestBoxGoalLabelTask


TASKS = (
    (
        "task_games__sokoban__box_goal_status_count",
        GamesSokobanBoxGoalStatusCountTask,
        ("box_on_goal_count", "box_off_goal_count"),
        "integer",
        "bbox_set",
    ),
    (
        "task_games__sokoban__closest_box_goal_label",
        GamesSokobanClosestBoxGoalLabelTask,
        ("single",),
        "option_letter",
        "bbox",
    ),
)


def _annotation_bboxes(annotation_value):
    if annotation_value and isinstance(annotation_value[0], (int, float)):
        return [annotation_value]
    return list(annotation_value)


def test_sokoban_tasks_are_registered() -> None:
    for task_id, task_cls, _queries, _answer_schema, _annotation_schema in TASKS:
        assert TASK_REGISTRY[task_id] is task_cls
        task = task_cls()
        assert task.domain == "games"
        assert not hasattr(task_cls, "scene_id")


def test_sokoban_tasks_emit_public_contracts() -> None:
    for task_index, (_task_id, task_cls, queries, answer_schema, annotation_schema) in enumerate(TASKS):
        for query_index, query_id in enumerate(queries):
            out = task_cls().generate(
                2026052300 + (task_index * 30) + query_index,
                params={"query_id": query_id},
                max_attempts=60,
            )
            trace = out.trace_payload
            execution = trace["execution_trace"]

            json.dumps(trace)
            assert out.scene_id == "sokoban"
            assert out.query_id == query_id
            assert trace["query_spec"]["query_id"] == query_id
            assert trace["render_spec"]["scene_id"] == "sokoban"
            assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
            assert out.answer_gt.type == answer_schema
            assert out.annotation_gt.type == annotation_schema
            assert str(out.answer_gt.value) == str(execution["answer_value"])
            assert out.image.size == (
                int(trace["render_spec"]["canvas_width"]),
                int(trace["render_spec"]["canvas_height"]),
            )

            assert trace["render_map"]["annotation_source"] == "cell_bboxes_px"
            assert execution["walls"]
            assert execution["boxes_start"]
            assert execution["targets"]

            if query_id in {"box_on_goal_count", "box_off_goal_count"}:
                assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
                assert execution["option_count"] == 0
                assert execution["option_specs"] == []
                assert trace["query_spec"]["params"]["prompt_query_key"] == query_id
                assert execution["query_id"] == query_id
                assert execution["goal_status_count"] == int(out.answer_gt.value)
                assert len(out.annotation_gt.value) == int(out.answer_gt.value)
                assert 1 <= int(out.answer_gt.value) <= 5
                assert len(execution["boxes_on_matching_goals"]) >= 1
                assert len(execution["boxes_off_matching_goals"]) >= 1
            elif query_id == "single":
                assert trace["projected_annotation"]["bbox"] == out.annotation_gt.value
                support = execution["relation_support"]
                distances = {
                    str(item["box_label"]): int(item["distance"])
                    for item in support["pair_distances"]
                }
                answer = str(out.answer_gt.value)
                assert execution["distance_kind"] == "manhattan"
                assert execution["query_id"] == "single"
                assert execution["internal_query_id"] == "closest_box_goal_label"
                assert trace["query_spec"]["params"]["prompt_query_key"] == "closest_box_goal_label"
                assert int(execution["option_count"]) in {4, 6}
                assert answer == str(support["answer_box_label"])
                assert distances[answer] == min(distances.values())
                assert sum(1 for value in distances.values() if value == distances[answer]) == 1
                assert len(out.annotation_gt.value) == 4
                assert len(execution["boxes_on_matching_goals"]) == 0

            for bbox in _annotation_bboxes(out.annotation_gt.value):
                assert len(bbox) == 4
                assert 0 <= float(bbox[0]) < float(bbox[2]) <= out.image.size[0]
                assert 0 <= float(bbox[1]) < float(bbox[3]) <= out.image.size[1]


def test_sokoban_generation_is_deterministic() -> None:
    cases = (
        (
            GamesSokobanBoxGoalStatusCountTask(),
            {"query_id": "box_off_goal_count", "scene_variant": "paper_grid"},
        ),
        (
            GamesSokobanClosestBoxGoalLabelTask(),
            {"query_id": "single", "scene_variant": "paper_grid"},
        ),
    )
    for task, params in cases:
        out_a = task.generate(2026052399, params=params, max_attempts=60)
        out_b = task.generate(2026052399, params=params, max_attempts=60)

        assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
        assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
        assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
        assert out_a.prompt == out_b.prompt
        assert out_a.image.tobytes() == out_b.image.tobytes()
