"""Behavior tests for puzzle spatial tasks."""

from __future__ import annotations

from typing import Sequence

from trace.tasks.puzzles.shared.spatial_blocks_common import total_cubes_from_height_rows
from trace.tasks.puzzles.spatial.cube_removal_count import PuzzlesSpatialCubeRemovalCountTask
from trace.tasks.puzzles.spatial.fold_result_label import PuzzlesSpatialFoldResultLabelTask
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


def test_puzzle_spatial_fold_result_label_contract_matches_winning_option_choice() -> None:
    task = PuzzlesSpatialFoldResultLabelTask()
    task_variants = (
        "vertical_fold_result",
        "horizontal_fold_result",
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
            assert int(render["antialias_supersample_scale"]) == 2
            assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
            assert int(execution["option_count"]) == 6
            assert int(execution["grid_size"]) == 6
            assert 3 <= int(execution["mark_count"]) <= 5
            assert str(execution["question_format"]) == "fold_result_mcq"
            assert str(execution["view_family"]) == "paper_fold_result_mcq"
            assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
            assert str(out.answer_gt.value) == str(execution["answer_option_label"])

            expected_bbox = [
                float(value)
                for value in render_map["option_choice_bboxes_px"][str(execution["correct_option_choice_id"])]
            ]
            assert evidence_bboxes[0] == expected_bbox
            assert len(render_map["reference_paper_bbox_px"]) == 4
            reference_paper_bbox = [float(value) for value in render_map["reference_paper_bbox_px"]]
            arrow_entities = [
                entity for entity in trace["scene_ir"]["entities"] if str(entity["entity_type"]) == "puzzle_fold_arrow"
            ]
            assert len(arrow_entities) == 2
            assert all(not _bboxes_overlap(entity["bbox_px"], reference_paper_bbox) for entity in arrow_entities)

            option_specs = execution["option_specs"]
            assert len(option_specs) == 6
            assert [str(option["option_label"]) for option in option_specs] == ["A", "B", "C", "D", "E", "F"]
            assert sum(1 for option in option_specs if bool(option["is_correct"])) == 1
            assert len({_mark_signature(option["mark_specs"]) for option in option_specs}) == 6

            winning_option = next(option for option in option_specs if bool(option["is_correct"]))
            assert str(winning_option["option_label"]) == str(out.answer_gt.value)
            assert str(winning_option["option_choice_id"]) == str(execution["correct_option_choice_id"])
            assert str(solver["correct_option_label"]) == str(out.answer_gt.value)
            assert int(solver["correct_option_index"]) == int(execution["correct_option_index"])
            assert _mark_signature(winning_option["mark_specs"]) == _mark_signature(execution["folded_result_mark_specs"])
            assert _mark_signature(solver["folded_result_mark_specs"]) == _mark_signature(execution["folded_result_mark_specs"])
            assert int(execution["folded_mark_count"]) >= 1
            assert int(execution["kept_mark_count"]) >= 1
            assert int(execution["folded_mark_count"]) + int(execution["kept_mark_count"]) == int(execution["mark_count"])

            if str(task_variant) == "vertical_fold_result":
                assert str(execution["fold_axis"]) == "vertical"
                assert int(execution["result_grid_cols"]) == 3
                assert int(execution["result_grid_rows"]) == 6
                assert str(execution["fold_direction"]) in {"left_to_right", "right_to_left"}
            else:
                assert str(execution["fold_axis"]) == "horizontal"
                assert int(execution["result_grid_cols"]) == 6
                assert int(execution["result_grid_rows"]) == 3
                assert str(execution["fold_direction"]) in {"top_to_bottom", "bottom_to_top"}


def test_puzzle_spatial_prompt_examples_match_selected_variants() -> None:
    task = PuzzlesSpatialFoldResultLabelTask()
    expected = {
        "vertical_fold_result": (
            {"evidence": [[206, 388, 324, 613]], "answer": "A"},
            {"answer": "A"},
        ),
        "horizontal_fold_result": (
            {"evidence": [[482, 388, 718, 500]], "answer": "B"},
            {"answer": "B"},
        ),
    }
    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=26090):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_puzzle_spatial_fold_result_label_task_is_deterministic() -> None:
    task = PuzzlesSpatialFoldResultLabelTask()
    params = {"task_variant": "horizontal_fold_result", "scene_variant": "fold_card"}
    out_a = task.generate(26140, params=params, max_attempts=10)
    out_b = task.generate(26140, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_puzzle_spatial_answer_letters_cover_six_option_range() -> None:
    task = PuzzlesSpatialFoldResultLabelTask()
    observed_letters = set()
    for seed in range(26180, 26280):
        out = task.generate(seed, params={"task_variant": "vertical_fold_result"}, max_attempts=10)
        observed_letters.add(str(out.answer_gt.value))
    assert observed_letters == {"A", "B", "C", "D", "E", "F"}


def test_total_cubes_helper_matches_height_grid_sum() -> None:
    assert int(total_cubes_from_height_rows([[2, 2], [2, 2]])) == 8
    assert int(total_cubes_from_height_rows([[3, 1], [2, 4]])) == 10


def test_puzzle_spatial_cube_removal_count_contract_matches_structure_bboxes() -> None:
    task = PuzzlesSpatialCubeRemovalCountTask()
    scene_variants = ("stack_strip", "stack_card", "stack_outline")

    for scene_index, scene_variant in enumerate(scene_variants):
        seed = 27120 + scene_index
        out = task.generate(
            seed,
            params={"scene_variant": scene_variant},
            max_attempts=10,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]
        render_map = trace["render_map"]
        evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

        assert str(out.task_variant) == "cube_removal_count"
        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "bbox_set"
        assert len(evidence_bboxes) == 2
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert str(execution["question_format"]) == "cube_removal_count"
        assert str(execution["view_family"]) == "isometric_block_comparison"
        assert int(out.answer_gt.value) == int(execution["removal_count"])
        assert 1 <= int(execution["removal_count"]) <= 5
        assert int(execution["original_total_cubes"]) > int(execution["remaining_total_cubes"])
        assert int(execution["original_total_cubes"]) - int(execution["remaining_total_cubes"]) == int(out.answer_gt.value)
        assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
        assert [str(item) for item in execution["supporting_structure_ids"]] == [
            str(execution["original_structure_bbox_id"]),
            str(execution["remaining_structure_bbox_id"]),
        ]

        expected_original_bbox = [float(value) for value in render_map["structure_bboxes_px"][str(execution["original_structure_bbox_id"])]]
        expected_remaining_bbox = [float(value) for value in render_map["structure_bboxes_px"][str(execution["remaining_structure_bbox_id"])]]
        assert evidence_bboxes[0] == expected_original_bbox
        assert evidence_bboxes[1] == expected_remaining_bbox
        assert evidence_bboxes[0] == [float(value) for value in render_map["original_structure_bbox_px"]]
        assert evidence_bboxes[1] == [float(value) for value in render_map["remaining_structure_bbox_px"]]

        original_cube_records = execution["original_cube_records"]
        remaining_cube_records = execution["remaining_cube_records"]
        removed_cube_records = execution["removed_cube_records"]
        assert len(original_cube_records) == int(execution["original_total_cubes"])
        assert len(remaining_cube_records) == int(execution["remaining_total_cubes"])
        assert len(removed_cube_records) == int(execution["removal_count"])


def test_puzzle_spatial_cube_removal_prompt_examples_match_selected_variant() -> None:
    task = PuzzlesSpatialCubeRemovalCountTask()
    out = task.generate(27190, params={}, max_attempts=10)
    answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
    assert answer_and_evidence == {"evidence": [[132, 175, 459, 656], [750, 207, 1080, 656]], "answer": 4}
    assert answer_only == {"answer": 4}


def test_puzzle_spatial_cube_removal_count_task_is_deterministic() -> None:
    task = PuzzlesSpatialCubeRemovalCountTask()
    params = {"scene_variant": "stack_card"}
    out_a = task.generate(27240, params=params, max_attempts=10)
    out_b = task.generate(27240, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
