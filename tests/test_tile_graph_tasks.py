"""Behavior tests for tile graph tasks."""

from __future__ import annotations

import json

from trace.tasks.tile.graph.degree_count import TileGraphDegreeCountTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_tile_graph_degree_count_outputs_expected_contract() -> None:
    task = TileGraphDegreeCountTask()
    out = task.generate(
        9301,
        params={
            "rows_min": 7,
            "rows_max": 7,
            "cols_min": 7,
            "cols_max": 7,
            "palette_size_min": 3,
            "palette_size_max": 3,
            "target_degree_min": 1,
            "target_degree_max": 1,
            "target_answer_count_min": 2,
            "target_answer_count_max": 2,
            "short_side_px_min": 32,
            "short_side_px_max": 32,
            "aspect_ratio_min": 1.5,
            "aspect_ratio_max": 1.5,
        },
        max_attempts=120,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]

    assert str(out.task_variant) == "degree_count"
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
    assert int(out.answer_gt.value) == 2
    assert execution["matching_coords"] == evidence_coords
    assert execution["target_degree_range"] == [1, 1]
    assert int(execution["target_degree"]) == 1
    assert execution["target_answer_count_range"] == [2, 2]
    assert int(execution["target_answer_count"]) == 2
    assert str(execution["query_color_label"]).endswith(f"[{execution['query_color_hex']}]")
    assert str(execution["query_color_label"]) in str(out.prompt)

    degree_map = execution["same_color_degree_by_coord"]
    witness_ids = set(trace["witness_symbolic"]["ids"])
    assert all(int(degree_map[witness_id]) == 1 for witness_id in witness_ids)
    matching_entities = [
        entity
        for entity in trace["scene_ir"]["entities"]
        if bool(entity["attrs"].get("is_degree_match"))
    ]
    assert {str(entity["entity_id"]) for entity in matching_entities} == witness_ids


def test_tile_graph_degree_count_is_deterministic() -> None:
    task = TileGraphDegreeCountTask()
    params = {
        "rows_min": 3,
        "rows_max": 7,
        "cols_min": 3,
        "cols_max": 7,
        "palette_size_min": 2,
        "palette_size_max": 3,
    }
    out_a = task.generate(99181, params=params, max_attempts=120)
    out_b = task.generate(99181, params=params, max_attempts=120)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"]["matching_coords"] == out_b.trace_payload["execution_trace"]["matching_coords"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.size == out_b.image.size
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_tile_graph_degree_count_prompt_example_matches_contract() -> None:
    task = TileGraphDegreeCountTask()
    out = task.generate(9329, params={}, max_attempts=120)
    example = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert example == {"evidence": [[0, 1], [2, 2]], "answer": 2}
