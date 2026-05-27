"""Parallel-coordinates profile chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
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
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.bbox_projection import bbox_union as _bbox_union, round_bbox as _bbox
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
from ..shared.fixed_query_task import MergedChartQueryVariantTaskMixin
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_parallel_coords_base"
SCENE_ID = "parallel_coords"

CONDITION_QUERY_VARIANTS: Tuple[str, ...] = (
    "above_on_both_axes",
    "below_on_both_axes",
    "above_on_one_below_on_other",
)
DELTA_QUERY_VARIANTS: Tuple[str, ...] = (
    "largest_increase_between_axes",
    "largest_decrease_between_axes",
    "largest_absolute_change_between_axes",
)
CROSSING_QUERY_VARIANTS: Tuple[str, ...] = (
    "all_crossings_between_adjacent_axes",
    "crossings_involving_profile_between_axes",
)
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = CONDITION_QUERY_VARIANTS + DELTA_QUERY_VARIANTS + CROSSING_QUERY_VARIANTS
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("vertical_parallel_coordinates",)

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "parallel_coordinates")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="parallel_coordinates")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="parallel_coordinates", apply_prob=0.15)

_METRIC_LABEL_POOL: Tuple[str, ...] = (
    "Cost",
    "Speed",
    "Quality",
    "Risk",
    "Reach",
    "Yield",
    "Safety",
    "Growth",
    "Access",
    "Stability",
    "Capacity",
    "Delay",
)
_PROFILE_LABEL_POOL: Tuple[str, ...] = tuple("ABCDEFGH")
_PROFILE_PALETTE: Tuple[Tuple[int, int, int], ...] = (
    (38, 101, 176),
    (216, 95, 2),
    (27, 158, 119),
    (117, 112, 179),
    (231, 41, 138),
    (102, 166, 30),
    (230, 171, 2),
    (166, 118, 29),
)
_QUERY_LOADS: Dict[str, float] = {
    "above_on_both_axes": 0.60,
    "below_on_both_axes": 0.60,
    "above_on_one_below_on_other": 0.68,
    "largest_increase_between_axes": 0.64,
    "largest_decrease_between_axes": 0.64,
    "largest_absolute_change_between_axes": 0.70,
    "all_crossings_between_adjacent_axes": 0.82,
    "crossings_involving_profile_between_axes": 0.76,
}

RGB = Tuple[int, int, int]
BBox = List[float]


@dataclass(frozen=True)
class _Profile:
    profile_id: str
    label: str
    values: Tuple[int, ...]
    color_rgb: RGB


@dataclass(frozen=True)
class _Query:
    query_id: str
    answer: int | str
    answer_type: str
    axis_i: int
    axis_j: int
    threshold: int | None
    reference_profile_id: str | None
    evidence_profile_ids: Tuple[str, ...]
    crossing_pairs: Tuple[Tuple[str, str], ...]
    params: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    scene_variant: str
    metrics: Tuple[str, ...]
    profiles: Tuple[_Profile, ...]
    query: _Query


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    plot_margin_left_px: int
    plot_margin_right_px: int
    plot_margin_top_px: int
    plot_margin_bottom_px: int
    panel_fill_rgb: RGB
    panel_border_rgb: RGB
    plot_fill_rgb: RGB
    axis_rgb: RGB
    selected_axis_rgb: RGB
    grid_rgb: RGB
    threshold_rgb: RGB
    text_rgb: RGB
    muted_text_rgb: RGB
    text_stroke_rgb: RGB
    line_width_px: int
    point_radius_px: int
    axis_line_width_px: int
    selected_axis_line_width_px: int
    grid_line_width_px: int
    label_font_size_px: int
    tick_font_size_px: int
    title_font_size_px: int
    threshold_font_size_px: int
    layout_jitter_meta: Dict[str, Any]


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: BBox
    axis_x_px: Dict[int, float]
    point_bboxes_px: Dict[str, BBox]
    segment_bboxes_px: Dict[str, BBox]
    profile_bboxes_px: Dict[str, BBox]
    label_bboxes_px: Dict[str, BBox]
    threshold_bboxes_px: Dict[int, BBox]


def _render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


def _render_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), _RENDER_DEFAULTS.get(str(key), int(fallback))))


def _gen_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), int(fallback))))


def _render_rgb(params: Mapping[str, Any], key: str, fallback: RGB) -> RGB:
    return resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        str(key),
        fallback,
        instance_seed=_render_style_seed(params),
        namespace=TASK_ID,
    )


def _support_probability_map(values: Sequence[int | str]) -> Dict[str, float]:
    if not values:
        return {}
    return {str(value): 1.0 / float(len(values)) for value in values}


def _balanced_int(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    namespace: str,
    low: int,
    high: int,
) -> Tuple[int, Dict[str, float]]:
    values = tuple(int(value) for value in range(int(low), int(high) + 1))
    if not values:
        raise ValueError(f"empty integer support for {namespace}")
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    return int(values[int(index) % len(values)]), uniform_probability_map(values)


def _resolve_query_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_QUERY_VARIANTS,
        task_id=TASK_ID,
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        balance_flag_key="balanced_query_variant_sampling",
        axis_namespace="query_variant",
    )


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


def _resolve_render_params(params: Mapping[str, Any]) -> _RenderParams:
    left = _render_int(params, "plot_margin_left_px", 138)
    right = _render_int(params, "plot_margin_right_px", 138)
    top = _render_int(params, "plot_margin_top_px", 116)
    bottom = _render_int(params, "plot_margin_bottom_px", 118)
    left, right, top, bottom, layout_jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(left),
        right_px=int(right),
        top_px=int(top),
        bottom_px=int(bottom),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=_render_style_seed(params),
        namespace=f"{TASK_ID}.layout",
    )
    return _RenderParams(
        canvas_width=_render_int(params, "canvas_width", 1180),
        canvas_height=_render_int(params, "canvas_height", 760),
        plot_margin_left_px=int(left),
        plot_margin_right_px=int(right),
        plot_margin_top_px=int(top),
        plot_margin_bottom_px=int(bottom),
        panel_fill_rgb=_render_rgb(params, "panel_fill_rgb", (255, 255, 255)),
        panel_border_rgb=_render_rgb(params, "panel_border_rgb", (194, 202, 214)),
        plot_fill_rgb=_render_rgb(params, "plot_fill_rgb", (252, 253, 255)),
        axis_rgb=_render_rgb(params, "axis_rgb", (78, 88, 102)),
        selected_axis_rgb=_render_rgb(params, "selected_axis_rgb", (26, 66, 118)),
        grid_rgb=_render_rgb(params, "grid_rgb", (226, 231, 238)),
        threshold_rgb=_render_rgb(params, "threshold_rgb", (204, 56, 60)),
        text_rgb=_render_rgb(params, "text_rgb", (32, 38, 48)),
        muted_text_rgb=_render_rgb(params, "muted_text_rgb", (89, 100, 116)),
        text_stroke_rgb=_render_rgb(params, "text_stroke_rgb", (255, 255, 255)),
        line_width_px=_render_int(params, "line_width_px", 4),
        point_radius_px=_render_int(params, "point_radius_px", 5),
        axis_line_width_px=_render_int(params, "axis_line_width_px", 2),
        selected_axis_line_width_px=_render_int(params, "selected_axis_line_width_px", 4),
        grid_line_width_px=_render_int(params, "grid_line_width_px", 1),
        label_font_size_px=_render_int(params, "label_font_size_px", 18),
        tick_font_size_px=_render_int(params, "tick_font_size_px", 15),
        title_font_size_px=_render_int(params, "title_font_size_px", 28),
        threshold_font_size_px=_render_int(params, "threshold_font_size_px", 15),
        layout_jitter_meta=dict(layout_jitter_meta),
    )


def _choose_axis_pair(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    axis_count: int,
    adjacent_only: bool,
    namespace: str,
) -> Tuple[int, int]:
    pairs = (
        [(index, index + 1) for index in range(int(axis_count) - 1)]
        if bool(adjacent_only)
        else [(i, j) for i in range(int(axis_count)) for j in range(i + 1, int(axis_count))]
    )
    if not pairs:
        raise ValueError("axis_count must allow at least one axis pair")
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    return tuple(pairs[int(index) % len(pairs)])  # type: ignore[return-value]


def _make_exact_inversion_permutation(n: int, inversions: int, rng) -> Tuple[int, ...]:
    """Return one permutation of 0..n-1 with exactly `inversions` inversions."""

    target = int(inversions)
    if target < 0 or target > (int(n) * (int(n) - 1)) // 2:
        raise ValueError("inversion count outside feasible range")
    for _ in range(2000):
        values = list(range(int(n)))
        rng.shuffle(values)
        if _inversion_count(values) == target:
            return tuple(values)
    # Deterministic construction from inversion vector.
    remaining = int(target)
    code: List[int] = []
    for i in range(int(n)):
        max_here = int(n) - 1 - int(i)
        take = min(max_here, remaining)
        code.append(int(take))
        remaining -= int(take)
    pool = list(range(int(n)))
    out: List[int] = []
    for take in code:
        out.append(pool.pop(int(take)))
    return tuple(out)


def _inversion_count(values: Sequence[int]) -> int:
    return sum(1 for i, j in combinations(range(len(values)), 2) if int(values[i]) > int(values[j]))


def _rank_values(order: Sequence[int], *, value_min: int, value_max: int) -> Dict[int, int]:
    n = len(order)
    if n <= 1:
        return {int(order[0]): int(value_min)}
    lo = int(value_min) + 1
    hi = int(value_max) - 1
    step = max(1, int((hi - lo) / max(1, n - 1)))
    return {int(profile_index): int(min(hi, lo + (rank * step))) for rank, profile_index in enumerate(order)}


def _sample_base(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    query_variant: str,
    query_variant_probabilities: Mapping[str, float],
) -> Tuple[str, Tuple[str, ...], List[str], int, int, int, int, Dict[str, Any]]:
    scene_variant, scene_probs = _resolve_scene_variant(params, instance_seed=int(instance_seed))
    axis_min, axis_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="axis_count_min",
        max_key="axis_count_max",
        fallback_min=4,
        fallback_max=6,
        context=f"generation defaults for {TASK_ID}",
    )
    profile_min, profile_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="profile_count_min",
        max_key="profile_count_max",
        fallback_min=5,
        fallback_max=8,
        context=f"generation defaults for {TASK_ID}",
    )
    if str(query_variant) in CROSSING_QUERY_VARIANTS:
        axis_min, axis_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="crossing_axis_count_min",
            max_key="crossing_axis_count_max",
            fallback_min=int(axis_min),
            fallback_max=int(axis_max),
            context=f"crossing generation defaults for {TASK_ID}",
        )
        profile_min, profile_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="crossing_profile_count_min",
            max_key="crossing_profile_count_max",
            fallback_min=int(profile_min),
            fallback_max=int(profile_max),
            context=f"crossing generation defaults for {TASK_ID}",
        )
    value_min, value_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="value_min",
        max_key="value_max",
        fallback_min=1,
        fallback_max=20,
        context=f"generation defaults for {TASK_ID}",
    )
    axis_count, axis_count_probs = _balanced_int(
        params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.axis_count",
        low=int(axis_min),
        high=int(axis_max),
    )
    profile_count, profile_count_probs = _balanced_int(
        params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.profile_count",
        low=int(profile_min),
        high=min(int(profile_max), len(_PROFILE_LABEL_POOL)),
    )
    metric_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.metrics")
    metrics = list(_METRIC_LABEL_POOL)
    metric_rng.shuffle(metrics)
    trace_params = {
        "query_variant": str(query_variant),
        "query_variant": str(query_variant),
        "scene_variant": str(scene_variant),
        "query_variant_probabilities": dict(query_variant_probabilities),
        "scene_variant_probabilities": dict(scene_probs),
        "axis_count": int(axis_count),
        "axis_count_probabilities": dict(axis_count_probs),
        "profile_count": int(profile_count),
        "profile_count_probabilities": dict(profile_count_probs),
        "value_min": int(value_min),
        "value_max": int(value_max),
    }
    return (
        str(scene_variant),
        tuple(str(value) for value in metrics[: int(axis_count)]),
        list(_PROFILE_LABEL_POOL[: int(profile_count)]),
        int(profile_count),
        int(axis_count),
        int(value_min),
        int(value_max),
        trace_params,
    )


def _build_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    query_variant: str,
    query_variant_probabilities: Mapping[str, float],
) -> _Dataset:
    (
        scene_variant,
        metrics,
        profile_labels,
        profile_count,
        axis_count,
        value_min,
        value_max,
        trace_params,
    ) = _sample_base(
        params=params,
        instance_seed=int(instance_seed),
        query_variant=str(query_variant),
        query_variant_probabilities=query_variant_probabilities,
    )
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.values.{query_variant}")
    values: List[List[int]] = [
        [int(rng.randint(int(value_min), int(value_max))) for _ in range(int(axis_count))]
        for _ in range(int(profile_count))
    ]
    axis_i, axis_j = _choose_axis_pair(
        params,
        instance_seed=int(instance_seed),
        axis_count=int(axis_count),
        adjacent_only=str(query_variant) in CROSSING_QUERY_VARIANTS,
        namespace=f"{TASK_ID}.{query_variant}.axis_pair",
    )
    threshold: int | None = None
    reference_profile_id: str | None = None
    evidence_profile_ids: Tuple[str, ...] = ()
    crossing_pairs: Tuple[Tuple[str, str], ...] = ()

    if str(query_variant) in CONDITION_QUERY_VARIANTS:
        threshold_min = _gen_int(params, "condition_threshold_min", 8)
        threshold_max = _gen_int(params, "condition_threshold_max", 14)
        threshold, threshold_probs = _balanced_int(
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_variant}.threshold",
            low=int(threshold_min),
            high=int(threshold_max),
        )
        count_min = _gen_int(params, "condition_answer_count_min", 1)
        count_max = min(_gen_int(params, "condition_answer_count_max", 5), int(profile_count) - 1)
        target_count, target_count_probs = _balanced_int(
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_variant}.answer",
            low=int(count_min),
            high=max(int(count_min), int(count_max)),
        )
        evidence_indices = set(rng.sample(list(range(int(profile_count))), int(target_count)))
        for profile_index in range(int(profile_count)):
            is_target = int(profile_index) in evidence_indices
            if str(query_variant) == "above_on_both_axes":
                if is_target:
                    values[profile_index][axis_i] = int(rng.randint(int(threshold) + 1, int(value_max)))
                    values[profile_index][axis_j] = int(rng.randint(int(threshold) + 1, int(value_max)))
                else:
                    fail_axis = axis_i if rng.random() < 0.5 else axis_j
                    values[profile_index][axis_i] = int(rng.randint(int(value_min), int(value_max)))
                    values[profile_index][axis_j] = int(rng.randint(int(value_min), int(value_max)))
                    values[profile_index][fail_axis] = int(rng.randint(int(value_min), int(threshold)))
            elif str(query_variant) == "below_on_both_axes":
                if is_target:
                    values[profile_index][axis_i] = int(rng.randint(int(value_min), int(threshold) - 1))
                    values[profile_index][axis_j] = int(rng.randint(int(value_min), int(threshold) - 1))
                else:
                    fail_axis = axis_i if rng.random() < 0.5 else axis_j
                    values[profile_index][axis_i] = int(rng.randint(int(value_min), int(value_max)))
                    values[profile_index][axis_j] = int(rng.randint(int(value_min), int(value_max)))
                    values[profile_index][fail_axis] = int(rng.randint(int(threshold), int(value_max)))
            else:
                if is_target:
                    values[profile_index][axis_i] = int(rng.randint(int(threshold) + 1, int(value_max)))
                    values[profile_index][axis_j] = int(rng.randint(int(value_min), int(threshold) - 1))
                else:
                    if rng.random() < 0.5:
                        values[profile_index][axis_i] = int(rng.randint(int(value_min), int(threshold)))
                    else:
                        values[profile_index][axis_j] = int(rng.randint(int(threshold), int(value_max)))
            evidence_profile_ids = tuple(f"profile_{index}" for index in sorted(evidence_indices))
        answer: int | str = int(target_count)
        answer_type = "integer"
        trace_params.update(
            {
                "threshold": int(threshold),
                "threshold_probabilities": dict(threshold_probs),
                "target_count": int(target_count),
                "target_count_probabilities": dict(target_count_probs),
            }
        )
    elif str(query_variant) in DELTA_QUERY_VARIANTS:
        target_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_variant}.target_profile",
        ) % int(profile_count)
        deltas = list(range(1, min(12, int(value_max) - int(value_min)) + 1))
        rng.shuffle(deltas)
        if len(deltas) < int(profile_count):
            raise ValueError("not enough distinct deltas for profile extrema")
        target_delta = int(max(deltas))
        other_deltas = [int(value) for value in deltas if int(value) != int(target_delta)]
        for profile_index in range(int(profile_count)):
            delta = int(target_delta if int(profile_index) == int(target_index) else other_deltas.pop())
            base_low = int(value_min)
            base_high = int(value_max) - int(delta)
            base = int(rng.randint(int(base_low), int(base_high)))
            if str(query_variant) == "largest_increase_between_axes":
                values[profile_index][axis_i] = int(base)
                values[profile_index][axis_j] = int(base + delta)
            elif str(query_variant) == "largest_decrease_between_axes":
                values[profile_index][axis_i] = int(base + delta)
                values[profile_index][axis_j] = int(base)
            else:
                if int(profile_index) == int(target_index) or rng.random() < 0.5:
                    values[profile_index][axis_i] = int(base)
                    values[profile_index][axis_j] = int(base + delta)
                else:
                    values[profile_index][axis_i] = int(base + delta)
                    values[profile_index][axis_j] = int(base)
        evidence_profile_ids = (f"profile_{target_index}",)
        answer = str(profile_labels[int(target_index)])
        answer_type = "string"
        trace_params.update({"target_profile_index": int(target_index), "target_delta": int(target_delta)})
    elif str(query_variant) == "all_crossings_between_adjacent_axes":
        max_crossings = min(_gen_int(params, "crossing_answer_count_max", 10), (int(profile_count) * (int(profile_count) - 1)) // 2)
        min_crossings = min(_gen_int(params, "crossing_answer_count_min", 1), int(max_crossings))
        target_count, target_count_probs = _balanced_int(
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_variant}.answer",
            low=int(min_crossings),
            high=int(max_crossings),
        )
        order_a = tuple(range(int(profile_count)))
        order_b = _make_exact_inversion_permutation(int(profile_count), int(target_count), rng)
        rank_values_a = _rank_values(order_a, value_min=int(value_min), value_max=int(value_max))
        rank_values_b = _rank_values(order_b, value_min=int(value_min), value_max=int(value_max))
        for profile_index in range(int(profile_count)):
            values[profile_index][axis_i] = int(rank_values_a[int(profile_index)])
            values[profile_index][axis_j] = int(rank_values_b[int(profile_index)])
        profile_ids = [f"profile_{index}" for index in range(int(profile_count))]
        crossing_pairs = tuple(
            (profile_ids[a], profile_ids[b])
            for a, b in combinations(range(int(profile_count)), 2)
            if (values[a][axis_i] - values[b][axis_i]) * (values[a][axis_j] - values[b][axis_j]) < 0
        )
        evidence_profile_ids = tuple(profile_ids)
        answer = int(len(crossing_pairs))
        answer_type = "integer"
        trace_params.update({"target_count": int(target_count), "target_count_probabilities": dict(target_count_probs)})
    elif str(query_variant) == "crossings_involving_profile_between_axes":
        max_cross = min(_gen_int(params, "profile_crossing_answer_count_max", 5), int(profile_count) - 1)
        min_cross = min(_gen_int(params, "profile_crossing_answer_count_min", 1), int(max_cross))
        target_count, target_count_probs = _balanced_int(
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_variant}.answer",
            low=int(min_cross),
            high=int(max_cross),
        )
        target_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.{query_variant}.target_profile",
        ) % int(profile_count)
        others = [index for index in range(int(profile_count)) if int(index) != int(target_index)]
        order_a = [int(target_index)] + others
        order_b = others[: int(target_count)] + [int(target_index)] + others[int(target_count) :]
        rank_values_a = _rank_values(order_a, value_min=int(value_min), value_max=int(value_max))
        rank_values_b = _rank_values(order_b, value_min=int(value_min), value_max=int(value_max))
        for profile_index in range(int(profile_count)):
            values[profile_index][axis_i] = int(rank_values_a[int(profile_index)])
            values[profile_index][axis_j] = int(rank_values_b[int(profile_index)])
        reference_profile_id = f"profile_{target_index}"
        crossing_pairs = tuple((reference_profile_id, f"profile_{index}") for index in others[: int(target_count)])
        evidence_profile_ids = (reference_profile_id,) + tuple(f"profile_{index}" for index in others[: int(target_count)])
        answer = int(target_count)
        answer_type = "integer"
        trace_params.update(
            {
                "target_count": int(target_count),
                "target_count_probabilities": dict(target_count_probs),
                "reference_profile_id": str(reference_profile_id),
                "reference_profile_label": str(profile_labels[int(target_index)]),
            }
        )
    else:
        raise ValueError(f"unsupported query variant: {query_variant}")

    profiles = tuple(
        _Profile(
            profile_id=f"profile_{index}",
            label=str(label),
            values=tuple(int(value) for value in values[index]),
            color_rgb=tuple(int(channel) for channel in _PROFILE_PALETTE[index % len(_PROFILE_PALETTE)]),
        )
        for index, label in enumerate(profile_labels)
    )
    trace_params.update(
        {
            "axis_i": int(axis_i),
            "axis_j": int(axis_j),
            "axis_i_label": str(metrics[int(axis_i)]),
            "axis_j_label": str(metrics[int(axis_j)]),
            "answer": answer,
            "answer_type": str(answer_type),
            "evidence_profile_ids": list(evidence_profile_ids),
            "crossing_pairs": [list(pair) for pair in crossing_pairs],
        }
    )
    return _Dataset(
        scene_variant=str(scene_variant),
        metrics=tuple(metrics),
        profiles=profiles,
        query=_Query(
            query_id=str(query_variant),
            answer=answer,
            answer_type=str(answer_type),
            axis_i=int(axis_i),
            axis_j=int(axis_j),
            threshold=threshold,
            reference_profile_id=reference_profile_id,
            evidence_profile_ids=tuple(evidence_profile_ids),
            crossing_pairs=tuple(crossing_pairs),
            params=dict(trace_params),
        ),
    )


def _text_bbox(draw: ImageDraw.ImageDraw, xy: Tuple[float, float], text: str, font: Any, *, stroke_width: int = 0) -> BBox:
    box = draw.textbbox(tuple(float(value) for value in xy), str(text), font=font, stroke_width=max(0, int(stroke_width)))
    return _bbox([box[0], box[1], box[2], box[3]])


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    font: Any,
    *,
    fill: RGB,
    stroke_fill: RGB,
    stroke_width: int = 0,
) -> BBox:
    box = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width)))
    width = float(box[2] - box[0])
    height = float(box[3] - box[1])
    x = float(xy[0]) - width / 2.0
    y = float(xy[1]) - height / 2.0
    draw.text((x, y), str(text), font=font, fill=fill, stroke_fill=stroke_fill, stroke_width=max(0, int(stroke_width)))
    return _bbox([x, y, x + width, y + height])


def _render_parallel_coordinates(background: Image.Image, *, dataset: _Dataset, render_params: _RenderParams) -> _Rendered:
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size
    panel_margin = 34
    left = float(render_params.plot_margin_left_px)
    right = float(width - int(render_params.plot_margin_right_px))
    top = float(render_params.plot_margin_top_px)
    bottom = float(height - int(render_params.plot_margin_bottom_px))
    plot_bbox = _bbox([left, top, right, bottom])
    panel_bbox = [panel_margin, 36, width - panel_margin, height - 42]
    draw.rounded_rectangle(panel_bbox, radius=8, fill=render_params.panel_fill_rgb, outline=render_params.panel_border_rgb, width=1)
    draw.rectangle([left, top, right, bottom], fill=render_params.plot_fill_rgb)

    title_font = load_font(render_params.title_font_size_px, bold=True)
    label_font = load_font(render_params.label_font_size_px, bold=True)
    tick_font = load_font(render_params.tick_font_size_px, bold=False)
    threshold_font = load_font(render_params.threshold_font_size_px, bold=True)
    draw.text((panel_margin + 22, 50), "Profile Comparison", font=title_font, fill=render_params.text_rgb)

    value_min = int(dataset.query.params["value_min"])
    value_max = int(dataset.query.params["value_max"])

    def y_px(value: float) -> float:
        ratio = (float(value) - float(value_min)) / max(1.0, float(value_max) - float(value_min))
        return bottom - (ratio * (bottom - top))

    axis_count = len(dataset.metrics)
    axis_x: Dict[int, float] = {}
    for axis_index in range(axis_count):
        x = left + (float(axis_index) * (right - left) / max(1, axis_count - 1))
        axis_x[int(axis_index)] = float(x)

    tick_values = [value_min, int(round((value_min + value_max) / 2.0)), value_max]
    for tick in tick_values:
        y = y_px(float(tick))
        draw.line([left, y, right, y], fill=render_params.grid_rgb, width=render_params.grid_line_width_px)
        draw.text(
            (left - 46, y - 9),
            str(int(tick)),
            font=tick_font,
            fill=render_params.muted_text_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=1,
        )

    selected_axes = {int(dataset.query.axis_i), int(dataset.query.axis_j)}
    threshold_bboxes: Dict[int, BBox] = {}
    for axis_index, metric in enumerate(dataset.metrics):
        x = axis_x[int(axis_index)]
        selected = int(axis_index) in selected_axes
        axis_rgb = render_params.selected_axis_rgb if selected else render_params.axis_rgb
        axis_width = render_params.selected_axis_line_width_px if selected else render_params.axis_line_width_px
        draw.line([x, top, x, bottom], fill=axis_rgb, width=axis_width)
        _draw_centered_text(
            draw,
            (x, bottom + 34),
            str(metric),
            label_font,
            fill=render_params.text_rgb,
            stroke_fill=render_params.text_stroke_rgb,
            stroke_width=1,
        )
        for tick in tick_values:
            y = y_px(float(tick))
            draw.line([x - 5, y, x + 5, y], fill=axis_rgb, width=2)
        if dataset.query.threshold is not None and selected:
            y = y_px(float(dataset.query.threshold))
            draw.line([x - 22, y, x + 22, y], fill=render_params.threshold_rgb, width=3)
            text_bbox = _text_bbox(draw, (x + 26, y - 9), str(dataset.query.threshold), threshold_font, stroke_width=1)
            draw.text(
                (x + 26, y - 9),
                str(dataset.query.threshold),
                font=threshold_font,
                fill=render_params.threshold_rgb,
                stroke_fill=render_params.text_stroke_rgb,
                stroke_width=1,
            )
            threshold_bboxes[int(axis_index)] = _bbox_union([[x - 22, y - 2, x + 22, y + 2], text_bbox], padding=2)

    point_bboxes: Dict[str, BBox] = {}
    segment_bboxes: Dict[str, BBox] = {}
    profile_bboxes: Dict[str, BBox] = {}
    label_bboxes: Dict[str, BBox] = {}
    entities: List[Dict[str, Any]] = []
    radius = float(render_params.point_radius_px)

    # Draw less emphasized lines first so labels and points stay legible.
    for profile in dataset.profiles:
        points = [(axis_x[index], y_px(profile.values[index])) for index in range(axis_count)]
        line_rgb = tuple(int(c) for c in profile.color_rgb)
        draw.line(points, fill=line_rgb, width=render_params.line_width_px, joint="curve")
        profile_segment_boxes: List[BBox] = []
        for axis_index in range(axis_count):
            x, y = points[int(axis_index)]
            point_box = _bbox([x - radius, y - radius, x + radius, y + radius])
            point_bboxes[f"{profile.profile_id}:axis_{axis_index}"] = point_box
            draw.ellipse(point_box, fill=line_rgb, outline=(255, 255, 255), width=2)
        for axis_index in range(axis_count - 1):
            x0, y0 = points[int(axis_index)]
            x1, y1 = points[int(axis_index) + 1]
            seg_box = _bbox([min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)])
            padded = _bbox_union([seg_box], padding=8)
            segment_bboxes[f"{profile.profile_id}:axis_{axis_index}_{axis_index + 1}"] = padded
            profile_segment_boxes.append(padded)
        label_left_xy = (left - 74, points[0][1] - 10)
        label_right_xy = (right + 48, points[-1][1] - 10)
        for suffix, xy in (("left", label_left_xy), ("right", label_right_xy)):
            box = _text_bbox(draw, xy, profile.label, label_font, stroke_width=2)
            draw.text(xy, profile.label, font=label_font, fill=line_rgb, stroke_fill=render_params.text_stroke_rgb, stroke_width=2)
            label_bboxes[f"{profile.profile_id}:{suffix}"] = box
        profile_bboxes[profile.profile_id] = _bbox_union(
            profile_segment_boxes
            + [point_bboxes[f"{profile.profile_id}:axis_{index}"] for index in range(axis_count)]
            + [label_bboxes[f"{profile.profile_id}:left"], label_bboxes[f"{profile.profile_id}:right"]],
            padding=4,
        )
        entities.append(
            {
                "entity_id": profile.profile_id,
                "entity_type": "parallel_coordinate_profile",
                "label": profile.label,
                "values": [int(value) for value in profile.values],
                "color_rgb": list(line_rgb),
                "bbox_px": list(profile_bboxes[profile.profile_id]),
            }
        )

    return _Rendered(
        image=image,
        entities=tuple(entities),
        plot_bbox_px=list(plot_bbox),
        axis_x_px={int(k): float(v) for k, v in axis_x.items()},
        point_bboxes_px=dict(point_bboxes),
        segment_bboxes_px=dict(segment_bboxes),
        profile_bboxes_px=dict(profile_bboxes),
        label_bboxes_px=dict(label_bboxes),
        threshold_bboxes_px=dict(threshold_bboxes),
    )


def _segment_key(profile_id: str, axis_i: int, axis_j: int) -> str:
    if int(axis_j) != int(axis_i) + 1:
        return str(profile_id)
    return f"{profile_id}:axis_{int(axis_i)}_{int(axis_j)}"


def _evidence_bboxes(dataset: _Dataset, rendered: _Rendered) -> List[BBox]:
    axis_i = int(dataset.query.axis_i)
    axis_j = int(dataset.query.axis_j)
    boxes: List[BBox] = []
    for profile_id in dataset.query.evidence_profile_ids:
        key = _segment_key(str(profile_id), int(axis_i), int(axis_j))
        if key in rendered.segment_bboxes_px:
            boxes.append(list(rendered.segment_bboxes_px[key]))
        else:
            boxes.append(list(rendered.profile_bboxes_px[str(profile_id)]))
    return boxes


def _build_prompt_slots(dataset: _Dataset, prompt_defaults: Mapping[str, Any]) -> Dict[str, Any]:
    is_label = str(dataset.query.answer_type) == "string"
    axis_i_label = str(dataset.metrics[int(dataset.query.axis_i)])
    axis_j_label = str(dataset.metrics[int(dataset.query.axis_j)])
    slots: Dict[str, Any] = {
        "object_description": str(prompt_defaults["object_description_parallel_coordinates"]),
        "axis_i": axis_i_label,
        "axis_j": axis_j_label,
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_defaults["answer_hint_label" if is_label else "answer_hint_count"]),
        "evidence_hint": str(prompt_defaults["evidence_hint_label" if is_label else "evidence_hint_count"]),
        "json_example": str(prompt_defaults["json_example_label" if is_label else "json_example_count"]),
        "json_example_answer_only": str(prompt_defaults["json_example_answer_only_label" if is_label else "json_example_answer_only_count"]),
    }
    if dataset.query.threshold is not None:
        slots["threshold"] = int(dataset.query.threshold)
    if str(dataset.query.query_id) == "above_on_both_axes":
        slots["condition_phrase"] = "above"
        slots["condition_detail"] = f"above {int(dataset.query.threshold)} on both axes"
    elif str(dataset.query.query_id) == "below_on_both_axes":
        slots["condition_phrase"] = "below"
        slots["condition_detail"] = f"below {int(dataset.query.threshold)} on both axes"
    elif str(dataset.query.query_id) == "above_on_one_below_on_other":
        slots["condition_phrase"] = "mixed"
        slots["condition_detail"] = f"above {int(dataset.query.threshold)} on {axis_i_label} and below {int(dataset.query.threshold)} on {axis_j_label}"
    elif str(dataset.query.query_id) == "largest_increase_between_axes":
        slots["delta_phrase"] = "largest increase"
    elif str(dataset.query.query_id) == "largest_decrease_between_axes":
        slots["delta_phrase"] = "largest decrease"
    elif str(dataset.query.query_id) == "largest_absolute_change_between_axes":
        slots["delta_phrase"] = "largest absolute change"
    elif str(dataset.query.query_id) == "crossings_involving_profile_between_axes":
        reference = str(dataset.query.params["reference_profile_label"])
        slots["reference_profile"] = reference
    return slots


class ChartsParallelCoordinatesProfileTask:
    """Generate parallel-coordinates profile chart questions."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "parallel_coordinates"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                return self._generate_once(int(instance_seed) + int(attempt), params=dict(params))
            except Exception as exc:
                last_error = exc
                continue
        raise RuntimeError(f"failed to generate {self.task_id} after {max_attempts} attempts: {last_error}")

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        query_variant, query_variant_probabilities = _resolve_query_variant(params, instance_seed=int(instance_seed))
        dataset = _build_dataset(
            params=params,
            instance_seed=int(instance_seed),
            query_variant=str(query_variant),
            query_variant_probabilities=query_variant_probabilities,
        )
        render_params = _resolve_render_params({**dict(params), "_render_style_seed": int(instance_seed)})
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered = _render_parallel_coordinates(background, dataset=dataset, render_params=render_params)
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
                "answer_hint_label",
                "answer_hint_count",
                "evidence_hint_label",
                "evidence_hint_count",
                "json_example_label",
                "json_example_count",
                "json_example_answer_only_label",
                "json_example_answer_only_count",
                "object_description_parallel_coordinates",
            ],
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots=_build_prompt_slots(dataset, prompt_defaults),
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_bboxes = _evidence_bboxes(dataset, rendered)
        answer_value: int | str = int(dataset.query.answer) if str(dataset.query.answer_type) == "integer" else str(dataset.query.answer)
        answer_gt = TypedValue(type=str(dataset.query.answer_type), value=answer_value)
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        profiles_by_id = {profile.profile_id: profile for profile in dataset.profiles}
        axis_pair = [int(dataset.query.axis_i), int(dataset.query.axis_j)]
        profile_rows = [
            {
                "profile_id": str(profile.profile_id),
                "label": str(profile.label),
                "values": [int(value) for value in profile.values],
                "color_rgb": list(profile.color_rgb),
            }
            for profile in dataset.profiles
        ]
        projected_evidence = {
            "bbox_set": list(evidence_bboxes),
            "profile_ids": [str(value) for value in dataset.query.evidence_profile_ids],
            "profile_labels": [str(profiles_by_id[str(value)].label) for value in dataset.query.evidence_profile_ids],
            "axis_pair": list(axis_pair),
            "segment_bboxes": {
                str(key): list(value)
                for key, value in rendered.segment_bboxes_px.items()
                if any(str(key).startswith(str(profile_id) + ":") for profile_id in dataset.query.evidence_profile_ids)
            },
        }
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(len(dataset.profiles) * len(dataset.metrics), [20, 54]),
                "reasoning_load": clamp_unit_interval(_QUERY_LOADS[str(query_variant)]),
                "scene_variant_load": 0.68,
            },
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_parallel_coords",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_variant": str(query_variant),
                    "query_variant": str(query_variant),
                    "scene_variant": str(dataset.scene_variant),
                    "answer": answer_value,
                    "axis_pair": list(axis_pair),
                    "evidence_profile_ids": [str(value) for value in dataset.query.evidence_profile_ids],
                },
            },
            "query_spec": {
                "query_variant": str(query_variant),
                "query_variant": str(query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(dataset.query.params),
            },
            "render_spec": {
                "scene_variant": str(dataset.scene_variant),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "axis_x_px": {str(key): float(value) for key, value in rendered.axis_x_px.items()},
                "line_width_px": int(render_params.line_width_px),
                "point_radius_px": int(render_params.point_radius_px),
                "layout_jitter": dict(render_params.layout_jitter_meta),
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "axis_x_px": {str(key): float(value) for key, value in rendered.axis_x_px.items()},
                "point_bboxes_px": dict(rendered.point_bboxes_px),
                "segment_bboxes_px": dict(rendered.segment_bboxes_px),
                "profile_bboxes_px": dict(rendered.profile_bboxes_px),
                "label_bboxes_px": dict(rendered.label_bboxes_px),
                "threshold_bboxes_px": {str(key): list(value) for key, value in rendered.threshold_bboxes_px.items()},
            },
            "execution_trace": {
                "query_variant": str(query_variant),
                "query_variant": str(query_variant),
                "scene_variant": str(dataset.scene_variant),
                "question_format": "parallel_coords_query",
                "answer": answer_value,
                "answer_type": str(dataset.query.answer_type),
                "axis_i": int(dataset.query.axis_i),
                "axis_j": int(dataset.query.axis_j),
                "axis_i_label": str(dataset.metrics[int(dataset.query.axis_i)]),
                "axis_j_label": str(dataset.metrics[int(dataset.query.axis_j)]),
                "metrics": [str(value) for value in dataset.metrics],
                "profiles": list(profile_rows),
                "threshold": dataset.query.threshold,
                "reference_profile_id": dataset.query.reference_profile_id,
                "evidence_profile_ids": [str(value) for value in dataset.query.evidence_profile_ids],
                "crossing_pairs": [list(pair) for pair in dataset.query.crossing_pairs],
                **dict(dataset.query.params),
            },
            "witness_symbolic": {
                "type": "parallel_coordinates_witness",
                "answer": answer_value,
                "axis_pair": list(axis_pair),
                "profile_ids": [str(value) for value in dataset.query.evidence_profile_ids],
            },
            "projected_evidence": dict(projected_evidence),
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
            query_variant=str(query_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            scene_id=SCENE_ID,
        )


@register_task
class ChartsParallelCoordinatesAxisConditionCountTask(
    MergedChartQueryVariantTaskMixin,
    ChartsParallelCoordinatesProfileTask,
):
    """Count profiles satisfying two axis predicates."""

    task_id = "task_charts__parallel_coords__axis_condition_count"
    allowed_query_variants = CONDITION_QUERY_VARIANTS


@register_task
class ChartsParallelCoordinatesAxisDeltaExtremumLabelTask(
    MergedChartQueryVariantTaskMixin,
    ChartsParallelCoordinatesProfileTask,
):
    """Return the profile with the largest axis-to-axis change."""

    task_id = "task_charts__parallel_coords__axis_delta_extremum_label"
    allowed_query_variants = DELTA_QUERY_VARIANTS


@register_task
class ChartsParallelCoordinatesCrossingCountTask(
    MergedChartQueryVariantTaskMixin,
    ChartsParallelCoordinatesProfileTask,
):
    """Count profile-line crossings between adjacent axes."""

    task_id = "task_charts__parallel_coords__crossing_count"
    allowed_query_variants = CROSSING_QUERY_VARIANTS


__all__ = [
    "ChartsParallelCoordinatesAxisConditionCountTask",
    "ChartsParallelCoordinatesAxisDeltaExtremumLabelTask",
    "ChartsParallelCoordinatesCrossingCountTask",
    "ChartsParallelCoordinatesProfileTask",
    "CONDITION_QUERY_VARIANTS",
    "CROSSING_QUERY_VARIANTS",
    "DELTA_QUERY_VARIANTS",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_QUERY_VARIANTS",
]
