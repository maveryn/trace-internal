"""Physics mechanics task for simple spring-extension proportionality diagrams."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.drawing import draw_centered_text, draw_rounded_rect
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.render_variation import resolve_layout_jitter, resolve_render_int
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ...shared.variant_sampling import (
    apply_balanced_variant_sampling,
    resolve_compatible_scene_query_ids,
    resolve_variant,
)
from ..shared.complexity import build_physics_spring_extension_complexity
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.fixed_query_task import FixedPhysicsQueryVariantTaskMixin
from ..shared.style import SUPPORTED_PHYSICS_COLOR_NAMES, build_physics_spring_theme
from ..shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_ID = "physics_mechanics_spring_extension_family"
SPRING_SEMANTIC_COLORS = ((255, 231, 231), (187, 56, 56), (167, 38, 38))
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "paired_springs",
    "staggered_springs",
    "textured_spring",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "missing_weight_for_extension",
    "missing_extension_for_weight",
    "extension_difference",
)
SUPPORTED_PUBLIC_QUERY_IDS: Tuple[str, ...] = (
    "missing_value",
    "extension_difference",
)
_SOLVE_FOR_BY_QUERY_ID = {
    "missing_weight_for_extension": "weight",
    "missing_extension_for_weight": "extension",
}
_QUERY_ID_BY_SOLVE_FOR = {
    "weight": "missing_weight_for_extension",
    "extension": "missing_extension_for_weight",
}
_SUPPORTED_SOLVE_FOR_TARGETS: Tuple[str, ...] = ("weight", "extension")
COMPATIBILITY: Dict[str, Sequence[str]] = {
    "paired_springs": SUPPORTED_QUERY_IDS,
    "staggered_springs": SUPPORTED_QUERY_IDS,
    "textured_spring": SUPPORTED_QUERY_IDS,
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for spring-extension scenes."""

    canvas_width: int = 980
    canvas_height: int = 660
    card_width_px: int = 304
    card_height_px: int = 470
    card_left_px: int = 86
    card_top_px: int = 108
    card_gap_px: int = 108
    stagger_offset_y_px: int = 28
    card_corner_radius_px: int = 24
    card_outline_width_px: int = 4
    support_width_px: int = 164
    support_height_px: int = 16
    support_corner_radius_px: int = 8
    anchor_y_gap_px: int = 22
    hanger_line_width_px: int = 4
    ruler_top_gap_px: int = 18
    ruler_right_gap_px: int = 42
    ruler_value_max: int = 14
    ruler_unit_px: int = 25
    ruler_width_px: int = 4
    ruler_tick_long_px: int = 20
    ruler_tick_short_px: int = 12
    ruler_font_size_px: int = 19
    spring_neutral_units: int = 2
    spring_line_width_px: int = 5
    spring_half_width_px: int = 16
    spring_turn_count: int = 8
    weight_box_width_px: int = 78
    weight_box_height_px: int = 54
    weight_font_size_px: int = 28
    marker_height_px: int = 22
    marker_width_px: int = 52
    missing_tag_width_px: int = 52
    missing_tag_height_px: int = 34
    missing_tag_top_gap_px: int = 22
    label_stroke_width_px: int = 3
    texture_spacing_px: int = 18
    texture_line_width_px: int = 2
    scale_factor_support: Tuple[int, ...] = (1, 2, 3)
    weight_value_min: int = 1
    weight_value_max: int = 9
    extension_value_max: int = 14
    missing_weight_support: Tuple[int, ...] = tuple(range(1, 10))
    missing_extension_support: Tuple[int, ...] = tuple(range(1, 13))
    extension_difference_scale_factor_support: Tuple[int, ...] = (2,)
    extension_difference_support: Tuple[int, ...] = (2, 4, 8, 10, 12)


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved scene/query axes and answer support for one instance."""

    scene_variant: str
    query_id: str
    public_query_id: str
    solve_for: str | None
    accent_color_name: str
    target_answer: int
    scene_variant_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    solve_for_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _ColumnSpec:
    """One spring card's symbolic measurement state."""

    column_id: str
    shown_weight_value: int | None
    true_weight_value: int
    shown_extension_value: int | None
    true_extension_value: int
    missing_weight: bool
    missing_extension: bool
    detached_weight: bool


