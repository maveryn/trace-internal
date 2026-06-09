"""Physics equivalent-circuit tasks for resistor and capacitor diagrams."""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.render_variation import resolve_layout_jitter, resolve_render_int
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_compatible_scene_query_ids, resolve_variant
from ..shared.circuit_scene import RenderedCircuitScene, render_component_network_scene
from ..shared.complexity import build_physics_circuit_resistance_complexity
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.fixed_query_task import FixedPhysicsQueryVariantTaskMixin
from ..shared.style import SUPPORTED_PHYSICS_COLOR_NAMES
from ..shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_ID = "physics_circuits_equivalent_component_family"
PUBLIC_SCENE_ID = "circuit_equivalent"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "series_parallel",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "total_resistance",
    "total_capacitance",
)
COMPATIBILITY: Dict[str, Sequence[str]] = {
    "series_parallel": SUPPORTED_QUERY_IDS,
}
QUERY_COMPONENT_KIND: Dict[str, str] = {
    "total_resistance": "resistor",
    "total_capacitance": "capacitor",
}
QUERY_SUPPORT_KEY: Dict[str, str] = {
    "total_resistance": "total_resistance_target_answer_support",
    "total_capacitance": "total_capacitance_target_answer_support",
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for equivalent-circuit scenes."""

    canvas_width: int = 1280
    canvas_height: int = 720
    terminal_left_x_px: int = 96
    terminal_radius_px: int = 12
    terminal_font_size_px: int = 24
    wire_width_px: int = 5
    component_symbol_width_px: int = 118
    component_symbol_height_px: int = 56
    component_label_font_size_px: int = 20
    label_stroke_width_px: int = 3
    parallel_rail_left_x_px: int = 268
    parallel_branch_top_y_px: int = 180
    parallel_branch_bottom_y_px: int = 470
    component_value_min: int = 1
    component_value_max: int = 60
    total_resistance_target_answer_support: Tuple[int, ...] = tuple(range(1, 21))
    total_capacitance_target_answer_support: Tuple[int, ...] = tuple(range(1, 21))
    parallel_component_count_options: Tuple[int, ...] = (2, 3, 4)
    parallel_block_count_options: Tuple[int, ...] = (1, 2)
    series_parallel_branch_count_options: Tuple[int, ...] = (2, 3)


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved scene/task axes and answer support for one instance."""

    scene_variant: str
    query_id: str
    component_kind: str
    accent_color_name: str
    target_answer: int
    target_answer_support: Tuple[int, ...]
    scene_variant_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _CircuitLayout:
    """One sampled equivalent-circuit topology satisfying the requested total."""

    scene_variant: str
    component_kind: str
    series_values: Tuple[int, ...]
    parallel_values: Tuple[int, ...]
    target_answer: int
    equivalent_value: Fraction
    parallel_blocks: Tuple[Tuple[int, ...], ...] = tuple()
    inter_block_series_values: Tuple[int, ...] = tuple()
    outer_series_values: Tuple[int, int] = (0, 0)


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "circuits")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="circuits", apply_prob=0.5)


def _resolve_int_options(params: Mapping[str, Any], *, key: str, fallback: Sequence[int]) -> Tuple[int, ...]:
    """Resolve a positive integer option list from params/config defaults."""

    raw = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), fallback))
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        raise ValueError(f"{key} must be a sequence of positive integers")
    values = tuple(int(value) for value in raw)
    if not values or any(int(value) < 1 for value in values):
        raise ValueError(f"{key} must contain at least one positive integer")
    return tuple(dict.fromkeys(values))


def _value_bounds(params: Mapping[str, Any]) -> Tuple[int, int]:
    min_value = int(params.get("component_value_min", group_default(_GEN_DEFAULTS, "component_value_min", _DEFAULTS.component_value_min)))
    max_value = int(params.get("component_value_max", group_default(_GEN_DEFAULTS, "component_value_max", _DEFAULTS.component_value_max)))
    if min_value < 1 or max_value < min_value:
        raise ValueError("component value bounds must be positive and ordered")
    return int(min_value), int(max_value)


