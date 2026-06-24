"""Compute a value gap between two styled legend series at one x position."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.seed import spawn_rng
from trace.tasks.charts.style_legend._lifecycle import (
    package_style_legend_plan,
    run_style_legend_lifecycle,
)
from trace.tasks.charts.style_legend.shared.defaults import balanced_choice, gen_int, selection_index
from trace.tasks.charts.style_legend.shared.prompts import (
    ANSWER_HINT_VALUE,
    JSON_EXAMPLES,
    ANSWER_ONLY_EXAMPLES,
    POINT_SET_HINT,
)
from trace.tasks.charts.style_legend.shared.sampling import (
    base_series,
    common_setup,
    package_dataset,
    replace_series_value,
)
from trace.tasks.charts.style_legend.shared.state import DOMAIN, point_id
from trace.tasks.registry import register_task


TASK_ID = "task_charts__style_legend__pairwise_gap_value"
TASK_PARAM_DEFAULTS: dict[str, Any] = {}
PROGRAM_CODE = "abs_difference(value(series_a, x_position), value(series_b, x_position)); output=integer_value; annotation=point_set; scene=style_legend; scope=pairwise_gap_value"
PROMPT_KEY = "pairwise_gap_value"


def _build_plan(params: Mapping[str, Any], seed: int, _selected: str, probabilities: Mapping[str, float]):
    """Sample the two-series absolute-gap objective and bind its witnesses."""

    task_params = {**TASK_PARAM_DEFAULTS, **dict(params)}
    (
        x_count,
        series_count,
        labels_x,
        meta_x,
        labels_series,
        meta_series,
        palette_mode,
        palette_probs,
        legend_position,
        legend_probs,
        styles,
    ) = common_setup(task_params, instance_seed=int(seed))
    value_min = int(gen_int(task_params, "style_legend_value_min", 0))
    value_max = int(gen_int(task_params, "style_legend_value_max", 100))
    x_index = int(
        balanced_choice(
            tuple(range(1, max(2, int(x_count) - 1))),
            task_params,
            instance_seed=int(seed),
            namespace=f"{TASK_ID}.x_index",
        )
    )
    left_index = int(
        balanced_choice(
            tuple(range(int(series_count))),
            task_params,
            instance_seed=int(seed),
            namespace=f"{TASK_ID}.left_series",
        )
    )
    right_index = (int(left_index) + 1 + int(selection_index(task_params, instance_seed=int(seed), namespace=f"{TASK_ID}.right_offset")) % (int(series_count) - 1)) % int(series_count)
    gap_min = int(gen_int(task_params, "style_legend_gap_answer_min", 8))
    gap_max = max(int(gap_min), int(gen_int(task_params, "style_legend_gap_answer_max", 36)))
    gap = int(balanced_choice(tuple(range(int(gap_min), int(gap_max) + 1)), task_params, instance_seed=int(seed), namespace=f"{TASK_ID}.answer_gap"))
    rng = spawn_rng(int(seed), f"{TASK_ID}.force")
    low = int(rng.randint(max(int(value_min) + 5, 8), max(int(value_min) + 5, int(value_max) - int(gap) - 5)))
    high = int(low + gap)
    if rng.random() < 0.5:
        left_value, right_value = int(high), int(low)
    else:
        left_value, right_value = int(low), int(high)
    series = base_series(
        labels=labels_series,
        x_count=int(x_count),
        styles=styles,
        instance_seed=int(seed),
        value_min=int(value_min),
        value_max=int(value_max),
    )
    updated = list(series)
    updated[int(left_index)] = replace_series_value(updated[int(left_index)], x_index=int(x_index), value=int(left_value))
    updated[int(right_index)] = replace_series_value(updated[int(right_index)], x_index=int(x_index), value=int(right_value))
    left_series = updated[int(left_index)]
    right_series = updated[int(right_index)]
    dataset = package_dataset(
        x_labels_value=labels_x,
        x_label_meta=meta_x,
        series=updated,
        series_label_meta=meta_series,
        target_x_index=int(x_index),
        threshold_value=None,
        pair_series_ids=(str(left_series.series_id), str(right_series.series_id)),
        palette_mode=str(palette_mode),
        palette_mode_probabilities=palette_probs,
        legend_position=str(legend_position),
        legend_position_probabilities=legend_probs,
    )
    return package_style_legend_plan(
        dataset=dataset,
        params=task_params,
        answer_value=int(gap),
        answer_type="integer",
        annotation_type="point_set",
        annotation_marker_ids=(
            point_id(str(left_series.series_id), int(x_index)),
            point_id(str(right_series.series_id), int(x_index)),
        ),
        prompt_key=PROMPT_KEY,
        prompt_slots={
            "x_label": str(labels_x[int(x_index)]),
            "left_series_label": str(left_series.label),
            "right_series_label": str(right_series.label),
        },
        answer_hint=ANSWER_HINT_VALUE,
        annotation_hint=POINT_SET_HINT,
        json_example=str(JSON_EXAMPLES["gap_value"]),
        json_example_answer_only=str(ANSWER_ONLY_EXAMPLES["gap_value"]),
        program_code=PROGRAM_CODE,
        reasoning_load=0.64,
        objective_trace={
            "x_label": str(labels_x[int(x_index)]),
            "left_series_label": str(left_series.label),
            "right_series_label": str(right_series.label),
            "left_series_id": str(left_series.series_id),
            "right_series_id": str(right_series.series_id),
            "left_value": int(left_value),
            "right_value": int(right_value),
            "absolute_gap": int(gap),
            "query_id_probabilities": dict(probabilities),
        },
    )


@register_task
class ChartsStyleLegendPairwiseGapValueTask:
    """Compute a value gap between two styled legend series at one x position."""

    task_id = TASK_ID
    domain = DOMAIN
    objective_contract = "pairwise_gap_value"
    supported_query_ids = (SINGLE_QUERY_ID,)
    default_query_id = SINGLE_QUERY_ID
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int):
        return run_style_legend_lifecycle(
            task=self,
            instance_seed=int(instance_seed),
            params={**TASK_PARAM_DEFAULTS, **dict(params)},
            max_attempts=int(max_attempts),
            default_query_id=self.default_query_id,
            build_plan=_build_plan,
        )


__all__ = ["ChartsStyleLegendPairwiseGapValueTask"]
