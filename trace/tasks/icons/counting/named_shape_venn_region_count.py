"""Count prompt-named procedural icons in overlapping Venn regions."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.taxonomy import resolve_task_taxonomy
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.color_format import format_named_color_with_hex
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import uniform_probability_map
from ...shared.named_colors import available_named_colors, named_color
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.weighted_sampling import sample_weighted_value, weighted_probability_map
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.icon_noise import serialize_icon_noise_edits
from ..shared.icon_scene import (
    BBox,
    draw_single_panel,
    max_overlap_with_existing,
    resolve_single_panel_layout,
    single_panel_geometry_to_trace,
    sort_bboxes_reading_order,
)
from ..shared.icon_task_rendering import icon_render_style_trace, resolve_icon_render_params, sample_icon_instance_noise
from ..shared.procedural_named_icons import (
    PROCEDURAL_NAMED_ICON_FILL_STYLES,
    PROCEDURAL_NAMED_ICON_SHAPES,
    QUERYABLE_PROCEDURAL_NAMED_ICON_FILL_STYLES,
    procedural_named_icon_display_name,
    procedural_named_icon_fill_style_display_name,
    procedural_named_icon_fill_style_probability_map,
    render_procedural_named_icon_rgba,
    sample_procedural_named_icon_fill_style,
    validate_procedural_named_icon_fill_style_support,
)


TASK_ID = "task_icons__venn_field__venn_region_shape_count"
SCENE_ID = "venn_field"

QUERY_IDS: Tuple[str, ...] = (
    "inside_both_circles_count",
    "inside_either_circle_count",
    "inside_exactly_one_circle_count",
    "outside_both_circles_count",
)

TARGET_ATTRIBUTE_MODES: Tuple[str, ...] = (
    "shape_only",
    "color_shape",
    "fill_style_shape",
)

VENN_CATEGORIES: Tuple[str, ...] = ("left_only", "right_only", "both", "neither")


@dataclass(frozen=True)
class _TaskDefaults:
    object_count_min: int = 8
    object_count_max: int = 16
    target_count_min: int = 1
    target_count_max: int = 5
    target_opposite_count_min: int = 1
    target_opposite_count_max: int = 3
    canvas_width: int = 800
    canvas_height: int = 480
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    scene_icon_size_min_px: int = 40
    scene_icon_size_max_px: int = 72
    scene_max_overlap_fraction: float = 0.0
    scene_placement_max_attempts: int = 240
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    reference_panel_width_px: int = ICON_SHARED_DEFAULTS.reference_panel_width_px
    reference_icon_size_px: int = ICON_SHARED_DEFAULTS.reference_icon_size_px
    panel_gap_px: int = ICON_SHARED_DEFAULTS.panel_gap_px
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
    named_icon_fill_style_support: Tuple[str, ...] = PROCEDURAL_NAMED_ICON_FILL_STYLES
    queryable_named_icon_fill_style_support: Tuple[str, ...] = QUERYABLE_PROCEDURAL_NAMED_ICON_FILL_STYLES
    target_attribute_mode_weights: Dict[str, float] | None = None
    venn_boundary_margin_px: int = 12
    venn_left_fill_rgb: Tuple[int, int, int] = (90, 150, 235)
    venn_right_fill_rgb: Tuple[int, int, int] = (72, 190, 138)
    venn_left_outline_rgb: Tuple[int, int, int] = (38, 95, 190)
    venn_right_outline_rgb: Tuple[int, int, int] = (34, 135, 86)
    venn_fill_alpha: int = 54
    venn_outline_width_px: int = 3


@dataclass(frozen=True)
class _NamedColorEntry:
    name: str
    rgb: Tuple[int, int, int]
    label: str


@dataclass(frozen=True)
class _VennSpec:
    left_center_xy: Tuple[float, float]
    right_center_xy: Tuple[float, float]
    radius_px: float
    left_bbox_xyxy: Tuple[int, int, int, int]
    right_bbox_xyxy: Tuple[int, int, int, int]


@dataclass(frozen=True)
class _IconPlan:
    shape_id: str
    color_name: str
    tint_rgb: Tuple[int, int, int]
    fill_style: str
    venn_category: str
    matches_target: bool


@dataclass(frozen=True)
class _RenderedVennIcon:
    instance_id: str
    shape_id: str
    shape_name: str
    color_name: str
    bbox_xyxy: Tuple[int, int, int, int]
    center_xy: Tuple[float, float]
    nominal_size_px: int
    rotation_degrees: int
    tint_rgb: Tuple[int, int, int]
    fill_style: str
    venn_category: str
    inside_left_circle: bool
    inside_right_circle: bool
    matches_target: bool
    counted: bool
    noise_edits: Tuple[Dict[str, Any], ...]
    noise_seed: int | None


@dataclass(frozen=True)
class _ScenePayload:
    image: Image.Image
    panel_geometry: Dict[str, Any]
    venn: _VennSpec
    query_id: str
    target_attribute_mode: str
    target_shape_id: str
    target_shape_name: str
    target_color: _NamedColorEntry | None
    target_fill_style: str
    target_description: str
    target_count: int
    object_count: int
    instances: Tuple[_RenderedVennIcon, ...]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    query_probabilities: Dict[str, float]
    shape_probabilities: Dict[str, float]
    color_probabilities: Dict[str, float]
    fill_style_probabilities: Dict[str, float]
    target_attribute_mode_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    object_count_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _bounds(params: Mapping[str, Any], low_key: str, high_key: str, fallback_low: int, fallback_high: int) -> Tuple[int, int]:
    low = int(params.get(low_key, group_default(_GEN_DEFAULTS, low_key, fallback_low)))
    high = int(params.get(high_key, group_default(_GEN_DEFAULTS, high_key, fallback_high)))
    if low < 0 or high < low:
        raise ValueError(f"invalid {low_key}/{high_key} bounds")
    return int(low), int(high)


def _int_default(params: Mapping[str, Any], defaults: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(key, group_default(defaults, key, fallback)))


def _rgb_default(params: Mapping[str, Any], defaults: Mapping[str, Any], key: str, fallback: Sequence[int]) -> Tuple[int, int, int]:
    raw = params.get(key, group_default(defaults, key, tuple(fallback)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or len(raw) < 3:
        raw = tuple(fallback)
    return tuple(int(value) for value in raw[:3])


def _shape_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("shape_id_support", group_default(_GEN_DEFAULTS, "shape_id_support", PROCEDURAL_NAMED_ICON_SHAPES))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("shape_id_support must be a sequence")
    values = tuple(str(value) for value in raw)
    unsupported = sorted(set(values) - set(PROCEDURAL_NAMED_ICON_SHAPES))
    if unsupported:
        raise ValueError(f"unsupported procedural named icon shapes: {unsupported}")
    support = tuple(dict.fromkeys(values))
    if len(support) < 5:
        raise ValueError("shape_id_support must include at least five shapes")
    return support


def _color_support(params: Mapping[str, Any]) -> Tuple[_NamedColorEntry, ...]:
    color_by_name = {str(name): tuple(int(channel) for channel in rgb) for name, rgb in available_named_colors()}
    raw = params.get("named_color_support", group_default(_GEN_DEFAULTS, "named_color_support", tuple(color_by_name)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("named_color_support must be a sequence")
    names = tuple(dict.fromkeys(str(value).strip().lower() for value in raw if str(value).strip()))
    unsupported = sorted(set(names) - set(color_by_name))
    if unsupported:
        raise ValueError(f"unsupported named colors: {unsupported}")
    if len(names) < 2:
        raise ValueError("named_color_support must include at least two colors")
    return tuple(
        _NamedColorEntry(
            name=str(name),
            rgb=tuple(int(channel) for channel in named_color(str(name))),
            label=format_named_color_with_hex(str(name), named_color(str(name))),
        )
        for name in names
    )


def _query_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("named_venn_query_ids", group_default(_GEN_DEFAULTS, "named_venn_query_ids", QUERY_IDS))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("named_venn_query_ids must be a sequence")
    values = tuple(dict.fromkeys(str(value) for value in raw if str(value).strip()))
    unsupported = sorted(set(values) - set(QUERY_IDS))
    if unsupported:
        raise ValueError(f"unsupported named Venn query ids: {unsupported}")
    if not values:
        raise ValueError("named_venn_query_ids resolved no query ids")
    return values


def _fill_style_support(params: Mapping[str, Any], *, queryable_only: bool = False) -> Tuple[str, ...]:
    key = "queryable_named_icon_fill_style_support" if bool(queryable_only) else "named_icon_fill_style_support"
    fallback = (
        _DEFAULTS.queryable_named_icon_fill_style_support
        if bool(queryable_only)
        else _DEFAULTS.named_icon_fill_style_support
    )
    raw = params.get(key, group_default(_GEN_DEFAULTS, key, fallback))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raw = fallback
    support = validate_procedural_named_icon_fill_style_support(
        tuple(str(value) for value in raw),
        queryable_only=bool(queryable_only),
    )
    if bool(queryable_only):
        renderable = set(_fill_style_support(params, queryable_only=False))
        unsupported = sorted(set(support) - renderable)
        if unsupported:
            raise ValueError(f"queryable fill styles must also be renderable: {unsupported}")
    return support


def _fill_style_probabilities(params: Mapping[str, Any], support: Sequence[str]) -> Dict[str, float]:
    raw = params.get(
        "named_icon_fill_style_weights",
        group_default(_GEN_DEFAULTS, "named_icon_fill_style_weights", None),
    )
    if not isinstance(raw, Mapping):
        raw = None
    return procedural_named_icon_fill_style_probability_map(tuple(str(value) for value in support), dict(raw) if raw is not None else None)


def _target_mode_probabilities(params: Mapping[str, Any]) -> Dict[str, float]:
    raw = params.get("target_attribute_mode_weights", group_default(_GEN_DEFAULTS, "target_attribute_mode_weights", None))
    if not isinstance(raw, Mapping):
        raw = {"shape_only": 0.4, "color_shape": 0.35, "fill_style_shape": 0.25}
    return weighted_probability_map(TARGET_ATTRIBUTE_MODES, raw)


def _uniform_string_probability_map(values: Sequence[str], *, selected: str | None = None) -> Dict[str, float]:
    support = tuple(str(value) for value in values)
    if selected is not None:
        return {str(selected): 1.0}
    probability = 1.0 / float(len(support))
    return {str(value): probability for value in support}


def _bbox_from_center(center_xy: Sequence[float], sprite_size: Sequence[int]) -> Tuple[int, int, int, int]:
    cx, cy = float(center_xy[0]), float(center_xy[1])
    w, h = int(sprite_size[0]), int(sprite_size[1])
    x0 = int(round(cx - 0.5 * float(w)))
    y0 = int(round(cy - 0.5 * float(h)))
    return (int(x0), int(y0), int(x0 + w), int(y0 + h))


def _bbox_corners(box: Sequence[int | float]) -> Tuple[Tuple[float, float], ...]:
    x0, y0, x1, y1 = [float(value) for value in box]
    return ((x0, y0), (x1, y0), (x1, y1), (x0, y1))


def _rotation_for_shape(rng, shape_id: str) -> int:
    rotatable = {
        "triangle",
        "pentagon",
        "hexagon",
        "octagon",
        "arrow",
        "lightning_bolt",
        "leaf",
        "flag",
        "capsule",
        "teardrop",
        "hourglass",
        "key",
        "ladder",
        "kite",
        "rocket",
        "pencil",
    }
    if str(shape_id) not in rotatable:
        return 0
    return int(rng.choice((0, 90, 180, 270))) % 360


def _sample_venn_spec(rng, *, content_bbox: BBox) -> _VennSpec:
    x0, y0, x1, y1 = [float(value) for value in content_bbox]
    width = float(x1 - x0)
    height = float(y1 - y0)
    radius = float(min(width * 0.24, height * 0.43))
    radius = float(max(118.0, min(radius, 158.0)))
    separation = float(radius * rng.uniform(1.02, 1.18))
    center_x = 0.5 * float(x0 + x1)
    center_y = float(y0) + (0.50 * height)
    left_center = (center_x - (0.5 * separation), center_y)
    right_center = (center_x + (0.5 * separation), center_y)

    def _circle_bbox(center: Sequence[float]) -> Tuple[int, int, int, int]:
        cx, cy = float(center[0]), float(center[1])
        return (
            int(round(cx - radius)),
            int(round(cy - radius)),
            int(round(cx + radius)),
            int(round(cy + radius)),
        )

    return _VennSpec(
        left_center_xy=(float(left_center[0]), float(left_center[1])),
        right_center_xy=(float(right_center[0]), float(right_center[1])),
        radius_px=float(radius),
        left_bbox_xyxy=_circle_bbox(left_center),
        right_bbox_xyxy=_circle_bbox(right_center),
    )


def _corner_distances_to_circle(box: Sequence[int | float], center_xy: Sequence[float]) -> Tuple[float, ...]:
    cx, cy = float(center_xy[0]), float(center_xy[1])
    return tuple(math.hypot(float(x) - cx, float(y) - cy) for x, y in _bbox_corners(box))


def _bbox_inside_circle(box: Sequence[int | float], *, center_xy: Sequence[float], radius_px: float, margin_px: int) -> bool:
    threshold = float(radius_px) - float(max(0, int(margin_px)))
    if threshold <= 0.0:
        return False
    return all(float(distance) <= threshold for distance in _corner_distances_to_circle(box, center_xy))


def _bbox_outside_circle(box: Sequence[int | float], *, center_xy: Sequence[float], radius_px: float, margin_px: int) -> bool:
    cx, cy = float(center_xy[0]), float(center_xy[1])
    x0, y0, x1, y1 = [float(value) for value in box]
    nearest_x = min(max(cx, x0), x1)
    nearest_y = min(max(cy, y0), y1)
    return math.hypot(nearest_x - cx, nearest_y - cy) >= float(radius_px) + float(max(0, int(margin_px)))


def _bbox_venn_category(venn: _VennSpec, box: Sequence[int | float], *, margin_px: int) -> str | None:
    left_inside = _bbox_inside_circle(box, center_xy=venn.left_center_xy, radius_px=venn.radius_px, margin_px=int(margin_px))
    right_inside = _bbox_inside_circle(box, center_xy=venn.right_center_xy, radius_px=venn.radius_px, margin_px=int(margin_px))
    left_outside = _bbox_outside_circle(box, center_xy=venn.left_center_xy, radius_px=venn.radius_px, margin_px=int(margin_px))
    right_outside = _bbox_outside_circle(box, center_xy=venn.right_center_xy, radius_px=venn.radius_px, margin_px=int(margin_px))
    if left_inside and right_inside:
        return "both"
    if left_inside and right_outside:
        return "left_only"
    if left_outside and right_inside:
        return "right_only"
    if left_outside and right_outside:
        return "neither"
    return None


def _category_membership(category: str) -> Tuple[bool, bool]:
    if str(category) == "both":
        return True, True
    if str(category) == "left_only":
        return True, False
    if str(category) == "right_only":
        return False, True
    if str(category) == "neither":
        return False, False
    raise ValueError(f"unsupported Venn category: {category}")


def _counted_categories(query_id: str) -> Tuple[str, ...]:
    if str(query_id) == "inside_both_circles_count":
        return ("both",)
    if str(query_id) == "inside_either_circle_count":
        return ("left_only", "right_only", "both")
    if str(query_id) == "inside_exactly_one_circle_count":
        return ("left_only", "right_only")
    if str(query_id) == "outside_both_circles_count":
        return ("neither",)
    raise ValueError(f"unsupported query_id: {query_id}")


def _target_description(*, mode: str, shape_name: str, target_color: _NamedColorEntry | None, target_fill_style: str) -> str:
    quoted_shape = f'"{shape_name}"'
    if str(mode) == "shape_only":
        return f"{quoted_shape} icons"
    if str(mode) == "color_shape":
        if target_color is None:
            raise ValueError("color_shape target is missing target_color")
        return f"{target_color.label} {quoted_shape} icons"
    if str(mode) == "fill_style_shape":
        return f"{procedural_named_icon_fill_style_display_name(str(target_fill_style))} {quoted_shape} icons"
    raise ValueError(f"unsupported target mode: {mode}")


def _sample_nonmatching_icon(
    rng,
    *,
    mode: str,
    target_shape_id: str,
    target_color: _NamedColorEntry | None,
    target_fill_style: str,
    shape_support: Sequence[str],
    color_support: Sequence[_NamedColorEntry],
    fill_style_support: Sequence[str],
    fill_style_probabilities: Mapping[str, float],
) -> Tuple[str, _NamedColorEntry, str]:
    other_shapes = [str(value) for value in shape_support if str(value) != str(target_shape_id)]
    if not other_shapes:
        raise ValueError("shape support resolved no distractor shapes")
    color_by_name = {str(entry.name): entry for entry in color_support}
    if str(mode) == "shape_only":
        shape_id = str(rng.choice(other_shapes))
        color = rng.choice(color_support)
        fill_style = sample_procedural_named_icon_fill_style(rng, support=fill_style_support, probabilities=fill_style_probabilities)
        return str(shape_id), color, str(fill_style)

    draw = float(rng.random())
    if str(mode) == "color_shape":
        if target_color is None:
            raise ValueError("color_shape distractor is missing target_color")
        other_colors = [entry for entry in color_support if str(entry.name) != str(target_color.name)]
        if draw < 0.40 and other_colors:
            shape_id = str(target_shape_id)
            color = rng.choice(other_colors)
        elif draw < 0.78:
            shape_id = str(rng.choice(other_shapes))
            color = target_color
        else:
            shape_id = str(rng.choice(other_shapes))
            color = rng.choice(other_colors or list(color_support))
        fill_style = sample_procedural_named_icon_fill_style(rng, support=fill_style_support, probabilities=fill_style_probabilities)
        return str(shape_id), color_by_name[str(color.name)], str(fill_style)

    other_fill_styles = [str(value) for value in fill_style_support if str(value) != str(target_fill_style)]
    if draw < 0.40 and other_fill_styles:
        shape_id = str(target_shape_id)
        fill_style = str(rng.choice(other_fill_styles))
    elif draw < 0.78:
        shape_id = str(rng.choice(other_shapes))
        fill_style = str(target_fill_style)
    else:
        shape_id = str(rng.choice(other_shapes))
        fill_style = str(rng.choice(other_fill_styles or list(fill_style_support)))
    color = rng.choice(color_support)
    return str(shape_id), color_by_name[str(color.name)], str(fill_style)


def _make_plans(
    *,
    rng,
    query_id: str,
    mode: str,
    target_count: int,
    object_count: int,
    target_opposite_count: int,
    target_shape_id: str,
    target_color: _NamedColorEntry | None,
    target_fill_style: str,
    shape_support: Sequence[str],
    color_support: Sequence[_NamedColorEntry],
    fill_style_support: Sequence[str],
    fill_style_probabilities: Mapping[str, float],
) -> Tuple[_IconPlan, ...]:
    counted_categories = tuple(_counted_categories(str(query_id)))
    non_counted_categories = tuple(str(value) for value in VENN_CATEGORIES if str(value) not in set(counted_categories))
    if not non_counted_categories:
        raise ValueError("Venn task resolved no non-counted target distractor categories")
    color_by_name = {str(entry.name): entry for entry in color_support}
    if str(mode) == "color_shape":
        if target_color is None:
            raise ValueError("color_shape plan is missing target color")
        target_color_entry = color_by_name[str(target_color.name)]
    else:
        target_color_entry = rng.choice(color_support)
    plans: list[_IconPlan] = []

    def _target_plan(category: str) -> _IconPlan:
        color = target_color_entry if str(mode) == "color_shape" else rng.choice(color_support)
        fill_style = (
            str(target_fill_style)
            if str(mode) == "fill_style_shape"
            else sample_procedural_named_icon_fill_style(rng, support=fill_style_support, probabilities=fill_style_probabilities)
        )
        return _IconPlan(
            shape_id=str(target_shape_id),
            color_name=str(color.name),
            tint_rgb=tuple(int(channel) for channel in color.rgb),
            fill_style=str(fill_style),
            venn_category=str(category),
            matches_target=True,
        )

    for _ in range(int(target_count)):
        plans.append(_target_plan(str(rng.choice(counted_categories))))
    for _ in range(int(target_opposite_count)):
        plans.append(_target_plan(str(rng.choice(non_counted_categories))))

    while len(plans) < int(object_count):
        shape_id, color, fill_style = _sample_nonmatching_icon(
            rng,
            mode=str(mode),
            target_shape_id=str(target_shape_id),
            target_color=target_color,
            target_fill_style=str(target_fill_style),
            shape_support=shape_support,
            color_support=color_support,
            fill_style_support=fill_style_support,
            fill_style_probabilities=fill_style_probabilities,
        )
        plans.append(
            _IconPlan(
                shape_id=str(shape_id),
                color_name=str(color.name),
                tint_rgb=tuple(int(channel) for channel in color.rgb),
                fill_style=str(fill_style),
                venn_category=str(rng.choice(VENN_CATEGORIES)),
                matches_target=False,
            )
        )
    rng.shuffle(plans)
    return tuple(plans)


def _draw_venn_underlay(image: Image.Image, *, venn: _VennSpec, render_params: Mapping[str, Any]) -> None:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    alpha = int(render_params["venn_fill_alpha"])
    draw.ellipse(
        tuple(int(value) for value in venn.left_bbox_xyxy),
        fill=tuple(int(value) for value in render_params["venn_left_fill_rgb"]) + (alpha,),
    )
    draw.ellipse(
        tuple(int(value) for value in venn.right_bbox_xyxy),
        fill=tuple(int(value) for value in render_params["venn_right_fill_rgb"]) + (alpha,),
    )
    image.alpha_composite(overlay)


def _draw_venn_outline(image: Image.Image, *, venn: _VennSpec, render_params: Mapping[str, Any]) -> None:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width = max(1, int(render_params["venn_outline_width_px"]))
    draw.ellipse(
        tuple(int(value) for value in venn.left_bbox_xyxy),
        outline=tuple(int(value) for value in render_params["venn_left_outline_rgb"]) + (235,),
        width=width,
    )
    draw.ellipse(
        tuple(int(value) for value in venn.right_bbox_xyxy),
        outline=tuple(int(value) for value in render_params["venn_right_outline_rgb"]) + (235,),
        width=width,
    )
    image.alpha_composite(overlay)


def _sample_center_for_category(
    rng,
    *,
    content_bbox: BBox,
    sprite_size: Tuple[int, int],
    venn: _VennSpec,
    category: str,
    margin_px: int,
) -> Tuple[float, float, Tuple[int, int, int, int]]:
    x0, y0, x1, y1 = [int(value) for value in content_bbox]
    half_w = 0.5 * float(sprite_size[0])
    half_h = 0.5 * float(sprite_size[1])
    min_x = float(x0) + half_w
    max_x = float(x1) - half_w
    min_y = float(y0) + half_h
    max_y = float(y1) - half_h
    if min_x >= max_x or min_y >= max_y:
        raise ValueError("sprite does not fit content bbox")
    for _ in range(1200):
        cx = float(rng.uniform(min_x, max_x))
        cy = float(rng.uniform(min_y, max_y))
        bbox = _bbox_from_center((cx, cy), sprite_size)
        if _bbox_venn_category(venn, bbox, margin_px=int(margin_px)) == str(category):
            return float(cx), float(cy), tuple(int(value) for value in bbox)
    raise ValueError(f"could not sample icon center in Venn category {category}")


def _venn_to_trace(venn: _VennSpec) -> Dict[str, Any]:
    return {
        "left_circle": {
            "center_xy": [float(value) for value in venn.left_center_xy],
            "radius_px": float(venn.radius_px),
            "bbox_xyxy": [int(value) for value in venn.left_bbox_xyxy],
        },
        "right_circle": {
            "center_xy": [float(value) for value in venn.right_center_xy],
            "radius_px": float(venn.radius_px),
            "bbox_xyxy": [int(value) for value in venn.right_bbox_xyxy],
        },
    }


def _serialize_icon(instance: _RenderedVennIcon) -> Dict[str, Any]:
    return {
        "entity_kind": "procedural_named_icon",
        "instance_id": str(instance.instance_id),
        "shape_id": str(instance.shape_id),
        "shape_name": str(instance.shape_name),
        "color_name": str(instance.color_name),
        "bbox_xyxy": [int(value) for value in instance.bbox_xyxy],
        "center_xy": [float(value) for value in instance.center_xy],
        "nominal_size_px": int(instance.nominal_size_px),
        "rotation_degrees": int(instance.rotation_degrees),
        "tint_rgb": [int(value) for value in instance.tint_rgb],
        "fill_style": str(instance.fill_style),
        "venn_category": str(instance.venn_category),
        "inside_left_circle": bool(instance.inside_left_circle),
        "inside_right_circle": bool(instance.inside_right_circle),
        "matches_target": bool(instance.matches_target),
        "counted": bool(instance.counted),
        "noise_edits": [dict(edit) for edit in instance.noise_edits],
        "noise_seed": None if instance.noise_seed is None else int(instance.noise_seed),
    }


def _make_scene(*, instance_seed: int, params: Mapping[str, Any], render_params: Mapping[str, Any], attempt: int) -> _ScenePayload:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:scene", int(attempt))
    layout = resolve_single_panel_layout(
        canvas_width=int(render_params["canvas_width"]),
        canvas_height=int(render_params["canvas_height"]),
        outer_margin_px=int(render_params["outer_margin_px"]),
        panel_padding_px=int(render_params["panel_padding_px"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
    )
    content_bbox = tuple(int(value) for value in layout.scene_content_xyxy)
    venn = _sample_venn_spec(rng, content_bbox=content_bbox)

    query_support = _query_support(params)
    explicit_query = params.get("query_id", params.get("named_venn_query_id"))
    if explicit_query is not None:
        query_id = str(explicit_query)
        if query_id not in set(query_support):
            raise ValueError(f"query_id must be one of {query_support}")
    else:
        query_id = str(rng.choice(query_support))

    mode_probabilities = _target_mode_probabilities(params)
    explicit_mode = params.get("target_attribute_mode")
    if explicit_mode is not None:
        target_attribute_mode = str(explicit_mode)
        if target_attribute_mode not in set(TARGET_ATTRIBUTE_MODES):
            raise ValueError(f"target_attribute_mode must be one of {TARGET_ATTRIBUTE_MODES}")
    else:
        target_attribute_mode = str(sample_weighted_value(rng, TARGET_ATTRIBUTE_MODES, mode_probabilities))

    shape_support = _shape_support(params)
    explicit_shape = params.get("shape_id", params.get("target_shape_id"))
    if explicit_shape is not None:
        target_shape_id = str(explicit_shape)
        if target_shape_id not in set(shape_support):
            raise ValueError(f"target shape must be one of {shape_support}")
    else:
        target_shape_id = str(rng.choice(shape_support))
    target_shape_name = procedural_named_icon_display_name(str(target_shape_id))

    color_support = _color_support(params)
    color_by_name = {str(entry.name): entry for entry in color_support}
    fill_style_support = _fill_style_support(params, queryable_only=False)
    queryable_fill_style_support = _fill_style_support(params, queryable_only=True)
    fill_style_probabilities = _fill_style_probabilities(params, fill_style_support)

    target_color: _NamedColorEntry | None = None
    target_fill_style = ""
    explicit_color = params.get("color_name", params.get("target_color_name"))
    explicit_fill_style = params.get("fill_style", params.get("target_fill_style"))
    if str(target_attribute_mode) == "color_shape":
        if explicit_color is not None:
            color_name = str(explicit_color).strip().lower()
            if color_name not in color_by_name:
                raise ValueError(f"target color must be one of {tuple(color_by_name)}")
        else:
            color_name = str(rng.choice(color_support).name)
        target_color = color_by_name[str(color_name)]
    elif str(target_attribute_mode) == "fill_style_shape":
        if explicit_fill_style is not None:
            target_fill_style = str(explicit_fill_style).strip()
            if target_fill_style not in set(queryable_fill_style_support):
                raise ValueError(f"target fill style must be one of {queryable_fill_style_support}")
        else:
            target_fill_style = str(rng.choice(queryable_fill_style_support))

    answer_min, answer_max = _bounds(params, "target_count_min", "target_count_max", _DEFAULTS.target_count_min, _DEFAULTS.target_count_max)
    object_min, object_max = _bounds(params, "object_count_min", "object_count_max", _DEFAULTS.object_count_min, _DEFAULTS.object_count_max)
    opposite_min, opposite_max = _bounds(
        params,
        "target_opposite_count_min",
        "target_opposite_count_max",
        _DEFAULTS.target_opposite_count_min,
        _DEFAULTS.target_opposite_count_max,
    )
    answer_support = tuple(range(int(answer_min), int(answer_max) + 1))
    target_count_probabilities = weighted_probability_map(
        answer_support,
        params.get("target_count_weights", group_default(_GEN_DEFAULTS, "target_count_weights", None)),
    )
    explicit_target = params.get("target_count", params.get("target_answer"))
    if explicit_target is not None:
        target_count = int(explicit_target)
        if target_count not in set(answer_support):
            raise ValueError(f"target_count must be in {answer_support}")
    else:
        target_count = int(sample_weighted_value(rng, answer_support, target_count_probabilities))
    target_opposite_count = int(rng.randint(int(opposite_min), int(opposite_max)))
    min_object_count = max(int(object_min), int(target_count) + int(target_opposite_count) + 4)
    if min_object_count > int(object_max):
        raise ValueError("object_count range cannot support requested target/opposite counts")
    object_support = tuple(range(int(min_object_count), int(object_max) + 1))
    explicit_object = params.get("object_count")
    if explicit_object is not None:
        object_count = int(explicit_object)
        if object_count not in set(object_support):
            raise ValueError(f"object_count must be in {object_support}")
    else:
        object_count = int(rng.choice(object_support))

    plans = _make_plans(
        rng=rng,
        query_id=str(query_id),
        mode=str(target_attribute_mode),
        target_count=int(target_count),
        object_count=int(object_count),
        target_opposite_count=int(target_opposite_count),
        target_shape_id=str(target_shape_id),
        target_color=target_color,
        target_fill_style=str(target_fill_style),
        shape_support=shape_support,
        color_support=color_support,
        fill_style_support=fill_style_support,
        fill_style_probabilities=fill_style_probabilities,
    )

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
    _draw_venn_underlay(image, venn=venn, render_params=render_params)

    min_size = max(12, int(render_params["scene_icon_size_min_px"]))
    max_size = max(min_size, int(render_params["scene_icon_size_max_px"]))
    existing_bboxes: list[BBox] = []
    rendered: list[_RenderedVennIcon] = []
    margin_px = int(render_params["venn_boundary_margin_px"])
    counted_categories = set(_counted_categories(str(query_id)))
    for index, plan in enumerate(plans):
        placed = False
        nominal_size = int(rng.randint(int(min_size), int(max_size)))
        rotation = _rotation_for_shape(rng, str(plan.shape_id))
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:named_icon_{int(index)}",
            render_params=render_params,
        )
        for shrink_round in range(7):
            candidate_size = max(28, int(round(float(nominal_size) * (0.92 ** int(shrink_round)))))
            sprite = render_procedural_named_icon_rgba(
                shape_id=str(plan.shape_id),
                size_px=int(candidate_size),
                tint_rgb=tuple(int(value) for value in plan.tint_rgb),
                fill_style=str(plan.fill_style),
                rotation_degrees=int(rotation),
                mirror_x=False,
                noise_edits=tuple(noise_edits),
                noise_seed=int(noise_seed),
            )
            for _ in range(int(render_params["scene_placement_max_attempts"])):
                cx, cy, bbox = _sample_center_for_category(
                    rng,
                    content_bbox=content_bbox,
                    sprite_size=tuple(int(value) for value in sprite.size),
                    venn=venn,
                    category=str(plan.venn_category),
                    margin_px=int(margin_px),
                )
                if max_overlap_with_existing(bbox, existing_bboxes) > float(render_params["scene_max_overlap_fraction"]):
                    continue
                image.alpha_composite(sprite, (int(bbox[0]), int(bbox[1])))
                left_inside, right_inside = _category_membership(str(plan.venn_category))
                counted = bool(plan.matches_target and str(plan.venn_category) in counted_categories)
                rendered.append(
                    _RenderedVennIcon(
                        instance_id=f"named_venn_icon_{int(index):02d}",
                        shape_id=str(plan.shape_id),
                        shape_name=procedural_named_icon_display_name(str(plan.shape_id)),
                        color_name=str(plan.color_name),
                        bbox_xyxy=tuple(int(value) for value in bbox),
                        center_xy=(float(cx), float(cy)),
                        nominal_size_px=int(candidate_size),
                        rotation_degrees=int(rotation),
                        tint_rgb=tuple(int(value) for value in plan.tint_rgb),
                        fill_style=str(plan.fill_style),
                        venn_category=str(plan.venn_category),
                        inside_left_circle=bool(left_inside),
                        inside_right_circle=bool(right_inside),
                        matches_target=bool(plan.matches_target),
                        counted=bool(counted),
                        noise_edits=serialize_icon_noise_edits(tuple(noise_edits)),
                        noise_seed=int(noise_seed),
                    )
                )
                existing_bboxes.append(tuple(int(value) for value in bbox))
                placed = True
                break
            if placed:
                break
        if not placed:
            raise ValueError("could not place named Venn icon with requested membership")

    _draw_venn_outline(image, venn=venn, render_params=render_params)
    counted_count = sum(1 for instance in rendered if instance.counted)
    if int(counted_count) != int(target_count):
        raise RuntimeError("rendered Venn count did not match target answer")

    return _ScenePayload(
        image=image.convert("RGB"),
        panel_geometry=single_panel_geometry_to_trace(layout),
        venn=venn,
        query_id=str(query_id),
        target_attribute_mode=str(target_attribute_mode),
        target_shape_id=str(target_shape_id),
        target_shape_name=str(target_shape_name),
        target_color=target_color,
        target_fill_style=str(target_fill_style),
        target_description=_target_description(
            mode=str(target_attribute_mode),
            shape_name=str(target_shape_name),
            target_color=target_color,
            target_fill_style=str(target_fill_style),
        ),
        target_count=int(target_count),
        object_count=int(object_count),
        instances=tuple(rendered),
        sampled_palette_rgb=tuple(tuple(int(channel) for channel in entry.rgb) for entry in color_support),
        query_probabilities=_uniform_string_probability_map(query_support, selected=str(query_id) if explicit_query is not None else None),
        shape_probabilities=_uniform_string_probability_map(shape_support, selected=str(target_shape_id) if explicit_shape is not None else None),
        color_probabilities=_uniform_string_probability_map(
            tuple(str(entry.name) for entry in color_support),
            selected=str(target_color.name) if explicit_color is not None and target_color is not None else None,
        ),
        fill_style_probabilities=dict(fill_style_probabilities),
        target_attribute_mode_probabilities=dict(mode_probabilities),
        target_count_probabilities=dict(uniform_probability_map(answer_support, selected=int(target_count)) if explicit_target is not None else target_count_probabilities),
        object_count_probabilities=dict(uniform_probability_map(object_support, selected=int(object_count) if explicit_object is not None else None)),
    )


def _complexity(scene: _ScenePayload, *, render_params: Mapping[str, Any]) -> TaskComplexity:
    answer_load = (int(scene.target_count) - _DEFAULTS.target_count_min) / max(1, _DEFAULTS.target_count_max - _DEFAULTS.target_count_min)
    object_load = (int(scene.object_count) - _DEFAULTS.object_count_min) / max(1, _DEFAULTS.object_count_max - _DEFAULTS.object_count_min)
    query_difficulty = {
        "inside_both_circles_count": 0.58,
        "inside_either_circle_count": 0.68,
        "inside_exactly_one_circle_count": 0.74,
        "outside_both_circles_count": 0.50,
    }[str(scene.query_id)]
    attribute_difficulty = {
        "shape_only": 0.20,
        "color_shape": 0.45,
        "fill_style_shape": 0.55,
    }[str(scene.target_attribute_mode)]
    shape_diversity = len(set(instance.shape_id for instance in scene.instances)) / max(1.0, float(scene.object_count))
    score = (
        0.24 * max(0.0, min(1.0, answer_load))
        + 0.20 * max(0.0, min(1.0, object_load))
        + 0.26 * float(query_difficulty)
        + 0.18 * float(attribute_difficulty)
        + 0.12 * max(0.0, min(1.0, shape_diversity))
    )
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "answer_load": round(float(answer_load), 6),
            "object_load": round(float(object_load), 6),
            "query_difficulty": round(float(query_difficulty), 6),
            "attribute_difficulty": round(float(attribute_difficulty), 6),
            "shape_diversity": round(float(shape_diversity), 6),
            "query_id": str(scene.query_id),
            "target_attribute_mode": str(scene.target_attribute_mode),
            "target_shape_id": str(scene.target_shape_id),
            "target_count": int(scene.target_count),
            "object_count": int(scene.object_count),
            "scene_icon_size_min_px": int(render_params["scene_icon_size_min_px"]),
            "scene_icon_size_max_px": int(render_params["scene_icon_size_max_px"]),
        },
    )


@register_task
class IconsCountingNamedShapeVennRegionCountTask:
    """Count named procedural icons satisfying a Venn-region predicate."""

    task_id = TASK_ID
    domain = "icons"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        render_params = resolve_icon_render_params(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        render_params["venn_boundary_margin_px"] = _int_default(
            params,
            _RENDER_DEFAULTS,
            "venn_boundary_margin_px",
            _DEFAULTS.venn_boundary_margin_px,
        )
        render_params["venn_left_fill_rgb"] = _rgb_default(params, _RENDER_DEFAULTS, "venn_left_fill_rgb", _DEFAULTS.venn_left_fill_rgb)
        render_params["venn_right_fill_rgb"] = _rgb_default(params, _RENDER_DEFAULTS, "venn_right_fill_rgb", _DEFAULTS.venn_right_fill_rgb)
        render_params["venn_left_outline_rgb"] = _rgb_default(
            params,
            _RENDER_DEFAULTS,
            "venn_left_outline_rgb",
            _DEFAULTS.venn_left_outline_rgb,
        )
        render_params["venn_right_outline_rgb"] = _rgb_default(
            params,
            _RENDER_DEFAULTS,
            "venn_right_outline_rgb",
            _DEFAULTS.venn_right_outline_rgb,
        )
        render_params["venn_fill_alpha"] = _int_default(params, _RENDER_DEFAULTS, "venn_fill_alpha", _DEFAULTS.venn_fill_alpha)
        render_params["venn_outline_width_px"] = _int_default(
            params,
            _RENDER_DEFAULTS,
            "venn_outline_width_px",
            _DEFAULTS.venn_outline_width_px,
        )

        last_error: Exception | None = None
        scene: _ScenePayload | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                scene = _make_scene(
                    instance_seed=int(instance_seed),
                    params=params,
                    render_params=render_params,
                    attempt=int(attempt),
                )
                break
            except Exception as exc:  # pragma: no cover - exercised by retry loop.
                last_error = exc
                scene = None
        if scene is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        evidence_bboxes = sort_bboxes_reading_order(tuple(instance.bbox_xyxy for instance in scene.instances if instance.counted))
        if len(evidence_bboxes) != int(scene.target_count):
            raise RuntimeError("projected Venn evidence did not match target answer")

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                f"question_text_{scene.query_id}",
                "evidence_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        question_key = f"question_text_{scene.query_id}"
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(prompt_defaults[question_key]).format(target_description=str(scene.target_description)),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]).format(target_description=str(scene.target_description)),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        taxonomy = resolve_task_taxonomy(str(self.task_id))
        serialized_instances = [_serialize_icon(instance) for instance in scene.instances]
        counted_instance_ids = tuple(str(instance.instance_id) for instance in scene.instances if instance.counted)
        target_instance_ids = tuple(str(instance.instance_id) for instance in scene.instances if instance.matches_target)
        category_counts = dict(Counter(str(instance.venn_category) for instance in scene.instances))
        target_category_counts = dict(Counter(str(instance.venn_category) for instance in scene.instances if instance.matches_target))
        venn_payload = _venn_to_trace(scene.venn)
        common_ids = {
            "domain": taxonomy.domain,
            "scene_id": taxonomy.scene_id,
            "task_id": str(self.task_id),
            "query_id": str(scene.query_id),
        }
        trace_payload = {
            "taxonomy": {
                "domain": taxonomy.domain,
                "scene_id": taxonomy.scene_id,
                "task_id": str(self.task_id),
                "source_domain": taxonomy.source_domain,
                "source_task_group": taxonomy.source_task_group,
                "query_id": str(scene.query_id),
            },
            "scene_ir": {
                **common_ids,
                "scene_kind": "icons_named_shape_venn_region_field",
                "entities": list(serialized_instances),
                "relations": {
                    "counting_rule": "target_named_icon_membership_in_overlapping_marked_circles",
                    "target_attribute_mode": str(scene.target_attribute_mode),
                    "target_description": str(scene.target_description),
                    "target_shape_id": str(scene.target_shape_id),
                    "target_shape_name": str(scene.target_shape_name),
                    "target_color_name": "" if scene.target_color is None else str(scene.target_color.name),
                    "target_fill_style": str(scene.target_fill_style),
                    "target_count": int(scene.target_count),
                    "counted_venn_categories": list(_counted_categories(str(scene.query_id))),
                    "category_counts": {str(key): int(value) for key, value in category_counts.items()},
                    "target_category_counts": {str(key): int(value) for key, value in target_category_counts.items()},
                    "venn": dict(venn_payload),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene.panel_geometry),
                },
            },
            "query_spec": {
                **common_ids,
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_id": taxonomy.scene_id,
                    "query_id": str(scene.query_id),
                    "target_attribute_mode": str(scene.target_attribute_mode),
                    "target_description": str(scene.target_description),
                    "target_shape_id": str(scene.target_shape_id),
                    "target_shape_name": str(scene.target_shape_name),
                    "target_color_name": "" if scene.target_color is None else str(scene.target_color.name),
                    "target_fill_style": str(scene.target_fill_style),
                    "target_count": int(scene.target_count),
                    "object_count": int(scene.object_count),
                    "shape_id_support": list(_shape_support(params)),
                    "query_probabilities": dict(scene.query_probabilities),
                    "shape_probabilities": dict(scene.shape_probabilities),
                    "color_probabilities": dict(scene.color_probabilities),
                    "fill_style_probabilities": dict(scene.fill_style_probabilities),
                    "target_attribute_mode_probabilities": dict(scene.target_attribute_mode_probabilities),
                    "target_count_probabilities": dict(scene.target_count_probabilities),
                    "object_count_probabilities": dict(scene.object_count_probabilities),
                    "venn": dict(venn_payload),
                },
            },
            "render_spec": {
                **common_ids,
                "canvas_size": list(scene.panel_geometry["canvas_size"]),
                "coord_space": "pixel",
                "panel_geometry": dict(scene.panel_geometry),
                "style": {
                    **icon_render_style_trace(render_params=render_params, sampled_palette_rgb=scene.sampled_palette_rgb),
                    "venn_left_fill_rgb": [int(value) for value in render_params["venn_left_fill_rgb"]],
                    "venn_right_fill_rgb": [int(value) for value in render_params["venn_right_fill_rgb"]],
                    "venn_left_outline_rgb": [int(value) for value in render_params["venn_left_outline_rgb"]],
                    "venn_right_outline_rgb": [int(value) for value in render_params["venn_right_outline_rgb"]],
                    "venn_fill_alpha": int(render_params["venn_fill_alpha"]),
                    "venn_outline_width_px": int(render_params["venn_outline_width_px"]),
                    "venn_boundary_margin_px": int(render_params["venn_boundary_margin_px"]),
                },
            },
            "render_map": {
                "image_id": "img0",
                "object_bboxes_px": {
                    str(instance.instance_id): [int(value) for value in instance.bbox_xyxy]
                    for instance in scene.instances
                },
                "object_centers_px": {
                    str(instance.instance_id): [float(value) for value in instance.center_xy]
                    for instance in scene.instances
                },
                "target_instance_ids": list(target_instance_ids),
                "counted_instance_ids": list(counted_instance_ids),
                "venn": dict(venn_payload),
            },
            "execution_trace": {
                **common_ids,
                "scene_variant": "single_panel_named_shape_venn_field",
                "question_format": "count_named_icons_by_venn_region_membership",
                "target_attribute_mode": str(scene.target_attribute_mode),
                "target_description": str(scene.target_description),
                "target_shape_id": str(scene.target_shape_id),
                "target_shape_name": str(scene.target_shape_name),
                "target_color_name": "" if scene.target_color is None else str(scene.target_color.name),
                "target_fill_style": str(scene.target_fill_style),
                "target_count": int(scene.target_count),
                "object_count": int(scene.object_count),
                "counted_venn_categories": list(_counted_categories(str(scene.query_id))),
                "category_counts": {str(key): int(value) for key, value in category_counts.items()},
                "target_category_counts": {str(key): int(value) for key, value in target_category_counts.items()},
                "target_instance_ids": list(target_instance_ids),
                "counted_instance_ids": list(counted_instance_ids),
                "venn": dict(venn_payload),
            },
            "witness_symbolic": {
                "target_attribute_mode": str(scene.target_attribute_mode),
                "target_description": str(scene.target_description),
                "answer": int(scene.target_count),
                "counted_instance_ids": list(counted_instance_ids),
                "counted_venn_categories": list(_counted_categories(str(scene.query_id))),
                "venn": dict(venn_payload),
            },
            "projected_evidence": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
                "counted_instance_ids": list(counted_instance_ids),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(scene.target_count)),
            evidence_gt=TypedValue(type="bbox_set", value=list(evidence_bboxes)),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_complexity(scene, render_params=render_params),
            task_versions=default_task_versions(),
            scene_id=taxonomy.scene_id,
            query_id=str(scene.query_id),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
        )


__all__ = ["IconsCountingNamedShapeVennRegionCountTask"]
