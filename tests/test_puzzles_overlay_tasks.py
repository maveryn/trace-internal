"""Behavior tests for scene-package overlay puzzle tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.puzzles.overlay.overlay_result_label import (
    PuzzlesOverlayResultLabelTask,
)
from tests.helpers import extract_prompt_json_example


def _cell_signature(cells: list[list[int]] | list[dict[str, object]]) -> tuple[tuple[int, int], ...]:
    """Return a hashable row-major cell signature."""

    if cells and isinstance(cells[0], dict):
        return tuple(
            sorted(
                (int(item["cell"][0]), int(item["cell"][1]))
                for item in cells
            )
        )
    return tuple(sorted((int(cell[0]), int(cell[1])) for cell in cells))


def test_overlay_result_label_contract_matches_winning_option_choice() -> None:
    """Check source union, answer binding, and scalar bbox annotation."""

    task = PuzzlesOverlayResultLabelTask()
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
        annotation_bbox = [float(value) for value in out.annotation_gt.value]

        assert str(out.query_id) == SINGLE_QUERY_ID
        assert str(out.scene_id) == "overlay"
        assert str(trace["query_spec"]["query_id"]) == SINGLE_QUERY_ID
        assert str(execution["query_id"]) == SINGLE_QUERY_ID
        assert str(execution["internal_query_id"]) == "overlay_union_same_grid"
        assert out.answer_gt.type == "option_letter"
        assert out.annotation_gt.type == "bbox"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert str(render["scene_style"]["mark_shape"]) in {
            "circle",
            "square",
            "diamond",
            "rounded_square",
        }
        assert str(execution["mark_shape"]) == str(render["scene_style"]["mark_shape"])
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert str(execution["question_format"]) == "overlay_union_mcq"
        assert str(execution["view_family"]) == "transparent_sheet_overlay_mcq"
        assert 4 <= int(execution["grid_size"]) <= 5
        assert int(execution["option_count"]) == 4
        assert 2 <= int(execution["left_mark_count"]) <= 5
        assert 2 <= int(execution["right_mark_count"]) <= 5
        assert 1 <= int(execution["overlap_count"]) <= 2
        assert trace["projected_annotation"]["bbox"] == annotation_bbox
        assert str(out.answer_gt.value) == str(execution["answer_option_label"])

        expected_bbox = [
            float(value)
            for value in render_map["option_choice_bboxes_px"][
                str(execution["correct_option_choice_id"])
            ]
        ]
        assert annotation_bbox == expected_bbox
        assert [str(item) for item in execution["supporting_item_ids"]] == [
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
        assert len({_cell_signature(option["cells"]) for option in option_specs}) == int(
            execution["option_count"]
        )
        source_bboxes = [
            [float(value) for value in render_map["source_sheet_bboxes_px"][sheet_id]]
            for sheet_id in ("source_sheet_left", "source_sheet_right")
        ]
        option_width = expected_bbox[2] - expected_bbox[0]
        option_height = expected_bbox[3] - expected_bbox[1]
        assert all((bbox[2] - bbox[0]) == option_width for bbox in source_bboxes)
        assert all((bbox[3] - bbox[1]) == option_height for bbox in source_bboxes)

        divider_entities = [
            entity
            for entity in trace["scene_ir"]["entities"]
            if str(entity["entity_type"]) == "puzzle_overlay_divider"
        ]
        assert len(divider_entities) == 1
        mark_entities = [
            entity
            for entity in trace["scene_ir"]["entities"]
            if str(entity["entity_type"]).endswith("overlay_mark")
        ]
        assert mark_entities
        assert {str(entity["attrs"]["mark_shape"]) for entity in mark_entities} == {
            str(execution["mark_shape"])
        }

        winning_option = next(option for option in option_specs if bool(option["is_correct"]))
        assert str(winning_option["option_label"]) == str(out.answer_gt.value)
        assert str(winning_option["option_choice_id"]) == str(
            execution["correct_option_choice_id"]
        )
        assert _cell_signature(winning_option["cells"]) == union_signature


def test_overlay_prompt_examples_use_scalar_bbox() -> None:
    """Prompt examples should match scalar bbox annotation shape."""

    out = PuzzlesOverlayResultLabelTask().generate(25990, params={}, max_attempts=10)
    answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
    answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
    assert answer_and_annotation == {"annotation": [521, 384, 679, 542], "answer": "B"}
    assert answer_only == {"answer": "B"}


def test_overlay_result_label_task_is_deterministic() -> None:
    """Generation should be deterministic for a fixed seed and parameters."""

    task = PuzzlesOverlayResultLabelTask()
    params = {"scene_variant": "overlay_card"}
    out_a = task.generate(26010, params=params, max_attempts=10)
    out_b = task.generate(26010, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_overlay_sampling_covers_visual_axes() -> None:
    """Scene variants, mark shapes, options, and answer letters should vary."""

    task = PuzzlesOverlayResultLabelTask()
    scene_variants = Counter()
    mark_shapes = Counter()
    option_counts = Counter()
    answer_letters = Counter()
    for sampling_index in range(120):
        out = task.generate(
            26020 + sampling_index,
            params={},
            max_attempts=10,
        )
        execution = out.trace_payload["execution_trace"]
        scene_variants[str(execution["scene_variant"])] += 1
        mark_shapes[str(execution["mark_shape"])] += 1
        option_counts[int(execution["option_count"])] += 1
        answer_letters[str(out.answer_gt.value)] += 1

    assert set(scene_variants) == {"overlay_strip", "overlay_card", "overlay_outline"}
    assert set(mark_shapes) == {"circle", "square", "diamond", "rounded_square"}
    assert set(option_counts) == {4}
    assert set(answer_letters).issubset({"A", "B", "C", "D"})
    assert len(answer_letters) >= 4
