"""Chart counterfactual arithmetic task over labeled single-series chart scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
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
from ...shared.text_rendering import temporary_default_font_family
from ..shared.chart_scene import render_labeled_chart_scene, value_axis_render_metadata
from ..shared.complexity import build_chart_complexity, normalize_int_with_bounds, resolve_chart_complexity_weights
from ..shared.labeled_chart_common import (
    LabeledChartDefaults,
    apply_scene_variant_mark_count_cap,
    balanced_choice_from_values,
    build_chart_mark_specs,
    choose_mark_count,
    projected_mark_evidence,
    resolve_chart_axis_variant,
    resolve_chart_mark_colors,
    resolve_chart_render_params_for_task,
    resolve_mark_count_bounds,
    resolve_value_bounds,
    sample_chart_labels,
    sample_composition_with_sum,
    sorted_labels,
)
from ..shared.fixed_query_task import MergedChartQueryVariantTaskMixin
from ..shared.information_style import prepare_chart_information_scene
from ..shared.visual_defaults import (
    chart_font_asset_metadata,
    load_chart_background_defaults,
    load_chart_noise_defaults,
    sample_chart_font_family,
)


TASK_ID = "charts_hypothetical_counterfactual_value_base"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "remaining_mean_after_removal",
    "target_share_after_removal",
    "baseline_from_aggregate_percent_change",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "bar",
    "dot_plot",
    "lollipop",
)

_DEFAULTS = LabeledChartDefaults(mark_count_min=4, mark_count_max=10, value_min=5, value_max=80)
_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "hypothetical")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="hypothetical")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="hypothetical", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "remaining_mean_after_removal": 0.60,
    "target_share_after_removal": 0.78,
    "baseline_from_aggregate_percent_change": 0.72,
}
_SCENE_VARIANT_LOADS: Dict[str, float] = {
    "bar": 0.0,
    "dot_plot": 0.40,
    "lollipop": 0.52,
}


@dataclass(frozen=True)
class _CounterfactualDataset:
    labels: Tuple[str, ...]
    values: Tuple[int, ...]
    answer_value: int
    evidence_labels: Tuple[str, ...]
    trace_extras: Dict[str, Any]


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


def _uses_uniform_query_id_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> bool:
    """Return true when `_sample_cursor` is driving the default query-id cycle."""

    if params.get("query_id") is not None or params.get("query_id_weights") is not None:
        return False
    enabled = bool(params.get("balanced_query_id_sampling", group_default(_GEN_DEFAULTS, "balanced_query_id_sampling", True)))
    if not bool(enabled):
        return False
    positives = [float(value) for value in query_id_probabilities.values() if float(value) > 0.0]
    if len(positives) != len(SUPPORTED_QUERY_IDS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _support_params_for_query_id_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Use the per-variant occurrence index for balanced answer/support cycling."""

    support_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return support_params
    if not _uses_uniform_query_id_cycle(params, query_id_probabilities=query_id_probabilities):
        return support_params
    support_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_QUERY_IDS))
    return support_params


def _resolve_int_list(params: Mapping[str, Any], key: str, fallback: Sequence[int]) -> Tuple[int, ...]:
    raw = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), list(fallback)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError(f"{key} must be a sequence of integers")
    values = tuple(int(value) for value in raw)
    if not values:
        raise ValueError(f"{key} must not be empty")
    return tuple(values)


def _choose_count_param(
    params: Mapping[str, Any],
    *,
    explicit_key: str,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    max_allowed: int,
    instance_seed: int,
    namespace: str,
) -> int:
    min_count = int(params.get(str(min_key), group_default(_GEN_DEFAULTS, str(min_key), int(fallback_min))))
    max_count = int(params.get(str(max_key), group_default(_GEN_DEFAULTS, str(max_key), int(fallback_max))))
    max_count = min(int(max_count), int(max_allowed))
    candidates = [int(value) for value in range(int(min_count), int(max_count) + 1) if int(value) >= 0]
    if not candidates:
        raise ValueError(f"no feasible count support for {namespace}")
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        value = int(explicit)
        if int(value) not in set(candidates):
            raise ValueError(f"{explicit_key} outside feasible support")
        return int(value)
    return balanced_choice_from_values(candidates, params=params, instance_seed=int(instance_seed), namespace=str(namespace))


