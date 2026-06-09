"""Circle centerline overlap measurement tasks."""

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
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.prompt_json_example import dump_prompt_json_examples
from ...shared.text_rendering import load_font
from ..shared.complexity import build_geometry_measurement_complexity, normalize_linear
from ..shared.diagram_style import prepare_geometry_diagram_style_and_background
from ..shared.fixed_query_task import geometry_selected_probability_map as _probability_map
from ..shared.measurement_rendering import (
    assert_bboxes_inside as _assert_bboxes_inside,
    bbox_from_points,
    bbox_to_list,
    draw_dimension_line as _draw_dimension,
    draw_readout_centered as _draw_text_centered,
)
from ..shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS
from ..shared.scene_transform import LazySceneTransform
from ..shared.vector2d import (
    add as _add,
    mul as _mul,
    perp as _perp,
    point_to_list as _point_to_list,
    sub as _sub,
    unit as _unit,
)

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

SCENE_ID = "circle_centerline_overlap"
TASK_GROUP = "measurement"
TASK_ID = "task_geometry__circle_centerline_overlap__segment_length_value"
PROMPT_BUNDLE_ID = "geometry_circle_centerline_overlap_v0"
QUERY_ID_CENTER_DISTANCE = "center_distance_from_overlap"
QUERY_ID_BOUNDARY_SEGMENT = "boundary_segment_from_overlap"
QUERY_IDS: Tuple[str, ...] = (QUERY_ID_CENTER_DISTANCE, QUERY_ID_BOUNDARY_SEGMENT)
LABEL_MODES: Tuple[str, ...] = ("radius", "diameter")
BOUNDARY_PAIRS: Tuple[str, ...] = ("AB", "BC")
BOUNDARY_TARGET_ROLES: Tuple[str, ...] = ("left_center_to_right_boundary", "left_boundary_to_right_center")

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", TASK_GROUP)


@dataclass(frozen=True)
class _OverlapCase:
    radius_a: int
    radius_b: int
    radius_c: int
    overlap_ab: int
    overlap_bc: int

    @property
    def distance_ab(self) -> int:
        return int(self.radius_a) + int(self.radius_b) - int(self.overlap_ab)

    @property
    def distance_bc(self) -> int:
        return int(self.radius_b) + int(self.radius_c) - int(self.overlap_bc)

    @property
    def distance_ac(self) -> int:
        return int(self.distance_ab) + int(self.distance_bc)

    @property
    def key(self) -> str:
        return (
            f"ra{self.radius_a}_rb{self.radius_b}_rc{self.radius_c}"
            f"_oab{self.overlap_ab}_obc{self.overlap_bc}"
        )


_CASES: Tuple[_OverlapCase, ...] = (
    _OverlapCase(5, 15, 5, 2, 2),
    _OverlapCase(6, 14, 8, 3, 4),
    _OverlapCase(7, 12, 6, 2, 3),
    _OverlapCase(6, 13, 11, 3, 2),
    _OverlapCase(8, 16, 7, 4, 3),
    _OverlapCase(6, 12, 10, 2, 5),
    _OverlapCase(9, 15, 8, 3, 4),
    _OverlapCase(6, 12, 9, 3, 2),
    _OverlapCase(9, 14, 9, 4, 5),
    _OverlapCase(7, 16, 10, 4, 6),
)


@dataclass(frozen=True)
class _ResolvedProblem:
    task_id: str
    query_id: str
    case: _OverlapCase
    label_mode: str
    boundary_pair: str
    boundary_target_role: str
    answer: int
    target_name: str
    known_segment_name: str
    known_segment_value: int
    target_segment_points: Tuple[str, str]
    known_segment_points: Tuple[str, str]
    query_probabilities: Dict[str, float]
    case_probabilities: Dict[str, float]
    label_mode_probabilities: Dict[str, float]
    boundary_pair_probabilities: Dict[str, float]
    boundary_target_role_probabilities: Dict[str, float]
    answer_support_probabilities: Dict[str, float]


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
    label_backing_color: Color
    fill_colors: Tuple[Color, Color, Color]
    accent_color: Color
    line_width: int
    label_stroke_width: int
    font: Any
    small_font: Any
    diagram_style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]
    scene_transform: LazySceneTransform


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    annotation_keyed_points: Dict[str, Point]
    annotation_roles: Tuple[str, ...]
    label_bboxes: Dict[str, BBox]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]


