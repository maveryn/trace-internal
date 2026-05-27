"""Select the labeled named icon at a requested distance rank from a named reference."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.color_format import format_named_color_with_hex
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.labeling import LABEL_POOL_A_L
from ...shared.named_colors import available_named_colors, named_color
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import draw_text_centered, load_font
from ...shared.variant_sampling import resolve_variant
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.icon_noise import serialize_icon_noise_edits
from ..shared.icon_scene import BBox, draw_single_panel, resolve_single_panel_layout, single_panel_geometry_to_trace, sort_bboxes_reading_order
from ..shared.icon_task_rendering import icon_render_style_trace, resolve_icon_render_params, resolve_icon_rgb_param, sample_icon_instance_noise
from ..shared.procedural_named_icon_field_scene import (
    bbox_center_float,
    bbox_from_center_dimensions,
    bbox_inside,
    boxes_overlap,
    label_bbox_for_icon,
    render_planned_named_icon_sprite,
    union_bbox,
    resolve_named_icon_fill_style_probabilities,
)
from ..shared.procedural_named_icons import (
    DEFAULT_PROCEDURAL_NAMED_ICON_FILL_STYLE_WEIGHTS,
    PROCEDURAL_NAMED_ICON_FILL_STYLES,
    PROCEDURAL_NAMED_ICON_SHAPES,
    procedural_named_icon_display_name,
    procedural_named_icon_fill_style_probability_map,
    render_procedural_named_icon_rgba,
    sample_procedural_named_icon_fill_style,
    validate_procedural_named_icon_fill_style_support,
)
from ..shared.public_query_task import rewrite_icons_query_output


TASK_ID = "task_icons__named_field__reference_distance_rank_label"
SCENE_ID = "named_field"
PUBLIC_QUERY_ID = "named_reference_distance_rank_label"

QUERY_IDS: Tuple[str, ...] = (
    "closest_to_named_reference_label",
    "second_closest_to_named_reference_label",
    "farthest_from_named_reference_label",
)
RANK_BY_QUERY_ID: Dict[str, int] = {
    "closest_to_named_reference_label": 0,
    "second_closest_to_named_reference_label": 1,
    "farthest_from_named_reference_label": 5,
}
OPTION_LABELS: Tuple[str, ...] = tuple(str(label) for label in LABEL_POOL_A_L[:6])
_ANGLE_POOL_DEGREES: Tuple[int, ...] = (
    -62,
    -46,
    -30,
    -14,
    4,
    20,
    38,
    56,
    124,
    140,
    158,
    176,
    194,
    212,
    230,
    248,
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable defaults for the named-reference distance-rank task."""

    candidate_count: int = 6
    distractor_count_min: int = 4
    distractor_count_max: int = 8
    canvas_width: int = 960
    canvas_height: int = 560
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    scene_icon_size_min_px: int = 50
    scene_icon_size_max_px: int = 72
    reference_icon_size_min_px: int = 58
    reference_icon_size_max_px: int = 76
    reference_icon_size_px: int = 68
    reference_panel_width_px: int = ICON_SHARED_DEFAULTS.reference_panel_width_px
    panel_gap_px: int = ICON_SHARED_DEFAULTS.panel_gap_px
    scene_max_overlap_fraction: float = 0.0
    scene_placement_max_attempts: int = 260
    scene_size_shrink_rounds: int = ICON_SHARED_DEFAULTS.scene_size_shrink_rounds
    scene_size_shrink_factor: float = ICON_SHARED_DEFAULTS.scene_size_shrink_factor
    palette_size_min: int = 8
    palette_size_max: int = 12
    color_channel_min: int = 24
    color_channel_max: int = 220
    min_color_distance: float = 40.0
    color_distance_space: str = "lab"
    background_color_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.background_color_rgb
    panel_fill_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_fill_rgb
    panel_border_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_border_rgb
    header_text_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.header_text_rgb
    icon_noise_edit_types: Tuple[str, ...] = ICON_SHARED_DEFAULTS.icon_noise_edit_types
    icon_noise_edit_count_range: Tuple[int, int] = ICON_SHARED_DEFAULTS.icon_noise_edit_count_range
    icon_noise_value_ranges: Dict[str, Dict[str, Tuple[float, float]]] = field(
        default_factory=lambda: {
            "blur": {"radius": (0.2, 0.6)},
            "downsample": {"scale": (0.85, 0.95)},
            "jpeg": {"quality": (70.0, 90.0)},
            "noise": {"alpha": (0.03, 0.08)},
        }
    )
    named_icon_fill_style_support: Tuple[str, ...] = PROCEDURAL_NAMED_ICON_FILL_STYLES
    distance_rank_margin_px: int = 24
    center_distance_min_px: int = 92
    center_distance_gap_jitter_px: int = 5
    icon_collision_gap_px: int = 8
    candidate_label_font_size_px: int = 24
    candidate_label_padding_px: int = 5
    candidate_label_gap_px: int = 4
    candidate_label_color_rgb: Tuple[int, int, int] = (52, 60, 77)
    candidate_label_background_rgb: Tuple[int, int, int] = (255, 255, 255)
    candidate_label_border_rgb: Tuple[int, int, int] = (172, 183, 204)


@dataclass(frozen=True)
class _IconPlan:
    """Semantic plan for one rendered icon."""

    role: str
    label: str
    shape_id: str
    color_name: str
    tint_rgb: Tuple[int, int, int]
    fill_style: str
    nominal_size_px: int
    rotation_degrees: int
    noise_edits: Tuple[Any, ...]
    noise_seed: int | None


