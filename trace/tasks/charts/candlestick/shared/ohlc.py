"""Scene-local candlestick/OHLC sampling and rendering helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from PIL import Image, ImageDraw

from trace.core.seed import hash64, spawn_rng
from trace.core.visual.background import make_background_canvas
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.charts.shared.labeled_chart_common import sample_chart_labels
from trace.tasks.charts.shared.visual_defaults import (
    chart_font_asset_metadata,
    load_chart_scene_background_defaults,
    load_chart_scene_noise_defaults,
    sample_chart_font_family,
)
from trace.tasks.shared.bbox_projection import bbox_union_raw as _bbox_union
from trace.tasks.shared.config_defaults import (
    group_default,
    load_scene_generation_rendering_prompt_defaults,
    resolve_required_int_bounds,
)
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.render_variation import apply_layout_jitter_to_margins, resolve_render_rgb
from trace.tasks.shared.text_legibility import draw_text_traced
from trace.tasks.shared.text_rendering import draw_text_centered, load_font, temporary_default_font_family


DOMAIN = "charts"
SCENE_ID = "candlestick"
SCENE_NAMESPACE = "charts.candlestick"
PROMPT_BUNDLE_ID = "charts_candlestick_v1"

GENERATION_DEFAULTS, RENDERING_DEFAULTS, PROMPT_DEFAULTS = (
    load_scene_generation_rendering_prompt_defaults(DOMAIN, SCENE_ID)
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_scene_background_defaults(scene_id=SCENE_ID)
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)

RGB = tuple[int, int, int]
BBox = list[float]
Point = list[float]


@dataclass(frozen=True)
class Candle:
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
class Selection:
    answer: int | str
    answer_type: str
    annotation_candle_ids: tuple[str, ...]
    annotation_label_ids: tuple[str, ...]
    annotation_roles: tuple[str, ...]
    trace: dict[str, Any]


@dataclass(frozen=True)
class Dataset:
    candles: tuple[Candle, ...]
    selection: Selection


@dataclass(frozen=True)
class RenderParams:
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
    layout_jitter_meta: dict[str, Any]


@dataclass(frozen=True)
class Rendered:
    image: Image.Image
    entities: tuple[dict[str, Any], ...]
    plot_bbox_px: BBox
    candle_bboxes_px: dict[str, BBox]
    body_bboxes_px: dict[str, BBox]
    wick_bboxes_px: dict[str, BBox]
    value_label_bboxes_px: dict[str, BBox]
    x_label_bboxes_px: dict[str, BBox]


@dataclass(frozen=True)
class RenderArtifacts:
    rendered: Rendered
    render_params: RenderParams
    background_style: dict[str, Any]
    font_assets: dict[str, Any]
    post_image_noise: dict[str, Any]


def _bbox(values: Sequence[float]) -> BBox:
    return [round(float(value), 3) for value in values]


def _bbox_center(box: Sequence[float]) -> Point:
    return [
        round((float(box[0]) + float(box[2])) / 2.0, 3),
        round((float(box[1]) + float(box[3])) / 2.0, 3),
    ]


def _text_bbox_at(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: tuple[float, float],
    font: Any,
    stroke_width: int = 1,
) -> BBox:
    raw = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width)))
    width = float(raw[2] - raw[0])
    height = float(raw[3] - raw[1])
    cx, cy = float(center[0]), float(center[1])
    return _bbox([cx - width / 2.0, cy - height / 2.0, cx + width / 2.0, cy + height / 2.0])


def _render_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(RENDERING_DEFAULTS, str(key), int(fallback))))


def _render_float(params: Mapping[str, Any], key: str, fallback: float) -> float:
    return float(params.get(str(key), group_default(RENDERING_DEFAULTS, str(key), float(fallback))))


def resolve_render_params(params: Mapping[str, Any], *, instance_seed: int) -> RenderParams:
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
        defaults=RENDERING_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.layout",
    )
    return RenderParams(
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
            params, RENDERING_DEFAULTS, "axis_color_rgb", (62, 68, 78), instance_seed=int(instance_seed), namespace=SCENE_NAMESPACE
        ),
        grid_color_rgb=resolve_render_rgb(
            params, RENDERING_DEFAULTS, "grid_color_rgb", (224, 228, 235), instance_seed=int(instance_seed), namespace=SCENE_NAMESPACE
        ),
        plot_fill_rgb=resolve_render_rgb(
            params, RENDERING_DEFAULTS, "plot_fill_rgb", (255, 255, 255), instance_seed=int(instance_seed), namespace=SCENE_NAMESPACE
        ),
        text_color_rgb=resolve_render_rgb(
            params, RENDERING_DEFAULTS, "text_color_rgb", (38, 42, 52), instance_seed=int(instance_seed), namespace=SCENE_NAMESPACE
        ),
        muted_text_rgb=resolve_render_rgb(
            params, RENDERING_DEFAULTS, "muted_text_rgb", (82, 92, 108), instance_seed=int(instance_seed), namespace=SCENE_NAMESPACE
        ),
        text_stroke_rgb=resolve_render_rgb(
            params, RENDERING_DEFAULTS, "text_stroke_rgb", (255, 255, 255), instance_seed=int(instance_seed), namespace=SCENE_NAMESPACE
        ),
        up_fill_rgb=resolve_render_rgb(
            params, RENDERING_DEFAULTS, "up_fill_rgb", (59, 151, 119), instance_seed=int(instance_seed), namespace=SCENE_NAMESPACE
        ),
        down_fill_rgb=resolve_render_rgb(
            params, RENDERING_DEFAULTS, "down_fill_rgb", (210, 93, 83), instance_seed=int(instance_seed), namespace=SCENE_NAMESPACE
        ),
        wick_rgb=resolve_render_rgb(
            params, RENDERING_DEFAULTS, "wick_rgb", (54, 60, 70), instance_seed=int(instance_seed), namespace=SCENE_NAMESPACE
        ),
        body_outline_rgb=resolve_render_rgb(
            params, RENDERING_DEFAULTS, "body_outline_rgb", (38, 44, 54), instance_seed=int(instance_seed), namespace=SCENE_NAMESPACE
        ),
        layout_jitter_meta=dict(jitter_meta),
    )


def sample_candles(params: Mapping[str, Any], *, instance_seed: int) -> tuple[Candle, ...]:
    candle_min, candle_max = resolve_required_int_bounds(
        params,
        GENERATION_DEFAULTS,
        min_key="candle_count_min",
        max_key="candle_count_max",
        fallback_min=7,
        fallback_max=10,
        context="candlestick candle count",
    )
    value_min, value_max = resolve_required_int_bounds(
        params,
        GENERATION_DEFAULTS,
        min_key="value_min",
        max_key="value_max",
        fallback_min=8,
        fallback_max=96,
        context="candlestick value range",
    )
    body_min, body_max = resolve_required_int_bounds(
        params,
        GENERATION_DEFAULTS,
        min_key="body_size_min",
        max_key="body_size_max",
        fallback_min=4,
        fallback_max=20,
        context="candlestick body size",
    )
    wick_min, wick_max = resolve_required_int_bounds(
        params,
        GENERATION_DEFAULTS,
        min_key="wick_size_min",
        max_key="wick_size_max",
        fallback_min=2,
        fallback_max=10,
        context="candlestick wick size",
    )
    if int(body_max) - int(body_min) + 1 < int(candle_max):
        raise ValueError("body size support must allow unique body ranges")

    for attempt in range(250):
        rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.candles.retry", int(attempt))
        candle_count = int(candle_min) + int(rng.randrange(int(candle_max) - int(candle_min) + 1))
        labels = sample_chart_labels(
            count=int(candle_count),
            instance_seed=int(hash64(int(instance_seed), "candlestick.labels", int(attempt))),
            namespace=f"{SCENE_NAMESPACE}.labels:{int(candle_count)}",
        )
        body_sizes = list(range(int(body_min), int(body_max) + 1))
        rng.shuffle(body_sizes)
        body_sizes = body_sizes[: int(candle_count)]
        candles: list[Candle] = []
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
                Candle(
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


def range_extremum_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    range_kind: str,
    extremum: str,
) -> Dataset:
    candles = sample_candles(params, instance_seed=int(instance_seed))
    if str(range_kind) not in {"wick", "body"}:
        raise ValueError(f"unsupported candlestick range kind: {range_kind}")
    if str(extremum) not in {"largest", "smallest"}:
        raise ValueError(f"unsupported candlestick extremum: {extremum}")
    scored = [
        (
            int(candle.wick_range if str(range_kind) == "wick" else candle.body_size),
            candle,
        )
        for candle in candles
    ]
    scored.sort(key=lambda item: (int(item[0]), str(item[1].label)))
    target = scored[-1][1] if str(extremum) == "largest" else scored[0][1]
    if str(range_kind) == "wick":
        value_ids = (f"{target.candle_id}:high", f"{target.candle_id}:low")
        range_phrase = "high-low wick range"
        annotation_roles = ("answer_wick",)
        answer_range = int(target.wick_range)
    else:
        value_ids = (f"{target.candle_id}:open", f"{target.candle_id}:close")
        range_phrase = "open-close body size"
        annotation_roles = ("answer_body",)
        answer_range = int(target.body_size)
    selection = Selection(
        answer=str(target.label),
        answer_type="string",
        annotation_candle_ids=(str(target.candle_id),),
        annotation_label_ids=(f"x_label:{target.candle_id}", *value_ids),
        annotation_roles=tuple(annotation_roles),
        trace={
            "range_kind": str(range_kind),
            "range_kind_phrase": str(range_phrase),
            "extremum": str(extremum),
            "extremum_phrase": str(extremum),
            "answer_candle_id": str(target.candle_id),
            "answer_label": str(target.label),
            "answer_range_value": int(answer_range),
            "candle_count": int(len(candles)),
        },
    )
    return Dataset(candles=tuple(candles), selection=selection)


def counterfactual_close_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    change_direction: str,
) -> Dataset:
    candles = sample_candles(params, instance_seed=int(instance_seed))
    change_min, change_max = resolve_required_int_bounds(
        params,
        GENERATION_DEFAULTS,
        min_key="counterfactual_change_min",
        max_key="counterfactual_change_max",
        fallback_min=2,
        fallback_max=6,
        context="candlestick counterfactual body-size change",
    )
    increase = str(change_direction) == "increase"
    if str(change_direction) not in {"increase", "decrease"}:
        raise ValueError(f"unsupported body-size change direction: {change_direction}")
    index_seed = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.counterfactual.target",
    )
    candidates = list(candles)
    start_index = int(index_seed) % len(candidates)
    candidates = candidates[start_index:] + candidates[:start_index]
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
        answer = int(candidate.open_value) + int(new_body) if str(candidate.direction) == "up" else int(candidate.open_value) - int(new_body)
        if 1 <= int(answer) <= 99:
            selection = Selection(
                answer=int(answer),
                answer_type="integer",
                annotation_candle_ids=(str(candidate.candle_id),),
                annotation_label_ids=(
                    f"x_label:{candidate.candle_id}",
                    f"{candidate.candle_id}:open",
                    f"{candidate.candle_id}:close",
                ),
                annotation_roles=("target_body",),
                trace={
                    "target_candle_id": str(candidate.candle_id),
                    "target_label": str(candidate.label),
                    "target_direction": str(candidate.direction),
                    "change_value": int(change),
                    "change_direction": str(change_direction),
                    "change_phrase": "increased" if increase else "decreased",
                    "change_verb": "increase" if increase else "decrease",
                    "change_past_phrase": "increased" if increase else "decreased",
                    "current_body_size": int(current_body),
                    "new_body_size": int(new_body),
                    "candle_count": int(len(candles)),
                },
            )
            return Dataset(candles=tuple(candles), selection=selection)
    raise ValueError("no feasible counterfactual close target")


def draw_candlesticks(
    base_image: Image.Image,
    *,
    dataset: Dataset,
    render_params: RenderParams,
) -> Rendered:
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
    draw_text_traced(
        draw,
        (left, max(12, top - 50)),
        "OHLC candlestick chart",
        font=title_font,
        fill=tuple(render_params.text_color_rgb),
        role="readout",
        required=False,
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
        draw_text_traced(
            draw,
            (left - int(render_params.tick_length_px) - 8 - (bbox[2] - bbox[0]), y - (bbox[3] - bbox[1]) / 2),
            text,
            font=tick_font,
            fill=tuple(render_params.muted_text_rgb),
            role="readout",
            required=False,
        )
    draw.line([left, bottom, right, bottom], fill=tuple(render_params.axis_color_rgb), width=int(render_params.axis_line_width_px))
    draw.line([left, top, left, bottom], fill=tuple(render_params.axis_color_rgb), width=int(render_params.axis_line_width_px))

    slot_count = len(dataset.candles)
    slot_w = plot_w / float(slot_count)
    body_w = max(30.0, min(54.0, slot_w * float(render_params.candle_width_fraction)))
    candle_bboxes: dict[str, BBox] = {}
    body_bboxes: dict[str, BBox] = {}
    wick_bboxes: dict[str, BBox] = {}
    value_label_bboxes: dict[str, BBox] = {}
    x_label_bboxes: dict[str, BBox] = {}
    entities: list[dict[str, Any]] = []

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

    return Rendered(
        image=image,
        entities=tuple(entities),
        plot_bbox_px=list(plot_bbox),
        candle_bboxes_px=dict(candle_bboxes),
        body_bboxes_px=dict(body_bboxes),
        wick_bboxes_px=dict(wick_bboxes),
        value_label_bboxes_px=dict(value_label_bboxes),
        x_label_bboxes_px=dict(x_label_bboxes),
    )


def render_dataset(
    *,
    dataset: Dataset,
    params: Mapping[str, Any],
    instance_seed: int,
) -> RenderArtifacts:
    render_params = resolve_render_params(params, instance_seed=int(instance_seed))
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=dict(params),
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    chart_font_family = sample_chart_font_family(
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.chart_font",
        params=params,
    )
    with temporary_default_font_family(str(chart_font_family)):
        rendered = draw_candlesticks(background, dataset=dataset, render_params=render_params)
    image, post_noise_meta = apply_post_image_noise(
        rendered.image,
        instance_seed=int(instance_seed),
        params=dict(params),
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    rendered = Rendered(
        image=image,
        entities=tuple(dict(entity) for entity in rendered.entities),
        plot_bbox_px=list(rendered.plot_bbox_px),
        candle_bboxes_px=dict(rendered.candle_bboxes_px),
        body_bboxes_px=dict(rendered.body_bboxes_px),
        wick_bboxes_px=dict(rendered.wick_bboxes_px),
        value_label_bboxes_px=dict(rendered.value_label_bboxes_px),
        x_label_bboxes_px=dict(rendered.x_label_bboxes_px),
    )
    return RenderArtifacts(
        rendered=rendered,
        render_params=render_params,
        background_style=dict(background_meta),
        font_assets=chart_font_asset_metadata(str(chart_font_family)),
        post_image_noise=dict(post_noise_meta),
    )


def annotation_boxes_and_points(
    *,
    rendered: Rendered,
    selection: Selection,
) -> tuple[list[BBox], list[Point]]:
    annotation_boxes: list[BBox] = []
    annotation_points: list[Point] = []
    for role, candle_id in zip(selection.annotation_roles, selection.annotation_candle_ids):
        if str(role).endswith("_wick"):
            annotation_box = list(rendered.wick_bboxes_px[str(candle_id)])
        else:
            annotation_box = list(rendered.body_bboxes_px[str(candle_id)])
        annotation_boxes.append(list(annotation_box))
        annotation_points.append(_bbox_center(annotation_box))
    return annotation_boxes, annotation_points


def candle_rows(dataset: Dataset) -> list[dict[str, Any]]:
    return [
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


def build_trace_scaffold(
    *,
    dataset: Dataset,
    artifacts: RenderArtifacts,
    relations: Mapping[str, Any],
    witness_symbolic: Mapping[str, Any],
    projected_annotation: Mapping[str, Any],
) -> dict[str, Any]:
    rendered = artifacts.rendered
    render_params = artifacts.render_params
    return {
        "scene_ir": {
            "scene_kind": "chart_candlestick_ohlc",
            "entities": [dict(entity) for entity in rendered.entities],
            "relations": dict(relations),
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
            "background_style": dict(artifacts.background_style),
            "font_assets": dict(artifacts.font_assets),
            "post_image_noise": dict(artifacts.post_image_noise),
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
            "question_format": "candlestick_ohlc_query",
            "answer": dataset.selection.answer,
            "answer_type": str(dataset.selection.answer_type),
            "candle_count": int(len(dataset.candles)),
            "candles": candle_rows(dataset),
            "annotation_candle_ids": list(dataset.selection.annotation_candle_ids),
            "support_label_ids": list(dataset.selection.annotation_label_ids),
            "annotation_roles": list(dataset.selection.annotation_roles),
            **dict(relations),
        },
        "witness_symbolic": dict(witness_symbolic),
        "projected_annotation": dict(projected_annotation),
    }


__all__ = [
    "Dataset",
    "DOMAIN",
    "PROMPT_BUNDLE_ID",
    "PROMPT_DEFAULTS",
    "SCENE_ID",
    "annotation_boxes_and_points",
    "build_trace_scaffold",
    "counterfactual_close_dataset",
    "range_extremum_dataset",
    "render_dataset",
]
