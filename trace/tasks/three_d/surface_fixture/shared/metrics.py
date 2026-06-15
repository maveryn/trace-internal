"""Surface-fixture dataset builders for count-style objectives."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.seed import spawn_rng

from .layout import grid_for_total, layout_cells, resolve_repeated_layout_style, target_ids_from_indices
from .rendering import layout_surface_element_grid
from .sampling import configured_int, resolve_color, resolve_int_support, sample_indices, uniform_int_probability_map
from .state import (
    ELEMENT_DISPLAY_NAME,
    ELEMENT_PLURAL,
    SEMANTIC_COLOR_SUPPORT,
    SURFACE_FIXTURE_DISPLAY_NAME,
    semantic_color_label,
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


def _resolve_active_colors(
    *,
    params: Mapping[str, Any],
    target_color: str,
    rng: Any,
) -> Tuple[str, ...]:
    explicit_colors = params.get("active_color_names", params.get("color_names"))
    if explicit_colors is not None:
        if not isinstance(explicit_colors, Sequence) or isinstance(explicit_colors, (str, bytes)):
            raise ValueError("active_color_names must be a sequence of color names")
        colors = tuple(str(color) for color in explicit_colors)
        if len(colors) != len(set(colors)):
            raise ValueError("active_color_names must be unique")
        if len(colors) < 2 or len(colors) > 4:
            raise ValueError("active_color_names must contain 2 to 4 colors")
        if str(target_color) not in set(colors):
            raise ValueError("active_color_names must include target_color_name")
        unsupported = [color for color in colors if color not in set(SEMANTIC_COLOR_SUPPORT)]
        if unsupported:
            raise ValueError(f"unsupported active color names: {unsupported}")
        return tuple(colors)

    color_count = int(params.get("active_color_count", params.get("color_count", 2 + int(rng.randrange(3)))))
    if color_count < 2 or color_count > 4:
        raise ValueError(f"active_color_count must be in 2..4, got {color_count}")
    other_colors = [color for color in SEMANTIC_COLOR_SUPPORT if str(color) != str(target_color)]
    rng.shuffle(other_colors)
    return tuple([str(target_color), *[str(color) for color in other_colors[: color_count - 1]]])


def _resolve_initial_color_counts(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    active_colors: Sequence[str],
    target_color: str,
    instance_seed: int,
    namespace: str,
    rng: Any,
) -> Tuple[Dict[str, int], Dict[str, float]]:
    """Bind the visible starting multicolor state while preserving target evidence.

    The key invariant for operation tasks is that `target_color` has a known
    positive initial count and every active distractor color is visible at least
    once, so later text operations can change color counts without changing the
    visual witness set.
    """

    raw_counts = params.get("initial_color_counts")
    if raw_counts is not None:
        if not isinstance(raw_counts, Mapping):
            raise ValueError("initial_color_counts must be a mapping from color name to count")
        counts = {str(color): int(raw_counts.get(str(color), 0)) for color in active_colors}
        if counts[str(target_color)] <= 0:
            raise ValueError("initial target color count must be positive")
        if any(int(count) <= 0 for count in counts.values()):
            raise ValueError("each active color must have at least one initial object")
        return counts, uniform_int_probability_map(range(1, 13), selected=int(counts[str(target_color)]))

    target_count, target_probabilities = resolve_int_support(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.initial_target_count",
        min_key="initial_target_count_min",
        max_key="initial_target_count_max",
        default_min=2,
        default_max=5,
        explicit_keys=("initial_target_count",),
        lower_bound=1,
        upper_bound=10,
    )
    minimum_total = int(target_count) + len(active_colors) - 1
    initial_total, _ = resolve_int_support(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.initial_total_count",
        min_key="initial_total_count_min",
        max_key="initial_total_count_max",
        default_min=8,
        default_max=14,
        explicit_keys=("initial_total_count", "total_count"),
        lower_bound=minimum_total,
        upper_bound=20,
    )
    counts = {str(color): 0 for color in active_colors}
    counts[str(target_color)] = int(target_count)
    other_colors = [str(color) for color in active_colors if str(color) != str(target_color)]
    for color in other_colors:
        counts[color] = 1
    remaining = int(initial_total) - int(target_count) - len(other_colors)
    for _ in range(max(0, int(remaining))):
        color = other_colors[int(rng.randrange(len(other_colors)))]
        counts[str(color)] += 1
    return counts, dict(target_probabilities)


def _coerce_operation_records(raw_operations: Any) -> list[Dict[str, Any]]:
    if not isinstance(raw_operations, Sequence) or isinstance(raw_operations, (str, bytes)):
        raise ValueError("operations must be a sequence")
    operations: list[Dict[str, Any]] = []
    for raw in raw_operations:
        if isinstance(raw, Mapping):
            action = str(raw.get("action", "")).lower()
            color_name = str(raw.get("color_name", raw.get("color", "")))
            count = int(raw.get("count", raw.get("amount", 0)))
        elif isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)) and len(raw) == 3:
            action = str(raw[0]).lower()
            color_name = str(raw[1])
            count = int(raw[2])
        else:
            raise ValueError("each operation must be a mapping or (action, color, count) triple")
        operations.append({"action": action, "color_name": color_name, "count": int(count)})
    return operations


def _apply_operation_sequence(
    *,
    initial_counts: Mapping[str, int],
    active_colors: Sequence[str],
    operations: Sequence[Mapping[str, Any]],
) -> Dict[str, int]:
    counts = {str(color): int(initial_counts[str(color)]) for color in active_colors}
    active_set = set(str(color) for color in active_colors)
    for operation in operations:
        action = str(operation["action"])
        color_name = str(operation["color_name"])
        amount = int(operation["count"])
        if action not in {"add", "remove"}:
            raise ValueError(f"unsupported operation action: {action}")
        if color_name not in active_set:
            raise ValueError(f"operation color {color_name!r} is not an active fixture color")
        if amount <= 0:
            raise ValueError("operation counts must be positive")
        if action == "add":
            counts[color_name] += int(amount)
        else:
            if counts[color_name] < int(amount):
                raise ValueError(f"cannot remove {amount} {color_name} elements from current count {counts[color_name]}")
            counts[color_name] -= int(amount)
    return counts


def _sample_operation_sequence(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    active_colors: Sequence[str],
    target_color: str,
    initial_counts: Mapping[str, int],
    instance_seed: int,
    namespace: str,
) -> Tuple[list[Dict[str, Any]], Dict[str, int], Dict[str, float]]:
    """Sample or validate the three text operations for the final-count program.

    The sequence is symbolic, not rendered. It must include a target-color
    operation, keep all color counts nonnegative, and change the final target
    count so this task remains distinct from direct colored-element counting.
    """

    amount_min = max(1, configured_int(params, gen_defaults, "operation_amount_min", 1))
    amount_max = max(amount_min, min(5, configured_int(params, gen_defaults, "operation_amount_max", 3)))
    final_min = max(0, configured_int(params, gen_defaults, "final_count_min", 1))
    final_max = max(final_min, min(20, configured_int(params, gen_defaults, "final_count_max", 9)))
    answer_probabilities = uniform_int_probability_map(range(int(final_min), int(final_max) + 1))
    if "operations" in params:
        operations = _coerce_operation_records(params["operations"])
        if len(operations) != 3:
            raise ValueError("surface-fixture operation tasks require exactly three operations")
        final_counts = _apply_operation_sequence(
            initial_counts=initial_counts,
            active_colors=active_colors,
            operations=operations,
        )
        final_target_count = int(final_counts[str(target_color)])
        if final_target_count == int(initial_counts[str(target_color)]):
            raise ValueError("target-color operations must change the target-color count")
        if final_target_count < int(final_min) or final_target_count > int(final_max):
            raise ValueError(f"final target count {final_target_count} outside configured support {final_min}..{final_max}")
        return operations, final_counts, uniform_int_probability_map(range(int(final_min), int(final_max) + 1), selected=final_target_count)

    rng = spawn_rng(int(instance_seed), f"{namespace}.operations")
    non_target_colors = [str(color) for color in active_colors if str(color) != str(target_color)]
    for _attempt in range(200):
        target_op_count = 2 if rng.random() < 0.45 else 1
        positions = list(range(3))
        rng.shuffle(positions)
        target_positions = set(positions[:target_op_count])
        colors = [
            str(target_color) if index in target_positions else non_target_colors[int(rng.randrange(len(non_target_colors)))]
            for index in range(3)
        ]
        current_counts = {str(color): int(initial_counts[str(color)]) for color in active_colors}
        operations: list[Dict[str, Any]] = []
        for color_name in colors:
            action = ("add", "remove")[int(rng.randrange(2))]
            if action == "remove" and int(current_counts[color_name]) < int(amount_min):
                action = "add"
            if action == "remove":
                max_amount = min(int(amount_max), int(current_counts[color_name]))
                amount = int(amount_min + int(rng.randrange(max_amount - amount_min + 1)))
                current_counts[color_name] -= int(amount)
            else:
                amount = int(amount_min + int(rng.randrange(amount_max - amount_min + 1)))
                current_counts[color_name] += int(amount)
            operations.append({"action": str(action), "color_name": str(color_name), "count": int(amount)})
        final_target_count = int(current_counts[str(target_color)])
        if final_target_count == int(initial_counts[str(target_color)]):
            continue
        if final_target_count < int(final_min) or final_target_count > int(final_max):
            continue
        return operations, current_counts, dict(answer_probabilities)
    raise ValueError("could not sample valid color operation sequence")


def _operation_phrase(
    operations: Sequence[Mapping[str, Any]],
    *,
    element_name: str,
    element_plural: str,
) -> str:
    phrases = []
    for operation in operations:
        amount = int(operation["count"])
        noun = str(element_name if amount == 1 else element_plural)
        color_label = semantic_color_label(str(operation["color_name"]))
        phrases.append(f"{operation['action']} {amount} {color_label} {noun}")
    return "; ".join(phrases)


def build_color_operation_surface_data(
    *,
    namespace: str,
    scene_variant: str,
    element_type: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, float]]:
    """Create a colored fixture plus three hypothetical add/remove operations."""

    target_color = resolve_color(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.target_color",
        explicit_key="target_color_name",
    )
    rng = spawn_rng(int(instance_seed), f"{namespace}.cells")
    active_colors = _resolve_active_colors(params=params, target_color=str(target_color), rng=rng)
    initial_counts, _initial_target_probabilities = _resolve_initial_color_counts(
        params=params,
        gen_defaults=gen_defaults,
        active_colors=active_colors,
        target_color=str(target_color),
        instance_seed=int(instance_seed),
        namespace=str(namespace),
        rng=rng,
    )
    operations, final_counts, answer_probabilities = _sample_operation_sequence(
        params=params,
        gen_defaults=gen_defaults,
        active_colors=active_colors,
        target_color=str(target_color),
        initial_counts=initial_counts,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    initial_total = int(sum(int(count) for count in initial_counts.values()))
    rows, cols = grid_for_total(initial_total)
    total_slots = int(rows) * int(cols)
    present_indices = sample_indices(rng, list(range(total_slots)), initial_total)
    color_sequence: list[str] = []
    for color in active_colors:
        color_sequence.extend([str(color)] * int(initial_counts[str(color)]))
    rng.shuffle(color_sequence)
    color_by_index = {int(index): str(color_sequence[offset]) for offset, index in enumerate(present_indices)}
    target_indices = [int(index) for index in present_indices if str(color_by_index[int(index)]) == str(target_color)]
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
    initial_target_count = int(initial_counts[str(target_color)])
    final_target_count = int(final_counts[str(target_color)])
    operation_phrase = _operation_phrase(
        operations,
        element_name=str(ELEMENT_DISPLAY_NAME[str(element_type)]),
        element_plural=str(ELEMENT_PLURAL[str(element_type)]),
    )
    dataset = base_surface_data(
        scene_variant=str(scene_variant),
        element_type=str(element_type),
        answer_value=int(final_target_count),
        target_element_ids=target_ids_from_indices(cells, target_indices),
        surface_cells=cells,
        rows=int(rows),
        cols=int(cols),
        layout_style=layout_style,
        solver_trace={
            "count_program": "initial_target_color_count plus signed matching-color operation deltas",
            "visual_count_predicate": "element_type == target_element_type and color_name == target_color_name",
            "target_color_name": str(target_color),
            "initial_target_count": int(initial_target_count),
            "initial_color_counts": dict(initial_counts),
            "operations": [dict(operation) for operation in operations],
            "final_color_counts": dict(final_counts),
            "final_target_count": int(final_target_count),
            "target_color_delta": int(final_target_count - initial_target_count),
            "unique_integer_answer": True,
        },
        extra={
            "target_color_name": str(target_color),
            "active_color_names": list(active_colors),
            "initial_target_count": int(initial_target_count),
            "initial_color_counts": dict(initial_counts),
            "operations": [dict(operation) for operation in operations],
            "final_color_counts": dict(final_counts),
            "operation_phrase": str(operation_phrase),
        },
    )
    return dataset, dict(answer_probabilities)


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
        default_min=1,
        default_max=6,
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


__all__ = [
    "base_surface_data",
    "build_color_operation_surface_data",
    "build_color_surface_data",
    "build_missing_surface_data",
    "build_repeated_surface_data",
    "build_scoped_color_surface_data",
]