@dataclass(frozen=True)
class _RenderedDistanceIcon:
    """Rendered icon metadata for the distance-rank scene."""

    instance_id: str
    role: str
    label: str
    shape_id: str
    shape_name: str
    color_name: str
    tint_rgb: Tuple[int, int, int]
    fill_style: str
    bbox_xyxy: Tuple[int, int, int, int]
    center_xy: Tuple[float, float]
    nominal_size_px: int
    rotation_degrees: int
    distance_to_reference_px: float | None
    distance_rank: int | None
    noise_edits: Tuple[Dict[str, Any], ...]
    noise_seed: int | None


@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready payload for one named-reference distance-rank scene."""

    query_id: str
    answer_label: str
    answer_rank: int
    reference_description: str
    reference_icon: _RenderedDistanceIcon
    candidate_icons: Tuple[_RenderedDistanceIcon, ...]
    distractor_icons: Tuple[_RenderedDistanceIcon, ...]
    distance_by_label: Dict[str, float]
    sorted_candidate_labels_by_distance: Tuple[str, ...]
    panel_geometry: Dict[str, Any]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    distractor_count: int


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "relation")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _shape_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("shape_id_support", group_default(_GEN_DEFAULTS, "shape_id_support", PROCEDURAL_NAMED_ICON_SHAPES))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("shape_id_support must be a sequence")
    values = tuple(dict.fromkeys(str(value) for value in raw if str(value).strip()))
    unsupported = sorted(set(values) - set(PROCEDURAL_NAMED_ICON_SHAPES))
    if unsupported:
        raise ValueError(f"unsupported procedural named icon shapes: {unsupported}")
    if len(values) < 8:
        raise ValueError("named-reference distance rank needs at least eight supported icon shapes")
    return values


def _color_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    available = {str(name): tuple(int(channel) for channel in rgb) for name, rgb in available_named_colors()}
    raw = params.get("named_color_support", group_default(_GEN_DEFAULTS, "named_color_support", tuple(available)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("named_color_support must be a sequence")
    values = tuple(dict.fromkeys(str(value).strip().lower() for value in raw if str(value).strip()))
    unsupported = sorted(set(values) - set(available))
    if unsupported:
        raise ValueError(f"unsupported named colors: {unsupported}")
    if len(values) < 4:
        raise ValueError("named-reference distance rank needs at least four named colors")
    return values


def _fill_style_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get(
        "named_icon_fill_style_support",
        group_default(_GEN_DEFAULTS, "named_icon_fill_style_support", _DEFAULTS.named_icon_fill_style_support),
    )
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raw = _DEFAULTS.named_icon_fill_style_support
    return validate_procedural_named_icon_fill_style_support(tuple(str(value) for value in raw))



def uniform_string_probability_map(values: Sequence[str], *, selected: str | None = None) -> Dict[str, float]:
    support = tuple(str(value) for value in values)
    if not support:
        return {}
    if selected is not None:
        return {str(value): (1.0 if str(value) == str(selected) else 0.0) for value in support}
    probability = 1.0 / float(len(support))
    return {str(value): float(probability) for value in support}


def _uniform_int_probability_map(values: Sequence[int], *, selected: int | None = None) -> Dict[str, float]:
    support = tuple(int(value) for value in values)
    if not support:
        return {}
    if selected is not None:
        return {str(value): (1.0 if int(value) == int(selected) else 0.0) for value in support}
    probability = 1.0 / float(len(support))
    return {str(value): float(probability) for value in support}


def _weighted_choice(rng, probabilities: Mapping[str, float]) -> str:
    threshold = float(rng.random())
    cumulative = 0.0
    items = [(str(key), float(value)) for key, value in sorted(probabilities.items()) if float(value) > 0.0]
    if not items:
        raise ValueError("probability map has no positive values")
    total = sum(float(value) for _key, value in items)
    for key, value in items:
        cumulative += float(value) / float(total)
        if threshold <= cumulative:
            return str(key)
    return str(items[-1][0])


def _resolve_query(rng, *, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    query_params = dict(params)
    explicit_variant = str(query_params.get("query_id", "") or "").strip()
    if query_params.get("distance_rank_query") is None and explicit_variant in set(QUERY_IDS):
        query_params["distance_rank_query"] = explicit_variant
    if explicit_variant == PUBLIC_QUERY_ID:
        query_params.pop("query_id", None)
    query_id, probabilities = resolve_variant(
        rng,
        params=query_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=QUERY_IDS,
        explicit_key="distance_rank_query",
        weights_key="distance_rank_query_weights",
    )
    return str(query_id), dict(probabilities)


def _resolve_answer_label(rng, *, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    explicit_label = params.get("answer_label")
    if explicit_label is not None:
        value = str(explicit_label).strip().upper()
        if value not in set(OPTION_LABELS):
            raise ValueError(f"answer_label must be one of {OPTION_LABELS}")
        return value, uniform_string_probability_map(OPTION_LABELS, selected=value)
    explicit_index = params.get("answer_index")
    if explicit_index is not None:
        index = int(explicit_index)
        if index < 0 or index >= len(OPTION_LABELS):
            raise ValueError("answer_index must be in 0..5")
        value = str(OPTION_LABELS[index])
        return value, uniform_string_probability_map(OPTION_LABELS, selected=value)
    value = str(rng.choice(OPTION_LABELS))
    return value, uniform_string_probability_map(OPTION_LABELS)


def _resolve_distractor_count(rng, *, params: Mapping[str, Any]) -> Tuple[int, Dict[str, float]]:
    low = int(params.get("distractor_count_min", group_default(_GEN_DEFAULTS, "distractor_count_min", _DEFAULTS.distractor_count_min)))
    high = int(params.get("distractor_count_max", group_default(_GEN_DEFAULTS, "distractor_count_max", _DEFAULTS.distractor_count_max)))
    if low < 0 or high < low:
        raise ValueError("invalid distractor_count_min/distractor_count_max")
    explicit = params.get("distractor_count")
    support = tuple(range(int(low), int(high) + 1))
    if explicit is not None:
        value = int(explicit)
        if value not in support:
            raise ValueError("distractor_count is outside configured support")
        return value, _uniform_int_probability_map(support, selected=value)
    value = int(rng.randint(int(low), int(high)))
    return value, _uniform_int_probability_map(support)


def _resolve_render_params(params: Mapping[str, Any], *, instance_seed: int) -> Dict[str, Any]:
    render_params = resolve_icon_render_params(
        params=params,
        render_defaults=_RENDER_DEFAULTS,
        fallback_defaults=_DEFAULTS,
        instance_seed=int(instance_seed),
    )
    for key in (
        "distance_rank_margin_px",
        "center_distance_min_px",
        "center_distance_gap_jitter_px",
        "icon_collision_gap_px",
        "candidate_label_font_size_px",
        "candidate_label_padding_px",
        "candidate_label_gap_px",
    ):
        render_params[key] = int(params.get(key, group_default(_RENDER_DEFAULTS, key, getattr(_DEFAULTS, key))))
    for key in ("candidate_label_color_rgb", "candidate_label_background_rgb", "candidate_label_border_rgb"):
        render_params[key] = resolve_icon_rgb_param(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            key=key,
            fallback=getattr(_DEFAULTS, key),
            instance_seed=int(instance_seed),
        )
    return render_params


def _sample_size(rng, *, low: int, high: int) -> int:
    return int(rng.randint(min(int(low), int(high)), max(int(low), int(high))))


def _sample_non_reference_combo(
    rng,
    *,
    shape_support: Sequence[str],
    color_support: Sequence[str],
    reference_shape_id: str,
    reference_color_name: str,
) -> Tuple[str, str]:
    for _ in range(200):
        shape_id = str(rng.choice(tuple(str(value) for value in shape_support)))
        color_name = str(rng.choice(tuple(str(value) for value in color_support)))
        if shape_id != str(reference_shape_id) or color_name != str(reference_color_name):
            return shape_id, color_name
    raise RuntimeError("failed to sample non-reference icon color/shape combo")


def _sample_icon_plans(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    render_params: Mapping[str, Any],
    answer_label: str,
    answer_rank: int,
    distractor_count: int,
) -> Tuple[Tuple[_IconPlan, ...], str, str, str, Tuple[Tuple[int, int, int], ...]]:
    shape_support = _shape_support(params)
    color_support = _color_support(params)
    fill_support = _fill_style_support(params)
    fill_probs = resolve_named_icon_fill_style_probabilities(params, _GEN_DEFAULTS, fill_support, default_weights=DEFAULT_PROCEDURAL_NAMED_ICON_FILL_STYLE_WEIGHTS)

    reference_shape_id = str(params.get("reference_shape_id", rng.choice(shape_support)))
    if reference_shape_id not in set(shape_support):
        raise ValueError(f"unsupported reference_shape_id: {reference_shape_id}")
    reference_color_name = str(params.get("reference_color_name", rng.choice(color_support))).strip().lower()
    if reference_color_name not in set(color_support):
        raise ValueError(f"unsupported reference_color_name: {reference_color_name}")
    reference_rgb = tuple(int(channel) for channel in named_color(reference_color_name))

    remaining_labels = [str(label) for label in OPTION_LABELS if str(label) != str(answer_label)]
    rng.shuffle(remaining_labels)
    labels_by_rank: List[str] = []
    for rank in range(len(OPTION_LABELS)):
        labels_by_rank.append(str(answer_label) if int(rank) == int(answer_rank) else str(remaining_labels.pop()))

    reference_size = _sample_size(
        rng,
        low=int(render_params.get("reference_icon_size_min_px", _DEFAULTS.reference_icon_size_min_px)),
        high=int(render_params.get("reference_icon_size_max_px", _DEFAULTS.reference_icon_size_max_px)),
    )
    reference_noise, reference_noise_seed = sample_icon_instance_noise(
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:reference",
        render_params=render_params,
    )
    plans: List[_IconPlan] = [
        _IconPlan(
            role="reference",
            label="",
            shape_id=str(reference_shape_id),
            color_name=str(reference_color_name),
            tint_rgb=reference_rgb,
            fill_style="solid",
            nominal_size_px=int(reference_size),
            rotation_degrees=0,
            noise_edits=tuple(reference_noise),
            noise_seed=int(reference_noise_seed),
        )
    ]

    for rank, label in enumerate(labels_by_rank):
        shape_id, color_name = _sample_non_reference_combo(
            rng,
            shape_support=shape_support,
            color_support=color_support,
            reference_shape_id=str(reference_shape_id),
            reference_color_name=str(reference_color_name),
        )
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:candidate:{label}",
            render_params=render_params,
        )
        plans.append(
            _IconPlan(
                role="candidate",
                label=str(label),
                shape_id=str(shape_id),
                color_name=str(color_name),
                tint_rgb=tuple(int(channel) for channel in named_color(str(color_name))),
                fill_style=sample_procedural_named_icon_fill_style(rng, support=fill_support, probabilities=fill_probs),
                nominal_size_px=_sample_size(
                    rng,
                    low=int(render_params["scene_icon_size_min_px"]),
                    high=int(render_params["scene_icon_size_max_px"]),
                ),
                rotation_degrees=int(rng.choice((0, 0, 0, 90, 180, 270))),
                noise_edits=tuple(noise_edits),
                noise_seed=int(noise_seed),
            )
        )

    for index in range(int(distractor_count)):
        shape_id, color_name = _sample_non_reference_combo(
            rng,
            shape_support=shape_support,
            color_support=color_support,
            reference_shape_id=str(reference_shape_id),
            reference_color_name=str(reference_color_name),
        )
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:distractor:{index}",
            render_params=render_params,
        )
        plans.append(
            _IconPlan(
                role="distractor",
                label="",
                shape_id=str(shape_id),
                color_name=str(color_name),
                tint_rgb=tuple(int(channel) for channel in named_color(str(color_name))),
                fill_style=sample_procedural_named_icon_fill_style(rng, support=fill_support, probabilities=fill_probs),
                nominal_size_px=_sample_size(
                    rng,
                    low=int(render_params["scene_icon_size_min_px"]),
                    high=int(render_params["scene_icon_size_max_px"]),
                ),
                rotation_degrees=int(rng.choice((0, 0, 0, 90, 180, 270))),
                noise_edits=tuple(noise_edits),
                noise_seed=int(noise_seed),
            )
        )

    sampled_palette_rgb = tuple(tuple(int(channel) for channel in named_color(color_name)) for color_name in color_support)
    reference_description = (
        f"{format_named_color_with_hex(reference_color_name, reference_rgb)} "
        f"{procedural_named_icon_display_name(reference_shape_id)}"
    )
    return tuple(plans), str(reference_shape_id), str(reference_color_name), str(reference_description), sampled_palette_rgb








def _occupancy_bbox_for_icon(
    *,
    icon_bbox: BBox,
    label: str,
    content_bbox: BBox,
    label_font,
    render_params: Mapping[str, Any],
) -> BBox:
    if not str(label):
        return tuple(int(value) for value in icon_bbox)
    label_bbox = label_bbox_for_icon(
        icon_bbox=tuple(int(value) for value in icon_bbox),
        label=str(label),
        content_bbox=tuple(int(value) for value in content_bbox),
        font=label_font,
        padding_px=int(render_params["candidate_label_padding_px"]),
        gap_px=int(render_params["candidate_label_gap_px"]),
    )
    return union_bbox(tuple(int(value) for value in icon_bbox), label_bbox)



def _candidate_distances(rng, *, render_params: Mapping[str, Any]) -> Tuple[float, ...]:
    margin = max(10, int(render_params["distance_rank_margin_px"]))
    min_distance = max(74, int(render_params["center_distance_min_px"]))
    jitter = max(0, int(render_params["center_distance_gap_jitter_px"]))
    values: List[float] = [float(min_distance + int(rng.randint(0, max(1, margin // 2))))]
    for _ in range(1, len(OPTION_LABELS)):
        values.append(float(values[-1] + margin + (int(rng.randint(0, jitter)) if jitter > 0 else 0)))
    return tuple(float(value) for value in values)


def _draw_candidate_label(
    *,
    image: Image.Image,
    icon_bbox: BBox,
    label: str,
    content_bbox: BBox,
    label_font,
    render_params: Mapping[str, Any],
) -> BBox:
    label_bbox = label_bbox_for_icon(
        icon_bbox=tuple(int(value) for value in icon_bbox),
        label=str(label),
        content_bbox=tuple(int(value) for value in content_bbox),
        font=label_font,
        padding_px=int(render_params["candidate_label_padding_px"]),
        gap_px=int(render_params["candidate_label_gap_px"]),
    )
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        label_bbox,
        radius=max(4, int(round(0.28 * float(label_bbox[3] - label_bbox[1])))),
        fill=tuple(int(value) for value in render_params["candidate_label_background_rgb"]) + (238,),
        outline=tuple(int(value) for value in render_params["candidate_label_border_rgb"]) + (255,),
        width=1,
    )
    draw_text_centered(
        draw,
        text=str(label),
        center=bbox_center_float(label_bbox),
        font=label_font,
        fill=tuple(int(value) for value in render_params["candidate_label_color_rgb"]),
        stroke_fill=tuple(int(value) for value in render_params["candidate_label_background_rgb"]),
        stroke_width=1,
    )
    return tuple(int(value) for value in label_bbox)


def _render_placed_scene(
    *,
    rng,
    instance_seed: int,
    query_id: str,
    answer_label: str,
    answer_rank: int,
    plans: Sequence[_IconPlan],
    reference_description: str,
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...],
    distractor_count: int,
    render_params: Mapping[str, Any],
) -> Tuple[_ScenePayload, Image.Image]:
    layout = resolve_single_panel_layout(
        canvas_width=int(render_params["canvas_width"]),
        canvas_height=int(render_params["canvas_height"]),
        outer_margin_px=int(render_params["outer_margin_px"]),
        panel_padding_px=int(render_params["panel_padding_px"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
    )
    content_bbox = tuple(int(value) for value in layout.scene_content_xyxy)
    label_font = load_font(int(render_params["candidate_label_font_size_px"]), bold=True)
    sprites = [render_planned_named_icon_sprite(plan) for plan in plans]
    reference_plan = plans[0]
    reference_sprite = sprites[0]
    candidate_plans = [plan for plan in plans if str(plan.role) == "candidate"]
    candidate_sprites = [sprites[index] for index, plan in enumerate(plans) if str(plan.role) == "candidate"]
    distractor_pairs = [(plan, sprites[index]) for index, plan in enumerate(plans) if str(plan.role) == "distractor"]

    collision_gap = int(render_params["icon_collision_gap_px"])
    max_attempts = max(1, int(render_params["scene_placement_max_attempts"]))
    last_error: Exception | None = None
    for _ in range(max_attempts):
        try:
            occupancy: List[BBox] = []
            placed_bboxes: Dict[str, BBox] = {}

            rx0 = int(content_bbox[0] + int(max(reference_sprite.size)) + 36)
            rx1 = int(content_bbox[2] - int(max(reference_sprite.size)) - 36)
            ry0 = int(content_bbox[1] + int(max(reference_sprite.size)) + 40)
            ry1 = int(content_bbox[3] - int(max(reference_sprite.size)) - 40)
            if rx1 <= rx0 or ry1 <= ry0:
                raise ValueError("content bbox too small for reference icon")
            reference_center = (float(rng.randint(rx0, rx1)), float(rng.randint(ry0, ry1)))
            reference_bbox = bbox_from_center_dimensions(
                reference_center,
                width=int(reference_sprite.size[0]),
                height=int(reference_sprite.size[1]),
            )
            if not bbox_inside(reference_bbox, content_bbox):
                raise ValueError("reference icon outside content")
            occupancy.append(reference_bbox)
            placed_bboxes["reference"] = reference_bbox

            labels_by_rank = [str(plan.label) for plan in candidate_plans]
            plans_by_label = {str(plan.label): plan for plan in candidate_plans}
            sprites_by_label = {str(plan.label): sprite for plan, sprite in zip(candidate_plans, candidate_sprites)}
            distances = _candidate_distances(rng, render_params=render_params)
            angle_values = list(_ANGLE_POOL_DEGREES)
            rng.shuffle(angle_values)
            candidate_records: List[_RenderedDistanceIcon] = []
            for rank, label in enumerate(labels_by_rank):
                plan = plans_by_label[str(label)]
                sprite = sprites_by_label[str(label)]
                distance = float(distances[int(rank)])
                placed = False
                for angle_attempt in range(len(angle_values)):
                    angle_degrees = float(angle_values[(int(rank) + int(angle_attempt)) % len(angle_values)])
                    angle = math.radians(angle_degrees)
                    center = (
                        float(reference_center[0]) + distance * math.cos(angle),
                        float(reference_center[1]) + distance * math.sin(angle),
                    )
                    bbox = bbox_from_center_dimensions(center, width=int(sprite.size[0]), height=int(sprite.size[1]))
                    occupancy_bbox = _occupancy_bbox_for_icon(
                        icon_bbox=bbox,
                        label=str(label),
                        content_bbox=content_bbox,
                        label_font=label_font,
                        render_params=render_params,
                    )
                    if not bbox_inside(occupancy_bbox, content_bbox):
                        continue
                    if any(boxes_overlap(occupancy_bbox, other, gap_px=collision_gap) for other in occupancy):
                        continue
                    occupancy.append(occupancy_bbox)
                    placed_bboxes[str(label)] = bbox
                    candidate_records.append(
                        _RenderedDistanceIcon(
                            instance_id=f"candidate_{str(label)}",
                            role="candidate",
                            label=str(label),
                            shape_id=str(plan.shape_id),
                            shape_name=procedural_named_icon_display_name(str(plan.shape_id)),
                            color_name=str(plan.color_name),
                            tint_rgb=tuple(int(value) for value in plan.tint_rgb),
                            fill_style=str(plan.fill_style),
                            bbox_xyxy=tuple(int(value) for value in bbox),
                            center_xy=bbox_center_float(bbox),
                            nominal_size_px=int(plan.nominal_size_px),
                            rotation_degrees=int(plan.rotation_degrees),
                            distance_to_reference_px=float(distance),
                            distance_rank=int(rank),
                            noise_edits=tuple(serialize_icon_noise_edits(plan.noise_edits)),
                            noise_seed=plan.noise_seed,
                        )
                    )
                    placed = True
                    break
                if not placed:
                    raise ValueError("failed to place distance-ranked candidate")

            distractor_records: List[_RenderedDistanceIcon] = []
            for index, (plan, sprite) in enumerate(distractor_pairs):
                placed = False
                for _placement_attempt in range(80):
                    cx = float(rng.randint(int(content_bbox[0] + sprite.size[0] // 2), int(content_bbox[2] - sprite.size[0] // 2)))
                    cy = float(rng.randint(int(content_bbox[1] + sprite.size[1] // 2), int(content_bbox[3] - sprite.size[1] // 2)))
                    bbox = bbox_from_center_dimensions((cx, cy), width=int(sprite.size[0]), height=int(sprite.size[1]))
                    if not bbox_inside(bbox, content_bbox):
                        continue
                    if any(boxes_overlap(bbox, other, gap_px=collision_gap) for other in occupancy):
                        continue
                    occupancy.append(bbox)
                    distance = math.hypot(float(cx) - float(reference_center[0]), float(cy) - float(reference_center[1]))
                    distractor_records.append(
                        _RenderedDistanceIcon(
                            instance_id=f"distractor_{int(index):02d}",
                            role="distractor",
                            label="",
                            shape_id=str(plan.shape_id),
                            shape_name=procedural_named_icon_display_name(str(plan.shape_id)),
                            color_name=str(plan.color_name),
                            tint_rgb=tuple(int(value) for value in plan.tint_rgb),
                            fill_style=str(plan.fill_style),
                            bbox_xyxy=tuple(int(value) for value in bbox),
                            center_xy=(float(cx), float(cy)),
                            nominal_size_px=int(plan.nominal_size_px),
                            rotation_degrees=int(plan.rotation_degrees),
                            distance_to_reference_px=float(distance),
                            distance_rank=None,
                            noise_edits=tuple(serialize_icon_noise_edits(plan.noise_edits)),
                            noise_seed=plan.noise_seed,
                        )
                    )
                    placed = True
                    break
                if not placed:
                    raise ValueError("failed to place distractor icon")

            sorted_candidates = tuple(
                sorted(candidate_records, key=lambda item: (float(item.distance_to_reference_px or 0.0), str(item.label)))
            )
            sorted_labels = tuple(str(item.label) for item in sorted_candidates)
            if sorted_labels[int(answer_rank)] != str(answer_label):
                raise ValueError("constructed candidate distances did not preserve answer rank")
            adjacent_gaps = [
                float(sorted_candidates[index + 1].distance_to_reference_px or 0.0)
                - float(sorted_candidates[index].distance_to_reference_px or 0.0)
                for index in range(len(sorted_candidates) - 1)
            ]
            if int(answer_rank) > 0 and adjacent_gaps[int(answer_rank) - 1] < float(render_params["distance_rank_margin_px"]):
                raise ValueError("distance gap before answer is too small")
            if int(answer_rank) < len(sorted_candidates) - 1 and adjacent_gaps[int(answer_rank)] < float(render_params["distance_rank_margin_px"]):
                raise ValueError("distance gap after answer is too small")

            image = Image.new("RGBA", (int(layout.canvas_width), int(layout.canvas_height)))
            draw_single_panel(
                image=image,
                layout=layout,
                background_rgb=tuple(int(value) for value in render_params["background_color_rgb"]),
                panel_fill_rgb=tuple(int(value) for value in render_params["panel_fill_rgb"]),
                panel_border_rgb=tuple(int(value) for value in render_params["panel_border_rgb"]),
                title_color_rgb=tuple(int(value) for value in render_params["header_text_rgb"]),
                corner_radius_px=int(render_params["panel_corner_radius_px"]),
                title_font_size_px=int(render_params["panel_title_font_size_px"]),
                scene_title="Scene",
            )
            image.alpha_composite(reference_sprite, (int(reference_bbox[0]), int(reference_bbox[1])))
            for record in candidate_records:
                sprite = sprites_by_label[str(record.label)]
                image.alpha_composite(sprite, (int(record.bbox_xyxy[0]), int(record.bbox_xyxy[1])))
            for record, (_plan, sprite) in zip(distractor_records, distractor_pairs):
                image.alpha_composite(sprite, (int(record.bbox_xyxy[0]), int(record.bbox_xyxy[1])))
            for record in candidate_records:
                _draw_candidate_label(
                    image=image,
                    icon_bbox=tuple(int(value) for value in record.bbox_xyxy),
                    label=str(record.label),
                    content_bbox=content_bbox,
                    label_font=label_font,
                    render_params=render_params,
                )

            reference_record = _RenderedDistanceIcon(
                instance_id="reference",
                role="reference",
                label="",
                shape_id=str(reference_plan.shape_id),
                shape_name=procedural_named_icon_display_name(str(reference_plan.shape_id)),
                color_name=str(reference_plan.color_name),
                tint_rgb=tuple(int(value) for value in reference_plan.tint_rgb),
                fill_style=str(reference_plan.fill_style),
                bbox_xyxy=tuple(int(value) for value in reference_bbox),
                center_xy=bbox_center_float(reference_bbox),
                nominal_size_px=int(reference_plan.nominal_size_px),
                rotation_degrees=int(reference_plan.rotation_degrees),
                distance_to_reference_px=None,
                distance_rank=None,
                noise_edits=tuple(serialize_icon_noise_edits(reference_plan.noise_edits)),
                noise_seed=reference_plan.noise_seed,
            )
            distance_by_label = {
                str(record.label): float(record.distance_to_reference_px or 0.0)
                for record in candidate_records
            }
            return (
                _ScenePayload(
                    query_id=str(query_id),
                    answer_label=str(answer_label),
                    answer_rank=int(answer_rank),
                    reference_description=str(reference_description),
                    reference_icon=reference_record,
                    candidate_icons=tuple(sorted(candidate_records, key=lambda item: str(item.label))),
                    distractor_icons=tuple(distractor_records),
                    distance_by_label=distance_by_label,
                    sorted_candidate_labels_by_distance=tuple(sorted_labels),
                    panel_geometry=single_panel_geometry_to_trace(layout),
                    sampled_palette_rgb=tuple(sampled_palette_rgb),
                    distractor_count=int(distractor_count),
                ),
                image.convert("RGB"),
            )
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError("failed to render named-reference distance-rank scene") from last_error


def _serialize_distance_icon(icon: _RenderedDistanceIcon) -> Dict[str, Any]:
    return {
        "entity_kind": "procedural_named_icon",
        "instance_id": str(icon.instance_id),
        "role": str(icon.role),
        "label": str(icon.label),
        "shape_id": str(icon.shape_id),
        "shape_name": str(icon.shape_name),
        "color_name": str(icon.color_name),
        "tint_rgb": [int(value) for value in icon.tint_rgb],
        "fill_style": str(icon.fill_style),
        "bbox_xyxy": [int(value) for value in icon.bbox_xyxy],
        "center_xy": [float(icon.center_xy[0]), float(icon.center_xy[1])],
        "nominal_size_px": int(icon.nominal_size_px),
        "rotation_degrees": int(icon.rotation_degrees),
        "distance_to_reference_px": None if icon.distance_to_reference_px is None else float(icon.distance_to_reference_px),
        "distance_rank": None if icon.distance_rank is None else int(icon.distance_rank),
        "noise_edits": [dict(edit) for edit in icon.noise_edits],
        "noise_seed": None if icon.noise_seed is None else int(icon.noise_seed),
    }


def _build_complexity(*, scene_payload: _ScenePayload, render_params: Mapping[str, Any]) -> TaskComplexity:
    rank_load = {
        "closest_to_named_reference_label": 0.35,
        "second_closest_to_named_reference_label": 0.75,
        "farthest_from_named_reference_label": 0.45,
    }.get(str(scene_payload.query_id), 0.50)
    clutter = min(1.0, float(len(scene_payload.candidate_icons) + len(scene_payload.distractor_icons)) / 14.0)
    distance_gap = float(render_params["distance_rank_margin_px"])
    ambiguity = max(0.0, min(1.0, 1.0 - (distance_gap / 60.0)))
    score = (0.45 * rank_load) + (0.30 * clutter) + (0.25 * ambiguity)
    return TaskComplexity(
        complexity_score=max(0.0, min(1.0, float(score))),
        complexity_components={
            "spatial_reasoning": float(rank_load),
            "visual_scan": float(clutter),
            "ambiguity": float(ambiguity),
            "clutter": float(clutter),
            "candidate_count": int(len(scene_payload.candidate_icons)),
            "distractor_count": int(len(scene_payload.distractor_icons)),
            "distance_rank_margin_px": float(distance_gap),
        },
    )


@register_task
class IconsRelationNamedReferenceDistanceRankLabelTask:
    """Select the labeled named icon nearest/farthest/second-nearest to a unique reference."""

    task_id = TASK_ID
    domain = "icons"
    task_group = "relation"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic named-reference distance-rank instance."""

        sample_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:sample")
        query_id, query_probabilities = _resolve_query(sample_rng, params=params)
        answer_rank = int(RANK_BY_QUERY_ID[str(query_id)])
        answer_label, answer_label_probabilities = _resolve_answer_label(sample_rng, params=params)
        candidate_count = int(params.get("candidate_count", group_default(_GEN_DEFAULTS, "candidate_count", _DEFAULTS.candidate_count)))
        if int(candidate_count) != len(OPTION_LABELS):
            raise ValueError("task_icons__named_field__reference_distance_rank_label requires candidate_count=6")
        distractor_count, distractor_count_probabilities = _resolve_distractor_count(sample_rng, params=params)
        render_params = _resolve_render_params(params, instance_seed=int(instance_seed))

        scene_payload = None
        image = None
        last_error: Exception | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                plans, _reference_shape_id, _reference_color_name, reference_description, sampled_palette_rgb = _sample_icon_plans(
                    sample_rng,
                    instance_seed=int(instance_seed),
                    params=params,
                    render_params=render_params,
                    answer_label=str(answer_label),
                    answer_rank=int(answer_rank),
                    distractor_count=int(distractor_count),
                )
                scene_payload, image = _render_placed_scene(
                    rng=sample_rng,
                    instance_seed=int(instance_seed),
                    query_id=str(query_id),
                    answer_label=str(answer_label),
                    answer_rank=int(answer_rank),
                    plans=plans,
                    reference_description=str(reference_description),
                    sampled_palette_rgb=tuple(sampled_palette_rgb),
                    distractor_count=int(distractor_count),
                    render_params=render_params,
                )
                break
            except Exception as exc:
                last_error = exc
                continue
        if scene_payload is None or image is None:
            raise RuntimeError("failed to generate task_icons__named_field__reference_distance_rank_label instance") from last_error

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                f"question_text_{scene_payload.query_id}",
                "evidence_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        question_text = str(prompt_defaults[f"question_text_{scene_payload.query_id}"]).format(
            reference_description=str(scene_payload.reference_description)
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(question_text),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        candidate_by_label = {str(icon.label): icon for icon in scene_payload.candidate_icons}
        answer_icon = candidate_by_label[str(scene_payload.answer_label)]
        evidence_bboxes = sort_bboxes_reading_order((answer_icon.bbox_xyxy, scene_payload.reference_icon.bbox_xyxy))
        answer_gt = TypedValue(type="option_letter", value=str(scene_payload.answer_label))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        serialized_reference = _serialize_distance_icon(scene_payload.reference_icon)
        serialized_candidates = [_serialize_distance_icon(icon) for icon in scene_payload.candidate_icons]
        serialized_distractors = [_serialize_distance_icon(icon) for icon in scene_payload.distractor_icons]

        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_named_field_distance_rank",
                "entities": [dict(serialized_reference), *serialized_candidates, *serialized_distractors],
                "relations": {
                    "target": "labeled_candidate_distance_rank_from_named_reference",
                    "query_id": str(scene_payload.query_id),
                    "reference_instance_id": str(scene_payload.reference_icon.instance_id),
                    "reference_description": str(scene_payload.reference_description),
                    "candidate_labels": [str(label) for label in OPTION_LABELS],
                    "answer_label": str(scene_payload.answer_label),
                    "answer_rank": int(scene_payload.answer_rank),
                    "sorted_candidate_labels_by_distance": list(scene_payload.sorted_candidate_labels_by_distance),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene_payload.panel_geometry),
                },
            },
            "query_spec": {
                "query_id": str(PUBLIC_QUERY_ID),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "distance_rank_query": str(scene_payload.query_id),
                    "distance_rank_query_probabilities": dict(query_probabilities),
                    "answer_label": str(scene_payload.answer_label),
                    "answer_label_probabilities": dict(answer_label_probabilities),
                    "candidate_count": int(len(scene_payload.candidate_icons)),
                    "distractor_count": int(scene_payload.distractor_count),
                    "distractor_count_probabilities": dict(distractor_count_probabilities),
                    "reference_description": str(scene_payload.reference_description),
                },
            },
            "render_spec": {
                "canvas_size": [int(render_params["canvas_width"]), int(render_params["canvas_height"])],
                "coord_space": "pixel",
                "panel_geometry": dict(scene_payload.panel_geometry),
                "style": {
                    **icon_render_style_trace(
                        render_params=render_params,
                        sampled_palette_rgb=tuple(scene_payload.sampled_palette_rgb),
                    ),
                    "candidate_label_font_size_px": int(render_params["candidate_label_font_size_px"]),
                    "candidate_label_color_rgb": [int(value) for value in render_params["candidate_label_color_rgb"]],
                    "candidate_label_background_rgb": [
                        int(value) for value in render_params["candidate_label_background_rgb"]
                    ],
                    "candidate_label_border_rgb": [int(value) for value in render_params["candidate_label_border_rgb"]],
                },
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {
                    "reference": dict(serialized_reference),
                    "candidate_icons": list(serialized_candidates),
                    "distractor_icons": list(serialized_distractors),
                    "answer_label": str(scene_payload.answer_label),
                    "answer_candidate": _serialize_distance_icon(answer_icon),
                },
            },
            "execution_trace": {
                "scene_variant": "single_panel_named_field_distance_rank",
                "query_id": str(scene_payload.query_id),
                "distance_rank_query": str(scene_payload.query_id),
                "distance_rank_query_probabilities": dict(query_probabilities),
                "answer_label": str(scene_payload.answer_label),
                "answer_label_probabilities": dict(answer_label_probabilities),
                "answer_rank": int(scene_payload.answer_rank),
                "candidate_count": int(len(scene_payload.candidate_icons)),
                "distractor_count": int(scene_payload.distractor_count),
                "distractor_count_probabilities": dict(distractor_count_probabilities),
                "reference_description": str(scene_payload.reference_description),
                "reference_instance_id": str(scene_payload.reference_icon.instance_id),
                "candidate_labels": [str(label) for label in OPTION_LABELS],
                "distance_by_label_px": {str(key): float(value) for key, value in scene_payload.distance_by_label.items()},
                "sorted_candidate_labels_by_distance": list(scene_payload.sorted_candidate_labels_by_distance),
                "question_format": "select_labeled_named_icon_by_distance_rank_from_unique_named_reference",
            },
            "witness_symbolic": {
                "query_id": str(scene_payload.query_id),
                "reference_instance_id": str(scene_payload.reference_icon.instance_id),
                "reference_description": str(scene_payload.reference_description),
                "answer_label": str(scene_payload.answer_label),
                "answer_instance_id": str(answer_icon.instance_id),
                "answer_rank": int(scene_payload.answer_rank),
                "sorted_candidate_labels_by_distance": list(scene_payload.sorted_candidate_labels_by_distance),
                "evidence_instance_ids": [str(scene_payload.reference_icon.instance_id), str(answer_icon.instance_id)],
            },
            "projected_evidence": {
                "type": "bbox_set",
                "bbox_set": list(evidence_bboxes),
                "items": [
                    {"instance_id": str(scene_payload.reference_icon.instance_id), "bbox_xyxy": list(scene_payload.reference_icon.bbox_xyxy)},
                    {"instance_id": str(answer_icon.instance_id), "bbox_xyxy": list(answer_icon.bbox_xyxy)},
                ],
            },
        }
        output = TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(scene_payload=scene_payload, render_params=render_params),
            task_versions=default_task_versions(),
            query_id=str(PUBLIC_QUERY_ID),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
        return rewrite_icons_query_output(
            output,
            query_id=str(scene_payload.query_id),
            scene_id=SCENE_ID,
            query_probabilities=query_probabilities,
        )
