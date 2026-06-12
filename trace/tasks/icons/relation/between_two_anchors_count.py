"""Count scene icons whose centers lie in the strip between two aligned anchors."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.counting_sampling import resolve_counting_target_and_distractor_triplet
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.anchor_marking import draw_anchor_marker
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.annotation import bbox_set_annotation
from ..shared.icon_assets import render_icon_rgba, resolve_icon_pool
from ..shared.icon_noise import serialize_icon_noise_edits
from ..shared.icon_scene import (
    draw_single_panel,
    max_overlap_with_existing,
    overlap_fraction_smaller,
    random_paste_bbox,
    resolve_single_panel_layout,
    single_panel_geometry_to_trace,
    sort_bboxes_reading_order,
)
from ..shared.icon_style import icon_palette_meets_distance_constraints, sample_icon_palette
from ..shared.icon_task_rendering import (
    icon_render_style_trace,
    resolve_icon_render_params,
    resolve_icon_rgb_param,
    sample_icon_instance_noise,
)
from ..shared.public_query_task import rewrite_icons_query_output


_PUBLIC_QUERY_ID = "between_anchors_strip_count"
_RELATION_VARIANTS: Tuple[str, ...] = (
    "inside_vertical_strip",
    "inside_horizontal_strip",
)
_STRIP_AXES: Tuple[str, ...] = ("vertical", "horizontal")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for two-anchor strip relation counting."""

    object_count_min: int = 1
    object_count_max: int = 15
    target_count_min: int = 0
    target_count_max: int = 5
    distractor_count_min: int = 1
    distractor_count_max: int = 10
    distractor_margin_over_target: int = 0
    canvas_width: int = ICON_SHARED_DEFAULTS.canvas_width
    canvas_height: int = ICON_SHARED_DEFAULTS.canvas_height
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    scene_icon_size_min_px: int = ICON_SHARED_DEFAULTS.scene_icon_size_min_px
    scene_icon_size_max_px: int = ICON_SHARED_DEFAULTS.scene_icon_size_max_px
    scene_max_overlap_fraction: float = 0.08
    scene_placement_max_attempts: int = 140
    scene_size_shrink_rounds: int = ICON_SHARED_DEFAULTS.scene_size_shrink_rounds
    scene_size_shrink_factor: float = ICON_SHARED_DEFAULTS.scene_size_shrink_factor
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    pool_manifest: str = "all_icons.txt"
    rotation_candidates_degrees: Tuple[int, ...] = (0, 90, 180, 270)
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
        default_factory=lambda: deepcopy(ICON_SHARED_DEFAULTS.icon_noise_value_ranges)
    )
    anchor_highlight_padding_px: int = 10
    anchor_highlight_radius_px: int = 14
    anchor_outline_rgb: Tuple[int, int, int] = (74, 113, 188)
    anchor_label_color_rgb: Tuple[int, int, int] = (57, 87, 145)
    anchor_label_font_size_px: int = 20
    strip_boundary_margin_px: int = 14
    strip_span_ratio_min: float = 0.32
    strip_span_ratio_max: float = 0.60
    strip_outside_ratio_min: float = 0.12
    anchor_edge_padding_px: int = 10


@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready payload for one two-anchor strip relation scene."""

    object_count: int
    target_count: int
    distractor_count: int
    query_id: str
    anchor_icon_id: str
    anchor_tint_rgb: Tuple[int, int, int]
    anchor_rotation_degrees: int
    anchor_a_center_xy: Tuple[float, float]
    anchor_b_center_xy: Tuple[float, float]
    strip_boundary_margin_px: int
    scene_icon_ids: Tuple[str, ...]
    scene_tints_rgb: Tuple[Tuple[int, int, int], ...]
    scene_rotations_degrees: Tuple[int, ...]
    matching_scene_indices: Tuple[int, ...]
    matching_bboxes: Tuple[Tuple[int, int, int, int], ...]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    panel_geometry: Dict[str, Any]
    scene_instances: Tuple[Dict[str, Any], ...]
    anchor_instances: Tuple[Dict[str, Any], Dict[str, Any]]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_scene_defaults("icons", "relation")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="task_icons__two_anchor__between_anchors_count",
)


def _strip_axis_to_variant(strip_axis: str) -> str:
    """Map public strip axis to the construction variant."""

    if str(strip_axis) == "vertical":
        return "inside_vertical_strip"
    if str(strip_axis) == "horizontal":
        return "inside_horizontal_strip"
    raise ValueError(f"unsupported strip_axis: {strip_axis}")


def _variant_to_strip_axis(query_id: str) -> str:
    """Map source construction variant to the public strip axis."""

    if str(query_id) == "inside_vertical_strip":
        return "vertical"
    if str(query_id) == "inside_horizontal_strip":
        return "horizontal"
    raise ValueError(f"unsupported strip relation variant: {query_id}")


def _resolve_strip_axis(scene_rng, *, params: Mapping[str, Any], instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve vertical-vs-horizontal strip axis."""

    axis_params = dict(params)
    if axis_params.get("strip_axis") is None and axis_params.get("axis") is not None:
        axis_params["strip_axis"] = axis_params["axis"]
    explicit_variant = axis_params.get("query_id")
    if axis_params.get("strip_axis") is None and explicit_variant is not None:
        variant = str(explicit_variant).strip()
        if variant in set(_RELATION_VARIANTS):
            axis_params["strip_axis"] = _variant_to_strip_axis(variant)
        elif variant == str(_PUBLIC_QUERY_ID):
            axis_params.pop("query_id", None)
    selected_axis, axis_probabilities = resolve_variant(
        scene_rng,
        params=axis_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=_STRIP_AXES,
        explicit_key="strip_axis",
        weights_key="strip_axis_weights",
    )
    selected_axis = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=axis_params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected_axis),
        variant_probabilities=axis_probabilities,
        supported_variants=_STRIP_AXES,
        balance_flag_key="balanced_strip_axis_sampling",
        explicit_key="strip_axis",
        weights_key="strip_axis_weights",
    )
    return str(selected_axis), dict(axis_probabilities)


