"""Circle-theorem value task over composite measurement labeled circle diagrams."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.support_sampling import resolve_integer_choice
from ...shared.text_rendering import (
    draw_text_centered,
    load_font,
    resolve_text_label_center,
)
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.background_defaults import load_geometry_background_defaults
from ..shared.complexity import build_geometry_circle_theorem_complexity
from ..shared.fixed_query_task import (
    FixedGeometryQueryTaskMixin,
    MultiFixedGeometryQueryTaskMixin,
)
from ..shared.noise_defaults import load_geometry_noise_defaults
from ..shared.render_variation import sample_int_render_param
from ..shared.shape_style import (
    extract_background_anchor_colors,
    sample_geometry_shape_style,
)

from .theorem_common import (
    Point,
    BBox,
    TASK_ID,
    SUPPORTED_QUERY_IDS,
    _build_keyed_point_prompt_examples,
    _DIAMETER_SUPPORT,
    _TANGENT_SECANT_SUPPORT,
    _SECANT_SECANT_SUPPORT,
    _SECANT_SECANT_VARIABLE_SUPPORT,
    _INTERSECTING_CHORDS_ARC_SUPPORT,
    _MULTI_STEP_ANGLE_SUPPORT,
    _INSCRIBED_ANGLE_SUPPORT,
    _CENTRAL_ANGLE_SUPPORT,
    _TANGENT_CHORD_ANGLE_SUPPORT,
    _EXTERNAL_SECANT_ANGLE_SUPPORT,
    _CYCLIC_QUADRILATERAL_ANGLE_SUPPORT,
    _ANSWER_SUPPORT_BY_VARIANT,
    _TANGENT_SECANT_TARGET_KINDS,
    _SECANT_SECANT_VARIABLE_TARGET_KINDS,
    _POINT_LABEL_ALPHABET,
    _CENTER_LABEL,
    _TASK_GROUP_DEFAULTS,
    _GEN_DEFAULTS,
    _RENDER_DEFAULTS,
    _PROMPT_DEFAULTS,
    _BACKGROUND_DEFAULTS,
    _POST_IMAGE_NOISE_DEFAULTS,
    _Defaults,
    _ResolvedQuery,
    _RenderedScene,
    _DEFAULTS,
    _text_bbox_for_center,
    _bbox_to_list,
    _circle_from_three_points,
    _sample_point_label_map,
    _visible_segment,
    _visible_angle,
    _visible_arc,
    _line_intersection,
    _angle_degrees_at,
)
from .theorem_builders import (
    _build_scene_payload,
    _resolve_query,
)
from .theorem_rendering import _render_base_scene


class GeometryCircleTheoremValueTask:
    """Solve one integer value from a labeled circle-theorem diagram."""

    task_id = TASK_ID
    domain = "geometry"
    task_group = "circle"
    scene_id = "circle_theorem"
    public_scene_id = "circle_theorem"

    def generate(
        self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int
    ) -> TaskOutput:
        query = _resolve_query(int(instance_seed), params=params)
        rng = spawn_rng(int(instance_seed), f"{self.task_id}.scene")
        last_error: Exception | None = None
        rendered_scene: _RenderedScene | None = None
        selected_scene_payload: Dict[str, Any] | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                scene_payload = _build_scene_payload(rng, query=query)
                rendered_scene = _render_base_scene(
                    rng=rng,
                    instance_seed=int(instance_seed),
                    params=params,
                    point_model=scene_payload["point_model"],
                    circle_center=scene_payload["circle_center"],
                    circle_radius=float(scene_payload["circle_radius"]),
                    segments=scene_payload["segments"],
                    measurement_specs=scene_payload["measurement_specs"],
                    support_measurement_tokens=scene_payload[
                        "support_measurement_tokens"
                    ],
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
            raise RuntimeError(
                f"failed to generate {self.task_id} instance"
            ) from last_error

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
            context=f"prompt defaults for {self.task_id}",
        )
        annotation_keyed_points = {
            str(label): [
                round(float(rendered_scene.point_pixels[str(label)][0]), 3),
                round(float(rendered_scene.point_pixels[str(label)][1]), 3),
            ]
            for label in rendered_scene.annotation_point_labels
        }
        annotation_points = [list(point) for point in annotation_keyed_points.values()]
        annotation_point_keys = ", ".join(
            f'"{label}"' for label in rendered_scene.annotation_point_labels
        )
        annotation_hint = str(prompt_defaults["annotation_hint_circle_points"]).format(
            annotation_point_keys=annotation_point_keys
        )
        json_example, json_example_answer_only = _build_keyed_point_prompt_examples(
            annotation_point_labels=rendered_scene.annotation_point_labels
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(
                    prompt_defaults["json_output_contract_answer_only"]
                ),
                "annotation_hint": str(annotation_hint),
                "answer_hint": str(prompt_defaults["answer_hint_integer"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                **dict(selected_scene_payload.get("prompt_slots", {})),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(rendered_scene.answer_value))
        annotation_gt = TypedValue(
            type="keyed_point_map", value=dict(annotation_keyed_points)
        )
        query_params = {
            "query_id": str(query.query_id),
            "query_id_probabilities": dict(query.query_id_probabilities),
            "target_answer": int(query.target_answer),
            "target_answer_probabilities": dict(query.target_answer_probabilities),
        }
        if query.tangent_secant_target_kind is not None:
            query_params["tangent_secant_target_kind"] = str(
                query.tangent_secant_target_kind
            )
            query_params["tangent_secant_target_kind_probabilities"] = dict(
                query.tangent_secant_target_kind_probabilities or {}
            )
        if query.secant_secant_variable_target_kind is not None:
            query_params["secant_secant_variable_target_kind"] = str(
                query.secant_secant_variable_target_kind
            )
            query_params["secant_secant_variable_target_kind_probabilities"] = dict(
                query.secant_secant_variable_target_kind_probabilities or {}
            )
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_circle_theorem_value",
                "entities": list(rendered_scene.scene_entities),
                "relations": {
                    "query_id": str(query.query_id),
                    "answer_segment": str(
                        rendered_scene.theorem_trace["answer_segment"]
                    ),
                    "answer_value": int(rendered_scene.answer_value),
                    "theorem": str(rendered_scene.theorem_trace["theorem"]),
                },
            },
            "query_spec": {
                "query_id": str(query.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(
                    prompt_artifacts.prompt_variant_active_key
                ),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "canvas_size": int(rendered_scene.image.size[0]),
                "coord_space": "pixel",
                "background_style": dict(rendered_scene.background_meta),
                "post_image_noise": dict(rendered_scene.post_noise_meta),
                "shape_style": dict(rendered_scene.shape_style),
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
                "query_id": str(query.query_id),
                "query_id_probabilities": dict(query.query_id_probabilities),
                "target_answer": int(query.target_answer),
                "target_answer_probabilities": dict(query.target_answer_probabilities),
                "answer_type": "integer",
                "answer_value": int(rendered_scene.answer_value),
                "annotation_point_labels": list(rendered_scene.annotation_point_labels),
                "support_measurement_tokens": list(
                    rendered_scene.support_measurement_tokens
                ),
                "annotation_values": dict(rendered_scene.annotation_values),
                **dict(rendered_scene.theorem_trace),
            },
            "witness_symbolic": {
                "type": "circle_theorem_construction_points",
                "query_id": str(query.query_id),
                "answer_segment": str(rendered_scene.theorem_trace["answer_segment"]),
                "answer_value": int(rendered_scene.answer_value),
                "annotation_point_labels": list(rendered_scene.annotation_point_labels),
                "support_measurement_tokens": list(
                    rendered_scene.support_measurement_tokens
                ),
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

        complexity = build_geometry_circle_theorem_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            query_id=str(query.query_id),
            annotation_count=len(rendered_scene.token_bboxes),
            answer_value=int(rendered_scene.answer_value),
        )

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=rendered_scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )

@register_task
class GeometryCircleDiameterPerpendicularChordLengthValueTask(
    FixedGeometryQueryTaskMixin,
    GeometryCircleTheoremValueTask,
):
    """Solve a length in a diameter-perpendicular-chord diagram."""

    task_id = "task_geometry__circle_theorem__diameter_perpendicular_chord_length_value"
    fixed_query_id = "diameter_perpendicular_chord_length"
    public_scene_id = "circle_theorem"

@register_task
class GeometryCircleTangentSecantLengthValueTask(
    FixedGeometryQueryTaskMixin,
    GeometryCircleTheoremValueTask,
):
    """Solve a length in a tangent-secant diagram."""

    task_id = "task_geometry__circle_theorem__tangent_secant_length_value"
    fixed_query_id = "tangent_secant_length"
    public_scene_id = "circle_theorem"

@register_task
class GeometryCircleSecantSecantLengthValueTask(
    MultiFixedGeometryQueryTaskMixin,
    GeometryCircleTheoremValueTask,
):
    """Solve a length in a secant-secant diagram."""

    task_id = "task_geometry__circle_theorem__secant_secant_length_value"
    fixed_query_ids = (
        "secant_secant_length",
        "secant_secant_variable_segment_length",
    )
    public_scene_id = "circle_theorem"

@register_task
class GeometryCircleIntersectingChordsArcMeasureValueTask(
    FixedGeometryQueryTaskMixin,
    GeometryCircleTheoremValueTask,
):
    """Solve an arc measure in an intersecting-chords diagram."""

    task_id = "task_geometry__circle_theorem__intersecting_chords_arc_measure_value"
    fixed_query_id = "intersecting_chords_arc_measure"
    public_scene_id = "circle_theorem"

@register_task
class GeometryCircleInscribedAngleFromCentralTask(
    FixedGeometryQueryTaskMixin,
    GeometryCircleTheoremValueTask,
):
    """Solve an inscribed angle from a visible central angle."""

    task_id = "task_geometry__circle_theorem__inscribed_angle_value_inscribed_angle_from_central"
    fixed_query_id = "inscribed_angle_from_central"
    public_scene_id = "circle_theorem"

@register_task
class GeometryCircleCentralAngleFromInscribedTask(
    FixedGeometryQueryTaskMixin,
    GeometryCircleTheoremValueTask,
):
    """Solve a central angle from a visible inscribed angle."""

    task_id = "task_geometry__circle_theorem__inscribed_angle_value_central_angle_from_inscribed"
    fixed_query_id = "central_angle_from_inscribed"
    public_scene_id = "circle_theorem"

@register_task
class GeometryCircleInscribedAngleFromArcTask(
    FixedGeometryQueryTaskMixin,
    GeometryCircleTheoremValueTask,
):
    """Solve an inscribed angle from a visible arc measure."""

    task_id = "task_geometry__circle_theorem__inscribed_angle_value_inscribed_angle_from_arc"
    fixed_query_id = "inscribed_angle_from_arc"
    public_scene_id = "circle_theorem"

@register_task
class GeometryCircleTangentChordAngleFromArcTask(
    FixedGeometryQueryTaskMixin,
    GeometryCircleTheoremValueTask,
):
    """Solve a tangent-chord angle from a visible arc measure."""

    task_id = "task_geometry__circle_theorem__tangent_chord_angle_value_tangent_chord_angle_from_arc"
    fixed_query_id = "tangent_chord_angle_from_arc"
    public_scene_id = "circle_theorem"

@register_task
class GeometryCircleTangentChordAngleFromInscribedTask(
    FixedGeometryQueryTaskMixin,
    GeometryCircleTheoremValueTask,
):
    """Solve a tangent-chord angle from a matching inscribed angle."""

    task_id = "task_geometry__circle_theorem__tangent_chord_angle_value_tangent_chord_angle_from_inscribed"
    fixed_query_id = "tangent_chord_angle_from_inscribed"
    public_scene_id = "circle_theorem"

@register_task
class GeometryCircleMultiStepAngleValueTask(
    FixedGeometryQueryTaskMixin,
    GeometryCircleTheoremValueTask,
):
    """Solve an angle from multiple arc measurements in an intersecting-chords diagram."""

    task_id = "task_geometry__circle_theorem__multi_step_angle_value"
    fixed_query_id = "multi_step_angle_value"
    public_scene_id = "circle_theorem"

@register_task
class GeometryCircleExternalSecantAngleValueTask(
    FixedGeometryQueryTaskMixin,
    GeometryCircleTheoremValueTask,
):
    """Solve an outside angle formed by two secants from intercepted arcs."""

    task_id = "task_geometry__circle_theorem__external_secant_angle_value"
    fixed_query_id = "external_two_secants_angle_from_arcs"
    public_scene_id = "circle_theorem"

@register_task
class GeometryCircleCyclicQuadrilateralAngleValueTask(
    MultiFixedGeometryQueryTaskMixin,
    GeometryCircleTheoremValueTask,
):
    """Solve a cyclic quadrilateral interior or exterior angle."""

    task_id = "task_geometry__circle_theorem__cyclic_quadrilateral_angle_value"
    fixed_query_ids = (
        "opposite_angle_supplement",
        "exterior_angle_from_opposite_interior",
    )
    public_scene_id = "circle_theorem"

__all__ = [
    "GeometryCircleCentralAngleFromInscribedTask",
    "GeometryCircleCyclicQuadrilateralAngleValueTask",
    "GeometryCircleDiameterPerpendicularChordLengthValueTask",
    "GeometryCircleExternalSecantAngleValueTask",
    "GeometryCircleInscribedAngleFromArcTask",
    "GeometryCircleInscribedAngleFromCentralTask",
    "GeometryCircleIntersectingChordsArcMeasureValueTask",
    "GeometryCircleMultiStepAngleValueTask",
    "GeometryCircleSecantSecantLengthValueTask",
    "GeometryCircleTangentChordAngleFromArcTask",
    "GeometryCircleTangentChordAngleFromInscribedTask",
    "GeometryCircleTangentSecantLengthValueTask",
    "GeometryCircleTheoremValueTask",
]
