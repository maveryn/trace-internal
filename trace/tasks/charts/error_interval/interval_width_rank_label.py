"""Public task for `task_charts__error_interval__interval_width_rank_label`."""

from __future__ import annotations

from typing import Any

from trace.core.seed import hash64
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.charts.error_interval.shared.interval_chart import (
    REFERENCE_COUNT_PROMPT_KEYS,
    RELATION_LABEL_PROMPT_KEYS,
    SCENE_ID,
    _support_probability_map,
    build_error_interval_dataset,
)
from trace.tasks.charts.error_interval.shared.prompts import build_prompt_artifacts, dynamic_slots
from trace.tasks.charts.error_interval.shared.runtime import (
    annotation_payload,
    answer_typed_value,
    build_trace_scaffold,
    render_dataset,
)
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


QUERY_IDS = RELATION_LABEL_PROMPT_KEYS
DEFAULT_QUERY_ID = "widest_interval_label"


@register_task
class ChartsErrorIntervalRelationLabelTask:
    """Identify a category by ranked interval width."""

    task_id = "task_charts__error_interval__interval_width_rank_label"
    domain = "charts"
    scene_id = SCENE_ID
    objective_contract = "interval_width_rank_label"
    supported_query_ids = QUERY_IDS
    default_dataset_enabled = True

    def _generate_once(
        self,
        instance_seed: int,
        *,
        params: dict[str, Any],
        selected_query_id: str,
        query_probabilities: dict[str, float],
    ) -> TaskOutput:
        dataset = build_error_interval_dataset(params, instance_seed=int(instance_seed), prompt_key=str(selected_query_id))
        rendered, render_meta, sidecar_meta = render_dataset(dataset, params=params, instance_seed=int(instance_seed))
        answer_gt = answer_typed_value(dataset)
        annotation_type, annotation, projected_annotation, annotation_refs = annotation_payload(dataset=dataset, rendered=rendered)
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key=str(selected_query_id),
            dynamic_slot_values=dynamic_slots(dataset),
            instance_seed=int(instance_seed),
        )
        trace_payload = build_trace_scaffold(
            dataset=dataset,
            rendered=rendered,
            render_meta=render_meta,
            sidecar_meta=sidecar_meta,
            projected_annotation=projected_annotation,
            annotation_refs=annotation_refs,
            answer_value=answer_gt.value,
        )
        relation_params = {
            "query_id": str(selected_query_id),
            "query_id_probabilities": dict(query_probabilities),
            "scene_id": SCENE_ID,
            "scene_variant": str(dataset.scene_variant),
            "scene_variant_probabilities": dict(dataset.scene_variant_probabilities),
            "category_count": int(len(dataset.items)),
            "category_count_probabilities": dict(_support_probability_map(range(6, 11))),
            "reference_value": dataset.reference_value,
            "answer_value": dataset.query.answer,
            "answer_family": "reference_count" if str(dataset.query.prompt_key) in REFERENCE_COUNT_PROMPT_KEYS else "interval_width_rank_label",
            **dict(dataset.query.params),
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
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            annotation_gt=TypedValue(type=str(annotation_type), value=annotation),
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(selected_query_id),
        )

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=self.supported_query_ids,
            default_query_id=DEFAULT_QUERY_ID,
            task_id=self.task_id,
        )
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) if attempt_index == 0 else int(hash64(int(instance_seed), self.task_id, int(attempt_index)))
            try:
                return self._generate_once(
                    int(attempt_seed),
                    params=task_params,
                    selected_query_id=str(selected_query_id),
                    query_probabilities=dict(probabilities),
                )
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}") from last_error


__all__ = ["ChartsErrorIntervalRelationLabelTask"]
