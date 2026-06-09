"""Volume-equivalence conversion geometry measurement tasks."""

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
from ...shared.text_legibility import draw_text_traced
from ...shared.text_rendering import load_font
from ..shared.complexity import build_geometry_measurement_complexity, normalize_linear
from ..shared.diagram_style import prepare_geometry_diagram_style_and_background
from ..shared.fixed_query_task import (
    geometry_query_ids_for_task,
    geometry_selected_probability_map as _probability_map,
    select_indexed_geometry_query_id,
)
from ..shared.measurement_rendering import bbox_to_list, bbox_union_from_bboxes as _bbox_union, pad_bbox
from ..shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS
from ..shared.option_count import resolve_geometry_option_count

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

SCENE_ID = "volume_equivalence_conversion"
TASK_GROUP = "measurement"
TASK_ID_MISSING_DIMENSION = "task_geometry__volume_equivalence_conversion__missing_dimension_value"
TASK_ID_EQUAL_VOLUME_OPTION = "task_geometry__volume_equivalence_conversion__equal_volume_option_label"
TASK_ID = TASK_ID_MISSING_DIMENSION
PROMPT_BUNDLE_ID = "geometry_volume_equivalence_conversion_v0"

QUERY_ID_CUBOID_TO_CYLINDER_LENGTH = "cuboid_to_cylinder_length"
QUERY_ID_CYLINDER_TO_CONE_HEIGHT = "cylinder_to_cone_height"
QUERY_ID_CONE_TO_CUBOID_HEIGHT = "cone_to_cuboid_height"
QUERY_ID_CONE_MATCHES_CYLINDER_OPTION = "cone_matches_cylinder_option"
QUERY_ID_CYLINDER_MATCHES_CONE_OPTION = "cylinder_matches_cone_option"
QUERY_ID_CUBOID_MATCHES_CYLINDER_OPTION = "cuboid_matches_cylinder_option"
MISSING_DIMENSION_QUERY_IDS: Tuple[str, ...] = (
    QUERY_ID_CUBOID_TO_CYLINDER_LENGTH,
    QUERY_ID_CYLINDER_TO_CONE_HEIGHT,
    QUERY_ID_CONE_TO_CUBOID_HEIGHT,
)
EQUAL_VOLUME_OPTION_QUERY_IDS: Tuple[str, ...] = (
    QUERY_ID_CONE_MATCHES_CYLINDER_OPTION,
    QUERY_ID_CYLINDER_MATCHES_CONE_OPTION,
    QUERY_ID_CUBOID_MATCHES_CYLINDER_OPTION,
)
QUERY_IDS: Tuple[str, ...] = MISSING_DIMENSION_QUERY_IDS + EQUAL_VOLUME_OPTION_QUERY_IDS

MISSING_DIMENSION_ANNOTATION_KEYS: Tuple[str, ...] = (
    "source_solid_bbox",
    "target_solid_bbox",
    "source_dimension_region_bbox",
    "target_dimension_region_bbox",
    "target_unknown_region_bbox",
)
OPTION_ANNOTATION_KEYS: Tuple[str, ...] = (
    "source_solid_bbox",
    "source_dimension_region_bbox",
    "selected_option_bbox",
    "selected_option_dimension_region_bbox",
)
ANNOTATION_KEYS: Tuple[str, ...] = MISSING_DIMENSION_ANNOTATION_KEYS

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", TASK_GROUP)
_OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")

_CUBOID_TO_CYLINDER_LENGTH_CASES: Tuple[Tuple[int, int, int, int], ...] = (
    (6, 4, 5, 12),
    (8, 5, 3, 10),
    (9, 4, 5, 10),
    (10, 6, 4, 12),
    (7, 6, 4, 21),
    (12, 5, 3, 30),
)
_CYLINDER_TO_CONE_HEIGHT_CASES: Tuple[Tuple[int, int, int], ...] = (
    (12, 5, 10),
    (8, 6, 12),
    (9, 8, 24),
    (10, 6, 18),
    (14, 5, 15),
    (16, 6, 18),
)
_CONE_TO_CUBOID_HEIGHT_CASES: Tuple[Tuple[int, int, int, int], ...] = (
    (18, 6, 6, 3),
    (24, 9, 6, 4),
    (30, 12, 10, 3),
    (36, 15, 9, 4),
    (54, 9, 9, 3),
    (42, 14, 7, 4),
)

_OPTION_SOURCE_CASES: Dict[str, Tuple[Tuple[int, ...], ...]] = {
    QUERY_ID_CONE_MATCHES_CYLINDER_OPTION: ((18, 6), (24, 6), (30, 9), (36, 5)),
    QUERY_ID_CYLINDER_MATCHES_CONE_OPTION: ((12, 4), (9, 6), (15, 4), (18, 5)),
    QUERY_ID_CUBOID_MATCHES_CYLINDER_OPTION: ((6, 4, 4), (8, 3, 5), (8, 4, 3), (10, 4, 3)),
}


@dataclass(frozen=True)
class _SolidSpec:
    shape: str
    base_area: int
    height: int
    length: int
    width: int
    depth: int


