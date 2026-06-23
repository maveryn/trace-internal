"""Return the panel label with highest local point density in a requested quadrant."""

from __future__ import annotations

from typing import Any

from ....core.seed import hash64
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.fixed_query import select_task_query_id
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PromptTraceArtifacts, build_prompt_query_spec
from .shared.annotations import density_region_bbox_annotation
from .shared.output import base_execution_record, render_map, render_spec
from .shared.prompts import build_prompt_artifacts, dynamic_slots
from .shared.rendering import render_scatter_facet_dataset
from .shared.sampling import build_dataset
from .shared.state import DOMAIN, SCENE_ID


QUERY_IDS = (
    "upper_right_density_extremum_label",
    "upper_left_density_extremum_label",
    "lower_right_density_extremum_label",
    "lower_left_density_extremum_label",
)
QUERY_REGION_BY_ID = {
    "upper_right_density_extremum_label": "upper_right",
    "upper_left_density_extremum_label": "upper_left",
    "lower_right_density_extremum_label": "lower_right",
    "lower_left_density_extremum_label": "lower_left",
}
REASONING_LOAD_BY_QUERY = {
    "upper_right_density_extremum_label": 0.72,
    "upper_left_density_extremum_label": 0.72,
    "lower_right_density_extremum_label": 0.72,
    "lower_left_density_extremum_label": 0.72,
}
TASK_PARAM_DEFAULTS: dict[str, Any] = {}
TASK_ID = "task_charts__scatter_facet_grid__region_density_extremum_label"
QUESTION_FORMAT = "scatter_facet_grid_query"


def _trace_payload(
    *,
    dataset: Any,
    rendered: Any,
    prompt_artifacts: PromptTraceArtifacts,
    selected_query_id: str,
    query_probabilities: dict[str, float],
    annotation: Any,
    witness_symbolic: dict[str, Any],
) -> dict[str, Any]:
    """Assemble task-owned verifier records after semantic answer binding."""

    execution = {
        **base_execution_record(dataset),
        "query_id": str(selected_query_id),
        "query_id_probabilities": dict(query_probabilities),
        "question_format": QUESTION_FORMAT,
        "annotation_type": str(annotation.annotation_type),
        "reasoning_load": float(REASONING_LOAD_BY_QUERY[str(selected_query_id)]),
    }
    spec = render_spec(rendered)
    spec.update(
        {
            "scene_variant": "facet_grid",
            "layout_id": str(dataset.layout_id),
            "rows": int(dataset.rows),
            "cols": int(dataset.cols),
            "panel_count": int(len(dataset.panels)),
        }
    )
    query_params = {
        "query_id": str(selected_query_id),
        "query_id_probabilities": dict(query_probabilities),
        "scene_variant": "facet_grid",
        "program_code": "argmax_label(panel, local_point_density(panel, target_region))",
        "target_region": str(dataset.query.target_region),
        "target_region_phrase": str(dataset.query.trace["target_region_phrase"]),
        **dict(dataset.query.trace),
    }
    rendered_scene = rendered.rendered_scene
    return {
        "scene_ir": {
            "scene_kind": "chart_scatter_facet_grid",
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": {
                "query_id": str(selected_query_id),
                "target_region": str(dataset.query.target_region),
                "answer": str(dataset.query.answer_label),
                "annotation_type": str(annotation.annotation_type),
                "panel_count": int(len(dataset.panels)),
            },
        },
        "query_spec": build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(selected_query_id),
            params=query_params,
        ),
        "render_spec": dict(spec),
        "render_map": render_map(rendered),
        "execution_trace": dict(execution),
        "witness_symbolic": {
            **dict(witness_symbolic),
            "answer": str(dataset.query.answer_label),
            "annotation_type": str(annotation.annotation_type),
        },
        "projected_annotation": dict(annotation.projected_annotation),
        "background": dict(rendered.background_meta),
        "post_image_noise": dict(rendered.post_noise_meta),
    }


@register_task
class ChartsScatterFacetGridRegionDensityExtremumLabelTask:
    """Return the panel label with highest local point density in a requested quadrant."""

    task_id = TASK_ID
    domain = DOMAIN
    objective_contract = "region_density_extremum_label"
    supported_query_ids = QUERY_IDS
    default_query_id = QUERY_IDS[0]
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params={**TASK_PARAM_DEFAULTS, **dict(params)},
            supported_query_ids=self.supported_query_ids,
            default_query_id=self.default_query_id,
            task_id=self.task_id,
        )
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) if attempt_index == 0 else int(hash64(int(instance_seed), self.task_id, attempt_index))
            try:
                attempt_params = {**dict(task_params), "_attempt_index": int(attempt_index)}
                return self._generate_once(
                    int(attempt_seed),
                    params=attempt_params,
                    selected_query_id=str(selected_query_id),
                    query_probabilities=query_probabilities,
                )
            except (RuntimeError, ValueError) as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")

    def _generate_once(
        self,
        instance_seed: int,
        *,
        params: dict[str, Any],
        selected_query_id: str,
        query_probabilities: dict[str, float],
    ) -> TaskOutput:
        """Bind query region, render the scene, and emit the scalar bbox annotation."""

        target_region = str(QUERY_REGION_BY_ID[str(selected_query_id)])
        dataset = build_dataset(
            params=params,
            instance_seed=int(instance_seed),
            target_region=target_region,
        )
        rendered = render_scatter_facet_dataset(
            dataset=dataset,
            params=params,
            instance_seed=int(instance_seed),
        )
        annotation, witness_symbolic = density_region_bbox_annotation(dataset=dataset, rendered=rendered)
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key=str(selected_query_id),
            dynamic_slot_values=dynamic_slots(dataset=dataset),
            instance_seed=int(instance_seed),
        )
        trace_payload = _trace_payload(
            dataset=dataset,
            rendered=rendered,
            prompt_artifacts=prompt_artifacts,
            selected_query_id=str(selected_query_id),
            query_probabilities=dict(query_probabilities),
            annotation=annotation,
            witness_symbolic=witness_symbolic,
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=TypedValue(type="string", value=str(dataset.query.answer_label)),
            annotation_gt=annotation.annotation_gt,
            image=rendered.image,
            image_id="img0",
            trace_payload=dict(trace_payload),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(selected_query_id),
        )


__all__ = ["ChartsScatterFacetGridRegionDensityExtremumLabelTask", "QUERY_IDS", "SUPPORTED_QUERY_IDS", "TASK_ID"]

SUPPORTED_QUERY_IDS = QUERY_IDS
