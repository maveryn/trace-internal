"""Compute an opposite-side sum in a tangential quadrilateral."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from trace.core.scene_config import get_scene_defaults
from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec
from trace.tasks.geometry.shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS

from ._lifecycle import projected_keyed_point_payload, render_spec_payload, render_with_layout_retry
from .shared.annotations import keyed_point_annotation
from .shared.construction import (
    select_target_pair,
    select_tangent_case,
    side_lengths_from_vertex_tangents,
    vertex_tangents_from_case,
)
from .shared.prompts import tangential_prompt_artifacts
from .shared.rendering import create_circle_polygon_render_context, render_tangential_scene
from .shared.state import SCENE_ID, RenderedTangentialScene, TangentialDiagramSpec


TASK_ID = "task_geometry__circle_polygon_composite__tangential_quadrilateral_side_sum_value"
QUERY_ID = "opposite_side_sum_from_tangent_quadrilateral"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)

_SCENE_DEFAULTS = get_scene_defaults("geometry", SCENE_ID)
_GEN_DEFAULTS_UNUSED, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS,
    task_id=TASK_ID,
)


@dataclass(frozen=True)
class _TangentialProblem:
    """Task-owned answer, prompt, and trace facts for one side-sum instance."""

    diagram_spec: TangentialDiagramSpec
    target_pair: str
    target_pair_label: str
    known_pair: str
    known_pair_label: str
    answer: int
    target_pair_probabilities: dict[str, float]
    tangent_case_probabilities: dict[str, float]


def _bind_side_sum_problem(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    selected_query: str,
) -> _TangentialProblem:
    """Bind the hidden side pair and answer before rendering."""

    target_pair, target_pair_probabilities = select_target_pair(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{selected_query}.target_pair",
    )
    tangent_case, tangent_case_probabilities = select_tangent_case(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{selected_query}.tangent_case",
    )
    vertex_tangents = vertex_tangents_from_case(tangent_case)
    side_lengths = side_lengths_from_vertex_tangents(tangent_case)
    if target_pair == "AB_CD":
        target_pair_label = "AB + CD"
        known_pair = "BC_DA"
        known_pair_label = "BC and DA"
        unknown_sides = ("AB", "CD")
        answer = int(side_lengths["AB"] + side_lengths["CD"])
    else:
        target_pair_label = "BC + DA"
        known_pair = "AB_CD"
        known_pair_label = "AB and CD"
        unknown_sides = ("BC", "DA")
        answer = int(side_lengths["BC"] + side_lengths["DA"])
    return _TangentialProblem(
        diagram_spec=TangentialDiagramSpec(
            vertex_tangents=dict(vertex_tangents),
            side_lengths=dict(side_lengths),
            unknown_sides=tuple(unknown_sides),
        ),
        target_pair=str(target_pair),
        target_pair_label=str(target_pair_label),
        known_pair=str(known_pair),
        known_pair_label=str(known_pair_label),
        answer=int(answer),
        target_pair_probabilities=dict(target_pair_probabilities),
        tangent_case_probabilities=dict(tangent_case_probabilities),
    )


def _draw_tangential_diagram_with_retry(
    *,
    instance_seed: int,
    task_params: Mapping[str, Any],
    selected_query: str,
    problem: _TangentialProblem,
    max_attempts: int,
) -> tuple[Any, RenderedTangentialScene]:
    """Retry only the stochastic layout while preserving the task-bound answer."""

    def build_context(attempt_seed: int, attempt_params: Mapping[str, Any]) -> Any:
        return create_circle_polygon_render_context(
            instance_seed=int(attempt_seed),
            params=attempt_params,
            rendering_defaults=_RENDER_DEFAULTS,
            fill_namespace=f"{TASK_ID}.{selected_query}.fill_palette",
        )

    def draw_scene(render_context: Any, attempt_seed: int) -> RenderedTangentialScene:
        return render_tangential_scene(
            render_context,
            problem.diagram_spec,
            instance_seed=int(attempt_seed),
            render_namespace=f"{TASK_ID}.{selected_query}.render.scene",
        )

    return render_with_layout_retry(
        instance_seed=int(instance_seed),
        task_params=task_params,
        max_attempts=int(max_attempts),
        build_context=build_context,
        draw_scene=draw_scene,
    )


def _build_side_sum_trace_payload(
    *,
    rendered: RenderedTangentialScene,
    image_size: tuple[int, int],
    render_context: Any,
    noise_meta: Mapping[str, Any],
    selected_query: str,
    query_probabilities: Mapping[str, float],
    prompt_artifacts: Any,
    problem: _TangentialProblem,
    annotation_value: Mapping[str, list[float]],
) -> dict[str, Any]:
    """Serialize task-owned side-sum facts into trace metadata."""

    side_lengths = problem.diagram_spec.side_lengths
    opposite_sum_ab_cd = int(side_lengths["AB"] + side_lengths["CD"])
    opposite_sum_bc_da = int(side_lengths["BC"] + side_lengths["DA"])
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(selected_query),
        params={
            "query_id": str(selected_query),
            "query_id_probabilities": dict(query_probabilities),
            "target_pair": str(problem.target_pair),
            "target_pair_probabilities": dict(problem.target_pair_probabilities),
            "tangent_case_probabilities": dict(problem.tangent_case_probabilities),
        },
    )
    query_spec["scene_id"] = SCENE_ID
    query_spec["task_id"] = TASK_ID

    return {
        "scene_ir": {
            "domain": "geometry",
            "scene_id": SCENE_ID,
            "task_id": TASK_ID,
            "query_id": str(selected_query),
            "entities": {
                "vertices": dict(rendered.render_map["vertices"]),
                "tangency_points": dict(rendered.render_map["tangency_points"]),
                "incircle_center": list(rendered.render_map["incircle_center"]),
            },
            "relations": {
                "type": "tangential_quadrilateral_opposite_side_sum",
                "target_pair": str(problem.target_pair),
                "known_pair": str(problem.known_pair),
            },
        },
        "query_spec": query_spec,
        "render_spec": render_spec_payload(
            scene_id=SCENE_ID,
            task_id=TASK_ID,
            query_id=str(selected_query),
            image_size=image_size,
            render_context=render_context,
            noise_meta=noise_meta,
            prompt_artifacts=prompt_artifacts,
        ),
        "render_map": dict(rendered.render_map),
        "execution_trace": {
            "task_id": TASK_ID,
            "scene_id": SCENE_ID,
            "query_id": str(selected_query),
            "target_pair": str(problem.target_pair),
            "known_pair": str(problem.known_pair),
            "vertex_tangents": dict(problem.diagram_spec.vertex_tangents),
            "side_lengths": dict(side_lengths),
            "opposite_sum_AB_CD": int(opposite_sum_ab_cd),
            "opposite_sum_BC_DA": int(opposite_sum_bc_da),
            "answer": int(problem.answer),
            "annotation_roles": list(rendered.annotation_roles),
        },
        "witness_symbolic": {
            "task_id": TASK_ID,
            "scene_id": SCENE_ID,
            "query_id": str(selected_query),
            "formula_family": "pitot_theorem_tangential_quadrilateral",
            "target_pair": str(problem.target_pair),
            "known_pair": str(problem.known_pair),
            "vertex_tangents": dict(problem.diagram_spec.vertex_tangents),
            "side_lengths": dict(side_lengths),
            "opposite_sum_AB_CD": int(opposite_sum_ab_cd),
            "opposite_sum_BC_DA": int(opposite_sum_bc_da),
            "answer_value": int(problem.answer),
        },
        "projected_annotation": projected_keyed_point_payload(annotation_value),
    }


@register_task
class GeometryCirclePolygonCompositeTangentialQuadrilateralSideSumValueTask:
    """Compute an opposite side sum in a tangential quadrilateral."""

    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Select a side-sum query and bind answer/annotation in this public task."""

        selected_query, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            task_id=TASK_ID,
        )
        problem = _bind_side_sum_problem(
            instance_seed=int(instance_seed),
            params=task_params,
            selected_query=str(selected_query),
        )
        render_context, rendered = _draw_tangential_diagram_with_retry(
            instance_seed=int(instance_seed),
            task_params=task_params,
            selected_query=str(selected_query),
            problem=problem,
            max_attempts=int(max_attempts),
        )
        image, noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=task_params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        _prompt_defaults, prompt_artifacts = tangential_prompt_artifacts(
            prompt_defaults=_PROMPT_DEFAULTS,
            prompt_query_key=str(selected_query),
            target_pair=str(problem.target_pair_label),
            known_pair=str(problem.known_pair_label),
            answer_value=int(problem.answer),
            annotation_keys=rendered.annotation_roles,
            instance_seed=int(instance_seed),
        )
        annotation_value = keyed_point_annotation(rendered)
        trace_payload = _build_side_sum_trace_payload(
            rendered=rendered,
            image_size=image.size,
            render_context=render_context,
            noise_meta=dict(noise_meta),
            selected_query=str(selected_query),
            query_probabilities=query_probabilities,
            prompt_artifacts=prompt_artifacts,
            problem=problem,
            annotation_value=annotation_value,
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(problem.answer)),
            annotation_gt=TypedValue(type="keyed_point_map", value=dict(annotation_value)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(selected_query),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = [
    "GeometryCirclePolygonCompositeTangentialQuadrilateralSideSumValueTask",
    "QUERY_ID",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
