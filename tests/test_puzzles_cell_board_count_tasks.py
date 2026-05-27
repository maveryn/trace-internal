"""Behavior tests for cell-board count tasks."""

from __future__ import annotations

import json

from trace.tasks.puzzles.cell_board.count_color_components import TileColorComponentsTask
from tests.cell_board_evidence_helpers import tile_coords_from_points, tile_ids_from_points
from trace.tasks.puzzles.cell_board.count_color_count import TileColorCountTask
from trace.tasks.puzzles.cell_board.count_largest_component_size import TileLargestComponentSizeTask


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


def test_cell_board_color_count_outputs_expected_contract() -> None:
    task = TileColorCountTask()
    out = task.generate(
        4401,
        params={
            "rows_min": 4,
            "rows_max": 4,
            "cols_min": 5,
            "cols_max": 5,
            "palette_size_min": 3,
            "palette_size_max": 3,
            "short_side_px_min": 32,
            "short_side_px_max": 32,
            "aspect_ratio_min": 1.5,
            "aspect_ratio_max": 1.5,
            "target_color_count": 5,
        },
        max_attempts=40,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]

    assert str(out.query_id) == "color_count"
    assert out.answer_gt.type == "integer"
    assert isinstance(out.answer_gt.value, int)
    assert out.evidence_gt.type == "point_set"
    assert isinstance(out.evidence_gt.value, list)
    assert out.evidence_gt.value
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert trace["query_spec"]["prompt_variant_active_key"] == "answer_and_evidence"

    assert str(render["coord_space"]) == "tile_grid"
    assert str(render["tiling_type"]) == "rectangular_tiling"
    assert int(render["rows"]) == 4
    assert int(render["cols"]) == 5
    assert int(render["tile_width_px"]) != int(render["tile_height_px"])
    assert out.image.size == (int(render["canvas_width_px"]), int(render["canvas_height_px"]))

    assert trace["projected_evidence"]["type"] == "point_set"
    assert trace["projected_evidence"]["point_set"] == out.evidence_gt.value
    assert trace["projected_evidence"]["pixel_point_set"] == out.evidence_gt.value
    evidence_coords = tile_coords_from_points(trace, out.evidence_gt.value)
    assert evidence_coords == sorted(evidence_coords, key=lambda item: (int(item[0]), int(item[1])))
    assert evidence_coords == execution["matching_coords"]
    assert int(out.answer_gt.value) == len(evidence_coords)
    assert int(out.answer_gt.value) == 5
    assert int(out.answer_gt.value) == int(execution["counts_by_color_name"][execution["query_color_name"]])
    assert execution["query_selection_strategy"] == "uniform_over_target_color_count_with_constructed_board"
    assert execution["target_color_count_range"] == [4, 15]
    assert int(execution["target_color_count"]) == 5
    assert int(out.answer_gt.value) in [int(value) for value in execution["available_color_count_answers"]]
    assert str(execution["query_color_hex"]).startswith("#")
    assert str(execution["query_color_label"]).endswith(f"[{execution['query_color_hex']}]")
    assert str(execution["query_color_label"]) in str(out.prompt)

    witness_ids = tile_ids_from_points(trace, out.evidence_gt.value)
    assert len(witness_ids) == len(evidence_coords)
    for row, col in evidence_coords:
        anchor = trace["render_map"]["anchors"][f"cell_{row}_{col}"]
        assert anchor["coord_space"] == "pixel"
    matched_entities = [
        entity
        for entity in trace["scene_ir"]["entities"]
        if bool(entity["attrs"]["is_query_match"])
    ]
    assert len(matched_entities) == len(evidence_coords)


