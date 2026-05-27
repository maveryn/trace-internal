"""Contract tests for the puzzle spatial solid-view counting task."""

from __future__ import annotations

from collections import Counter

import pytest

from trace.core.seed import hash64
from trace.tasks import TASK_REGISTRY
from trace.tasks.puzzles.shared.solid_view_query import SolidViewCountGenerator, _resolve_axes
from trace.tasks.puzzles.shared.solid_view_scene import CubeStack, projected_view_cells, view_grid_dimensions
from trace.tasks.puzzles.spatial.cube_structure_count import (
    PuzzlesSpatialCubeProjectionConsistencyLabelTask,
    PuzzlesSpatialCubeProjectionMatchLabelTask,
    PuzzlesSpatialCubeVisibleProjectionCountTask,
)


TASK_ID = "task_puzzles__voxel_cube__cube_visible_projection_count"
PROJECTION_MATCH_TASK_ID = "task_puzzles__voxel_cube__cube_projection_match_label"
PROJECTION_CONSISTENCY_TASK_ID = "task_puzzles__voxel_cube__cube_projection_consistency_label"
INTERNAL_TASK_KEY = "puzzles_spatial_cube_structure_internal"


def test_puzzles_spatial_visible_cube_count_is_registered_under_split_task() -> None:
    task_cls = TASK_REGISTRY[TASK_ID]
    assert task_cls is PuzzlesSpatialCubeVisibleProjectionCountTask
    task = task_cls()
    assert task.domain == "puzzles"
    assert task.task_group == "spatial"


def test_puzzles_spatial_projection_match_is_registered_under_cube_voxel_scene() -> None:
    task_cls = TASK_REGISTRY[PROJECTION_MATCH_TASK_ID]
    assert task_cls is PuzzlesSpatialCubeProjectionMatchLabelTask
    task = task_cls()
    assert task.domain == "puzzles"
    assert task.task_group == "spatial"


def test_puzzles_spatial_projection_consistency_is_registered_under_cube_voxel_scene() -> None:
    task_cls = TASK_REGISTRY[PROJECTION_CONSISTENCY_TASK_ID]
    assert task_cls is PuzzlesSpatialCubeProjectionConsistencyLabelTask
    task = task_cls()
    assert task.domain == "puzzles"
    assert task.task_group == "spatial"


def test_puzzles_spatial_visible_cube_count_split_wrapper_rewrites_public_contract() -> None:
    out = PuzzlesSpatialCubeVisibleProjectionCountTask().generate(
        23291,
        params={"view_direction": "front", "target_count": 4},
        max_attempts=60,
    )

    assert str(out.query_id) == "default"
    assert str(out.query_id) == "visible_cube_count"
    assert str(out.scene_id) == "voxel_cube"
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 4
    assert out.evidence_gt.type == "bbox_set"
    assert str(out.trace_payload["query_spec"]["query_id"]) == "default"
    assert str(out.trace_payload["query_spec"]["query_id"]) == "visible_cube_count"
    assert str(out.trace_payload["execution_trace"]["query_id"]) == "default"
    assert str(out.trace_payload["execution_trace"]["query_id"]) == "visible_cube_count"
    assert str(out.trace_payload["execution_trace"]["view_direction"]) == "front"
    assert str(out.trace_payload["execution_trace"]["internal_query_id"]) == "front_view_visible_count"
    assert 50 <= int(out.trace_payload["render_map"]["stack_voxel_scale_percent"]) <= 100


