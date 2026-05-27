"""Behavior tests for puzzle spatial tasks."""

from __future__ import annotations

from collections import Counter
from typing import Sequence

from trace.tasks.puzzles.shared.assembly_common import can_tile_polyomino_with_pieces
from trace.tasks.puzzles.shared.shape_complement_common import shape_complement_d4_signature
from trace.tasks.puzzles.shared.spatial_blocks_common import total_cubes_from_height_rows
from trace.tasks.puzzles.spatial.polyomino_arrangement_label import (
    PuzzlesSpatialPolyominoMissingRegionPieceLabelTask,
)
from trace.tasks.puzzles.spatial.transform_result_label import (
    PuzzlesSpatialOverlayResultLabelTask,
    PuzzlesSpatialPaperFoldCutResultLabelTask,
    PuzzlesSpatialPaperFoldResultLabelTask,
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


def _bbox_center_distance(a: Sequence[float], b: Sequence[float]) -> float:
    """Return the distance between two bbox centers."""

    ax = 0.5 * (float(a[0]) + float(a[2]))
    ay = 0.5 * (float(a[1]) + float(a[3]))
    bx = 0.5 * (float(b[0]) + float(b[2]))
    by = 0.5 * (float(b[1]) + float(b[3]))
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5


def _cell_signature(cells: list[list[int]] | list[dict[str, object]]) -> tuple[tuple[int, int], ...]:
    """Return a hashable row-major cell signature."""

    if cells and isinstance(cells[0], dict):
        return tuple(sorted((int(item["cell"][0]), int(item["cell"][1])) for item in cells))  # type: ignore[index]
    return tuple(sorted((int(cell[0]), int(cell[1])) for cell in cells))  # type: ignore[index]


def _hole_signature(hole_specs: list[dict[str, object]]) -> tuple[tuple[int, int], ...]:
    """Return a hashable signature for unfolded hole specs."""

    return tuple(sorted((int(hole["cell"][0]), int(hole["cell"][1])) for hole in hole_specs))


def test_puzzle_spatial_overlay_result_label_contract_matches_winning_option_choice() -> None:
    task = PuzzlesSpatialOverlayResultLabelTask()
    scene_variants = ("overlay_strip", "overlay_card", "overlay_outline")

    for scene_index, scene_variant in enumerate(scene_variants):
        seed = 25920 + scene_index
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

        assert str(out.query_variant) == "default"
        assert str(out.query_id) == "overlay_result"
        assert str(trace["query_spec"]["query_variant"]) == "default"
        assert str(trace["query_spec"]["query_id"]) == "overlay_result"
        assert str(execution["query_variant"]) == "default"
        assert str(execution["query_id"]) == "overlay_result"
        assert str(execution["internal_query_variant"]) == "overlay_union_same_grid"
        assert out.answer_gt.type == "option_letter"
        assert out.evidence_gt.type == "bbox_set"
        assert len(evidence_bboxes) == 1
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert str(render["mark_style"]["shape"]) in {"circle", "square", "diamond", "rounded_square"}
        assert str(execution["mark_shape"]) == str(render["mark_style"]["shape"])
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert str(execution["question_format"]) == "overlay_union_mcq"
        assert str(execution["view_family"]) == "transparent_sheet_overlay_mcq"
        assert 4 <= int(execution["grid_size"]) <= 5
        assert 5 <= int(execution["option_count"]) <= 6
        assert 2 <= int(execution["left_mark_count"]) <= 5
        assert 2 <= int(execution["right_mark_count"]) <= 5
        assert 1 <= int(execution["overlap_count"]) <= 2
        assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
        assert str(out.answer_gt.value) == str(execution["answer_option_label"])

        expected_bbox = [
            float(value)
            for value in render_map["option_choice_bboxes_px"][str(execution["correct_option_choice_id"])]
        ]
        assert evidence_bboxes[0] == expected_bbox
        assert [str(item) for item in execution["supporting_option_choice_ids"]] == [
            str(execution["correct_option_choice_id"])
        ]

        left_signature = _cell_signature(execution["left_cells"])
        right_signature = _cell_signature(execution["right_cells"])
        overlap_signature = _cell_signature(execution["overlap_cells"])
        union_signature = _cell_signature(execution["union_cells"])
        assert set(overlap_signature) <= set(left_signature)
        assert set(overlap_signature) <= set(right_signature)
        assert set(left_signature) | set(right_signature) == set(union_signature)
        assert set(left_signature) & set(right_signature) == set(overlap_signature)

        option_specs = execution["option_specs"]
        assert sum(1 for option in option_specs if bool(option["is_correct"])) == 1
        assert len({_cell_signature(option["cells"]) for option in option_specs}) == int(execution["option_count"])
        source_bboxes = [
            [float(value) for value in render_map["source_sheet_bboxes_px"][sheet_id]]
            for sheet_id in ("source_sheet_left", "source_sheet_right")
        ]
        option_bbox = expected_bbox
        option_width = option_bbox[2] - option_bbox[0]
        option_height = option_bbox[3] - option_bbox[1]
        assert all((bbox[2] - bbox[0]) == option_width for bbox in source_bboxes)
        assert all((bbox[3] - bbox[1]) == option_height for bbox in source_bboxes)
        divider_entities = [
            entity for entity in trace["scene_ir"]["entities"] if str(entity["entity_type"]) == "puzzle_overlay_divider"
        ]
        assert len(divider_entities) == 1
        mark_entities = [
            entity for entity in trace["scene_ir"]["entities"] if str(entity["entity_type"]).endswith("overlay_mark")
        ]
        assert mark_entities
        assert {str(entity["attrs"]["mark_shape"]) for entity in mark_entities} == {str(execution["mark_shape"])}

        winning_option = next(option for option in option_specs if bool(option["is_correct"]))
        assert str(winning_option["option_label"]) == str(out.answer_gt.value)
        assert str(winning_option["option_choice_id"]) == str(execution["correct_option_choice_id"])
        assert _cell_signature(winning_option["cells"]) == union_signature


def test_puzzle_spatial_overlay_prompt_examples_match_selected_variant() -> None:
    task = PuzzlesSpatialOverlayResultLabelTask()
    out = task.generate(25990, params={}, max_attempts=10)
    answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
    assert answer_and_evidence == {"evidence": [[521, 384, 679, 542]], "answer": "B"}
    assert answer_only == {"answer": "B"}


def test_puzzle_spatial_overlay_result_label_task_is_deterministic() -> None:
    task = PuzzlesSpatialOverlayResultLabelTask()
    params = {"scene_variant": "overlay_card"}
    out_a = task.generate(26010, params=params, max_attempts=10)
    out_b = task.generate(26010, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()

def test_puzzle_spatial_overlay_balanced_sampling_keeps_answer_letters_under_cap() -> None:
    task = PuzzlesSpatialOverlayResultLabelTask()
    observed_letters = Counter()
    for sampling_index in range(100):
        out = task.generate(
            26020 + sampling_index,
            params={},
            max_attempts=10,
        )
        observed_letters[str(out.answer_gt.value)] += 1

    assert set(observed_letters).issubset({"A", "B", "C", "D", "E", "F"})
    assert len(observed_letters) >= 5
    assert max(observed_letters.values()) <= 25


def test_puzzle_spatial_fold_result_label_contract_matches_winning_option_choice() -> None:
    task = PuzzlesSpatialPaperFoldResultLabelTask()
    fold_axes = ("vertical", "horizontal")
    scene_variants = ("fold_strip", "fold_card", "fold_outline")

    for variant_index, fold_axis in enumerate(fold_axes):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 26020 + (variant_index * 20) + scene_index
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
            evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

            assert str(out.query_variant) == "default"
            assert str(out.query_id) == "paper_fold_result"
            assert str(trace["query_spec"]["query_variant"]) == "default"
            assert str(trace["query_spec"]["query_id"]) == "paper_fold_result"
            assert str(execution["query_variant"]) == "default"
            assert str(execution["query_id"]) == "paper_fold_result"
            assert str(execution["internal_query_variant"]) == f"{fold_axis}_fold_result"
            assert out.answer_gt.type == "option_letter"
            assert out.evidence_gt.type == "bbox_set"
            assert len(evidence_bboxes) == 1
            assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(render["scene_variant"]) == str(scene_variant)
            assert int(render["antialias_supersample_scale"]) == 2
            assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
            assert 5 <= int(execution["option_count"]) <= 6
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
            option_count = int(execution["option_count"])
            assert len(option_specs) == int(option_count)
            assert [str(option["option_label"]) for option in option_specs] == [
                chr(ord("A") + index) for index in range(int(option_count))
            ]
            assert sum(1 for option in option_specs if bool(option["is_correct"])) == 1
            assert len({_mark_signature(option["mark_specs"]) for option in option_specs}) == int(option_count)

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

            if str(fold_axis) == "vertical":
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
    task = PuzzlesSpatialPaperFoldResultLabelTask()
    out = task.generate(26090, params={}, max_attempts=10)
    answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
    assert answer_and_evidence == {"evidence": [[206, 388, 324, 613]], "answer": "A"}
    assert answer_only == {"answer": "A"}


def test_puzzle_spatial_fold_result_label_task_is_deterministic() -> None:
    task = PuzzlesSpatialPaperFoldResultLabelTask()
    params = {"fold_axis": "horizontal", "scene_variant": "fold_card"}
    out_a = task.generate(26140, params=params, max_attempts=10)
    out_b = task.generate(26140, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_puzzle_spatial_answer_letters_cover_six_option_range() -> None:
    task = PuzzlesSpatialPaperFoldResultLabelTask()
    observed_letters = set()
    for seed in range(26180, 26280):
        out = task.generate(seed, params={"fold_axis": "vertical"}, max_attempts=10)
        observed_letters.add(str(out.answer_gt.value))
    assert observed_letters == {"A", "B", "C", "D", "E", "F"}


def test_puzzle_spatial_fold_result_balanced_sampling_covers_letters_per_variant() -> None:
    task_cases = (
        (PuzzlesSpatialOverlayResultLabelTask(), "overlay_result"),
        (PuzzlesSpatialPaperFoldResultLabelTask(), "paper_fold_result"),
        (PuzzlesSpatialPaperFoldCutResultLabelTask(), "paper_fold_cut_result"),
    )
    observed_by_query = {query_id: set() for _, query_id in task_cases}
    observed_axes_by_query = {"paper_fold_result": set(), "paper_fold_cut_result": set()}
    for task, query_id in task_cases:
        for sampling_index in range(80):
            out = task.generate(
                26320 + sampling_index,
                params={},
                max_attempts=10,
            )
            observed_by_query[str(query_id)].add(str(out.answer_gt.value))
            fold_axis = out.trace_payload["query_spec"]["params"].get("fold_axis")
            if fold_axis is not None:
                observed_axes_by_query[str(query_id)].add(str(fold_axis))

    for observed_letters in observed_by_query.values():
        assert observed_letters <= {"A", "B", "C", "D", "E", "F"}
        assert len(observed_letters) >= 3
    assert observed_axes_by_query == {
        "paper_fold_result": {"vertical", "horizontal"},
        "paper_fold_cut_result": {"vertical", "horizontal"},
    }


def test_puzzle_spatial_fold_result_label_fold_cut_variants_match_winning_option_choice() -> None:
    task = PuzzlesSpatialPaperFoldCutResultLabelTask()
    query_variants = (
        ("paper_fold_cut_result", "vertical", 1),
        ("paper_fold_cut_result", "horizontal", 1),
        ("paper_fold_cut_result", None, 2),
    )
    scene_variants = ("fold_strip", "fold_card", "fold_outline")

    for variant_index, (query_variant, fold_axis, fold_count) in enumerate(query_variants):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 26420 + (variant_index * 20) + scene_index
            params = {"scene_variant": scene_variant}
            params["fold_count"] = fold_count
            if fold_axis is not None:
                params["fold_axis"] = fold_axis
            out = task.generate(
                seed,
                params=params,
                max_attempts=10,
            )
            trace = out.trace_payload
            execution = trace["execution_trace"]
            render = trace["render_spec"]
            render_map = trace["render_map"]
            solver = execution["solver_trace"]
            evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

            assert str(out.query_variant) == "default"
            assert str(out.query_id) == "paper_fold_cut_result"
            assert str(trace["query_spec"]["query_variant"]) == "default"
            assert str(trace["query_spec"]["query_id"]) == "paper_fold_cut_result"
            assert str(execution["query_variant"]) == "default"
            assert str(execution["query_id"]) == "paper_fold_cut_result"
            if fold_axis is not None:
                assert str(execution["internal_query_variant"]) == f"single_{fold_axis}_fold_cut_result"
            else:
                assert str(execution["internal_query_variant"]) == "double_fold_cut_result"
            assert out.answer_gt.type == "option_letter"
            assert out.evidence_gt.type == "bbox_set"
            assert len(evidence_bboxes) == 1
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(render["scene_variant"]) == str(scene_variant)
            assert int(render["antialias_supersample_scale"]) == 2
            assert str(render["cut_hole_style"]["shape"]) in {"circle", "square", "diamond", "rounded_square"}
            assert str(execution["cut_hole_shape"]) == str(render["cut_hole_style"]["shape"])
            assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
            assert 5 <= int(execution["option_count"]) <= 6
            assert int(execution["grid_size"]) == 6
            assert 1 <= int(execution["cut_count"]) <= 2
            assert str(execution["question_format"]) == "fold_cut_unfolded_result_mcq"
            assert str(execution["view_family"]) == "paper_fold_cut_result_mcq"
            assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
            assert str(out.answer_gt.value) == str(execution["answer_option_label"])

            expected_bbox = [
                float(value)
                for value in render_map["option_choice_bboxes_px"][str(execution["correct_option_choice_id"])]
            ]
            assert evidence_bboxes[0] == expected_bbox
            assert len(render_map["reference_paper_bbox_px"]) == 4
            assert len(render_map["folded_packet_bbox_px"]) == 4
            assert [str(item) for item in execution["supporting_option_choice_ids"]] == [
                str(execution["correct_option_choice_id"])
            ]

            option_specs = execution["option_specs"]
            option_count = int(execution["option_count"])
            assert len(option_specs) == int(option_count)
            assert [str(option["option_label"]) for option in option_specs] == [
                chr(ord("A") + index) for index in range(int(option_count))
            ]
            assert sum(1 for option in option_specs if bool(option["is_correct"])) == 1
            assert len({_cell_signature(option["cells"]) for option in option_specs}) == int(option_count)

            winning_option = next(option for option in option_specs if bool(option["is_correct"]))
            assert str(winning_option["option_label"]) == str(out.answer_gt.value)
            assert str(winning_option["option_choice_id"]) == str(execution["correct_option_choice_id"])
            assert _cell_signature(winning_option["cells"]) == _cell_signature(execution["unfolded_hole_cells"])
            assert _hole_signature(winning_option["hole_specs"]) == _cell_signature(execution["unfolded_hole_cells"])
            assert str(solver["correct_option_label"]) == str(out.answer_gt.value)
            assert int(solver["correct_option_index"]) == int(execution["correct_option_index"])
            assert _cell_signature(solver["unfolded_hole_cells"]) == _cell_signature(execution["unfolded_hole_cells"])

            hole_entities = [
                entity
                for entity in trace["scene_ir"]["entities"]
                if str(entity["entity_type"]) in {"puzzle_fold_cut_hole", "puzzle_fold_cut_unfolded_hole"}
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
                assert {str(step["fold_axis"]) for step in execution["fold_sequence"]} == {"vertical", "horizontal"}
                assert int(execution["folded_grid_cols"]) == 3
                assert int(execution["folded_grid_rows"]) == 3


def test_puzzle_spatial_fold_cut_prompt_examples_match_selected_variants() -> None:
    task = PuzzlesSpatialPaperFoldCutResultLabelTask()
    out = task.generate(26520, params={}, max_attempts=10)
    answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
    assert answer_and_evidence == {"evidence": [[134, 420, 312, 598]], "answer": "A"}
    assert answer_only == {"answer": "A"}


def test_puzzle_spatial_fold_result_label_fold_cut_variant_is_deterministic() -> None:
    task = PuzzlesSpatialPaperFoldCutResultLabelTask()
    params = {"fold_count": 2, "scene_variant": "fold_card"}
    out_a = task.generate(26580, params=params, max_attempts=10)
    out_b = task.generate(26580, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_total_cubes_helper_matches_height_grid_sum() -> None:
    assert int(total_cubes_from_height_rows([[2, 2], [2, 2]])) == 8
    assert int(total_cubes_from_height_rows([[3, 1], [2, 4]])) == 10


def test_assembly_tiling_helper_accepts_rotation_only_match() -> None:
    target = ((0, 0), (1, 0), (0, 1), (1, 1))
    pieces = [
        ((0, 0), (1, 0), (0, 1)),
        ((0, 0),),
    ]
    assert can_tile_polyomino_with_pieces(target, pieces)


def test_puzzle_spatial_polyomino_arrangement_variants_have_option_evidence() -> None:
    cases = (
        (
            PuzzlesSpatialPolyominoMissingRegionPieceLabelTask(),
            "marked_region_piece_label",
            2,
            {"query_variant": "marked_region_piece_label"},
        ),
        (
            PuzzlesSpatialPolyominoMissingRegionPieceLabelTask(),
            "rectangle_complement_piece",
            2,
            {"query_variant": "rectangle_complement_piece"},
        ),
    )

    for index, (task, query_variant, evidence_count, extra_params) in enumerate(cases):
        out = task.generate(
            27150 + index,
            params={"scene_variant": "polyomino_card", **extra_params},
            max_attempts=20,
        )
        execution = out.trace_payload["execution_trace"]
        item_bboxes = out.trace_payload["render_map"]["item_bboxes_px"]

        assert str(out.query_variant) == "default"
        assert str(out.query_id) == str(query_variant)
        assert str(execution["query_variant"]) == "default"
        assert str(execution["query_id"]) == str(query_variant)
        assert str(execution["internal_query_variant"]) == str(query_variant)
        assert out.answer_gt.type == "option_letter"
        assert out.evidence_gt.type == "bbox_set"
        assert len(out.evidence_gt.value) == int(evidence_count)
        assert str(execution["correct_option_panel_id"]) in item_bboxes
        assert str(out.answer_gt.value) == str(execution["answer_option_label"])
        assert out.trace_payload["projected_evidence"]["bbox_set"] == out.evidence_gt.value


def test_puzzle_spatial_polyomino_rectangle_complement_contract_matches_winning_option_panel() -> None:
    task = PuzzlesSpatialPolyominoMissingRegionPieceLabelTask()
    matching_policies = (
        "exact_orientation",
        "rotation_reflection_allowed",
    )
    scene_variants = ("polyomino_strip", "polyomino_card", "polyomino_outline")

    for policy_index, matching_policy in enumerate(matching_policies):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 27220 + (policy_index * 20) + scene_index
            out = task.generate(
                seed,
                params={
                    "query_variant": "rectangle_complement_piece",
                    "matching_policy": matching_policy,
                    "scene_variant": scene_variant,
                },
                max_attempts=10,
            )
            trace = out.trace_payload
            execution = trace["execution_trace"]
            payload = execution["variant_payload"]
            render = trace["render_spec"]
            render_map = trace["render_map"]
            evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

            assert str(out.query_variant) == "default"
            assert str(out.query_id) == "rectangle_complement_piece"
            assert str(trace["query_spec"]["query_variant"]) == "default"
            assert str(trace["query_spec"]["query_id"]) == "rectangle_complement_piece"
            assert str(execution["query_variant"]) == "default"
            assert str(execution["query_id"]) == "rectangle_complement_piece"
            assert str(execution["internal_query_variant"]) == "rectangle_complement_piece"
            assert out.answer_gt.type == "option_letter"
            assert out.evidence_gt.type == "bbox_set"
            assert len(evidence_bboxes) == 2
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(render["scene_variant"]) == str(scene_variant)
            assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
            assert 5 <= int(payload["option_count"]) <= 6
            assert 3 <= int(payload["cutout_cell_count"]) <= 7
            assert str(execution["matching_policy"]) == str(matching_policy)
            assert str(payload["matching_policy_parameter"]) == str(matching_policy)
            assert str(execution["question_format"]) == "polyomino_rectangle_complement_piece"
            assert str(execution["view_family"]) == "polyomino_rectangle_complement_piece_option_puzzle"
            assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
            assert str(out.answer_gt.value) == str(execution["answer_option_label"])

            expected_bbox = [
                float(value)
                for value in render_map["item_bboxes_px"][str(execution["correct_option_panel_id"])]
            ]
            marked_bbox = [float(value) for value in render_map["item_bboxes_px"]["marked_region"]]
            assert evidence_bboxes[0] == expected_bbox
            assert evidence_bboxes[1] == marked_bbox
            assert [str(item) for item in execution["evidence_item_ids"]] == [
                str(execution["correct_option_panel_id"]),
                "marked_region",
            ]

            option_specs = execution["option_specs"]
            expected_labels = [chr(ord("A") + index) for index in range(int(payload["option_count"]))]
            assert [str(option["option_label"]) for option in option_specs] == expected_labels
            assert sum(1 for option in option_specs if bool(option["is_correct"])) == 1
            assert len({_cell_signature(option["cells"]) for option in option_specs}) == int(payload["option_count"])

            winning_option = next(option for option in option_specs if bool(option["is_correct"]))
            assert str(winning_option["option_label"]) == str(out.answer_gt.value)
            assert str(winning_option["option_panel_id"]) == str(execution["correct_option_panel_id"])

            target_cells = set(_cell_signature(payload["target_cells"]))
            remaining_cells = set(_cell_signature(payload["remaining_cells"]))
            cutout_cells = set(_cell_signature(payload["cutout_cells_in_target"]))
            assert remaining_cells.isdisjoint(cutout_cells)
            assert target_cells == remaining_cells | cutout_cells
            width, height = [int(value) for value in payload["target_bbox_dims"]]
            assert int(payload["target_cell_count"]) == width * height
            assert str(payload["target_generation_kind"]) == "rectangle"
            assert sum(1 for option in option_specs if bool(option["matches_under_policy"])) == 1
            if str(matching_policy) == "exact_orientation":
                assert str(payload["correct_option_transform"]) == "identity"
                assert _cell_signature(winning_option["cells"]) == _cell_signature(payload["cutout_cells"])
            else:
                winning_signature = shape_complement_d4_signature(
                    tuple((int(cell[0]), int(cell[1])) for cell in winning_option["cells"])
                )
                cutout_signature = shape_complement_d4_signature(
                    tuple((int(cell[0]), int(cell[1])) for cell in payload["cutout_cells"])
                )
                assert winning_signature == cutout_signature
                assert sum(
                    1
                    for option in option_specs
                    if shape_complement_d4_signature(
                        tuple((int(cell[0]), int(cell[1])) for cell in option["cells"])
                    )
                    == cutout_signature
                ) == 1


def test_puzzle_spatial_polyomino_rectangle_complement_prompt_examples_match_selected_policy() -> None:
    task = PuzzlesSpatialPolyominoMissingRegionPieceLabelTask()
    out = task.generate(
        27320,
        params={"query_variant": "rectangle_complement_piece", "matching_policy": "rotation_reflection_allowed"},
        max_attempts=10,
    )
    answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
    assert answer_and_evidence == {"evidence": [[416, 604, 592, 808], [580, 218, 618, 256]], "answer": "C"}
    assert answer_only == {"answer": "C"}
    assert "Rotation and reflection are allowed" in out.prompt


def test_puzzle_spatial_polyomino_rectangle_complement_balanced_sampling_covers_letters_per_policy() -> None:
    task = PuzzlesSpatialPolyominoMissingRegionPieceLabelTask()
    observed_by_policy = {
        "exact_orientation": set(),
        "rotation_reflection_allowed": set(),
    }
    for sampling_index in range(200):
        out = task.generate(
            27380 + sampling_index,
            params={"query_variant": "rectangle_complement_piece"},
            max_attempts=10,
        )
        policy = str(out.trace_payload["execution_trace"]["matching_policy"])
        observed_by_policy[policy].add(str(out.answer_gt.value))

    assert observed_by_policy["exact_orientation"] >= {"A", "B", "C", "D", "E"}
    assert observed_by_policy["rotation_reflection_allowed"] >= {"A", "B", "C", "D", "E"}


def test_puzzle_spatial_polyomino_rectangle_complement_task_is_deterministic() -> None:
    task = PuzzlesSpatialPolyominoMissingRegionPieceLabelTask()
    params = {
        "query_variant": "rectangle_complement_piece",
        "matching_policy": "rotation_reflection_allowed",
        "scene_variant": "polyomino_card",
    }
    out_a = task.generate(27480, params=params, max_attempts=10)
    out_b = task.generate(27480, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
