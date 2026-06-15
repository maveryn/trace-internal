"""Neutral rendering and trace preparation for cone-net tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from PIL import Image

from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.geometry.shared.annotation_values import PixelAnnotationArtifacts
from trace.tasks.shared.fixed_query import geometry_selected_probability_map
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.annotations import cone_net_annotation
from .shared.defaults import POST_IMAGE_NOISE_DEFAULTS, SCENE_ID, SCENE_KIND, SCENE_VARIANT, load_cone_net_task_defaults
from .shared.prompts import cone_net_prompt_artifacts
from .shared.rendering import render_cone_net_with_retries
from .shared.state import ConeNetDiagramSpec, RenderedConeNetScene


def _cone_net_trace_payload(
    *,
    rendered: RenderedConeNetScene,
    annotation_artifacts: PixelAnnotationArtifacts,
    prompt_artifacts: Any,
    selected_query: str,
    query_probabilities: Mapping[str, float],
    internal_prompt_key: str,
    answer_value: float,
    case_index: int,
    target_support_probabilities: Mapping[str, float],
    render_meta: Mapping[str, Any],
    noise_meta: Mapping[str, Any],
    image_size: tuple[int, int],
) -> dict[str, Any]:
    """Build trace sections using identity already selected by a public task."""

    annotation_roles = [str(role) for role in rendered.annotation_roles]
    measurement_fields = dict(rendered.measurements)
    query_params = {
        "scene_id": SCENE_ID,
        "query_id": str(selected_query),
        "internal_query_id": str(internal_prompt_key),
        "query_id_probabilities": dict(query_probabilities),
        "case_index": int(case_index),
        "target_support_probabilities": dict(target_support_probabilities),
        **dict(measurement_fields),
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
            "entities": [dict(entity) for entity in rendered.scene_entities],
            "relations": {
                "query_id": str(selected_query),
                "internal_query_id": str(internal_prompt_key),
                "scene_variant": SCENE_VARIANT,
                "answer_value": float(answer_value),
                "annotation_roles": list(annotation_roles),
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
            "scene_variant": SCENE_VARIANT,
            "query_id": str(selected_query),
            "internal_query_id": str(internal_prompt_key),
            "query_id_probabilities": dict(query_probabilities),
            "answer_type": "number",
            "answer_value": float(answer_value),
            "answer_rounding": "nearest_tenth",
            "annotation_roles": list(annotation_roles),
            "reasoning_steps": int(measurement_fields.get("reasoning_steps", 1)),
            **dict(measurement_fields),
        },
        "witness_symbolic": {
            "type": "cone_sector_net_formula",
            "scene_id": SCENE_ID,
            "query_id": str(selected_query),
            "internal_query_id": str(internal_prompt_key),
            "answer_value": float(answer_value),
            "source_witness_type": annotation_artifacts.annotation_type,
            "original_annotation_value": annotation_artifacts.value,
            **dict(measurement_fields),
        },
        "projected_annotation": dict(annotation_artifacts.projected_annotation),
    }


@dataclass(frozen=True)
class ConeNetTaskParts:
    """Prepared non-verifier output fields for one task-owned objective."""

    prompt: str
    prompt_variants: dict[str, str]
    image: Image.Image
    annotation_artifacts: PixelAnnotationArtifacts
    trace_payload: dict[str, Any]
    task_versions: dict[str, str]
    scene_id: str


def prepare_cone_net_task_parts(
    *,
    public_identifier: str,
    internal_prompt_key: str,
    selected_query: str,
    query_probabilities: Mapping[str, float],
    spec: ConeNetDiagramSpec,
    case_index: int,
    support_values: tuple[float, ...],
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> ConeNetTaskParts:
    """Prepare shared visual artifacts after the public task has bound its answer."""

    render_defaults, prompt_defaults = load_cone_net_task_defaults(str(public_identifier))
    rendered, render_meta = render_cone_net_with_retries(
        spec=spec,
        instance_seed=int(instance_seed),
        params=params,
        render_defaults=render_defaults,
        max_attempts=int(max_attempts),
        random_namespace=f"{public_identifier}.render",
    )
    image, noise_meta = apply_post_image_noise(
        rendered.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    annotation_artifacts = cone_net_annotation(rendered)
    _prompt_defaults, prompt_artifacts = cone_net_prompt_artifacts(
        prompt_defaults=prompt_defaults,
        prompt_key=str(internal_prompt_key),
        annotation_keys=tuple(annotation_artifacts.value.keys()),
        answer_value=float(spec.answer),
        instance_seed=int(instance_seed),
    )
    support_probabilities = geometry_selected_probability_map(
        support_values,
        float(spec.answer),
        is_selected=lambda value, selected: float(value) == float(selected),
    )
    trace_payload = _cone_net_trace_payload(
        rendered=rendered,
        annotation_artifacts=annotation_artifacts,
        prompt_artifacts=prompt_artifacts,
        selected_query=str(selected_query),
        query_probabilities=query_probabilities,
        internal_prompt_key=str(internal_prompt_key),
        answer_value=float(spec.answer),
        case_index=int(case_index),
        target_support_probabilities=support_probabilities,
        render_meta=render_meta,
        noise_meta=noise_meta,
        image_size=(int(image.size[0]), int(image.size[1])),
    )
    return ConeNetTaskParts(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        image=image,
        annotation_artifacts=annotation_artifacts,
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
    )


__all__ = ["ConeNetTaskParts", "prepare_cone_net_task_parts"]