def _choose_mark_count(params: Mapping[str, Any], *, scene_variant: str, query_id: str, instance_seed: int) -> int:
    mark_count_min, mark_count_max = resolve_mark_count_bounds(
        params,
        gen_defaults=_GEN_DEFAULTS,
        defaults=_DEFAULTS,
        task_id=TASK_ID,
    )
    mark_count_min, mark_count_max = apply_scene_variant_mark_count_cap(
        scene_variant=str(scene_variant),
        mark_count_min=int(mark_count_min),
        mark_count_max=int(mark_count_max),
    )
    return choose_mark_count(
        [int(value) for value in range(int(mark_count_min), int(mark_count_max) + 1)],
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.mark_count.{query_id}",
    )


def _split_labels(
    labels: Sequence[str],
    *,
    selected_count: int,
    instance_seed: int,
    namespace: str,
) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    rng = spawn_rng(int(instance_seed), str(namespace))
    shuffled = [str(label) for label in labels]
    rng.shuffle(shuffled)
    selected = tuple(str(label) for label in shuffled[: int(selected_count)])
    remaining = tuple(str(label) for label in shuffled[int(selected_count) :])
    return tuple(selected), tuple(remaining)


def _compose_values_with_sum(
    *,
    total: int,
    count: int,
    value_min: int,
    value_max: int,
    instance_seed: int,
    namespace: str,
) -> List[int]:
    if int(count) <= 0:
        raise ValueError("count must be positive")
    if int(total) < int(count) * int(value_min) or int(total) > int(count) * int(value_max):
        raise ValueError("total outside feasible value bounds")
    rng = spawn_rng(int(instance_seed), str(namespace))
    values = sample_composition_with_sum(
        rng,
        target_sum=int(total),
        count=int(count),
        value_min=int(value_min),
        value_max=int(value_max),
    )
    rng.shuffle(values)
    return [int(value) for value in values]


def _random_values(
    *,
    count: int,
    value_min: int,
    value_max: int,
    instance_seed: int,
    namespace: str,
) -> List[int]:
    rng = spawn_rng(int(instance_seed), str(namespace))
    return [int(rng.randint(int(value_min), int(value_max))) for _ in range(int(count))]


def _values_from_label_map(labels: Sequence[str], values_by_label: Mapping[str, int]) -> Tuple[int, ...]:
    return tuple(int(values_by_label[str(label)]) for label in labels)


def _format_labels(labels: Sequence[str]) -> str:
    ordered = [f'"{str(label)}"' for label in labels]
    if not ordered:
        return ""
    if len(ordered) == 1:
        return str(ordered[0])
    if len(ordered) == 2:
        return f"{ordered[0]} and {ordered[1]}"
    return f"{', '.join(ordered[:-1])}, and {ordered[-1]}"


