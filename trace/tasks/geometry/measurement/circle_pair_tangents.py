"""Circle-pair common tangent measurement tasks."""

from __future__ import annotations

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
    draw_right_angle_marker,
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

SCENE_ID = "circle_pair_tangents"
TASK_GROUP = "measurement"
TASK_ID_COMMON_TANGENT_LENGTH = "task_geometry__circle_pair_tangents__common_tangent_length_value"
TASK_ID_CENTER_DISTANCE = "task_geometry__circle_pair_tangents__center_distance_value"
TASK_ID = TASK_ID_COMMON_TANGENT_LENGTH
PROMPT_BUNDLE_ID = "geometry_circle_pair_tangents_v0"
QUERY_ID_COMMON_TANGENT_LENGTH = "external_common_tangent_length"
QUERY_ID_CENTER_DISTANCE = "external_common_tangent_center_distance"
QUERY_ID = QUERY_ID_COMMON_TANGENT_LENGTH
ANNOTATION_KEYS: Tuple[str, ...] = ("O1", "O2", "T1", "T2")

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", TASK_GROUP)


@dataclass(frozen=True)
class _TangentCase:
    small_radius: int
    large_radius: int
    center_distance: int
    tangent_length: int

    @property
    def radius_difference(self) -> int:
        return int(self.large_radius) - int(self.small_radius)

    @property
    def key(self) -> str:
        return (
            f"r{int(self.small_radius)}-{int(self.large_radius)}"
            f"_d{int(self.center_distance)}_t{int(self.tangent_length)}"
        )


_TANGENT_CASES: Tuple[_TangentCase, ...] = (
    _TangentCase(3, 8, 13, 12),
    _TangentCase(2, 11, 15, 12),
    _TangentCase(4, 12, 17, 15),
    _TangentCase(3, 15, 20, 16),
    _TangentCase(5, 12, 25, 24),
    _TangentCase(6, 16, 26, 24),
    _TangentCase(4, 24, 29, 21),
    _TangentCase(6, 22, 34, 30),
)
_LARGER_SIDE_VALUES: Tuple[str, ...] = ("left", "right")
_TANGENT_SIDE_VALUES: Tuple[str, ...] = ("above", "below")


@dataclass(frozen=True)
class _TaskContract:
    task_id: str
    query_id: str
    formula_family: str
    unknown_role: str
    answer_attr: str
    formula: str


_CONTRACTS_BY_TASK_ID: Dict[str, _TaskContract] = {
    TASK_ID_COMMON_TANGENT_LENGTH: _TaskContract(
        task_id=TASK_ID_COMMON_TANGENT_LENGTH,
        query_id=QUERY_ID_COMMON_TANGENT_LENGTH,
        formula_family="external_common_tangent_length",
        unknown_role="tangent_length",
        answer_attr="tangent_length",
        formula="t^2 = d^2 - (r2-r1)^2",
    ),
    TASK_ID_CENTER_DISTANCE: _TaskContract(
        task_id=TASK_ID_CENTER_DISTANCE,
        query_id=QUERY_ID_CENTER_DISTANCE,
        formula_family="external_common_tangent_center_distance",
        unknown_role="center_distance",
        answer_attr="center_distance",
        formula="d^2 = t^2 + (r2-r1)^2",
    ),
}


@dataclass(frozen=True)
class _ResolvedProblem:
    task_id: str
    query_id: str
    radius_o1: int
    radius_o2: int
    center_distance: int
    tangent_length: int
    larger_circle_side: str
    tangent_side: str
    tangent_case_key: str
    query_probabilities: Dict[str, float]
    tangent_case_probabilities: Dict[str, float]
    larger_side_probabilities: Dict[str, float]
    tangent_side_probabilities: Dict[str, float]
    answer_support_probabilities: Dict[str, float]

    @property
    def answer_value(self) -> int:
        if self.query_id == QUERY_ID_CENTER_DISTANCE:
            return int(self.center_distance)
        return int(self.tangent_length)


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
    circle_fill_o1: Color
    circle_fill_o2: Color
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


def _answer_support_probabilities(*, selected: int, answer_attr: str) -> Dict[str, float]:
    if answer_attr == "center_distance":
        support = tuple(sorted({int(case.center_distance) for case in _TANGENT_CASES}))
    else:
        support = tuple(sorted({int(case.tangent_length) for case in _TANGENT_CASES}))
    return _probability_map(support, selected=int(selected))


