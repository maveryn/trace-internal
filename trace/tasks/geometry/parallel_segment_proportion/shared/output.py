"""Trace-section helpers for parallel-segment proportion tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .defaults import SCENE_ID, SCENE_KIND, SCENE_VARIANT
from .state import ParallelProportionPlan, RenderedParallelProportionScene
from ...shared.annotation_values import PixelAnnotationArtifacts


def numeric_answer(value: float) -> float | int:
    """Return integer-looking geometry answers as ints for stable JSON."""

    rounded = round(float(value), 1)
    if abs(rounded - round(rounded)) <= 1e-9:
        return int(round(rounded))
    return float(rounded)


@dataclass(frozen=True)
class ParallelTraceSections:
    """Task-neutral trace fragments assembled with public task fields later."""

    query_params_base: dict[str, Any]
    scene_relations: dict[str, Any]
    render_spec_base: dict[str, Any]
    execution_common: dict[str, Any]
    witness_common: dict[str, Any]


def build_parallel_trace_sections(
    *,
    plan: ParallelProportionPlan,
    rendered: RenderedParallelProportionScene,
    annotation_artifacts: PixelAnnotationArtifacts,
    construction_probabilities: Mapping[str, float],
    render_meta: Mapping[str, Any],
    noise_meta: Mapping[str, Any],
    image_size: tuple[int, int],
) -> ParallelTraceSections:
    """Format shared scene/verifier fragments without public task identity."""

    answer_value = numeric_answer(plan.answer)
    query_params_base = {
        "construction_family": str(plan.construction_family),
        "construction_family_probabilities": dict(construction_probabilities),
        "source_kind": str(plan.construction_family),
        "source_kind_probabilities": dict(construction_probabilities),
        "answer_support": [str(value) for value in plan.answer_support],
        **dict(plan.params),
    }
    scene_relations = {
        "scene_variant": SCENE_VARIANT,
        "construction_family": str(plan.construction_family),
        "relation": str(plan.relation),
        "formula_family": str(plan.formula_family),
        "answer_value": answer_value,
        **dict(rendered.witness),
    }
    render_spec_base = {
        "canvas_size": [int(image_size[0]), int(image_size[1])],
        "coord_space": "pixel",
        "single_object_scene_rotation": dict(render_meta.get("single_object_scene_rotation", {})),
        "post_image_noise": dict(noise_meta),
        **dict(render_meta),
    }
    execution_common = {
        "scene_variant": SCENE_VARIANT,
        "source_kind": str(plan.construction_family),
        "source_kind_probabilities": dict(construction_probabilities),
        "construction_family": str(plan.construction_family),
        "target_name": str(plan.target_name),
        "variable_name": str(plan.variable_name),
        "relation": str(plan.relation),
        "formula_family": str(plan.formula_family),
        "answer_type": "number",
        "answer": answer_value,
        "answer_value": answer_value,
        "labels": dict(plan.labels),
        "annotation_type": annotation_artifacts.annotation_type,
        **dict(plan.params),
    }
    witness_common = {
        "scene_id": SCENE_ID,
        "construction_family": str(plan.construction_family),
        "target_name": str(plan.target_name),
        "answer": answer_value,
        "labels": dict(plan.labels),
        "source_witness_type": annotation_artifacts.annotation_type,
    }
    return ParallelTraceSections(
        query_params_base=query_params_base,
        scene_relations=scene_relations,
        render_spec_base=render_spec_base,
        execution_common=execution_common,
        witness_common=witness_common,
    )


def build_scene_ir(*, scene_entities: tuple[dict[str, Any], ...], relations: Mapping[str, Any]) -> dict[str, Any]:
    """Build the scene-level trace root before public task identity is added."""

    return {
        "scene_kind": SCENE_KIND,
        "scene_id": SCENE_ID,
        "entities": [dict(entity) for entity in scene_entities],
        "relations": dict(relations),
    }


__all__ = [
    "ParallelTraceSections",
    "build_parallel_trace_sections",
    "build_scene_ir",
    "numeric_answer",
]