def _build_remaining_mean_after_removal(
    *,
    labels: Sequence[str],
    params: Mapping[str, Any],
    instance_seed: int,
    value_min: int,
    value_max: int,
) -> _CounterfactualDataset:
    mark_count = len(labels)
    removed_count = _choose_count_param(
        params,
        explicit_key="removed_count",
        min_key="removed_count_min",
        max_key="removed_count_max",
        fallback_min=1,
        fallback_max=3,
        max_allowed=int(mark_count) - 3,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.removed_count.remaining_mean",
    )
    removed_labels, retained_labels = _split_labels(
        labels,
        selected_count=int(removed_count),
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.labels.remaining_mean",
    )
    retained_count = len(retained_labels)
    answer_min = int(params.get("target_answer_min", group_default(_GEN_DEFAULTS, "target_answer_min", 15)))
    answer_max = int(params.get("target_answer_max", group_default(_GEN_DEFAULTS, "target_answer_max", 65)))
    candidates = [
        int(value)
        for value in range(max(int(value_min), int(answer_min)), min(int(value_max), int(answer_max)) + 1)
        if int(value) * int(retained_count) >= int(retained_count) * int(value_min)
        and int(value) * int(retained_count) <= int(retained_count) * int(value_max)
    ]
    answer_value = balanced_choice_from_values(
        candidates,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.answer.remaining_mean",
    )
    retained_values = _compose_values_with_sum(
        total=int(answer_value) * int(retained_count),
        count=int(retained_count),
        value_min=int(value_min),
        value_max=int(value_max),
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.values.remaining_mean.retained",
    )
    removed_values = _random_values(
        count=int(removed_count),
        value_min=int(value_min),
        value_max=int(value_max),
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.values.remaining_mean.removed",
    )
    values_by_label = {
        **{str(label): int(value) for label, value in zip(retained_labels, retained_values)},
        **{str(label): int(value) for label, value in zip(removed_labels, removed_values)},
    }
    return _CounterfactualDataset(
        labels=tuple(labels),
        values=_values_from_label_map(labels, values_by_label),
        answer_value=int(answer_value),
        evidence_labels=tuple(sorted_labels(retained_labels)),
        trace_extras={
            "removed_labels": list(sorted_labels(removed_labels)),
            "retained_labels": list(sorted_labels(retained_labels)),
            "removed_count": int(removed_count),
            "retained_count": int(retained_count),
            "retained_sum": int(sum(retained_values)),
            "counterfactual_operation": "remove_labels_then_mean",
        },
    )


def _build_target_share_after_removal(
    *,
    labels: Sequence[str],
    params: Mapping[str, Any],
    instance_seed: int,
    value_min: int,
    value_max: int,
) -> _CounterfactualDataset:
    mark_count = len(labels)
    removed_count = _choose_count_param(
        params,
        explicit_key="removed_count",
        min_key="removed_count_min",
        max_key="removed_count_max",
        fallback_min=1,
        fallback_max=3,
        max_allowed=int(mark_count) - 3,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.removed_count.target_share",
    )
    removed_labels, retained_labels = _split_labels(
        labels,
        selected_count=int(removed_count),
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.labels.target_share",
    )
    target_pool = [label for label in retained_labels]
    target_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.target_label.target_share",
    )
    target_label = str(target_pool[int(target_index) % len(target_pool)])
    other_retained = [str(label) for label in retained_labels if str(label) != str(target_label)]
    share_options = _resolve_int_list(params, "share_percent_values", (10, 15, 20, 25, 30, 40, 50, 60))
    feasible: List[Tuple[int, int, int, int]] = []
    for percent in share_options:
        for target_value in range(int(value_min), int(value_max) + 1):
            if int(target_value) * 100 % int(percent) != 0:
                continue
            remaining_total = int(target_value) * 100 // int(percent)
            other_sum = int(remaining_total) - int(target_value)
            if int(other_sum) >= len(other_retained) * int(value_min) and int(other_sum) <= len(other_retained) * int(value_max):
                feasible.append((int(percent), int(target_value), int(remaining_total), int(other_sum)))
    if not feasible:
        raise ValueError("no feasible target-share support")
    share_support = sorted(set(item[0] for item in feasible))
    answer_value = balanced_choice_from_values(
        share_support,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.answer.target_share",
    )
    choices = [item for item in feasible if int(item[0]) == int(answer_value)]
    choice_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.target_share.choice.{answer_value}",
    )
    _, target_value, remaining_total, other_sum = choices[int(choice_index) % len(choices)]
    other_values = _compose_values_with_sum(
        total=int(other_sum),
        count=len(other_retained),
        value_min=int(value_min),
        value_max=int(value_max),
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.values.target_share.retained_other",
    )
    removed_values = _random_values(
        count=int(removed_count),
        value_min=int(value_min),
        value_max=int(value_max),
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.values.target_share.removed",
    )
    values_by_label = {
        str(target_label): int(target_value),
        **{str(label): int(value) for label, value in zip(other_retained, other_values)},
        **{str(label): int(value) for label, value in zip(removed_labels, removed_values)},
    }
    return _CounterfactualDataset(
        labels=tuple(labels),
        values=_values_from_label_map(labels, values_by_label),
        answer_value=int(answer_value),
        evidence_labels=tuple(sorted_labels(retained_labels)),
        trace_extras={
            "removed_labels": list(sorted_labels(removed_labels)),
            "retained_labels": list(sorted_labels(retained_labels)),
            "target_label": str(target_label),
            "target_value": int(target_value),
            "remaining_total": int(remaining_total),
            "percent_value": int(answer_value),
            "counterfactual_operation": "remove_labels_then_target_share_percent",
        },
    )