def _circle_bbox(center: Point, radius: float) -> BBox:
    return (
        float(center[0]) - float(radius),
        float(center[1]) - float(radius),
        float(center[0]) + float(radius),
        float(center[1]) + float(radius),
    )


def _segment_length(case: _OverlapCase, pair: str, role: str) -> int:
    if str(pair) == "AB":
        left_radius, right_radius, distance = int(case.radius_a), int(case.radius_b), int(case.distance_ab)
    elif str(pair) == "BC":
        left_radius, right_radius, distance = int(case.radius_b), int(case.radius_c), int(case.distance_bc)
    else:
        raise ValueError(f"unsupported boundary pair: {pair}")
    if str(role) == "left_center_to_right_boundary":
        return int(distance) - int(right_radius)
    if str(role) == "left_boundary_to_right_center":
        return int(distance) - int(left_radius)
    raise ValueError(f"unsupported boundary target role: {role}")


def _answer_support_probabilities(*, query_id: str, selected: int) -> Dict[str, float]:
    support: set[int] = set()
    if str(query_id) == QUERY_ID_CENTER_DISTANCE:
        support = {int(case.distance_ac) for case in _CASES}
    elif str(query_id) == QUERY_ID_BOUNDARY_SEGMENT:
        for case in _CASES:
            for pair in BOUNDARY_PAIRS:
                for role in BOUNDARY_TARGET_ROLES:
                    support.add(_segment_length(case, pair, role))
    else:
        raise ValueError(f"unsupported query_id: {query_id}")
    return _probability_map(tuple(sorted(support)), selected=int(selected))


def _validate_case(case: _OverlapCase) -> None:
    radii = (int(case.radius_a), int(case.radius_b), int(case.radius_c))
    if min(radii) <= 0:
        raise ValueError("circle radii must be positive")
    if int(case.overlap_ab) <= 0 or int(case.overlap_bc) <= 0:
        raise ValueError("adjacent overlaps must be positive")
    d_ab = int(case.distance_ab)
    d_bc = int(case.distance_bc)
    d_ac = int(case.distance_ac)
    if not (abs(case.radius_a - case.radius_b) + 1 < d_ab < case.radius_a + case.radius_b):
        raise ValueError("AB must be a proper adjacent overlap without containment")
    if not (abs(case.radius_b - case.radius_c) + 1 < d_bc < case.radius_b + case.radius_c):
        raise ValueError("BC must be a proper adjacent overlap without containment")
    if d_ac <= int(case.radius_a) + int(case.radius_c) + 1:
        raise ValueError("non-adjacent circles A and C must not overlap")
    for pair in BOUNDARY_PAIRS:
        for role in BOUNDARY_TARGET_ROLES:
            if _segment_length(case, pair, role) < 3:
                raise ValueError("boundary segment answers must be at least 3")


def _select_case(*, instance_seed: int, params: Mapping[str, Any]) -> tuple[_OverlapCase, Dict[str, float]]:
    explicit = params.get("overlap_case")
    if explicit is not None:
        if not isinstance(explicit, Sequence) or isinstance(explicit, (str, bytes)) or len(explicit) != 5:
            raise ValueError("overlap_case must be [radius_a, radius_b, radius_c, overlap_ab, overlap_bc]")
        case = _OverlapCase(*(int(value) for value in explicit))
        _validate_case(case)
        return case, {case.key: 1.0}
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.overlap_case")
    case = _CASES[int(index) % len(_CASES)]
    probability = 1.0 / float(len(_CASES))
    return case, {candidate.key: probability for candidate in _CASES}


def _select_query(*, instance_seed: int, params: Mapping[str, Any]) -> tuple[str, Dict[str, float]]:
    explicit = params.get("query_id")
    if explicit is not None:
        value = str(explicit)
        if value not in QUERY_IDS:
            raise ValueError(f"query_id must be one of {QUERY_IDS}")
        return value, _probability_map(QUERY_IDS, selected=value)
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.query_id")
    value = QUERY_IDS[int(index) % len(QUERY_IDS)]
    return str(value), _probability_map(QUERY_IDS)


