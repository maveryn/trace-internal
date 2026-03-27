"""Behavior tests for tile pattern tasks."""

from __future__ import annotations

import json

from trace.tasks.tile.pattern_match3_run_count import TileMatch3RunCountTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_tile_match3_run_count_rows_outputs_expected_contract() -> None:
    task = TileMatch3RunCountTask()
    out = task.generate(
        7701,
        params={
            "task_variant": "rows",
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

    assert str(out.task_variant) == "rows"
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
    assert trace["projected_evidence"]["grid_point_set"] == evidence_coords
    assert int(out.answer_gt.value) == len(execution["qualifying_runs"])
    assert execution["line_axis"] == "rows"
    assert int(execution["run_length"]) == 3
    assert execution["target_qualifying_line_count_range"] == [1, 4]
    assert int(out.answer_gt.value) == int(execution["target_qualifying_line_count"])
    assert str(execution["query_color_label"]).endswith(f"[{execution['query_color_hex']}]")
    assert str(execution["query_color_label"]) in str(out.prompt)

    assert len(execution["qualifying_line_indices"]) == int(out.answer_gt.value)
    assert execution["qualifying_line_indices"] == sorted(execution["qualifying_line_indices"])
    flattened = [coord for run in execution["qualifying_runs"] for coord in run["coords"]]
    assert sorted(flattened) == evidence_coords
    assert all(len(run["coords"]) == 3 for run in execution["qualifying_runs"])
    assert all(len(run["ids"]) == 3 for run in execution["qualifying_runs"])
    assert all(run["line_index"] == run["coords"][0][0] for run in execution["qualifying_runs"])

    witness_ids = set(trace["witness_symbolic"]["ids"])
    evidence_entities = [
        entity
        for entity in trace["scene_ir"]["entities"]
        if bool(entity["attrs"].get("is_canonical_run_evidence"))
    ]
    assert {str(entity["entity_id"]) for entity in evidence_entities} == witness_ids


def test_tile_match3_run_count_cols_caps_target_range_for_small_boards() -> None:
    task = TileMatch3RunCountTask()
    out = task.generate(
        7717,
        params={
            "task_variant": "cols",
            "rows_min": 3,
            "rows_max": 3,
            "cols_min": 4,
            "cols_max": 4,
            "_sampling_index": 0,
        },
        max_attempts=40,
    )
    execution = out.trace_payload["execution_trace"]

    assert str(out.task_variant) == "cols"
    assert execution["line_axis"] == "columns"
    assert execution["target_qualifying_line_count_range"] == [1, 4]
    assert int(execution["target_qualifying_line_count"]) == 1
    assert int(out.answer_gt.value) == 1


def test_tile_match3_run_count_is_deterministic() -> None:
    task = TileMatch3RunCountTask()
    params = {
        "rows_min": 3,
        "rows_max": 7,
        "cols_min": 3,
        "cols_max": 7,
        "palette_size_min": 2,
        "palette_size_max": 3,
    }
    out_a = task.generate(99137, params=params, max_attempts=40)
    out_b = task.generate(99137, params=params, max_attempts=40)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"]["qualifying_runs"] == out_b.trace_payload["execution_trace"]["qualifying_runs"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.size == out_b.image.size
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_tile_match3_run_count_prompt_examples_match_variant_contract() -> None:
    task = TileMatch3RunCountTask()
    out_rows = task.generate(7729, params={"task_variant": "rows"}, max_attempts=40)
    out_cols = task.generate(7731, params={"task_variant": "cols"}, max_attempts=40)

    rows_example = _extract_prompt_json_example(out_rows.prompt_variants["answer_and_evidence"])
    cols_example = _extract_prompt_json_example(out_cols.prompt_variants["answer_and_evidence"])

    assert rows_example == {"evidence": [[0, 1], [0, 2], [0, 3], [2, 0], [2, 1], [2, 2]], "answer": 2}
    assert cols_example == {"evidence": [[0, 1], [0, 3], [1, 1], [1, 3], [2, 1], [2, 3]], "answer": 2}
