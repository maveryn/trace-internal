"""Behavior tests for tile topology tasks."""

from __future__ import annotations

import json

from trace.tasks.tile.topology.hole_count import TileHoleCountTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_tile_hole_count_outputs_expected_contract() -> None:
    task = TileHoleCountTask()
    out = task.generate(
        9101,
        params={
            "rows_min": 7,
            "rows_max": 7,
            "cols_min": 7,
            "cols_max": 7,
            "answer_min": 3,
            "answer_max": 3,
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

    assert str(out.task_variant) == "hole_count"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "grid_point_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert str(render["tiling_type"]) == "rectangular_tiling"
    assert int(render["rows"]) == 7
    assert int(render["cols"]) == 7
    assert int(render["tile_width_px"]) != int(render["tile_height_px"])
    assert out.image.size == (int(render["canvas_width_px"]), int(render["canvas_height_px"]))

    evidence_coords = [[int(point[0]), int(point[1])] for point in out.evidence_gt.value]
    assert evidence_coords == sorted(evidence_coords, key=lambda item: (int(item[0]), int(item[1])))
    assert trace["projected_evidence"]["grid_point_set"] == evidence_coords
    assert int(out.answer_gt.value) == len(evidence_coords)
    assert int(out.answer_gt.value) == 3
    assert execution["target_hole_count_range"] == [3, 3]
    assert int(execution["target_hole_count"]) == 3
    assert int(execution["white_component_count"]) == int(out.answer_gt.value) + 1
    assert int(execution["black_component_count"]) == 1
    assert int(execution["exterior_white_component_count"]) == 1
    assert str(execution["wall_color_label"]).endswith(f"[{execution['wall_color_hex']}]")
    assert str(execution["hole_color_label"]).endswith(f"[{execution['hole_color_hex']}]")
    assert str(execution["wall_color_label"]) in str(out.prompt)
    assert str(execution["hole_color_label"]) in str(out.prompt)

    holes = execution["holes"]
    assert len(holes) == 3
    assert execution["hole_witness_coords"] == evidence_coords
    assert all(int(hole["area"]) >= 1 for hole in holes)
    assert all(not any(coord[0] in (0, 6) or coord[1] in (0, 6) for coord in hole["coords"]) for hole in holes)
    assert [hole["witness_coord"] for hole in holes] == evidence_coords

    witness_ids = set(trace["witness_symbolic"]["ids"])
    evidence_entities = [
        entity
        for entity in trace["scene_ir"]["entities"]
        if bool(entity["attrs"].get("is_hole_witness"))
    ]
    assert {str(entity["entity_id"]) for entity in evidence_entities} == witness_ids


def test_tile_hole_count_caps_target_range_for_small_boards() -> None:
    task = TileHoleCountTask()
    out = task.generate(
        9117,
        params={
            "rows_min": 5,
            "rows_max": 5,
            "cols_min": 5,
            "cols_max": 5,
        },
        max_attempts=80,
    )
    execution = out.trace_payload["execution_trace"]

    assert execution["target_hole_count_range"] == [1, 1]
    assert int(execution["target_hole_count"]) == 1
    assert int(out.answer_gt.value) == 1


def test_tile_hole_count_is_deterministic() -> None:
    task = TileHoleCountTask()
    params = {
        "rows_min": 3,
        "rows_max": 7,
        "cols_min": 3,
        "cols_max": 7,
    }
    out_a = task.generate(99171, params=params, max_attempts=80)
    out_b = task.generate(99171, params=params, max_attempts=80)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"]["holes"] == out_b.trace_payload["execution_trace"]["holes"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.size == out_b.image.size
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_tile_hole_count_prompt_example_matches_contract() -> None:
    task = TileHoleCountTask()
    out = task.generate(9129, params={}, max_attempts=80)
    example = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert example == {"evidence": [[2, 2], [4, 4]], "answer": 2}