def _select_from_values(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    key: str,
    values: Tuple[str, ...],
) -> tuple[str, Dict[str, float]]:
    explicit = params.get(key)
    if explicit is not None:
        value = str(explicit)
        if value not in values:
            raise ValueError(f"{key} must be one of {values}")
        return value, _probability_map(values, selected=value)
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.{key}")
    value = values[int(index) % len(values)]
    return str(value), _probability_map(values)


def _boundary_names(pair: str, role: str) -> tuple[str, str, tuple[str, str], tuple[str, str]]:
    if str(pair) == "AB":
        left_center, right_center = "A", "B"
        left_boundary, right_boundary = "X", "Y"
    elif str(pair) == "BC":
        left_center, right_center = "B", "C"
        left_boundary, right_boundary = "U", "V"
    else:
        raise ValueError(f"unsupported boundary pair: {pair}")
    if str(role) == "left_center_to_right_boundary":
        target_name = f"{left_center}{right_boundary}"
        known_name = f"{left_boundary}{right_center}"
        target_points = (left_center, right_boundary)
        known_points = (left_boundary, right_center)
    elif str(role) == "left_boundary_to_right_center":
        target_name = f"{left_boundary}{right_center}"
        known_name = f"{left_center}{right_boundary}"
        target_points = (left_boundary, right_center)
        known_points = (left_center, right_boundary)
    else:
        raise ValueError(f"unsupported boundary target role: {role}")
    return target_name, known_name, target_points, known_points


def _resolve_problem(*, instance_seed: int, params: Mapping[str, Any]) -> _ResolvedProblem:
    query_id, query_probabilities = _select_query(instance_seed=int(instance_seed), params=params)
    case, case_probabilities = _select_case(instance_seed=int(instance_seed), params=params)
    label_mode, label_mode_probabilities = _select_from_values(
        params=params,
        instance_seed=int(instance_seed),
        key="label_mode",
        values=LABEL_MODES,
    )
    boundary_pair, boundary_pair_probabilities = _select_from_values(
        params=params,
        instance_seed=int(instance_seed),
        key="boundary_pair",
        values=BOUNDARY_PAIRS,
    )
    boundary_target_role, boundary_target_role_probabilities = _select_from_values(
        params=params,
        instance_seed=int(instance_seed),
        key="boundary_target_role",
        values=BOUNDARY_TARGET_ROLES,
    )

    if query_id == QUERY_ID_CENTER_DISTANCE:
        answer = int(case.distance_ac)
        target_name = "AC"
        known_segment_name = ""
        known_segment_value = 0
        target_segment_points = ("A", "C")
        known_segment_points = ("", "")
        boundary_pair_probabilities = {value: 0.0 for value in BOUNDARY_PAIRS}
        boundary_target_role_probabilities = {value: 0.0 for value in BOUNDARY_TARGET_ROLES}
    else:
        target_name, known_segment_name, target_segment_points, known_segment_points = _boundary_names(
            boundary_pair,
            boundary_target_role,
        )
        answer = _segment_length(case, boundary_pair, boundary_target_role)
        opposite_role = (
            "left_boundary_to_right_center"
            if boundary_target_role == "left_center_to_right_boundary"
            else "left_center_to_right_boundary"
        )
        known_segment_value = _segment_length(case, boundary_pair, opposite_role)

    return _ResolvedProblem(
        task_id=TASK_ID,
        query_id=str(query_id),
        case=case,
        label_mode=str(label_mode),
        boundary_pair=str(boundary_pair),
        boundary_target_role=str(boundary_target_role),
        answer=int(answer),
        target_name=str(target_name),
        known_segment_name=str(known_segment_name),
        known_segment_value=int(known_segment_value),
        target_segment_points=tuple(target_segment_points),
        known_segment_points=tuple(known_segment_points),
        query_probabilities=dict(query_probabilities),
        case_probabilities=dict(case_probabilities),
        label_mode_probabilities=dict(label_mode_probabilities),
        boundary_pair_probabilities=dict(boundary_pair_probabilities),
        boundary_target_role_probabilities=dict(boundary_target_role_probabilities),
        answer_support_probabilities=_answer_support_probabilities(query_id=str(query_id), selected=int(answer)),
    )


