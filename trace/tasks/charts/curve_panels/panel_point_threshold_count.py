"""Public task for `task_charts__curve_panels__panel_point_threshold_count`."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.base import TaskOutput
from trace.tasks.charts.curve_panels._lifecycle import (
    CurvePanelTaskPlan,
    build_curve_panel_plan_from_query,
    build_curve_panel_query_record,
    run_curve_panel_task_lifecycle,
)
from trace.tasks.charts.curve_panels.shared.defaults import (
    SCENE_NAMESPACE,
)
from trace.tasks.registry import register_task
from trace.tasks.charts.curve_panels.shared.sampling import (
    balanced_choice,
    generation_int,
    point_id,
    side_value,
    threshold_panel_context,
)

ABOVE_QUERY_ID = "panel_point_above_threshold_count"
BELOW_QUERY_ID = "panel_point_below_threshold_count"
QUERY_DIRECTIONS = {ABOVE_QUERY_ID: "above", BELOW_QUERY_ID: "below"}
TASK_PARAM_DEFAULTS: dict[str, Any] = {
    "panel_count_min": 4,
    "panel_count_max": 6,
    "method_count_min": 3,
    "method_count_max": 4,
    "x_tick_count_min": 5,
    "x_tick_count_max": 7,
    "point_threshold_target_count_min": 3,
    "point_threshold_target_count_max": 12,
}


def _force_point_threshold_partition(
    *,
    method_labels: tuple[str, ...],
    x_values: tuple[int, ...],
    target_count: int,
    direction: str,
    values: dict[str, dict[str, list[int]]],
    query_panel: str,
    threshold: int,
    y_min: int,
    y_max: int,
    rng: Any,
) -> tuple[set[tuple[str, int]], tuple[str, ...]]:
    """Choose matching plotted points and force all marks to the requested side."""

    slots = [
        (str(method), int(x_index))
        for method in method_labels
        for x_index in range(len(x_values))
    ]
    rng.shuffle(slots)
    matching_slots = set(slots[: int(target_count)])
    matching_side = "above" if str(direction) == "above" else "below"
    nonmatching_side = "below" if str(direction) == "above" else "above"
    for method in method_labels:
        for x_index, _x_value in enumerate(x_values):
            side = (
                matching_side
                if (str(method), int(x_index)) in matching_slots
                else nonmatching_side
            )
            values[str(query_panel)][str(method)][int(x_index)] = side_value(
                rng=rng,
                threshold=int(threshold),
                side=str(side),
                y_min=int(y_min),
                y_max=int(y_max),
            )
    annotation_ids = tuple(
        point_id(str(query_panel), str(method), int(x_values[int(x_index)]))
        for method, x_index in slots[: int(target_count)]
    )
    return matching_slots, annotation_ids


@register_task
class ChartsScientificPanelPointThresholdCountTask:
    """Count all plotted markers in one panel satisfying a one-bound threshold."""

    task_id = "task_charts__curve_panels__panel_point_threshold_count"
    domain = "charts"
    objective_contract = "panel_point_threshold_count"
    supported_query_ids = (ABOVE_QUERY_ID, BELOW_QUERY_ID)
    default_dataset_enabled = True

    def _build_panel_point_threshold_plan(
        self, instance_seed: int, params: Mapping[str, Any], selected_query_id: str
    ) -> CurvePanelTaskPlan:
        """Build the task-owned semantic sample before shared rendering."""

        effective_params = {**TASK_PARAM_DEFAULTS, **dict(params)}
        try:
            direction = QUERY_DIRECTIONS[str(selected_query_id)]
        except KeyError as exc:
            raise ValueError(
                f"unsupported curve-panel point-threshold query: {selected_query_id}"
            ) from exc
        (
            sampled_x_values,
            y_min,
            y_max,
            panel_labels,
            method_labels,
            panel_label_meta,
            colors,
            rng,
            query_panel,
            threshold,
            values,
            _non_answer_params,
        ) = threshold_panel_context(
            effective_params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.panel_point_threshold_count",
        )
        total_slots = int(len(method_labels)) * int(len(sampled_x_values))
        target_min = max(
            1,
            int(
                generation_int(effective_params, "point_threshold_target_count_min", 3)
            ),
        )
        target_max = min(
            int(total_slots) - 1,
            int(
                generation_int(effective_params, "point_threshold_target_count_max", 12)
            ),
        )
        if int(target_min) > int(target_max):
            target_min = max(1, min(int(total_slots), int(target_max)))
        target_count = int(
            balanced_choice(
                list(range(int(target_min), int(target_max) + 1)),
                effective_params,
                instance_seed=int(instance_seed),
                namespace=f"{SCENE_NAMESPACE}.panel_point_threshold_count.answer",
            )
        )
        _matching_slots, annotation_ids = _force_point_threshold_partition(
            method_labels=tuple(method_labels),
            x_values=tuple(sampled_x_values),
            target_count=int(target_count),
            direction=str(direction),
            values=values,
            query_panel=str(query_panel),
            threshold=int(threshold),
            y_min=int(y_min),
            y_max=int(y_max),
            rng=rng,
        )
        phrase = "above" if str(direction) == "above" else "below"
        query = build_curve_panel_query_record(
            prompt_key=selected_query_id,
            answer=target_count,
            answer_type="integer",
            panel_label=query_panel,
            threshold_value=threshold,
            threshold_direction=direction,
            threshold_panel_labels=(query_panel,),
            annotation_panel_labels=(query_panel,),
            annotation_point_ids=annotation_ids,
            trace={
                "query_panel_label": str(query_panel),
                "threshold_value": int(threshold),
                "threshold_direction": str(direction),
                "threshold_direction_phrase": str(phrase),
                "matching_point_ids": list(annotation_ids),
                "values_in_query_panel": {
                    str(method): [
                        int(value) for value in values[str(query_panel)][str(method)]
                    ]
                    for method in method_labels
                },
                **dict(panel_label_meta),
            },
        )
        return build_curve_panel_plan_from_query(
            x_values=tuple(sampled_x_values),
            y_min=int(y_min),
            y_max=int(y_max),
            panel_labels=tuple(panel_labels),
            method_labels=tuple(method_labels),
            colors=tuple(colors),
            values_by_panel_method=values,
            query=query,
            dynamic_slots={
                "panel_label": f'"{query.panel_label}"',
                "threshold_value": str(query.threshold_value),
                "threshold_direction_phrase": str(phrase),
            },
            instance_seed=int(instance_seed),
        )

    def generate(
        self, instance_seed: int, *, params: dict[str, Any], max_attempts: int
    ) -> TaskOutput:
        """Select the local query, then run neutral curve-panel lifecycle."""

        return run_curve_panel_task_lifecycle(
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            supported_query_ids=self.supported_query_ids,
            default_query_id=ABOVE_QUERY_ID,
            failure_label=self.task_id,
            build_plan=self._build_panel_point_threshold_plan,
        )


__all__ = ["ChartsScientificPanelPointThresholdCountTask"]