def test_puzzles_spatial_projection_match_split_wrapper_rewrites_public_contract() -> None:
    out = PuzzlesSpatialCubeProjectionMatchLabelTask().generate(
        23292,
        params={"view_direction": "right", "target_count": 4, "projection_match_option_count_min": 5, "projection_match_option_count_max": 5},
        max_attempts=80,
    )

    assert str(out.query_id) == "default"
    assert str(out.query_id) == "projection_match_label"
    assert str(out.scene_id) == "voxel_cube"
    assert out.answer_gt.type == "string"
    assert str(out.answer_gt.value) in set("ABCDE")
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 1
    assert str(out.trace_payload["query_spec"]["query_id"]) == "default"
    assert str(out.trace_payload["query_spec"]["query_id"]) == "projection_match_label"
    assert str(out.trace_payload["execution_trace"]["query_id"]) == "default"
    assert str(out.trace_payload["execution_trace"]["query_id"]) == "projection_match_label"
    assert str(out.trace_payload["execution_trace"]["view_direction"]) == "right"
    assert str(out.trace_payload["execution_trace"]["internal_query_id"]) == "right_view_visible_count"
    assert str(out.trace_payload["execution_trace"]["answer_label"]) == str(out.answer_gt.value)
    option_cells = out.trace_payload["execution_trace"]["option_cells"]
    correct_cells = out.trace_payload["execution_trace"]["correct_projection_cells"]
    assert option_cells[str(out.answer_gt.value)] == correct_cells
    assert 50 <= int(out.trace_payload["render_map"]["stack_voxel_scale_percent"]) <= 100


@pytest.mark.parametrize(
    "consistency_query",
    ("inconsistent_projection_label", "candidate_stack_from_views_label"),
)
def test_puzzles_spatial_projection_consistency_split_wrapper_rewrites_public_contract(consistency_query: str) -> None:
    out = PuzzlesSpatialCubeProjectionConsistencyLabelTask().generate(
        23293,
        params={
            "consistency_query": consistency_query,
            "projection_consistency_option_count_min": 5,
            "projection_consistency_option_count_max": 5,
        },
        max_attempts=100,
    )

    assert str(out.query_id) == "default"
    assert str(out.query_id) == "projection_consistency_label"
    assert str(out.scene_id) == "voxel_cube"
    assert out.answer_gt.type == "string"
    assert str(out.answer_gt.value) in set("ABCDE")
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 1
    assert str(out.trace_payload["query_spec"]["query_id"]) == "default"
    assert str(out.trace_payload["query_spec"]["query_id"]) == "projection_consistency_label"
    assert str(out.trace_payload["execution_trace"]["query_id"]) == "default"
    assert str(out.trace_payload["execution_trace"]["query_id"]) == "projection_consistency_label"
    assert str(out.trace_payload["execution_trace"]["consistency_query"]) == consistency_query
    assert str(out.trace_payload["execution_trace"]["answer_label"]) == str(out.answer_gt.value)
    assert int(out.trace_payload["execution_trace"]["option_count"]) == 5

    render_map = out.trace_payload["render_map"]
    execution = out.trace_payload["execution_trace"]
    answer_label = str(out.answer_gt.value)
    if consistency_query == "inconsistent_projection_label":
        assert 50 <= int(render_map["stack_voxel_scale_percent"]) <= 100
        heights = {
            (int(item["x"]), int(item["y"])): int(item["height"])
            for item in execution["reference_stack_heights"]
        }
        stack = CubeStack(
            width=int(execution["stack_width"]),
            depth=int(execution["stack_depth"]),
            heights=heights,
        )
        query_id = str(render_map["panel_query_by_label"][answer_label])
        shown_cells = sorted(tuple(int(value) for value in cell) for cell in render_map["option_cells"][answer_label])
        expected_cells = sorted(projected_view_cells(stack, query_id=query_id))
        assert shown_cells != expected_cells
    else:
        assert render_map["option_stack_heights"][answer_label] == render_map["reference_stack_heights"]
        scales = {str(label): int(value) for label, value in render_map["option_voxel_scale_percent"].items()}
        assert set(scales) == set("ABCDE")
        assert all(50 <= value <= 100 for value in scales.values())


