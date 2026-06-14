"""Surface-fixture dataset builders for count-style objectives."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.seed import spawn_rng

from .layout import edge_neighbors, grid_for_total, layout_cells, resolve_repeated_layout_style, target_ids_from_indices
from .rendering import layout_surface_element_grid
from .sampling import resolve_color, resolve_int_support, sample_indices
from .state import (
    ELEMENT_DISPLAY_NAME,
    ELEMENT_PLURAL,
    SEMANTIC_COLOR_SUPPORT,
    STATE_DISPLAY_NAME,
    STATE_SUPPORT_BY_SCENE_VARIANT,
    SURFACE_FIXTURE_DISPLAY_NAME,
)


def base_surface_data(
    *,
    scene_variant: str,
    element_type: str,
    answer_value: int,
    target_element_ids: Sequence[str],
    surface_cells: Sequence[Mapping[str, Any]],
    rows: int,
    cols: int,
    layout_style: str,
    solver_trace: Mapping[str, Any],
    extra: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build the scene dataset consumed by the renderer and output assembly."""

    data: Dict[str, Any] = {
        "scene_variant": str(scene_variant),
        "fixture_display_name": str(SURFACE_FIXTURE_DISPLAY_NAME[str(scene_variant)]),
        "target_element_type": str(element_type),
        "target_element_name": str(ELEMENT_DISPLAY_NAME[str(element_type)]),
        "target_element_plural": str(ELEMENT_PLURAL[str(element_type)]),
        "answer_value": int(answer_value),
        "target_element_ids": list(str(element_id) for element_id in target_element_ids),
        "surface_cells": [dict(cell) for cell in surface_cells],
        "layout_rows": int(rows),
        "layout_columns": int(cols),
        "layout_style": str(layout_style),
        "surface_world_corners": [
            [-2.0, 1.35, 2.55],
            [2.0, 1.35, 2.55],
            [2.0, 1.35, 0.15],
            [-2.0, 1.35, 0.15],
        ],
        "solver_trace": dict(solver_trace),
    }
    if extra:
        data.update(dict(extra))
    data["target_count"] = int(len([cell for cell in surface_cells if bool(cell.get("present", True))]))
    return data


def build_repeated_surface_data(
    *,
    namespace: str,
    scene_variant: str,
    element_type: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, float]]:
    """Create a fixture with one repeated element type to count."""

    count, probabilities = resolve_int_support(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.target_count",
        min_key="target_count_min",
        max_key="target_count_max",
        default_min=8,
        default_max=24,
        explicit_keys=("target_count", "element_count"),
        lower_bound=4,
        upper_bound=32,
    )
    rows, cols = layout_surface_element_grid(int(count))
    layout_family, layout_style, layout_family_probabilities, layout_style_probabilities = resolve_repeated_layout_style(
        scene_variant=str(scene_variant),
        rng=spawn_rng(int(instance_seed), f"{namespace}.layout_style"),
        params=params,
    )
    rng = spawn_rng(int(instance_seed), f"{namespace}.cells")
    indices = list(range(int(count)))
    cells = layout_cells(
        scene_variant=str(scene_variant),
        element_type=str(element_type),
        rows=int(rows),
        cols=int(cols),
        present_indices=indices,
        target_indices=indices,
        rng=rng,
        layout_style=layout_style,
    )
    dataset = base_surface_data(
        scene_variant=str(scene_variant),
        element_type=str(element_type),
        answer_value=int(count),
        target_element_ids=target_ids_from_indices(cells, indices),
        surface_cells=cells,
        rows=int(rows),
        cols=int(cols),
        layout_style=layout_style,
        solver_trace={
            "count_predicate": "element_type == target_element_type",
            "target_element_type": str(element_type),
            "target_element_plural": str(ELEMENT_PLURAL[str(element_type)]),
            "target_count": int(count),
            "element_count": int(count),
            "layout_family": str(layout_family),
            "layout_family_probabilities": dict(layout_family_probabilities),
            "layout_style": str(layout_style),
            "layout_style_probabilities": dict(layout_style_probabilities),
            "unique_integer_answer": True,
        },
        extra={
            "layout_family": str(layout_family),
            "layout_family_probabilities": dict(layout_family_probabilities),
            "layout_style_probabilities": dict(layout_style_probabilities),
        },
    )
    return dataset, dict(probabilities)


