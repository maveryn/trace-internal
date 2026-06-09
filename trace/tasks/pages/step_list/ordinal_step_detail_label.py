"""Numbered step-list page lookup task."""

from __future__ import annotations

import json
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
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import fit_font_to_box, load_font
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ...shared.text_legibility import draw_text_traced
from ..shared.complexity import build_pages_complexity, normalize_int_with_bounds, resolve_pages_complexity_weights
from ..shared.fixed_query_task import FixedPagesQueryTaskMixin, MergedPagesQueryTaskMixin
from ..shared.page_text_resources import page_text_resource_metadata, sample_page_context_batch, sample_page_label_batch
from ..shared.visual_defaults import load_pages_background_defaults, load_pages_noise_defaults


TASK_ID = "pages_step_list_ordinal_step_detail_source"
PUBLIC_SCENE_ID = "step_list"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "nth_step_title",
    "nth_step_detail",
    "step_after_named_step",
    "step_title_for_detail",
    "step_number_for_detail",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "vertical_cards",
    "horizontal_cards",
    "two_column_cards",
)
SUPPORTED_ORDINAL_REFERENCES: Tuple[str, ...] = ("first", "interior", "final")

_CARD_PALETTE: Tuple[Tuple[int, int, int], ...] = (
    (61, 119, 175),
    (45, 142, 113),
    (193, 94, 77),
    (130, 105, 184),
    (198, 145, 61),
    (77, 132, 95),
    (59, 107, 145),
    (172, 88, 132),
)
_SCENE_LOAD_BY_VARIANT: Dict[str, float] = {
    "vertical_cards": 0.42,
    "horizontal_cards": 0.50,
    "two_column_cards": 0.46,
}
_REASONING_LOAD_BY_QUERY: Dict[str, float] = {
    "nth_step_title": 0.38,
    "nth_step_detail": 0.44,
    "step_after_named_step": 0.58,
    "step_title_for_detail": 0.54,
    "step_number_for_detail": 0.50,
}


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    outer_margin_px: int
    header_height_px: int
    card_gap_px: int
    card_corner_radius_px: int
    card_outline_width_px: int
    number_badge_size_px: int
    title_font_size_px: int
    subtitle_font_size_px: int
    step_title_font_size_px: int
    step_detail_font_size_px: int


@dataclass(frozen=True)
class _StepSpec:
    step_id: str
    order_index: int
    step_number: int
    title: str
    detail: str
    accent_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class _RenderedStepList:
    image: Image.Image
    entities: List[Dict[str, Any]]
    card_traces: List[Dict[str, Any]]
    panel_bbox_px: List[float]
    title_bbox_px: List[float]
    layout_meta: Dict[str, Any]


_TASK_GROUP_DEFAULTS = get_task_group_defaults("pages", "step_list")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_pages_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_pages_background_defaults(task_group="step_list")
POST_IMAGE_NOISE_DEFAULTS = load_pages_noise_defaults(task_group="step_list", apply_prob=0.0)


def _resolve_named_variant(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    supported: Sequence[str],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    namespace: str,
) -> Tuple[str, Dict[str, float]]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{namespace}")
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=[str(value) for value in supported],
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
    )
    balanced = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=[str(value) for value in supported],
        balance_flag_key=str(balance_flag_key),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        sampling_namespace=f"{TASK_ID}.{namespace}",
    )
    if str(balanced) != str(selected) and params.get(str(explicit_key)) is not None:
        return str(balanced), {str(key): (1.0 if str(key) == str(balanced) else 0.0) for key in supported}
    return str(balanced), dict(probabilities)


def _resolve_int_support(params: Mapping[str, Any], key: str, fallback: Sequence[int]) -> Tuple[int, ...]:
    raw_values = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), fallback))
    values: List[int] = []
    for raw_value in raw_values:
        value = int(raw_value)
        if value not in values:
            values.append(value)
    if not values:
        raise ValueError(f"{key} must not be empty for {TASK_ID}")
    return tuple(int(value) for value in values)


