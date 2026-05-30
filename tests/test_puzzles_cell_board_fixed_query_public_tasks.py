"""Contracts for fixed-query public cell-board tasks."""

from __future__ import annotations

import pytest

import trace.tasks  # noqa: F401 - ensures task modules register on import
from trace.tasks.puzzles.cell_board.shared.rectangular_board import SUPPORTED_CELL_BOARD_TILE_STYLES
from trace.tasks.registry import TASK_REGISTRY


_CELL_BOARD_PUBLIC_TASKS = [
    (
        "task_puzzles__cell_board__attribute_count",
        {"color_cell_count", "column_color_cell_count", "edge_color_cell_count", "row_color_cell_count"},
        {"point_set"},
    ),
    (
        "task_puzzles__cell_board__color_region_count",
        {"color_components", "largest_component_size"},
        {"point_set"},
    ),
    (
        "task_puzzles__cell_board__reachability_count",
        {"region_size", "reachable_target_count", "unreachable_target_count"},
        {"point_set"},
    ),
    ("task_puzzles__cell_board__path_distance", {"shortest_path", "min_distance"}, {"point_sequence"}),
    ("task_puzzles__cell_board__symmetry_violation_count", {"symmetry_violation_count"}, {"point_set"}),
]


@pytest.mark.parametrize(("task_id", "query_ids", "evidence_types"), _CELL_BOARD_PUBLIC_TASKS)
def test_cell_board_public_tasks_emit_query_id(
    task_id: str,
    query_ids: set[str],
    evidence_types: set[str],
) -> None:
    task = TASK_REGISTRY[task_id]()
    output = task.generate(12345, params={}, max_attempts=400)
    query_id = str(output.query_id)

    assert query_id in query_ids
    assert output.scene_id == "cell_board"
    assert output.evidence_gt.type in evidence_types

    for payload_key in ("query_spec", "execution_trace", "render_spec"):
        payload = output.trace_payload[payload_key]
        assert payload["query_id"] == query_id

    render_spec = output.trace_payload["render_spec"]
    assert render_spec["label_style"]["font"]["font_family"]
    assert render_spec["background_style"]["scene_style"]["board_label_font"]["font_family"] == render_spec["label_style"]["font"]["font_family"]
    board_style = render_spec["background_style"]["scene_style"]["cell_board"]
    assert board_style["tile_style"] in set(SUPPORTED_CELL_BOARD_TILE_STYLES)
    assert board_style["semantic_color_policy"]["tile_fill_colors_preserved"] is True
    assert board_style["semantic_color_policy"]["tile_geometry_preserved"] is True

    if "internal_query_id" in output.trace_payload["query_spec"]:
        assert output.trace_payload["query_spec"]["internal_query_id"] == query_id
    if "internal_query_id" in output.trace_payload["execution_trace"]:
        assert output.trace_payload["execution_trace"]["internal_query_id"] == query_id
    assert set(output.trace_payload["query_spec"]["query_id_probabilities"]) == query_ids

    relations = output.trace_payload["scene_ir"]["relations"]
    assert relations["query_id"] == query_id


@pytest.mark.parametrize(("task_id", "query_ids", "_evidence_types"), _CELL_BOARD_PUBLIC_TASKS)
def test_cell_board_public_tasks_accept_explicit_query_id(
    task_id: str,
    query_ids: set[str],
    _evidence_types: set[str],
) -> None:
    task = TASK_REGISTRY[task_id]()
    query_id = sorted(query_ids)[0]
    output = task.generate(12345, params={"query_id": query_id}, max_attempts=400)

    assert output.query_id == query_id
    assert output.trace_payload["query_spec"]["query_id"] == query_id
    assert output.trace_payload["query_spec"]["query_id_probabilities"] == {query_id: 1.0}


@pytest.mark.parametrize(
    ("query_id", "prompt_task_group", "prompt_bundle_id"),
    [
        ("region_size", "cell_board_reachability", "puzzles_cell_board_reachability_v0"),
        ("reachable_target_count", "cell_board_path", "puzzles_cell_board_path_v0"),
        ("unreachable_target_count", "cell_board_path", "puzzles_cell_board_path_v0"),
    ],
)
def test_cell_board_reachability_prompt_metadata_tracks_source_query(
    query_id: str,
    prompt_task_group: str,
    prompt_bundle_id: str,
) -> None:
    task = TASK_REGISTRY["task_puzzles__cell_board__reachability_count"]()
    output = task.generate(20260520, params={"query_id": query_id}, max_attempts=500)
    prompt_variant = output.trace_payload["query_spec"]["prompt_variant"]

    assert prompt_variant["prompt_domain"] == "puzzles"
    assert prompt_variant["prompt_task_group"] == prompt_task_group
    assert prompt_variant["prompt_bundle_id"] == prompt_bundle_id
