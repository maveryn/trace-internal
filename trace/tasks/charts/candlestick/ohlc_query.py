"""Candlestick/OHLC chart tasks over open-high-low-close values."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import hash64, spawn_rng
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
from ...shared.text_rendering import draw_text_centered, load_font
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin, MergedChartQueryVariantTaskMixin
from ..shared.labeled_chart_common import sample_chart_labels
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_candlestick_ohlc_query_base"
SCENE_ID = "candlestick"
RANGE_EXTREMUM_QUERY_IDS: Tuple[str, ...] = (
    "wick_range_extremum_label",
    "body_range_extremum_label",
)
COUNTERFACTUAL_QUERY_ID = "close_after_body_change_value"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    *RANGE_EXTREMUM_QUERY_IDS,
    COUNTERFACTUAL_QUERY_ID,
)

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "candlestick")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="candlestick")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="candlestick", apply_prob=0.0)

_REASONING_LOAD_BY_QUERY: Dict[str, float] = {
    "wick_range_extremum_label": 0.68,
    "body_range_extremum_label": 0.62,
    COUNTERFACTUAL_QUERY_ID: 0.74,
}

RGB = Tuple[int, int, int]
BBox = List[float]


@dataclass(frozen=True)
class _Candle:
    candle_id: str
    label: str
    open_value: int
    high_value: int
    low_value: int
    close_value: int

    @property
    def direction(self) -> str:
        return "up" if int(self.close_value) > int(self.open_value) else "down"

    @property
    def body_size(self) -> int:
        return abs(int(self.close_value) - int(self.open_value))

    @property
    def wick_range(self) -> int:
        return int(self.high_value) - int(self.low_value)


@dataclass(frozen=True)
class _Query:
    query_id: str
    answer: int | str
    answer_type: str
    evidence_candle_ids: Tuple[str, ...]
    evidence_label_ids: Tuple[str, ...]
    params: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    candles: Tuple[_Candle, ...]
    query: _Query


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    plot_margin_left_px: int
    plot_margin_right_px: int
    plot_margin_top_px: int
    plot_margin_bottom_px: int
    axis_line_width_px: int
    grid_line_width_px: int
    wick_line_width_px: int
    body_outline_width_px: int
    tick_length_px: int
    title_font_size_px: int
    tick_font_size_px: int
    label_font_size_px: int
    value_font_size_px: int
    candle_width_fraction: float
    y_axis_min: int
    y_axis_max: int
    y_tick_step: int
    axis_color_rgb: RGB
    grid_color_rgb: RGB
    plot_fill_rgb: RGB
    text_color_rgb: RGB
    muted_text_rgb: RGB
    text_stroke_rgb: RGB
    up_fill_rgb: RGB
    down_fill_rgb: RGB
    wick_rgb: RGB
    body_outline_rgb: RGB
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: BBox
    candle_bboxes_px: Dict[str, BBox]
    body_bboxes_px: Dict[str, BBox]
    wick_bboxes_px: Dict[str, BBox]
    value_label_bboxes_px: Dict[str, BBox]
    x_label_bboxes_px: Dict[str, BBox]


def _bbox(values: Sequence[float]) -> BBox:
    return [round(float(value), 3) for value in values]


def _text_bbox_at(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Tuple[float, float],
    font: Any,
    stroke_width: int = 1,
) -> BBox:
    raw = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width)))
    width = float(raw[2] - raw[0])
    height = float(raw[3] - raw[1])
    cx, cy = float(center[0]), float(center[1])
    return _bbox([cx - width / 2.0, cy - height / 2.0, cx + width / 2.0, cy + height / 2.0])


def _render_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_RENDER_DEFAULTS, str(key), int(fallback))))


def _render_float(params: Mapping[str, Any], key: str, fallback: float) -> float:
    return float(params.get(str(key), group_default(_RENDER_DEFAULTS, str(key), float(fallback))))


def _resolve_render_params(params: Mapping[str, Any], *, instance_seed: int) -> _RenderParams:
    margin_left = _render_int(params, "plot_margin_left_px", 94)
    margin_right = _render_int(params, "plot_margin_right_px", 70)
    margin_top = _render_int(params, "plot_margin_top_px", 82)
    margin_bottom = _render_int(params, "plot_margin_bottom_px", 108)
    margin_left, margin_right, margin_top, margin_bottom, jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(margin_left),
        right_px=int(margin_right),
        top_px=int(margin_top),
        bottom_px=int(margin_bottom),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="charts.candlestick.layout",
    )
    return _RenderParams(
        canvas_width=_render_int(params, "canvas_width", 1440),
        canvas_height=_render_int(params, "canvas_height", 820),
        plot_margin_left_px=int(margin_left),
        plot_margin_right_px=int(margin_right),
        plot_margin_top_px=int(margin_top),
        plot_margin_bottom_px=int(margin_bottom),
        axis_line_width_px=_render_int(params, "axis_line_width_px", 2),
        grid_line_width_px=_render_int(params, "grid_line_width_px", 1),
        wick_line_width_px=_render_int(params, "wick_line_width_px", 4),
        body_outline_width_px=_render_int(params, "body_outline_width_px", 2),
        tick_length_px=_render_int(params, "tick_length_px", 8),
        title_font_size_px=_render_int(params, "title_font_size_px", 26),
        tick_font_size_px=_render_int(params, "tick_font_size_px", 16),
        label_font_size_px=_render_int(params, "label_font_size_px", 18),
        value_font_size_px=_render_int(params, "value_font_size_px", 15),
        candle_width_fraction=max(0.26, min(0.62, _render_float(params, "candle_width_fraction", 0.36))),
        y_axis_min=_render_int(params, "y_axis_min", 0),
        y_axis_max=max(80, _render_int(params, "y_axis_max", 100)),
        y_tick_step=max(5, _render_int(params, "y_tick_step", 20)),
        axis_color_rgb=resolve_render_rgb(
            params, _RENDER_DEFAULTS, "axis_color_rgb", (62, 68, 78), instance_seed=int(instance_seed), namespace=TASK_ID
        ),
        grid_color_rgb=resolve_render_rgb(
            params, _RENDER_DEFAULTS, "grid_color_rgb", (224, 228, 235), instance_seed=int(instance_seed), namespace=TASK_ID
        ),
        plot_fill_rgb=resolve_render_rgb(
            params, _RENDER_DEFAULTS, "plot_fill_rgb", (255, 255, 255), instance_seed=int(instance_seed), namespace=TASK_ID
        ),
        text_color_rgb=resolve_render_rgb(
            params, _RENDER_DEFAULTS, "text_color_rgb", (38, 42, 52), instance_seed=int(instance_seed), namespace=TASK_ID
        ),
        muted_text_rgb=resolve_render_rgb(
            params, _RENDER_DEFAULTS, "muted_text_rgb", (82, 92, 108), instance_seed=int(instance_seed), namespace=TASK_ID
        ),
        text_stroke_rgb=resolve_render_rgb(
            params, _RENDER_DEFAULTS, "text_stroke_rgb", (255, 255, 255), instance_seed=int(instance_seed), namespace=TASK_ID
        ),
        up_fill_rgb=resolve_render_rgb(
            params, _RENDER_DEFAULTS, "up_fill_rgb", (59, 151, 119), instance_seed=int(instance_seed), namespace=TASK_ID
        ),
        down_fill_rgb=resolve_render_rgb(
            params, _RENDER_DEFAULTS, "down_fill_rgb", (210, 93, 83), instance_seed=int(instance_seed), namespace=TASK_ID
        ),
        wick_rgb=resolve_render_rgb(
            params, _RENDER_DEFAULTS, "wick_rgb", (54, 60, 70), instance_seed=int(instance_seed), namespace=TASK_ID
        ),
        body_outline_rgb=resolve_render_rgb(
            params, _RENDER_DEFAULTS, "body_outline_rgb", (38, 44, 54), instance_seed=int(instance_seed), namespace=TASK_ID
        ),
        layout_jitter_meta=dict(jitter_meta),
    )


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    for key in ("query_id", "query_id"):
        raw = params.get(str(key))
        if raw is not None and str(raw) in SUPPORTED_QUERY_IDS:
            return str(raw), {str(raw): 1.0}

    raw_weights = params.get("query_id_weights", group_default(_GEN_DEFAULTS, "query_id_weights", {}))
    if isinstance(raw_weights, Mapping):
        weighted = [(str(key), float(value)) for key, value in raw_weights.items() if str(key) in SUPPORTED_QUERY_IDS and float(value) > 0.0]
    else:
        weighted = []
    if not weighted:
        weighted = [(str(query_id), 1.0) for query_id in SUPPORTED_QUERY_IDS]

    total = sum(weight for _, weight in weighted)
    probabilities = {str(query_id): float(weight) / float(total) for query_id, weight in weighted}
    if bool(params.get("balanced_query_id_sampling", group_default(_GEN_DEFAULTS, "balanced_query_id_sampling", True))):
        index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace="charts.candlestick.query")
        return str(weighted[int(index) % len(weighted)][0]), probabilities

    rng = spawn_rng(int(instance_seed), "charts.candlestick.query")
    threshold = rng.random() * float(total)
    cursor = 0.0
    for query_id, weight in weighted:
        cursor += float(weight)
        if threshold <= cursor:
            return str(query_id), probabilities
    return str(weighted[-1][0]), probabilities


def _sample_candles(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[_Candle, ...]:
    candle_min, candle_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="candle_count_min",
        max_key="candle_count_max",
        fallback_min=7,
        fallback_max=10,
        context="candlestick candle count",
    )
    value_min, value_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="value_min",
        max_key="value_max",
        fallback_min=8,
        fallback_max=96,
        context="candlestick value range",
    )
    body_min, body_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="body_size_min",
        max_key="body_size_max",
        fallback_min=4,
        fallback_max=20,
        context="candlestick body size",
    )
    wick_min, wick_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="wick_size_min",
        max_key="wick_size_max",
        fallback_min=2,
        fallback_max=10,
        context="candlestick wick size",
    )
    if int(body_max) - int(body_min) + 1 < int(candle_max):
        raise ValueError("body size support must allow unique body ranges")

    for attempt in range(250):
        rng = spawn_rng(int(instance_seed), "charts.candlestick.candles.retry", int(attempt))
        candle_count = int(candle_min) + int(rng.randrange(int(candle_max) - int(candle_min) + 1))
        labels = sample_chart_labels(count=int(candle_count), instance_seed=int(hash64(int(instance_seed), "candlestick.labels", int(attempt))))
        body_sizes = list(range(int(body_min), int(body_max) + 1))
        rng.shuffle(body_sizes)
        body_sizes = body_sizes[: int(candle_count)]
        candles: List[_Candle] = []
        for index in range(int(candle_count)):
            body = int(body_sizes[index])
            direction = "up" if ((index + int(rng.randrange(2))) % 2 == 0) else "down"
            if index == 0:
                direction = "up"
            if index == 1:
                direction = "down"
            if direction == "up":
                open_low = int(value_min) + int(wick_max)
                open_high = int(value_max) - int(body) - int(wick_max)
                if open_low > open_high:
                    break
                open_value = int(rng.randint(open_low, open_high))
                close_value = int(open_value) + int(body)
            else:
                open_low = int(value_min) + int(body) + int(wick_max)
                open_high = int(value_max) - int(wick_max)
                if open_low > open_high:
                    break
                open_value = int(rng.randint(open_low, open_high))
                close_value = int(open_value) - int(body)
            upper_wick = int(rng.randint(int(wick_min), int(wick_max)))
            lower_wick = int(rng.randint(int(wick_min), int(wick_max)))
            high_value = max(int(open_value), int(close_value)) + int(upper_wick)
            low_value = min(int(open_value), int(close_value)) - int(lower_wick)
            if not (int(value_min) <= int(low_value) < int(high_value) <= int(value_max)):
                break
            candles.append(
                _Candle(
                    candle_id=f"candle_{index}",
                    label=str(labels[index]),
                    open_value=int(open_value),
                    high_value=int(high_value),
                    low_value=int(low_value),
                    close_value=int(close_value),
                )
            )
        if len(candles) != int(candle_count):
            continue
        directions = [candle.direction for candle in candles]
        if directions.count("up") < 2 or directions.count("down") < 2:
            continue
        if len({int(candle.body_size) for candle in candles}) != len(candles):
            continue
        if len({int(candle.wick_range) for candle in candles}) != len(candles):
            continue
        return tuple(candles)
    raise ValueError("could not sample a valid candlestick OHLC series")


def _build_query(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    candles: Tuple[_Candle, ...],
    query_id: str,
    query_probabilities: Mapping[str, float],
) -> _Query:
    index_seed = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"charts.candlestick.{query_id}.target")
    base_params: Dict[str, Any] = {
        "query_id": str(query_id),
        "query_id_probabilities": dict(query_probabilities),
        "candle_count": int(len(candles)),
    }

    if str(query_id) in RANGE_EXTREMUM_QUERY_IDS:
        range_kind = "wick" if str(query_id) == "wick_range_extremum_label" else "body"
        extremum = "largest" if int(index_seed) % 2 == 0 else "smallest"
        scored = [
            (
                int(candle.wick_range if range_kind == "wick" else candle.body_size),
                candle,
            )
            for candle in candles
        ]
        scored.sort(key=lambda item: (int(item[0]), str(item[1].label)))
        target = scored[-1][1] if str(extremum) == "largest" else scored[0][1]
        if str(range_kind) == "wick":
            value_ids = (f"{target.candle_id}:high", f"{target.candle_id}:low")
            range_phrase = "high-low wick range"
        else:
            value_ids = (f"{target.candle_id}:open", f"{target.candle_id}:close")
            range_phrase = "open-close body size"
        return _Query(
            query_id=str(query_id),
            answer=str(target.label),
            answer_type="string",
            evidence_candle_ids=(str(target.candle_id),),
            evidence_label_ids=(f"x_label:{target.candle_id}", *value_ids),
            params={
                **base_params,
                "range_kind": str(range_kind),
                "range_kind_phrase": str(range_phrase),
                "extremum": str(extremum),
                "extremum_phrase": str(extremum),
                "answer_candle_id": str(target.candle_id),
                "answer_label": str(target.label),
                "answer_range_value": int(target.wick_range if range_kind == "wick" else target.body_size),
            },
        )

    if str(query_id) == COUNTERFACTUAL_QUERY_ID:
        change_min, change_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="counterfactual_change_min",
            max_key="counterfactual_change_max",
            fallback_min=2,
            fallback_max=6,
            context="candlestick counterfactual body-size change",
        )
        candidates = list(candles)
        start_index = int(index_seed) % len(candidates)
        candidates = candidates[start_index:] + candidates[:start_index]
        increase = int(index_seed) % 2 == 0
        for candidate in candidates:
            current_body = int(candidate.body_size)
            if increase:
                max_change = min(int(change_max), 96 - max(int(candidate.open_value), int(candidate.close_value)))
            else:
                max_change = min(int(change_max), int(current_body) - 1)
            if int(max_change) < int(change_min):
                continue
            change = int(change_min) + int(index_seed % (int(max_change) - int(change_min) + 1))
            new_body = int(current_body) + int(change) if increase else int(current_body) - int(change)
            if str(candidate.direction) == "up":
                answer = int(candidate.open_value) + int(new_body)
            else:
                answer = int(candidate.open_value) - int(new_body)
            if 1 <= int(answer) <= 99:
                return _Query(
                    query_id=str(query_id),
                    answer=int(answer),
                    answer_type="integer",
                    evidence_candle_ids=(str(candidate.candle_id),),
                    evidence_label_ids=(
                        f"x_label:{candidate.candle_id}",
                        f"{candidate.candle_id}:open",
                        f"{candidate.candle_id}:close",
                    ),
                    params={
                        **base_params,
                        "target_candle_id": str(candidate.candle_id),
                        "target_label": str(candidate.label),
                        "target_direction": str(candidate.direction),
                        "change_value": int(change),
                        "change_direction": "increase" if increase else "decrease",
                        "change_phrase": "increased" if increase else "decreased",
                        "change_verb": "increase" if increase else "decrease",
                        "change_past_phrase": "increased" if increase else "decreased",
                        "current_body_size": int(current_body),
                        "new_body_size": int(new_body),
                    },
                )
        raise ValueError("no feasible counterfactual close target")

    raise ValueError(f"unsupported candlestick query: {query_id}")


def _build_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    query_id, query_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
    for attempt in range(120):
        attempt_seed = int(instance_seed) if attempt == 0 else int(hash64(int(instance_seed), "charts.candlestick.dataset", int(attempt)))
        candles = _sample_candles(params, instance_seed=int(attempt_seed))
        try:
            query = _build_query(
                params=params,
                instance_seed=int(instance_seed),
                candles=tuple(candles),
                query_id=str(query_id),
                query_probabilities=query_probabilities,
            )
            return _Dataset(candles=tuple(candles), query=query)
        except ValueError:
            continue
    raise ValueError(f"could not build valid candlestick dataset for query {query_id}")


def _draw_candlesticks(
    base_image: Image.Image,
    *,
    dataset: _Dataset,
    render_params: _RenderParams,
) -> _Rendered:
    image = base_image.convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = int(render_params.canvas_width), int(render_params.canvas_height)
    left = int(render_params.plot_margin_left_px)
    right = width - int(render_params.plot_margin_right_px)
    top = int(render_params.plot_margin_top_px)
    bottom = height - int(render_params.plot_margin_bottom_px)
    plot_bbox = _bbox([left, top, right, bottom])
    draw.rounded_rectangle(
        [left, top, right, bottom],
        radius=8,
        fill=tuple(render_params.plot_fill_rgb),
        outline=(202, 208, 218),
        width=1,
    )

    title_font = load_font(int(render_params.title_font_size_px), bold=True)
    tick_font = load_font(int(render_params.tick_font_size_px), bold=False)
    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    value_font = load_font(int(render_params.value_font_size_px), bold=True)
    draw.text(
        (left, max(12, top - 50)),
        "OHLC candlestick chart",
        font=title_font,
        fill=tuple(render_params.text_color_rgb),
    )

    y_min = int(render_params.y_axis_min)
    y_max = int(render_params.y_axis_max)
    plot_h = float(bottom - top)
    plot_w = float(right - left)

    def y_for(value: int | float) -> float:
        span = max(1.0, float(y_max - y_min))
        return float(bottom) - ((float(value) - float(y_min)) / span) * plot_h

    for tick in range(int(y_min), int(y_max) + 1, int(render_params.y_tick_step)):
        y = y_for(int(tick))
        draw.line([left, y, right, y], fill=tuple(render_params.grid_color_rgb), width=int(render_params.grid_line_width_px))
        draw.line([left - int(render_params.tick_length_px), y, left, y], fill=tuple(render_params.axis_color_rgb), width=1)
        text = str(tick)
        bbox = draw.textbbox((0, 0), text, font=tick_font)
        draw.text(
            (left - int(render_params.tick_length_px) - 8 - (bbox[2] - bbox[0]), y - (bbox[3] - bbox[1]) / 2),
            text,
            font=tick_font,
            fill=tuple(render_params.muted_text_rgb),
        )
    draw.line([left, bottom, right, bottom], fill=tuple(render_params.axis_color_rgb), width=int(render_params.axis_line_width_px))
    draw.line([left, top, left, bottom], fill=tuple(render_params.axis_color_rgb), width=int(render_params.axis_line_width_px))

    slot_count = len(dataset.candles)
    slot_w = plot_w / float(slot_count)
    body_w = max(30.0, min(54.0, slot_w * float(render_params.candle_width_fraction)))
    candle_bboxes: Dict[str, BBox] = {}
    body_bboxes: Dict[str, BBox] = {}
    wick_bboxes: Dict[str, BBox] = {}
    value_label_bboxes: Dict[str, BBox] = {}
    x_label_bboxes: Dict[str, BBox] = {}
    entities: List[Dict[str, Any]] = []

    for index, candle in enumerate(dataset.candles):
        cx = float(left) + (float(index) + 0.5) * slot_w
        high_y = y_for(int(candle.high_value))
        low_y = y_for(int(candle.low_value))
        open_y = y_for(int(candle.open_value))
        close_y = y_for(int(candle.close_value))
        body_top = min(open_y, close_y)
        body_bottom = max(open_y, close_y)
        if body_bottom - body_top < 8:
            midpoint = (body_top + body_bottom) / 2.0
            body_top = midpoint - 4.0
            body_bottom = midpoint + 4.0

        wick_box = _bbox([cx - 4, high_y, cx + 4, low_y])
        draw.line([cx, high_y, cx, low_y], fill=tuple(render_params.wick_rgb), width=int(render_params.wick_line_width_px))
        tick_half = max(8.0, body_w * 0.24)
        draw.line([cx - tick_half, high_y, cx + tick_half, high_y], fill=tuple(render_params.wick_rgb), width=2)
        draw.line([cx - tick_half, low_y, cx + tick_half, low_y], fill=tuple(render_params.wick_rgb), width=2)
        fill = tuple(render_params.up_fill_rgb if candle.direction == "up" else render_params.down_fill_rgb)
        body_box = _bbox([cx - body_w / 2.0, body_top, cx + body_w / 2.0, body_bottom])
        draw.rounded_rectangle(
            body_box,
            radius=4,
            fill=fill,
            outline=tuple(render_params.body_outline_rgb),
            width=int(render_params.body_outline_width_px),
        )
        candle_box = _bbox_union([wick_box, body_box], padding=3.0)
        wick_bboxes[str(candle.candle_id)] = wick_box
        body_bboxes[str(candle.candle_id)] = body_box
        candle_bboxes[str(candle.candle_id)] = candle_box

        side_label_offset = max(16.0, body_w * 0.32)
        label_specs = [
            ("high", f"H{int(candle.high_value)}", (cx, max(float(top) + 14.0, high_y - 18.0))),
            ("low", f"L{int(candle.low_value)}", (cx, min(float(bottom) - 14.0, low_y + 18.0))),
            ("open", f"O{int(candle.open_value)}", (cx - body_w / 2.0 - side_label_offset, open_y)),
            ("close", f"C{int(candle.close_value)}", (cx + body_w / 2.0 + side_label_offset, close_y)),
        ]
        for value_kind, text, center in label_specs:
            box = _text_bbox_at(draw, text=str(text), center=center, font=value_font, stroke_width=2)
            draw_text_centered(
                draw,
                text=str(text),
                center=center,
                font=value_font,
                fill=tuple(render_params.text_color_rgb),
                stroke_fill=tuple(render_params.text_stroke_rgb),
                stroke_width=2,
            )
            value_label_bboxes[f"{candle.candle_id}:{value_kind}"] = list(box)

        x_center = (float(cx), float(bottom) + 28.0)
        x_box = _text_bbox_at(draw, text=str(candle.label), center=x_center, font=label_font, stroke_width=1)
        draw_text_centered(
            draw,
            text=str(candle.label),
            center=x_center,
            font=label_font,
            fill=tuple(render_params.text_color_rgb),
            stroke_fill=tuple(render_params.text_stroke_rgb),
            stroke_width=1,
        )
        x_label_bboxes[str(candle.candle_id)] = list(x_box)
        entities.append(
            {
                "entity_id": str(candle.candle_id),
                "entity_type": "ohlc_candle",
                "label": str(candle.label),
                "open": int(candle.open_value),
                "high": int(candle.high_value),
                "low": int(candle.low_value),
                "close": int(candle.close_value),
                "direction": str(candle.direction),
                "body_size": int(candle.body_size),
                "wick_range": int(candle.wick_range),
                "candle_bbox_px": list(candle_box),
                "body_bbox_px": list(body_box),
                "wick_bbox_px": list(wick_box),
                "x_label_bbox_px": list(x_box),
            }
        )

    return _Rendered(
        image=image,
        entities=tuple(entities),
        plot_bbox_px=list(plot_bbox),
        candle_bboxes_px=dict(candle_bboxes),
        body_bboxes_px=dict(body_bboxes),
        wick_bboxes_px=dict(wick_bboxes),
        value_label_bboxes_px=dict(value_label_bboxes),
        x_label_bboxes_px=dict(x_label_bboxes),
    )


def _build_prompt_slots(dataset: _Dataset, prompt_defaults: Mapping[str, Any]) -> Dict[str, Any]:
    is_label = str(dataset.query.answer_type) == "string"
    slots: Dict[str, Any] = {
        "object_description": str(prompt_defaults["object_description_candlestick"]),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_defaults["answer_hint_label" if is_label else "answer_hint_value"]),
        "evidence_hint": str(prompt_defaults["evidence_hint_label" if is_label else "evidence_hint_value"]),
        "json_example": str(prompt_defaults["json_example_label" if is_label else "json_example_value"]),
        "json_example_answer_only": str(prompt_defaults["json_example_answer_only_label" if is_label else "json_example_answer_only_value"]),
    }
    params = dataset.query.params
    for key in (
        "direction_phrase",
        "direction_detail",
        "threshold_value",
        "range_kind_phrase",
        "extremum_phrase",
        "target_label",
        "change_verb",
        "change_past_phrase",
        "change_value",
    ):
        if key in params:
            slots[str(key)] = params[str(key)]
    return slots


class ChartsCandlestickOHLCQueryTask:
    """Generate OHLC candlestick chart questions."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "candlestick"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) if attempt == 0 else int(hash64(int(instance_seed), "charts.candlestick.retry", int(attempt)))
            try:
                return self._generate_once(int(attempt_seed), params=dict(params))
            except Exception as exc:
                last_error = exc
                continue
        raise RuntimeError(f"failed to generate {self.task_id} after {max_attempts} attempts: {last_error}")

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        dataset = _build_dataset(params=params, instance_seed=int(instance_seed))
        render_params = _resolve_render_params(params, instance_seed=int(instance_seed))
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered = _draw_candlesticks(background, dataset=dataset, render_params=render_params)
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_value",
                "answer_hint_label",
                "evidence_hint_value",
                "evidence_hint_label",
                "json_example_value",
                "json_example_label",
                "json_example_answer_only_value",
                "json_example_answer_only_label",
                "object_description_candlestick",
            ],
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(dataset.query.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots=_build_prompt_slots(dataset, prompt_defaults),
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_boxes: List[BBox] = []
        for candle_id in dataset.query.evidence_candle_ids:
            evidence_boxes.append(list(rendered.body_bboxes_px[str(candle_id)]))
        for label_id in dataset.query.evidence_label_ids:
            if str(label_id).startswith("x_label:"):
                candle_id = str(label_id).split(":", 1)[1]
                evidence_boxes.append(list(rendered.x_label_bboxes_px[str(candle_id)]))
            elif str(label_id).endswith(":body_values"):
                candle_id = str(label_id).split(":", 1)[0]
                evidence_boxes.append(list(rendered.value_label_bboxes_px[f"{candle_id}:open"]))
                evidence_boxes.append(list(rendered.value_label_bboxes_px[f"{candle_id}:close"]))
            else:
                evidence_boxes.append(list(rendered.value_label_bboxes_px[str(label_id)]))

        answer_value: int | str = int(dataset.query.answer) if str(dataset.query.answer_type) == "integer" else str(dataset.query.answer)
        answer_gt = TypedValue(type=str(dataset.query.answer_type), value=answer_value)
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_boxes))
        candle_rows = [
            {
                "candle_id": str(candle.candle_id),
                "label": str(candle.label),
                "open": int(candle.open_value),
                "high": int(candle.high_value),
                "low": int(candle.low_value),
                "close": int(candle.close_value),
                "direction": str(candle.direction),
                "body_size": int(candle.body_size),
                "wick_range": int(candle.wick_range),
            }
            for candle in dataset.candles
        ]
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(len(dataset.candles), [7, 10]),
                "reasoning_load": clamp_unit_interval(_REASONING_LOAD_BY_QUERY[str(dataset.query.query_id)]),
                "scene_variant_load": 0.70,
            },
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_candlestick_ohlc",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(dataset.query.query_id),
                    "answer": answer_value,
                    "evidence_candle_ids": list(dataset.query.evidence_candle_ids),
                    "evidence_label_ids": list(dataset.query.evidence_label_ids),
                },
            },
            "query_spec": {
                "query_id": str(dataset.query.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(dataset.query.params),
            },
            "render_spec": {
                "scene_variant": "candlestick",
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "y_axis_min": int(render_params.y_axis_min),
                "y_axis_max": int(render_params.y_axis_max),
                "layout_jitter": dict(render_params.layout_jitter_meta),
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "candle_bboxes_px": dict(rendered.candle_bboxes_px),
                "body_bboxes_px": dict(rendered.body_bboxes_px),
                "wick_bboxes_px": dict(rendered.wick_bboxes_px),
                "value_label_bboxes_px": dict(rendered.value_label_bboxes_px),
                "x_label_bboxes_px": dict(rendered.x_label_bboxes_px),
            },
            "execution_trace": {
                "query_id": str(dataset.query.query_id),
                "question_format": "candlestick_ohlc_query",
                "answer": answer_value,
                "answer_type": str(dataset.query.answer_type),
                "candle_count": int(len(dataset.candles)),
                "candles": list(candle_rows),
                "evidence_candle_ids": list(dataset.query.evidence_candle_ids),
                "evidence_label_ids": list(dataset.query.evidence_label_ids),
                **dict(dataset.query.params),
            },
            "witness_symbolic": {
                "type": "candlestick_ohlc_witness",
                "candle_ids": list(dataset.query.evidence_candle_ids),
                "label_ids": list(dataset.query.evidence_label_ids),
                "answer": answer_value,
            },
            "projected_evidence": {
                "bbox_set": list(evidence_boxes),
                "candle_ids": list(dataset.query.evidence_candle_ids),
                "label_ids": list(dataset.query.evidence_label_ids),
            },
            "background": background_meta,
            "post_image_noise": dict(post_noise_meta),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(dataset.query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class ChartsCandlestickRangeExtremumLabelTask(
    MergedChartQueryVariantTaskMixin,
    ChartsCandlestickOHLCQueryTask,
):
    """Return the period label with an extremal wick or body range."""

    task_id = "task_charts__candlestick__range_extremum_label"
    allowed_query_ids = RANGE_EXTREMUM_QUERY_IDS


@register_task
class ChartsCandlestickCounterfactualCloseValueTask(
    FixedChartQueryVariantTaskMixin,
    ChartsCandlestickOHLCQueryTask,
):
    """Compute a counterfactual close after changing one candle body size."""

    task_id = "task_charts__candlestick__counterfactual_close_value"
    fixed_query_id = COUNTERFACTUAL_QUERY_ID


__all__ = [
    "ChartsCandlestickCounterfactualCloseValueTask",
    "ChartsCandlestickOHLCQueryTask",
    "ChartsCandlestickRangeExtremumLabelTask",
    "SUPPORTED_QUERY_IDS",
]
