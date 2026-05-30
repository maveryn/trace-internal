"""Waterfall chart tasks for cumulative-change reasoning."""

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
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.bbox_projection import bbox_union as _bbox_union, round_bbox as _bbox
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_rgb
from ...shared.text_rendering import draw_text_centered, load_font, temporary_default_font_family
from ...shared.text_legibility import draw_text_traced
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin, MergedChartQueryVariantTaskMixin
from ..shared.labeled_chart_common import sample_chart_labels
from ..shared.unanswerable import UNANSWERABLE_ANSWER, absence_proof, should_use_unanswerable_branch
from ..shared.visual_defaults import (
    chart_font_asset_metadata,
    load_chart_background_defaults,
    load_chart_noise_defaults,
    sample_chart_font_family,
)


TASK_ID = "charts_waterfall_panel_query_base"
SCENE_ID = "waterfall"
RUNNING_TOTAL_QUERY_ID = "running_total_after_step"
THRESHOLD_QUERY_IDS: Tuple[str, ...] = (
    "first_total_at_least_threshold",
    "first_total_at_most_threshold",
)
COUNTERFACTUAL_QUERY_IDS: Tuple[str, ...] = (
    "remove_step_final_total",
    "reverse_step_final_total",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    RUNNING_TOTAL_QUERY_ID,
    *THRESHOLD_QUERY_IDS,
    *COUNTERFACTUAL_QUERY_IDS,
)

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "waterfall")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="waterfall")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="waterfall", apply_prob=0.0)

_REASONING_LOAD_BY_QUERY: Dict[str, float] = {
    RUNNING_TOTAL_QUERY_ID: 0.66,
    "first_total_at_least_threshold": 0.72,
    "first_total_at_most_threshold": 0.72,
    "remove_step_final_total": 0.76,
    "reverse_step_final_total": 0.82,
}

RGB = Tuple[int, int, int]
BBox = List[float]


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
class _Step:
    step_id: str
    label: str
    delta: int
    running_before: int
    running_after: int


