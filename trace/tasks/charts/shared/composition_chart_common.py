"""Shared generation/render helpers for composition-style chart task families."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default
from .labeled_chart_common import (
    LabeledChartDefaults,
    PIE_LIKE_SCENE_VARIANTS,
    balanced_choice_from_values,
    compose_with_sum,
    projected_mark_evidence,
    resolve_value_bounds,
    sample_composition_with_sum,
    sample_chart_labels,
)
from .multiseries_chart_common import (
    build_multiseries_mark_specs,
    resolve_category_count_bounds,
    resolve_multiseries_chart_colors,
    resolve_series_count_bounds,
    sample_series_labels,
)


TaskVariant = str
SceneVariant = str

SUPPORTED_COMPOSITION_TASK_VARIANTS: Tuple[str, ...] = (
    "stack_total_at_label",
    "stack_segment_value",
    "combined_share_subset",
)
STACKED_COMPOSITION_SCENE_VARIANTS: Tuple[str, ...] = (
    "stacked_bar",
    "stacked_horizontal_bar",
)
SUPPORTED_COMPOSITION_SCENE_VARIANTS: Tuple[str, ...] = (
    "stacked_bar",
    "stacked_horizontal_bar",
    "pie",
    "donut",
)
_SCENE_VARIANTS_BY_TASK_VARIANT: Dict[str, Tuple[str, ...]] = {
    "stack_total_at_label": STACKED_COMPOSITION_SCENE_VARIANTS,
    "stack_segment_value": STACKED_COMPOSITION_SCENE_VARIANTS,
    "combined_share_subset": ("pie", "donut"),
}


@dataclass(frozen=True)
class CompositionChartDefaults(LabeledChartDefaults):
    """Stable fallback defaults shared by composition-style chart tasks."""

    category_count_min: int = 4
    category_count_max: int = 7
    series_count_min: int = 3
    series_count_max: int = 5
    value_min: int = 4
    value_max: int = 18
    canvas_width: int = 980
    canvas_height: int = 620
    plot_margin_left_px: int = 108
    plot_margin_right_px: int = 56
    plot_margin_top_px: int = 44
    plot_margin_bottom_px: int = 100


def supported_scene_variants_for_task_variant(task_variant: str) -> Tuple[str, ...]:
    """Return the supported scene variants for one composition query variant."""

    variants = _SCENE_VARIANTS_BY_TASK_VARIANT.get(str(task_variant))
    if variants is None:
        raise ValueError(f"unsupported composition task_variant: {task_variant}")
    return tuple(str(value) for value in variants)


def _choose_count(
    *,
    params: Mapping[str, Any],
    explicit_key: str,
    supported_values: Sequence[int],
    instance_seed: int,
    namespace: str,
) -> int:
    """Choose one explicit-or-balanced count from the supported values."""

    ordered = [int(value) for value in supported_values]
    if not ordered:
        raise ValueError(f"no feasible values for {namespace}")
    explicit_value = params.get(str(explicit_key))
    if explicit_value is not None:
        selected = int(explicit_value)
        if int(selected) not in set(ordered):
            raise ValueError(f"explicit {explicit_key} is outside feasible support")
        return int(selected)
    return balanced_choice_from_values(
        ordered,
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )


def _values_by_label(labels: Sequence[str], values: Sequence[int]) -> Dict[str, int]:
    """Map ordered labels to ordered integer values."""

    return {
        str(label): int(value)
        for label, value in zip(labels, values)
    }


def _sample_stack_values(
    rng,
    *,
    series_count: int,
    value_min: int,
    value_max: int,
) -> List[int]:
    """Sample one ordered positive stack-value list."""

    return [int(rng.randint(int(value_min), int(value_max))) for _ in range(int(series_count))]


def _build_stack_total_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: CompositionChartDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Build one stacked-chart dataset for `stack_total_at_label`."""

    value_min, value_max = resolve_value_bounds(params, gen_defaults=gen_defaults, defaults=defaults, task_id=task_id)
    category_count_min, category_count_max = resolve_category_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    series_count_min, series_count_max = resolve_series_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    target_answer_min = int(
        params.get(
            "target_answer_min",
            group_default(gen_defaults, "target_answer_min", int(series_count_min) * int(value_min)),
        )
    )
    target_answer_max = int(
        params.get(
            "target_answer_max",
            group_default(gen_defaults, "target_answer_max", int(series_count_max) * int(value_max)),
        )
    )
    feasible_answers = [
        int(value)
        for value in range(int(target_answer_min), int(target_answer_max) + 1)
        if any(
            int(series_count) * int(value_min) <= int(value) <= int(series_count) * int(value_max)
            for series_count in range(int(series_count_min), int(series_count_max) + 1)
        )
    ]
    target_answer = balanced_choice_from_values(
        feasible_answers,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.target_answer:stack_total_at_label",
    )
    feasible_series_counts = [
        int(series_count)
        for series_count in range(int(series_count_min), int(series_count_max) + 1)
        if int(series_count) * int(value_min) <= int(target_answer) <= int(series_count) * int(value_max)
    ]
    series_count = _choose_count(
        params=params,
        explicit_key="series_count",
        supported_values=feasible_series_counts,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.series_count:stack_total_at_label:{int(target_answer)}",
    )
    category_count = _choose_count(
        params=params,
        explicit_key="category_count",
        supported_values=range(int(category_count_min), int(category_count_max) + 1),
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.category_count:stack_total_at_label",
    )

    series_labels = list(sample_series_labels(count=int(series_count), instance_seed=int(instance_seed)))
    category_labels = list(sample_chart_labels(count=int(category_count), instance_seed=int(instance_seed)))
    query_rng = spawn_rng(int(instance_seed), f"{task_id}.stack_total.query")
    query_category_index = int(query_rng.randrange(len(category_labels)))
    query_category_label = str(category_labels[int(query_category_index)])

    values_rng = spawn_rng(int(instance_seed), f"{task_id}.stack_total.values")
    values_by_category: Dict[str, Dict[str, int]] = {}
    evidence_values: List[int] | None = None
    for category_label in category_labels:
        if str(category_label) == str(query_category_label):
            stack_values = compose_with_sum(
                int(target_answer),
                count=int(series_count),
                value_min=int(value_min),
                value_max=int(value_max),
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.stack_total.compose",
            )
        else:
            stack_values = _sample_stack_values(
                values_rng,
                series_count=int(series_count),
                value_min=int(value_min),
                value_max=int(value_max),
            )
        values_by_category[str(category_label)] = _values_by_label(series_labels, stack_values)
        if str(category_label) == str(query_category_label):
            evidence_values = [int(value) for value in stack_values]
    if evidence_values is None:
        raise RuntimeError("stack_total_at_label failed to assign evidence values")

    return {
        "scene_mode": "stacked",
        "series_labels": list(series_labels),
        "category_labels": list(category_labels),
        "values_by_category": {
            str(category_label): {
                str(series_label): int(value)
                for series_label, value in values_by_category[str(category_label)].items()
            }
            for category_label in category_labels
        },
        "query_category_label": str(query_category_label),
        "query_series_label": "",
        "query_subset_labels": [],
        "evidence_labels": list(series_labels),
        "evidence_values": [int(value) for value in evidence_values],
        "answer_value": int(target_answer),
        "series_count": int(series_count),
        "category_count": int(category_count),
        "series_count_range": [int(series_count_min), int(series_count_max)],
        "category_count_range": [int(category_count_min), int(category_count_max)],
        "target_answer": int(target_answer),
        "target_answer_range": [
            int(min(feasible_answers)),
            int(max(feasible_answers)),
        ],
        "value_semantics": "integer",
        "composition_scope": "stack",
    }