def _resolve_step_count(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
) -> Tuple[int, Tuple[int, ...], Dict[str, float]]:
    support = _resolve_int_support(params, "step_count_support", (5, 6, 7, 8))
    explicit = params.get("step_count")
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(support):
            raise ValueError(f"step_count must be in {support}")
        return int(selected), tuple(support), {str(int(selected)): 1.0}
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.step_count",
    )
    selected = int(support[int(index) % len(support)])
    probability = 1.0 / float(len(support))
    return int(selected), tuple(support), {str(value): float(probability) for value in support}


def _ordinal_label(index: int, *, final_index: int) -> str:
    if int(index) == 0:
        return "first"
    if int(index) == int(final_index):
        return "final"
    number = int(index) + 1
    if 10 <= (number % 100) <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def _resolve_target_index(
    *,
    query_id: str,
    params: Mapping[str, Any],
    step_count: int,
    instance_seed: int,
) -> Tuple[int, int | None, str, Dict[str, float]]:
    if str(query_id) == "step_after_named_step":
        max_source = int(step_count) - 2
        if max_source < 0:
            raise ValueError("step_after_named_step requires at least two steps")
        explicit_source = params.get("source_step_index")
        if explicit_source is not None:
            source_index = int(explicit_source)
            if source_index < 0 or source_index > int(max_source):
                raise ValueError(f"source_step_index must be in 0..{max_source}")
        else:
            source_index = int(
                resolve_selection_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    namespace=f"{TASK_ID}.source_step_index.{step_count}",
                )
                % (int(max_source) + 1)
            )
        return int(source_index) + 1, int(source_index), "after_named", {"after_named": 1.0}

    explicit_index = params.get("target_step_index")
    if explicit_index is not None:
        target_index = int(explicit_index)
        if target_index < 0 or target_index >= int(step_count):
            raise ValueError(f"target_step_index must be in 0..{int(step_count) - 1}")
        reference = _ordinal_label(int(target_index), final_index=int(step_count) - 1)
        return int(target_index), None, str(reference), {str(reference): 1.0}

    if str(query_id) in {"step_title_for_detail", "step_number_for_detail"}:
        target_index = int(
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.detail_lookup_step_index.{query_id}.{step_count}",
            )
            % int(step_count)
        )
        probabilities = {str(index + 1): 1.0 / float(step_count) for index in range(int(step_count))}
        return (
            int(target_index),
            None,
            _ordinal_label(int(target_index), final_index=int(step_count) - 1),
            dict(probabilities),
        )

    ordinal_reference, ordinal_probabilities = _resolve_named_variant(
        params=params,
        instance_seed=int(instance_seed),
        supported=SUPPORTED_ORDINAL_REFERENCES,
        explicit_key="ordinal_reference",
        weights_key="ordinal_reference_weights",
        balance_flag_key="balanced_ordinal_reference_sampling",
        namespace=f"ordinal_reference.{query_id}",
    )
    if str(ordinal_reference) == "first":
        target_index = 0
    elif str(ordinal_reference) == "final":
        target_index = int(step_count) - 1
    else:
        interior_count = max(1, int(step_count) - 2)
        target_index = 1 + int(
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.interior_step_index.{query_id}.{step_count}",
            )
            % int(interior_count)
        )
    return (
        int(target_index),
        None,
        _ordinal_label(int(target_index), final_index=int(step_count) - 1),
        dict(ordinal_probabilities),
    )


