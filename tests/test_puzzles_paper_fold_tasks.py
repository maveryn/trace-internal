"""Behavior tests for migrated paper-fold puzzle tasks."""

from __future__ import annotations

from typing import Sequence

from trace.tasks.puzzles.paper_fold.paper_fold_result_label import (
    PuzzlesPaperFoldResultLabelTask,
)
from tests.helpers import extract_prompt_json_example


def _mark_signature(mark_specs: list[dict[str, object]]) -> tuple[tuple[str, int, int], ...]:
    """Return one hashable signature for a folded-result mark set."""

    return tuple(
        sorted(
            (
                str(mark["object_type"]),
                int(mark["cell"][0]),
                int(mark["cell"][1]),
            )
            for mark in mark_specs
        )
    )


def _bboxes_overlap(a: Sequence[float], b: Sequence[float]) -> bool:
    """Return whether two axis-aligned bboxes overlap."""

    return not (
        float(a[2]) <= float(b[0])
        or float(b[2]) <= float(a[0])
        or float(a[3]) <= float(b[1])
        or float(b[3]) <= float(a[1])
    )


def test_paper_fold_result_label_contract_matches_winning_option_choice() -> None:
    task = PuzzlesPaperFoldResultLabelTask()
    fold_axes = ("vertical", "horizontal")
    scene_variants = ("fold_strip", "fold_card", "fold_outline")

    for axis_index, fold_axis in enumerate(fold_axes):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 26020 + (axis_index * 20) + scene_index
            out = task.generate(
                seed,
                params={"fold_axis": fold_axis, "scene_variant": scene_variant},
                max_attempts=10,
            )
            trace = out.trace_payload
            execution = trace["execution_trace"]
            render = trace["render_spec"]
            render_map = trace["render_map"]
            solver = execution["solver_trace"]
            annotation_bbox = [float(value) for value in out.annotation_gt.value]

            assert str(out.query_id) == "single"
            assert str(trace["query_spec"]["query_id"]) == "single"
            assert str(execution["query_id"]) == "single"
            assert out.answer_gt.type == "option_letter"
            assert out.annotation_gt.type == "bbox"
            assert sorted(out.prompt_variants.keys()) == [
                "answer_and_annotation",
                "answer_only",
            ]
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(render["scene_variant"]) == str(scene_variant)
            assert int(render["antialias_supersample_scale"]) == 2
            assert out.image.size == (
                int(render["canvas_width"]),
                int(render["canvas_height"]),
            )
            assert int(execution["option_count"]) == 4
            assert int(execution["grid_size"]) == 6
            assert 3 <= int(execution["mark_count"]) <= 5
            assert str(execution["question_format"]) == "fold_result_mcq"
            assert str(execution["view_family"]) == "paper_fold_result_mcq"
            assert trace["projected_annotation"]["bbox"] == annotation_bbox
            assert str(out.answer_gt.value) == str(execution["answer_option_label"])

            expected_bbox = [
                float(value)
                for value in render_map["option_choice_bboxes_px"][
                    str(execution["correct_option_choice_id"])
                ]
            ]
            assert annotation_bbox == expected_bbox
            assert len(render_map["reference_paper_bbox_px"]) == 4
            reference_paper_bbox = [
                float(value) for value in render_map["reference_paper_bbox_px"]
            ]
            arrow_entities = [
                entity
                for entity in trace["scene_ir"]["entities"]
                if str(entity["entity_type"]) == "puzzle_fold_arrow"
            ]
            assert len(arrow_entities) == 2
            assert all(
                not _bboxes_overlap(entity["bbox_px"], reference_paper_bbox)
                for entity in arrow_entities
            )

            option_specs = execution["option_specs"]
            option_count = int(execution["option_count"])
            assert len(option_specs) == option_count
            assert [str(option["option_label"]) for option in option_specs] == [
                chr(ord("A") + index) for index in range(option_count)
            ]
            assert sum(1 for option in option_specs if bool(option["is_correct"])) == 1
            assert len(
                {_mark_signature(option["mark_specs"]) for option in option_specs}
            ) == option_count

            winning_option = next(
                option for option in option_specs if bool(option["is_correct"])
            )
            assert str(winning_option["option_label"]) == str(out.answer_gt.value)
            assert str(winning_option["option_choice_id"]) == str(
                execution["correct_option_choice_id"]
            )
            assert str(solver["correct_option_label"]) == str(out.answer_gt.value)
            assert int(solver["correct_option_index"]) == int(
                execution["correct_option_index"]
            )
            assert _mark_signature(winning_option["mark_specs"]) == _mark_signature(
                execution["folded_result_mark_specs"]
            )
            assert _mark_signature(solver["folded_result_mark_specs"]) == _mark_signature(
                execution["folded_result_mark_specs"]
            )
            assert int(execution["folded_mark_count"]) >= 1
            assert int(execution["kept_mark_count"]) >= 1
            assert int(execution["folded_mark_count"]) + int(
                execution["kept_mark_count"]
            ) == int(execution["mark_count"])

            if str(fold_axis) == "vertical":
                assert str(execution["fold_axis"]) == "vertical"
                assert int(execution["result_grid_cols"]) == 3
                assert int(execution["result_grid_rows"]) == 6
                assert str(execution["fold_direction"]) in {
                    "left_to_right",
                    "right_to_left",
                }
            else:
                assert str(execution["fold_axis"]) == "horizontal"
                assert int(execution["result_grid_cols"]) == 6
                assert int(execution["result_grid_rows"]) == 3
                assert str(execution["fold_direction"]) in {
                    "top_to_bottom",
                    "bottom_to_top",
                }


def test_paper_fold_prompt_examples_match_scalar_annotation() -> None:
    task = PuzzlesPaperFoldResultLabelTask()
    out = task.generate(26090, params={}, max_attempts=10)
    answer_and_annotation = extract_prompt_json_example(
        out.prompt_variants["answer_and_annotation"]
    )
    answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
    assert answer_and_annotation == {
        "annotation": [206, 388, 324, 613],
        "answer": "A",
    }
    assert answer_only == {"answer": "A"}


def test_paper_fold_result_label_task_is_deterministic() -> None:
    task = PuzzlesPaperFoldResultLabelTask()
    params = {"fold_axis": "horizontal", "scene_variant": "fold_card"}
    out_a = task.generate(26140, params=params, max_attempts=10)
    out_b = task.generate(26140, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload[
        "query_spec"
    ]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_paper_fold_answer_letters_and_axes_cover_expected_support() -> None:
    task = PuzzlesPaperFoldResultLabelTask()
    observed_letters = set()
    observed_axes = set()
    for seed in range(26180, 26320):
        out = task.generate(seed, params={}, max_attempts=10)
        observed_letters.add(str(out.answer_gt.value))
        observed_axes.add(str(out.trace_payload["execution_trace"]["fold_axis"]))
    assert observed_letters == {"A", "B", "C", "D"}
    assert observed_axes == {"vertical", "horizontal"}
