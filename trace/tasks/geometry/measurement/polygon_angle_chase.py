"""Polygon angle-chase measurement tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.prompt_json_example import dump_prompt_json_examples
from ...shared.text_legibility import draw_text_traced
from ...shared.text_rendering import load_font
from ..shared.complexity import (
    build_geometry_measurement_complexity,
    normalize_linear,
)
from ..shared.diagram_style import (
    geometry_diagram_style_metadata,
    prepare_geometry_diagram_style_and_background,
)
from ..shared.fixed_query_task import (
    geometry_selected_probability_map as _probability_map,
    select_indexed_geometry_query_id,
)
from ..shared.measurement_rendering import bbox_from_points, pad_bbox
from ..shared.metadata_serialization import geometry_json_ready
from ..shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS
from ..shared.scene_transform import LazySceneTransform
from ..shared.vector2d import add_scaled as _add, mul as _scale, sub as _sub, unit as _unit

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

SCENE_ID = "polygon_angle_chase"
TASK_GROUP = "measurement"
PROMPT_BUNDLE_ID = "geometry_polygon_angle_chase_v0"
TASK_ID = "task_geometry__polygon_angle_chase__polygon_interior_angle_value"
PARALLEL_TASK_ID = "task_geometry__polygon_angle_chase__parallel_line_angle_value"
SYMMETRY_TASK_ID = "task_geometry__polygon_angle_chase__symmetry_angle_value"
DEGREE_SYMBOL = chr(176)

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", TASK_GROUP)
_QUERY_SIDE_COUNTS: Dict[str, int] = {
    "triangle_interior_angle": 3,
    "quadrilateral_interior_angle": 4,
    "pentagon_interior_angle": 5,
    "hexagon_interior_angle": 6,
}
_PARALLEL_QUERY_IDS: Tuple[str, ...] = ("single_transversal_chain", "two_transversal_angle_sum")
_SINGLE_TRANSVERSAL_RELATIONS: Tuple[str, ...] = ("corresponding_same", "supplementary")
_SYMMETRY_QUERY_IDS: Tuple[str, ...] = (
    "rectangle_diagonal_angle",
    "reflection_axis_angle",
    "isosceles_base_angle_chain",
)
_ISOSCELES_TARGET_ROLES: Tuple[str, ...] = ("base_angle", "apex_angle")
_LABEL_STYLES: Tuple[str, ...] = ("target_expression_mixed", "all_expression")
_VERTEX_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")


@dataclass(frozen=True)
class _ResolvedPolygonProblem:
    query_id: str
    side_count: int
    target_index: int
    target_angle_name: str
    labels: Tuple[str, ...]
    numeric_angles: Tuple[int, ...]
    display_angle_labels: Tuple[str, ...]
    answer: int
    label_style: str
    expression_vertex_index: int | None
    query_probabilities: Dict[str, float]
    label_style_probabilities: Dict[str, float]
    witness: Dict[str, Any]


@dataclass(frozen=True)
class _ResolvedParallelLineProblem:
    query_id: str
    relation_id: str
    support_angles: Tuple[int, ...]
    answer: int
    target_angle_label: str
    query_probabilities: Dict[str, float]
    relation_probabilities: Dict[str, float]
    witness: Dict[str, Any]


@dataclass(frozen=True)
class _ResolvedSymmetryAngleProblem:
    query_id: str
    relation_id: str
    support_angle: int
    answer: int
    target_angle_label: str
    target_role: str
    query_probabilities: Dict[str, float]
    target_role_probabilities: Dict[str, float]
    witness: Dict[str, Any]


@dataclass
class _RenderContext:
    image: Image.Image
    draw: ImageDraw.ImageDraw
    width: int
    height: int
    line_color: Color
    secondary_color: Color
    label_color: Color
    label_stroke_color: Color
    fill_color: Color
    accent_color: Color
    line_width: int
    label_stroke_width: int
    font: Any
    small_font: Any
    diagram_style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]
    scene_transform: LazySceneTransform


@dataclass(frozen=True)
class _RenderedPolygonScene:
    image: Image.Image
    annotation_keyed_points: Dict[str, Point]
    annotation_roles: Tuple[str, ...]
    point_label_bboxes: Dict[str, BBox]
    angle_arc_bboxes: Dict[str, BBox]
    angle_label_bboxes: Dict[str, BBox]
    vertices: Tuple[Point, ...]


@dataclass(frozen=True)
class _RenderedParallelLineScene:
    image: Image.Image
    annotation_keyed_points: Dict[str, Point]
    annotation_roles: Tuple[str, ...]
    angle_arc_bboxes: Dict[str, BBox]
    angle_label_bboxes: Dict[str, BBox]
    line_segments: Dict[str, Tuple[Point, Point]]
    intersections: Dict[str, Point]


@dataclass(frozen=True)
class _RenderedSymmetryAngleScene:
    image: Image.Image
    annotation_keyed_points: Dict[str, Point]
    annotation_roles: Tuple[str, ...]
    angle_arc_bboxes: Dict[str, BBox]
    angle_label_bboxes: Dict[str, BBox]
    construction_segments: Dict[str, Tuple[Point, Point]]
    construction_points: Dict[str, Point]


def _query_angle_sum(side_count: int) -> int:
    return int(side_count - 2) * 180


def _polygon_kind(side_count: int) -> str:
    if int(side_count) == 3:
        return "triangle"
    if int(side_count) == 4:
        return "quadrilateral"
    if int(side_count) == 5:
        return "pentagon"
    if int(side_count) == 6:
        return "hexagon"
    return f"{int(side_count)}-gon"


def _angle_name(labels: Sequence[str], index: int) -> str:
    side_count = len(labels)
    prev_label = str(labels[(int(index) - 1) % side_count])
    vertex_label = str(labels[int(index) % side_count])
    next_label = str(labels[(int(index) + 1) % side_count])
    return f"{prev_label}{vertex_label}{next_label}"


def _format_degrees(value: int) -> str:
    return f"{int(value)}{DEGREE_SYMBOL}"


def _format_linear_expression(coefficient: int, constant: int) -> str:
    coeff = int(coefficient)
    const = int(constant)
    if coeff == 1:
        body = "x"
    elif coeff == -1:
        body = "-x"
    else:
        body = f"{coeff}x"
    if const > 0:
        return f"{body}+{const}"
    if const < 0:
        return f"{body}{const}"
    return body


def _format_angle_expression(coefficient: int, constant: int) -> str:
    expression = _format_linear_expression(coefficient, constant)
    if int(coefficient) == 1 and int(constant) == 0:
        return f"x{DEGREE_SYMBOL}"
    return f"({expression}){DEGREE_SYMBOL}"


def _bbox_overlaps(a: BBox, b: BBox, *, pad: float = 3.0) -> bool:
    ax0, ay0, ax1, ay1 = [float(value) for value in a]
    bx0, by0, bx1, by1 = [float(value) for value in b]
    return not (
        ax1 + float(pad) < bx0
        or bx1 + float(pad) < ax0
        or ay1 + float(pad) < by0
        or by1 + float(pad) < ay0
    )


def _assert_non_overlapping(bboxes: Sequence[BBox]) -> None:
    for left_index, left in enumerate(bboxes):
        for right in bboxes[left_index + 1 :]:
            if _bbox_overlaps(left, right, pad=2.0):
                raise ValueError("polygon angle label layout overlaps")


def _sample_values_for_sum(
    rng: Any,
    *,
    count: int,
    total: int,
    min_value: int,
    max_value: int,
    step: int,
) -> Tuple[int, ...]:
    candidates = tuple(range(int(min_value), int(max_value) + 1, int(step)))
    if int(count) <= 0:
        if int(total) != 0:
            raise ValueError("empty angle value set cannot match nonzero total")
        return ()
    for _ in range(3000):
        values = [int(rng.choice(candidates)) for _ in range(max(0, int(count) - 1))]
        last = int(total) - sum(values)
        if last in candidates:
            values.append(int(last))
            rng.shuffle(values)
            return tuple(int(value) for value in values)
    raise ValueError("failed to sample polygon angle values with requested sum")


def _sample_candidate_values_for_sum(
    rng: Any,
    *,
    count: int,
    total: int,
    candidates: Sequence[int],
) -> Tuple[int, ...]:
    resolved = tuple(int(value) for value in candidates)
    if int(count) <= 0:
        if int(total) != 0:
            raise ValueError("empty value set cannot match nonzero total")
        return ()
    candidate_set = set(resolved)
    for _ in range(6000):
        values = [int(rng.choice(resolved)) for _ in range(max(0, int(count) - 1))]
        last = int(total) - sum(values)
        if last in candidate_set:
            values.append(int(last))
            rng.shuffle(values)
            return tuple(int(value) for value in values)
    raise ValueError("failed to sample candidate values with requested sum")


def _select_label_style(
    *,
    task_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> tuple[str, Dict[str, float]]:
    explicit = params.get("label_style")
    if explicit is not None:
        style = str(explicit)
        if style not in set(_LABEL_STYLES):
            raise ValueError(f"unsupported label_style for {task_id}: {style}")
        return style, _probability_map(_LABEL_STYLES, selected=style)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.label_style",
    )
    style = str(_LABEL_STYLES[int(index) % len(_LABEL_STYLES)])
    return style, _probability_map(_LABEL_STYLES)


def _select_parallel_query_id(
    *,
    task_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> tuple[str, Dict[str, float]]:
    explicit = params.get("query_id")
    if explicit is not None and str(explicit) != "default":
        query_id = str(explicit)
        if query_id not in _PARALLEL_QUERY_IDS:
            raise ValueError(f"unsupported query_id for {task_id}: {query_id}")
        return query_id, _probability_map(_PARALLEL_QUERY_IDS, selected=query_id)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.query_id",
    )
    query_id = str(_PARALLEL_QUERY_IDS[int(index) % len(_PARALLEL_QUERY_IDS)])
    return query_id, _probability_map(_PARALLEL_QUERY_IDS)


def _select_single_transversal_relation(
    *,
    task_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> tuple[str, Dict[str, float]]:
    explicit = params.get("relation_id")
    if explicit is not None:
        relation_id = str(explicit)
        if relation_id not in _SINGLE_TRANSVERSAL_RELATIONS:
            raise ValueError(f"unsupported relation_id for {task_id}: {relation_id}")
        return relation_id, _probability_map(_SINGLE_TRANSVERSAL_RELATIONS, selected=relation_id)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.single_transversal_relation",
    )
    relation_id = str(_SINGLE_TRANSVERSAL_RELATIONS[int(index) % len(_SINGLE_TRANSVERSAL_RELATIONS)])
    return relation_id, _probability_map(_SINGLE_TRANSVERSAL_RELATIONS)


def _select_symmetry_query_id(
    *,
    task_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> tuple[str, Dict[str, float]]:
    explicit = params.get("query_id")
    if explicit is not None and str(explicit) != "default":
        query_id = str(explicit)
        if query_id not in _SYMMETRY_QUERY_IDS:
            raise ValueError(f"unsupported query_id for {task_id}: {query_id}")
        return query_id, _probability_map(_SYMMETRY_QUERY_IDS, selected=query_id)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.query_id",
    )
    query_id = str(_SYMMETRY_QUERY_IDS[int(index) % len(_SYMMETRY_QUERY_IDS)])
    return query_id, _probability_map(_SYMMETRY_QUERY_IDS)


def _select_isosceles_target_role(
    *,
    task_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> tuple[str, Dict[str, float]]:
    explicit = params.get("target_role")
    if explicit is not None:
        role = str(explicit)
        if role not in _ISOSCELES_TARGET_ROLES:
            raise ValueError(f"unsupported target_role for {task_id}: {role}")
        return role, _probability_map(_ISOSCELES_TARGET_ROLES, selected=role)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.isosceles_target_role",
    )
    role = str(_ISOSCELES_TARGET_ROLES[int(index) % len(_ISOSCELES_TARGET_ROLES)])
    return role, _probability_map(_ISOSCELES_TARGET_ROLES)


def _resolve_symmetry_angle_problem(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> _ResolvedSymmetryAngleProblem:
    query_id, query_probabilities = _select_symmetry_query_id(
        task_id=task_id,
        params=params,
        instance_seed=int(instance_seed),
    )
    rng = spawn_rng(int(instance_seed), f"{task_id}.symmetry_problem")
    step = int(group_default(generation_defaults, "angle_step", 5))
    target_label = str(params.get("target_angle_label", "x"))

    if str(query_id) == "rectangle_diagonal_angle":
        known_min = int(group_default(generation_defaults, "rectangle_known_angle_min", 25))
        known_max = int(group_default(generation_defaults, "rectangle_known_angle_max", 65))
        candidates = tuple(range(int(known_min), int(known_max) + 1, int(step)))
        known_angle = int(params.get("support_angle", rng.choice(candidates)))
        if known_angle not in candidates:
            raise ValueError("support_angle is outside rectangle diagonal support")
        answer = 90 - int(known_angle)
        witness = {
            "relation_id": "rectangle_diagonal_complement",
            "support_angle": int(known_angle),
            "answer_angle": int(answer),
            "target_role": "corner_complement",
            "equation": "target_angle = 90 - support_angle",
        }
        return _ResolvedSymmetryAngleProblem(
            query_id=str(query_id),
            relation_id="rectangle_diagonal_complement",
            support_angle=int(known_angle),
            answer=int(answer),
            target_angle_label=str(target_label),
            target_role="corner_complement",
            query_probabilities=dict(query_probabilities),
            target_role_probabilities={"corner_complement": 1.0},
            witness=dict(witness),
        )

    if str(query_id) == "reflection_axis_angle":
        support_min = int(group_default(generation_defaults, "reflection_support_angle_min", 25))
        support_max = int(group_default(generation_defaults, "reflection_support_angle_max", 50))
        candidates = tuple(range(int(support_min), int(support_max) + 1, int(step)))
        support_angle = int(params.get("support_angle", rng.choice(candidates)))
        if support_angle not in candidates:
            raise ValueError("support_angle is outside reflection support")
        answer = 2 * int(support_angle)
        witness = {
            "relation_id": "reflection_axis_angle_double",
            "support_angle": int(support_angle),
            "answer_angle": int(answer),
            "target_role": "reflected_ray_angle",
            "equation": "target_angle = 2 * support_angle",
        }
        return _ResolvedSymmetryAngleProblem(
            query_id=str(query_id),
            relation_id="reflection_axis_angle_double",
            support_angle=int(support_angle),
            answer=int(answer),
            target_angle_label=str(target_label),
            target_role="reflected_ray_angle",
            query_probabilities=dict(query_probabilities),
            target_role_probabilities={"reflected_ray_angle": 1.0},
            witness=dict(witness),
        )

    if str(query_id) == "isosceles_base_angle_chain":
        target_role, target_role_probabilities = _select_isosceles_target_role(
            task_id=task_id,
            params=params,
            instance_seed=int(instance_seed),
        )
        if target_role == "base_angle":
            support_min = int(group_default(generation_defaults, "isosceles_apex_angle_min", 40))
            support_max = int(group_default(generation_defaults, "isosceles_apex_angle_max", 90))
            candidates = tuple(range(int(support_min), int(support_max) + 1, int(step * 2)))
            support_angle = int(params.get("support_angle", rng.choice(candidates)))
            if support_angle not in candidates:
                raise ValueError("support_angle is outside isosceles apex support")
            answer = (180 - int(support_angle)) // 2
            equation = "target_angle = (180 - apex_angle) / 2"
            relation_id = "isosceles_base_from_apex"
        else:
            support_min = int(group_default(generation_defaults, "isosceles_base_angle_min", 45))
            support_max = int(group_default(generation_defaults, "isosceles_base_angle_max", 70))
            candidates = tuple(range(int(support_min), int(support_max) + 1, int(step)))
            support_angle = int(params.get("support_angle", rng.choice(candidates)))
            if support_angle not in candidates:
                raise ValueError("support_angle is outside isosceles base support")
            answer = 180 - (2 * int(support_angle))
            equation = "target_angle = 180 - 2 * base_angle"
            relation_id = "isosceles_apex_from_base"
        witness = {
            "relation_id": str(relation_id),
            "support_angle": int(support_angle),
            "answer_angle": int(answer),
            "target_role": str(target_role),
            "equation": str(equation),
        }
        return _ResolvedSymmetryAngleProblem(
            query_id=str(query_id),
            relation_id=str(relation_id),
            support_angle=int(support_angle),
            answer=int(answer),
            target_angle_label=str(target_label),
            target_role=str(target_role),
            query_probabilities=dict(query_probabilities),
            target_role_probabilities=dict(target_role_probabilities),
            witness=dict(witness),
        )

    raise ValueError(f"unsupported symmetry query_id: {query_id}")


def _resolve_parallel_line_problem(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> _ResolvedParallelLineProblem:
    query_id, query_probabilities = _select_parallel_query_id(
        task_id=task_id,
        params=params,
        instance_seed=int(instance_seed),
    )
    rng = spawn_rng(int(instance_seed), f"{task_id}.parallel_problem")
    step = int(group_default(generation_defaults, "angle_step", 5))
    support_min = int(group_default(generation_defaults, "support_angle_min", 40))
    support_max = int(group_default(generation_defaults, "support_angle_max", 75))
    candidates = tuple(range(int(support_min), int(support_max) + 1, int(step)))
    target_label = str(params.get("target_angle_label", "x"))

    if str(query_id) == "single_transversal_chain":
        relation_id, relation_probabilities = _select_single_transversal_relation(
            task_id=task_id,
            params=params,
            instance_seed=int(instance_seed),
        )
        support_angle = int(params.get("support_angle", rng.choice(candidates)))
        if support_angle not in candidates:
            raise ValueError("support_angle is outside configured support")
        answer = int(support_angle if relation_id == "corresponding_same" else 180 - support_angle)
        witness = {
            "parallel_line_count": 3,
            "transversal_count": 1,
            "relation_id": str(relation_id),
            "support_angle": int(support_angle),
            "answer_angle": int(answer),
            "equation": (
                "target_angle = support_angle"
                if relation_id == "corresponding_same"
                else "target_angle = 180 - support_angle"
            ),
        }
        return _ResolvedParallelLineProblem(
            query_id=str(query_id),
            relation_id=str(relation_id),
            support_angles=(int(support_angle),),
            answer=int(answer),
            target_angle_label=str(target_label),
            query_probabilities=dict(query_probabilities),
            relation_probabilities=dict(relation_probabilities),
            witness=dict(witness),
        )

    if str(query_id) == "two_transversal_angle_sum":
        answer_min = int(group_default(generation_defaults, "answer_angle_min", 45))
        answer_max = int(group_default(generation_defaults, "answer_angle_max", 110))
        for _ in range(1000):
            left_angle = int(params.get("support_angle_1", rng.choice(candidates)))
            right_angle = int(params.get("support_angle_2", rng.choice(candidates)))
            answer = 180 - left_angle - right_angle
            if int(answer_min) <= int(answer) <= int(answer_max) and answer % step == 0:
                break
        else:
            raise ValueError("failed to sample two-transversal angle-sum problem")
        relation_probabilities = {"angle_sum": 1.0}
        witness = {
            "parallel_line_count": 2,
            "transversal_count": 2,
            "relation_id": "angle_sum",
            "support_angles": [int(left_angle), int(right_angle)],
            "answer_angle": int(answer),
            "equation": "target_angle = 180 - support_angle_1 - support_angle_2",
        }
        return _ResolvedParallelLineProblem(
            query_id=str(query_id),
            relation_id="angle_sum",
            support_angles=(int(left_angle), int(right_angle)),
            answer=int(answer),
            target_angle_label=str(target_label),
            query_probabilities=dict(query_probabilities),
            relation_probabilities=dict(relation_probabilities),
            witness=dict(witness),
        )

    raise ValueError(f"unsupported parallel-line query_id: {query_id}")


def _resolve_problem(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> _ResolvedPolygonProblem:
    query_id, query_probabilities = select_indexed_geometry_query_id(
        params=params,
        query_ids=tuple(_QUERY_SIDE_COUNTS),
        task_id=str(task_id),
        instance_seed=int(instance_seed),
    )
    side_count = int(_QUERY_SIDE_COUNTS[str(query_id)])
    labels = _VERTEX_LABELS[:side_count]
    polygon_sum = _query_angle_sum(side_count)
    label_style, label_style_probabilities = _select_label_style(
        task_id=task_id,
        params=params,
        instance_seed=int(instance_seed),
    )
    target_index = int(
        params.get(
            "target_index",
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.target_index",
            )
            % side_count,
        )
    )
    if target_index < 0 or target_index >= side_count:
        raise ValueError("target_index is outside polygon vertex support")

    min_angle = int(group_default(generation_defaults, "angle_min", 40))
    max_angle = int(group_default(generation_defaults, "angle_max", 150))
    step = int(group_default(generation_defaults, "angle_step", 5))
    rng = spawn_rng(int(instance_seed), f"{task_id}.problem")
    candidates = tuple(range(int(min_angle), int(max_angle) + 1, int(step)))

    display_labels: list[str] = [""] * side_count
    numeric_angles: list[int] = [0] * side_count
    expression_vertex_index: int | None = None
    witness: Dict[str, Any] = {
        "polygon_side_count": int(side_count),
        "interior_angle_sum": int(polygon_sum),
        "label_style": str(label_style),
    }

    support_indices = [index for index in range(side_count) if index != target_index]
    support_start = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.expression_support_start",
        )
    ) % len(support_indices)
    ordered_support_indices = support_indices[support_start:] + support_indices[:support_start]
    constant_candidates = tuple(range(-35, 36))
    x_floor = max(35, int(round(float(polygon_sum) / float(side_count))) - 35)
    x_ceiling = min(135, int(round(float(polygon_sum) / float(side_count))) + 35)
    x_candidates = tuple(range(x_floor, x_ceiling + 1))
    candidate_set = set(candidates)

    if label_style == "target_expression_mixed":
        expression_count = 2 if side_count <= 4 else 3
        expression_indices = tuple([target_index, *ordered_support_indices[: expression_count - 1]])
        numeric_indices = tuple(index for index in range(side_count) if index not in expression_indices)
        expression_vertex_index = expression_indices[1] if len(expression_indices) > 1 else target_index
        for _ in range(8000):
            x_value = int(rng.choice(x_candidates))
            constants_by_index = {
                int(index): int(rng.choice(constant_candidates))
                for index in expression_indices
            }
            if constants_by_index[int(target_index)] == 0:
                continue
            if sum(1 for value in constants_by_index.values() if int(value) != 0) < 2:
                continue
            expression_values = {
                int(index): int(x_value) + int(constant)
                for index, constant in constants_by_index.items()
            }
            if any(value not in candidate_set for value in expression_values.values()):
                continue
            remaining_total = int(polygon_sum) - sum(int(value) for value in expression_values.values())
            try:
                numeric_values = _sample_values_for_sum(
                    rng,
                    count=len(numeric_indices),
                    total=remaining_total,
                    min_value=min_angle,
                    max_value=max_angle,
                    step=step,
                )
            except ValueError:
                continue
            numeric_by_index = {int(index): int(value) for index, value in zip(numeric_indices, numeric_values)}
            for index in range(side_count):
                if index in expression_values:
                    numeric_angles[index] = int(expression_values[index])
                    display_labels[index] = _format_angle_expression(1, int(constants_by_index[index]))
                else:
                    value = int(numeric_by_index[index])
                    numeric_angles[index] = value
                    display_labels[index] = _format_degrees(value)
            witness.update(
                {
                    "equation": f"sum(visible_linear_expressions) + sum(visible_numeric_angles) = {polygon_sum}",
                    "x": int(x_value),
                    "expression_vertices": [str(labels[int(index)]) for index in expression_indices],
                    "expressions": {
                        str(labels[int(index)]): _format_linear_expression(1, int(constants_by_index[int(index)]))
                        for index in expression_indices
                    },
                    "expression_values": {
                        str(labels[int(index)]): int(expression_values[int(index)])
                        for index in expression_indices
                    },
                    "answer_angle": int(expression_values[int(target_index)]),
                    "known_numeric_angle_values": [
                        int(numeric_by_index[int(index)])
                        for index in numeric_indices
                    ],
                }
            )
            break
        else:
            raise ValueError("failed to construct mixed algebraic polygon angle problem")
    elif label_style == "all_expression":
        expression_indices = tuple(range(side_count))
        expression_vertex_index = ordered_support_indices[0] if ordered_support_indices else target_index
        for _ in range(8000):
            x_value = int(rng.choice(x_candidates))
            required_constant_sum = int(polygon_sum) - (int(side_count) * int(x_value))
            try:
                constants = _sample_candidate_values_for_sum(
                    rng,
                    count=side_count,
                    total=required_constant_sum,
                    candidates=constant_candidates,
                )
            except ValueError:
                continue
            constants_by_index = {
                int(index): int(constant)
                for index, constant in zip(expression_indices, constants)
            }
            if constants_by_index[int(target_index)] == 0:
                continue
            if sum(1 for value in constants_by_index.values() if int(value) != 0) < max(2, side_count - 1):
                continue
            expression_values = {
                int(index): int(x_value) + int(constant)
                for index, constant in constants_by_index.items()
            }
            if any(value not in candidate_set for value in expression_values.values()):
                continue
            for index in range(side_count):
                numeric_angles[index] = int(expression_values[index])
                display_labels[index] = _format_angle_expression(1, int(constants_by_index[index]))
            witness.update(
                {
                    "equation": f"sum(visible_linear_expressions) = {polygon_sum}",
                    "x": int(x_value),
                    "expression_vertices": [str(labels[int(index)]) for index in expression_indices],
                    "expressions": {
                        str(labels[int(index)]): _format_linear_expression(1, int(constants_by_index[int(index)]))
                        for index in expression_indices
                    },
                    "expression_values": {
                        str(labels[int(index)]): int(expression_values[int(index)])
                        for index in expression_indices
                    },
                    "answer_angle": int(expression_values[int(target_index)]),
                    "known_numeric_angle_values": [],
                }
            )
            break
        else:
            raise ValueError("failed to construct all-expression polygon angle problem")
    else:
        raise ValueError(f"unsupported polygon angle label_style: {label_style}")

    target_angle_name = _angle_name(labels, target_index)
    angle_names = [_angle_name(labels, index) for index in range(side_count)]
    witness.update(
        {
            "target_vertex": str(labels[int(target_index)]),
            "target_angle_name": str(target_angle_name),
            "angle_names": list(angle_names),
            "numeric_angles": [int(value) for value in numeric_angles],
            "display_angle_labels": list(display_labels),
        }
    )
    return _ResolvedPolygonProblem(
        query_id=str(query_id),
        side_count=int(side_count),
        target_index=int(target_index),
        target_angle_name=str(target_angle_name),
        labels=tuple(labels),
        numeric_angles=tuple(int(value) for value in numeric_angles),
        display_angle_labels=tuple(str(value) for value in display_labels),
        answer=int(numeric_angles[int(target_index)]),
        label_style=str(label_style),
        expression_vertex_index=expression_vertex_index,
        query_probabilities=dict(query_probabilities),
        label_style_probabilities=dict(label_style_probabilities),
        witness=dict(witness),
    )


def _draw_text_centered(ctx: _RenderContext, text: str, center: Point, *, small: bool = True) -> BBox:
    font = ctx.small_font if bool(small) else ctx.font
    x, y = float(center[0]), float(center[1])
    draw_text_traced(
        ctx.draw,
        (x, y),
        str(text),
        anchor="mm",
        font=font,
        fill=ctx.label_color,
        stroke_width=max(0, int(ctx.label_stroke_width)),
        stroke_fill=ctx.label_stroke_color,
        role="readout",
        required=False,
    )
    bbox = ctx.draw.textbbox(
        (x, y),
        str(text),
        anchor="mm",
        font=font,
        stroke_width=max(0, int(ctx.label_stroke_width)),
    )
    return pad_bbox(bbox, 2.0, width=ctx.width, height=ctx.height)


def _draw_angle_marker(
    ctx: _RenderContext,
    *,
    vertex: Point,
    prev_point: Point,
    next_point: Point,
    label: str,
    radius: float,
) -> tuple[BBox, BBox, Point]:
    vector_prev = _unit(_sub(prev_point, vertex))
    vector_next = _unit(_sub(next_point, vertex))
    angle_prev = math.atan2(vector_prev[1], vector_prev[0])
    angle_next = math.atan2(vector_next[1], vector_next[0])
    delta = ((angle_next - angle_prev + math.pi) % (2.0 * math.pi)) - math.pi
    steps = max(8, int(abs(delta) / (math.pi / 18.0)))
    arc_points = []
    for step_index in range(steps + 1):
        theta = angle_prev + (delta * (float(step_index) / float(steps)))
        arc_points.append(
            (
                float(vertex[0]) + (float(radius) * math.cos(theta)),
                float(vertex[1]) + (float(radius) * math.sin(theta)),
            )
        )
    ctx.draw.line(arc_points, fill=ctx.accent_color, width=max(2, ctx.line_width - 1), joint="curve")
    arc_bbox = bbox_from_points(arc_points, width=ctx.width, height=ctx.height, pad=ctx.line_width + 2)

    bisector = _unit((vector_prev[0] + vector_next[0], vector_prev[1] + vector_next[1]))
    if math.hypot(bisector[0], bisector[1]) <= 1e-6:
        bisector = _unit((-float(vertex[0]) + (ctx.width / 2.0), -float(vertex[1]) + (ctx.height / 2.0)))
    label_center = _add(vertex, bisector, float(radius) + 24.0)
    label_bbox = _draw_text_centered(ctx, label, label_center, small=True)
    annotation_point = _add(vertex, bisector, max(10.0, float(radius) * 0.35))
    return arc_bbox, label_bbox, annotation_point


def _sample_polygon_vertices(ctx: _RenderContext, problem: _ResolvedPolygonProblem, *, instance_seed: int) -> Tuple[Point, ...]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.render.polygon")
    side_count = int(problem.side_count)
    margin_x = 105.0
    margin_y = 86.0
    center = (
        (ctx.width / 2.0) + rng.uniform(-28.0, 28.0),
        (ctx.height / 2.0) + rng.uniform(-20.0, 24.0),
    )
    radius_x = rng.uniform(185.0, 235.0) * (0.92 if side_count == 5 else 1.0)
    radius_y = rng.uniform(145.0, 190.0)
    phase = rng.uniform(-math.pi, math.pi)
    raw_points = []
    for index in range(side_count):
        theta = phase + (2.0 * math.pi * float(index) / float(side_count)) + rng.uniform(-0.11, 0.11)
        local_radius_x = radius_x * rng.uniform(0.91, 1.08)
        local_radius_y = radius_y * rng.uniform(0.91, 1.08)
        raw_points.append(
            (
                center[0] + (local_radius_x * math.cos(theta)),
                center[1] + (local_radius_y * math.sin(theta)),
            )
        )
    min_x = min(point[0] for point in raw_points)
    max_x = max(point[0] for point in raw_points)
    min_y = min(point[1] for point in raw_points)
    max_y = max(point[1] for point in raw_points)
    shift_x = 0.0
    shift_y = 0.0
    if min_x < margin_x:
        shift_x = margin_x - min_x
    if max_x + shift_x > ctx.width - margin_x:
        shift_x = (ctx.width - margin_x) - max_x
    if min_y < margin_y:
        shift_y = margin_y - min_y
    if max_y + shift_y > ctx.height - margin_y:
        shift_y = (ctx.height - margin_y) - max_y
    return tuple((float(x) + shift_x, float(y) + shift_y) for x, y in raw_points)


def _render_problem(
    ctx: _RenderContext,
    problem: _ResolvedPolygonProblem,
    *,
    instance_seed: int,
) -> _RenderedPolygonScene:
    vertices = _sample_polygon_vertices(ctx, problem, instance_seed=int(instance_seed))
    vertices = ctx.scene_transform.points(vertices)
    ctx.draw.polygon(vertices, fill=ctx.fill_color)
    ctx.draw.line(
        [*vertices, vertices[0]],
        fill=ctx.line_color,
        width=int(ctx.line_width),
        joint="curve",
    )

    centroid = (
        sum(float(point[0]) for point in vertices) / float(len(vertices)),
        sum(float(point[1]) for point in vertices) / float(len(vertices)),
    )
    point_label_bboxes: Dict[str, BBox] = {}
    angle_arc_bboxes: Dict[str, BBox] = {}
    angle_label_bboxes: Dict[str, BBox] = {}
    annotation_points: Dict[str, Point] = {}

    for index, vertex in enumerate(vertices):
        label = str(problem.labels[index])
        outward = _unit(_sub(vertex, centroid))
        point_label_center = _add(vertex, outward, 25.0)
        point_label_bboxes[label] = _draw_text_centered(ctx, label, point_label_center, small=True)

    label_bboxes = list(point_label_bboxes.values())
    for index, vertex in enumerate(vertices):
        prev_point = vertices[(index - 1) % len(vertices)]
        next_point = vertices[(index + 1) % len(vertices)]
        arc_bbox, label_bbox, _ = _draw_angle_marker(
            ctx,
            vertex=vertex,
            prev_point=prev_point,
            next_point=next_point,
            label=str(problem.display_angle_labels[index]),
            radius=45.0 if problem.side_count == 4 else 39.0,
        )
        angle_name = _angle_name(problem.labels, index)
        angle_arc_bboxes[angle_name] = arc_bbox
        angle_label_bboxes[angle_name] = label_bbox
        label_bboxes.append(label_bbox)
        if index == int(problem.target_index):
            annotation_points["target_vertex"] = vertex
        else:
            support_index = len([key for key in annotation_points if key.startswith("known_angle_")]) + 1
            annotation_points[f"known_angle_{support_index}_vertex"] = vertex

    _assert_non_overlapping(label_bboxes)
    for bbox in label_bboxes:
        x0, y0, x1, y1 = [float(value) for value in bbox]
        if x0 <= 6 or y0 <= 6 or x1 >= ctx.width - 6 or y1 >= ctx.height - 6:
            raise ValueError("polygon angle label too close to canvas edge")

    return _RenderedPolygonScene(
        image=ctx.image,
        annotation_keyed_points=dict(annotation_points),
        annotation_roles=tuple(annotation_points.keys()),
        point_label_bboxes=dict(point_label_bboxes),
        angle_arc_bboxes=dict(angle_arc_bboxes),
        angle_label_bboxes=dict(angle_label_bboxes),
        vertices=tuple(vertices),
    )


def _make_prompt_examples(annotation_keys: Sequence[str]) -> tuple[str, str]:
    annotation = {
        str(key): [120 + (index * 45), 180 + (index * 18)]
        for index, key in enumerate(annotation_keys)
    }
    return dump_prompt_json_examples(annotation=annotation, answer=85, ensure_ascii=False)


def _make_render_context(
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
) -> _RenderContext:
    width = int(params.get("canvas_width", group_default(rendering_defaults, "canvas_width", 760)))
    height = int(params.get("canvas_height", group_default(rendering_defaults, "canvas_height", 560)))
    image, background_meta, diagram_style, diagram_style_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        task_group=TASK_GROUP,
        canvas_width=int(width),
        canvas_height=int(height),
        allow_dark=False,
        require_grid=None,
    )
    draw = ImageDraw.Draw(image)
    font_size = int(params.get("label_font_size", group_default(rendering_defaults, "label_font_size", 22)))
    small_font_size = int(
        params.get("small_label_font_size", group_default(rendering_defaults, "small_label_font_size", 18))
    )
    line_width = int(params.get("line_width", group_default(rendering_defaults, "line_width", 3)))
    label_stroke_width = int(
        params.get(
            "label_stroke_width",
            group_default(rendering_defaults, "label_stroke_width", int(diagram_style.label_stroke_width_px)),
        )
    )
    return _RenderContext(
        image=image,
        draw=draw,
        width=int(width),
        height=int(height),
        line_color=tuple(int(value) for value in diagram_style.stroke_rgb),
        secondary_color=tuple(int(value) for value in diagram_style.secondary_stroke_rgb),
        label_color=tuple(int(value) for value in diagram_style.label_rgb),
        label_stroke_color=tuple(int(value) for value in diagram_style.label_stroke_rgb),
        fill_color=tuple(int(value) for value in diagram_style.muted_fill_rgb),
        accent_color=tuple(int(value) for value in diagram_style.accent_rgb),
        line_width=max(2, int(line_width)),
        label_stroke_width=max(0, int(label_stroke_width)),
        font=load_font(font_size),
        small_font=load_font(small_font_size),
        diagram_style_meta=dict(diagram_style_meta),
        background_meta=dict(background_meta),
        scene_transform=LazySceneTransform(
            spawn_rng(int(instance_seed), f"{SCENE_ID}.scene_transform"),
            params=params,
            render_defaults=rendering_defaults,
            canvas_width=int(width),
            canvas_height=int(height),
        ),
    )


def _line_point(start: Point, end: Point, t: float) -> Point:
    return (
        float(start[0]) + ((float(end[0]) - float(start[0])) * float(t)),
        float(start[1]) + ((float(end[1]) - float(start[1])) * float(t)),
    )


def _draw_parallel_line_marks(ctx: _RenderContext, segments: Sequence[tuple[Point, Point]], *, count: int = 1) -> BBox:
    mark_points: list[Point] = []
    for segment_index, (start, end) in enumerate(segments):
        direction = _unit(_sub(end, start))
        normal = (-direction[1], direction[0])
        base = _line_point(start, end, 0.38 + (0.08 * (segment_index % 2)))
        for mark_index in range(max(1, int(count))):
            center = _add(base, direction, (float(mark_index) - ((max(1, int(count)) - 1) / 2.0)) * 13.0)
            p0 = _add(center, normal, -8.0)
            p1 = _add(center, normal, 8.0)
            ctx.draw.line([p0, p1], fill=ctx.secondary_color, width=max(2, ctx.line_width - 1))
            mark_points.extend([p0, p1])
    return bbox_from_points(mark_points, width=ctx.width, height=ctx.height, pad=ctx.line_width + 2)


def _draw_segment(ctx: _RenderContext, start: Point, end: Point, *, secondary: bool = False) -> None:
    ctx.draw.line(
        [start, end],
        fill=ctx.secondary_color if bool(secondary) else ctx.line_color,
        width=int(ctx.line_width),
    )


def _assert_parallel_line_layout(label_bboxes: Sequence[BBox], *, width: int, height: int) -> None:
    _assert_non_overlapping(label_bboxes)
    for bbox in label_bboxes:
        x0, y0, x1, y1 = [float(value) for value in bbox]
        if x0 <= 8 or y0 <= 8 or x1 >= width - 8 or y1 >= height - 8:
            raise ValueError("parallel-line angle label too close to canvas edge")


def _draw_dashed_segment(
    ctx: _RenderContext,
    start: Point,
    end: Point,
    *,
    color: Color | None = None,
    width: int | None = None,
    dash: float = 14.0,
    gap: float = 8.0,
) -> None:
    direction = _unit(_sub(end, start))
    length = math.hypot(float(end[0]) - float(start[0]), float(end[1]) - float(start[1]))
    cursor = 0.0
    while cursor < length:
        segment_end = min(length, cursor + float(dash))
        p0 = _add(start, direction, cursor)
        p1 = _add(start, direction, segment_end)
        ctx.draw.line(
            [p0, p1],
            fill=tuple(int(value) for value in (color or ctx.secondary_color)),
            width=max(1, int(width or max(2, ctx.line_width - 1))),
        )
        cursor += float(dash) + float(gap)


def _draw_right_angle_marker(
    ctx: _RenderContext,
    *,
    vertex: Point,
    arm_a: Point,
    arm_b: Point,
    size: float = 22.0,
) -> BBox:
    u = _unit(_sub(arm_a, vertex))
    v = _unit(_sub(arm_b, vertex))
    p1 = _add(vertex, u, float(size))
    p2 = _add(p1, v, float(size))
    p3 = _add(vertex, v, float(size))
    ctx.draw.line([p1, p2, p3], fill=ctx.secondary_color, width=max(2, ctx.line_width - 1))
    return bbox_from_points((p1, p2, p3), width=ctx.width, height=ctx.height, pad=ctx.line_width + 2)


def _draw_equal_side_ticks(ctx: _RenderContext, segments: Sequence[Tuple[Point, Point]], *, count: int = 1) -> BBox:
    tick_points: list[Point] = []
    for start, end in segments:
        direction = _unit(_sub(end, start))
        normal = (-direction[1], direction[0])
        midpoint = _line_point(start, end, 0.5)
        for index in range(max(1, int(count))):
            shift = (float(index) - ((max(1, int(count)) - 1) / 2.0)) * 6.0
            center = _add(midpoint, direction, shift)
            p0 = _add(center, normal, -8.0)
            p1 = _add(center, normal, 8.0)
            ctx.draw.line([p0, p1], fill=ctx.accent_color, width=max(2, ctx.line_width - 1))
            tick_points.extend((p0, p1))
    return bbox_from_points(tick_points, width=ctx.width, height=ctx.height, pad=ctx.line_width + 2)


def _assert_symmetry_angle_layout(label_bboxes: Sequence[BBox], *, width: int, height: int) -> None:
    _assert_non_overlapping(label_bboxes)
    for bbox in label_bboxes:
        x0, y0, x1, y1 = [float(value) for value in bbox]
        if x0 <= 8 or y0 <= 8 or x1 >= width - 8 or y1 >= height - 8:
            raise ValueError("symmetry angle label too close to canvas edge")


def _render_rectangle_diagonal_angle(
    ctx: _RenderContext,
    problem: _ResolvedSymmetryAngleProblem,
    *,
    instance_seed: int,
) -> _RenderedSymmetryAngleScene:
    rng = spawn_rng(int(instance_seed), f"{SYMMETRY_TASK_ID}.render.rectangle_diagonal")
    known_angle = int(problem.support_angle)
    ratio = math.tan(math.radians(float(known_angle)))
    max_w = 355.0
    max_h = 260.0
    if ratio <= max_h / max_w:
        rect_w = max_w
        rect_h = rect_w * ratio
    else:
        rect_h = max_h
        rect_w = rect_h / ratio
    scale = rng.uniform(0.94, 1.05)
    rect_w *= scale
    rect_h *= scale
    cx = (ctx.width / 2.0) + rng.uniform(-24.0, 28.0)
    cy = (ctx.height / 2.0) + rng.uniform(-18.0, 20.0)
    a = (cx - (rect_w / 2.0), cy - (rect_h / 2.0))
    b = (cx + (rect_w / 2.0), cy - (rect_h / 2.0))
    c = (cx + (rect_w / 2.0), cy + (rect_h / 2.0))
    d = (cx - (rect_w / 2.0), cy + (rect_h / 2.0))

    ctx.draw.polygon((a, b, c, d), fill=ctx.fill_color)
    ctx.draw.line([a, b, c, d, a], fill=ctx.line_color, width=ctx.line_width, joint="curve")
    _draw_segment(ctx, a, c, secondary=True)
    right_angle_bbox = _draw_right_angle_marker(ctx, vertex=a, arm_a=b, arm_b=d)

    point_bboxes = [
        _draw_text_centered(ctx, "A", _add(a, (-1.0, -1.0), 22.0), small=True),
        _draw_text_centered(ctx, "B", _add(b, (1.0, -1.0), 22.0), small=True),
        _draw_text_centered(ctx, "C", _add(c, (1.0, 1.0), 22.0), small=True),
        _draw_text_centered(ctx, "D", _add(d, (-1.0, 1.0), 22.0), small=True),
    ]
    support_arc, support_label_bbox, _ = _draw_angle_marker(
        ctx,
        vertex=a,
        prev_point=b,
        next_point=c,
        label=_format_degrees(known_angle),
        radius=39.0,
    )
    target_arc, target_label_bbox, _ = _draw_angle_marker(
        ctx,
        vertex=a,
        prev_point=c,
        next_point=d,
        label=str(problem.target_angle_label),
        radius=69.0,
    )
    _assert_symmetry_angle_layout(
        [*point_bboxes, support_label_bbox, target_label_bbox],
        width=ctx.width,
        height=ctx.height,
    )

    return _RenderedSymmetryAngleScene(
        image=ctx.image,
        annotation_keyed_points={
            "target_vertex": a,
            "known_angle_vertex": a,
            "diagonal_endpoint_1": a,
            "diagonal_endpoint_2": c,
        },
        annotation_roles=("target_vertex", "known_angle_vertex", "diagonal_endpoint_1", "diagonal_endpoint_2"),
        angle_arc_bboxes={
            "known_angle": support_arc,
            "target_angle": target_arc,
            "right_angle_marker": right_angle_bbox,
        },
        angle_label_bboxes={
            "known_angle_label": support_label_bbox,
            "target_angle_label": target_label_bbox,
        },
        construction_segments={
            "side_ab": (a, b),
            "side_bc": (b, c),
            "side_cd": (c, d),
            "side_da": (d, a),
            "diagonal_ac": (a, c),
        },
        construction_points={"A": a, "B": b, "C": c, "D": d},
    )


def _render_reflection_axis_angle(
    ctx: _RenderContext,
    problem: _ResolvedSymmetryAngleProblem,
    *,
    instance_seed: int,
) -> _RenderedSymmetryAngleScene:
    rng = spawn_rng(int(instance_seed), f"{SYMMETRY_TASK_ID}.render.reflection_axis")
    support_angle = int(problem.support_angle)
    vertex = ((ctx.width / 2.0) + rng.uniform(-24.0, 24.0), 235.0 + rng.uniform(-14.0, 16.0))
    axis_top = (vertex[0], 82.0 + rng.uniform(-8.0, 8.0))
    axis_bottom = (vertex[0], 454.0 + rng.uniform(-8.0, 8.0))
    ray_length = 205.0 + rng.uniform(-8.0, 12.0)
    sin_a = math.sin(math.radians(float(support_angle)))
    cos_a = math.cos(math.radians(float(support_angle)))
    left_endpoint = _add(vertex, (-sin_a, cos_a), ray_length)
    right_endpoint = _add(vertex, (sin_a, cos_a), ray_length)

    _draw_dashed_segment(ctx, axis_top, axis_bottom, color=ctx.secondary_color, width=max(2, ctx.line_width - 1))
    _draw_segment(ctx, vertex, left_endpoint)
    _draw_segment(ctx, vertex, right_endpoint)
    axis_mark_bbox = _draw_equal_side_ticks(ctx, ((axis_top, vertex), (vertex, axis_bottom)), count=1)

    support_arc, support_label_bbox, _ = _draw_angle_marker(
        ctx,
        vertex=vertex,
        prev_point=axis_bottom,
        next_point=right_endpoint,
        label=_format_degrees(support_angle),
        radius=38.0,
    )
    target_arc, target_label_bbox, _ = _draw_angle_marker(
        ctx,
        vertex=vertex,
        prev_point=left_endpoint,
        next_point=right_endpoint,
        label=str(problem.target_angle_label),
        radius=72.0,
    )
    point_bboxes = [
        _draw_text_centered(ctx, "P", _add(vertex, (0.0, -1.0), 26.0), small=True),
    ]
    _assert_symmetry_angle_layout(
        [*point_bboxes, support_label_bbox, target_label_bbox],
        width=ctx.width,
        height=ctx.height,
    )

    return _RenderedSymmetryAngleScene(
        image=ctx.image,
        annotation_keyed_points={
            "target_vertex": vertex,
            "support_vertex": vertex,
            "axis_point_1": axis_top,
            "axis_point_2": axis_bottom,
        },
        annotation_roles=("target_vertex", "support_vertex", "axis_point_1", "axis_point_2"),
        angle_arc_bboxes={
            "known_angle": support_arc,
            "target_angle": target_arc,
            "symmetry_axis_marks": axis_mark_bbox,
        },
        angle_label_bboxes={
            "known_angle_label": support_label_bbox,
            "target_angle_label": target_label_bbox,
        },
        construction_segments={
            "symmetry_axis": (axis_top, axis_bottom),
            "ray_left": (vertex, left_endpoint),
            "ray_right": (vertex, right_endpoint),
        },
        construction_points={
            "target_vertex": vertex,
            "axis_point_1": axis_top,
            "axis_point_2": axis_bottom,
            "left_ray_endpoint": left_endpoint,
            "right_ray_endpoint": right_endpoint,
        },
    )


def _render_isosceles_base_angle_chain(
    ctx: _RenderContext,
    problem: _ResolvedSymmetryAngleProblem,
    *,
    instance_seed: int,
) -> _RenderedSymmetryAngleScene:
    rng = spawn_rng(int(instance_seed), f"{SYMMETRY_TASK_ID}.render.isosceles")
    if problem.target_role == "base_angle":
        apex_angle = int(problem.support_angle)
        support_label = _format_degrees(apex_angle)
    else:
        apex_angle = int(problem.answer)
        support_label = _format_degrees(int(problem.support_angle))
    half_apex = max(16.0, float(apex_angle) / 2.0)
    max_half_base = 178.0
    max_height = 278.0
    height = max_half_base / math.tan(math.radians(half_apex))
    if height > max_height:
        height = max_height
        half_base = height * math.tan(math.radians(half_apex))
    else:
        half_base = max_half_base
    scale = rng.uniform(0.94, 1.05)
    half_base *= scale
    height *= scale
    cx = (ctx.width / 2.0) + rng.uniform(-24.0, 24.0)
    cy = (ctx.height / 2.0) + rng.uniform(-14.0, 18.0)
    apex = (cx, cy - (height / 2.0))
    base_left = (cx - half_base, cy + (height / 2.0))
    base_right = (cx + half_base, cy + (height / 2.0))

    ctx.draw.polygon((apex, base_left, base_right), fill=ctx.fill_color)
    ctx.draw.line([apex, base_left, base_right, apex], fill=ctx.line_color, width=ctx.line_width, joint="curve")
    ticks_bbox = _draw_equal_side_ticks(ctx, ((apex, base_left), (apex, base_right)), count=1)
    point_bboxes = [
        _draw_text_centered(ctx, "A", _add(apex, (0.0, -1.0), 25.0), small=True),
        _draw_text_centered(ctx, "B", _add(base_left, (-1.0, 1.0), 24.0), small=True),
        _draw_text_centered(ctx, "C", _add(base_right, (1.0, 1.0), 24.0), small=True),
    ]

    if problem.target_role == "base_angle":
        target_arc, target_label_bbox, _ = _draw_angle_marker(
            ctx,
            vertex=base_left,
            prev_point=base_right,
            next_point=apex,
            label=str(problem.target_angle_label),
            radius=43.0,
        )
        support_arc, support_label_bbox, _ = _draw_angle_marker(
            ctx,
            vertex=apex,
            prev_point=base_left,
            next_point=base_right,
            label=support_label,
            radius=47.0,
        )
        target_vertex = base_left
        support_vertex = apex
    else:
        target_arc, target_label_bbox, _ = _draw_angle_marker(
            ctx,
            vertex=apex,
            prev_point=base_left,
            next_point=base_right,
            label=str(problem.target_angle_label),
            radius=47.0,
        )
        support_arc, support_label_bbox, _ = _draw_angle_marker(
            ctx,
            vertex=base_left,
            prev_point=base_right,
            next_point=apex,
            label=support_label,
            radius=43.0,
        )
        target_vertex = apex
        support_vertex = base_left

    _assert_symmetry_angle_layout(
        [*point_bboxes, support_label_bbox, target_label_bbox],
        width=ctx.width,
        height=ctx.height,
    )

    return _RenderedSymmetryAngleScene(
        image=ctx.image,
        annotation_keyed_points={
            "target_vertex": target_vertex,
            "support_vertex": support_vertex,
            "apex_vertex": apex,
            "base_left_vertex": base_left,
            "base_right_vertex": base_right,
        },
        annotation_roles=("target_vertex", "support_vertex", "apex_vertex", "base_left_vertex", "base_right_vertex"),
        angle_arc_bboxes={
            "known_angle": support_arc,
            "target_angle": target_arc,
            "equal_side_ticks": ticks_bbox,
        },
        angle_label_bboxes={
            "known_angle_label": support_label_bbox,
            "target_angle_label": target_label_bbox,
        },
        construction_segments={
            "side_ab": (apex, base_left),
            "side_ac": (apex, base_right),
            "base_bc": (base_left, base_right),
        },
        construction_points={"A": apex, "B": base_left, "C": base_right},
    )


def _render_symmetry_angle_problem(
    ctx: _RenderContext,
    problem: _ResolvedSymmetryAngleProblem,
    *,
    instance_seed: int,
) -> _RenderedSymmetryAngleScene:
    if problem.query_id == "rectangle_diagonal_angle":
        return _render_rectangle_diagonal_angle(ctx, problem, instance_seed=int(instance_seed))
    if problem.query_id == "reflection_axis_angle":
        return _render_reflection_axis_angle(ctx, problem, instance_seed=int(instance_seed))
    if problem.query_id == "isosceles_base_angle_chain":
        return _render_isosceles_base_angle_chain(ctx, problem, instance_seed=int(instance_seed))
    raise ValueError(f"unsupported symmetry query_id: {problem.query_id}")


def _render_single_transversal_chain(
    ctx: _RenderContext,
    problem: _ResolvedParallelLineProblem,
    *,
    instance_seed: int,
) -> _RenderedParallelLineScene:
    rng = spawn_rng(int(instance_seed), f"{PARALLEL_TASK_ID}.render.single_transversal")
    support_angle = int(problem.support_angles[0])
    top_y = 140.0 + rng.uniform(-12.0, 10.0)
    mid_y = 280.0 + rng.uniform(-8.0, 8.0)
    bottom_y = 420.0 + rng.uniform(-10.0, 12.0)
    center_x = (ctx.width / 2.0) + rng.uniform(-28.0, 28.0)
    dy = bottom_y - top_y
    dx = dy / math.tan(math.radians(float(support_angle)))
    top_x = center_x - (dx / 2.0)
    bottom_x = center_x + (dx / 2.0)
    if top_x < 150.0:
        shift = 150.0 - top_x
        top_x += shift
        bottom_x += shift
    if bottom_x > ctx.width - 150.0:
        shift = (ctx.width - 150.0) - bottom_x
        top_x += shift
        bottom_x += shift

    line_x0 = 90.0 + rng.uniform(-8.0, 8.0)
    line_x1 = ctx.width - 90.0 + rng.uniform(-8.0, 8.0)
    top_line = ((line_x0, top_y), (line_x1, top_y))
    mid_line = ((line_x0, mid_y), (line_x1, mid_y))
    bottom_line = ((line_x0, bottom_y), (line_x1, bottom_y))
    for segment in (top_line, mid_line, bottom_line):
        _draw_segment(ctx, segment[0], segment[1])

    t_mid = (mid_y - top_y) / (bottom_y - top_y)
    support_vertex = (float(top_x), float(top_y))
    bridge_vertex = (float(top_x + ((bottom_x - top_x) * t_mid)), float(mid_y))
    target_vertex = (float(bottom_x), float(bottom_y))
    v_down = _unit(_sub(target_vertex, support_vertex))
    trans_start = _add(support_vertex, v_down, -70.0)
    trans_end = _add(target_vertex, v_down, 70.0)
    _draw_segment(ctx, trans_start, trans_end)
    parallel_marks_bbox = _draw_parallel_line_marks(ctx, (top_line, mid_line, bottom_line), count=1)

    east = (1.0, 0.0)
    west = (-1.0, 0.0)
    support_arc, support_label_bbox, _ = _draw_angle_marker(
        ctx,
        vertex=support_vertex,
        prev_point=_add(support_vertex, east, 80.0),
        next_point=_add(support_vertex, v_down, 80.0),
        label=_format_degrees(support_angle),
        radius=36.0,
    )
    if problem.relation_id == "corresponding_same":
        target_prev = _add(target_vertex, east, 80.0)
    else:
        target_prev = _add(target_vertex, west, 80.0)
    target_arc, target_label_bbox, _ = _draw_angle_marker(
        ctx,
        vertex=target_vertex,
        prev_point=target_prev,
        next_point=_add(target_vertex, v_down, 80.0),
        label=str(problem.target_angle_label),
        radius=36.0,
    )
    _assert_parallel_line_layout([support_label_bbox, target_label_bbox], width=ctx.width, height=ctx.height)

    return _RenderedParallelLineScene(
        image=ctx.image,
        annotation_keyed_points={
            "target_vertex": target_vertex,
            "support_vertex": support_vertex,
            "bridge_vertex": bridge_vertex,
        },
        annotation_roles=("target_vertex", "support_vertex", "bridge_vertex"),
        angle_arc_bboxes={
            "support_angle": support_arc,
            "target_angle": target_arc,
            "parallel_marks": parallel_marks_bbox,
        },
        angle_label_bboxes={
            "support_angle_label": support_label_bbox,
            "target_angle_label": target_label_bbox,
        },
        line_segments={
            "parallel_line_1": top_line,
            "parallel_line_2": mid_line,
            "parallel_line_3": bottom_line,
            "transversal": (trans_start, trans_end),
        },
        intersections={
            "support_vertex": support_vertex,
            "bridge_vertex": bridge_vertex,
            "target_vertex": target_vertex,
        },
    )


def _render_two_transversal_angle_sum(
    ctx: _RenderContext,
    problem: _ResolvedParallelLineProblem,
    *,
    instance_seed: int,
) -> _RenderedParallelLineScene:
    rng = spawn_rng(int(instance_seed), f"{PARALLEL_TASK_ID}.render.two_transversal")
    left_angle, right_angle = [int(value) for value in problem.support_angles]
    top_y = 142.0 + rng.uniform(-10.0, 10.0)
    target_y = 294.0 + rng.uniform(-12.0, 12.0)
    bottom_y = 430.0 + rng.uniform(-10.0, 10.0)
    target_x = (ctx.width / 2.0) + rng.uniform(-24.0, 24.0)
    left_dx = (target_y - top_y) / math.tan(math.radians(float(left_angle)))
    right_dx = (target_y - top_y) / math.tan(math.radians(float(right_angle)))
    support_vertex_1 = (float(target_x - left_dx), float(top_y))
    support_vertex_2 = (float(target_x + right_dx), float(top_y))
    target_vertex = (float(target_x), float(target_y))
    scale_to_bottom = (bottom_y - target_y) / (target_y - top_y)
    bottom_right = _add(target_vertex, _sub(target_vertex, support_vertex_1), scale_to_bottom)
    bottom_left = _add(target_vertex, _sub(target_vertex, support_vertex_2), scale_to_bottom)

    line_x0 = 88.0 + rng.uniform(-8.0, 8.0)
    line_x1 = ctx.width - 88.0 + rng.uniform(-8.0, 8.0)
    top_line = ((line_x0, top_y), (line_x1, top_y))
    bottom_line = ((line_x0, bottom_y), (line_x1, bottom_y))
    for segment in (top_line, bottom_line):
        _draw_segment(ctx, segment[0], segment[1])
    _draw_segment(ctx, support_vertex_1, bottom_right)
    _draw_segment(ctx, support_vertex_2, bottom_left)
    parallel_marks_bbox = _draw_parallel_line_marks(ctx, (top_line, bottom_line), count=1)

    east = (1.0, 0.0)
    west = (-1.0, 0.0)
    support_arc_1, support_label_bbox_1, _ = _draw_angle_marker(
        ctx,
        vertex=support_vertex_1,
        prev_point=_add(support_vertex_1, east, 80.0),
        next_point=target_vertex,
        label=_format_degrees(left_angle),
        radius=35.0,
    )
    support_arc_2, support_label_bbox_2, _ = _draw_angle_marker(
        ctx,
        vertex=support_vertex_2,
        prev_point=target_vertex,
        next_point=_add(support_vertex_2, west, 80.0),
        label=_format_degrees(right_angle),
        radius=35.0,
    )
    target_arc, target_label_bbox, _ = _draw_angle_marker(
        ctx,
        vertex=target_vertex,
        prev_point=support_vertex_1,
        next_point=support_vertex_2,
        label=str(problem.target_angle_label),
        radius=42.0,
    )
    _assert_parallel_line_layout(
        [support_label_bbox_1, support_label_bbox_2, target_label_bbox],
        width=ctx.width,
        height=ctx.height,
    )

    return _RenderedParallelLineScene(
        image=ctx.image,
        annotation_keyed_points={
            "target_vertex": target_vertex,
            "support_vertex_1": support_vertex_1,
            "support_vertex_2": support_vertex_2,
        },
        annotation_roles=("target_vertex", "support_vertex_1", "support_vertex_2"),
        angle_arc_bboxes={
            "support_angle_1": support_arc_1,
            "support_angle_2": support_arc_2,
            "target_angle": target_arc,
            "parallel_marks": parallel_marks_bbox,
        },
        angle_label_bboxes={
            "support_angle_1_label": support_label_bbox_1,
            "support_angle_2_label": support_label_bbox_2,
            "target_angle_label": target_label_bbox,
        },
        line_segments={
            "parallel_line_1": top_line,
            "parallel_line_2": bottom_line,
            "transversal_1": (support_vertex_1, bottom_right),
            "transversal_2": (support_vertex_2, bottom_left),
        },
        intersections={
            "target_vertex": target_vertex,
            "support_vertex_1": support_vertex_1,
            "support_vertex_2": support_vertex_2,
        },
    )


def _render_parallel_line_problem(
    ctx: _RenderContext,
    problem: _ResolvedParallelLineProblem,
    *,
    instance_seed: int,
) -> _RenderedParallelLineScene:
    if problem.query_id == "single_transversal_chain":
        return _render_single_transversal_chain(ctx, problem, instance_seed=int(instance_seed))
    if problem.query_id == "two_transversal_angle_sum":
        return _render_two_transversal_angle_sum(ctx, problem, instance_seed=int(instance_seed))
    raise ValueError(f"unsupported parallel-line query_id: {problem.query_id}")


@register_task
class GeometryPolygonAngleChaseInteriorAngleValueTask:
    """Infer a missing polygon interior angle from visible angle labels."""

    task_id = TASK_ID
    domain = "geometry"
    task_group = TASK_GROUP
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    default_dataset_enabled = True

    def _make_render_context(
        self,
        instance_seed: int,
        params: Mapping[str, Any],
        rendering_defaults: Mapping[str, Any],
    ) -> _RenderContext:
        return _make_render_context(instance_seed, params, rendering_defaults)

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            _TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
        )
        rendered: _RenderedPolygonScene | None = None
        problem: _ResolvedPolygonProblem | None = None
        ctx: _RenderContext | None = None
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_params = dict(params)
            attempt_params["_render_attempt"] = int(attempt)
            try:
                problem = _resolve_problem(
                    task_id=self.task_id,
                    instance_seed=int(instance_seed) + int(attempt),
                    params=attempt_params,
                    generation_defaults=generation_defaults,
                )
                ctx = self._make_render_context(
                    int(instance_seed) + int(attempt),
                    attempt_params,
                    rendering_defaults,
                )
                rendered = _render_problem(
                    ctx,
                    problem,
                    instance_seed=int(instance_seed) + int(attempt),
                )
                break
            except Exception as exc:
                last_error = exc
                continue
        if rendered is None or problem is None or ctx is None:
            raise RuntimeError(f"failed to generate {self.task_id}") from last_error

        image, noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt_defaults = required_group_defaults(
            prompt_defaults,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "object_description",
                "json_output_contract",
                "json_output_contract_answer_only",
                "annotation_hint",
                "answer_hint_integer",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        annotation_keys = tuple(rendered.annotation_keyed_points.keys())
        json_example, json_example_answer_only = _make_prompt_examples(annotation_keys)
        annotation_key_list = ", ".join(f'"{key}"' for key in annotation_keys)
        annotation_hint = str(prompt_defaults["annotation_hint"]).format(annotation_keys=annotation_key_list)
        polygon_kind = _polygon_kind(problem.side_count)
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(problem.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "polygon_kind": polygon_kind,
                "target_angle_name": str(problem.target_angle_name),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(annotation_hint),
                "answer_hint": str(prompt_defaults["answer_hint_integer"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        annotation_value = {
            str(key): [round(float(point[0]), 3), round(float(point[1]), 3)]
            for key, point in rendered.annotation_keyed_points.items()
        }
        vertices_payload = {
            str(label): [round(float(point[0]), 3), round(float(point[1]), 3)]
            for label, point in zip(problem.labels, rendered.vertices)
        }
        angle_names = [_angle_name(problem.labels, index) for index in range(problem.side_count)]
        render_map = {
            "point_label_bboxes": geometry_json_ready(rendered.point_label_bboxes, round_floats=False),
            "angle_arc_bboxes": geometry_json_ready(rendered.angle_arc_bboxes, round_floats=False),
            "angle_label_bboxes": geometry_json_ready(rendered.angle_label_bboxes, round_floats=False),
            "polygon_vertices": dict(vertices_payload),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "domain": self.domain,
                "task_group": self.task_group,
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "entities": [
                    {
                        "type": "convex_polygon",
                        "labels": list(problem.labels),
                        "vertices": dict(vertices_payload),
                    },
                ],
                "relations": {
                    "type": "polygon_interior_angle_sum",
                    "side_count": int(problem.side_count),
                    "interior_angle_sum": _query_angle_sum(problem.side_count),
                    "query_id": str(problem.query_id),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "params": {
                    "query_id": str(problem.query_id),
                    "query_id_probabilities": dict(problem.query_probabilities),
                    "label_style": str(problem.label_style),
                    "label_style_probabilities": dict(problem.label_style_probabilities),
                    "target_index": int(problem.target_index),
                },
            },
            "render_spec": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "canvas": {"width": int(ctx.width), "height": int(ctx.height)},
                "single_object_scene_rotation": ctx.scene_transform.metadata(),
                "style": {
                    "technical_diagram": dict(ctx.diagram_style_meta),
                    "background": dict(ctx.background_meta),
                    "post_image_noise": dict(noise_meta),
                },
                "prompt": {
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                },
            },
            "render_map": dict(render_map),
            "execution_trace": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "target_angle_name": str(problem.target_angle_name),
                "target_index": int(problem.target_index),
                "target_vertex": str(problem.labels[int(problem.target_index)]),
                "angle_names": list(angle_names),
                "numeric_angles": [int(value) for value in problem.numeric_angles],
                "display_angle_labels": list(problem.display_angle_labels),
                "answer": int(problem.answer),
                "annotation_roles": list(rendered.annotation_roles),
                **dict(problem.witness),
            },
            "witness_symbolic": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                **dict(problem.witness),
            },
            "projected_annotation": {
                "type": "keyed_point_map",
                "keyed_point_map": dict(annotation_value),
                "pixel_keyed_point_map": dict(annotation_value),
            },
        }
        complexity = build_geometry_measurement_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            visual_scan=normalize_linear(problem.side_count, min_value=4, max_value=5),
            measurement_precision=0.78 if problem.label_style == "all_expression" else 0.68,
            ambiguity=0.25 if problem.side_count == 4 else 0.45,
            output_burden=normalize_linear(len(annotation_value), min_value=4, max_value=5),
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(problem.answer)),
            annotation_gt=TypedValue(type="keyed_point_map", value=dict(annotation_value)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(problem.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class GeometryPolygonAngleChaseParallelLineAngleValueTask:
    """Infer a missing angle from parallel-line transversal relations."""

    task_id = PARALLEL_TASK_ID
    domain = "geometry"
    task_group = TASK_GROUP
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            _TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
        )
        rendered: _RenderedParallelLineScene | None = None
        problem: _ResolvedParallelLineProblem | None = None
        ctx: _RenderContext | None = None
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_params = dict(params)
            attempt_params["_render_attempt"] = int(attempt)
            try:
                problem = _resolve_parallel_line_problem(
                    task_id=self.task_id,
                    instance_seed=int(instance_seed) + int(attempt),
                    params=attempt_params,
                    generation_defaults=generation_defaults,
                )
                ctx = _make_render_context(
                    int(instance_seed) + int(attempt),
                    attempt_params,
                    rendering_defaults,
                )
                rendered = _render_parallel_line_problem(
                    ctx,
                    problem,
                    instance_seed=int(instance_seed) + int(attempt),
                )
                break
            except Exception as exc:
                last_error = exc
                continue
        if rendered is None or problem is None or ctx is None:
            raise RuntimeError(f"failed to generate {self.task_id}") from last_error

        image, noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt_defaults = required_group_defaults(
            prompt_defaults,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "object_description",
                "json_output_contract",
                "json_output_contract_answer_only",
                "annotation_hint",
                "answer_hint_integer",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        annotation_keys = tuple(rendered.annotation_keyed_points.keys())
        json_example, json_example_answer_only = _make_prompt_examples(annotation_keys)
        annotation_key_list = ", ".join(f'"{key}"' for key in annotation_keys)
        annotation_hint = str(prompt_defaults["annotation_hint"]).format(annotation_keys=annotation_key_list)
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(problem.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "target_angle_label": str(problem.target_angle_label),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(annotation_hint),
                "answer_hint": str(prompt_defaults["answer_hint_integer"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        annotation_value = {
            str(key): [round(float(point[0]), 3), round(float(point[1]), 3)]
            for key, point in rendered.annotation_keyed_points.items()
        }
        intersections_payload = {
            str(key): [round(float(point[0]), 3), round(float(point[1]), 3)]
            for key, point in rendered.intersections.items()
        }
        render_map = {
            "angle_arc_bboxes": geometry_json_ready(rendered.angle_arc_bboxes, round_floats=False),
            "angle_label_bboxes": geometry_json_ready(rendered.angle_label_bboxes, round_floats=False),
            "line_segments": geometry_json_ready(rendered.line_segments, round_floats=False),
            "intersections": dict(intersections_payload),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "domain": self.domain,
                "task_group": self.task_group,
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "entities": {
                    "parallel_lines": [
                        str(key) for key in sorted(rendered.line_segments) if key.startswith("parallel_line_")
                    ],
                    "transversals": [
                        str(key) for key in sorted(rendered.line_segments) if key.startswith("transversal")
                    ],
                    "intersections": dict(intersections_payload),
                },
                "relations": {
                    "type": "parallel_line_angle_chain",
                    "query_id": str(problem.query_id),
                    "relation_id": str(problem.relation_id),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "params": {
                    "query_id": str(problem.query_id),
                    "query_id_probabilities": dict(problem.query_probabilities),
                    "relation_id": str(problem.relation_id),
                    "relation_id_probabilities": dict(problem.relation_probabilities),
                },
            },
            "render_spec": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "canvas": {"width": int(ctx.width), "height": int(ctx.height)},
                "style": {
                    "technical_diagram": dict(ctx.diagram_style_meta),
                    "background": dict(ctx.background_meta),
                    "post_image_noise": dict(noise_meta),
                },
                "prompt": {
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                },
            },
            "render_map": dict(render_map),
            "execution_trace": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "target_angle_label": str(problem.target_angle_label),
                "support_angles": [int(value) for value in problem.support_angles],
                "answer": int(problem.answer),
                "annotation_roles": list(rendered.annotation_roles),
                **dict(problem.witness),
            },
            "witness_symbolic": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                **dict(problem.witness),
            },
            "projected_annotation": {
                "type": "keyed_point_map",
                "keyed_point_map": dict(annotation_value),
                "pixel_keyed_point_map": dict(annotation_value),
            },
        }
        complexity = build_geometry_measurement_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            visual_scan=0.55 if problem.query_id == "single_transversal_chain" else 0.72,
            measurement_precision=0.50,
            ambiguity=0.45 if problem.query_id == "single_transversal_chain" else 0.62,
            output_burden=normalize_linear(len(annotation_value), min_value=3, max_value=4),
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(problem.answer)),
            annotation_gt=TypedValue(type="keyed_point_map", value=dict(annotation_value)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(problem.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class GeometryPolygonAngleChaseSymmetryAngleValueTask:
    """Infer a missing angle from visible symmetry or equal-angle structure."""

    task_id = SYMMETRY_TASK_ID
    domain = "geometry"
    task_group = TASK_GROUP
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            _TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
        )
        rendered: _RenderedSymmetryAngleScene | None = None
        problem: _ResolvedSymmetryAngleProblem | None = None
        ctx: _RenderContext | None = None
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_params = dict(params)
            attempt_params["_render_attempt"] = int(attempt)
            try:
                problem = _resolve_symmetry_angle_problem(
                    task_id=self.task_id,
                    instance_seed=int(instance_seed) + int(attempt),
                    params=attempt_params,
                    generation_defaults=generation_defaults,
                )
                ctx = _make_render_context(
                    int(instance_seed) + int(attempt),
                    attempt_params,
                    rendering_defaults,
                )
                rendered = _render_symmetry_angle_problem(
                    ctx,
                    problem,
                    instance_seed=int(instance_seed) + int(attempt),
                )
                break
            except Exception as exc:
                last_error = exc
                continue
        if rendered is None or problem is None or ctx is None:
            raise RuntimeError(f"failed to generate {self.task_id}") from last_error

        image, noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt_defaults = required_group_defaults(
            prompt_defaults,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "object_description",
                "json_output_contract",
                "json_output_contract_answer_only",
                "annotation_hint",
                "answer_hint_integer",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        annotation_keys = tuple(rendered.annotation_keyed_points.keys())
        json_example, json_example_answer_only = _make_prompt_examples(annotation_keys)
        annotation_key_list = ", ".join(f'"{key}"' for key in annotation_keys)
        annotation_hint = str(prompt_defaults["annotation_hint"]).format(annotation_keys=annotation_key_list)
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(problem.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "target_angle_label": str(problem.target_angle_label),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(annotation_hint),
                "answer_hint": str(prompt_defaults["answer_hint_integer"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        annotation_value = {
            str(key): [round(float(point[0]), 3), round(float(point[1]), 3)]
            for key, point in rendered.annotation_keyed_points.items()
        }
        construction_points_payload = {
            str(key): [round(float(point[0]), 3), round(float(point[1]), 3)]
            for key, point in rendered.construction_points.items()
        }
        render_map = {
            "angle_arc_bboxes": geometry_json_ready(rendered.angle_arc_bboxes, round_floats=False),
            "angle_label_bboxes": geometry_json_ready(rendered.angle_label_bboxes, round_floats=False),
            "construction_segments": geometry_json_ready(rendered.construction_segments, round_floats=False),
            "construction_points": dict(construction_points_payload),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "domain": self.domain,
                "task_group": self.task_group,
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "entities": {
                    "construction_points": dict(construction_points_payload),
                    "construction_segments": geometry_json_ready(rendered.construction_segments, round_floats=False),
                },
                "relations": {
                    "type": "symmetry_angle_chain",
                    "query_id": str(problem.query_id),
                    "relation_id": str(problem.relation_id),
                    "target_role": str(problem.target_role),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "params": {
                    "query_id": str(problem.query_id),
                    "query_id_probabilities": dict(problem.query_probabilities),
                    "relation_id": str(problem.relation_id),
                    "target_role": str(problem.target_role),
                    "target_role_probabilities": dict(problem.target_role_probabilities),
                },
            },
            "render_spec": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "canvas": {"width": int(ctx.width), "height": int(ctx.height)},
                "style": {
                    "technical_diagram": dict(ctx.diagram_style_meta),
                    "background": dict(ctx.background_meta),
                    "post_image_noise": dict(noise_meta),
                },
                "prompt": {
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                },
            },
            "render_map": dict(render_map),
            "execution_trace": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "target_angle_label": str(problem.target_angle_label),
                "support_angle": int(problem.support_angle),
                "answer": int(problem.answer),
                "annotation_roles": list(rendered.annotation_roles),
                **dict(problem.witness),
            },
            "witness_symbolic": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                **dict(problem.witness),
            },
            "projected_annotation": {
                "type": "keyed_point_map",
                "keyed_point_map": dict(annotation_value),
                "pixel_keyed_point_map": dict(annotation_value),
            },
        }
        complexity = build_geometry_measurement_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            visual_scan=0.52 if problem.query_id == "rectangle_diagonal_angle" else 0.66,
            measurement_precision=0.48,
            ambiguity=0.38 if problem.query_id == "rectangle_diagonal_angle" else 0.55,
            output_burden=normalize_linear(len(annotation_value), min_value=4, max_value=5),
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(problem.answer)),
            annotation_gt=TypedValue(type="keyed_point_map", value=dict(annotation_value)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(problem.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = [
    "GeometryPolygonAngleChaseInteriorAngleValueTask",
    "GeometryPolygonAngleChaseParallelLineAngleValueTask",
    "GeometryPolygonAngleChaseSymmetryAngleValueTask",
]
