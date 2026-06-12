"""Count repeated surface elements in synthetic 3D fixture scenes."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .....core.seed import spawn_rng
from .....core.scene_config import (
    get_domain_defaults,
    get_scene_defaults,
    resolve_scene_section_defaults,
)
from .....core.types import TypedValue
from .....core.visual.background import make_background_canvas
from .....core.visual.noise import apply_post_image_noise
from ....base import TaskOutput
from ....shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_scene_generation_rendering_prompt_defaults,
)
from ....shared.output_metadata import default_task_versions
from ....shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ...shared.object_scene import _resolve_render_params
from ...shared.task_support import normalize_unit as _normalize_unit
from ...shared.task_support import resolve_axis_variant as _shared_resolve_axis_variant
from .common import (
    ADJACENCY_SCENE_VARIANTS,
    ADJACENT_TASK_ID,
    COLORED_TASK_ID,
    COLORABLE_SCENE_VARIANTS,
    ELEMENT_DISPLAY_NAME,
    ELEMENT_PLURAL,
    ELEMENT_TYPE_BY_SCENE_VARIANT,
    EMPTY_MISSING_TASK_ID,
    MISSING_SCENE_VARIANTS,
    REPEATED_TASK_ID,
    SCENE_ID,
    SCENE_VARIANT_BY_ELEMENT_TYPE,
    SCOPED_COLORED_TASK_ID,
    SEMANTIC_COLOR_RGB,
    SEMANTIC_COLOR_SUPPORT,
    STATE_DISPLAY_NAME,
    STATE_SUPPORT_BY_SCENE_VARIANT,
    STATE_TASK_ID,
    SUPPORTED_SCENE_VARIANTS,
    SURFACE_FIXTURE_DISPLAY_NAME,
    SURFACE_FIXTURE_TASK_IDS,
)
from .rendering import layout_surface_element_grid, render_surface_fixture


TASK_ID = REPEATED_TASK_ID
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("element_type_count",)

QUERY_IDS_BY_TASK_ID: Mapping[str, Tuple[str, ...]] = {
    REPEATED_TASK_ID: ("element_type_count",),
    COLORED_TASK_ID: ("element_color_count",),
    STATE_TASK_ID: ("element_state_count",),
    SCOPED_COLORED_TASK_ID: ("scoped_element_color_count",),
    EMPTY_MISSING_TASK_ID: ("empty_or_missing_cell_count",),
    ADJACENT_TASK_ID: ("adjacent_to_reference_count",),
}

SCENE_VARIANTS_BY_TASK_ID: Mapping[str, Tuple[str, ...]] = {
    REPEATED_TASK_ID: tuple(SUPPORTED_SCENE_VARIANTS),
    COLORED_TASK_ID: tuple(COLORABLE_SCENE_VARIANTS),
    STATE_TASK_ID: tuple(STATE_SUPPORT_BY_SCENE_VARIANT.keys()),
    SCOPED_COLORED_TASK_ID: tuple(COLORABLE_SCENE_VARIANTS),
    EMPTY_MISSING_TASK_ID: tuple(MISSING_SCENE_VARIANTS),
    ADJACENT_TASK_ID: tuple(ADJACENCY_SCENE_VARIANTS),
}

_SCENE_DEFAULTS = get_scene_defaults("three_d", SCENE_ID)
_DOMAIN_DEFAULTS = get_domain_defaults("three_d")
_VISUAL_DEFAULTS = _DOMAIN_DEFAULTS.get("visual", {}) if isinstance(_DOMAIN_DEFAULTS, Mapping) else {}
_BACKGROUND_DEFAULTS = _VISUAL_DEFAULTS.get("background", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}
_NOISE_DEFAULTS = _VISUAL_DEFAULTS.get("noise", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}


def _one_hot_probability_map(values: Sequence[str], selected: str) -> Dict[str, float]:
    return {str(value): (1.0 if str(value) == str(selected) else 0.0) for value in values}


def _uniform_probability_map(values: Sequence[int], *, selected: int | None = None) -> Dict[str, float]:
    support = tuple(int(value) for value in values)
    if selected is not None:
        return {str(value): (1.0 if int(value) == int(selected) else 0.0) for value in support}
    probability = 1.0 / float(max(1, len(support)))
    return {str(value): float(probability) for value in support}


def _configured_int(params: Mapping[str, Any], gen_defaults: Mapping[str, Any], key: str, default: int) -> int:
    return int(params.get(str(key), group_default(gen_defaults, str(key), int(default))))


def _task_defaults(task_id: str) -> Tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    gen_defaults, render_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
        _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
        task_id=str(task_id),
    )


def _resolve_int_support(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    min_key: str,
    max_key: str,
    default_min: int,
    default_max: int,
    explicit_keys: Sequence[str],
    lower_bound: int = 0,
    upper_bound: int = 64,
) -> Tuple[int, Dict[str, float]]:
    minimum = max(int(lower_bound), min(int(upper_bound), _configured_int(params, gen_defaults, min_key, int(default_min))))
    maximum = max(minimum, min(int(upper_bound), _configured_int(params, gen_defaults, max_key, int(default_max))))
    support = tuple(range(int(minimum), int(maximum) + 1))
    explicit = None
    for key in explicit_keys:
        if key in params:
            explicit = params[key]
            break
    if explicit is not None:
        selected = int(explicit)
        if selected not in set(support):
            raise ValueError(f"unsupported {explicit_keys[0]}: {selected}")
        return int(selected), _uniform_probability_map(support, selected=int(selected))
    rng = spawn_rng(int(instance_seed), str(namespace))
    selected = int(support[int(rng.randrange(len(support)))])
    return int(selected), _uniform_probability_map(support)


def _resolve_query_id(
    *,
    task_id: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[str, Dict[str, float]]:
    supported = QUERY_IDS_BY_TASK_ID[str(task_id)]
    return _shared_resolve_axis_variant(
        params,
        task_id=str(task_id),
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=supported,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def _resolve_scene_and_element(
    *,
    task_id: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[str, Dict[str, float], str, Dict[str, float]]:
    supported_scenes = SCENE_VARIANTS_BY_TASK_ID[str(task_id)]
    supported_elements = tuple(str(ELEMENT_TYPE_BY_SCENE_VARIANT[str(scene)]) for scene in supported_scenes)
    explicit_element = params.get("target_element_type", params.get("element_type"))
    explicit_scene = params.get("scene_variant")
    if explicit_element is not None:
        element_type = str(explicit_element)
        if element_type not in set(supported_elements):
            raise ValueError(f"unsupported target_element_type for {task_id}: {element_type}")
        expected_scene = str(SCENE_VARIANT_BY_ELEMENT_TYPE[element_type])
        if expected_scene not in set(supported_scenes):
            raise ValueError(f"unsupported scene_variant for {task_id}: {expected_scene}")
        if explicit_scene is not None and str(explicit_scene) != expected_scene:
            raise ValueError(f"{element_type} fixtures require scene_variant={expected_scene}")
        return (
            expected_scene,
            _one_hot_probability_map(supported_scenes, expected_scene),
            element_type,
            _one_hot_probability_map(supported_elements, element_type),
        )

    scene_variant, scene_probabilities = _shared_resolve_axis_variant(
        params,
        task_id=str(task_id),
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=supported_scenes,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )
    element_type = str(ELEMENT_TYPE_BY_SCENE_VARIANT[str(scene_variant)])
    return (
        str(scene_variant),
        dict(scene_probabilities),
        str(element_type),
        _one_hot_probability_map(supported_elements, str(element_type)) if explicit_scene is not None else {
            str(ELEMENT_TYPE_BY_SCENE_VARIANT[str(scene)]): float(scene_probabilities[str(scene)])
            for scene in supported_scenes
        },
    )


def _resolve_color(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    explicit_key: str,
    exclude: Sequence[str] = (),
) -> str:
    explicit = params.get(str(explicit_key))
    support = tuple(color for color in SEMANTIC_COLOR_SUPPORT if str(color) not in set(str(item) for item in exclude))
    if not support:
        raise ValueError("empty color support")
    if explicit is not None:
        color = str(explicit)
        if color not in set(support):
            raise ValueError(f"unsupported {explicit_key}: {color}")
        return str(color)
    rng = spawn_rng(int(instance_seed), str(namespace))
    return str(support[int(rng.randrange(len(support)))])


def _layout_cells(
    *,
    scene_variant: str,
    element_type: str,
    rows: int,
    cols: int,
    present_indices: Sequence[int],
    target_indices: Sequence[int],
    rng: Any,
    layout_style: str,
    color_by_index: Mapping[int, str] | None = None,
    state_by_index: Mapping[int, str] | None = None,
    reference_index: int | None = None,
    include_absent: bool = False,
) -> List[Dict[str, Any]]:
    color_by_index = color_by_index or {}
    state_by_index = state_by_index or {}
    present_set = {int(index) for index in present_indices}
    target_set = {int(index) for index in target_indices}
    u_pad = 0.065
    v_pad = 0.075
    gap = 0.016
    if str(layout_style) == "variable_grid":
        col_weights = [float(rng.uniform(0.78, 1.22)) for _ in range(int(cols))]
        row_weights = [float(rng.uniform(0.82, 1.18)) for _ in range(int(rows))]
    else:
        col_weights = [1.0 for _ in range(int(cols))]
        row_weights = [1.0 for _ in range(int(rows))]
    col_total = sum(col_weights) or 1.0
    row_total = sum(row_weights) or 1.0
    col_edges = [u_pad]
    for weight in col_weights:
        col_edges.append(float(col_edges[-1]) + (1.0 - 2.0 * u_pad) * float(weight) / float(col_total))
    row_edges = [v_pad]
    for weight in row_weights:
        row_edges.append(float(row_edges[-1]) + (1.0 - 2.0 * v_pad) * float(weight) / float(row_total))

    cells: List[Dict[str, Any]] = []
    for flat_index in range(int(rows) * int(cols)):
        row = int(flat_index // int(cols))
        col = int(flat_index % int(cols))
        u0 = float(col_edges[col])
        u1 = float(col_edges[col + 1])
        v0 = float(row_edges[row])
        v1 = float(row_edges[row + 1])
        if str(layout_style) == "brick_grid" and row % 2 == 1:
            shift = ((u1 - u0) * 0.22)
            u0 = max(u_pad, u0 + shift)
            u1 = min(1.0 - u_pad, u1 + shift)
        is_present = int(flat_index) in present_set
        if not is_present and not bool(include_absent):
            continue
        color_name = str(color_by_index.get(int(flat_index), ""))
        state = str(state_by_index.get(int(flat_index), "normal"))
        count_role = "target" if int(flat_index) in target_set else "distractor"
        if reference_index is not None and int(flat_index) == int(reference_index):
            count_role = "reference"
        element_id = f"{element_type}_{flat_index:02d}" if is_present else f"missing_{element_type}_{flat_index:02d}"
        cells.append(
            {
                "element_id": str(element_id),
                "cell_id": f"cell_{flat_index:02d}",
                "flat_index": int(flat_index),
                "element_type": str(element_type),
                "row": int(row),
                "column": int(col),
                "u0": float(u0 + gap),
                "u1": float(u1 - gap),
                "v0": float(v0 + gap),
                "v1": float(v1 - gap),
                "present": bool(is_present),
                "color_name": str(color_name),
                "fill_rgb": list(SEMANTIC_COLOR_RGB[color_name]) if color_name else None,
                "state": str(state),
                "count_role": str(count_role),
            }
        )
    return cells


def _target_ids_from_indices(cells: Sequence[Mapping[str, Any]], target_indices: Sequence[int]) -> List[str]:
    target_set = {int(index) for index in target_indices}
    return [str(cell["element_id"]) for cell in cells if int(cell["flat_index"]) in target_set]


def _sample_indices(rng: Any, support: Sequence[int], count: int) -> List[int]:
    choices = list(int(value) for value in support)
    rng.shuffle(choices)
    return sorted(choices[: int(count)])


def _grid_for_total(total_slots: int, *, min_cols: int = 3) -> Tuple[int, int]:
    rows, cols = layout_surface_element_grid(int(total_slots))
    cols = max(int(min_cols), int(cols))
    rows = int((int(total_slots) + int(cols) - 1) // int(cols))
    return int(rows), int(cols)


def _base_dataset(
    *,
    query_id: str,
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
    data: Dict[str, Any] = {
        "query_id": str(query_id),
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


def _build_repeated_dataset(
    *,
    task_id: str,
    query_id: str,
    scene_variant: str,
    element_type: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, float]]:
    count, probabilities = _resolve_int_support(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.target_count",
        min_key="target_count_min",
        max_key="target_count_max",
        default_min=8,
        default_max=24,
        explicit_keys=("target_count", "element_count"),
        lower_bound=4,
        upper_bound=32,
    )
    rows, cols = layout_surface_element_grid(int(count))
    layout_style = "brick_grid" if str(scene_variant) == "brick_wall" else "uniform_grid"
    rng = spawn_rng(int(instance_seed), f"{task_id}.cells")
    indices = list(range(int(count)))
    cells = _layout_cells(
        scene_variant=str(scene_variant),
        element_type=str(element_type),
        rows=int(rows),
        cols=int(cols),
        present_indices=indices,
        target_indices=indices,
        rng=rng,
        layout_style=layout_style,
    )
    dataset = _base_dataset(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        element_type=str(element_type),
        answer_value=int(count),
        target_element_ids=_target_ids_from_indices(cells, indices),
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
            "unique_integer_answer": True,
        },
    )
    return dataset, dict(probabilities)


def _build_colored_dataset(
    *,
    task_id: str,
    query_id: str,
    scene_variant: str,
    element_type: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, float]]:
    target_count, target_probabilities = _resolve_int_support(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.target_count",
        min_key="target_count_min",
        max_key="target_count_max",
        default_min=3,
        default_max=10,
        explicit_keys=("target_count", "answer_count"),
        lower_bound=1,
        upper_bound=16,
    )
    distractor_count, _ = _resolve_int_support(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.distractor_count",
        min_key="distractor_count_min",
        max_key="distractor_count_max",
        default_min=5,
        default_max=12,
        explicit_keys=("distractor_count",),
        lower_bound=1,
        upper_bound=24,
    )
    total = int(target_count) + int(distractor_count)
    rows, cols = _grid_for_total(total)
    total_slots = int(rows) * int(cols)
    rng = spawn_rng(int(instance_seed), f"{task_id}.cells")
    all_indices = list(range(total_slots))
    present_indices = _sample_indices(rng, all_indices, total)
    target_indices = _sample_indices(rng, present_indices, target_count)
    target_color = _resolve_color(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.target_color", explicit_key="target_color_name")
    other_colors = [color for color in SEMANTIC_COLOR_SUPPORT if color != target_color]
    color_by_index: Dict[int, str] = {}
    for index in present_indices:
        color_by_index[int(index)] = str(target_color if int(index) in set(target_indices) else other_colors[int(rng.randrange(len(other_colors)))])
    layout_style = "variable_grid" if str(scene_variant) in {"brick_wall", "paver_floor", "mailbox_bank"} else "uniform_grid"
    cells = _layout_cells(
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
    dataset = _base_dataset(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        element_type=str(element_type),
        answer_value=int(target_count),
        target_element_ids=_target_ids_from_indices(cells, target_indices),
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


def _build_state_dataset(
    *,
    task_id: str,
    query_id: str,
    scene_variant: str,
    element_type: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, float]]:
    target_count, target_probabilities = _resolve_int_support(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.target_count",
        min_key="target_count_min",
        max_key="target_count_max",
        default_min=2,
        default_max=8,
        explicit_keys=("target_count", "answer_count"),
        lower_bound=1,
        upper_bound=14,
    )
    distractor_count, _ = _resolve_int_support(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.distractor_count",
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
        rng_state = spawn_rng(int(instance_seed), f"{task_id}.target_state")
        target_state = str(state_support[int(rng_state.randrange(len(state_support)))])
    total = int(target_count) + int(distractor_count)
    rows, cols = _grid_for_total(total)
    total_slots = int(rows) * int(cols)
    rng = spawn_rng(int(instance_seed), f"{task_id}.cells")
    present_indices = _sample_indices(rng, list(range(total_slots)), total)
    target_indices = _sample_indices(rng, present_indices, target_count)
    other_states = [state for state in state_support if state != target_state]
    state_by_index: Dict[int, str] = {}
    for index in present_indices:
        state_by_index[int(index)] = str(
            target_state if int(index) in set(target_indices) else other_states[int(rng.randrange(len(other_states)))]
        )
    color_by_index = {int(index): str(SEMANTIC_COLOR_SUPPORT[int(rng.randrange(len(SEMANTIC_COLOR_SUPPORT)))]) for index in present_indices}
    cells = _layout_cells(
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
    dataset = _base_dataset(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        element_type=str(element_type),
        answer_value=int(target_count),
        target_element_ids=_target_ids_from_indices(cells, target_indices),
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


def _build_scoped_colored_dataset(
    *,
    task_id: str,
    query_id: str,
    scene_variant: str,
    element_type: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, float]]:
    target_count, target_probabilities = _resolve_int_support(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.target_count",
        min_key="target_count_min",
        max_key="target_count_max",
        default_min=1,
        default_max=6,
        explicit_keys=("target_count", "answer_count"),
        lower_bound=1,
        upper_bound=10,
    )
    rng = spawn_rng(int(instance_seed), f"{task_id}.cells")
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
    target_indices = _sample_indices(rng, scope_indices, int(target_count))
    target_color = _resolve_color(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.target_color", explicit_key="target_color_name")
    other_colors = [color for color in SEMANTIC_COLOR_SUPPORT if color != target_color]
    outside_same_color_count = min(int(rng.randrange(1, 4)), max(0, total_slots - len(scope_indices)))
    outside_indices = [index for index in all_indices if index not in set(scope_indices)]
    outside_same_color = set(_sample_indices(rng, outside_indices, outside_same_color_count))
    color_by_index: Dict[int, str] = {}
    for index in all_indices:
        if int(index) in set(target_indices) or int(index) in outside_same_color:
            color_by_index[int(index)] = str(target_color)
        else:
            color_by_index[int(index)] = str(other_colors[int(rng.randrange(len(other_colors)))])
    cells = _layout_cells(
        scene_variant=str(scene_variant),
        element_type=str(element_type),
        rows=int(rows),
        cols=int(cols),
        present_indices=all_indices,
        target_indices=target_indices,
        rng=rng,
        layout_style="variable_grid" if str(scene_variant) in {"brick_wall", "paver_floor"} else "uniform_grid",
        color_by_index=color_by_index,
    )
    dataset = _base_dataset(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        element_type=str(element_type),
        answer_value=int(target_count),
        target_element_ids=_target_ids_from_indices(cells, target_indices),
        surface_cells=cells,
        rows=int(rows),
        cols=int(cols),
        layout_style="variable_grid" if str(scene_variant) in {"brick_wall", "paver_floor"} else "uniform_grid",
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


def _build_missing_dataset(
    *,
    task_id: str,
    query_id: str,
    scene_variant: str,
    element_type: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, float]]:
    missing_count, probabilities = _resolve_int_support(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.missing_count",
        min_key="missing_count_min",
        max_key="missing_count_max",
        default_min=2,
        default_max=8,
        explicit_keys=("missing_count", "target_count", "answer_count"),
        lower_bound=1,
        upper_bound=12,
    )
    total_slots, _ = _resolve_int_support(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.total_slots",
        min_key="total_slot_count_min",
        max_key="total_slot_count_max",
        default_min=12,
        default_max=24,
        explicit_keys=("total_slots", "cell_count"),
        lower_bound=int(missing_count) + 2,
        upper_bound=36,
    )
    rows, cols = _grid_for_total(int(total_slots))
    total_grid_slots = int(rows) * int(cols)
    rng = spawn_rng(int(instance_seed), f"{task_id}.cells")
    all_indices = list(range(total_grid_slots))
    missing_indices = _sample_indices(rng, all_indices, int(missing_count))
    present_indices = [index for index in all_indices if index not in set(missing_indices)]
    color_by_index = {int(index): str(SEMANTIC_COLOR_SUPPORT[int(rng.randrange(len(SEMANTIC_COLOR_SUPPORT)))]) for index in present_indices}
    cells = _layout_cells(
        scene_variant=str(scene_variant),
        element_type=str(element_type),
        rows=int(rows),
        cols=int(cols),
        present_indices=present_indices,
        target_indices=missing_indices,
        rng=rng,
        layout_style="brick_grid" if str(scene_variant) == "brick_wall" else "uniform_grid",
        color_by_index=color_by_index,
        include_absent=True,
    )
    dataset = _base_dataset(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        element_type=str(element_type),
        answer_value=int(missing_count),
        target_element_ids=_target_ids_from_indices(cells, missing_indices),
        surface_cells=cells,
        rows=int(rows),
        cols=int(cols),
        layout_style="brick_grid" if str(scene_variant) == "brick_wall" else "uniform_grid",
        solver_trace={
            "count_predicate": "present == false",
            "missing_count": int(missing_count),
            "total_slot_count": int(total_grid_slots),
            "unique_integer_answer": True,
        },
        extra={"missing_count": int(missing_count), "total_slot_count": int(total_grid_slots)},
    )
    return dataset, dict(probabilities)


def _edge_neighbors(index: int, rows: int, cols: int) -> List[int]:
    row = int(index // cols)
    col = int(index % cols)
    neighbors = []
    if row > 0:
        neighbors.append((row - 1) * cols + col)
    if row + 1 < rows:
        neighbors.append((row + 1) * cols + col)
    if col > 0:
        neighbors.append(row * cols + col - 1)
    if col + 1 < cols:
        neighbors.append(row * cols + col + 1)
    return neighbors


def _build_adjacent_dataset(
    *,
    task_id: str,
    query_id: str,
    scene_variant: str,
    element_type: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, float]]:
    answer_count, probabilities = _resolve_int_support(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.answer_count",
        min_key="target_count_min",
        max_key="target_count_max",
        default_min=2,
        default_max=4,
        explicit_keys=("target_count", "answer_count", "neighbor_count"),
        lower_bound=1,
        upper_bound=4,
    )
    rng = spawn_rng(int(instance_seed), f"{task_id}.cells")
    rows = int(params.get("layout_rows", 4 + int(rng.randrange(2))))
    cols = int(params.get("layout_columns", 5 + int(rng.randrange(2))))
    candidates = [index for index in range(rows * cols) if len(_edge_neighbors(index, rows, cols)) >= int(answer_count)]
    if not candidates:
        raise ValueError(f"no reference cells with at least {answer_count} edge-neighbors")
    reference_index = int(params.get("reference_index", candidates[int(rng.randrange(len(candidates)))]))
    neighbor_candidates = _edge_neighbors(reference_index, rows, cols)
    if len(neighbor_candidates) < int(answer_count):
        raise ValueError(f"reference_index {reference_index} has {len(neighbor_candidates)} edge-neighbors, expected at least {answer_count}")
    target_indices = _sample_indices(rng, neighbor_candidates, int(answer_count))
    omitted_neighbor_indices = [index for index in neighbor_candidates if int(index) not in set(target_indices)]
    reference_color = _resolve_color(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.reference_color", explicit_key="reference_color_name")
    other_colors = [color for color in SEMANTIC_COLOR_SUPPORT if color != reference_color]
    color_by_index = {
        int(index): (str(reference_color) if int(index) == int(reference_index) else str(other_colors[int(rng.randrange(len(other_colors)))]))
        for index in range(rows * cols)
    }
    cells = _layout_cells(
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
    dataset = _base_dataset(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        element_type=str(element_type),
        answer_value=int(answer_count),
        target_element_ids=_target_ids_from_indices(cells, target_indices),
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
            "reference_element_id": str(cells[int(reference_index)]["element_id"]),
        },
    )
    return dataset, dict(probabilities)


def _build_surface_dataset(
    *,
    task_id: str,
    query_id: str,
    scene_variant: str,
    element_type: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, float]]:
    if str(task_id) == REPEATED_TASK_ID:
        return _build_repeated_dataset(
            task_id=str(task_id),
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            element_type=str(element_type),
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
        )
    if str(task_id) == COLORED_TASK_ID:
        return _build_colored_dataset(
            task_id=str(task_id),
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            element_type=str(element_type),
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
        )
    if str(task_id) == STATE_TASK_ID:
        return _build_state_dataset(
            task_id=str(task_id),
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            element_type=str(element_type),
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
        )
    if str(task_id) == SCOPED_COLORED_TASK_ID:
        return _build_scoped_colored_dataset(
            task_id=str(task_id),
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            element_type=str(element_type),
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
        )
    if str(task_id) == EMPTY_MISSING_TASK_ID:
        return _build_missing_dataset(
            task_id=str(task_id),
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            element_type=str(element_type),
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
        )
    if str(task_id) == ADJACENT_TASK_ID:
        return _build_adjacent_dataset(
            task_id=str(task_id),
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            element_type=str(element_type),
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
        )
    raise ValueError(f"unsupported surface fixture task_id: {task_id}")




def _generate_surface_fixture_task(task: Any, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
    task_id = str(task.task_id)
    query_id, query_probabilities = _resolve_query_id(
        task_id=task_id,
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
    )
    scene_variant, scene_probabilities, element_type, element_probabilities = _resolve_scene_and_element(
        task_id=task_id,
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
    )
    dataset, answer_value_probabilities = _build_surface_dataset(
        task_id=task_id,
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        element_type=str(element_type),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
    )

    render_params = _resolve_render_params(params, render_defaults=render_defaults)
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=_BACKGROUND_DEFAULTS,
    )
    rendered = render_surface_fixture(background, dataset=dataset, render_params=render_params)
    image, post_noise_meta = apply_post_image_noise(
        rendered.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=_NOISE_DEFAULTS,
    )
    target_element_ids = [str(element_id) for element_id in dataset["target_element_ids"]]
    annotation_bboxes = [list(rendered.element_bboxes_px[str(element_id)]) for element_id in target_element_ids]

    prompt_defaults = required_group_defaults(
        prompt_defaults_raw,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description",
            "answer_hint",
            "annotation_hint",
            "json_example",
            "json_example_answer_only",
        ),
        context=f"prompt defaults for {task_id}",
    )
    prompt_selection = render_scene_prompt_variants(
        domain=task.domain,
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(prompt_defaults["object_description"]),
            "target_element_name": str(dataset["target_element_name"]),
            "target_element_plural": str(dataset["target_element_plural"]),
            "target_color_name": str(dataset.get("target_color_name", "")),
            "target_state_label": str(dataset.get("target_state_label", "")),
            "scope_phrase": str(dataset.get("scope_phrase", "")),
            "reference_color_name": str(dataset.get("reference_color_name", "")),
            "fixture_display_name": str(dataset.get("fixture_display_name", "fixture surface")),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint"]),
            "annotation_hint": str(prompt_defaults["annotation_hint"]),
            "json_example": str(prompt_defaults["json_example"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
        },
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

    answer_value = int(dataset["answer_value"])
    answer_gt = TypedValue(type="integer", value=int(answer_value))
    annotation_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_bboxes])
    total_elements = len([cell for cell in dataset["surface_cells"] if bool(cell.get("present", True))])
    solver_trace = dict(dataset["solver_trace"])
    solver_trace.update(
        {
            "answer_value": int(answer_value),
            "target_element_ids": list(target_element_ids),
            "target_element_bboxes_px": {
                str(element_id): list(rendered.element_bboxes_px[str(element_id)])
                for element_id in target_element_ids
            },
        }
    )

    trace_payload = {
        "scene_ir": {
            "scene_kind": f"three_d_surface_fixture_{task_id.rsplit('__', 1)[-1]}",
            "entities": [dict(entity) for entity in rendered.entities],
            "relations": {
                "scene_variant": str(scene_variant),
                "fixture_display_name": str(dataset["fixture_display_name"]),
                "target_element_type": str(dataset["target_element_type"]),
                "target_element_name": str(dataset["target_element_name"]),
                "target_element_plural": str(dataset["target_element_plural"]),
                "answer_value": int(answer_value),
                "target_element_ids": list(target_element_ids),
                "layout_rows": int(dataset["layout_rows"]),
                "layout_columns": int(dataset["layout_columns"]),
                "layout_style": str(dataset["layout_style"]),
            },
        },
        "query_spec": {
            "query_id": str(query_id),
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": {
                "query_id": str(query_id),
                "query_id_probabilities": dict(query_probabilities),
                "scene_variant": str(scene_variant),
                "scene_variant_probabilities": dict(scene_probabilities),
                "target_element_type": str(dataset["target_element_type"]),
                "target_element_type_probabilities": dict(element_probabilities),
                "answer_value": int(answer_value),
                "answer_value_probabilities": dict(answer_value_probabilities),
            },
        },
        "render_spec": {
            "canvas_width": int(render_params.canvas_width),
            "canvas_height": int(render_params.canvas_height),
            "coord_space": "pixel",
            "scene_variant": str(scene_variant),
            "background_style": dict(background_meta),
            "post_image_noise": dict(post_noise_meta),
            "projection_model": "synthetic_perspective_panel_v0",
            "surface_world_corners": [list(point) for point in dataset["surface_world_corners"]],
        },
        "render_map": {
            "image_id": "img0",
            "scene_bbox_px": list(rendered.scene_bbox_px),
            "fixture_bbox_px": list(rendered.fixture_bbox_px),
            "element_bboxes_px": dict(rendered.element_bboxes_px),
            "element_centers_px": dict(rendered.element_centers_px),
            "target_element_bboxes_px": {
                str(element_id): list(rendered.element_bboxes_px[str(element_id)])
                for element_id in target_element_ids
            },
            "target_element_centers_px": {
                str(element_id): list(rendered.element_centers_px[str(element_id)])
                for element_id in target_element_ids
            },
        },
        "execution_trace": {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "answer_value": int(answer_value),
            "target_element_type": str(dataset["target_element_type"]),
            "target_element_name": str(dataset["target_element_name"]),
            "target_element_plural": str(dataset["target_element_plural"]),
            "target_element_ids": list(target_element_ids),
            "target_element_bboxes_px": {
                str(element_id): list(rendered.element_bboxes_px[str(element_id)])
                for element_id in target_element_ids
            },
            "layout_rows": int(dataset["layout_rows"]),
            "layout_columns": int(dataset["layout_columns"]),
            "layout_style": str(dataset["layout_style"]),
            "surface_cells": [dict(cell) for cell in dataset["surface_cells"]],
            "question_format": str(query_id),
            "solver_trace": dict(solver_trace),
        },
        "witness_symbolic": {
            "type": "counted_surface_element_set",
            "element_ids": list(target_element_ids),
            "target_element_type": str(dataset["target_element_type"]),
            "answer_value": int(answer_value),
        },
        "projected_annotation": {
            "type": "bbox_set",
            "bbox_set": [list(bbox) for bbox in annotation_bboxes],
            "pixel_bbox_set": [list(bbox) for bbox in annotation_bboxes],
        },
        "background": dict(background_meta),
        "post_image_noise": dict(post_noise_meta),
    }

    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        answer_gt=answer_gt,
        annotation_gt=annotation_gt,
        image=image,
        image_id="img0",
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(query_id),
    )


class BaseSurfaceFixtureCountTask:
    domain = "three_d"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = (
                int(instance_seed)
                if attempt_index == 0
                else int(spawn_rng(int(instance_seed), f"{self.task_id}.attempt_seed.{attempt_index}").randrange(1, 2**62))
            )
            try:
                return _generate_surface_fixture_task(self, int(attempt_seed), params=params)
            except Exception as exc:  # pragma: no cover - retry loop matches other 3D tasks.
                last_error = exc
        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts: {last_error}")

__all__ = [
    "ADJACENT_TASK_ID",
    "BaseSurfaceFixtureCountTask",
    "COLORED_TASK_ID",
    "ELEMENT_TYPE_BY_SCENE_VARIANT",
    "EMPTY_MISSING_TASK_ID",
    "REPEATED_TASK_ID",
    "SCENE_ID",
    "SCOPED_COLORED_TASK_ID",
    "STATE_TASK_ID",
    "SUPPORTED_QUERY_IDS",
    "SURFACE_FIXTURE_TASK_IDS",
    "TASK_ID",
]
