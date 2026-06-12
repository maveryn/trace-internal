"""Compute the outer chord length from the two radii."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from trace.core.scene_config import get_scene_defaults
from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults, required_group_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    build_prompt_query_spec,
    render_scene_prompt_variants,
)
from trace.tasks.shared.fixed_query import geometry_selected_probability_map

from .shared.runtime import (
    DOMAIN,
    POST_IMAGE_NOISE_DEFAULTS,
    SCENE_ID,
    make_chord_length_problem,
    chord_length_support_values,
    create_render_context,
    render_concentric_chord_scene,
    select_case_index,
)

TASK_ID = "task_geometry__concentric_chord__chord_length_from_radii"
QUERY_ID = "chord_length_from_radii"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
_SCENE_DEFAULTS = get_scene_defaults(DOMAIN, SCENE_ID)
_GEN_DEFAULTS_UNUSED, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    DOMAIN,
    SCENE_ID,
    task_id=TASK_ID,
)




def _prompt_artifacts(*, selected_query: str, instance_seed: int) -> tuple[Dict[str, Any], Any]:
    prompt_defaults = required_group_defaults(
        _PROMPT_DEFAULTS,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "object_description",
            "json_output_contract",
            "json_output_contract_answer_only",
            "annotation_hint",
            "answer_hint_number",
            "json_example",
            "json_example_answer_only",
        ),
        context=f"prompt defaults for {TASK_ID}",
    )
    prompt_selection = render_scene_prompt_variants(
        domain=DOMAIN,
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(selected_query),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(prompt_defaults["object_description"]),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(prompt_defaults["annotation_hint"]),
            "answer_hint": str(prompt_defaults["answer_hint_number"]),
            "json_example": str(prompt_defaults["json_example"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
        },
        instance_seed=int(instance_seed),
    )
    return dict(prompt_defaults), build_prompt_trace_artifacts(prompt_selection)


def _keyed_points(rendered: Any) -> Dict[str, list[float]]:
    return {
        str(key): [round(float(point[0]), 3), round(float(point[1]), 3)]
        for key, point in rendered.annotation_keyed_points.items()
    }


def _trace_payload(
    *,
    selected_query: str,
    query_probabilities: Mapping[str, float],
    prompt_artifacts: Any,
    rendered: Any,
    render_meta: Mapping[str, Any],
    noise_meta: Mapping[str, Any],
    image_size: tuple[int, int],
    case_index: int,
    target_support_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    annotation_keyed_points = _keyed_points(rendered)
    witness_payload = dict(rendered.witness)
    query_params = {
        "scene_id": SCENE_ID,
        "scene_variant": "tangent_chord",
        "query_id": str(selected_query),
        "query_id_probabilities": dict(query_probabilities),
        "case_index": int(case_index),
        "target_support_probabilities": dict(target_support_probabilities),
        **dict(witness_payload),
    }
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(selected_query),
        params=query_params,
    )
    query_spec["scene_id"] = SCENE_ID
    return {
        "scene_ir": {
            "scene_kind": "geometry_concentric_circle_chord",
            "scene_id": SCENE_ID,
            "entities": [dict(entity) for entity in rendered.scene_entities],
            "relations": {
                "query_id": str(selected_query),
                "scene_variant": "tangent_chord",
                "answer_value": float(rendered.answer),
                "annotation_roles": list(rendered.annotation_roles),
            },
        },
        "query_spec": query_spec,
        "render_spec": {
            "canvas_size": [int(image_size[0]), int(image_size[1])],
            "coord_space": "pixel",
            "post_image_noise": dict(noise_meta),
            **dict(render_meta),
        },
        "render_map": {"coord_space": "pixel", **dict(rendered.render_map)},
        "execution_trace": {
            "scene_id": SCENE_ID,
            "scene_variant": "tangent_chord",
            "query_id": str(selected_query),
            "query_id_probabilities": dict(query_probabilities),
            "answer_type": "number",
            "answer_value": float(rendered.answer),
            "answer_rounding": "nearest_tenth",
            "annotation_roles": list(rendered.annotation_roles),
            "reasoning_steps": 1,
            **dict(witness_payload),
        },
        "witness_symbolic": {
            "type": "concentric_circle_chord_formula",
            "scene_id": SCENE_ID,
            "query_id": str(selected_query),
            "answer_value": float(rendered.answer),
            "source_witness_type": "keyed_point_map",
            "original_annotation_value": dict(annotation_keyed_points),
            **dict(witness_payload),
        },
        "projected_annotation": {
            "type": "keyed_point_map",
            "keyed_point_map": dict(annotation_keyed_points),
            "pixel_keyed_point_map": dict(annotation_keyed_points),
        },
    }


@register_task
class GeometryConcentricChordLengthFromRadiiTask:
    """Compute the outer chord length from the visible radii."""

    task_id = TASK_ID
    domain = DOMAIN
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    reasoning_kind = "concentric_circle_chord"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            task_id=TASK_ID,
        )
        case_index = select_case_index(
            instance_seed=int(instance_seed),
            params=task_params,
            namespace=f"{TASK_ID}.{selected_query}.case",
        )
        problem = make_chord_length_problem(case_index=int(case_index), params=task_params)
        support_probabilities = geometry_selected_probability_map(
            chord_length_support_values(),
            problem.answer,
            is_selected=lambda value, selected: float(value) == float(selected),
        )
        last_error: Exception | None = None
        rendered = None
        render_meta: Dict[str, Any] | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                attempt_params = dict(task_params)
                attempt_params["_render_attempt"] = int(attempt_index)
                ctx, render_meta_attempt = create_render_context(
                    instance_seed=int(instance_seed) + int(attempt_index),
                    params=attempt_params,
                    render_defaults=_RENDER_DEFAULTS,
                    random_namespace=f"{TASK_ID}.render",
                )
                rendered = render_concentric_chord_scene(ctx, problem)
                render_meta = dict(render_meta_attempt)
                render_meta["single_object_scene_rotation"] = ctx.scene_transform.metadata()
                break
            except Exception as exc:
                last_error = exc
                continue
        if rendered is None or render_meta is None:
            raise RuntimeError(f"failed to generate {TASK_ID}") from last_error

        image, noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=task_params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        _prompt_defaults, prompt_artifacts = _prompt_artifacts(
            selected_query=str(selected_query),
            instance_seed=int(instance_seed),
        )
        annotation_value = _keyed_points(rendered)
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="number", value=float(rendered.answer)),
            annotation_gt=TypedValue(type="keyed_point_map", value=dict(annotation_value)),
            image=image,
            image_id="img0",
            trace_payload=_trace_payload(
                selected_query=str(selected_query),
                query_probabilities=query_probabilities,
                prompt_artifacts=prompt_artifacts,
                rendered=rendered,
                render_meta=render_meta,
                noise_meta=noise_meta,
                image_size=(int(image.size[0]), int(image.size[1])),
                case_index=int(case_index),
                target_support_probabilities=support_probabilities,
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(selected_query),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GeometryConcentricChordLengthFromRadiiTask"]
