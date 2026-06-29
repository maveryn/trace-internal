"""Behavior tests for migrated paper fold-cut puzzle tasks."""

from __future__ import annotations

from trace.tasks.puzzles.paper_fold_cut.paper_fold_cut_result_label import (
    PuzzlesPaperFoldCutResultLabelTask,
)
from tests.helpers import extract_prompt_json_example


def _cell_signature(
    cells: list[list[int]] | list[dict[str, object]],
) -> tuple[tuple[int, int], ...]:
    """Return a hashable row-major cell signature."""

    if cells and isinstance(cells[0], dict):
        return tuple(
            sorted(
                (int(item["cell"][0]), int(item["cell"][1])) for item in cells
            )
        )  # type: ignore[index]
    return tuple(sorted((int(cell[0]), int(cell[1])) for cell in cells))  # type: ignore[index]


def _hole_signature(hole_specs: list[dict[str, object]]) -> tuple[tuple[int, int], ...]:
    """Return a hashable signature for unfolded hole specs."""

    return tuple(
        sorted((int(hole["cell"][0]), int(hole["cell"][1])) for hole in hole_specs)
    )


def test_paper_fold_cut_result_label_contract_matches_winning_option_choice() -> None:
    task = PuzzlesPaperFoldCutResultLabelTask()
    cases = (
        ("vertical", 1),
        ("horizontal", 1),
        ("vertical", 2),
        ("horizontal", 2),
    )
    scene_variants = ("fold_strip", "fold_card", "fold_outline")

    for case_index, (fold_axis, fold_count) in enumerate(cases):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 26420 + (case_index * 20) + scene_index
            out = task.generate(
                seed,
                params={
                    "fold_axis": fold_axis,
                    "fold_count": fold_count,
                    "scene_variant": scene_variant,
                },
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
            if int(fold_count) == 1:
                expected_grammar = f"single_{fold_axis}_fold_cut_result"
                assert str(execution["internal_grammar_id"]) == expected_grammar
            else:
                assert str(execution["internal_grammar_id"]) == "double_fold_cut_result"
            assert out.answer_gt.type == "option_letter"
            assert out.annotation_gt.type == "bbox"
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(render["scene_variant"]) == str(scene_variant)
            assert int(render["antialias_supersample_scale"]) == 2
            assert str(render["cut_hole_style"]["shape"]) in {
                "circle",
                "square",
                "diamond",
                "rounded_square",
            }
            assert str(execution["cut_hole_shape"]) == str(
                render["cut_hole_style"]["shape"]
            )
            assert out.image.size == (
                int(render["canvas_width"]),
                int(render["canvas_height"]),
            )
            assert int(execution["option_count"]) == 4
            assert int(execution["grid_size"]) == 6
            assert 1 <= int(execution["cut_count"]) <= 2
            assert str(execution["question_format"]) == "fold_cut_unfolded_result_mcq"
            assert str(execution["view_family"]) == "paper_fold_cut_result_mcq"
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
            assert len(render_map["folded_packet_bbox_px"]) == 4
            assert [str(item) for item in execution["supporting_option_choice_ids"]] == [
                str(execution["correct_option_choice_id"])
            ]

            option_specs = execution["option_specs"]
            option_count = int(execution["option_count"])
            assert len(option_specs) == option_count
            assert [str(option["option_label"]) for option in option_specs] == [
                chr(ord("A") + index) for index in range(option_count)
            ]
            assert sum(1 for option in option_specs if bool(option["is_correct"])) == 1
            assert len({_cell_signature(option["cells"]) for option in option_specs}) == option_count

            winning_option = next(
                option for option in option_specs if bool(option["is_correct"])
            )
            assert str(winning_option["option_label"]) == str(out.answer_gt.value)
            assert str(winning_option["option_choice_id"]) == str(
                execution["correct_option_choice_id"]
            )
            assert _cell_signature(winning_option["cells"]) == _cell_signature(
                execution["unfolded_hole_cells"]
            )
            assert _hole_signature(winning_option["hole_specs"]) == _cell_signature(
                execution["unfolded_hole_cells"]
            )
            assert str(solver["correct_option_label"]) == str(out.answer_gt.value)
            assert int(solver["correct_option_index"]) == int(
                execution["correct_option_index"]
            )
            assert _cell_signature(solver["unfolded_hole_cells"]) == _cell_signature(
                execution["unfolded_hole_cells"]
            )

            hole_entities = [
                entity
                for entity in trace["scene_ir"]["entities"]
                if str(entity["entity_type"])
                in {"puzzle_fold_cut_hole", "puzzle_fold_cut_unfolded_hole"}
            ]
            assert hole_entities
            assert {str(entity["attrs"]["cut_hole_shape"]) for entity in hole_entities} == {
                str(execution["cut_hole_shape"])
            }

            if int(fold_count) == 1 and str(fold_axis) == "vertical":
                assert int(execution["fold_count"]) == 1
                assert str(execution["fold_sequence"][0]["fold_axis"]) == "vertical"
                assert int(execution["folded_grid_cols"]) == 3
                assert int(execution["folded_grid_rows"]) == 6
            elif int(fold_count) == 1 and str(fold_axis) == "horizontal":
                assert int(execution["fold_count"]) == 1
                assert str(execution["fold_sequence"][0]["fold_axis"]) == "horizontal"
                assert int(execution["folded_grid_cols"]) == 6
                assert int(execution["folded_grid_rows"]) == 3
            else:
                assert int(execution["fold_count"]) == 2
                assert {
                    str(step["fold_axis"]) for step in execution["fold_sequence"]
                } == {"vertical", "horizontal"}
                assert int(execution["folded_grid_cols"]) == 3
                assert int(execution["folded_grid_rows"]) == 3


def test_paper_fold_cut_sampling_covers_letters_and_axes() -> None:
    task = PuzzlesPaperFoldCutResultLabelTask()
    observed_letters = set()
    observed_axes = set()
    observed_fold_counts = set()
    for sampling_index in range(120):
        out = task.generate(
            26320 + sampling_index,
            params={},
            max_attempts=10,
        )
        params = out.trace_payload["query_spec"]["params"]
        observed_letters.add(str(out.answer_gt.value))
        observed_axes.add(str(params["fold_axis"]))
        observed_fold_counts.add(int(params["fold_count"]))

    assert observed_letters <= {"A", "B", "C", "D"}
    assert len(observed_letters) >= 3
    assert observed_axes == {"vertical", "horizontal"}
    assert observed_fold_counts == {1, 2}


def test_paper_fold_cut_prompt_examples_match_scalar_annotation() -> None:
    task = PuzzlesPaperFoldCutResultLabelTask()
    out = task.generate(26520, params={}, max_attempts=10)
    answer_and_annotation = extract_prompt_json_example(
        out.prompt_variants["answer_and_annotation"]
    )
    answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
    assert answer_and_annotation == {
        "annotation": [134, 420, 312, 598],
        "answer": "A",
    }
    assert answer_only == {"answer": "A"}


def test_paper_fold_cut_result_label_task_is_deterministic() -> None:
    task = PuzzlesPaperFoldCutResultLabelTask()
    params = {"fold_count": 2, "scene_variant": "fold_card"}
    out_a = task.generate(26580, params=params, max_attempts=10)
    out_b = task.generate(26580, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload[
        "query_spec"
    ]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
