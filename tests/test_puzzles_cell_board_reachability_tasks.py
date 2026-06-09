"""Behavior tests for cell-board reachability tasks."""

from __future__ import annotations

import json

from trace.tasks.puzzles.cell_board.reachability_region_size import TileRegionSizeTask
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


def test_cell_board_region_size_outputs_expected_contract() -> None:
    task = TileRegionSizeTask()
    out = task.generate(
        6601,
        params={
            "rows_min": 4,
            "rows_max": 4,
            "cols_min": 5,
            "cols_max": 5,
            "short_side_px_min": 32,
            "short_side_px_max": 32,
            "aspect_ratio_min": 1.5,
            "aspect_ratio_max": 1.5,
            "obstacle_fraction_min": 0.20,
            "obstacle_fraction_max": 0.20,
            "reachable_fraction_min": 0.20,
            "reachable_fraction_max": 0.90,
            "answer_min": 4,
            "answer_max": 4,
        },
        max_attempts=300,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]

    assert str(out.query_id) == "region_size"
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "point_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
    assert str(render["tiling_type"]) == "rectangular_tiling"
    assert int(render["rows"]) == 4
    assert int(render["cols"]) == 5
    assert int(render["tile_width_px"]) != int(render["tile_height_px"])
    assert out.image.size == (int(render["canvas_width_px"]), int(render["canvas_height_px"]))

    assert trace["projected_annotation"]["type"] == "point_set"
    assert trace["projected_annotation"]["point_set"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_point_set"] == out.annotation_gt.value
    annotation_coords = tile_coords_from_points(trace, out.annotation_gt.value)
    assert annotation_coords == sorted(annotation_coords, key=lambda item: (int(item[0]), int(item[1])))
    assert annotation_coords == execution["reachable_coords"]
    assert int(out.answer_gt.value) == len(annotation_coords)
    assert 3 <= int(out.answer_gt.value) <= 8
    assert int(execution["answer_min"]) == 4
    assert int(execution["answer_max"]) == 4
    assert list(execution["answer_range"]) == [4, 4]
    assert int(execution["target_region_size"]) == int(out.answer_gt.value)
    assert execution["start_coord"] in annotation_coords
    assert str(execution["obstacle_color_label"]).endswith("[#000000]")
    assert str(execution["start_color_label"]) in str(out.prompt)

    blocked_coords = {tuple(coord) for coord in execution["blocked_coords"]}
    assert tuple(execution["start_coord"]) not in blocked_coords
    reachable_entities = [
        entity
        for entity in trace["scene_ir"]["entities"]
        if bool(entity["attrs"]["is_reachable"])
    ]
    assert len(reachable_entities) == len(annotation_coords)
    start_entities = [entity for entity in reachable_entities if bool(entity["attrs"]["is_start"])]
    assert len(start_entities) == 1
    assert start_entities[0]["attrs"]["fill_rgb"] == execution["start_color_rgb"]
    _assert_normalized_complexity(out)


def test_cell_board_region_size_is_deterministic() -> None:
    task = TileRegionSizeTask()
    params = {
        "rows_min": 3,
        "rows_max": 7,
        "cols_min": 3,
        "cols_max": 7,
        "obstacle_fraction_min": 0.12,
        "obstacle_fraction_max": 0.38,
        "reachable_fraction_min": 0.20,
        "reachable_fraction_max": 0.85,
    }
    out_a = task.generate(99101, params=params, max_attempts=80)
    out_b = task.generate(99101, params=params, max_attempts=80)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["witness_symbolic"] == out_b.trace_payload["witness_symbolic"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert (
        out_a.trace_payload["execution_trace"]["start_color_label"]
        == out_b.trace_payload["execution_trace"]["start_color_label"]
    )
    assert out_a.prompt == out_b.prompt
    assert out_a.image.size == out_b.image.size
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_cell_board_region_size_prompt_example_matches_contract() -> None:
    task = TileRegionSizeTask()
    out = task.generate(6629, params={}, max_attempts=80)
    example = _extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
    assert list(example.keys()) == ["annotation", "answer"]
    assert example["annotation"] == [[120, 120], [168, 120], [168, 168], [168, 216]]
    assert int(example["answer"]) == 4
