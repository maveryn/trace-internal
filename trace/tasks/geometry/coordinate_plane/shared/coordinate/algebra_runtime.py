"""Shared runtime for coordinate-plane algebra candidate tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ......core.seed import spawn_rng
from ......core.scene_config import get_scene_defaults
from .....shared.config_defaults import required_group_defaults, split_scene_generation_rendering_prompt_defaults
from .....shared.deterministic_sampling import resolve_selection_index
from .....shared.prompt_json_example import resolve_prompt_json_examples
from .....shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_scene_prompt_variants
from .....shared.text_rendering import load_font, resolve_scene_label_font_size_px
from .....shared.text_legibility import draw_text_traced
from ....shared.background_defaults import load_geometry_background_defaults
from trace.tasks.shared.fixed_query import select_geometry_query_id
from ....shared.graph_rendering import graph_paper_grid_from_frame, graph_units_to_pixel, scale_point
from ....shared.noise_defaults import load_geometry_noise_defaults
from ....shared.option_count import resolve_geometry_option_count
from ....shared.point_labels import draw_labeled_points
from ....shared.single_object_scene import finalize_graph_scene_image, make_graph_scene_canvas, resolve_graph_scene_context
from .quadrilateral import (
    _draw_marker,
    _marker_bbox,
    _probability_map,
    _resolve_label_pool,
    _resolve_marker_colors,
    _sample_marker_style,
)

SCENE_ID = "coordinate_plane"
from .params import resolve_int_param as _resolve_int_param


GraphPoint = Tuple[int, int]
PixelPoint = Tuple[float, float]
Color = Tuple[int, int, int]
GuideSegment = Tuple[str, str, str]

MISSING_ENDPOINT_QUERY_IDS: Tuple[str, ...] = (
    "missing_endpoint_from_midpoint",
    "missing_startpoint_from_midpoint",
)
SECTION_POINT_QUERY_IDS: Tuple[str, ...] = (
    "one_third_from_p_to_q",
    "two_thirds_from_p_to_q",
)
TRANSFORMED_POINT_QUERY_IDS: Tuple[str, ...] = (
    "translate_point",
    "translate_by_reference_vector",
    "reflect_over_vertical_line",
    "reflect_over_horizontal_line",
    "rotate_90_about_marked_center",
)
REFLECTED_POINT_QUERY_IDS: Tuple[str, ...] = (
    "reflect_over_vertical_line",
    "reflect_over_horizontal_line",
)
ROTATED_POINT_QUERY_IDS: Tuple[str, ...] = ("rotate_90_about_marked_center",)
TRANSLATED_POINT_QUERY_IDS: Tuple[str, ...] = (
    "translate_point",
    "translate_by_reference_vector",
)
DEFAULT_LABEL_POOL: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")

_SCENE_DEFAULTS = get_scene_defaults("geometry", "coordinate_plane")
_BACKGROUND_DEFAULTS = load_geometry_background_defaults(scene_id="coordinate")
_NOISE_DEFAULTS = load_geometry_noise_defaults(scene_id="coordinate")


@dataclass(frozen=True)
class _TaskDefaults:
    canvas_size_min: int = 680
    canvas_size_max: int = 760
    graph_cells_min: int = 18
    graph_cells_max: int = 20
    graph_abs_max: int = 7
    candidate_count: int = 6
    marker_radius_px: int = 7
    marker_radius_px_min: int = 6
    marker_radius_px_max: int = 9
    label_font_size_min: int = 16
    label_font_size_max: int = 28
    label_stroke_width: int = 1
    label_offset_px: int = 15
    transform_label_font_size: int = 20


@dataclass(frozen=True)
class _ResolvedQuery:
    query_id: str
    query_probabilities: Dict[str, float]
    winner_label: str
    winner_label_probabilities: Dict[str, float]
    label_pool: Tuple[str, ...]


@dataclass(frozen=True)
class _AlgebraProblem:
    query_id: str
    known_points_by_label: Dict[str, GraphPoint]
    target_label_name: str
    target_point: GraphPoint
    formula: str
    transform_text: str | None = None
    transform_line: Dict[str, int] | None = None
    guide_segments: Tuple[GuideSegment, ...] = ()


@dataclass(frozen=True)
class _RenderedScene:
    problem: _AlgebraProblem
    candidate_points_by_label: Dict[str, GraphPoint]
    candidate_bboxes_by_label: Dict[str, List[int]]
    known_points_px_by_label: Dict[str, PixelPoint]
    candidate_points_px_by_label: Dict[str, PixelPoint]
    label_box_bbox_px: List[int] | None
    marker_meta: Dict[str, Any]
    image: Image.Image
    background_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]
    render_spec_extra: Dict[str, Any]
    option_count_probabilities: Dict[str, float]


@dataclass(frozen=True)
class AlgebraArtifacts:
    query: _ResolvedQuery
    rendered: _RenderedScene
    prompt_artifacts: Any
    annotation_value: List[List[float]]
    trace_payload: Dict[str, Any]



_DEFAULTS = _TaskDefaults()

_MIDPOINT_CASES: Tuple[Tuple[GraphPoint, GraphPoint], ...] = (
    ((-4, 1), (0, 3)),
    ((3, -5), (-1, -2)),
    ((-6, -2), (-2, 1)),
    ((5, 3), (1, 0)),
    ((-1, 6), (2, 2)),
    ((6, -1), (2, 2)),
    ((-5, 5), (-1, 1)),
    ((4, 6), (0, 2)),
    ((-6, 3), (-2, -1)),
    ((2, -6), (-1, -2)),
)
_SECTION_CASES: Tuple[Tuple[GraphPoint, GraphPoint], ...] = (
    ((-6, -3), (3, 3)),
    ((4, -5), (-5, 1)),
    ((-6, 5), (3, -4)),
    ((5, 4), (-4, -5)),
    ((-5, -1), (4, 5)),
    ((3, -6), (-6, 3)),
    ((-4, 6), (5, 0)),
    ((-7, 2), (2, -4)),
)
_TRANSLATION_CASES: Tuple[Tuple[GraphPoint, GraphPoint], ...] = (
    ((-4, 1), (5, 2)),
    ((3, -5), (-4, 3)),
    ((-6, -2), (3, 5)),
    ((5, 3), (-6, -4)),
    ((-1, 6), (4, -5)),
    ((6, -1), (-5, 4)),
    ((-5, 4), (6, -3)),
    ((2, -6), (-3, 5)),
)
_REFERENCE_VECTOR_CASES: Tuple[Tuple[GraphPoint, GraphPoint, GraphPoint], ...] = (
    ((-5, -4), (-2, 1), (1, -6)),
    ((4, -5), (-1, -2), (2, 1)),
    ((-6, 3), (-1, 0), (-2, 5)),
    ((3, 4), (-2, -1), (6, 1)),
    ((-3, 6), (2, 2), (-5, 0)),
    ((5, 2), (1, 6), (2, -5)),
    ((-4, -2), (1, 2), (-2, -4)),
    ((2, -6), (-3, -2), (5, 1)),
)
_VERTICAL_REFLECTION_CASES: Tuple[Tuple[GraphPoint, int], ...] = (
    ((-4, 1), 1),
    ((5, -3), 0),
    ((-6, 4), -2),
    ((3, 6), -1),
    ((1, -5), 3),
    ((6, 2), 2),
    ((-5, -4), -1),
    ((4, 3), 1),
)
_HORIZONTAL_REFLECTION_CASES: Tuple[Tuple[GraphPoint, int], ...] = (
    ((-4, 1), 3),
    ((5, -3), -1),
    ((-6, 4), 0),
    ((3, 6), 2),
    ((1, -5), -2),
    ((6, 2), -1),
    ((-5, -4), 1),
    ((4, 3), -2),
)
_ROTATION_CASES: Tuple[Tuple[GraphPoint, GraphPoint, str], ...] = (
    ((0, 0), (3, 2), "clockwise"),
    ((0, 0), (3, 2), "counterclockwise"),
    ((1, -1), (5, 1), "clockwise"),
    ((1, -1), (5, 1), "counterclockwise"),
    ((-2, 2), (1, 6), "clockwise"),
    ((-2, 2), (1, 6), "counterclockwise"),
    ((2, 1), (-2, 4), "clockwise"),
    ((2, 1), (-2, 4), "counterclockwise"),
    ((-1, -2), (-5, 1), "clockwise"),
    ((-1, -2), (-5, 1), "counterclockwise"),
)


def _split_defaults_for_task(config_key: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    return split_scene_generation_rendering_prompt_defaults(
        _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
        task_id=str(config_key),
    )


def _select_winner_label(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    label_pool: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    labels = tuple(str(label) for label in label_pool)
    explicit = params.get("winner_label", params.get("answer_label"))
    if explicit is not None:
        label = str(explicit)
        if label not in set(labels):
            raise ValueError(f"winner_label={label!r} is not in label pool {labels!r}")
        return label, {label: 1.0}
    selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.winner_label",
    )
    return str(labels[int(selection_index) % len(labels)]), _probability_map(labels)


def _resolve_query(
    *,
    namespace: str,
    query_ids: Sequence[str],
    label_pool: Sequence[str],
    instance_seed: int,
    params: Mapping[str, Any],
) -> _ResolvedQuery:
    query_id, query_probabilities = select_geometry_query_id(
        params,
        query_ids=tuple(query_ids),
        task_id=str(namespace),
        instance_seed=int(instance_seed),
    )
    winner_label, winner_probabilities = _select_winner_label(
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
        label_pool=tuple(label_pool),
    )
    return _ResolvedQuery(
        query_id=str(query_id),
        query_probabilities=dict(query_probabilities),
        winner_label=str(winner_label),
        winner_label_probabilities=dict(winner_probabilities),
        label_pool=tuple(str(label) for label in label_pool),
    )


def _case_index(*, params: Mapping[str, Any], instance_seed: int, namespace: str, query_id: str, count: int) -> int:
    explicit = params.get("case_index")
    if explicit is not None:
        return int(explicit) % int(count)
    selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.{query_id}.case",
    )
    return int(selection_index) % int(count)


def _in_bounds(point: GraphPoint, *, max_abs: int) -> bool:
    return abs(int(point[0])) <= int(max_abs) and abs(int(point[1])) <= int(max_abs)


def _add_candidate(
    candidates: List[GraphPoint],
    point: GraphPoint,
    *,
    occupied: set[GraphPoint],
    max_abs: int,
) -> None:
    graph_point = (int(point[0]), int(point[1]))
    if graph_point in occupied or graph_point in set(candidates):
        return
    if not _in_bounds(graph_point, max_abs=int(max_abs)):
        return
    candidates.append(graph_point)


def _sample_problem(
    *,
    namespace: str,
    query_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
) -> _AlgebraProblem:
    if str(query_id) in set(MISSING_ENDPOINT_QUERY_IDS):
        index = _case_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=str(namespace),
            query_id=str(query_id),
            count=len(_MIDPOINT_CASES),
        )
        endpoint, midpoint = _MIDPOINT_CASES[int(index)]
        missing = ((2 * int(midpoint[0])) - int(endpoint[0]), (2 * int(midpoint[1])) - int(endpoint[1]))
        if str(query_id) == "missing_endpoint_from_midpoint":
            return _AlgebraProblem(
                query_id=str(query_id),
                known_points_by_label={"P": endpoint, "M": midpoint},
                target_label_name="Q",
                target_point=tuple(missing),
                formula="Q = 2M - P",
                transform_text="M is midpoint",
                guide_segments=(("P", "M", "solid"),),
            )
        return _AlgebraProblem(
            query_id=str(query_id),
            known_points_by_label={"Q": endpoint, "M": midpoint},
            target_label_name="P",
            target_point=tuple(missing),
            formula="P = 2M - Q",
            transform_text="M is midpoint",
            guide_segments=(("Q", "M", "solid"),),
        )

    if str(query_id) in set(SECTION_POINT_QUERY_IDS):
        index = _case_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=str(namespace),
            query_id=str(query_id),
            count=len(_SECTION_CASES),
        )
        point_p, point_q = _SECTION_CASES[int(index)]
        dx = int(point_q[0]) - int(point_p[0])
        dy = int(point_q[1]) - int(point_p[1])
        if int(dx) % 3 != 0 or int(dy) % 3 != 0:
            raise RuntimeError("section point case must have displacement divisible by 3")
        step = 1 if str(query_id) == "one_third_from_p_to_q" else 2
        target = (int(point_p[0]) + (int(step) * int(dx) // 3), int(point_p[1]) + (int(step) * int(dy) // 3))
        return _AlgebraProblem(
            query_id=str(query_id),
            known_points_by_label={"P": point_p, "Q": point_q},
            target_label_name="R",
            target_point=tuple(target),
            formula=f"R = P + {int(step)}/3 * (Q - P)",
            guide_segments=(("P", "Q", "solid"),),
        )

    if str(query_id) == "translate_point":
        index = _case_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=str(namespace),
            query_id=str(query_id),
            count=len(_TRANSLATION_CASES),
        )
        source, vector = _TRANSLATION_CASES[int(index)]
        target = (int(source[0]) + int(vector[0]), int(source[1]) + int(vector[1]))
        return _AlgebraProblem(
            query_id=str(query_id),
            known_points_by_label={"P": source},
            target_label_name="P'",
            target_point=tuple(target),
            formula="P' = P + translation vector",
            transform_text=f"translate P by ({int(vector[0])}, {int(vector[1])})",
        )

    if str(query_id) == "translate_by_reference_vector":
        index = _case_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=str(namespace),
            query_id=str(query_id),
            count=len(_REFERENCE_VECTOR_CASES),
        )
        point_r, point_s, source = _REFERENCE_VECTOR_CASES[int(index)]
        vector = (int(point_s[0]) - int(point_r[0]), int(point_s[1]) - int(point_r[1]))
        target = (int(source[0]) + int(vector[0]), int(source[1]) + int(vector[1]))
        return _AlgebraProblem(
            query_id=str(query_id),
            known_points_by_label={"R": point_r, "S": point_s, "P": source},
            target_label_name="P'",
            target_point=tuple(target),
            formula="P' = P + (S - R)",
            transform_text="translate P by vector RS",
            guide_segments=(("R", "S", "arrow"),),
        )

    if str(query_id) == "reflect_over_vertical_line":
        index = _case_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=str(namespace),
            query_id=str(query_id),
            count=len(_VERTICAL_REFLECTION_CASES),
        )
        source, x_value = _VERTICAL_REFLECTION_CASES[int(index)]
        target = ((2 * int(x_value)) - int(source[0]), int(source[1]))
        return _AlgebraProblem(
            query_id=str(query_id),
            known_points_by_label={"P": source},
            target_label_name="P'",
            target_point=tuple(target),
            formula="P' = reflection of P across x = k",
            transform_text=f"reflect P over x = {int(x_value)}",
            transform_line={"axis": "x", "value": int(x_value)},
        )

    if str(query_id) == "reflect_over_horizontal_line":
        index = _case_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=str(namespace),
            query_id=str(query_id),
            count=len(_HORIZONTAL_REFLECTION_CASES),
        )
        source, y_value = _HORIZONTAL_REFLECTION_CASES[int(index)]
        target = (int(source[0]), (2 * int(y_value)) - int(source[1]))
        return _AlgebraProblem(
            query_id=str(query_id),
            known_points_by_label={"P": source},
            target_label_name="P'",
            target_point=tuple(target),
            formula="P' = reflection of P across y = k",
            transform_text=f"reflect P over y = {int(y_value)}",
            transform_line={"axis": "y", "value": int(y_value)},
        )

    if str(query_id) == "rotate_90_about_marked_center":
        index = _case_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=str(namespace),
            query_id=str(query_id),
            count=len(_ROTATION_CASES),
        )
        center, source, direction = _ROTATION_CASES[int(index)]
        dx = int(source[0]) - int(center[0])
        dy = int(source[1]) - int(center[1])
        if str(direction) == "clockwise":
            rotated = (int(dy), -int(dx))
        else:
            rotated = (-int(dy), int(dx))
        target = (int(center[0]) + int(rotated[0]), int(center[1]) + int(rotated[1]))
        return _AlgebraProblem(
            query_id=str(query_id),
            known_points_by_label={"O": center, "P": source},
            target_label_name="P'",
            target_point=tuple(target),
            formula=f"P' = 90-degree {direction} rotation of P about O",
            transform_text=f"rotate P 90 degrees {direction} about O",
            guide_segments=(("O", "P", "solid"),),
        )

    raise ValueError(f"unsupported coordinate algebra query: {query_id}")


def _candidate_labels_for_query(query: _ResolvedQuery, *, candidate_count: int) -> Tuple[str, ...]:
    labels = tuple(query.label_pool[: int(candidate_count)])
    if str(query.winner_label) not in set(labels):
        labels = tuple([str(query.winner_label), *[label for label in labels if label != str(query.winner_label)]])
        labels = labels[: int(candidate_count)]
    return labels


def _common_distractors(problem: _AlgebraProblem, *, max_abs: int) -> Tuple[GraphPoint, ...]:
    target = tuple(problem.target_point)
    known_points = dict(problem.known_points_by_label)
    distractors: List[GraphPoint] = []

    if str(problem.query_id) in set(MISSING_ENDPOINT_QUERY_IDS):
        endpoint = next(point for label, point in known_points.items() if str(label) != "M")
        midpoint = known_points["M"]
        _add_candidate(distractors, midpoint, occupied=set(), max_abs=int(max_abs))
        _add_candidate(distractors, (int(endpoint[0]) + int(midpoint[0]), int(endpoint[1]) + int(midpoint[1])), occupied=set(), max_abs=int(max_abs))
        _add_candidate(distractors, (int(endpoint[0]) - int(midpoint[0]), int(endpoint[1]) - int(midpoint[1])), occupied=set(), max_abs=int(max_abs))
        _add_candidate(distractors, ((2 * int(endpoint[0])) - int(midpoint[0]), (2 * int(endpoint[1])) - int(midpoint[1])), occupied=set(), max_abs=int(max_abs))
    elif str(problem.query_id) in set(SECTION_POINT_QUERY_IDS):
        point_p = known_points["P"]
        point_q = known_points["Q"]
        dx = int(point_q[0]) - int(point_p[0])
        dy = int(point_q[1]) - int(point_p[1])
        one_third = (int(point_p[0]) + (int(dx) // 3), int(point_p[1]) + (int(dy) // 3))
        two_thirds = (int(point_p[0]) + (2 * int(dx) // 3), int(point_p[1]) + (2 * int(dy) // 3))
        reverse_one_third = (int(point_q[0]) - (int(dx) // 3), int(point_q[1]) - (int(dy) // 3))
        midpoint = ((int(point_p[0]) + int(point_q[0])) // 2, (int(point_p[1]) + int(point_q[1])) // 2)
        for point in (one_third, two_thirds, reverse_one_third, midpoint):
            _add_candidate(distractors, point, occupied=set(), max_abs=int(max_abs))
        _add_candidate(distractors, (int(target[0]) + (int(dx) // 3), int(target[1]) + (int(dy) // 3)), occupied=set(), max_abs=int(max_abs))
        _add_candidate(distractors, (int(target[0]) - (int(dx) // 3), int(target[1]) - (int(dy) // 3)), occupied=set(), max_abs=int(max_abs))
    elif str(problem.query_id) == "translate_point":
        source = known_points["P"]
        dx = int(target[0]) - int(source[0])
        dy = int(target[1]) - int(source[1])
        _add_candidate(distractors, (int(source[0]) + dx, int(source[1])), occupied=set(), max_abs=int(max_abs))
        _add_candidate(distractors, (int(source[0]), int(source[1]) + dy), occupied=set(), max_abs=int(max_abs))
        _add_candidate(distractors, (int(source[0]) - dx, int(source[1]) - dy), occupied=set(), max_abs=int(max_abs))
        _add_candidate(distractors, (int(source[0]) + dy, int(source[1]) + dx), occupied=set(), max_abs=int(max_abs))
    elif str(problem.query_id) == "translate_by_reference_vector":
        source = known_points["P"]
        point_r = known_points["R"]
        point_s = known_points["S"]
        dx = int(point_s[0]) - int(point_r[0])
        dy = int(point_s[1]) - int(point_r[1])
        _add_candidate(distractors, (int(source[0]) + dx, int(source[1])), occupied=set(), max_abs=int(max_abs))
        _add_candidate(distractors, (int(source[0]), int(source[1]) + dy), occupied=set(), max_abs=int(max_abs))
        _add_candidate(distractors, (int(source[0]) - dx, int(source[1]) - dy), occupied=set(), max_abs=int(max_abs))
        _add_candidate(distractors, (int(source[0]) + dy, int(source[1]) + dx), occupied=set(), max_abs=int(max_abs))
        _add_candidate(distractors, (int(point_r[0]) + int(source[0]) - int(point_s[0]), int(point_r[1]) + int(source[1]) - int(point_s[1])), occupied=set(), max_abs=int(max_abs))
    elif str(problem.query_id) == "reflect_over_vertical_line":
        source = known_points["P"]
        line_value = int(problem.transform_line["value"]) if problem.transform_line else 0
        _add_candidate(distractors, (-int(source[0]), int(source[1])), occupied=set(), max_abs=int(max_abs))
        _add_candidate(distractors, (int(target[0]), -int(target[1])), occupied=set(), max_abs=int(max_abs))
        _add_candidate(distractors, (int(source[0]), (2 * line_value) - int(source[1])), occupied=set(), max_abs=int(max_abs))
        _add_candidate(distractors, (int(target[0]) + 1, int(target[1])), occupied=set(), max_abs=int(max_abs))
        _add_candidate(distractors, (int(target[0]) - 1, int(target[1])), occupied=set(), max_abs=int(max_abs))
    elif str(problem.query_id) == "reflect_over_horizontal_line":
        source = known_points["P"]
        line_value = int(problem.transform_line["value"]) if problem.transform_line else 0
        _add_candidate(distractors, (int(source[0]), -int(source[1])), occupied=set(), max_abs=int(max_abs))
        _add_candidate(distractors, (-int(target[0]), int(target[1])), occupied=set(), max_abs=int(max_abs))
        _add_candidate(distractors, ((2 * line_value) - int(source[0]), int(source[1])), occupied=set(), max_abs=int(max_abs))
        _add_candidate(distractors, (int(target[0]), int(target[1]) + 1), occupied=set(), max_abs=int(max_abs))
        _add_candidate(distractors, (int(target[0]), int(target[1]) - 1), occupied=set(), max_abs=int(max_abs))
    elif str(problem.query_id) == "rotate_90_about_marked_center":
        center = known_points["O"]
        source = known_points["P"]
        dx = int(source[0]) - int(center[0])
        dy = int(source[1]) - int(center[1])
        clockwise = (int(center[0]) + int(dy), int(center[1]) - int(dx))
        counterclockwise = (int(center[0]) - int(dy), int(center[1]) + int(dx))
        half_turn = (int(center[0]) - int(dx), int(center[1]) - int(dy))
        reflect_x_through_center = ((2 * int(center[0])) - int(source[0]), int(source[1]))
        reflect_y_through_center = (int(source[0]), (2 * int(center[1])) - int(source[1]))
        for point in (clockwise, counterclockwise, half_turn, reflect_x_through_center, reflect_y_through_center):
            _add_candidate(distractors, point, occupied=set(), max_abs=int(max_abs))

    for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1), (2, 0), (0, 2), (-2, 0), (0, -2)):
        _add_candidate(distractors, (int(target[0]) + int(dx), int(target[1]) + int(dy)), occupied=set(), max_abs=int(max_abs))
    return tuple(distractors)


def _sample_candidate_points(
    problem: _AlgebraProblem,
    *,
    query: _ResolvedQuery,
    candidate_labels: Sequence[str],
    rng,
    max_abs: int,
) -> Dict[str, GraphPoint]:
    occupied = set(problem.known_points_by_label.values()) | {tuple(problem.target_point)}
    candidate_points_by_label: Dict[str, GraphPoint] = {str(query.winner_label): tuple(problem.target_point)}
    distractors: List[GraphPoint] = []
    for point in _common_distractors(problem, max_abs=int(max_abs)):
        _add_candidate(distractors, point, occupied=occupied, max_abs=int(max_abs))
    rng.shuffle(distractors)

    for label in candidate_labels:
        if str(label) == str(query.winner_label):
            continue
        while distractors:
            point = distractors.pop(0)
            if point not in occupied and point not in set(candidate_points_by_label.values()):
                candidate_points_by_label[str(label)] = tuple(point)
                occupied.add(tuple(point))
                break
        if str(label) in candidate_points_by_label:
            continue
        for _ in range(500):
            point = (int(rng.randint(-int(max_abs), int(max_abs))), int(rng.randint(-int(max_abs), int(max_abs))))
            if point in occupied or point in set(candidate_points_by_label.values()):
                continue
            candidate_points_by_label[str(label)] = tuple(point)
            occupied.add(tuple(point))
            break
        if str(label) not in candidate_points_by_label:
            raise RuntimeError("failed to sample coordinate algebra distractor")

    return dict(candidate_points_by_label)


def _draw_dashed_axis_line(
    draw: ImageDraw.ImageDraw,
    *,
    context: Any,
    line: Mapping[str, int],
    max_abs: int,
    color: Color,
) -> None:
    scale = int(context.scene_scale)
    line_value = int(line["value"])
    if str(line["axis"]) == "x":
        start = graph_units_to_pixel((line_value, -int(max_abs) - 1), graph_origin=context.graph_origin, spacing=int(context.graph_spacing))
        end = graph_units_to_pixel((line_value, int(max_abs) + 1), graph_origin=context.graph_origin, spacing=int(context.graph_spacing))
    else:
        start = graph_units_to_pixel((-int(max_abs) - 1, line_value), graph_origin=context.graph_origin, spacing=int(context.graph_spacing))
        end = graph_units_to_pixel((int(max_abs) + 1, line_value), graph_origin=context.graph_origin, spacing=int(context.graph_spacing))
    start_scaled = scale_point(start, scale)
    end_scaled = scale_point(end, scale)
    if str(line["axis"]) == "x":
        y0, y1 = sorted([float(start_scaled[1]), float(end_scaled[1])])
        x = float(start_scaled[0])
        dash = max(8, 7 * scale)
        gap = max(6, 5 * scale)
        cursor = y0
        while cursor < y1:
            draw.line([(x, cursor), (x, min(y1, cursor + dash))], fill=color, width=max(2, 2 * scale))
            cursor += dash + gap
    else:
        x0, x1 = sorted([float(start_scaled[0]), float(end_scaled[0])])
        y = float(start_scaled[1])
        dash = max(8, 7 * scale)
        gap = max(6, 5 * scale)
        cursor = x0
        while cursor < x1:
            draw.line([(cursor, y), (min(x1, cursor + dash), y)], fill=color, width=max(2, 2 * scale))
            cursor += dash + gap


def _draw_label_box(
    draw: ImageDraw.ImageDraw,
    *,
    context: Any,
    text: str,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
) -> List[int]:
    scale = int(context.scene_scale)
    font_size = _resolve_int_param(params, rendering_defaults, "transform_label_font_size", _DEFAULTS.transform_label_font_size)
    font = load_font(max(12, int(font_size) * scale), bold=True)
    left = int(context.graph_panel_layout.panel_bbox_px[0]) + 16
    top = int(context.graph_panel_layout.panel_bbox_px[1]) + 14
    text_bbox = draw.textbbox((left * scale, top * scale), str(text), font=font)
    pad_x = 8 * scale
    pad_y = 5 * scale
    box = [
        int(text_bbox[0] - pad_x),
        int(text_bbox[1] - pad_y),
        int(text_bbox[2] + pad_x),
        int(text_bbox[3] + pad_y),
    ]
    draw.rounded_rectangle(box, radius=5 * scale, fill=(255, 255, 255), outline=(82, 92, 108), width=max(1, scale))
    draw_text_traced(draw,(left * scale, top * scale), str(text), fill=(34, 44, 58), font=font, role="readout", required=False)
    return [int(round(value / float(scale))) for value in box]


def _draw_guide_segments(
    draw: ImageDraw.ImageDraw,
    *,
    context: Any,
    points_by_label: Mapping[str, GraphPoint],
    segments: Sequence[GuideSegment],
    color: Color,
) -> None:
    scale = int(context.scene_scale)
    for start_label, end_label, style in segments:
        if str(start_label) not in points_by_label or str(end_label) not in points_by_label:
            continue
        start_px = scale_point(
            graph_units_to_pixel(points_by_label[str(start_label)], graph_origin=context.graph_origin, spacing=int(context.graph_spacing)),
            scale,
        )
        end_px = scale_point(
            graph_units_to_pixel(points_by_label[str(end_label)], graph_origin=context.graph_origin, spacing=int(context.graph_spacing)),
            scale,
        )
        line_width = max(2, 2 * scale)
        draw.line([start_px, end_px], fill=color, width=line_width)
        if str(style) != "arrow":
            continue
        angle = math.atan2(float(end_px[1]) - float(start_px[1]), float(end_px[0]) - float(start_px[0]))
        arrow_len = 12.0 * float(scale)
        wing = math.pi / 7.0
        p1 = (
            float(end_px[0]) - (arrow_len * math.cos(angle - wing)),
            float(end_px[1]) - (arrow_len * math.sin(angle - wing)),
        )
        p2 = (
            float(end_px[0]) - (arrow_len * math.cos(angle + wing)),
            float(end_px[1]) - (arrow_len * math.sin(angle + wing)),
        )
        draw.polygon([end_px, p1, p2], fill=color)


def _render_scene(
    *,
    namespace: str,
    query: _ResolvedQuery,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
) -> _RenderedScene:
    rng = spawn_rng(int(instance_seed), f"{namespace}.render")
    max_abs = _resolve_int_param(params, generation_defaults, "algebra_graph_abs_max", _DEFAULTS.graph_abs_max)
    candidate_count, option_count_probabilities = resolve_geometry_option_count(
        params=params,
        gen_defaults=generation_defaults,
        field_name="algebra_candidate_count",
        supported_counts=(4, 6),
        task_id=str(namespace),
        instance_seed=int(instance_seed),
    )
    if int(candidate_count) > len(query.label_pool):
        raise ValueError("algebra_candidate_count cannot exceed candidate label pool length")
    candidate_labels = _candidate_labels_for_query(query, candidate_count=int(candidate_count))
    problem = _sample_problem(
        namespace=str(namespace),
        query_id=str(query.query_id),
        instance_seed=int(instance_seed),
        params=params,
    )
    candidate_points_by_label = _sample_candidate_points(
        problem,
        query=query,
        candidate_labels=candidate_labels,
        rng=rng,
        max_abs=int(max_abs),
    )

    context = resolve_graph_scene_context(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        render_defaults=rendering_defaults,
        background_defaults=_BACKGROUND_DEFAULTS,
        fallback_canvas_min=_resolve_int_param(params, rendering_defaults, "algebra_canvas_size_min", _DEFAULTS.canvas_size_min),
        fallback_canvas_max=_resolve_int_param(params, rendering_defaults, "algebra_canvas_size_max", _DEFAULTS.canvas_size_max),
        fallback_cells_min=_resolve_int_param(params, rendering_defaults, "algebra_graph_cells_min", _DEFAULTS.graph_cells_min),
        fallback_cells_max=_resolve_int_param(params, rendering_defaults, "algebra_graph_cells_max", _DEFAULTS.graph_cells_max),
        require_graph_paper_background=True,
        graph_style_overrides={
            "origin_fraction_x": 0.5,
            "origin_fraction_y": 0.5,
            "axis_scale_labels_enabled": True,
            "axis_scale_label_max_abs": max(6, int(max_abs)),
            "origin_label_enabled": False,
        },
    )
    image, draw, background_meta = make_graph_scene_canvas(
        instance_seed=int(instance_seed),
        context=context,
        background_defaults=_BACKGROUND_DEFAULTS,
        require_graph_paper=True,
    )

    marker_radius = _resolve_int_param(params, rendering_defaults, "marker_radius_px", _DEFAULTS.marker_radius_px)
    marker_radius = max(
        _resolve_int_param(params, rendering_defaults, "marker_radius_px_min", _DEFAULTS.marker_radius_px_min),
        min(_resolve_int_param(params, rendering_defaults, "marker_radius_px_max", _DEFAULTS.marker_radius_px_max), int(marker_radius)),
    )
    label_font_size_px = resolve_scene_label_font_size_px(
        canvas_size=int(context.canvas_size),
        graph_spacing=int(context.graph_spacing),
        scene_scale=int(context.scene_scale),
        min_px=_resolve_int_param(params, rendering_defaults, "label_font_size_min", _DEFAULTS.label_font_size_min),
        max_px=_resolve_int_param(params, rendering_defaults, "label_font_size_max", _DEFAULTS.label_font_size_max),
    )
    label_offset_px = _resolve_int_param(params, rendering_defaults, "label_offset_px", _DEFAULTS.label_offset_px)
    label_stroke_width = _resolve_int_param(params, rendering_defaults, "label_stroke_width", _DEFAULTS.label_stroke_width)
    known_style = _sample_marker_style(rng, params=params, defaults=rendering_defaults, key="known_marker_style")
    midpoint_style = "diamond" if str(known_style) != "diamond" else "ring"
    candidate_style = _sample_marker_style(rng, params=params, defaults=rendering_defaults, key="candidate_marker_style")
    known_color, candidate_color, color_meta = _resolve_marker_colors(rng)
    midpoint_color = (36, 115, 170) if known_color != (36, 115, 170) else (142, 86, 46)
    axis_color = (72, 82, 98)
    guide_color = (94, 103, 118)

    if problem.transform_line is not None:
        _draw_dashed_axis_line(
            draw,
            context=context,
            line=problem.transform_line,
            max_abs=int(max_abs),
            color=axis_color,
        )
    if problem.guide_segments:
        _draw_guide_segments(
            draw,
            context=context,
            points_by_label=problem.known_points_by_label,
            segments=problem.guide_segments,
            color=guide_color,
        )
    label_box_bbox = None
    if problem.transform_text:
        label_box_bbox = _draw_label_box(
            draw,
            context=context,
            text=str(problem.transform_text),
            params=params,
            rendering_defaults=rendering_defaults,
        )

    known_points_px_by_label = {
        str(label): graph_units_to_pixel(point, graph_origin=context.graph_origin, spacing=int(context.graph_spacing))
        for label, point in problem.known_points_by_label.items()
    }
    candidate_points_px_by_label = {
        str(label): graph_units_to_pixel(point, graph_origin=context.graph_origin, spacing=int(context.graph_spacing))
        for label, point in candidate_points_by_label.items()
    }
    render_radius = int(marker_radius) * int(context.scene_scale)

    for label, point_px in known_points_px_by_label.items():
        style = midpoint_style if str(label) == "M" else str(known_style)
        color = midpoint_color if str(label) == "M" else known_color
        _draw_marker(
            draw,
            scale_point(point_px, int(context.scene_scale)),
            style=str(style),
            color=color,
            radius=int(render_radius),
            width=max(2, int(context.scene_scale) * 2),
        )

    for label in candidate_labels:
        point_px = candidate_points_px_by_label[str(label)]
        _draw_marker(
            draw,
            scale_point(point_px, int(context.scene_scale)),
            style=str(candidate_style),
            color=candidate_color,
            radius=int(render_radius),
            width=max(2, int(context.scene_scale) * 2),
        )

    blocked_points = [
        *[scale_point(point, int(context.scene_scale)) for point in known_points_px_by_label.values()],
        *[scale_point(candidate_points_px_by_label[str(label)], int(context.scene_scale)) for label in candidate_labels],
    ]
    draw_labeled_points(
        draw,
        points=[scale_point(point, int(context.scene_scale)) for point in known_points_px_by_label.values()],
        labels=list(known_points_px_by_label.keys()),
        label_offset_px=float(label_offset_px) * float(context.scene_scale),
        font_size_px=int(label_font_size_px),
        text_stroke_width=int(label_stroke_width) * int(context.scene_scale),
        blocked_points=blocked_points,
        blocked_point_clearance_px=float(render_radius + 6),
        marker_radius_px=0,
        marker_color=known_color,
        label_color=known_color,
        label_stroke_color=(255, 255, 255),
        canvas_size=int(context.canvas_size) * int(context.scene_scale),
    )
    draw_labeled_points(
        draw,
        points=[scale_point(candidate_points_px_by_label[str(label)], int(context.scene_scale)) for label in candidate_labels],
        labels=list(candidate_labels),
        label_offset_px=float(label_offset_px) * float(context.scene_scale),
        font_size_px=int(label_font_size_px),
        text_stroke_width=int(label_stroke_width) * int(context.scene_scale),
        blocked_points=blocked_points,
        blocked_point_clearance_px=float(render_radius + 6),
        marker_radius_px=0,
        marker_color=candidate_color,
        label_color=candidate_color,
        label_stroke_color=(255, 255, 255),
        canvas_size=int(context.canvas_size) * int(context.scene_scale),
    )

    candidate_bboxes_by_label = {
        str(label): _marker_bbox(
            candidate_points_px_by_label[str(label)],
            radius=int(marker_radius),
            canvas_width=int(context.canvas_size),
            canvas_height=int(context.canvas_size),
        )
        for label in candidate_labels
    }
    image, background_meta_final, post_noise_meta = finalize_graph_scene_image(
        image,
        instance_seed=int(instance_seed),
        context=context,
        background_meta=background_meta,
        noise_defaults=_NOISE_DEFAULTS,
    )
    marker_meta = {
        "known_marker_style": str(known_style),
        "midpoint_marker_style": str(midpoint_style),
        "candidate_marker_style": str(candidate_style),
        "marker_radius_px": int(marker_radius),
        "midpoint_color": list(midpoint_color),
        "transform_axis_color": list(axis_color),
        "guide_segment_color": list(guide_color),
        **dict(color_meta),
    }
    return _RenderedScene(
        problem=problem,
        candidate_points_by_label=dict(candidate_points_by_label),
        candidate_bboxes_by_label=dict(candidate_bboxes_by_label),
        known_points_px_by_label=dict(known_points_px_by_label),
        candidate_points_px_by_label=dict(candidate_points_px_by_label),
        label_box_bbox_px=list(label_box_bbox) if label_box_bbox is not None else None,
        marker_meta=dict(marker_meta),
        image=image,
        background_meta=dict(background_meta_final),
        post_noise_meta=dict(post_noise_meta),
        render_spec_extra={
            "canvas_size": int(context.canvas_size),
            "coord_space": "pixel",
            "graph_coordinate_frame": dict(context.graph_frame),
            "graph_paper_grid": graph_paper_grid_from_frame(context.graph_frame),
            "scene_scale": int(context.scene_scale),
            **dict(context.graph_layout_metadata),
        },
        option_count_probabilities=dict(option_count_probabilities),
    )




def _trace_payload(
    *,
    namespace: str,
    query: _ResolvedQuery,
    rendered: _RenderedScene,
    prompt_defaults: Mapping[str, Any],
    prompt_artifacts: Any,
    annotation_value: List[List[float]],
) -> Dict[str, Any]:
    candidate_trace = {
        str(label): {
            "point_graph": [int(value) for value in rendered.candidate_points_by_label[str(label)]],
            "point_px": [float(value) for value in rendered.candidate_points_px_by_label[str(label)]],
            "bbox_px": list(rendered.candidate_bboxes_by_label[str(label)]),
            "is_answer": str(label) == str(query.winner_label),
        }
        for label in sorted(rendered.candidate_points_by_label)
    }
    known_trace = {
        str(label): {
            "point_graph": [int(value) for value in point],
            "point_px": [float(value) for value in rendered.known_points_px_by_label[str(label)]],
        }
        for label, point in rendered.problem.known_points_by_label.items()
    }
    relations = {
        "scene_id": SCENE_ID,
        "query_id": str(query.query_id),
        "query_id_probabilities": dict(query.query_probabilities),
        "winner_label": str(query.winner_label),
        "target_label_name": str(rendered.problem.target_label_name),
        "target_point_graph": [int(value) for value in rendered.problem.target_point],
        "formula": str(rendered.problem.formula),
    }
    if rendered.problem.transform_text is not None:
        relations["transform_text"] = str(rendered.problem.transform_text)
    if rendered.problem.transform_line is not None:
        relations["transform_line"] = dict(rendered.problem.transform_line)
    if rendered.problem.guide_segments:
        relations["guide_segments"] = [list(segment) for segment in rendered.problem.guide_segments]
    return {
        "scene_ir": {
            "scene_kind": "geometry_coordinate_algebra",
            "entities": [
                {"entity_type": "known_point", "label": str(label), **dict(payload)}
                for label, payload in known_trace.items()
            ]
            + [
                {"entity_type": "candidate_point", "label": str(label), **dict(payload)}
                for label, payload in candidate_trace.items()
            ],
            "relations": dict(relations),
        },
        "query_spec": {
            "query_id": str(query.query_id),
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": {
                "scene_id": SCENE_ID,
                "query_id": str(query.query_id),
                "query_id_probabilities": dict(query.query_probabilities),
                "winner_label": str(query.winner_label),
                "winner_label_probabilities": dict(query.winner_label_probabilities),
                "candidate_label_pool": list(rendered.candidate_points_by_label.keys()),
                "algebra_candidate_count_probabilities": dict(rendered.option_count_probabilities),
                "target_label_name": str(rendered.problem.target_label_name),
            },
        },
        "render_spec": {
            **dict(rendered.render_spec_extra),
            "scene_id": SCENE_ID,
            "marker_style": dict(rendered.marker_meta),
            "label_box_bbox_px": list(rendered.label_box_bbox_px) if rendered.label_box_bbox_px else None,
            "post_image_noise": dict(rendered.post_noise_meta),
            "background_style": dict(rendered.background_meta),
            "algebra_candidate_count_probabilities": dict(rendered.option_count_probabilities),
        },
        "render_map": {
            "coord_space": "pixel",
            "known_points_graph_by_label": {
                str(label): [int(value) for value in point] for label, point in rendered.problem.known_points_by_label.items()
            },
            "known_points_px_by_label": {
                str(label): [float(value) for value in point] for label, point in rendered.known_points_px_by_label.items()
            },
            "candidate_points_graph_by_label": {
                str(label): [int(value) for value in point] for label, point in rendered.candidate_points_by_label.items()
            },
            "candidate_points_px_by_label": {
                str(label): [float(value) for value in point] for label, point in rendered.candidate_points_px_by_label.items()
            },
            "candidate_bboxes_px_by_label": dict(rendered.candidate_bboxes_by_label),
        },
        "execution_trace": {
            "scene_id": SCENE_ID,
            "query_id": str(query.query_id),
            "answer_type": "option_letter",
            "answer_value": str(query.winner_label),
            "target_label_name": str(rendered.problem.target_label_name),
            "target_point_graph": [int(value) for value in rendered.problem.target_point],
            "formula": str(rendered.problem.formula),
            "transform_text": rendered.problem.transform_text,
            "transform_line": dict(rendered.problem.transform_line) if rendered.problem.transform_line is not None else None,
            "guide_segments": [list(segment) for segment in rendered.problem.guide_segments],
            "known_points_by_label": dict(known_trace),
            "candidate_points_by_label": dict(candidate_trace),
            "query_id_probabilities": dict(query.query_probabilities),
            "algebra_candidate_count_probabilities": dict(rendered.option_count_probabilities),
        },
        "witness_symbolic": {
            "type": "coordinate_algebra_candidate_point",
            "query_id": str(query.query_id),
            "answer_label": str(query.winner_label),
            "target_label_name": str(rendered.problem.target_label_name),
            "target_point_graph": [int(value) for value in rendered.problem.target_point],
            "known_points_graph_by_label": {
                str(label): [int(value) for value in point] for label, point in rendered.problem.known_points_by_label.items()
            },
            "formula": str(rendered.problem.formula),
        },
        "projected_annotation": {
            "type": "point_set",
            "point_set": list(annotation_value),
            "pixel_point_set": list(annotation_value),
            "candidate_points_px_by_label": {
                str(label): [float(value) for value in point]
                for label, point in rendered.candidate_points_px_by_label.items()
            },
        },
    }


def _candidate_point_annotation(rendered: _RenderedScene, label: str) -> List[List[float]]:
    point = rendered.candidate_points_px_by_label[str(label)]
    return [[float(point[0]), float(point[1])]]


def build_algebra_artifacts(
    *,
    namespace: str,
    config_key: str,
    query_ids: Sequence[str],
    scene_key: str,
    instance_seed: int,
    params: Dict[str, Any],
) -> AlgebraArtifacts:
    generation_defaults, rendering_defaults, prompt_defaults_all = _split_defaults_for_task(str(config_key))
    label_pool = _resolve_label_pool(params, generation_defaults, "algebra_candidate_labels", DEFAULT_LABEL_POOL)
    query = _resolve_query(
        namespace=str(namespace),
        query_ids=tuple(query_ids),
        label_pool=label_pool,
        instance_seed=int(instance_seed),
        params=params,
    )
    rendered = _render_scene(
        namespace=str(namespace),
        query=query,
        instance_seed=int(instance_seed),
        params=params,
        generation_defaults=generation_defaults,
        rendering_defaults=rendering_defaults,
    )
    prompt_defaults = required_group_defaults(
        prompt_defaults_all,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description",
            "annotation_hint_candidate_point",
            "answer_hint_option_letter",
        ),
        context=f"prompt defaults for {config_key}",
    )
    annotation_value = _candidate_point_annotation(rendered, str(query.winner_label))
    json_example, json_example_answer_only = resolve_prompt_json_examples(
        prompt_defaults_all,
        annotation_value=annotation_value,
        answer_type="option_letter",
    )
    prompt_selection = render_scene_prompt_variants(
        domain="geometry",
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults.get("scene_key", scene_key)),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(query.query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(prompt_defaults["object_description"]),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(prompt_defaults["annotation_hint_candidate_point"]),
            "answer_hint": str(prompt_defaults["answer_hint_option_letter"]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        },
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    trace_payload = _trace_payload(
        namespace=str(namespace),
        query=query,
        rendered=rendered,
        prompt_defaults=prompt_defaults,
        prompt_artifacts=prompt_artifacts,
        annotation_value=annotation_value,
    )

