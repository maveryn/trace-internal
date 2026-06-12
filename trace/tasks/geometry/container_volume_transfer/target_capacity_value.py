"""Compute target capacity from source volume and pour count."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Mapping, Tuple

from trace.core.scene_config import get_scene_defaults
from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults, required_group_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_query_spec, build_prompt_trace_artifacts, render_scene_prompt_variants
from trace.tasks.geometry.shared.measurement_rendering import bbox_to_list

from .shared.runtime import (
    POST_IMAGE_NOISE_DEFAULTS,
    FILL_COUNT_QUERY_IDS,
    RESULTING_HEIGHT_QUERY_IDS,
    TARGET_CAPACITY_QUERY_IDS,
    TRANSFERRED_VOLUME_QUERY_IDS,
    FILL_COUNT_ANNOTATION_KEYS,
    RESULTING_HEIGHT_ANNOTATION_KEYS,
    TARGET_CAPACITY_ANNOTATION_KEYS,
    TRANSFERRED_VOLUME_ANNOTATION_KEYS,
    QUERY_ID_CONE_TO_CYLINDER_FILL_COUNT,
    QUERY_ID_CYLINDER_TO_CUBOID_FILL_COUNT,
    QUERY_ID_CONE_POURS_TO_CYLINDER_HEIGHT,
    QUERY_ID_CYLINDER_POURS_TO_CUBOID_HEIGHT,
    QUERY_ID_TARGET_CAPACITY_FROM_SOURCE_AND_COUNT,
    QUERY_ID_REPEATED_CONE_POURS_TOTAL_VOLUME,
    QUERY_ID_REPEATED_CYLINDER_POURS_TOTAL_VOLUME,
    cone_fill_count_support_probabilities,
    cone_resulting_height_support_probabilities,
    create_render_context,
    cylinder_fill_count_support_probabilities,
    cylinder_resulting_height_support_probabilities,
    json_answer_value,
    make_prompt_examples,
    render_container_volume_transfer_scene,
    repeated_cone_volume_support_probabilities,
    repeated_cylinder_volume_support_probabilities,
    resolve_cone_fill_count_case,
    resolve_cone_resulting_height_case,
    resolve_cylinder_fill_count_case,
    resolve_cylinder_resulting_height_case,
    resolve_target_capacity_case,
    resolve_transferred_volume_case,
    select_cone_fill_count_case,
    select_cone_resulting_height_case,
    select_cylinder_fill_count_case,
    select_cylinder_resulting_height_case,
    select_repeated_cone_volume_case,
    select_repeated_cylinder_volume_case,
    select_target_capacity_case,
    target_capacity_support_probabilities,
)

DOMAIN = "geometry"
SCENE_ID = "container_volume_transfer"
PROMPT_BUNDLE_ID = "geometry_container_volume_transfer_v0"
_SCENE_DEFAULTS = get_scene_defaults(DOMAIN, SCENE_ID)

TASK_ID = "task_geometry__container_volume_transfer__target_capacity_value"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = TARGET_CAPACITY_QUERY_IDS
ANNOTATION_KEYS: Tuple[str, ...] = TARGET_CAPACITY_ANNOTATION_KEYS
PROMPT_TASK_KEY = "target_capacity_value_query"
OBJECTIVE = "target_capacity"
ANSWER_GT_TYPE = "integer"
ANSWER_HINT_KEY = "answer_hint_integer"
_GEN_DEFAULTS_UNUSED, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    DOMAIN,
    SCENE_ID,
    task_id=TASK_ID,
)

_QUERY_PROGRAMS = {
    QUERY_ID_TARGET_CAPACITY_FROM_SOURCE_AND_COUNT: (select_target_capacity_case, resolve_target_capacity_case, target_capacity_support_probabilities),
}


def _resolve_selected_problem(*, selected_query: str, query_probabilities: Mapping[str, float], instance_seed: int, params: Mapping[str, Any]):
    program = _QUERY_PROGRAMS.get(str(selected_query))
    if program is None:
        raise ValueError(f"unsupported query_id for {TASK_ID}: {selected_query}")
    case_selector, resolver, support_builder = program
    case, case_probabilities = case_selector(
        instance_seed=int(instance_seed),
        params=params,
        namespace=f"geometry.container_volume_transfer.{OBJECTIVE}.{selected_query}",
    )
    problem = resolver(case)
    explicit_answer = params.get("fill_count")
    if explicit_answer is not None and int(explicit_answer) != int(problem.fill_count):
        raise ValueError("fill_count must equal target_volume / source_volume")
    explicit_pour_count = params.get("pour_count")
    if explicit_pour_count is not None and int(explicit_pour_count) != int(problem.pour_count):
        raise ValueError("pour_count must match the selected transfer_case")
    return replace(
        problem,
        query_probabilities=dict(query_probabilities),
        case_probabilities=dict(case_probabilities),
        answer_support_probabilities=support_builder(),
    )


def _prompt_artifacts(*, selected_query: str, answer: int | float, instance_seed: int):
    prompt_defaults = required_group_defaults(
        _PROMPT_DEFAULTS,
        (
            "bundle_id",
            "scene_key",
            "object_description",
            "json_output_contract",
            "json_output_contract_answer_only",
            "annotation_hint",
            ANSWER_HINT_KEY,
        ),
        context=f"prompt defaults for {TASK_ID}",
    )
    annotation_names = ", ".join(f'"{key}"' for key in ANNOTATION_KEYS)
    json_example, json_example_answer_only = make_prompt_examples(answer=answer, annotation_keys=ANNOTATION_KEYS)
    prompt_selection = render_scene_prompt_variants(
        domain=DOMAIN,
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=PROMPT_TASK_KEY,
        query_key=str(selected_query),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(prompt_defaults["object_description"]),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(prompt_defaults["annotation_hint"]).format(annotation_keys=annotation_names),
            "answer_hint": str(prompt_defaults[ANSWER_HINT_KEY]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        },
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(prompt_selection)


def _annotation_value(rendered: Any) -> Dict[str, list[float]]:
    return {str(key): bbox_to_list(rendered.annotation_bboxes[str(key)]) for key in ANNOTATION_KEYS}




@register_task
class GeometryContainerVolumeTransferTargetCapacityValueTask:
    """Compute target capacity from the source container and displayed transfer count."""

    task_id = TASK_ID
    domain = DOMAIN
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    reasoning_kind = "container_volume_transfer"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SUPPORTED_QUERY_IDS[0],
            task_id=TASK_ID,
        )
        problem = _resolve_selected_problem(
            selected_query=str(selected_query),
            query_probabilities=query_probabilities,
            instance_seed=int(instance_seed),
            params=task_params,
        )
        rendered = None
        ctx = None
        render_meta: Dict[str, Any] | None = None
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                render_seed = int(instance_seed) + int(attempt_index) * 9973
                ctx, render_meta = create_render_context(
                    instance_seed=render_seed,
                    params=task_params,
                    render_defaults=_RENDER_DEFAULTS,
                    random_namespace=f"geometry.container_volume_transfer.{OBJECTIVE}.render",
                )
                rendered = render_container_volume_transfer_scene(ctx, problem, instance_seed=render_seed)
                break
            except Exception as exc:
                last_error = exc
                rendered = None
                ctx = None
                render_meta = None
        if rendered is None or ctx is None or render_meta is None:
            raise RuntimeError(f"failed to generate {TASK_ID}") from last_error

        image, noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=task_params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        annotation_value = _annotation_value(rendered)
        prompt_artifacts = _prompt_artifacts(
            selected_query=str(selected_query),
            answer=problem.answer,
            instance_seed=int(instance_seed),
        )
        query_params = {
            "scene_id": SCENE_ID,
            "query_id": str(selected_query),
            "query_id_probabilities": dict(problem.query_probabilities),
            "case_probabilities": dict(problem.case_probabilities),
            "answer_support_probabilities": dict(problem.answer_support_probabilities),
            "source_shape": str(problem.source_shape),
            "target_shape": str(problem.target_shape),
            "source_base_area": int(problem.source_base_area),
            "source_height": int(problem.source_height),
            "source_volume": int(problem.source_volume),
            "target_base_area": int(problem.target_base_area),
            "target_length": int(problem.target_length),
            "target_width": int(problem.target_width),
            "target_height": int(problem.target_height),
            "target_volume": int(problem.target_volume),
            "fill_count": int(problem.fill_count),
            "pour_count": int(problem.pour_count),
            "resulting_height": float(problem.resulting_height),
        }
        query_spec = build_prompt_query_spec(prompt_artifacts=prompt_artifacts, query_id=str(selected_query), params=query_params)
        query_spec["scene_id"] = SCENE_ID
        projected_annotation = {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(annotation_value),
            "pixel_keyed_bbox_map": dict(annotation_value),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "domain": DOMAIN,
                "scene_id": SCENE_ID,
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "type": str(problem.formula_family),
                    "source_shape": str(problem.source_shape),
                    "target_shape": str(problem.target_shape),
                    "source_volume": int(problem.source_volume),
                    "target_volume": int(problem.target_volume),
                    "pour_count": int(problem.pour_count),
                    "annotation_roles": list(ANNOTATION_KEYS),
                },
            },
            "query_spec": query_spec,
            "render_spec": {
                "canvas_size": [int(image.size[0]), int(image.size[1])],
                "coord_space": "pixel",
                "post_image_noise": dict(noise_meta),
                **dict(render_meta),
            },
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "scene_id": SCENE_ID,
                "query_id": str(selected_query),
                "formula_family": str(problem.formula_family),
                "formula": str(problem.formula),
                "answer": json_answer_value(problem.answer),
                "annotation_roles": list(ANNOTATION_KEYS),
                **dict(query_params),
            },
            "witness_symbolic": {"type": "container_volume_transfer", **dict(query_params)},
            "projected_annotation": projected_annotation,
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type=ANSWER_GT_TYPE, value=json_answer_value(problem.answer)),
            annotation_gt=TypedValue(type="keyed_bbox_map", value=dict(annotation_value)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(selected_query),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GeometryContainerVolumeTransferTargetCapacityValueTask"]
