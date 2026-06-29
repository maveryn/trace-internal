"""Behavior tests for the polyomino-missing puzzle scene."""

from __future__ import annotations

from trace.tasks.puzzles.polyomino_missing.rectangle_complement_piece import (
    PuzzlesPolyominoMissingRectangleComplementPieceTask,
)
from trace.tasks.puzzles.polyomino_missing.shared.rules import d4_signature
from tests.helpers import extract_prompt_json_example


def _cell_signature(cells: list[list[int]] | list[dict[str, object]]) -> tuple[tuple[int, int], ...]:
    """Return a hashable row-major cell signature."""

    if cells and isinstance(cells[0], dict):
        return tuple(
            sorted((int(item["cell"][0]), int(item["cell"][1])) for item in cells)  # type: ignore[index]
        )
    return tuple(sorted((int(cell[0]), int(cell[1])) for cell in cells))  # type: ignore[index]


def _annotation_bbox_map(out) -> dict[str, list[float]]:
    """Return the role-bound bbox map from generated annotation."""

    assert out.annotation_gt.type == "bbox_map"
    return {
        str(key): [float(value) for value in bbox]
        for key, bbox in dict(out.annotation_gt.value).items()
    }


def test_rectangle_complement_contract_matches_winning_option_panel() -> None:
    task = PuzzlesPolyominoMissingRectangleComplementPieceTask()
    matching_policies = ("exact_orientation", "rotation_reflection_allowed")
    scene_variants = ("polyomino_strip", "polyomino_card", "polyomino_outline")

    for policy_index, matching_policy in enumerate(matching_policies):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 27220 + (policy_index * 20) + scene_index
            out = task.generate(
                seed,
                params={"query_id": matching_policy, "scene_variant": scene_variant},
                max_attempts=10,
            )
            trace = out.trace_payload
            execution = trace["execution_trace"]
            payload = execution["variant_payload"]
            render = trace["render_spec"]
            render_map = trace["render_map"]
            annotation_map = _annotation_bbox_map(out)

            assert str(out.query_id) == str(matching_policy)
            assert str(trace["query_spec"]["query_id"]) == str(matching_policy)
            assert str(execution["query_id"]) == str(matching_policy)
            assert out.answer_gt.type == "option_letter"
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(render["scene_variant"]) == str(scene_variant)
            assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
            assert int(payload["option_count"]) in {4, 6}
            assert 3 <= int(payload["cutout_cell_count"]) <= 7
            assert str(execution["matching_policy"]) == str(matching_policy)
            assert str(execution["question_format"]) == "rectangle_complement_piece"
            assert (
                str(execution["view_family"])
                == "polyomino_rectangle_complement_piece_option_puzzle"
            )
            assert str(out.answer_gt.value) == str(execution["answer_option_label"])

            expected_bbox = [
                float(value)
                for value in render_map["item_bboxes_px"][str(execution["correct_option_panel_id"])]
            ]
            missing_bbox = [
                float(value) for value in render_map["item_bboxes_px"]["missing_region"]
            ]
            assert annotation_map["selected_option"] == expected_bbox
            assert annotation_map["missing_region"] == missing_bbox
            assert [str(item) for item in execution["annotation_item_roles"]] == [
                "selected_option",
                "missing_region",
            ]

            option_specs = execution["option_specs"]
            expected_labels = [
                chr(ord("A") + index) for index in range(int(payload["option_count"]))
            ]
            assert [str(option["option_label"]) for option in option_specs] == expected_labels
            assert sum(1 for option in option_specs if bool(option["is_correct"])) == 1
            assert len({_cell_signature(option["cells"]) for option in option_specs}) == int(
                payload["option_count"]
            )

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
                assert _cell_signature(winning_option["cells"]) == _cell_signature(
                    payload["cutout_cells"]
                )
            else:
                winning_signature = d4_signature(
                    tuple((int(cell[0]), int(cell[1])) for cell in winning_option["cells"])
                )
                cutout_signature = d4_signature(
                    tuple((int(cell[0]), int(cell[1])) for cell in payload["cutout_cells"])
                )
                assert winning_signature == cutout_signature


def test_rectangle_complement_prompt_examples_match_bbox_map_contract() -> None:
    task = PuzzlesPolyominoMissingRectangleComplementPieceTask()
    out = task.generate(
        27320,
        params={"query_id": "rotation_reflection_allowed"},
        max_attempts=10,
    )
    answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
    answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])

    assert answer_and_annotation == {
        "annotation": {
            "selected_option": [416, 604, 592, 808],
            "missing_region": [580, 218, 618, 256],
        },
        "answer": "C",
    }
    assert answer_only == {"answer": "C"}
    assert "rotated or reflected" in out.prompt


def test_rectangle_complement_sampling_covers_letters_per_query() -> None:
    task = PuzzlesPolyominoMissingRectangleComplementPieceTask()
    observed_by_query = {
        "exact_orientation": set(),
        "rotation_reflection_allowed": set(),
    }
    for sampling_index in range(200):
        out = task.generate(27380 + sampling_index, params={}, max_attempts=10)
        query = str(out.trace_payload["execution_trace"]["query_id"])
        observed_by_query[query].add(str(out.answer_gt.value))

    assert observed_by_query["exact_orientation"] >= {"A", "B", "C", "D", "E"}
    assert observed_by_query["rotation_reflection_allowed"] >= {"A", "B", "C", "D", "E"}


def test_rectangle_complement_task_is_deterministic() -> None:
    task = PuzzlesPolyominoMissingRectangleComplementPieceTask()
    params = {
        "query_id": "rotation_reflection_allowed",
        "scene_variant": "polyomino_card",
    }
    out_a = task.generate(27480, params=params, max_attempts=10)
    out_b = task.generate(27480, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload[
        "query_spec"
    ]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
