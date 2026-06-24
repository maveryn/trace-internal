"""Find a segment length from parallel-segment proportion markings."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from ._lifecycle import ParallelSceneArtifacts, prepare_parallel_scene_artifacts
from .shared.construction import (
    SEGMENT_LENGTH_ANSWER_SUPPORT,
    build_segment_length_plan,
    select_answer,
    select_construction_family,
    select_variant_index,
)
from .shared.defaults import SCENE_DEFAULTS, SCENE_ID
from .shared.output import (
    ParallelTraceSections,
    build_parallel_trace_sections,
    build_scene_ir,
    numeric_answer,
)
from .shared.prompts import parallel_segment_prompt_artifacts
from .shared.state import ParallelProportionPlan

TASK_ID = "task_geometry__parallel_segment_proportion__segment_length_value"
SUPPORTED_QUERY_IDS: tuple[str, ...] = ("single",)
PROMPT_TASK_KEY = "segment_length_value"
OBJECT_DESCRIPTION = "a labeled parallel-line proportion diagram with expression and measurement labels"


def _resolve_segment_plan(instance_seed: int, params: Mapping[str, Any]) -> tuple[ParallelProportionPlan, dict[str, float]]:
    """Bind the target-segment objective to one answer-balanced construction case."""

    construction_family, construction_probabilities = select_construction_family(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.construction_family",
    )
    target_length = select_answer(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{construction_family}.answer",
        support=SEGMENT_LENGTH_ANSWER_SUPPORT,
    )
    variant_index = select_variant_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{construction_family}.case",
    )
    plan = build_segment_length_plan(
        construction_family=str(construction_family),
        answer=int(target_length),
        variant_index=int(variant_index),
    )
    return plan, dict(construction_probabilities)


def _segment_trace_payload(
    *,
    selected_query: str,
    query_probabilities: Mapping[str, float],
    sections: ParallelTraceSections,
    artifacts: ParallelSceneArtifacts,
    prompt_artifacts: Any,
) -> dict[str, Any]:
    """Assemble segment-length trace fields after answer and annotation are bound."""

    scene_ir = build_scene_ir(
        scene_entities=artifacts.rendered.scene_entities,
        relations={"query_id": str(selected_query), **sections.scene_relations},
    )
    scene_ir["task_id"] = TASK_ID
    return {
        "scene_ir": scene_ir,
        "query_spec": _segment_query_spec(
            prompt_artifacts=prompt_artifacts,
            selected_query=str(selected_query),
            query_probabilities=query_probabilities,
            sections=sections,
        ),
        "render_spec": {
            "task_id": TASK_ID,
            "scene_id": SCENE_ID,
            "query_id": str(selected_query),
            **sections.render_spec_base,
        },
        "render_map": dict(artifacts.rendered.render_map),
        "execution_trace": {
            "task_id": TASK_ID,
            "scene_id": SCENE_ID,
            "query_id": str(selected_query),
            "query_id_probabilities": dict(query_probabilities),
            "objective": "segment_length_value",
            **sections.execution_common,
        },
        "witness_symbolic": {
            "type": "parallel_segment_proportion_length",
            "task_id": TASK_ID,
            "query_id": str(selected_query),
            **sections.witness_common,
        },
        "projected_annotation": dict(artifacts.annotation_artifacts.projected_annotation),
    }


def _segment_query_spec(
    *,
    prompt_artifacts: Any,
    selected_query: str,
    query_probabilities: Mapping[str, float],
    sections: ParallelTraceSections,
) -> dict[str, Any]:
    """Build public query metadata for the segment-length task."""

    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(selected_query),
        params={
            "scene_id": SCENE_ID,
            "query_id": str(selected_query),
            "query_id_probabilities": dict(query_probabilities),
            **sections.query_params_base,
        },
    )
    query_spec["scene_id"] = SCENE_ID
    return query_spec


@register_task
class GeometryParallelSegmentProportionSegmentLengthValueTask:
    """Solve the visible proportion equation for a requested segment length."""

    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        """Own segment answer binding, annotation binding, and final output."""

        selected_query, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id="single",
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        _gen_defaults, rendering_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
            SCENE_DEFAULTS,
            task_id=TASK_ID,
        )
        artifacts = prepare_parallel_scene_artifacts(
            instance_seed=int(instance_seed),
            params=task_params,
            rendering_defaults=rendering_defaults,
            max_attempts=int(max_attempts),
            resolve_plan=_resolve_segment_plan,
        )
        prompt_artifacts = parallel_segment_prompt_artifacts(
            prompt_defaults=prompt_defaults,
            prompt_task_key=PROMPT_TASK_KEY,
            object_description=OBJECT_DESCRIPTION,
            target_name=artifacts.plan.target_name,
            variable_name=artifacts.plan.variable_name,
            answer=float(artifacts.plan.answer),
            instance_seed=int(instance_seed),
        )[1]
        sections = build_parallel_trace_sections(
            plan=artifacts.plan,
            rendered=artifacts.rendered,
            annotation_artifacts=artifacts.annotation_artifacts,
            construction_probabilities=artifacts.construction_probabilities,
            render_meta=artifacts.render_meta,
            noise_meta=artifacts.noise_meta,
            image_size=(int(artifacts.image.size[0]), int(artifacts.image.size[1])),
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="number", value=numeric_answer(artifacts.plan.answer)),
            annotation_gt=TypedValue(
                type=artifacts.annotation_artifacts.annotation_type,
                value=artifacts.annotation_artifacts.value,
            ),
            image=artifacts.image,
            image_id="img0",
            trace_payload=_segment_trace_payload(
                selected_query=str(selected_query),
                query_probabilities=query_probabilities,
                sections=sections,
                artifacts=artifacts,
                prompt_artifacts=prompt_artifacts,
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(selected_query),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GeometryParallelSegmentProportionSegmentLengthValueTask"]