def _bbox_center(box: Sequence[int | float]) -> Tuple[float, float]:
    """Return the geometric center of one `xyxy` box."""

    return (0.5 * (float(box[0]) + float(box[2])), 0.5 * (float(box[1]) + float(box[3])))


def _resolve_rotation_candidates(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Resolve the supported scene icon rotations."""

    raw = params.get(
        "rotation_candidates_degrees",
        group_default(_GEN_DEFAULTS, "rotation_candidates_degrees", list(_DEFAULTS.rotation_candidates_degrees)),
    )
    if not isinstance(raw, (list, tuple)):
        raise ValueError("rotation_candidates_degrees must be a sequence")
    rotations = tuple(int(value) % 360 for value in raw)
    if not rotations:
        raise ValueError("rotation_candidates_degrees must contain at least one entry")
    return rotations


def _center_in_strip(
    *,
    center_xy: Sequence[float],
    anchor_a_center_xy: Sequence[float],
    anchor_b_center_xy: Sequence[float],
    query_id: str,
    margin_px: int,
) -> bool:
    """Return whether one candidate center lies safely inside the requested strip."""

    cx, cy = float(center_xy[0]), float(center_xy[1])
    ax, ay = float(anchor_a_center_xy[0]), float(anchor_a_center_xy[1])
    bx, by = float(anchor_b_center_xy[0]), float(anchor_b_center_xy[1])
    margin = float(max(0, int(margin_px)))
    if str(query_id) == "inside_vertical_strip":
        left, right = sorted((float(ax), float(bx)))
        return float(left + margin) <= float(cx) <= float(right - margin)
    if str(query_id) == "inside_horizontal_strip":
        top, bottom = sorted((float(ay), float(by)))
        return float(top + margin) <= float(cy) <= float(bottom - margin)
    raise ValueError(f"unsupported query_id: {query_id}")


def _center_outside_strip(
    *,
    center_xy: Sequence[float],
    anchor_a_center_xy: Sequence[float],
    anchor_b_center_xy: Sequence[float],
    query_id: str,
    margin_px: int,
) -> bool:
    """Return whether one candidate center lies safely outside the requested strip."""

    cx, cy = float(center_xy[0]), float(center_xy[1])
    ax, ay = float(anchor_a_center_xy[0]), float(anchor_a_center_xy[1])
    bx, by = float(anchor_b_center_xy[0]), float(anchor_b_center_xy[1])
    margin = float(max(0, int(margin_px)))
    if str(query_id) == "inside_vertical_strip":
        left, right = sorted((float(ax), float(bx)))
        return float(cx) <= float(left - margin) or float(cx) >= float(right + margin)
    if str(query_id) == "inside_horizontal_strip":
        top, bottom = sorted((float(ay), float(by)))
        return float(cy) <= float(top - margin) or float(cy) >= float(bottom + margin)
    raise ValueError(f"unsupported query_id: {query_id}")


def _target_region_bbox(
    *,
    content_bbox: Sequence[int | float],
    anchor_a_center_xy: Sequence[float],
    anchor_b_center_xy: Sequence[float],
    query_id: str,
    margin_px: int,
    sprite_size: Sequence[int | float],
) -> Tuple[int, int, int, int] | None:
    """Return a content sub-rectangle that guarantees a target center falls in-strip."""

    x0, y0, x1, y1 = [float(value) for value in content_bbox]
    sprite_w, sprite_h = float(sprite_size[0]), float(sprite_size[1])
    half_w = 0.5 * float(sprite_w)
    half_h = 0.5 * float(sprite_h)
    ax, ay = float(anchor_a_center_xy[0]), float(anchor_a_center_xy[1])
    bx, by = float(anchor_b_center_xy[0]), float(anchor_b_center_xy[1])
    margin = float(max(0, int(margin_px)))
    if str(query_id) == "inside_vertical_strip":
        left, right = sorted((float(ax), float(bx)))
        region = (
            int(round(max(float(x0), float(left + margin - half_w)))),
            int(round(float(y0))),
            int(round(min(float(x1), float(right - margin + half_w)))),
            int(round(float(y1))),
        )
    elif str(query_id) == "inside_horizontal_strip":
        top, bottom = sorted((float(ay), float(by)))
        region = (
            int(round(float(x0))),
            int(round(max(float(y0), float(top + margin - half_h)))),
            int(round(float(x1))),
            int(round(min(float(y1), float(bottom - margin + half_h)))),
        )
    else:
        raise ValueError(f"unsupported query_id: {query_id}")
    if int(region[2]) - int(region[0]) <= int(sprite_w) or int(region[3]) - int(region[1]) <= int(sprite_h):
        return None
    return tuple(int(value) for value in region)


def _sample_anchor_pair_bboxes(
    rng,
    *,
    content_bbox: Sequence[int | float],
    sprite_size: Tuple[int, int],
    query_id: str,
    span_ratio_min: float,
    span_ratio_max: float,
    outside_ratio_min: float,
    edge_padding_px: int,
) -> Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]:
    """Sample one aligned anchor pair whose strip stays well inside the scene."""

    x0, y0, x1, y1 = [int(round(float(value))) for value in content_bbox]
    sprite_w, sprite_h = int(sprite_size[0]), int(sprite_size[1])
    half_w = 0.5 * float(sprite_w)
    half_h = 0.5 * float(sprite_h)
    width = max(1.0, float(x1 - x0))
    height = max(1.0, float(y1 - y0))
    outside_ratio = max(0.0, float(outside_ratio_min))
    edge_padding = max(0, int(edge_padding_px))

    if str(query_id) == "inside_vertical_strip":
        span_min = max(float(sprite_w) + 32.0, float(span_ratio_min) * float(width))
        span_max = min(float(span_ratio_max) * float(width), float(width) - 2.0 * float(outside_ratio * width))
        if span_min > span_max:
            raise ValueError("no feasible vertical strip span for aligned anchors")
        span = float(rng.uniform(float(span_min), float(span_max)))
        cx_min = float(x0) + half_w + max(float(edge_padding), float(outside_ratio * width))
        cx_max = float(x1) - half_w - max(float(edge_padding), float(outside_ratio * width)) - float(span)
        if cx_min > cx_max:
            raise ValueError("no feasible vertical anchor centers")
        left_center_x = float(rng.uniform(float(cx_min), float(cx_max)))
        right_center_x = float(left_center_x + span)
        center_y_min = float(y0) + half_h + float(edge_padding)
        center_y_max = float(y1) - half_h - float(edge_padding)
        if center_y_min > center_y_max:
            raise ValueError("no feasible vertical anchor y coordinate")
        center_y = float(rng.uniform(float(center_y_min), float(center_y_max)))
        anchor_a_center = (float(left_center_x), float(center_y))
        anchor_b_center = (float(right_center_x), float(center_y))
    elif str(query_id) == "inside_horizontal_strip":
        span_min = max(float(sprite_h) + 32.0, float(span_ratio_min) * float(height))
        span_max = min(float(span_ratio_max) * float(height), float(height) - 2.0 * float(outside_ratio * height))
        if span_min > span_max:
            raise ValueError("no feasible horizontal strip span for aligned anchors")
        span = float(rng.uniform(float(span_min), float(span_max)))
        cy_min = float(y0) + half_h + max(float(edge_padding), float(outside_ratio * height))
        cy_max = float(y1) - half_h - max(float(edge_padding), float(outside_ratio * height)) - float(span)
        if cy_min > cy_max:
            raise ValueError("no feasible horizontal anchor centers")
        top_center_y = float(rng.uniform(float(cy_min), float(cy_max)))
        bottom_center_y = float(top_center_y + span)
        center_x_min = float(x0) + half_w + float(edge_padding)
        center_x_max = float(x1) - half_w - float(edge_padding)
        if center_x_min > center_x_max:
            raise ValueError("no feasible horizontal anchor x coordinate")
        center_x = float(rng.uniform(float(center_x_min), float(center_x_max)))
        anchor_a_center = (float(center_x), float(top_center_y))
        anchor_b_center = (float(center_x), float(bottom_center_y))
    else:
        raise ValueError(f"unsupported query_id: {query_id}")

    def _center_to_bbox(center_xy: Sequence[float]) -> Tuple[int, int, int, int]:
        center_x, center_y = float(center_xy[0]), float(center_xy[1])
        x_min = int(round(float(center_x) - half_w))
        y_min = int(round(float(center_y) - half_h))
        return (
            int(x_min),
            int(y_min),
            int(x_min + sprite_w),
            int(y_min + sprite_h),
        )

    return _center_to_bbox(anchor_a_center), _center_to_bbox(anchor_b_center)


def _sample_scene(
    rng,
    *,
    instance_seed: int,
    query_id: str,
    object_count: int,
    target_count: int,
    distractor_count: int,
    pool_manifest: str,
    rotation_candidates: Tuple[int, ...],
    render_params: Mapping[str, Any],
) -> Tuple[_ScenePayload, Image.Image]:
    """Sample and render one two-anchor strip relation scene."""

    pool = tuple(str(icon_id) for icon_id in resolve_icon_pool(str(pool_manifest)))
    if len(pool) < 2:
        raise ValueError("two-anchor strip relation pool resolved too few icons")
    anchor_icon_id = str(rng.choice(pool))
    candidate_pool = tuple(str(icon_id) for icon_id in pool if str(icon_id) != str(anchor_icon_id))
    if not candidate_pool:
        raise ValueError("two-anchor strip relation pool resolved no non-anchor icon ids")

    palette_size = int(rng.randint(int(render_params["palette_size_min"]), int(render_params["palette_size_max"])))
    palette = sample_icon_palette(
        rng,
        palette_size=int(palette_size),
        channel_min=int(render_params["color_channel_min"]),
        channel_max=int(render_params["color_channel_max"]),
        anchor_colors=(
            tuple(int(v) for v in render_params["background_color_rgb"]),
            tuple(int(v) for v in render_params["panel_fill_rgb"]),
            tuple(int(v) for v in render_params["panel_border_rgb"]),
            tuple(int(v) for v in render_params["header_text_rgb"]),
        ),
        min_color_distance=float(render_params["min_color_distance"]),
        distance_space=str(render_params["color_distance_space"]),
    )
    if not icon_palette_meets_distance_constraints(
        palette=palette,
        anchor_colors=(
            tuple(int(v) for v in render_params["background_color_rgb"]),
            tuple(int(v) for v in render_params["panel_fill_rgb"]),
            tuple(int(v) for v in render_params["panel_border_rgb"]),
            tuple(int(v) for v in render_params["header_text_rgb"]),
        ),
        min_color_distance=float(render_params["min_color_distance"]),
        distance_space=str(render_params["color_distance_space"]),
    ):
        raise ValueError("sampled icon palette did not satisfy strict distance constraints")

    anchor_tint_rgb = tuple(int(channel) for channel in rng.choice(palette))
    anchor_rotation_degrees = int(rng.choice(rotation_candidates))
    anchor_nominal_size = int(rng.randint(int(render_params["scene_icon_size_min_px"]), int(render_params["scene_icon_size_max_px"])))
    anchor_noise_edits_a, anchor_noise_seed_a = sample_icon_instance_noise(
        instance_seed=int(instance_seed),
        namespace=f"task_icons__two_anchor__between_anchors_count:{query_id}:anchor_a",
        render_params=render_params,
    )
    anchor_noise_edits_b, anchor_noise_seed_b = sample_icon_instance_noise(
        instance_seed=int(instance_seed),
        namespace=f"task_icons__two_anchor__between_anchors_count:{query_id}:anchor_b",
        render_params=render_params,
    )

    layout = resolve_single_panel_layout(
        canvas_width=int(render_params["canvas_width"]),
        canvas_height=int(render_params["canvas_height"]),
        outer_margin_px=int(render_params["outer_margin_px"]),
        panel_padding_px=int(render_params["panel_padding_px"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
    )
    image = Image.new("RGBA", (int(layout.canvas_width), int(layout.canvas_height)))
    draw_single_panel(
        image=image,
        layout=layout,
        background_rgb=tuple(int(v) for v in render_params["background_color_rgb"]),
        panel_fill_rgb=tuple(int(v) for v in render_params["panel_fill_rgb"]),
        panel_border_rgb=tuple(int(v) for v in render_params["panel_border_rgb"]),
        title_color_rgb=tuple(int(v) for v in render_params["header_text_rgb"]),
        corner_radius_px=int(render_params["panel_corner_radius_px"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
        scene_title="Scene",
        icon_canvas_style=render_params.get("_icon_canvas_style_object"),
    )
    scene_content_bbox = tuple(int(value) for value in layout.scene_content_xyxy)

    anchor_sprite_a = render_icon_rgba(
        icon_id=str(anchor_icon_id),
        size_px=int(anchor_nominal_size),
        tint_rgb=tuple(int(channel) for channel in anchor_tint_rgb),
        rotation_degrees=int(anchor_rotation_degrees),
        mirror_x=False,
        noise_edits=tuple(anchor_noise_edits_a),
        noise_seed=int(anchor_noise_seed_a),
    )
    anchor_bbox_a, anchor_bbox_b = _sample_anchor_pair_bboxes(
        rng,
        content_bbox=scene_content_bbox,
        sprite_size=anchor_sprite_a.size,
        query_id=str(query_id),
        span_ratio_min=float(render_params["strip_span_ratio_min"]),
        span_ratio_max=float(render_params["strip_span_ratio_max"]),
        outside_ratio_min=float(render_params["strip_outside_ratio_min"]),
        edge_padding_px=int(render_params["anchor_edge_padding_px"]),
    )
    image.alpha_composite(anchor_sprite_a, (int(anchor_bbox_a[0]), int(anchor_bbox_a[1])))
    anchor_sprite_b = render_icon_rgba(
        icon_id=str(anchor_icon_id),
        size_px=int(anchor_nominal_size),
        tint_rgb=tuple(int(channel) for channel in anchor_tint_rgb),
        rotation_degrees=int(anchor_rotation_degrees),
        mirror_x=False,
        noise_edits=tuple(anchor_noise_edits_b),
        noise_seed=int(anchor_noise_seed_b),
    )
    image.alpha_composite(anchor_sprite_b, (int(anchor_bbox_b[0]), int(anchor_bbox_b[1])))

    anchor_highlight_a = draw_anchor_marker(
        image=image,
        anchor_bbox=anchor_bbox_a,
        content_bbox=scene_content_bbox,
        highlight_padding_px=int(render_params["anchor_highlight_padding_px"]),
        highlight_radius_px=int(render_params["anchor_highlight_radius_px"]),
        outline_rgb=tuple(int(v) for v in render_params["anchor_outline_rgb"]),
        label_color_rgb=tuple(int(v) for v in render_params["anchor_label_color_rgb"]),
        panel_fill_rgb=tuple(int(v) for v in render_params["panel_fill_rgb"]),
        label_font_size_px=int(render_params["anchor_label_font_size_px"]),
        label_text="A",
    )
    anchor_highlight_b = draw_anchor_marker(
        image=image,
        anchor_bbox=anchor_bbox_b,
        content_bbox=scene_content_bbox,
        highlight_padding_px=int(render_params["anchor_highlight_padding_px"]),
        highlight_radius_px=int(render_params["anchor_highlight_radius_px"]),
        outline_rgb=tuple(int(v) for v in render_params["anchor_outline_rgb"]),
        label_color_rgb=tuple(int(v) for v in render_params["anchor_label_color_rgb"]),
        panel_fill_rgb=tuple(int(v) for v in render_params["panel_fill_rgb"]),
        label_font_size_px=int(render_params["anchor_label_font_size_px"]),
        label_text="B",
    )

    anchor_a_center_xy = _bbox_center(anchor_bbox_a)
    anchor_b_center_xy = _bbox_center(anchor_bbox_b)

    placed_bboxes: List[Tuple[int, int, int, int]] = [
        tuple(int(value) for value in anchor_highlight_a),
        tuple(int(value) for value in anchor_highlight_b),
    ]
    match_indices = set(rng.sample(list(range(int(object_count))), int(target_count)))
    matching_indices: List[int] = []
    matching_bboxes: List[Tuple[int, int, int, int]] = []
    scene_instances: List[Dict[str, Any]] = []
    scene_icon_ids: List[str] = []
    scene_tints_rgb: List[Tuple[int, int, int]] = []
    scene_rotations_degrees: List[int] = []

    min_size = max(16, int(render_params["scene_icon_size_min_px"]))
    max_size = max(min_size, int(render_params["scene_icon_size_max_px"]))
    placement_attempts = max(1, int(render_params["scene_placement_max_attempts"]))
    shrink_rounds = max(0, int(render_params["scene_size_shrink_rounds"]))
    shrink_factor = max(0.1, min(1.0, float(render_params["scene_size_shrink_factor"])))
    max_overlap_fraction = max(0.0, min(1.0, float(render_params["scene_max_overlap_fraction"])))

    for index in range(int(object_count)):
        is_target = int(index) in match_indices
        icon_id = str(rng.choice(candidate_pool))
        tint_rgb = tuple(int(channel) for channel in rng.choice(palette))
        rotation_degrees = int(rng.choice(rotation_candidates))
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"task_icons__two_anchor__between_anchors_count:{query_id}:scene_icon_{int(index)}",
            render_params=render_params,
        )
        sprite = None
        paste_bbox = None
        nominal_size = None
        for shrink_round in range(int(shrink_rounds) + 1):
            round_max_size = max(int(min_size), int(round(float(max_size) * (float(shrink_factor) ** int(shrink_round)))))
            for _ in range(int(placement_attempts)):
                sampled_size = int(rng.randint(int(min_size), int(round_max_size)))
                candidate_sprite = render_icon_rgba(
                    icon_id=str(icon_id),
                    size_px=int(sampled_size),
                    tint_rgb=tuple(int(channel) for channel in tint_rgb),
                    rotation_degrees=int(rotation_degrees),
                    mirror_x=False,
                    noise_edits=tuple(noise_edits),
                    noise_seed=int(noise_seed),
                )
                region_bbox = scene_content_bbox
                if bool(is_target):
                    target_region = _target_region_bbox(
                        content_bbox=scene_content_bbox,
                        anchor_a_center_xy=anchor_a_center_xy,
                        anchor_b_center_xy=anchor_b_center_xy,
                        query_id=str(query_id),
                        margin_px=int(render_params["strip_boundary_margin_px"]),
                        sprite_size=candidate_sprite.size,
                    )
                    if target_region is None:
                        continue
                    region_bbox = target_region
                try:
                    candidate_bbox = random_paste_bbox(
                        sprite_size=candidate_sprite.size,
                        content_bbox=region_bbox,
                        rng=rng,
                    )
                except ValueError:
                    continue
                if float(max_overlap_with_existing(candidate_bbox, placed_bboxes)) > float(max_overlap_fraction):
                    continue
                center_xy = _bbox_center(candidate_bbox)
                if bool(is_target):
                    if not _center_in_strip(
                        center_xy=center_xy,
                        anchor_a_center_xy=anchor_a_center_xy,
                        anchor_b_center_xy=anchor_b_center_xy,
                        query_id=str(query_id),
                        margin_px=int(render_params["strip_boundary_margin_px"]),
                    ):
                        continue
                else:
                    if not _center_outside_strip(
                        center_xy=center_xy,
                        anchor_a_center_xy=anchor_a_center_xy,
                        anchor_b_center_xy=anchor_b_center_xy,
                        query_id=str(query_id),
                        margin_px=int(render_params["strip_boundary_margin_px"]),
                    ):
                        continue
                sprite = candidate_sprite
                paste_bbox = tuple(int(value) for value in candidate_bbox)
                nominal_size = int(sampled_size)
                break
            if sprite is not None and paste_bbox is not None and nominal_size is not None:
                break
        if sprite is None or paste_bbox is None or nominal_size is None:
            raise ValueError("failed to place icon under two-anchor strip constraints")
        image.alpha_composite(sprite, (int(paste_bbox[0]), int(paste_bbox[1])))
        placed_bboxes.append(tuple(int(value) for value in paste_bbox))
        center_xy = _bbox_center(paste_bbox)
        in_strip = _center_in_strip(
            center_xy=center_xy,
            anchor_a_center_xy=anchor_a_center_xy,
            anchor_b_center_xy=anchor_b_center_xy,
            query_id=str(query_id),
            margin_px=int(render_params["strip_boundary_margin_px"]),
        )
        if bool(is_target):
            matching_indices.append(int(index))
            matching_bboxes.append(tuple(int(value) for value in paste_bbox))
        scene_icon_ids.append(str(icon_id))
        scene_tints_rgb.append(tuple(int(channel) for channel in tint_rgb))
        scene_rotations_degrees.append(int(rotation_degrees))
        scene_instances.append(
            {
                "entity_kind": "scene_icon",
                "role": "candidate",
                "instance_id": f"scene_icon_{int(index)}",
                "icon_id": str(icon_id),
                "panel": "scene",
                "bbox_xyxy": [int(value) for value in paste_bbox],
                "center_xy": [float(center_xy[0]), float(center_xy[1])],
                "nominal_size_px": int(nominal_size),
                "rotation_degrees": int(rotation_degrees) % 360,
                "mirror_x": False,
                "tint_rgb": [int(channel) for channel in tint_rgb],
                "noise_edits": [dict(edit) for edit in serialize_icon_noise_edits(tuple(noise_edits))],
                "noise_seed": int(noise_seed),
                "center_in_strip": bool(in_strip),
                "is_match": bool(is_target),
            }
        )

    anchor_instances = (
        {
            "entity_kind": "anchor_icon",
            "role": "anchor_a",
            "label": "A",
            "instance_id": "anchor_a",
            "icon_id": str(anchor_icon_id),
            "panel": "scene",
            "bbox_xyxy": [int(value) for value in anchor_bbox_a],
            "center_xy": [float(anchor_a_center_xy[0]), float(anchor_a_center_xy[1])],
            "nominal_size_px": int(anchor_nominal_size),
            "rotation_degrees": int(anchor_rotation_degrees) % 360,
            "mirror_x": False,
            "tint_rgb": [int(channel) for channel in anchor_tint_rgb],
            "noise_edits": [dict(edit) for edit in serialize_icon_noise_edits(tuple(anchor_noise_edits_a))],
            "noise_seed": int(anchor_noise_seed_a),
            "highlight_bbox_xyxy": [int(value) for value in anchor_highlight_a],
        },
        {
            "entity_kind": "anchor_icon",
            "role": "anchor_b",
            "label": "B",
            "instance_id": "anchor_b",
            "icon_id": str(anchor_icon_id),
            "panel": "scene",
            "bbox_xyxy": [int(value) for value in anchor_bbox_b],
            "center_xy": [float(anchor_b_center_xy[0]), float(anchor_b_center_xy[1])],
            "nominal_size_px": int(anchor_nominal_size),
            "rotation_degrees": int(anchor_rotation_degrees) % 360,
            "mirror_x": False,
            "tint_rgb": [int(channel) for channel in anchor_tint_rgb],
            "noise_edits": [dict(edit) for edit in serialize_icon_noise_edits(tuple(anchor_noise_edits_b))],
            "noise_seed": int(anchor_noise_seed_b),
            "highlight_bbox_xyxy": [int(value) for value in anchor_highlight_b],
        },
    )

    return (
        _ScenePayload(
            object_count=int(object_count),
            target_count=int(target_count),
            distractor_count=int(distractor_count),
            query_id=str(query_id),
            anchor_icon_id=str(anchor_icon_id),
            anchor_tint_rgb=tuple(int(channel) for channel in anchor_tint_rgb),
            anchor_rotation_degrees=int(anchor_rotation_degrees) % 360,
            anchor_a_center_xy=(float(anchor_a_center_xy[0]), float(anchor_a_center_xy[1])),
            anchor_b_center_xy=(float(anchor_b_center_xy[0]), float(anchor_b_center_xy[1])),
            strip_boundary_margin_px=int(render_params["strip_boundary_margin_px"]),
            scene_icon_ids=tuple(str(icon_id) for icon_id in scene_icon_ids),
            scene_tints_rgb=tuple(tuple(int(channel) for channel in tint) for tint in scene_tints_rgb),
            scene_rotations_degrees=tuple(int(value) for value in scene_rotations_degrees),
            matching_scene_indices=tuple(int(value) for value in matching_indices),
            matching_bboxes=tuple(tuple(int(value) for value in box) for box in matching_bboxes),
            sampled_palette_rgb=tuple(tuple(int(channel) for channel in color) for color in palette),
            panel_geometry=single_panel_geometry_to_trace(layout),
            scene_instances=tuple(dict(entity) for entity in scene_instances),
            anchor_instances=(dict(anchor_instances[0]), dict(anchor_instances[1])),
        ),
        image.convert("RGB"),
    )


@register_task
class IconsRelationBetweenTwoAnchorsCountTask:
    """Count scene icons whose centers lie in the strip between two anchors."""

    task_id = "task_icons__two_anchor__between_anchors_count"
    domain = "icons"
    scene_id = "relation"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic two-anchor strip relation instance."""

        scene_rng = spawn_rng(int(instance_seed), "scene")
        strip_axis, strip_axis_probabilities = _resolve_strip_axis(
            scene_rng,
            params=params,
            instance_seed=int(instance_seed),
        )
        query_id = _strip_axis_to_variant(str(strip_axis))
        public_query_id = str(_PUBLIC_QUERY_ID)
        counting_params = dict(params)
        (
            object_count,
            object_count_probabilities,
            target_count,
            target_count_probabilities,
            distractor_count,
            distractor_count_probabilities,
        ) = resolve_counting_target_and_distractor_triplet(
            scene_rng,
            instance_seed=int(instance_seed),
            params=counting_params,
            gen_defaults=_GEN_DEFAULTS,
            fallback_total_min=_DEFAULTS.object_count_min,
            fallback_total_max=_DEFAULTS.object_count_max,
            fallback_target_min=_DEFAULTS.target_count_min,
            fallback_target_max=_DEFAULTS.target_count_max,
            fallback_distractor_min=_DEFAULTS.distractor_count_min,
            fallback_distractor_max=_DEFAULTS.distractor_count_max,
        )
        render_params = resolve_icon_render_params(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        for extra_key, fallback_value in (
            ("anchor_highlight_padding_px", _DEFAULTS.anchor_highlight_padding_px),
            ("anchor_highlight_radius_px", _DEFAULTS.anchor_highlight_radius_px),
            ("anchor_label_font_size_px", _DEFAULTS.anchor_label_font_size_px),
            ("strip_boundary_margin_px", _DEFAULTS.strip_boundary_margin_px),
            ("strip_span_ratio_min", _DEFAULTS.strip_span_ratio_min),
            ("strip_span_ratio_max", _DEFAULTS.strip_span_ratio_max),
            ("strip_outside_ratio_min", _DEFAULTS.strip_outside_ratio_min),
            ("anchor_edge_padding_px", _DEFAULTS.anchor_edge_padding_px),
        ):
            render_params[str(extra_key)] = params.get(
                str(extra_key),
                group_default(_RENDER_DEFAULTS, str(extra_key), fallback_value),
            )
        render_params["anchor_outline_rgb"] = resolve_icon_rgb_param(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            key="anchor_outline_rgb",
            fallback=_DEFAULTS.anchor_outline_rgb,
            instance_seed=int(instance_seed),
        )
        render_params["anchor_label_color_rgb"] = resolve_icon_rgb_param(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            key="anchor_label_color_rgb",
            fallback=_DEFAULTS.anchor_label_color_rgb,
            instance_seed=int(instance_seed),
        )

        pool_manifest = str(params.get("pool_manifest", group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest)))
        rotation_candidates = _resolve_rotation_candidates(params)

        scene_payload = None
        image = None
        last_error: Exception | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                scene_payload, image = _sample_scene(
                    scene_rng,
                    instance_seed=int(instance_seed),
                    query_id=str(query_id),
                    object_count=int(object_count),
                    target_count=int(target_count),
                    distractor_count=int(distractor_count),
                    pool_manifest=str(pool_manifest),
                    rotation_candidates=tuple(rotation_candidates),
                    render_params=render_params,
                )
                break
            except Exception as exc:
                last_error = exc
                continue
        if scene_payload is None or image is None:
            raise RuntimeError("failed to generate task_icons__two_anchor__between_anchors_count instance") from last_error

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "annotation_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        question_text = str(
            required_group_default(
                _PROMPT_DEFAULTS,
                f"question_text_{strip_axis}_strip",
                context=f"prompt defaults for {self.task_id}",
            )
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            scene_id=self.scene_id,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(question_text),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        annotation_value = sort_bboxes_reading_order(scene_payload.matching_bboxes)
        annotation_payload = bbox_set_annotation(annotation_value)
        answer_value = int(scene_payload.target_count)

        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_two_anchor_strip_relation",
                "entities": [
                    dict(scene_payload.anchor_instances[0]),
                    dict(scene_payload.anchor_instances[1]),
                    *[dict(entity) for entity in scene_payload.scene_instances],
                ],
                "relations": {
                    "counting_target": "candidate_icon_centers_in_strip_between_two_anchors",
                    "query_id": str(public_query_id),
                    "internal_query_id": str(scene_payload.query_id),
                    "strip_axis": str(strip_axis),
                    "anchor_icon_id": str(scene_payload.anchor_icon_id),
                    "matching_scene_indices": [int(value) for value in scene_payload.matching_scene_indices],
                    "strip_boundary_margin_px": int(scene_payload.strip_boundary_margin_px),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene_payload.panel_geometry),
                },
            },
            "query_spec": {
                "query_id": str(public_query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "object_count": int(object_count),
                    "object_count_probabilities": dict(object_count_probabilities),
                    "target_count": int(target_count),
                    "target_count_probabilities": dict(target_count_probabilities),
                    "distractor_count": int(distractor_count),
                    "distractor_count_probabilities": dict(distractor_count_probabilities),
                    "distractor_margin_over_target": int(
                        params.get(
                            "distractor_margin_over_target",
                            group_default(_GEN_DEFAULTS, "distractor_margin_over_target", _DEFAULTS.distractor_margin_over_target),
                        )
                    ),
                    "pool_manifest": str(pool_manifest),
                    "rotation_candidates_degrees": [int(value) for value in rotation_candidates],
                    "strip_axis": str(strip_axis),
                    "strip_axis_probabilities": dict(strip_axis_probabilities),
                    "internal_query_id": str(scene_payload.query_id),
                    "strip_boundary_margin_px": int(render_params["strip_boundary_margin_px"]),
                    "strip_span_ratio_min": float(render_params["strip_span_ratio_min"]),
                    "strip_span_ratio_max": float(render_params["strip_span_ratio_max"]),
                    "strip_outside_ratio_min": float(render_params["strip_outside_ratio_min"]),
                },
            },
            "render_spec": {
                "canvas_size": [int(render_params["canvas_width"]), int(render_params["canvas_height"])],
                "coord_space": "pixel",
                "panel_geometry": dict(scene_payload.panel_geometry),
                "style": {
                    **icon_render_style_trace(render_params=render_params, sampled_palette_rgb=scene_payload.sampled_palette_rgb),
                    "strip_boundary_margin_px": int(render_params["strip_boundary_margin_px"]),
                    "strip_span_ratio_min": float(render_params["strip_span_ratio_min"]),
                    "strip_span_ratio_max": float(render_params["strip_span_ratio_max"]),
                    "strip_outside_ratio_min": float(render_params["strip_outside_ratio_min"]),
                    "anchor_highlight_padding_px": int(render_params["anchor_highlight_padding_px"]),
                    "anchor_highlight_radius_px": int(render_params["anchor_highlight_radius_px"]),
                    "anchor_outline_rgb": [int(v) for v in render_params["anchor_outline_rgb"]],
                    "anchor_label_color_rgb": [int(v) for v in render_params["anchor_label_color_rgb"]],
                    "anchor_label_font_size_px": int(render_params["anchor_label_font_size_px"]),
                },
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {
                    "anchor_a": dict(scene_payload.anchor_instances[0]),
                    "anchor_b": dict(scene_payload.anchor_instances[1]),
                    "matching_scene_boxes": list(annotation_payload["annotation_value"]),
                },
            },
            "execution_trace": {
                "scene_variant": "scene_two_anchors_strip",
                "query_id": str(public_query_id),
                "internal_query_id": str(scene_payload.query_id),
                "strip_axis": str(strip_axis),
                "object_count": int(scene_payload.object_count),
                "object_count_probabilities": dict(object_count_probabilities),
                "target_count": int(scene_payload.target_count),
                "target_count_probabilities": dict(target_count_probabilities),
                "distractor_count": int(scene_payload.distractor_count),
                "distractor_count_probabilities": dict(distractor_count_probabilities),
                "distractor_margin_over_target": int(
                    params.get(
                        "distractor_margin_over_target",
                        group_default(_GEN_DEFAULTS, "distractor_margin_over_target", _DEFAULTS.distractor_margin_over_target),
                    )
                ),
                "anchor_icon_id": str(scene_payload.anchor_icon_id),
                "anchor_tint_rgb": list(scene_payload.anchor_tint_rgb),
                "anchor_rotation_degrees": int(scene_payload.anchor_rotation_degrees),
                "anchor_a_center_xy": [float(scene_payload.anchor_a_center_xy[0]), float(scene_payload.anchor_a_center_xy[1])],
                "anchor_b_center_xy": [float(scene_payload.anchor_b_center_xy[0]), float(scene_payload.anchor_b_center_xy[1])],
                "scene_icon_ids": list(scene_payload.scene_icon_ids),
                "scene_tints_rgb": [list(color) for color in scene_payload.scene_tints_rgb],
                "scene_rotations_degrees": [int(value) for value in scene_payload.scene_rotations_degrees],
                "matching_scene_indices": [int(value) for value in scene_payload.matching_scene_indices],
                "question_format": "count_scene_icon_centers_in_strip_between_two_anchors",
                "strip_boundary_margin_px": int(scene_payload.strip_boundary_margin_px),
                "strip_axis_probabilities": dict(strip_axis_probabilities),
            },
            "witness_symbolic": {
                "query_id": str(public_query_id),
                "internal_query_id": str(scene_payload.query_id),
                "strip_axis": str(strip_axis),
                "anchor_a_center_xy": [float(scene_payload.anchor_a_center_xy[0]), float(scene_payload.anchor_a_center_xy[1])],
                "anchor_b_center_xy": [float(scene_payload.anchor_b_center_xy[0]), float(scene_payload.anchor_b_center_xy[1])],
                "matching_scene_indices": [int(value) for value in scene_payload.matching_scene_indices],
                "strip_boundary_margin_px": int(scene_payload.strip_boundary_margin_px),
            },
            "projected_annotation": dict(annotation_payload["projected_annotation"]),
        }
        output = TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="integer", value=int(answer_value)),
            annotation_gt=TypedValue(
                type=str(annotation_payload["annotation_type"]),
                value=list(annotation_payload["annotation_value"]),
            ),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            query_id=str(public_query_id),
        )
        return rewrite_icons_query_output(
            output,
            query_id=str(scene_payload.query_id),
            scene_id="two_anchor",
            query_probabilities={
                _strip_axis_to_variant(str(key)): float(value)
                for key, value in strip_axis_probabilities.items()
            },
        )


__all__ = ["IconsRelationBetweenTwoAnchorsCountTask"]
