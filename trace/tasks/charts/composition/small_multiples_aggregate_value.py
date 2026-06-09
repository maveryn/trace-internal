"""Small-multiple composition chart aggregation task."""

from __future__ import annotations

import math
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
from ...shared.bbox_projection import bbox_union
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_int, resolve_render_rgb
from ...shared.text_rendering import load_font, temporary_default_font_family
from ...shared.text_legibility import draw_text_traced
from ..shared.complexity import build_chart_complexity, normalize_int_with_bounds, resolve_chart_complexity_weights
from ..shared.labeled_chart_common import (
    LabeledChartDefaults,
    balanced_choice_from_values,
    resolve_chart_axis_variant,
    sample_composition_with_sum,
)
from ..shared.fixed_query_task import MergedChartQueryVariantTaskMixin
from ..shared.label_assets import (
    resolve_chart_category_labels,
    resolve_chart_panel_labels,
    validate_chart_label_namespaces,
)
from ..shared.visual_defaults import (
    chart_font_asset_metadata,
    load_chart_background_defaults,
    load_chart_noise_defaults,
    sample_chart_font_family,
)


TASK_ID = "charts_composition_small_multiples_aggregate_value_base"
SCENE_ID = "small_multiple"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "top_k_by_segment_then_sum_other_segment_count",
    "conditioned_panel_sum_from_percent",
    "average_top_k_minus_average_bottom_k",
    "composition_shift_l1_distance",
)
AGGREGATE_QUERY_IDS: Tuple[str, ...] = (
    "top_k_by_segment_then_sum_other_segment_count",
    "conditioned_panel_sum_from_percent",
)
DIFFERENCE_QUERY_IDS: Tuple[str, ...] = (
    "average_top_k_minus_average_bottom_k",
    "composition_shift_l1_distance",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("small_multiple_pie", "small_multiple_donut")

_DEFAULTS = LabeledChartDefaults(canvas_width=1400, canvas_height=900)
_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "composition")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="composition")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="composition", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "top_k_by_segment_then_sum_other_segment_count": 0.82,
    "conditioned_panel_sum_from_percent": 0.78,
    "average_top_k_minus_average_bottom_k": 0.88,
    "composition_shift_l1_distance": 0.84,
}
_SCENE_VARIANT_LOADS: Dict[str, float] = {
    "small_multiple_pie": 0.48,
    "small_multiple_donut": 0.55,
}
_SEGMENT_COLORS: Tuple[Tuple[int, int, int], ...] = (
    (54, 119, 196),
    (219, 107, 59),
    (84, 157, 85),
    (162, 94, 179),
    (224, 168, 55),
    (69, 178, 176),
    (197, 83, 125),
)


@dataclass(frozen=True)
class _PanelSpec:
    label: str
    total: int
    shares_by_segment: Dict[str, int]


@dataclass(frozen=True)
class _Dataset:
    panels: Tuple[_PanelSpec, ...]
    segment_labels: Tuple[str, ...]
    answer_value: int
    annotation_values: Tuple[int, ...]
    annotation_keys: Tuple[Tuple[str, str], ...]
    trace_extras: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedSmallMultiples:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    panel_traces: Tuple[Dict[str, Any], ...]
    plot_bbox_px: Tuple[int, int, int, int]
    annotation_bbox_by_key: Dict[Tuple[str, str], List[float]]
    total_bbox_by_panel: Dict[str, List[float]]
    legend_bbox_px: List[float]
    legend_item_bboxes_px: Dict[str, List[float]]
    layout_jitter_meta: Dict[str, Any]


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


