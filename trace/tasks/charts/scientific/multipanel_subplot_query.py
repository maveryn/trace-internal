"""Scientific multi-panel subplot query task."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import bbox_union_raw as _bbox_union
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_rgb
from ...shared.text_rendering import load_font
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_curve_panels_subplot_query_base"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "curve_at_x_extremum_label",
    "threshold_series_count",
    "cross_panel_delta_extremum_label",
    "curve_intersection_count",
    "earliest_maximum_panel_label",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("multipanel_line_grid",)

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "scientific")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="scientific")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="scientific", apply_prob=0.0)

_PANEL_LABELS: Tuple[str, ...] = tuple("ABCDEFGHI")
_METHOD_LABELS: Tuple[str, ...] = ("M1", "M2", "M3", "M4", "M5", "M6")
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "curve_at_x_extremum_label": 0.54,
    "threshold_series_count": 0.58,
    "cross_panel_delta_extremum_label": 0.78,
    "curve_intersection_count": 0.72,
    "earliest_maximum_panel_label": 0.76,
}
_SCENE_LOAD_BY_VARIANT: Dict[str, float] = {"multipanel_line_grid": 0.82}

RGB = Tuple[int, int, int]
BBox = Tuple[float, float, float, float]


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
class _Curve:
    method_label: str
    values: Tuple[int, ...]
    color_rgb: RGB


@dataclass(frozen=True)
class _Panel:
    panel_label: str
    curves: Tuple[_Curve, ...]


@dataclass(frozen=True)
class _Intersection:
    intersection_id: str
    panel_label: str
    method_a_label: str
    method_b_label: str
    x_value: float
    y_value: float


@dataclass(frozen=True)
class _Query:
    query_id: str
    scene_variant: str
    answer: str | int
    answer_type: str
    panel_label: str
    method_label: str
    method_a_label: str
    method_b_label: str
    x_value: int
    start_x_value: int
    end_x_value: int
    threshold_value: int
    evidence_panel_labels: Tuple[str, ...]
    evidence_point_ids: Tuple[str, ...]
    evidence_intersection_ids: Tuple[str, ...]
    trace: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    scene_variant: str
    x_values: Tuple[int, ...]
    y_min: int
    y_max: int
    panels: Tuple[_Panel, ...]
    query: _Query
    intersections: Tuple[_Intersection, ...]


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: List[float]
    panel_bboxes: Dict[str, List[float]]
    panel_plot_bboxes: Dict[str, List[float]]
    point_bboxes: Dict[str, List[float]]
    intersection_bboxes: Dict[str, List[float]]
    legend_bboxes: Dict[str, List[float]]
    render_meta: Dict[str, Any]


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _text_bbox(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    *,
    stroke_width: int = 0,
) -> List[float]:
    try:
        box = draw.textbbox((float(xy[0]), float(xy[1])), str(text), font=font, stroke_width=max(0, int(stroke_width)))
        return _bbox(box)
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        return _bbox([float(xy[0]), float(xy[1]), float(xy[0]) + float(width), float(xy[1]) + float(height)])


def _center_text(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill: RGB,
    stroke_fill: RGB = (255, 255, 255),
    stroke_width: int = 0,
) -> List[float]:
    try:
        box = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width)))
        width = float(box[2] - box[0])
        height = float(box[3] - box[1])
        x = float(center[0]) - (0.5 * width) - float(box[0])
        y = float(center[1]) - (0.5 * height) - float(box[1])
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        x = float(center[0]) - (0.5 * float(width))
        y = float(center[1]) - (0.5 * float(height))
    draw.text(
        (float(x), float(y)),
        str(text),
        font=font,
        fill=fill,
        stroke_fill=stroke_fill,
        stroke_width=max(0, int(stroke_width)),
    )
    return _text_bbox(draw, (float(x), float(y)), str(text), font, stroke_width=max(0, int(stroke_width)))


def _as_rgb(value: Any, fallback: RGB) -> RGB:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 3:
        return tuple(int(channel) for channel in fallback)
    return tuple(max(0, min(255, int(channel))) for channel in value[:3])  # type: ignore[index]


def _resolve_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), _RENDER_DEFAULTS.get(str(key), int(fallback))))


def _render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


def _resolve_rgb(params: Mapping[str, Any], key: str, fallback: RGB) -> RGB:
    return resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        str(key),
        fallback,
        instance_seed=_render_style_seed(params),
        namespace=TASK_ID,
    )


def _gen_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), int(fallback))))


def _without_sample_cursor(params: Mapping[str, Any]) -> Dict[str, Any]:
    copied = dict(params)
    copied.pop("_sample_cursor", None)
    return copied


def _choice_index(params: Mapping[str, Any], *, instance_seed: int, namespace: str) -> int:
    return int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace)))


def _balanced_choice(values: Sequence[Any], params: Mapping[str, Any], *, instance_seed: int, namespace: str) -> Any:
    support = list(values)
    if not support:
        raise ValueError(f"empty support for {namespace}")
    index = _choice_index(params, instance_seed=int(instance_seed), namespace=str(namespace))
    return support[int(index) % len(support)]


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_QUERY_IDS,
        task_id=TASK_ID,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def _uses_uniform_query_id_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> bool:
    if params.get("query_id") is not None or params.get("query_id_weights") is not None:
        return False
    positives = [float(value) for value in query_id_probabilities.values() if float(value) > 0.0]
    if len(positives) != len(SUPPORTED_QUERY_IDS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _support_sampling_params(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    support_params = dict(params)
    sampling_index = support_params.get("_sample_cursor")
    if sampling_index is None:
        return support_params
    if not _uses_uniform_query_id_cycle(params, query_id_probabilities=query_id_probabilities):
        return support_params
    support_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_QUERY_IDS))
    return support_params


def _palette(params: Mapping[str, Any]) -> Tuple[RGB, ...]:
    raw = params.get("method_palette_rgb", _RENDER_DEFAULTS.get("method_palette_rgb", ()))
    colors: List[RGB] = []
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        for item in raw:
            if isinstance(item, Sequence) and not isinstance(item, (str, bytes)) and len(item) >= 3:
                colors.append(_as_rgb(item, (0, 0, 0)))
    return tuple(colors) if colors else (
        (39, 105, 176),
        (203, 79, 72),
        (52, 145, 98),
        (138, 91, 184),
        (211, 139, 44),
        (48, 147, 168),
    )


def _panel_count(params: Mapping[str, Any], *, instance_seed: int, min_required: int = 4) -> int:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="panel_count_min",
        max_key="panel_count_max",
        fallback_min=6,
        fallback_max=8,
        context=f"generation defaults for {TASK_ID}",
    )
    low = max(4, int(min_required), int(low))
    high = min(len(_PANEL_LABELS), int(high))
    if int(low) > int(high):
        raise ValueError("panel_count support is empty")
    return int(
        _balanced_choice(
            list(range(int(low), int(high) + 1)),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.panel_count",
        )
    )


def _panel_answer_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    _low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="panel_count_min",
        max_key="panel_count_max",
        fallback_min=6,
        fallback_max=8,
        context=f"generation defaults for {TASK_ID}",
    )
    high = min(len(_PANEL_LABELS), max(4, int(high)))
    return tuple(_PANEL_LABELS[: int(high)])


def _method_count(params: Mapping[str, Any], *, instance_seed: int, min_required: int = 3) -> int:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="method_count_min",
        max_key="method_count_max",
        fallback_min=5,
        fallback_max=5,
        context=f"generation defaults for {TASK_ID}",
    )
    low = max(3, int(min_required), int(low))
    high = min(len(_METHOD_LABELS), int(high))
    if int(low) > int(high):
        raise ValueError("method_count support is empty")
    return int(
        _balanced_choice(
            list(range(int(low), int(high) + 1)),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.method_count",
        )
    )


def _method_count_max(params: Mapping[str, Any]) -> int:
    _low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="method_count_min",
        max_key="method_count_max",
        fallback_min=5,
        fallback_max=5,
        context=f"generation defaults for {TASK_ID}",
    )
    return min(len(_METHOD_LABELS), max(3, int(high)))


def _x_values(params: Mapping[str, Any], *, instance_seed: int, min_required: int = 4) -> Tuple[int, ...]:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="x_tick_count_min",
        max_key="x_tick_count_max",
        fallback_min=6,
        fallback_max=12,
        context=f"generation defaults for {TASK_ID}",
    )
    low = max(4, int(min_required), int(low))
    high = max(int(low), int(high))
    count = int(
        _balanced_choice(
            list(range(int(low), int(high) + 1)),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.x_tick_count",
        )
    )
    step_min = int(_gen_int(params, "x_step_min", 5))
    step_max = int(_gen_int(params, "x_step_max", 20))
    span_min = int(_gen_int(params, "x_span_min", 50))
    span_max = int(_gen_int(params, "x_span_max", 100))
    if int(step_min) > int(step_max):
        raise ValueError("x_step_min must be <= x_step_max")
    if int(span_min) > int(span_max):
        raise ValueError("x_span_min must be <= x_span_max")
    step_support = [
        int(step)
        for step in range(max(1, int(step_min)), int(step_max) + 1)
        if int(span_min) <= int(step) * max(1, int(count) - 1) <= int(span_max)
    ]
    if not step_support:
        raise ValueError("x step/span support is empty for sampled x_tick_count")
    step = int(
        _balanced_choice(
            step_support,
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.x_step:{int(count)}",
        )
    )
    return tuple(int(index) * int(step) for index in range(int(count)))


def _threshold_values(params: Mapping[str, Any]) -> Tuple[int, ...]:
    raw = params.get("threshold_values", _GEN_DEFAULTS.get("threshold_values", (45, 55, 65)))
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        values = tuple(int(value) for value in raw)
        if values:
            return values
    return (45, 55, 65)


def _threshold_for_x_values(params: Mapping[str, Any], *, instance_seed: int, x_values: Sequence[int]) -> int:
    support = tuple(value for value in _threshold_values(params) if 10 <= int(value) <= 90)
    if not support:
        support = (45, 55, 65)
    return int(
        _balanced_choice(
            support,
            _without_sample_cursor(params),
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.threshold:{len(x_values)}:{int(max(x_values)) if x_values else 0}",
        )
    )


def _point_id(panel_label: str, method_label: str, x_value: int) -> str:
    return f"{str(panel_label)}|{str(method_label)}|{int(x_value)}"


def _intersection_id(panel_label: str, method_a_label: str, method_b_label: str, index: int) -> str:
    return f"{str(panel_label)}|{str(method_a_label)}|{str(method_b_label)}|intersection:{int(index)}"


def _random_curve_values(*, rng: Any, count: int, value_min: int, value_max: int) -> List[int]:
    current = int(rng.randint(28, 72))
    values: List[int] = []
    for _ in range(int(count)):
        current += int(rng.randint(-15, 15))
        current = max(int(value_min) + 8, min(int(value_max) - 8, int(current)))
        values.append(int(current))
    return values


def _make_random_panels(
    *,
    panel_labels: Sequence[str],
    method_labels: Sequence[str],
    x_count: int,
    colors: Sequence[RGB],
    instance_seed: int,
    namespace: str,
    value_min: int,
    value_max: int,
) -> Dict[str, Dict[str, List[int]]]:
    values: Dict[str, Dict[str, List[int]]] = {}
    for panel in panel_labels:
        values[str(panel)] = {}
        for method in method_labels:
            rng = spawn_rng(int(instance_seed), f"{str(namespace)}:{str(panel)}:{str(method)}")
            values[str(panel)][str(method)] = _random_curve_values(
                rng=rng,
                count=int(x_count),
                value_min=int(value_min),
                value_max=int(value_max),
            )
    return values


def _panels_from_values(
    *,
    values_by_panel_method: Mapping[str, Mapping[str, Sequence[int]]],
    panel_labels: Sequence[str],
    method_labels: Sequence[str],
    colors: Sequence[RGB],
) -> Tuple[_Panel, ...]:
    panels: List[_Panel] = []
    for panel in panel_labels:
        curves: List[_Curve] = []
        for index, method in enumerate(method_labels):
            curves.append(
                _Curve(
                    method_label=str(method),
                    values=tuple(int(value) for value in values_by_panel_method[str(panel)][str(method)]),
                    color_rgb=tuple(colors[int(index) % len(colors)]),
                )
            )
        panels.append(_Panel(panel_label=str(panel), curves=tuple(curves)))
    return tuple(panels)


def _common_axes(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    min_x_tick_count: int = 4,
) -> Tuple[Tuple[int, ...], int, int, int, Tuple[str, ...], Tuple[str, ...]]:
    non_answer_params = _without_sample_cursor(params)
    panel_count = _panel_count(non_answer_params, instance_seed=int(instance_seed))
    method_count = _method_count(non_answer_params, instance_seed=int(instance_seed))
    x_values = _x_values(
        non_answer_params,
        instance_seed=int(instance_seed),
        min_required=int(min_x_tick_count),
    )
    y_min = int(_gen_int(params, "y_value_min", 0))
    y_max = int(_gen_int(params, "y_value_max", 100))
    if int(y_min) >= int(y_max):
        raise ValueError("y_value_min must be lower than y_value_max")
    return (
        tuple(x_values),
        int(y_min),
        int(y_max),
        int(panel_count),
        tuple(_PANEL_LABELS[: int(panel_count)]),
        tuple(_METHOD_LABELS[: int(method_count)]),
    )


def _build_curve_at_x_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    non_answer_params = _without_sample_cursor(params)
    answer_method = str(
        _balanced_choice(
            _METHOD_LABELS,
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.curve_at_x.answer",
        )
    )
    min_method_count = max(3, int(_METHOD_LABELS.index(str(answer_method))) + 1)
    panel_count = _panel_count(non_answer_params, instance_seed=int(instance_seed))
    method_count = _method_count(non_answer_params, instance_seed=int(instance_seed), min_required=int(min_method_count))
    x_values = _x_values(non_answer_params, instance_seed=int(instance_seed))
    y_min = int(_gen_int(params, "y_value_min", 0))
    y_max = int(_gen_int(params, "y_value_max", 100))
    if int(y_min) >= int(y_max):
        raise ValueError("y_value_min must be lower than y_value_max")
    panel_labels = tuple(_PANEL_LABELS[: int(panel_count)])
    method_labels = tuple(_METHOD_LABELS[: int(method_count)])
    colors = _palette(params)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.curve_at_x")
    query_panel = str(
        _balanced_choice(panel_labels, non_answer_params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.curve_at_x.panel")
    )
    x_index = 1 + int(rng.randint(0, max(1, len(x_values) - 3)))
    x_value = int(x_values[int(x_index)])
    values = _make_random_panels(
        panel_labels=panel_labels,
        method_labels=method_labels,
        x_count=len(x_values),
        colors=colors,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.curve_at_x.values",
        value_min=y_min,
        value_max=y_max,
    )
    winner_min = int(_gen_int(params, "curve_at_x_winner_min", 82))
    winner_max = int(_gen_int(params, "curve_at_x_winner_max", 92))
    gap_min = max(1, int(_gen_int(params, "curve_at_x_gap_min", 24)))
    gap_max = max(int(gap_min), int(_gen_int(params, "curve_at_x_gap_max", 56)))
    winner_min = max(int(y_min) + int(gap_min) + 5, min(int(y_max) - 5, int(winner_min)))
    winner_max = max(int(winner_min), min(int(y_max) - 5, int(winner_max)))
    winning_value = int(rng.randint(int(winner_min), int(winner_max)))
    for index, method in enumerate(method_labels):
        if str(method) == str(answer_method):
            values[str(query_panel)][str(method)][int(x_index)] = int(winning_value)
        else:
            gap = int(rng.randint(int(gap_min), int(gap_max)))
            values[str(query_panel)][str(method)][int(x_index)] = max(
                int(y_min) + 5,
                min(int(y_max) - 5, int(winning_value) - int(gap)),
            )

    evidence_ids = tuple(_point_id(str(query_panel), str(method), int(x_value)) for method in method_labels)
    query = _Query(
        query_id="curve_at_x_extremum_label",
        scene_variant="multipanel_line_grid",
        answer=str(answer_method),
        answer_type="string",
        panel_label=str(query_panel),
        method_label=str(answer_method),
        method_a_label="",
        method_b_label="",
        x_value=int(x_value),
        start_x_value=0,
        end_x_value=0,
        threshold_value=0,
        evidence_panel_labels=(str(query_panel),),
        evidence_point_ids=evidence_ids,
        evidence_intersection_ids=(),
        trace={
            "query_panel_label": str(query_panel),
            "query_x_value": int(x_value),
            "compared_method_labels": list(method_labels),
            "values_at_query_x": {
                str(method): int(values[str(query_panel)][str(method)][int(x_index)])
                for method in method_labels
            },
        },
    )
    return _Dataset(
        scene_variant="multipanel_line_grid",
        x_values=tuple(x_values),
        y_min=int(y_min),
        y_max=int(y_max),
        panels=_panels_from_values(values_by_panel_method=values, panel_labels=panel_labels, method_labels=method_labels, colors=colors),
        query=query,
        intersections=(),
    )


def _build_threshold_count_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    non_answer_params = _without_sample_cursor(params)
    target_count = int(
        _balanced_choice(
            list(range(1, _method_count_max(params) + 1)),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.threshold_count.answer",
        )
    )
    panel_count = _panel_count(non_answer_params, instance_seed=int(instance_seed))
    method_count = _method_count(non_answer_params, instance_seed=int(instance_seed), min_required=int(target_count))
    x_values = _x_values(non_answer_params, instance_seed=int(instance_seed))
    y_min = int(_gen_int(params, "y_value_min", 0))
    y_max = int(_gen_int(params, "y_value_max", 100))
    if int(y_min) >= int(y_max):
        raise ValueError("y_value_min must be lower than y_value_max")
    panel_labels = tuple(_PANEL_LABELS[: int(panel_count)])
    method_labels = tuple(_METHOD_LABELS[: int(method_count)])
    colors = _palette(params)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.threshold_count")
    query_panel = str(
        _balanced_choice(panel_labels, _without_sample_cursor(params), instance_seed=int(instance_seed), namespace=f"{TASK_ID}.threshold_count.panel")
    )
    x_index = 1 + int(rng.randint(0, max(1, len(x_values) - 3)))
    x_value = int(x_values[int(x_index)])
    threshold = _threshold_for_x_values(params, instance_seed=int(instance_seed), x_values=x_values)
    values = _make_random_panels(
        panel_labels=panel_labels,
        method_labels=method_labels,
        x_count=len(x_values),
        colors=colors,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.threshold_count.values",
        value_min=y_min,
        value_max=y_max,
    )
    shuffled_methods = list(method_labels)
    rng.shuffle(shuffled_methods)
    above_methods = set(str(method) for method in shuffled_methods[: int(target_count)])
    for method in method_labels:
        if str(method) in above_methods:
            values[str(query_panel)][str(method)][int(x_index)] = int(rng.randint(int(threshold) + 8, min(int(y_max) - 5, int(threshold) + 34)))
        else:
            values[str(query_panel)][str(method)][int(x_index)] = int(rng.randint(max(int(y_min) + 5, int(threshold) - 34), int(threshold) - 4))

    evidence_ids = tuple(
        _point_id(str(query_panel), str(method), int(x_value))
        for method in method_labels
        if str(method) in above_methods
    )
    query = _Query(
        query_id="threshold_series_count",
        scene_variant="multipanel_line_grid",
        answer=int(target_count),
        answer_type="integer",
        panel_label=str(query_panel),
        method_label="",
        method_a_label="",
        method_b_label="",
        x_value=int(x_value),
        start_x_value=0,
        end_x_value=0,
        threshold_value=int(threshold),
        evidence_panel_labels=(str(query_panel),),
        evidence_point_ids=evidence_ids,
        evidence_intersection_ids=(),
        trace={
            "query_panel_label": str(query_panel),
            "query_x_value": int(x_value),
            "threshold_value": int(threshold),
            "matching_method_labels": [str(method) for method in method_labels if str(method) in above_methods],
            "values_at_query_x": {
                str(method): int(values[str(query_panel)][str(method)][int(x_index)])
                for method in method_labels
            },
        },
    )
    return _Dataset(
        scene_variant="multipanel_line_grid",
        x_values=tuple(x_values),
        y_min=int(y_min),
        y_max=int(y_max),
        panels=_panels_from_values(values_by_panel_method=values, panel_labels=panel_labels, method_labels=method_labels, colors=colors),
        query=query,
        intersections=(),
    )


def _replace_curve_interval(
    curve_values: List[int],
    *,
    start_index: int,
    end_index: int,
    start_value: int,
    end_value: int,
    rng: Any,
    y_min: int,
    y_max: int,
) -> None:
    curve_values[int(start_index)] = int(start_value)
    curve_values[int(end_index)] = int(end_value)
    span = max(1, int(end_index) - int(start_index))
    for index in range(int(start_index) + 1, int(end_index)):
        alpha = float(index - int(start_index)) / float(span)
        base = (1.0 - alpha) * float(start_value) + alpha * float(end_value)
        curve_values[int(index)] = max(int(y_min) + 5, min(int(y_max) - 5, int(round(base + rng.randint(-4, 4)))))


def _build_cross_panel_delta_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    answer_panel = str(
        _balanced_choice(
            _panel_answer_support(params),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.cross_panel_delta.answer",
        )
    )
    non_answer_params = _without_sample_cursor(params)
    min_panel_count = max(4, int(_PANEL_LABELS.index(str(answer_panel))) + 1)
    panel_count = _panel_count(non_answer_params, instance_seed=int(instance_seed), min_required=int(min_panel_count))
    method_count = _method_count(non_answer_params, instance_seed=int(instance_seed))
    x_values = _x_values(non_answer_params, instance_seed=int(instance_seed))
    y_min = int(_gen_int(params, "y_value_min", 0))
    y_max = int(_gen_int(params, "y_value_max", 100))
    if int(y_min) >= int(y_max):
        raise ValueError("y_value_min must be lower than y_value_max")
    panel_labels = tuple(_PANEL_LABELS[: int(panel_count)])
    method_labels = tuple(_METHOD_LABELS[: int(method_count)])
    colors = _palette(params)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.cross_panel_delta")
    method_label = str(
        _balanced_choice(
            method_labels,
            _without_sample_cursor(params),
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.cross_panel_delta.method",
        )
    )
    max_start_index = max(1, len(x_values) - 3)
    start_index = int(rng.randint(1, int(max_start_index)))
    end_min = min(len(x_values) - 2, int(start_index) + 1)
    end_max = len(x_values) - 2
    if int(end_min) > int(end_max):
        raise RuntimeError("x value support is too small for cross-panel delta")
    end_index = int(rng.randint(int(end_min), int(end_max)))
    start_x = int(x_values[int(start_index)])
    end_x = int(x_values[int(end_index)])
    values = _make_random_panels(
        panel_labels=panel_labels,
        method_labels=method_labels,
        x_count=len(x_values),
        colors=colors,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.cross_panel_delta.values",
        value_min=y_min,
        value_max=y_max,
    )
    target_delta = int(42 + rng.randint(0, 12))
    deltas: Dict[str, int] = {}
    for panel_index, panel in enumerate(panel_labels):
        if str(panel) == str(answer_panel):
            start_value = int(rng.randint(18, 34))
            delta = int(target_delta)
        else:
            start_value = int(rng.randint(24, 56))
            delta = int(rng.randint(-12, int(target_delta) - 14))
        end_value = max(int(y_min) + 5, min(int(y_max) - 5, int(start_value) + int(delta)))
        actual_delta = int(end_value) - int(start_value)
        if str(panel) != str(answer_panel) and int(actual_delta) >= int(target_delta):
            end_value = int(start_value) + int(target_delta) - 14 - (int(panel_index) % 5)
            end_value = max(int(y_min) + 5, min(int(y_max) - 5, int(end_value)))
            actual_delta = int(end_value) - int(start_value)
        deltas[str(panel)] = int(actual_delta)
        _replace_curve_interval(
            values[str(panel)][str(method_label)],
            start_index=int(start_index),
            end_index=int(end_index),
            start_value=int(start_value),
            end_value=int(end_value),
            rng=rng,
            y_min=int(y_min),
            y_max=int(y_max),
        )
    if max(deltas, key=lambda label: (deltas[label], label)) != str(answer_panel):
        raise RuntimeError("cross-panel delta construction lost unique target")

    evidence_ids: List[str] = []
    for panel in panel_labels:
        evidence_ids.append(_point_id(str(panel), str(method_label), int(start_x)))
        evidence_ids.append(_point_id(str(panel), str(method_label), int(end_x)))
    query = _Query(
        query_id="cross_panel_delta_extremum_label",
        scene_variant="multipanel_line_grid",
        answer=str(answer_panel),
        answer_type="string",
        panel_label=str(answer_panel),
        method_label=str(method_label),
        method_a_label="",
        method_b_label="",
        x_value=0,
        start_x_value=int(start_x),
        end_x_value=int(end_x),
        threshold_value=0,
        evidence_panel_labels=(str(answer_panel),),
        evidence_point_ids=tuple(evidence_ids),
        evidence_intersection_ids=(),
        trace={
            "method_label": str(method_label),
            "start_x_value": int(start_x),
            "end_x_value": int(end_x),
            "deltas_by_panel": dict(deltas),
            "winning_panel_label": str(answer_panel),
        },
    )
    return _Dataset(
        scene_variant="multipanel_line_grid",
        x_values=tuple(x_values),
        y_min=int(y_min),
        y_max=int(y_max),
        panels=_panels_from_values(values_by_panel_method=values, panel_labels=panel_labels, method_labels=method_labels, colors=colors),
        query=query,
        intersections=(),
    )


def _build_intersection_curves(
    *,
    x_values: Sequence[int],
    target_count: int,
    instance_seed: int,
    namespace: str,
) -> Tuple[List[int], List[int], List[_Intersection]]:
    rng = spawn_rng(int(instance_seed), str(namespace))
    interval_count = len(x_values) - 1
    change_positions = list(range(1, int(interval_count) + 1))
    rng.shuffle(change_positions)
    change_set = set(int(position) for position in change_positions[: int(target_count)])
    signs: List[int] = []
    sign = 1
    for index in range(len(x_values)):
        if int(index) > 0 and int(index) in change_set:
            sign *= -1
        signs.append(int(sign))

    method_a: List[int] = []
    method_b: List[int] = []
    for index, sign_value in enumerate(signs):
        base = int(50 + rng.randint(-7, 7))
        magnitude = int(12 + rng.randint(0, 14))
        method_a.append(max(8, min(92, int(base) + (int(sign_value) * int(magnitude)))))
        method_b.append(max(8, min(92, int(base) - (int(sign_value) * int(magnitude)))))
    return method_a, method_b, []


def _intersection_points(
    *,
    panel_label: str,
    method_a_label: str,
    method_b_label: str,
    x_values: Sequence[int],
    values_a: Sequence[int],
    values_b: Sequence[int],
) -> Tuple[_Intersection, ...]:
    intersections: List[_Intersection] = []
    for index in range(len(x_values) - 1):
        d0 = float(values_a[int(index)] - values_b[int(index)])
        d1 = float(values_a[int(index) + 1] - values_b[int(index) + 1])
        if d0 == 0.0 or d1 == 0.0 or (d0 > 0) == (d1 > 0):
            continue
        t = abs(d0) / (abs(d0) + abs(d1))
        x0 = float(x_values[int(index)])
        x1 = float(x_values[int(index) + 1])
        y0 = float(values_a[int(index)])
        y1 = float(values_a[int(index) + 1])
        x_value = x0 + (t * (x1 - x0))
        y_value = y0 + (t * (y1 - y0))
        intersections.append(
            _Intersection(
                intersection_id=_intersection_id(str(panel_label), str(method_a_label), str(method_b_label), len(intersections)),
                panel_label=str(panel_label),
                method_a_label=str(method_a_label),
                method_b_label=str(method_b_label),
                x_value=float(x_value),
                y_value=float(y_value),
            )
        )
    return tuple(intersections)


def _build_intersection_count_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    x_values, y_min, y_max, _panel_count_value, panel_labels, method_labels = _common_axes(
        params,
        instance_seed=int(instance_seed),
        min_x_tick_count=5,
    )
    colors = _palette(params)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.intersection_count")
    query_panel = str(
        _balanced_choice(panel_labels, _without_sample_cursor(params), instance_seed=int(instance_seed), namespace=f"{TASK_ID}.intersection_count.panel")
    )
    method_a_label = str(method_labels[0])
    method_b_label = str(method_labels[1])
    target_count = int(
        _balanced_choice(
            list(range(0, 5)),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.intersection_count.answer",
        )
    )
    values = _make_random_panels(
        panel_labels=panel_labels,
        method_labels=method_labels,
        x_count=len(x_values),
        colors=colors,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.intersection_count.values",
        value_min=y_min,
        value_max=y_max,
    )
    method_a_values, method_b_values, _ = _build_intersection_curves(
        x_values=x_values,
        target_count=int(target_count),
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.intersection_count.curves",
    )
    values[str(query_panel)][str(method_a_label)] = list(method_a_values)
    values[str(query_panel)][str(method_b_label)] = list(method_b_values)
    intersections = _intersection_points(
        panel_label=str(query_panel),
        method_a_label=str(method_a_label),
        method_b_label=str(method_b_label),
        x_values=x_values,
        values_a=method_a_values,
        values_b=method_b_values,
    )
    if len(intersections) != int(target_count):
        raise RuntimeError("intersection construction drifted from target count")

    query = _Query(
        query_id="curve_intersection_count",
        scene_variant="multipanel_line_grid",
        answer=int(target_count),
        answer_type="integer",
        panel_label=str(query_panel),
        method_label="",
        method_a_label=str(method_a_label),
        method_b_label=str(method_b_label),
        x_value=0,
        start_x_value=0,
        end_x_value=0,
        threshold_value=0,
        evidence_panel_labels=(str(query_panel),),
        evidence_point_ids=(),
        evidence_intersection_ids=tuple(str(item.intersection_id) for item in intersections),
        trace={
            "query_panel_label": str(query_panel),
            "method_a_label": str(method_a_label),
            "method_b_label": str(method_b_label),
            "intersection_count": int(target_count),
            "intersection_points": [
                {"x_value": round(float(item.x_value), 3), "y_value": round(float(item.y_value), 3)}
                for item in intersections
            ],
        },
    )
    return _Dataset(
        scene_variant="multipanel_line_grid",
        x_values=tuple(x_values),
        y_min=int(y_min),
        y_max=int(y_max),
        panels=_panels_from_values(values_by_panel_method=values, panel_labels=panel_labels, method_labels=method_labels, colors=colors),
        query=query,
        intersections=tuple(intersections),
    )


def _build_earliest_maximum_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    answer_panel = str(
        _balanced_choice(
            _panel_answer_support(params),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.earliest_max.answer",
        )
    )
    non_answer_params = _without_sample_cursor(params)
    min_panel_count = max(4, int(_PANEL_LABELS.index(str(answer_panel))) + 1)
    panel_count = _panel_count(non_answer_params, instance_seed=int(instance_seed), min_required=int(min_panel_count))
    method_count = _method_count(non_answer_params, instance_seed=int(instance_seed))
    x_values = _x_values(non_answer_params, instance_seed=int(instance_seed))
    y_min = int(_gen_int(params, "y_value_min", 0))
    y_max = int(_gen_int(params, "y_value_max", 100))
    if int(y_min) >= int(y_max):
        raise ValueError("y_value_min must be lower than y_value_max")
    panel_labels = tuple(_PANEL_LABELS[: int(panel_count)])
    method_labels = tuple(_METHOD_LABELS[: int(method_count)])
    colors = _palette(params)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.earliest_max")
    method_label = str(
        _balanced_choice(
            method_labels,
            _without_sample_cursor(params),
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.earliest_max.method",
        )
    )
    values = _make_random_panels(
        panel_labels=panel_labels,
        method_labels=method_labels,
        x_count=len(x_values),
        colors=colors,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.earliest_max.values",
        value_min=y_min,
        value_max=y_max,
    )
    peak_indices: Dict[str, int] = {}
    for panel_index, panel in enumerate(panel_labels):
        if str(panel) == str(answer_panel):
            peak_index = 1
        else:
            peak_index = 2 + (int(panel_index) % max(1, len(x_values) - 3))
            peak_index = min(len(x_values) - 2, int(peak_index))
        peak_indices[str(panel)] = int(peak_index)
        peak_value = int(82 + rng.randint(0, 12))
        curve: List[int] = []
        for index in range(len(x_values)):
            distance = abs(int(index) - int(peak_index))
            value = int(peak_value) - (int(distance) * int(12 + rng.randint(0, 4))) - int(rng.randint(0, 5))
            curve.append(max(int(y_min) + 5, min(int(y_max) - 5, int(value))))
        curve[int(peak_index)] = int(peak_value)
        values[str(panel)][str(method_label)] = list(curve)

    evidence_ids = tuple(
        _point_id(str(panel), str(method_label), int(x_values[int(peak_indices[str(panel)])]))
        for panel in panel_labels
    )
    peak_x_by_panel = {str(panel): int(x_values[int(peak_indices[str(panel)])]) for panel in panel_labels}
    if min(peak_x_by_panel, key=lambda label: (peak_x_by_panel[label], label)) != str(answer_panel):
        raise RuntimeError("earliest maximum construction lost unique target")

    query = _Query(
        query_id="earliest_maximum_panel_label",
        scene_variant="multipanel_line_grid",
        answer=str(answer_panel),
        answer_type="string",
        panel_label=str(answer_panel),
        method_label=str(method_label),
        method_a_label="",
        method_b_label="",
        x_value=0,
        start_x_value=0,
        end_x_value=0,
        threshold_value=0,
        evidence_panel_labels=(str(answer_panel),),
        evidence_point_ids=evidence_ids,
        evidence_intersection_ids=(),
        trace={
            "method_label": str(method_label),
            "peak_x_by_panel": dict(peak_x_by_panel),
            "peak_indices_by_panel": {str(panel): int(index) for panel, index in peak_indices.items()},
            "winning_panel_label": str(answer_panel),
        },
    )
    return _Dataset(
        scene_variant="multipanel_line_grid",
        x_values=tuple(x_values),
        y_min=int(y_min),
        y_max=int(y_max),
        panels=_panels_from_values(values_by_panel_method=values, panel_labels=panel_labels, method_labels=method_labels, colors=colors),
        query=query,
        intersections=(),
    )


def _build_dataset(query_id: str, params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    if str(query_id) == "curve_at_x_extremum_label":
        return _build_curve_at_x_dataset(params, instance_seed=int(instance_seed))
    if str(query_id) == "threshold_series_count":
        return _build_threshold_count_dataset(params, instance_seed=int(instance_seed))
    if str(query_id) == "cross_panel_delta_extremum_label":
        return _build_cross_panel_delta_dataset(params, instance_seed=int(instance_seed))
    if str(query_id) == "curve_intersection_count":
        return _build_intersection_count_dataset(params, instance_seed=int(instance_seed))
    if str(query_id) == "earliest_maximum_panel_label":
        return _build_earliest_maximum_dataset(params, instance_seed=int(instance_seed))
    raise ValueError(f"unsupported query_id: {query_id}")


def _panel_layout(plot_bbox: BBox, panel_count: int, gap: float) -> List[BBox]:
    x1, y1, x2, y2 = (float(value) for value in plot_bbox)
    cols = 3 if int(panel_count) <= 6 else 4
    rows = int(math.ceil(float(panel_count) / float(cols)))
    width = (x2 - x1 - (float(cols - 1) * float(gap))) / float(cols)
    height = (y2 - y1 - (float(rows - 1) * float(gap))) / float(rows)
    boxes: List[BBox] = []
    for index in range(int(panel_count)):
        row = int(index) // int(cols)
        col = int(index) % int(cols)
        px1 = x1 + (float(col) * (width + float(gap)))
        py1 = y1 + (float(row) * (height + float(gap)))
        boxes.append((px1, py1, px1 + width, py1 + height))
    return boxes


def _scale_point(
    *,
    x_value: float,
    y_value: float,
    x_values: Sequence[int],
    y_min: int,
    y_max: int,
    plot_bbox: BBox,
) -> Tuple[float, float]:
    x1, y1, x2, y2 = (float(value) for value in plot_bbox)
    x_min = float(min(x_values))
    x_max = float(max(x_values))
    x_fraction = 0.0 if x_max == x_min else (float(x_value) - x_min) / (x_max - x_min)
    y_fraction = 0.0 if int(y_max) == int(y_min) else (float(y_value) - float(y_min)) / (float(y_max) - float(y_min))
    return (
        float(x1) + (x_fraction * (float(x2) - float(x1))),
        float(y2) - (y_fraction * (float(y2) - float(y1))),
    )


def _draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    *,
    xy0: Tuple[float, float],
    xy1: Tuple[float, float],
    fill: RGB,
    width: int,
    dash_px: float = 8.0,
    gap_px: float = 6.0,
) -> None:
    x0, y0 = float(xy0[0]), float(xy0[1])
    x1, y1 = float(xy1[0]), float(xy1[1])
    length = math.hypot(x1 - x0, y1 - y0)
    if length <= 0:
        return
    dx = (x1 - x0) / length
    dy = (y1 - y0) / length
    pos = 0.0
    while pos < length:
        end = min(length, pos + float(dash_px))
        draw.line(
            [(x0 + dx * pos, y0 + dy * pos), (x0 + dx * end, y0 + dy * end)],
            fill=fill,
            width=max(1, int(width)),
        )
        pos = end + float(gap_px)


def _draw_legend(
    draw: ImageDraw.ImageDraw,
    *,
    method_labels: Sequence[str],
    colors: Sequence[RGB],
    params: Mapping[str, Any],
    origin: Tuple[float, float],
) -> Dict[str, List[float]]:
    font = load_font(_resolve_int(params, "legend_font_size_px", 17), bold=True)
    text_rgb = _resolve_rgb(params, "text_color_rgb", (36, 42, 54))
    bboxes: Dict[str, List[float]] = {}
    x = float(origin[0])
    y = float(origin[1])
    for index, method in enumerate(method_labels):
        color = tuple(colors[int(index) % len(colors)])
        swatch = [x, y + 5.0, x + 24.0, y + 18.0]
        draw.rounded_rectangle(swatch, radius=3, fill=color, outline=(255, 255, 255), width=1)
        text_xy = (x + 31.0, y)
        draw.text(text_xy, str(method), font=font, fill=text_rgb)
        text_box = _text_bbox(draw, text_xy, str(method), font)
        bboxes[str(method)] = _bbox([swatch[0], swatch[1], text_box[2], text_box[3]])
        x = float(text_box[2]) + 28.0
    return bboxes


def _draw_panel(
    draw: ImageDraw.ImageDraw,
    *,
    panel: _Panel,
    panel_bbox: BBox,
    dataset: _Dataset,
    params: Mapping[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, List[float]], Dict[str, List[float]], List[float]]:
    x1, y1, x2, y2 = (float(value) for value in panel_bbox)
    panel_fill = _resolve_rgb(params, "panel_fill_rgb", (255, 255, 255))
    panel_border = _resolve_rgb(params, "panel_border_rgb", (190, 199, 212))
    axis_rgb = _resolve_rgb(params, "axis_color_rgb", (68, 72, 82))
    grid_rgb = _resolve_rgb(params, "grid_color_rgb", (225, 229, 235))
    text_rgb = _resolve_rgb(params, "text_color_rgb", (36, 42, 54))
    muted_rgb = _resolve_rgb(params, "muted_text_rgb", (91, 102, 120))
    text_stroke = _resolve_rgb(params, "text_stroke_rgb", (255, 255, 255))
    threshold_rgb = _resolve_rgb(params, "threshold_rgb", (178, 74, 74))
    panel_title_font = load_font(_resolve_int(params, "panel_title_font_size_px", 18), bold=True)
    tick_font = load_font(_resolve_int(params, "tick_font_size_px", 12), bold=False)

    draw.rounded_rectangle(
        [x1, y1, x2, y2],
        radius=_resolve_int(params, "panel_corner_radius_px", 6),
        fill=panel_fill,
        outline=panel_border,
        width=_resolve_int(params, "panel_border_width_px", 2),
    )
    title_text = f"Panel {str(panel.panel_label)}"
    title_xy = (x1 + 12.0, y1 + 7.0)
    draw.text(title_xy, title_text, font=panel_title_font, fill=text_rgb)

    left_pad = 48.0
    right_pad = 18.0
    top_pad = 44.0
    bottom_pad = 42.0
    plot_bbox = (x1 + left_pad, y1 + top_pad, x2 - right_pad, y2 - bottom_pad)
    px1, py1, px2, py2 = plot_bbox
    draw.rectangle([px1, py1, px2, py2], fill=(255, 255, 255), outline=grid_rgb, width=1)

    y_ticks = [0, 25, 50, 75, 100]
    for tick in y_ticks:
        sx, sy = _scale_point(
            x_value=dataset.x_values[0],
            y_value=float(tick),
            x_values=dataset.x_values,
            y_min=dataset.y_min,
            y_max=dataset.y_max,
            plot_bbox=plot_bbox,
        )
        draw.line([px1, sy, px2, sy], fill=grid_rgb, width=_resolve_int(params, "grid_line_width_px", 1))
        draw.text((px1 - 34.0, sy - 7.0), str(tick), font=tick_font, fill=muted_rgb)

    tick_stride = max(1, int(math.ceil(float(len(dataset.x_values)) / 6.0)))
    x_ticks_to_draw = list(dataset.x_values[::tick_stride])
    if dataset.x_values[-1] not in x_ticks_to_draw:
        x_ticks_to_draw.append(int(dataset.x_values[-1]))
    for x_tick in x_ticks_to_draw:
        sx, _ = _scale_point(
            x_value=float(x_tick),
            y_value=float(dataset.y_min),
            x_values=dataset.x_values,
            y_min=dataset.y_min,
            y_max=dataset.y_max,
            plot_bbox=plot_bbox,
        )
        draw.line([sx, py1, sx, py2], fill=grid_rgb, width=_resolve_int(params, "grid_line_width_px", 1))
        _center_text(
            draw,
            center=(sx, py2 + 15.0),
            text=str(x_tick),
            font=tick_font,
            fill=muted_rgb,
            stroke_fill=text_stroke,
            stroke_width=1,
        )

    draw.line([px1, py2, px2, py2], fill=axis_rgb, width=_resolve_int(params, "axis_line_width_px", 2))
    draw.line([px1, py1, px1, py2], fill=axis_rgb, width=_resolve_int(params, "axis_line_width_px", 2))

    if (
        str(dataset.query.query_id) == "threshold_series_count"
        and str(dataset.query.panel_label) == str(panel.panel_label)
    ):
        _, threshold_y = _scale_point(
            x_value=float(dataset.x_values[0]),
            y_value=float(dataset.query.threshold_value),
            x_values=dataset.x_values,
            y_min=dataset.y_min,
            y_max=dataset.y_max,
            plot_bbox=plot_bbox,
        )
        _draw_dashed_line(
            draw,
            xy0=(px1, threshold_y),
            xy1=(px2, threshold_y),
            fill=threshold_rgb,
            width=2,
        )
        draw.text((px2 - 44.0, threshold_y - 18.0), f"y={dataset.query.threshold_value}", font=tick_font, fill=threshold_rgb)

    point_radius = float(_resolve_int(params, "point_radius_px", 5))
    point_bboxes: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = []
    for curve in panel.curves:
        points: List[Tuple[float, float]] = []
        for x_value, y_value in zip(dataset.x_values, curve.values):
            points.append(
                _scale_point(
                    x_value=float(x_value),
                    y_value=float(y_value),
                    x_values=dataset.x_values,
                    y_min=dataset.y_min,
                    y_max=dataset.y_max,
                    plot_bbox=plot_bbox,
                )
            )
        if len(points) >= 2:
            draw.line(points, fill=curve.color_rgb, width=_resolve_int(params, "line_width_px", 3), joint="curve")
        for x_value, y_value, (cx, cy) in zip(dataset.x_values, curve.values, points):
            marker = [
                float(cx) - float(point_radius),
                float(cy) - float(point_radius),
                float(cx) + float(point_radius),
                float(cy) + float(point_radius),
            ]
            draw.ellipse(marker, fill=curve.color_rgb, outline=(255, 255, 255), width=1)
            point_id = _point_id(str(panel.panel_label), str(curve.method_label), int(x_value))
            point_bboxes[str(point_id)] = _bbox(marker)
            entities.append(
                {
                    "entity_id": str(point_id),
                    "entity_type": "scientific_curve_marker",
                    "bbox_px": _bbox(marker),
                    "attrs": {
                        "panel_label": str(panel.panel_label),
                        "method_label": str(curve.method_label),
                        "x_value": int(x_value),
                        "y_value": int(y_value),
                        "center_px": [round(float(cx), 3), round(float(cy), 3)],
                    },
                }
            )

    return entities, point_bboxes, {}, _bbox(plot_bbox)


def _render_dataset(dataset: _Dataset, *, params: Mapping[str, Any], instance_seed: int) -> _Rendered:
    params = {**dict(params), "_render_style_seed": int(instance_seed)}
    canvas_width = _resolve_int(params, "canvas_width", 1600)
    canvas_height = _resolve_int(params, "canvas_height", 1000)
    background, background_meta = make_background_canvas(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    outer = _resolve_int(params, "outer_margin_px", 42)
    margin_left, margin_right, margin_top, margin_bottom, layout_jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(outer),
        right_px=int(outer),
        top_px=int(outer),
        bottom_px=int(outer),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.layout",
    )
    title_band = _resolve_int(params, "title_band_height_px", 92)
    panel_gap = _resolve_int(params, "panel_gap_px", 24)
    text_rgb = _resolve_rgb(params, "text_color_rgb", (36, 42, 54))
    muted_rgb = _resolve_rgb(params, "muted_text_rgb", (91, 102, 120))
    title_font = load_font(_resolve_int(params, "title_font_size_px", 30), bold=True)
    subtitle_font = load_font(_resolve_int(params, "subtitle_font_size_px", 18), bold=False)

    draw.text((float(margin_left), 22.0 + float(layout_jitter_meta.get("dy_px", 0))), "Scientific Multi-Panel Figure", font=title_font, fill=text_rgb)
    draw.text((float(margin_left), 58.0 + float(layout_jitter_meta.get("dy_px", 0))), "Synthetic method curves arranged as labeled scientific subplots.", font=subtitle_font, fill=muted_rgb)
    method_labels = tuple(curve.method_label for curve in dataset.panels[0].curves)
    legend_bboxes = _draw_legend(
        draw,
        method_labels=method_labels,
        colors=tuple(curve.color_rgb for curve in dataset.panels[0].curves),
        params=params,
        origin=(float(canvas_width) - 560.0, 38.0),
    )

    plot_bbox = [
        float(margin_left),
        float(title_band) + float(layout_jitter_meta.get("dy_px", 0)),
        float(canvas_width - margin_right),
        float(canvas_height - margin_bottom),
    ]
    panel_boxes = _panel_layout(tuple(plot_bbox), len(dataset.panels), gap=float(panel_gap))

    entities: List[Dict[str, Any]] = []
    panel_bboxes: Dict[str, List[float]] = {}
    panel_plot_bboxes: Dict[str, List[float]] = {}
    point_bboxes: Dict[str, List[float]] = {}
    for panel, panel_bbox in zip(dataset.panels, panel_boxes):
        rendered_entities, rendered_points, _extra_bboxes, panel_plot_bbox = _draw_panel(
            draw,
            panel=panel,
            panel_bbox=panel_bbox,
            dataset=dataset,
            params=params,
        )
        panel_bboxes[str(panel.panel_label)] = _bbox(panel_bbox)
        panel_plot_bboxes[str(panel.panel_label)] = list(panel_plot_bbox)
        point_bboxes.update(rendered_points)
        entities.extend(rendered_entities)
        entities.append(
            {
                "entity_id": f"scientific_subplot_{str(panel.panel_label)}",
                "entity_type": "scientific_subplot_panel",
                "bbox_px": _bbox(panel_bbox),
                "attrs": {
                    "panel_label": str(panel.panel_label),
                    "method_count": int(len(panel.curves)),
                    "x_tick_count": int(len(dataset.x_values)),
                },
            }
        )

    intersection_bboxes: Dict[str, List[float]] = {}
    for intersection in dataset.intersections:
        panel_plot_bbox = panel_plot_bboxes.get(str(intersection.panel_label))
        if panel_plot_bbox is None:
            continue
        cx, cy = _scale_point(
            x_value=float(intersection.x_value),
            y_value=float(intersection.y_value),
            x_values=dataset.x_values,
            y_min=dataset.y_min,
            y_max=dataset.y_max,
            plot_bbox=tuple(float(value) for value in panel_plot_bbox),
        )
        radius = 7.0
        box = _bbox([float(cx) - radius, float(cy) - radius, float(cx) + radius, float(cy) + radius])
        intersection_bboxes[str(intersection.intersection_id)] = list(box)
        entities.append(
            {
                "entity_id": str(intersection.intersection_id),
                "entity_type": "scientific_curve_intersection",
                "bbox_px": list(box),
                "attrs": {
                    "panel_label": str(intersection.panel_label),
                    "method_a_label": str(intersection.method_a_label),
                    "method_b_label": str(intersection.method_b_label),
                    "x_value": round(float(intersection.x_value), 3),
                    "y_value": round(float(intersection.y_value), 3),
                    "center_px": [round(float(cx), 3), round(float(cy), 3)],
                },
            }
        )

    image, post_noise_meta = apply_post_image_noise(
        image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return _Rendered(
        image=image,
        entities=tuple(entities),
        plot_bbox_px=_bbox(plot_bbox),
        panel_bboxes=dict(panel_bboxes),
        panel_plot_bboxes=dict(panel_plot_bboxes),
        point_bboxes=dict(point_bboxes),
        intersection_bboxes=dict(intersection_bboxes),
        legend_bboxes=dict(legend_bboxes),
        render_meta={
            "background_style": dict(background_meta),
            "post_image_noise": dict(post_noise_meta),
            "layout_jitter": dict(layout_jitter_meta),
            "x_values": list(dataset.x_values),
            "y_range": [int(dataset.y_min), int(dataset.y_max)],
            "panel_bboxes_px": dict(panel_bboxes),
            "panel_plot_bboxes_px": dict(panel_plot_bboxes),
        },
    )


def _evidence_bboxes(dataset: _Dataset, rendered: _Rendered) -> List[List[float]]:
    boxes: List[List[float]] = []
    for panel_label in dataset.query.evidence_panel_labels:
        panel_box = rendered.panel_bboxes.get(str(panel_label))
        if panel_box is not None:
            boxes.append(list(panel_box))
    for point_id in dataset.query.evidence_point_ids:
        point_box = rendered.point_bboxes.get(str(point_id))
        if point_box is not None:
            boxes.append(list(point_box))
    for intersection_id in dataset.query.evidence_intersection_ids:
        intersection_box = rendered.intersection_bboxes.get(str(intersection_id))
        if intersection_box is not None:
            boxes.append(list(intersection_box))
    return boxes


def _values_by_panel_method(dataset: _Dataset) -> Dict[str, Dict[str, List[int]]]:
    return {
        str(panel.panel_label): {
            str(curve.method_label): [int(value) for value in curve.values]
            for curve in panel.curves
        }
        for panel in dataset.panels
    }


class ChartsScientificMultipanelSubplotQueryTask:
    """Answer panel-aware questions on scientific multi-subplot line figures."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "scientific"

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
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        support_params = _support_sampling_params(params, query_id_probabilities=query_id_probabilities)
        dataset: _Dataset | None = None
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                attempt_params = {**dict(support_params), "_attempt_index": int(attempt_index)}
                dataset = _build_dataset(str(query_id), attempt_params, instance_seed=int(instance_seed) + int(attempt_index))
                break
            except Exception as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError(f"failed to generate {self.task_id} instance") from last_error

        rendered = _render_dataset(dataset, params=params, instance_seed=int(instance_seed))
        evidence_boxes = _evidence_bboxes(dataset, rendered)
        if not evidence_boxes:
            raise RuntimeError(f"{self.task_id} produced empty evidence")

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_multipanel_line_grid",
                "answer_hint_label",
                "answer_hint_count",
                "evidence_hint_curve_at_x_extremum_label",
                "evidence_hint_threshold_series_count",
                "evidence_hint_cross_panel_delta_extremum_label",
                "evidence_hint_curve_intersection_count",
                "evidence_hint_earliest_maximum_panel_label",
                "json_example_curve_at_x_extremum_label",
                "json_example_threshold_series_count",
                "json_example_cross_panel_delta_extremum_label",
                "json_example_curve_intersection_count",
                "json_example_earliest_maximum_panel_label",
                "json_example_answer_only_curve_at_x_extremum_label",
                "json_example_answer_only_threshold_series_count",
                "json_example_answer_only_cross_panel_delta_extremum_label",
                "json_example_answer_only_curve_intersection_count",
                "json_example_answer_only_earliest_maximum_panel_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        answer_hint_key = "answer_hint_count" if str(dataset.query.answer_type) == "integer" else "answer_hint_label"
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(dataset.query.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_multipanel_line_grid"]),
                "panel_label": str(dataset.query.panel_label),
                "method_label": str(dataset.query.method_label),
                "method_a_label": str(dataset.query.method_a_label),
                "method_b_label": str(dataset.query.method_b_label),
                "x_value": str(dataset.query.x_value),
                "start_x_value": str(dataset.query.start_x_value),
                "end_x_value": str(dataset.query.end_x_value),
                "threshold_value": str(dataset.query.threshold_value),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(dataset.query.query_id)}"]),
                "answer_hint": str(prompt_defaults[str(answer_hint_key)]),
                "json_example": str(prompt_defaults[f"json_example_{str(dataset.query.query_id)}"]),
                "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{str(dataset.query.query_id)}"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type=str(dataset.query.answer_type), value=dataset.query.answer)
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_boxes])
        values_by_panel_method = _values_by_panel_method(dataset)
        method_labels = [str(curve.method_label) for curve in dataset.panels[0].curves]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"chart_scientific_{str(dataset.scene_variant)}",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(dataset.query.query_id),
                    "scene_variant": str(dataset.scene_variant),
                    "answer": dataset.query.answer,
                    "evidence_panel_labels": list(dataset.query.evidence_panel_labels),
                    "evidence_point_ids": list(dataset.query.evidence_point_ids),
                    "evidence_intersection_ids": list(dataset.query.evidence_intersection_ids),
                },
            },
            "query_spec": {
                "query_id": str(dataset.query.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(dataset.query.query_id),
                    "scene_variant": str(dataset.scene_variant),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "panel_count": int(len(dataset.panels)),
                    "method_count": int(len(method_labels)),
                    "x_tick_count": int(len(dataset.x_values)),
                    "question_format": "curve_panels_subplot_query",
                },
            },
            "render_spec": {
                "canvas_width": _resolve_int(params, "canvas_width", 1600),
                "canvas_height": _resolve_int(params, "canvas_height", 1000),
                "coord_space": "pixel",
                "scene_variant": str(dataset.scene_variant),
                "plot_bbox_px": list(rendered.plot_bbox_px),
                **dict(rendered.render_meta),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "panel_bboxes_px": dict(rendered.panel_bboxes),
                "panel_plot_bboxes_px": dict(rendered.panel_plot_bboxes),
                "point_bboxes_px": dict(rendered.point_bboxes),
                "intersection_bboxes_px": dict(rendered.intersection_bboxes),
                "legend_bboxes_px": dict(rendered.legend_bboxes),
            },
            "execution_trace": {
                "query_id": str(dataset.query.query_id),
                "scene_variant": str(dataset.scene_variant),
                "answer": dataset.query.answer,
                "answer_type": str(dataset.query.answer_type),
                "panel_labels": [str(panel.panel_label) for panel in dataset.panels],
                "method_labels": list(method_labels),
                "x_values": list(dataset.x_values),
                "y_range": [int(dataset.y_min), int(dataset.y_max)],
                "panel_count": int(len(dataset.panels)),
                "method_count": int(len(method_labels)),
                "values_by_panel_method": values_by_panel_method,
                "evidence_panel_labels": list(dataset.query.evidence_panel_labels),
                "evidence_point_ids": list(dataset.query.evidence_point_ids),
                "evidence_intersection_ids": list(dataset.query.evidence_intersection_ids),
                "query_id_probabilities": dict(query_id_probabilities),
                "question_format": "curve_panels_subplot_query",
                **dict(dataset.query.trace),
            },
            "witness_symbolic": {
                "type": "curve_panels_subplot",
                "panel_labels": list(dataset.query.evidence_panel_labels),
                "point_ids": list(dataset.query.evidence_point_ids),
                "intersection_ids": list(dataset.query.evidence_intersection_ids),
                "answer": dataset.query.answer,
            },
            "projected_evidence": {
                "bbox_set": [list(bbox) for bbox in evidence_boxes],
                "panel_labels": list(dataset.query.evidence_panel_labels),
                "point_ids": list(dataset.query.evidence_point_ids),
                "intersection_ids": list(dataset.query.evidence_intersection_ids),
            },
        }

        visual_count = int(len(dataset.panels)) * int(len(method_labels)) * int(len(dataset.x_values))
        visual_max = int(_gen_int(params, "panel_count_max", 8)) * int(_gen_int(params, "method_count_max", 6)) * int(_gen_int(params, "x_tick_count_max", 12))
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(visual_count), [6 * 5 * 7, max(6 * 5 * 7, int(visual_max))]),
                "reasoning_load": clamp_unit_interval(float(_REASONING_LOAD_BY_VARIANT[str(dataset.query.query_id)])),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(dataset.scene_variant)]),
            },
        )

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(dataset.query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class ChartsScientificCurveAtXExtremumLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsScientificMultipanelSubplotQueryTask,
):
    """Return the panel or curve label with an extremal value at a shared x-position."""

    task_id = "task_charts__curve_panels__curve_at_x_extremum_label"
    fixed_query_id = "curve_at_x_extremum_label"


