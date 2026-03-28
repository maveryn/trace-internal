"""Behavior tests for tile path tasks."""

from __future__ import annotations

import json

from trace.tasks.tile.path_reachable_target_count import TileReachableTargetCountTask
from trace.tasks.tile.path_shortest_path import TileShortestPathTask


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


def test_tile_shortest_path_outputs_expected_contract() -> None:
    task = TileShortestPathTask()
    out = task.generate(
        7701,
        params={
            "rows": 7,
            "cols": 7,
            "target_shortest_len_min": 4,
            "target_shortest_len_max": 10,
            "short_side_px_min": 32,
            "short_side_px_max": 32,
            "aspect_ratio_min": 1.0,
            "aspect_ratio_max": 1.0,
            "obstacle_prob_min": 0.20,
            "obstacle_prob_max": 0.20,
        },
        max_attempts=160,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]

    assert str(out.task_variant) == "shortest_path"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "grid_point_path"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert str(render["tiling_type"]) == "rectangular_tiling"
    assert float(render["tile_aspect_ratio"]) == 1.0
    assert int(render["tile_width_px"]) == int(render["tile_height_px"])
    assert out.image.size == (int(render["canvas_width_px"]), int(render["canvas_height_px"]))

    path_coords = [[int(point[0]), int(point[1])] for point in out.evidence_gt.value]
    assert path_coords == execution["path_coords"]
    assert int(out.answer_gt.value) == len(path_coords) - 1
    assert path_coords[0] == execution["start_coord"]
    assert path_coords[-1] == execution["goal_coord"]
    assert str(execution["obstacle_color_label"]).endswith("[#000000]")
    assert str(execution["start_color_label"]) in str(out.prompt)
    assert str(execution["goal_color_label"]) in str(out.prompt)

    path_entities = [
        entity
        for entity in trace["scene_ir"]["entities"]
        if bool(entity["attrs"]["is_on_shortest_path"])
    ]
    assert len(path_entities) == len(path_coords)
    start_entities = [entity for entity in path_entities if bool(entity["attrs"]["is_start"])]
    goal_entities = [entity for entity in path_entities if bool(entity["attrs"]["is_goal"])]
    assert len(start_entities) == 1
    assert len(goal_entities) == 1
    assert start_entities[0]["attrs"]["fill_rgb"] == execution["start_color_rgb"]
    assert goal_entities[0]["attrs"]["fill_rgb"] == execution["goal_color_rgb"]
    _assert_normalized_complexity(out)


