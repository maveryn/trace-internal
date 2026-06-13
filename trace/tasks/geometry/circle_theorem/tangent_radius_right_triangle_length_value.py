"""Tangent-radius right-triangle length task for circle diagrams."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    split_scene_generation_rendering_prompt_defaults,
)

SCENE_ID = "circle_theorem"
from ...shared.prompt_json_example import dump_prompt_json_examples
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from trace.tasks.shared.fixed_query import geometry_probability_map as _probability_map
from ..shared.pythagorean import (
    IntegerRightTriangle,
    integer_right_triangles,
    validate_integer_right_triangle,
)
from ._lifecycle import run_role_keyed_number_circle_theorem_task
from .shared.state import _sample_point_label_map, _visible_angle, _visible_segment


Point = Tuple[float, float]

TASK_ID = "task_geometry__circle_theorem__tangent_radius_right_triangle_length_value"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "radius_from_external_distance_and_angle",
    "tangent_length_from_radius_and_external_distance",
)


def _default_tangent_radius_triples() -> Tuple[Tuple[int, int, int], ...]:
    """Return radius-tangent-external triples with broad default support."""

    triples: list[Tuple[int, int, int]] = []
    used_radii: set[int] = set()
    used_tangent_lengths: set[int] = set()
    used_external_distances: set[int] = set()
    for triangle in integer_right_triangles(
        min_leg=3,
        max_leg=55,
        max_hypotenuse=65,
    ):
        radius = min(int(triangle.leg_a), int(triangle.leg_b))
        tangent = max(int(triangle.leg_a), int(triangle.leg_b))
        external = int(triangle.hypotenuse)
        if radius in used_radii or tangent in used_tangent_lengths:
            continue
        if external in used_external_distances:
            continue
        triples.append((radius, tangent, external))
        used_radii.add(radius)
        used_tangent_lengths.add(tangent)
        used_external_distances.add(external)
    if len(triples) < 12:
        raise RuntimeError("tangent-radius triple pool is unexpectedly small")
    return tuple(triples)


_DEFAULT_TRIPLES: Tuple[Tuple[int, int, int], ...] = _default_tangent_radius_triples()
_DEFAULT_EXTERNAL_DISTANCE_SUPPORT: Tuple[int, ...] = (8, 10, 12, 14, 16, 18, 20)
_DEFAULT_ANGLE_SUPPORT: Tuple[int, ...] = (30, 45, 60)

_SCENE_DEFAULTS = get_scene_defaults("geometry", "circle_theorem")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = (
    split_scene_generation_rendering_prompt_defaults(_SCENE_DEFAULTS, task_id=TASK_ID)
)


@dataclass(frozen=True)
class _ResolvedTangentRadiusQuery:
    query_id: str
    radius_value: float
    tangent_length: float
    external_distance: float
    angle_degrees: int | None
    answer_value: float
    answer_segment_canonical: str
    query_id_probabilities: Dict[str, float]
    support_probabilities: Dict[str, float]


def _round1(value: float) -> float:
    return float(round(float(value) + 1e-9, 1))


def _format_measurement(value: float) -> str:
    rounded = _round1(float(value))
    if math.isclose(rounded, round(rounded), abs_tol=1e-9):
        return str(int(round(rounded)))
    return f"{rounded:.1f}"


def _support_ints(key: str, fallback: Sequence[int]) -> Tuple[int, ...]:
    raw = _GEN_DEFAULTS.get(str(key), tuple(fallback))
    support = tuple(int(value) for value in raw)
    if not support:
        raise ValueError(f"{key} must contain at least one value")
    return support


def _support_triples() -> Tuple[Tuple[int, int, int], ...]:
    raw = _GEN_DEFAULTS.get("tangent_radius_right_triangle_triples", _DEFAULT_TRIPLES)
    triples = tuple(tuple(int(part) for part in triple) for triple in raw)
    if not triples:
        raise ValueError(
            "tangent_radius_right_triangle_triples must contain at least one triple"
        )
    for triple in triples:
        if len(triple) != 3:
            raise ValueError(f"invalid tangent-radius triple: {triple!r}")
        radius, tangent, external = triple
        try:
            validate_integer_right_triangle(
                IntegerRightTriangle(
                    leg_a=int(radius),
                    leg_b=int(tangent),
                    hypotenuse=int(external),
                )
            )
        except ValueError as exc:
            raise ValueError(f"invalid tangent-radius triple: {triple!r}") from exc
    return triples


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
) -> _ResolvedTangentRadiusQuery:
    """Resolve the tangent-radius query into one right-triangle length target."""
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
    if str(query_id) == "tangent_length_from_radius_and_external_distance":
        triples = _support_triples()
        explicit_radius = params.get("radius_value", params.get("radius"))
        explicit_external = params.get(
            "external_distance", params.get("center_distance")
        )
        if explicit_radius is not None and explicit_external is not None:
            radius = float(explicit_radius)
            external = float(explicit_external)
            if external <= radius:
                raise ValueError("external_distance must be larger than radius_value")
            tangent = math.sqrt((external * external) - (radius * radius))
            support_key = "-".join(
                (
                    _format_measurement(radius),
                    _format_measurement(tangent),
                    _format_measurement(external),
                )
            )
            support_probabilities = {support_key: 1.0}
        else:
            radius, tangent, external = triples[int(rng.randrange(len(triples)))]
            support_probabilities = _probability_map(
                tuple(f"{r}-{t}-{d}" for r, t, d in triples)
            )
        return _ResolvedTangentRadiusQuery(
            query_id=str(query_id),
            radius_value=float(radius),
            tangent_length=float(tangent),
            external_distance=float(external),
            angle_degrees=None,
            answer_value=_round1(float(tangent)),
            answer_segment_canonical="PT",
            query_id_probabilities=dict(query_probabilities),
            support_probabilities=dict(support_probabilities),
        )

    external, external_probabilities = _select_int(
        rng=rng,
        params=params,
        explicit_keys=("external_distance", "center_distance"),
        support=_support_ints(
            "tangent_radius_external_distance_support",
            _DEFAULT_EXTERNAL_DISTANCE_SUPPORT,
        ),
    )
    angle, angle_probabilities = _select_int(
        rng=rng,
        params=params,
        explicit_keys=("angle_degrees", "angle_value"),
        support=_support_ints("tangent_radius_angle_support", _DEFAULT_ANGLE_SUPPORT),
    )
    radius = float(external) * math.sin(math.radians(float(angle)))
    tangent = float(external) * math.cos(math.radians(float(angle)))
    support_probabilities = {
        f"external_distance:{external_key}|angle_degrees:{angle_key}": float(
            external_probability
        )
        * float(angle_probability)
        for external_key, external_probability in external_probabilities.items()
        for angle_key, angle_probability in angle_probabilities.items()
    }
    return _ResolvedTangentRadiusQuery(
        query_id=str(query_id),
        radius_value=float(radius),
        tangent_length=float(tangent),
        external_distance=float(external),
        angle_degrees=int(angle),
        answer_value=_round1(radius),
        answer_segment_canonical="OT",
        query_id_probabilities=dict(query_probabilities),
        support_probabilities=dict(support_probabilities),
    )


def _rotate(point: Point, degrees: float) -> Point:
    radians = math.radians(float(degrees))
    c = math.cos(radians)
    s = math.sin(radians)
    x, y = float(point[0]), float(point[1])
    return (float((x * c) - (y * s)), float((x * s) + (y * c)))


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


def _tangent_radius_payload(
    rng, *, query: _ResolvedTangentRadiusQuery
) -> Dict[str, Any]:
    """Construct the tangent-radius diagram with the right angle and role witnesses aligned."""
    radius = float(query.radius_value)

    tangent = float(query.tangent_length)
    side = float(rng.choice((-1, 1)))
    rotation = float(rng.choice((15, 30, 45, 60, 75, 105, 120, 135, 150)))
    canonical_points = {
        "O": _rotate((0.0, 0.0), rotation),
        "T": _rotate((radius, 0.0), rotation),
        "P": _rotate((radius, side * tangent), rotation),
    }
    label_map = _sample_point_label_map(rng, ("O", "P", "T"))
    point_model = {label_map[key]: value for key, value in canonical_points.items()}

    radius_segment = _visible_segment(label_map, "O", "T")
    tangent_segment = _visible_segment(label_map, "P", "T")
    external_segment = _visible_segment(label_map, "O", "P")
    answer_segment = (
        radius_segment
        if query.answer_segment_canonical == "OT"
        else tangent_segment
    )
    support_measurement_tokens = []
    measurement_specs = []
    annotation_values: Dict[str, int] = {}
    if query.query_id == "radius_from_external_distance_and_angle":
        external_token = f"{external_segment}={_format_measurement(query.external_distance)}"
        answer_token = f"{radius_segment}=?"
        angle_name = _visible_angle(label_map, "O", "P", "T")
        angle_token = f"{angle_name}={int(query.angle_degrees or 0)}°"
        support_measurement_tokens.extend((external_token, angle_token))
        measurement_specs.extend(
            (
                (external_token, "OP", 1.0),
                (answer_token, "OT", -1.0),
            )
        )
        angle_marker_specs = (
            {
                "token": angle_token,
                "vertex": label_map["P"],
                "arm0": label_map["O"],
                "arm1": label_map["T"],
                "radius_px": 42.0,
            },
        )
        annotation_values[str(external_segment)] = int(round(query.external_distance))
        annotation_values[str(angle_name)] = int(query.angle_degrees or 0)
    else:
        radius_token = f"{radius_segment}={_format_measurement(query.radius_value)}"
        external_token = f"{external_segment}={_format_measurement(query.external_distance)}"
        answer_token = f"{tangent_segment}=?"
        support_measurement_tokens.extend((radius_token, external_token))
        measurement_specs.extend(
            (
                (radius_token, "OT", 1.0),
                (external_token, "OP", -1.0),
                (answer_token, "PT", 1.0),
            )
        )
        angle_marker_specs = tuple()
        annotation_values[str(radius_segment)] = int(round(query.radius_value))
        annotation_values[str(external_segment)] = int(round(query.external_distance))

    segments = {
        "OT": (label_map["O"], label_map["T"]),
        "PT": (label_map["P"], label_map["T"]),
        "OP": (label_map["O"], label_map["P"]),
    }
    annotation_role_to_label = {
        "center": label_map["O"],
        "tangent_point": label_map["T"],
        "external_point": label_map["P"],
    }
    theorem_trace = {
        "theorem": "tangent_radius_right_triangle",
        "label_map": dict(label_map),
        "canonical_answer_segment": str(query.answer_segment_canonical),
        "answer_segment": str(answer_segment),
        "answer_value": float(query.answer_value),
        "answer_rounding": "nearest_tenth",
        "radius_value": float(query.radius_value),
        "tangent_length": float(query.tangent_length),
        "external_distance": float(query.external_distance),
        "angle_degrees": None
        if query.angle_degrees is None
        else int(query.angle_degrees),
        "right_angle_vertex": str(label_map["T"]),
        "formula": "OT^2+PT^2=OP^2",
        "annotation_role_to_label": dict(annotation_role_to_label),
        "distractor_tokens": [],
    }
    return {
        "point_model": point_model,
        "circle_center": canonical_points["O"],
        "circle_radius": float(radius),
        "segments": segments,
        "measurement_specs": tuple(measurement_specs),
        "support_measurement_tokens": tuple(support_measurement_tokens),
        "annotation_point_labels": tuple(annotation_role_to_label.values()),
        "annotation_role_to_label": dict(annotation_role_to_label),
        "annotation_values": dict(annotation_values),
        "theorem_trace": theorem_trace,
        "angle_marker_specs": angle_marker_specs,
        "right_angle_marker_specs": (
            {
                "vertex": label_map["T"],
                "arm0": label_map["O"],
                "arm1": label_map["P"],
                "size_px": 24.0,
            },
        ),
        "circle_arc_specs": tuple(),
        "prompt_slots": {
            "radius_segment": str(radius_segment),
            "tangent_segment": str(tangent_segment),
            "external_distance_segment": str(external_segment),
            "answer_segment": str(answer_segment),
            "angle_name": ""
            if query.angle_degrees is None
            else str(_visible_angle(label_map, "O", "P", "T")),
        },
    }


@register_task
class GeometryCircleTangentRadiusRightTriangleLengthValueTask:
    """Compute a length in the tangent-radius right triangle."""

    task_id = TASK_ID
    domain = "geometry"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(
        self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int
    ) -> TaskOutput:
        """Generate a tangent-radius instance after binding the numeric query."""

        query = _resolve_query(int(instance_seed), params=params)
        query_params = {
            "query_id_probabilities": dict(query.query_id_probabilities),
            "radius_value": float(query.radius_value),
            "tangent_length": float(query.tangent_length),
            "external_distance": float(query.external_distance),
            "angle_degrees": None
            if query.angle_degrees is None
            else int(query.angle_degrees),
            "support_probabilities": dict(query.support_probabilities),
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
            build_scene_payload=lambda rng: _tangent_radius_payload(rng, query=query),
            render_defaults=_RENDER_DEFAULTS,
            scene_kind="geometry_circle_theorem_tangent_radius_right_triangle",
            witness_type="circle_theorem_tangent_radius_right_triangle",
            object_description_key="object_description_tangent_radius",
            answer_hint_key="answer_hint_tangent_radius_number",
            annotation_hint_key="annotation_hint_tangent_radius_points",
        )


__all__ = ["GeometryCircleTangentRadiusRightTriangleLengthValueTask"]