def _make_render_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
) -> _RenderContext:
    width = int(params.get("canvas_width", group_default(rendering_defaults, "canvas_width", 820)))
    height = int(params.get("canvas_height", group_default(rendering_defaults, "canvas_height", 600)))
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
    fill_palettes: Tuple[Tuple[Color, Color, Color], ...] = (
        ((238, 246, 255), (255, 247, 231), (241, 248, 239)),
        ((241, 248, 239), (246, 242, 255), (255, 242, 235)),
        ((255, 242, 235), (232, 246, 250), (248, 247, 240)),
        ((248, 247, 240), (234, 242, 255), (246, 242, 255)),
    )
    fill_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_ID}.fill_palette",
    )
    font_size = int(params.get("label_font_size", group_default(rendering_defaults, "label_font_size", 22)))
    small_font_size = int(params.get("small_label_font_size", group_default(rendering_defaults, "small_label_font_size", 18)))
    line_width = int(params.get("line_width", group_default(rendering_defaults, "line_width", 3)))
    label_stroke_width = int(
        params.get(
            "label_stroke_width",
            group_default(rendering_defaults, "label_stroke_width", int(diagram_style.label_stroke_width_px)),
        )
    )
    return _RenderContext(
        image=image,
        draw=ImageDraw.Draw(image),
        width=int(width),
        height=int(height),
        line_color=tuple(int(value) for value in diagram_style.stroke_rgb),
        secondary_color=tuple(int(value) for value in diagram_style.secondary_stroke_rgb),
        label_color=tuple(int(value) for value in diagram_style.label_rgb),
        label_stroke_color=tuple(int(value) for value in diagram_style.label_stroke_rgb),
        label_backing_color=tuple(int(value) for value in diagram_style.panel_fill_rgb),
        fill_colors=tuple(fill_palettes[int(fill_index) % len(fill_palettes)]),
        accent_color=tuple(int(value) for value in diagram_style.accent_rgb),
        line_width=max(2, int(line_width)),
        label_stroke_width=max(0, int(label_stroke_width)),
        font=load_font(max(12, int(font_size))),
        small_font=load_font(max(10, int(small_font_size))),
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


def _circle_measure_label(case: _OverlapCase, label: str, mode: str) -> str:
    radius = {"A": int(case.radius_a), "B": int(case.radius_b), "C": int(case.radius_c)}[str(label)]
    if str(mode) == "diameter":
        return f"d{label}={2 * radius}"
    return f"r{label}={radius}"


def _render_scene(ctx: _RenderContext, problem: _ResolvedProblem, *, instance_seed: int) -> _RenderedScene:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.render.scene")
    case = problem.case
    centers_local: Dict[str, Point] = {
        "A": (0.0, 0.0),
        "B": (float(case.distance_ab), 0.0),
        "C": (float(case.distance_ac), 0.0),
    }
    radii = {"A": int(case.radius_a), "B": int(case.radius_b), "C": int(case.radius_c)}
    points_local: Dict[str, Point] = {
        "A": centers_local["A"],
        "B": centers_local["B"],
        "C": centers_local["C"],
        "X": (centers_local["A"][0] + float(case.radius_a), 0.0),
        "Y": (centers_local["B"][0] - float(case.radius_b), 0.0),
        "U": (centers_local["B"][0] + float(case.radius_b), 0.0),
        "V": (centers_local["C"][0] - float(case.radius_c), 0.0),
    }
    local_min_x = min(centers_local[key][0] - radii[key] for key in centers_local)
    local_max_x = max(centers_local[key][0] + radii[key] for key in centers_local)
    local_max_r = max(radii.values())
    span_x = max(1.0, float(local_max_x - local_min_x))
    span_y = max(1.0, float(local_max_r * 2.0))
    scale = min((float(ctx.width) - 190.0) / span_x, (float(ctx.height) - 180.0) / span_y)
    scale *= float(rng.uniform(0.86, 0.95))
    angle = math.radians(float(rng.uniform(-5.0, 5.0)))
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    local_center = ((local_min_x + local_max_x) / 2.0, 0.0)
    target_center = (
        float(ctx.width) / 2.0 + float(rng.uniform(-22.0, 22.0)),
        float(ctx.height) / 2.0 + float(rng.uniform(-18.0, 18.0)),
    )

    def transform(point: Point) -> Point:
        x = (float(point[0]) - float(local_center[0])) * float(scale)
        y = (float(point[1]) - float(local_center[1])) * float(scale)
        return (
            x * cos_a - y * sin_a + target_center[0],
            x * sin_a + y * cos_a + target_center[1],
        )

    points = {key: transform(value) for key, value in points_local.items()}
    radius_px = {key: float(value) * float(scale) for key, value in radii.items()}
    ctx.scene_transform.resolve(tuple(points.values()))
    points = ctx.scene_transform.keyed_points(points)
    radius_px = {
        key: float(value) * float(ctx.scene_transform.transform.scale)
        for key, value in radius_px.items()
    }
    centerline = _unit(_sub(points["C"], points["A"]))
    normal = _perp(centerline)

    circle_bboxes: Dict[str, BBox] = {}
    for index, label in enumerate(("A", "B", "C")):
        bbox = _circle_bbox(points[label], radius_px[label])
        circle_bboxes[label] = bbox
        ctx.draw.ellipse(bbox, fill=ctx.fill_colors[index], outline=ctx.line_color, width=ctx.line_width)
    _assert_bboxes_inside(
        circle_bboxes.values(),
        width=ctx.width,
        height=ctx.height,
        error_message="circle centerline overlap label too close to canvas edge",
    )

    line_start = _add(points["A"], _mul(centerline, -radius_px["A"] - 16.0))
    line_end = _add(points["C"], _mul(centerline, radius_px["C"] + 16.0))
    ctx.draw.line([line_start, line_end], fill=ctx.secondary_color, width=max(2, ctx.line_width - 1))

    label_bboxes: Dict[str, BBox] = {}
    dot_radius = max(4, int(ctx.line_width + 1))
    boundary_dot_radius = max(3, int(ctx.line_width))
    if problem.query_id == QUERY_ID_CENTER_DISTANCE:
        boundary_label_side = -24.0
        boundary_label_spread = 14.0
    else:
        boundary_label_side = 25.0
        boundary_label_spread = 12.0
    point_offsets = {
        "A": _add(_mul(normal, -26.0), _mul(centerline, -15.0)),
        "B": _mul(normal, -30.0),
        "C": _add(_mul(normal, -26.0), _mul(centerline, 15.0)),
        "X": _add(_mul(normal, boundary_label_side), _mul(centerline, boundary_label_spread)),
        "Y": _add(_mul(normal, boundary_label_side), _mul(centerline, -boundary_label_spread)),
        "U": _add(_mul(normal, boundary_label_side), _mul(centerline, boundary_label_spread)),
        "V": _add(_mul(normal, boundary_label_side), _mul(centerline, -boundary_label_spread)),
    }
    for label in ("A", "B", "C"):
        point = points[label]
        ctx.draw.ellipse(
            (point[0] - dot_radius, point[1] - dot_radius, point[0] + dot_radius, point[1] + dot_radius),
            fill=ctx.line_color,
            outline=ctx.line_color,
            width=1,
        )
        label_bboxes[f"{label}_label"] = _draw_text_centered(ctx, label, _add(point, point_offsets[label]), small=True)
    for label in ("X", "Y", "U", "V"):
        point = points[label]
        ctx.draw.ellipse(
            (
                point[0] - boundary_dot_radius,
                point[1] - boundary_dot_radius,
                point[0] + boundary_dot_radius,
                point[1] + boundary_dot_radius,
            ),
            fill=ctx.accent_color,
            outline=ctx.line_color,
            width=1,
        )
        label_bboxes[f"{label}_label"] = _draw_text_centered(ctx, label, _add(point, point_offsets[label]), small=True)

    for label in ("A", "B", "C"):
        text_point = _add(points[label], _mul(normal, -radius_px[label] - 22.0))
        label_bboxes[f"{label}_measure"] = _draw_text_centered(
            ctx,
            _circle_measure_label(case, label, problem.label_mode),
            text_point,
            small=True,
        )

    annotation: Dict[str, Point]
    if problem.query_id == QUERY_ID_CENTER_DISTANCE:
        label_bboxes["overlap_ab"] = _draw_dimension(
            ctx,
            points["Y"],
            points["X"],
            f"XY={int(case.overlap_ab)}",
            label_offset=_mul(normal, 58.0),
            color=ctx.accent_color,
        )
        label_bboxes["overlap_bc"] = _draw_dimension(
            ctx,
            points["V"],
            points["U"],
            f"UV={int(case.overlap_bc)}",
            label_offset=_mul(normal, 58.0),
            color=ctx.accent_color,
        )
        label_bboxes["target_ac"] = _draw_dimension(
            ctx,
            points["A"],
            points["C"],
            "AC=?",
            label_offset=_mul(normal, -62.0),
            color=ctx.secondary_color,
        )
        annotation = {
            "center_a": points["A"],
            "center_b": points["B"],
            "center_c": points["C"],
            "overlap_ab_left": points["Y"],
            "overlap_ab_right": points["X"],
            "overlap_bc_left": points["V"],
            "overlap_bc_right": points["U"],
        }
    else:
        known_start, known_end = problem.known_segment_points
        target_start, target_end = problem.target_segment_points
        label_bboxes["known_segment"] = _draw_dimension(
            ctx,
            points[known_start],
            points[known_end],
            f"{problem.known_segment_name}={int(problem.known_segment_value)}",
            label_offset=_mul(normal, 46.0),
            color=ctx.accent_color,
        )
        label_bboxes["target_segment"] = _draw_dimension(
            ctx,
            points[target_start],
            points[target_end],
            f"{problem.target_name}=?",
            label_offset=_mul(normal, -52.0),
            color=ctx.secondary_color,
        )
        annotation = {
            "target_start": points[target_start],
            "target_end": points[target_end],
            "known_segment_start": points[known_start],
            "known_segment_end": points[known_end],
            "center_a": points["A"],
            "center_b": points["B"],
            "center_c": points["C"],
        }

    _assert_bboxes_inside(
        label_bboxes.values(),
        width=ctx.width,
        height=ctx.height,
        error_message="circle centerline overlap label too close to canvas edge",
    )
    scene_entities = tuple(
        {
            "entity_id": f"circle_{label.lower()}",
            "entity_type": "circle",
            "label": label,
            "center": _point_to_list(points[label]),
            "radius_units": int(radii[label]),
            "diameter_units": int(2 * radii[label]),
            "radius_px": round(float(radius_px[label]), 3),
            "bbox": bbox_to_list(circle_bboxes[label]),
        }
        for label in ("A", "B", "C")
    )
    render_map = {
        "coord_space": "pixel",
        "query_id": str(problem.query_id),
        "centers": {label: _point_to_list(points[label]) for label in ("A", "B", "C")},
        "boundary_points": {label: _point_to_list(points[label]) for label in ("X", "Y", "U", "V")},
        "circle_bboxes": {label: bbox_to_list(circle_bboxes[label]) for label in ("A", "B", "C")},
        "label_bboxes": {key: bbox_to_list(value) for key, value in label_bboxes.items()},
        "scale_px_per_unit": round(float(scale), 3),
        "centerline_angle_degrees": round(math.degrees(angle), 3),
        "target_name": str(problem.target_name),
        "label_mode": str(problem.label_mode),
    }
    return _RenderedScene(
        image=ctx.image,
        annotation_keyed_points={key: tuple(value) for key, value in annotation.items()},
        annotation_roles=tuple(annotation.keys()),
        label_bboxes=dict(label_bboxes),
        scene_entities=scene_entities,
        render_map=render_map,
    )


def _make_prompt_examples(*, answer_value: int, annotation_keys: Sequence[str]) -> tuple[str, str]:
    annotation = {str(key): [120 + index * 34, 220 + (index % 2) * 28] for index, key in enumerate(annotation_keys)}
    return dump_prompt_json_examples(annotation=annotation, answer=int(answer_value))


@register_task
class GeometryCircleCenterlineOverlapSegmentLengthValueTask:
    """Find a missing centerline segment in an overlapping-circle chain."""

    task_id = TASK_ID
    domain = "geometry"
    task_group = TASK_GROUP
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            _TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
        )
        problem = _resolve_problem(instance_seed=int(instance_seed), params=params)
        rendered: _RenderedScene | None = None
        ctx: _RenderContext | None = None
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_params = dict(params)
            attempt_params["_render_attempt"] = int(attempt)
            try:
                ctx = _make_render_context(
                    instance_seed=int(instance_seed) + int(attempt),
                    params=attempt_params,
                    rendering_defaults=rendering_defaults,
                )
                rendered = _render_scene(ctx, problem, instance_seed=int(instance_seed) + int(attempt))
                break
            except Exception as exc:
                last_error = exc
                continue
        if rendered is None or ctx is None:
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
        annotation_key_text = ", ".join(f'"{key}"' for key in rendered.annotation_roles)
        json_example, json_example_answer_only = _make_prompt_examples(
            answer_value=int(problem.answer),
            annotation_keys=rendered.annotation_roles,
        )
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
                "target_name": str(problem.target_name),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]).format(annotation_keys=annotation_key_text),
                "answer_hint": str(prompt_defaults["answer_hint_integer"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        annotation_value = {str(key): _point_to_list(value) for key, value in rendered.annotation_keyed_points.items()}
        case = problem.case
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "domain": self.domain,
                "task_group": self.task_group,
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "type": "circle_centerline_overlap_chain",
                    "adjacent_overlaps_only": True,
                    "circle_count": 3,
                    "distance_ab": int(case.distance_ab),
                    "distance_bc": int(case.distance_bc),
                    "distance_ac": int(case.distance_ac),
                    "overlap_ab": int(case.overlap_ab),
                    "overlap_bc": int(case.overlap_bc),
                    "target_name": str(problem.target_name),
                    "annotation_roles": list(rendered.annotation_roles),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(problem.query_id),
                    "query_id_probabilities": dict(problem.query_probabilities),
                    "overlap_case_key": str(case.key),
                    "overlap_case_probabilities": dict(problem.case_probabilities),
                    "label_mode": str(problem.label_mode),
                    "label_mode_probabilities": dict(problem.label_mode_probabilities),
                    "boundary_pair": str(problem.boundary_pair),
                    "boundary_pair_probabilities": dict(problem.boundary_pair_probabilities),
                    "boundary_target_role": str(problem.boundary_target_role),
                    "boundary_target_role_probabilities": dict(problem.boundary_target_role_probabilities),
                    "answer_support_probabilities": dict(problem.answer_support_probabilities),
                },
            },
            "render_spec": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "canvas": {"width": int(image.size[0]), "height": int(image.size[1])},
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
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "radius_a": int(case.radius_a),
                "radius_b": int(case.radius_b),
                "radius_c": int(case.radius_c),
                "diameter_a": int(case.radius_a * 2),
                "diameter_b": int(case.radius_b * 2),
                "diameter_c": int(case.radius_c * 2),
                "distance_ab": int(case.distance_ab),
                "distance_bc": int(case.distance_bc),
                "distance_ac": int(case.distance_ac),
                "overlap_ab": int(case.overlap_ab),
                "overlap_bc": int(case.overlap_bc),
                "label_mode": str(problem.label_mode),
                "boundary_pair": str(problem.boundary_pair),
                "boundary_target_role": str(problem.boundary_target_role),
                "target_name": str(problem.target_name),
                "known_segment_name": str(problem.known_segment_name),
                "known_segment_value": int(problem.known_segment_value),
                "answer": int(problem.answer),
                "annotation_roles": list(rendered.annotation_roles),
            },
            "witness_symbolic": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "formula_family": "circle_centerline_overlap_segment_length",
                "circle_count": 3,
                "radii": {"A": int(case.radius_a), "B": int(case.radius_b), "C": int(case.radius_c)},
                "distances": {"AB": int(case.distance_ab), "BC": int(case.distance_bc), "AC": int(case.distance_ac)},
                "overlaps": {"XY": int(case.overlap_ab), "UV": int(case.overlap_bc)},
                "target_name": str(problem.target_name),
                "known_segment_name": str(problem.known_segment_name),
                "known_segment_value": int(problem.known_segment_value),
                "answer_value": int(problem.answer),
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
            visual_scan=0.64,
            measurement_precision=0.56,
            ambiguity=0.46,
            output_burden=normalize_linear(len(annotation_value), min_value=4, max_value=8),
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
    "BOUNDARY_PAIRS",
    "BOUNDARY_TARGET_ROLES",
    "GeometryCircleCenterlineOverlapSegmentLengthValueTask",
    "QUERY_ID_BOUNDARY_SEGMENT",
    "QUERY_ID_CENTER_DISTANCE",
    "QUERY_IDS",
    "SCENE_ID",
    "TASK_ID",
]
