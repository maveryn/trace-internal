"""Chord-length circle theorem task with radius and angle annotations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    split_scene_generation_rendering_prompt_defaults,
)

SCENE_ID = "circle_theorem"
from ...shared.prompt_json_example import dump_prompt_json_examples
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from trace.tasks.shared.fixed_query import geometry_probability_map as _probability_map
from ._lifecycle import run_role_keyed_number_circle_theorem_task
from .shared.spatial_primitives import _circle_point
from .shared.state import (
    _sample_point_label_map,
    _visible_angle,
    _visible_segment,
)


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
    """Resolve the chord-length query, supports, and rounded numeric target."""
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
    """Construct the chord/radius diagram while preserving the selected formula witness."""
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
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(
        self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int
    ) -> TaskOutput:
        """Generate a chord-length instance after binding the numeric query."""

        query = _resolve_query(int(instance_seed), params=params)
        query_params = {
            "query_id_probabilities": dict(query.query_id_probabilities),
            "radius_value": int(query.radius_value),
            "radius_probabilities": dict(query.radius_probabilities),
            "angle_degrees": int(query.angle_degrees),
            "angle_probabilities": dict(query.angle_probabilities),
            "central_angle_degrees": int(query.central_angle_degrees),
            "answer_rounding": "nearest_tenth",
        }
        return run_role_keyed_number_circle_theorem_task(
            task_id=TASK_ID,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            query_id=str(query.query_id),
            answer_value=float(query.answer_value),
            query_params=query_params,
            build_scene_payload=lambda rng: _chord_payload(rng, query=query),
            render_defaults=_RENDER_DEFAULTS,
            scene_kind="geometry_circle_theorem_chord_length",
            witness_type="circle_theorem_chord_length_formula",
            object_description_key="object_description_chord_length",
            answer_hint_key="answer_hint_number",
            annotation_hint_key="annotation_hint_chord_length_points",
        )


__all__ = ["GeometryCircleChordLengthFromRadiusAngleValueTask"]
