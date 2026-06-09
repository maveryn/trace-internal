"""Contract tests for nonogram puzzle tasks."""

from __future__ import annotations

from trace.tasks import TASK_REGISTRY
from trace.tasks.puzzles.logic.nonogram_grid import (
    PuzzlesLogicNonogramCandidateSolutionLabelTask,
    PuzzlesLogicNonogramLineCompletionLabelTask,
)


TASKS = (
    (
        "task_puzzles__nonogram__nonogram_line_completion_label",
        PuzzlesLogicNonogramLineCompletionLabelTask,
        "line_completion_label",
        "option_letter",
    ),
    (
        "task_puzzles__nonogram__nonogram_candidate_solution_label",
        PuzzlesLogicNonogramCandidateSolutionLabelTask,
        "candidate_solution_label",
        "option_letter",
    ),
)


def test_nonogram_tasks_are_registered() -> None:
    for task_id, task_cls, _query_id, _answer_type in TASKS:
        assert TASK_REGISTRY[task_id] is task_cls
        task = task_cls()
        assert task.domain == "puzzles"
        assert task.task_group == "logic"


def test_nonogram_tasks_emit_public_contracts() -> None:
    for index, (_task_id, task_cls, query_id, answer_type) in enumerate(TASKS):
        out = task_cls().generate(2026052300 + index, params={}, max_attempts=20)
        trace = out.trace_payload
        execution = trace["execution_trace"]

        assert out.scene_id == "nonogram"
        assert out.query_id == query_id
        assert out.answer_gt.type == answer_type
        assert out.annotation_gt.type == "bbox_set"
        assert execution["query_id"] == query_id
        assert trace["query_spec"]["query_id"] == query_id
        assert trace["render_spec"]["scene_id"] == "nonogram"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
        assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
        assert out.image.size == (
            int(trace["render_spec"]["canvas_width"]),
            int(trace["render_spec"]["canvas_height"]),
        )

        for bbox in out.annotation_gt.value:
            assert len(bbox) == 4
            assert 0 <= float(bbox[0]) < float(bbox[2]) <= out.image.size[0]
            assert 0 <= float(bbox[1]) < float(bbox[3]) <= out.image.size[1]

        assert str(out.answer_gt.value) == str(execution["answer_value"])
        assert 4 <= int(execution["option_count"]) <= 6
        assert len(out.annotation_gt.value) == 3


def test_nonogram_generation_is_deterministic() -> None:
    task = PuzzlesLogicNonogramCandidateSolutionLabelTask()
    params = {"scene_variant": "nonogram_card"}
    out_a = task.generate(2026052399, params=params, max_attempts=20)
    out_b = task.generate(2026052399, params=params, max_attempts=20)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_nonogram_line_completion_options_have_unique_valid_answer() -> None:
    out = PuzzlesLogicNonogramLineCompletionLabelTask().generate(2026052401, params={}, max_attempts=20)
    execution = out.trace_payload["execution_trace"]
    clue = [int(value) for value in execution["marked_clue"]]
    partial = execution["partial_line"]
    valid_labels = []
    from trace.tasks.puzzles.shared.nonogram_scene import clue_for_line, line_matches_partial

    for option in execution["option_specs"]:
        line = [int(value) for value in option["line"]]
        if clue_for_line(line) == clue and line_matches_partial(line, partial):
            valid_labels.append(str(option["option_label"]))
    assert valid_labels == [str(out.answer_gt.value)]
