"""Public task for `task_charts__boxplot__median_reference_label`."""

from __future__ import annotations

from typing import Any

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.charts.boxplot._lifecycle import (
    SingleBoxplotTaskPlan,
    boxplot_attempt_seed,
    materialize_single_boxplot_plan,
)
from trace.tasks.charts.boxplot.shared.defaults import DOMAIN, SCENE_ID, SCENE_NAMESPACE, merge_task_defaults
from trace.tasks.charts.boxplot.shared.prompts import SINGLE_SCENE_PROMPT_KEY, build_prompt_artifacts
from trace.tasks.charts.boxplot.shared.rendering import resolve_mark_style
from trace.tasks.charts.boxplot.shared.sampling import (
    build_boxplot_for_median,
    choose_category_count,
    quartiles_by_label,
    resolve_value_bounds,
    sample_clustered_unique,
    sample_clustered_unique_low,
    sample_labels,
    sample_unique_top_gap_margins,
    select_semantic_branch,
)
from trace.tasks.charts.shared.chart_scene import BoxPlotSpec
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import DEFAULT_QUERY_ID, select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions


TASK_ID = "task_charts__boxplot__median_reference_label"
OBJECTIVE_CONTRACT = "median_reference_label"
DIRECTION_BRANCHES = ("above_reference_q3", "below_reference_q1")


def _prompt_slots(direction: str, reference_label: str) -> dict[str, str]:
    if str(direction) == "above_reference_q3":
        return {
            "reference_label": f'"{reference_label}"',
            "median_reference_direction_word": "above",
            "reference_quartile_name": "upper quartile",
            "median_reference_gap_phrase": "between its median and the reference upper quartile",
        }
    if str(direction) == "below_reference_q1":
        return {
            "reference_label": f'"{reference_label}"',
            "median_reference_direction_word": "below",
            "reference_quartile_name": "lower quartile",
            "median_reference_gap_phrase": "between the reference lower quartile and its median",
        }
    raise ValueError(f"unsupported median reference direction: {direction}")


