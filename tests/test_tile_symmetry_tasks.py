"""Behavior tests for tile symmetry tasks."""

from __future__ import annotations

import json

from trace.tasks.tile.symmetry.violation_count import TileSymmetryViolationCountTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_tile_symmetry_outputs_expected_contract() -> None:
    task = TileSymmetryViolationCountTask()
    out = task.generate(
        8801,
        params={
            "task_variant": "vertical",
            "rows_min": 5,
            "rows_max": 5,
            "cols_min": 5,
            "cols_max": 5,
            "palette_size_min": 3,
            "palette_size_max": 3,
            "target_violation_count_min": 2,
            "target_violation_count_max": 2,
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

    assert str(out.task_variant) == "vertical"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "grid_point_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert str(render["tiling_type"]) == "rectangular_tiling"
    assert int(render["rows"]) == 5
    assert int(render["cols"]) == 5
    assert out.image.size == (int(render["canvas_width_px"]), int(render["canvas_height_px"]))

    evidence_coords = [[int(point[0]), int(point[1])] for point in out.evidence_gt.value]
    assert evidence_coords == execution["violation_coords"]
    assert int(out.answer_gt.value) == 2
    assert int(out.answer_gt.value) == len(evidence_coords)
    assert execution["target_violation_count_range"] == [2, 2]
    assert execution["mirror_axis"] == "vertical"
    assert execution["counted_side"] == "right side"
    assert all(int(coord[1]) >= 3 for coord in evidence_coords)

    violating_entities = [
        entity
        for entity in trace["scene_ir"]["entities"]
        if bool(entity["attrs"]["is_violation"])
    ]
    assert len(violating_entities) == len(evidence_coords)
    assert all(bool(entity["attrs"]["is_counted_side"]) for entity in violating_entities)


def test_tile_symmetry_is_deterministic() -> None:
    task = TileSymmetryViolationCountTask()
    params = {
        "rows_min": 3,
        "rows_max": 7,
        "cols_min": 3,
        "cols_max": 7,
        "target_violation_count_min": 1,
        "target_violation_count_max": 10,
    }
    out_a = task.generate(8817, params=params, max_attempts=80)
    out_b = task.generate(8817, params=params, max_attempts=80)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["witness_symbolic"] == out_b.trace_payload["witness_symbolic"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.size == out_b.image.size
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_tile_symmetry_prompt_example_matches_contract() -> None:
    task = TileSymmetryViolationCountTask()
    out = task.generate(8833, params={}, max_attempts=80)
    example = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert list(example.keys()) == ["evidence", "answer"]
    assert example["evidence"] == [[0, 2], [1, 2]]
    assert int(example["answer"]) == 2
