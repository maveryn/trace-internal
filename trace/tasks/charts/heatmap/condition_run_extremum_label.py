"""Public task for `task_charts__heatmap__condition_run_extremum_label`."""

from __future__ import annotations

from typing import Any

from trace.core.seed import hash64
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.charts.heatmap.shared.grid_common import SCENE_ID, _condition_support, _is_continuous_colorbar_prompt_key
from trace.tasks.charts.heatmap.shared.grid_dataset import construct_heatmap_dataset
from trace.tasks.charts.heatmap.shared.grid_sampling import (
    _decoupled_sampling_params,
    _resolve_condition_kind,
    _resolve_scene_variant,
)
from trace.tasks.charts.heatmap.shared.prompts import build_prompt_artifacts, dynamic_slots
from trace.tasks.charts.heatmap.shared.runtime import (
    annotation_payload,
    answer_typed_value,
    build_trace_scaffold,
    render_dataset,
)
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec


QUERY_IDS = ("condition_run_extremum_label",)
DEFAULT_QUERY_ID = "condition_run_extremum_label"


@register_task
class ChartsHeatmapConditionRunExtremumLabelTask:
    """Return the row label with the longest consecutive run satisfying a color condition."""

    task_id = "task_charts__heatmap__condition_run_extremum_label"
    domain = "charts"
    scene_id = SCENE_ID
    objective_contract = "condition_run_extremum_label"
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
        requested_scene = params.get("scene_variant")
        if _is_continuous_colorbar_prompt_key(str(selected_query_id)) or str(requested_scene) == "continuous_colorbar_heatmap":
            raise ValueError("condition-run heatmap tasks do not support continuous_colorbar_heatmap")
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        condition_params = _decoupled_sampling_params(
            params,
            divisor=2,
            explicit_keys=("condition_kind", "condition_kind_weights"),
        )
        condition_kind, condition_probabilities = _resolve_condition_kind(
            condition_params,
            scene_variant=str(scene_variant),
            instance_seed=int(instance_seed),
        )
        dataset = construct_heatmap_dataset(
            prompt_key=str(selected_query_id),
            scene_variant=str(scene_variant),
            query_axis="row",
            condition_kind=str(condition_kind),
            extremum_direction="hottest",
            params={**dict(params), "_enable_unanswerable": False},
            instance_seed=int(instance_seed),
        )
        rendered, render_meta, background_meta, post_noise_meta = render_dataset(
            dataset,
            params=params,
            instance_seed=int(instance_seed),
        )
        answer_gt = answer_typed_value(dataset)
        annotation_type, annotation, projected_annotation = annotation_payload(dataset=dataset, rendered=rendered)
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key=str(selected_query_id),
            dynamic_slot_values=dynamic_slots(dataset, supports_unanswerable=False),
            instance_seed=int(instance_seed),
        )
        trace_payload = build_trace_scaffold(
            dataset=dataset,
            rendered=rendered,
            render_meta=render_meta,
            background_meta=background_meta,
            post_noise_meta=post_noise_meta,
            projected_annotation=projected_annotation,
            annotation_value=annotation,
            answer_value=answer_gt.value,
        )
        relation_params = {
            "query_id": str(selected_query_id),
            "query_id_probabilities": dict(query_probabilities),
            "scene_id": SCENE_ID,
            "scene_variant": str(dataset["scene_variant"]),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "row_count": int(dataset["row_count"]),
            "column_count": int(dataset["column_count"]),
            "row_count_probabilities": dict(dataset["row_count_probabilities"]),
            "column_count_probabilities": dict(dataset["column_count_probabilities"]),
            "heat_bin_count": int(dataset["heat_bin_count"]),
            "query_axis": str(dataset["query_axis"]),
            "condition_kind_probabilities": dict(condition_probabilities),
            "condition_support": list(_condition_support(str(dataset["scene_variant"]))),
            **dict(dataset["question_params"]),
        }
        trace_payload["scene_ir"]["relations"]["query_id"] = str(selected_query_id)
        trace_payload["query_spec"] = build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(selected_query_id),
            params=relation_params,
        )
        trace_payload["execution_trace"]["query_id"] = str(selected_query_id)
        trace_payload["execution_trace"]["query_id_probabilities"] = dict(query_probabilities)
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=TypedValue(type=str(annotation_type), value=annotation),
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(selected_query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
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


__all__ = ["ChartsHeatmapConditionRunExtremumLabelTask"]
