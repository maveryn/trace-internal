"""Combo chart panel tasks for mixed bar/area/line reasoning."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.sampling import normalize_positive_weights, weighted_choice
from ....core.seed import hash64, spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import resolve_render_int, resolve_render_rgb
from ...shared.text_rendering import draw_text_centered, load_font
from ..shared.complexity import (
    build_chart_complexity,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


SCENE_ID = "combo_mark"
TASK_ID = "charts_combo_panel_query_base"

_SCENE_VARIANTS: Tuple[str, ...] = (
    "bar_line_shared_axis",
    "bar_line_dual_axis",
    "stacked_bar_line",
    "grouped_bar_line",
    "area_line_overlay",
)
_SCENE_VARIANT_LOADS: Dict[str, float] = {
    "bar_line_shared_axis": 0.10,
    "bar_line_dual_axis": 0.30,
    "stacked_bar_line": 0.54,
    "grouped_bar_line": 0.48,
    "area_line_overlay": 0.36,
}
_QUERY_REASONING_LOAD: Dict[str, float] = {
    "primary_minus_line_at_label": 0.20,
    "line_minus_primary_at_label": 0.20,
    "absolute_gap_at_label": 0.18,
    "larger_minus_smaller_at_label": 0.22,
    "max_line_where_primary_above_threshold": 0.54,
    "min_line_where_primary_above_threshold": 0.54,
    "max_primary_where_line_below_threshold": 0.56,
    "min_primary_where_line_below_threshold": 0.56,
    "primary_above_and_line_above": 0.42,
    "primary_above_and_line_below": 0.46,
    "primary_below_and_line_above": 0.46,
    "primary_between_and_line_above": 0.58,
    "line_change_minus_primary_change": 0.70,
    "primary_change_minus_line_change": 0.70,
    "absolute_change_gap": 0.66,
    "larger_change_minus_smaller_change": 0.74,
    "largest_absolute_gap_label": 0.50,
    "smallest_nonzero_absolute_gap_label": 0.54,
    "largest_primary_over_line_gap_label": 0.58,
    "largest_line_over_primary_gap_label": 0.58,
}

_LABEL_POOL: Tuple[str, ...] = (
    "Aster",
    "Beryl",
    "Cedar",
    "Dune",
    "Elm",
    "Flint",
    "Grove",
    "Harbor",
    "Iris",
    "Juniper",
    "Keel",
    "Lumen",
    "Mica",
    "Nori",
    "Onyx",
    "Pine",
    "Quartz",
    "Reed",
)
_METRIC_PAIRS: Tuple[Tuple[str, str], ...] = (
    ("Revenue", "Target"),
    ("Orders", "Forecast"),
    ("Output", "Plan"),
    ("Visits", "Goal"),
    ("Demand", "Capacity"),
    ("Actual", "Benchmark"),
)

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "combo")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="combo")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="combo", apply_prob=0.0)


def _public_task_param_overrides(task_id: str) -> Dict[str, Any]:
    """Return task-id-specific generation/rendering params for public wrappers."""

    overrides: Dict[str, Any] = {}
    if not isinstance(_TASK_GROUP_DEFAULTS, Mapping):
        return overrides
    for section in ("generation", "rendering"):
        section_cfg = _TASK_GROUP_DEFAULTS.get(section)
        if not isinstance(section_cfg, Mapping):
            continue
        task_overrides = section_cfg.get("task_overrides")
        if not isinstance(task_overrides, Mapping):
            continue
        task_values = task_overrides.get(str(task_id))
        if isinstance(task_values, Mapping):
            overrides.update(dict(task_values))
    return overrides


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    plot_left: int
    plot_right: int
    plot_top: int
    plot_bottom: int
    axis_width: int
    grid_width: int
    line_width: int
    point_radius: int
    tick_font_size: int
    label_font_size: int
    value_font_size: int
    legend_font_size: int
    primary_rgb: Tuple[int, int, int]
    primary_alt_rgb: Tuple[int, int, int]
    line_rgb: Tuple[int, int, int]
    area_rgb: Tuple[int, int, int]
    axis_rgb: Tuple[int, int, int]
    grid_rgb: Tuple[int, int, int]
    text_rgb: Tuple[int, int, int]
    panel_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class _ComboScene:
    image: Image.Image
    labels: Tuple[str, ...]
    primary_values: Tuple[int, ...]
    line_values: Tuple[int, ...]
    primary_points: Tuple[Tuple[float, float], ...]
    line_points: Tuple[Tuple[float, float], ...]
    entities: Tuple[Dict[str, Any], ...]
    scene_variant: str
    primary_name: str
    line_name: str
    primary_axis_max: int
    line_axis_max: int
    plot_bbox: Tuple[int, int, int, int]


def _as_int_bounds(params: Mapping[str, Any], low_key: str, high_key: str, fallback: Tuple[int, int]) -> Tuple[int, int]:
    low = int(params.get(low_key, group_default(_GEN_DEFAULTS, low_key, int(fallback[0]))))
    high = int(params.get(high_key, group_default(_GEN_DEFAULTS, high_key, int(fallback[1]))))
    if low > high:
        raise ValueError(f"{low_key} must be <= {high_key}")
    return low, high


def _axis_choice(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    supported: Sequence[str],
    explicit_keys: Sequence[str],
    weights_key: str,
    balance_key: str,
    namespace: str,
    sampling_divisor: int = 1,
) -> Tuple[str, Dict[str, float]]:
    for key in explicit_keys:
        value = params.get(str(key))
        if value is not None and str(value).strip():
            text = str(value)
            if text not in set(supported):
                raise ValueError(f"unsupported {key}: {text}")
            return text, {str(item): 1.0 if str(item) == text else 0.0 for item in supported}
    raw_weights = params.get(str(weights_key), group_default(_GEN_DEFAULTS, str(weights_key), None))
    if isinstance(raw_weights, Mapping):
        probabilities = normalize_positive_weights({str(k): float(v) for k, v in raw_weights.items()}, default_keys=supported)
    else:
        probabilities = normalize_positive_weights({}, default_keys=supported)
    if bool(params.get(str(balance_key), group_default(_GEN_DEFAULTS, str(balance_key), True))) and params.get("_sample_cursor") is not None:
        positives = [key for key in supported if float(probabilities.get(str(key), 0.0)) > 0.0]
        index = abs(int(params.get("_sample_cursor", 0))) // max(1, int(sampling_divisor))
        return str(positives[int(index) % len(positives)]), dict(probabilities)
    rng = spawn_rng(int(instance_seed), str(namespace))
    return weighted_choice(rng, probabilities, sort_keys=True), dict(probabilities)


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> _RenderParams:
    canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 1080)))
    canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 660)))
    return _RenderParams(
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        plot_left=int(params.get("plot_left_px", group_default(_RENDER_DEFAULTS, "plot_left_px", 86))),
        plot_right=int(canvas_width - int(params.get("plot_right_margin_px", group_default(_RENDER_DEFAULTS, "plot_right_margin_px", 176)))),
        plot_top=int(params.get("plot_top_px", group_default(_RENDER_DEFAULTS, "plot_top_px", 58))),
        plot_bottom=int(canvas_height - int(params.get("plot_bottom_margin_px", group_default(_RENDER_DEFAULTS, "plot_bottom_margin_px", 92)))),
        axis_width=resolve_render_int(params, _RENDER_DEFAULTS, "axis_line_width_px", 2, instance_seed=instance_seed, namespace=TASK_ID),
        grid_width=resolve_render_int(params, _RENDER_DEFAULTS, "grid_line_width_px", 1, instance_seed=instance_seed, namespace=TASK_ID),
        line_width=resolve_render_int(params, _RENDER_DEFAULTS, "line_width_px", 4, instance_seed=instance_seed, namespace=TASK_ID),
        point_radius=resolve_render_int(params, _RENDER_DEFAULTS, "point_radius_px", 7, instance_seed=instance_seed, namespace=TASK_ID),
        tick_font_size=int(params.get("tick_font_size_px", group_default(_RENDER_DEFAULTS, "tick_font_size_px", 16))),
        label_font_size=int(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", 18))),
        value_font_size=int(params.get("value_font_size_px", group_default(_RENDER_DEFAULTS, "value_font_size_px", 15))),
        legend_font_size=int(params.get("legend_font_size_px", group_default(_RENDER_DEFAULTS, "legend_font_size_px", 18))),
        primary_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "primary_rgb", (73, 125, 203), instance_seed=instance_seed, namespace=TASK_ID),
        primary_alt_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "primary_alt_rgb", (104, 171, 130), instance_seed=instance_seed, namespace=TASK_ID),
        line_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "line_rgb", (220, 115, 55), instance_seed=instance_seed, namespace=TASK_ID),
        area_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "area_rgb", (117, 166, 214), instance_seed=instance_seed, namespace=TASK_ID),
        axis_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "axis_color_rgb", (66, 72, 82), instance_seed=instance_seed, namespace=TASK_ID),
        grid_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "grid_color_rgb", (224, 228, 234), instance_seed=instance_seed, namespace=TASK_ID),
        text_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "text_color_rgb", (36, 42, 52), instance_seed=instance_seed, namespace=TASK_ID),
        panel_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "plot_fill_rgb", (255, 255, 255), instance_seed=instance_seed, namespace=TASK_ID),
    )


def _round_axis_max(value: int) -> int:
    return int(max(20, int(math.ceil((float(value) + 8.0) / 10.0) * 10)))


def _value_to_y(value: int, *, top: int, bottom: int, axis_max: int) -> float:
    return float(bottom) - ((float(value) / float(max(1, int(axis_max)))) * float(bottom - top))


def _draw_label_box(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Tuple[float, float],
    font,
    fill: Tuple[int, int, int],
    stroke_fill: Tuple[int, int, int] = (255, 255, 255),
) -> Tuple[float, float, float, float]:
    bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=1)
    w = float(bbox[2] - bbox[0])
    h = float(bbox[3] - bbox[1])
    x0 = float(center[0]) - (0.5 * w) - 4.0
    y0 = float(center[1]) - (0.5 * h) - 2.0
    x1 = float(center[0]) + (0.5 * w) + 4.0
    y1 = float(center[1]) + (0.5 * h) + 2.0
    draw.rounded_rectangle((x0, y0, x1, y1), radius=4, fill=stroke_fill, outline=(214, 218, 226), width=1)
    draw_text_centered(draw, text=str(text), center=center, font=font, fill=fill, stroke_width=0)
    return (x0, y0, x1, y1)


def _draw_axes(
    draw: ImageDraw.ImageDraw,
    *,
    p: _RenderParams,
    labels: Sequence[str],
    primary_axis_max: int,
    line_axis_max: int,
    dual_axis: bool,
) -> None:
    tick_font = load_font(p.tick_font_size, bold=False)
    label_font = load_font(p.label_font_size, bold=True)
    left, right, top, bottom = p.plot_left, p.plot_right, p.plot_top, p.plot_bottom
    draw.rounded_rectangle((left - 14, top - 18, right + 14, bottom + 12), radius=10, fill=p.panel_rgb, outline=(211, 216, 224), width=1)
    for i in range(5):
        value = int(round(primary_axis_max * i / 4))
        y = _value_to_y(value, top=top, bottom=bottom, axis_max=primary_axis_max)
        draw.line((left, y, right, y), fill=p.grid_rgb, width=p.grid_width)
        draw.text((left - 12, y), str(value), anchor="rm", font=tick_font, fill=p.text_rgb)
        if dual_axis:
            line_value = int(round(line_axis_max * i / 4))
            draw.text((right + 12, y), str(line_value), anchor="lm", font=tick_font, fill=p.text_rgb)
    draw.line((left, top, left, bottom), fill=p.axis_rgb, width=p.axis_width)
    draw.line((left, bottom, right, bottom), fill=p.axis_rgb, width=p.axis_width)
    if dual_axis:
        draw.line((right, top, right, bottom), fill=p.axis_rgb, width=p.axis_width)
    step = float(right - left) / float(max(1, len(labels)))
    for idx, label in enumerate(labels):
        x = float(left) + (float(idx) + 0.5) * step
        draw.line((x, bottom, x, bottom + 6), fill=p.axis_rgb, width=1)
        draw_text_centered(draw, text=str(label), center=(x, bottom + 24), font=label_font, fill=p.text_rgb, stroke_width=1)


def _draw_legend(
    draw: ImageDraw.ImageDraw,
    *,
    p: _RenderParams,
    scene_variant: str,
    primary_name: str,
    line_name: str,
) -> None:
    font = load_font(p.legend_font_size, bold=True)
    x0 = p.plot_right + 38
    y0 = p.plot_top + 24
    draw.text((x0, y0), "Legend", font=font, fill=p.text_rgb)
    y = y0 + 34
    if scene_variant == "area_line_overlay":
        draw.rectangle((x0, y + 2, x0 + 28, y + 18), fill=p.area_rgb, outline=p.primary_rgb)
    elif scene_variant in {"stacked_bar_line", "grouped_bar_line"}:
        draw.rectangle((x0, y + 2, x0 + 13, y + 20), fill=p.primary_rgb, outline=(55, 62, 72))
        draw.rectangle((x0 + 15, y + 2, x0 + 28, y + 20), fill=p.primary_alt_rgb, outline=(55, 62, 72))
    else:
        draw.rectangle((x0, y + 2, x0 + 28, y + 20), fill=p.primary_rgb, outline=(55, 62, 72))
    draw.text((x0 + 38, y), str(primary_name), font=font, fill=p.text_rgb)
    y += 34
    draw.line((x0, y + 11, x0 + 30, y + 11), fill=p.line_rgb, width=p.line_width)
    draw.ellipse((x0 + 11, y + 2, x0 + 21, y + 12), fill=(255, 255, 255), outline=p.line_rgb, width=3)
    draw.text((x0 + 38, y), str(line_name), font=font, fill=p.text_rgb)


def _render_combo_scene(
    base: Image.Image,
    *,
    labels: Sequence[str],
    primary_values: Sequence[int],
    line_values: Sequence[int],
    scene_variant: str,
    primary_name: str,
    line_name: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _ComboScene:
    p = _render_params(params, instance_seed=int(instance_seed))
    image = base.convert("RGB")
    draw = ImageDraw.Draw(image)
    primary_axis_max = _round_axis_max(max(primary_values))
    line_axis_max = _round_axis_max(max(line_values)) if scene_variant == "bar_line_dual_axis" else _round_axis_max(max(max(primary_values), max(line_values)))
    if scene_variant != "bar_line_dual_axis":
        primary_axis_max = line_axis_max
    _draw_axes(
        draw,
        p=p,
        labels=labels,
        primary_axis_max=primary_axis_max,
        line_axis_max=line_axis_max,
        dual_axis=(scene_variant == "bar_line_dual_axis"),
    )
    value_font = load_font(p.value_font_size, bold=True)
    n = len(labels)
    step = float(p.plot_right - p.plot_left) / float(max(1, n))
    bar_width = max(22.0, min(56.0, 0.44 * float(step)))
    primary_points: list[Tuple[float, float]] = []
    line_points: list[Tuple[float, float]] = []
    entities: list[Dict[str, Any]] = []

    if scene_variant == "area_line_overlay":
        area_points = []
        for idx, value in enumerate(primary_values):
            x = float(p.plot_left) + (float(idx) + 0.5) * step
            y = _value_to_y(int(value), top=p.plot_top, bottom=p.plot_bottom, axis_max=primary_axis_max)
            area_points.append((x, y))
        polygon = [(area_points[0][0], float(p.plot_bottom))] + area_points + [(area_points[-1][0], float(p.plot_bottom))]
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        odraw.polygon(polygon, fill=tuple(p.area_rgb) + (112,))
        odraw.line(area_points, fill=tuple(p.primary_rgb) + (255,), width=3)
        image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(image)

    for idx, (label, primary_value) in enumerate(zip(labels, primary_values)):
        x = float(p.plot_left) + (float(idx) + 0.5) * step
        y = _value_to_y(int(primary_value), top=p.plot_top, bottom=p.plot_bottom, axis_max=primary_axis_max)
        primary_points.append((x, y))
        if scene_variant in {"bar_line_shared_axis", "bar_line_dual_axis"}:
            box = (x - 0.5 * bar_width, y, x + 0.5 * bar_width, p.plot_bottom)
            draw.rectangle(box, fill=p.primary_rgb, outline=(55, 62, 72), width=1)
        elif scene_variant == "stacked_bar_line":
            split = int(round(int(primary_value) * (0.42 + 0.16 * (idx % 3) / 2.0)))
            split = max(2, min(int(primary_value) - 2, split))
            y_split = _value_to_y(split, top=p.plot_top, bottom=p.plot_bottom, axis_max=primary_axis_max)
            draw.rectangle((x - 0.5 * bar_width, y_split, x + 0.5 * bar_width, p.plot_bottom), fill=p.primary_rgb, outline=(55, 62, 72), width=1)
            draw.rectangle((x - 0.5 * bar_width, y, x + 0.5 * bar_width, y_split), fill=p.primary_alt_rgb, outline=(55, 62, 72), width=1)
        elif scene_variant == "grouped_bar_line":
            split = int(round(int(primary_value) * (0.45 + 0.10 * (idx % 2))))
            other = int(primary_value) - split
            bw = 0.42 * bar_width
            y_a = _value_to_y(split, top=p.plot_top, bottom=p.plot_bottom, axis_max=primary_axis_max)
            y_b = _value_to_y(other, top=p.plot_top, bottom=p.plot_bottom, axis_max=primary_axis_max)
            draw.rectangle((x - bw - 2, y_a, x - 2, p.plot_bottom), fill=p.primary_rgb, outline=(55, 62, 72), width=1)
            draw.rectangle((x + 2, y_b, x + bw + 2, p.plot_bottom), fill=p.primary_alt_rgb, outline=(55, 62, 72), width=1)
            draw.line((x - bw - 4, y, x + bw + 4, y), fill=(55, 62, 72), width=2)
        _draw_label_box(draw, text=str(int(primary_value)), center=(x, max(p.plot_top + 12, y - 15)), font=value_font, fill=p.primary_rgb)
        entities.append(
            {
                "type": "combo_primary_mark",
                "metric": str(primary_name),
                "x_label": str(label),
                "value": int(primary_value),
                "center_px": [float(x), float(y)],
                "bbox_px": [float(x - bar_width * 0.55), float(y), float(x + bar_width * 0.55), float(p.plot_bottom)],
            }
        )

    for idx, (label, line_value) in enumerate(zip(labels, line_values)):
        x = float(p.plot_left) + (float(idx) + 0.5) * step
        y = _value_to_y(int(line_value), top=p.plot_top, bottom=p.plot_bottom, axis_max=line_axis_max)
        line_points.append((x, y))
    if len(line_points) >= 2:
        draw.line(line_points, fill=p.line_rgb, width=p.line_width, joint="curve")
    for idx, (label, line_value) in enumerate(zip(labels, line_values)):
        x, y = line_points[idx]
        r = float(p.point_radius)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255), outline=p.line_rgb, width=3)
        offset = -21 if float(y) > float(primary_points[idx][1]) - 22 else 22
        _draw_label_box(draw, text=str(int(line_value)), center=(x, min(p.plot_bottom - 14, max(p.plot_top + 12, y + offset))), font=value_font, fill=p.line_rgb)
        entities.append(
            {
                "type": "combo_line_point",
                "metric": str(line_name),
                "x_label": str(label),
                "value": int(line_value),
                "center_px": [float(x), float(y)],
                "bbox_px": [float(x - r), float(y - r), float(x + r), float(y + r)],
            }
        )
    _draw_legend(draw, p=p, scene_variant=str(scene_variant), primary_name=str(primary_name), line_name=str(line_name))
    return _ComboScene(
        image=image,
        labels=tuple(str(label) for label in labels),
        primary_values=tuple(int(value) for value in primary_values),
        line_values=tuple(int(value) for value in line_values),
        primary_points=tuple(primary_points),
        line_points=tuple(line_points),
        entities=tuple(entities),
        scene_variant=str(scene_variant),
        primary_name=str(primary_name),
        line_name=str(line_name),
        primary_axis_max=int(primary_axis_max),
        line_axis_max=int(line_axis_max),
        plot_bbox=(int(p.plot_left), int(p.plot_top), int(p.plot_right), int(p.plot_bottom)),
    )


def _sample_labels(rng, count: int) -> Tuple[str, ...]:
    offset = int(rng.randrange(0, len(_LABEL_POOL)))
    values = [_LABEL_POOL[(offset + idx) % len(_LABEL_POOL)] for idx in range(int(count))]
    return tuple(values)


def _sample_values(rng, *, count: int, low: int, high: int) -> Tuple[int, ...]:
    return tuple(int(rng.randint(int(low), int(high))) for _ in range(int(count)))


def _choose_metric_pair(instance_seed: int) -> Tuple[str, str]:
    index = int(hash64(instance_seed, "charts.combo.metric_pair") % len(_METRIC_PAIRS))
    return _METRIC_PAIRS[index]


def _unique_extremum(labels: Sequence[str], values: Sequence[int], *, mode: str) -> Tuple[str, int]:
    if not labels:
        raise ValueError("empty candidate set")
    target = max(values) if str(mode) == "max" else min(values)
    winners = [str(label) for label, value in zip(labels, values) if int(value) == int(target)]
    if len(winners) != 1:
        raise ValueError("extremum tie")
    return str(winners[0]), int(target)


def _indices_for_evidence(indices: Iterable[int], scene: _ComboScene, *, include_primary: bool, include_line: bool) -> Tuple[list[list[float]], list[str]]:
    points: list[list[float]] = []
    labels: list[str] = []
    for idx in indices:
        if include_primary:
            points.append([float(scene.primary_points[int(idx)][0]), float(scene.primary_points[int(idx)][1])])
            labels.append(f"{scene.primary_name}:{scene.labels[int(idx)]}")
        if include_line:
            points.append([float(scene.line_points[int(idx)][0]), float(scene.line_points[int(idx)][1])])
            labels.append(f"{scene.line_name}:{scene.labels[int(idx)]}")
    return points, labels


def _select_threshold(values: Sequence[int], *, rng, above: bool, min_candidates: int = 2) -> int:
    sorted_values = sorted(set(int(value) for value in values))
    if len(sorted_values) < 4:
        raise ValueError("not enough distinct threshold values")
    candidates = []
    for low, high in zip(sorted_values[:-1], sorted_values[1:]):
        threshold = int((int(low) + int(high)) // 2)
        count = sum(1 for value in values if (int(value) > threshold if above else int(value) < threshold))
        if int(min_candidates) <= count <= len(values) - 1:
            candidates.append(threshold)
    if not candidates:
        raise ValueError("no usable threshold")
    return int(candidates[int(rng.randrange(0, len(candidates)))])


def _explicit_axis_selected(params: Mapping[str, Any], keys: Sequence[str], supported: Sequence[str]) -> bool:
    supported_set = {str(item) for item in supported}
    for key in keys:
        value = params.get(str(key))
        if value is not None and str(value).strip() in supported_set:
            return True
    return False


def _balanced_target_count(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    label_count: int,
    sampling_divisor: int,
) -> Tuple[int, Dict[int, float], Tuple[int, int]]:
    low = int(params.get("dual_condition_target_count_min", group_default(_GEN_DEFAULTS, "dual_condition_target_count_min", 1)))
    high = int(params.get("dual_condition_target_count_max", group_default(_GEN_DEFAULTS, "dual_condition_target_count_max", 5)))
    high = min(int(high), max(1, int(label_count) - 1))
    if int(high) < int(low):
        raise ValueError("dual-condition target count support is infeasible")
    support = tuple(range(int(low), int(high) + 1))
    probabilities = {int(value): 1.0 / float(len(support)) for value in support}
    sampling_index = params.get("_sample_cursor")
    if sampling_index is not None:
        index = abs(int(sampling_index)) // max(1, int(sampling_divisor))
    else:
        index = int(hash64(instance_seed, "charts.combo.dual_condition_target_count"))
    return int(support[int(index) % len(support)]), probabilities, (int(low), int(high))


def _threshold_candidates_for(values: Sequence[int], *, above: bool) -> Tuple[int, ...]:
    sorted_values = sorted(set(int(value) for value in values))
    if len(sorted_values) < 2:
        return ()
    thresholds = []
    for low, high in zip(sorted_values[:-1], sorted_values[1:]):
        thresholds.append(int(low) if bool(above) else int(high))
    return tuple(dict.fromkeys(thresholds))


def _choose_targeted_dual_condition(
    *,
    query_id: str,
    primary: Sequence[int],
    line: Sequence[int],
    rng,
    target_count: int,
) -> Tuple[list[int], Dict[str, int]]:
    q = str(query_id)
    candidates: list[Tuple[list[int], Dict[str, int]]] = []
    if q == "primary_between_and_line_above":
        primary_values = sorted(set(int(value) for value in primary))
        line_thresholds = _threshold_candidates_for(line, above=True)
        for low_index, low in enumerate(primary_values):
            for high in primary_values[low_index:]:
                for line_threshold in line_thresholds:
                    matching = [
                        idx
                        for idx, (a, b) in enumerate(zip(primary, line))
                        if int(low) <= int(a) <= int(high) and int(b) > int(line_threshold)
                    ]
                    if len(matching) == int(target_count):
                        candidates.append(
                            (
                                [int(idx) for idx in matching],
                                {
                                    "lower_threshold_value": int(low),
                                    "upper_threshold_value": int(high),
                                    "line_threshold_value": int(line_threshold),
                                },
                            )
                        )
    else:
        primary_above = "primary_above" in q
        line_above = "line_above" in q
        primary_thresholds = _threshold_candidates_for(primary, above=primary_above)
        line_thresholds = _threshold_candidates_for(line, above=line_above)
        for primary_threshold in primary_thresholds:
            for line_threshold in line_thresholds:
                matching = [
                    idx
                    for idx, (a, b) in enumerate(zip(primary, line))
                    if (int(a) > int(primary_threshold) if primary_above else int(a) < int(primary_threshold))
                    and (int(b) > int(line_threshold) if line_above else int(b) < int(line_threshold))
                ]
                if len(matching) == int(target_count):
                    candidates.append(
                        (
                            [int(idx) for idx in matching],
                            {
                                "primary_threshold_value": int(primary_threshold),
                                "line_threshold_value": int(line_threshold),
                            },
                        )
                    )
    if not candidates:
        raise ValueError("no targeted dual-condition threshold pair")
    return candidates[int(rng.randrange(0, len(candidates)))]


def _resolve_query_answer(
    *,
    task_query_ids: Sequence[str],
    query_id: str,
    scene: _ComboScene,
    rng,
    params: Mapping[str, Any],
    instance_seed: int,
    target_sampling_divisor: int,
) -> Tuple[TypedValue, list[list[float]], Dict[str, Any], str, str, str, str]:
    labels = scene.labels
    primary = scene.primary_values
    line = scene.line_values
    q = str(query_id)
    prompt_slots: Dict[str, Any] = {}
    answer_hint_key = "answer_hint_value_integer"
    evidence_hint_key = "evidence_hint_needed_chart_marks"
    if q in {
        "primary_minus_line_at_label",
        "line_minus_primary_at_label",
        "absolute_gap_at_label",
        "larger_minus_smaller_at_label",
    }:
        usable = [idx for idx, (a, b) in enumerate(zip(primary, line)) if int(a) != int(b)]
        if not usable:
            raise ValueError("cross-mark gap needs unequal values")
        idx = int(usable[int(rng.randrange(0, len(usable)))])
        if q == "primary_minus_line_at_label":
            answer = int(primary[idx]) - int(line[idx])
        elif q == "line_minus_primary_at_label":
            answer = int(line[idx]) - int(primary[idx])
        elif q == "absolute_gap_at_label":
            answer = abs(int(primary[idx]) - int(line[idx]))
        else:
            answer = max(int(primary[idx]), int(line[idx])) - min(int(primary[idx]), int(line[idx]))
        evidence, evidence_labels = _indices_for_evidence([idx], scene, include_primary=True, include_line=True)
        prompt_slots["target_label"] = str(labels[idx])
        return (
            TypedValue(type="integer", value=int(answer)),
            evidence,
            {"target_label": str(labels[idx]), "target_index": idx, "evidence_labels": evidence_labels},
            "cross_mark_difference_query",
            q,
            answer_hint_key,
            evidence_hint_key,
        )
    if q in {
        "max_line_where_primary_above_threshold",
        "min_line_where_primary_above_threshold",
        "max_primary_where_line_below_threshold",
        "min_primary_where_line_below_threshold",
    }:
        if "primary_above" in q:
            threshold = _select_threshold(primary, rng=rng, above=True)
            candidate_indices = [idx for idx, value in enumerate(primary) if int(value) > int(threshold)]
            target_values = [int(line[idx]) for idx in candidate_indices]
            mode = "max" if q.startswith("max_") else "min"
            answer, _ = _unique_extremum([labels[idx] for idx in candidate_indices], target_values, mode=mode)
            answer_index = labels.index(answer)
            evidence, evidence_labels = _indices_for_evidence(candidate_indices, scene, include_primary=True, include_line=True)
            relation_phrase = "above"
        else:
            threshold = _select_threshold(line, rng=rng, above=False)
            candidate_indices = [idx for idx, value in enumerate(line) if int(value) < int(threshold)]
            target_values = [int(primary[idx]) for idx in candidate_indices]
            mode = "max" if q.startswith("max_") else "min"
            answer, _ = _unique_extremum([labels[idx] for idx in candidate_indices], target_values, mode=mode)
            answer_index = labels.index(answer)
            evidence, evidence_labels = _indices_for_evidence(candidate_indices, scene, include_primary=True, include_line=True)
            relation_phrase = "below"
        prompt_slots.update({"threshold_value": int(threshold), "threshold_relation": relation_phrase})
        return (
            TypedValue(type="string", value=str(answer)),
            evidence,
            {
                "threshold_value": int(threshold),
                "target_index": int(answer_index),
                "candidate_indices": [int(idx) for idx in candidate_indices],
                "evidence_labels": evidence_labels,
            },
            "conditioned_extremum_query",
            q,
            "answer_hint_category_label_extremum",
            evidence_hint_key,
        )
    if q in {
        "primary_above_and_line_above",
        "primary_above_and_line_below",
        "primary_below_and_line_above",
        "primary_between_and_line_above",
    }:
        target_count, target_probabilities, target_range = _balanced_target_count(
            params=params,
            instance_seed=int(instance_seed),
            label_count=len(labels),
            sampling_divisor=int(target_sampling_divisor),
        )
        matching, extra = _choose_targeted_dual_condition(
            query_id=q,
            primary=primary,
            line=line,
            rng=rng,
            target_count=int(target_count),
        )
        prompt_slots.update(dict(extra))
        evidence, evidence_labels = _indices_for_evidence(matching, scene, include_primary=True, include_line=True)
        return (
            TypedValue(type="integer", value=int(len(matching))),
            evidence,
            {
                **extra,
                "target_count": int(target_count),
                "target_count_range": [int(target_range[0]), int(target_range[1])],
                "target_count_probabilities": {str(key): float(value) for key, value in target_probabilities.items()},
                "matching_indices": [int(idx) for idx in matching],
                "evidence_labels": evidence_labels,
            },
            "dual_condition_count_query",
            q,
            "answer_hint_matching_category_count",
            "evidence_hint_matching_category_marks",
        )
    if q in {
        "line_change_minus_primary_change",
        "primary_change_minus_line_change",
        "absolute_change_gap",
        "larger_change_minus_smaller_change",
    }:
        interval_span_min = int(params.get("interval_span_min", 2))
        interval_span_max = int(params.get("interval_span_max", max(2, len(labels) - 1)))
        feasible_span_min = max(2, int(interval_span_min))
        feasible_span_max = min(max(2, int(interval_span_max)), max(2, len(labels) - 1))
        if feasible_span_min > feasible_span_max:
            raise ValueError("interval_change_comparison_query has no feasible interval span")
        span = int(rng.randint(int(feasible_span_min), int(feasible_span_max)))
        start = int(rng.randrange(0, max(1, len(labels) - int(span))))
        end = int(start + int(span))
        primary_change = int(primary[end]) - int(primary[start])
        line_change = int(line[end]) - int(line[start])
        if q == "line_change_minus_primary_change":
            answer = int(line_change) - int(primary_change)
        elif q == "primary_change_minus_line_change":
            answer = int(primary_change) - int(line_change)
        elif q == "absolute_change_gap":
            answer = abs(int(line_change) - int(primary_change))
        else:
            answer = max(int(line_change), int(primary_change)) - min(int(line_change), int(primary_change))
        evidence, evidence_labels = _indices_for_evidence([start, end], scene, include_primary=True, include_line=True)
        prompt_slots.update({"start_label": str(labels[start]), "end_label": str(labels[end])})
        return (
            TypedValue(type="integer", value=int(answer)),
            evidence,
            {
                "start_label": str(labels[start]),
                "end_label": str(labels[end]),
                "start_index": int(start),
                "end_index": int(end),
                "interval_span": int(span),
                "interval_span_range": [int(feasible_span_min), int(feasible_span_max)],
                "primary_change": int(primary_change),
                "line_change": int(line_change),
                "evidence_labels": evidence_labels,
            },
            "interval_change_comparison_query",
            q,
            answer_hint_key,
            evidence_hint_key,
        )
    if q in {
        "largest_absolute_gap_label",
        "smallest_nonzero_absolute_gap_label",
        "largest_primary_over_line_gap_label",
        "largest_line_over_primary_gap_label",
    }:
        candidates: list[Tuple[int, int]] = []
        for idx, (a, b) in enumerate(zip(primary, line)):
            signed_gap = int(a) - int(b)
            if q == "largest_absolute_gap_label":
                candidates.append((idx, abs(int(signed_gap))))
            elif q == "smallest_nonzero_absolute_gap_label":
                if int(signed_gap) != 0:
                    candidates.append((idx, abs(int(signed_gap))))
            elif q == "largest_primary_over_line_gap_label":
                if int(signed_gap) > 0:
                    candidates.append((idx, int(signed_gap)))
            elif q == "largest_line_over_primary_gap_label" and int(signed_gap) < 0:
                candidates.append((idx, -int(signed_gap)))
        if not candidates:
            raise ValueError("no gap-extremum candidates")
        target_value = min(value for _, value in candidates) if q == "smallest_nonzero_absolute_gap_label" else max(value for _, value in candidates)
        winners = [idx for idx, value in candidates if int(value) == int(target_value)]
        if len(winners) != 1:
            raise ValueError("gap extremum tie")
        answer_index = int(winners[0])
        candidate_indices = [int(idx) for idx, _ in candidates]
        evidence, evidence_labels = _indices_for_evidence(candidate_indices, scene, include_primary=True, include_line=True)
        return (
            TypedValue(type="string", value=str(labels[answer_index])),
            evidence,
            {
                "target_index": int(answer_index),
                "target_label": str(labels[answer_index]),
                "target_gap_value": int(target_value),
                "candidate_indices": candidate_indices,
                "gap_values": {str(labels[idx]): int(abs(int(primary[idx]) - int(line[idx]))) for idx in range(len(labels))},
                "signed_gap_values": {str(labels[idx]): int(primary[idx]) - int(line[idx]) for idx in range(len(labels))},
                "evidence_labels": evidence_labels,
            },
            "gap_extremum_label_query",
            q,
            "answer_hint_category_label",
            "evidence_hint_candidate_category_marks",
        )
    raise ValueError(f"unsupported combo query id: {q}")


def _merge_prompt_slots(base: Mapping[str, Any], extra: Mapping[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    merged.update(dict(extra))
    return merged


class ChartsComboPanelQueryTask:
    """Shared generator for public combo-chart tasks."""

    domain = "charts"
    task_group = "combo"
    default_dataset_enabled = True
    task_id = TASK_ID
    query_ids: Tuple[str, ...] = ()

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        if not self.query_ids:
            raise ValueError("combo chart task must define query_ids")
        query_id, query_probabilities = _axis_choice(
            params=params,
            instance_seed=int(instance_seed),
            supported=self.query_ids,
            explicit_keys=("query_id", "query_variant", "query_variant"),
            weights_key="query_variant_weights",
            balance_key="balanced_query_variant_sampling",
            namespace=f"{self.task_id}.query",
        )
        query_axis_explicit = _explicit_axis_selected(
            params,
            ("query_id", "query_variant", "query_variant"),
            self.query_ids,
        )
        scene_variant, scene_probabilities = _axis_choice(
            params=params,
            instance_seed=int(instance_seed),
            supported=_SCENE_VARIANTS,
            explicit_keys=("scene_variant",),
            weights_key="scene_variant_weights",
            balance_key="balanced_scene_variant_sampling",
            namespace=f"{self.task_id}.scene",
            sampling_divisor=max(1, len(self.query_ids)),
        )
        scene_axis_explicit = _explicit_axis_selected(params, ("scene_variant",), _SCENE_VARIANTS)
        target_sampling_divisor = (1 if query_axis_explicit else max(1, len(self.query_ids))) * (
            1 if scene_axis_explicit else max(1, len(_SCENE_VARIANTS))
        )
        label_min, label_max = _as_int_bounds(params, "label_count_min", "label_count_max", (7, 11))
        value_min, value_max = _as_int_bounds(params, "value_min", "value_max", (12, 88))
        rng = spawn_rng(int(instance_seed), f"{self.task_id}.values")
        label_count = int(rng.randint(int(label_min), int(label_max)))
        labels = _sample_labels(rng, label_count)
        primary_values = _sample_values(rng, count=label_count, low=value_min, high=value_max)
        line_values = _sample_values(rng, count=label_count, low=value_min, high=value_max)
        primary_name, line_name = _choose_metric_pair(int(instance_seed))
        background, background_meta = make_background_canvas(
            canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 1080))),
            canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 660))),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        scene = _render_combo_scene(
            background,
            labels=labels,
            primary_values=primary_values,
            line_values=line_values,
            scene_variant=str(scene_variant),
            primary_name=str(primary_name),
            line_name=str(line_name),
            params=params,
            instance_seed=int(instance_seed),
        )
        answer_gt, evidence_points, query_trace, task_key, query_key, answer_hint_key, evidence_hint_key = _resolve_query_answer(
            task_query_ids=self.query_ids,
            query_id=str(query_id),
            scene=scene,
            rng=spawn_rng(int(instance_seed), f"{self.task_id}.query_params"),
            params=params,
            instance_seed=int(instance_seed),
            target_sampling_divisor=int(target_sampling_divisor),
        )
        prompt_defaults = dict(_PROMPT_DEFAULTS)
        object_description_key = f"object_description_{scene_variant}"
        if object_description_key not in prompt_defaults:
            raise ValueError(f"missing prompt default '{object_description_key}' for {self.task_id}")
        object_description_template = str(
            params.get(
                object_description_key,
                prompt_defaults[object_description_key],
            )
        )
        object_description = object_description_template.format(
            primary_name=str(primary_name),
            line_name=str(line_name),
        )
        prompt_slots = _merge_prompt_slots(
            {
                "object_description": object_description,
                "primary_name": str(primary_name),
                "line_name": str(line_name),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[answer_hint_key]),
                "evidence_hint": str(prompt_defaults[evidence_hint_key]),
                "json_example": str(prompt_defaults[f"json_example_{task_key}"]),
                "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{task_key}"]),
            },
            query_trace,
        )
        prompt_selection = render_task_prompt_variants(
            domain="charts",
            task_group="combo",
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(task_key),
            query_key=str(query_key),
            slots=prompt_slots,
            instance_seed=int(instance_seed),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        image, post_noise_meta = apply_post_image_noise(
            scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        query_params = {
            "query_variant": "default",
            "query_id": str(query_id),
            "query_variant": str(query_id),
            "query_variant_probabilities": dict(query_probabilities),
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(scene_probabilities),
            "labels": list(labels),
            "primary_name": str(primary_name),
            "line_name": str(line_name),
            "primary_values": [int(value) for value in primary_values],
            "line_values": [int(value) for value in line_values],
            "label_count": int(label_count),
            "label_count_range": [int(label_min), int(label_max)],
            **dict(query_trace),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_combo_panel",
                "entities": [dict(entity) for entity in scene.entities],
                "relations": dict(query_params),
            },
            "query_spec": {
                "query_variant": "default",
                "query_id": str(query_id),
                "query_variant": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "scene_id": SCENE_ID,
                "scene_variant": str(scene_variant),
                "plot_bbox": list(scene.plot_bbox),
                "primary_axis_max": int(scene.primary_axis_max),
                "line_axis_max": int(scene.line_axis_max),
                "background": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(scene.plot_bbox),
                "primary_points_px": [list(point) for point in scene.primary_points],
                "line_points_px": [list(point) for point in scene.line_points],
                "entities": [dict(entity) for entity in scene.entities],
            },
            "execution_trace": {
                "query_id": str(query_id),
                "query_variant": str(query_id),
                "query_variant": "default",
                "question_format": str(task_key),
                "answer": answer_gt.value,
                "answer_type": str(answer_gt.type),
                **dict(query_params),
            },
            "verifier_payload": {
                "answer": answer_gt.value,
                "answer_type": str(answer_gt.type),
                "query_id": str(query_id),
                "primary_values": [int(value) for value in primary_values],
                "line_values": [int(value) for value in line_values],
                "labels": list(labels),
                **dict(query_trace),
            },
            "witness_symbolic": {
                "type": "combo_chart_marks",
                "evidence_labels": list(query_trace.get("evidence_labels", [])),
            },
            "projected_evidence": {
                "point_set": [list(point) for point in evidence_points],
            },
            "background": dict(background_meta),
            "post_image_noise": dict(post_noise_meta),
        }
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(label_count), [int(label_min), int(label_max)]),
                "reasoning_load": float(_QUERY_REASONING_LOAD[str(query_id)]),
                "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(scene_variant)]),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=TypedValue(type="point_set", value=[list(point) for point in evidence_points]),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_variant="default",
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        public_overrides = (
            _public_task_param_overrides(str(self.task_id))
            if str(self.task_id) != str(TASK_ID)
            else {}
        )
        if public_overrides:
            merged_params = dict(public_overrides)
            merged_params.update(dict(params))
            params = merged_params
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) if attempt == 0 else int(hash64(instance_seed, f"{self.task_id}.retry", attempt))
            try:
                return self._generate_once(attempt_seed, params=params)
            except ValueError as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")


@register_task
class ChartsComboCrossMarkDifferenceValueTask(ChartsComboPanelQueryTask):
    """Compute differences between the primary mark value and overlaid line value."""

    task_id = "task_charts__combo_mark__cross_mark_difference_value"
    query_ids = (
        "primary_minus_line_at_label",
        "line_minus_primary_at_label",
    )


@register_task
class ChartsComboConditionedExtremumLabelTask(ChartsComboPanelQueryTask):
    """Filter by one combo-chart series and find an extremum in the other."""

    task_id = "task_charts__combo_mark__conditioned_extremum_label"
    query_ids = (
        "max_line_where_primary_above_threshold",
        "min_line_where_primary_above_threshold",
        "max_primary_where_line_below_threshold",
        "min_primary_where_line_below_threshold",
    )


@register_task
class ChartsComboDualConditionCountTask(ChartsComboPanelQueryTask):
    """Count categories satisfying conditions over both combo-chart encodings."""

    task_id = "task_charts__combo_mark__dual_condition_count"
    query_ids = (
        "primary_above_and_line_above",
        "primary_above_and_line_below",
        "primary_below_and_line_above",
        "primary_between_and_line_above",
    )


@register_task
class ChartsComboIntervalChangeComparisonValueTask(ChartsComboPanelQueryTask):
    """Compare primary-value and line-value changes over an interval."""

    task_id = "task_charts__combo_mark__interval_change_comparison_value"
    query_ids = (
        "line_change_minus_primary_change",
        "primary_change_minus_line_change",
        "absolute_change_gap",
        "larger_change_minus_smaller_change",
    )


@register_task
class ChartsComboGapExtremumLabelTask(ChartsComboPanelQueryTask):
    """Find the category with an extremal gap between the primary and line encodings."""

    task_id = "task_charts__combo_mark__gap_extremum_label"
    query_ids = (
        "largest_absolute_gap_label",
        "smallest_nonzero_absolute_gap_label",
        "largest_primary_over_line_gap_label",
        "largest_line_over_primary_gap_label",
    )


__all__ = [
    "ChartsComboConditionedExtremumLabelTask",
    "ChartsComboCrossMarkDifferenceValueTask",
    "ChartsComboDualConditionCountTask",
    "ChartsComboGapExtremumLabelTask",
    "ChartsComboIntervalChangeComparisonValueTask",
    "ChartsComboPanelQueryTask",
]