def _select_case(*, instance_seed: int, params: Mapping[str, Any], task_id: str) -> tuple[_TangentCase, Dict[str, float]]:
    explicit = params.get("tangent_case")
    if explicit is not None:
        if not isinstance(explicit, Sequence) or isinstance(explicit, (str, bytes)) or len(explicit) != 4:
            raise ValueError("tangent_case must be [small_radius, large_radius, center_distance, tangent_length]")
        case = _TangentCase(*(int(value) for value in explicit))
        _validate_case(case)
        return case, {case.key: 1.0}

    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.tangent_case",
    )
    case = _TANGENT_CASES[int(index) % len(_TANGENT_CASES)]
    probability = 1.0 / float(len(_TANGENT_CASES))
    return case, {candidate.key: probability for candidate in _TANGENT_CASES}


def _select_larger_side(*, instance_seed: int, params: Mapping[str, Any], task_id: str) -> tuple[str, Dict[str, float]]:
    explicit = params.get("larger_circle_side")
    if explicit is not None:
        value = str(explicit)
        if value not in _LARGER_SIDE_VALUES:
            raise ValueError(f"larger_circle_side must be one of {_LARGER_SIDE_VALUES}")
        return value, _probability_map(_LARGER_SIDE_VALUES, selected=value)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.larger_circle_side",
    )
    value = _LARGER_SIDE_VALUES[int(index) % len(_LARGER_SIDE_VALUES)]
    return str(value), _probability_map(_LARGER_SIDE_VALUES)


def _select_tangent_side(*, instance_seed: int, params: Mapping[str, Any], task_id: str) -> tuple[str, Dict[str, float]]:
    explicit = params.get("tangent_side")
    if explicit is not None:
        value = str(explicit)
        if value not in _TANGENT_SIDE_VALUES:
            raise ValueError(f"tangent_side must be one of {_TANGENT_SIDE_VALUES}")
        return value, _probability_map(_TANGENT_SIDE_VALUES, selected=value)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.tangent_side",
    )
    value = _TANGENT_SIDE_VALUES[int(index) % len(_TANGENT_SIDE_VALUES)]
    return str(value), _probability_map(_TANGENT_SIDE_VALUES)


def _validate_case(case: _TangentCase) -> None:
    if int(case.small_radius) <= 0 or int(case.large_radius) <= 0:
        raise ValueError("circle radii must be positive")
    if int(case.large_radius) <= int(case.small_radius):
        raise ValueError("large_radius must be greater than small_radius")
    if int(case.center_distance) <= int(case.large_radius) + int(case.small_radius) - 1:
        raise ValueError("circles must be separated enough for a clear external tangent")
    expected = int(case.center_distance) ** 2 - int(case.radius_difference) ** 2
    if expected <= 0 or int(case.tangent_length) ** 2 != expected:
        raise ValueError("tangent_case must satisfy t^2 = d^2 - (r_large-r_small)^2")


def _resolve_problem(*, instance_seed: int, params: Mapping[str, Any], contract: _TaskContract) -> _ResolvedProblem:
    explicit_query = params.get("query_id")
    if explicit_query is not None and str(explicit_query) != contract.query_id:
        raise ValueError(f"unsupported query_id for {contract.task_id}: {explicit_query}")

    case, tangent_case_probabilities = _select_case(
        instance_seed=int(instance_seed),
        params=params,
        task_id=str(contract.task_id),
    )
    larger_side, larger_side_probabilities = _select_larger_side(
        instance_seed=int(instance_seed),
        params=params,
        task_id=str(contract.task_id),
    )
    tangent_side, tangent_side_probabilities = _select_tangent_side(
        instance_seed=int(instance_seed),
        params=params,
        task_id=str(contract.task_id),
    )
    if larger_side == "left":
        radius_o1 = int(case.large_radius)
        radius_o2 = int(case.small_radius)
    else:
        radius_o1 = int(case.small_radius)
        radius_o2 = int(case.large_radius)

    return _ResolvedProblem(
        task_id=str(contract.task_id),
        query_id=str(contract.query_id),
        radius_o1=int(radius_o1),
        radius_o2=int(radius_o2),
        center_distance=int(case.center_distance),
        tangent_length=int(case.tangent_length),
        larger_circle_side=str(larger_side),
        tangent_side=str(tangent_side),
        tangent_case_key=str(case.key),
        query_probabilities={str(contract.query_id): 1.0},
        tangent_case_probabilities=dict(tangent_case_probabilities),
        larger_side_probabilities=dict(larger_side_probabilities),
        tangent_side_probabilities=dict(tangent_side_probabilities),
        answer_support_probabilities=_answer_support_probabilities(
            selected=int(getattr(case, contract.answer_attr)),
            answer_attr=str(contract.answer_attr),
        ),
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
    fill_palettes: Tuple[Tuple[Color, Color], ...] = (
        ((238, 246, 255), (255, 247, 231)),
        ((241, 248, 239), (246, 242, 255)),
        ((255, 242, 235), (232, 246, 250)),
        ((248, 247, 240), (234, 242, 255)),
    )
    fill_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_ID}.fill_palette",
    )
    circle_fill_o1, circle_fill_o2 = fill_palettes[int(fill_index) % len(fill_palettes)]
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
        circle_fill_o1=tuple(int(value) for value in circle_fill_o1),
        circle_fill_o2=tuple(int(value) for value in circle_fill_o2),
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