@dataclass(frozen=True)
class _Query:
    query_id: str
    answer: int | str
    answer_type: str
    evidence_bar_ids: Tuple[str, ...]
    evidence_extra_ids: Tuple[str, ...]
    params: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    start_value: int
    final_value: int
    steps: Tuple[_Step, ...]
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
    connector_width_px: int
    bar_outline_width_px: int
    tick_length_px: int
    title_font_size_px: int
    tick_font_size_px: int
    label_font_size_px: int
    value_font_size_px: int
    threshold_font_size_px: int
    bar_width_fraction: float
    axis_color_rgb: RGB
    grid_color_rgb: RGB
    plot_fill_rgb: RGB
    text_color_rgb: RGB
    muted_text_rgb: RGB
    text_stroke_rgb: RGB
    start_fill_rgb: RGB
    final_fill_rgb: RGB
    positive_fill_rgb: RGB
    negative_fill_rgb: RGB
    connector_rgb: RGB
    threshold_rgb: RGB
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: BBox
    bar_bboxes_px: Dict[str, BBox]
    value_label_bboxes_px: Dict[str, BBox]
    x_label_bboxes_px: Dict[str, BBox]
    connector_bboxes_px: Dict[str, BBox]
    extra_bboxes_px: Dict[str, BBox]
    threshold_value: int | None
    y_axis_max: int


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
    margin_left = _render_int(params, "plot_margin_left_px", 82)
    margin_right = _render_int(params, "plot_margin_right_px", 46)
    margin_top = _render_int(params, "plot_margin_top_px", 70)
    margin_bottom = _render_int(params, "plot_margin_bottom_px", 96)
    margin_left, margin_right, margin_top, margin_bottom, jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(margin_left),
        right_px=int(margin_right),
        top_px=int(margin_top),
        bottom_px=int(margin_bottom),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="charts.waterfall.layout",
    )
    return _RenderParams(
        canvas_width=_render_int(params, "canvas_width", 1180),
        canvas_height=_render_int(params, "canvas_height", 760),
        plot_margin_left_px=int(margin_left),
        plot_margin_right_px=int(margin_right),
        plot_margin_top_px=int(margin_top),
        plot_margin_bottom_px=int(margin_bottom),
        axis_line_width_px=_render_int(params, "axis_line_width_px", 2),
        grid_line_width_px=_render_int(params, "grid_line_width_px", 1),
        connector_width_px=_render_int(params, "connector_width_px", 2),
        bar_outline_width_px=_render_int(params, "bar_outline_width_px", 2),
        tick_length_px=_render_int(params, "tick_length_px", 8),
        title_font_size_px=_render_int(params, "title_font_size_px", 26),
        tick_font_size_px=_render_int(params, "tick_font_size_px", 16),
        label_font_size_px=_render_int(params, "label_font_size_px", 18),
        value_font_size_px=_render_int(params, "value_font_size_px", 17),
        threshold_font_size_px=_render_int(params, "threshold_font_size_px", 16),
        bar_width_fraction=max(0.35, min(0.78, _render_float(params, "bar_width_fraction", 0.56))),
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
        start_fill_rgb=resolve_render_rgb(
            params, _RENDER_DEFAULTS, "start_fill_rgb", (76, 118, 178), instance_seed=int(instance_seed), namespace=TASK_ID
        ),
        final_fill_rgb=resolve_render_rgb(
            params, _RENDER_DEFAULTS, "final_fill_rgb", (58, 92, 150), instance_seed=int(instance_seed), namespace=TASK_ID
        ),
        positive_fill_rgb=resolve_render_rgb(
            params, _RENDER_DEFAULTS, "positive_fill_rgb", (74, 154, 98), instance_seed=int(instance_seed), namespace=TASK_ID
        ),
        negative_fill_rgb=resolve_render_rgb(
            params, _RENDER_DEFAULTS, "negative_fill_rgb", (206, 92, 74), instance_seed=int(instance_seed), namespace=TASK_ID
        ),
        connector_rgb=resolve_render_rgb(
            params, _RENDER_DEFAULTS, "connector_rgb", (126, 134, 148), instance_seed=int(instance_seed), namespace=TASK_ID
        ),
        threshold_rgb=resolve_render_rgb(
            params, _RENDER_DEFAULTS, "threshold_rgb", (102, 91, 168), instance_seed=int(instance_seed), namespace=TASK_ID
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
        index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace="charts.waterfall.query")
        return str(weighted[int(index) % len(weighted)][0]), probabilities

    rng = spawn_rng(int(instance_seed), "charts.waterfall.query")
    threshold = rng.random() * float(total)
    cursor = 0.0
    for query_id, weight in weighted:
        cursor += float(weight)
        if threshold <= cursor:
            return str(query_id), probabilities
    return str(weighted[-1][0]), probabilities


def _sample_steps(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[int, Tuple[_Step, ...]]:
    step_min, step_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="step_count_min",
        max_key="step_count_max",
        fallback_min=6,
        fallback_max=9,
        context="waterfall step count",
    )
    start_min, start_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="start_value_min",
        max_key="start_value_max",
        fallback_min=35,
        fallback_max=65,
        context="waterfall start value",
    )
    delta_min, delta_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="delta_abs_min",
        max_key="delta_abs_max",
        fallback_min=5,
        fallback_max=20,
        context="waterfall delta magnitude",
    )
    total_min, total_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="running_total_min",
        max_key="running_total_max",
        fallback_min=8,
        fallback_max=95,
        context="waterfall running total",
    )

    for attempt in range(200):
        local_rng = spawn_rng(int(instance_seed), "charts.waterfall.steps.retry", int(attempt))
        step_count = int(step_min) + int(local_rng.randrange(int(step_max) - int(step_min) + 1))
        start_value = int(local_rng.randint(int(start_min), int(start_max)))
        labels = sample_chart_labels(
            count=int(step_count),
            instance_seed=int(instance_seed) + int(attempt) * 7919,
            namespace=f"{TASK_ID}.labels:{int(step_count)}",
        )
        current = int(start_value)
        steps: List[_Step] = []
        has_positive = False
        has_negative = False
        for index in range(int(step_count)):
            magnitude = int(local_rng.randint(int(delta_min), int(delta_max)))
            sign = 1 if local_rng.random() < 0.52 else -1
            if current + sign * magnitude > int(total_max):
                sign = -1
            if current + sign * magnitude < int(total_min):
                sign = 1
            delta = int(sign) * int(magnitude)
            next_value = int(current) + int(delta)
            if not (int(total_min) <= int(next_value) <= int(total_max)):
                break
            steps.append(
                _Step(
                    step_id=f"step_{index}",
                    label=str(labels[index]),
                    delta=int(delta),
                    running_before=int(current),
                    running_after=int(next_value),
                )
            )
            current = int(next_value)
            has_positive = bool(has_positive or delta > 0)
            has_negative = bool(has_negative or delta < 0)
        if len(steps) == int(step_count) and has_positive and has_negative:
            return int(start_value), tuple(steps)

    raise ValueError("could not sample a valid waterfall sequence")