@register_task
class ChartsScientificThresholdSeriesCountTask(
    FixedChartQueryVariantTaskMixin,
    ChartsScientificMultipanelSubplotQueryTask,
):
    """Count series satisfying a threshold condition in a scientific panel."""

    task_id = "task_charts__curve_panels__threshold_series_count"
    fixed_query_id = "threshold_series_count"


@register_task
class ChartsScientificCrossPanelDeltaExtremumLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsScientificMultipanelSubplotQueryTask,
):
    """Return the label with an extremal cross-panel delta."""

    task_id = "task_charts__curve_panels__cross_panel_delta_extremum_label"
    fixed_query_id = "cross_panel_delta_extremum_label"


@register_task
class ChartsScientificCurveIntersectionCountTask(
    FixedChartQueryVariantTaskMixin,
    ChartsScientificMultipanelSubplotQueryTask,
):
    """Count curve intersections in a scientific subplot."""

    task_id = "task_charts__curve_panels__curve_intersection_count"
    fixed_query_id = "curve_intersection_count"


@register_task
class ChartsScientificEarliestMaximumPanelLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsScientificMultipanelSubplotQueryTask,
):
    """Return the panel label whose selected curve reaches its maximum earliest."""

    task_id = "task_charts__curve_panels__earliest_maximum_panel_label"
    fixed_query_id = "earliest_maximum_panel_label"


__all__ = [
    "ChartsScientificCrossPanelDeltaExtremumLabelTask",
    "ChartsScientificCurveAtXExtremumLabelTask",
    "ChartsScientificCurveIntersectionCountTask",
    "ChartsScientificEarliestMaximumPanelLabelTask",
    "ChartsScientificMultipanelSubplotQueryTask",
    "ChartsScientificThresholdSeriesCountTask",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_QUERY_IDS",
]