def _build_stack_segment_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: CompositionChartDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Build one stacked-chart dataset for `stack_segment_value`."""

    value_min, value_max = resolve_value_bounds(params, gen_defaults=gen_defaults, defaults=defaults, task_id=task_id)
    category_count_min, category_count_max = resolve_category_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    series_count_min, series_count_max = resolve_series_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    target_answer_min = int(params.get("target_answer_min", group_default(gen_defaults, "target_answer_min", int(value_min))))
    target_answer_max = int(params.get("target_answer_max", group_default(gen_defaults, "target_answer_max", int(value_max))))
    feasible_answers = [int(value) for value in range(int(target_answer_min), int(target_answer_max) + 1)]
    target_answer = balanced_choice_from_values(
        feasible_answers,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.target_answer:stack_segment_value",
    )
    series_count = _choose_count(
        params=params,
        explicit_key="series_count",
        supported_values=range(int(series_count_min), int(series_count_max) + 1),
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.series_count:stack_segment_value",
    )
    category_count = _choose_count(
        params=params,
        explicit_key="category_count",
        supported_values=range(int(category_count_min), int(category_count_max) + 1),
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.category_count:stack_segment_value",
    )
    series_labels = list(sample_series_labels(count=int(series_count), instance_seed=int(instance_seed)))
    category_labels = list(sample_chart_labels(count=int(category_count), instance_seed=int(instance_seed)))

    query_rng = spawn_rng(int(instance_seed), f"{task_id}.stack_segment.query")
    query_category_label = str(category_labels[int(query_rng.randrange(len(category_labels)))])
    query_series_label = str(series_labels[int(query_rng.randrange(len(series_labels)))])

    values_rng = spawn_rng(int(instance_seed), f"{task_id}.stack_segment.values")
    values_by_category: Dict[str, Dict[str, int]] = {}
    evidence_values: List[int] | None = None
    for category_label in category_labels:
        stack_values = _sample_stack_values(
            values_rng,
            series_count=int(series_count),
            value_min=int(value_min),
            value_max=int(value_max),
        )
        if str(category_label) == str(query_category_label):
            query_index = series_labels.index(str(query_series_label))
            stack_values[int(query_index)] = int(target_answer)
            evidence_values = [int(value) for value in stack_values]
        values_by_category[str(category_label)] = _values_by_label(series_labels, stack_values)
    if evidence_values is None:
        raise RuntimeError("stack_segment_value failed to assign evidence values")

    return {
        "scene_mode": "stacked",
        "series_labels": list(series_labels),
        "category_labels": list(category_labels),
        "values_by_category": {
            str(category_label): {
                str(series_label): int(value)
                for series_label, value in values_by_category[str(category_label)].items()
            }
            for category_label in category_labels
        },
        "query_category_label": str(query_category_label),
        "query_series_label": str(query_series_label),
        "query_subset_labels": [],
        "evidence_labels": list(series_labels),
        "evidence_values": [int(value) for value in evidence_values],
        "answer_value": int(target_answer),
        "series_count": int(series_count),
        "category_count": int(category_count),
        "series_count_range": [int(series_count_min), int(series_count_max)],
        "category_count_range": [int(category_count_min), int(category_count_max)],
        "target_answer": int(target_answer),
        "target_answer_range": [int(min(feasible_answers)), int(max(feasible_answers))],
        "value_semantics": "integer",
        "composition_scope": "stack",
    }


def _build_combined_share_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: CompositionChartDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Build one pie-style percentage composition for `combined_share_subset`."""

    series_count_min, series_count_max = resolve_series_count_bounds(
        params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
    )
    if int(series_count_min) < 3:
        raise ValueError("combined_share_subset requires at least three labels")
    series_count = _choose_count(
        params=params,
        explicit_key="series_count",
        supported_values=range(int(series_count_min), int(series_count_max) + 1),
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.series_count:combined_share_subset",
    )
    series_labels = list(sample_series_labels(count=int(series_count), instance_seed=int(instance_seed)))
    query_rng = spawn_rng(int(instance_seed), f"{task_id}.combined_share.query")
    query_indices = list(range(int(series_count)))
    query_rng.shuffle(query_indices)
    subset_indices = sorted(query_indices[:2])
    subset_labels = [str(series_labels[int(index)]) for index in subset_indices]

    target_answer_min = int(params.get("target_answer_min", group_default(gen_defaults, "target_answer_min", 5)))
    target_answer_max = int(params.get("target_answer_max", group_default(gen_defaults, "target_answer_max", 95)))
    subset_min = 2
    subset_max = 100 - (int(series_count) - 2)
    feasible_answers = [
        int(value)
        for value in range(int(target_answer_min), int(target_answer_max) + 1)
        if int(subset_min) <= int(value) <= int(subset_max)
    ]
    target_answer = balanced_choice_from_values(
        feasible_answers,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.target_answer:combined_share_subset:{int(series_count)}",
    )

    values_rng = spawn_rng(int(instance_seed), f"{task_id}.combined_share.values")
    subset_values = sample_composition_with_sum(
        values_rng,
        target_sum=int(target_answer),
        count=2,
        value_min=1,
        value_max=99,
    )
    remaining_values = sample_composition_with_sum(
        values_rng,
        target_sum=100 - int(target_answer),
        count=int(series_count) - 2,
        value_min=1,
        value_max=99,
    )
    values_by_label: Dict[str, int] = {}
    remaining_iter = iter(int(value) for value in remaining_values)
    subset_iter = iter(int(value) for value in subset_values)
    for index, series_label in enumerate(series_labels):
        if int(index) in set(subset_indices):
            values_by_label[str(series_label)] = int(next(subset_iter))
        else:
            values_by_label[str(series_label)] = int(next(remaining_iter))
    evidence_values = [int(values_by_label[str(label)]) for label in series_labels]

    return {
        "scene_mode": "pie_like",
        "series_labels": list(series_labels),
        "category_labels": [],
        "values": [int(values_by_label[str(label)]) for label in series_labels],
        "values_by_label": {str(label): int(values_by_label[str(label)]) for label in series_labels},
        "query_category_label": "",
        "query_series_label": "",
        "query_subset_labels": list(subset_labels),
        "evidence_labels": list(series_labels),
        "evidence_values": [int(value) for value in evidence_values],
        "answer_value": int(target_answer),
        "series_count": int(series_count),
        "category_count": 0,
        "series_count_range": [int(series_count_min), int(series_count_max)],
        "category_count_range": [0, 0],
        "target_answer": int(target_answer),
        "target_answer_range": [int(min(feasible_answers)), int(max(feasible_answers))],
        "value_semantics": "percentage",
        "composition_total": 100,
        "composition_scope": "chart",
    }