def _threshold_options(dataset: _Dataset | Tuple[int, Tuple[_Step, ...]], *, direction: str) -> Tuple[Tuple[int, int], ...]:
    if isinstance(dataset, tuple):
        start_value, steps = dataset
    else:
        start_value, steps = dataset.start_value, dataset.steps
    options: List[Tuple[int, int]] = []
    previous_totals: List[int] = [int(start_value)]
    for index, step in enumerate(steps):
        if str(direction) == "at_least":
            low = max(previous_totals) + 1
            high = int(step.running_after)
        else:
            low = int(step.running_after)
            high = min(previous_totals) - 1
        if int(low) <= int(high):
            options.append((int(index), int((int(low) + int(high)) // 2)))
        previous_totals.append(int(step.running_after))
    return tuple(options)


def _build_query(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    start_value: int,
    steps: Tuple[_Step, ...],
    query_id: str,
    query_probabilities: Mapping[str, float],
) -> _Query:
    index_seed = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"charts.waterfall.{query_id}.target")
    target_support = list(range(len(steps)))
    if str(query_id) == RUNNING_TOTAL_QUERY_ID:
        min_index = int(params.get("running_total_target_index_min", 0))
        max_index = int(params.get("running_total_target_index_max", len(steps) - 1))
        max_from_end = params.get("running_total_target_max_from_end")
        if max_from_end is not None:
            max_index = min(int(max_index), len(steps) - 1 - max(0, int(max_from_end)))
        target_support = [index for index in target_support if int(min_index) <= int(index) <= int(max_index)]
        if not target_support:
            raise ValueError("no feasible running-total target step")
    target_index = int(target_support[int(index_seed) % len(target_support)])
    target_step = steps[target_index]
    base_params: Dict[str, Any] = {
        "query_id": str(query_id),
        "query_id_probabilities": dict(query_probabilities),
        "step_count": int(len(steps)),
        "start_value": int(start_value),
        "final_value": int(steps[-1].running_after),
    }

    if str(query_id) == RUNNING_TOTAL_QUERY_ID:
        evidence = ("start",) + tuple(step.step_id for step in steps[: target_index + 1])
        return _Query(
            query_id=str(query_id),
            answer=int(target_step.running_after),
            answer_type="integer",
            evidence_bar_ids=evidence,
            evidence_extra_ids=(f"x_label:{target_step.step_id}",),
            params={
                **base_params,
                "target_step_id": str(target_step.step_id),
                "target_step_label": str(target_step.label),
                "target_step_index": int(target_index),
            },
        )

    if str(query_id) in THRESHOLD_QUERY_IDS:
        direction = "at_least" if str(query_id) == "first_total_at_least_threshold" else "at_most"
        if should_use_unanswerable_branch(
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_id}",
            enabled=bool(params.get("_enable_unanswerable", False)),
        ):
            running_totals = [int(step.running_after) for step in steps]
            threshold_value = max(running_totals) + 1 if str(direction) == "at_least" else min(running_totals) - 1
            return _Query(
                query_id=str(query_id),
                answer=UNANSWERABLE_ANSWER,
                answer_type="string",
                evidence_bar_ids=(),
                evidence_extra_ids=(),
                params={
                    **base_params,
                    "threshold_direction": str(direction),
                    "threshold_value": int(threshold_value),
                    "answer_step_id": "",
                    "answer_step_label": "",
                    "answer_step_index": -1,
                    "answerability": "unanswerable",
                    "absence_proof": absence_proof(
                        requested_item=f"first contribution step with running total {str(direction).replace('_', ' ')} {int(threshold_value)}",
                        visible_candidates=[str(step.label) for step in steps],
                        checked_scope="waterfall contribution steps and running totals",
                        absence_reason="no contribution step makes the running total satisfy the threshold rule",
                    ),
                },
            )
        options = _threshold_options((int(start_value), tuple(steps)), direction=str(direction))
        if not options:
            raise ValueError(f"no feasible threshold crossing for {query_id}")
        option_index = int(index_seed) % len(options)
        crossing_index, threshold_value = options[option_index]
        crossing_step = steps[int(crossing_index)]
        evidence = ("start",) + tuple(step.step_id for step in steps[: int(crossing_index) + 1])
        return _Query(
            query_id=str(query_id),
            answer=str(crossing_step.label),
            answer_type="string",
            evidence_bar_ids=evidence,
            evidence_extra_ids=("threshold_label",),
            params={
                **base_params,
                "threshold_direction": str(direction),
                "threshold_value": int(threshold_value),
                "answer_step_id": str(crossing_step.step_id),
                "answer_step_label": str(crossing_step.label),
                "answer_step_index": int(crossing_index),
                "answerability": "answerable",
            },
        )

    if str(query_id) in COUNTERFACTUAL_QUERY_IDS:
        final_value = int(steps[-1].running_after)
        if str(query_id) == "remove_step_final_total":
            answer = int(final_value) - int(target_step.delta)
            operation_phrase = "removed"
        else:
            answer = int(final_value) - (2 * int(target_step.delta))
            operation_phrase = "changed sign"
        return _Query(
            query_id=str(query_id),
            answer=int(answer),
            answer_type="integer",
            evidence_bar_ids=("final", str(target_step.step_id)),
            evidence_extra_ids=(f"x_label:{target_step.step_id}",),
            params={
                **base_params,
                "target_step_id": str(target_step.step_id),
                "target_step_label": str(target_step.label),
                "target_step_index": int(target_index),
                "target_delta": int(target_step.delta),
                "counterfactual_operation": str(operation_phrase),
            },
        )

    raise ValueError(f"unsupported waterfall query: {query_id}")


def _build_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    query_id, query_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
    for attempt in range(80):
        attempt_seed = int(instance_seed) if attempt == 0 else int(hash64(int(instance_seed), "charts.waterfall.dataset", int(attempt)))
        start_value, steps = _sample_steps(params, instance_seed=int(attempt_seed))
        try:
            query = _build_query(
                params=params,
                instance_seed=int(instance_seed),
                start_value=int(start_value),
                steps=tuple(steps),
                query_id=str(query_id),
                query_probabilities=query_probabilities,
            )
            return _Dataset(start_value=int(start_value), final_value=int(steps[-1].running_after), steps=tuple(steps), query=query)
        except ValueError:
            continue
    raise ValueError(f"could not build valid waterfall dataset for query {query_id}")


def _draw_waterfall(
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
    threshold_font = load_font(int(render_params.threshold_font_size_px), bold=True)

    draw_text_traced(draw,
        (left, max(12, top - 48)),
        "Waterfall chart",
        font=title_font,
        fill=tuple(render_params.text_color_rgb),
     role="readout", required=False,)

    y_axis_max = int(group_default(_RENDER_DEFAULTS, "y_axis_max", 100))
    y_axis_max = int(max(80, y_axis_max))
    plot_h = float(bottom - top)
    plot_w = float(right - left)

    def y_for(value: int | float) -> float:
        return float(bottom) - (float(value) / float(y_axis_max)) * plot_h

    tick_step = int(group_default(_RENDER_DEFAULTS, "y_tick_step", 20))
    for tick in range(0, int(y_axis_max) + 1, int(tick_step)):
        y = y_for(int(tick))
        draw.line([left, y, right, y], fill=tuple(render_params.grid_color_rgb), width=int(render_params.grid_line_width_px))
        draw.line([left - int(render_params.tick_length_px), y, left, y], fill=tuple(render_params.axis_color_rgb), width=1)
        text = str(tick)
        bbox = draw.textbbox((0, 0), text, font=tick_font)
        draw_text_traced(draw,
            (left - int(render_params.tick_length_px) - 8 - (bbox[2] - bbox[0]), y - (bbox[3] - bbox[1]) / 2),
            text,
            font=tick_font,
            fill=tuple(render_params.muted_text_rgb),
         role="readout", required=False,)
    draw.line([left, bottom, right, bottom], fill=tuple(render_params.axis_color_rgb), width=int(render_params.axis_line_width_px))
    draw.line([left, top, left, bottom], fill=tuple(render_params.axis_color_rgb), width=int(render_params.axis_line_width_px))

    all_items: List[Tuple[str, str, int, int, int, RGB]] = [
        ("start", "Start", int(dataset.start_value), 0, int(dataset.start_value), tuple(render_params.start_fill_rgb)),
    ]
    for step in dataset.steps:
        fill = tuple(render_params.positive_fill_rgb if int(step.delta) > 0 else render_params.negative_fill_rgb)
        all_items.append((str(step.step_id), str(step.label), int(step.delta), int(step.running_before), int(step.running_after), fill))
    all_items.append(("final", "Final", int(dataset.final_value), 0, int(dataset.final_value), tuple(render_params.final_fill_rgb)))

    slot_count = len(all_items)
    slot_w = plot_w / float(slot_count)
    bar_w = max(26.0, min(74.0, slot_w * float(render_params.bar_width_fraction)))
    bar_bboxes: Dict[str, BBox] = {}
    value_label_bboxes: Dict[str, BBox] = {}
    x_label_bboxes: Dict[str, BBox] = {}
    connector_bboxes: Dict[str, BBox] = {}
    entities: List[Dict[str, Any]] = []

    centers: Dict[str, float] = {}
    for index, (bar_id, label, raw_value, before, after, fill) in enumerate(all_items):
        cx = float(left) + (float(index) + 0.5) * slot_w
        centers[str(bar_id)] = float(cx)
        y0 = y_for(0)
        if str(bar_id) in {"start", "final"}:
            y_top = y_for(int(after))
            y_bottom = y0
            value_text = str(int(after))
        else:
            y_top = min(y_for(int(before)), y_for(int(after)))
            y_bottom = max(y_for(int(before)), y_for(int(after)))
            value_text = f"{int(raw_value):+d}"
        box = _bbox([cx - bar_w / 2.0, y_top, cx + bar_w / 2.0, y_bottom])
        draw.rectangle(box, fill=fill, outline=(48, 54, 64), width=int(render_params.bar_outline_width_px))
        bar_bboxes[str(bar_id)] = box

        value_center = (float(cx), float(y_top) - 14.0)
        if y_bottom - y_top >= 30.0:
            value_center = (float(cx), float(y_top + y_bottom) / 2.0)
        value_box = _text_bbox_at(draw, text=value_text, center=value_center, font=value_font, stroke_width=2)
        draw_text_centered(
            draw,
            text=value_text,
            center=value_center,
            font=value_font,
            fill=tuple(render_params.text_color_rgb),
            stroke_fill=tuple(render_params.text_stroke_rgb),
            stroke_width=2,
        )
        value_label_bboxes[str(bar_id)] = value_box

        x_center = (float(cx), float(bottom) + 26.0)
        x_box = _text_bbox_at(draw, text=str(label), center=x_center, font=label_font, stroke_width=1)
        draw_text_centered(
            draw,
            text=str(label),
            center=x_center,
            font=label_font,
            fill=tuple(render_params.text_color_rgb),
            stroke_fill=tuple(render_params.text_stroke_rgb),
            stroke_width=1,
        )
        x_label_bboxes[str(bar_id)] = x_box
        entities.append(
            {
                "entity_id": str(bar_id),
                "entity_type": "waterfall_bar",
                "label": str(label),
                "value": int(raw_value),
                "running_before": int(before),
                "running_after": int(after),
                "bar_bbox_px": list(box),
                "value_label_bbox_px": list(value_box),
                "x_label_bbox_px": list(x_box),
            }
        )

    previous_id = "start"
    for step in dataset.steps:
        y = y_for(int(step.running_before))
        x1 = centers[str(previous_id)] + bar_w / 2.0
        x2 = centers[str(step.step_id)] - bar_w / 2.0
        draw.line([x1, y, x2, y], fill=tuple(render_params.connector_rgb), width=int(render_params.connector_width_px))
        connector_bboxes[f"{previous_id}->{step.step_id}"] = _bbox([x1, y - 3, x2, y + 3])
        previous_id = str(step.step_id)
    y = y_for(int(dataset.final_value))
    x1 = centers[str(previous_id)] + bar_w / 2.0
    x2 = centers["final"] - bar_w / 2.0
    draw.line([x1, y, x2, y], fill=tuple(render_params.connector_rgb), width=int(render_params.connector_width_px))
    connector_bboxes[f"{previous_id}->final"] = _bbox([x1, y - 3, x2, y + 3])

    extra_bboxes: Dict[str, BBox] = {}
    threshold_value = dataset.query.params.get("threshold_value")
    if threshold_value is not None:
        threshold_int = int(threshold_value)
        y = y_for(threshold_int)
        dash = 12
        x = float(left)
        while x < float(right):
            draw.line(
                [x, y, min(float(right), x + dash), y],
                fill=tuple(render_params.threshold_rgb),
                width=max(1, int(render_params.connector_width_px)),
            )
            x += dash * 1.8
        threshold_text = f"T={threshold_int}"
        center = (float(right) - 34.0, y - 14.0)
        threshold_box = _text_bbox_at(draw, text=threshold_text, center=center, font=threshold_font, stroke_width=2)
        draw_text_centered(
            draw,
            text=threshold_text,
            center=center,
            font=threshold_font,
            fill=tuple(render_params.threshold_rgb),
            stroke_fill=tuple(render_params.text_stroke_rgb),
            stroke_width=2,
        )
        extra_bboxes["threshold_line"] = _bbox([left, y - 3, right, y + 3])
        extra_bboxes["threshold_label"] = threshold_box

    return _Rendered(
        image=image,
        entities=tuple(entities),
        plot_bbox_px=list(plot_bbox),
        bar_bboxes_px=dict(bar_bboxes),
        value_label_bboxes_px=dict(value_label_bboxes),
        x_label_bboxes_px=dict(x_label_bboxes),
        connector_bboxes_px=dict(connector_bboxes),
        extra_bboxes_px=dict(extra_bboxes),
        threshold_value=int(threshold_value) if threshold_value is not None else None,
        y_axis_max=int(y_axis_max),
    )


def _build_prompt_slots(dataset: _Dataset, prompt_defaults: Mapping[str, Any]) -> Dict[str, Any]:
    is_label = str(dataset.query.answer_type) == "string"
    slots: Dict[str, Any] = {
        "object_description": str(prompt_defaults["object_description_waterfall"]),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_defaults["answer_hint_label" if is_label else "answer_hint_value"]),
        "evidence_hint": str(prompt_defaults["evidence_hint_label" if is_label else "evidence_hint_value"]),
        "json_example": str(prompt_defaults["json_example_label" if is_label else "json_example_value"]),
        "json_example_answer_only": str(prompt_defaults["json_example_answer_only_label" if is_label else "json_example_answer_only_value"]),
        "unanswerable_instruction": str(prompt_defaults.get("unanswerable_instruction", "")),
    }
    params = dataset.query.params
    if "target_step_label" in params:
        slots["target_step_label"] = str(params["target_step_label"])
    if "threshold_value" in params:
        slots["threshold_value"] = int(params["threshold_value"])
    if str(dataset.query.query_id) == "first_total_at_least_threshold":
        slots["threshold_relation_phrase"] = "at least"
    elif str(dataset.query.query_id) == "first_total_at_most_threshold":
        slots["threshold_relation_phrase"] = "at most"
    if str(dataset.query.query_id) == "remove_step_final_total":
        slots["counterfactual_phrase"] = "removed"
    elif str(dataset.query.query_id) == "reverse_step_final_total":
        slots["counterfactual_phrase"] = "reversed"
    return slots


class ChartsWaterfallPanelQueryTask:
    """Generate waterfall chart questions over cumulative totals."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "waterfall"
    default_dataset_enabled = True

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
            attempt_seed = int(instance_seed) if attempt == 0 else int(hash64(int(instance_seed), "charts.waterfall.retry", int(attempt)))
            try:
                return self._generate_once(int(attempt_seed), params=dict(params))
            except Exception as exc:
                last_error = exc
                continue
        raise RuntimeError(f"failed to generate {self.task_id} after {max_attempts} attempts: {last_error}")

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        params = {**dict(params), "_enable_unanswerable": bool(getattr(self, "supports_unanswerable", False))}
        dataset = _build_dataset(params=params, instance_seed=int(instance_seed))
        render_params = _resolve_render_params(params, instance_seed=int(instance_seed))
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        chart_font_family = sample_chart_font_family(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.chart_font",
            params=params,
        )
        with temporary_default_font_family(str(chart_font_family)):
            rendered = _draw_waterfall(background, dataset=dataset, render_params=render_params)
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
                "object_description_waterfall",
                "unanswerable_instruction",
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
        for bar_id in dataset.query.evidence_bar_ids:
            evidence_boxes.append(list(rendered.value_label_bboxes_px[str(bar_id)]))
        for extra_id in dataset.query.evidence_extra_ids:
            if str(extra_id).startswith("x_label:"):
                bar_id = str(extra_id).split(":", 1)[1]
                evidence_boxes.append(list(rendered.x_label_bboxes_px[str(bar_id)]))
            else:
                evidence_boxes.append(list(rendered.extra_bboxes_px[str(extra_id)]))

        answer_value: int | str = int(dataset.query.answer) if str(dataset.query.answer_type) == "integer" else str(dataset.query.answer)
        answer_gt = TypedValue(type=str(dataset.query.answer_type), value=answer_value)
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_boxes))
        step_rows = [
            {
                "step_id": str(step.step_id),
                "label": str(step.label),
                "delta": int(step.delta),
                "running_before": int(step.running_before),
                "running_after": int(step.running_after),
            }
            for step in dataset.steps
        ]
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(len(dataset.steps), [6, 9]),
                "reasoning_load": clamp_unit_interval(_REASONING_LOAD_BY_QUERY[str(dataset.query.query_id)]),
                "scene_variant_load": 0.68,
            },
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_waterfall",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(dataset.query.query_id),
                    "answer": answer_value,
                    "evidence_bar_ids": list(dataset.query.evidence_bar_ids),
                    "evidence_extra_ids": list(dataset.query.evidence_extra_ids),
                    "answerability": str(dataset.query.params.get("answerability", "answerable")),
                    **(
                        {"absence_proof": dict(dataset.query.params["absence_proof"])}
                        if str(dataset.query.params.get("answerability")) == "unanswerable"
                        else {}
                    ),
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
                "scene_variant": "waterfall",
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "background_style": dict(background_meta),
                "font_assets": chart_font_asset_metadata(str(chart_font_family)),
                "y_axis_max": int(rendered.y_axis_max),
                "threshold_value": rendered.threshold_value,
                "layout_jitter": dict(render_params.layout_jitter_meta),
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "bar_bboxes_px": dict(rendered.bar_bboxes_px),
                "value_label_bboxes_px": dict(rendered.value_label_bboxes_px),
                "x_label_bboxes_px": dict(rendered.x_label_bboxes_px),
                "connector_bboxes_px": dict(rendered.connector_bboxes_px),
                "extra_bboxes_px": dict(rendered.extra_bboxes_px),
            },
            "execution_trace": {
                "query_id": str(dataset.query.query_id),
                "question_format": "waterfall_cumulative_query",
                "answer": answer_value,
                "answer_type": str(dataset.query.answer_type),
                "start_value": int(dataset.start_value),
                "final_value": int(dataset.final_value),
                "step_count": int(len(dataset.steps)),
                "steps": list(step_rows),
                "evidence_bar_ids": list(dataset.query.evidence_bar_ids),
                "evidence_extra_ids": list(dataset.query.evidence_extra_ids),
                **dict(dataset.query.params),
            },
            "witness_symbolic": {
                "type": "waterfall_cumulative_witness",
                "bar_ids": list(dataset.query.evidence_bar_ids),
                "extra_ids": list(dataset.query.evidence_extra_ids),
                "answer": answer_value,
                "answerability": str(dataset.query.params.get("answerability", "answerable")),
                **(
                    {"absence_proof": dict(dataset.query.params["absence_proof"])}
                    if str(dataset.query.params.get("answerability")) == "unanswerable"
                    else {}
                ),
            },
            "projected_evidence": {
                "type": "bbox_set",
                "bbox_set": list(evidence_boxes),
                "bar_ids": list(dataset.query.evidence_bar_ids),
                "extra_ids": list(dataset.query.evidence_extra_ids),
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
class ChartsWaterfallRunningTotalValueTask(
    FixedChartQueryVariantTaskMixin,
    ChartsWaterfallPanelQueryTask,
):
    """Compute the running total after a named waterfall contribution."""

    task_id = "task_charts__waterfall__running_total_value"
    fixed_query_id = RUNNING_TOTAL_QUERY_ID


@register_task
class ChartsWaterfallThresholdCrossingLabelTask(
    MergedChartQueryVariantTaskMixin,
    ChartsWaterfallPanelQueryTask,
):
    """Return the first contribution label where the running total crosses a threshold."""

    task_id = "task_charts__waterfall__threshold_crossing_label"
    allowed_query_ids = THRESHOLD_QUERY_IDS
    supports_unanswerable = True


@register_task
class ChartsWaterfallCounterfactualFinalValueTask(
    MergedChartQueryVariantTaskMixin,
    ChartsWaterfallPanelQueryTask,
):
    """Compute the final total under a counterfactual contribution edit."""

    task_id = "task_charts__waterfall__counterfactual_final_value"
    allowed_query_ids = COUNTERFACTUAL_QUERY_IDS


__all__ = [
    "ChartsWaterfallCounterfactualFinalValueTask",
    "ChartsWaterfallPanelQueryTask",
    "ChartsWaterfallRunningTotalValueTask",
    "ChartsWaterfallThresholdCrossingLabelTask",
    "SUPPORTED_QUERY_IDS",
]