def build_color_surface_data(
    *,
    namespace: str,
    scene_variant: str,
    element_type: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, float]]:
    """Create a fixture where only a target color subset is counted."""

    target_count, target_probabilities = resolve_int_support(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.target_count",
        min_key="target_count_min",
        max_key="target_count_max",
        default_min=3,
        default_max=10,
        explicit_keys=("target_count", "answer_count"),
        lower_bound=1,
        upper_bound=16,
    )
    distractor_count, _ = resolve_int_support(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.distractor_count",
        min_key="distractor_count_min",
        max_key="distractor_count_max",
        default_min=5,
        default_max=12,
        explicit_keys=("distractor_count",),
        lower_bound=1,
        upper_bound=24,
    )
    total = int(target_count) + int(distractor_count)
    rows, cols = grid_for_total(total)
    total_slots = int(rows) * int(cols)
    rng = spawn_rng(int(instance_seed), f"{namespace}.cells")
    all_indices = list(range(total_slots))
    present_indices = sample_indices(rng, all_indices, total)
    target_indices = sample_indices(rng, present_indices, target_count)
    target_color = resolve_color(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.target_color",
        explicit_key="target_color_name",
    )
    other_colors = [color for color in SEMANTIC_COLOR_SUPPORT if color != target_color]
    color_by_index: Dict[int, str] = {}
    target_set = set(target_indices)
    for index in present_indices:
        color_by_index[int(index)] = str(target_color if int(index) in target_set else other_colors[int(rng.randrange(len(other_colors)))])
    layout_style = "variable_grid" if str(scene_variant) in {"brick_wall", "paver_floor", "mailbox_bank"} else "uniform_grid"
    cells = layout_cells(
        scene_variant=str(scene_variant),
        element_type=str(element_type),
        rows=int(rows),
        cols=int(cols),
        present_indices=present_indices,
        target_indices=target_indices,
        rng=rng,
        layout_style=layout_style,
        color_by_index=color_by_index,
    )
    dataset = base_surface_data(
        scene_variant=str(scene_variant),
        element_type=str(element_type),
        answer_value=int(target_count),
        target_element_ids=target_ids_from_indices(cells, target_indices),
        surface_cells=cells,
        rows=int(rows),
        cols=int(cols),
        layout_style=layout_style,
        solver_trace={
            "count_predicate": "element_type == target_element_type and color_name == target_color_name",
            "target_color_name": str(target_color),
            "target_count": int(target_count),
            "distractor_count": int(distractor_count),
            "unique_integer_answer": True,
        },
        extra={"target_color_name": str(target_color)},
    )
    return dataset, dict(target_probabilities)


