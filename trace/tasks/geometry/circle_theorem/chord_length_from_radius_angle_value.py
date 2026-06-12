"""Chord-length circle theorem task with radius and angle annotations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_scene_generation_rendering_prompt_defaults,
)

SCENE_ID = "circle_theorem"
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ...shared.prompt_json_example import dump_prompt_json_examples
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from trace.tasks.shared.fixed_query import geometry_probability_map as _probability_map
from .shared.circle.theorem_builders import _circle_point
from .shared.circle.theorem_common import (
    _CENTER_LABEL,
    _sample_point_label_map,
    _visible_angle,
    _visible_segment,
)
from .shared.circle.theorem_rendering import _render_base_scene


Point = Tuple[float, float]

TASK_ID = "task_geometry__circle_theorem__chord_length_from_radius_angle_value"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "chord_length_from_radius_and_central_angle",
    "chord_length_from_radius_and_inscribed_angle",
)
_DEFAULT_RADIUS_SUPPORT: Tuple[int, ...] = tuple(range(6, 17))
_DEFAULT_CENTRAL_ANGLE_SUPPORT: Tuple[int, ...] = (60, 90, 120, 150)
_DEFAULT_INSCRIBED_ANGLE_SUPPORT: Tuple[int, ...] = (30, 45, 60, 75)

_SCENE_DEFAULTS = get_scene_defaults("geometry", "circle_theorem")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = (
    split_scene_generation_rendering_prompt_defaults(_SCENE_DEFAULTS, task_id=TASK_ID)
)


@dataclass(frozen=True)
class _ResolvedChordLengthQuery:
    query_id: str
    radius_value: int
    angle_degrees: int
    central_angle_degrees: int
    answer_value: float
    query_id_probabilities: Dict[str, float]
    radius_probabilities: Dict[str, float]
    angle_probabilities: Dict[str, float]


def _round1(value: float) -> float:
    return float(round(float(value) + 1e-9, 1))


def _format_decimal(value: float) -> str:
    return f"{float(value):.1f}"


def _support_from_defaults(key: str, fallback: Sequence[int]) -> Tuple[int, ...]:
    raw_support = _GEN_DEFAULTS.get(str(key), tuple(fallback))
    support = tuple(int(value) for value in raw_support)
    if not support:
        raise ValueError(f"{key} must contain at least one value")
    return support


def _select_int(
    *,
    rng,
    params: Mapping[str, Any],
    explicit_keys: Sequence[str],
    support: Sequence[int],
) -> Tuple[int, Dict[str, float]]:
    values = tuple(int(value) for value in support)
    for key in explicit_keys:
        if key in params:
            selected = int(params[str(key)])
            if selected not in set(values):
                raise ValueError(f"{key}={selected!r} is not in support {values!r}")
            return selected, {str(selected): 1.0}
    return int(rng.choice(values)), _probability_map(values)


def _resolve_query(
    instance_seed: int, *, params: Mapping[str, Any]
) -> _ResolvedChordLengthQuery:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query")
    query_id, query_probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
    )
    query_id = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(query_id),
        variant_probabilities=query_probabilities,
        supported_variants=SUPPORTED_QUERY_IDS,
        balance_flag_key="balanced_query_id_sampling",
        explicit_key="query_id",
        weights_key="query_id_weights",
        sampling_namespace=f"{TASK_ID}.query_id",
    )
    radius, radius_probabilities = _select_int(
        rng=rng,
        params=params,
        explicit_keys=("radius_value", "radius"),
        support=_support_from_defaults("radius_support", _DEFAULT_RADIUS_SUPPORT),
    )
    if str(query_id) == "chord_length_from_radius_and_central_angle":
        angle_support = _support_from_defaults(
            "central_angle_support", _DEFAULT_CENTRAL_ANGLE_SUPPORT
        )
    else:
        angle_support = _support_from_defaults(
            "inscribed_angle_support", _DEFAULT_INSCRIBED_ANGLE_SUPPORT
        )
    angle, angle_probabilities = _select_int(
        rng=rng,
        params=params,
        explicit_keys=("angle_degrees", "angle_value"),
        support=angle_support,
    )
    central_angle = (
        int(angle)
        if str(query_id) == "chord_length_from_radius_and_central_angle"
        else int(2 * angle)
    )
    if not (20 <= int(central_angle) <= 170):
        raise ValueError(f"unsupported central angle for chord task: {central_angle}")
    answer = _round1(
        2.0 * float(radius) * math.sin(math.radians(float(central_angle) / 2.0))
    )
    return _ResolvedChordLengthQuery(
        query_id=str(query_id),
        radius_value=int(radius),
        angle_degrees=int(angle),
        central_angle_degrees=int(central_angle),
        answer_value=float(answer),
        query_id_probabilities=dict(query_probabilities),
        radius_probabilities=dict(radius_probabilities),
        angle_probabilities=dict(angle_probabilities),
    )


def _build_keyed_role_prompt_examples(
    *, annotation_keys: Sequence[str], answer_value: float
) -> Tuple[str, str]:
    example_points = {
        str(key): [128 + (43 * index), 214 + (29 * index)]
        for index, key in enumerate(annotation_keys)
    }
    return dump_prompt_json_examples(
        annotation=example_points,
        answer=_round1(float(answer_value)),
        ensure_ascii=False,
    )


def _chord_payload(rng, *, query: _ResolvedChordLengthQuery) -> Dict[str, Any]:
    radius = float(query.radius_value)
    central_angle = int(query.central_angle_degrees)
    rotation = float(rng.choice((18, 34, 50, 66, 82, 98, 114, 130, 146)))
    center = (0.0, 0.0)
    canonical_points: Dict[str, Point] = {
        "O": center,
        "A": _circle_point(radius, rotation - (0.5 * central_angle)),
        "B": _circle_point(radius, rotation + (0.5 * central_angle)),
    }
    is_inscribed = str(query.query_id) == "chord_length_from_radius_and_inscribed_angle"
    if is_inscribed:
        c_offset = float(rng.choice((-36, -24, -12, 12, 24, 36)))
        canonical_points["C"] = _circle_point(radius, rotation + 180.0 + c_offset)

    canonical_labels = ("O", "A", "B", "C") if is_inscribed else ("O", "A", "B")
    label_map = _sample_point_label_map(rng, canonical_labels)
    point_model = {label_map[key]: value for key, value in canonical_points.items()}

    radius_segment = _visible_segment(label_map, "O", "A")
    chord_segment = _visible_segment(label_map, "A", "B")
    answer_token = f"{chord_segment}=?"
    radius_token = f"{radius_segment}={int(query.radius_value)}"
    segments = {
        "OA": (label_map["O"], label_map["A"]),
        "AB": (label_map["A"], label_map["B"]),
    }
    measurement_specs = (
        (radius_token, "OA", -1.0),
        (answer_token, "AB", 1.0),
    )
    if is_inscribed:
        angle_name = _visible_angle(label_map, "A", "C", "B")
        angle_token = f"{angle_name}={int(query.angle_degrees)}°"
        segments.update(
            {
                "CA": (label_map["C"], label_map["A"]),
                "CB": (label_map["C"], label_map["B"]),
            }
        )
        angle_marker_specs = (
            {
                "token": angle_token,
                "vertex": label_map["C"],
                "arm0": label_map["A"],
                "arm1": label_map["B"],
                "radius_px": 42.0,
            },
        )
        annotation_role_to_label = {
            "center": label_map["O"],
            "chord_endpoint_1": label_map["A"],
            "chord_endpoint_2": label_map["B"],
            "inscribed_angle_vertex": label_map["C"],
        }
        angle_prompt_slot = "inscribed angle"
    else:
        angle_name = _visible_angle(label_map, "A", "O", "B")
        angle_token = f"{angle_name}={int(query.angle_degrees)}°"
        segments["OB"] = (label_map["O"], label_map["B"])
        angle_marker_specs = (
            {
                "token": angle_token,
                "vertex": label_map["O"],
                "arm0": label_map["A"],
                "arm1": label_map["B"],
                "radius_px": 48.0,
            },
        )
        annotation_role_to_label = {
            "center": label_map["O"],
            "chord_endpoint_1": label_map["A"],
            "chord_endpoint_2": label_map["B"],
        }
        angle_prompt_slot = "central angle"

    theorem_trace = {
        "theorem": "chord_length_from_radius_angle",
        "label_map": dict(label_map),
        "canonical_answer_segment": "AB",
        "answer_segment": str(chord_segment),
        "answer_value": float(query.answer_value),
        "answer_rounding": "nearest_tenth",
        "radius_value": int(query.radius_value),
        "visible_radius_segment": str(radius_segment),
        "angle_degrees": int(query.angle_degrees),
        "central_angle_degrees": int(query.central_angle_degrees),
        "visible_angle": str(angle_name),
        "formula": "chord=2*r*sin(theta/2)",
        "annotation_role_to_label": dict(annotation_role_to_label),
        "distractor_tokens": [],
    }
    return {
        "point_model": point_model,
        "circle_center": center,
        "circle_radius": float(radius),
        "segments": segments,
        "measurement_specs": measurement_specs,
        "angle_marker_specs": angle_marker_specs,
        "circle_arc_specs": tuple(),
        "support_measurement_tokens": (radius_token, angle_token),
        "annotation_point_labels": tuple(annotation_role_to_label.values()),
        "annotation_role_to_label": dict(annotation_role_to_label),
        "annotation_values": {
            str(radius_segment): int(query.radius_value),
            str(angle_name): int(query.angle_degrees),
        },
        "theorem_trace": theorem_trace,
        "prompt_slots": {
            "radius_segment": str(radius_segment),
            "angle_name": str(angle_name),
            "angle_kind": str(angle_prompt_slot),
            "answer_segment": str(chord_segment),
            "chord_segment": str(chord_segment),
        },
    }


@register_task
class GeometryCircleChordLengthFromRadiusAngleValueTask:
    """Compute a chord length from a visible radius and circle angle."""

    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(
        self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int
    ) -> TaskOutput:
        query = _resolve_query(int(instance_seed), params=params)
        rng = spawn_rng(int(instance_seed), f"{self.task_id}.scene")
        rendered_scene = None
        scene_payload: Dict[str, Any] | None = None
        last_error: Exception | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                candidate_payload = _chord_payload(rng, query=query)
                rendered_scene = _render_base_scene(
                    rng=rng,
                    instance_seed=int(instance_seed),
                    params=params,
                    point_model=candidate_payload["point_model"],
                    circle_center=candidate_payload["circle_center"],
                    circle_radius=float(candidate_payload["circle_radius"]),
                    segments=candidate_payload["segments"],
                    measurement_specs=candidate_payload["measurement_specs"],
                    support_measurement_tokens=candidate_payload[
                        "support_measurement_tokens"
                    ],
                    annotation_point_labels=candidate_payload["annotation_point_labels"],
                    annotation_values=candidate_payload["annotation_values"],
                    theorem_trace=candidate_payload["theorem_trace"],
                    angle_marker_specs=candidate_payload["angle_marker_specs"],
                    circle_arc_specs=candidate_payload["circle_arc_specs"],
                )
                scene_payload = dict(candidate_payload)
                break
            except Exception as exc:
                last_error = exc
                continue
        if rendered_scene is None or scene_payload is None:
            raise RuntimeError(f"failed to generate {self.task_id}") from last_error

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "object_description_chord_length",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_number",
                "annotation_hint_chord_length_points",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        annotation_role_to_label = {
            str(key): str(value)
            for key, value in scene_payload["annotation_role_to_label"].items()
        }
        annotation_keyed_points = {
            str(role): [
                round(float(rendered_scene.point_pixels[str(label)][0]), 3),
                round(float(rendered_scene.point_pixels[str(label)][1]), 3),
            ]
            for role, label in annotation_role_to_label.items()
        }
        annotation_keys = tuple(annotation_keyed_points)
        annotation_hint = str(prompt_defaults["annotation_hint_chord_length_points"]).format(
            annotation_keys=", ".join(f'"{key}"' for key in annotation_keys)
        )
        json_example, json_example_answer_only = _build_keyed_role_prompt_examples(
            annotation_keys=annotation_keys,
            answer_value=float(query.answer_value),
        )
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=str(getattr(self, "scene_id", "") or getattr(self, "public_scene_id", "") or globals().get("SCENE_ID", "")),
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(
                    prompt_defaults["object_description_chord_length"]
                ),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(
                    prompt_defaults["json_output_contract_answer_only"]
                ),
                "annotation_hint": str(annotation_hint),
                "answer_hint": str(prompt_defaults["answer_hint_number"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                **dict(scene_payload.get("prompt_slots", {})),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="number", value=float(query.answer_value))
        annotation_gt = TypedValue(
            type="keyed_point_map", value=dict(annotation_keyed_points)
        )
        query_params = {
            "scene_id": SCENE_ID,
            "query_id": str(query.query_id),
            "query_id_probabilities": dict(query.query_id_probabilities),
            "radius_value": int(query.radius_value),
            "radius_probabilities": dict(query.radius_probabilities),
            "angle_degrees": int(query.angle_degrees),
            "angle_probabilities": dict(query.angle_probabilities),
            "central_angle_degrees": int(query.central_angle_degrees),
            "answer_rounding": "nearest_tenth",
            "annotation_role_to_label": dict(annotation_role_to_label),
        }
        annotation_points = [list(point) for point in annotation_keyed_points.values()]
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_circle_theorem_chord_length",
                "scene_id": SCENE_ID,
                "entities": list(rendered_scene.scene_entities),
                "relations": {
                    "query_id": str(query.query_id),
                    "answer_segment": str(
                        rendered_scene.theorem_trace["answer_segment"]
                    ),
                    "answer_value": float(query.answer_value),
                    "theorem": str(rendered_scene.theorem_trace["theorem"]),
                    "annotation_roles": list(annotation_keys),
                },
            },
            "query_spec": {
                "scene_id": SCENE_ID,
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
                "scene_id": SCENE_ID,
                "query_id": str(query.query_id),
                "query_id_probabilities": dict(query.query_id_probabilities),
                "answer_type": "number",
                "answer_value": float(query.answer_value),
                "answer_rounding": "nearest_tenth",
                "support_measurement_tokens": list(
                    rendered_scene.support_measurement_tokens
                ),
                "annotation_roles": list(annotation_keys),
                "annotation_values": dict(rendered_scene.annotation_values),
                **dict(rendered_scene.theorem_trace),
            },
            "witness_symbolic": {
                "type": "circle_theorem_chord_length_formula",
                "scene_id": SCENE_ID,
                "query_id": str(query.query_id),
                "answer_segment": str(rendered_scene.theorem_trace["answer_segment"]),
                "answer_value": float(query.answer_value),
                "source_witness_type": "keyed_point_map",
                "original_annotation_value": dict(annotation_keyed_points),
                "annotation_role_to_label": dict(annotation_role_to_label),
                "support_measurement_tokens": list(
                    rendered_scene.support_measurement_tokens
                ),
            },
            "projected_annotation": {
                "type": "keyed_point_map",
                "keyed_point_map": dict(annotation_keyed_points),
                "pixel_keyed_point_map": dict(annotation_keyed_points),
                "point_set": list(annotation_points),
                "pixel_point_set": list(annotation_points),
            },
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=rendered_scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GeometryCircleChordLengthFromRadiusAngleValueTask"]
