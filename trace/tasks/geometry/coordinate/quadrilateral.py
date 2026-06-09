"""Coordinate quadrilateral completion and panel-match tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import resolve_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import resolve_scene_label_font_size_px
from ..shared.background_defaults import load_geometry_background_defaults
from ..shared.complexity import build_geometry_task_complexity, clamp_unit_interval, resolve_geometry_complexity_weights
from ..shared.coordinate_panel_grid import (
    CoordinatePanelConfig,
    CoordinatePanelStyle,
    coordinate_panel_layout,
    draw_coordinate_panel_grid,
    graph_point_to_panel_pixel,
    panel_bbox_for_index,
    plot_bbox_for_panel,
)
from ..shared.fixed_query_task import geometry_probability_map as _probability_map, select_geometry_query_id
from ..shared.graph_rendering import graph_paper_grid_from_frame, graph_units_to_pixel, scale_point
from ..shared.noise_defaults import load_geometry_noise_defaults
from ..shared.option_count import panel_grid_shape_for_option_count, resolve_geometry_option_count
from ..shared.point_labels import draw_labeled_points
from ..shared.quadrilateral_prototypes import classify_quadrilateral_kind
from ..shared.single_object_scene import finalize_graph_scene_image, make_graph_scene_canvas, resolve_graph_scene_context
from .params import resolve_int_param as _resolve_int_param


GraphPoint = Tuple[int, int]
PixelPoint = Tuple[float, float]
Color = Tuple[int, int, int]
BBox = Tuple[int, int, int, int]

COMPLETION_TASK_ID = "task_geometry__coordinate_plane__quadrilateral_completion_label"
SHAPE_MATCH_TASK_ID = "task_geometry__coordinate_panels__quadrilateral_shape_match_label"
COMPLETION_SCENE_ID = "coordinate_plane"
PANEL_SCENE_ID = "coordinate_panels"

COMPLETION_QUERY_IDS: Tuple[str, ...] = (
    "parallelogram_completion_label",
    "rectangle_completion_label",
    "square_completion_label",
    "rhombus_completion_label",
)
SHAPE_MATCH_QUERY_IDS: Tuple[str, ...] = (
    "square_shape_match_label",
    "rectangle_shape_match_label",
    "rhombus_shape_match_label",
    "parallelogram_shape_match_label",
)

QUERY_TARGET_KIND: Dict[str, str] = {
    "parallelogram_completion_label": "parallelogram_only",
    "rectangle_completion_label": "rectangle_non_square",
    "square_completion_label": "square",
    "rhombus_completion_label": "rhombus_non_square",
    "square_shape_match_label": "square",
    "rectangle_shape_match_label": "rectangle_non_square",
    "rhombus_shape_match_label": "rhombus_non_square",
    "parallelogram_shape_match_label": "parallelogram_only",
}
TARGET_SHAPE_NAME: Dict[str, str] = {
    "parallelogram_only": "parallelogram",
    "rectangle_non_square": "rectangle",
    "square": "square",
    "rhombus_non_square": "rhombus",
    "other": "other",
}
ALL_EXACT_SHAPE_KINDS: Tuple[str, ...] = (
    "square",
    "rectangle_non_square",
    "rhombus_non_square",
    "parallelogram_only",
)
DEFAULT_COMPLETION_LABEL_POOL: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")
DEFAULT_PANEL_LABEL_POOL: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")
MARKER_STYLES: Tuple[str, ...] = ("filled_circle", "ring", "cross", "diamond", "square")

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "coordinate")
_BACKGROUND_DEFAULTS = load_geometry_background_defaults(task_group="coordinate")
_NOISE_DEFAULTS = load_geometry_noise_defaults(task_group="coordinate")
_PANEL_BACKGROUND_DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    "styles": {
        "solid_offwhite": {"kind": "solid", "color": [252, 252, 252]},
        "solid_cool": {"kind": "solid", "color": [246, 248, 252]},
        "solid_warm": {"kind": "solid", "color": [252, 249, 245]},
        "solid_mist": {"kind": "solid", "color": [248, 252, 249]},
    },
    "weights": {
        "solid_offwhite": 0.35,
        "solid_cool": 0.25,
        "solid_warm": 0.20,
        "solid_mist": 0.20,
    },
}


@dataclass(frozen=True)
class _TaskDefaults:
    completion_canvas_size_min: int = 660
    completion_canvas_size_max: int = 740
    completion_graph_cells_min: int = 18
    completion_graph_cells_max: int = 20
    completion_graph_abs_max: int = 7
    completion_candidate_count: int = 6
    panel_canvas_width: int = 1024
    panel_canvas_height: int = 720
    panel_grid_min: int = -6
    panel_grid_max: int = 6
    panel_graph_abs_max: int = 4
    panel_count: int = 6
    marker_radius_px: int = 7
    marker_radius_px_min: int = 6
    marker_radius_px_max: int = 9
    panel_marker_radius_px: int = 5
    panel_marker_radius_px_min: int = 4
    panel_marker_radius_px_max: int = 6
    label_offset_px: int = 18
    label_font_size_min: int = 17
    label_font_size_max: int = 28
    label_stroke_width: int = 1


@dataclass(frozen=True)
class _ResolvedQuery:
    query_id: str
    target_kind: str
    target_shape_name: str
    query_probabilities: Dict[str, float]
    winner_label: str
    winner_label_probabilities: Dict[str, float]
    label_pool: Tuple[str, ...]


@dataclass(frozen=True)
class _CompletionScene:
    known_points: Tuple[GraphPoint, GraphPoint, GraphPoint]
    missing_point: GraphPoint
    candidate_points_by_label: Dict[str, GraphPoint]
    candidate_bboxes_by_label: Dict[str, List[int]]
    known_points_px: Tuple[PixelPoint, PixelPoint, PixelPoint]
    candidate_points_px_by_label: Dict[str, PixelPoint]
    target_ordered_vertices: Tuple[GraphPoint, GraphPoint, GraphPoint, GraphPoint]
    marker_meta: Dict[str, Any]
    image: Image.Image
    background_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]
    render_spec_extra: Dict[str, Any]
    option_count_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _PanelSpec:
    label: str
    points: Tuple[GraphPoint, GraphPoint, GraphPoint, GraphPoint]
    classified_kind: str
    panel_bbox: List[int]
    plot_bbox: List[int]


@dataclass(frozen=True)
class _PanelScene:
    panels_by_label: Dict[str, _PanelSpec]
    marker_meta: Dict[str, Any]
    panel_style_meta: Dict[str, Any]
    image: Image.Image
    background_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]
    option_count_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_PANEL_STYLES: Tuple[CoordinatePanelStyle, ...] = (
    CoordinatePanelStyle(),
    CoordinatePanelStyle(
        panel_fill=(255, 255, 255),
        panel_outline=(190, 205, 218),
        plot_fill=(249, 252, 255),
        plot_outline=(176, 192, 208),
        grid_color=(218, 228, 238),
        axis_color=(94, 115, 135),
        tick_color=(82, 98, 116),
        text_color=(28, 45, 62),
    ),
    CoordinatePanelStyle(
        panel_fill=(255, 255, 252),
        panel_outline=(207, 197, 178),
        plot_fill=(253, 251, 245),
        plot_outline=(194, 183, 162),
        grid_color=(232, 224, 207),
        axis_color=(125, 107, 82),
        tick_color=(104, 91, 72),
        text_color=(55, 45, 34),
    ),
    CoordinatePanelStyle(
        panel_fill=(253, 255, 252),
        panel_outline=(186, 209, 198),
        plot_fill=(248, 253, 249),
        plot_outline=(174, 198, 187),
        grid_color=(218, 232, 224),
        axis_color=(87, 124, 108),
        tick_color=(74, 102, 91),
        text_color=(35, 58, 49),
    ),
)
_MARKER_COLOR_PALETTES: Tuple[Tuple[Color, Color], ...] = (
    ((32, 92, 166), (206, 92, 38)),
    ((38, 123, 96), (129, 77, 172)),
    ((19, 119, 150), (190, 67, 104)),
    ((97, 100, 36), (178, 83, 43)),
    ((54, 94, 132), (185, 104, 28)),
    ((105, 76, 151), (34, 130, 121)),
)
_SQUARE_VECTORS: Tuple[GraphPoint, ...] = (
    (2, 0),
    (3, 0),
    (0, 2),
    (0, 3),
    (2, 1),
    (1, 2),
    (2, -1),
    (1, -2),
    (3, 1),
    (1, 3),
    (3, -1),
    (1, -3),
)
_RECTANGLE_VECTOR_PAIRS: Tuple[Tuple[GraphPoint, GraphPoint], ...] = (
    ((4, 0), (0, 2)),
    ((3, 0), (0, 2)),
    ((2, 0), (0, 4)),
    ((2, 1), (-2, 4)),
    ((1, 2), (-4, 2)),
    ((2, -1), (2, 4)),
    ((1, -2), (4, 2)),
)
_RHOMBUS_VECTOR_PAIRS: Tuple[Tuple[GraphPoint, GraphPoint], ...] = (
    ((2, 1), (1, 2)),
    ((3, 1), (1, 3)),
    ((3, 2), (2, 3)),
    ((2, -1), (1, -2)),
    ((3, -1), (1, -3)),
    ((3, -2), (2, -3)),
)
_PARALLELOGRAM_VECTOR_PAIRS: Tuple[Tuple[GraphPoint, GraphPoint], ...] = (
    ((4, 0), (1, 2)),
    ((3, 0), (1, 2)),
    ((2, 1), (3, -1)),
    ((3, 1), (1, 2)),
    ((4, 1), (-1, 2)),
    ((2, -1), (3, 1)),
)


def _split_defaults_for_task(task_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    return split_generation_rendering_prompt_defaults(
        _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        task_id=str(task_id),
    )


def _select_winner_label(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    label_pool: Sequence[str],
    query_id_count: int,
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
        namespace=f"{task_id}.winner_label",
    )
    return str(labels[int(selection_index) % len(labels)]), _probability_map(labels)


def _resolve_query(
    *,
    task_id: str,
    query_ids: Sequence[str],
    scene_label_pool: Sequence[str],
    instance_seed: int,
    params: Mapping[str, Any],
) -> _ResolvedQuery:
    query_id, query_probabilities = select_geometry_query_id(
        params,
        query_ids=tuple(query_ids),
        task_id=str(task_id),
        instance_seed=int(instance_seed),
    )
    winner_label, winner_probabilities = _select_winner_label(
        params=params,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        label_pool=tuple(scene_label_pool),
        query_id_count=len(tuple(query_ids)),
    )
    target_kind = str(QUERY_TARGET_KIND[str(query_id)])
    return _ResolvedQuery(
        query_id=str(query_id),
        target_kind=str(target_kind),
        target_shape_name=str(TARGET_SHAPE_NAME[str(target_kind)]),
        query_probabilities=dict(query_probabilities),
        winner_label=str(winner_label),
        winner_label_probabilities=dict(winner_probabilities),
        label_pool=tuple(str(label) for label in scene_label_pool),
    )


def _transform_vector(vector: GraphPoint, transform_index: int) -> GraphPoint:
    x, y = int(vector[0]), int(vector[1])
    variants = (
        (x, y),
        (-x, y),
        (x, -y),
        (-x, -y),
        (y, x),
        (-y, x),
        (y, -x),
        (-y, -x),
    )
    return tuple(int(value) for value in variants[int(transform_index) % len(variants)])  # type: ignore[return-value]


def _vector_pair_for_kind(kind: str, rng) -> Tuple[GraphPoint, GraphPoint]:
    if str(kind) == "square":
        u = tuple(int(value) for value in rng.choice(_SQUARE_VECTORS))
        v = (-int(u[1]), int(u[0]))
    elif str(kind) == "rectangle_non_square":
        u, v = rng.choice(_RECTANGLE_VECTOR_PAIRS)
    elif str(kind) == "rhombus_non_square":
        u, v = rng.choice(_RHOMBUS_VECTOR_PAIRS)
    elif str(kind) == "parallelogram_only":
        u, v = rng.choice(_PARALLELOGRAM_VECTOR_PAIRS)
    else:
        raise ValueError(f"unsupported quadrilateral kind: {kind}")

    transform = int(rng.randrange(8))
    u_t = _transform_vector(tuple(u), int(transform))
    v_t = _transform_vector(tuple(v), int(transform))
    if bool(rng.randrange(2)):
        u_t, v_t = v_t, u_t
    return u_t, v_t


def _translate_points_within(points: Sequence[GraphPoint], *, rng, max_abs: int) -> Tuple[GraphPoint, ...]:
    min_x = min(int(point[0]) for point in points)
    max_x = max(int(point[0]) for point in points)
    min_y = min(int(point[1]) for point in points)
    max_y = max(int(point[1]) for point in points)
    shift_x_min = int(-int(max_abs) - int(min_x))
    shift_x_max = int(int(max_abs) - int(max_x))
    shift_y_min = int(-int(max_abs) - int(min_y))
    shift_y_max = int(int(max_abs) - int(max_y))
    if shift_x_min > shift_x_max or shift_y_min > shift_y_max:
        raise ValueError("shape does not fit inside graph bounds")
    shift = (int(rng.randint(shift_x_min, shift_x_max)), int(rng.randint(shift_y_min, shift_y_max)))
    return tuple((int(x) + int(shift[0]), int(y) + int(shift[1])) for x, y in points)


def _sample_ordered_quadrilateral(kind: str, *, rng, max_abs: int) -> Tuple[GraphPoint, GraphPoint, GraphPoint, GraphPoint]:
    for _ in range(400):
        u, v = _vector_pair_for_kind(str(kind), rng)
        base_points: Tuple[GraphPoint, GraphPoint, GraphPoint, GraphPoint] = (
            (0, 0),
            (int(u[0]), int(u[1])),
            (int(u[0]) + int(v[0]), int(u[1]) + int(v[1])),
            (int(v[0]), int(v[1])),
        )
        try:
            translated = _translate_points_within(base_points, rng=rng, max_abs=int(max_abs))
        except ValueError:
            continue
        start = int(rng.randrange(4))
        ordered = tuple(translated[(start + index) % 4] for index in range(4))
        if bool(rng.randrange(2)):
            ordered = (ordered[0], ordered[3], ordered[2], ordered[1])
        if _classify_point_set(ordered) == str(kind):
            return ordered  # type: ignore[return-value]
    raise RuntimeError(f"failed to sample {kind} quadrilateral")


def _signed_area(vertices: Sequence[GraphPoint]) -> float:
    total = 0.0
    for index, point in enumerate(vertices):
        nxt = vertices[(int(index) + 1) % len(vertices)]
        total += (float(point[0]) * float(nxt[1])) - (float(nxt[0]) * float(point[1]))
    return 0.5 * float(total)


def _order_points_around_centroid(points: Sequence[GraphPoint]) -> Tuple[GraphPoint, ...] | None:
    unique = tuple((int(x), int(y)) for x, y in points)
    if len(unique) != 4 or len(set(unique)) != 4:
        return None
    cx = sum(float(point[0]) for point in unique) / 4.0
    cy = sum(float(point[1]) for point in unique) / 4.0
    ordered = tuple(
        sorted(
            unique,
            key=lambda point: math.atan2(float(point[1]) - float(cy), float(point[0]) - float(cx)),
        )
    )
    if abs(float(_signed_area(ordered))) <= 1e-9:
        return None
    return ordered


def _is_convex(vertices: Sequence[GraphPoint]) -> bool:
    signs: List[int] = []
    for index in range(len(vertices)):
        a = vertices[index]
        b = vertices[(index + 1) % len(vertices)]
        c = vertices[(index + 2) % len(vertices)]
        cross = ((int(b[0]) - int(a[0])) * (int(c[1]) - int(b[1]))) - (
            (int(b[1]) - int(a[1])) * (int(c[0]) - int(b[0]))
        )
        if int(cross) == 0:
            return False
        signs.append(1 if int(cross) > 0 else -1)
    return len(set(signs)) == 1


def _classify_point_set(points: Sequence[GraphPoint]) -> str:
    ordered = _order_points_around_centroid(points)
    if ordered is None or not _is_convex(ordered):
        return "other"
    return str(classify_quadrilateral_kind(tuple((float(x), float(y)) for x, y in ordered)))


def _is_ambiguous_for_prompt(kind: str, target_kind: str) -> bool:
    if str(kind) == str(target_kind):
        return True
    if str(target_kind) == "parallelogram_only" and str(kind) in ALL_EXACT_SHAPE_KINDS:
        return True
    if str(target_kind) in {"rectangle_non_square", "rhombus_non_square"} and str(kind) == "square":
        return True
    return False


def _sample_distractor_point(
    *,
    known_points: Sequence[GraphPoint],
    target_kind: str,
    occupied: set[GraphPoint],
    rng,
    max_abs: int,
) -> GraphPoint:
    for _ in range(2000):
        candidate = (int(rng.randint(-int(max_abs), int(max_abs))), int(rng.randint(-int(max_abs), int(max_abs))))
        if candidate in occupied:
            continue
        kind = _classify_point_set([*known_points, candidate])
        if _is_ambiguous_for_prompt(str(kind), str(target_kind)):
            continue
        return candidate
    raise RuntimeError("failed to sample quadrilateral completion distractor")


def _sample_other_quadrilateral(*, rng, max_abs: int) -> Tuple[GraphPoint, GraphPoint, GraphPoint, GraphPoint]:
    for _ in range(1200):
        base_kind = str(rng.choice(ALL_EXACT_SHAPE_KINDS))
        points = list(_sample_ordered_quadrilateral(base_kind, rng=rng, max_abs=int(max_abs)))
        index = int(rng.randrange(4))
        for delta in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)):
            mutated = list(points)
            mutated[index] = (int(mutated[index][0]) + int(delta[0]), int(mutated[index][1]) + int(delta[1]))
            if any(max(abs(int(coord)) for coord in point) > int(max_abs) for point in mutated):
                continue
            if len(set(mutated)) != 4:
                continue
            if _classify_point_set(mutated) == "other":
                return tuple(mutated)  # type: ignore[return-value]
    raise RuntimeError("failed to sample other quadrilateral point set")


def _sample_panel_points(kind: str, *, rng, max_abs: int) -> Tuple[GraphPoint, GraphPoint, GraphPoint, GraphPoint]:
    if str(kind) == "other":
        return _sample_other_quadrilateral(rng=rng, max_abs=int(max_abs))
    return _sample_ordered_quadrilateral(str(kind), rng=rng, max_abs=int(max_abs))


def _shape_distractor_kinds(target_kind: str, *, rng, count: int) -> List[str]:
    if str(target_kind) == "square":
        base = ["rectangle_non_square", "rhombus_non_square", "parallelogram_only", "other", "other"]
    elif str(target_kind) == "rectangle_non_square":
        base = ["rhombus_non_square", "parallelogram_only", "other", "other", "other"]
    elif str(target_kind) == "rhombus_non_square":
        base = ["rectangle_non_square", "parallelogram_only", "other", "other", "other"]
    elif str(target_kind) == "parallelogram_only":
        base = ["other", "other", "other", "other", "other"]
    else:
        base = ["other"] * int(count)
    while len(base) < int(count):
        base.append("other")
    rng.shuffle(base)
    return list(base[: int(count)])


def _resolve_label_pool(params: Mapping[str, Any], defaults: Mapping[str, Any], key: str, fallback: Sequence[str]) -> Tuple[str, ...]:
    raw = params.get(str(key), group_default(defaults, str(key), list(fallback)))
    if isinstance(raw, str):
        labels = tuple(part.strip() for part in raw.split(",") if part.strip())
    elif isinstance(raw, Sequence):
        labels = tuple(str(item).strip() for item in raw if str(item).strip())
    else:
        labels = tuple(str(item) for item in fallback)
    if not labels:
        raise ValueError(f"{key} must contain at least one label")
    if len(set(labels)) != len(labels):
        raise ValueError(f"{key} must not contain duplicates")
    return labels


def _sample_marker_style(rng, *, params: Mapping[str, Any], defaults: Mapping[str, Any], key: str) -> str:
    explicit = params.get(str(key), group_default(defaults, str(key), None))
    if explicit is not None:
        style = str(explicit)
        if style not in set(MARKER_STYLES):
            raise ValueError(f"{key}={style!r} is not supported")
        return style
    return str(rng.choice(MARKER_STYLES))


def _draw_marker(
    draw: ImageDraw.ImageDraw,
    point: PixelPoint,
    *,
    style: str,
    color: Color,
    radius: int,
    outline: Color = (255, 255, 255),
    width: int = 2,
) -> None:
    x, y = float(point[0]), float(point[1])
    r = max(2, int(radius))
    w = max(1, int(width))
    fill = tuple(int(value) for value in color)
    stroke = tuple(int(value) for value in outline)
    if str(style) == "ring":
        draw.ellipse([x - r, y - r, x + r, y + r], fill=stroke, outline=fill, width=w)
    elif str(style) == "cross":
        draw.line([(x - r, y - r), (x + r, y + r)], fill=fill, width=w)
        draw.line([(x - r, y + r), (x + r, y - r)], fill=fill, width=w)
    elif str(style) == "diamond":
        draw.polygon([(x, y - r), (x + r, y), (x, y + r), (x - r, y)], fill=fill, outline=stroke)
    elif str(style) == "square":
        draw.rectangle([x - r, y - r, x + r, y + r], fill=fill, outline=stroke, width=w)
    else:
        draw.ellipse([x - r, y - r, x + r, y + r], fill=fill, outline=stroke, width=w)


def _marker_bbox(point: PixelPoint, *, radius: int, canvas_width: int, canvas_height: int) -> List[int]:
    pad = max(4, int(radius) + 8)
    return [
        max(0, min(int(canvas_width), int(round(float(point[0]) - float(pad))))),
        max(0, min(int(canvas_height), int(round(float(point[1]) - float(pad))))),
        max(0, min(int(canvas_width), int(round(float(point[0]) + float(pad))))),
        max(0, min(int(canvas_height), int(round(float(point[1]) + float(pad))))),
    ]


def _resolve_marker_colors(rng) -> Tuple[Color, Color, Dict[str, Any]]:
    known_color, candidate_color = rng.choice(_MARKER_COLOR_PALETTES)
    return tuple(known_color), tuple(candidate_color), {
        "palette": [list(known_color), list(candidate_color)],
        "known_color": list(known_color),
        "candidate_color": list(candidate_color),
    }


def _render_completion_scene(
    query: _ResolvedQuery,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
) -> _CompletionScene:
    rng = spawn_rng(int(instance_seed), f"{COMPLETION_TASK_ID}.render")
    max_abs = _resolve_int_param(
        params, generation_defaults, "completion_graph_abs_max", _DEFAULTS.completion_graph_abs_max
    )
    candidate_count, option_count_probabilities = resolve_geometry_option_count(
        params=params,
        gen_defaults=generation_defaults,
        field_name="completion_candidate_count",
        supported_counts=(4, 6),
        task_id=COMPLETION_TASK_ID,
        instance_seed=int(instance_seed),
    )
    if int(candidate_count) > len(query.label_pool):
        raise ValueError("completion_candidate_count cannot exceed candidate label pool length")

    target_vertices = _sample_ordered_quadrilateral(str(query.target_kind), rng=rng, max_abs=int(max_abs))
    missing_index = int(rng.randrange(4))
    missing_point = target_vertices[int(missing_index)]
    known_points = tuple(target_vertices[index] for index in range(4) if int(index) != int(missing_index))

    candidate_labels = tuple(query.label_pool[: int(candidate_count)])
    if str(query.winner_label) not in set(candidate_labels):
        candidate_labels = tuple([str(query.winner_label), *[label for label in candidate_labels if label != str(query.winner_label)]])
        candidate_labels = candidate_labels[: int(candidate_count)]
    occupied = set(known_points) | {missing_point}
    candidate_points_by_label: Dict[str, GraphPoint] = {str(query.winner_label): tuple(missing_point)}
    for label in candidate_labels:
        if str(label) == str(query.winner_label):
            continue
        point = _sample_distractor_point(
            known_points=known_points,
            target_kind=str(query.target_kind),
            occupied=occupied,
            rng=rng,
            max_abs=int(max_abs),
        )
        occupied.add(point)
        candidate_points_by_label[str(label)] = tuple(point)

    context = resolve_graph_scene_context(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        render_defaults=rendering_defaults,
        background_defaults=_BACKGROUND_DEFAULTS,
        fallback_canvas_min=_resolve_int_param(
            params, rendering_defaults, "completion_canvas_size_min", _DEFAULTS.completion_canvas_size_min
        ),
        fallback_canvas_max=_resolve_int_param(
            params, rendering_defaults, "completion_canvas_size_max", _DEFAULTS.completion_canvas_size_max
        ),
        fallback_cells_min=_resolve_int_param(
            params, rendering_defaults, "completion_graph_cells_min", _DEFAULTS.completion_graph_cells_min
        ),
        fallback_cells_max=_resolve_int_param(
            params, rendering_defaults, "completion_graph_cells_max", _DEFAULTS.completion_graph_cells_max
        ),
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
    candidate_style = _sample_marker_style(rng, params=params, defaults=rendering_defaults, key="candidate_marker_style")
    known_color, candidate_color, color_meta = _resolve_marker_colors(rng)
    known_points_px = tuple(
        graph_units_to_pixel(point, graph_origin=context.graph_origin, spacing=int(context.graph_spacing))
        for point in known_points
    )
    candidate_points_px_by_label = {
        str(label): graph_units_to_pixel(point, graph_origin=context.graph_origin, spacing=int(context.graph_spacing))
        for label, point in candidate_points_by_label.items()
    }
    render_radius = int(marker_radius) * int(context.scene_scale)
    for point_px in known_points_px:
        _draw_marker(
            draw,
            scale_point(point_px, int(context.scene_scale)),
            style=str(known_style),
            color=known_color,
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
    draw_labeled_points(
        draw,
        points=[scale_point(candidate_points_px_by_label[str(label)], int(context.scene_scale)) for label in candidate_labels],
        labels=list(candidate_labels),
        label_offset_px=float(label_offset_px) * float(context.scene_scale),
        font_size_px=int(label_font_size_px),
        text_stroke_width=int(label_stroke_width) * int(context.scene_scale),
        blocked_points=[
            *[scale_point(point, int(context.scene_scale)) for point in known_points_px],
            *[scale_point(candidate_points_px_by_label[str(label)], int(context.scene_scale)) for label in candidate_labels],
        ],
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
        "candidate_marker_style": str(candidate_style),
        "marker_radius_px": int(marker_radius),
        **dict(color_meta),
    }
    return _CompletionScene(
        known_points=tuple(known_points),  # type: ignore[arg-type]
        missing_point=tuple(missing_point),
        candidate_points_by_label=dict(candidate_points_by_label),
        candidate_bboxes_by_label=dict(candidate_bboxes_by_label),
        known_points_px=tuple((float(x), float(y)) for x, y in known_points_px),  # type: ignore[arg-type]
        candidate_points_px_by_label=dict(candidate_points_px_by_label),
        target_ordered_vertices=tuple(target_vertices),
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


def _panel_style(rng) -> Tuple[CoordinatePanelStyle, Dict[str, Any]]:
    index = int(rng.randrange(len(_PANEL_STYLES)))
    style = _PANEL_STYLES[int(index)]
    return style, {"style_index": int(index), "style": style.to_trace_dict()}


def _render_panel_scene(
    query: _ResolvedQuery,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
) -> _PanelScene:
    rng = spawn_rng(int(instance_seed), f"{SHAPE_MATCH_TASK_ID}.render")
    max_abs = _resolve_int_param(params, generation_defaults, "panel_graph_abs_max", _DEFAULTS.panel_graph_abs_max)
    panel_count, option_count_probabilities = resolve_geometry_option_count(
        params=params,
        gen_defaults=generation_defaults,
        field_name="panel_count",
        supported_counts=(4, 6),
        task_id=SHAPE_MATCH_TASK_ID,
        instance_seed=int(instance_seed),
    )
    if int(panel_count) > len(query.label_pool):
        raise ValueError("panel_count cannot exceed panel label pool length")
    label_pool = tuple(query.label_pool[: int(panel_count)])
    if str(query.winner_label) not in set(label_pool):
        label_pool = tuple([str(query.winner_label), *[label for label in label_pool if label != str(query.winner_label)]])
        label_pool = label_pool[: int(panel_count)]

    columns, rows = panel_grid_shape_for_option_count(int(panel_count))
    panel_config = CoordinatePanelConfig(
        grid_min=_resolve_int_param(params, rendering_defaults, "panel_grid_min", _DEFAULTS.panel_grid_min),
        grid_max=_resolve_int_param(params, rendering_defaults, "panel_grid_max", _DEFAULTS.panel_grid_max),
        columns=int(columns),
        rows=int(rows),
    )
    canvas_width = _resolve_int_param(params, rendering_defaults, "panel_canvas_width", _DEFAULTS.panel_canvas_width)
    canvas_height = _resolve_int_param(params, rendering_defaults, "panel_canvas_height", _DEFAULTS.panel_canvas_height)
    image, background_meta = make_background_canvas(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=_PANEL_BACKGROUND_DEFAULTS,
        fallback_color=(248, 250, 252),
    )
    draw = ImageDraw.Draw(image)
    style, panel_style_meta = _panel_style(rng)
    marker_style = _sample_marker_style(rng, params=params, defaults=rendering_defaults, key="panel_marker_style")
    _, marker_color, color_meta = _resolve_marker_colors(rng)
    marker_radius = _resolve_int_param(params, rendering_defaults, "panel_marker_radius_px", _DEFAULTS.panel_marker_radius_px)
    marker_radius = max(
        _resolve_int_param(params, rendering_defaults, "panel_marker_radius_px_min", _DEFAULTS.panel_marker_radius_px_min),
        min(
            _resolve_int_param(params, rendering_defaults, "panel_marker_radius_px_max", _DEFAULTS.panel_marker_radius_px_max),
            int(marker_radius),
        ),
    )
    distractor_kinds = _shape_distractor_kinds(str(query.target_kind), rng=rng, count=int(panel_count) - 1)
    kind_by_label: Dict[str, str] = {}
    distractor_iter = iter(distractor_kinds)
    for label in label_pool:
        kind_by_label[str(label)] = str(query.target_kind) if str(label) == str(query.winner_label) else str(next(distractor_iter))

    layout = coordinate_panel_layout(int(canvas_width), int(canvas_height), config=panel_config)
    panels_by_label: Dict[str, _PanelSpec] = {}
    for index, label in enumerate(label_pool):
        panel_bbox = panel_bbox_for_index(layout, int(index), config=panel_config)
        plot_bbox = plot_bbox_for_panel(panel_bbox)
        draw_coordinate_panel_grid(
            draw,
            panel_bbox=panel_bbox,
            plot_bbox=plot_bbox,
            label=str(label),
            config=panel_config,
            style=style,
        )
        points = _sample_panel_points(str(kind_by_label[str(label)]), rng=rng, max_abs=int(max_abs))
        classified_kind = _classify_point_set(points)
        if str(kind_by_label[str(label)]) != "other" and str(classified_kind) != str(kind_by_label[str(label)]):
            raise RuntimeError(f"panel {label} sampled as {kind_by_label[str(label)]} but classified {classified_kind}")
        if str(label) != str(query.winner_label) and _is_ambiguous_for_prompt(str(classified_kind), str(query.target_kind)):
            raise RuntimeError("sampled ambiguous distractor panel")
        for point in points:
            point_px = graph_point_to_panel_pixel(point, plot_bbox=plot_bbox, config=panel_config)
            _draw_marker(
                draw,
                point_px,
                style=str(marker_style),
                color=marker_color,
                radius=int(marker_radius),
                width=2,
            )
        panels_by_label[str(label)] = _PanelSpec(
            label=str(label),
            points=tuple(points),
            classified_kind=str(classified_kind),
            panel_bbox=[int(value) for value in panel_bbox],
            plot_bbox=[int(value) for value in plot_bbox],
        )

    image, post_noise_meta = apply_post_image_noise(
        image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=_NOISE_DEFAULTS,
    )
    marker_meta = {
        "panel_marker_style": str(marker_style),
        "panel_marker_color": list(marker_color),
        "panel_marker_radius_px": int(marker_radius),
        "color_selection": dict(color_meta),
    }
    return _PanelScene(
        panels_by_label=dict(panels_by_label),
        marker_meta=dict(marker_meta),
        panel_style_meta=dict(panel_style_meta),
        image=image,
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
        option_count_probabilities=dict(option_count_probabilities),
    )


def _build_complexity(*, task_id: str, query_id: str, object_count: int, panel_count: int = 1) -> Any:
    weights = resolve_geometry_complexity_weights(
        _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        task_id=str(task_id),
    )
    is_panel = int(panel_count) > 1
    reasoning_by_kind = {
        "square": 0.66,
        "rectangle_non_square": 0.58,
        "rhombus_non_square": 0.64,
        "parallelogram_only": 0.55,
    }
    target_kind = str(QUERY_TARGET_KIND[str(query_id)])
    return build_geometry_task_complexity(
        weights=weights,
        components={
            "visual_scan": clamp_unit_interval(0.35 + (0.08 * float(panel_count)) + (0.02 * float(object_count))),
            "coordinate_reasoning": clamp_unit_interval(float(reasoning_by_kind[str(target_kind)]) + (0.10 if is_panel else 0.0)),
            "ambiguity": clamp_unit_interval(0.46 + (0.08 if target_kind in {"square", "rhombus_non_square"} else 0.0)),
            "output_burden": 0.24,
        },
    )


def _prompt_defaults(task_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    return _split_defaults_for_task(str(task_id))


def _completion_trace_payload(
    *,
    query: _ResolvedQuery,
    rendered: _CompletionScene,
    prompt_defaults: Mapping[str, Any],
    prompt_artifacts: Any,
    annotation_value: List[List[float]],
) -> Dict[str, Any]:
    candidate_trace = {
        str(label): {
            "point_graph": [int(value) for value in rendered.candidate_points_by_label[str(label)]],
            "point_px": [float(value) for value in rendered.candidate_points_px_by_label[str(label)]],
            "bbox_px": list(rendered.candidate_bboxes_by_label[str(label)]),
            "classification_with_known_points": _classify_point_set(
                [*rendered.known_points, rendered.candidate_points_by_label[str(label)]]
            ),
            "is_answer": str(label) == str(query.winner_label),
        }
        for label in sorted(rendered.candidate_points_by_label)
    }
    return {
        "scene_ir": {
            "scene_kind": "geometry_coordinate_quadrilateral_candidate",
            "entities": [
                {
                    "entity_type": "known_point",
                    "point_graph": [int(value) for value in point],
                    "point_px": [float(value) for value in rendered.known_points_px[index]],
                }
                for index, point in enumerate(rendered.known_points)
            ]
            + [
                {
                    "entity_type": "candidate_point",
                    "label": str(label),
                    **dict(candidate_trace[str(label)]),
                }
                for label in sorted(candidate_trace)
            ],
            "relations": {
                "scene_id": COMPLETION_SCENE_ID,
                "query_id": str(query.query_id),
                "query_id_probabilities": dict(query.query_probabilities),
                "target_kind": str(query.target_kind),
                "target_shape_name": str(query.target_shape_name),
                "winner_label": str(query.winner_label),
            },
        },
        "query_spec": {
            "query_id": str(query.query_id),
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": {
                "scene_id": COMPLETION_SCENE_ID,
                "query_id": str(query.query_id),
                "query_id_probabilities": dict(query.query_probabilities),
                "target_kind": str(query.target_kind),
                "target_shape_name": str(query.target_shape_name),
                "winner_label": str(query.winner_label),
                "winner_label_probabilities": dict(query.winner_label_probabilities),
                "candidate_label_pool": list(rendered.candidate_points_by_label.keys()),
                "completion_candidate_count_probabilities": dict(rendered.option_count_probabilities),
            },
        },
        "render_spec": {
            **dict(rendered.render_spec_extra),
            "scene_id": COMPLETION_SCENE_ID,
            "marker_style": dict(rendered.marker_meta),
            "post_image_noise": dict(rendered.post_noise_meta),
            "background_style": dict(rendered.background_meta),
        },
        "render_map": {
            "coord_space": "pixel",
            "known_points_graph": [[int(value) for value in point] for point in rendered.known_points],
            "known_points_px": [[float(value) for value in point] for point in rendered.known_points_px],
            "candidate_points_graph_by_label": {
                str(label): [int(value) for value in point] for label, point in rendered.candidate_points_by_label.items()
            },
            "candidate_points_px_by_label": {
                str(label): [float(value) for value in point] for label, point in rendered.candidate_points_px_by_label.items()
            },
            "candidate_bboxes_px_by_label": dict(rendered.candidate_bboxes_by_label),
        },
        "execution_trace": {
            "scene_id": COMPLETION_SCENE_ID,
            "query_id": str(query.query_id),
            "answer_type": "option_letter",
            "answer_value": str(query.winner_label),
            "target_kind": str(query.target_kind),
            "target_shape_name": str(query.target_shape_name),
            "known_points_graph": [[int(value) for value in point] for point in rendered.known_points],
            "missing_point_graph": [int(value) for value in rendered.missing_point],
            "candidate_points_by_label": dict(candidate_trace),
            "target_ordered_vertices": [[int(value) for value in point] for point in rendered.target_ordered_vertices],
            "query_id_probabilities": dict(query.query_probabilities),
            "completion_candidate_count_probabilities": dict(rendered.option_count_probabilities),
        },
        "witness_symbolic": {
            "type": "coordinate_quadrilateral_completion",
            "answer_label": str(query.winner_label),
            "target_kind": str(query.target_kind),
            "known_points_graph": [[int(value) for value in point] for point in rendered.known_points],
            "missing_point_graph": [int(value) for value in rendered.missing_point],
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


def _panel_trace_payload(
    *,
    query: _ResolvedQuery,
    rendered: _PanelScene,
    prompt_defaults: Mapping[str, Any],
    prompt_artifacts: Any,
    annotation_value: List[List[int]],
) -> Dict[str, Any]:
    panels_trace = {
        str(label): {
            "label": str(label),
            "points_graph": [[int(value) for value in point] for point in spec.points],
            "classified_kind": str(spec.classified_kind),
            "panel_bbox": list(spec.panel_bbox),
            "plot_bbox": list(spec.plot_bbox),
            "is_answer": str(label) == str(query.winner_label),
        }
        for label, spec in rendered.panels_by_label.items()
    }

    return {
        "scene_ir": {
            "scene_kind": "geometry_coordinate_panels",
            "entities": [dict(panels_trace[str(label)]) for label in sorted(panels_trace)],
            "relations": {
                "scene_id": PANEL_SCENE_ID,
                "query_id": str(query.query_id),
                "query_id_probabilities": dict(query.query_probabilities),
                "target_kind": str(query.target_kind),
                "target_shape_name": str(query.target_shape_name),
                "winner_label": str(query.winner_label),
            },
        },
        "query_spec": {
            "query_id": str(query.query_id),
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": {
                "scene_id": PANEL_SCENE_ID,
                "query_id": str(query.query_id),
                "query_id_probabilities": dict(query.query_probabilities),
                "target_kind": str(query.target_kind),
                "target_shape_name": str(query.target_shape_name),
                "winner_label": str(query.winner_label),
                "winner_label_probabilities": dict(query.winner_label_probabilities),
                "candidate_label_pool": list(rendered.panels_by_label.keys()),
                "panel_count_probabilities": dict(rendered.option_count_probabilities),
            },
        },
        "render_spec": {
            "canvas_width": int(rendered.image.size[0]),
            "canvas_height": int(rendered.image.size[1]),
            "coord_space": "pixel",
            "scene_id": PANEL_SCENE_ID,
            "panel_count": int(len(rendered.panels_by_label)),
            "panel_count_probabilities": dict(rendered.option_count_probabilities),
            "panel_style": dict(rendered.panel_style_meta),
            "marker_style": dict(rendered.marker_meta),
            "background_style": dict(rendered.background_meta),
            "post_image_noise": dict(rendered.post_noise_meta),
        },
        "render_map": {
            "coord_space": "pixel",
            "panel_bboxes": {str(label): list(spec.panel_bbox) for label, spec in rendered.panels_by_label.items()},
            "plot_bboxes": {str(label): list(spec.plot_bbox) for label, spec in rendered.panels_by_label.items()},
            "points_graph_by_label": {
                str(label): [[int(value) for value in point] for point in spec.points]
                for label, spec in rendered.panels_by_label.items()
            },
        },
        "execution_trace": {
            "scene_id": PANEL_SCENE_ID,
            "query_id": str(query.query_id),
            "answer_type": "option_letter",
            "answer_value": str(query.winner_label),
            "target_kind": str(query.target_kind),
            "target_shape_name": str(query.target_shape_name),
            "panels_by_label": dict(panels_trace),
            "query_id_probabilities": dict(query.query_probabilities),
            "panel_count_probabilities": dict(rendered.option_count_probabilities),
        },
        "witness_symbolic": {
            "type": "coordinate_quadrilateral_shape_panel_match",
            "answer_label": str(query.winner_label),
            "target_kind": str(query.target_kind),
            "panels_by_label": dict(panels_trace),
        },
        "projected_annotation": {
            "type": "bbox_set",
            "bbox_set": list(annotation_value),
            "panel_bbox_by_label": {str(label): list(spec.panel_bbox) for label, spec in rendered.panels_by_label.items()},
        },
    }


def _completion_point_annotation(rendered: _CompletionScene, label: str) -> List[List[float]]:
    point = rendered.candidate_points_px_by_label[str(label)]
    return [[float(point[0]), float(point[1])]]


@register_task
class GeometryCoordinateQuadrilateralCompletionLabelTask:
    """Choose the candidate point that completes a coordinate quadrilateral."""

    task_id = COMPLETION_TASK_ID
    domain = "geometry"
    task_group = "coordinate"
    default_dataset_enabled = True
    scene_id = COMPLETION_SCENE_ID
    public_scene_id = COMPLETION_SCENE_ID

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        generation_defaults, rendering_defaults, prompt_defaults_all = _prompt_defaults(self.task_id)
        label_pool = _resolve_label_pool(
            params,
            generation_defaults,
            "completion_candidate_labels",
            DEFAULT_COMPLETION_LABEL_POOL,
        )
        query = _resolve_query(
            task_id=self.task_id,
            query_ids=COMPLETION_QUERY_IDS,
            scene_label_pool=label_pool,
            instance_seed=int(instance_seed),
            params=params,
        )
        rendered = _render_completion_scene(
            query,
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
            context=f"prompt defaults for {self.task_id}",
        )
        annotation_value = _completion_point_annotation(rendered, str(query.winner_label))
        json_example, json_example_answer_only = resolve_prompt_json_examples(
            prompt_defaults_all,
            annotation_value=annotation_value,
            answer_type="option_letter",
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
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint_candidate_point"]),
                "answer_hint": str(prompt_defaults["answer_hint_option_letter"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        trace_payload = _completion_trace_payload(
            query=query,
            rendered=rendered,
            prompt_defaults=prompt_defaults,
            prompt_artifacts=prompt_artifacts,
            annotation_value=annotation_value,
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="option_letter", value=str(query.winner_label)),
            annotation_gt=TypedValue(type="point_set", value=annotation_value),
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(
                task_id=self.task_id,
                query_id=str(query.query_id),
                object_count=3 + len(rendered.candidate_points_by_label),
            ),
            task_versions=default_task_versions(),
            scene_id=COMPLETION_SCENE_ID,
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class GeometryCoordinateQuadrilateralShapeMatchLabelTask:
    """Choose the coordinate panel whose four points form the requested quadrilateral."""

    task_id = SHAPE_MATCH_TASK_ID
    domain = "geometry"
    task_group = "coordinate"
    default_dataset_enabled = True
    scene_id = PANEL_SCENE_ID
    public_scene_id = PANEL_SCENE_ID

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        generation_defaults, rendering_defaults, prompt_defaults_all = _prompt_defaults(self.task_id)
        label_pool = _resolve_label_pool(params, generation_defaults, "panel_labels", DEFAULT_PANEL_LABEL_POOL)
        query = _resolve_query(
            task_id=self.task_id,
            query_ids=SHAPE_MATCH_QUERY_IDS,
            scene_label_pool=label_pool,
            instance_seed=int(instance_seed),
            params=params,
        )
        rendered = _render_panel_scene(
            query,
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
                "annotation_hint_selected_panel_bbox",
                "answer_hint_option_letter",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        annotation_value = [list(rendered.panels_by_label[str(query.winner_label)].panel_bbox)]
        json_example, json_example_answer_only = resolve_prompt_json_examples(
            prompt_defaults_all,
            annotation_value=annotation_value,
            answer_type="option_letter",
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
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint_selected_panel_bbox"]),
                "answer_hint": str(prompt_defaults["answer_hint_option_letter"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        trace_payload = _panel_trace_payload(
            query=query,
            rendered=rendered,
            prompt_defaults=prompt_defaults,
            prompt_artifacts=prompt_artifacts,
            annotation_value=annotation_value,
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="option_letter", value=str(query.winner_label)),
            annotation_gt=TypedValue(type="bbox_set", value=annotation_value),
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(
                task_id=self.task_id,
                query_id=str(query.query_id),
                object_count=4,
                panel_count=len(rendered.panels_by_label),
            ),
            task_versions=default_task_versions(),
            scene_id=PANEL_SCENE_ID,
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = [
    "GeometryCoordinateQuadrilateralCompletionLabelTask",
    "GeometryCoordinateQuadrilateralShapeMatchLabelTask",
]
