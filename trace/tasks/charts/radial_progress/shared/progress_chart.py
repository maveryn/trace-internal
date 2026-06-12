"""Radial progress and gauge chart tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from .....core.seed import spawn_rng
from .....core.scene_config import get_scene_defaults
from ....shared.config_defaults import (
    group_default,
    resolve_required_int_bounds,
    split_scene_generation_rendering_prompt_defaults,
)
from ....shared.deterministic_sampling import resolve_selection_index
from ....shared.drawing import draw_centered_text, draw_rounded_rect
from ....shared.font_assets import sample_font_family
from ....shared.render_variation import resolve_render_rgb
from ....shared.text_rendering import load_font
from ....shared.text_legibility import draw_text_traced
from ...shared.label_assets import resolve_chart_entity_labels
from ...shared.labeled_chart_common import resolve_chart_axis_variant
from ...shared.visual_defaults import load_chart_scene_background_defaults, load_chart_scene_noise_defaults


TASK_ID = "charts_radial_progress_base"
SCENE_ID = "radial_progress"

CONDITION_COUNT_QUERY_IDS: Tuple[str, ...] = (
    "at_least_threshold_count",
    "below_threshold_count",
    "within_range_count",
    "remaining_at_least_threshold_count",
)
REMAINING_EXTREMUM_QUERY_IDS: Tuple[str, ...] = (
    "highest_remaining_label",
    "lowest_remaining_label",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "full_progress_rings",
    "semicircle_gauges",
    "segmented_radial_bars",
)

_TASK_GROUP_DEFAULTS = get_scene_defaults("charts", "radial_progress")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_scene_background_defaults(scene_id="radial_progress")
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id="radial_progress", apply_prob=0.2)

_QUERY_LOADS: Dict[str, float] = {
    "at_least_threshold_count": 0.52,
    "below_threshold_count": 0.52,
    "within_range_count": 0.68,
    "remaining_at_least_threshold_count": 0.64,
    "highest_remaining_label": 0.50,
    "lowest_remaining_label": 0.50,
}
_SCENE_LOADS: Dict[str, float] = {
    "full_progress_rings": 0.52,
    "semicircle_gauges": 0.58,
    "segmented_radial_bars": 0.66,
}

RGB = Tuple[int, int, int]
BBox = List[float]


@dataclass(frozen=True)
class _ProgressItem:
    item_id: str
    label: str
    value: int
    color_rgb: RGB


@dataclass(frozen=True)
class _Query:
    query_id: str
    answer: int | str
    answer_type: str
    annotation_item_ids: Tuple[str, ...]
    params: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    items: Tuple[_ProgressItem, ...]
    query_id: str
    query_probabilities: Dict[str, float]
    scene_variant: str
    scene_variant_probabilities: Dict[str, float]
    query: _Query
    title: str


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    outer_margin_px: int
    title_band_height_px: int
    card_gap_px: int
    card_corner_radius_px: int
    card_outline_width_px: int
    title_font_size_px: int
    label_font_size_px: int
    tick_font_size_px: int
    ring_width_px: int
    gauge_width_px: int
    segment_width_px: int
    tick_length_px: int
    text_rgb: RGB
    muted_text_rgb: RGB
    text_stroke_rgb: RGB
    card_fill_rgb: RGB
    card_alt_fill_rgb: RGB
    card_outline_rgb: RGB
    track_rgb: RGB
    tick_rgb: RGB
    needle_rgb: RGB


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: BBox
    item_bboxes_px: Dict[str, BBox]
    progress_bboxes_px: Dict[str, BBox]
    render_meta: Dict[str, Any]


def _bbox(values: Sequence[float]) -> BBox:
    return [round(float(value), 3) for value in values]


def _support_probability_map(values: Sequence[int | str]) -> Dict[str, float]:
    support = [str(value) for value in values]
    if not support:
        return {}
    weight = 1.0 / float(len(support))
    return {str(value): float(weight) for value in support}


def _resolve_scene_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _sample_int_range(
    params: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    instance_seed: int,
    namespace: str,
) -> Tuple[int, Dict[str, float]]:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
        context=f"generation defaults for {TASK_ID}",
    )
    support = list(range(int(low), int(high) + 1))
    index = abs(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace)))
    return int(support[int(index % len(support))]), _support_probability_map(support)


def _choose_labels(*, count: int, instance_seed: int) -> List[str]:
    rng = spawn_rng(int(instance_seed), "charts.radial_progress.labels")
    labels = resolve_chart_entity_labels(
        rng,
        count=int(count),
        min_chars=2,
        max_chars=7,
        allow_spaces=False,
    ).labels
    return [str(label) for label in labels]


def _sample_chart_font_family(instance_seed: int, params: Mapping[str, Any]) -> str:
    return str(
        sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.chart_font",
            params=params,
            exclude_tags=("display",),
            explicit_key="chart_font_family",
            weights_key="chart_font_family_weights",
        )
    )


def _palette(params: Mapping[str, Any], *, count: int, instance_seed: int) -> List[RGB]:
    raw_palette = params.get("progress_palette_rgb", group_default(_RENDER_DEFAULTS, "progress_palette_rgb", []))
    palette: List[RGB] = []
    if isinstance(raw_palette, Sequence):
        for raw in raw_palette:
            if isinstance(raw, Sequence) and len(raw) == 3:
                palette.append(tuple(int(channel) for channel in raw))
    if not palette:
        palette = [
            (37, 99, 235),
            (220, 84, 45),
            (16, 132, 96),
            (139, 92, 246),
            (202, 138, 4),
            (14, 116, 144),
        ]
    offset = abs(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace="charts.radial_progress.palette")) % len(palette)
    return [palette[(index + int(offset)) % len(palette)] for index in range(int(count))]


def _value_support(params: Mapping[str, Any]) -> List[int]:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="value_min",
        max_key="value_max",
        fallback_min=10,
        fallback_max=95,
        context=f"generation defaults for {TASK_ID}",
    )
    step = max(1, int(params.get("value_step", group_default(_GEN_DEFAULTS, "value_step", 5))))
    return [int(value) for value in range(int(low), int(high) + 1, int(step))]


def _sample_from_support(rng, support: Sequence[int], *, count: int) -> List[int]:
    if not support:
        raise ValueError("empty support for radial progress values")
    return [int(support[int(rng.randrange(0, len(support)))]) for _ in range(int(count))]


def _construct_condition_values(
    *,
    query_id: str,
    item_count: int,
    answer_count: int,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[List[int], Tuple[str, ...], Dict[str, Any]]:
    rng = spawn_rng(int(instance_seed), f"charts.radial_progress.values.{query_id}")
    support = _value_support(params)
    target_indices = tuple(sorted(rng.sample(range(int(item_count)), k=int(answer_count))))

    threshold_values = [int(v) for v in params.get("threshold_values", group_default(_GEN_DEFAULTS, "threshold_values", [30, 40, 50, 60, 70]))]
    if not threshold_values:
        threshold_values = [30, 40, 50, 60, 70]
    threshold_index = abs(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"charts.radial_progress.threshold.{query_id}")) % len(threshold_values)
    threshold = int(threshold_values[int(threshold_index)])

    values: List[int] = []
    query_params: Dict[str, Any] = {
        "answer_count": int(answer_count),
        "answer_count_probabilities": _support_probability_map(range(1, int(params.get("answer_count_max", group_default(_GEN_DEFAULTS, "answer_count_max", 5))) + 1)),
    }

    if query_id == "at_least_threshold_count":
        target_support = [v for v in support if int(v) >= int(threshold)]
        other_support = [v for v in support if int(v) < int(threshold)]
        query_params.update({"threshold_value": int(threshold), "threshold_phrase": f"at least {threshold}%"})
    elif query_id == "below_threshold_count":
        target_support = [v for v in support if int(v) < int(threshold)]
        other_support = [v for v in support if int(v) >= int(threshold)]
        query_params.update({"threshold_value": int(threshold), "threshold_phrase": f"below {threshold}%"})
    elif query_id == "remaining_at_least_threshold_count":
        remaining_threshold = int(threshold)
        max_value_for_remaining = int(100 - remaining_threshold)
        target_support = [v for v in support if int(100 - v) >= int(remaining_threshold)]
        other_support = [v for v in support if int(100 - v) < int(remaining_threshold)]
        query_params.update(
            {
                "threshold_value": int(remaining_threshold),
                "threshold_phrase": f"at least {remaining_threshold}% remaining",
                "max_value_for_remaining": int(max_value_for_remaining),
            }
        )
    elif query_id == "within_range_count":
        range_pairs = params.get(
            "range_pairs",
            group_default(_GEN_DEFAULTS, "range_pairs", [[25, 55], [30, 60], [35, 70], [40, 75]]),
        )
        pairs: List[Tuple[int, int]] = []
        if isinstance(range_pairs, Sequence):
            for raw in range_pairs:
                if isinstance(raw, Sequence) and len(raw) == 2:
                    pairs.append((int(raw[0]), int(raw[1])))
        if not pairs:
            pairs = [(25, 55), (30, 60), (35, 70), (40, 75)]
        pair_index = abs(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace="charts.radial_progress.range_pair")) % len(pairs)
        lower, upper = pairs[int(pair_index)]
        if int(lower) > int(upper):
            lower, upper = upper, lower
        target_support = [v for v in support if int(lower) <= int(v) <= int(upper)]
        other_support = [v for v in support if int(v) < int(lower) or int(v) > int(upper)]
        query_params.update({"range_lower": int(lower), "range_upper": int(upper), "range_phrase": f"from {lower}% through {upper}%"})
    else:
        raise ValueError(f"unsupported radial progress query: {query_id}")

    if not target_support or not other_support:
        raise ValueError(f"query support is empty for {query_id}")

    target_values = _sample_from_support(rng, target_support, count=int(answer_count))
    other_values = _sample_from_support(rng, other_support, count=int(item_count) - int(answer_count))
    other_iter = iter(other_values)
    target_iter = iter(target_values)
    target_set = set(int(index) for index in target_indices)
    for index in range(int(item_count)):
        values.append(int(next(target_iter) if int(index) in target_set else next(other_iter)))
    return values, tuple(str(f"i{index}") for index in target_indices), dict(query_params)


def _construct_extremum_values(
    *,
    query_id: str,
    item_count: int,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[List[int], Tuple[str, ...], Dict[str, Any]]:
    rng = spawn_rng(int(instance_seed), f"charts.radial_progress.extremum_values.{query_id}")
    support = list(_value_support(params))
    if len(support) < int(item_count):
        raise ValueError("radial progress extremum queries require enough distinct values to avoid ties")

    values = [int(value) for value in rng.sample(support, k=int(item_count))]
    if str(query_id) == "highest_remaining_label":
        target_index = min(range(int(item_count)), key=lambda index: int(values[index]))
        extremum_phrase = "the most remaining progress"
    elif str(query_id) == "lowest_remaining_label":
        target_index = max(range(int(item_count)), key=lambda index: int(values[index]))
        extremum_phrase = "the least remaining progress"
    else:
        raise ValueError(f"unsupported radial progress extremum query: {query_id}")

    return (
        values,
        (f"i{int(target_index)}",),
        {
            "extremum_phrase": str(extremum_phrase),
            "target_value": int(values[int(target_index)]),
            "target_remaining": int(100 - int(values[int(target_index)])),
        },
    )


def _construct_dataset(
    *,
    query_id: str,
    query_probabilities: Dict[str, float],
    scene_variant: str,
    scene_variant_probabilities: Dict[str, float],
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Dataset:
    item_count, item_count_probabilities = _sample_int_range(
        params,
        min_key="item_count_min",
        max_key="item_count_max",
        fallback_min=6,
        fallback_max=10,
        instance_seed=int(instance_seed),
        namespace="charts.radial_progress.item_count",
    )
    labels = _choose_labels(count=int(item_count), instance_seed=int(instance_seed))
    colors = _palette(params, count=int(item_count), instance_seed=int(instance_seed))

    if str(query_id) in CONDITION_COUNT_QUERY_IDS:
        max_answer = min(
            int(item_count) - 1,
            int(params.get("answer_count_max", group_default(_GEN_DEFAULTS, "answer_count_max", 5))),
        )
        min_answer = int(params.get("answer_count_min", group_default(_GEN_DEFAULTS, "answer_count_min", 1)))
        answer_support = list(range(max(1, min_answer), max(1, int(max_answer)) + 1))
        answer_index = abs(
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"charts.radial_progress.answer_count.{query_id}",
            )
        ) % len(answer_support)
        answer_count = int(answer_support[int(answer_index)])
        values, annotation_item_ids, query_params = _construct_condition_values(
            query_id=str(query_id),
            item_count=int(item_count),
            answer_count=int(answer_count),
            params=params,
            instance_seed=int(instance_seed),
        )
        answer: int | str = int(answer_count)
        answer_type = "integer"
        query_params.update({"answer_count_probabilities": _support_probability_map(answer_support)})
    elif str(query_id) in REMAINING_EXTREMUM_QUERY_IDS:
        values, annotation_item_ids, query_params = _construct_extremum_values(
            query_id=str(query_id),
            item_count=int(item_count),
            params=params,
            instance_seed=int(instance_seed),
        )
        target_index = int(str(annotation_item_ids[0]).removeprefix("i"))
        answer = str(labels[int(target_index)])
        answer_type = "string"
        query_params.update(
            {
                "label_support": [str(label) for label in labels],
                "target_label": str(answer),
            }
        )
    else:
        raise ValueError(f"unsupported radial progress query: {query_id}")

    query_params.update(
        {
            "item_count_probabilities": dict(item_count_probabilities),
        }
    )
    items = tuple(
        _ProgressItem(
            item_id=f"i{index}",
            label=str(labels[index]),
            value=int(values[index]),
            color_rgb=tuple(int(v) for v in colors[index]),
        )
        for index in range(int(item_count))
    )

    title_options = [str(value) for value in params.get("title_options", group_default(_RENDER_DEFAULTS, "title_options", ["Progress Summary"]))] or ["Progress Summary"]
    title_index = abs(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace="charts.radial_progress.title")) % len(title_options)
    query = _Query(
        query_id=str(query_id),
        answer=answer,
        answer_type=str(answer_type),
        annotation_item_ids=tuple(str(value) for value in annotation_item_ids),
        params=dict(query_params),
    )
    return _Dataset(
        items=items,
        query_id=str(query_id),
        query_probabilities=dict(query_probabilities),
        scene_variant=str(scene_variant),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        query=query,
        title=str(title_options[int(title_index)]),
    )


def _render_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_RENDER_DEFAULTS, str(key), int(fallback))))


def _resolve_render_params(params: Mapping[str, Any], *, instance_seed: int) -> _RenderParams:
    return _RenderParams(
        canvas_width=_render_int(params, "canvas_width", 1320),
        canvas_height=_render_int(params, "canvas_height", 900),
        outer_margin_px=_render_int(params, "outer_margin_px", 48),
        title_band_height_px=_render_int(params, "title_band_height_px", 68),
        card_gap_px=_render_int(params, "card_gap_px", 18),
        card_corner_radius_px=_render_int(params, "card_corner_radius_px", 12),
        card_outline_width_px=_render_int(params, "card_outline_width_px", 2),
        title_font_size_px=_render_int(params, "title_font_size_px", 30),
        label_font_size_px=_render_int(params, "label_font_size_px", 20),
        tick_font_size_px=_render_int(params, "tick_font_size_px", 13),
        ring_width_px=_render_int(params, "ring_width_px", 16),
        gauge_width_px=_render_int(params, "gauge_width_px", 16),
        segment_width_px=_render_int(params, "segment_width_px", 14),
        tick_length_px=_render_int(params, "tick_length_px", 8),
        text_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "text_rgb", [36, 42, 52], instance_seed=int(instance_seed), namespace="charts.radial_progress"),
        muted_text_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "muted_text_rgb", [88, 96, 112], instance_seed=int(instance_seed), namespace="charts.radial_progress"),
        text_stroke_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "text_stroke_rgb", [255, 255, 255], instance_seed=int(instance_seed), namespace="charts.radial_progress"),
        card_fill_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "card_fill_rgb", [255, 255, 255], instance_seed=int(instance_seed), namespace="charts.radial_progress"),
        card_alt_fill_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "card_alt_fill_rgb", [248, 250, 252], instance_seed=int(instance_seed), namespace="charts.radial_progress"),
        card_outline_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "card_outline_rgb", [194, 202, 214], instance_seed=int(instance_seed), namespace="charts.radial_progress"),
        track_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "track_rgb", [225, 230, 238], instance_seed=int(instance_seed), namespace="charts.radial_progress"),
        tick_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "tick_rgb", [96, 107, 122], instance_seed=int(instance_seed), namespace="charts.radial_progress"),
        needle_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "needle_rgb", [44, 52, 64], instance_seed=int(instance_seed), namespace="charts.radial_progress"),
    )


def _point(cx: float, cy: float, radius: float, degrees: float) -> Tuple[float, float]:
    radians = math.radians(float(degrees))
    return float(cx + (radius * math.cos(radians))), float(cy + (radius * math.sin(radians)))


def _draw_text(
    draw: ImageDraw.ImageDraw,
    *,
    xy: Tuple[float, float],
    text: str,
    font,
    fill: RGB,
    stroke_fill: RGB,
    anchor: str = "mm",
    stroke_width: int = 1,
) -> BBox:
    draw_text_traced(
        draw,
        (float(xy[0]), float(xy[1])),
        str(text),
        font=font,
        fill=tuple(fill),
        stroke_width=max(0, int(stroke_width)),
        stroke_fill=tuple(stroke_fill),
        anchor=str(anchor),
     role="readout", required=False,)
    bbox = draw.textbbox(
        (float(xy[0]), float(xy[1])),
        str(text),
        font=font,
        stroke_width=max(0, int(stroke_width)),
        anchor=str(anchor),
    )
    return _bbox(bbox)


def _draw_ticks(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    radius: float,
    values: Sequence[int],
    start_degrees: float,
    span_degrees: float,
    p: _RenderParams,
    label_values: Sequence[int],
) -> None:
    tick_font = load_font(p.tick_font_size_px, bold=True)
    label_set = {int(value) for value in label_values}
    cx, cy = float(center[0]), float(center[1])
    for value in values:
        angle = float(start_degrees + (span_degrees * (int(value) / 100.0)))
        outer = _point(cx, cy, float(radius) + 3.0, angle)
        inner = _point(cx, cy, max(1.0, float(radius) - float(p.tick_length_px)), angle)
        draw.line([inner, outer], fill=tuple(p.tick_rgb), width=2)
        if int(value) in label_set:
            label_point = _point(cx, cy, float(radius) + 19.0, angle)
            text = "0/100" if int(value) == 0 and 100 in label_set else str(value)
            if int(value) == 100 and 0 in label_set:
                continue
            _draw_text(
                draw,
                xy=label_point,
                text=text,
                font=tick_font,
                fill=p.muted_text_rgb,
                stroke_fill=p.text_stroke_rgb,
                anchor="mm",
                stroke_width=1,
            )


def _draw_full_ring(
    draw: ImageDraw.ImageDraw,
    *,
    item: _ProgressItem,
    center: Tuple[float, float],
    radius: float,
    p: _RenderParams,
) -> BBox:
    cx, cy = float(center[0]), float(center[1])
    bbox = (cx - radius, cy - radius, cx + radius, cy + radius)
    width = max(6, int(p.ring_width_px))
    draw.arc(bbox, start=-90, end=270, fill=tuple(p.track_rgb), width=width)
    end_angle = float(-90.0 + (360.0 * (int(item.value) / 100.0)))
    draw.arc(bbox, start=-90, end=end_angle, fill=tuple(item.color_rgb), width=width)
    _draw_ticks(
        draw,
        center=(cx, cy),
        radius=radius,
        values=(0, 25, 50, 75, 100),
        start_degrees=-90,
        span_degrees=360,
        p=p,
        label_values=(0, 50),
    )
    return _bbox([cx - radius - 24, cy - radius - 24, cx + radius + 24, cy + radius + 24])


def _draw_semicircle_gauge(
    draw: ImageDraw.ImageDraw,
    *,
    item: _ProgressItem,
    center: Tuple[float, float],
    radius: float,
    p: _RenderParams,
) -> BBox:
    cx, cy = float(center[0]), float(center[1])
    bbox = (cx - radius, cy - radius, cx + radius, cy + radius)
    width = max(6, int(p.gauge_width_px))
    draw.arc(bbox, start=180, end=360, fill=tuple(p.track_rgb), width=width)
    end_angle = float(180.0 + (180.0 * (int(item.value) / 100.0)))
    draw.arc(bbox, start=180, end=end_angle, fill=tuple(item.color_rgb), width=width)
    _draw_ticks(
        draw,
        center=(cx, cy),
        radius=radius,
        values=(0, 25, 50, 75, 100),
        start_degrees=180,
        span_degrees=180,
        p=p,
        label_values=(0, 50, 100),
    )
    needle_end = _point(cx, cy, max(1.0, radius - 22.0), end_angle)
    draw.line([(cx, cy), needle_end], fill=tuple(p.needle_rgb), width=3)
    r = 5.0
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=tuple(p.needle_rgb), outline=tuple(p.text_stroke_rgb), width=1)
    return _bbox([cx - radius - 24, cy - radius - 28, cx + radius + 24, cy + 24])


def _paste_annular_segment(
    image: Image.Image,
    *,
    center: Tuple[float, float],
    radius: float,
    width: float,
    start_degrees: float,
    end_degrees: float,
    fill: RGB,
) -> None:
    cx, cy = float(center[0]), float(center[1])
    outer_radius = float(radius) + (float(width) * 0.5)
    inner_radius = max(1.0, float(radius) - (float(width) * 0.5))
    pad = int(math.ceil(float(outer_radius) + 5.0))
    size = int((2 * pad) + 1)
    scale = 4
    scaled_size = int(size * scale)
    local_center = float(pad * scale)

    mask = Image.new("L", (scaled_size, scaled_size), 0)
    mask_draw = ImageDraw.Draw(mask)
    outer_box = (
        local_center - (outer_radius * scale),
        local_center - (outer_radius * scale),
        local_center + (outer_radius * scale),
        local_center + (outer_radius * scale),
    )
    inner_box = (
        local_center - (inner_radius * scale),
        local_center - (inner_radius * scale),
        local_center + (inner_radius * scale),
        local_center + (inner_radius * scale),
    )
    mask_draw.pieslice(outer_box, start=float(start_degrees), end=float(end_degrees), fill=255)
    mask_draw.pieslice(inner_box, start=float(start_degrees) - 1.0, end=float(end_degrees) + 1.0, fill=0)
    try:
        resample = Image.Resampling.LANCZOS
    except AttributeError:  # pragma: no cover - Pillow compatibility
        resample = Image.LANCZOS
    mask = mask.resize((size, size), resample)
    color_patch = Image.new("RGB", (size, size), tuple(int(v) for v in fill))
    image.paste(color_patch, (int(round(cx - pad)), int(round(cy - pad))), mask)


def _draw_segmented_radial_bar(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    *,
    item: _ProgressItem,
    center: Tuple[float, float],
    radius: float,
    p: _RenderParams,
) -> BBox:
    cx, cy = float(center[0]), float(center[1])
    width = max(10, int(p.segment_width_px))
    segment_count = 20
    filled_count = int(round(int(item.value) / 5.0))
    gap_degrees = 2.2
    for index in range(segment_count):
        start = float(-90.0 + (index * 360.0 / segment_count) + gap_degrees * 0.5)
        end = float(-90.0 + ((index + 1) * 360.0 / segment_count) - gap_degrees * 0.5)
        fill = item.color_rgb if int(index) < int(filled_count) else p.track_rgb
        _paste_annular_segment(
            image,
            center=(cx, cy),
            radius=float(radius),
            width=float(width),
            start_degrees=float(start),
            end_degrees=float(end),
            fill=tuple(int(v) for v in fill),
        )
    outline_width = 1
    outer_radius = float(radius) + (float(width) * 0.5)
    inner_radius = max(1.0, float(radius) - (float(width) * 0.5))
    for outline_radius in (inner_radius, outer_radius):
        outline_bbox = (
            cx - outline_radius,
            cy - outline_radius,
            cx + outline_radius,
            cy + outline_radius,
        )
        draw.ellipse(outline_bbox, outline=tuple(p.card_outline_rgb), width=outline_width)
    _draw_ticks(
        draw,
        center=(cx, cy),
        radius=radius,
        values=(0, 25, 50, 75, 100),
        start_degrees=-90,
        span_degrees=360,
        p=p,
        label_values=(0, 50, 100),
    )
    return _bbox([cx - radius - 24, cy - radius - 24, cx + radius + 24, cy + radius + 24])


def _entity_record(item: _ProgressItem, *, item_bbox: Sequence[float], progress_bbox: Sequence[float]) -> Dict[str, Any]:
    return {
        "entity_id": str(item.item_id),
        "entity_type": "radial_progress_item",
        "label": str(item.label),
        "value": int(item.value),
        "remaining": int(100 - int(item.value)),
        "bbox_px": list(item_bbox),
        "progress_bbox_px": list(progress_bbox),
    }


def _render_chart(
    *,
    background: Image.Image,
    dataset: _Dataset,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Rendered:
    p = _resolve_render_params(params, instance_seed=int(instance_seed))
    image = background.convert("RGB")
    if image.size != (int(p.canvas_width), int(p.canvas_height)):
        image = image.resize((int(p.canvas_width), int(p.canvas_height)))
    draw = ImageDraw.Draw(image)

    title_font = load_font(p.title_font_size_px, bold=True)
    label_font = load_font(p.label_font_size_px, bold=True)
    margin = float(p.outer_margin_px)
    draw_centered_text(
        draw,
        text=str(dataset.title),
        center=(p.canvas_width / 2.0, margin + p.title_band_height_px * 0.38),
        font=title_font,
        fill=p.text_rgb,
        stroke_fill=p.text_stroke_rgb,
        stroke_width=1,
    )
    plot_left = margin
    plot_top = margin + float(p.title_band_height_px)
    plot_right = float(p.canvas_width) - margin
    plot_bottom = float(p.canvas_height) - margin
    plot_bbox = _bbox([plot_left, plot_top, plot_right, plot_bottom])

    item_count = len(dataset.items)
    columns = 4 if item_count <= 8 else 5
    rows = int(math.ceil(float(item_count) / float(columns)))
    gap = float(p.card_gap_px)
    card_w = float((plot_right - plot_left - ((columns - 1) * gap)) / float(columns))
    card_h = float((plot_bottom - plot_top - ((rows - 1) * gap)) / float(rows))
    item_bboxes: Dict[str, BBox] = {}
    progress_bboxes: Dict[str, BBox] = {}
    entities: List[Dict[str, Any]] = []

    for index, item in enumerate(dataset.items):
        row = int(index // columns)
        col = int(index % columns)
        x0 = float(plot_left + col * (card_w + gap))
        y0 = float(plot_top + row * (card_h + gap))
        x1 = float(x0 + card_w)
        y1 = float(y0 + card_h)
        card_fill = p.card_fill_rgb if (index + row) % 2 == 0 else p.card_alt_fill_rgb
        draw_rounded_rect(
            draw,
            (x0, y0, x1, y1),
            radius=int(p.card_corner_radius_px),
            fill=card_fill,
            outline=p.card_outline_rgb,
            width=int(p.card_outline_width_px),
        )
        _draw_text(
            draw,
            xy=((x0 + x1) / 2.0, y0 + 24.0),
            text=item.label,
            font=label_font,
            fill=p.text_rgb,
            stroke_fill=p.text_stroke_rgb,
            anchor="mm",
            stroke_width=1,
        )
        center_x = float((x0 + x1) / 2.0)
        if dataset.scene_variant == "semicircle_gauges":
            center_y = float(y0 + card_h * 0.72)
            radius = max(38.0, min(card_w * 0.36, card_h * 0.44))
            progress_bbox = _draw_semicircle_gauge(draw, item=item, center=(center_x, center_y), radius=radius, p=p)
        else:
            center_y = float(y0 + card_h * 0.55)
            radius = max(34.0, min(card_w * 0.32, card_h * 0.31))
            if dataset.scene_variant == "full_progress_rings":
                progress_bbox = _draw_full_ring(draw, item=item, center=(center_x, center_y), radius=radius, p=p)
            elif dataset.scene_variant == "segmented_radial_bars":
                progress_bbox = _draw_segmented_radial_bar(image, draw, item=item, center=(center_x, center_y), radius=radius, p=p)
            else:
                raise ValueError(f"unsupported radial progress scene variant: {dataset.scene_variant}")
        item_bbox = _bbox([x0, y0, x1, y1])
        item_bboxes[item.item_id] = item_bbox
        progress_bboxes[item.item_id] = progress_bbox
        entities.append(_entity_record(item, item_bbox=item_bbox, progress_bbox=progress_bbox))

    render_meta = {
        "scene_variant": str(dataset.scene_variant),
        "value_scale_min": 0,
        "value_scale_max": 100,
        "style": {
            "card_fill_rgb": list(p.card_fill_rgb),
            "card_alt_fill_rgb": list(p.card_alt_fill_rgb),
            "card_outline_rgb": list(p.card_outline_rgb),
            "track_rgb": list(p.track_rgb),
            "tick_rgb": list(p.tick_rgb),
        },
    }
    return _Rendered(
        image=image,
        entities=tuple(entities),
        plot_bbox_px=list(plot_bbox),
        item_bboxes_px=dict(item_bboxes),
        progress_bboxes_px=dict(progress_bboxes),
        render_meta=render_meta,
    )


def _query_slots(query_id: str, qparams: Mapping[str, Any]) -> Dict[str, Any]:
    if str(query_id) in REMAINING_EXTREMUM_QUERY_IDS:
        return {
            "extremum_phrase": str(qparams["extremum_phrase"]),
            "range_phrase": "",
            "threshold_phrase": "",
        }
    if str(query_id) == "within_range_count":
        return {"range_phrase": str(qparams["range_phrase"]), "threshold_phrase": "", "extremum_phrase": ""}
    return {"threshold_phrase": str(qparams["threshold_phrase"]), "range_phrase": "", "extremum_phrase": ""}