@dataclass(frozen=True)
class _SceneSpec:
    """Resolved symbolic scene specification for one instance."""

    scene_variant: str
    query_id: str
    scale_factor: int
    left: _ColumnSpec
    right: _ColumnSpec
    target_answer: int
    annotation_entity_ids: Tuple[str, ...]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered spring-extension scene plus prompt-facing annotation metadata."""

    image: Image.Image
    annotation_bboxes: List[List[float]]
    annotation_entity_ids: List[str]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]
    shown_measurement_count: int


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "mechanics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="mechanics", apply_prob=0.5)


def _with_sampling_divisor(params: Mapping[str, Any], *, divisor: int, explicit_keys: Sequence[str]) -> Mapping[str, Any]:
    """No-op hook for axis-decoupling call sites."""

    _ = int(divisor), explicit_keys
    return params


def _resolve_public_query_id(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve the public spring query family, accepting old inverse names as aliases."""

    explicit_query = params.get("query_id")
    if explicit_query is not None and str(explicit_query) in _SOLVE_FOR_BY_QUERY_ID:
        return "missing_value", {
            key: (1.0 if key == "missing_value" else 0.0)
            for key in SUPPORTED_PUBLIC_QUERY_IDS
        }
    if explicit_query is not None and str(explicit_query) in SUPPORTED_PUBLIC_QUERY_IDS:
        selected = str(explicit_query)
        return selected, {
            key: (1.0 if key == selected else 0.0)
            for key in SUPPORTED_PUBLIC_QUERY_IDS
        }

    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_PUBLIC_QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_PUBLIC_QUERY_IDS,
        balance_flag_key="balanced_query_id_sampling",
        explicit_key="query_id",
        weights_key="query_id_weights",
        sampling_namespace=f"{TASK_ID}.query_id",
    )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_solve_for(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve whether the missing value is weight or extension."""

    explicit_query = params.get("query_id")
    if explicit_query is not None and str(explicit_query) in _SOLVE_FOR_BY_QUERY_ID:
        selected = str(_SOLVE_FOR_BY_QUERY_ID[str(explicit_query)])
        return selected, {key: (1.0 if key == selected else 0.0) for key in _SUPPORTED_SOLVE_FOR_TARGETS}

    explicit_solve_for = params.get("solve_for")
    if explicit_solve_for is not None:
        selected = str(explicit_solve_for).strip().lower()
        if selected not in _SUPPORTED_SOLVE_FOR_TARGETS:
            raise ValueError(f"unsupported solve_for: {explicit_solve_for}")
        return selected, {key: (1.0 if key == selected else 0.0) for key in _SUPPORTED_SOLVE_FOR_TARGETS}

    solve_params = _with_sampling_divisor(
        params,
        divisor=len(SUPPORTED_PUBLIC_QUERY_IDS),
        explicit_keys=("solve_for",),
    )
    selected, probabilities = resolve_variant(
        rng,
        params=solve_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=_SUPPORTED_SOLVE_FOR_TARGETS,
        explicit_key="solve_for",
        weights_key="solve_for_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=solve_params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=_SUPPORTED_SOLVE_FOR_TARGETS,
        balance_flag_key="balanced_solve_for_sampling",
        explicit_key="solve_for",
        weights_key="solve_for_weights",
        sampling_namespace=f"{TASK_ID}.solve_for",
    )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_target_answer(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
) -> Tuple[int, Dict[str, float]]:
    """Resolve one balanced answer target for the active spring query."""

    if str(query_id) == "missing_weight_for_extension":
        support_key = "missing_weight_support"
        fallback = _DEFAULTS.missing_weight_support
    elif str(query_id) == "missing_extension_for_weight":
        support_key = "missing_extension_support"
        fallback = _DEFAULTS.missing_extension_support
    else:
        support_key = "extension_difference_support"
        fallback = _DEFAULTS.extension_difference_support
    target_params = dict(params)
    return resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=target_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=support_key,
        explicit_key="target_answer",
        fallback_support=fallback,
        namespace=f"{TASK_ID}.target_answer.{str(query_id)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve one compatible scene/query pair, color, and answer target."""

    axis_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.axes")
    public_query_id, query_probs = _resolve_public_query_id(
        axis_rng,
        instance_seed=int(instance_seed),
        params=params,
    )
    solve_for: str | None = None
    solve_for_probabilities: Dict[str, float] = {}
    if str(public_query_id) == "missing_value":
        solve_for, solve_for_probabilities = _resolve_solve_for(
            axis_rng,
            instance_seed=int(instance_seed),
            params=params,
        )
        query_id = str(_QUERY_ID_BY_SOLVE_FOR[str(solve_for)])
    else:
        query_id = str(public_query_id)
    scene_params = _with_sampling_divisor(
        params,
        divisor=len(SUPPORTED_QUERY_IDS),
        explicit_keys=("scene_variant",),
    )
    scene_variant, scene_probs = resolve_variant(
        axis_rng,
        params=scene_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
    )
    scene_variant = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=scene_params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(scene_variant),
        variant_probabilities=scene_probs,
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        balance_flag_key="balanced_scene_variant_sampling",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        sampling_namespace=f"{TASK_ID}.scene_variant",
    )
    target_answer, target_answer_probabilities = _resolve_target_answer(
        instance_seed=int(instance_seed),
        params=params,
        query_id=str(query_id),
    )
    color_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.accent_color_name")
    accent_color_name, accent_probs = resolve_variant(
        color_rng,
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
        variant_probabilities=accent_probs,
        supported_variants=SUPPORTED_PHYSICS_COLOR_NAMES,
        balance_flag_key="balanced_accent_color_name_sampling",
        explicit_key="accent_color_name",
        weights_key="accent_color_name_weights",
        sampling_namespace=f"{TASK_ID}.accent_color_name",
    )
    return _ResolvedAxes(
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        public_query_id=str(public_query_id),
        solve_for=(str(solve_for) if solve_for is not None else None),
        accent_color_name=str(accent_color_name),
        target_answer=int(target_answer),
        scene_variant_probabilities=dict(scene_probs),
        query_id_probabilities=dict(query_probs),
        solve_for_probabilities=dict(solve_for_probabilities),
        accent_color_name_probabilities=dict(accent_probs),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _scale_factor_support(params: Mapping[str, Any], *, query_id: str | None = None) -> Tuple[int, ...]:
    """Return the active integer scale-factor support."""

    base_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="scale_factor_support",
        fallback=_DEFAULTS.scale_factor_support,
    )
    if str(query_id) == "extension_difference":
        return resolve_integer_support(
            params,
            gen_defaults=_GEN_DEFAULTS,
            key="extension_difference_scale_factor_support",
            fallback=base_support,
        )
    return base_support


def _answer_support_key(query_id: str) -> str:
    """Return the configured answer-support key for one query id."""

    if str(query_id) == "missing_weight_for_extension":
        return "missing_weight_support"
    if str(query_id) == "missing_extension_for_weight":
        return "missing_extension_support"
    return "extension_difference_support"