@dataclass(frozen=True)
class _ResolvedProblem:
    task_id: str
    query_id: str
    source: _SolidSpec
    target: _SolidSpec
    answer: int | str
    answer_schema: str
    formula_family: str
    formula: str
    target_unknown_role: str
    option_specs: Tuple[Tuple[str, _SolidSpec, int], ...]
    selected_option_label: str
    query_probabilities: Dict[str, float]
    case_probabilities: Dict[str, float]
    answer_support_probabilities: Dict[str, float]
    option_count_probabilities: Dict[str, float]


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
    source_fill: Color
    target_fill: Color
    option_fill: Color
    accent_color: Color
    muted_color: Color
    line_width: int
    label_stroke_width: int
    font: Any
    small_font: Any
    diagram_style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    annotation_bboxes: Dict[str, BBox]
    label_bboxes: Dict[str, BBox]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]


def _volume(spec: _SolidSpec) -> int:
    if spec.shape == "cuboid":
        return int(spec.length) * int(spec.width) * int(spec.height)
    if spec.shape == "cylinder":
        return int(spec.base_area) * int(spec.height)
    if spec.shape == "cone":
        numerator = int(spec.base_area) * int(spec.height)
        if numerator % 3 != 0:
            raise ValueError("cone base_area * height must be divisible by 3")
        return numerator // 3
    raise ValueError(f"unsupported solid shape: {spec.shape}")


_QUERY_IDS_BY_TASK_ID: Dict[str, Tuple[str, ...]] = {
    TASK_ID_MISSING_DIMENSION: MISSING_DIMENSION_QUERY_IDS,
    TASK_ID_EQUAL_VOLUME_OPTION: EQUAL_VOLUME_OPTION_QUERY_IDS,
}


def _case_key(query_id: str, case: Sequence[int]) -> str:
    return f"{query_id}:" + "_".join(str(int(value)) for value in case)


def _cases_for_query(query_id: str) -> Tuple[Tuple[int, ...], ...]:
    if str(query_id) == QUERY_ID_CUBOID_TO_CYLINDER_LENGTH:
        return tuple(_CUBOID_TO_CYLINDER_LENGTH_CASES)
    if str(query_id) == QUERY_ID_CYLINDER_TO_CONE_HEIGHT:
        return tuple(_CYLINDER_TO_CONE_HEIGHT_CASES)
    if str(query_id) == QUERY_ID_CONE_TO_CUBOID_HEIGHT:
        return tuple(_CONE_TO_CUBOID_HEIGHT_CASES)
    return tuple(_OPTION_SOURCE_CASES[str(query_id)])


def _select_case(*, query_id: str, instance_seed: int, params: Mapping[str, Any]) -> tuple[Tuple[int, ...], Dict[str, float]]:
    explicit = params.get("conversion_case")
    cases = _cases_for_query(str(query_id))
    if explicit is not None:
        if not isinstance(explicit, Sequence) or isinstance(explicit, (str, bytes)):
            raise ValueError("conversion_case must be a numeric sequence")
        case = tuple(int(value) for value in explicit)
        keys = tuple(_case_key(str(query_id), candidate) for candidate in cases) + (_case_key(str(query_id), case),)
        return case, {key: (1.0 if key == _case_key(str(query_id), case) else 0.0) for key in dict.fromkeys(keys)}
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{query_id}.case")
    case = cases[int(index) % len(cases)]
    probability = 1.0 / float(len(cases))
    return tuple(int(value) for value in case), {_case_key(str(query_id), candidate): probability for candidate in cases}


def _resolve_missing_dimension(query_id: str, case: Sequence[int]) -> tuple[_SolidSpec, _SolidSpec, int, str, str]:
    if str(query_id) == QUERY_ID_CUBOID_TO_CYLINDER_LENGTH:
        length, width, height, target_base_area = [int(value) for value in case]
        source = _SolidSpec("cuboid", 0, height, length, width, 0)
        answer = _volume(source) // int(target_base_area)
        if int(target_base_area) * int(answer) != _volume(source):
            raise ValueError("cuboid-to-cylinder case must yield integer target length")
        target = _SolidSpec("cylinder", int(target_base_area), int(answer), 0, 0, 0)
        return source, target, int(answer), "cylinder_length", "target_length = source_cuboid_volume / cylinder_base_area"
    if str(query_id) == QUERY_ID_CYLINDER_TO_CONE_HEIGHT:
        source_base_area, source_height, target_base_area = [int(value) for value in case]
        source = _SolidSpec("cylinder", int(source_base_area), int(source_height), 0, 0, 0)
        answer = (3 * _volume(source)) // int(target_base_area)
        if int(target_base_area) * int(answer) != 3 * _volume(source):
            raise ValueError("cylinder-to-cone case must yield integer target height")
        target = _SolidSpec("cone", int(target_base_area), int(answer), 0, 0, 0)
        return source, target, int(answer), "cone_height", "target_height = 3 * source_cylinder_volume / cone_base_area"
    if str(query_id) == QUERY_ID_CONE_TO_CUBOID_HEIGHT:
        source_base_area, source_height, target_length, target_width = [int(value) for value in case]
        source = _SolidSpec("cone", int(source_base_area), int(source_height), 0, 0, 0)
        target_base = int(target_length) * int(target_width)
        answer = _volume(source) // target_base
        if target_base * int(answer) != _volume(source):
            raise ValueError("cone-to-cuboid case must yield integer target height")
        target = _SolidSpec("cuboid", 0, int(answer), int(target_length), int(target_width), 0)
        return source, target, int(answer), "cuboid_height", "target_height = source_cone_volume / (cuboid_length * cuboid_width)"
    raise ValueError(f"unsupported missing-dimension query_id: {query_id}")