def _ellipse_bbox(center: Point, radius: float) -> BBox:
    return (
        float(center[0]) - float(radius),
        float(center[1]) - float(radius),
        float(center[0]) + float(radius),
        float(center[1]) + float(radius),
    )


def _render_scene(ctx: _RenderContext, problem: _ResolvedProblem, *, instance_seed: int) -> _RenderedScene:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.render.scene")
    radius_o1 = float(problem.radius_o1)
    radius_o2 = float(problem.radius_o2)
    center_distance = float(problem.center_distance)
    tangent_length = float(problem.tangent_length)
    delta = radius_o2 - radius_o1
    side_sign = 1.0 if str(problem.tangent_side) == "above" else -1.0

    u_unit = (tangent_length / center_distance, side_sign * delta / center_distance)
    n_unit = (delta / center_distance, -side_sign * tangent_length / center_distance)

    o1_local = (0.0, 0.0)
    o2_local = (center_distance, 0.0)
    t1_local = _add(o1_local, _mul(n_unit, radius_o1))
    t2_local = _add(o2_local, _mul(n_unit, radius_o2))

    local_points = (
        _add(o1_local, (-radius_o1, -radius_o1)),
        _add(o1_local, (radius_o1, radius_o1)),
        _add(o2_local, (-radius_o2, -radius_o2)),
        _add(o2_local, (radius_o2, radius_o2)),
        t1_local,
        t2_local,
    )
    min_x = min(point[0] for point in local_points)
    max_x = max(point[0] for point in local_points)
    min_y = min(point[1] for point in local_points)
    max_y = max(point[1] for point in local_points)
    span_x = max(1e-6, float(max_x - min_x))
    span_y = max(1e-6, float(max_y - min_y))
    scale = min((ctx.width - 190.0) / span_x, (ctx.height - 160.0) / span_y)
    scale *= float(rng.uniform(0.86, 0.95))
    local_center = ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)
    target_center = (
        (ctx.width / 2.0) + float(rng.uniform(-28.0, 28.0)),
        (ctx.height / 2.0) + float(rng.uniform(-22.0, 22.0)),
    )

    def transform(point: Point) -> Point:
        return (
            (float(point[0]) - float(local_center[0])) * float(scale) + float(target_center[0]),
            (float(point[1]) - float(local_center[1])) * float(scale) + float(target_center[1]),
        )

    o1 = transform(o1_local)
    o2 = transform(o2_local)
    t1 = transform(t1_local)
    t2 = transform(t2_local)
    radius_o1_px = radius_o1 * scale
    radius_o2_px = radius_o2 * scale
    ctx.scene_transform.resolve((o1, o2, t1, t2))
    o1, o2, t1, t2 = ctx.scene_transform.points((o1, o2, t1, t2))
    radius_o1_px *= float(ctx.scene_transform.transform.scale)
    radius_o2_px *= float(ctx.scene_transform.transform.scale)
    u_px = _sub(t2, t1)
    n_px = _sub(t1, o1)

    o1_bbox = _ellipse_bbox(o1, radius_o1_px)
    o2_bbox = _ellipse_bbox(o2, radius_o2_px)
    _assert_bboxes_inside(
        (o1_bbox, o2_bbox),
        width=ctx.width,
        height=ctx.height,
        error_message="circle-pair tangent label too close to canvas edge",
    )

    ctx.draw.ellipse(o1_bbox, fill=ctx.circle_fill_o1, outline=ctx.line_color, width=ctx.line_width)
    ctx.draw.ellipse(o2_bbox, fill=ctx.circle_fill_o2, outline=ctx.line_color, width=ctx.line_width)

    center_label_offset = (0.0, 26.0 if str(problem.tangent_side) == "above" else -26.0)
    tangent_label_offset = (0.0, -28.0 if str(problem.tangent_side) == "above" else 28.0)
    radius_label_shift = _mul(_perp(n_px), 0.18)

    label_bboxes: Dict[str, BBox] = {}
    center_label = "O1O2=?" if problem.query_id == QUERY_ID_CENTER_DISTANCE else f"O1O2={int(problem.center_distance)}"
    tangent_label = "T1T2=?" if problem.query_id == QUERY_ID_COMMON_TANGENT_LENGTH else f"T1T2={int(problem.tangent_length)}"

    label_bboxes["center_distance"] = _draw_dimension(
        ctx,
        o1,
        o2,
        center_label,
        label_offset=center_label_offset,
        color=ctx.secondary_color,
        tick_px=7.0,
    )
    label_bboxes["radius_o1"] = _draw_dimension(
        ctx,
        o1,
        t1,
        f"r1={int(problem.radius_o1)}",
        label_offset=radius_label_shift,
        color=ctx.secondary_color,
        tick_px=7.0,
    )
    label_bboxes["radius_o2"] = _draw_dimension(
        ctx,
        o2,
        t2,
        f"r2={int(problem.radius_o2)}",
        label_offset=_mul(radius_label_shift, -1.0),
        color=ctx.secondary_color,
        tick_px=7.0,
    )

    extension = max(18.0, ctx.line_width * 7.0)
    tangent_start = _add(t1, _mul(_unit(u_px), -extension))
    tangent_end = _add(t2, _mul(_unit(u_px), extension))
    ctx.draw.line([tangent_start, tangent_end], fill=ctx.accent_color, width=ctx.line_width + 1)
    label_bboxes["tangent_length"] = _draw_dimension(
        ctx,
        t1,
        t2,
        tangent_label,
        label_offset=tangent_label_offset,
        color=ctx.accent_color,
        tick_px=7.0,
    )

    label_bboxes["right_angle_t1"] = draw_right_angle_marker(ctx, t1, arm_a=_mul(n_px, -1.0), arm_b=u_px)
    label_bboxes["right_angle_t2"] = draw_right_angle_marker(ctx, t2, arm_a=_mul(n_px, -1.0), arm_b=u_px)

    dot_radius = max(3, int(ctx.line_width + 1))
    point_label_offsets = {
        "O1": (-18.0, 18.0),
        "O2": (18.0, 18.0),
        "T1": (-22.0, -20.0 if str(problem.tangent_side) == "above" else 20.0),
        "T2": (22.0, -20.0 if str(problem.tangent_side) == "above" else 20.0),
    }
    for label, point in (("O1", o1), ("O2", o2), ("T1", t1), ("T2", t2)):
        ctx.draw.ellipse(
            (point[0] - dot_radius, point[1] - dot_radius, point[0] + dot_radius, point[1] + dot_radius),
            fill=ctx.line_color if label.startswith("O") else ctx.accent_color,
            outline=ctx.line_color,
            width=1,
        )
        offset = point_label_offsets[label]
        label_bboxes[f"{label}_label"] = _draw_text_centered(ctx, label, _add(point, offset), small=True)
    _assert_bboxes_inside(
        label_bboxes.values(),
        width=ctx.width,
        height=ctx.height,
        error_message="circle-pair tangent label too close to canvas edge",
    )

    annotation = {"O1": o1, "O2": o2, "T1": t1, "T2": t2}
    scene_entities = (
        {
            "entity_id": "circle_o1",
            "entity_type": "circle",
            "center": _point_to_list(o1),
            "radius_units": int(problem.radius_o1),
            "radius_px": round(float(radius_o1_px), 3),
            "bbox": bbox_to_list(o1_bbox),
        },
        {
            "entity_id": "circle_o2",
            "entity_type": "circle",
            "center": _point_to_list(o2),
            "radius_units": int(problem.radius_o2),
            "radius_px": round(float(radius_o2_px), 3),
            "bbox": bbox_to_list(o2_bbox),
        },
        {
            "entity_id": "common_tangent_segment",
            "entity_type": "segment",
            "endpoints": [_point_to_list(t1), _point_to_list(t2)],
            "length_units": int(problem.tangent_length),
            "bbox": bbox_to_list(bbox_from_points((t1, t2), width=ctx.width, height=ctx.height, pad=16.0)),
        },
    )
    render_map = {
        "coord_space": "pixel",
        "query_id": str(problem.query_id),
        "centers": {"O1": _point_to_list(o1), "O2": _point_to_list(o2)},
        "tangent_points": {"T1": _point_to_list(t1), "T2": _point_to_list(t2)},
        "circle_bboxes": {"O1": bbox_to_list(o1_bbox), "O2": bbox_to_list(o2_bbox)},
        "tangent_segment": [_point_to_list(t1), _point_to_list(t2)],
        "center_segment": [_point_to_list(o1), _point_to_list(o2)],
        "radii_segments": {"O1T1": [_point_to_list(o1), _point_to_list(t1)], "O2T2": [_point_to_list(o2), _point_to_list(t2)]},
        "label_bboxes": {key: bbox_to_list(value) for key, value in label_bboxes.items()},
        "scale_px_per_unit": round(float(scale), 3),
        "tangent_side": str(problem.tangent_side),
        "larger_circle_side": str(problem.larger_circle_side),
    }
    return _RenderedScene(
        image=ctx.image,
        annotation_keyed_points={key: tuple(value) for key, value in annotation.items()},
        annotation_roles=tuple(ANNOTATION_KEYS),
        label_bboxes=dict(label_bboxes),
        scene_entities=scene_entities,
        render_map=render_map,
    )


