"""Coordinate locus and shaded-region label tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import resolve_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font
from ..shared.background_defaults import load_geometry_background_defaults
from ..shared.complexity import build_geometry_task_complexity, clamp_unit_interval, resolve_geometry_complexity_weights
from ..shared.coordinate_panel_grid import (
    CoordinatePanelConfig,
    CoordinatePanelStyle,
    coordinate_panel_layout,
    draw_coordinate_panel_grid,
    graph_point_to_panel_pixel,
    panel_bbox_for_index,
    plot_bbox_for_panel,
)
from ..shared.fixed_query_task import select_geometry_query_id
from ..shared.graph_rendering import graph_paper_grid_from_frame, graph_units_to_pixel, scale_point
from ..shared.noise_defaults import load_geometry_noise_defaults
from ..shared.point_labels import draw_labeled_points
from ..shared.single_object_scene import finalize_graph_scene_image, make_graph_scene_canvas, resolve_graph_scene_context
from .quadrilateral import (
    _draw_marker,
    _marker_bbox,
    _probability_map,
    _resolve_label_pool,
    _resolve_marker_colors,
    _sample_marker_style,
)


GraphPoint = Tuple[int, int]
PixelPoint = Tuple[float, float]
Color = Tuple[int, int, int]
BBox = Tuple[int, int, int, int]

POINT_TASK_ID = "task_geometry__coordinate_plane__locus_point_label"
PANEL_TASK_ID = "task_geometry__coordinate_plane__locus_panel_match_label"
SCENE_ID = "coordinate_plane"

POINT_QUERY_IDS: Tuple[str, ...] = (
    "circle_region_point",
    "annulus_region_point",
    "vertical_strip_region_point",
    "half_plane_intersection_region_point",
)
PANEL_QUERY_IDS: Tuple[str, ...] = (
    "circle_inequality_panel_match",
    "vertical_strip_panel_match",
    "horizontal_halfplane_panel_match",
    "two_inequality_panel_match",
)
DEFAULT_LABEL_POOL: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "coordinate")
_BACKGROUND_DEFAULTS = load_geometry_background_defaults(task_group="coordinate")
_NOISE_DEFAULTS = load_geometry_noise_defaults(task_group="coordinate")
_PANEL_BACKGROUND_DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    "styles": {
        "solid_offwhite": {"kind": "solid", "color": [252, 252, 252]},
        "solid_cool": {"kind": "solid", "color": [246, 248, 252]},
        "solid_warm": {"kind": "solid", "color": [252, 249, 245]},
        "solid_mist": {"kind": "solid", "color": [248, 252, 249]},
    },
    "weights": {
        "solid_offwhite": 0.35,
        "solid_cool": 0.25,
        "solid_warm": 0.20,
        "solid_mist": 0.20,
    },
}


@dataclass(frozen=True)
class _TaskDefaults:
    canvas_size_min: int = 680
    canvas_size_max: int = 760
    graph_cells_min: int = 18
    graph_cells_max: int = 20
    graph_abs_max: int = 6
    candidate_count: int = 6
    marker_radius_px: int = 7
    marker_radius_px_min: int = 6
    marker_radius_px_max: int = 9
    label_font_size_min: int = 16
    label_font_size_max: int = 28
    label_stroke_width: int = 1
    label_offset_px: int = 15
    panel_canvas_width: int = 1040
    panel_canvas_height: int = 760
    panel_grid_min: int = -6
    panel_grid_max: int = 6
    panel_count: int = 6
    panel_top_reserved_px: int = 58
    panel_marker_radius_px: int = 4
    panel_marker_radius_px_min: int = 3
    panel_marker_radius_px_max: int = 5
    condition_label_font_size: int = 18


@dataclass(frozen=True)
class _RegionSpec:
    kind: str
    params: Dict[str, int]
    condition_text: str


@dataclass(frozen=True)
class _ResolvedQuery:
    query_id: str
    query_probabilities: Dict[str, float]
    winner_label: str
    winner_label_probabilities: Dict[str, float]
    label_pool: Tuple[str, ...]


@dataclass(frozen=True)
class _PointScene:
    region: _RegionSpec
    candidate_points_by_label: Dict[str, GraphPoint]
    candidate_bboxes_by_label: Dict[str, List[int]]
    candidate_points_px_by_label: Dict[str, PixelPoint]
    center_point_px: PixelPoint | None
    marker_meta: Dict[str, Any]
    image: Image.Image
    background_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]
    render_spec_extra: Dict[str, Any]


@dataclass(frozen=True)
class _PanelSpec:
    label: str
    region: _RegionSpec
    panel_bbox: List[int]
    plot_bbox: List[int]
    is_answer: bool


@dataclass(frozen=True)
class _PanelScene:
    condition_text: str
    panels_by_label: Dict[str, _PanelSpec]
    condition_label_bbox_px: List[int]
    panel_style_meta: Dict[str, Any]
    marker_meta: Dict[str, Any]
    image: Image.Image
    background_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_REGION_FILL: Color = (82, 142, 218)
_REGION_OUTLINE: Color = (32, 83, 138)
_BOUNDARY_DASH_FILL: Color = (42, 84, 124)
_PANEL_STYLES: Tuple[CoordinatePanelStyle, ...] = (
    CoordinatePanelStyle(),
    CoordinatePanelStyle(
        panel_fill=(255, 255, 255),
        panel_outline=(190, 205, 218),
        plot_fill=(249, 252, 255),
        plot_outline=(176, 192, 208),
        grid_color=(218, 228, 238),
        axis_color=(94, 115, 135),
        tick_color=(82, 98, 116),
        text_color=(28, 45, 62),
    ),
    CoordinatePanelStyle(
        panel_fill=(255, 255, 252),
        panel_outline=(207, 197, 178),
        plot_fill=(253, 251, 245),
        plot_outline=(194, 183, 162),
        grid_color=(232, 224, 207),
        axis_color=(125, 107, 82),
        tick_color=(104, 91, 72),
        text_color=(55, 45, 34),
    ),
)


def _split_defaults_for_task(task_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    return split_generation_rendering_prompt_defaults(
        _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        task_id=str(task_id),
    )


def _resolve_int_param(params: Mapping[str, Any], defaults: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(defaults, str(key), int(fallback))))


def _select_winner_label(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    label_pool: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    labels = tuple(str(label) for label in label_pool)
    explicit = params.get("winner_label", params.get("answer_label"))
    if explicit is not None:
        label = str(explicit)
        if label not in set(labels):
            raise ValueError(f"winner_label={label!r} is not in label pool {labels!r}")
        return label, {label: 1.0}
    selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.winner_label",
    )
    return str(labels[int(selection_index) % len(labels)]), _probability_map(labels)


def _resolve_query(
    *,
    task_id: str,
    query_ids: Sequence[str],
    label_pool: Sequence[str],
    instance_seed: int,
    params: Mapping[str, Any],
) -> _ResolvedQuery:
    query_id, query_probabilities = select_geometry_query_id(
        params,
        query_ids=tuple(query_ids),
        task_id=str(task_id),
        instance_seed=int(instance_seed),
    )
    winner_label, winner_probabilities = _select_winner_label(
        params=params,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        label_pool=tuple(label_pool),
    )
    return _ResolvedQuery(
        query_id=str(query_id),
        query_probabilities=dict(query_probabilities),
        winner_label=str(winner_label),
        winner_label_probabilities=dict(winner_probabilities),
        label_pool=tuple(str(label) for label in label_pool),
    )


def _candidate_labels_for_query(query: _ResolvedQuery, *, candidate_count: int) -> Tuple[str, ...]:
    labels = tuple(query.label_pool[: int(candidate_count)])
    if str(query.winner_label) not in set(labels):
        labels = tuple([str(query.winner_label), *[label for label in labels if label != str(query.winner_label)]])
        labels = labels[: int(candidate_count)]
    return labels


def _region_contains(region: _RegionSpec, point: GraphPoint) -> bool:
    x, y = int(point[0]), int(point[1])
    params = dict(region.params)
    if str(region.kind) in {"circle", "annulus"}:
        cx = int(params.get("cx", 0))
        cy = int(params.get("cy", 0))
        d2 = (int(x) - cx) ** 2 + (int(y) - cy) ** 2
        if str(region.kind) == "circle":
            return int(d2) <= int(params["r"]) ** 2
        return int(params["inner_r"]) ** 2 <= int(d2) <= int(params["outer_r"]) ** 2
    if "x_min" in params and int(x) < int(params["x_min"]):
        return False
    if "x_max" in params and int(x) > int(params["x_max"]):
        return False
    if "y_min" in params and int(y) < int(params["y_min"]):
        return False
    if "y_max" in params and int(y) > int(params["y_max"]):
        return False
    return True


def _region_boundary_point(region: _RegionSpec, point: GraphPoint) -> bool:
    x, y = int(point[0]), int(point[1])
    params = dict(region.params)
    if str(region.kind) == "circle":
        cx = int(params.get("cx", 0))
        cy = int(params.get("cy", 0))
        return ((x - cx) ** 2 + (y - cy) ** 2) == int(params["r"]) ** 2
    if str(region.kind) == "annulus":
        cx = int(params.get("cx", 0))
        cy = int(params.get("cy", 0))
        d2 = (x - cx) ** 2 + (y - cy) ** 2
        return int(d2) in {int(params["inner_r"]) ** 2, int(params["outer_r"]) ** 2}
    return any(
        (
            "x_min" in params and x == int(params["x_min"]),
            "x_max" in params and x == int(params["x_max"]),
            "y_min" in params and y == int(params["y_min"]),
            "y_max" in params and y == int(params["y_max"]),
        )
    )


def _sample_region_for_point_query(query_id: str, rng, *, max_abs: int) -> _RegionSpec:
    circle_cases = (
        _RegionSpec("circle", {"cx": 0, "cy": 0, "r": 4}, "inside circle centered at O"),
        _RegionSpec("circle", {"cx": 1, "cy": -1, "r": 3}, "inside circle centered at O"),
        _RegionSpec("circle", {"cx": -1, "cy": 2, "r": 3}, "inside circle centered at O"),
        _RegionSpec("circle", {"cx": 2, "cy": 1, "r": 3}, "inside circle centered at O"),
    )
    annulus_cases = (
        _RegionSpec("annulus", {"cx": 0, "cy": 0, "inner_r": 2, "outer_r": 5}, "inside the shaded ring"),
        _RegionSpec("annulus", {"cx": 1, "cy": -1, "inner_r": 2, "outer_r": 4}, "inside the shaded ring"),
        _RegionSpec("annulus", {"cx": -1, "cy": 1, "inner_r": 2, "outer_r": 4}, "inside the shaded ring"),
    )
    strip_cases = (
        _RegionSpec("vertical_strip", {"x_min": -2, "x_max": 2}, "-2 <= x <= 2"),
        _RegionSpec("vertical_strip", {"x_min": -4, "x_max": -1}, "-4 <= x <= -1"),
        _RegionSpec("vertical_strip", {"x_min": 1, "x_max": 4}, "1 <= x <= 4"),
    )
    intersection_cases = (
        _RegionSpec("half_plane_intersection", {"x_min": -1, "y_max": 2}, "x >= -1 and y <= 2"),
        _RegionSpec("half_plane_intersection", {"x_min": 1, "y_max": 1}, "x >= 1 and y <= 1"),
        _RegionSpec("half_plane_intersection", {"x_min": -2, "y_max": 0}, "x >= -2 and y <= 0"),
    )
    if str(query_id) == "circle_region_point":
        return rng.choice(circle_cases)
    if str(query_id) == "annulus_region_point":
        return rng.choice(annulus_cases)
    if str(query_id) == "vertical_strip_region_point":
        return rng.choice(strip_cases)
    if str(query_id) == "half_plane_intersection_region_point":
        return rng.choice(intersection_cases)
    raise ValueError(f"unsupported locus point query: {query_id}")


def _grid_points(max_abs: int) -> Tuple[GraphPoint, ...]:
    return tuple((x, y) for x in range(-int(max_abs), int(max_abs) + 1) for y in range(-int(max_abs), int(max_abs) + 1))


def _sample_candidate_points(
    *,
    region: _RegionSpec,
    query: _ResolvedQuery,
    candidate_labels: Sequence[str],
    rng,
    max_abs: int,
) -> Dict[str, GraphPoint]:
    available = [point for point in _grid_points(int(max_abs)) if not _region_boundary_point(region, point)]
    inside = [point for point in available if _region_contains(region, point)]
    outside = [point for point in available if not _region_contains(region, point)]
    if not inside or len(outside) < int(len(candidate_labels) - 1):
        raise RuntimeError("locus region does not have enough candidate support")
    target = tuple(rng.choice(inside))
    rng.shuffle(outside)
    candidate_points_by_label: Dict[str, GraphPoint] = {str(query.winner_label): target}
    occupied = {target}
    for label in candidate_labels:
        if str(label) == str(query.winner_label):
            continue
        for point in outside:
            if tuple(point) in occupied:
                continue
            candidate_points_by_label[str(label)] = tuple(point)
            occupied.add(tuple(point))
            break
        if str(label) not in candidate_points_by_label:
            raise RuntimeError("failed to sample locus-region distractor")
    return dict(candidate_points_by_label)


def _scaled_bbox(bbox: Sequence[int], scale: int) -> Tuple[int, int, int, int]:
    return tuple(int(value) * int(scale) for value in bbox)  # type: ignore[return-value]


def _clip_bbox(bbox: Sequence[float], clip: Sequence[int]) -> Tuple[int, int, int, int] | None:
    left = max(int(round(float(bbox[0]))), int(clip[0]))
    top = max(int(round(float(bbox[1]))), int(clip[1]))
    right = min(int(round(float(bbox[2]))), int(clip[2]))
    bottom = min(int(round(float(bbox[3]))), int(clip[3]))
    if right <= left or bottom <= top:
        return None
    return (left, top, right, bottom)


def _apply_region_mask(image: Image.Image, mask: Image.Image, *, color: Color) -> None:
    overlay = Image.new("RGBA", image.size, (int(color[0]), int(color[1]), int(color[2]), 0))
    overlay.putalpha(mask)
    composed = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    image.paste(composed)


def _draw_scaled_line(draw: ImageDraw.ImageDraw, points: Sequence[PixelPoint], *, fill: Color, width: int) -> None:
    draw.line([(float(x), float(y)) for x, y in points], fill=fill, width=max(1, int(width)))


def _project_single(point: Tuple[float, float], *, context: Any) -> PixelPoint:
    return scale_point(
        graph_units_to_pixel(point, graph_origin=context.graph_origin, spacing=int(context.graph_spacing)),
        int(context.scene_scale),
    )


def _single_region_bbox(region: _RegionSpec, *, context: Any, radius_key: str) -> Tuple[int, int, int, int]:
    params = dict(region.params)
    cx = int(params.get("cx", 0))
    cy = int(params.get("cy", 0))
    radius = int(params[radius_key])
    left_top = _project_single((cx - radius, cy + radius), context=context)
    right_bottom = _project_single((cx + radius, cy - radius), context=context)
    return (
        int(round(float(left_top[0]))),
        int(round(float(left_top[1]))),
        int(round(float(right_bottom[0]))),
        int(round(float(right_bottom[1]))),
    )


def _constraint_rect(region: _RegionSpec, *, grid_min: int, grid_max: int) -> Tuple[int, int, int, int]:
    params = dict(region.params)
    return (
        int(params.get("x_min", grid_min)),
        int(params.get("y_min", grid_min)),
        int(params.get("x_max", grid_max)),
        int(params.get("y_max", grid_max)),
    )


def _draw_single_region(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    *,
    region: _RegionSpec,
    context: Any,
    max_abs: int,
) -> None:
    scale = int(context.scene_scale)
    clip = _scaled_bbox(context.graph_panel_layout.content_bbox_px, int(scale))
    mask = Image.new("L", image.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    if str(region.kind) == "circle":
        bbox = _clip_bbox(_single_region_bbox(region, context=context, radius_key="r"), clip)
        if bbox is not None:
            mask_draw.ellipse(bbox, fill=78)
            _apply_region_mask(image, mask, color=_REGION_FILL)
            draw.ellipse(bbox, outline=_REGION_OUTLINE, width=max(2, 2 * scale))
        return
    if str(region.kind) == "annulus":
        outer = _clip_bbox(_single_region_bbox(region, context=context, radius_key="outer_r"), clip)
        inner = _clip_bbox(_single_region_bbox(region, context=context, radius_key="inner_r"), clip)
        if outer is not None:
            mask_draw.ellipse(outer, fill=82)
            if inner is not None:
                mask_draw.ellipse(inner, fill=0)
            _apply_region_mask(image, mask, color=_REGION_FILL)
            draw.ellipse(outer, outline=_REGION_OUTLINE, width=max(2, 2 * scale))
            if inner is not None:
                draw.ellipse(inner, outline=_REGION_OUTLINE, width=max(2, 2 * scale))
        return

    x_min, y_min, x_max, y_max = _constraint_rect(region, grid_min=-int(max_abs), grid_max=int(max_abs))
    top_left = _project_single((x_min, y_max), context=context)
    bottom_right = _project_single((x_max, y_min), context=context)
    rect = _clip_bbox((top_left[0], top_left[1], bottom_right[0], bottom_right[1]), clip)
    if rect is None:
        return
    mask_draw.rectangle(rect, fill=76)
    _apply_region_mask(image, mask, color=_REGION_FILL)
    params = dict(region.params)
    line_width = max(2, 2 * scale)
    for key in ("x_min", "x_max"):
        if key not in params:
            continue
        x_value = int(params[key])
        start = _project_single((x_value, -int(max_abs)), context=context)
        end = _project_single((x_value, int(max_abs)), context=context)
        _draw_scaled_line(draw, [(start[0], clip[1]), (end[0], clip[3])], fill=_BOUNDARY_DASH_FILL, width=line_width)
    for key in ("y_min", "y_max"):
        if key not in params:
            continue
        y_value = int(params[key])
        start = _project_single((-int(max_abs), y_value), context=context)
        end = _project_single((int(max_abs), y_value), context=context)
        _draw_scaled_line(draw, [(clip[0], start[1]), (clip[2], end[1])], fill=_BOUNDARY_DASH_FILL, width=line_width)


def _draw_center_marker(
    draw: ImageDraw.ImageDraw,
    *,
    context: Any,
    region: _RegionSpec,
    marker_radius: int,
    label_font_size_px: int,
    label_offset_px: int,
    label_stroke_width: int,
    color: Color,
) -> PixelPoint | None:
    if str(region.kind) not in {"circle", "annulus"}:
        return None
    center = (int(region.params.get("cx", 0)), int(region.params.get("cy", 0)))
    point_px = graph_units_to_pixel(center, graph_origin=context.graph_origin, spacing=int(context.graph_spacing))
    render_px = scale_point(point_px, int(context.scene_scale))
    _draw_marker(
        draw,
        render_px,
        style="cross",
        color=color,
        radius=max(4, int(marker_radius) * int(context.scene_scale)),
        width=max(2, int(context.scene_scale) * 2),
    )
    draw_labeled_points(
        draw,
        points=[render_px],
        labels=["O"],
        label_offset_px=float(label_offset_px) * float(context.scene_scale),
        font_size_px=int(label_font_size_px),
        text_stroke_width=int(label_stroke_width) * int(context.scene_scale),
        blocked_points=[render_px],
        blocked_point_clearance_px=float(marker_radius * int(context.scene_scale) + 8),
        marker_radius_px=0,
        marker_color=color,
        label_color=color,
        label_stroke_color=(255, 255, 255),
        canvas_size=int(context.canvas_size) * int(context.scene_scale),
    )
    return (float(point_px[0]), float(point_px[1]))


def _render_point_scene(
    query: _ResolvedQuery,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
) -> _PointScene:
    rng = spawn_rng(int(instance_seed), f"{POINT_TASK_ID}.render")
    max_abs = _resolve_int_param(params, generation_defaults, "locus_graph_abs_max", _DEFAULTS.graph_abs_max)
    candidate_count = max(4, _resolve_int_param(params, generation_defaults, "locus_candidate_count", _DEFAULTS.candidate_count))
    if int(candidate_count) > len(query.label_pool):
        raise ValueError("locus_candidate_count cannot exceed candidate label pool length")
    candidate_labels = _candidate_labels_for_query(query, candidate_count=int(candidate_count))
    region = _sample_region_for_point_query(str(query.query_id), rng, max_abs=int(max_abs))
    candidate_points_by_label = _sample_candidate_points(
        region=region,
        query=query,
        candidate_labels=candidate_labels,
        rng=rng,
        max_abs=int(max_abs),
    )
    context = resolve_graph_scene_context(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        render_defaults=rendering_defaults,
        background_defaults=_BACKGROUND_DEFAULTS,
        fallback_canvas_min=_resolve_int_param(params, rendering_defaults, "locus_canvas_size_min", _DEFAULTS.canvas_size_min),
        fallback_canvas_max=_resolve_int_param(params, rendering_defaults, "locus_canvas_size_max", _DEFAULTS.canvas_size_max),
        fallback_cells_min=_resolve_int_param(params, rendering_defaults, "locus_graph_cells_min", _DEFAULTS.graph_cells_min),
        fallback_cells_max=_resolve_int_param(params, rendering_defaults, "locus_graph_cells_max", _DEFAULTS.graph_cells_max),
        require_graph_paper_background=True,
        graph_style_overrides={
            "origin_fraction_x": 0.5,
            "origin_fraction_y": 0.5,
            "axis_scale_labels_enabled": True,
            "axis_scale_label_max_abs": max(6, int(max_abs)),
            "origin_label_enabled": False,
        },
    )
    image, draw, background_meta = make_graph_scene_canvas(
        instance_seed=int(instance_seed),
        context=context,
        background_defaults=_BACKGROUND_DEFAULTS,
        require_graph_paper=True,
    )
    _draw_single_region(image, draw, region=region, context=context, max_abs=int(max_abs))

    marker_radius = _resolve_int_param(params, rendering_defaults, "marker_radius_px", _DEFAULTS.marker_radius_px)
    marker_radius = max(
        _resolve_int_param(params, rendering_defaults, "marker_radius_px_min", _DEFAULTS.marker_radius_px_min),
        min(_resolve_int_param(params, rendering_defaults, "marker_radius_px_max", _DEFAULTS.marker_radius_px_max), int(marker_radius)),
    )
    label_font_size_px = int(
        max(
            _resolve_int_param(params, rendering_defaults, "label_font_size_min", _DEFAULTS.label_font_size_min),
            min(
                _resolve_int_param(params, rendering_defaults, "label_font_size_max", _DEFAULTS.label_font_size_max),
                int(round(float(context.graph_spacing) * 0.75)),
            ),
        )
    )
    label_offset_px = _resolve_int_param(params, rendering_defaults, "label_offset_px", _DEFAULTS.label_offset_px)
    label_stroke_width = _resolve_int_param(params, rendering_defaults, "label_stroke_width", _DEFAULTS.label_stroke_width)
    center_color, candidate_color, color_meta = _resolve_marker_colors(rng)
    candidate_style = _sample_marker_style(rng, params=params, defaults=rendering_defaults, key="candidate_marker_style")
    center_point_px = _draw_center_marker(
        draw,
        context=context,
        region=region,
        marker_radius=int(marker_radius),
        label_font_size_px=int(label_font_size_px),
        label_offset_px=int(label_offset_px),
        label_stroke_width=int(label_stroke_width),
        color=center_color,
    )
    candidate_points_px_by_label = {
        str(label): graph_units_to_pixel(point, graph_origin=context.graph_origin, spacing=int(context.graph_spacing))
        for label, point in candidate_points_by_label.items()
    }
    render_radius = int(marker_radius) * int(context.scene_scale)
    for label in candidate_labels:
        _draw_marker(
            draw,
            scale_point(candidate_points_px_by_label[str(label)], int(context.scene_scale)),
            style=str(candidate_style),
            color=candidate_color,
            radius=int(render_radius),
            width=max(2, int(context.scene_scale) * 2),
        )
    blocked_points = [scale_point(candidate_points_px_by_label[str(label)], int(context.scene_scale)) for label in candidate_labels]
    if center_point_px is not None:
        blocked_points.append(scale_point(center_point_px, int(context.scene_scale)))
    draw_labeled_points(
        draw,
        points=[scale_point(candidate_points_px_by_label[str(label)], int(context.scene_scale)) for label in candidate_labels],
        labels=list(candidate_labels),
        label_offset_px=float(label_offset_px) * float(context.scene_scale),
        font_size_px=int(label_font_size_px),
        text_stroke_width=int(label_stroke_width) * int(context.scene_scale),
        blocked_points=blocked_points,
        blocked_point_clearance_px=float(render_radius + 7),
        marker_radius_px=0,
        marker_color=candidate_color,
        label_color=candidate_color,
        label_stroke_color=(255, 255, 255),
        canvas_size=int(context.canvas_size) * int(context.scene_scale),
    )
    candidate_bboxes_by_label = {
        str(label): _marker_bbox(
            candidate_points_px_by_label[str(label)],
            radius=int(marker_radius),
            canvas_width=int(context.canvas_size),
            canvas_height=int(context.canvas_size),
        )
        for label in candidate_labels
    }
    image, background_meta_final, post_noise_meta = finalize_graph_scene_image(
        image,
        instance_seed=int(instance_seed),
        context=context,
        background_meta=background_meta,
        noise_defaults=_NOISE_DEFAULTS,
    )
    marker_meta = {
        "candidate_marker_style": str(candidate_style),
        "marker_radius_px": int(marker_radius),
        "region_fill": list(_REGION_FILL),
        "region_outline": list(_REGION_OUTLINE),
        "region_fill_alpha": 78,
        **dict(color_meta),
    }
    return _PointScene(
        region=region,
        candidate_points_by_label=dict(candidate_points_by_label),
        candidate_bboxes_by_label=dict(candidate_bboxes_by_label),
        candidate_points_px_by_label=dict(candidate_points_px_by_label),
        center_point_px=center_point_px,
        marker_meta=dict(marker_meta),
        image=image,
        background_meta=dict(background_meta_final),
        post_noise_meta=dict(post_noise_meta),
        render_spec_extra={
            "canvas_size": int(context.canvas_size),
            "coord_space": "pixel",
            "graph_coordinate_frame": dict(context.graph_frame),
            "graph_paper_grid": graph_paper_grid_from_frame(context.graph_frame),
            "scene_scale": int(context.scene_scale),
            **dict(context.graph_layout_metadata),
        },
    )


def _panel_style(rng) -> Tuple[CoordinatePanelStyle, Dict[str, Any]]:
    index = int(rng.randrange(len(_PANEL_STYLES)))
    style = _PANEL_STYLES[int(index)]
    return style, {"style_index": int(index), "style": style.to_trace_dict()}


def _panel_target_region(query_id: str) -> _RegionSpec:
    if str(query_id) == "circle_inequality_panel_match":
        return _RegionSpec("circle", {"cx": 0, "cy": 0, "r": 4}, "x^2 + y^2 <= 16")
    if str(query_id) == "vertical_strip_panel_match":
        return _RegionSpec("vertical_strip", {"x_min": -2, "x_max": 2}, "-2 <= x <= 2")
    if str(query_id) == "horizontal_halfplane_panel_match":
        return _RegionSpec("upper_halfplane", {"y_min": -1}, "y >= -1")
    if str(query_id) == "two_inequality_panel_match":
        return _RegionSpec("half_plane_intersection", {"x_min": -1, "y_max": 3}, "x >= -1 and y <= 3")
    raise ValueError(f"unsupported locus panel query: {query_id}")


def _panel_distractor_regions(query_id: str) -> Tuple[_RegionSpec, ...]:
    if str(query_id) == "circle_inequality_panel_match":
        return (
            _RegionSpec("circle", {"cx": 0, "cy": 0, "r": 3}, "x^2 + y^2 <= 9"),
            _RegionSpec("circle", {"cx": 1, "cy": 0, "r": 4}, "(x - 1)^2 + y^2 <= 16"),
            _RegionSpec("annulus", {"cx": 0, "cy": 0, "inner_r": 2, "outer_r": 4}, "4 <= x^2 + y^2 <= 16"),
            _RegionSpec("vertical_strip", {"x_min": -2, "x_max": 2}, "-2 <= x <= 2"),
            _RegionSpec("horizontal_strip", {"y_min": -2, "y_max": 2}, "-2 <= y <= 2"),
        )
    if str(query_id) == "vertical_strip_panel_match":
        return (
            _RegionSpec("horizontal_strip", {"y_min": -2, "y_max": 2}, "-2 <= y <= 2"),
            _RegionSpec("vertical_strip", {"x_min": -3, "x_max": 1}, "-3 <= x <= 1"),
            _RegionSpec("right_halfplane", {"x_min": -2}, "x >= -2"),
            _RegionSpec("left_halfplane", {"x_max": 2}, "x <= 2"),
            _RegionSpec("circle", {"cx": 0, "cy": 0, "r": 3}, "x^2 + y^2 <= 9"),
        )
    if str(query_id) == "horizontal_halfplane_panel_match":
        return (
            _RegionSpec("lower_halfplane", {"y_max": -1}, "y <= -1"),
            _RegionSpec("right_halfplane", {"x_min": -1}, "x >= -1"),
            _RegionSpec("left_halfplane", {"x_max": -1}, "x <= -1"),
            _RegionSpec("horizontal_strip", {"y_min": -1, "y_max": 3}, "-1 <= y <= 3"),
            _RegionSpec("vertical_strip", {"x_min": -2, "x_max": 2}, "-2 <= x <= 2"),
        )
    if str(query_id) == "two_inequality_panel_match":
        return (
            _RegionSpec("half_plane_intersection", {"x_max": -1, "y_max": 3}, "x <= -1 and y <= 3"),
            _RegionSpec("half_plane_intersection", {"x_min": -1, "y_min": 3}, "x >= -1 and y >= 3"),
            _RegionSpec("half_plane_intersection", {"x_min": 1, "y_max": 3}, "x >= 1 and y <= 3"),
            _RegionSpec("half_plane_intersection", {"x_min": -1, "y_max": 1}, "x >= -1 and y <= 1"),
            _RegionSpec("vertical_strip", {"x_min": -1, "x_max": 3}, "-1 <= x <= 3"),
        )
    raise ValueError(f"unsupported locus panel query: {query_id}")


def _panel_region_bbox(
    region: _RegionSpec,
    *,
    plot_bbox: BBox,
    config: CoordinatePanelConfig,
    radius_key: str,
) -> Tuple[int, int, int, int]:
    params = dict(region.params)
    cx = int(params.get("cx", 0))
    cy = int(params.get("cy", 0))
    radius = int(params[radius_key])
    left_top = graph_point_to_panel_pixel((cx - radius, cy + radius), plot_bbox=plot_bbox, config=config)
    right_bottom = graph_point_to_panel_pixel((cx + radius, cy - radius), plot_bbox=plot_bbox, config=config)
    return (
        int(round(float(left_top[0]))),
        int(round(float(left_top[1]))),
        int(round(float(right_bottom[0]))),
        int(round(float(right_bottom[1]))),
    )


def _draw_panel_region(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    *,
    region: _RegionSpec,
    plot_bbox: BBox,
    config: CoordinatePanelConfig,
) -> None:
    clip = tuple(int(value) for value in plot_bbox)
    mask = Image.new("L", image.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    if str(region.kind) == "circle":
        bbox = _clip_bbox(_panel_region_bbox(region, plot_bbox=plot_bbox, config=config, radius_key="r"), clip)
        if bbox is not None:
            mask_draw.ellipse(bbox, fill=76)
            _apply_region_mask(image, mask, color=_REGION_FILL)
            draw.ellipse(bbox, outline=_REGION_OUTLINE, width=2)
        return
    if str(region.kind) == "annulus":
        outer = _clip_bbox(_panel_region_bbox(region, plot_bbox=plot_bbox, config=config, radius_key="outer_r"), clip)
        inner = _clip_bbox(_panel_region_bbox(region, plot_bbox=plot_bbox, config=config, radius_key="inner_r"), clip)
        if outer is not None:
            mask_draw.ellipse(outer, fill=76)
            if inner is not None:
                mask_draw.ellipse(inner, fill=0)
            _apply_region_mask(image, mask, color=_REGION_FILL)
            draw.ellipse(outer, outline=_REGION_OUTLINE, width=2)
            if inner is not None:
                draw.ellipse(inner, outline=_REGION_OUTLINE, width=2)
        return
    x_min, y_min, x_max, y_max = _constraint_rect(region, grid_min=int(config.grid_min), grid_max=int(config.grid_max))
    top_left = graph_point_to_panel_pixel((x_min, y_max), plot_bbox=plot_bbox, config=config)
    bottom_right = graph_point_to_panel_pixel((x_max, y_min), plot_bbox=plot_bbox, config=config)
    rect = _clip_bbox((top_left[0], top_left[1], bottom_right[0], bottom_right[1]), clip)
    if rect is None:
        return
    mask_draw.rectangle(rect, fill=74)
    _apply_region_mask(image, mask, color=_REGION_FILL)
    params = dict(region.params)
    for key in ("x_min", "x_max"):
        if key not in params:
            continue
        x_value = int(params[key])
        x_px, _ = graph_point_to_panel_pixel((x_value, 0), plot_bbox=plot_bbox, config=config)
        draw.line([(float(x_px), clip[1]), (float(x_px), clip[3])], fill=_BOUNDARY_DASH_FILL, width=2)
    for key in ("y_min", "y_max"):
        if key not in params:
            continue
        _, y_px = graph_point_to_panel_pixel((0, int(params[key])), plot_bbox=plot_bbox, config=config)
        draw.line([(clip[0], float(y_px)), (clip[2], float(y_px))], fill=_BOUNDARY_DASH_FILL, width=2)


def _draw_condition_box(
    draw: ImageDraw.ImageDraw,
    *,
    canvas_width: int,
    text: str,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
) -> List[int]:
    font_size = _resolve_int_param(params, rendering_defaults, "locus_condition_label_font_size", _DEFAULTS.condition_label_font_size)
    font = load_font(max(12, int(font_size)), bold=True)
    label_text = f"Condition: {text}"
    text_bbox = draw.textbbox((0, 0), label_text, font=font)
    pad_x = 12
    pad_y = 6
    width = int(text_bbox[2] - text_bbox[0]) + (2 * pad_x)
    height = int(text_bbox[3] - text_bbox[1]) + (2 * pad_y)
    left = int(round((int(canvas_width) - width) / 2.0))
    top = 10
    box = [left, top, left + width, top + height]
    draw.rounded_rectangle(box, radius=6, fill=(255, 255, 255), outline=(82, 96, 116), width=2)
    draw.text((left + pad_x, top + pad_y), label_text, fill=(30, 43, 62), font=font)
    return [int(value) for value in box]


def _render_panel_scene(
    query: _ResolvedQuery,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
) -> _PanelScene:
    rng = spawn_rng(int(instance_seed), f"{PANEL_TASK_ID}.render")
    panel_count = max(4, _resolve_int_param(params, generation_defaults, "locus_panel_count", _DEFAULTS.panel_count))
    if int(panel_count) > len(query.label_pool):
        raise ValueError("locus_panel_count cannot exceed panel label pool length")
    label_pool = tuple(query.label_pool[: int(panel_count)])
    if str(query.winner_label) not in set(label_pool):
        label_pool = tuple([str(query.winner_label), *[label for label in label_pool if label != str(query.winner_label)]])
        label_pool = label_pool[: int(panel_count)]

    target_region = _panel_target_region(str(query.query_id))
    distractors = list(_panel_distractor_regions(str(query.query_id)))
    rng.shuffle(distractors)
    region_by_label: Dict[str, _RegionSpec] = {}
    distractor_iter = iter(distractors)
    for label in label_pool:
        region_by_label[str(label)] = target_region if str(label) == str(query.winner_label) else next(distractor_iter)

    panel_config = CoordinatePanelConfig(
        grid_min=_resolve_int_param(params, rendering_defaults, "locus_panel_grid_min", _DEFAULTS.panel_grid_min),
        grid_max=_resolve_int_param(params, rendering_defaults, "locus_panel_grid_max", _DEFAULTS.panel_grid_max),
        columns=3,
        rows=2,
    )
    canvas_width = _resolve_int_param(params, rendering_defaults, "locus_panel_canvas_width", _DEFAULTS.panel_canvas_width)
    canvas_height = _resolve_int_param(params, rendering_defaults, "locus_panel_canvas_height", _DEFAULTS.panel_canvas_height)
    top_reserved = _resolve_int_param(params, rendering_defaults, "locus_panel_top_reserved_px", _DEFAULTS.panel_top_reserved_px)
    image, background_meta = make_background_canvas(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=_PANEL_BACKGROUND_DEFAULTS,
        fallback_color=(248, 250, 252),
    )
    draw = ImageDraw.Draw(image)
    condition_label_bbox = _draw_condition_box(
        draw,
        canvas_width=int(canvas_width),
        text=str(target_region.condition_text),
        params=params,
        rendering_defaults=rendering_defaults,
    )
    style, panel_style_meta = _panel_style(rng)
    layout = coordinate_panel_layout(
        int(canvas_width),
        max(320, int(canvas_height) - int(top_reserved)),
        config=panel_config,
    )
    layout["margin_y"] = int(layout["margin_y"]) + int(top_reserved)
    panels_by_label: Dict[str, _PanelSpec] = {}
    for index, label in enumerate(label_pool):
        panel_bbox = panel_bbox_for_index(layout, int(index), config=panel_config)
        plot_bbox = plot_bbox_for_panel(panel_bbox)
        draw_coordinate_panel_grid(
            draw,
            panel_bbox=panel_bbox,
            plot_bbox=plot_bbox,
            label=str(label),
            config=panel_config,
            style=style,
        )
        _draw_panel_region(
            image,
            draw,
            region=region_by_label[str(label)],
            plot_bbox=plot_bbox,
            config=panel_config,
        )
        panels_by_label[str(label)] = _PanelSpec(
            label=str(label),
            region=region_by_label[str(label)],
            panel_bbox=[int(value) for value in panel_bbox],
            plot_bbox=[int(value) for value in plot_bbox],
            is_answer=str(label) == str(query.winner_label),
        )
    image, post_noise_meta = apply_post_image_noise(
        image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=_NOISE_DEFAULTS,
    )
    return _PanelScene(
        condition_text=str(target_region.condition_text),
        panels_by_label=dict(panels_by_label),
        condition_label_bbox_px=list(condition_label_bbox),
        panel_style_meta=dict(panel_style_meta),
        marker_meta={
            "region_fill": list(_REGION_FILL),
            "region_outline": list(_REGION_OUTLINE),
            "region_fill_alpha": 76,
        },
        image=image,
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
    )


def _region_trace(region: _RegionSpec) -> Dict[str, Any]:
    return {
        "kind": str(region.kind),
        "params": {str(key): int(value) for key, value in region.params.items()},
        "condition_text": str(region.condition_text),
    }


def _build_complexity(*, task_id: str, query_id: str, object_count: int, panel_count: int = 1) -> Any:
    weights = resolve_geometry_complexity_weights(
        _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        task_id=str(task_id),
    )
    is_panel = int(panel_count) > 1
    region_reasoning = 0.58
    if "annulus" in str(query_id):
        region_reasoning = 0.66
    elif "half_plane_intersection" in str(query_id) or "two_inequality" in str(query_id):
        region_reasoning = 0.70
    return build_geometry_task_complexity(
        weights=weights,
        components={
            "visual_scan": clamp_unit_interval(0.40 + (0.06 * float(panel_count)) + (0.015 * float(object_count))),
            "coordinate_reasoning": clamp_unit_interval(region_reasoning + (0.08 if is_panel else 0.0)),
            "ambiguity": 0.50 if is_panel else 0.44,
            "output_burden": 0.24,
        },
    )


def _point_trace_payload(
    *,
    query: _ResolvedQuery,
    rendered: _PointScene,
    prompt_defaults: Mapping[str, Any],
    prompt_artifacts: Any,
    evidence_value: List[List[int]],
) -> Dict[str, Any]:
    candidate_trace = {
        str(label): {
            "point_graph": [int(value) for value in rendered.candidate_points_by_label[str(label)]],
            "point_px": [float(value) for value in rendered.candidate_points_px_by_label[str(label)]],
            "bbox_px": list(rendered.candidate_bboxes_by_label[str(label)]),
            "inside_region": bool(_region_contains(rendered.region, rendered.candidate_points_by_label[str(label)])),
            "is_answer": str(label) == str(query.winner_label),
        }
        for label in sorted(rendered.candidate_points_by_label)
    }
    return {
        "scene_ir": {
            "scene_kind": "geometry_coordinate_locus_region",
            "entities": [
                {
                    "entity_type": "candidate_point",
                    "label": str(label),
                    **dict(payload),
                }
                for label, payload in candidate_trace.items()
            ],
            "relations": {
                "scene_id": SCENE_ID,
                "query_id": str(query.query_id),
                "query_id_probabilities": dict(query.query_probabilities),
                "winner_label": str(query.winner_label),
                "region": _region_trace(rendered.region),
            },
        },
        "query_spec": {
            "query_id": str(query.query_id),
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": {
                "scene_id": SCENE_ID,
                "query_id": str(query.query_id),
                "query_id_probabilities": dict(query.query_probabilities),
                "winner_label": str(query.winner_label),
                "winner_label_probabilities": dict(query.winner_label_probabilities),
                "candidate_label_pool": list(rendered.candidate_points_by_label.keys()),
            },
        },
        "render_spec": {
            **dict(rendered.render_spec_extra),
            "scene_id": SCENE_ID,
            "marker_style": dict(rendered.marker_meta),
            "post_image_noise": dict(rendered.post_noise_meta),
            "background_style": dict(rendered.background_meta),
        },
        "render_map": {
            "coord_space": "pixel",
            "candidate_points_graph_by_label": {
                str(label): [int(value) for value in point] for label, point in rendered.candidate_points_by_label.items()
            },
            "candidate_points_px_by_label": {
                str(label): [float(value) for value in point] for label, point in rendered.candidate_points_px_by_label.items()
            },
            "candidate_bboxes_px_by_label": dict(rendered.candidate_bboxes_by_label),
        },
        "execution_trace": {
            "scene_id": SCENE_ID,
            "query_id": str(query.query_id),
            "answer_type": "option_letter",
            "answer_value": str(query.winner_label),
            "region": _region_trace(rendered.region),
            "center_point_px": list(rendered.center_point_px) if rendered.center_point_px is not None else None,
            "candidate_points_by_label": dict(candidate_trace),
            "query_id_probabilities": dict(query.query_probabilities),
        },
        "witness_symbolic": {
            "type": "coordinate_locus_point_membership",
            "answer_label": str(query.winner_label),
            "region": _region_trace(rendered.region),
            "candidate_points_by_label": dict(candidate_trace),
        },
        "projected_evidence": {
            "type": "bbox_set",
            "bbox_set": list(evidence_value),
            "candidate_bboxes_px_by_label": dict(rendered.candidate_bboxes_by_label),
        },
    }


def _panel_trace_payload(
    *,
    query: _ResolvedQuery,
    rendered: _PanelScene,
    prompt_defaults: Mapping[str, Any],
    prompt_artifacts: Any,
    evidence_value: List[List[int]],
) -> Dict[str, Any]:
    panels_trace = {
        str(label): {
            "label": str(label),
            "region": _region_trace(spec.region),
            "panel_bbox": list(spec.panel_bbox),
            "plot_bbox": list(spec.plot_bbox),
            "is_answer": bool(spec.is_answer),
        }
        for label, spec in rendered.panels_by_label.items()
    }
    return {
        "scene_ir": {
            "scene_kind": "geometry_coordinate_locus_panel_grid",
            "entities": [dict(panels_trace[str(label)]) for label in sorted(panels_trace)],
            "relations": {
                "scene_id": SCENE_ID,
                "query_id": str(query.query_id),
                "query_id_probabilities": dict(query.query_probabilities),
                "winner_label": str(query.winner_label),
                "condition_text": str(rendered.condition_text),
            },
        },
        "query_spec": {
            "query_id": str(query.query_id),
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": {
                "scene_id": SCENE_ID,
                "query_id": str(query.query_id),
                "query_id_probabilities": dict(query.query_probabilities),
                "winner_label": str(query.winner_label),
                "winner_label_probabilities": dict(query.winner_label_probabilities),
                "candidate_label_pool": list(rendered.panels_by_label.keys()),
            },
        },
        "render_spec": {
            "canvas_width": int(rendered.image.size[0]),
            "canvas_height": int(rendered.image.size[1]),
            "coord_space": "pixel",
            "scene_id": SCENE_ID,
            "panel_count": int(len(rendered.panels_by_label)),
            "condition_label_bbox_px": list(rendered.condition_label_bbox_px),
            "panel_style": dict(rendered.panel_style_meta),
            "marker_style": dict(rendered.marker_meta),
            "background_style": dict(rendered.background_meta),
            "post_image_noise": dict(rendered.post_noise_meta),
        },
        "render_map": {
            "coord_space": "pixel",
            "panel_bboxes": {str(label): list(spec.panel_bbox) for label, spec in rendered.panels_by_label.items()},
            "plot_bboxes": {str(label): list(spec.plot_bbox) for label, spec in rendered.panels_by_label.items()},
        },
        "execution_trace": {
            "scene_id": SCENE_ID,
            "query_id": str(query.query_id),
            "answer_type": "option_letter",
            "answer_value": str(query.winner_label),
            "condition_text": str(rendered.condition_text),
            "panels_by_label": dict(panels_trace),
            "query_id_probabilities": dict(query.query_probabilities),
        },
        "witness_symbolic": {
            "type": "coordinate_locus_panel_match",
            "answer_label": str(query.winner_label),
            "condition_text": str(rendered.condition_text),
            "panels_by_label": dict(panels_trace),
        },
        "projected_evidence": {
            "type": "bbox_set",
            "bbox_set": list(evidence_value),
            "panel_bbox_by_label": {str(label): list(spec.panel_bbox) for label, spec in rendered.panels_by_label.items()},
        },
    }


@register_task
class GeometryCoordinateLocusPointLabelTask:
    """Choose the candidate point that lies in a shaded coordinate locus region."""

    task_id = POINT_TASK_ID
    domain = "geometry"
    task_group = "coordinate"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        generation_defaults, rendering_defaults, prompt_defaults_all = _split_defaults_for_task(self.task_id)
        label_pool = _resolve_label_pool(params, generation_defaults, "locus_candidate_labels", DEFAULT_LABEL_POOL)
        query = _resolve_query(
            task_id=self.task_id,
            query_ids=POINT_QUERY_IDS,
            label_pool=label_pool,
            instance_seed=int(instance_seed),
            params=params,
        )
        rendered = _render_point_scene(
            query,
            instance_seed=int(instance_seed),
            params=params,
            generation_defaults=generation_defaults,
            rendering_defaults=rendering_defaults,
        )
        prompt_defaults = required_group_defaults(
            prompt_defaults_all,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "evidence_hint_candidate_bbox",
                "answer_hint_option_letter",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        evidence_value = [list(rendered.candidate_bboxes_by_label[str(query.winner_label)])]
        json_example, json_example_answer_only = resolve_prompt_json_examples(
            prompt_defaults_all,
            evidence_value=evidence_value,
            answer_type="option_letter",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint_candidate_bbox"]),
                "answer_hint": str(prompt_defaults["answer_hint_option_letter"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="option_letter", value=str(query.winner_label)),
            evidence_gt=TypedValue(type="bbox_set", value=evidence_value),
            image=rendered.image,
            image_id="img0",
            trace_payload=_point_trace_payload(
                query=query,
                rendered=rendered,
                prompt_defaults=prompt_defaults,
                prompt_artifacts=prompt_artifacts,
                evidence_value=evidence_value,
            ),
            complexity=_build_complexity(
                task_id=self.task_id,
                query_id=str(query.query_id),
                object_count=len(rendered.candidate_points_by_label),
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class GeometryCoordinateLocusPanelMatchLabelTask:
    """Choose the panel whose shaded coordinate region matches the condition box."""

    task_id = PANEL_TASK_ID
    domain = "geometry"
    task_group = "coordinate"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        generation_defaults, rendering_defaults, prompt_defaults_all = _split_defaults_for_task(self.task_id)
        label_pool = _resolve_label_pool(params, generation_defaults, "locus_panel_labels", DEFAULT_LABEL_POOL)
        query = _resolve_query(
            task_id=self.task_id,
            query_ids=PANEL_QUERY_IDS,
            label_pool=label_pool,
            instance_seed=int(instance_seed),
            params=params,
        )
        rendered = _render_panel_scene(
            query,
            instance_seed=int(instance_seed),
            params=params,
            generation_defaults=generation_defaults,
            rendering_defaults=rendering_defaults,
        )
        prompt_defaults = required_group_defaults(
            prompt_defaults_all,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "evidence_hint_selected_panel_bbox",
                "answer_hint_option_letter",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        evidence_value = [list(rendered.panels_by_label[str(query.winner_label)].panel_bbox)]
        json_example, json_example_answer_only = resolve_prompt_json_examples(
            prompt_defaults_all,
            evidence_value=evidence_value,
            answer_type="option_letter",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint_selected_panel_bbox"]),
                "answer_hint": str(prompt_defaults["answer_hint_option_letter"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="option_letter", value=str(query.winner_label)),
            evidence_gt=TypedValue(type="bbox_set", value=evidence_value),
            image=rendered.image,
            image_id="img0",
            trace_payload=_panel_trace_payload(
                query=query,
                rendered=rendered,
                prompt_defaults=prompt_defaults,
                prompt_artifacts=prompt_artifacts,
                evidence_value=evidence_value,
            ),
            complexity=_build_complexity(
                task_id=self.task_id,
                query_id=str(query.query_id),
                object_count=len(rendered.panels_by_label),
                panel_count=len(rendered.panels_by_label),
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = [
    "GeometryCoordinateLocusPanelMatchLabelTask",
    "GeometryCoordinateLocusPointLabelTask",
]