def test_cell_board_color_count_is_deterministic() -> None:
    task = TileColorCountTask()
    params = {
        "rows_min": 3,
        "rows_max": 7,
        "cols_min": 3,
        "cols_max": 7,
        "palette_size_min": 3,
        "palette_size_max": 5,
    }
    out_a = task.generate(99173, params=params, max_attempts=40)
    out_b = task.generate(99173, params=params, max_attempts=40)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["witness_symbolic"] == out_b.trace_payload["witness_symbolic"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.size == out_b.image.size
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_cell_board_color_count_prompt_example_matches_contract() -> None:
    task = TileColorCountTask()
    out = task.generate(4419, params={}, max_attempts=40)
    example = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert list(example.keys()) == ["evidence", "answer"]
    assert isinstance(example["evidence"], list)
    assert all(isinstance(point, list) and len(point) == 2 for point in example["evidence"])
    assert isinstance(example["answer"], int)


def test_cell_board_color_components_outputs_expected_contract() -> None:
    task = TileColorComponentsTask()
    out = task.generate(
        5501,
        params={
            "rows_min": 4,
            "rows_max": 4,
            "cols_min": 5,
            "cols_max": 5,
            "palette_size_min": 3,
            "palette_size_max": 3,
            "short_side_px_min": 32,
            "short_side_px_max": 32,
            "aspect_ratio_min": 1.5,
            "aspect_ratio_max": 1.5,
        },
        max_attempts=40,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]

    assert str(out.query_id) == "color_components"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "point_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert str(render["tiling_type"]) == "rectangular_tiling"
    assert int(render["rows"]) == 4
    assert int(render["cols"]) == 5
    assert int(render["tile_width_px"]) != int(render["tile_height_px"])
    assert out.image.size == (int(render["canvas_width_px"]), int(render["canvas_height_px"]))

    assert trace["projected_evidence"]["type"] == "point_set"
    assert trace["projected_evidence"]["point_set"] == out.evidence_gt.value
    assert trace["projected_evidence"]["pixel_point_set"] == out.evidence_gt.value
    evidence_coords = tile_coords_from_points(trace, out.evidence_gt.value)
    assert evidence_coords == sorted(evidence_coords, key=lambda item: (int(item[0]), int(item[1])))
    assert evidence_coords == execution["matching_coords"]
    components = execution["components"]
    assert int(out.answer_gt.value) == len(components)
    assert int(out.answer_gt.value) >= 1
    assert execution["query_selection_strategy"] == "uniform_over_target_component_range_with_rejection"
    assert int(execution["target_component_count"]) == int(out.answer_gt.value)
    assert execution["target_component_count_range"] == [1, 5]
    assert int(out.answer_gt.value) in [int(value) for value in execution["available_component_answers"]]
    flattened = [coord for component in components for coord in component["coords"]]
    assert sorted(flattened) == sorted(evidence_coords)
    assert execution["component_sizes"] == [len(component["coords"]) for component in components]
    assert str(execution["query_color_label"]).endswith(f"[{execution['query_color_hex']}]")
    assert str(execution["query_color_label"]) in str(out.prompt)

    matched_entities = [
        entity
        for entity in trace["scene_ir"]["entities"]
        if bool(entity["attrs"]["is_query_match"])
    ]
    assert len(matched_entities) == len(evidence_coords)
    matched_component_indices = {
        int(entity["attrs"]["query_component_index"])
        for entity in matched_entities
    }
    assert matched_component_indices == set(range(len(components)))


def test_cell_board_color_components_is_deterministic() -> None:
    task = TileColorComponentsTask()
    params = {
        "rows_min": 3,
        "rows_max": 7,
        "cols_min": 3,
        "cols_max": 7,
        "palette_size_min": 3,
        "palette_size_max": 5,
    }
    out_a = task.generate(88173, params=params, max_attempts=40)
    out_b = task.generate(88173, params=params, max_attempts=40)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"]["components"] == out_b.trace_payload["execution_trace"]["components"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.size == out_b.image.size
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_cell_board_color_components_prompt_example_matches_contract() -> None:
    task = TileColorComponentsTask()
    out = task.generate(5519, params={}, max_attempts=40)
    example = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert list(example.keys()) == ["evidence", "answer"]
    assert example["evidence"] == [[120, 120], [168, 120], [216, 216]]
    assert int(example["answer"]) == 2


def test_cell_board_largest_component_size_outputs_expected_contract() -> None:
    task = TileLargestComponentSizeTask()
    out = task.generate(
        6501,
        params={
            "rows_min": 4,
            "rows_max": 4,
            "cols_min": 5,
            "cols_max": 5,
            "palette_size_min": 3,
            "palette_size_max": 3,
            "short_side_px_min": 32,
            "short_side_px_max": 32,
            "aspect_ratio_min": 1.5,
            "aspect_ratio_max": 1.5,
        },
        max_attempts=80,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]

    assert str(out.query_id) == "largest_component_size"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "point_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert str(render["tiling_type"]) == "rectangular_tiling"
    assert int(render["rows"]) == 4
    assert int(render["cols"]) == 5
    assert int(render["tile_width_px"]) != int(render["tile_height_px"])
    assert out.image.size == (int(render["canvas_width_px"]), int(render["canvas_height_px"]))

    assert trace["projected_evidence"]["type"] == "point_set"
    assert trace["projected_evidence"]["point_set"] == out.evidence_gt.value
    assert trace["projected_evidence"]["pixel_point_set"] == out.evidence_gt.value
    evidence_coords = tile_coords_from_points(trace, out.evidence_gt.value)
    assert evidence_coords == sorted(evidence_coords, key=lambda item: (int(item[0]), int(item[1])))
    assert evidence_coords == execution["winning_component_coords"]
    assert int(out.answer_gt.value) == len(evidence_coords)
    assert int(out.answer_gt.value) == int(execution["target_largest_component_size"])
    assert execution["target_largest_component_size_range"] == [2, 7]
    assert int(out.answer_gt.value) in [int(value) for value in execution["available_largest_component_sizes"]]
    assert int(execution["query_component_count"]) >= 2
    assert execution["component_sizes"] == [len(component["coords"]) for component in execution["components"]]
    winning_components = [component for component in execution["components"] if bool(component["is_largest_component"])]
    assert len(winning_components) == 1
    assert winning_components[0]["coords"] == evidence_coords
    assert int(winning_components[0]["size"]) == int(out.answer_gt.value)
    assert str(execution["query_color_label"]).endswith(f"[{execution['query_color_hex']}]")
    assert str(execution["query_color_label"]) in str(out.prompt)

    matched_entities = [
        entity
        for entity in trace["scene_ir"]["entities"]
        if bool(entity["attrs"]["is_query_match"])
    ]
    largest_entities = [
        entity
        for entity in matched_entities
        if bool(entity["attrs"]["is_largest_component"])
    ]
    assert len(largest_entities) == len(evidence_coords)
    assert {str(entity["entity_id"]) for entity in largest_entities} == set(tile_ids_from_points(trace, out.evidence_gt.value))


def test_cell_board_largest_component_size_caps_target_range_for_small_boards() -> None:
    task = TileLargestComponentSizeTask()
    out = task.generate(
        6517,
        params={
            "rows_min": 3,
            "rows_max": 3,
            "cols_min": 3,
            "cols_max": 3,
            "palette_size_min": 3,
            "palette_size_max": 3,
        },
        max_attempts=120,
    )
    execution = out.trace_payload["execution_trace"]

    assert execution["target_largest_component_size_range"] == [2, 6]
    assert 2 <= int(execution["target_largest_component_size"]) <= 6
    assert int(out.answer_gt.value) == int(execution["target_largest_component_size"])


def test_cell_board_largest_component_size_is_deterministic() -> None:
    task = TileLargestComponentSizeTask()
    params = {
        "rows_min": 3,
        "rows_max": 7,
        "cols_min": 3,
        "cols_max": 7,
        "palette_size_min": 2,
        "palette_size_max": 3,
    }
    out_a = task.generate(99119, params=params, max_attempts=80)
    out_b = task.generate(99119, params=params, max_attempts=80)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"]["components"] == out_b.trace_payload["execution_trace"]["components"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.size == out_b.image.size
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_cell_board_largest_component_size_prompt_example_matches_contract() -> None:
    task = TileLargestComponentSizeTask()
    out = task.generate(6529, params={}, max_attempts=80)
    example = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert list(example.keys()) == ["evidence", "answer"]
    assert example["evidence"] == [[120, 120], [168, 120], [168, 168], [216, 168]]
    assert int(example["answer"]) == 4


def test_cell_board_count_complexity_is_normalized_and_monotonic() -> None:
    color_count_task = TileColorCountTask()
    color_count = color_count_task.generate(6601, params={}, max_attempts=40)
    _assert_normalized_complexity(color_count)

    color_components_task = TileColorComponentsTask()
    color_components = color_components_task.generate(6602, params={}, max_attempts=200)
    _assert_normalized_complexity(color_components)

    largest_task = TileLargestComponentSizeTask()
    easy_largest = largest_task.generate(
        6603,
        params={
            "rows_min": 7,
            "rows_max": 7,
            "cols_min": 7,
            "cols_max": 7,
            "palette_size_min": 3,
            "palette_size_max": 3,
            "target_largest_component_size_min": 2,
            "target_largest_component_size_max": 2,
        },
        max_attempts=200,
    )
    hard_largest = largest_task.generate(
        6603,
        params={
            "rows_min": 7,
            "rows_max": 7,
            "cols_min": 7,
            "cols_max": 7,
            "palette_size_min": 3,
            "palette_size_max": 3,
            "target_largest_component_size_min": 5,
            "target_largest_component_size_max": 5,
        },
        max_attempts=200,
    )
    _assert_normalized_complexity(easy_largest)
    _assert_normalized_complexity(hard_largest)
    assert float(hard_largest.complexity.complexity_components["reasoning_load"]) > float(
        easy_largest.complexity.complexity_components["reasoning_load"]
    )
    assert float(hard_largest.complexity.complexity_score) > float(
        easy_largest.complexity.complexity_score
    )
