"""Behavior tests for tile transition tasks."""

from __future__ import annotations

import json

from trace.tasks.tile.transition_gravity_max_drop import TileGravityMaxDropTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_tile_gravity_max_drop_outputs_expected_contract() -> None:
    task = TileGravityMaxDropTask()
    out = task.generate(
        8801,
        params={
            "rows_min": 5,
            "rows_max": 5,
            "cols_min": 4,
            "cols_max": 4,
            "short_side_px_min": 32,
            "short_side_px_max": 32,
            "aspect_ratio_min": 1.5,
            "aspect_ratio_max": 1.5
        },
        max_attempts=40,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]

    assert str(out.task_variant) == "gravity_max_drop"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "grid_point_path"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert str(render["tiling_type"]) == "rectangular_tiling"
    assert int(render["rows"]) == 5
    assert int(render["cols"]) == 4
    assert int(render["tile_width_px"]) != int(render["tile_height_px"])
    assert out.image.size == (int(render["canvas_width_px"]), int(render["canvas_height_px"]))

    evidence_path = [[int(point[0]), int(point[1])] for point in out.evidence_gt.value]
    assert evidence_path == execution["winner_path_coords"]
    assert len(evidence_path) == int(out.answer_gt.value) + 1
    assert evidence_path[0] == execution["winner_source_coord"]
    assert evidence_path[-1] == execution["winner_final_coord"]
    assert execution["target_max_drop_range"] == [1, 3]
    assert int(out.answer_gt.value) == int(execution["target_max_drop"])
    assert int(out.answer_gt.value) == int(execution["drops"][execution["winner_col"]])
    assert bool(execution["unique_max"]) is True
    assert str(execution["drop_color_label"]).endswith(f"[{execution['drop_color_hex']}]")
    assert str(execution["obstacle_color_label"]).endswith(f"[{execution['obstacle_color_hex']}]")
    assert str(execution["drop_color_label"]) in str(out.prompt)
    assert str(execution["obstacle_color_label"]) in str(out.prompt)

    winner_columns = [column for column in execution["columns"] if bool(column["is_winner"])]
    assert len(winner_columns) == 1
    assert int(winner_columns[0]["column"]) == int(execution["winner_col"])
    assert int(winner_columns[0]["drop_distance"]) == int(out.answer_gt.value)
    assert len(trace["witness_symbolic"]["ids"]) == len(evidence_path)
    assert trace["projected_evidence"]["grid_point_path"] == evidence_path

    winning_entities = [
        entity
        for entity in trace["scene_ir"]["entities"]
        if bool(entity["attrs"].get("is_winning_path"))
    ]
    assert {str(entity["entity_id"]) for entity in winning_entities} == set(trace["witness_symbolic"]["ids"])


def test_tile_gravity_max_drop_caps_target_range_for_small_rows() -> None:
    task = TileGravityMaxDropTask()
    out = task.generate(
        8817,
        params={
            "rows_min": 4,
            "rows_max": 4,
            "cols_min": 3,
            "cols_max": 3,
            "_sampling_index": 0,
        },
        max_attempts=40,
    )
    execution = out.trace_payload["execution_trace"]

    assert execution["target_max_drop_range"] == [1, 2]
    assert int(execution["target_max_drop"]) == 1
    assert int(out.answer_gt.value) == 1


def test_tile_gravity_max_drop_is_deterministic() -> None:
    task = TileGravityMaxDropTask()
    params = {
        "rows_min": 3,
        "rows_max": 7,
        "cols_min": 3,
        "cols_max": 7,
    }
    out_a = task.generate(99151, params=params, max_attempts=40)
    out_b = task.generate(99151, params=params, max_attempts=40)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"]["columns"] == out_b.trace_payload["execution_trace"]["columns"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.size == out_b.image.size
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_tile_gravity_max_drop_prompt_example_matches_contract() -> None:
    task = TileGravityMaxDropTask()
    out = task.generate(8829, params={}, max_attempts=40)
    example = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert example == {"evidence": [[0, 1], [1, 1], [2, 1]], "answer": 2}