def build_state_surface_data(
    *,
    namespace: str,
    scene_variant: str,
    element_type: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, float]]:
    """Create a fixture where one visible element state is counted."""

    target_count, target_probabilities = resolve_int_support(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.target_count",
        min_key="target_count_min",
        max_key="target_count_max",
        default_min=2,
        default_max=8,
        explicit_keys=("target_count", "answer_count"),
        lower_bound=1,
        upper_bound=14,
    )
    distractor_count, _ = resolve_int_support(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.distractor_count",
        min_key="distractor_count_min",
        max_key="distractor_count_max",
        default_min=5,
        default_max=12,
        explicit_keys=("distractor_count",),
        lower_bound=1,
        upper_bound=24,
    )
    state_support = STATE_SUPPORT_BY_SCENE_VARIANT[str(scene_variant)]
    explicit = params.get("target_state")
    if explicit is not None:
        target_state = str(explicit)
        if target_state not in set(state_support):
            raise ValueError(f"unsupported target_state for {scene_variant}: {target_state}")
    else:
        rng_state = spawn_rng(int(instance_seed), f"{namespace}.target_state")
        target_state = str(state_support[int(rng_state.randrange(len(state_support)))])
    total = int(target_count) + int(distractor_count)
    rows, cols = grid_for_total(total)
    total_slots = int(rows) * int(cols)
    rng = spawn_rng(int(instance_seed), f"{namespace}.cells")
    present_indices = sample_indices(rng, list(range(total_slots)), total)
    target_indices = sample_indices(rng, present_indices, target_count)
    other_states = [state for state in state_support if state != target_state]
    state_by_index: Dict[int, str] = {}
    target_set = set(target_indices)
    for index in present_indices:
        state_by_index[int(index)] = str(
            target_state if int(index) in target_set else other_states[int(rng.randrange(len(other_states)))]
        )
    color_by_index = {int(index): str(SEMANTIC_COLOR_SUPPORT[int(rng.randrange(len(SEMANTIC_COLOR_SUPPORT)))]) for index in present_indices}
    cells = layout_cells(
        scene_variant=str(scene_variant),
        element_type=str(element_type),
        rows=int(rows),
        cols=int(cols),
        present_indices=present_indices,
        target_indices=target_indices,
        rng=rng,
        layout_style="uniform_grid",
        color_by_index=color_by_index,
        state_by_index=state_by_index,
    )
    dataset = base_surface_data(
        scene_variant=str(scene_variant),
        element_type=str(element_type),
        answer_value=int(target_count),
        target_element_ids=target_ids_from_indices(cells, target_indices),
        surface_cells=cells,
        rows=int(rows),
        cols=int(cols),
        layout_style="uniform_grid",
        solver_trace={
            "count_predicate": "element_type == target_element_type and state == target_state",
            "target_state": str(target_state),
            "target_state_label": str(STATE_DISPLAY_NAME[str(target_state)]),
            "target_count": int(target_count),
            "distractor_count": int(distractor_count),
            "unique_integer_answer": True,
        },
        extra={
            "target_state": str(target_state),
            "target_state_label": str(STATE_DISPLAY_NAME[str(target_state)]),
        },
    )
    return dataset, dict(target_probabilities)