def _reference_side_count(
    *,
    params: dict[str, Any],
    rng: Any,
    side: str,
    candidate_count: int,
    median_min: int,
    median_max: int,
    value_min: int,
) -> int:
    """Choose how many non-reference boxes should lie on the queried side."""

    min_key = "median_reference_above_count_min" if str(side) == "above" else "median_reference_below_count_min"
    max_key = "median_reference_above_count_max" if str(side) == "above" else "median_reference_below_count_max"
    explicit_min = params.get(min_key)
    explicit_max = params.get(max_key)
    if explicit_min is None and explicit_max is None:
        count_min = max(2, int(candidate_count) // 2)
        count_max = min(int(candidate_count), int(count_min) + 1)
    else:
        count_min = max(2, int(2 if explicit_min is None else explicit_min))
        count_max = min(
            int(candidate_count),
            max(int(count_min), int(candidate_count if explicit_max is None else explicit_max)),
        )
    feasible_counts: list[int] = []
    for active_count in range(int(count_min), int(count_max) + 1):
        passive_count = int(candidate_count) - int(active_count)
        if int(passive_count) < 0:
            continue
        if str(side) == "above":
            threshold_min = max(int(value_min) + 3, int(median_min) + int(passive_count))
            threshold_max = int(median_max) - int(active_count)
        else:
            threshold_min = int(median_min) + int(active_count)
            threshold_max = int(median_max) - int(passive_count)
        if int(threshold_min) <= int(threshold_max):
            feasible_counts.append(int(active_count))
    if not feasible_counts:
        raise ValueError("no feasible reference-median side counts for requested category count")
    return int(rng.choice(feasible_counts))


def _reference_box_above(
    *,
    label: str,
    threshold: int,
    value_min: int,
    value_max: int,
    rng: Any,
    fill_rgb: tuple[int, int, int],
    outline_rgb: tuple[int, int, int],
) -> BoxPlotSpec:
    reference_q3 = int(threshold)
    reference_q1 = int(rng.randint(int(value_min) + 1, int(reference_q3) - 2))
    reference_median = int(rng.randint(int(reference_q1) + 1, int(reference_q3) - 1))
    reference_whisker_min = max(int(value_min), int(reference_q1) - int(rng.randint(0, min(2, int(reference_q1) - int(value_min)))))
    reference_whisker_max = min(int(value_max), int(reference_q3) + int(rng.randint(0, min(2, int(value_max) - int(reference_q3)))))
    return BoxPlotSpec(
        label=str(label),
        whisker_min=int(reference_whisker_min),
        q1=int(reference_q1),
        median=int(reference_median),
        q3=int(reference_q3),
        whisker_max=int(reference_whisker_max),
        fill_rgb=fill_rgb,
        outline_rgb=outline_rgb,
    )


def _reference_box_below(
    *,
    label: str,
    threshold: int,
    value_min: int,
    value_max: int,
    rng: Any,
    fill_rgb: tuple[int, int, int],
    outline_rgb: tuple[int, int, int],
) -> BoxPlotSpec:
    reference_q1 = int(threshold)
    reference_median = int(rng.randint(int(reference_q1) + 1, int(value_max) - 1))
    reference_q3 = int(rng.randint(int(reference_median) + 1, int(value_max)))
    reference_whisker_min = max(int(value_min), int(reference_q1) - int(rng.randint(0, min(2, int(reference_q1) - int(value_min)))))
    reference_whisker_max = min(int(value_max), int(reference_q3) + int(rng.randint(0, min(2, int(value_max) - int(reference_q3)))))
    return BoxPlotSpec(
        label=str(label),
        whisker_min=int(reference_whisker_min),
        q1=int(reference_q1),
        median=int(reference_median),
        q3=int(reference_q3),
        whisker_max=int(reference_whisker_max),
        fill_rgb=fill_rgb,
        outline_rgb=outline_rgb,
    )


def _build_reference_boxes(
    *,
    side: str,
    labels: tuple[str, ...],
    value_min: int,
    value_max: int,
    params: dict[str, Any],
    rng: Any,
    fill_rgb: tuple[int, int, int],
    outline_rgb: tuple[int, int, int],
) -> tuple[tuple[BoxPlotSpec, ...], str, int, dict[str, Any]]:
    """Construct reference and candidate boxes with a unique margin winner."""

    if len(labels) < 4:
        raise ValueError("boxplot reference-median task requires at least four categories")
    gap_min = max(1, int(params.get("median_reference_winner_gap_min", 1)))
    gap_max = max(int(gap_min), int(params.get("median_reference_winner_gap_max", gap_min)))
    median_min = int(value_min) + 2
    median_max = int(value_max) - 2
    candidate_count = len(labels) - 1
    active_count = _reference_side_count(
        params=params,
        rng=rng,
        side=str(side),
        candidate_count=int(candidate_count),
        median_min=int(median_min),
        median_max=int(median_max),
        value_min=int(value_min),
    )
    passive_count = int(candidate_count) - int(active_count)
    if str(side) == "above":
        threshold_min = max(int(value_min) + 3, int(median_min) + int(passive_count))
        threshold_max = int(median_max) - int(active_count)
    elif str(side) == "below":
        threshold_min = int(median_min) + int(active_count)
        threshold_max = int(median_max) - int(passive_count)
    else:
        raise ValueError(f"unsupported reference side: {side}")
    if int(threshold_min) > int(threshold_max):
        raise ValueError("boxplot reference-median support is too small for requested category count")

    threshold = int(rng.randint(int(threshold_min), int(threshold_max)))
    if str(side) == "above":
        active_support = int(median_max) - int(threshold)
        passive_medians = sample_clustered_unique_low(rng, int(median_min), int(threshold) - 1, int(passive_count))
    else:
        active_support = int(threshold) - int(median_min)
        passive_medians = sample_clustered_unique(rng, int(threshold) + 1, int(median_max), int(passive_count))
    active_margins = sample_unique_top_gap_margins(
        rng=rng,
        support_max=int(active_support),
        count=int(active_count),
        gap_min=int(gap_min),
        gap_max=int(gap_max),
    )

    shuffled_labels = list(labels)
    rng.shuffle(shuffled_labels)
    reference_label = str(shuffled_labels[0])
    candidate_labels = [str(label) for label in shuffled_labels[1:]]
    active_labels = list(candidate_labels[: int(active_count)])
    passive_labels = list(candidate_labels[int(active_count) :])
    label_to_margin = {str(label): int(margin) for label, margin in zip(active_labels, active_margins)}
    winner_margin = int(max(active_margins))
    winner_label = next(str(label) for label, margin in label_to_margin.items() if int(margin) == int(winner_margin))

    label_to_box: dict[str, BoxPlotSpec] = {}
    if str(side) == "above":
        reference_box = _reference_box_above(
            label=str(reference_label),
            threshold=int(threshold),
            value_min=int(value_min),
            value_max=int(value_max),
            rng=rng,
            fill_rgb=fill_rgb,
            outline_rgb=outline_rgb,
        )
        label_to_box[str(reference_label)] = reference_box
        for label, margin in label_to_margin.items():
            label_to_box[str(label)] = build_boxplot_for_median(
                label=str(label),
                median=int(threshold) + int(margin),
                value_min=int(value_min),
                value_max=int(value_max),
                rng=rng,
                fill_rgb=fill_rgb,
                outline_rgb=outline_rgb,
            )
        reference_meta = {"reference_q3": int(reference_box.q3)}
    else:
        reference_box = _reference_box_below(
            label=str(reference_label),
            threshold=int(threshold),
            value_min=int(value_min),
            value_max=int(value_max),
            rng=rng,
            fill_rgb=fill_rgb,
            outline_rgb=outline_rgb,
        )
        label_to_box[str(reference_label)] = reference_box
        for label, margin in label_to_margin.items():
            label_to_box[str(label)] = build_boxplot_for_median(
                label=str(label),
                median=int(threshold) - int(margin),
                value_min=int(value_min),
                value_max=int(value_max),
                rng=rng,
                fill_rgb=fill_rgb,
                outline_rgb=outline_rgb,
            )
        reference_meta = {"reference_q1": int(reference_box.q1)}

    for label, median in zip(passive_labels, passive_medians):
        label_to_box[str(label)] = build_boxplot_for_median(
            label=str(label),
            median=int(median),
            value_min=int(value_min),
            value_max=int(value_max),
            rng=rng,
            fill_rgb=fill_rgb,
            outline_rgb=outline_rgb,
        )
    ordered_boxplots = tuple(label_to_box[str(label)] for label in labels)
    return ordered_boxplots, str(winner_label), int(winner_margin), {
        "reference_label": str(reference_label),
        "winner_margin": int(winner_margin),
        "reference_side_count": int(active_count),
        "reference_other_side_count": int(passive_count),
        **reference_meta,
    }


def _build_reference_plan(params: dict[str, Any], instance_seed: int, selected_query_id: str) -> SingleBoxplotTaskPlan:
    """Bind the median-reference objective before neutral scene rendering."""

    direction, direction_probabilities, branch_params = select_semantic_branch(
        params=params,
        branch_key="median_reference_direction",
        support=DIRECTION_BRANCHES,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.reference.direction",
    )
    side = "above" if str(direction) == "above_reference_q3" else "below"
    effective_params = merge_task_defaults(branch_params, {})
    mark_style = resolve_mark_style(effective_params, instance_seed=int(instance_seed), mark_count=1)
    category_count, category_range = choose_category_count(
        params=effective_params,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.reference.category_count.{side}",
    )
    value_min, value_max = resolve_value_bounds(effective_params, instance_seed=int(instance_seed))
    labels = sample_labels(
        count=int(category_count),
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.reference.labels.{side}.{int(category_count)}",
    )
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.reference.{side}")
    fill_rgb = tuple(int(channel) for channel in mark_style["mark_fill_rgb"])
    outline_rgb = tuple(int(channel) for channel in mark_style["mark_outline_rgb"])
    boxplots, answer_label, answer_margin, reference_meta = _build_reference_boxes(
        side=str(side),
        labels=labels,
        value_min=int(value_min),
        value_max=int(value_max),
        params=effective_params,
        rng=rng,
        fill_rgb=fill_rgb,
        outline_rgb=outline_rgb,
    )
    reference_label = str(reference_meta["reference_label"])
    prompt_artifacts = build_prompt_artifacts(
        scene_key=SINGLE_SCENE_PROMPT_KEY,
        prompt_query_key=OBJECTIVE_CONTRACT,
        dynamic_slots=_prompt_slots(str(direction), reference_label),
        instance_seed=int(instance_seed),
    )
    relations = {
        "query_id": str(selected_query_id),
        "scene_variant": "boxplot",
        "category_count": int(category_count),
        "category_count_range": [int(category_range[0]), int(category_range[1])],
        "value_range": [int(value_min), int(value_max)],
        "labels": [str(spec.label) for spec in boxplots],
        "answer_label": str(answer_label),
        "annotation_value": int(answer_margin),
        "median_reference_direction": str(direction),
        "median_reference_direction_probabilities": dict(direction_probabilities),
        "quartiles_by_label": quartiles_by_label(boxplots),
        **reference_meta,
    }
    return SingleBoxplotTaskPlan(
        boxplots=boxplots,
        params=effective_params,
        mark_style=mark_style,
        answer_gt=TypedValue(type="string", value=str(answer_label)),
        answer_value=str(answer_label),
        question_format="label_open",
        role_to_label={"reference_boxplot": reference_label, "answer_boxplot": str(answer_label)},
        relations=relations,
        prompt_artifacts=prompt_artifacts,
    )


@register_task
class ChartsDistributionBoxplotMedianReferenceLabelTask:
    """Select the boxplot whose median is farthest from a reference quartile."""

    task_id = TASK_ID
    domain = DOMAIN
    objective_contract = OBJECTIVE_CONTRACT
    supported_query_ids = (DEFAULT_QUERY_ID,)
    default_dataset_enabled = True

    def _prepare_reference_plan(
        self,
        params: dict[str, Any],
        instance_seed: int,
        selected_query_id: str,
    ) -> SingleBoxplotTaskPlan:
        """Build and validate the reference-vs-answer annotation roles."""

        plan = _build_reference_plan(dict(params), int(instance_seed), str(selected_query_id))
        expected_roles = {"reference_boxplot", "answer_boxplot"}
        if set(plan.role_to_label) != expected_roles:
            raise RuntimeError("median-reference annotation roles must bind reference and answer boxplots")
        if plan.role_to_label["reference_boxplot"] == plan.role_to_label["answer_boxplot"]:
            raise RuntimeError("median-reference task must not choose the reference as the answer")
        return plan

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, _probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=self.supported_query_ids,
            default_query_id=DEFAULT_QUERY_ID,
            task_id=self.task_id,
        )
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_seed = boxplot_attempt_seed(int(instance_seed), int(attempt))
            try:
                plan = self._prepare_reference_plan(dict(task_params), int(attempt_seed), str(selected_query_id))
                materialized = materialize_single_boxplot_plan(
                    instance_seed=int(attempt_seed),
                    selected_query_id=str(selected_query_id),
                    plan=plan,
                )
                return TaskOutput(
                    prompt=materialized.prompt,
                    answer_gt=materialized.answer_gt,
                    annotation_gt=materialized.annotation_gt,
                    image=materialized.image,
                    image_id="img0",
                    trace_payload=materialized.trace_payload,
                    task_versions=default_task_versions(),
                    scene_id=SCENE_ID,
                    query_id=materialized.query_id,
                    prompt_variants=materialized.prompt_variants,
                )
            except ValueError as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")


__all__ = ["ChartsDistributionBoxplotMedianReferenceLabelTask"]
