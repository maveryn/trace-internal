"""Smooth density-curve chart tasks with label-selection answers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from .....core.sampling import normalize_positive_weights, weighted_choice
from .....core.seed import spawn_rng
from .....core.scene_config import get_scene_defaults
from ....shared.color_distance import sample_color_palette_with_distance_constraints
from ....shared.config_defaults import group_default, split_scene_generation_rendering_prompt_defaults
from ....shared.text_legibility import draw_text_traced
from ....shared.text_rendering import load_font
from ...shared.distribution_chart_common import DistributionChartDefaults, LabeledChartDefaults, resolve_chart_render_params_for_task
from ...shared.label_assets import ResolvedChartLabels, resolve_chart_category_labels
from ...shared.visual_defaults import load_chart_scene_noise_defaults


SCENE_NAMESPACE = "charts.density_curve"
SCENE_ID = "density_curve"
SCENE_VARIANT = "density_curve"

SUPPORTED_PROMPT_KEYS: Tuple[str, ...] = (
    "highest_mean_label",
    "lowest_mean_label",
    "leftmost_mode_label",
    "rightmost_mode_label",
    "greatest_interval_mass_label",
    "least_interval_mass_label",
    "highest_density_at_x_label",
    "lowest_density_at_x_label",
)
SUPPORTED_DENSITY_FAMILIES: Tuple[str, ...] = (
    "gaussian",
    "gaussian_mixture_2",
    "gaussian_mixture_3",
    "skewed_unimodal",
    "lognormal_like",
    "student_t_like",
    "asymmetric_bimodal",
)
SUPPORTED_CURVE_LINE_STYLES: Tuple[str, ...] = ("solid", "dash", "dot")

_MEAN_PROMPT_KEYS = ("highest_mean_label", "lowest_mean_label")
_MODE_PROMPT_KEYS = ("leftmost_mode_label", "rightmost_mode_label")
_INTERVAL_PROMPT_KEYS = ("greatest_interval_mass_label", "least_interval_mass_label")
_DENSITY_AT_X_PROMPT_KEYS = ("highest_density_at_x_label", "lowest_density_at_x_label")

_TASK_GROUP_DEFAULTS = get_scene_defaults("charts", "density_curve")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    **{"task" "_id": SCENE_NAMESPACE},
)
_DEFAULTS = DistributionChartDefaults()
_RENDER_DEFAULTS_FALLBACK = LabeledChartDefaults()
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id="density_curve", apply_prob=0.0)

_REASONING_LOAD_BY_QUERY: Dict[str, float] = {
    "highest_mean_label": 0.56,
    "lowest_mean_label": 0.56,
    "leftmost_mode_label": 0.58,
    "rightmost_mode_label": 0.58,
    "greatest_interval_mass_label": 0.74,
    "least_interval_mass_label": 0.74,
    "highest_density_at_x_label": 0.62,
    "lowest_density_at_x_label": 0.62,
}

RGB = Tuple[int, int, int]
BBox = List[float]


@dataclass(frozen=True)
class _CurvePoint:
    x_value: float
    y_value: float


@dataclass(frozen=True)
class _DensityCurve:
    label: str
    color_rgb: RGB
    line_style: str
    family: str
    component_count: int
    points: Tuple[_CurvePoint, ...]
    mean_x: float
    mode_x: float
    mode_y: float
    interval_mass: float
    density_at_x: float


@dataclass(frozen=True)
class _Query:
    prompt_key: str
    answer_label: str
    annotation_key: str
    interval_start: float
    interval_end: float
    reference_x: float
    trace: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    curves: Tuple[_DensityCurve, ...]
    query: _Query
    x_min: float
    x_max: float
    y_max: float
    curve_count: int
    label_resolution: ResolvedChartLabels


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: BBox
    legend_bbox_px: BBox
    legend_item_bboxes_px: Dict[str, BBox]
    curve_bboxes_px: Dict[str, BBox]
    mean_marker_bboxes_px: Dict[str, BBox]
    mode_marker_bboxes_px: Dict[str, BBox]
    interval_mass_bboxes_px: Dict[str, BBox]
    density_at_x_points_px: Dict[str, List[float]]
    title_bbox_px: BBox
    render_meta: Dict[str, Any]


def _bbox(values: Sequence[float]) -> BBox:
    return [round(float(value), 3) for value in values]


def _bbox_union(boxes: Sequence[Sequence[float]]) -> BBox:
    valid = [tuple(float(value) for value in box[:4]) for box in boxes if len(box) >= 4]
    if not valid:
        return []
    return _bbox((min(box[0] for box in valid), min(box[1] for box in valid), max(box[2] for box in valid), max(box[3] for box in valid)))


def _gen_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), int(fallback))))


def _gen_float(params: Mapping[str, Any], key: str, fallback: float) -> float:
    return float(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), float(fallback))))


def _resolve_curve_count(params: Mapping[str, Any], *, rng) -> Tuple[int, Dict[str, float]]:
    count_min = max(2, _gen_int(params, "density_curve_count_min", 4))
    count_max = max(count_min, _gen_int(params, "density_curve_count_max", 7))
    raw_weights = params.get("density_curve_count_weights", group_default(_GEN_DEFAULTS, "density_curve_count_weights", {}))
    if isinstance(raw_weights, Mapping):
        weights = {
            str(count): float(raw_weights.get(str(count), raw_weights.get(int(count), 0.0)))
            for count in range(int(count_min), int(count_max) + 1)
        }
    else:
        weights = {}
    probabilities = normalize_positive_weights(weights, default_keys=tuple(str(count) for count in range(int(count_min), int(count_max) + 1)))
    selected = int(weighted_choice(rng, probabilities, sort_keys=True))
    return int(selected), dict(probabilities)


def _resolve_density_family(params: Mapping[str, Any], *, rng) -> Tuple[str, Dict[str, float]]:
    raw_weights = params.get("density_family_weights", group_default(_GEN_DEFAULTS, "density_family_weights", {}))
    if not isinstance(raw_weights, Mapping):
        raw_weights = {}
    probabilities = normalize_positive_weights(
        {str(key): float(value) for key, value in raw_weights.items() if str(key) in set(SUPPORTED_DENSITY_FAMILIES)},
        default_keys=SUPPORTED_DENSITY_FAMILIES,
    )
    return str(weighted_choice(rng, probabilities, sort_keys=True)), dict(probabilities)


def _normal_pdf(x_value: float, mean: float, sigma: float) -> float:
    sigma = max(1e-6, float(sigma))
    z_value = (float(x_value) - float(mean)) / sigma
    return math.exp(-0.5 * z_value * z_value) / sigma


def _split_normal_pdf(x_value: float, mode: float, left_sigma: float, right_sigma: float) -> float:
    sigma = float(left_sigma) if float(x_value) < float(mode) else float(right_sigma)
    z_value = (float(x_value) - float(mode)) / max(1e-6, sigma)
    return math.exp(-0.5 * z_value * z_value)


def _student_t_like_pdf(x_value: float, center: float, scale: float, nu: float) -> float:
    scaled = (float(x_value) - float(center)) / max(1e-6, float(scale))
    return (1.0 + (scaled * scaled / max(1.0, float(nu)))) ** (-(float(nu) + 1.0) / 2.0)


def _lognormal_like_pdf(x_value: float, shift: float, mu: float, sigma: float) -> float:
    shifted = max(0.25, float(x_value) - float(shift))
    log_value = math.log(shifted)
    return math.exp(-((log_value - float(mu)) ** 2) / (2.0 * float(sigma) * float(sigma))) / (shifted * max(1e-6, float(sigma)))


def _density_values_for_family(rng, *, family: str, xs: Sequence[float]) -> Tuple[Tuple[float, ...], int, Tuple[Dict[str, float], ...]]:
    if str(family) == "gaussian":
        mean = float(rng.uniform(18.0, 82.0))
        sigma = float(rng.uniform(7.0, 15.0))
        return tuple(_normal_pdf(x, mean, sigma) for x in xs), 1, ({"mean": mean, "sigma": sigma, "weight": 1.0},)

    if str(family) in {"gaussian_mixture_2", "gaussian_mixture_3", "asymmetric_bimodal"}:
        component_count = 3 if str(family) == "gaussian_mixture_3" else 2
        base_centers = sorted(float(rng.uniform(14.0, 86.0)) for _ in range(int(component_count)))
        if str(family) == "asymmetric_bimodal":
            base_centers = sorted((float(rng.uniform(16.0, 38.0)), float(rng.uniform(58.0, 86.0))))
        raw_weights = [float(rng.uniform(0.45, 1.35)) for _ in range(int(component_count))]
        weight_total = sum(raw_weights)
        weights = [float(value) / float(weight_total) for value in raw_weights]
        sigmas = [float(rng.uniform(5.0, 12.5)) for _ in range(int(component_count))]
        values = []
        for x in xs:
            values.append(sum(float(w) * _normal_pdf(float(x), float(center), float(sigma)) for w, center, sigma in zip(weights, base_centers, sigmas)))
        components = tuple(
            {"mean": float(center), "sigma": float(sigma), "weight": float(weight)}
            for center, sigma, weight in zip(base_centers, sigmas, weights)
        )
        return tuple(values), int(component_count), components

    if str(family) == "skewed_unimodal":
        mode = float(rng.uniform(22.0, 78.0))
        if rng.random() < 0.5:
            left_sigma, right_sigma = float(rng.uniform(5.0, 8.5)), float(rng.uniform(12.0, 20.0))
        else:
            left_sigma, right_sigma = float(rng.uniform(12.0, 20.0)), float(rng.uniform(5.0, 8.5))
        values = tuple(_split_normal_pdf(x, mode, left_sigma, right_sigma) for x in xs)
        return values, 1, ({"mode": mode, "left_sigma": left_sigma, "right_sigma": right_sigma, "weight": 1.0},)

    if str(family) == "lognormal_like":
        shift = float(rng.uniform(-4.0, 8.0))
        mu = float(rng.uniform(3.0, 4.0))
        sigma = float(rng.uniform(0.28, 0.55))
        values = tuple(_lognormal_like_pdf(x, shift, mu, sigma) for x in xs)
        return values, 1, ({"shift": shift, "mu": mu, "sigma": sigma, "weight": 1.0},)

    if str(family) == "student_t_like":
        center = float(rng.uniform(20.0, 80.0))
        scale = float(rng.uniform(7.0, 14.0))
        nu = float(rng.uniform(2.2, 5.5))
        values = tuple(_student_t_like_pdf(x, center, scale, nu) for x in xs)
        return values, 1, ({"center": center, "scale": scale, "nu": nu, "weight": 1.0},)

    raise ValueError(f"unsupported density family: {family}")


def _integral(xs: Sequence[float], ys: Sequence[float]) -> float:
    if len(xs) < 2:
        return 0.0
    total = 0.0
    for index in range(len(xs) - 1):
        dx = float(xs[index + 1]) - float(xs[index])
        total += 0.5 * dx * (float(ys[index]) + float(ys[index + 1]))
    return float(total)


def _interval_integral(xs: Sequence[float], ys: Sequence[float], *, start: float, end: float) -> float:
    selected_x: list[float] = []
    selected_y: list[float] = []
    for x_value, y_value in zip(xs, ys):
        if float(start) <= float(x_value) <= float(end):
            selected_x.append(float(x_value))
            selected_y.append(float(y_value))
    return _integral(selected_x, selected_y)


def _interpolated_y_at_x(xs: Sequence[float], ys: Sequence[float], *, x_value: float) -> float:
    if not xs or not ys:
        return 0.0
    target = float(x_value)
    if target <= float(xs[0]):
        return float(ys[0])
    if target >= float(xs[-1]):
        return float(ys[-1])
    for index in range(len(xs) - 1):
        left_x, right_x = float(xs[index]), float(xs[index + 1])
        if left_x <= target <= right_x:
            left_y, right_y = float(ys[index]), float(ys[index + 1])
            t_value = (target - left_x) / max(1e-9, right_x - left_x)
            return left_y + (t_value * (right_y - left_y))
    return float(ys[-1])


def _curve_metrics(
    xs: Sequence[float],
    ys: Sequence[float],
    *,
    interval_start: float,
    interval_end: float,
    reference_x: float,
) -> Tuple[float, float, float, float, float]:
    mass = max(1e-9, _integral(xs, ys))
    mean_x = _integral(xs, [float(x) * float(y) for x, y in zip(xs, ys)]) / mass
    peak_index = max(range(len(ys)), key=lambda index: (float(ys[index]), -abs(float(xs[index]) - mean_x)))
    mode_x = float(xs[int(peak_index)])
    mode_y = float(ys[int(peak_index)])
    interval_mass = _interval_integral(xs, ys, start=float(interval_start), end=float(interval_end)) / mass
    density_at_x = _interpolated_y_at_x(xs, ys, x_value=float(reference_x))
    return float(mean_x), float(mode_x), float(mode_y), float(interval_mass), float(density_at_x)


def _winner_for_query(prompt_key: str, curves: Sequence[_DensityCurve]) -> str:
    if str(prompt_key) == "highest_mean_label":
        return max((curve.label for curve in curves), key=lambda label: (next(c.mean_x for c in curves if c.label == label), label))
    if str(prompt_key) == "lowest_mean_label":
        return min((curve.label for curve in curves), key=lambda label: (next(c.mean_x for c in curves if c.label == label), label))
    if str(prompt_key) == "rightmost_mode_label":
        return max((curve.label for curve in curves), key=lambda label: (next(c.mode_x for c in curves if c.label == label), label))
    if str(prompt_key) == "leftmost_mode_label":
        return min((curve.label for curve in curves), key=lambda label: (next(c.mode_x for c in curves if c.label == label), label))
    if str(prompt_key) == "greatest_interval_mass_label":
        return max((curve.label for curve in curves), key=lambda label: (next(c.interval_mass for c in curves if c.label == label), label))
    if str(prompt_key) == "least_interval_mass_label":
        return min((curve.label for curve in curves), key=lambda label: (next(c.interval_mass for c in curves if c.label == label), label))
    if str(prompt_key) == "highest_density_at_x_label":
        return max((curve.label for curve in curves), key=lambda label: (next(c.density_at_x for c in curves if c.label == label), label))
    if str(prompt_key) == "lowest_density_at_x_label":
        return min((curve.label for curve in curves), key=lambda label: (next(c.density_at_x for c in curves if c.label == label), label))
    raise ValueError(f"unsupported density-curve prompt key: {prompt_key}")


def _winner_gap_for_query(prompt_key: str, curves: Sequence[_DensityCurve]) -> float:
    if str(prompt_key) in _MEAN_PROMPT_KEYS:
        values = sorted(float(curve.mean_x) for curve in curves)
        return abs(float(values[-1] - values[-2]) if str(prompt_key) == "highest_mean_label" else float(values[1] - values[0]))
    if str(prompt_key) in _MODE_PROMPT_KEYS:
        values = sorted(float(curve.mode_x) for curve in curves)
        return abs(float(values[-1] - values[-2]) if str(prompt_key) == "rightmost_mode_label" else float(values[1] - values[0]))
    if str(prompt_key) in _INTERVAL_PROMPT_KEYS:
        values = sorted(float(curve.interval_mass) for curve in curves)
        return abs(float(values[-1] - values[-2]) if str(prompt_key) == "greatest_interval_mass_label" else float(values[1] - values[0]))
    values = sorted(float(curve.density_at_x) for curve in curves)
    return abs(float(values[-1] - values[-2]) if str(prompt_key) == "highest_density_at_x_label" else float(values[1] - values[0]))


def _min_gap_for_query(prompt_key: str, params: Mapping[str, Any]) -> float:
    if str(prompt_key) in _MEAN_PROMPT_KEYS:
        return _gen_float(params, "density_curve_mean_winner_gap_min", 5.5)
    if str(prompt_key) in _MODE_PROMPT_KEYS:
        return _gen_float(params, "density_curve_mode_winner_gap_min", 5.0)
    if str(prompt_key) in _INTERVAL_PROMPT_KEYS:
        return _gen_float(params, "density_curve_interval_mass_winner_gap_min", 0.045)
    return _gen_float(params, "density_curve_at_x_winner_gap_min", 0.006)


def _sample_palette(params: Mapping[str, Any], *, instance_seed: int, count: int, anchor_colors: Sequence[RGB]) -> Tuple[RGB, ...]:
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.palette")
    channel_min = int(params.get("density_curve_color_channel_min", group_default(_RENDER_DEFAULTS, "mark_color_channel_min", 20)))
    channel_max = int(params.get("density_curve_color_channel_max", group_default(_RENDER_DEFAULTS, "mark_color_channel_max", 210)))
    min_distance = float(params.get("density_curve_color_min_distance", group_default(_RENDER_DEFAULTS, "mark_color_min_distance", 38.0)))
    distance_space = str(params.get("density_curve_color_distance_space", group_default(_RENDER_DEFAULTS, "mark_color_distance_space", "lab")))
    return sample_color_palette_with_distance_constraints(
        rng,
        palette_size=int(count),
        channel_min=int(channel_min),
        channel_max=int(channel_max),
        anchor_colors=tuple(anchor_colors),
        min_distance=float(min_distance),
        distance_space=str(distance_space),
    )


def _build_dataset(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    prompt_key: str,
    prompt_key_probabilities: Mapping[str, float],
    render_params,
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.dataset")
    curve_count, curve_count_probabilities = _resolve_curve_count(params, rng=rng)
    x_min = _gen_float(params, "density_curve_x_min", 0.0)
    x_max = _gen_float(params, "density_curve_x_max", 100.0)
    grid_size = max(81, _gen_int(params, "density_curve_x_grid_size", 161))
    xs = tuple(float(x_min) + (float(x_max) - float(x_min)) * (float(index) / float(grid_size - 1)) for index in range(int(grid_size)))
    interval_width_min = _gen_float(params, "density_curve_interval_width_min", 18.0)
    interval_width_max = max(interval_width_min, _gen_float(params, "density_curve_interval_width_max", 34.0))
    interval_width = float(rng.uniform(float(interval_width_min), float(interval_width_max)))
    interval_start = float(rng.uniform(float(x_min) + 8.0, float(x_max) - float(interval_width) - 8.0))
    interval_end = float(interval_start + interval_width)
    reference_x = float(rng.uniform(float(x_min) + 14.0, float(x_max) - 14.0))
    labels_resolution = resolve_chart_category_labels(
        rng,
        count=int(curve_count),
        min_chars=int(params.get("density_curve_label_min_chars", group_default(_GEN_DEFAULTS, "density_curve_label_min_chars", 3))),
        max_chars=int(params.get("density_curve_label_max_chars", group_default(_GEN_DEFAULTS, "density_curve_label_max_chars", 10))),
        allow_spaces=bool(params.get("density_curve_label_allow_spaces", group_default(_GEN_DEFAULTS, "density_curve_label_allow_spaces", False))),
    )
    labels = tuple(str(label) for label in labels_resolution.labels)
    palette = _sample_palette(
        params,
        instance_seed=int(instance_seed),
        count=int(curve_count),
        anchor_colors=(tuple(render_params.plot_fill_rgb), tuple(render_params.text_color_rgb), tuple(render_params.grid_color_rgb)),
    )
    styles_raw = params.get("density_curve_line_style_weights", group_default(_GEN_DEFAULTS, "density_curve_line_style_weights", {}))
    style_probabilities = normalize_positive_weights(
        {str(key): float(value) for key, value in styles_raw.items()} if isinstance(styles_raw, Mapping) else {},
        default_keys=SUPPORTED_CURVE_LINE_STYLES,
    )

    curves: list[_DensityCurve] = []
    family_probabilities: Dict[str, float] | None = None
    y_max = 0.0
    for index, label in enumerate(labels):
        family, probabilities = _resolve_density_family(params, rng=rng)
        family_probabilities = dict(probabilities)
        raw_values, component_count, _components = _density_values_for_family(rng, family=str(family), xs=xs)
        total = max(1e-9, _integral(xs, raw_values))
        ys = tuple(float(value) / total for value in raw_values)
        mean_x, mode_x, mode_y, interval_mass, density_at_x = _curve_metrics(
            xs,
            ys,
            interval_start=float(interval_start),
            interval_end=float(interval_end),
            reference_x=float(reference_x),
        )
        y_max = max(float(y_max), max(float(value) for value in ys))
        style = str(weighted_choice(rng, style_probabilities, sort_keys=True))
        curves.append(
            _DensityCurve(
                label=str(label),
                color_rgb=tuple(int(channel) for channel in palette[int(index) % len(palette)]),
                line_style=str(style),
                family=str(family),
                component_count=int(component_count),
                points=tuple(_CurvePoint(x_value=float(x), y_value=float(y)) for x, y in zip(xs, ys)),
                mean_x=float(mean_x),
                mode_x=float(mode_x),
                mode_y=float(mode_y),
                interval_mass=float(interval_mass),
                density_at_x=float(density_at_x),
            )
        )

    answer_label = _winner_for_query(str(prompt_key), curves)
    gap = _winner_gap_for_query(str(prompt_key), curves)
    if float(gap) < float(_min_gap_for_query(str(prompt_key), params)):
        raise ValueError("density-curve sampled metrics did not satisfy winner-gap constraints")
    annotation_key = (
        "answer_mean_marker"
        if str(prompt_key) in _MEAN_PROMPT_KEYS
        else "answer_mode_marker"
        if str(prompt_key) in _MODE_PROMPT_KEYS
        else "answer_interval_mass"
        if str(prompt_key) in _INTERVAL_PROMPT_KEYS
        else "answer_density_at_x"
    )
    metric_by_label = {
        "mean_x_by_label": {str(curve.label): round(float(curve.mean_x), 4) for curve in curves},
        "mode_x_by_label": {str(curve.label): round(float(curve.mode_x), 4) for curve in curves},
        "interval_mass_by_label": {str(curve.label): round(float(curve.interval_mass), 6) for curve in curves},
        "density_at_x_by_label": {str(curve.label): round(float(curve.density_at_x), 8) for curve in curves},
    }
    query_trace = {
        "prompt_key": str(prompt_key),
        "answer": str(answer_label),
        "annotation_key": str(annotation_key),
        "curve_count": int(curve_count),
        "curve_count_range": [int(_gen_int(params, "density_curve_count_min", 4)), int(_gen_int(params, "density_curve_count_max", 7))],
        "curve_count_probabilities": dict(curve_count_probabilities),
        "density_family_probabilities": dict(family_probabilities or {}),
        "prompt_key_probabilities": dict(prompt_key_probabilities),
        "winner_gap": round(float(gap), 6),
        "x_range": [round(float(x_min), 3), round(float(x_max), 3)],
        "x_grid_size": int(grid_size),
        "interval_start": round(float(interval_start), 3),
        "interval_end": round(float(interval_end), 3),
        "interval_label": f"{interval_start:.0f}-{interval_end:.0f}",
        "reference_x": round(float(reference_x), 3),
        "reference_x_label": f"{reference_x:.0f}",
        "labels": list(labels),
        "families_by_label": {str(curve.label): str(curve.family) for curve in curves},
        "component_count_by_label": {str(curve.label): int(curve.component_count) for curve in curves},
        "line_style_by_label": {str(curve.label): str(curve.line_style) for curve in curves},
        "label_resolution": {
            key: list(value) if isinstance(value, tuple) else dict(value) if isinstance(value, Mapping) else value
            for key, value in dict(labels_resolution.__dict__).items()
        },
        **metric_by_label,
    }
    return _Dataset(
        curves=tuple(curves),
        query=_Query(
            prompt_key=str(prompt_key),
            answer_label=str(answer_label),
            annotation_key=str(annotation_key),
            interval_start=float(interval_start),
            interval_end=float(interval_end),
            reference_x=float(reference_x),
            trace=dict(query_trace),
        ),
        x_min=float(x_min),
        x_max=float(x_max),
        y_max=float(max(1e-9, y_max)),
        curve_count=int(curve_count),
        label_resolution=labels_resolution,
    )


def _value_to_px(plot_bbox: Sequence[float], *, x_value: float, y_value: float, x_min: float, x_max: float, y_max: float) -> Tuple[float, float]:
    px0, py0, px1, py1 = [float(value) for value in plot_bbox[:4]]
    x_unit = (float(x_value) - float(x_min)) / max(1e-9, float(x_max) - float(x_min))
    y_unit = float(y_value) / max(1e-9, float(y_max))
    return px0 + max(0.0, min(1.0, x_unit)) * (px1 - px0), py1 - max(0.0, min(1.0, y_unit)) * (py1 - py0)


def _draw_polyline(draw: ImageDraw.ImageDraw, points: Sequence[Tuple[float, float]], *, fill: RGB, width: int, style: str) -> None:
    if len(points) < 2:
        return
    if str(style) == "solid":
        draw.line(tuple(points), fill=tuple(fill) + (255,), width=int(width), joint="curve")
        return
    if str(style) == "dot":
        radius = max(1.4, float(width) * 0.55)
        for index, point in enumerate(points):
            if index % 4 != 0:
                continue
            x, y = float(point[0]), float(point[1])
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=tuple(fill) + (255,))
        return
    chunk = 6
    for start in range(0, len(points) - 1, chunk * 2):
        segment = points[start : min(len(points), start + chunk)]
        if len(segment) >= 2:
            draw.line(tuple(segment), fill=tuple(fill) + (255,), width=int(width), joint="curve")


def _curve_points_px(curve: _DensityCurve, plot_bbox: Sequence[float], *, x_min: float, x_max: float, y_max: float) -> Tuple[Tuple[float, float], ...]:
    return tuple(_value_to_px(plot_bbox, x_value=point.x_value, y_value=point.y_value, x_min=x_min, x_max=x_max, y_max=y_max) for point in curve.points)


def _curve_bbox(points: Sequence[Tuple[float, float]], *, pad: float = 3.0) -> BBox:
    if not points:
        return []
    return _bbox((min(x for x, _y in points) - pad, min(y for _x, y in points) - pad, max(x for x, _y in points) + pad, max(y for _x, y in points) + pad))


def _clip_bbox_to_container(bbox: Sequence[float], container: Sequence[float]) -> BBox:
    if len(bbox) < 4 or len(container) < 4:
        return []
    x0, y0, x1, y1 = [float(value) for value in bbox[:4]]
    cx0, cy0, cx1, cy1 = [float(value) for value in container[:4]]
    return _bbox((max(cx0, x0), max(cy0, y0), min(cx1, x1), min(cy1, y1)))


def _render_density_curve_scene(
    image: Image.Image,
    *,
    dataset: _Dataset,
    render_params,
) -> _Rendered:
    draw = ImageDraw.Draw(image, "RGBA")
    title_font = load_font(max(12, int(render_params.label_font_size_px) + 4))
    label_font = load_font(int(render_params.label_font_size_px))
    tick_font = load_font(int(render_params.tick_font_size_px))
    legend_font = load_font(max(10, int(render_params.tick_font_size_px) + 1))
    plot_bbox = _bbox(
        (
            int(render_params.plot_margin_left_px),
            int(render_params.plot_margin_top_px),
            int(render_params.canvas_width) - int(render_params.plot_margin_right_px),
            int(render_params.canvas_height) - int(render_params.plot_margin_bottom_px),
        )
    )
    px0, py0, px1, py1 = [float(value) for value in plot_bbox]
    draw.rectangle(plot_bbox, fill=tuple(render_params.plot_fill_rgb) + (255,), outline=tuple(render_params.axis_color_rgb) + (255,), width=1)

    y_scale_max = float(dataset.y_max) * 1.16
    for tick in (0, 25, 50, 75, 100):
        x_tick, _ = _value_to_px(plot_bbox, x_value=float(tick), y_value=0.0, x_min=dataset.x_min, x_max=dataset.x_max, y_max=y_scale_max)
        draw.line((x_tick, py0, x_tick, py1), fill=tuple(render_params.grid_color_rgb) + (255,), width=int(render_params.grid_line_width_px))
        draw.line((x_tick, py1, x_tick, py1 + int(render_params.tick_length_px)), fill=tuple(render_params.axis_color_rgb) + (255,), width=int(render_params.axis_line_width_px))
        draw_text_traced(draw, (x_tick, py1 + 8.0), str(tick), font=tick_font, fill=render_params.text_color_rgb, stroke_fill=render_params.text_stroke_rgb, stroke_width=1, anchor="ma", role="axis_tick", required=False)
    for frac, label in ((0.25, "low"), (0.5, "mid"), (0.75, "high")):
        y_tick = py1 - float(frac) * (py1 - py0)
        draw.line((px0, y_tick, px1, y_tick), fill=tuple(render_params.grid_color_rgb) + (255,), width=int(render_params.grid_line_width_px))
        draw_text_traced(draw, (px0 - 8.0, y_tick), str(label), font=tick_font, fill=render_params.text_color_rgb, stroke_fill=render_params.text_stroke_rgb, stroke_width=1, anchor="rm", role="axis_tick", required=False)

    interval_start_px, _ = _value_to_px(plot_bbox, x_value=dataset.query.interval_start, y_value=0.0, x_min=dataset.x_min, x_max=dataset.x_max, y_max=y_scale_max)
    interval_end_px, _ = _value_to_px(plot_bbox, x_value=dataset.query.interval_end, y_value=0.0, x_min=dataset.x_min, x_max=dataset.x_max, y_max=y_scale_max)
    if dataset.query.prompt_key in _INTERVAL_PROMPT_KEYS:
        draw.rectangle((interval_start_px, py0, interval_end_px, py1), fill=(90, 110, 135, 34), outline=(90, 110, 135, 100), width=1)
        draw_text_traced(draw, ((interval_start_px + interval_end_px) / 2.0, py0 + 6.0), f"range {dataset.query.trace['interval_label']}", font=tick_font, fill=render_params.text_color_rgb, stroke_fill=render_params.text_stroke_rgb, stroke_width=1, anchor="ma", role="readout", required=False)

    curve_bboxes: Dict[str, BBox] = {}
    mean_marker_bboxes: Dict[str, BBox] = {}
    mode_marker_bboxes: Dict[str, BBox] = {}
    interval_mass_bboxes: Dict[str, BBox] = {}
    density_at_x_points: Dict[str, List[float]] = {}
    entities: list[Dict[str, Any]] = []

    curve_points_by_label = {
        str(curve.label): _curve_points_px(curve, plot_bbox, x_min=dataset.x_min, x_max=dataset.x_max, y_max=y_scale_max)
        for curve in dataset.curves
    }

    if dataset.query.prompt_key in _INTERVAL_PROMPT_KEYS:
        for curve in dataset.curves:
            points = curve_points_by_label[str(curve.label)]
            area_points = [(interval_start_px, py1)]
            area_points.extend(
                point
                for point, source in zip(points, curve.points)
                if float(dataset.query.interval_start) <= float(source.x_value) <= float(dataset.query.interval_end)
            )
            area_points.append((interval_end_px, py1))
            if len(area_points) >= 3:
                draw.polygon(tuple(area_points), fill=tuple(curve.color_rgb) + (34,))
                interval_mass_bboxes[str(curve.label)] = _clip_bbox_to_container(_curve_bbox(area_points, pad=2.0), plot_bbox)

    reference_x_px, _ = _value_to_px(plot_bbox, x_value=dataset.query.reference_x, y_value=0.0, x_min=dataset.x_min, x_max=dataset.x_max, y_max=y_scale_max)
    if dataset.query.prompt_key in _DENSITY_AT_X_PROMPT_KEYS:
        draw.line((reference_x_px, py0, reference_x_px, py1), fill=tuple(render_params.axis_color_rgb) + (130,), width=max(1, int(render_params.guide_line_width_px)))
        draw_text_traced(draw, (reference_x_px, py0 + 6.0), f"x = {dataset.query.trace['reference_x_label']}", font=tick_font, fill=render_params.text_color_rgb, stroke_fill=render_params.text_stroke_rgb, stroke_width=1, anchor="ma", role="readout", required=False)

    for curve in dataset.curves:
        points = curve_points_by_label[str(curve.label)]
        _draw_polyline(draw, points, fill=curve.color_rgb, width=int(render_params.line_width_px), style=str(curve.line_style))
        curve_bboxes[str(curve.label)] = _curve_bbox(points, pad=3.0)

    if dataset.query.prompt_key in _MEAN_PROMPT_KEYS:
        for curve in dataset.curves:
            x_px, _ = _value_to_px(plot_bbox, x_value=curve.mean_x, y_value=0.0, x_min=dataset.x_min, x_max=dataset.x_max, y_max=y_scale_max)
            marker = (x_px - 6.0, py1 + 14.0, x_px, py1 + 2.0, x_px + 6.0, py1 + 14.0)
            draw.polygon(marker, fill=tuple(curve.color_rgb) + (255,), outline=tuple(render_params.text_stroke_rgb) + (255,))
            draw.line((x_px, py1, x_px, py0), fill=tuple(curve.color_rgb) + (84,), width=max(1, int(render_params.guide_line_width_px)))
            mean_marker_bboxes[str(curve.label)] = _bbox((x_px - 7.0, py1 + 1.0, x_px + 7.0, py1 + 15.0))

    if dataset.query.prompt_key in _MODE_PROMPT_KEYS:
        for curve in dataset.curves:
            x_px, y_px = _value_to_px(plot_bbox, x_value=curve.mode_x, y_value=curve.mode_y, x_min=dataset.x_min, x_max=dataset.x_max, y_max=y_scale_max)
            radius = max(5.0, float(render_params.point_radius_px))
            draw.ellipse((x_px - radius, y_px - radius, x_px + radius, y_px + radius), fill=tuple(curve.color_rgb) + (255,), outline=tuple(render_params.text_stroke_rgb) + (255,), width=2)
            mode_marker_bboxes[str(curve.label)] = _bbox((x_px - radius, y_px - radius, x_px + radius, y_px + radius))

    if dataset.query.prompt_key in _DENSITY_AT_X_PROMPT_KEYS:
        radius = max(4.5, float(render_params.point_radius_px) * 0.85)
        for curve in dataset.curves:
            x_px, y_px = _value_to_px(plot_bbox, x_value=dataset.query.reference_x, y_value=curve.density_at_x, x_min=dataset.x_min, x_max=dataset.x_max, y_max=y_scale_max)
            draw.ellipse((x_px - radius, y_px - radius, x_px + radius, y_px + radius), fill=tuple(curve.color_rgb) + (255,), outline=tuple(render_params.text_stroke_rgb) + (255,), width=2)
            density_at_x_points[str(curve.label)] = [round(float(x_px), 3), round(float(y_px), 3)]

    title_record = draw_text_traced(
        draw,
        ((px0 + px1) / 2.0, max(24.0, py0 - 28.0)),
        "Density curve comparison",
        font=title_font,
        fill=render_params.text_color_rgb,
        stroke_fill=render_params.text_stroke_rgb,
        stroke_width=1,
        anchor="mm",
        role="readout",
        required=False,
    )
    draw_text_traced(draw, ((px0 + px1) / 2.0, py1 + 44.0), "x value", font=label_font, fill=render_params.text_color_rgb, stroke_fill=render_params.text_stroke_rgb, stroke_width=1, anchor="mm", role="chart_label", required=False)
    draw_text_traced(draw, (px0, py0 - 10.0), "density", font=label_font, fill=render_params.text_color_rgb, stroke_fill=render_params.text_stroke_rgb, stroke_width=1, anchor="ls", role="chart_label", required=False)

    legend_x0 = px1 + 18.0
    legend_y0 = py0 + 8.0
    legend_x1 = float(render_params.canvas_width) - 18.0
    row_h = max(24.0, float(render_params.tick_font_size_px) + 8.0)
    legend_y1 = min(py1, legend_y0 + (row_h * float(len(dataset.curves))) + 16.0)
    legend_bbox = _bbox((legend_x0, legend_y0, legend_x1, legend_y1))
    draw.rectangle(legend_bbox, fill=tuple(render_params.plot_fill_rgb) + (210,), outline=tuple(render_params.grid_color_rgb) + (255,), width=1)
    legend_items: Dict[str, BBox] = {}
    for index, curve in enumerate(dataset.curves):
        row_y = legend_y0 + 12.0 + (float(index) * row_h)
        draw.line((legend_x0 + 10.0, row_y + 7.0, legend_x0 + 42.0, row_y + 7.0), fill=tuple(curve.color_rgb) + (255,), width=max(3, int(render_params.line_width_px)))
        label_record = draw_text_traced(draw, (legend_x0 + 50.0, row_y), str(curve.label), font=legend_font, fill=render_params.text_color_rgb, stroke_fill=render_params.text_stroke_rgb, stroke_width=1, anchor="la", role="legend_label", required=True)
        legend_items[str(curve.label)] = list(label_record["bbox_px"])

    for curve in dataset.curves:
        entities.append(
            {
                "entity_id": f"curve:{curve.label}",
                "entity_type": "density_curve",
                "label": str(curve.label),
                "family": str(curve.family),
                "component_count": int(curve.component_count),
                "color_rgb": [int(channel) for channel in curve.color_rgb],
                "line_style": str(curve.line_style),
                "bbox_px": list(curve_bboxes[str(curve.label)]),
                "mean_marker_bbox_px": list(mean_marker_bboxes.get(str(curve.label), [])),
                "mode_marker_bbox_px": list(mode_marker_bboxes.get(str(curve.label), [])),
                "interval_mass_bbox_px": list(interval_mass_bboxes.get(str(curve.label), [])),
                "density_at_x_point_px": list(density_at_x_points.get(str(curve.label), [])),
            }
        )

    return _Rendered(
        image=image,
        entities=tuple(entities),
        plot_bbox_px=list(plot_bbox),
        legend_bbox_px=list(legend_bbox),
        legend_item_bboxes_px=dict(legend_items),
        curve_bboxes_px=dict(curve_bboxes),
        mean_marker_bboxes_px=dict(mean_marker_bboxes),
        mode_marker_bboxes_px=dict(mode_marker_bboxes),
        interval_mass_bboxes_px=dict(interval_mass_bboxes),
        density_at_x_points_px=dict(density_at_x_points),
        title_bbox_px=list(title_record["bbox_px"]),
        render_meta={
            "y_scale_max": round(float(y_scale_max), 8),
            "interval_visible": bool(dataset.query.prompt_key in _INTERVAL_PROMPT_KEYS),
            "mean_markers_visible": bool(dataset.query.prompt_key in _MEAN_PROMPT_KEYS),
            "mode_markers_visible": bool(dataset.query.prompt_key in _MODE_PROMPT_KEYS),
            "density_at_x_markers_visible": bool(dataset.query.prompt_key in _DENSITY_AT_X_PROMPT_KEYS),
        },
    )


def build_density_curve_dataset(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    prompt_key: str,
    render_params: Any,
) -> _Dataset:
    return _build_dataset(
        params,
        instance_seed=int(instance_seed),
        prompt_key=str(prompt_key),
        prompt_key_probabilities={},
        render_params=render_params,
    )


def render_density_curve_scene(
    image: Image.Image,
    *,
    dataset: _Dataset,
    render_params: Any,
) -> _Rendered:
    return _render_density_curve_scene(image, dataset=dataset, render_params=render_params)


def resolve_density_curve_render_params(params: Mapping[str, Any], *, instance_seed: int) -> Any:
    return resolve_chart_render_params_for_task(
        params,
        render_defaults=_RENDER_DEFAULTS,
        defaults=_RENDER_DEFAULTS_FALLBACK,
        instance_seed=int(instance_seed),
    )


def density_curve_count_bounds(params: Mapping[str, Any]) -> Tuple[int, int]:
    return (
        int(_gen_int(params, "density_curve_count_min", 4)),
        int(_gen_int(params, "density_curve_count_max", 7)),
    )


