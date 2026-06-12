"""Public task for `task_charts__density_curve__density_at_x_extremum_label`."""

from __future__ import annotations

from typing import Any

from trace.core.seed import hash64
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.charts.density_curve.shared.density_curve import (
    SCENE_ID,
    SCENE_NAMESPACE,
    build_density_curve_dataset,
    resolve_density_curve_render_params,
)
from trace.tasks.charts.density_curve.shared.prompts import build_prompt_artifacts, dynamic_slots
from trace.tasks.charts.density_curve.shared.runtime import (
    annotation_payload,
    answer_typed_value,
    build_trace_scaffold,
    render_dataset,
)
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


SUPPORTED_QUERY_IDS = ("highest_density_at_x_label", "lowest_density_at_x_label")
DEFAULT_QUERY_ID = "highest_density_at_x_label"


@register_task
class ChartsDistributionDensityCurveDensityAtXExtremumLabelTask:
    """Return the density-curve label with the highest or lowest density at a marked x-value."""

    task_id = "task_charts__density_curve__density_at_x_extremum_label"
    domain = "charts"
    scene_id = SCENE_ID
    objective_contract = "density_at_x_extremum_label"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def _generate_once(self, instance_seed: int, *, params: dict[str, Any], selected_query_id: str, max_attempts: int) -> TaskOutput:
        effective_params = dict(params)
        render_params = resolve_density_curve_render_params(effective_params, instance_seed=int(instance_seed))
        last_error: Exception | None = None
        dataset = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) if attempt_index == 0 else int(hash64(int(instance_seed), f"{SCENE_NAMESPACE}.attempt", int(attempt_index)))
            try:
                dataset = build_density_curve_dataset(
                    effective_params,
                    instance_seed=int(attempt_seed),
                    prompt_key=str(selected_query_id),
                    render_params=render_params,
                )
                break
            except ValueError as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError(f"could not generate {self.task_id} after {max_attempts} attempts") from last_error

        rendered, render_meta = render_dataset(dataset, params=effective_params, instance_seed=int(instance_seed))
        answer_gt = answer_typed_value(dataset)
        annotation_type, annotation, projected_annotation = annotation_payload(dataset=dataset, rendered=rendered)
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key=str(selected_query_id),
            dynamic_slot_values=dynamic_slots(dataset),
            instance_seed=int(instance_seed),
        )
        trace_payload = build_trace_scaffold(
            dataset=dataset,
            rendered=rendered,
            render_meta=render_meta,
            projected_annotation=projected_annotation,
            answer_label=str(answer_gt.value),
        )
        relation_params = {
            "query_id": str(selected_query_id),
            "scene_id": SCENE_ID,
            "scene_variant": str(dataset.query.trace.get("scene_variant", "density_curve")),
            "curve_count": int(dataset.curve_count),
            "interval_start": round(float(dataset.query.interval_start), 3),
            "interval_end": round(float(dataset.query.interval_end), 3),
            "reference_x": round(float(dataset.query.reference_x), 3),
            **dict(dataset.query.trace),
        }
        trace_payload["scene_ir"]["relations"]["query_id"] = str(selected_query_id)
        trace_payload["query_spec"] = build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(selected_query_id),
            params=relation_params,
        )
        trace_payload["execution_trace"]["query_id"] = str(selected_query_id)
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=TypedValue(type=str(annotation_type), value=annotation),
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            query_id=str(selected_query_id),
            scene_id=SCENE_ID,
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, _probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=self.supported_query_ids,
            default_query_id=DEFAULT_QUERY_ID,
            task_id=self.task_id,
        )
        return self._generate_once(
            int(instance_seed),
            params=task_params,
            selected_query_id=str(selected_query_id),
            max_attempts=int(max_attempts),
        )


__all__ = ["ChartsDistributionDensityCurveDensityAtXExtremumLabelTask"]
