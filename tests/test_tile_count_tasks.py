"""Behavior tests for tile count tasks."""

from __future__ import annotations

import json

from trace.tasks.tile.count.color_components import TileColorComponentsTask
from trace.tasks.tile.count.color_count import TileColorCountTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_tile_color_count_outputs_expected_contract() -> None:
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
        },
        max_attempts=40,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]

    assert str(out.task_variant) == "color_count"
    assert out.answer_gt.type == "integer"
    assert isinstance(out.answer_gt.value, int)
    assert out.evidence_gt.type == "grid_point_set"
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

    evidence_coords = [[int(point[0]), int(point[1])] for point in out.evidence_gt.value]
    assert evidence_coords == sorted(evidence_coords, key=lambda item: (int(item[0]), int(item[1])))
    assert evidence_coords == execution["matching_coords"]
    assert int(out.answer_gt.value) == len(evidence_coords)
    assert int(out.answer_gt.value) == int(execution["counts_by_color_name"][execution["query_color_name"]])
    assert str(execution["query_color_hex"]).startswith("#")
    assert str(execution["query_color_label"]).endswith(f"[{execution['query_color_hex']}]")
    assert str(execution["query_color_label"]) in str(out.prompt)

    witness_ids = list(trace["witness_symbolic"]["ids"])
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


def test_tile_color_count_is_deterministic() -> None:
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


def test_tile_color_count_prompt_example_matches_contract() -> None:
    task = TileColorCountTask()
    out = task.generate(4419, params={}, max_attempts=40)
    example = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert list(example.keys()) == ["evidence", "answer"]
    assert isinstance(example["evidence"], list)
    assert all(isinstance(point, list) and len(point) == 2 for point in example["evidence"])
    assert isinstance(example["answer"], int)


def test_tile_color_components_outputs_expected_contract() -> None:
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

    assert str(out.task_variant) == "color_components"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "grid_point_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert str(render["tiling_type"]) == "rectangular_tiling"
    assert int(render["rows"]) == 4
    assert int(render["cols"]) == 5
    assert int(render["tile_width_px"]) != int(render["tile_height_px"])
    assert out.image.size == (int(render["canvas_width_px"]), int(render["canvas_height_px"]))

    evidence_coords = [[int(point[0]), int(point[1])] for point in out.evidence_gt.value]
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


def test_tile_color_components_is_deterministic() -> None:
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


def test_tile_color_components_prompt_example_matches_contract() -> None:
    task = TileColorComponentsTask()
    out = task.generate(5519, params={}, max_attempts=40)
    example = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert list(example.keys()) == ["evidence", "answer"]
    assert example["evidence"] == [[0, 0], [0, 1], [2, 2]]
    assert int(example["answer"]) == 2