def _resolve_render_params(params: Mapping[str, Any]) -> _RenderParams:
    def _int_value(key: str, fallback: int, *, minimum: int = 1) -> int:
        return max(int(minimum), int(params.get(key, group_default(_RENDER_DEFAULTS, key, fallback))))

    return _RenderParams(
        canvas_width=_int_value("canvas_width", 1000, minimum=320),
        canvas_height=_int_value("canvas_height", 820, minimum=320),
        outer_margin_px=_int_value("outer_margin_px", 34, minimum=0),
        header_height_px=_int_value("header_height_px", 86, minimum=40),
        card_gap_px=_int_value("card_gap_px", 14, minimum=4),
        card_corner_radius_px=_int_value("card_corner_radius_px", 14, minimum=0),
        card_outline_width_px=_int_value("card_outline_width_px", 2, minimum=1),
        number_badge_size_px=_int_value("number_badge_size_px", 38, minimum=20),
        title_font_size_px=_int_value("title_font_size_px", 30, minimum=14),
        subtitle_font_size_px=_int_value("subtitle_font_size_px", 17, minimum=10),
        step_title_font_size_px=_int_value("step_title_font_size_px", 22, minimum=12),
        step_detail_font_size_px=_int_value("step_detail_font_size_px", 17, minimum=10),
    )


def _text_bbox(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    font: Any,
    *,
    stroke_width: int = 0,
) -> List[float]:
    try:
        bbox = draw.textbbox((float(xy[0]), float(xy[1])), str(text), font=font, stroke_width=int(stroke_width))
        return [float(value) for value in bbox]
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        return [float(xy[0]), float(xy[1]), float(xy[0]) + float(width), float(xy[1]) + float(height)]


def _draw_text(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    font: Any,
    fill: Tuple[int, int, int],
) -> List[float]:
    draw_text_traced(draw,(float(xy[0]), float(xy[1])), str(text), fill=fill, font=font, role="readout", required=False)
    return _text_bbox(draw, xy, str(text), font)


def _blend_rgb(color_a: Sequence[int], color_b: Sequence[int], weight_b: float) -> Tuple[int, int, int]:
    weight = max(0.0, min(1.0, float(weight_b)))
    return tuple(
        int(round((float(color_a[index]) * (1.0 - weight)) + (float(color_b[index]) * weight)))
        for index in range(3)
    )