def _make_prompt_examples(*, answer_value: int) -> tuple[str, str]:
    annotation = {"O1": [220, 340], "O2": [570, 280], "T1": [240, 185], "T2": [590, 125]}
    return dump_prompt_json_examples(annotation=annotation, answer=int(answer_value))


@register_task
class GeometryCirclePairTangentsCommonTangentLengthValueTask:
    """Compute the external common tangent length between two circles."""

    task_id = TASK_ID
    domain = "geometry"
    task_group = TASK_GROUP
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        contract = _CONTRACTS_BY_TASK_ID[str(self.task_id)]
        _generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            _TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
        )
        problem = _resolve_problem(instance_seed=int(instance_seed), params=params, contract=contract)
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
        json_example, json_example_answer_only = _make_prompt_examples(answer_value=int(problem.answer_value))
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
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint_integer"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        annotation_value = {str(key): _point_to_list(value) for key, value in rendered.annotation_keyed_points.items()}
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "domain": self.domain,
                "task_group": self.task_group,
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "type": "external_common_tangent_right_triangle",
                    "center_distance": int(problem.center_distance),
                    "radius_difference": abs(int(problem.radius_o2) - int(problem.radius_o1)),
                    "tangent_length": int(problem.tangent_length),
                    "unknown_role": str(contract.unknown_role),
                    "annotation_roles": list(ANNOTATION_KEYS),
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
                    "tangent_case_key": str(problem.tangent_case_key),
                    "tangent_case_probabilities": dict(problem.tangent_case_probabilities),
                    "larger_circle_side": str(problem.larger_circle_side),
                    "larger_circle_side_probabilities": dict(problem.larger_side_probabilities),
                    "tangent_side": str(problem.tangent_side),
                    "tangent_side_probabilities": dict(problem.tangent_side_probabilities),
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
                "radius_o1": int(problem.radius_o1),
                "radius_o2": int(problem.radius_o2),
                "center_distance": int(problem.center_distance),
                "radius_difference": abs(int(problem.radius_o2) - int(problem.radius_o1)),
                "tangent_length": int(problem.tangent_length),
                "answer": int(problem.answer_value),
                "tangent_side": str(problem.tangent_side),
                "larger_circle_side": str(problem.larger_circle_side),
                "formula_family": str(contract.formula_family),
                "formula": str(contract.formula),
                "unknown_role": str(contract.unknown_role),
                "annotation_roles": list(ANNOTATION_KEYS),
            },
            "witness_symbolic": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "formula_family": str(contract.formula_family),
                "unknown_role": str(contract.unknown_role),
                "radius_o1": int(problem.radius_o1),
                "radius_o2": int(problem.radius_o2),
                "center_distance": int(problem.center_distance),
                "radius_difference": abs(int(problem.radius_o2) - int(problem.radius_o1)),
                "tangent_length": int(problem.tangent_length),
                "answer_value": int(problem.answer_value),
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
            visual_scan=0.62,
            measurement_precision=0.62,
            ambiguity=0.52,
            output_burden=normalize_linear(len(annotation_value), min_value=2, max_value=4),
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(problem.answer_value)),
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
class GeometryCirclePairTangentsCenterDistanceValueTask(GeometryCirclePairTangentsCommonTangentLengthValueTask):
    """Compute the center distance between two externally tangent-guided circles."""

    task_id = TASK_ID_CENTER_DISTANCE


__all__ = [
    "ANNOTATION_KEYS",
    "GeometryCirclePairTangentsCenterDistanceValueTask",
    "GeometryCirclePairTangentsCommonTangentLengthValueTask",
    "QUERY_ID",
    "QUERY_ID_CENTER_DISTANCE",
    "QUERY_ID_COMMON_TANGENT_LENGTH",
    "SCENE_ID",
    "TASK_ID",
    "TASK_ID_CENTER_DISTANCE",
    "TASK_ID_COMMON_TANGENT_LENGTH",
]