def _build_baseline_from_aggregate_percent_change(
    *,
    labels: Sequence[str],
    params: Mapping[str, Any],
    instance_seed: int,
    value_min: int,
    value_max: int,
) -> _CounterfactualDataset:
    mark_count = len(labels)
    aggregate_count = _choose_count_param(
        params,
        explicit_key="aggregate_count",
        min_key="aggregate_count_min",
        max_key="aggregate_count_max",
        fallback_min=2,
        fallback_max=4,
        max_allowed=int(mark_count) - 1,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.aggregate_count.baseline",
    )
    aggregate_labels, other_labels = _split_labels(
        labels,
        selected_count=int(aggregate_count),
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.labels.baseline",
    )
    percent_options = _resolve_int_list(params, "baseline_percent_values", (25, 50, 75, 100))
    feasible: List[Tuple[int, int, int]] = []
    for percent in percent_options:
        for baseline in range(int(value_min), int(value_max) * int(aggregate_count) + 1):
            aggregate_sum_numerator = int(baseline) * (100 + int(percent))
            if aggregate_sum_numerator % 100 != 0:
                continue
            aggregate_sum = int(aggregate_sum_numerator // 100)
            if int(aggregate_sum) >= int(aggregate_count) * int(value_min) and int(aggregate_sum) <= int(aggregate_count) * int(value_max):
                feasible.append((int(percent), int(baseline), int(aggregate_sum)))
    if not feasible:
        raise ValueError("no feasible aggregate baseline support")
    baseline_support = sorted(set(item[1] for item in feasible))
    answer_value = balanced_choice_from_values(
        baseline_support,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.answer.baseline",
    )
    choices = [item for item in feasible if int(item[1]) == int(answer_value)]
    choice_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.baseline.choice.{answer_value}",
    )
    percent_value, _, aggregate_sum = choices[int(choice_index) % len(choices)]
    aggregate_values = _compose_values_with_sum(
        total=int(aggregate_sum),
        count=int(aggregate_count),
        value_min=int(value_min),
        value_max=int(value_max),
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.values.baseline.aggregate",
    )
    other_values = _random_values(
        count=len(other_labels),
        value_min=int(value_min),
        value_max=int(value_max),
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.values.baseline.other",
    )
    values_by_label = {
        **{str(label): int(value) for label, value in zip(aggregate_labels, aggregate_values)},
        **{str(label): int(value) for label, value in zip(other_labels, other_values)},
    }
    return _CounterfactualDataset(
        labels=tuple(labels),
        values=_values_from_label_map(labels, values_by_label),
        answer_value=int(answer_value),
        evidence_labels=tuple(sorted_labels(aggregate_labels)),
        trace_extras={
            "aggregate_labels": list(sorted_labels(aggregate_labels)),
            "aggregate_count": int(aggregate_count),
            "aggregate_sum": int(aggregate_sum),
            "percent_value": int(percent_value),
            "counterfactual_operation": "aggregate_percent_higher_than_baseline",
        },
    )