def _balanced_int(
    values: Sequence[int],
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> int:
    return balanced_choice_from_values(
        [int(value) for value in values],
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )


def _axis_is_explicit(params: Mapping[str, Any], *, explicit_key: str, weights_key: str) -> bool:
    return params.get(str(explicit_key)) is not None or params.get(str(weights_key)) is not None


def _params_with_shifted_sample_cursor(
    params: Mapping[str, Any],
    *,
    divisor: int,
) -> Dict[str, Any]:
    shifted = dict(params)
    if "_sample_cursor" not in shifted:
        return shifted
    shifted["_sample_cursor"] = abs(int(shifted["_sample_cursor"])) // max(1, int(divisor))
    return shifted


def _params_for_scene_axis(params: Mapping[str, Any]) -> Dict[str, Any]:
    shifted = dict(params)
    if "_sample_cursor" not in shifted:
        return shifted
    stride = max(1, int(_task_axis_stride(params)))
    sampling_index = abs(int(shifted["_sample_cursor"]))
    shifted["_sample_cursor"] = int(sampling_index // stride) + int(sampling_index % stride)
    return shifted


def _task_axis_stride(params: Mapping[str, Any]) -> int:
    if _axis_is_explicit(params, explicit_key="query_id", weights_key="query_id_weights"):
        return 1
    return len(SUPPORTED_QUERY_IDS)


def _scene_axis_stride(params: Mapping[str, Any]) -> int:
    if _axis_is_explicit(params, explicit_key="scene_variant", weights_key="scene_variant_weights"):
        return 1
    return len(SUPPORTED_SCENE_VARIANTS)


def _resolve_count_bounds(params: Mapping[str, Any], *, min_key: str, max_key: str, fallback_min: int, fallback_max: int) -> Tuple[int, int]:
    min_value = int(params.get(str(min_key), group_default(_GEN_DEFAULTS, str(min_key), int(fallback_min))))
    max_value = int(params.get(str(max_key), group_default(_GEN_DEFAULTS, str(max_key), int(fallback_max))))
    if int(min_value) > int(max_value):
        raise ValueError(f"{min_key} must be <= {max_key}")
    return int(min_value), int(max_value)


def _sample_total_values(params: Mapping[str, Any]) -> Tuple[int, ...]:
    raw = params.get("total_values", group_default(_GEN_DEFAULTS, "total_values", [1000, 1200, 1400, 1600, 1800, 2000, 2400, 3000]))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("total_values must be a sequence")
    values = tuple(int(value) for value in raw)
    if not values or any(int(value) % 100 != 0 or int(value) <= 0 for value in values):
        raise ValueError("total_values must contain positive multiples of 100")
    return values


def _choose_total(total_values: Sequence[int], *, instance_seed: int, namespace: str) -> int:
    rng = spawn_rng(int(instance_seed), str(namespace))
    return int(total_values[int(rng.randrange(0, len(total_values)))])


def _format_quoted(values: Sequence[str]) -> str:
    return ", ".join(f'"{str(value)}"' for value in values)


def _choose_segments(segment_count: int, *, instance_seed: int) -> Tuple[str, ...]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.segment_labels")
    labels = resolve_chart_category_labels(
        rng,
        count=int(segment_count),
        min_chars=2,
        max_chars=8,
        allow_spaces=False,
    ).labels
    return tuple(str(label) for label in labels)


def _resolved_label_metadata(resolved: Any) -> Dict[str, Any]:
    return {
        "label_variant": str(resolved.label_variant),
        "label_pool_kind": str(resolved.label_pool_kind),
        "label_source_kind": str(resolved.label_source_kind),
        "label_bucket": str(resolved.label_bucket),
        "label_manifest": str(resolved.label_manifest),
        "label_filter": dict(resolved.label_filter),
        "label_bucket_probabilities": dict(resolved.label_bucket_probabilities),
    }


def _choose_panel_labels(
    panel_count: int,
    *,
    segment_labels: Sequence[str],
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[str, ...], Dict[str, Any]]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.panel_labels")
    resolved = resolve_chart_panel_labels(
        rng,
        count=int(panel_count),
        min_chars=1,
        max_chars=10,
        allow_spaces=False,
        variant_weights=params.get(
            "panel_label_variant_weights",
            group_default(
                _GEN_DEFAULTS,
                "panel_label_variant_weights",
                {
                    "temporal_sequence": 0.6,
                    "named_compact": 1.0,
                    "report_topics": 0.75,
                    "technical_topics": 1.0,
                    "condition_labels": 0.5,
                },
            ),
        ),
        reserved_labels=tuple(str(label) for label in segment_labels),
    )
    collision_check = validate_chart_label_namespaces(
        panel_labels=resolved.labels,
        other_label_groups={"segment_labels": tuple(str(label) for label in segment_labels)},
        context="small-multiple composition panel labels",
    )
    return tuple(str(label) for label in resolved.labels), {
        "panel_label_resolution": _resolved_label_metadata(resolved),
        "panel_label_collision_check": dict(collision_check),
    }


def _sample_shares(
    *,
    segment_labels: Sequence[str],
    fixed: Mapping[str, int],
    instance_seed: int,
    namespace: str,
    value_min: int = 6,
    value_max: int = 58,
) -> Dict[str, int]:
    fixed_values = {str(key): int(value) for key, value in fixed.items()}
    remaining_labels = [str(label) for label in segment_labels if str(label) not in fixed_values]
    fixed_sum = int(sum(fixed_values.values()))
    remaining_sum = int(100 - fixed_sum)
    if not remaining_labels:
        if int(remaining_sum) != 0:
            raise ValueError("fixed shares do not sum to 100")
        return dict(fixed_values)
    if int(remaining_sum) < len(remaining_labels) * int(value_min) or int(remaining_sum) > len(remaining_labels) * int(value_max):
        raise ValueError("fixed shares leave no feasible remainder")
    rng = spawn_rng(int(instance_seed), str(namespace))
    values = sample_composition_with_sum(
        rng,
        target_sum=int(remaining_sum),
        count=len(remaining_labels),
        value_min=int(value_min),
        value_max=int(value_max),
    )
    rng.shuffle(values)
    shares = dict(fixed_values)
    shares.update({str(label): int(value) for label, value in zip(remaining_labels, values)})
    if int(sum(shares.values())) != 100:
        raise RuntimeError("percentage shares drifted from 100")
    return {str(label): int(shares[str(label)]) for label in segment_labels}


def _counts_for_panel(panel: _PanelSpec) -> Dict[str, int]:
    return {
        str(segment): int(int(share) * int(panel.total) // 100)
        for segment, share in panel.shares_by_segment.items()
    }


def _build_base_panels(
    *,
    panel_labels: Sequence[str],
    segment_labels: Sequence[str],
    total_values: Sequence[int],
    instance_seed: int,
    fixed_by_panel: Mapping[str, Mapping[str, int]] | None = None,
) -> Tuple[_PanelSpec, ...]:
    panels: List[_PanelSpec] = []
    fixed_by_panel = fixed_by_panel or {}
    for index, label in enumerate(panel_labels):
        shares = _sample_shares(
            segment_labels=segment_labels,
            fixed=fixed_by_panel.get(str(label), {}),
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.shares.{label}.{index}",
        )
        panels.append(
            _PanelSpec(
                label=str(label),
                total=_choose_total(total_values, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.total.{label}.{index}"),
                shares_by_segment=shares,
            )
        )
    return tuple(panels)


def _build_top_k_dataset(
    *,
    panel_labels: Sequence[str],
    segment_labels: Sequence[str],
    total_values: Sequence[int],
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.top_k")
    rank_segment, target_segment = rng.sample(list(segment_labels), 2)
    top_k_values = tuple(int(value) for value in params.get("top_k_values", group_default(_GEN_DEFAULTS, "top_k_values", [2, 3])))
    feasible_k = [value for value in top_k_values if 1 < int(value) < len(panel_labels)]
    top_k = _balanced_int(feasible_k, params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.top_k.k")
    supports = [16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56]
    rng.shuffle(supports)
    fixed_by_panel = {str(label): {str(rank_segment): int(supports[index])} for index, label in enumerate(panel_labels)}
    panels = _build_base_panels(
        panel_labels=panel_labels,
        segment_labels=segment_labels,
        total_values=total_values,
        instance_seed=int(instance_seed),
        fixed_by_panel=fixed_by_panel,
    )
    selected = tuple(sorted(panels, key=lambda panel: int(panel.shares_by_segment[str(rank_segment)]), reverse=True)[: int(top_k)])
    selected_counts = tuple(int(_counts_for_panel(panel)[str(target_segment)]) for panel in selected)
    annotation_keys = tuple((str(panel.label), str(target_segment)) for panel in selected)
    return _Dataset(
        panels=panels,
        segment_labels=tuple(segment_labels),
        answer_value=int(sum(selected_counts)),
        annotation_values=selected_counts,
        annotation_keys=annotation_keys,
        trace_extras={
            "rank_segment": str(rank_segment),
            "target_segment": str(target_segment),
            "top_k": int(top_k),
            "selected_panels": [str(panel.label) for panel in selected],
            "selected_target_counts": [int(value) for value in selected_counts],
            "calculation": "rank_panels_then_sum_target_counts",
        },
    )


def _build_conditioned_dataset(
    *,
    panel_labels: Sequence[str],
    segment_labels: Sequence[str],
    total_values: Sequence[int],
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.conditioned")
    condition_segment, target_segment = rng.sample(list(segment_labels), 2)
    threshold_values = tuple(int(value) for value in params.get("condition_threshold_values", group_default(_GEN_DEFAULTS, "condition_threshold_values", [32, 35, 38])))
    threshold = _balanced_int(threshold_values, params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.conditioned.threshold")
    selected_count_values = [value for value in range(2, len(panel_labels)) if value < len(panel_labels)]
    selected_count = _balanced_int(selected_count_values, params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.conditioned.selected_count")
    selected_labels = set(rng.sample(list(panel_labels), int(selected_count)))
    fixed_by_panel: Dict[str, Dict[str, int]] = {}
    for label in panel_labels:
        if str(label) in selected_labels:
            fixed_by_panel[str(label)] = {str(condition_segment): int(rng.randint(int(threshold) + 5, 56))}
        else:
            fixed_by_panel[str(label)] = {str(condition_segment): int(rng.randint(10, max(12, int(threshold) - 5)))}
    panels = _build_base_panels(
        panel_labels=panel_labels,
        segment_labels=segment_labels,
        total_values=total_values,
        instance_seed=int(instance_seed),
        fixed_by_panel=fixed_by_panel,
    )
    selected = tuple(panel for panel in panels if int(panel.shares_by_segment[str(condition_segment)]) > int(threshold))
    selected_counts = tuple(int(_counts_for_panel(panel)[str(target_segment)]) for panel in selected)
    annotation_keys = tuple((str(panel.label), str(target_segment)) for panel in selected)
    return _Dataset(
        panels=panels,
        segment_labels=tuple(segment_labels),
        answer_value=int(sum(selected_counts)),
        annotation_values=selected_counts,
        annotation_keys=annotation_keys,
        trace_extras={
            "condition_segment": str(condition_segment),
            "target_segment": str(target_segment),
            "threshold": int(threshold),
            "selected_panels": [str(panel.label) for panel in selected],
            "selected_target_counts": [int(value) for value in selected_counts],
            "calculation": "filter_panels_by_percentage_then_sum_target_counts",
        },
    )


def _build_average_difference_dataset(
    *,
    panel_labels: Sequence[str],
    segment_labels: Sequence[str],
    total_values: Sequence[int],
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Dataset:
    del params
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.average_diff")
    rank_segment, target_segment = rng.sample(list(segment_labels), 2)
    k = 2
    rank_support = [10, 12, 14, 16, 18, 20, 22, 24, 26]
    rng.shuffle(rank_support)
    ordered_labels = list(panel_labels)
    target_values_by_label: Dict[str, int] = {}
    ranked_preview = sorted(
        [(str(label), int(rank_support[index])) for index, label in enumerate(ordered_labels)],
        key=lambda item: item[1],
        reverse=True,
    )
    top_labels = {label for label, _ in ranked_preview[:k]}
    bottom_labels = {label for label, _ in ranked_preview[-k:]}
    for label in ordered_labels:
        if str(label) in top_labels:
            target_values_by_label[str(label)] = int(rng.choice([26, 30, 34]))
        elif str(label) in bottom_labels:
            target_values_by_label[str(label)] = int(rng.choice([8, 12, 16, 20, 24]))
        else:
            target_values_by_label[str(label)] = int(rng.choice([14, 18, 22]))
    fixed_by_panel = {
        str(label): {
            str(rank_segment): int(rank_support[index]),
            str(target_segment): int(target_values_by_label[str(label)]),
        }
        for index, label in enumerate(ordered_labels)
    }
    panels = _build_base_panels(
        panel_labels=panel_labels,
        segment_labels=segment_labels,
        total_values=total_values,
        instance_seed=int(instance_seed),
        fixed_by_panel=fixed_by_panel,
    )
    sorted_panels = tuple(sorted(panels, key=lambda panel: int(panel.shares_by_segment[str(rank_segment)]), reverse=True))
    top_panels = sorted_panels[:k]
    bottom_panels = sorted_panels[-k:]
    top_values = tuple(int(panel.shares_by_segment[str(target_segment)]) for panel in top_panels)
    bottom_values = tuple(int(panel.shares_by_segment[str(target_segment)]) for panel in bottom_panels)
    top_avg = int(sum(top_values) // k)
    bottom_avg = int(sum(bottom_values) // k)
    annotation_keys = tuple((str(panel.label), str(target_segment)) for panel in (*top_panels, *bottom_panels))
    return _Dataset(
        panels=panels,
        segment_labels=tuple(segment_labels),
        answer_value=int(top_avg - bottom_avg),
        annotation_values=tuple(int(value) for value in (*top_values, *bottom_values)),
        annotation_keys=annotation_keys,
        trace_extras={
            "rank_segment": str(rank_segment),
            "target_segment": str(target_segment),
            "top_k": int(k),
            "bottom_k": int(k),
            "top_panels": [str(panel.label) for panel in top_panels],
            "bottom_panels": [str(panel.label) for panel in bottom_panels],
            "top_target_percentages": [int(value) for value in top_values],
            "bottom_target_percentages": [int(value) for value in bottom_values],
            "top_average": int(top_avg),
            "bottom_average": int(bottom_avg),
            "calculation": "rank_panels_then_subtract_average_target_percentages",
        },
    )


def _build_shift_dataset(
    *,
    panel_labels: Sequence[str],
    segment_labels: Sequence[str],
    total_values: Sequence[int],
    instance_seed: int,
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.shift")
    panels = _build_base_panels(
        panel_labels=panel_labels,
        segment_labels=segment_labels,
        total_values=total_values,
        instance_seed=int(instance_seed),
    )
    start_label, end_label = rng.sample(list(panel_labels), 2)
    by_label = {str(panel.label): panel for panel in panels}
    start_panel = by_label[str(start_label)]
    end_panel = by_label[str(end_label)]
    changes = tuple(
        abs(int(end_panel.shares_by_segment[str(segment)]) - int(start_panel.shares_by_segment[str(segment)]))
        for segment in segment_labels
    )
    annotation_keys = tuple(
        (str(label), str(segment))
        for label in (str(start_panel.label), str(end_panel.label))
        for segment in segment_labels
    )
    return _Dataset(
        panels=panels,
        segment_labels=tuple(segment_labels),
        answer_value=int(sum(changes)),
        annotation_values=tuple(int(value) for value in changes),
        annotation_keys=annotation_keys,
        trace_extras={
            "start_panel": str(start_panel.label),
            "end_panel": str(end_panel.label),
            "segment_changes": [int(value) for value in changes],
            "calculation": "sum_absolute_percentage_point_changes",
        },
    )


def _build_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Dataset:
    panel_min, panel_max = _resolve_count_bounds(params, min_key="panel_count_min", max_key="panel_count_max", fallback_min=6, fallback_max=9)
    segment_min, segment_max = _resolve_count_bounds(params, min_key="segment_count_min", max_key="segment_count_max", fallback_min=5, fallback_max=7)
    count_params = _params_with_shifted_sample_cursor(
        params,
        divisor=int(_task_axis_stride(params) * _scene_axis_stride(params)),
    )
    panel_count = _balanced_int(
        range(int(panel_min), int(panel_max) + 1),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.panel_count",
    )
    segment_count = _balanced_int(
        range(int(segment_min), int(segment_max) + 1),
        params=count_params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.segment_count",
    )
    segment_labels = _choose_segments(int(segment_count), instance_seed=int(instance_seed))
    panel_labels, panel_label_meta = _choose_panel_labels(
        int(panel_count),
        segment_labels=segment_labels,
        params=params,
        instance_seed=int(instance_seed),
    )
    total_values = _sample_total_values(params)
    builders = {
        "top_k_by_segment_then_sum_other_segment_count": _build_top_k_dataset,
        "conditioned_panel_sum_from_percent": _build_conditioned_dataset,
        "average_top_k_minus_average_bottom_k": _build_average_difference_dataset,
    }
    if str(query_id) == "composition_shift_l1_distance":
        dataset = _build_shift_dataset(
            panel_labels=panel_labels,
            segment_labels=segment_labels,
            total_values=total_values,
            instance_seed=int(instance_seed),
        )
    else:
        dataset = builders[str(query_id)](
            panel_labels=panel_labels,
            segment_labels=segment_labels,
            total_values=total_values,
            params=params,
            instance_seed=int(instance_seed),
        )
    return _Dataset(
        panels=tuple(dataset.panels),
        segment_labels=tuple(dataset.segment_labels),
        answer_value=int(dataset.answer_value),
        annotation_values=tuple(int(value) for value in dataset.annotation_values),
        annotation_keys=tuple((str(panel), str(segment)) for panel, segment in dataset.annotation_keys),
        trace_extras={
            "panel_count": int(panel_count),
            "panel_count_range": [int(panel_min), int(panel_max)],
            "segment_count": int(segment_count),
            "segment_count_range": [int(segment_min), int(segment_max)],
            **dict(panel_label_meta),
            **dict(dataset.trace_extras),
        },
    )


def _text_bbox_at_origin(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: Any,
    *,
    stroke_width: int = 0,
) -> Tuple[float, float, float, float]:
    try:
        bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width)))
        return float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        pad = float(max(0, int(stroke_width)))
        return float(-pad), float(-pad), float(width + pad), float(height + pad)


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: Any, *, stroke_width: int = 0) -> Tuple[float, float]:
    bbox = _text_bbox_at_origin(draw, str(text), font, stroke_width=max(0, int(stroke_width)))
    return float(bbox[2] - bbox[0]), float(bbox[3] - bbox[1])


def _centered_text_bbox(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    font: Any,
    *,
    stroke_width: int = 0,
) -> Tuple[float, float, float, float]:
    raw = _text_bbox_at_origin(draw, str(text), font, stroke_width=max(0, int(stroke_width)))
    width = float(raw[2] - raw[0])
    height = float(raw[3] - raw[1])
    left = float(xy[0]) - (width / 2.0) - float(raw[0])
    top = float(xy[1]) - (height / 2.0) - float(raw[1])
    return (
        float(left + raw[0]),
        float(top + raw[1]),
        float(left + raw[2]),
        float(top + raw[3]),
    )


def _bbox_center_point(bbox: Sequence[float]) -> List[float]:
    return [
        round((float(bbox[0]) + float(bbox[2])) / 2.0, 3),
        round((float(bbox[1]) + float(bbox[3])) / 2.0, 3),
    ]


def _annotation_map_key(role: str, panel: str, segment: str | None = None) -> str:
    if segment is None:
        return f"{str(role)}|{str(panel)}"
    return f"{str(role)}|{str(panel)}|{str(segment)}"


def _format_annotation_key_list(keys: Sequence[str]) -> str:
    return ", ".join(f'"{str(key)}"' for key in keys)


def _build_keyed_annotation_points(
    *,
    query_id: str,
    dataset: _Dataset,
    rendered_scene: _RenderedSmallMultiples,
) -> Dict[str, List[float]]:
    extras = dict(dataset.trace_extras)
    points: Dict[str, List[float]] = {}

    def add_segment(role: str, panel: str, segment: str) -> None:
        bbox = rendered_scene.annotation_bbox_by_key.get((str(panel), str(segment)))
        if bbox is None:
            return
        points[_annotation_map_key(str(role), str(panel), str(segment))] = _bbox_center_point(bbox)

    def add_total(panel: str) -> None:
        bbox = rendered_scene.total_bbox_by_panel.get(str(panel))
        if bbox is None:
            return
        points[_annotation_map_key("total", str(panel))] = _bbox_center_point(bbox)

    if str(query_id) == "top_k_by_segment_then_sum_other_segment_count":
        rank_segment = str(extras["rank_segment"])
        target_segment = str(extras["target_segment"])
        for panel in extras.get("selected_panels", []):
            add_segment("rank", str(panel), rank_segment)
            add_segment("target", str(panel), target_segment)
            add_total(str(panel))
    elif str(query_id) == "conditioned_panel_sum_from_percent":
        condition_segment = str(extras["condition_segment"])
        target_segment = str(extras["target_segment"])
        for panel in extras.get("selected_panels", []):
            add_segment("condition", str(panel), condition_segment)
            add_segment("target", str(panel), target_segment)
            add_total(str(panel))
    elif str(query_id) == "average_top_k_minus_average_bottom_k":
        rank_segment = str(extras["rank_segment"])
        target_segment = str(extras["target_segment"])
        for panel in tuple(extras.get("top_panels", [])) + tuple(extras.get("bottom_panels", [])):
            add_segment("rank", str(panel), rank_segment)
            add_segment("target", str(panel), target_segment)
    elif str(query_id) == "composition_shift_l1_distance":
        start_panel = str(extras["start_panel"])
        end_panel = str(extras["end_panel"])
        for segment in dataset.segment_labels:
            add_segment("start", start_panel, str(segment))
            add_segment("end", end_panel, str(segment))
    else:
        raise ValueError(f"unsupported small-multiple query id: {query_id}")

    return dict(points)


def _draw_centered(draw: ImageDraw.ImageDraw, xy: Tuple[float, float], text: str, font: Any, fill: Tuple[int, int, int], *, stroke_width: int = 0, stroke_fill: Tuple[int, int, int] = (255, 255, 255)) -> List[float]:
    raw = _text_bbox_at_origin(draw, str(text), font, stroke_width=max(0, int(stroke_width)))
    width = float(raw[2] - raw[0])
    height = float(raw[3] - raw[1])
    left = float(xy[0]) - (width / 2.0) - float(raw[0])
    top = float(xy[1]) - (height / 2.0) - float(raw[1])
    draw_text_traced(draw,
        (float(left), float(top)),
        str(text),
        font=font,
        fill=fill,
        stroke_width=max(0, int(stroke_width)),
        stroke_fill=stroke_fill,
     role="readout", required=False,)
    return [
        float(left + raw[0]),
        float(top + raw[1]),
        float(left + raw[2]),
        float(top + raw[3]),
    ]


def _segment_bbox(center: Tuple[float, float], radius: float, start_angle: float, end_angle: float) -> List[float]:
    mid = math.radians((float(start_angle) + float(end_angle)) / 2.0)
    cx = float(center[0]) + (math.cos(mid) * float(radius) * 0.58)
    cy = float(center[1]) + (math.sin(mid) * float(radius) * 0.58)
    half = max(18.0, float(radius) * 0.22)
    return [float(cx - half), float(cy - half), float(cx + half), float(cy + half)]


def _render_small_multiples(
    *,
    base_image: Image.Image,
    dataset: _Dataset,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _RenderedSmallMultiples:
    image = base_image.convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size
    text_color = resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        "text_color_rgb",
        [36, 40, 48],
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    grid_color = resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        "grid_color_rgb",
        [214, 219, 228],
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    panel_fill = resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        "plot_fill_rgb",
        [255, 255, 255],
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    mark_outline_width_px = resolve_render_int(
        params,
        _RENDER_DEFAULTS,
        "mark_outline_width_px",
        2,
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    title_font = load_font(int(params.get("title_font_size_px", group_default(_RENDER_DEFAULTS, "title_font_size_px", 24))), bold=True)
    subtitle_font = load_font(int(params.get("subtitle_font_size_px", group_default(_RENDER_DEFAULTS, "subtitle_font_size_px", 17))), bold=False)
    slice_font = load_font(int(params.get("slice_font_size_px", group_default(_RENDER_DEFAULTS, "slice_font_size_px", 17))), bold=True)
    small_slice_font = load_font(int(params.get("small_slice_font_size_px", group_default(_RENDER_DEFAULTS, "small_slice_font_size_px", 14))), bold=True)
    legend_font = load_font(int(params.get("legend_font_size_px", group_default(_RENDER_DEFAULTS, "legend_font_size_px", 18))), bold=True)

    margin_left = int(params.get("plot_margin_left_px", group_default(_RENDER_DEFAULTS, "plot_margin_left_px", 54)))
    margin_right = int(params.get("plot_margin_right_px", group_default(_RENDER_DEFAULTS, "plot_margin_right_px", 54)))
    margin_top = int(params.get("plot_margin_top_px", group_default(_RENDER_DEFAULTS, "plot_margin_top_px", 38)))
    margin_bottom = int(params.get("plot_margin_bottom_px", group_default(_RENDER_DEFAULTS, "plot_margin_bottom_px", 110)))
    margin_left, margin_right, margin_top, margin_bottom, layout_jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(margin_left),
        right_px=int(margin_right),
        top_px=int(margin_top),
        bottom_px=int(margin_bottom),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.layout",
    )
    plot_bbox = (margin_left, margin_top, width - margin_right, height - margin_bottom)
    panel_count = len(dataset.panels)
    cols = 2 if int(panel_count) <= 4 else 3
    rows = int(math.ceil(float(panel_count) / float(cols)))
    gap_x = 26
    gap_y = 28
    cell_width = (plot_bbox[2] - plot_bbox[0] - ((cols - 1) * gap_x)) / float(cols)
    cell_height = (plot_bbox[3] - plot_bbox[1] - ((rows - 1) * gap_y)) / float(rows)
    entities: List[Dict[str, Any]] = []
    panel_traces: List[Dict[str, Any]] = []
    annotation_bbox_by_key: Dict[Tuple[str, str], List[float]] = {}
    total_bbox_by_panel: Dict[str, List[float]] = {}
    segment_color_by_label = {
        str(label): _SEGMENT_COLORS[index % len(_SEGMENT_COLORS)]
        for index, label in enumerate(dataset.segment_labels)
    }

    for panel_index, panel in enumerate(dataset.panels):
        row = int(panel_index // cols)
        col = int(panel_index % cols)
        x0 = float(plot_bbox[0] + (col * (cell_width + gap_x)))
        y0 = float(plot_bbox[1] + (row * (cell_height + gap_y)))
        x1 = float(x0 + cell_width)
        y1 = float(y0 + cell_height)
        draw.rounded_rectangle((x0, y0, x1, y1), radius=8, fill=panel_fill, outline=grid_color, width=max(1, int(mark_outline_width_px)))
        _draw_centered(draw, ((x0 + x1) / 2.0, y0 + 23), str(panel.label), title_font, text_color)
        total_bbox_by_panel[str(panel.label)] = _draw_centered(
            draw,
            ((x0 + x1) / 2.0, y0 + 51),
            f"Total {int(panel.total)}",
            subtitle_font,
            text_color,
        )
        radius = max(42.0, min(cell_width * 0.29, (cell_height - 78.0) * 0.43))
        center = ((x0 + x1) / 2.0, y0 + 63.0 + radius)
        pie_box = (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius)
        start_angle = -90.0
        slice_traces: List[Dict[str, Any]] = []
        for segment in dataset.segment_labels:
            share = int(panel.shares_by_segment[str(segment)])
            end_angle = float(start_angle + (float(share) * 3.6))
            color = segment_color_by_label[str(segment)]
            draw.pieslice(pie_box, start=float(start_angle), end=float(end_angle), fill=color, outline=(255, 255, 255), width=max(1, int(mark_outline_width_px)))
            if str(scene_variant) == "small_multiple_donut":
                inner = radius * 0.45
                draw.ellipse((center[0] - inner, center[1] - inner, center[0] + inner, center[1] + inner), fill=panel_fill, outline=panel_fill)
            wedge_bbox = _segment_bbox(center, radius, start_angle, end_angle)
            mid = math.radians((start_angle + end_angle) / 2.0)
            if int(share) <= 7:
                label_radius = radius * (0.84 if str(scene_variant) == "small_multiple_pie" else 0.82)
                active_slice_font = small_slice_font
            else:
                label_radius = radius * (0.70 if str(scene_variant) == "small_multiple_pie" else 0.76)
                active_slice_font = slice_font
            lx = float(center[0] + (math.cos(mid) * label_radius))
            ly = float(center[1] + (math.sin(mid) * label_radius))
            text_bbox = _draw_centered(
                draw,
                (lx, ly),
                str(share),
                active_slice_font,
                (255, 255, 255),
                stroke_width=2,
                stroke_fill=(30, 34, 42),
            )
            annotation_bbox_by_key[(str(panel.label), str(segment))] = list(text_bbox)
            count_value = int(int(share) * int(panel.total) // 100)
            slice_trace = {
                "panel_label": str(panel.label),
                "segment_label": str(segment),
                "share_percent": int(share),
                "total": int(panel.total),
                "count": int(count_value),
                "slice_bbox_px": list(text_bbox),
                "slice_wedge_bbox_px": list(wedge_bbox),
                "slice_center_px": [float(lx), float(ly)],
                "fill_rgb": list(color),
            }
            entities.append(
                {
                    "entity_id": f"{panel.label}:{segment}",
                    "kind": "composition_segment",
                    "attrs": dict(slice_trace),
                }
            )
            slice_traces.append(dict(slice_trace))
            start_angle = float(end_angle)
        panel_traces.append(
            {
                "panel_label": str(panel.label),
                "total": int(panel.total),
                "panel_bbox_px": [float(x0), float(y0), float(x1), float(y1)],
                "slices": slice_traces,
            }
        )

    legend_y = height - 58
    legend_items = list(dataset.segment_labels)
    item_width = max(118.0, (width - margin_left - margin_right) / float(max(1, len(legend_items))))
    legend_x0 = (width - (item_width * len(legend_items))) / 2.0
    legend_boxes: List[Sequence[float]] = []
    legend_item_bboxes: Dict[str, List[float]] = {}
    for index, segment in enumerate(legend_items):
        x = float(legend_x0 + (index * item_width))
        color = segment_color_by_label[str(segment)]
        swatch_bbox = (float(x), float(legend_y - 11), float(x + 26), float(legend_y + 15))
        legend_text = f"Segment {segment}"
        text_xy = (float(x + 34), float(legend_y - 12))
        text_bbox = draw.textbbox(text_xy, legend_text, font=legend_font)
        row_bbox = bbox_union((swatch_bbox, text_bbox), padding=4.0)
        legend_boxes.append(row_bbox)
        legend_item_bboxes[str(segment)] = list(row_bbox)
        draw.rectangle(swatch_bbox, fill=color, outline=(80, 84, 92), width=1)
        draw_text_traced(draw, text_xy, legend_text, font=legend_font, fill=text_color, role="readout", required=False)
    legend_bbox = bbox_union(legend_boxes, padding=6.0) if legend_boxes else []

    return _RenderedSmallMultiples(
        image=image,
        entities=tuple(entities),
        panel_traces=tuple(panel_traces),
        plot_bbox_px=tuple(int(value) for value in plot_bbox),
        annotation_bbox_by_key=dict(annotation_bbox_by_key),
        total_bbox_by_panel=dict(total_bbox_by_panel),
        legend_bbox_px=list(legend_bbox),
        legend_item_bboxes_px=dict(legend_item_bboxes),
        layout_jitter_meta=dict(layout_jitter_meta),
    )


class ChartsCompositionSmallMultiplesAggregateValueTask:
    """Return an integer aggregation over small-multiple composition charts."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "composition"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        if str(self.task_id) != TASK_ID:
            shared_gen_defaults, _, _ = split_generation_rendering_prompt_defaults(
                _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
            )
            task_gen_defaults, _, _ = split_generation_rendering_prompt_defaults(
                _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
                task_id=str(self.task_id),
            )
            task_override_params = {
                str(key): value
                for key, value in task_gen_defaults.items()
                if shared_gen_defaults.get(str(key)) != value
            }
            effective_params = dict(task_override_params)
            effective_params.update(dict(params))
            if "query_id_weights" in task_override_params:
                raw_weights = params.get("query_id_weights")
                override_weights = task_override_params["query_id_weights"]
                override_keys = set(str(key) for key in override_weights) if isinstance(override_weights, Mapping) else set()
                raw_keys = set(str(key) for key in raw_weights) if isinstance(raw_weights, Mapping) else set()
                raw_is_uniform_allowed = (
                    isinstance(raw_weights, Mapping)
                    and raw_keys == override_keys
                    and all(float(value) == 1.0 for value in raw_weights.values())
                )
                if raw_is_uniform_allowed:
                    effective_params["query_id_weights"] = task_override_params["query_id_weights"]
            params = effective_params
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        scene_params = _params_for_scene_axis(params)
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(scene_params, instance_seed=int(instance_seed))
        dataset = _build_dataset(query_id=str(query_id), params=params, instance_seed=int(instance_seed))

        canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
        canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
        background, background_meta = make_background_canvas(
            canvas_width=int(canvas_width),
            canvas_height=int(canvas_height),
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
            rendered_scene = _render_small_multiples(
                base_image=background,
                dataset=dataset,
                scene_variant=str(scene_variant),
                params=params,
                instance_seed=int(instance_seed),
            )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        annotation_points_by_key = _build_keyed_annotation_points(
            query_id=str(query_id),
            dataset=dataset,
            rendered_scene=rendered_scene,
        )
        annotation_key_list = _format_annotation_key_list(list(annotation_points_by_key.keys()))

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "object_description_small_multiple_pie",
                "object_description_small_multiple_donut",
                "annotation_hint_top_k_by_segment_then_sum_other_segment_count",
                "annotation_hint_conditioned_panel_sum_from_percent",
                "annotation_hint_average_top_k_minus_average_bottom_k",
                "annotation_hint_composition_shift_l1_distance",
                "json_example_top_k_by_segment_then_sum_other_segment_count",
                "json_example_conditioned_panel_sum_from_percent",
                "json_example_average_top_k_minus_average_bottom_k",
                "json_example_composition_shift_l1_distance",
                "json_example_answer_only_top_k_by_segment_then_sum_other_segment_count",
                "json_example_answer_only_conditioned_panel_sum_from_percent",
                "json_example_answer_only_average_top_k_minus_average_bottom_k",
                "json_example_answer_only_composition_shift_l1_distance",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        extras = dict(dataset.trace_extras)
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        annotation_hint = str(prompt_defaults[f"annotation_hint_{str(query_id)}"]).format(
            annotation_key_list=str(annotation_key_list)
        )
        json_example = str(prompt_defaults[f"json_example_{str(query_id)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(query_id)}"])
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
                "top_k": str(extras.get("top_k", "")),
                "bottom_k": str(extras.get("bottom_k", "")),
                "rank_segment": str(extras.get("rank_segment", "")),
                "target_segment": str(extras.get("target_segment", "")),
                "condition_segment": str(extras.get("condition_segment", "")),
                "threshold": str(extras.get("threshold", "")),
                "start_panel": str(extras.get("start_panel", "")),
                "end_panel": str(extras.get("end_panel", "")),
                "segment_list": _format_quoted(dataset.segment_labels),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(annotation_hint),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        panels_trace = [
            {
                "panel_label": str(panel.label),
                "total": int(panel.total),
                "shares_by_segment": {str(key): int(value) for key, value in panel.shares_by_segment.items()},
                "counts_by_segment": _counts_for_panel(panel),
            }
            for panel in dataset.panels
        ]
        point_set = [list(point) for point in annotation_points_by_key.values()]
        answer_gt = TypedValue(type="integer", value=int(dataset.answer_value))
        annotation_gt = TypedValue(type="keyed_point_map", value=dict(annotation_points_by_key))
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": f"chart_{str(scene_variant)}_composition_small_multiples",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "segment_labels": [str(label) for label in dataset.segment_labels],
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
                    "query_id_probabilities": dict(query_id_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "panel_count": int(extras["panel_count"]),
                    "segment_count": int(extras["segment_count"]),
                    **{
                        str(key): value
                        for key, value in extras.items()
                        if str(key)
                        in {
                            "rank_segment",
                            "target_segment",
                            "condition_segment",
                            "threshold",
                            "top_k",
                            "bottom_k",
                            "start_panel",
                            "end_panel",
                        }
                    },
                },
            },
            "render_spec": {
                "canvas_width": int(canvas_width),
                "canvas_height": int(canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "font_assets": chart_font_asset_metadata(str(chart_font_family)),
                "layout_jitter": dict(rendered_scene.layout_jitter_meta),
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "small_multiple_layout": "grid",
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "legend_bbox_px": list(rendered_scene.legend_bbox_px),
                "legend_item_bboxes_px": {
                    str(segment): list(bbox)
                    for segment, bbox in rendered_scene.legend_item_bboxes_px.items()
                },
                "context_protected_bboxes_px": {
                    "plot": list(rendered_scene.plot_bbox_px),
                    **({"legend": list(rendered_scene.legend_bbox_px)} if rendered_scene.legend_bbox_px else {}),
                },
                "panel_traces": [dict(panel) for panel in rendered_scene.panel_traces],
                "annotation_bbox_by_key": {
                    f"{panel}:{segment}": list(bbox)
                    for (panel, segment), bbox in rendered_scene.annotation_bbox_by_key.items()
                },
                "total_bbox_by_panel": {
                    str(panel): list(bbox)
                    for panel, bbox in rendered_scene.total_bbox_by_panel.items()
                },
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "answer_value": int(dataset.answer_value),
                "annotation_values": [int(value) for value in dataset.annotation_values],
                "annotation_keys": [[str(panel), str(segment)] for panel, segment in dataset.annotation_keys],
                "annotation_point_keys": list(annotation_points_by_key.keys()),
                "segment_labels": [str(label) for label in dataset.segment_labels],
                "panels": panels_trace,
                "question_format": "numeric_open",
                "query_id_probabilities": dict(query_id_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                **dict(extras),
            },
            "witness_symbolic": {
                "type": "small_multiple_aggregate",
                "query_id": str(query_id),
                "answer_value": int(dataset.answer_value),
                "annotation_values": [int(value) for value in dataset.annotation_values],
                "annotation_point_keys": list(annotation_points_by_key.keys()),
                "calculation": dict(extras),
            },
            "projected_annotation": {
                "type": "keyed_point_map",
                "keyed_point_map": dict(annotation_points_by_key),
                "pixel_keyed_point_map": dict(annotation_points_by_key),
                "point_set": list(point_set),
                "pixel_point_set": list(point_set),
            },
        }
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(extras["panel_count"]), extras["panel_count_range"]),
                "reasoning_load": float(_REASONING_LOAD_BY_VARIANT[str(query_id)]),
                "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(scene_variant)]),
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
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class ChartsCompositionSmallMultiplesConditionedPanelSumFromPercentTask(
    MergedChartQueryVariantTaskMixin,
    ChartsCompositionSmallMultiplesAggregateValueTask,
):
    """Compute a conditioned panel sum from percent composition values."""

    task_id = "task_charts__small_multiple__conditioned_panel_sum_from_percent"
    allowed_query_ids = ("conditioned_panel_sum_from_percent",)


@register_task
class ChartsCompositionSmallMultiplesTopKBySegmentThenSumOtherSegmentCountTask(
    MergedChartQueryVariantTaskMixin,
    ChartsCompositionSmallMultiplesAggregateValueTask,
):
    """Select panels by one segment ranking and sum another segment count."""

    task_id = "task_charts__small_multiple__top_k_by_segment_then_sum_other_segment_count"
    allowed_query_ids = ("top_k_by_segment_then_sum_other_segment_count",)


@register_task
class ChartsCompositionSmallMultiplesAverageTopKMinusAverageBottomKTask(
    MergedChartQueryVariantTaskMixin,
    ChartsCompositionSmallMultiplesAggregateValueTask,
):
    """Compute the difference between top-k and bottom-k segment averages."""

    task_id = "task_charts__small_multiple__average_top_k_minus_average_bottom_k"
    allowed_query_ids = ("average_top_k_minus_average_bottom_k",)


@register_task
class ChartsCompositionSmallMultiplesCompositionShiftL1DistanceTask(
    MergedChartQueryVariantTaskMixin,
    ChartsCompositionSmallMultiplesAggregateValueTask,
):
    """Compute the L1 composition shift between two panels."""

    task_id = "task_charts__small_multiple__composition_shift_l1_distance"
    allowed_query_ids = ("composition_shift_l1_distance",)


__all__ = [
    "AGGREGATE_QUERY_IDS",
    "ChartsCompositionSmallMultiplesAverageTopKMinusAverageBottomKTask",
    "ChartsCompositionSmallMultiplesAggregateValueTask",
    "ChartsCompositionSmallMultiplesCompositionShiftL1DistanceTask",
    "ChartsCompositionSmallMultiplesConditionedPanelSumFromPercentTask",
    "ChartsCompositionSmallMultiplesTopKBySegmentThenSumOtherSegmentCountTask",
    "DIFFERENCE_QUERY_IDS",
]
