"""Behavior tests for cell-board symmetry tasks."""

from __future__ import annotations

import json

from trace.tasks.puzzles.cell_board.symmetry_violation_count import TileSymmetryViolationCountTask
from tests.cell_board_evidence_helpers import tile_coords_from_points, tile_ids_from_points


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


def test_cell_board_symmetry_outputs_expected_contract() -> None:
    task = TileSymmetryViolationCountTask()
    out = task.generate(
        8801,
        params={
            "query_id": "vertical",
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

    assert str(out.query_id) == "symmetry_violation_count"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "point_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert str(render["tiling_type"]) == "rectangular_tiling"
    assert int(render["rows"]) == 5
    assert int(render["cols"]) == 5
    assert out.image.size == (int(render["canvas_width_px"]), int(render["canvas_height_px"]))

    assert trace["projected_evidence"]["type"] == "point_set"
    assert trace["projected_evidence"]["point_set"] == out.evidence_gt.value
    assert trace["projected_evidence"]["pixel_point_set"] == out.evidence_gt.value
    evidence_coords = tile_coords_from_points(trace, out.evidence_gt.value)
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
    _assert_normalized_complexity(out)


def test_cell_board_symmetry_is_deterministic() -> None:
    task = TileSymmetryViolationCountTask()
    params = {
        "rows_min": 3,
        "rows_max": 7,
        "cols_min": 3,
        "cols_max": 7,
        "target_violation_count_min": 1,
        "target_violation_count_max": 8,
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


def test_cell_board_symmetry_prompt_example_matches_contract() -> None:
    task = TileSymmetryViolationCountTask()
    out = task.generate(8833, params={}, max_attempts=80)
    example = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert list(example.keys()) == ["evidence", "answer"]
    assert example["evidence"] == [[216, 120], [216, 168]]
    assert int(example["answer"]) == 2


def test_cell_board_symmetry_review_sampling_covers_answers_per_variant() -> None:
    task = TileSymmetryViolationCountTask()
    answers_by_axis: dict[str, set[int]] = {"vertical": set(), "horizontal": set()}
    for index in range(16):
        out = task.generate(
            8861 + index,
            params={
                "rows_min": 3,
                "rows_max": 7,
                "cols_min": 3,
                "cols_max": 7,
                "target_violation_count_min": 1,
                "target_violation_count_max": 8,
            },
            max_attempts=80,
        )
        axis = str(out.trace_payload["execution_trace"]["mirror_axis"])
        answers_by_axis[axis].add(int(out.answer_gt.value))

    assert all(answers_by_axis.values())
    assert answers_by_axis["vertical"].issubset(set(range(1, 9)))
    assert answers_by_axis["horizontal"].issubset(set(range(1, 9)))


def test_cell_board_symmetry_complexity_is_normalized_and_monotonic() -> None:
    task = TileSymmetryViolationCountTask()
    easy = task.generate(
        8841,
        params={
            "query_id": "vertical",
            "rows_min": 5,
            "rows_max": 5,
            "cols_min": 5,
            "cols_max": 5,
            "target_violation_count_min": 1,
            "target_violation_count_max": 1,
        },
        max_attempts=80,
    )
    hard = task.generate(
        8841,
        params={
            "query_id": "vertical",
            "rows_min": 5,
            "rows_max": 5,
            "cols_min": 5,
            "cols_max": 5,
            "target_violation_count_min": 5,
            "target_violation_count_max": 5,
        },
        max_attempts=80,
    )
    _assert_normalized_complexity(easy)
    _assert_normalized_complexity(hard)
    assert float(hard.complexity.complexity_components["reasoning_load"]) > float(
        easy.complexity.complexity_components["reasoning_load"]
    )
    assert float(hard.complexity.complexity_score) > float(easy.complexity.complexity_score)