def build_scoped_color_surface_data(
    *,
    namespace: str,
    scene_variant: str,
    element_type: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, float]]:
    """Create a row/column scoped color-count fixture."""

    target_count, target_probabilities = resolve_int_support(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.target_count",
        min_key="target_count_min",
        max_key="target_count_max",
        default_min=1,
        default_max=6,
        explicit_keys=("target_count", "answer_count"),
        lower_bound=1,
        upper_bound=10,
    )
    rng = spawn_rng(int(instance_seed), f"{namespace}.cells")
    rows = int(params.get("layout_rows", 4 + int(rng.randrange(3))))
    cols = int(params.get("layout_columns", 4 + int(rng.randrange(3))))
    axis = str(params.get("scope_axis", ("row", "column")[int(rng.randrange(2))]))
    if axis not in {"row", "column"}:
        raise ValueError(f"unsupported scope_axis: {axis}")
    scope_len = cols if axis == "row" else rows
    if int(target_count) > int(scope_len):
        raise ValueError(f"target_count {target_count} exceeds {axis} length {scope_len}")
    scope_index = int(params.get("scope_index", int(rng.randrange(rows if axis == "row" else cols))))
    total_slots = int(rows) * int(cols)
    all_indices = list(range(total_slots))
    if axis == "row":
        scope_indices = [scope_index * cols + col for col in range(cols)]
        scope_phrase = f"row {scope_index + 1}"
    else:
        scope_indices = [row * cols + scope_index for row in range(rows)]
        scope_phrase = f"column {scope_index + 1}"
    target_indices = sample_indices(rng, scope_indices, int(target_count))
    target_color = resolve_color(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.target_color",
        explicit_key="target_color_name",
    )
    other_colors = [color for color in SEMANTIC_COLOR_SUPPORT if color != target_color]
    outside_same_color_count = min(int(rng.randrange(1, 4)), max(0, total_slots - len(scope_indices)))
    outside_indices = [index for index in all_indices if index not in set(scope_indices)]
    outside_same_color = set(sample_indices(rng, outside_indices, outside_same_color_count))
    target_set = set(target_indices)
    color_by_index: Dict[int, str] = {}
    for index in all_indices:
        if int(index) in target_set or int(index) in outside_same_color:
            color_by_index[int(index)] = str(target_color)
        else:
            color_by_index[int(index)] = str(other_colors[int(rng.randrange(len(other_colors)))])
    layout_style = "variable_grid" if str(scene_variant) in {"brick_wall", "paver_floor"} else "uniform_grid"
    cells = layout_cells(
        scene_variant=str(scene_variant),
        element_type=str(element_type),
        rows=int(rows),
        cols=int(cols),
        present_indices=all_indices,
        target_indices=target_indices,
        rng=rng,
        layout_style=layout_style,
        color_by_index=color_by_index,
    )
    dataset = base_surface_data(
        scene_variant=str(scene_variant),
        element_type=str(element_type),
        answer_value=int(target_count),
        target_element_ids=target_ids_from_indices(cells, target_indices),
        surface_cells=cells,
        rows=int(rows),
        cols=int(cols),
        layout_style=layout_style,
        solver_trace={
            "count_predicate": "scope_match and color_name == target_color_name",
            "scope_axis": str(axis),
            "scope_index": int(scope_index),
            "scope_phrase": str(scope_phrase),
            "target_color_name": str(target_color),
            "target_count": int(target_count),
            "outside_same_color_distractor_count": int(len(outside_same_color)),
            "unique_integer_answer": True,
        },
        extra={
            "scope_axis": str(axis),
            "scope_index": int(scope_index),
            "scope_phrase": str(scope_phrase),
            "target_color_name": str(target_color),
        },
    )
    return dataset, dict(target_probabilities)


def build_missing_surface_data(
    *,
    namespace: str,
    scene_variant: str,
    element_type: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, float]]:
    """Create a fixture grid with absent positions as the counted set."""

    missing_count, probabilities = resolve_int_support(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.missing_count",
        min_key="missing_count_min",
        max_key="missing_count_max",
        default_min=2,
        default_max=8,
        explicit_keys=("missing_count", "target_count", "answer_count"),
        lower_bound=1,
        upper_bound=12,
    )
    total_slots, _ = resolve_int_support(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.total_slots",
        min_key="total_slot_count_min",
        max_key="total_slot_count_max",
        default_min=12,
        default_max=24,
        explicit_keys=("total_slots", "cell_count"),
        lower_bound=int(missing_count) + 2,
        upper_bound=36,
    )
    rows, cols = grid_for_total(int(total_slots))
    total_grid_slots = int(rows) * int(cols)
    rng = spawn_rng(int(instance_seed), f"{namespace}.cells")
    all_indices = list(range(total_grid_slots))
    missing_indices = sample_indices(rng, all_indices, int(missing_count))
    present_indices = [index for index in all_indices if index not in set(missing_indices)]
    color_by_index = {int(index): str(SEMANTIC_COLOR_SUPPORT[int(rng.randrange(len(SEMANTIC_COLOR_SUPPORT)))]) for index in present_indices}
    layout_style = "brick_grid" if str(scene_variant) == "brick_wall" else "uniform_grid"
    cells = layout_cells(
        scene_variant=str(scene_variant),
        element_type=str(element_type),
        rows=int(rows),
        cols=int(cols),
        present_indices=present_indices,
        target_indices=missing_indices,
        rng=rng,
        layout_style=layout_style,
        color_by_index=color_by_index,
        include_absent=True,
    )
    dataset = base_surface_data(
        scene_variant=str(scene_variant),
        element_type=str(element_type),
        answer_value=int(missing_count),
        target_element_ids=target_ids_from_indices(cells, missing_indices),
        surface_cells=cells,
        rows=int(rows),
        cols=int(cols),
        layout_style=layout_style,
        solver_trace={
            "count_predicate": "present == false",
            "missing_count": int(missing_count),
            "total_slot_count": int(total_grid_slots),
            "unique_integer_answer": True,
        },
        extra={"missing_count": int(missing_count), "total_slot_count": int(total_grid_slots)},
    )
    return dataset, dict(probabilities)


