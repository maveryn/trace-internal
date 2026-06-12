"""Runtime assembly helpers for circle-theorem public objectives."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, Mapping

from trace.core.seed import spawn_rng
from trace.tasks.shared.config_defaults import required_group_defaults
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_query_spec,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .theorem_builders import _build_scene_payload
from .theorem_common import _PROMPT_DEFAULTS, _RenderedScene, _build_keyed_point_prompt_examples
from .theorem_rendering import _render_base_scene
from .theorem_sampling import _resolve_query


SCENE_ID = "circle_theorem"


@dataclass(frozen=True)
class CircleTheoremComponents:
    """Generated fields that public task files bind into final task records."""

    prompt: str
    prompt_variants: Dict[str, Any]
    answer_value: int
    annotation_keyed_points: Dict[str, list[float]]
    annotation_points: list[list[float]]
    image: Any
    trace_payload: Dict[str, Any]
    annotation_count: int


def generate_circle_theorem_components(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    selected_query: str,
    query_probabilities: Mapping[str, float],
    max_attempts: int,
    generation_namespace: str,
) -> CircleTheoremComponents:
    """Generate one selected circle-theorem query branch."""

    forced_params = dict(params)
    forced_params["query_id"] = str(selected_query)
    query = _resolve_query(int(instance_seed), params=forced_params)
    query = replace(query, query_id_probabilities=dict(query_probabilities))
    rng = spawn_rng(int(instance_seed), f"{generation_namespace}.scene")

    last_error: Exception | None = None
    rendered_scene: _RenderedScene | None = None
    selected_scene_payload: Dict[str, Any] | None = None
    for _ in range(max(1, int(max_attempts))):
        try:
            scene_payload = _build_scene_payload(rng, query=query)
            rendered_scene = _render_base_scene(
                rng=rng,
                instance_seed=int(instance_seed),
                params=forced_params,
                point_model=scene_payload["point_model"],
                circle_center=scene_payload["circle_center"],
                circle_radius=float(scene_payload["circle_radius"]),
                segments=scene_payload["segments"],
                measurement_specs=scene_payload["measurement_specs"],
                support_measurement_tokens=scene_payload["support_measurement_tokens"],
                annotation_point_labels=scene_payload["annotation_point_labels"],
                annotation_values=scene_payload["annotation_values"],
                theorem_trace=scene_payload["theorem_trace"],
                angle_marker_specs=scene_payload.get("angle_marker_specs"),
                circle_arc_specs=scene_payload.get("circle_arc_specs"),
            )
            selected_scene_payload = dict(scene_payload)
            break
        except Exception as exc:
            last_error = exc
            continue
    if rendered_scene is None or selected_scene_payload is None:
        raise RuntimeError("failed to generate circle theorem instance") from last_error

    prompt_defaults = required_group_defaults(
        _PROMPT_DEFAULTS,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "object_description",
            "json_output_contract",
            "json_output_contract_answer_only",
            "answer_hint_integer",
            "annotation_hint_circle_points",
        ),
        context="circle theorem prompt defaults",
    )
    annotation_keyed_points = {
        str(label): [
            round(float(rendered_scene.point_pixels[str(label)][0]), 3),
            round(float(rendered_scene.point_pixels[str(label)][1]), 3),
        ]
        for label in rendered_scene.annotation_point_labels
    }
    annotation_points = [list(point) for point in annotation_keyed_points.values()]
    annotation_point_keys = ", ".join(f'"{label}"' for label in rendered_scene.annotation_point_labels)
    annotation_hint = str(prompt_defaults["annotation_hint_circle_points"]).format(
        annotation_point_keys=annotation_point_keys
    )
    json_example, json_example_answer_only = _build_keyed_point_prompt_examples(
        annotation_point_labels=rendered_scene.annotation_point_labels
    )
    prompt_selection = render_scene_prompt_variants(
        domain="geometry",
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(query.query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(prompt_defaults["object_description"]),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(annotation_hint),
            "answer_hint": str(prompt_defaults["answer_hint_integer"]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
            **dict(selected_scene_payload.get("prompt_slots", {})),
        },
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

    query_params: Dict[str, Any] = {
        "query_id": str(query.query_id),
        "query_id_probabilities": dict(query.query_id_probabilities),
        "target_answer": int(query.target_answer),
        "target_answer_probabilities": dict(query.target_answer_probabilities),
    }
    if query.tangent_secant_target_kind is not None:
        query_params["tangent_secant_target_kind"] = str(query.tangent_secant_target_kind)
        query_params["tangent_secant_target_kind_probabilities"] = dict(
            query.tangent_secant_target_kind_probabilities or {}
        )
    if query.secant_secant_variable_target_kind is not None:
        query_params["secant_secant_variable_target_kind"] = str(query.secant_secant_variable_target_kind)
        query_params["secant_secant_variable_target_kind_probabilities"] = dict(
            query.secant_secant_variable_target_kind_probabilities or {}
        )
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(query.query_id),
        params=query_params,
    )
    query_spec["scene_id"] = SCENE_ID
    trace_payload: Dict[str, Any] = {
        "scene_ir": {
            "scene_id": SCENE_ID,
            "scene_kind": "geometry_circle_theorem_value",
            "entities": list(rendered_scene.scene_entities),
            "relations": {
                "query_id": str(query.query_id),
                "answer_segment": str(rendered_scene.theorem_trace["answer_segment"]),
                "answer_value": int(rendered_scene.answer_value),
                "theorem": str(rendered_scene.theorem_trace["theorem"]),
            },
        },
        "query_spec": query_spec,
        "render_spec": {
            "scene_id": SCENE_ID,
            "query_id": str(query.query_id),
            "canvas_size": int(rendered_scene.image.size[0]),
            "coord_space": "pixel",
            "background_style": dict(rendered_scene.background_meta),
            "post_image_noise": dict(rendered_scene.post_noise_meta),
            "shape_style": dict(rendered_scene.shape_style),
            "prompt": {
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            },
            **dict(rendered_scene.render_params),
        },
        "render_map": {
            "point_pixels": dict(rendered_scene.point_pixels),
            "point_label_bboxes": dict(rendered_scene.point_label_bboxes),
            "point_model": dict(rendered_scene.point_model),
            "segment_pixels": dict(rendered_scene.segment_pixels),
            "circle_center_pixel": list(rendered_scene.circle_center_pixel),
            "circle_center_model": list(rendered_scene.circle_center_model),
            "circle_radius_px": float(rendered_scene.circle_radius_px),
            "circle_radius_model": float(rendered_scene.circle_radius_model),
            "measurement_token_bboxes": dict(rendered_scene.token_bboxes),
            "coord_space": "pixel",
        },
        "execution_trace": {
            "scene_id": SCENE_ID,
            "query_id": str(query.query_id),
            "query_id_probabilities": dict(query.query_id_probabilities),
            "target_answer": int(query.target_answer),
            "target_answer_probabilities": dict(query.target_answer_probabilities),
            "answer_type": "integer",
            "answer_value": int(rendered_scene.answer_value),
            "annotation_point_labels": list(rendered_scene.annotation_point_labels),
            "support_measurement_tokens": list(rendered_scene.support_measurement_tokens),
            "annotation_values": dict(rendered_scene.annotation_values),
            **dict(rendered_scene.theorem_trace),
        },
        "witness_symbolic": {
            "type": "circle_theorem_construction_points",
            "scene_id": SCENE_ID,
            "query_id": str(query.query_id),
            "answer_segment": str(rendered_scene.theorem_trace["answer_segment"]),
            "answer_value": int(rendered_scene.answer_value),
            "annotation_point_labels": list(rendered_scene.annotation_point_labels),
            "support_measurement_tokens": list(rendered_scene.support_measurement_tokens),
            "source_witness_type": "keyed_point_map",
            "original_annotation_value": list(rendered_scene.annotation_point_labels),
            "annotation_values": dict(rendered_scene.annotation_values),
        },
        "projected_annotation": {
            "type": "keyed_point_map",
            "keyed_point_map": dict(annotation_keyed_points),
            "pixel_keyed_point_map": dict(annotation_keyed_points),
            "point_set": list(annotation_points),
            "pixel_point_set": list(annotation_points),
        },
    }
    return CircleTheoremComponents(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        answer_value=int(rendered_scene.answer_value),
        annotation_keyed_points=dict(annotation_keyed_points),
        annotation_points=list(annotation_points),
        image=rendered_scene.image,
        trace_payload=trace_payload,
        annotation_count=len(rendered_scene.token_bboxes),
    )


__all__ = ["CircleTheoremComponents", "SCENE_ID", "generate_circle_theorem_components"]
