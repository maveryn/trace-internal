"""Behavior tests for tile reachability tasks."""

from __future__ import annotations

import json

from trace.tasks.tile.reachability.reachable_count import TileReachableCountTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_tile_reachable_count_outputs_expected_contract() -> None:
    task = TileReachableCountTask()
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
        },
        max_attempts=80,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]

    assert str(out.task_variant) == "reachable_count"
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
    assert evidence_coords == execution["reachable_coords"]
    assert int(out.answer_gt.value) == len(evidence_coords)
    assert execution["start_coord"] in evidence_coords
    assert str(execution["obstacle_color_label"]).endswith("[#000000]")
    assert "purple [#963ACA]" in str(out.prompt)

    blocked_coords = {tuple(coord) for coord in execution["blocked_coords"]}
    assert tuple(execution["start_coord"]) not in blocked_coords
    reachable_entities = [
        entity
        for entity in trace["scene_ir"]["entities"]
        if bool(entity["attrs"]["is_reachable"])
    ]
    assert len(reachable_entities) == len(evidence_coords)
    assert any(bool(entity["attrs"]["is_start"]) for entity in reachable_entities)


def test_tile_reachable_count_is_deterministic() -> None:
    task = TileReachableCountTask()
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
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["witness_symbolic"] == out_b.trace_payload["witness_symbolic"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.size == out_b.image.size
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_tile_reachable_count_prompt_example_matches_contract() -> None:
    task = TileReachableCountTask()
    out = task.generate(6629, params={}, max_attempts=80)
    example = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert list(example.keys()) == ["evidence", "answer"]
    assert example["evidence"] == [[0, 0], [0, 1], [1, 1], [2, 1]]
    assert int(example["answer"]) == 4
