"""Behavior tests for puzzle spatial tasks."""

from __future__ import annotations

from trace.tasks.puzzles.spatial.fold_hole_label import PuzzlesSpatialFoldHoleLabelTask
from tests.helpers import extract_prompt_json_example


def _hole_signature(cells: list[list[int]]) -> tuple[tuple[int, int], ...]:
    """Return one hashable signature for a hole pattern."""

    return tuple((int(item[0]), int(item[1])) for item in cells)


def test_puzzle_spatial_fold_hole_label_contract_matches_winning_option_panel() -> None:
    task = PuzzlesSpatialFoldHoleLabelTask()
    task_variants = (
        "single_fold_single_hole",
        "single_fold_two_holes",
        "double_fold_single_hole",
    )
    scene_variants = ("fold_strip", "fold_card", "fold_outline")

    for variant_index, task_variant in enumerate(task_variants):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 26020 + (variant_index * 20) + scene_index
            out = task.generate(
                seed,
                params={"task_variant": task_variant, "scene_variant": scene_variant},
                max_attempts=10,
            )
            trace = out.trace_payload
            execution = trace["execution_trace"]
            render = trace["render_spec"]
            render_map = trace["render_map"]
            solver = execution["solver_trace"]
            evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

            assert str(out.task_variant) == str(task_variant)
            assert out.answer_gt.type == "option_letter"
            assert out.evidence_gt.type == "bbox_set"
            assert len(evidence_bboxes) == 1
            assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(render["scene_variant"]) == str(scene_variant)
            assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
            assert int(execution["option_count"]) == 6
            assert int(execution["grid_size"]) == 6
            assert str(execution["question_format"]) == "fold_hole_mcq"
            assert str(execution["view_family"]) == "fold_hole_unfold_mcq"
            assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
            assert str(out.answer_gt.value) == str(execution["answer_option_label"])
            assert len(render_map["step_panel_bboxes_px"]) == 3

            expected_bbox = [
                float(value)
                for value in render_map["option_panel_bboxes_px"][str(execution["correct_option_panel_id"])]
            ]
            assert evidence_bboxes[0] == expected_bbox

            option_specs = execution["option_specs"]
            assert len(option_specs) == 6
            assert [str(option["option_label"]) for option in option_specs] == ["A", "B", "C", "D", "E", "F"]
            assert sum(1 for option in option_specs if bool(option["is_correct"])) == 1
            assert len({_hole_signature(option["hole_cells"]) for option in option_specs}) == 6

            winning_option = next(option for option in option_specs if bool(option["is_correct"]))
            assert str(winning_option["option_label"]) == str(out.answer_gt.value)
            assert str(winning_option["option_panel_id"]) == str(execution["correct_option_panel_id"])
            assert str(solver["correct_option_label"]) == str(out.answer_gt.value)
            assert int(solver["correct_option_index"]) == int(execution["correct_option_index"])
            assert _hole_signature(winning_option["hole_cells"]) == _hole_signature(execution["unfolded_hole_cells"])
            assert _hole_signature(solver["unfolded_hole_cells"]) == _hole_signature(execution["unfolded_hole_cells"])

            if str(task_variant) == "double_fold_single_hole":
                assert list(execution["fold_axes"]) == ["vertical", "horizontal"]
                assert int(execution["punch_count"]) == 1
                assert len(execution["unfolded_hole_cells"]) == 4
            elif str(task_variant) == "single_fold_two_holes":
                assert len(execution["fold_axes"]) == 1
                assert int(execution["punch_count"]) == 2
                assert len(execution["unfolded_hole_cells"]) == 4
            else:
                assert len(execution["fold_axes"]) == 1
                assert int(execution["punch_count"]) == 1
                assert len(execution["unfolded_hole_cells"]) == 2


def test_puzzle_spatial_prompt_examples_match_selected_variants() -> None:
    task = PuzzlesSpatialFoldHoleLabelTask()
    expected = {
        "single_fold_single_hole": (
            {"evidence": [[333, 616, 481, 804]], "answer": "B"},
            {"answer": "B"},
        ),
        "single_fold_two_holes": (
            {"evidence": [[499, 616, 647, 804]], "answer": "C"},
            {"answer": "C"},
        ),
        "double_fold_single_hole": (
            {"evidence": [[665, 616, 813, 804]], "answer": "D"},
            {"answer": "D"},
        ),
    }
    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=26090):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_puzzle_spatial_fold_hole_label_task_is_deterministic() -> None:
    task = PuzzlesSpatialFoldHoleLabelTask()
    params = {"task_variant": "double_fold_single_hole", "scene_variant": "fold_card"}
    out_a = task.generate(26140, params=params, max_attempts=10)
    out_b = task.generate(26140, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_puzzle_spatial_answer_letters_cover_six_option_range() -> None:
    task = PuzzlesSpatialFoldHoleLabelTask()
    observed_letters = set()
    for seed in range(26180, 26280):
        out = task.generate(seed, params={"task_variant": "single_fold_single_hole"}, max_attempts=10)
        observed_letters.add(str(out.answer_gt.value))
    assert observed_letters == {"A", "B", "C", "D", "E", "F"}