def _sample_scene_spec(
    rng,
    *,
    scene_variant: str,
    query_id: str,
    target_answer: int,
    params: Mapping[str, Any],
) -> _SceneSpec:
    """Sample one spring-extension symbolic scene that realizes the target answer."""

    scale_support = _scale_factor_support(params, query_id=str(query_id))
    weight_min = int(group_default(_GEN_DEFAULTS, "weight_value_min", _DEFAULTS.weight_value_min))
    weight_max = int(group_default(_GEN_DEFAULTS, "weight_value_max", _DEFAULTS.weight_value_max))
    extension_max = int(group_default(_GEN_DEFAULTS, "extension_value_max", _DEFAULTS.extension_value_max))
    target_answer = int(target_answer)

    if str(query_id) == "missing_weight_for_extension":
        scale_candidates = [int(scale) for scale in scale_support if int(scale) * int(target_answer) <= int(extension_max)]
        if not scale_candidates:
            raise ValueError("no feasible scale factor for missing_weight_for_extension")
        scale_factor = int(rng.choice(scale_candidates))
        reference_candidates = [
            int(weight)
            for weight in range(int(weight_min), int(weight_max) + 1)
            if int(weight) != int(target_answer) and (int(weight) * int(scale_factor)) <= int(extension_max)
        ]
        if not reference_candidates:
            raise ValueError("no feasible reference weight for missing_weight_for_extension")
        left_weight = int(rng.choice(reference_candidates))
        left_extension = int(left_weight * scale_factor)
        right_extension = int(target_answer * scale_factor)
        left = _ColumnSpec(
            column_id="left",
            shown_weight_value=int(left_weight),
            true_weight_value=int(left_weight),
            shown_extension_value=int(left_extension),
            true_extension_value=int(left_extension),
            missing_weight=False,
            missing_extension=False,
            detached_weight=False,
        )
        right = _ColumnSpec(
            column_id="right",
            shown_weight_value=None,
            true_weight_value=int(target_answer),
            shown_extension_value=int(right_extension),
            true_extension_value=int(right_extension),
            missing_weight=True,
            missing_extension=False,
            detached_weight=False,
        )
        annotation_entity_ids = (
            "left_weight_block",
            "left_extension_marker",
            "right_weight_block",
            "right_extension_marker",
        )
    elif str(query_id) == "missing_extension_for_weight":
        scale_candidates = [
            int(scale)
            for scale in scale_support
            if int(target_answer) % int(scale) == 0
            and weight_min <= int(target_answer // int(scale)) <= weight_max
        ]
        if not scale_candidates:
            raise ValueError("no feasible scale factor for missing_extension_for_weight")
        scale_factor = int(rng.choice(scale_candidates))
        right_weight = int(target_answer // scale_factor)
        reference_candidates = [
            int(weight)
            for weight in range(int(weight_min), int(weight_max) + 1)
            if int(weight) != int(right_weight) and (int(weight) * int(scale_factor)) <= int(extension_max)
        ]
        if not reference_candidates:
            raise ValueError("no feasible reference weight for missing_extension_for_weight")
        left_weight = int(rng.choice(reference_candidates))
        left_extension = int(left_weight * scale_factor)
        left = _ColumnSpec(
            column_id="left",
            shown_weight_value=int(left_weight),
            true_weight_value=int(left_weight),
            shown_extension_value=int(left_extension),
            true_extension_value=int(left_extension),
            missing_weight=False,
            missing_extension=False,
            detached_weight=False,
        )
        right = _ColumnSpec(
            column_id="right",
            shown_weight_value=int(right_weight),
            true_weight_value=int(right_weight),
            shown_extension_value=None,
            true_extension_value=int(target_answer),
            missing_weight=False,
            missing_extension=True,
            detached_weight=True,
        )
        annotation_entity_ids = (
            "left_weight_block",
            "left_extension_marker",
            "right_weight_block",
            "right_extension_marker",
        )
    else:
        feasible_pairs: List[Tuple[int, int, int, int]] = []
        for scale_factor in scale_support:
            scale_value = int(scale_factor)
            if int(target_answer) % int(scale_value) != 0:
                continue
            delta = int(target_answer) // int(scale_value)
            if int(delta) <= 0:
                continue
            max_weight_for_scale = min(int(weight_max), int(extension_max) // int(scale_value))
            for lower_weight in range(int(weight_min), int(max_weight_for_scale - delta) + 1):
                upper_weight = int(lower_weight + delta)
                if int(upper_weight) > int(max_weight_for_scale):
                    continue
                feasible_pairs.append((int(scale_value), int(lower_weight), int(upper_weight), int(delta)))
        if not feasible_pairs:
            raise ValueError("no feasible weight pair for extension_difference")
        scale_factor, lower_weight, upper_weight, _ = feasible_pairs[int(rng.randrange(len(feasible_pairs)))]
        if bool(rng.randrange(2)):
            left_weight, right_weight = int(lower_weight), int(upper_weight)
        else:
            left_weight, right_weight = int(upper_weight), int(lower_weight)
        left_extension = int(left_weight * scale_factor)
        right_extension = int(right_weight * scale_factor)
        left = _ColumnSpec(
            column_id="left",
            shown_weight_value=int(left_weight),
            true_weight_value=int(left_weight),
            shown_extension_value=int(left_extension),
            true_extension_value=int(left_extension),
            missing_weight=False,
            missing_extension=False,
            detached_weight=False,
        )
        right = _ColumnSpec(
            column_id="right",
            shown_weight_value=int(right_weight),
            true_weight_value=int(right_weight),
            shown_extension_value=int(right_extension),
            true_extension_value=int(right_extension),
            missing_weight=False,
            missing_extension=False,
            detached_weight=False,
        )
        annotation_entity_ids = ("left_extension_marker", "right_extension_marker")

    return _SceneSpec(
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        scale_factor=int(scale_factor),
        left=left,
        right=right,
        target_answer=int(target_answer),
        annotation_entity_ids=tuple(str(item) for item in annotation_entity_ids),
    )


def _spring_content_bbox(render_defaults: Mapping[str, Any], *, scene_variant: str) -> List[float]:
    """Return a conservative spring-diagram bbox before whole-scene placement."""

    card_left = float(render_defaults["card_left_px"])
    card_top = float(render_defaults["card_top_px"])
    card_width = float(render_defaults["card_width_px"])
    card_height = float(render_defaults["card_height_px"])
    card_gap = float(render_defaults["card_gap_px"])
    stagger_offset = float(render_defaults["stagger_offset_y_px"]) if str(scene_variant) == "staggered_springs" else 0.0
    right_left = float(card_left + card_width + card_gap)
    right_top = float(card_top + stagger_offset)
    max_column_extra_bottom = (
        34.0
        + float(render_defaults["support_height_px"])
        + float(render_defaults["anchor_y_gap_px"])
        + float(render_defaults["ruler_top_gap_px"])
        + (float(render_defaults["ruler_value_max"]) * float(render_defaults["ruler_unit_px"]))
        + float(render_defaults["weight_box_height_px"])
    )
    left = float(card_left - 14.0)
    top = float(min(card_top, right_top) - 14.0)
    right = float(right_left + card_width + 14.0)
    bottom = max(
        float(card_top + card_height),
        float(right_top + card_height),
        float(card_top + max_column_extra_bottom),
        float(right_top + max_column_extra_bottom),
    ) + 14.0
    return [round(left, 3), round(top, 3), round(right, 3), round(bottom, 3)]


def _resolve_spring_layout_placement(
    *,
    render_defaults: Mapping[str, Any],
    params: Mapping[str, Any],
    instance_seed: int,
    scene_variant: str,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Resolve whole-spring-diagram placement before rendering and annotation projection."""

    canvas_width = int(render_defaults["canvas_width"])
    canvas_height = int(render_defaults["canvas_height"])
    content_bbox = _spring_content_bbox(render_defaults, scene_variant=str(scene_variant))
    content_left, content_top, content_right, content_bottom = [float(value) for value in content_bbox]
    jitter = resolve_layout_jitter(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.spring_layout",
    )
    min_margin = int(jitter.get("min_margin_px", 14))
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

    adjusted = dict(render_defaults)
    adjusted["card_left_px"] = int(render_defaults["card_left_px"]) + int(dx)
    adjusted["card_top_px"] = int(render_defaults["card_top_px"]) + int(dy)
    adjusted["layout_offset_x_px"] = int(dx)
    adjusted["layout_offset_y_px"] = int(dy)

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
            "mode": "whole_spring_diagram_offset",
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
    return adjusted, placement


def _draw_card_texture(draw: ImageDraw.ImageDraw, *, bbox: Sequence[float], line_rgb: Tuple[int, int, int], spacing_px: int, width_px: int) -> None:
    """Draw light diagonal texture within one spring card."""

    left, top, right, bottom = [float(value) for value in bbox]
    span = int(bottom - top)
    offset = -span
    while offset < int(right - left) + span:
        start = (float(left + offset), float(top))
        end = (float(left + offset + span), float(bottom))
        draw.line([start, end], fill=tuple(int(value) for value in line_rgb), width=int(width_px))
        offset += max(8, int(spacing_px))


def _draw_weight_block(
    draw: ImageDraw.ImageDraw,
    *,
    center_x: float,
    top_y: float,
    width_px: int,
    height_px: int,
    label_text: str,
    fill_rgb: Tuple[int, int, int],
    outline_rgb: Tuple[int, int, int],
    text_rgb: Tuple[int, int, int],
    font,
    stroke_width: int,
) -> List[float]:
    """Draw one labeled weight block and return its bbox."""

    bbox = [
        round(float(center_x - (width_px / 2.0)), 3),
        round(float(top_y), 3),
        round(float(center_x + (width_px / 2.0)), 3),
        round(float(top_y + height_px), 3),
    ]
    draw_rounded_rect(
        draw,
        bbox,
        radius=min(16, int(height_px // 3)),
        fill=tuple(int(value) for value in fill_rgb),
        outline=tuple(int(value) for value in outline_rgb),
        width=max(2, int(stroke_width)),
    )
    draw_centered_text(
        draw,
        text=str(label_text),
        center=(float(center_x), float(top_y + (height_px / 2.0))),
        font=font,
        fill=tuple(int(value) for value in text_rgb),
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(text_rgb)),
        stroke_width=max(1, int(stroke_width)),
    )
    return list(bbox)


def _draw_spring(
    draw: ImageDraw.ImageDraw,
    *,
    center_x: float,
    top_y: float,
    bottom_y: float,
    half_width_px: int,
    turn_count: int,
    line_width_px: int,
    line_rgb: Tuple[int, int, int],
    dashed: bool,
) -> List[float]:
    """Draw one vertical coil spring and return its bounding bbox."""

    if float(bottom_y) <= float(top_y) + 4.0:
        bottom_y = float(top_y) + 4.0
    points: List[Tuple[float, float]] = [(float(center_x), float(top_y))]
    total_height = float(bottom_y - top_y)
    segment_count = max(4, int(turn_count) * 2)
    for index in range(1, int(segment_count)):
        frac = float(index) / float(segment_count)
        y = float(top_y + (frac * total_height))
        x = float(center_x + (half_width_px if index % 2 else -half_width_px))
        points.append((x, y))
    points.append((float(center_x), float(bottom_y)))
    if bool(dashed):
        dash_length = 6
        for start_index in range(len(points) - 1):
            if start_index % 2:
                continue
            draw.line(
                [points[start_index], points[start_index + 1]],
                fill=tuple(int(value) for value in line_rgb),
                width=int(line_width_px),
            )
    else:
        draw.line(points, fill=tuple(int(value) for value in line_rgb), width=int(line_width_px))
    return [
        round(float(center_x - half_width_px - line_width_px), 3),
        round(float(top_y), 3),
        round(float(center_x + half_width_px + line_width_px), 3),
        round(float(bottom_y), 3),
    ]


def _draw_ruler(
    draw: ImageDraw.ImageDraw,
    *,
    x_px: float,
    top_px: float,
    unit_px: int,
    max_value: int,
    width_px: int,
    tick_long_px: int,
    tick_short_px: int,
    font,
    label_fill_rgb: Tuple[int, int, int],
    line_rgb: Tuple[int, int, int],
    stroke_width: int,
) -> List[float]:
    """Draw one vertical extension ruler and return its bbox."""

    bottom_px = float(top_px + (int(max_value) * int(unit_px)))
    draw.line(
        [(float(x_px), float(top_px)), (float(x_px), float(bottom_px))],
        fill=tuple(int(value) for value in line_rgb),
        width=max(2, int(width_px)),
    )
    for value in range(0, int(max_value) + 1):
        y = float(top_px + (int(value) * int(unit_px)))
        tick_length = int(tick_long_px if value % 2 == 0 else tick_short_px)
        draw.line(
            [(float(x_px - tick_length), y), (float(x_px), y)],
            fill=tuple(int(value) for value in line_rgb),
            width=max(2, int(width_px)),
        )
        label_center = (float(x_px - tick_length - 18), float(y))
        draw_centered_text(
            draw,
            text=str(int(value)),
            center=label_center,
            font=font,
            fill=tuple(int(value) for value in label_fill_rgb),
            stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(label_fill_rgb)),
            stroke_width=max(1, int(stroke_width)),
        )
    return [
        round(float(x_px - tick_long_px - 44), 3),
        round(float(top_px - 12), 3),
        round(float(x_px + width_px), 3),
        round(float(bottom_px + 12), 3),
    ]


def _render_column(
    draw: ImageDraw.ImageDraw,
    *,
    theme,
    spec: _ColumnSpec,
    card_bbox: Sequence[float],
    render_defaults: Mapping[str, Any],
    scene_variant: str,
    font_family: str | None = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Render one spring card and return trace metadata for the column."""

    left, top, right, bottom = [float(value) for value in card_bbox]
    card_center_x = float((left + right) / 2.0)
    support_y = float(top + 34.0)
    support_width = int(render_defaults["support_width_px"])
    support_height = int(render_defaults["support_height_px"])
    support_bbox = [
        round(float(card_center_x - (support_width / 2.0)), 3),
        round(float(support_y), 3),
        round(float(card_center_x + (support_width / 2.0)), 3),
        round(float(support_y + support_height), 3),
    ]
    draw_rounded_rect(
        draw,
        support_bbox,
        radius=int(render_defaults["support_corner_radius_px"]),
        fill=tuple(int(value) for value in theme.support_fill_rgb),
        outline=tuple(int(value) for value in theme.support_outline_rgb),
        width=3,
    )
    if str(scene_variant) == "textured_spring":
        _draw_card_texture(
            draw,
            bbox=support_bbox,
            line_rgb=tuple(int(value) for value in theme.texture_rgb),
            spacing_px=int(render_defaults["texture_spacing_px"]),
            width_px=int(render_defaults["texture_line_width_px"]),
        )

    anchor_y = float(support_bbox[3] + int(render_defaults["anchor_y_gap_px"]))
    ruler_x = float(right - int(render_defaults["ruler_right_gap_px"]))
    ruler_top = float(anchor_y + int(render_defaults["ruler_top_gap_px"]))
    ruler_bbox = _draw_ruler(
        draw,
        x_px=float(ruler_x),
        top_px=float(ruler_top),
        unit_px=int(render_defaults["ruler_unit_px"]),
        max_value=int(render_defaults["ruler_value_max"]),
        width_px=int(render_defaults["ruler_width_px"]),
        tick_long_px=int(render_defaults["ruler_tick_long_px"]),
        tick_short_px=int(render_defaults["ruler_tick_short_px"]),
        font=load_font(int(render_defaults["ruler_font_size_px"]), bold=False, font_family=font_family),
        label_fill_rgb=tuple(int(value) for value in theme.ruler_text_rgb),
        line_rgb=tuple(int(value) for value in theme.ruler_rgb),
        stroke_width=int(render_defaults["label_stroke_width_px"]),
    )

    spring_x = float(card_center_x - 26.0)
    marker_width = int(render_defaults["marker_width_px"])
    marker_height = int(render_defaults["marker_height_px"])
    weight_box_width = int(render_defaults["weight_box_width_px"])
    weight_box_height = int(render_defaults["weight_box_height_px"])
    weight_font = load_font(int(render_defaults["weight_font_size_px"]), bold=True, font_family=font_family)

    shown_extension = None if spec.shown_extension_value is None else int(spec.shown_extension_value)
    true_extension = int(spec.true_extension_value)
    spring_end_y = float(ruler_top + ((shown_extension if shown_extension is not None else int(render_defaults["spring_neutral_units"])) * int(render_defaults["ruler_unit_px"])))

    hanger_bbox = [
        round(float(spring_x - (int(render_defaults["hanger_line_width_px"]) / 2.0) - 1.0), 3),
        round(float(support_bbox[3]), 3),
        round(float(spring_x + (int(render_defaults["hanger_line_width_px"]) / 2.0) + 1.0), 3),
        round(float(anchor_y), 3),
    ]
    draw.line(
        [(float(spring_x), float(support_bbox[3])), (float(spring_x), float(anchor_y))],
        fill=tuple(int(value) for value in theme.spring_rgb),
        width=max(2, int(render_defaults["hanger_line_width_px"])),
    )

    extension_marker_bbox: List[float] | None = None
    if shown_extension is not None:
        marker_y = float(ruler_top + (shown_extension * int(render_defaults["ruler_unit_px"])))
        extension_marker_bbox = [
            round(float(ruler_x - marker_width), 3),
            round(float(marker_y - (marker_height / 2.0)), 3),
            round(float(ruler_x + 2.0), 3),
            round(float(marker_y + (marker_height / 2.0)), 3),
        ]
        draw_rounded_rect(
            draw,
            extension_marker_bbox,
            radius=max(4, int(marker_height // 2)),
            fill=tuple(int(value) for value in theme.marker_fill_rgb),
            outline=tuple(int(value) for value in theme.marker_outline_rgb),
            width=2,
        )
        draw_centered_text(
            draw,
            text=str(int(shown_extension)),
            center=(
                float((extension_marker_bbox[0] + extension_marker_bbox[2]) / 2.0),
                float((extension_marker_bbox[1] + extension_marker_bbox[3]) / 2.0),
            ),
            font=load_font(max(14, int(render_defaults["ruler_font_size_px"]) - 2), bold=True, font_family=font_family),
            fill=tuple(int(value) for value in theme.ruler_text_rgb),
            stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(theme.ruler_text_rgb)),
            stroke_width=max(1, int(render_defaults["label_stroke_width_px"]) - 1),
        )
    else:
        missing_tag_width = int(render_defaults["missing_tag_width_px"])
        missing_tag_height = int(render_defaults["missing_tag_height_px"])
        marker_center_y = float(top + int(render_defaults["missing_tag_top_gap_px"]) + (missing_tag_height / 2.0))
        extension_marker_bbox = [
            round(float(ruler_x - missing_tag_width), 3),
            round(float(marker_center_y - (missing_tag_height / 2.0)), 3),
            round(float(ruler_x + 2.0), 3),
            round(float(marker_center_y + (missing_tag_height / 2.0)), 3),
        ]
        draw_rounded_rect(
            draw,
            extension_marker_bbox,
            radius=max(6, int(missing_tag_height // 3)),
            fill=tuple(int(value) for value in theme.missing_fill_rgb),
            outline=tuple(int(value) for value in theme.missing_outline_rgb),
            width=2,
        )
        draw_centered_text(
            draw,
            text="?",
            center=(
                float((extension_marker_bbox[0] + extension_marker_bbox[2]) / 2.0),
                float((extension_marker_bbox[1] + extension_marker_bbox[3]) / 2.0),
            ),
            font=load_font(max(22, int(render_defaults["weight_font_size_px"])), bold=True, font_family=font_family),
            fill=tuple(int(value) for value in theme.missing_text_rgb),
            stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(theme.missing_text_rgb)),
            stroke_width=max(1, int(render_defaults["label_stroke_width_px"])),
        )

    spring_bbox = _draw_spring(
        draw,
        center_x=float(spring_x),
        top_y=float(anchor_y),
        bottom_y=float(spring_end_y),
        half_width_px=int(render_defaults["spring_half_width_px"]),
        turn_count=int(render_defaults["spring_turn_count"]),
        line_width_px=int(render_defaults["spring_line_width_px"]),
        line_rgb=tuple(int(value) for value in theme.spring_rgb),
        dashed=bool(spec.missing_extension),
    )

    weight_bbox: List[float] | None = None
    if bool(spec.detached_weight):
        detached_center_x = float(card_center_x + 22.0)
        detached_top_y = float(bottom - weight_box_height - 42.0)
        draw.line(
            [(float(detached_center_x), float(detached_top_y - 24.0)), (float(detached_center_x), float(detached_top_y - 6.0))],
            fill=tuple(int(value) for value in theme.spring_rgb),
            width=3,
        )
        weight_bbox = _draw_weight_block(
            draw,
            center_x=float(detached_center_x),
            top_y=float(detached_top_y),
            width_px=int(weight_box_width),
            height_px=int(weight_box_height),
            label_text=str(spec.shown_weight_value),
            fill_rgb=tuple(int(value) for value in theme.weight_fill_rgb),
            outline_rgb=tuple(int(value) for value in theme.weight_outline_rgb),
            text_rgb=tuple(int(value) for value in theme.weight_text_rgb),
            font=weight_font,
            stroke_width=int(render_defaults["label_stroke_width_px"]),
        )
    else:
        weight_top_y = float(spring_end_y)
        draw.line(
            [(float(spring_x), float(spring_end_y)), (float(spring_x), float(weight_top_y))],
            fill=tuple(int(value) for value in theme.spring_rgb),
            width=3,
        )
        if bool(spec.missing_weight):
            weight_bbox = _draw_weight_block(
                draw,
                center_x=float(spring_x),
                top_y=float(weight_top_y),
                width_px=int(weight_box_width),
                height_px=int(weight_box_height),
                label_text="?",
                fill_rgb=tuple(int(value) for value in theme.missing_fill_rgb),
                outline_rgb=tuple(int(value) for value in theme.missing_outline_rgb),
                text_rgb=tuple(int(value) for value in theme.missing_text_rgb),
                font=weight_font,
                stroke_width=int(render_defaults["label_stroke_width_px"]),
            )
        else:
            weight_bbox = _draw_weight_block(
                draw,
                center_x=float(spring_x),
                top_y=float(weight_top_y),
                width_px=int(weight_box_width),
                height_px=int(weight_box_height),
                label_text=str(spec.shown_weight_value),
                fill_rgb=tuple(int(value) for value in theme.weight_fill_rgb),
                outline_rgb=tuple(int(value) for value in theme.weight_outline_rgb),
                text_rgb=tuple(int(value) for value in theme.weight_text_rgb),
                font=weight_font,
                stroke_width=int(render_defaults["label_stroke_width_px"]),
            )

    entities = [
        {
            "entity_id": f"{spec.column_id}_card",
            "entity_type": "spring_card",
            "bbox_px": [round(float(value), 3) for value in card_bbox],
            "scene_role": spec.column_id,
        },
        {
            "entity_id": f"{spec.column_id}_support_bar",
            "entity_type": "support_bar",
            "bbox_px": list(support_bbox),
            "scene_role": spec.column_id,
        },
        {
            "entity_id": f"{spec.column_id}_spring_hanger",
            "entity_type": "spring_hanger",
            "bbox_px": list(hanger_bbox),
            "scene_role": spec.column_id,
        },
        {
            "entity_id": f"{spec.column_id}_spring_body",
            "entity_type": "spring_body",
            "bbox_px": list(spring_bbox),
            "scene_role": spec.column_id,
            "missing_extension": bool(spec.missing_extension),
        },
        {
            "entity_id": f"{spec.column_id}_ruler",
            "entity_type": "ruler",
            "bbox_px": list(ruler_bbox),
            "scene_role": spec.column_id,
        },
        {
            "entity_id": f"{spec.column_id}_extension_marker",
            "entity_type": "extension_marker" if not spec.missing_extension else "missing_extension_marker",
            "bbox_px": list(extension_marker_bbox),
            "scene_role": spec.column_id,
            "value": None if spec.shown_extension_value is None else int(spec.shown_extension_value),
            "true_value": int(true_extension),
        },
    ]
    if weight_bbox is not None:
        entities.append(
            {
                "entity_id": f"{spec.column_id}_weight_block",
                "entity_type": "missing_weight_block" if spec.missing_weight else "weight_block",
                "bbox_px": list(weight_bbox),
                "scene_role": spec.column_id,
                "value": None if spec.shown_weight_value is None else int(spec.shown_weight_value),
                "true_value": int(spec.true_weight_value),
                "detached": bool(spec.detached_weight),
            }
        )
    column_trace = {
        "column_id": str(spec.column_id),
        "shown_weight_value": None if spec.shown_weight_value is None else int(spec.shown_weight_value),
        "true_weight_value": int(spec.true_weight_value),
        "shown_extension_value": None if spec.shown_extension_value is None else int(spec.shown_extension_value),
        "true_extension_value": int(spec.true_extension_value),
        "missing_weight": bool(spec.missing_weight),
        "missing_extension": bool(spec.missing_extension),
        "detached_weight": bool(spec.detached_weight),
        "card_bbox_px": [round(float(value), 3) for value in card_bbox],
        "spring_bbox_px": list(spring_bbox),
        "hanger_bbox_px": list(hanger_bbox),
        "weight_bbox_px": None if weight_bbox is None else list(weight_bbox),
        "extension_marker_bbox_px": list(extension_marker_bbox),
    }
    return column_trace, entities


def _render_scene(
    *,
    background: Image.Image,
    render_defaults: Mapping[str, Any],
    accent_color_name: str,
    scene_spec: _SceneSpec,
    diagram_style: Any | None = None,
    font_family: str | None = None,
) -> _RenderedScene:
    """Render one spring-extension diagram and return trace metadata."""

    image = background.copy()
    draw = ImageDraw.Draw(image)
    theme = build_physics_spring_theme(str(accent_color_name), diagram_style=diagram_style)

    card_left = float(render_defaults["card_left_px"])
    card_top = float(render_defaults["card_top_px"])
    card_width = float(render_defaults["card_width_px"])
    card_height = float(render_defaults["card_height_px"])
    card_gap = float(render_defaults["card_gap_px"])
    stagger_offset = float(render_defaults["stagger_offset_y_px"])
    card_outline_width = int(render_defaults["card_outline_width_px"])
    card_radius = int(render_defaults["card_corner_radius_px"])

    left_card_bbox = [card_left, card_top, card_left + card_width, card_top + card_height]
    right_top = card_top + (stagger_offset if str(scene_spec.scene_variant) == "staggered_springs" else 0.0)
    right_left = card_left + card_width + card_gap
    right_card_bbox = [right_left, right_top, right_left + card_width, right_top + card_height]

    for card_bbox in (left_card_bbox, right_card_bbox):
        draw_rounded_rect(
            draw,
            [round(float(value), 3) for value in card_bbox],
            radius=int(card_radius),
            fill=tuple(int(value) for value in theme.card_fill_rgb),
            outline=tuple(int(value) for value in theme.card_outline_rgb),
            width=max(2, int(card_outline_width)),
        )
        if str(scene_spec.scene_variant) == "textured_spring":
            _draw_card_texture(
                draw,
                bbox=card_bbox,
                line_rgb=tuple(int(value) for value in theme.texture_rgb),
                spacing_px=int(render_defaults["texture_spacing_px"]),
                width_px=int(render_defaults["texture_line_width_px"]),
            )

    left_trace, left_entities = _render_column(
        draw,
        theme=theme,
        spec=scene_spec.left,
        card_bbox=left_card_bbox,
        render_defaults=render_defaults,
        scene_variant=str(scene_spec.scene_variant),
        font_family=font_family,
    )
    right_trace, right_entities = _render_column(
        draw,
        theme=theme,
        spec=scene_spec.right,
        card_bbox=right_card_bbox,
        render_defaults=render_defaults,
        scene_variant=str(scene_spec.scene_variant),
        font_family=font_family,
    )

    scene_entities = left_entities + right_entities
    entity_bbox_map = {
        str(entity["entity_id"]): list(entity["bbox_px"])
        for entity in scene_entities
        if entity.get("bbox_px") is not None
    }
    annotation_bboxes = [list(entity_bbox_map[entity_id]) for entity_id in scene_spec.annotation_entity_ids if entity_id in entity_bbox_map]
    shown_measurement_count = sum(
        1
        for spec in (scene_spec.left, scene_spec.right)
        if spec.shown_weight_value is not None and spec.shown_extension_value is not None
    )
    render_map = {
        "accent_color_name": str(accent_color_name),
        "technical_diagram_frame_mode": str(getattr(diagram_style, "frame_mode", "none")),
        "left_card_bbox_px": [round(float(value), 3) for value in left_card_bbox],
        "right_card_bbox_px": [round(float(value), 3) for value in right_card_bbox],
        "annotation_entity_ids": list(scene_spec.annotation_entity_ids),
        "annotation_bboxes_px": [list(bbox) for bbox in annotation_bboxes],
        "entity_bbox_map_px": {str(key): list(value) for key, value in entity_bbox_map.items()},
        "columns": {
            "left": dict(left_trace),
            "right": dict(right_trace),
        },
    }
    return _RenderedScene(
        image=image,
        annotation_bboxes=[list(bbox) for bbox in annotation_bboxes],
        annotation_entity_ids=list(scene_spec.annotation_entity_ids),
        scene_entities=[dict(entity) for entity in scene_entities],
        render_map=dict(render_map),
        shown_measurement_count=int(shown_measurement_count),
    )


def _build_prompt_examples(query_id: str) -> Tuple[str, str]:
    """Return one stable prompt JSON example for the active spring query."""

    if str(query_id) == "extension_difference":
        annotation = [[210, 222, 260, 232], [620, 274, 670, 284]]
    else:
        annotation = {
            "reference_weight": [170, 342, 248, 396],
            "reference_extension": [204, 252, 256, 262],
            "query_weight": [595, 226, 647, 260],
            "query_extension": [598, 304, 650, 314],
        }
    return build_prompt_json_examples(annotation_value=annotation, answer_type="integer")


def _spring_missing_value_annotation_map(rendered_scene: _RenderedScene) -> Dict[str, List[float]]:
    """Return role-keyed annotation boxes for the public missing-value task."""

    entity_bbox_map = dict(rendered_scene.render_map.get("entity_bbox_map_px", {}))
    return {
        "reference_weight": [float(value) for value in entity_bbox_map["left_weight_block"]],
        "reference_extension": [float(value) for value in entity_bbox_map["left_extension_marker"]],
        "query_weight": [float(value) for value in entity_bbox_map["right_weight_block"]],
        "query_extension": [float(value) for value in entity_bbox_map["right_extension_marker"]],
    }


class _PhysicsMechanicsSpringExtensionBaseTask:
    """Return one simple spring-extension proportionality question."""

    task_id = TASK_ID
    domain = "physics"
    task_group = "mechanics"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        rendered_scene: _RenderedScene | None = None
        scene_spec: _SceneSpec | None = None

        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                scene_spec = _sample_scene_spec(
                    attempt_rng,
                    scene_variant=str(axes.scene_variant),
                    query_id=str(axes.query_id),
                    target_answer=int(axes.target_answer),
                    params=params,
                )
            except ValueError:
                continue

            render_defaults = {
                key: resolve_render_int(
                    params,
                    _RENDER_DEFAULTS,
                    key,
                    int(getattr(_DEFAULTS, key)),
                    instance_seed=int(instance_seed),
                    namespace=TASK_ID,
                )
                for key in (
                    "canvas_width",
                    "canvas_height",
                    "card_width_px",
                    "card_height_px",
                    "card_left_px",
                    "card_top_px",
                    "card_gap_px",
                    "stagger_offset_y_px",
                    "card_corner_radius_px",
                    "card_outline_width_px",
                    "support_width_px",
                    "support_height_px",
                    "support_corner_radius_px",
                    "anchor_y_gap_px",
                    "hanger_line_width_px",
                    "ruler_top_gap_px",
                    "ruler_right_gap_px",
                    "ruler_value_max",
                    "ruler_unit_px",
                    "ruler_width_px",
                    "ruler_tick_long_px",
                    "ruler_tick_short_px",
                    "ruler_font_size_px",
                    "spring_neutral_units",
                    "spring_line_width_px",
                    "spring_half_width_px",
                    "spring_turn_count",
                    "weight_box_width_px",
                    "weight_box_height_px",
                    "weight_font_size_px",
                    "marker_height_px",
                    "marker_width_px",
                    "missing_tag_width_px",
                    "missing_tag_height_px",
                    "missing_tag_top_gap_px",
                    "label_stroke_width_px",
                    "texture_spacing_px",
                    "texture_line_width_px",
                )
            }
            render_defaults, layout_placement_meta = _resolve_spring_layout_placement(
                render_defaults=render_defaults,
                params=params,
                instance_seed=int(instance_seed),
                scene_variant=str(axes.scene_variant),
            )
            background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
                scene_id="spring",
                task_group=self.task_group,
                canvas_width=int(render_defaults["canvas_width"]),
                canvas_height=int(render_defaults["canvas_height"]),
                instance_seed=int(instance_seed),
                params=params,
                protected_colors=SPRING_SEMANTIC_COLORS,
            )
            font_family = sample_font_family(
                role="readout",
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.render.font_family",
                params=params,
            )
            font_record = get_font_family_record(str(font_family))
            rendered_scene = _render_scene(
                background=background,
                render_defaults=render_defaults,
                accent_color_name=str(axes.accent_color_name),
                scene_spec=scene_spec,
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
                    "answer_hint",
                    "object_description_paired_springs",
                    "object_description_staggered_springs",
                    "object_description_textured_spring",
                    "annotation_hint_missing_weight",
                    "annotation_hint_missing_extension",
                    "annotation_hint_difference",
                ),
                context=f"prompt defaults for {self.task_id}",
            )
            json_example, json_example_answer_only = _build_prompt_examples(str(axes.query_id))
            prompt_selection = render_task_prompt_variants(
                domain=self.domain,
                task_group=self.task_group,
                bundle_id=str(prompt_defaults["bundle_id"]),
                scene_key=str(prompt_defaults["scene_key"]),
                task_key=str(prompt_defaults["task_key"]),
                query_key=str(axes.public_query_id),
                answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
                slots={
                    "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                    "solve_for": str(axes.solve_for or ""),
                    "json_output_contract": str(prompt_defaults["json_output_contract"]),
                    "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                    "answer_hint": str(prompt_defaults["answer_hint"]),
                    "json_example": str(json_example),
                    "json_example_answer_only": str(json_example_answer_only),
                    "annotation_hint": str(
                        prompt_defaults["annotation_hint_difference"]
                        if str(axes.query_id) == "extension_difference"
                        else prompt_defaults["annotation_hint_missing_weight"]
                        if str(axes.query_id) == "missing_weight_for_extension"
                        else prompt_defaults["annotation_hint_missing_extension"]
                    ),
                },
                instance_seed=int(instance_seed),
            )
            prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

            answer_gt = TypedValue(type="integer", value=int(axes.target_answer))
            if str(axes.public_query_id) == "missing_value":
                annotation_value = _spring_missing_value_annotation_map(rendered_scene)
                annotation_gt = TypedValue(type="keyed_bbox_map", value=dict(annotation_value))
                projected_annotation = {
                    "type": "keyed_bbox_map",
                    "keyed_bbox_map": dict(annotation_value),
                    "pixel_keyed_bbox_map": dict(annotation_value),
                }
                rendered_scene.render_map["annotation_bbox_map_px"] = dict(annotation_value)
            else:
                annotation_value = [list(bbox) for bbox in rendered_scene.annotation_bboxes]
                annotation_gt = TypedValue(type="bbox_set", value=list(annotation_value))
                projected_annotation = {
                    "type": "bbox_set",
                    "bbox_set": list(annotation_value),
                    "pixel_bbox_set": list(annotation_value),
                }
            target_support_key = _answer_support_key(str(axes.query_id))
            complexity = build_physics_spring_extension_complexity(
                task_group_defaults=_TASK_GROUP_DEFAULTS,
                task_id=TASK_ID,
                scene_variant=str(axes.scene_variant),
                query_id=str(axes.query_id),
                target_answer=int(axes.target_answer),
                scale_factor=int(scene_spec.scale_factor),
                shown_measurement_count=int(rendered_scene.shown_measurement_count),
                annotation_count=len(rendered_scene.annotation_bboxes),
            )
            trace_payload = {
                "scene_ir": {
                    "scene_kind": f"physics_spring_extension_{str(axes.scene_variant)}",
                    "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                    "relations": {
                        "scene_variant": str(axes.scene_variant),
                        "query_id": str(axes.public_query_id),
                        "internal_query_id": str(axes.query_id),
                        "solve_for": axes.solve_for,
                        "accent_color_name": str(axes.accent_color_name),
                        "scale_factor": int(scene_spec.scale_factor),
                        "target_answer": int(axes.target_answer),
                        "annotation_entity_ids": list(rendered_scene.annotation_entity_ids),
                    },
                },
                "query_spec": {
                    "query_id": str(axes.public_query_id),
                    "template_id": str(prompt_defaults["bundle_id"]),
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                    "params": {
                        "scene_variant": str(axes.scene_variant),
                        "query_id": str(axes.public_query_id),
                        "internal_query_id": str(axes.query_id),
                        "solve_for": axes.solve_for,
                        "accent_color_name": str(axes.accent_color_name),
                        "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                        "query_id_probabilities": dict(axes.query_id_probabilities),
                        "solve_for_probabilities": dict(axes.solve_for_probabilities),
                        "accent_color_name_probabilities": dict(axes.accent_color_name_probabilities),
                        "target_answer": int(axes.target_answer),
                        "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    },
                },
                "render_spec": {
                    "scene_variant": str(axes.scene_variant),
                    "canvas_width": int(image.size[0]),
                    "canvas_height": int(image.size[1]),
                    "accent_color_name": str(axes.accent_color_name),
                    "font": {
                        "font_family": str(font_family),
                        "font_asset_version": font_asset_version(),
                        "font_asset": font_record.to_trace(),
                        "scope": "spring_diagram",
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
                    "query_id": str(axes.public_query_id),
                    "internal_query_id": str(axes.query_id),
                    "solve_for": axes.solve_for,
                    "accent_color_name": str(axes.accent_color_name),
                    "target_answer": int(axes.target_answer),
                    "target_answer_support": list(
                        resolve_integer_support(
                            params,
                            gen_defaults=_GEN_DEFAULTS,
                            key=str(target_support_key),
                            fallback=getattr(_DEFAULTS, target_support_key),
                        )
                    ),
                    "scale_factor_support": list(_scale_factor_support(params, query_id=str(axes.query_id))),
                    "scale_factor": int(scene_spec.scale_factor),
                    "left_measurement": {
                        "shown_weight_value": None if scene_spec.left.shown_weight_value is None else int(scene_spec.left.shown_weight_value),
                        "true_weight_value": int(scene_spec.left.true_weight_value),
                        "shown_extension_value": None if scene_spec.left.shown_extension_value is None else int(scene_spec.left.shown_extension_value),
                        "true_extension_value": int(scene_spec.left.true_extension_value),
                    },
                    "right_measurement": {
                        "shown_weight_value": None if scene_spec.right.shown_weight_value is None else int(scene_spec.right.shown_weight_value),
                        "true_weight_value": int(scene_spec.right.true_weight_value),
                        "shown_extension_value": None if scene_spec.right.shown_extension_value is None else int(scene_spec.right.shown_extension_value),
                        "true_extension_value": int(scene_spec.right.true_extension_value),
                    },
                    "annotation_entity_ids": list(rendered_scene.annotation_entity_ids),
                },
                "witness_symbolic": {
                    "type": "object_set",
                    "ids": [str(item) for item in rendered_scene.annotation_entity_ids],
                },
                "projected_annotation": {
                    **dict(projected_annotation),
                },
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
                query_id=str(axes.public_query_id),
                scene_id="spring",
            )

        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")


@register_task
class PhysicsMechanicsSpringMissingValueTask(
    FixedPhysicsQueryVariantTaskMixin,
    _PhysicsMechanicsSpringExtensionBaseTask,
):
    """Return a missing weight or extension from a paired spring diagram."""

    task_id = "task_physics__spring__spring_missing_value"
    fixed_query_id = "missing_value"


@register_task
class PhysicsMechanicsSpringExtensionDifferenceTask(
    FixedPhysicsQueryVariantTaskMixin,
    _PhysicsMechanicsSpringExtensionBaseTask,
):
    """Return the absolute extension difference between two spring diagrams."""

    task_id = "task_physics__spring__spring_extension_difference"
    fixed_query_id = "extension_difference"


__all__ = [
    "PhysicsMechanicsSpringExtensionDifferenceTask",
    "PhysicsMechanicsSpringMissingValueTask",
]