def _build_counterfactual_dataset(
    *,
    query_id: str,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _CounterfactualDataset:
    value_min, value_max = resolve_value_bounds(
        params,
        gen_defaults=_GEN_DEFAULTS,
        defaults=_DEFAULTS,
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
    )
    mark_count = _choose_mark_count(
        params,
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        instance_seed=int(instance_seed),
    )
    labels = tuple(
        sample_chart_labels(
            count=int(mark_count),
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.labels:{str(query_id)}:{int(mark_count)}",
        )
    )
    builders = {
        "remaining_mean_after_removal": _build_remaining_mean_after_removal,
        "target_share_after_removal": _build_target_share_after_removal,
        "baseline_from_aggregate_percent_change": _build_baseline_from_aggregate_percent_change,
    }
    dataset = builders[str(query_id)](
        labels=labels,
        params=params,
        instance_seed=int(instance_seed),
        value_min=int(value_min),
        value_max=int(value_max),
    )
    return _CounterfactualDataset(
        labels=tuple(dataset.labels),
        values=tuple(int(value) for value in dataset.values),
        answer_value=int(dataset.answer_value),
        evidence_labels=tuple(sorted_labels(dataset.evidence_labels)),
        trace_extras={
            "value_min": int(value_min),
            "value_max": int(value_max),
            "mark_count": int(mark_count),
            "mark_count_range": [
                int(resolve_mark_count_bounds(params, gen_defaults=_GEN_DEFAULTS, defaults=_DEFAULTS, task_id=TASK_ID)[0]),
                int(resolve_mark_count_bounds(params, gen_defaults=_GEN_DEFAULTS, defaults=_DEFAULTS, task_id=TASK_ID)[1]),
            ],
            "labels": [str(label) for label in dataset.labels],
            "values_by_label": {str(label): int(value) for label, value in zip(dataset.labels, dataset.values)},
            **dict(dataset.trace_extras),
        },
    )


class ChartsHypotheticalCounterfactualValueTask:
    """Return an integer value after a chart-grounded counterfactual operation."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "hypothetical"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        support_params = _support_params_for_query_id_cycle(
            params,
            query_id_probabilities=query_id_probabilities,
        )
        dataset = _build_counterfactual_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            params=support_params,
            instance_seed=int(instance_seed),
        )
        mark_style = resolve_chart_mark_colors(
            params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
            scene_variant=str(scene_variant),
            mark_count=len(dataset.labels),
        )
        marks = build_chart_mark_specs(
            labels=dataset.labels,
            values=dataset.values,
            scene_variant=str(scene_variant),
            mark_style=mark_style,
        )
        render_params = resolve_chart_render_params_for_task(
            {**dict(params), **mark_style},
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )

        render_params, background, background_meta, information_style_meta = prepare_chart_information_scene(
            instance_seed=int(instance_seed),
            params=params,
            scene_id="single_series",
            task_group=self.task_group,
            render_params=render_params,
        )
        chart_font_family = sample_chart_font_family(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.chart_font",
            params=params,
        )
        with temporary_default_font_family(str(chart_font_family)):
            rendered_scene = render_labeled_chart_scene(
                background,
                scene_variant=str(scene_variant),
                marks=marks,
                render_params=render_params,
                instance_seed=int(instance_seed),
            )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
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
            )
            + tuple(f"object_description_{scene_variant}" for scene_variant in SUPPORTED_SCENE_VARIANTS)
            + tuple(f"evidence_hint_{query_id}" for query_id in SUPPORTED_QUERY_IDS)
            + tuple(f"json_example_{query_id}" for query_id in SUPPORTED_QUERY_IDS)
            + tuple(f"json_example_answer_only_{query_id}" for query_id in SUPPORTED_QUERY_IDS),
            context=f"prompt defaults for {self.task_id}",
        )
        extras = dict(dataset.trace_extras)
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        evidence_hint = str(prompt_defaults[f"evidence_hint_{str(query_id)}"])
        json_example = str(prompt_defaults[f"json_example_{str(query_id)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(query_id)}"])

        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "removed_labels_text": _format_labels(extras.get("removed_labels", [])),
                "retained_labels_text": _format_labels(extras.get("retained_labels", [])),
                "target_label": str(extras.get("target_label", "")),
                "aggregate_labels_text": _format_labels(extras.get("aggregate_labels", [])),
                "percent_value": str(extras.get("percent_value", "")),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(evidence_hint),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(dataset.answer_value))
        label_centers = {str(mark["label"]): list(mark["label_center_px"]) for mark in rendered_scene.mark_traces}
        values_by_label = {str(label): int(value) for label, value in zip(dataset.labels, dataset.values)}
        evidence_projection = projected_mark_evidence(rendered_scene, dataset.evidence_labels)
        evidence_points = [list(point) for point in evidence_projection["pixel_point_set"]]
        evidence_gt = TypedValue(type="point_set", value=evidence_points)

        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": f"chart_{str(scene_variant)}_hypothetical_counterfactual",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "evidence_labels": list(dataset.evidence_labels),
                    "counterfactual_operation": str(extras["counterfactual_operation"]),
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
                    "mark_count": int(extras["mark_count"]),
                    **{
                        str(key): value
                        for key, value in extras.items()
                        if str(key)
                        in {
                            "removed_labels",
                            "retained_labels",
                            "target_label",
                            "aggregate_labels",
                            "percent_value",
                        }
                    },
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "information_scene_style": dict(information_style_meta),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "layout_jitter": dict(render_params.layout_jitter_meta or {}),
                "text_style": {
                    "label_font_size_px": int(render_params.label_font_size_px),
                    "tick_font_size_px": int(render_params.tick_font_size_px),
                    "label_stroke_width_px": int(render_params.label_stroke_width_px),
                },
                "axis_style": {
                    "axis_line_width_px": int(render_params.axis_line_width_px),
                    "grid_line_width_px": int(render_params.grid_line_width_px),
                    "tick_length_px": int(render_params.tick_length_px),
                },
                "font_assets": chart_font_asset_metadata(str(chart_font_family)),
                "mark_style": {
                    "sampling_policy": str(mark_style["sampling_policy"]),
                    "mark_fill_rgb": list(mark_style["mark_fill_rgb"]),
                    "mark_outline_rgb": list(mark_style["mark_outline_rgb"]),
                    **{
                        str(key): value
                        for key, value in mark_style.items()
                        if key not in {"sampling_policy", "mark_fill_rgb", "mark_outline_rgb"}
                    },
                },
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "y_axis_max": int(rendered_scene.y_axis_max),
                "y_ticks": [int(value) for value in rendered_scene.y_ticks],
                **value_axis_render_metadata(rendered_scene),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "label_centers_px": dict(label_centers),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "answer_value": int(dataset.answer_value),
                "evidence_labels": list(dataset.evidence_labels),
                "labels": [str(label) for label in dataset.labels],
                "values": [int(value) for value in dataset.values],
                "values_by_label": dict(values_by_label),
                "query_id_probabilities": dict(query_id_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "question_format": "numeric_open",
                "mark_color_sampling_policy": str(mark_style["sampling_policy"]),
                "mark_fill_rgb": list(mark_style["mark_fill_rgb"]),
                "mark_outline_rgb": list(mark_style["mark_outline_rgb"]),
                **{
                    str(key): value
                    for key, value in mark_style.items()
                    if key not in {"sampling_policy", "mark_fill_rgb", "mark_outline_rgb"}
                },
                **dict(extras),
            },
            "witness_symbolic": {
                "type": "counterfactual_chart_calculation",
                "query_id": str(query_id),
                "answer_value": int(dataset.answer_value),
                "evidence_labels": list(dataset.evidence_labels),
                "calculation": dict(extras),
            },
            "projected_evidence": {
                "type": "point_set",
                "point_set": list(evidence_points),
                **dict(evidence_projection),
            },
        }

        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(extras["mark_count"]), extras["mark_count_range"]),
                "reasoning_load": float(_REASONING_LOAD_BY_VARIANT[str(query_id)]),
                "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(scene_variant)]),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id="single_series",
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class ChartsHypotheticalCounterfactualValuePublicTask(
    MergedChartQueryVariantTaskMixin,
    ChartsHypotheticalCounterfactualValueTask,
):
    """Compute one sampled counterfactual value from a labeled chart."""

    task_id = "task_charts__single_series__counterfactual_value"
    allowed_query_ids = SUPPORTED_QUERY_IDS


__all__ = [
    "ChartsHypotheticalCounterfactualValueTask",
    "ChartsHypotheticalCounterfactualValuePublicTask",
]