def build_adjacent_surface_data(
    *,
    namespace: str,
    scene_variant: str,
    element_type: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, float]]:
    """Create a fixture where neighbors of one reference cell are counted."""

    answer_count, probabilities = resolve_int_support(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.answer_count",
        min_key="target_count_min",
        max_key="target_count_max",
        default_min=2,
        default_max=4,
        explicit_keys=("target_count", "answer_count", "neighbor_count"),
        lower_bound=1,
        upper_bound=4,
    )
    rng = spawn_rng(int(instance_seed), f"{namespace}.cells")
    rows = int(params.get("layout_rows", 4 + int(rng.randrange(2))))
    cols = int(params.get("layout_columns", 5 + int(rng.randrange(2))))
    candidates = [index for index in range(rows * cols) if len(edge_neighbors(index, rows, cols)) >= int(answer_count)]
    if not candidates:
        raise ValueError(f"no reference cells with at least {answer_count} edge-neighbors")
    reference_index = int(params.get("reference_index", candidates[int(rng.randrange(len(candidates)))]))
    neighbor_candidates = edge_neighbors(reference_index, rows, cols)
    if len(neighbor_candidates) < int(answer_count):
        raise ValueError(f"reference_index {reference_index} has {len(neighbor_candidates)} edge-neighbors")
    target_indices = sample_indices(rng, neighbor_candidates, int(answer_count))
    omitted_neighbor_indices = [index for index in neighbor_candidates if int(index) not in set(target_indices)]
    reference_color = resolve_color(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.reference_color",
        explicit_key="reference_color_name",
    )
    other_colors = [color for color in SEMANTIC_COLOR_SUPPORT if color != reference_color]
    color_by_index = {
        int(index): (str(reference_color) if int(index) == int(reference_index) else str(other_colors[int(rng.randrange(len(other_colors)))]))
        for index in range(rows * cols)
    }
    cells = layout_cells(
        scene_variant=str(scene_variant),
        element_type=str(element_type),
        rows=int(rows),
        cols=int(cols),
        present_indices=[index for index in range(rows * cols) if int(index) not in set(omitted_neighbor_indices)],
        target_indices=target_indices,
        rng=rng,
        layout_style="uniform_grid",
        color_by_index=color_by_index,
        reference_index=int(reference_index),
    )
    reference_element_id = next(
        str(cell["element_id"])
        for cell in cells
        if int(cell["flat_index"]) == int(reference_index)
    )
    dataset = base_surface_data(
        scene_variant=str(scene_variant),
        element_type=str(element_type),
        answer_value=int(answer_count),
        target_element_ids=target_ids_from_indices(cells, target_indices),
        surface_cells=cells,
        rows=int(rows),
        cols=int(cols),
        layout_style="uniform_grid",
        solver_trace={
            "count_predicate": "shares an edge with reference cell",
            "reference_index": int(reference_index),
            "reference_color_name": str(reference_color),
            "target_count": int(answer_count),
            "omitted_edge_neighbor_count": int(len(omitted_neighbor_indices)),
            "unique_integer_answer": True,
        },
        extra={
            "reference_index": int(reference_index),
            "reference_color_name": str(reference_color),
            "reference_element_id": str(reference_element_id),
        },
    )
    return dataset, dict(probabilities)


__all__ = [
    "base_surface_data",
    "build_adjacent_surface_data",
    "build_color_surface_data",
    "build_missing_surface_data",
    "build_repeated_surface_data",
    "build_scoped_color_surface_data",
    "build_state_surface_data",
]