def _component_count_options(params: Mapping[str, Any], *, key: str) -> Tuple[int, ...]:
    if str(key) != "parallel_component_count_options":
        raise ValueError(f"unsupported component count key: {key}")
    return _resolve_int_options(params, key=str(key), fallback=_DEFAULTS.parallel_component_count_options)


def _branch_count_options(params: Mapping[str, Any]) -> Tuple[int, ...]:
    return _resolve_int_options(
        params,
        key="series_parallel_branch_count_options",
        fallback=_DEFAULTS.series_parallel_branch_count_options,
    )


def _parallel_block_count_options(params: Mapping[str, Any]) -> Tuple[int, ...]:
    return _resolve_int_options(
        params,
        key="parallel_block_count_options",
        fallback=_DEFAULTS.parallel_block_count_options,
    )


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve compatible scene/query/accent/target axes."""

    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.axes")
    scene_variant, scene_probabilities, query_id, query_probabilities = resolve_compatible_scene_query_ids(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_scene_variants=SUPPORTED_SCENE_VARIANTS,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        compatibility=COMPATIBILITY,
        scene_sampling_namespace=f"{TASK_ID}.scene_variant",
        query_sampling_namespace=f"{TASK_ID}.query_id",
    )
    accent_color_name, accent_probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_PHYSICS_COLOR_NAMES,
        explicit_key="accent_color_name",
        weights_key="accent_color_name_weights",
    )
    accent_color_name = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(accent_color_name),
        variant_probabilities=accent_probabilities,
        supported_variants=SUPPORTED_PHYSICS_COLOR_NAMES,
        balance_flag_key="balanced_accent_color_name_sampling",
        explicit_key="accent_color_name",
        weights_key="accent_color_name_weights",
        sampling_namespace=f"{TASK_ID}.accent_color_name",
    )
    target_answer, target_support, target_probabilities = _resolve_target_answer(
        instance_seed=int(instance_seed),
        params=params,
        query_id=str(query_id),
        scene_variant=str(scene_variant),
    )
    return _ResolvedAxes(
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        component_kind=str(QUERY_COMPONENT_KIND[str(query_id)]),
        accent_color_name=str(accent_color_name),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_support),
        scene_variant_probabilities={str(key): float(value) for key, value in scene_probabilities.items()},
        query_id_probabilities={str(key): float(value) for key, value in query_probabilities.items()},
        accent_color_name_probabilities={str(key): float(value) for key, value in accent_probabilities.items()},
        target_answer_probabilities={str(key): float(value) for key, value in target_probabilities.items()},
    )


def _can_realize_target(*, query_id: str, scene_variant: str, target: int, params: Mapping[str, Any]) -> bool:
    """Return true when the sampler has an exact construction for this target."""

    if int(target) < 1:
        return False
    _min_value, max_value = _value_bounds(params)
    component_kind = QUERY_COMPONENT_KIND[str(query_id)]
    if component_kind == "resistor":
        max_parallel_equivalent = max(int(max_value) // int(count) for count in _branch_count_options(params))
        return any(
            any(
                int(block_count) <= (int(target) - int(series_sum)) <= int(block_count) * int(max_parallel_equivalent)
                for series_sum in range(1, int(target))
            )
            for block_count in _parallel_block_count_options(params)
        )
    for block_count in _parallel_block_count_options(params):
        block_equivalent = int(block_count + 1) * int(target)
        if int(block_equivalent) > int(max_value):
            continue
        if any(
            int(branch_count) <= int(block_equivalent) <= int(branch_count) * int(max_value)
            for branch_count in _component_count_options(params, key="parallel_component_count_options")
        ):
            return True
    return False


def _resolve_target_answer(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
    scene_variant: str,
) -> Tuple[int, Tuple[int, ...], Dict[str, float]]:
    """Resolve a target answer from query/scene feasible support."""

    support_key = QUERY_SUPPORT_KEY[str(query_id)]
    fallback = getattr(_DEFAULTS, support_key)
    support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=str(support_key),
        fallback=fallback,
    )
    feasible = tuple(
        int(value)
        for value in support
        if _can_realize_target(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            target=int(value),
            params=params,
        )
    )
    if not feasible:
        raise ValueError(f"no feasible {query_id} target_answer values remain")
    resolved_params = dict(params)
    resolved_params[str(support_key)] = [int(value) for value in feasible]
    target_answer, probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=resolved_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(support_key),
        explicit_key="target_answer",
        fallback_support=feasible,
        namespace=f"{TASK_ID}.target_answer.{str(query_id)}.{str(scene_variant)}",
        balanced_flag_key="balanced_target_answer_sampling",
    )
    if int(target_answer) not in set(feasible):
        raise ValueError(f"unsupported target_answer: {target_answer}")
    return int(target_answer), tuple(int(value) for value in feasible), dict(probabilities)


def _choose_from_options(rng, options: Sequence[int]) -> int:
    values = tuple(int(value) for value in options)
    if not values:
        raise ValueError("empty option list")
    return int(values[int(rng.randrange(len(values)))])


def _compose_positive_sum(
    rng,
    *,
    total: int,
    count: int,
    max_value: int,
) -> Tuple[int, ...]:
    """Compose one positive integer sum with bounded parts."""

    if int(count) <= 1:
        if int(total) > int(max_value):
            raise ValueError("sum component exceeds max value")
        return (int(total),)
    count = min(int(count), int(total))
    if int(total) > int(count) * int(max_value):
        raise ValueError("cannot compose target within max value")
    values = [1 for _ in range(int(count))]
    remaining = int(total) - int(count)
    guard = 0
    while int(remaining) > 0:
        guard += 1
        if guard > 10000:
            raise ValueError("failed to compose bounded sum")
        index = int(rng.randrange(len(values)))
        room = int(max_value) - int(values[index])
        if room <= 0:
            continue
        addition = int(rng.randint(1, min(int(room), int(remaining))))
        values[index] += int(addition)
        remaining -= int(addition)
    rng.shuffle(values)
    return tuple(int(value) for value in values)


def _compose_nonnegative_sum(
    rng,
    *,
    total: int,
    count: int,
    max_value: int,
) -> Tuple[int, ...]:
    """Compose one nonnegative integer sum with bounded parts."""

    if int(count) < 1:
        raise ValueError("nonnegative composition requires at least one slot")
    if int(total) < 0 or int(total) > int(count) * int(max_value):
        raise ValueError("cannot compose bounded nonnegative sum")
    values = [0 for _ in range(int(count))]
    remaining = int(total)
    guard = 0
    while int(remaining) > 0:
        guard += 1
        if guard > 10000:
            raise ValueError("failed to compose bounded nonnegative sum")
        index = int(rng.randrange(len(values)))
        room = int(max_value) - int(values[index])
        if room <= 0:
            continue
        addition = int(rng.randint(1, min(int(room), int(remaining))))
        values[index] += int(addition)
        remaining -= int(addition)
    return tuple(int(value) for value in values)


def _sample_resistor_layout(
    rng,
    *,
    scene_variant: str,
    target_answer: int,
    params: Mapping[str, Any],
) -> _CircuitLayout:
    _min_value, max_value = _value_bounds(params)
    if str(scene_variant) != "series_parallel":
        raise ValueError(f"unsupported mixed circuit variant: {scene_variant}")
    max_parallel_equivalent = max(int(max_value) // int(count) for count in _branch_count_options(params))
    feasible_pairs: List[Tuple[int, int]] = []
    for block_count in _parallel_block_count_options(params):
        for series_sum in range(1, int(target_answer)):
            parallel_equivalent_sum = int(target_answer) - int(series_sum)
            if (
                int(block_count) <= int(parallel_equivalent_sum) <= int(block_count) * int(max_parallel_equivalent)
                and int(series_sum) <= (int(block_count) + 1) * int(max_value)
            ):
                feasible_pairs.append((int(block_count), int(series_sum)))
    if not feasible_pairs:
        raise ValueError("no feasible mixed resistor layout")
    block_count, series_sum = feasible_pairs[int(rng.randrange(len(feasible_pairs)))]
    parallel_equivalent_sum = int(target_answer) - int(series_sum)
    parallel_equivalents = _compose_positive_sum(
        rng,
        total=int(parallel_equivalent_sum),
        count=int(block_count),
        max_value=int(max_parallel_equivalent),
    )
    blocks: List[Tuple[int, ...]] = []
    for parallel_equivalent in parallel_equivalents:
        feasible_branch_counts = tuple(
            int(count)
            for count in _branch_count_options(params)
            if int(count) * int(parallel_equivalent) <= int(max_value)
        )
        branch_count = _choose_from_options(rng, feasible_branch_counts)
        blocks.append(tuple(int(branch_count) * int(parallel_equivalent) for _ in range(int(branch_count))))
    series_slots = _compose_nonnegative_sum(
        rng,
        total=int(series_sum),
        count=int(block_count) + 1,
        max_value=int(max_value),
    )
    outer = (int(series_slots[0]), int(series_slots[-1]))
    inter_block_series = tuple(int(value) for value in series_slots[1:-1])
    equivalent = Fraction(sum(series_slots), 1) + sum(_parallel_resistance(block) for block in blocks)
    return _CircuitLayout(
        scene_variant=str(scene_variant),
        component_kind="resistor",
        series_values=tuple(),
        parallel_values=tuple(),
        parallel_blocks=tuple(tuple(block) for block in blocks),
        inter_block_series_values=tuple(inter_block_series),
        outer_series_values=tuple(outer),
        target_answer=int(target_answer),
        equivalent_value=equivalent,
    )


def _sample_capacitor_layout(
    rng,
    *,
    scene_variant: str,
    target_answer: int,
    params: Mapping[str, Any],
) -> _CircuitLayout:
    _min_value, max_value = _value_bounds(params)
    if str(scene_variant) != "series_parallel":
        raise ValueError(f"unsupported mixed circuit variant: {scene_variant}")
    feasible_block_counts: List[int] = []
    for block_count in _parallel_block_count_options(params):
        block_equivalent = int(block_count + 1) * int(target_answer)
        if int(block_equivalent) <= int(max_value) and any(
            int(count) <= int(block_equivalent) <= int(count) * int(max_value)
            for count in _component_count_options(params, key="parallel_component_count_options")
        ):
            feasible_block_counts.append(int(block_count))
    if not feasible_block_counts:
        raise ValueError("no feasible mixed capacitor layout")
    block_count = _choose_from_options(rng, feasible_block_counts)
    block_equivalent = int(block_count + 1) * int(target_answer)
    blocks: List[Tuple[int, ...]] = []
    for _block_index in range(int(block_count)):
        count_options = tuple(
            int(count)
            for count in _component_count_options(params, key="parallel_component_count_options")
            if int(count) <= int(block_equivalent) <= int(count) * int(max_value)
        )
        count = _choose_from_options(rng, count_options)
        blocks.append(
            _compose_positive_sum(
                rng,
                total=int(block_equivalent),
                count=int(count),
                max_value=int(max_value),
            )
        )
    series_slots = [0 for _ in range(int(block_count) + 1)]
    series_slots[int(rng.randrange(len(series_slots)))] = int(block_equivalent)
    outer = (int(series_slots[0]), int(series_slots[-1]))
    inter_block_series = tuple(int(value) for value in series_slots[1:-1])
    equivalent = _series_capacitance([int(block_equivalent)] + [int(sum(block)) for block in blocks])
    return _CircuitLayout(
        scene_variant=str(scene_variant),
        component_kind="capacitor",
        series_values=tuple(),
        parallel_values=tuple(),
        parallel_blocks=tuple(tuple(block) for block in blocks),
        inter_block_series_values=tuple(inter_block_series),
        outer_series_values=tuple(outer),
        target_answer=int(target_answer),
        equivalent_value=equivalent,
    )


def _sample_layout(
    rng,
    *,
    scene_variant: str,
    component_kind: str,
    target_answer: int,
    params: Mapping[str, Any],
) -> _CircuitLayout:
    if str(component_kind) == "resistor":
        layout = _sample_resistor_layout(
            rng,
            scene_variant=str(scene_variant),
            target_answer=int(target_answer),
            params=params,
        )
    else:
        layout = _sample_capacitor_layout(
            rng,
            scene_variant=str(scene_variant),
            target_answer=int(target_answer),
            params=params,
        )
    if layout.equivalent_value != Fraction(int(target_answer), 1):
        raise ValueError("sampled equivalent value does not match target")
    return layout


def _parallel_resistance(values: Sequence[int]) -> Fraction:
    reciprocal_sum = sum(Fraction(1, int(value)) for value in values)
    if reciprocal_sum <= 0:
        raise ValueError("parallel resistance requires positive values")
    return Fraction(1, 1) / reciprocal_sum


def _series_capacitance(values: Sequence[int]) -> Fraction:
    reciprocal_sum = sum(Fraction(1, int(value)) for value in values)
    if reciprocal_sum <= 0:
        raise ValueError("series capacitance requires positive values")
    return Fraction(1, 1) / reciprocal_sum


def _render_defaults(params: Mapping[str, Any], *, instance_seed: int) -> Dict[str, int]:
    """Resolve render defaults and nonsemantic stroke/font variation."""

    keys = (
        "canvas_width",
        "canvas_height",
        "terminal_left_x_px",
        "terminal_radius_px",
        "terminal_font_size_px",
        "wire_width_px",
        "component_symbol_width_px",
        "component_symbol_height_px",
        "component_label_font_size_px",
        "label_stroke_width_px",
        "parallel_rail_left_x_px",
        "parallel_branch_top_y_px",
        "parallel_branch_bottom_y_px",
    )
    fallback_by_key = {
        "canvas_width": _DEFAULTS.canvas_width,
        "canvas_height": _DEFAULTS.canvas_height,
        "terminal_left_x_px": _DEFAULTS.terminal_left_x_px,
        "terminal_radius_px": _DEFAULTS.terminal_radius_px,
        "terminal_font_size_px": _DEFAULTS.terminal_font_size_px,
        "wire_width_px": _DEFAULTS.wire_width_px,
        "component_symbol_width_px": _DEFAULTS.component_symbol_width_px,
        "component_symbol_height_px": _DEFAULTS.component_symbol_height_px,
        "component_label_font_size_px": _DEFAULTS.component_label_font_size_px,
        "label_stroke_width_px": _DEFAULTS.label_stroke_width_px,
        "parallel_rail_left_x_px": _DEFAULTS.parallel_rail_left_x_px,
        "parallel_branch_top_y_px": _DEFAULTS.parallel_branch_top_y_px,
        "parallel_branch_bottom_y_px": _DEFAULTS.parallel_branch_bottom_y_px,
    }
    return {
        key: int(
            resolve_render_int(
                params,
                _RENDER_DEFAULTS,
                key,
                int(fallback_by_key[key]),
                instance_seed=int(instance_seed),
                namespace=TASK_ID,
            )
        )
        for key in keys
    }


def _circuit_content_bbox(*, render_defaults: Mapping[str, int], scene_variant: str) -> List[float]:
    canvas_width = int(render_defaults["canvas_width"])
    canvas_height = int(render_defaults["canvas_height"])
    mid_y = float(0.5 * canvas_height)
    left = float(render_defaults["terminal_left_x_px"]) - float(render_defaults["terminal_radius_px"]) - 26.0
    right = float(canvas_width - int(render_defaults["terminal_left_x_px"])) + float(render_defaults["terminal_radius_px"]) + 26.0
    if str(scene_variant) == "series":
        top = min(
            float(mid_y - 96.0),
            float(mid_y - float(render_defaults["terminal_radius_px"]) - 52.0),
        )
        bottom = float(mid_y + 42.0)
    else:
        top = min(
            float(render_defaults["parallel_branch_top_y_px"]) - 82.0,
            float(mid_y - float(render_defaults["terminal_radius_px"]) - 52.0),
        )
        bottom = float(render_defaults["parallel_branch_bottom_y_px"]) + 48.0
    return [round(left, 3), round(top, 3), round(right, 3), round(bottom, 3)]


def _resolve_layout_placement(
    *,
    render_defaults: Mapping[str, int],
    params: Mapping[str, Any],
    instance_seed: int,
    scene_variant: str,
) -> Tuple[Tuple[float, float], Dict[str, Any]]:
    """Resolve whole-circuit placement before annotation projection."""

    canvas_width = int(render_defaults["canvas_width"])
    canvas_height = int(render_defaults["canvas_height"])
    content_bbox = _circuit_content_bbox(render_defaults=render_defaults, scene_variant=str(scene_variant))
    content_left, content_top, content_right, content_bottom = [float(value) for value in content_bbox]
    jitter = resolve_layout_jitter(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.layout",
    )
    min_margin = int(jitter.get("min_margin_px", 18))
    requested_dx = int(jitter.get("requested_dx_px", 0))
    requested_dy = int(jitter.get("requested_dy_px", 0))
    min_dx = int(math.ceil(float(min_margin) - float(content_left)))
    max_dx = int(math.floor(float(canvas_width) - float(min_margin) - float(content_right)))
    min_dy = int(math.ceil(float(min_margin) - float(content_top)))
    max_dy = int(math.floor(float(canvas_height) - float(min_margin) - float(content_bottom)))
    if int(min_dx) > int(max_dx):
        min_dx = 0
        max_dx = 0
    if int(min_dy) > int(max_dy):
        min_dy = 0
        max_dy = 0
    if not bool(jitter.get("enabled", False)):
        requested_dx = 0
        requested_dy = 0
    dx = max(int(min_dx), min(int(max_dx), int(requested_dx)))
    dy = max(int(min_dy), min(int(max_dy), int(requested_dy)))
    content_width = round(float(content_right) - float(content_left), 3)
    content_height = round(float(content_bottom) - float(content_top), 3)
    final_bbox = [
        round(float(content_left) + float(dx), 3),
        round(float(content_top) + float(dy), 3),
        round(float(content_right) + float(dx), 3),
        round(float(content_bottom) + float(dy), 3),
    ]
    placement = dict(jitter)
    placement.update(
        {
            "mode": "whole_equivalent_circuit_diagram_offset",
            "content_bbox_px": list(content_bbox),
            "content_size_px": [float(content_width), float(content_height)],
            "final_content_bbox_px": list(final_bbox),
            "canvas_size_px": [int(canvas_width), int(canvas_height)],
            "free_space_px": [
                round(float(canvas_width) - float(content_width), 3),
                round(float(canvas_height) - float(content_height), 3),
            ],
            "available_offset_x_px": [int(min_dx), int(max_dx)],
            "available_offset_y_px": [int(min_dy), int(max_dy)],
            "sampled_offset_px": [int(requested_dx), int(requested_dy)],
            "final_offset_px": [int(dx), int(dy)],
            "default_origin_px": [round(float(content_left), 3), round(float(content_top), 3)],
            "final_origin_px": [round(float(content_left) + float(dx), 3), round(float(content_top) + float(dy), 3)],
            "dx_px": int(dx),
            "dy_px": int(dy),
        }
    )
    return (float(dx), float(dy)), placement


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    prefix = "R" if str(query_id) == "total_resistance" else "C"
    annotation_example = {
        f"{prefix}1": [2, 3, 4, 5],
        f"{prefix}2": [6, 7, 8, 9],
    }
    return build_prompt_json_examples(annotation_value=annotation_example, answer_type="integer")


class _PhysicsCircuitsEquivalentComponentBaseTask:
    """Return one equivalent-circuit question from a technical circuit diagram."""

    task_id = TASK_ID
    domain = "physics"
    task_group = "circuits"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)

        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                layout = _sample_layout(
                    attempt_rng,
                    scene_variant=str(axes.scene_variant),
                    component_kind=str(axes.component_kind),
                    target_answer=int(axes.target_answer),
                    params=params,
                )
            except ValueError:
                continue

            render_defaults = _render_defaults(params, instance_seed=int(instance_seed))
            origin_offset_px, layout_placement_meta = _resolve_layout_placement(
                render_defaults=render_defaults,
                params=params,
                instance_seed=int(instance_seed),
                scene_variant=str(axes.scene_variant),
            )
            background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
                scene_id=PUBLIC_SCENE_ID,
                task_group=self.task_group,
                canvas_width=int(render_defaults["canvas_width"]),
                canvas_height=int(render_defaults["canvas_height"]),
                instance_seed=int(instance_seed),
                params=params,
            )
            font_family = sample_font_family(
                role="readout",
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.render.font_family",
                params=params,
            )
            font_record = get_font_family_record(str(font_family))
            rendered_scene = render_component_network_scene(
                scene_variant=str(layout.scene_variant),
                component_kind=str(layout.component_kind),
                series_values=list(layout.series_values),
                parallel_values=list(layout.parallel_values),
                parallel_blocks=list(layout.parallel_blocks) or None,
                inter_block_series_values=list(layout.inter_block_series_values) or None,
                outer_series_values=list(layout.outer_series_values),
                background=background,
                render_defaults=render_defaults,
                accent_color_name=str(axes.accent_color_name),
                origin_offset_px=origin_offset_px,
                diagram_style=diagram_style,
                font_family=str(font_family),
            )
            image, post_noise_meta = apply_post_image_noise(
                rendered_scene.image,
                instance_seed=int(instance_seed),
                params=params,
                default_config=POST_IMAGE_NOISE_DEFAULTS,
            )

            prompt_defaults = required_group_defaults(
                _PROMPT_DEFAULTS,
                (
                    "bundle_id",
                    "scene_key",
                    "task_key",
                    "json_output_contract",
                    "json_output_contract_answer_only",
                    "answer_hint_total_resistance",
                    "answer_hint_total_capacitance",
                    "annotation_hint_total_resistance",
                    "annotation_hint_total_capacitance",
                    "object_description_series_parallel_total_resistance",
                    "object_description_series_parallel_total_capacitance",
                ),
                context=f"prompt defaults for {self.task_id}",
            )
            json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.query_id))
            prompt_selection = render_task_prompt_variants(
                domain=self.domain,
                task_group=self.task_group,
                bundle_id=str(prompt_defaults["bundle_id"]),
                scene_key=str(prompt_defaults["scene_key"]),
                task_key=str(prompt_defaults["task_key"]),
                query_key=str(axes.query_id),
                answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
                slots={
                    "object_description": str(
                        prompt_defaults[f"object_description_{str(axes.scene_variant)}_{str(axes.query_id)}"]
                    ),
                    "json_output_contract": str(prompt_defaults["json_output_contract"]),
                    "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                    "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(axes.query_id)}"]),
                    "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
                    "json_example": str(json_example),
                    "json_example_answer_only": str(json_example_answer_only),
                },
                instance_seed=int(instance_seed),
            )
            prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

            annotation_value = {
                str(key): [float(v) for v in bbox]
                for key, bbox in rendered_scene.annotation_bbox_map.items()
            }
            answer_gt = TypedValue(type="integer", value=int(axes.target_answer))
            annotation_gt = TypedValue(type="keyed_bbox_map", value=dict(annotation_value))
            projected_annotation = {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(annotation_value),
                "pixel_keyed_bbox_map": dict(annotation_value),
            }
            component_count = len(rendered_scene.component_specs)
            complexity = build_physics_circuit_resistance_complexity(
                task_group_defaults=_TASK_GROUP_DEFAULTS,
                task_id=TASK_ID,
                scene_variant=str(axes.scene_variant),
                query_id=str(axes.query_id),
                resistor_count=int(component_count),
                target_answer=int(axes.target_answer),
            )
            trace_payload = {
                "scene_ir": {
                    "scene_kind": f"physics_equivalent_circuit_{str(axes.component_kind)}_{str(axes.scene_variant)}",
                    "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                    "relations": {
                        "scene_variant": str(axes.scene_variant),
                        "query_id": str(axes.query_id),
                        "component_kind": str(axes.component_kind),
                        "target_answer": int(axes.target_answer),
                        "accent_color_name": str(axes.accent_color_name),
                        "annotation_entity_id_map": dict(rendered_scene.annotation_entity_id_map),
                    },
                },
                "query_spec": {
                    "query_id": str(axes.query_id),
                    "template_id": str(prompt_defaults["bundle_id"]),
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                    "params": {
                        "scene_variant": str(axes.scene_variant),
                        "query_id": str(axes.query_id),
                        "component_kind": str(axes.component_kind),
                        "accent_color_name": str(axes.accent_color_name),
                        "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                        "query_id_probabilities": dict(axes.query_id_probabilities),
                        "accent_color_name_probabilities": dict(axes.accent_color_name_probabilities),
                        "target_answer": int(axes.target_answer),
                        "target_answer_support": [int(value) for value in axes.target_answer_support],
                        "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    },
                },
                "render_spec": {
                    "scene_variant": str(axes.scene_variant),
                    "component_kind": str(axes.component_kind),
                    "component_symbol_style": "ansi_zigzag" if str(axes.component_kind) == "resistor" else "parallel_plates",
                    "canvas_width": int(image.size[0]),
                    "canvas_height": int(image.size[1]),
                    "accent_color_name": str(axes.accent_color_name),
                    "font": {
                        "font_family": str(font_family),
                        "font_asset_version": font_asset_version(),
                        "font_asset": font_record.to_trace(),
                        "scope": "equivalent_circuit_diagram",
                        "selection_policy": {
                            "pool": "global_approved_font_pool",
                            "include_tags": [],
                            "exclude_tags": [],
                            "exclusion_reason": "",
                        },
                    },
                    "technical_diagram_style": dict(diagram_style_meta),
                    "background_style": background_meta,
                    "layout_placement": dict(layout_placement_meta),
                    "post_image_noise": post_noise_meta,
                },
                "render_map": dict(rendered_scene.render_map),
                "execution_trace": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "component_kind": str(axes.component_kind),
                    "accent_color_name": str(axes.accent_color_name),
                    "target_answer": int(axes.target_answer),
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "equivalent_value": int(layout.equivalent_value),
                    "series_values": [int(value) for value in layout.series_values],
                    "parallel_values": [int(value) for value in layout.parallel_values],
                    "parallel_blocks": [[int(value) for value in block] for block in layout.parallel_blocks],
                    "inter_block_series_values": [int(value) for value in layout.inter_block_series_values],
                    "outer_series_values": [int(value) for value in layout.outer_series_values],
                    "component_specs": [
                        {
                            "component_id": str(spec.component_id),
                            "label": str(spec.label),
                            "kind": str(spec.kind),
                            "value": int(spec.value),
                            "unit": str(spec.unit),
                        }
                        for spec in rendered_scene.component_specs
                    ],
                    "annotation_entity_id_map": dict(rendered_scene.annotation_entity_id_map),
                },
                "witness_symbolic": {
                    "type": "object_map",
                    "ids": [str(value) for value in rendered_scene.annotation_entity_id_map.values()],
                    "key_to_entity_id": dict(rendered_scene.annotation_entity_id_map),
                },
                "projected_annotation": dict(projected_annotation),
                "background": background_meta,
                "post_image_noise": post_noise_meta,
            }
            return TaskOutput(
                prompt=str(prompt_artifacts.prompt),
                prompt_variants=dict(prompt_artifacts.prompt_variants),
                answer_gt=answer_gt,
                annotation_gt=annotation_gt,
                image=image,
                image_id="img0",
                trace_payload=trace_payload,
                complexity=complexity,
                task_versions=default_task_versions(),
                query_id=str(axes.query_id),
                scene_id=PUBLIC_SCENE_ID,
            )

        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")


@register_task
class PhysicsCircuitsTotalResistanceValueTask(
    FixedPhysicsQueryVariantTaskMixin,
    _PhysicsCircuitsEquivalentComponentBaseTask,
):
    """Return the total equivalent resistance of one visible resistor network."""

    task_id = "task_physics__circuit_equivalent__total_resistance_value"
    fixed_query_id = "total_resistance"


@register_task
class PhysicsCircuitsTotalCapacitanceValueTask(
    FixedPhysicsQueryVariantTaskMixin,
    _PhysicsCircuitsEquivalentComponentBaseTask,
):
    """Return the total equivalent capacitance of one visible capacitor network."""

    task_id = "task_physics__circuit_equivalent__total_capacitance_value"
    fixed_query_id = "total_capacitance"


__all__ = [
    "PhysicsCircuitsTotalCapacitanceValueTask",
    "PhysicsCircuitsTotalResistanceValueTask",
]
