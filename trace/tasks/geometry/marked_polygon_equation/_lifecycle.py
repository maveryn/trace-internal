"""Scene-private trace assembly for marked polygon equation tasks."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.prompt_variants import PromptTraceArtifacts, build_prompt_query_spec

from .shared.defaults import SCENE_DEFAULTS, SCENE_ID, SCENE_KIND, SCENE_VARIANT
from .shared.output import MarkedEquationTaskParts, prepare_marked_equation_parts
from .shared.prompts import number_answer
from .shared.state import MarkedEquationCase


def marked_equation_trace_payload(
    *,
    task_id: str,
    selected_query: str,
    query_probabilities: Mapping[str, float],
    case: MarkedEquationCase,
    case_index: int,
    construction_family_probabilities: Mapping[str, float],
    prompt_artifacts: PromptTraceArtifacts,
    parts: MarkedEquationTaskParts,
    answer_value: int | float,
    reasoning_steps: int,
) -> dict[str, Any]:
    """Build trace sections from a public-task-selected case and annotation."""

    case_fields = case.trace_fields()
    query_params = {
        "scene_id": SCENE_ID,
        "query_id": str(selected_query),
        "query_id_probabilities": dict(query_probabilities),
        "construction_family": str(case.construction_family),
        "construction_family_probabilities": dict(construction_family_probabilities),
        "case_index": int(case_index),
        **dict(case_fields),
    }
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(selected_query),
        params=query_params,
    )
    query_spec["scene_id"] = SCENE_ID
    return {
        "scene_ir": {
            "scene_kind": SCENE_KIND,
            "scene_id": SCENE_ID,
            "task_id": str(task_id),
            "entities": [dict(entity) for entity in parts.rendered.scene_entities],
            "relations": {
                "query_id": str(selected_query),
                "scene_variant": SCENE_VARIANT,
                "answer_value": answer_value,
                "annotation_roles": list(parts.annotation_artifacts.value.keys()),
                **dict(case_fields),
            },
        },
        "query_spec": query_spec,
        "render_spec": {
            "task_id": str(task_id),
            "scene_id": SCENE_ID,
            "query_id": str(selected_query),
            "post_image_noise": dict(parts.noise_meta),
            **dict(parts.render_meta),
            "prompt": {
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            },
        },
        "render_map": {"coord_space": "pixel", **dict(parts.rendered.render_map)},
        "execution_trace": {
            "task_id": str(task_id),
            "scene_id": SCENE_ID,
            "scene_variant": SCENE_VARIANT,
            "query_id": str(selected_query),
            "query_id_probabilities": dict(query_probabilities),
            "answer_type": "number",
            "answer": answer_value,
            "answer_value": answer_value,
            "annotation_roles": list(parts.annotation_artifacts.value.keys()),
            "reasoning_steps": int(reasoning_steps),
            **dict(case_fields),
        },
        "witness_symbolic": {
            "type": "marked_polygon_equation_formula",
            "task_id": str(task_id),
            "scene_id": SCENE_ID,
            "query_id": str(selected_query),
            "answer_value": answer_value,
            "source_witness_type": parts.annotation_artifacts.annotation_type,
            "original_annotation_value": parts.annotation_artifacts.value,
            **dict(case_fields),
        },
        "projected_annotation": dict(parts.annotation_artifacts.projected_annotation),
    }

def run_marked_equation_task(
    *,
    task_id: str,
    supported_queries: tuple[str, ...],
    build_case: Any,
    reasoning_steps: int,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> TaskOutput:
    """Run common scene plumbing after the public task selects its objective case."""

    selected_query, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=tuple(str(value) for value in supported_queries),
        default_query_id="single",
        task_id=str(task_id),
        namespace=f"{task_id}.query",
    )
    case, case_index, family_probabilities, task_params = build_case(int(instance_seed), task_params)
    _generation_defaults, rendering_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
        SCENE_DEFAULTS,
        task_id=str(task_id),
    )
    parts = prepare_marked_equation_parts(
        case=case,
        prompt_task_key=str(prompt_defaults["task_key"]),
        prompt_question_key=str(prompt_defaults["task_key"]),
        rendering_defaults=rendering_defaults,
        prompt_defaults=prompt_defaults,
        instance_seed=int(instance_seed),
        params=task_params,
        max_attempts=int(max_attempts),
    )
    answer_value = number_answer(case.answer)
    trace_payload = marked_equation_trace_payload(
        task_id=str(task_id),
        selected_query=str(selected_query),
        query_probabilities=query_probabilities,
        case=case,
        case_index=int(case_index),
        construction_family_probabilities=family_probabilities,
        prompt_artifacts=parts.prompt_artifacts,
        parts=parts,
        answer_value=answer_value,
        reasoning_steps=int(reasoning_steps),
    )
    return TaskOutput(
        prompt=str(parts.prompt),
        answer_gt=TypedValue(type="number", value=answer_value),
        annotation_gt=TypedValue(type=parts.annotation_artifacts.annotation_type, value=parts.annotation_artifacts.value),
        image=parts.image,
        image_id="img0",
        trace_payload=trace_payload,
        task_versions=parts.task_versions,
        scene_id=SCENE_ID,
        query_id=str(selected_query),
        prompt_variants=dict(parts.prompt_variants),
    )


__all__ = ["marked_equation_trace_payload", "run_marked_equation_task"]
