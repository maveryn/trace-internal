"""Behavior tests for tile shortest-path tasks."""

from __future__ import annotations

import json

from trace.tasks.tile.path.shortest_path import TileShortestPathTask


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