def build_composition_subset_dataset_for_variant(
    *,
    task_variant: str,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: CompositionChartDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Construct one composition-chart dataset for the requested query variant."""

    if str(scene_variant) not in set(supported_scene_variants_for_task_variant(str(task_variant))):
        raise ValueError(f"scene_variant={scene_variant} is incompatible with task_variant={task_variant}")
    if str(task_variant) == "stack_total_at_label":
        return _build_stack_total_dataset(
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=gen_defaults,
            defaults=defaults,
            task_id=task_id,
        )
    if str(task_variant) == "stack_segment_value":
        return _build_stack_segment_dataset(
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=gen_defaults,
            defaults=defaults,
            task_id=task_id,
        )
    if str(task_variant) == "combined_share_subset":
        if str(scene_variant) not in set(PIE_LIKE_SCENE_VARIANTS):
            raise ValueError("combined_share_subset currently supports only pie/donut scenes")
        return _build_combined_share_dataset(
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=gen_defaults,
            defaults=defaults,
            task_id=task_id,
        )
    raise ValueError(f"unsupported composition task_variant: {task_variant}")


def build_stacked_composition_mark_specs(
    *,
    category_labels: Sequence[str],
    series_labels: Sequence[str],
    values_by_category: Mapping[str, Mapping[str, int]],
    mark_style: Mapping[str, Any],
):
    """Build multiseries mark specs for one stacked composition chart."""

    return build_multiseries_mark_specs(
        category_labels=category_labels,
        series_labels=series_labels,
        values_by_category=values_by_category,
        mark_style=mark_style,
    )


def resolve_stacked_chart_colors(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    defaults: CompositionChartDefaults,
    instance_seed: int,
    series_count: int,
) -> Dict[str, Any]:
    """Resolve one per-series color palette for stacked charts."""

    return resolve_multiseries_chart_colors(
        params,
        render_defaults=render_defaults,
        defaults=defaults,
        instance_seed=int(instance_seed),
        series_count=int(series_count),
    )


def projected_composition_evidence(
    *,
    scene_variant: str,
    rendered_scene,
    evidence_labels: Sequence[str],
    query_category_label: str,
) -> Dict[str, Any]:
    """Project prompt-facing composition evidence into reusable pixel-space overlays."""

    if str(scene_variant) in set(STACKED_COMPOSITION_SCENE_VARIANTS):
        requested_series = [str(label) for label in evidence_labels]
        selected_traces = [
            mark_trace
            for mark_trace in rendered_scene.mark_traces
            if str(mark_trace.get("category_label", "")) == str(query_category_label)
            and str(mark_trace.get("series_label", "")) in set(requested_series)
        ]
        ordered = sorted(selected_traces, key=lambda item: int(item["series_rank"]))
        return {
            "pixel_point_map": {
                str(mark_trace["series_label"]): list(mark_trace["mark_center_px"])
                for mark_trace in ordered
            },
            "pixel_point_set": [list(mark_trace["mark_center_px"]) for mark_trace in ordered],
            "bbox_set": [list(mark_trace["mark_bbox_px"]) for mark_trace in ordered],
        }
    return projected_mark_evidence(rendered_scene, evidence_labels)


__all__ = [
    "CompositionChartDefaults",
    "STACKED_COMPOSITION_SCENE_VARIANTS",
    "SUPPORTED_COMPOSITION_SCENE_VARIANTS",
    "SUPPORTED_COMPOSITION_TASK_VARIANTS",
    "build_composition_subset_dataset_for_variant",
    "build_stacked_composition_mark_specs",
    "projected_composition_evidence",
    "resolve_stacked_chart_colors",
    "supported_scene_variants_for_task_variant",
]
