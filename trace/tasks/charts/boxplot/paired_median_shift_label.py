"""Public task for `task_charts__boxplot__paired_median_shift_label`."""

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
    PAIRED_SCENE_PROMPT_KEY,
    build_prompt_artifacts,
)
from trace.tasks.charts.boxplot.shared.rendering import (
    build_trace_scaffold,
    point_map_for_labels,
    render_paired_boxplot_panels,
    resolve_mark_style,
)
from trace.tasks.charts.shared.distribution_chart_common import build_boxplot_paired_median_shift_dataset
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


INCREASE_QUERY_ID = "paired_median_greatest_increase_label"
DECREASE_QUERY_ID = "paired_median_greatest_decrease_label"
ABSOLUTE_QUERY_ID = "paired_median_greatest_absolute_change_label"
TASK_PARAM_DEFAULTS = {
    "category_count_min": 4,
    "category_count_max": 6,
    "paired_median_shift_min": 2,
    "paired_median_shift_max": 10,
}


@register_task
class ChartsDistributionBoxplotPairedMedianShiftLabelTask:
    """Select the matched label with the requested before/after median shift."""

    task_id = "task_charts__boxplot__paired_median_shift_label"
    domain = DOMAIN
    scene_id = SCENE_ID
    objective_contract = "paired_median_shift_label"
    supported_query_ids = (INCREASE_QUERY_ID, DECREASE_QUERY_ID, ABSOLUTE_QUERY_ID)
    default_dataset_enabled = True

    def _generate_once(self, instance_seed: int, *, params: dict[str, Any], selected_query_id: str) -> TaskOutput:
        effective_params = merge_task_defaults(params, TASK_PARAM_DEFAULTS)
        mark_style = resolve_mark_style(effective_params, instance_seed=int(instance_seed), mark_count=1)
        before_boxplots, after_boxplots, answer_label, annotation_labels, trace_extras = (
            build_boxplot_paired_median_shift_dataset(
                query_id=str(selected_query_id),
                params=effective_params,
                instance_seed=int(instance_seed),
                gen_defaults=GENERATION_DEFAULTS,
                defaults=BOXPLOT_DEFAULTS,
                task_id=self.task_id,
                mark_style=mark_style,
            )
        )
        panels = dict(trace_extras.get("paired_panels", {"before": "Before", "after": "After"}))
        artifacts = render_paired_boxplot_panels(
            before_boxplots=before_boxplots,
            after_boxplots=after_boxplots,
            params=effective_params,
            mark_style=mark_style,
            before_title=str(panels.get("before", "Before")),
            after_title=str(panels.get("after", "After")),
            instance_seed=int(instance_seed),
        )
        role_to_label = {
            "before_boxplot": str(annotation_labels[0]),
            "after_boxplot": str(annotation_labels[1]),
        }
        label_to_point = point_map_for_labels(artifacts.rendered_scene, role_to_label.values())
        role_to_point = {
            str(role): label_to_point[str(label)]
            for role, label in role_to_label.items()
        }
        annotation, witness_symbolic = keyed_point_artifacts(role_to_point, role_to_label)
        prompt_artifacts = build_prompt_artifacts(
            scene_key=PAIRED_SCENE_PROMPT_KEY,
            prompt_query_key=str(selected_query_id),
            dynamic_slots={},
            instance_seed=int(instance_seed),
        )
        relations: dict[str, Any] = {
            **dict(trace_extras),
            "answer_label": str(answer_label),
            "annotation_labels": [str(label) for label in annotation_labels],
        }
        trace_payload = build_trace_scaffold(
            artifacts=artifacts,
            relations=relations,
            question_format="label_open",
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
            answer_gt=TypedValue(type="string", value=str(answer_label)),
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
            default_query_id=INCREASE_QUERY_ID,
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


__all__ = ["ChartsDistributionBoxplotPairedMedianShiftLabelTask"]
