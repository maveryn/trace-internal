"""Behavior tests for cell-board relation tasks."""

from __future__ import annotations

from collections import Counter
import json

from trace.core.seed import hash64
from trace.tasks.puzzles.cell_board.relation_min_distance import TileMinDistanceTask
from tests.cell_board_annotation_helpers import tile_coords_from_points, tile_ids_from_points


def _assert_normalized_complexity(out: object) -> None:
    complexity = out.complexity.to_dict()
    assert 0.0 <= float(complexity["complexity_score"]) <= 1.0
    assert set(complexity["complexity_components"].keys()) == {
        "reasoning_load",
        "visual_scan",
    }
    assert all(
        0.0 <= float(value) <= 1.0 for value in complexity["complexity_components"].values()
    )


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_cell_board_min_distance_outputs_expected_contract() -> None:
    task = TileMinDistanceTask()
    out = task.generate(
        9101,
        params={
            "rows_min": 5,
            "rows_max": 5,
            "cols_min": 7,
            "cols_max": 7,
            "target_distance_min": 4,
            "target_distance_max": 4,
            "short_side_px_min": 32,
            "short_side_px_max": 32,
            "aspect_ratio_min": 1.5,
            "aspect_ratio_max": 1.5,
        },
        max_attempts=10,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]

    assert str(out.query_id) == "min_distance"
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "point_sequence"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
    assert str(render["tiling_type"]) == "rectangular_tiling"
    assert int(render["rows"]) == 5
    assert int(render["cols"]) == 7
    assert int(render["tile_width_px"]) != int(render["tile_height_px"])
    assert out.image.size == (int(render["canvas_width_px"]), int(render["canvas_height_px"]))

    assert trace["projected_annotation"]["type"] == "point_sequence"
    assert trace["projected_annotation"]["point_sequence"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_point_sequence"] == out.annotation_gt.value
    annotation_coords = tile_coords_from_points(trace, out.annotation_gt.value)
    assert len(annotation_coords) == int(out.answer_gt.value) + 1
    assert int(out.answer_gt.value) == 4
    assert execution["target_distance_range"] == [4, 4]
    assert int(execution["target_distance"]) == 4
    assert int(execution["answer_value"]) == 4
    assert bool(execution["unique_closest_pair"]) is True
    assert str(execution["color_a_label"]).endswith(f"[{execution['color_a_hex']}]")
    assert str(execution["color_b_label"]).endswith(f"[{execution['color_b_hex']}]")
    assert str(execution["color_a_label"]) in str(out.prompt)
    assert str(execution["color_b_label"]) in str(out.prompt)

    assert annotation_coords[0] == execution["color_a_tip_coord"]
    assert annotation_coords[-1] == execution["color_b_tip_coord"]
    same_row = all(int(coord[0]) == int(annotation_coords[0][0]) for coord in annotation_coords)
    same_col = all(int(coord[1]) == int(annotation_coords[0][1]) for coord in annotation_coords)
    assert same_row or same_col

    color_a_coords = [tuple(coord) for coord in execution["color_a_coords"]]
    color_b_coords = [tuple(coord) for coord in execution["color_b_coords"]]
    pair_distances = [
        abs(int(left[0]) - int(right[0])) + abs(int(left[1]) - int(right[1]))
        for left in color_a_coords
        for right in color_b_coords
    ]
    assert min(pair_distances) == 4
    assert sum(1 for value in pair_distances if int(value) == 4) == 1
    _assert_normalized_complexity(out)


def test_cell_board_min_distance_caps_target_range_for_small_boards() -> None:
    task = TileMinDistanceTask()
    out = task.generate(
        9109,
        params={
            "rows_min": 3,
            "rows_max": 3,
            "cols_min": 4,
            "cols_max": 4,
        },
        max_attempts=10,
    )
    execution = out.trace_payload["execution_trace"]

    assert execution["target_distance_range"] == [3, 3]
    assert int(execution["target_distance"]) == 3
    assert int(out.answer_gt.value) == 3


def test_cell_board_min_distance_is_deterministic() -> None:
    task = TileMinDistanceTask()
    params = {
        "rows_min": 4,
        "rows_max": 8,
        "cols_min": 4,
        "cols_max": 8,
        "target_distance_min": 3,
        "target_distance_max": 7,
    }
    out_a = task.generate(9113, params=params, max_attempts=10)
    out_b = task.generate(9113, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.size == out_b.image.size
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_cell_board_min_distance_prompt_examples_match_variant_contract() -> None:
    task = TileMinDistanceTask()
    out = task.generate(9121, params={}, max_attempts=10)
    example = _extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
    answer_only_example = _extract_prompt_json_example(out.prompt_variants["answer_only"])

    assert example == {"annotation": [[168, 168], [216, 168], [264, 168], [312, 168]], "answer": 3}
    assert answer_only_example == {"answer": 3}


def test_cell_board_min_distance_review_seed_stream_stays_balanced() -> None:
    task = TileMinDistanceTask()
    counts = Counter()

    for seed_index in range(100):
        instance_seed = int(hash64(0, task.task_id, seed_index))
        out = task.generate(instance_seed, params={}, max_attempts=10)
        counts[int(out.answer_gt.value)] += 1

    assert set(counts.keys()) == {3, 4, 5, 6, 7}
    assert max(counts.values()) <= 35


def test_cell_board_relation_complexity_is_normalized_and_monotonic() -> None:
    task = TileMinDistanceTask()
    easy = task.generate(
        9129,
        params={
            "rows_min": 5,
            "rows_max": 5,
            "cols_min": 7,
            "cols_max": 8,
            "target_distance_min": 2,
            "target_distance_max": 2,
        },
        max_attempts=10,
    )
    hard = task.generate(
        9129,
        params={
            "rows_min": 5,
            "rows_max": 5,
            "cols_min": 7,
            "cols_max": 8,
            "target_distance_min": 5,
            "target_distance_max": 5,
        },
        max_attempts=10,
    )
    _assert_normalized_complexity(easy)
    _assert_normalized_complexity(hard)
    assert int(hard.answer_gt.value) > int(easy.answer_gt.value)