@pytest.mark.parametrize(
    ("params", "expected_answer"),
    (
        ({"scene_variant": "cube_stack", "query_id": "top_view_visible_count", "target_count": 3}, 3),
        ({"scene_variant": "cube_stack", "query_id": "front_view_visible_count", "target_count": 4}, 4),
        ({"scene_variant": "cube_stack", "query_id": "right_view_visible_count", "target_count": 5}, 5),
    ),
)
def test_puzzles_spatial_solid_view_count_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
) -> None:
    out = SolidViewCountGenerator().generate(23301, params=params, max_attempts=60)
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == int(expected_answer)
    assert out.trace_payload["query_spec"]["params"]["query_id"] == out.query_id
    assert out.trace_payload["execution_trace"]["target_count"] == int(expected_answer)
    query_grid_dims = out.trace_payload["projected_evidence"]["query_grid_dimensions"]
    assert int(out.answer_gt.value) < int(query_grid_dims[0]) * int(query_grid_dims[1])

    query_panel_bbox = out.trace_payload["projected_evidence"]["query_panel_bbox"]
    for bbox in out.evidence_gt.value:
        assert len(bbox) == 4
        assert float(bbox[0]) >= float(query_panel_bbox[0])
        assert float(bbox[1]) >= float(query_panel_bbox[1])
        assert float(bbox[2]) <= float(query_panel_bbox[2])
        assert float(bbox[3]) <= float(query_panel_bbox[3])


def test_puzzles_spatial_solid_view_count_is_deterministic() -> None:
    params = {"scene_variant": "cube_stack", "query_id": "front_view_visible_count", "target_count": 4}
    task = SolidViewCountGenerator()
    out_a = task.generate(23311, params=params, max_attempts=60)
    out_b = task.generate(23311, params=params, max_attempts=60)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_puzzles_spatial_solid_view_count_rejects_unsupported_scene_variant() -> None:
    with pytest.raises(ValueError):
        SolidViewCountGenerator().generate(
            23321,
            params={"scene_variant": "cylinder_stack", "query_id": "top_view_visible_count"},
            max_attempts=20,
        )


def test_puzzles_spatial_solid_view_count_rejects_unsupported_query_id() -> None:
    with pytest.raises(ValueError):
        SolidViewCountGenerator().generate(
            23322,
            params={"scene_variant": "cube_stack", "query_id": "volume"},
            max_attempts=20,
        )


def test_front_view_grid_crops_to_occupied_projection_support() -> None:
    stack = CubeStack(
        width=3,
        depth=4,
        heights={
            (2, 0): 1,
            (2, 1): 2,
            (2, 2): 1,
            (2, 3): 1,
        },
    )

    assert projected_view_cells(stack, query_id="front_view_visible_count") == ((0, 0), (0, 1))
    assert view_grid_dimensions(stack, query_id="front_view_visible_count") == (1, 2)


@pytest.mark.parametrize(
    ("query_id", "expected_snippet"),
    (
        ("front_view_visible_count", "left vertical face"),
        ("right_view_visible_count", "right vertical face"),
    ),
)
def test_solid_view_prompts_clarify_front_and_right_conventions(
    query_id: str,
    expected_snippet: str,
) -> None:
    out = SolidViewCountGenerator().generate(
        23331,
        params={"scene_variant": "cube_stack", "query_id": query_id, "target_count": 4},
        max_attempts=60,
    )

    assert expected_snippet in out.prompt


def test_puzzles_spatial_solid_view_count_balances_target_counts_across_review_seed_stream() -> None:
    target_counts = Counter()

    for index in range(250):
        instance_seed = hash64(0, INTERNAL_TASK_KEY, index)
        resolved = _resolve_axes(int(instance_seed), params={})
        target_counts[int(resolved.target_count)] += 1

    assert set(target_counts.keys()) == {3, 4, 5, 6, 7}
    assert min(target_counts.values()) >= 30


def test_puzzles_spatial_solid_view_count_decouplesseeded_sampler_axes() -> None:
    per_query_id_counts: dict[str, Counter[int]] = {
        "top_view_visible_count": Counter(),
        "front_view_visible_count": Counter(),
        "right_view_visible_count": Counter(),
    }

    for index in range(100):
        instance_seed = hash64(0, INTERNAL_TASK_KEY, index)
        resolved = _resolve_axes(int(instance_seed), params={})
        per_query_id_counts[str(resolved.query_id)][int(resolved.target_count)] += 1

    assert sum(sum(counter.values()) for counter in per_query_id_counts.values()) == 100
    for query_id, counts in per_query_id_counts.items():
        assert set(counts.keys()) == {3, 4, 5, 6, 7}
        assert max(counts.values()) <= 7, query_id
