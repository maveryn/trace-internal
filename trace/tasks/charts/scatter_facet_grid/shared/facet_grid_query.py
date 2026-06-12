"""Faceted scatter-density chart task."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from .....core.sampling import normalize_positive_weights, weighted_choice
from .....core.seed import spawn_rng
from .....core.scene_config import get_scene_defaults
from ....shared.config_defaults import (
    group_default,
    split_scene_generation_rendering_prompt_defaults,
)
from ....shared.render_variation import apply_layout_jitter_to_margins, resolve_render_int, resolve_render_rgb
from ....shared.text_legibility import draw_text_traced
from ....shared.text_rendering import load_font
from ...shared.label_assets import (
    ResolvedChartLabels,
    resolve_chart_panel_labels,
    validate_chart_label_namespaces,
)
from ...shared.visual_defaults import load_chart_scene_background_defaults, load_chart_scene_noise_defaults


TASK_ID = "charts_scatter_facet_grid_query_base"
SCENE_ID = "scatter_facet_grid"

_SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "upper_right_density_extremum_label",
    "upper_left_density_extremum_label",
    "lower_right_density_extremum_label",
    "lower_left_density_extremum_label",
)
_REGION_BY_QUERY_ID: Dict[str, str] = {
    "upper_right_density_extremum_label": "upper_right",
    "upper_left_density_extremum_label": "upper_left",
    "lower_right_density_extremum_label": "lower_right",
    "lower_left_density_extremum_label": "lower_left",
}
_REGION_PHRASE_BY_REGION: Dict[str, str] = {
    "upper_right": "upper-right",
    "upper_left": "upper-left",
    "lower_right": "lower-right",
    "lower_left": "lower-left",
}
_SUPPORTED_LAYOUTS: Tuple[str, ...] = ("2x3", "3x3", "3x4")

_TASK_GROUP_DEFAULTS = get_scene_defaults("charts", "scatter_facet_grid")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_scene_background_defaults(scene_id="scatter_facet_grid")
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id="scatter_facet_grid", apply_prob=0.0)

_REASONING_LOAD_BY_QUERY: Dict[str, float] = {
    "upper_right_density_extremum_label": 0.72,
    "upper_left_density_extremum_label": 0.72,
    "lower_right_density_extremum_label": 0.72,
    "lower_left_density_extremum_label": 0.72,
}

RGB = Tuple[int, int, int]
BBox = Tuple[float, float, float, float]


@dataclass(frozen=True)
class _Point:
    point_id: str
    panel_label: str
    x_value: float
    y_value: float
    layer: str


@dataclass(frozen=True)
class _Panel:
    label: str
    color_rgb: RGB
    background_points: Tuple[_Point, ...]
    target_points: Tuple[_Point, ...]
    distractor_points: Tuple[_Point, ...]
    target_density_score: float
    target_point_count: int
    target_spread: float


@dataclass(frozen=True)
class _Query:
    query_id: str
    region: str
    answer_label: str
    annotation_point_ids: Tuple[str, ...]
    trace: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    panels: Tuple[_Panel, ...]
    query: _Query
    rows: int
    cols: int
    layout_id: str
    label_resolution: ResolvedChartLabels


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    grid_left_px: int
    grid_right_px: int
    grid_top_px: int
    grid_bottom_px: int
    panel_gap_x_px: int
    panel_gap_y_px: int
    axis_line_width_px: int
    grid_line_width_px: int
    point_radius_px: int
    title_font_size_px: int
    panel_label_font_size_px: int
    axis_label_font_size_px: int
    tick_font_size_px: int
    background_point_rgb: RGB
    foreground_stroke_rgb: RGB
    region_tint_rgb: RGB
    axis_color_rgb: RGB
    grid_color_rgb: RGB
    text_color_rgb: RGB
    text_stroke_rgb: RGB
    panel_fill_rgb: RGB
    panel_border_rgb: RGB
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    panel_bboxes: Dict[str, List[float]]
    panel_label_bboxes: Dict[str, List[float]]
    region_bboxes: Dict[str, List[float]]
    density_region_bboxes: Dict[str, List[float]]
    point_bboxes: Dict[str, List[float]]
    point_centers: Dict[str, List[float]]
    title_bbox_px: List[float]
    x_axis_label_bbox_px: List[float]
    y_axis_label_bbox_px: List[float]
    title_text: str


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _bbox_union(boxes: Sequence[Sequence[float]]) -> List[float]:
    valid = [tuple(float(value) for value in box[:4]) for box in boxes if len(box) >= 4]
    if not valid:
        return []
    return _bbox(
        (
            min(box[0] for box in valid),
            min(box[1] for box in valid),
            max(box[2] for box in valid),
            max(box[3] for box in valid),
        )
    )


def _as_rgb(value: Any, fallback: RGB) -> RGB:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 3:
        return tuple(int(channel) for channel in fallback)
    return tuple(max(0, min(255, int(channel))) for channel in value[:3])  # type: ignore[index]


def _render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


def _resolve_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(
        resolve_render_int(
            params,
            _RENDER_DEFAULTS,
            str(key),
            int(fallback),
            instance_seed=_render_style_seed(params),
            namespace=TASK_ID,
        )
    )


def _resolve_rgb(params: Mapping[str, Any], key: str, fallback: RGB) -> RGB:
    return resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        str(key),
        tuple(int(channel) for channel in fallback),
        instance_seed=_render_style_seed(params),
        namespace=TASK_ID,
    )


def _resolve_layout(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, int, int, Dict[str, float]]:
    raw_weights = params.get("facet_layout_weights", group_default(_GEN_DEFAULTS, "facet_layout_weights", {}))
    if not isinstance(raw_weights, Mapping):
        raw_weights = {}
    probabilities = normalize_positive_weights(
        {str(key): float(value) for key, value in raw_weights.items()},
        default_keys=_SUPPORTED_LAYOUTS,
    )
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.layout")
    layout_id = weighted_choice(rng, probabilities, sort_keys=True)
    rows_text, cols_text = str(layout_id).split("x", 1)
    return str(layout_id), int(rows_text), int(cols_text), dict(probabilities)


def _gen_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), int(fallback))))


def _gen_float(params: Mapping[str, Any], key: str, fallback: float) -> float:
    return float(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), float(fallback))))


def _region_bounds(region: str) -> Tuple[float, float, float, float]:
    if str(region) == "upper_right":
        return (60.0, 60.0, 100.0, 100.0)
    if str(region) == "upper_left":
        return (0.0, 60.0, 40.0, 100.0)
    if str(region) == "lower_right":
        return (60.0, 0.0, 100.0, 40.0)
    if str(region) == "lower_left":
        return (0.0, 0.0, 40.0, 40.0)
    raise ValueError(f"unsupported scatter facet region: {region}")


def _outside_region_center(rng, region: str) -> Tuple[float, float]:
    if "upper" in str(region):
        y = float(rng.uniform(18.0, 42.0))
    else:
        y = float(rng.uniform(58.0, 82.0))
    if "right" in str(region):
        x = float(rng.uniform(18.0, 42.0))
    else:
        x = float(rng.uniform(58.0, 82.0))
    return x, y


def _sample_point_in_panel(
    rng,
    *,
    panel_label: str,
    point_id: str,
    center_x: float,
    center_y: float,
    spread: float,
    layer: str,
    x_bounds: Tuple[float, float] = (2.0, 98.0),
    y_bounds: Tuple[float, float] = (2.0, 98.0),
) -> _Point:
    x = max(float(x_bounds[0]), min(float(x_bounds[1]), float(rng.gauss(float(center_x), float(spread)))))
    y = max(float(y_bounds[0]), min(float(y_bounds[1]), float(rng.gauss(float(center_y), float(spread)))))
    return _Point(
        point_id=str(point_id),
        panel_label=str(panel_label),
        x_value=float(x),
        y_value=float(y),
        layer=str(layer),
    )


def _panel_density_score(*, target_point_count: int, target_spread: float) -> float:
    return float(target_point_count) / max(1.0, float(target_spread) ** 2)


def _density_profile_scores(rng, *, panel_count: int, answer_index: int, params: Mapping[str, Any]) -> List[float]:
    gap_min = _gen_float(params, "facet_density_winner_gap_min", 0.16)
    gap_max = _gen_float(params, "facet_density_winner_gap_max", 0.28)
    runner_score = 1.0 / (1.0 + float(rng.uniform(gap_min, gap_max)))
    scores = [float(rng.uniform(0.42, min(0.74, runner_score - 0.06))) for _ in range(int(panel_count))]
    scores[int(answer_index)] = 1.0
    runner_candidates = [index for index in range(int(panel_count)) if int(index) != int(answer_index)]
    runner_index = int(rng.choice(runner_candidates))
    scores[runner_index] = float(runner_score)
    return scores


def _build_dataset(params: Mapping[str, Any], *, instance_seed: int, query_id: str, query_id_probabilities: Mapping[str, float]) -> _Dataset:
    layout_id, rows, cols, layout_probabilities = _resolve_layout(params, instance_seed=int(instance_seed))
    capacity = int(rows) * int(cols)
    panel_min = max(1, _gen_int(params, "facet_panel_count_min", 6))
    panel_max = max(panel_min, _gen_int(params, "facet_panel_count_max", 12))
    low = max(panel_min, min(capacity, capacity - max(0, int(params.get("facet_layout_empty_slot_max", group_default(_GEN_DEFAULTS, "facet_layout_empty_slot_max", 2))))))
    high = min(panel_max, capacity)
    if low > high:
        low = high
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    panel_count = int(rng.randint(int(low), int(high)))
    region = str(_REGION_BY_QUERY_ID[str(query_id)])
    x0, y0, x1, y1 = _region_bounds(region)
    labels_resolution = resolve_chart_panel_labels(
        rng,
        count=int(panel_count),
        min_chars=int(params.get("facet_label_min_chars", group_default(_GEN_DEFAULTS, "facet_label_min_chars", 3))),
        max_chars=int(params.get("facet_label_max_chars", group_default(_GEN_DEFAULTS, "facet_label_max_chars", 10))),
        allow_spaces=bool(params.get("facet_label_allow_spaces", group_default(_GEN_DEFAULTS, "facet_label_allow_spaces", False))),
        variant_weights=params.get(
            "panel_label_variant_weights",
            group_default(
                _GEN_DEFAULTS,
                "panel_label_variant_weights",
                {
                    "named_compact": 1.0,
                    "technical_topics": 1.0,
                    "condition_labels": 0.75,
                    "temporal_sequence": 0.25,
                    "report_topics": 0.5,
                },
            ),
        ),
    )
    labels = tuple(str(label) for label in labels_resolution.labels)
    panel_label_collision_check = validate_chart_label_namespaces(
        panel_labels=labels,
        other_label_groups={},
        context="scatter facet-grid panel labels",
    )
    answer_index = int(rng.randrange(int(panel_count)))
    density_shape_scores = _density_profile_scores(rng, panel_count=int(panel_count), answer_index=int(answer_index), params=params)

    palette_raw = params.get("facet_palette_rgb", group_default(_RENDER_DEFAULTS, "facet_palette_rgb", ()))
    palette = tuple(_as_rgb(value, (79, 103, 185)) for value in palette_raw) if isinstance(palette_raw, Sequence) and not isinstance(palette_raw, (str, bytes)) else ()
    if not palette:
        palette = ((79, 103, 185), (173, 73, 126), (52, 133, 91), (210, 128, 44), (113, 82, 171), (48, 145, 165))

    background_min = _gen_int(params, "facet_background_points_min", 28)
    background_max = max(background_min, _gen_int(params, "facet_background_points_max", 42))
    distractor_min = _gen_int(params, "facet_distractor_points_min", 10)
    distractor_max = max(distractor_min, _gen_int(params, "facet_distractor_points_max", 18))
    panels: list[_Panel] = []
    for index, label in enumerate(labels):
        shape_score = float(density_shape_scores[int(index)])
        target_count = int(round(18.0 + (8.0 * shape_score)))
        target_spread = float(5.0 + (2.4 * (1.0 - shape_score)))
        center_x = float(rng.uniform(x0 + 11.0, x1 - 11.0))
        center_y = float(rng.uniform(y0 + 11.0, y1 - 11.0))
        background_points = tuple(
            _Point(
                point_id=f"{label}.bg{point_index}",
                panel_label=str(label),
                x_value=float(rng.uniform(2.0, 98.0)),
                y_value=float(rng.uniform(2.0, 98.0)),
                layer="background",
            )
            for point_index in range(int(rng.randint(background_min, background_max)))
        )
        target_points = tuple(
            _sample_point_in_panel(
                rng,
                panel_label=str(label),
                point_id=f"{label}.target{point_index}",
                center_x=center_x,
                center_y=center_y,
                spread=target_spread,
                layer="target",
                x_bounds=(float(x0) + 2.0, float(x1) - 2.0),
                y_bounds=(float(y0) + 2.0, float(y1) - 2.0),
            )
            for point_index in range(int(target_count))
        )
        distractor_center_x, distractor_center_y = _outside_region_center(rng, region)
        distractor_points = tuple(
            _sample_point_in_panel(
                rng,
                panel_label=str(label),
                point_id=f"{label}.dist{point_index}",
                center_x=distractor_center_x,
                center_y=distractor_center_y,
                spread=float(rng.uniform(5.8, 8.2)),
                layer="distractor",
            )
            for point_index in range(int(rng.randint(distractor_min, distractor_max)))
        )
        panels.append(
            _Panel(
                label=str(label),
                color_rgb=tuple(palette[int(index) % len(palette)]),
                background_points=tuple(background_points),
                target_points=tuple(target_points),
                distractor_points=tuple(distractor_points),
                target_density_score=_panel_density_score(target_point_count=int(target_count), target_spread=float(target_spread)),
                target_point_count=int(target_count),
                target_spread=float(target_spread),
            )
        )

    density_by_label = {str(panel.label): float(panel.target_density_score) for panel in panels}
    answer_label = max(sorted(density_by_label), key=lambda label: (density_by_label[label], label))
    if str(answer_label) != str(labels[int(answer_index)]):
        raise RuntimeError("scatter facet density construction failed to keep unique answer")
    ordered = sorted(density_by_label, key=lambda label: (-density_by_label[label], label))
    winner_gap = (
        (density_by_label[ordered[0]] - density_by_label[ordered[1]]) / max(1e-9, density_by_label[ordered[0]])
        if len(ordered) > 1
        else 1.0
    )
    query_trace = {
        "target_region": str(region),
        "target_region_phrase": str(_REGION_PHRASE_BY_REGION[str(region)]),
        "density_by_panel_label": {str(label): round(float(value), 5) for label, value in density_by_label.items()},
        "density_order_high_to_low": list(ordered),
        "density_winner_relative_gap": round(float(winner_gap), 5),
        "panel_count": int(panel_count),
        "layout_id": str(layout_id),
        "layout_rows": int(rows),
        "layout_cols": int(cols),
        "layout_probabilities": dict(layout_probabilities),
        "query_id_probabilities": dict(query_id_probabilities),
        "panel_label_resolution": {
            key: list(value) if isinstance(value, tuple) else dict(value) if isinstance(value, Mapping) else value
            for key, value in dict(labels_resolution.__dict__).items()
        },
        "panel_label_collision_check": dict(panel_label_collision_check),
    }
    answer_panel = next(panel for panel in panels if str(panel.label) == str(answer_label))
    return _Dataset(
        panels=tuple(panels),
        query=_Query(
            query_id=str(query_id),
            region=str(region),
            answer_label=str(answer_label),
            annotation_point_ids=tuple(str(point.point_id) for point in answer_panel.target_points),
            trace=dict(query_trace),
        ),
        rows=int(rows),
        cols=int(cols),
        layout_id=str(layout_id),
        label_resolution=labels_resolution,
    )


def _resolve_render_params(params: Mapping[str, Any]) -> _RenderParams:
    margin_left = _resolve_int(params, "facet_grid_left_px", 92)
    margin_right = _resolve_int(params, "facet_grid_right_px", 70)
    margin_top = _resolve_int(params, "facet_grid_top_px", 92)
    margin_bottom = _resolve_int(params, "facet_grid_bottom_px", 96)
    margin_left, margin_right, margin_top, margin_bottom, jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(margin_left),
        right_px=int(margin_right),
        top_px=int(margin_top),
        bottom_px=int(margin_bottom),
        params=params,
        defaults=_RENDER_DEFAULTS,
        namespace=TASK_ID,
        instance_seed=_render_style_seed(params),
    )
    return _RenderParams(
        canvas_width=_resolve_int(params, "facet_canvas_width", 1280),
        canvas_height=_resolve_int(params, "facet_canvas_height", 860),
        grid_left_px=int(margin_left),
        grid_right_px=int(margin_right),
        grid_top_px=int(margin_top),
        grid_bottom_px=int(margin_bottom),
        panel_gap_x_px=_resolve_int(params, "facet_panel_gap_x_px", 24),
        panel_gap_y_px=_resolve_int(params, "facet_panel_gap_y_px", 30),
        axis_line_width_px=_resolve_int(params, "facet_axis_line_width_px", 1),
        grid_line_width_px=_resolve_int(params, "facet_grid_line_width_px", 1),
        point_radius_px=_resolve_int(params, "facet_point_radius_px", 3),
        title_font_size_px=_resolve_int(params, "facet_title_font_size_px", 25),
        panel_label_font_size_px=_resolve_int(params, "facet_panel_label_font_size_px", 16),
        axis_label_font_size_px=_resolve_int(params, "facet_axis_label_font_size_px", 18),
        tick_font_size_px=_resolve_int(params, "facet_tick_font_size_px", 11),
        background_point_rgb=_resolve_rgb(params, "facet_background_point_rgb", (188, 194, 202)),
        foreground_stroke_rgb=_resolve_rgb(params, "facet_foreground_stroke_rgb", (255, 255, 255)),
        region_tint_rgb=_resolve_rgb(params, "facet_region_tint_rgb", (252, 231, 160)),
        axis_color_rgb=_resolve_rgb(params, "facet_axis_color_rgb", (82, 92, 108)),
        grid_color_rgb=_resolve_rgb(params, "facet_grid_color_rgb", (222, 227, 235)),
        text_color_rgb=_resolve_rgb(params, "facet_text_color_rgb", (25, 32, 44)),
        text_stroke_rgb=_resolve_rgb(params, "facet_text_stroke_rgb", (255, 255, 255)),
        panel_fill_rgb=_resolve_rgb(params, "facet_panel_fill_rgb", (250, 251, 253)),
        panel_border_rgb=_resolve_rgb(params, "facet_panel_border_rgb", (194, 202, 214)),
        layout_jitter_meta=dict(jitter_meta),
    )


def _value_to_px(panel_bbox: Sequence[float], *, x_value: float, y_value: float) -> Tuple[float, float]:
    x0, y0, x1, y1 = [float(value) for value in panel_bbox[:4]]
    x_px = x0 + (float(x_value) / 100.0) * (x1 - x0)
    y_px = y1 - (float(y_value) / 100.0) * (y1 - y0)
    return float(x_px), float(y_px)


def _region_bbox_px(panel_bbox: Sequence[float], region: str) -> List[float]:
    x0, y0, x1, y1 = _region_bounds(str(region))
    px0, py1 = _value_to_px(panel_bbox, x_value=x0, y_value=y0)
    px1, py0 = _value_to_px(panel_bbox, x_value=x1, y_value=y1)
    return _bbox((px0, py0, px1, py1))


def _draw_point(draw: ImageDraw.ImageDraw, center: Tuple[float, float], *, radius: int, fill: RGB, outline: RGB | None = None, alpha: int | None = None) -> List[float]:
    del alpha
    x, y = float(center[0]), float(center[1])
    r = float(radius)
    bbox = (x - r, y - r, x + r, y + r)
    draw.ellipse(bbox, fill=tuple(int(c) for c in fill), outline=outline)
    return _bbox(bbox)


def _all_panel_points(panel: _Panel) -> Tuple[_Point, ...]:
    return tuple(panel.background_points) + tuple(panel.target_points) + tuple(panel.distractor_points)


def _render_facet_grid(image: Image.Image, *, dataset: _Dataset, render_params: _RenderParams, instance_seed: int) -> _Rendered:
    del instance_seed
    draw = ImageDraw.Draw(image, "RGBA")
    title_font = load_font(render_params.title_font_size_px)
    panel_label_font = load_font(render_params.panel_label_font_size_px)
    axis_label_font = load_font(render_params.axis_label_font_size_px)
    tick_font = load_font(render_params.tick_font_size_px)

    grid_left = float(render_params.grid_left_px)
    grid_top = float(render_params.grid_top_px)
    grid_right = float(render_params.canvas_width - render_params.grid_right_px)
    grid_bottom = float(render_params.canvas_height - render_params.grid_bottom_px)
    usable_width = grid_right - grid_left
    usable_height = grid_bottom - grid_top
    panel_w = (usable_width - (float(dataset.cols - 1) * render_params.panel_gap_x_px)) / float(dataset.cols)
    panel_h = (usable_height - (float(dataset.rows - 1) * render_params.panel_gap_y_px)) / float(dataset.rows)

    title_text = "Faceted Scatter Density"
    title_record = draw_text_traced(
        draw,
        (float(render_params.canvas_width) / 2.0, 34.0),
        title_text,
        font=title_font,
        fill=render_params.text_color_rgb,
        stroke_fill=render_params.text_stroke_rgb,
        stroke_width=1,
        anchor="ma",
        role="readout",
        required=False,
    )
    x_label_record = draw_text_traced(
        draw,
        (float(render_params.canvas_width) / 2.0, float(render_params.canvas_height) - 34.0),
        "X score",
        font=axis_label_font,
        fill=render_params.text_color_rgb,
        stroke_fill=render_params.text_stroke_rgb,
        stroke_width=1,
        anchor="mm",
        role="readout",
        required=False,
    )
    y_label_record = draw_text_traced(
        draw,
        (30.0, float(render_params.canvas_height) / 2.0),
        "Y score",
        font=axis_label_font,
        fill=render_params.text_color_rgb,
        stroke_fill=render_params.text_stroke_rgb,
        stroke_width=1,
        anchor="mm",
        role="readout",
        required=False,
    )

    panel_bboxes: Dict[str, List[float]] = {}
    panel_label_bboxes: Dict[str, List[float]] = {}
    region_bboxes: Dict[str, List[float]] = {}
    density_region_bboxes: Dict[str, List[float]] = {}
    point_bboxes: Dict[str, List[float]] = {}
    point_centers: Dict[str, List[float]] = {}
    entities: list[Dict[str, Any]] = []

    for index, panel in enumerate(dataset.panels):
        row = int(index // dataset.cols)
        col = int(index % dataset.cols)
        px0 = grid_left + (float(col) * (panel_w + render_params.panel_gap_x_px))
        py0 = grid_top + (float(row) * (panel_h + render_params.panel_gap_y_px))
        px1 = px0 + panel_w
        py1 = py0 + panel_h
        panel_bbox = _bbox((px0, py0, px1, py1))
        panel_bboxes[str(panel.label)] = panel_bbox
        draw.rectangle(panel_bbox, fill=tuple(render_params.panel_fill_rgb) + (255,), outline=tuple(render_params.panel_border_rgb) + (255,), width=1)
        label_record = draw_text_traced(
            draw,
            ((px0 + px1) / 2.0, py0 - 7.0),
            str(panel.label),
            font=panel_label_font,
            fill=render_params.text_color_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=2,
            anchor="ms",
            role="readout",
            required=True,
        )
        panel_label_bboxes[str(panel.label)] = list(label_record["bbox_px"])

        region_bbox = _region_bbox_px(panel_bbox, dataset.query.region)
        region_bboxes[str(panel.label)] = list(region_bbox)
        draw.rectangle(region_bbox, fill=tuple(render_params.region_tint_rgb) + (54,), outline=tuple(render_params.region_tint_rgb) + (130,), width=1)

        for tick in (25, 50, 75):
            x_tick, _ = _value_to_px(panel_bbox, x_value=float(tick), y_value=0.0)
            _, y_tick = _value_to_px(panel_bbox, x_value=0.0, y_value=float(tick))
            draw.line((x_tick, py0, x_tick, py1), fill=tuple(render_params.grid_color_rgb) + (255,), width=render_params.grid_line_width_px)
            draw.line((px0, y_tick, px1, y_tick), fill=tuple(render_params.grid_color_rgb) + (255,), width=render_params.grid_line_width_px)
        draw.line((px0, py1, px1, py1), fill=tuple(render_params.axis_color_rgb) + (255,), width=render_params.axis_line_width_px)
        draw.line((px0, py0, px0, py1), fill=tuple(render_params.axis_color_rgb) + (255,), width=render_params.axis_line_width_px)
        if row == dataset.rows - 1:
            draw_text_traced(draw, (px0, py1 + 4.0), "0", font=tick_font, fill=render_params.text_color_rgb, anchor="la", role="readout", required=False)
            draw_text_traced(draw, (px1, py1 + 4.0), "100", font=tick_font, fill=render_params.text_color_rgb, anchor="ra", role="readout", required=False)
        if col == 0:
            draw_text_traced(draw, (px0 - 5.0, py1), "0", font=tick_font, fill=render_params.text_color_rgb, anchor="rm", role="readout", required=False)
            draw_text_traced(draw, (px0 - 5.0, py0), "100", font=tick_font, fill=render_params.text_color_rgb, anchor="rm", role="readout", required=False)

        for point in panel.background_points:
            center = _value_to_px(panel_bbox, x_value=point.x_value, y_value=point.y_value)
            point_box = _draw_point(
                draw,
                center,
                radius=max(1, int(render_params.point_radius_px) - 1),
                fill=render_params.background_point_rgb,
                outline=None,
            )
            point_bboxes[str(point.point_id)] = point_box
            point_centers[str(point.point_id)] = _bbox((center[0], center[1]))[:2]

        target_boxes: list[List[float]] = []
        for point in tuple(panel.distractor_points) + tuple(panel.target_points):
            center = _value_to_px(panel_bbox, x_value=point.x_value, y_value=point.y_value)
            fill_rgb = panel.color_rgb if str(point.layer) == "target" else tuple(max(0, int(c) - 26) for c in panel.color_rgb)
            point_box = _draw_point(
                draw,
                center,
                radius=int(render_params.point_radius_px),
                fill=fill_rgb,
                outline=render_params.foreground_stroke_rgb,
            )
            point_bboxes[str(point.point_id)] = point_box
            point_centers[str(point.point_id)] = _bbox((center[0], center[1]))[:2]
            if str(point.layer) == "target":
                target_boxes.append(point_box)
        density_bbox = _bbox_union(target_boxes)
        density_region_bboxes[str(panel.label)] = density_bbox

        entities.append(
            {
                "entity_id": f"panel:{panel.label}",
                "entity_type": "scatter_facet_panel",
                "label": str(panel.label),
                "bbox_px": list(panel_bbox),
                "target_region_bbox_px": list(region_bbox),
                "density_region_bbox_px": list(density_bbox),
                "target_density_score": round(float(panel.target_density_score), 5),
            }
        )

    return _Rendered(
        image=image,
        entities=tuple(entities),
        panel_bboxes=dict(panel_bboxes),
        panel_label_bboxes=dict(panel_label_bboxes),
        region_bboxes=dict(region_bboxes),
        density_region_bboxes=dict(density_region_bboxes),
        point_bboxes=dict(point_bboxes),
        point_centers=dict(point_centers),
        title_bbox_px=list(title_record["bbox_px"]),
        x_axis_label_bbox_px=list(x_label_record["bbox_px"]),
        y_axis_label_bbox_px=list(y_label_record["bbox_px"]),
        title_text=str(title_text),
    )


def _point_records(points: Sequence[_Point]) -> List[Dict[str, Any]]:
    return [
        {
            "point_id": str(point.point_id),
            "panel_label": str(point.panel_label),
            "x_value": round(float(point.x_value), 3),
            "y_value": round(float(point.y_value), 3),
            "layer": str(point.layer),
        }
        for point in points
    ]


def _panel_records(panels: Sequence[_Panel]) -> List[Dict[str, Any]]:
    return [
        {
            "label": str(panel.label),
            "color_rgb": [int(channel) for channel in panel.color_rgb],
            "target_density_score": round(float(panel.target_density_score), 5),
            "target_point_count": int(panel.target_point_count),
            "target_spread": round(float(panel.target_spread), 3),
            "background_points": _point_records(panel.background_points),
            "target_points": _point_records(panel.target_points),
            "distractor_points": _point_records(panel.distractor_points),
        }
        for panel in panels
    ]


