"""Cylinder wrapped mark position task."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_scene_prompt_variants

from .shared.runtime import (
    POST_IMAGE_NOISE_DEFAULTS,
    SCENE_ID,
    _ResolvedProblem,
    _RenderedCylinderScene,
    _make_context,
    _projected_annotation,
    _resolve_problem,
    _render_wrapped_mark_scene,
    round1,
)

DOMAIN = "geometry"
TASK_ID = "task_geometry__cylinder_wrap__wrapped_mark_position_label"
QUERY_ID = "wrapped_mark_position_label"
SCENE_VARIANT = "strip_to_rim_position"
PROMPT_FIELD_PREFIX = "wrapped_mark"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
_SCENE_DEFAULTS = get_scene_defaults(DOMAIN, SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS,
    task_id=TASK_ID,
)




def _prompt_artifacts(*, rendered: _RenderedCylinderScene, instance_seed: int) -> tuple[Dict[str, Any], Any]:
    prompt_defaults = required_group_defaults(
        _PROMPT_DEFAULTS,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            f"{PROMPT_FIELD_PREFIX}_object_description",
            f"{PROMPT_FIELD_PREFIX}_annotation_hint",
            f"{PROMPT_FIELD_PREFIX}_answer_hint",
            f"{PROMPT_FIELD_PREFIX}_json_example",
            f"{PROMPT_FIELD_PREFIX}_json_example_answer_only",
        ),
        context=f"prompt defaults for {TASK_ID}",
    )
    prompt_selection = render_scene_prompt_variants(
        domain=DOMAIN,
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=None,
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(prompt_defaults[f"{PROMPT_FIELD_PREFIX}_object_description"]),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(prompt_defaults[f"{PROMPT_FIELD_PREFIX}_annotation_hint"]),
            "answer_hint": str(prompt_defaults[f"{PROMPT_FIELD_PREFIX}_answer_hint"]),
            "json_example": str(prompt_defaults[f"{PROMPT_FIELD_PREFIX}_json_example"]),
            "json_example_answer_only": str(prompt_defaults[f"{PROMPT_FIELD_PREFIX}_json_example_answer_only"]),
        },
        instance_seed=int(instance_seed),
    )
    return dict(prompt_defaults), build_prompt_trace_artifacts(prompt_selection)


def _answer_value_and_gt(rendered: _RenderedCylinderScene) -> tuple[int | float | str, TypedValue]:
    if rendered.answer_type == "number":
        rounded_answer = float(round1(float(rendered.answer)))
        answer_value: int | float | str = rounded_answer
        if abs(rounded_answer - round(rounded_answer)) <= 1e-9:
            answer_value = int(round(rounded_answer))
        return answer_value, TypedValue(type="number", value=answer_value)
    answer_value = str(rendered.answer)
    return answer_value, TypedValue(type="option_letter", value=str(answer_value))


def _trace_payload(
    *,
    problem: _ResolvedProblem,
    rendered: _RenderedCylinderScene,
    prompt_defaults: Mapping[str, Any],
    prompt_artifacts: Any,
    render_meta: Mapping[str, Any],
    noise_meta: Mapping[str, Any],
    image_size: tuple[int, int],
    answer_value: int | float | str,
) -> Dict[str, Any]:
    query_params: Dict[str, Any] = {
        "scene_id": SCENE_ID,
        "scene_variant": SCENE_VARIANT,
        "query_id": QUERY_ID,
        "query_id_probabilities": {QUERY_ID: 1.0},
        **dict(rendered.witness),
    }
    if QUERY_ID == "wrapped_mark_position_label":
        query_params["target_index_probabilities"] = dict(problem.answer_probabilities)
        query_params["option_count_probabilities"] = dict(problem.option_count_probabilities)
    else:
        query_params["target_support_probabilities"] = dict(problem.answer_probabilities)
    return {
        "scene_ir": {
            "scene_kind": "geometry_cylinder_wrap",
            "scene_id": SCENE_ID,
            "entities": [dict(entity) for entity in rendered.scene_entities],
            "relations": {
                "scene_variant": SCENE_VARIANT,
                "query_id": QUERY_ID,
                "answer_value": answer_value,
                "annotation_roles": list(rendered.annotation_roles),
            },
        },
        "query_spec": {
            "scene_id": SCENE_ID,
            "query_id": QUERY_ID,
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": dict(query_params),
        },
        "render_spec": {
            "canvas_size": [int(image_size[0]), int(image_size[1])],
            "coord_space": "pixel",
            "post_image_noise": dict(noise_meta),
            **dict(render_meta),
        },
        "render_map": dict(rendered.render_map),
        "execution_trace": {
            "scene_id": SCENE_ID,
            "scene_variant": SCENE_VARIANT,
            "query_id": QUERY_ID,
            "answer_type": str(rendered.answer_type),
            "answer_value": answer_value,
            "annotation_roles": list(rendered.annotation_roles),
            "reasoning_steps": 2,
            **dict(rendered.witness),
        },
        "witness_symbolic": {
            "type": "cylinder_wrap_measurement",
            "scene_id": SCENE_ID,
            "scene_variant": SCENE_VARIANT,
            "query_id": QUERY_ID,
            "source_witness_type": str(rendered.annotation_type),
            "original_annotation_value": list(rendered.annotation_roles),
            "answer_value": answer_value,
            **dict(rendered.witness),
        },
        "projected_annotation": _projected_annotation(str(rendered.annotation_type), dict(rendered.annotation_value)),
    }


@register_task
class GeometryCylinderWrapWrappedMarkPositionLabelTask:
    """Match a mark on an unwrapped strip to a labeled rim position."""

    task_id = TASK_ID
    domain = DOMAIN
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS
    reasoning_kind = "cylinder_wrap"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        problem = _resolve_problem(
            runtime_key=TASK_ID,
            query_id=QUERY_ID,
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
        )
        rendered: _RenderedCylinderScene | None = None
        render_meta: Dict[str, Any] | None = None
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                ctx, render_meta_attempt = _make_context(
                    instance_seed=int(instance_seed) + int(attempt),
                    params=params,
                    render_defaults=_RENDER_DEFAULTS,
                    runtime_key=TASK_ID,
                )
                rendered = _render_wrapped_mark_scene(ctx, problem)
                render_meta = dict(render_meta_attempt)
                break
            except Exception as exc:
                last_error = exc
                continue
        if rendered is None or render_meta is None:
            raise RuntimeError(f"failed to generate {TASK_ID}") from last_error

        image, noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt_defaults, prompt_artifacts = _prompt_artifacts(rendered=rendered, instance_seed=int(instance_seed))
        answer_value, answer_gt = _answer_value_and_gt(rendered)
        annotation_value = dict(rendered.annotation_value)
        annotation_gt = TypedValue(type=str(rendered.annotation_type), value=dict(annotation_value))
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=_trace_payload(
                problem=problem,
                rendered=rendered,
                prompt_defaults=prompt_defaults,
                prompt_artifacts=prompt_artifacts,
                render_meta=dict(render_meta),
                noise_meta=dict(noise_meta),
                image_size=(int(image.size[0]), int(image.size[1])),
                answer_value=answer_value,
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GeometryCylinderWrapWrappedMarkPositionLabelTask"]
