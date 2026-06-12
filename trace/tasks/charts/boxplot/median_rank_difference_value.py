"""Public task for `task_charts__boxplot__median_rank_difference_value`."""

from __future__ import annotations

from typing import Any

from trace.core.seed import hash64
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.charts.boxplot.shared.annotations import keyed_point_artifacts
from trace.tasks.charts.boxplot.shared.defaults import (
    BOXPLOT_DEFAULTS,
    DOMAIN,
    GENERATION_DEFAULTS,
    SCENE_ID,
    merge_task_defaults,
)
from trace.tasks.charts.boxplot.shared.prompts import (
    SINGLE_SCENE_PROMPT_KEY,
    build_prompt_artifacts,
)
from trace.tasks.charts.boxplot.shared.rendering import (
    build_trace_scaffold,
    point_map_for_labels,
    render_single_boxplot_scene,
    resolve_mark_style,
)
from trace.tasks.charts.shared.distribution_chart_common import build_boxplot_median_rank_difference_dataset
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


TOP_SECOND_QUERY_ID = "median_top_second_difference_value"
TOP_THIRD_QUERY_ID = "median_top_third_difference_value"
TOP_BOTTOM_QUERY_ID = "median_top_bottom_difference_value"
TASK_PARAM_DEFAULTS = {
    "category_count_min": 6,
    "category_count_max": 12,
    "median_rank_difference_min": 2,
    "median_rank_difference_max": 18,
}


def _rank_params(selected_query_id: str, params: dict[str, Any]) -> dict[str, Any]:
    resolved = dict(params)
    resolved["median_rank_upper_rank"] = 1
    if str(selected_query_id) == TOP_SECOND_QUERY_ID:
        resolved["median_rank_lower_rank"] = 2
    elif str(selected_query_id) == TOP_THIRD_QUERY_ID:
        resolved["median_rank_lower_rank"] = 3
    elif str(selected_query_id) == TOP_BOTTOM_QUERY_ID:
        resolved["median_rank_lower_rank"] = "lowest"
    else:
        raise ValueError(f"unsupported median-rank query id: {selected_query_id}")
    return resolved


def _role_keys(selected_query_id: str) -> tuple[str, str]:
    if str(selected_query_id) == TOP_SECOND_QUERY_ID:
        return ("highest_median_boxplot", "second_highest_median_boxplot")
    if str(selected_query_id) == TOP_THIRD_QUERY_ID:
        return ("highest_median_boxplot", "third_highest_median_boxplot")
    if str(selected_query_id) == TOP_BOTTOM_QUERY_ID:
        return ("highest_median_boxplot", "lowest_median_boxplot")
    raise ValueError(f"unsupported median-rank query id: {selected_query_id}")


@register_task
class ChartsDistributionBoxplotMedianRankDifferenceValueTask:
    """Compute the difference between two ranked boxplot medians."""

    task_id = "task_charts__boxplot__median_rank_difference_value"
    domain = DOMAIN
    scene_id = SCENE_ID
    objective_contract = "median_rank_difference_value"
    supported_query_ids = (TOP_SECOND_QUERY_ID, TOP_THIRD_QUERY_ID, TOP_BOTTOM_QUERY_ID)
    default_dataset_enabled = True

    def _generate_once(self, instance_seed: int, *, params: dict[str, Any], selected_query_id: str) -> TaskOutput:
        effective_params = _rank_params(
            str(selected_query_id),
            merge_task_defaults(params, TASK_PARAM_DEFAULTS),
        )
        mark_style = resolve_mark_style(effective_params, instance_seed=int(instance_seed), mark_count=1)
        boxplots, answer_value, annotation_labels, trace_extras = build_boxplot_median_rank_difference_dataset(
            params=effective_params,
            instance_seed=int(instance_seed),
            gen_defaults=GENERATION_DEFAULTS,
            defaults=BOXPLOT_DEFAULTS,
            task_id=self.task_id,
            mark_style=mark_style,
        )
        artifacts = render_single_boxplot_scene(
            boxplots=boxplots,
            params=effective_params,
            mark_style=mark_style,
            instance_seed=int(instance_seed),
        )
        role_keys = _role_keys(str(selected_query_id))
        label_to_point = point_map_for_labels(artifacts.rendered_scene, annotation_labels)
        role_to_label = {
            str(role): str(label)
            for role, label in zip(role_keys, annotation_labels)
        }
        role_to_point = {
            str(role): label_to_point[str(label)]
            for role, label in role_to_label.items()
        }
        annotation, witness_symbolic = keyed_point_artifacts(role_to_point, role_to_label)
        prompt_artifacts = build_prompt_artifacts(
            scene_key=SINGLE_SCENE_PROMPT_KEY,
            prompt_query_key=str(selected_query_id),
            dynamic_slots={},
            instance_seed=int(instance_seed),
        )
        relations: dict[str, Any] = {
            **dict(trace_extras),
            "answer_value": int(answer_value),
            "annotation_labels": [str(label) for label in annotation_labels],
        }
        trace_payload = build_trace_scaffold(
            artifacts=artifacts,
            relations=relations,
            question_format="numeric_open",
            witness_symbolic=witness_symbolic,
            projected_annotation=annotation.projected_annotation,
        )
        trace_payload["scene_ir"]["relations"]["query_id"] = str(selected_query_id)
        trace_payload["query_spec"] = build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(selected_query_id),
            params={"query_id": str(selected_query_id), **relations},
        )
        trace_payload["execution_trace"]["query_id"] = str(selected_query_id)
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(answer_value)),
            annotation_gt=annotation.annotation_gt,
            image=artifacts.rendered_scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(selected_query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, _probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=self.supported_query_ids,
            default_query_id=TOP_THIRD_QUERY_ID,
            task_id=self.task_id,
        )
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_seed = (
                int(instance_seed)
                if attempt == 0
                else int(hash64(int(instance_seed), "charts.boxplot.retry", int(attempt)))
            )
            try:
                return self._generate_once(
                    int(attempt_seed),
                    params=task_params,
                    selected_query_id=str(selected_query_id),
                )
            except ValueError as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")


__all__ = ["ChartsDistributionBoxplotMedianRankDifferenceValueTask"]