def test_tile_shortest_path_is_deterministic() -> None:
    task = TileShortestPathTask()
    params = {
        "rows": 7,
        "cols": 7,
        "target_shortest_len_min": 4,
        "target_shortest_len_max": 10,
        "aspect_ratio_min": 1.0,
        "aspect_ratio_max": 1.0,
    }
    out_a = task.generate(7719, params=params, max_attempts=160)
    out_b = task.generate(7719, params=params, max_attempts=160)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["witness_symbolic"] == out_b.trace_payload["witness_symbolic"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.trace_payload["execution_trace"]["target_shortest_len"] == out_b.trace_payload["execution_trace"]["target_shortest_len"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.size == out_b.image.size
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_tile_shortest_path_prompt_example_matches_contract() -> None:
    task = TileShortestPathTask()
    out = task.generate(7733, params={}, max_attempts=160)
    example = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert list(example.keys()) == ["evidence", "answer"]
    assert example["evidence"] == [[0, 0], [0, 1], [1, 1], [1, 2]]
    assert int(example["answer"]) == 3


def test_tile_reachable_target_count_outputs_expected_contract() -> None:
    task = TileReachableTargetCountTask()
    out = task.generate(
        7749,
        params={
            "rows": 7,
            "cols": 7,
            "target_reachable_target_count_min": 2,
            "target_reachable_target_count_max": 2,
            "short_side_px_min": 32,
            "short_side_px_max": 32,
            "aspect_ratio_min": 1.0,
            "aspect_ratio_max": 1.0,
            "obstacle_prob_min": 0.20,
            "obstacle_prob_max": 0.20,
        },
        max_attempts=160,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]

    assert str(out.task_variant) == "reachable_target_count"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "grid_point_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert str(render["tiling_type"]) == "rectangular_tiling"
    assert float(render["tile_aspect_ratio"]) == 1.0
    assert int(render["tile_width_px"]) == int(render["tile_height_px"])
    assert out.image.size == (int(render["canvas_width_px"]), int(render["canvas_height_px"]))

    evidence_coords = [[int(point[0]), int(point[1])] for point in out.evidence_gt.value]
    assert evidence_coords == execution["reachable_target_coords"]
    assert int(out.answer_gt.value) == len(evidence_coords) == 2
    assert execution["target_reachable_target_count_range"] == [2, 2]
    assert int(execution["target_reachable_target_count"]) == 2
    assert int(execution["total_target_count"]) == 3
    assert str(execution["obstacle_color_label"]).endswith("[#000000]")
    assert str(execution["start_color_label"]) in str(out.prompt)
    assert str(execution["target_color_label"]) in str(out.prompt)

    target_coords = {tuple(coord) for coord in execution["target_coords"]}
    reachable_target_coords = {tuple(coord) for coord in execution["reachable_target_coords"]}
    unreachable_target_coords = {tuple(coord) for coord in execution["unreachable_target_coords"]}
    assert len(target_coords) == 3
    assert reachable_target_coords == {tuple(coord) for coord in evidence_coords}
    assert reachable_target_coords.isdisjoint({tuple(execution["start_coord"])})
    assert reachable_target_coords.issubset(target_coords)
    assert unreachable_target_coords.issubset(target_coords)
    assert reachable_target_coords.isdisjoint(unreachable_target_coords)

    target_entities = [
        entity
        for entity in trace["scene_ir"]["entities"]
        if bool(entity["attrs"]["is_target"])
    ]
    assert len(target_entities) == 3
    reachable_target_entities = [
        entity
        for entity in target_entities
        if bool(entity["attrs"]["is_reachable_target"])
    ]
    unreachable_target_entities = [
        entity
        for entity in target_entities
        if bool(entity["attrs"]["is_unreachable_target"])
    ]
    assert len(reachable_target_entities) == 2
    assert len(unreachable_target_entities) == 1
    assert all(entity["attrs"]["fill_rgb"] == execution["target_color_rgb"] for entity in target_entities)
    _assert_normalized_complexity(out)


def test_tile_reachable_target_count_supports_zero_answer_with_empty_evidence() -> None:
    task = TileReachableTargetCountTask()
    out = task.generate(
        7751,
        params={
            "rows": 7,
            "cols": 7,
            "target_reachable_target_count_min": 0,
            "target_reachable_target_count_max": 0,
        },
        max_attempts=160,
    )
    execution = out.trace_payload["execution_trace"]

    assert int(out.answer_gt.value) == 0
    assert out.evidence_gt.value == []
    assert execution["reachable_target_coords"] == []
    assert int(execution["total_target_count"]) >= 2


def test_tile_reachable_target_count_is_deterministic() -> None:
    task = TileReachableTargetCountTask()
    params = {
        "rows": 7,
        "cols": 7,
        "target_reachable_target_count_min": 0,
        "target_reachable_target_count_max": 6,
        "aspect_ratio_min": 1.0,
        "aspect_ratio_max": 1.0,
    }
    out_a = task.generate(7767, params=params, max_attempts=160)
    out_b = task.generate(7767, params=params, max_attempts=160)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["witness_symbolic"] == out_b.trace_payload["witness_symbolic"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert (
        out_a.trace_payload["execution_trace"]["target_reachable_target_count"]
        == out_b.trace_payload["execution_trace"]["target_reachable_target_count"]
    )
    assert out_a.prompt == out_b.prompt
    assert out_a.image.size == out_b.image.size
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_tile_reachable_target_count_prompt_example_matches_contract() -> None:
    task = TileReachableTargetCountTask()
    out = task.generate(7773, params={}, max_attempts=160)
    example = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert list(example.keys()) == ["evidence", "answer"]
    assert example["evidence"] == [[0, 2], [2, 1]]
    assert int(example["answer"]) == 2


def test_tile_path_complexity_is_normalized_and_monotonic() -> None:
    task = TileReachableTargetCountTask()
    easy = task.generate(
        7781,
        params={
            "rows": 7,
            "cols": 7,
            "target_reachable_target_count_min": 0,
            "target_reachable_target_count_max": 6,
            "_sampling_index": 0,
        },
        max_attempts=200,
    )
    hard = task.generate(
        7781,
        params={
            "rows": 7,
            "cols": 7,
            "target_reachable_target_count_min": 0,
            "target_reachable_target_count_max": 6,
            "_sampling_index": 6,
        },
        max_attempts=200,
    )
    _assert_normalized_complexity(easy)
    _assert_normalized_complexity(hard)
    assert float(hard.complexity.complexity_components["reasoning_load"]) > float(
        easy.complexity.complexity_components["reasoning_load"]
    )
    assert float(hard.complexity.complexity_score) > float(easy.complexity.complexity_score)