def _layout_card_bboxes(
    *,
    scene_variant: str,
    step_count: int,
    render_params: _RenderParams,
) -> Tuple[List[List[float]], Dict[str, Any]]:
    width = int(render_params.canvas_width)
    height = int(render_params.canvas_height)
    margin = int(render_params.outer_margin_px)
    gap = int(render_params.card_gap_px)
    top = float(margin + render_params.header_height_px)
    left = float(margin)
    right = float(width - margin)
    bottom = float(height - margin)
    inner_w = max(1.0, right - left)
    inner_h = max(1.0, bottom - top)
    bboxes: List[List[float]] = []

    if str(scene_variant) == "vertical_cards":
        card_h = (inner_h - (float(step_count - 1) * float(gap))) / float(step_count)
        for index in range(int(step_count)):
            y0 = top + (float(index) * (card_h + float(gap)))
            bboxes.append([left, y0, right, y0 + card_h])
        return bboxes, {"layout_columns": 1, "layout_rows": int(step_count)}

    if str(scene_variant) == "two_column_cards":
        columns = 2
        rows = int((int(step_count) + 1) // 2)
    else:
        rows = 2 if int(step_count) > 4 else 1
        columns = int((int(step_count) + int(rows) - 1) // int(rows))

    card_w = (inner_w - (float(columns - 1) * float(gap))) / float(columns)
    card_h = (inner_h - (float(rows - 1) * float(gap))) / float(rows)
    for index in range(int(step_count)):
        row = int(index) // int(columns)
        col = int(index) % int(columns)
        x0 = left + (float(col) * (card_w + float(gap)))
        y0 = top + (float(row) * (card_h + float(gap)))
        bboxes.append([x0, y0, x0 + card_w, y0 + card_h])
    return bboxes, {"layout_columns": int(columns), "layout_rows": int(rows)}


def _build_steps(*, step_count: int, instance_seed: int) -> Tuple[List[_StepSpec], str, str, Dict[str, Any]]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.steps")
    title_batch = sample_page_context_batch(
        rng,
        role="step_list_panel_title",
        count=1,
        manifest_names=("phrases/headlines.txt",),
        max_chars=28,
    )
    subtitle_batch = sample_page_context_batch(
        rng,
        role="step_list_panel_subtitle",
        count=1,
        manifest_names=("phrases/captions.txt", "phrases/legend_notes.txt"),
        max_chars=40,
    )
    step_title_batch = sample_page_label_batch(
        rng,
        role="step_list_step_title",
        count=int(step_count),
        manifest_name="panel_titles/technical_topics.txt",
        min_chars=3,
        max_chars=10,
        allow_spaces=True,
        allow_punctuation=False,
    )
    detail_batch = sample_page_context_batch(
        rng,
        role="step_list_step_detail",
        count=int(step_count),
        manifest_names=("phrases/callout_phrases.txt",),
        max_chars=16,
    )
    titles = list(step_title_batch.values)
    details = list(detail_batch.values)
    panel_title = str(title_batch.values[0])
    panel_subtitle = str(subtitle_batch.values[0])
    steps: List[_StepSpec] = []
    color_offset = int(rng.randrange(len(_CARD_PALETTE)))
    for index in range(int(step_count)):
        accent = _CARD_PALETTE[(int(index) + int(color_offset)) % len(_CARD_PALETTE)]
        steps.append(
            _StepSpec(
                step_id=f"step_{index + 1}",
                order_index=int(index),
                step_number=int(index) + 1,
                title=str(titles[int(index)]),
                detail=str(details[int(index)]),
                accent_rgb=tuple(int(channel) for channel in accent),
            )
        )
    return (
        steps,
        panel_title,
        panel_subtitle,
        page_text_resource_metadata(title_batch, subtitle_batch, step_title_batch, detail_batch),
    )


def _render_step_list(
    background: Image.Image,
    *,
    steps: Sequence[_StepSpec],
    panel_title: str,
    panel_subtitle: str,
    scene_variant: str,
    render_params: _RenderParams,
) -> _RenderedStepList:
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    width = int(render_params.canvas_width)
    height = int(render_params.canvas_height)
    margin = int(render_params.outer_margin_px)
    panel_bbox = [float(margin), float(margin), float(width - margin), float(height - margin)]
    card_fill = (255, 255, 255)
    panel_fill = (249, 250, 250)
    panel_outline = (205, 212, 220)
    text_rgb = (35, 42, 50)
    muted_rgb = (91, 101, 113)

    draw.rounded_rectangle(
        tuple(panel_bbox),
        radius=18,
        fill=panel_fill,
        outline=panel_outline,
        width=2,
    )
    title_font = load_font(int(render_params.title_font_size_px), bold=True)
    subtitle_font = load_font(int(render_params.subtitle_font_size_px), bold=False)
    title_xy = (float(margin + 24), float(margin + 18))
    title_bbox = _draw_text(draw, title_xy, str(panel_title), title_font, text_rgb)
    _draw_text(draw, (title_xy[0], title_xy[1] + 38.0), str(panel_subtitle), subtitle_font, muted_rgb)

    card_bboxes, layout_meta = _layout_card_bboxes(
        scene_variant=str(scene_variant),
        step_count=len(steps),
        render_params=render_params,
    )
    card_traces: List[Dict[str, Any]] = []
    entities: List[Dict[str, Any]] = []
    for step, card_bbox in zip(steps, card_bboxes):
        x0, y0, x1, y1 = [float(value) for value in card_bbox]
        accent = tuple(int(channel) for channel in step.accent_rgb)
        local_fill = _blend_rgb(card_fill, accent, 0.035)
        draw.rounded_rectangle(
            (x0, y0, x1, y1),
            radius=int(render_params.card_corner_radius_px),
            fill=local_fill,
            outline=panel_outline,
            width=int(render_params.card_outline_width_px),
        )
        draw.rounded_rectangle(
            (x0, y0, x1, y0 + 7.0),
            radius=int(render_params.card_corner_radius_px),
            fill=accent,
        )

        badge_size = float(render_params.number_badge_size_px)
        badge_x0 = x0 + 16.0
        badge_y0 = y0 + 22.0
        badge_bbox = [badge_x0, badge_y0, badge_x0 + badge_size, badge_y0 + badge_size]
        draw.ellipse(tuple(badge_bbox), fill=accent, outline=_blend_rgb(accent, (0, 0, 0), 0.18), width=2)
        number_font = fit_font_to_box(
            draw,
            text=str(step.step_number),
            max_width=badge_size - 8.0,
            max_height=badge_size - 8.0,
            bold=True,
            min_size_px=12,
            max_size_px=22,
            fill_ratio=0.95,
        )
        number_bbox_measure = _text_bbox(draw, (0.0, 0.0), str(step.step_number), number_font)
        number_w = number_bbox_measure[2] - number_bbox_measure[0]
        number_h = number_bbox_measure[3] - number_bbox_measure[1]
        number_xy = (
            badge_x0 + ((badge_size - number_w) * 0.5),
            badge_y0 + ((badge_size - number_h) * 0.46) - 1.0,
        )
        number_bbox = _draw_text(draw, number_xy, str(step.step_number), number_font, (255, 255, 255))

        text_left = badge_x0 + badge_size + 16.0
        text_right = x1 - 18.0
        title_font = fit_font_to_box(
            draw,
            text=str(step.title),
            max_width=max(30.0, text_right - text_left),
            max_height=30.0,
            bold=True,
            min_size_px=12,
            max_size_px=int(render_params.step_title_font_size_px),
            fill_ratio=0.97,
        )
        detail_font = fit_font_to_box(
            draw,
            text=str(step.detail),
            max_width=max(30.0, text_right - text_left),
            max_height=26.0,
            bold=False,
            min_size_px=10,
            max_size_px=int(render_params.step_detail_font_size_px),
            fill_ratio=0.97,
        )
        text_top = y0 + 21.0
        if (y1 - y0) > 115.0:
            text_top = y0 + 36.0
        title_bbox_step = _draw_text(draw, (text_left, text_top), str(step.title), title_font, text_rgb)
        detail_bbox = _draw_text(draw, (text_left, text_top + 34.0), str(step.detail), detail_font, muted_rgb)

        trace = {
            "step_id": str(step.step_id),
            "order_index": int(step.order_index),
            "step_number": int(step.step_number),
            "title": str(step.title),
            "detail": str(step.detail),
            "card_bbox_px": [float(value) for value in card_bbox],
            "number_bbox_px": [float(value) for value in number_bbox],
            "title_bbox_px": [float(value) for value in title_bbox_step],
            "detail_bbox_px": [float(value) for value in detail_bbox],
            "accent_rgb": [int(channel) for channel in accent],
        }
        entity = {
            "id": str(step.step_id),
            "type": "step_list_card",
            "bbox_px": [float(value) for value in card_bbox],
            "attrs": {
                "order_index": int(step.order_index),
                "step_number": int(step.step_number),
                "title": str(step.title),
                "detail": str(step.detail),
            },
        }
        card_traces.append(trace)
        entities.append(entity)

    return _RenderedStepList(
        image=image,
        entities=entities,
        card_traces=card_traces,
        panel_bbox_px=list(panel_bbox),
        title_bbox_px=list(title_bbox),
        layout_meta={
            "scene_variant": str(scene_variant),
            "card_count": int(len(steps)),
            **dict(layout_meta),
        },
    )


def _bbox_maps(
    card_traces: Sequence[Mapping[str, Any]],
) -> Tuple[Dict[str, List[float]], Dict[str, List[float]], Dict[str, List[float]], Dict[str, List[float]]]:
    card_map = {str(card["step_id"]): [float(value) for value in card["card_bbox_px"]] for card in card_traces}
    number_map = {str(card["step_id"]): [float(value) for value in card["number_bbox_px"]] for card in card_traces}
    title_map = {str(card["step_id"]): [float(value) for value in card["title_bbox_px"]] for card in card_traces}
    detail_map = {str(card["step_id"]): [float(value) for value in card["detail_bbox_px"]] for card in card_traces}
    return card_map, number_map, title_map, detail_map


def _annotation_bbox_map(
    *,
    query_id: str,
    target_step_id: str,
    source_step_id: str | None,
    number_bbox_map: Mapping[str, Sequence[float]],
    title_bbox_map: Mapping[str, Sequence[float]],
    detail_bbox_map: Mapping[str, Sequence[float]],
) -> Dict[str, List[float]]:
    if str(query_id) == "nth_step_title":
        return {"target_title": [float(value) for value in title_bbox_map[str(target_step_id)]]}
    if str(query_id) == "nth_step_detail":
        return {"target_detail": [float(value) for value in detail_bbox_map[str(target_step_id)]]}
    if str(query_id) == "step_after_named_step":
        if source_step_id is None:
            raise ValueError("step_after_named_step requires source_step_id")
        return {
            "source_title": [float(value) for value in title_bbox_map[str(source_step_id)]],
            "target_title": [float(value) for value in title_bbox_map[str(target_step_id)]],
        }
    if str(query_id) == "step_title_for_detail":
        return {
            "source_detail": [float(value) for value in detail_bbox_map[str(target_step_id)]],
            "target_title": [float(value) for value in title_bbox_map[str(target_step_id)]],
        }
    if str(query_id) == "step_number_for_detail":
        return {
            "source_detail": [float(value) for value in detail_bbox_map[str(target_step_id)]],
            "target_number": [float(value) for value in number_bbox_map[str(target_step_id)]],
        }
    raise ValueError(f"unsupported query_id: {query_id}")


def _build_prompt_examples(*, query_id: str) -> Tuple[str, str]:
    example_answer = "Review packet" if str(query_id) == "nth_step_detail" else "Review"
    annotation: Dict[str, List[int]] = {"target_title": [220, 216, 340, 244]}
    if str(query_id) == "nth_step_detail":
        annotation = {"target_detail": [220, 216, 370, 244]}
    if str(query_id) == "step_after_named_step":
        annotation = {"source_title": [120, 160, 210, 188], "target_title": [220, 216, 300, 244]}
    if str(query_id) == "step_title_for_detail":
        annotation = {"source_detail": [220, 250, 370, 278], "target_title": [220, 216, 340, 244]}
    if str(query_id) == "step_number_for_detail":
        example_answer = "3"
        annotation = {"source_detail": [220, 250, 370, 278], "target_number": [170, 214, 200, 244]}
    answer_and_annotation = {"annotation": annotation, "answer": example_answer}
    answer_only = {"answer": example_answer}
    return (
        json.dumps(answer_and_annotation, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
    )


class PagesStepListOrdinalStepDetailLabelTask:
    """Read one title/detail from a numbered page step-list."""

    task_id = TASK_ID
    domain = "pages"
    task_group = "step_list"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_named_variant(
            params=params,
            instance_seed=int(instance_seed),
            supported=SUPPORTED_QUERY_IDS,
            explicit_key="query_id",
            weights_key="query_id_weights",
            balance_flag_key="balanced_query_id_sampling",
            namespace="query_id",
        )
        scene_variant, scene_variant_probabilities = _resolve_named_variant(
            params=params,
            instance_seed=int(instance_seed),
            supported=SUPPORTED_SCENE_VARIANTS,
            explicit_key="scene_variant",
            weights_key="scene_variant_weights",
            balance_flag_key="balanced_scene_variant_sampling",
            namespace="scene_variant",
        )
        step_count, step_count_support, step_count_probabilities = _resolve_step_count(
            params,
            instance_seed=int(instance_seed),
        )
        target_index, source_index, step_reference, ordinal_reference_probabilities = _resolve_target_index(
            query_id=str(query_id),
            params=params,
            step_count=int(step_count),
            instance_seed=int(instance_seed),
        )
        steps, panel_title, panel_subtitle, page_text_resources = _build_steps(
            step_count=int(step_count),
            instance_seed=int(instance_seed),
        )
        target_step = steps[int(target_index)]
        source_step = steps[int(source_index)] if source_index is not None else None
        if str(query_id) in {"nth_step_title", "step_after_named_step", "step_title_for_detail"}:
            answer_value = str(target_step.title)
        elif str(query_id) == "step_number_for_detail":
            answer_value = str(target_step.step_number)
        else:
            answer_value = str(target_step.detail)

        render_params = _resolve_render_params(params)
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered = _render_step_list(
            background,
            steps=steps,
            panel_title=str(panel_title),
            panel_subtitle=str(panel_subtitle),
            scene_variant=str(scene_variant),
            render_params=render_params,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        card_bbox_map, number_bbox_map, title_bbox_map, detail_bbox_map = _bbox_maps(rendered.card_traces)
        annotation_bbox_map = _annotation_bbox_map(
            query_id=str(query_id),
            target_step_id=str(target_step.step_id),
            source_step_id=str(source_step.step_id) if source_step is not None else None,
            number_bbox_map=number_bbox_map,
            title_bbox_map=title_bbox_map,
            detail_bbox_map=detail_bbox_map,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                f"annotation_hint_{str(query_id)}",
                "object_description_vertical_cards",
                "object_description_horizontal_cards",
                "object_description_two_column_cards",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        json_example, json_example_answer_only = _build_prompt_examples(query_id=str(query_id))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "step_reference": str(step_reference),
                "source_step_title": f'"{str(source_step.title)}"' if source_step is not None else "",
                "source_step_detail": f'"{str(target_step.detail)}"',
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(query_id)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="string", value=str(answer_value))
        annotation_gt = TypedValue(type="keyed_bbox_map", value=dict(annotation_bbox_map))
        source_step_payload = None
        if source_step is not None:
            source_step_payload = {
                "step_id": str(source_step.step_id),
                "order_index": int(source_step.order_index),
                "step_number": int(source_step.step_number),
                "title": str(source_step.title),
                "detail": str(source_step.detail),
            }
        target_step_payload = {
            "step_id": str(target_step.step_id),
            "order_index": int(target_step.order_index),
            "step_number": int(target_step.step_number),
            "title": str(target_step.title),
            "detail": str(target_step.detail),
        }
        trace_payload = {
            "scene_ir": {
                "scene_id": PUBLIC_SCENE_ID,
                "scene_kind": "pages_step_list_cards",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "step_count": int(step_count),
                    "target_step": dict(target_step_payload),
                    "source_step": dict(source_step_payload) if source_step_payload is not None else None,
                    "answer_value": str(answer_value),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "step_count": int(step_count),
                    "step_reference": str(step_reference),
                    "source_step_detail": str(target_step.detail),
                    "target_step_index": int(target_index),
                    "source_step_index": int(source_index) if source_index is not None else None,
                    "target_answer": str(answer_value),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "ordinal_reference_probabilities": dict(ordinal_reference_probabilities),
                    "step_count_probabilities": dict(step_count_probabilities),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_id": PUBLIC_SCENE_ID,
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "panel_bbox_px": list(rendered.panel_bbox_px),
                "layout": dict(rendered.layout_meta),
                "text_style": {
                    "title_font_size_px": int(render_params.title_font_size_px),
                    "step_title_font_size_px": int(render_params.step_title_font_size_px),
                    "step_detail_font_size_px": int(render_params.step_detail_font_size_px),
                },
                "page_text_resources": dict(page_text_resources),
            },
            "render_map": {
                "image_id": "img0",
                "panel_bbox_px": list(rendered.panel_bbox_px),
                "document_title_bbox_px": list(rendered.title_bbox_px),
                "card_bboxes_px": dict(card_bbox_map),
                "number_bboxes_px": dict(number_bbox_map),
                "title_bboxes_px": dict(title_bbox_map),
                "detail_bboxes_px": dict(detail_bbox_map),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "question_format": "step_list_lookup_label",
                "step_count": int(step_count),
                "step_count_support": [int(value) for value in step_count_support],
                "step_reference": str(step_reference),
                "source_step_detail": str(target_step.detail),
                "target_step": dict(target_step_payload),
                "source_step": dict(source_step_payload) if source_step_payload is not None else None,
                "answer_value": str(answer_value),
                "steps": [dict(card) for card in rendered.card_traces],
                "page_text_resources": dict(page_text_resources),
                "query_id_probabilities": dict(query_id_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "ordinal_reference_probabilities": dict(ordinal_reference_probabilities),
                "step_count_probabilities": dict(step_count_probabilities),
            },
            "witness_symbolic": {
                "type": "step_list_lookup",
                "target_step_id": str(target_step.step_id),
                "source_step_id": str(source_step.step_id) if source_step is not None else "",
                "answer_value": str(answer_value),
                "annotation_roles": sorted(str(key) for key in annotation_bbox_map.keys()),
            },
            "projected_annotation": {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(annotation_bbox_map),
                "pixel_keyed_bbox_map": dict(annotation_bbox_map),
                "target_step_id": str(target_step.step_id),
                "source_step_id": str(source_step.step_id) if source_step is not None else "",
            },
        }
        complexity = build_pages_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "order_lookup": float(_REASONING_LOAD_BY_QUERY[str(query_id)]),
                "visual_scan": normalize_int_with_bounds(
                    int(step_count),
                    [min(step_count_support), max(step_count_support)],
                ),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class PagesStepListNthStepTitleLabelTask(FixedPagesQueryTaskMixin):
    """Return the title of an ordinally referenced step."""

    task_id = "task_pages__step_list__nth_step_title_label"
    domain = "pages"
    task_group = "step_list"
    public_scene_id = PUBLIC_SCENE_ID
    fixed_query_id = "nth_step_title"
    source_task_cls = PagesStepListOrdinalStepDetailLabelTask


@register_task
class PagesStepListNthStepDetailLabelTask(FixedPagesQueryTaskMixin):
    """Return the detail text of an ordinally referenced step."""

    task_id = "task_pages__step_list__nth_step_detail_label"
    domain = "pages"
    task_group = "step_list"
    public_scene_id = PUBLIC_SCENE_ID
    fixed_query_id = "nth_step_detail"
    source_task_cls = PagesStepListOrdinalStepDetailLabelTask


@register_task
class PagesStepListStepAfterNamedStepLabelTask(FixedPagesQueryTaskMixin):
    """Return the step title immediately after a named source step."""

    task_id = "task_pages__step_list__step_after_named_step_label"
    domain = "pages"
    task_group = "step_list"
    public_scene_id = PUBLIC_SCENE_ID
    fixed_query_id = "step_after_named_step"
    source_task_cls = PagesStepListOrdinalStepDetailLabelTask


@register_task
class PagesStepListStepForDetailLabelTask(MergedPagesQueryTaskMixin):
    """Return the owning step title or number for a named detail line."""

    task_id = "task_pages__step_list__step_for_detail_label"
    domain = "pages"
    task_group = "step_list"
    public_scene_id = PUBLIC_SCENE_ID
    allowed_query_ids = ("step_title_for_detail", "step_number_for_detail")
    source_task_cls = PagesStepListOrdinalStepDetailLabelTask


__all__ = [
    "PagesStepListNthStepDetailLabelTask",
    "PagesStepListNthStepTitleLabelTask",
    "PagesStepListOrdinalStepDetailLabelTask",
    "PagesStepListStepAfterNamedStepLabelTask",
    "PagesStepListStepForDetailLabelTask",
    "SUPPORTED_QUERY_IDS",
    "SUPPORTED_SCENE_VARIANTS",
]