def _make_option_specs(
    query_id: str,
    source: _SolidSpec,
    *,
    option_count: int,
    instance_seed: int,
    params: Mapping[str, Any],
) -> tuple[Tuple[Tuple[str, _SolidSpec, int], ...], str]:
    source_volume = _volume(source)
    if str(query_id) == QUERY_ID_CONE_MATCHES_CYLINDER_OPTION:
        correct = _SolidSpec("cylinder", 6, source_volume // 6, 0, 0, 0)
        distractors = [
            _SolidSpec("cylinder", 4, max(2, source_volume // 6), 0, 0, 0),
            _SolidSpec("cylinder", 9, max(2, source_volume // 6 + 1), 0, 0, 0),
            _SolidSpec("cylinder", 12, max(2, source_volume // 6 - 1), 0, 0, 0),
            _SolidSpec("cylinder", 15, max(2, source_volume // 6 + 2), 0, 0, 0),
            _SolidSpec("cylinder", 18, max(2, source_volume // 6 + 3), 0, 0, 0),
        ]
    elif str(query_id) == QUERY_ID_CYLINDER_MATCHES_CONE_OPTION:
        correct = _SolidSpec("cone", 18, source_volume // 6, 0, 0, 0)
        distractors = [
            _SolidSpec("cone", 12, max(3, source_volume // 6), 0, 0, 0),
            _SolidSpec("cone", 24, max(3, source_volume // 6 + 1), 0, 0, 0),
            _SolidSpec("cone", 15, max(3, source_volume // 6 + 2), 0, 0, 0),
            _SolidSpec("cone", 21, max(3, source_volume // 6 + 1), 0, 0, 0),
            _SolidSpec("cone", 30, max(3, source_volume // 6 + 2), 0, 0, 0),
        ]
    elif str(query_id) == QUERY_ID_CUBOID_MATCHES_CYLINDER_OPTION:
        correct = _SolidSpec("cylinder", 8, source_volume // 8, 0, 0, 0)
        distractors = [
            _SolidSpec("cylinder", 6, max(2, source_volume // 8), 0, 0, 0),
            _SolidSpec("cylinder", 10, max(2, source_volume // 8 + 1), 0, 0, 0),
            _SolidSpec("cylinder", 12, max(2, source_volume // 8 - 1), 0, 0, 0),
            _SolidSpec("cylinder", 14, max(2, source_volume // 8 + 2), 0, 0, 0),
            _SolidSpec("cylinder", 16, max(2, source_volume // 8 + 3), 0, 0, 0),
        ]
    else:
        raise ValueError(f"unsupported option query_id: {query_id}")
    rng = spawn_rng(int(instance_seed), f"{query_id}.option_distractors")
    rng.shuffle(distractors)
    candidates = [correct, *distractors[: max(0, int(option_count) - 1)]]
    # Deterministic rotation keeps the correct answer distributed across labels without hiding all case structure.
    offset = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{query_id}.answer_label")) % len(candidates)
    rotated = candidates[-offset:] + candidates[:-offset] if offset else candidates
    option_specs = tuple((label, spec, _volume(spec)) for label, spec in zip(_OPTION_LABELS[: int(option_count)], rotated))
    selected_label = next(label for label, spec, volume in option_specs if volume == source_volume and spec == correct)
    return option_specs, selected_label


def _resolve_option(
    query_id: str,
    case: Sequence[int],
    *,
    option_count: int,
    instance_seed: int,
    params: Mapping[str, Any],
) -> tuple[_SolidSpec, _SolidSpec, Tuple[Tuple[str, _SolidSpec, int], ...], str]:
    if str(query_id) == QUERY_ID_CONE_MATCHES_CYLINDER_OPTION:
        source = _SolidSpec("cone", int(case[0]), int(case[1]), 0, 0, 0)
    elif str(query_id) == QUERY_ID_CYLINDER_MATCHES_CONE_OPTION:
        source = _SolidSpec("cylinder", int(case[0]), int(case[1]), 0, 0, 0)
    elif str(query_id) == QUERY_ID_CUBOID_MATCHES_CYLINDER_OPTION:
        source = _SolidSpec("cuboid", 0, int(case[2]), int(case[0]), int(case[1]), 0)
    else:
        raise ValueError(f"unsupported option query_id: {query_id}")
    option_specs, selected_label = _make_option_specs(
        query_id,
        source,
        option_count=int(option_count),
        instance_seed=instance_seed,
        params=params,
    )
    selected = next(spec for label, spec, _volume_value in option_specs if label == selected_label)
    return source, selected, option_specs, selected_label


def _resolve_problem(*, task_id: str, instance_seed: int, params: Mapping[str, Any]) -> _ResolvedProblem:
    generation_defaults, _render_defaults, _prompt_defaults = split_generation_rendering_prompt_defaults(
        _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        task_id=str(task_id),
    )
    query_id, query_probabilities = select_indexed_geometry_query_id(
        params,
        query_ids=geometry_query_ids_for_task(
            str(task_id),
            _QUERY_IDS_BY_TASK_ID,
            context="volume-equivalence",
        ),
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        default_means_sample=False,
    )
    case, case_probabilities = _select_case(query_id=str(query_id), instance_seed=int(instance_seed), params=params)
    if str(task_id) == TASK_ID_MISSING_DIMENSION:
        source, target, answer, role, formula = _resolve_missing_dimension(query_id, case)
        support = sorted({_resolve_missing_dimension(query_id, candidate)[2] for candidate in _cases_for_query(query_id)})
        return _ResolvedProblem(
            task_id=str(task_id),
            query_id=str(query_id),
            source=source,
            target=target,
            answer=int(answer),
            answer_schema="integer",
            formula_family="volume_equivalence_missing_dimension",
            formula=formula,
            target_unknown_role=role,
            option_specs=(),
            selected_option_label="",
            query_probabilities=query_probabilities,
            case_probabilities=case_probabilities,
            answer_support_probabilities={str(value): 1.0 / float(len(support)) for value in support},
            option_count_probabilities={},
        )
    option_count, option_count_probabilities = resolve_geometry_option_count(
        params=params,
        gen_defaults=generation_defaults,
        field_name="option_count",
        supported_counts=(4, 6),
        task_id=str(task_id),
        instance_seed=int(instance_seed),
    )
    source, target, option_specs, selected_label = _resolve_option(
        query_id,
        case,
        option_count=int(option_count),
        instance_seed=instance_seed,
        params=params,
    )
    labels = tuple(label for label, _spec, _volume_value in option_specs)
    return _ResolvedProblem(
        task_id=str(task_id),
        query_id=str(query_id),
        source=source,
        target=target,
        answer=str(selected_label),
        answer_schema="option_letter",
        formula_family="volume_equivalence_option_match",
        formula="select option whose solid volume equals the source solid volume",
        target_unknown_role="equal_volume_option",
        option_specs=tuple(option_specs),
        selected_option_label=str(selected_label),
        query_probabilities=query_probabilities,
        case_probabilities=case_probabilities,
        answer_support_probabilities={label: 1.0 / float(len(labels)) for label in labels},
        option_count_probabilities=dict(option_count_probabilities),
    )


def _draw_text(ctx: _RenderContext, text: str, center: Point, *, small: bool = False) -> BBox:
    font = ctx.small_font if small else ctx.font
    bbox = ctx.draw.textbbox((0, 0), str(text), font=font, stroke_width=ctx.label_stroke_width)
    w = float(bbox[2] - bbox[0])
    h = float(bbox[3] - bbox[1])
    x = float(center[0]) - w / 2.0
    y = float(center[1]) - h / 2.0
    draw_text_traced(
        ctx.draw,
        (x, y),
        str(text),
        font=font,
        fill=ctx.label_color,
        stroke_width=ctx.label_stroke_width,
        stroke_fill=ctx.label_stroke_color,
        role="readout",
        required=False,
    )
    return pad_bbox((x, y, x + w, y + h), 4.0, width=ctx.width, height=ctx.height)


def _draw_value_box(ctx: _RenderContext, text: str, center: Point, *, small: bool = False) -> BBox:
    font = ctx.small_font if small else ctx.font
    bbox = ctx.draw.textbbox((0, 0), str(text), font=font, stroke_width=ctx.label_stroke_width)
    w = float(bbox[2] - bbox[0])
    h = float(bbox[3] - bbox[1])
    x0 = float(center[0]) - w / 2.0 - 10.0
    y0 = float(center[1]) - h / 2.0 - 6.0
    x1 = x0 + w + 20.0
    y1 = y0 + h + 12.0
    ctx.draw.rounded_rectangle((x0, y0, x1, y1), radius=6, fill=(255, 255, 255), outline=ctx.muted_color, width=1)
    draw_text_traced(
        ctx.draw,
        (x0 + 10.0, y0 + 6.0),
        str(text),
        font=font,
        fill=ctx.label_color,
        stroke_width=ctx.label_stroke_width,
        stroke_fill=ctx.label_stroke_color,
        role="readout",
        required=False,
    )
    return pad_bbox((x0, y0, x1, y1), 3.0, width=ctx.width, height=ctx.height)


def _draw_cylinder(ctx: _RenderContext, bbox: BBox, *, fill: Color) -> None:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    ellipse_h = min(34.0, max(18.0, (y1 - y0) * 0.17))
    body_top = y0 + ellipse_h / 2.0
    body_bottom = y1 - ellipse_h / 2.0
    ctx.draw.rectangle((x0, body_top, x1, body_bottom), fill=fill, outline=ctx.line_color, width=ctx.line_width)
    ctx.draw.ellipse((x0, y0, x1, y0 + ellipse_h), fill=fill, outline=ctx.line_color, width=ctx.line_width)
    ctx.draw.arc((x0, y1 - ellipse_h, x1, y1), start=0, end=180, fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.arc((x0, y1 - ellipse_h, x1, y1), start=180, end=360, fill=ctx.secondary_color, width=max(1, ctx.line_width - 1))


def _draw_cone(ctx: _RenderContext, bbox: BBox, *, fill: Color) -> None:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    apex = ((x0 + x1) / 2.0, y0)
    base_y = y1 - min(30.0, max(18.0, (y1 - y0) * 0.16))
    ctx.draw.polygon([apex, (x0, base_y), (x1, base_y)], fill=fill, outline=ctx.line_color)
    ctx.draw.line([apex, (x0, base_y)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([apex, (x1, base_y)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.ellipse((x0, base_y - 12.0, x1, y1), fill=fill, outline=ctx.line_color, width=ctx.line_width)
    ctx.draw.arc((x0, base_y - 12.0, x1, y1), start=180, end=360, fill=ctx.secondary_color, width=max(1, ctx.line_width - 1))


def _draw_cuboid(ctx: _RenderContext, bbox: BBox, *, fill: Color) -> None:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    depth = min(42.0, max(24.0, (x1 - x0) * 0.18))
    front = (x0, y0 + depth * 0.55, x1 - depth, y1)
    back = (front[0] + depth, front[1] - depth * 0.55, front[2] + depth, front[3] - depth * 0.55)
    ctx.draw.polygon([(front[0], front[1]), (back[0], back[1]), (back[2], back[1]), (front[2], front[1])], fill=fill, outline=ctx.line_color)
    ctx.draw.polygon([(front[2], front[1]), (back[2], back[1]), (back[2], back[3]), (front[2], front[3])], fill=tuple(max(0, c - 18) for c in fill), outline=ctx.line_color)
    ctx.draw.rectangle(front, fill=fill, outline=ctx.line_color, width=ctx.line_width)


def _draw_solid(ctx: _RenderContext, spec: _SolidSpec, bbox: BBox, *, fill: Color) -> None:
    if spec.shape == "cuboid":
        _draw_cuboid(ctx, bbox, fill=fill)
    elif spec.shape == "cylinder":
        _draw_cylinder(ctx, bbox, fill=fill)
    elif spec.shape == "cone":
        _draw_cone(ctx, bbox, fill=fill)
    else:
        raise ValueError(f"unsupported shape: {spec.shape}")


def _dimension_labels(spec: _SolidSpec, *, unknown_role: str = "") -> Tuple[str, ...]:
    if spec.shape == "cuboid":
        height = "H=?" if unknown_role == "cuboid_height" else f"H={spec.height}"
        return (f"L={spec.length}", f"W={spec.width}", height)
    if spec.shape == "cylinder":
        height = "length=?" if unknown_role == "cylinder_length" else f"length={spec.height}"
        return (f"base area={spec.base_area}", height)
    if spec.shape == "cone":
        height = "H=?" if unknown_role == "cone_height" else f"H={spec.height}"
        return (f"base area={spec.base_area}", height)
    return ()


def _draw_arrow(ctx: _RenderContext, start: Point, end: Point) -> BBox:
    ctx.draw.line([start, end], fill=ctx.accent_color, width=max(3, ctx.line_width + 1))
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    length = max(1e-6, (dx * dx + dy * dy) ** 0.5)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    head = 16.0
    wing = 8.0
    p1 = (float(end[0]) - ux * head + px * wing, float(end[1]) - uy * head + py * wing)
    p2 = (float(end[0]) - ux * head - px * wing, float(end[1]) - uy * head - py * wing)
    ctx.draw.polygon([end, p1, p2], fill=ctx.accent_color)
    return _bbox_union(
        (
            (start[0], start[1], start[0], start[1]),
            (end[0], end[1], end[0], end[1]),
            (p1[0], p1[1], p1[0], p1[1]),
            (p2[0], p2[1], p2[0], p2[1]),
        ),
        width=ctx.width,
        height=ctx.height,
        pad=8.0,
    )


def _option_positions(option_count: int) -> Tuple[Point, ...]:
    if int(option_count) == 4:
        return ((290.0, 360.0), (560.0, 360.0), (290.0, 520.0), (560.0, 520.0))
    if int(option_count) == 6:
        return ((160.0, 360.0), (425.0, 360.0), (690.0, 360.0), (160.0, 520.0), (425.0, 520.0), (690.0, 520.0))
    raise ValueError(f"unsupported volume option_count={option_count}")


def _render_missing_scene(ctx: _RenderContext, problem: _ResolvedProblem, *, instance_seed: int) -> _RenderedScene:
    rng = spawn_rng(int(instance_seed), f"{problem.task_id}.render.missing")
    source_bbox = (120.0 + rng.uniform(-8.0, 8.0), 205.0, 310.0 + rng.uniform(-8.0, 8.0), 420.0)
    target_bbox = (535.0 + rng.uniform(-8.0, 8.0), 205.0, 720.0 + rng.uniform(-8.0, 8.0), 420.0)
    ctx.draw.rounded_rectangle((72, 116, 780, 500), radius=10, fill=(255, 255, 255), outline=ctx.muted_color, width=1)
    _draw_solid(ctx, problem.source, source_bbox, fill=ctx.source_fill)
    _draw_solid(ctx, problem.target, target_bbox, fill=ctx.target_fill)
    label_bboxes: Dict[str, BBox] = {}
    label_bboxes["source_title"] = _draw_text(ctx, f"source {problem.source.shape}", ((source_bbox[0] + source_bbox[2]) / 2.0, 166.0), small=True)
    label_bboxes["target_title"] = _draw_text(ctx, f"target {problem.target.shape}", ((target_bbox[0] + target_bbox[2]) / 2.0, 166.0), small=True)
    source_label_boxes = []
    for i, text in enumerate(_dimension_labels(problem.source)):
        source_label_boxes.append(_draw_value_box(ctx, text, ((source_bbox[0] + source_bbox[2]) / 2.0, 450.0 + i * 34.0), small=True))
    target_label_boxes = []
    unknown_label_boxes = []
    for i, text in enumerate(_dimension_labels(problem.target, unknown_role=problem.target_unknown_role)):
        bbox = _draw_value_box(ctx, text, ((target_bbox[0] + target_bbox[2]) / 2.0, 450.0 + i * 34.0), small=True)
        target_label_boxes.append(bbox)
        if "?" in text:
            unknown_label_boxes.append(bbox)
    arrow_bbox = _draw_arrow(ctx, (source_bbox[2] + 42.0, 300.0), (target_bbox[0] - 42.0, 300.0))
    label_bboxes["equal_volume"] = _draw_text(ctx, "same volume", (ctx.width / 2.0, 260.0), small=True)
    annotation_bboxes = {
        "source_solid_bbox": pad_bbox(source_bbox, 8.0, width=ctx.width, height=ctx.height),
        "target_solid_bbox": pad_bbox(target_bbox, 8.0, width=ctx.width, height=ctx.height),
        "source_dimension_region_bbox": _bbox_union(source_label_boxes, width=ctx.width, height=ctx.height, pad=4.0),
        "target_dimension_region_bbox": _bbox_union(target_label_boxes, width=ctx.width, height=ctx.height, pad=4.0),
        "target_unknown_region_bbox": _bbox_union(unknown_label_boxes, width=ctx.width, height=ctx.height, pad=4.0),
    }
    render_map = {
        "coord_space": "pixel",
        "query_id": problem.query_id,
        "source_solid_bbox": bbox_to_list(annotation_bboxes["source_solid_bbox"]),
        "target_solid_bbox": bbox_to_list(annotation_bboxes["target_solid_bbox"]),
        "conversion_arrow_bbox": bbox_to_list(arrow_bbox),
        "annotation_bboxes": {key: bbox_to_list(value) for key, value in annotation_bboxes.items()},
    }
    return _RenderedScene(
        image=ctx.image,
        annotation_bboxes=annotation_bboxes,
        label_bboxes=label_bboxes,
        scene_entities=_scene_entities(problem),
        render_map=render_map,
    )


def _render_option_scene(ctx: _RenderContext, problem: _ResolvedProblem, *, instance_seed: int) -> _RenderedScene:
    rng = spawn_rng(int(instance_seed), f"{problem.task_id}.render.option")
    source_bbox = (320.0 + rng.uniform(-8.0, 8.0), 90.0, 510.0 + rng.uniform(-8.0, 8.0), 280.0)
    ctx.draw.rounded_rectangle((72, 42, 790, 585), radius=10, fill=(255, 255, 255), outline=ctx.muted_color, width=1)
    _draw_solid(ctx, problem.source, source_bbox, fill=ctx.source_fill)
    label_bboxes: Dict[str, BBox] = {
        "source_title": _draw_text(ctx, f"source {problem.source.shape}", ((source_bbox[0] + source_bbox[2]) / 2.0, 62.0), small=True)
    }
    source_label_boxes = []
    for i, text in enumerate(_dimension_labels(problem.source)):
        source_label_boxes.append(_draw_value_box(ctx, text, (190.0, 118.0 + i * 36.0), small=True))
    option_bboxes: Dict[str, BBox] = {}
    option_dimension_bboxes: Dict[str, BBox] = {}
    option_positions = _option_positions(len(problem.option_specs))
    for (label, spec, _volume_value), center in zip(problem.option_specs, option_positions):
        card = (center[0] - 82.0, center[1] - 80.0, center[0] + 82.0, center[1] + 70.0)
        ctx.draw.rounded_rectangle(card, radius=8, fill=(250, 252, 255), outline=ctx.muted_color, width=1)
        label_bboxes[f"option_{label}_label"] = _draw_text(ctx, label, (card[0] + 22.0, card[1] + 20.0), small=False)
        solid_bbox = (center[0] - 46.0, center[1] - 56.0, center[0] + 52.0, center[1] + 34.0)
        _draw_solid(ctx, spec, solid_bbox, fill=ctx.option_fill)
        dims = []
        for i, text in enumerate(_dimension_labels(spec)):
            dims.append(_draw_text(ctx, text, (center[0], card[3] - 30.0 + i * 19.0), small=True))
        option_bboxes[str(label)] = pad_bbox(card, 4.0, width=ctx.width, height=ctx.height)
        option_dimension_bboxes[str(label)] = _bbox_union(dims, width=ctx.width, height=ctx.height, pad=3.0)
    selected = str(problem.selected_option_label)
    annotation_bboxes = {
        "source_solid_bbox": pad_bbox(source_bbox, 8.0, width=ctx.width, height=ctx.height),
        "source_dimension_region_bbox": _bbox_union(source_label_boxes, width=ctx.width, height=ctx.height, pad=5.0),
        "selected_option_bbox": option_bboxes[selected],
        "selected_option_dimension_region_bbox": option_dimension_bboxes[selected],
    }
    render_map = {
        "coord_space": "pixel",
        "query_id": problem.query_id,
        "source_solid_bbox": bbox_to_list(annotation_bboxes["source_solid_bbox"]),
        "option_bboxes": {key: bbox_to_list(value) for key, value in option_bboxes.items()},
        "option_count": int(len(problem.option_specs)),
        "selected_option_label": selected,
        "annotation_bboxes": {key: bbox_to_list(value) for key, value in annotation_bboxes.items()},
    }
    return _RenderedScene(
        image=ctx.image,
        annotation_bboxes=annotation_bboxes,
        label_bboxes=label_bboxes,
        scene_entities=_scene_entities(problem),
        render_map=render_map,
    )


def _scene_entities(problem: _ResolvedProblem) -> Tuple[Dict[str, Any], ...]:
    entities = [
        {
            "entity_id": "source_solid",
            "entity_type": problem.source.shape,
            "base_area_units": int(problem.source.base_area),
            "height_units": int(problem.source.height),
            "length_units": int(problem.source.length),
            "width_units": int(problem.source.width),
            "volume_units": int(_volume(problem.source)),
        },
        {
            "entity_id": "target_solid",
            "entity_type": problem.target.shape,
            "base_area_units": int(problem.target.base_area),
            "height_units": int(problem.target.height),
            "length_units": int(problem.target.length),
            "width_units": int(problem.target.width),
            "volume_units": int(_volume(problem.target)),
        },
    ]
    for label, spec, volume in problem.option_specs:
        entities.append(
            {
                "entity_id": f"option_{label}",
                "entity_type": spec.shape,
                "option_label": str(label),
                "base_area_units": int(spec.base_area),
                "height_units": int(spec.height),
                "length_units": int(spec.length),
                "width_units": int(spec.width),
                "volume_units": int(volume),
                "is_answer": str(label) == str(problem.selected_option_label),
            }
        )
    return tuple(entities)


def _example_bbox_for_key(key: str) -> list[int]:
    examples = {
        "source_solid_bbox": [120, 205, 310, 420],
        "target_solid_bbox": [535, 205, 720, 420],
        "source_dimension_region_bbox": [130, 440, 305, 525],
        "target_dimension_region_bbox": [545, 440, 735, 525],
        "target_unknown_region_bbox": [555, 475, 715, 510],
        "selected_option_bbox": [470, 260, 635, 410],
        "selected_option_dimension_region_bbox": [490, 370, 620, 430],
    }
    return list(examples[str(key)])


def _make_prompt_examples(answer: int | str, annotation_keys: Sequence[str]) -> tuple[str, str]:
    annotation = {str(key): _example_bbox_for_key(str(key)) for key in annotation_keys}
    return dump_prompt_json_examples(annotation=annotation, answer=answer)


class _VolumeEquivalenceBaseTask:
    domain = "geometry"
    task_group = TASK_GROUP
    task_id = TASK_ID_MISSING_DIMENSION
    default_dataset_enabled = True
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    supported_queries: Tuple[str, ...] = MISSING_DIMENSION_QUERY_IDS

    def _make_render_context(
        self,
        *,
        instance_seed: int,
        params: Mapping[str, Any],
        render_defaults: Mapping[str, Any],
    ) -> _RenderContext:
        width = int(params.get("canvas_width", group_default(render_defaults, "canvas_width", 860)))
        height = int(params.get("canvas_height", group_default(render_defaults, "canvas_height", 640)))
        image, background_meta, diagram_style, diagram_style_meta = prepare_geometry_diagram_style_and_background(
            instance_seed=int(instance_seed),
            params=params,
            scene_id=SCENE_ID,
            task_group=TASK_GROUP,
            canvas_width=width,
            canvas_height=height,
            require_grid=False,
        )
        fill_palettes: Tuple[Tuple[Color, Color, Color, Color], ...] = (
            ((237, 246, 255), (239, 247, 232), (246, 241, 255), (48, 121, 179)),
            ((255, 242, 229), (235, 242, 255), (240, 250, 247), (176, 93, 47)),
            ((239, 238, 255), (255, 245, 232), (236, 248, 238), (111, 92, 190)),
        )
        palette_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{self.task_id}.palette")
        source_fill, target_fill, option_fill, accent = fill_palettes[int(palette_index) % len(fill_palettes)]
        font_size = int(params.get("label_font_size", group_default(render_defaults, "label_font_size", 22)))
        small_font_size = int(params.get("small_label_font_size", group_default(render_defaults, "small_label_font_size", 17)))
        line_width = int(params.get("line_width", group_default(render_defaults, "line_width", 3)))
        return _RenderContext(
            image=image,
            draw=ImageDraw.Draw(image),
            width=width,
            height=height,
            line_color=tuple(int(value) for value in diagram_style.stroke_rgb),
            secondary_color=tuple(int(value) for value in diagram_style.secondary_stroke_rgb),
            label_color=tuple(int(value) for value in diagram_style.label_rgb),
            label_stroke_color=tuple(int(value) for value in diagram_style.label_stroke_rgb),
            source_fill=source_fill,
            target_fill=target_fill,
            option_fill=option_fill,
            accent_color=accent,
            muted_color=tuple(int(value) for value in diagram_style.panel_border_rgb),
            line_width=max(2, line_width),
            label_stroke_width=max(1, int(diagram_style.label_stroke_width_px)),
            font=load_font(max(12, font_size), bold=True),
            small_font=load_font(max(10, small_font_size), bold=True),
            diagram_style_meta=dict(diagram_style_meta),
            background_meta=dict(background_meta),
        )

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            _TASK_GROUP_DEFAULTS,
            task_id=str(self.task_id),
        )
        problem = _resolve_problem(task_id=str(self.task_id), instance_seed=int(instance_seed), params=params)
        annotation_keys = OPTION_ANNOTATION_KEYS if str(self.task_id) == TASK_ID_EQUAL_VOLUME_OPTION else MISSING_DIMENSION_ANNOTATION_KEYS
        answer_hint_key = "answer_hint_option" if problem.answer_schema == "option_letter" else "answer_hint_integer"
        rendered: _RenderedScene | None = None
        ctx: _RenderContext | None = None
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                render_seed = int(instance_seed) + int(attempt) * 9973
                ctx = self._make_render_context(instance_seed=render_seed, params=params, render_defaults=render_defaults)
                if str(self.task_id) == TASK_ID_EQUAL_VOLUME_OPTION:
                    rendered = _render_option_scene(ctx, problem, instance_seed=render_seed)
                else:
                    rendered = _render_missing_scene(ctx, problem, instance_seed=render_seed)
                break
            except Exception as exc:
                last_error = exc
                rendered = None
                ctx = None
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
                answer_hint_key,
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _make_prompt_examples(problem.answer, annotation_keys)
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
                "answer_hint": str(prompt_defaults[answer_hint_key]),
                "json_example": str(prompt_defaults.get("json_example", json_example)),
                "json_example_answer_only": str(prompt_defaults.get("json_example_answer_only", json_example_answer_only)),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        annotation_value = {key: bbox_to_list(rendered.annotation_bboxes[key]) for key in annotation_keys}
        projected_annotation = {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(annotation_value),
            "pixel_keyed_bbox_map": dict(annotation_value),
        }
        answer_value = str(problem.answer) if problem.answer_schema == "option_letter" else int(problem.answer)
        query_params = {
            "task_id": str(self.task_id),
            "scene_id": SCENE_ID,
            "query_id": str(problem.query_id),
            "query_id_probabilities": dict(problem.query_probabilities),
            "case_probabilities": dict(problem.case_probabilities),
            "answer_support_probabilities": dict(problem.answer_support_probabilities),
            "option_count_probabilities": dict(problem.option_count_probabilities),
            "source_shape": problem.source.shape,
            "target_shape": problem.target.shape,
            "source_volume": int(_volume(problem.source)),
            "target_volume": int(_volume(problem.target)),
            "target_unknown_role": str(problem.target_unknown_role),
            "selected_option_label": str(problem.selected_option_label),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "domain": self.domain,
                "task_group": self.task_group,
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "type": str(problem.formula_family),
                    "source_volume": int(_volume(problem.source)),
                    "target_volume": int(_volume(problem.target)),
                    "annotation_roles": list(annotation_keys),
                },
            },
            "query_spec": {"task_id": str(self.task_id), "scene_id": SCENE_ID, "query_id": str(problem.query_id), "params": dict(query_params)},
            "render_spec": {
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "canvas": {"width": int(image.size[0]), "height": int(image.size[1])},
                "option_count": int(len(problem.option_specs)) if problem.option_specs else 0,
                "option_count_probabilities": dict(problem.option_count_probabilities),
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
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "formula_family": str(problem.formula_family),
                "formula": str(problem.formula),
                "source_shape": problem.source.shape,
                "target_shape": problem.target.shape,
                "source_volume": int(_volume(problem.source)),
                "target_volume": int(_volume(problem.target)),
                "target_unknown_role": str(problem.target_unknown_role),
                "selected_option_label": str(problem.selected_option_label),
                "option_count_probabilities": dict(problem.option_count_probabilities),
                "answer": answer_value,
                "annotation_roles": list(annotation_keys),
            },
            "witness_symbolic": dict(query_params),
            "projected_annotation": projected_annotation,
        }
        complexity = build_geometry_measurement_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=str(self.task_id),
            visual_scan=0.66 if problem.answer_schema == "option_letter" else 0.58,
            measurement_precision=0.62,
            ambiguity=0.50,
            output_burden=normalize_linear(len(annotation_value), min_value=4, max_value=5),
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type=problem.answer_schema, value=answer_value),
            annotation_gt=TypedValue(type="keyed_bbox_map", value=dict(annotation_value)),
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
class GeometryVolumeEquivalenceConversionMissingDimensionValueTask(_VolumeEquivalenceBaseTask):
    """Solve a missing dimension after recasting one solid as an equal-volume target."""

    task_id = TASK_ID_MISSING_DIMENSION
    supported_queries = MISSING_DIMENSION_QUERY_IDS


@register_task
class GeometryVolumeEquivalenceConversionEqualVolumeOptionLabelTask(_VolumeEquivalenceBaseTask):
    """Select the visual option whose solid volume equals the source solid volume."""

    task_id = TASK_ID_EQUAL_VOLUME_OPTION
    supported_queries = EQUAL_VOLUME_OPTION_QUERY_IDS


__all__ = [
    "EQUAL_VOLUME_OPTION_QUERY_IDS",
    "MISSING_DIMENSION_QUERY_IDS",
    "OPTION_ANNOTATION_KEYS",
    "PROMPT_BUNDLE_ID",
    "QUERY_ID_CONE_MATCHES_CYLINDER_OPTION",
    "QUERY_ID_CONE_TO_CUBOID_HEIGHT",
    "QUERY_ID_CUBOID_MATCHES_CYLINDER_OPTION",
    "QUERY_ID_CUBOID_TO_CYLINDER_LENGTH",
    "QUERY_ID_CYLINDER_MATCHES_CONE_OPTION",
    "QUERY_ID_CYLINDER_TO_CONE_HEIGHT",
    "SCENE_ID",
    "TASK_GROUP",
    "TASK_ID",
    "TASK_ID_EQUAL_VOLUME_OPTION",
    "TASK_ID_MISSING_DIMENSION",
    "GeometryVolumeEquivalenceConversionEqualVolumeOptionLabelTask",
    "GeometryVolumeEquivalenceConversionMissingDimensionValueTask",
]
