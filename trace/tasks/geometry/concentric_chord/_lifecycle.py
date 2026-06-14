"""Neutral rendering and trace preparation for concentric-chord tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from PIL import Image

from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.geometry.shared.annotation_values import PixelAnnotationArtifacts
from trace.tasks.shared.fixed_query import geometry_selected_probability_map
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .shared.annotations import concentric_chord_annotation
from .shared.defaults import POST_IMAGE_NOISE_DEFAULTS, SCENE_ID, SCENE_KIND, SCENE_VARIANT, load_concentric_chord_task_defaults
from .shared.prompts import concentric_chord_prompt_artifacts
from .shared.rendering import render_concentric_chord_with_retries
from .shared.state import ConcentricChordDiagramSpec, RenderedConcentricChordScene


def _concentric_chord_trace_payload(
    *,
    rendered: RenderedConcentricChordScene,
    annotation_artifacts: PixelAnnotationArtifacts,
    prompt_artifacts: Any,
    query_id: str,
    query_probabilities: Mapping[str, float],
    internal_query_id: str,
    answer_value: float,
    case_index: int,
    target_support_probabilities: Mapping[str, float],
    render_meta: Mapping[str, Any],
    noise_meta: Mapping[str, Any],
    image_size: tuple[int, int],
    measurement_fields: Mapping[str, Any],
) -> dict[str, Any]:
    """Build trace sections using identity already selected by a public task."""

    annotation_roles = [str(role) for role in rendered.annotation_roles]
    query_params = {
        "scene_id": SCENE_ID,
        "query_id": str(query_id),
        "internal_query_id": str(internal_query_id),
        "query_id_probabilities": dict(query_probabilities),
        "case_index": int(case_index),
        "target_support_probabilities": dict(target_support_probabilities),
        **dict(measurement_fields),
    }
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(query_id),
        params=query_params,
    )
    query_spec["scene_id"] = SCENE_ID
    return {
        "scene_ir": {
            "scene_kind": SCENE_KIND,
            "scene_id": SCENE_ID,
            "entities": [dict(entity) for entity in rendered.scene_entities],
            "relations": {
                "query_id": str(query_id),
                "internal_query_id": str(internal_query_id),
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
            "query_id": str(query_id),
            "internal_query_id": str(internal_query_id),
            "query_id_probabilities": dict(query_probabilities),
            "answer_type": "number",
            "answer_value": float(answer_value),
            "answer_rounding": "nearest_tenth",
            "annotation_roles": list(annotation_roles),
            "reasoning_steps": 1,
            **dict(measurement_fields),
        },
        "witness_symbolic": {
            "type": "concentric_circle_chord_formula",
            "scene_id": SCENE_ID,
            "query_id": str(query_id),
            "internal_query_id": str(internal_query_id),
            "answer_value": float(answer_value),
            "source_witness_type": annotation_artifacts.annotation_type,
            "original_annotation_value": annotation_artifacts.value,
            **dict(measurement_fields),
        },
        "projected_annotation": dict(annotation_artifacts.projected_annotation),
    }


@dataclass(frozen=True)
class ConcentricChordTaskParts:
    """Prepared non-verifier output fields for one task-owned objective."""

    prompt: str
    prompt_variants: dict[str, str]
    image: Image.Image
    annotation_artifacts: PixelAnnotationArtifacts
    trace_payload: dict[str, Any]
    task_versions: dict[str, str]
    scene_id: str


def prepare_concentric_chord_task_parts(
    *,
    task_id: str,
    internal_query_id: str,
    selected_query: str,
    query_probabilities: Mapping[str, float],
    spec: ConcentricChordDiagramSpec,
    case_index: int,
    support_values: tuple[int, ...],
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> ConcentricChordTaskParts:
    """Prepare shared visual artifacts after the public task has bound its answer."""

    render_defaults, prompt_defaults = load_concentric_chord_task_defaults(str(task_id))
    rendered, render_meta = render_concentric_chord_with_retries(
        spec=spec,
        instance_seed=int(instance_seed),
        params=params,
        render_defaults=render_defaults,
        max_attempts=int(max_attempts),
        random_namespace=f"{task_id}.render",
    )
    image, noise_meta = apply_post_image_noise(
        rendered.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    _prompt_defaults, prompt_artifacts = concentric_chord_prompt_artifacts(
        prompt_defaults=prompt_defaults,
        prompt_query_key=str(internal_query_id),
        instance_seed=int(instance_seed),
    )
    annotation_artifacts = concentric_chord_annotation(rendered)
    support_probabilities = geometry_selected_probability_map(
        support_values,
        float(spec.answer),
        is_selected=lambda value, selected: float(value) == float(selected),
    )
    measurement_fields = {
        "formula_family": "concentric_circle_tangent_chord",
        "unknown_measure": str(spec.unknown_measure),
        "outer_radius": int(spec.outer_radius),
        "inner_radius": int(spec.inner_radius),
        "half_chord": int(spec.half_chord),
        "chord_length": int(spec.chord_length),
        "pythagorean_relation": "R^2 = r^2 + (c/2)^2",
        "answer_value": float(spec.answer),
    }
    trace_payload = _concentric_chord_trace_payload(
        rendered=rendered,
        annotation_artifacts=annotation_artifacts,
        prompt_artifacts=prompt_artifacts,
        query_id=str(selected_query),
        query_probabilities=query_probabilities,
        internal_query_id=str(internal_query_id),
        answer_value=float(spec.answer),
        case_index=int(case_index),
        target_support_probabilities=support_probabilities,
        render_meta=render_meta,
        noise_meta=noise_meta,
        image_size=(int(image.size[0]), int(image.size[1])),
        measurement_fields=measurement_fields,
    )
    return ConcentricChordTaskParts(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        image=image,
        annotation_artifacts=annotation_artifacts,
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
    )


__all__ = ["ConcentricChordTaskParts", "prepare_concentric_chord_task_parts"]
