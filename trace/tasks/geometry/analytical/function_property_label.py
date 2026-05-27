"""Analytical 2D function-property label task with six mini coordinate panels."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.sampling import normalize_positive_weights, weighted_choice
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import resolve_prompt_json_examples
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.variant_sampling import (
    apply_balanced_variant_sampling,
    has_non_null_param,
    is_uniform_probability_map,
    resolve_variant,
)
from ..shared.complexity import build_geometry_task_complexity, clamp_unit_interval, resolve_geometry_complexity_weights
from ..shared.coordinate_panel_grid import (
    CoordinatePanelConfig,
    CoordinatePanelStyle,
    coordinate_panel_layout,
    draw_coordinate_panel_grid,
    draw_endpoint,
    graph_point_to_panel_pixel,
    linspace,
    panel_bbox_for_index,
    plot_bbox_for_panel,
)
from ..shared.diagram_style import (
    GeometryDiagramStyle,
    geometry_coordinate_panel_style_from_diagram_style,
    prepare_geometry_diagram_style_and_background,
)
from ..shared.fixed_query_task import MultiFixedGeometryQueryTaskMixin
from ..shared.noise_defaults import load_geometry_noise_defaults

Point = Tuple[float, float]
BBox = Tuple[int, int, int, int]

TASK_ID = "geometry_analytical_function_property_label_base"
MONOTONIC_INTERVAL_INCREASING_LABEL = "monotonic_interval_increasing_label"
MONOTONIC_INTERVAL_DECREASING_LABEL = "monotonic_interval_decreasing_label"
SIGN_INTERVAL_POSITIVE_LABEL = "sign_interval_positive_label"
SIGN_INTERVAL_NEGATIVE_LABEL = "sign_interval_negative_label"
MONOTONIC_INTERVAL_VARIANTS: Tuple[str, ...] = (
    MONOTONIC_INTERVAL_INCREASING_LABEL,
    MONOTONIC_INTERVAL_DECREASING_LABEL,
)
SIGN_INTERVAL_VARIANTS: Tuple[str, ...] = (
    SIGN_INTERVAL_POSITIVE_LABEL,
    SIGN_INTERVAL_NEGATIVE_LABEL,
)
INTERVAL_PROPERTY_VARIANTS: Tuple[str, ...] = MONOTONIC_INTERVAL_VARIANTS + SIGN_INTERVAL_VARIANTS
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "function_status_label",
    "one_to_one_status_label",
    "domain_match_label",
    "range_match_label",
    "y_axis_symmetry_label",
    "x_axis_symmetry_label",
    "origin_symmetry_label",
    *INTERVAL_PROPERTY_VARIANTS,
)
DEFAULT_LABEL_POOL: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "analytical")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_POST_IMAGE_NOISE_DEFAULTS = load_geometry_noise_defaults(task_group="analytical")
_GRID_MIN = -5
_GRID_MAX = 5
_PANEL_COLUMNS = 3
_PANEL_ROWS = 2
_PANEL_COUNT = 6
_PANEL_CONFIG = CoordinatePanelConfig(grid_min=_GRID_MIN, grid_max=_GRID_MAX, columns=_PANEL_COLUMNS, rows=_PANEL_ROWS)
Color = Tuple[int, int, int]
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
_LINE_COLOR_PALETTES: Tuple[Tuple[Color, ...], ...] = (
    (
        (27, 96, 168),
        (37, 132, 91),
        (169, 73, 32),
        (126, 74, 157),
        (183, 94, 127),
        (82, 103, 126),
    ),
    (
        (24, 105, 164),
        (22, 129, 114),
        (183, 91, 42),
        (117, 80, 178),
        (176, 66, 104),
        (92, 103, 72),
    ),
    (
        (35, 87, 158),
        (62, 126, 80),
        (158, 89, 51),
        (138, 75, 134),
        (169, 101, 52),
        (68, 112, 132),
    ),
)


@dataclass(frozen=True)
class _RelationSpec:
    """One graph relation rendered inside a mini coordinate panel."""

    relation_id: str
    draw_kind: str
    domain: Tuple[float, float]
    range: Tuple[float, float]
    is_function: bool
    is_one_to_one: bool
    points: Tuple[Point, ...] = ()
    center: Point | None = None
    radii: Point | None = None
    x_range: Tuple[float, float] | None = None
    y_range: Tuple[float, float] | None = None
    vertex: Point | None = None
    coefficient: float = 1.0
    symmetry_axes: Tuple[str, ...] = ()


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved task axes for one generated instance."""

    query_id: str
    query_id_probabilities: Dict[str, float]
    winner_label: str
    winner_label_probabilities: Dict[str, float]
    label_pool: Tuple[str, ...]
    target_interval: Tuple[float, float] | None = None


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered image plus traceable relation-panel metadata."""

    image: Image.Image
    background_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]
    diagram_style_meta: Dict[str, Any]
    panel_style_meta: Dict[str, Any]
    line_color_meta: Dict[str, Any]
    line_colors: Tuple[Color, ...]
    relations_by_label: Dict[str, _RelationSpec]
    panel_bboxes: Dict[str, List[int]]
    plot_bboxes: Dict[str, List[int]]
    target_domain: str
    target_range: str
    target_interval: str


def _format_number(value: float) -> str:
    rounded = round(float(value))
    if abs(float(value) - float(rounded)) <= 1e-9:
        return str(int(rounded))
    return f"{float(value):.1f}".rstrip("0").rstrip(".")


def _format_interval(interval: Sequence[float]) -> str:
    return f"[{_format_number(float(interval[0]))}, {_format_number(float(interval[1]))}]"


def _color_triplet(value: Any) -> Color:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 3:
        raise ValueError("expected an RGB color triple")
    return (
        max(0, min(255, int(value[0]))),
        max(0, min(255, int(value[1]))),
        max(0, min(255, int(value[2]))),
    )


def _resolve_panel_style(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    diagram_style: GeometryDiagramStyle | None = None,
) -> Tuple[CoordinatePanelStyle, Dict[str, Any]]:
    explicit_index = params.get("panel_style_index")
    if explicit_index is not None:
        style_index = int(explicit_index) % len(_PANEL_STYLES)
        return _PANEL_STYLES[int(style_index)], {
            "source": "params",
            "style_index": int(style_index),
            "style": _PANEL_STYLES[int(style_index)].to_trace_dict(),
        }
    if diagram_style is not None:
        style = geometry_coordinate_panel_style_from_diagram_style(diagram_style)
        return style, {
            "source": "technical_diagram_style",
            "style_pack": str(diagram_style.style_pack),
            "treatment": str(diagram_style.treatment),
            "palette_id": str(diagram_style.palette_id),
            "style": style.to_trace_dict(),
        }

    selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.panel_style",
    )
    style_index = int(selection_index) % len(_PANEL_STYLES)
    style = _PANEL_STYLES[int(style_index)]
    return style, {
        "source": "selection_index",
        "selection_index": int(selection_index),
        "style_index": int(style_index),
        "style": style.to_trace_dict(),
    }


def _resolve_line_colors(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[Tuple[Color, ...], Dict[str, Any]]:
    explicit = params.get("line_colors")
    if explicit is not None:
        if not isinstance(explicit, Sequence) or isinstance(explicit, (str, bytes)):
            raise ValueError("line_colors must be a sequence of RGB triples")
        colors = tuple(_color_triplet(color) for color in explicit)
        if len(colors) < _PANEL_COUNT:
            raise ValueError("line_colors must contain at least one color per panel")
        return colors, {
            "source": "params",
            "palette_index": None,
            "order": "as_provided",
            "colors": [list(color) for color in colors],
        }

    selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.line_colors",
    )
    palette_index = int(selection_index) % len(_LINE_COLOR_PALETTES)
    rotation = (int(selection_index) // len(_LINE_COLOR_PALETTES)) % _PANEL_COUNT
    palette = tuple(_LINE_COLOR_PALETTES[int(palette_index)])
    colors = tuple(palette[(index + int(rotation)) % len(palette)] for index in range(len(palette)))
    return colors, {
        "source": "selection_index",
        "selection_index": int(selection_index),
        "palette_index": int(palette_index),
        "rotation": int(rotation),
        "colors": [list(color) for color in colors],
    }


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query_id")
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_QUERY_IDS,
        balance_flag_key="balanced_query_id_sampling",
        explicit_key="query_id",
        weights_key="query_id_weights",
        sampling_namespace=f"{TASK_ID}.query_id",
    )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_label_pool(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw_pool = params.get("candidate_label_pool", group_default(_GEN_DEFAULTS, "candidate_label_pool", DEFAULT_LABEL_POOL))
    label_pool = tuple(str(label).strip().upper() for label in raw_pool)
    if len(label_pool) != _PANEL_COUNT or len(set(label_pool)) != _PANEL_COUNT:
        raise ValueError("function_property_label requires exactly six unique candidate labels")
    return label_pool


def _decoupled_winner_label_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    winner_params = dict(params)
    if "winner_label" not in winner_params and "answer_label" in winner_params:
        winner_params["winner_label"] = winner_params["answer_label"]
    return winner_params


def _resolve_winner_label(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    query_id: str,
    label_pool: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    winner_params = _decoupled_winner_label_params(params)
    label_set = tuple(str(label).upper() for label in label_pool)
    explicit = winner_params.get("winner_label")
    if explicit is not None:
        winner_label = str(explicit).strip().upper()
        if winner_label not in set(label_set):
            raise ValueError(f"unsupported winner_label: {winner_label}")
        return winner_label, {label: (1.0 if label == winner_label else 0.0) for label in label_set}

    raw_weights = winner_params.get("winner_label_weights", {label: 1.0 for label in label_set})
    if not isinstance(raw_weights, Mapping):
        raise ValueError("winner_label_weights must be a mapping when provided")
    weights = {str(key).upper(): float(value) for key, value in raw_weights.items() if str(key).upper() in set(label_set)}
    probabilities = normalize_positive_weights(weights, default_keys=label_set)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.winner_label")
    winner_label = str(weighted_choice(rng, probabilities, sort_keys=True)).upper()

    enabled = bool(winner_params.get("balanced_sampling", group_default(_GEN_DEFAULTS, "balanced_sampling", True)))
    overridden = any(has_non_null_param(winner_params, key) for key in ("winner_label", "answer_label", "winner_label_weights"))
    if bool(enabled) and (not overridden) and is_uniform_probability_map(probabilities):
        selection_index = resolve_selection_index(
            params=winner_params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.winner_label.{query_id}",
        )
        winner_label = str(label_set[int(selection_index) % len(label_set)])
    return winner_label, {str(key): float(value) for key, value in sorted(probabilities.items())}


def _target_interval_for_variant(query_id: str) -> Tuple[float, float] | None:
    """Return the prompt-facing x-interval for interval-property tasks."""

    if str(query_id) in set(MONOTONIC_INTERVAL_VARIANTS):
        return (-2.0, 2.0)
    if str(query_id) in set(SIGN_INTERVAL_VARIANTS):
        return (-4.0, 4.0)
    return None


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
    label_pool = _resolve_label_pool(params)
    winner_label, winner_label_probabilities = _resolve_winner_label(
        params,
        instance_seed=int(instance_seed),
        query_id=str(query_id),
        label_pool=label_pool,
    )
    return _ResolvedQuery(
        query_id=str(query_id),
        query_id_probabilities=dict(query_id_probabilities),
        winner_label=str(winner_label),
        winner_label_probabilities=dict(winner_label_probabilities),
        label_pool=tuple(label_pool),
        target_interval=_target_interval_for_variant(str(query_id)),
    )


def _line(relation_id: str, start: Point, end: Point, *, one_to_one: bool = True) -> _RelationSpec:
    domain = (min(float(start[0]), float(end[0])), max(float(start[0]), float(end[0])))
    range_ = (min(float(start[1]), float(end[1])), max(float(start[1]), float(end[1])))
    is_function = abs(float(start[0]) - float(end[0])) > 1e-9
    return _RelationSpec(
        relation_id=str(relation_id),
        draw_kind="polyline",
        points=(start, end),
        domain=domain,
        range=range_,
        is_function=bool(is_function),
        is_one_to_one=bool(is_function and one_to_one and abs(float(start[1]) - float(end[1])) > 1e-9),
    )


def _polyline(
    relation_id: str,
    points: Sequence[Point],
    *,
    is_function: bool,
    is_one_to_one: bool,
) -> _RelationSpec:
    domain = (min(float(point[0]) for point in points), max(float(point[0]) for point in points))
    range_ = (min(float(point[1]) for point in points), max(float(point[1]) for point in points))
    return _RelationSpec(
        relation_id=str(relation_id),
        draw_kind="polyline",
        points=tuple((float(x), float(y)) for x, y in points),
        domain=domain,
        range=range_,
        is_function=bool(is_function),
        is_one_to_one=bool(is_one_to_one),
    )


def _sampled_curve_relation(
    relation_id: str,
    draw_kind: str,
    points: Sequence[Point],
    *,
    is_one_to_one: bool,
) -> _RelationSpec:
    domain = (min(float(point[0]) for point in points), max(float(point[0]) for point in points))
    range_ = (min(float(point[1]) for point in points), max(float(point[1]) for point in points))
    return _RelationSpec(
        relation_id=str(relation_id),
        draw_kind=str(draw_kind),
        points=tuple((float(x), float(y)) for x, y in points),
        domain=domain,
        range=range_,
        is_function=True,
        is_one_to_one=bool(is_one_to_one),
    )


def _tag_symmetry(relation: _RelationSpec, *axes: str) -> _RelationSpec:
    ordered_axes = tuple(axis for axis in ("x_axis", "y_axis", "origin") if axis in {str(value) for value in axes})
    return replace(relation, symmetry_axes=ordered_axes)


def _ellipse(relation_id: str, center: Point, radii: Point, *, is_circle: bool = False) -> _RelationSpec:
    del is_circle
    cx, cy = float(center[0]), float(center[1])
    rx, ry = abs(float(radii[0])), abs(float(radii[1]))
    return _RelationSpec(
        relation_id=str(relation_id),
        draw_kind="ellipse",
        center=(cx, cy),
        radii=(rx, ry),
        domain=(cx - rx, cx + rx),
        range=(cy - ry, cy + ry),
        is_function=False,
        is_one_to_one=False,
    )


def _parabola_up(relation_id: str, *, vertex: Point, x_range: Tuple[float, float], coefficient: float) -> _RelationSpec:
    vx, vy = float(vertex[0]), float(vertex[1])
    x0, x1 = float(x_range[0]), float(x_range[1])
    y0 = float(coefficient) * ((x0 - vx) ** 2) + vy
    y1 = float(coefficient) * ((x1 - vx) ** 2) + vy
    return _RelationSpec(
        relation_id=str(relation_id),
        draw_kind="parabola_up",
        x_range=(x0, x1),
        vertex=(vx, vy),
        coefficient=float(coefficient),
        domain=(min(x0, x1), max(x0, x1)),
        range=(vy, max(y0, y1)),
        is_function=True,
        is_one_to_one=False,
    )


def _sideways_parabola(
    relation_id: str,
    *,
    vertex: Point,
    y_range: Tuple[float, float],
    coefficient: float,
) -> _RelationSpec:
    vx, vy = float(vertex[0]), float(vertex[1])
    y0, y1 = float(y_range[0]), float(y_range[1])
    x0 = float(coefficient) * ((y0 - vy) ** 2) + vx
    x1 = float(coefficient) * ((y1 - vy) ** 2) + vx
    return _RelationSpec(
        relation_id=str(relation_id),
        draw_kind="sideways_parabola",
        y_range=(y0, y1),
        vertex=(vx, vy),
        coefficient=float(coefficient),
        domain=(vx, max(x0, x1)),
        range=(min(y0, y1), max(y0, y1)),
        is_function=False,
        is_one_to_one=False,
    )


def _random_slanted_line(rng, relation_id: str, *, positive_slope: bool | None = None) -> _RelationSpec:
    for _ in range(100):
        x0 = int(rng.randint(-4, 1))
        x1 = int(rng.randint(x0 + 3, 4))
        if positive_slope is None:
            positive = bool(rng.choice((False, True)))
        else:
            positive = bool(positive_slope)
        if positive:
            y0 = int(rng.randint(-4, 1))
            y1 = int(rng.randint(y0 + 2, 4))
        else:
            y0 = int(rng.randint(-1, 4))
            y1 = int(rng.randint(-4, y0 - 2))
        return _line(str(relation_id), (float(x0), float(y0)), (float(x1), float(y1)), one_to_one=True)
    raise RuntimeError("failed to sample slanted line relation")


def _random_horizontal_line(rng, relation_id: str) -> _RelationSpec:
    x0 = int(rng.randint(-4, 1))
    x1 = int(rng.randint(x0 + 3, 4))
    y = int(rng.randint(-4, 4))
    return _line(str(relation_id), (float(x0), float(y)), (float(x1), float(y)), one_to_one=False)


def _random_vertical_segment(rng, relation_id: str) -> _RelationSpec:
    x = int(rng.randint(-4, 4))
    y0 = int(rng.randint(-4, 1))
    y1 = int(rng.randint(y0 + 3, 4))
    return _polyline(
        str(relation_id),
        ((float(x), float(y0)), (float(x), float(y1))),
        is_function=False,
        is_one_to_one=False,
    )


def _random_v_shape(rng, relation_id: str) -> _RelationSpec:
    vertex_x = int(rng.randint(-1, 1))
    vertex_y = int(rng.randint(-4, -1))
    left_x = int(rng.randint(-4, vertex_x - 2))
    right_x = int(rng.randint(vertex_x + 2, 4))
    endpoint_y = int(rng.randint(vertex_y + 2, 4))
    return _polyline(
        str(relation_id),
        ((float(left_x), float(endpoint_y)), (float(vertex_x), float(vertex_y)), (float(right_x), float(endpoint_y))),
        is_function=True,
        is_one_to_one=False,
    )


def _random_sideways_v(rng, relation_id: str) -> _RelationSpec:
    vertex_x = int(rng.randint(-4, -1))
    vertex_y = int(rng.randint(-1, 1))
    endpoint_x = int(rng.randint(vertex_x + 3, 4))
    upper_y = int(rng.randint(vertex_y + 2, 4))
    lower_y = int(rng.randint(-4, vertex_y - 2))
    return _polyline(
        str(relation_id),
        ((float(endpoint_x), float(upper_y)), (float(vertex_x), float(vertex_y)), (float(endpoint_x), float(lower_y))),
        is_function=False,
        is_one_to_one=False,
    )


def _random_parabola_up(rng, relation_id: str) -> _RelationSpec:
    coefficients = (0.35, 0.45, 0.55, 0.65)
    for _ in range(100):
        vertex_x = int(rng.randint(-1, 1))
        vertex_y = int(rng.randint(-4, -1))
        half_width = int(rng.choice((2, 3)))
        coefficient = float(rng.choice(coefficients))
        x_range = (float(vertex_x - half_width), float(vertex_x + half_width))
        if x_range[0] < -4.5 or x_range[1] > 4.5:
            continue
        y_edge = float(coefficient * (half_width ** 2) + vertex_y)
        if y_edge <= 4.6:
            return _parabola_up(
                str(relation_id),
                vertex=(float(vertex_x), float(vertex_y)),
                x_range=x_range,
                coefficient=float(coefficient),
            )
    raise RuntimeError("failed to sample upward parabola relation")


def _random_sideways_parabola(rng, relation_id: str) -> _RelationSpec:
    coefficients = (0.35, 0.45, 0.55, 0.65)
    for _ in range(100):
        vertex_x = int(rng.randint(-4, -1))
        vertex_y = int(rng.randint(-1, 1))
        half_height = int(rng.choice((2, 3)))
        coefficient = float(rng.choice(coefficients))
        y_range = (float(vertex_y - half_height), float(vertex_y + half_height))
        if y_range[0] < -4.5 or y_range[1] > 4.5:
            continue
        x_edge = float(coefficient * (half_height ** 2) + vertex_x)
        if x_edge <= 4.6:
            return _sideways_parabola(
                str(relation_id),
                vertex=(float(vertex_x), float(vertex_y)),
                y_range=y_range,
                coefficient=float(coefficient),
            )
    raise RuntimeError("failed to sample sideways parabola relation")


def _random_ellipse(rng, relation_id: str, *, circle: bool = False) -> _RelationSpec:
    for _ in range(100):
        if circle:
            radius = float(rng.choice((1.5, 2.0, 2.5)))
            rx = radius
            ry = radius
        else:
            rx = float(rng.choice((1.5, 2.0, 2.5, 3.0)))
            ry_options = [value for value in (1.0, 1.5, 2.0, 2.5, 3.0) if abs(float(value) - float(rx)) >= 0.5]
            ry = float(rng.choice(ry_options))
        cx_min = int(-4 + int(rx))
        cx_max = int(4 - int(rx))
        cy_min = int(-4 + int(ry))
        cy_max = int(4 - int(ry))
        if cx_min > cx_max or cy_min > cy_max:
            continue
        cx = float(rng.randint(cx_min, cx_max))
        cy = float(rng.randint(cy_min, cy_max))
        return _ellipse(str(relation_id), (cx, cy), (rx, ry), is_circle=bool(circle))
    raise RuntimeError("failed to sample ellipse relation")


def _random_monotone_endpoints(rng, *, increasing: bool) -> Tuple[float, float, float, float]:
    x0 = int(rng.randint(-4, -1))
    x1 = int(rng.randint(x0 + 3, 4))
    if bool(increasing):
        y0 = int(rng.randint(-4, 1))
        y1 = int(rng.randint(y0 + 2, 4))
    else:
        y0 = int(rng.randint(-1, 4))
        y1 = int(rng.randint(-4, y0 - 2))
    return float(x0), float(x1), float(y0), float(y1)


def _random_exponential_curve(rng, relation_id: str, *, increasing: bool | None = None) -> _RelationSpec:
    positive = bool(rng.choice((False, True))) if increasing is None else bool(increasing)
    x0, x1, y0, y1 = _random_monotone_endpoints(rng, increasing=positive)
    curvature = float(rng.choice((1.2, 1.5, 1.9, 2.3)))
    denom = math.exp(curvature) - 1.0
    points = []
    for x in linspace(x0, x1, 80):
        t = (float(x) - x0) / max(1e-9, x1 - x0)
        eased = (math.exp(curvature * t) - 1.0) / denom
        points.append((float(x), y0 + (y1 - y0) * eased))
    return _sampled_curve_relation(str(relation_id), "exponential", points, is_one_to_one=True)


def _random_logarithmic_curve(rng, relation_id: str, *, increasing: bool | None = None) -> _RelationSpec:
    positive = bool(rng.choice((False, True))) if increasing is None else bool(increasing)
    x0, x1, y0, y1 = _random_monotone_endpoints(rng, increasing=positive)
    curvature = float(rng.choice((3.0, 5.0, 8.0, 12.0)))
    denom = math.log1p(curvature)
    points = []
    for x in linspace(x0, x1, 80):
        t = (float(x) - x0) / max(1e-9, x1 - x0)
        eased = math.log1p(curvature * t) / denom
        points.append((float(x), y0 + (y1 - y0) * eased))
    return _sampled_curve_relation(str(relation_id), "logarithmic", points, is_one_to_one=True)


def _random_monotone_cubic_curve(rng, relation_id: str, *, increasing: bool | None = None) -> _RelationSpec:
    positive = bool(rng.choice((False, True))) if increasing is None else bool(increasing)
    x0, x1, y0, y1 = _random_monotone_endpoints(rng, increasing=positive)
    bend = float(rng.choice((-0.16, -0.10, 0.10, 0.16)))
    points = []
    for x in linspace(x0, x1, 90):
        t = (float(x) - x0) / max(1e-9, x1 - x0)
        # Strictly monotone cubic easing: the small cubic term changes shape
        # without reversing the y order.
        eased = t + bend * ((2.0 * t - 1.0) ** 3 - (2.0 * t - 1.0))
        points.append((float(x), y0 + (y1 - y0) * eased))
    return _sampled_curve_relation(str(relation_id), "monotone_cubic", points, is_one_to_one=True)


def _random_monotone_piecewise_curve(rng, relation_id: str, *, increasing: bool | None = None) -> _RelationSpec:
    positive = bool(rng.choice((False, True))) if increasing is None else bool(increasing)
    x0, x3, y0, y3 = _random_monotone_endpoints(rng, increasing=positive)
    x1 = float(rng.randint(int(x0) + 1, int(x3) - 2))
    x2 = float(rng.randint(int(x1) + 1, int(x3) - 1))
    low_y = min(float(y0), float(y3))
    high_y = max(float(y0), float(y3))
    span = max(1.0, high_y - low_y)
    t1 = float(rng.choice((0.28, 0.36, 0.44)))
    t2 = float(rng.choice((0.56, 0.64, 0.72)))
    if positive:
        y1 = low_y + span * t1
        y2 = low_y + span * t2
    else:
        y1 = high_y - span * t1
        y2 = high_y - span * t2
    return _polyline(
        str(relation_id),
        ((float(x0), float(y0)), (float(x1), float(y1)), (float(x2), float(y2)), (float(x3), float(y3))),
        is_function=True,
        is_one_to_one=True,
    )


def _random_sinusoidal_curve(rng, relation_id: str) -> _RelationSpec:
    for _ in range(100):
        x0 = float(int(rng.randint(-4, -3)))
        x1 = float(int(rng.randint(3, 4)))
        amplitude = float(rng.choice((1.4, 1.7, 2.0, 2.2)))
        center_y = float(rng.choice((-1.0, 0.0, 1.0)))
        cycles = float(rng.choice((1.0, 1.25, 1.5)))
        phase = float(rng.choice((0.0, math.pi / 4.0, math.pi / 2.0)))
        points = []
        for x in linspace(x0, x1, 100):
            t = (float(x) - x0) / max(1e-9, x1 - x0)
            y = center_y + amplitude * math.sin((2.0 * math.pi * cycles * t) + phase)
            points.append((float(x), float(y)))
        y_values = [point[1] for point in points]
        if min(y_values) >= -4.4 and max(y_values) <= 4.4:
            return _sampled_curve_relation(str(relation_id), "sinusoidal", points, is_one_to_one=False)
    raise RuntimeError("failed to sample sinusoidal relation")


def _random_turning_cubic_curve(rng, relation_id: str) -> _RelationSpec:
    for _ in range(100):
        x_shift = float(rng.choice((-0.8, -0.4, 0.0, 0.4, 0.8)))
        y_shift = float(rng.choice((-0.6, -0.3, 0.0, 0.3, 0.6)))
        scale = float(rng.choice((0.34, 0.40, 0.46)))
        if bool(rng.choice((False, True))):
            scale = -scale
        points = []
        for base_x in linspace(-2.4, 2.4, 90):
            x = float(base_x) + x_shift
            y = y_shift + scale * ((float(base_x) ** 3) - (3.0 * float(base_x)))
            points.append((float(x), float(y)))
        y_values = [point[1] for point in points]
        x_values = [point[0] for point in points]
        if min(x_values) >= -4.4 and max(x_values) <= 4.4 and min(y_values) >= -4.4 and max(y_values) <= 4.4:
            return _sampled_curve_relation(str(relation_id), "turning_cubic", points, is_one_to_one=False)
    raise RuntimeError("failed to sample turning cubic relation")


def _random_nonmonotone_piecewise_curve(rng, relation_id: str) -> _RelationSpec:
    for _ in range(100):
        x0 = float(int(rng.randint(-4, -2)))
        x1 = float(int(rng.randint(int(x0) + 1, 0)))
        x2 = float(int(rng.randint(int(x1) + 1, 2)))
        x3 = float(int(rng.randint(int(x2) + 1, 4)))
        base = float(int(rng.randint(-2, 2)))
        rise = float(rng.choice((2.0, 2.5, 3.0)))
        fall = float(rng.choice((1.5, 2.0, 2.5)))
        if bool(rng.choice((False, True))):
            ys = (base, base + rise, base + rise - fall, base + float(rng.choice((0.5, 1.0, 1.5))))
        else:
            ys = (base, base - rise, base - rise + fall, base - float(rng.choice((0.5, 1.0, 1.5))))
        if min(ys) >= -4.4 and max(ys) <= 4.4:
            return _polyline(
                str(relation_id),
                ((x0, float(ys[0])), (x1, float(ys[1])), (x2, float(ys[2])), (x3, float(ys[3]))),
                is_function=True,
                is_one_to_one=False,
            )
    raise RuntimeError("failed to sample nonmonotone piecewise relation")


def _random_origin_symmetric_sinusoidal_curve(rng, relation_id: str) -> _RelationSpec:
    amplitude = float(rng.choice((1.4, 1.7, 2.0, 2.2)))
    frequency = float(rng.choice((math.pi / 3.0, math.pi / 2.0, 2.0 * math.pi / 3.0)))
    points = [
        (float(x), float(amplitude * math.sin(frequency * float(x))))
        for x in linspace(-4.0, 4.0, 100)
    ]
    return _tag_symmetry(
        _sampled_curve_relation(str(relation_id), "sinusoidal", points, is_one_to_one=False),
        "origin",
    )


def _random_origin_symmetric_cubic_curve(rng, relation_id: str) -> _RelationSpec:
    x_extent = float(rng.choice((2.0, 2.2, 2.4)))
    coefficient = float(rng.choice((0.22, 0.28, 0.34)))
    points = [
        (float(x), float(coefficient * (float(x) ** 3)))
        for x in linspace(-x_extent, x_extent, 90)
    ]
    return _tag_symmetry(
        _sampled_curve_relation(str(relation_id), "cubic", points, is_one_to_one=True),
        "origin",
    )


def _random_y_axis_symmetric_relation(rng, relation_id: str, *, template_index: int) -> _RelationSpec:
    kind = int(template_index) % 3
    if kind == 0:
        vertex_y = float(int(rng.randint(-4, -2)))
        half_width = float(rng.choice((2, 3)))
        coefficient = float(rng.choice((0.35, 0.45, 0.55)))
        return _tag_symmetry(
            _parabola_up(
                str(relation_id),
                vertex=(0.0, vertex_y),
                x_range=(-half_width, half_width),
                coefficient=float(coefficient),
            ),
            "y_axis",
        )
    if kind == 1:
        vertex_y = float(int(rng.randint(-4, -2)))
        endpoint_y = float(int(rng.randint(int(vertex_y) + 2, 4)))
        half_width = float(int(rng.randint(2, 4)))
        return _tag_symmetry(
            _polyline(
                str(relation_id),
                ((-half_width, endpoint_y), (0.0, vertex_y), (half_width, endpoint_y)),
                is_function=True,
                is_one_to_one=False,
            ),
            "y_axis",
        )
    center_y = float(rng.choice((-2.0, -1.5, 1.5, 2.0)))
    return _tag_symmetry(
        _ellipse(
            str(relation_id),
            (0.0, center_y),
            (float(rng.choice((1.5, 2.0, 2.5))), float(rng.choice((1.0, 1.5, 2.0)))),
        ),
        "y_axis",
    )


def _random_x_axis_symmetric_relation(rng, relation_id: str, *, template_index: int) -> _RelationSpec:
    kind = int(template_index) % 3
    if kind == 0:
        vertex_x = float(int(rng.choice((-4, -3, -2))))
        half_height = float(rng.choice((2, 3)))
        coefficient = float(rng.choice((0.35, 0.45, 0.55)))
        return _tag_symmetry(
            _sideways_parabola(
                str(relation_id),
                vertex=(vertex_x, 0.0),
                y_range=(-half_height, half_height),
                coefficient=float(coefficient),
            ),
            "x_axis",
        )
    if kind == 1:
        vertex_x = float(int(rng.choice((-4, -3, -2))))
        endpoint_x = float(int(rng.randint(int(vertex_x) + 3, 4)))
        half_height = float(int(rng.randint(2, 4)))
        return _tag_symmetry(
            _polyline(
                str(relation_id),
                ((endpoint_x, half_height), (vertex_x, 0.0), (endpoint_x, -half_height)),
                is_function=False,
                is_one_to_one=False,
            ),
            "x_axis",
        )
    center_x = float(rng.choice((-2.0, -1.5, 1.5, 2.0)))
    return _tag_symmetry(
        _ellipse(
            str(relation_id),
            (center_x, 0.0),
            (float(rng.choice((1.0, 1.5, 2.0))), float(rng.choice((1.5, 2.0, 2.5)))),
        ),
        "x_axis",
    )


def _random_origin_symmetric_relation(rng, relation_id: str, *, template_index: int) -> _RelationSpec:
    kind = int(template_index) % 3
    if kind == 0:
        x_extent = float(int(rng.randint(2, 4)))
        y_extent = float(int(rng.randint(2, 4)))
        if bool(rng.choice((False, True))):
            y_extent = -y_extent
        return _tag_symmetry(
            _line(str(relation_id), (-x_extent, -y_extent), (x_extent, y_extent), one_to_one=True),
            "origin",
        )
    if kind == 1:
        return _random_origin_symmetric_sinusoidal_curve(rng, str(relation_id))
    return _random_origin_symmetric_cubic_curve(rng, str(relation_id))


def _random_asymmetric_relation(rng, relation_id: str, *, template_index: int) -> _RelationSpec:
    kind = int(template_index) % 4
    if kind == 0:
        return _random_exponential_curve(rng, str(relation_id))
    if kind == 1:
        return _random_logarithmic_curve(rng, str(relation_id))
    if kind == 2:
        vertex_x = float(rng.choice((-2.0, -1.5, 1.5, 2.0)))
        vertex_y = float(int(rng.randint(-4, -2)))
        return _parabola_up(
            str(relation_id),
            vertex=(vertex_x, vertex_y),
            x_range=(vertex_x - 2.0, vertex_x + 2.0),
            coefficient=float(rng.choice((0.35, 0.45, 0.55))),
        )
    return _polyline(
        str(relation_id),
        (
            (float(rng.choice((-4, -3))), float(rng.choice((1, 2, 3)))),
            (float(rng.choice((-1, 1))), float(rng.choice((-4, -3, -2)))),
            (float(rng.choice((3, 4))), float(rng.choice((0, 1, 2)))),
        ),
        is_function=True,
        is_one_to_one=False,
    )


def _sample_symmetry_winner(rng, query_id: str, template_index: int) -> _RelationSpec:
    if str(query_id) == "y_axis_symmetry_label":
        return _random_y_axis_symmetric_relation(rng, "y_axis_symmetric_relation", template_index=int(template_index))
    if str(query_id) == "x_axis_symmetry_label":
        return _random_x_axis_symmetric_relation(rng, "x_axis_symmetric_relation", template_index=int(template_index))
    if str(query_id) == "origin_symmetry_label":
        return _random_origin_symmetric_relation(rng, "origin_symmetric_relation", template_index=int(template_index))
    raise ValueError(f"unsupported symmetry query_id: {query_id}")


def _sample_symmetry_distractors(rng, query_id: str) -> List[_RelationSpec]:
    pools = {
        "y_axis_symmetry_label": (
            lambda index: _random_x_axis_symmetric_relation(rng, f"x_axis_distractor_{index}", template_index=index),
            lambda index: _random_origin_symmetric_relation(rng, f"origin_distractor_{index}", template_index=index),
            lambda index: _random_asymmetric_relation(rng, f"asymmetric_distractor_{index}", template_index=index),
        ),
        "x_axis_symmetry_label": (
            lambda index: _random_y_axis_symmetric_relation(rng, f"y_axis_distractor_{index}", template_index=index),
            lambda index: _random_origin_symmetric_relation(rng, f"origin_distractor_{index}", template_index=index),
            lambda index: _random_asymmetric_relation(rng, f"asymmetric_distractor_{index}", template_index=index),
        ),
        "origin_symmetry_label": (
            lambda index: _random_y_axis_symmetric_relation(rng, f"y_axis_distractor_{index}", template_index=index),
            lambda index: _random_x_axis_symmetric_relation(rng, f"x_axis_distractor_{index}", template_index=index),
            lambda index: _random_asymmetric_relation(rng, f"asymmetric_distractor_{index}", template_index=index),
        ),
    }
    samplers = pools.get(str(query_id))
    if samplers is None:
        raise ValueError(f"unsupported symmetry query_id: {query_id}")
    distractors = [
        samplers[0](0),
        samplers[0](1),
        samplers[1](0),
        samplers[1](1),
        samplers[2](0),
        samplers[2](1),
    ]
    rng.shuffle(distractors)
    return distractors


def _sample_function_winner(rng, template_index: int) -> _RelationSpec:
    kind = int(template_index) % 7
    if kind == 0:
        return _random_slanted_line(rng, "increasing_line_function", positive_slope=True)
    if kind == 1:
        return _random_slanted_line(rng, "decreasing_line_function", positive_slope=False)
    if kind == 2:
        return _random_v_shape(rng, "v_shape_function")
    if kind == 3:
        return _random_parabola_up(rng, "u_shape_function")
    if kind == 4:
        return _random_exponential_curve(rng, "exponential_function")
    if kind == 5:
        return _random_logarithmic_curve(rng, "logarithmic_function")
    return _random_sinusoidal_curve(rng, "sinusoidal_function")


def _sample_one_to_one_winner(rng, template_index: int) -> _RelationSpec:
    kind = int(template_index) % 6
    if kind == 0:
        return _random_exponential_curve(rng, "one_to_one_increasing_exponential", increasing=True)
    if kind == 1:
        return _random_exponential_curve(rng, "one_to_one_decreasing_exponential", increasing=False)
    if kind == 2:
        return _random_logarithmic_curve(rng, "one_to_one_increasing_logarithmic", increasing=True)
    if kind == 3:
        return _random_logarithmic_curve(rng, "one_to_one_decreasing_logarithmic", increasing=False)
    if kind == 4:
        return _random_monotone_cubic_curve(rng, "one_to_one_monotone_cubic")
    return _random_monotone_piecewise_curve(rng, "one_to_one_monotone_piecewise")


def _sample_function_distractors(rng) -> List[_RelationSpec]:
    return [
        _random_ellipse(rng, "ellipse_not_function"),
        _random_ellipse(rng, "circle_not_function", circle=True),
        _random_vertical_segment(rng, "vertical_segment_not_function"),
        _random_sideways_v(rng, "sideways_v_not_function"),
        _random_sideways_parabola(rng, "sideways_parabola_not_function"),
    ]


def _sample_one_to_one_distractors(rng) -> List[_RelationSpec]:
    return [
        _random_v_shape(rng, "v_shape_not_one_to_one"),
        _random_parabola_up(rng, "parabola_not_one_to_one"),
        _random_sinusoidal_curve(rng, "sinusoidal_not_one_to_one"),
        _random_turning_cubic_curve(rng, "turning_cubic_not_one_to_one"),
        _random_nonmonotone_piecewise_curve(rng, "piecewise_turn_not_one_to_one"),
        _random_parabola_up(rng, "offset_parabola_not_one_to_one"),
    ]


def _interval_key(interval: Sequence[float]) -> Tuple[float, float]:
    return (round(float(interval[0]), 4), round(float(interval[1]), 4))


def _sample_domain_range_bank(rng) -> Tuple[_RelationSpec, ...]:
    samplers = (
        lambda: _random_slanted_line(rng, "domain_range_line", positive_slope=None),
        lambda: _random_horizontal_line(rng, "domain_range_horizontal_line"),
        lambda: rng.choice(
            (
                lambda: _random_v_shape(rng, "domain_range_v_shape"),
                lambda: _random_parabola_up(rng, "domain_range_u_shape"),
                lambda: _random_sinusoidal_curve(rng, "domain_range_sinusoidal"),
            )
        )(),
        lambda: rng.choice(
            (
                lambda: _random_exponential_curve(rng, "domain_range_exponential"),
                lambda: _random_logarithmic_curve(rng, "domain_range_logarithmic"),
            )
        )(),
        lambda: _random_sideways_v(rng, "domain_range_sideways_v"),
        lambda: rng.choice(
            (
                lambda: _random_ellipse(rng, "domain_range_ellipse"),
                lambda: _random_ellipse(rng, "domain_range_circle", circle=True),
                lambda: _random_sideways_parabola(rng, "domain_range_sideways_parabola"),
            )
        )(),
    )
    for _ in range(200):
        bank = tuple(sampler() for sampler in samplers)
        domains = [_interval_key(relation.domain) for relation in bank]
        ranges = [_interval_key(relation.range) for relation in bank]
        if len(set(domains)) == len(domains) and len(set(ranges)) == len(ranges):
            return bank
    raise RuntimeError("failed to sample domain/range bank with unique intervals")


def _interval_monotone_relation(
    rng,
    relation_id: str,
    *,
    interval: Tuple[float, float],
    increasing: bool,
) -> _RelationSpec:
    """Build a strictly monotone polyline over the target interval."""

    x0, x3 = float(interval[0]), float(interval[1])
    x1 = float(x0 + ((x3 - x0) / 3.0))
    x2 = float(x0 + (2.0 * (x3 - x0) / 3.0))
    if bool(increasing):
        y0 = float(rng.choice((-4, -3)))
        y3 = float(rng.choice((3, 4)))
        y1 = float(rng.choice((-2, -1)))
        y2 = float(rng.choice((1, 2)))
    else:
        y0 = float(rng.choice((3, 4)))
        y3 = float(rng.choice((-4, -3)))
        y1 = float(rng.choice((1, 2)))
        y2 = float(rng.choice((-2, -1)))
    return _polyline(
        str(relation_id),
        ((x0, y0), (x1, y1), (x2, y2), (x3, y3)),
        is_function=True,
        is_one_to_one=True,
    )


def _interval_horizontal_relation(rng, relation_id: str, *, interval: Tuple[float, float]) -> _RelationSpec:
    y = float(rng.choice((-3, -2, 2, 3)))
    return _polyline(
        str(relation_id),
        ((float(interval[0]), y), (float(interval[1]), y)),
        is_function=True,
        is_one_to_one=False,
    )


def _interval_v_relation(rng, relation_id: str, *, interval: Tuple[float, float], inverted: bool) -> _RelationSpec:
    x0, x2 = float(interval[0]), float(interval[1])
    x1 = float(0.5 * (x0 + x2))
    if bool(inverted):
        y0 = float(rng.choice((-3, -2)))
        y1 = float(rng.choice((3, 4)))
        y2 = float(rng.choice((-4, -3)))
    else:
        y0 = float(rng.choice((3, 4)))
        y1 = float(rng.choice((-4, -3)))
        y2 = float(rng.choice((2, 3)))
    return _polyline(
        str(relation_id),
        ((x0, y0), (x1, y1), (x2, y2)),
        is_function=True,
        is_one_to_one=False,
    )


def _interval_mixed_relation(rng, relation_id: str, *, interval: Tuple[float, float]) -> _RelationSpec:
    x0, x4 = float(interval[0]), float(interval[1])
    step = float((x4 - x0) / 4.0)
    y_values = list(rng.choice(((-2, 3, -1, 2, -3), (2, -3, 1, -2, 3))))
    return _polyline(
        str(relation_id),
        tuple((float(x0 + (step * index)), float(y_values[index])) for index in range(5)),
        is_function=True,
        is_one_to_one=False,
    )


def _local_monotonic_relation(
    rng,
    relation_id: str,
    *,
    increasing: bool,
    matches_target: bool,
) -> _RelationSpec:
    """Build a full-window graph whose monotonicity is judged only on [-2, 2]."""

    x_values = (-4.0, -2.0, 0.0, 2.0, 4.0)
    if bool(matches_target):
        if bool(increasing):
            core = list(rng.choice(((-2.6, -0.6, 1.8), (-1.8, 0.2, 2.6), (-3.0, -1.0, 1.0))))
        else:
            core = list(rng.choice(((2.6, 0.6, -1.8), (1.8, -0.2, -2.6), (3.0, 1.0, -1.0))))
    else:
        if bool(increasing):
            patterns = (
                (-1.4, -1.4, 1.8),
                (-2.2, 1.6, 0.6),
                (1.2, -1.6, 2.4),
                (-0.4, 1.4, 1.2),
                (2.4, 0.6, -1.6),
            )
        else:
            patterns = (
                (1.4, 1.4, -1.8),
                (2.2, -1.6, -0.6),
                (-1.2, 1.6, -2.4),
                (0.4, -1.4, -1.2),
                (-2.4, -0.6, 1.6),
            )
        core = list(rng.choice(patterns))
    left_candidates = [float(value) for value in (-3.5, -2.5, -1.5, 1.5, 2.5, 3.5) if abs(float(value) - float(core[0])) >= 0.6]
    right_candidates = [float(value) for value in (-3.5, -2.5, -1.5, 1.5, 2.5, 3.5) if abs(float(value) - float(core[2])) >= 0.6]
    y_values = (
        float(rng.choice(left_candidates)),
        float(core[0]),
        float(core[1]),
        float(core[2]),
        float(rng.choice(right_candidates)),
    )
    return _polyline(
        str(relation_id),
        tuple((float(x_values[index]), float(y_values[index])) for index in range(len(x_values))),
        is_function=True,
        is_one_to_one=False,
    )


def _sample_monotonic_interval_bank(
    rng,
    *,
    query_id: str,
    target_interval: Tuple[float, float],
) -> Tuple[_RelationSpec, List[_RelationSpec]]:
    """Sample one winner and five nonmatching monotonic-interval distractors."""

    target_increasing = str(query_id) == MONOTONIC_INTERVAL_INCREASING_LABEL
    winner = _local_monotonic_relation(
        rng,
        "target_local_monotone_relation",
        increasing=bool(target_increasing),
        matches_target=True,
    )
    distractors = [
        _local_monotonic_relation(rng, "opposite_local_monotone_relation", increasing=not bool(target_increasing), matches_target=True),
        _local_monotonic_relation(rng, "local_flat_or_turn_relation_a", increasing=bool(target_increasing), matches_target=False),
        _local_monotonic_relation(rng, "local_flat_or_turn_relation_b", increasing=bool(target_increasing), matches_target=False),
        _local_monotonic_relation(rng, "local_flat_or_turn_relation_c", increasing=bool(target_increasing), matches_target=False),
        _local_monotonic_relation(rng, "local_flat_or_turn_relation_d", increasing=bool(target_increasing), matches_target=False),
    ]
    rng.shuffle(distractors)
    return winner, distractors


def _interval_sign_relation(
    rng,
    relation_id: str,
    *,
    interval: Tuple[float, float],
    positive: bool,
) -> _RelationSpec:
    """Build a function that stays strictly above or below the x-axis."""

    x0, x3 = float(interval[0]), float(interval[1])
    x1 = float(x0 + ((x3 - x0) / 3.0))
    x2 = float(x0 + (2.0 * (x3 - x0) / 3.0))
    if bool(positive):
        candidates = (1.2, 2.0, 2.8, 3.6)
    else:
        candidates = (-1.2, -2.0, -2.8, -3.6)
    values = [float(value) for value in rng.sample(list(candidates), 4)]
    return _polyline(
        str(relation_id),
        ((x0, values[0]), (x1, values[1]), (x2, values[2]), (x3, values[3])),
        is_function=True,
        is_one_to_one=False,
    )


def _interval_crossing_relation(
    rng,
    relation_id: str,
    *,
    interval: Tuple[float, float],
    start_positive: bool,
) -> _RelationSpec:
    """Build a function that changes sign over the target interval."""

    x0, x3 = float(interval[0]), float(interval[1])
    x1 = float(x0 + ((x3 - x0) / 3.0))
    x2 = float(x0 + (2.0 * (x3 - x0) / 3.0))
    if bool(start_positive):
        y_values = (3.0, 1.0, -1.0, -3.0)
    else:
        y_values = (-3.0, -1.0, 1.0, 3.0)
    if bool(rng.choice((False, True))):
        y_values = (y_values[0], y_values[2], y_values[1], y_values[3])
    return _polyline(
        str(relation_id),
        ((x0, y_values[0]), (x1, y_values[1]), (x2, y_values[2]), (x3, y_values[3])),
        is_function=True,
        is_one_to_one=False,
    )


def _sample_sign_interval_bank(
    rng,
    *,
    query_id: str,
    target_interval: Tuple[float, float],
) -> Tuple[_RelationSpec, List[_RelationSpec]]:
    """Sample one winner and five nonmatching sign-interval distractors."""

    target_positive = str(query_id) == SIGN_INTERVAL_POSITIVE_LABEL
    winner = _interval_sign_relation(
        rng,
        "target_interval_sign_relation",
        interval=target_interval,
        positive=bool(target_positive),
    )
    distractors = [
        _interval_sign_relation(
            rng,
            "opposite_interval_sign_relation_a",
            interval=target_interval,
            positive=not bool(target_positive),
        ),
        _interval_sign_relation(
            rng,
            "opposite_interval_sign_relation_b",
            interval=target_interval,
            positive=not bool(target_positive),
        ),
        _interval_crossing_relation(rng, "interval_crossing_relation_a", interval=target_interval, start_positive=True),
        _interval_crossing_relation(rng, "interval_crossing_relation_b", interval=target_interval, start_positive=False),
        _interval_mixed_relation(rng, "interval_mixed_sign_relation", interval=target_interval),
    ]
    rng.shuffle(distractors)
    return winner, distractors


def _template_index(params: Mapping[str, Any], *, instance_seed: int, query_id: str, support_size: int) -> int:
    selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.relation_template.{query_id}",
    )
    return int(selection_index) % max(1, int(support_size))


def _shuffled_without_winner(
    relations: Sequence[_RelationSpec],
    *,
    winner: _RelationSpec,
    rng,
) -> List[_RelationSpec]:
    distractors = [relation for relation in relations if str(relation.relation_id) != str(winner.relation_id)]
    rng.shuffle(distractors)
    return distractors


def _build_relations(query: _ResolvedQuery, *, instance_seed: int, params: Mapping[str, Any]) -> Dict[str, _RelationSpec]:
    query_id = str(query.query_id)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.relations.{query_id}")
    for _ in range(100):
        relations_by_label: Dict[str, _RelationSpec] = {}
        if query_id == "function_status_label":
            winner = _sample_function_winner(
                rng,
                _template_index(params, instance_seed=int(instance_seed), query_id=query_id, support_size=7),
            )
            distractors = _sample_function_distractors(rng)
            rng.shuffle(distractors)
        elif query_id == "one_to_one_status_label":
            winner = _sample_one_to_one_winner(
                rng,
                _template_index(params, instance_seed=int(instance_seed), query_id=query_id, support_size=6),
            )
            distractors = _sample_one_to_one_distractors(rng)
            rng.shuffle(distractors)
        elif query_id in {"y_axis_symmetry_label", "x_axis_symmetry_label", "origin_symmetry_label"}:
            winner = _sample_symmetry_winner(
                rng,
                query_id,
                _template_index(params, instance_seed=int(instance_seed), query_id=query_id, support_size=3),
            )
            distractors = _sample_symmetry_distractors(rng, query_id)
        elif query_id in {"domain_match_label", "range_match_label"}:
            bank = _sample_domain_range_bank(rng)
            winner = bank[_template_index(params, instance_seed=int(instance_seed), query_id=query_id, support_size=len(bank))]
            distractors = _shuffled_without_winner(bank, winner=winner, rng=rng)
        elif query_id in set(MONOTONIC_INTERVAL_VARIANTS):
            target_interval = query.target_interval
            if target_interval is None:
                raise ValueError(f"{query_id} requires target_interval")
            winner, distractors = _sample_monotonic_interval_bank(
                rng,
                query_id=query_id,
                target_interval=target_interval,
            )
        elif query_id in set(SIGN_INTERVAL_VARIANTS):
            target_interval = query.target_interval
            if target_interval is None:
                raise ValueError(f"{query_id} requires target_interval")
            winner, distractors = _sample_sign_interval_bank(
                rng,
                query_id=query_id,
                target_interval=target_interval,
            )
        else:
            raise ValueError(f"unsupported query_id: {query_id}")

        distractor_iter = iter(distractors)
        for label in query.label_pool:
            if str(label) == str(query.winner_label):
                relations_by_label[str(label)] = winner
            else:
                relations_by_label[str(label)] = next(distractor_iter)
        try:
            _validate_unique_answer(query, relations_by_label)
        except RuntimeError:
            continue
        return relations_by_label
    raise RuntimeError(f"failed to sample unique function-property answer for {query_id}")


def _symmetry_axis_for_variant(query_id: str) -> str:
    if str(query_id) == "y_axis_symmetry_label":
        return "y_axis"
    if str(query_id) == "x_axis_symmetry_label":
        return "x_axis"
    if str(query_id) == "origin_symmetry_label":
        return "origin"
    raise ValueError(f"unsupported symmetry query_id: {query_id}")


def _points_over_interval(relation: _RelationSpec, interval: Tuple[float, float]) -> List[Point]:
    """Return relation sample points within a closed x-interval."""

    x0, x1 = float(interval[0]), float(interval[1])
    lo, hi = min(x0, x1), max(x0, x1)
    if float(relation.domain[0]) > lo + 1e-6 or float(relation.domain[1]) < hi - 1e-6:
        return []
    points = [
        (float(x), float(y))
        for x, y in _relation_points(relation)
        if lo - 1e-6 <= float(x) <= hi + 1e-6
    ]
    return sorted(points, key=lambda point: (float(point[0]), float(point[1])))


def _is_increasing_on_interval(relation: _RelationSpec, interval: Tuple[float, float]) -> bool:
    points = _points_over_interval(relation, interval)
    if len(points) < 2 or not bool(relation.is_function):
        return False
    return all(float(points[index + 1][1]) > float(points[index][1]) + 1e-6 for index in range(len(points) - 1))


def _is_decreasing_on_interval(relation: _RelationSpec, interval: Tuple[float, float]) -> bool:
    points = _points_over_interval(relation, interval)
    if len(points) < 2 or not bool(relation.is_function):
        return False
    return all(float(points[index + 1][1]) < float(points[index][1]) - 1e-6 for index in range(len(points) - 1))


def _is_positive_on_interval(relation: _RelationSpec, interval: Tuple[float, float]) -> bool:
    points = _points_over_interval(relation, interval)
    if len(points) < 2 or not bool(relation.is_function):
        return False
    return all(float(point[1]) > 1e-6 for point in points)


def _is_negative_on_interval(relation: _RelationSpec, interval: Tuple[float, float]) -> bool:
    points = _points_over_interval(relation, interval)
    if len(points) < 2 or not bool(relation.is_function):
        return False
    return all(float(point[1]) < -1e-6 for point in points)


def _validate_unique_answer(query: _ResolvedQuery, relations_by_label: Mapping[str, _RelationSpec]) -> None:
    query_id = str(query.query_id)
    if query_id == "function_status_label":
        matches = [label for label, relation in relations_by_label.items() if bool(relation.is_function)]
    elif query_id == "one_to_one_status_label":
        matches = [label for label, relation in relations_by_label.items() if bool(relation.is_function and relation.is_one_to_one)]
    elif query_id in {"y_axis_symmetry_label", "x_axis_symmetry_label", "origin_symmetry_label"}:
        axis = _symmetry_axis_for_variant(query_id)
        matches = [label for label, relation in relations_by_label.items() if str(axis) in set(relation.symmetry_axes)]
    elif query_id == "domain_match_label":
        target = relations_by_label[str(query.winner_label)].domain
        matches = [label for label, relation in relations_by_label.items() if tuple(relation.domain) == tuple(target)]
    elif query_id == "range_match_label":
        target = relations_by_label[str(query.winner_label)].range
        matches = [label for label, relation in relations_by_label.items() if tuple(relation.range) == tuple(target)]
    elif query_id == MONOTONIC_INTERVAL_INCREASING_LABEL:
        if query.target_interval is None:
            raise ValueError(f"{query_id} requires target_interval")
        matches = [label for label, relation in relations_by_label.items() if _is_increasing_on_interval(relation, query.target_interval)]
    elif query_id == MONOTONIC_INTERVAL_DECREASING_LABEL:
        if query.target_interval is None:
            raise ValueError(f"{query_id} requires target_interval")
        matches = [label for label, relation in relations_by_label.items() if _is_decreasing_on_interval(relation, query.target_interval)]
    elif query_id == SIGN_INTERVAL_POSITIVE_LABEL:
        if query.target_interval is None:
            raise ValueError(f"{query_id} requires target_interval")
        matches = [label for label, relation in relations_by_label.items() if _is_positive_on_interval(relation, query.target_interval)]
    elif query_id == SIGN_INTERVAL_NEGATIVE_LABEL:
        if query.target_interval is None:
            raise ValueError(f"{query_id} requires target_interval")
        matches = [label for label, relation in relations_by_label.items() if _is_negative_on_interval(relation, query.target_interval)]
    else:
        raise ValueError(f"unsupported query_id: {query_id}")
    if matches != [str(query.winner_label)]:
        raise RuntimeError(f"function_property_label answer is not unique: {matches}")


def _relation_points(relation: _RelationSpec) -> List[Point]:
    if relation.points:
        return list(relation.points)
    if relation.draw_kind == "parabola_up":
        if relation.x_range is None or relation.vertex is None:
            raise ValueError("parabola relation missing x_range or vertex")
        vx, vy = relation.vertex
        return [
            (x, float(relation.coefficient) * ((x - float(vx)) ** 2) + float(vy))
            for x in linspace(float(relation.x_range[0]), float(relation.x_range[1]), 80)
        ]
    if relation.draw_kind == "sideways_parabola":
        if relation.y_range is None or relation.vertex is None:
            raise ValueError("sideways parabola relation missing y_range or vertex")
        vx, vy = relation.vertex
        return [
            (float(relation.coefficient) * ((y - float(vy)) ** 2) + float(vx), y)
            for y in linspace(float(relation.y_range[0]), float(relation.y_range[1]), 80)
        ]
    return []


def _draw_relation(
    draw: ImageDraw.ImageDraw,
    relation: _RelationSpec,
    *,
    plot_bbox: BBox,
    color: Tuple[int, int, int],
    line_width: int,
) -> None:
    if relation.draw_kind == "ellipse":
        if relation.center is None or relation.radii is None:
            raise ValueError("ellipse relation missing center or radii")
        cx, cy = relation.center
        rx, ry = relation.radii
        top_left = graph_point_to_panel_pixel(
            (float(cx) - float(rx), float(cy) + float(ry)),
            plot_bbox=plot_bbox,
            config=_PANEL_CONFIG,
        )
        bottom_right = graph_point_to_panel_pixel(
            (float(cx) + float(rx), float(cy) - float(ry)),
            plot_bbox=plot_bbox,
            config=_PANEL_CONFIG,
        )
        draw.ellipse((top_left[0], top_left[1], bottom_right[0], bottom_right[1]), outline=color, width=int(line_width))
        return

    graph_points = _relation_points(relation)
    pixel_points = [
        graph_point_to_panel_pixel(point, plot_bbox=plot_bbox, config=_PANEL_CONFIG)
        for point in graph_points
    ]
    if len(pixel_points) >= 2:
        draw.line(pixel_points, fill=color, width=int(line_width), joint="curve")
        draw_endpoint(draw, pixel_points[0], color=color, radius=max(3, int(line_width)))
        draw_endpoint(draw, pixel_points[-1], color=color, radius=max(3, int(line_width)))


def _render_scene(query: _ResolvedQuery, *, instance_seed: int, params: Mapping[str, Any]) -> _RenderedScene:
    canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 1024)))
    canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 720)))
    line_width = int(params.get("line_width", group_default(_RENDER_DEFAULTS, "line_width", 4)))
    canvas_width = max(720, int(canvas_width))
    canvas_height = max(520, int(canvas_height))
    line_width = max(2, int(line_width))

    line_colors, line_color_meta = _resolve_line_colors(params, instance_seed=int(instance_seed))
    image, background_meta, diagram_style, diagram_style_meta = prepare_geometry_diagram_style_and_background(
        scene_id="function_panels",
        task_group="analytical",
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        protected_colors=line_colors,
    )
    draw = ImageDraw.Draw(image)
    relations_by_label = _build_relations(query, instance_seed=int(instance_seed), params=params)
    panel_style, panel_style_meta = _resolve_panel_style(
        params,
        instance_seed=int(instance_seed),
        diagram_style=diagram_style,
    )
    layout = coordinate_panel_layout(int(canvas_width), int(canvas_height), config=_PANEL_CONFIG)
    panel_bboxes: Dict[str, List[int]] = {}
    plot_bboxes: Dict[str, List[int]] = {}

    for index, label in enumerate(query.label_pool):
        panel_bbox = panel_bbox_for_index(layout, int(index), config=_PANEL_CONFIG)
        plot_bbox = plot_bbox_for_panel(panel_bbox)
        panel_bboxes[str(label)] = [int(value) for value in panel_bbox]
        plot_bboxes[str(label)] = [int(value) for value in plot_bbox]
        draw_coordinate_panel_grid(
            draw,
            panel_bbox=panel_bbox,
            plot_bbox=plot_bbox,
            label=str(label),
            config=_PANEL_CONFIG,
            style=panel_style,
        )
        color = line_colors[int(index) % len(line_colors)]
        _draw_relation(
            draw,
            relations_by_label[str(label)],
            plot_bbox=plot_bbox,
            color=color,
            line_width=int(line_width),
        )

    image, post_noise_meta = apply_post_image_noise(
        image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=_POST_IMAGE_NOISE_DEFAULTS,
    )
    winner_relation = relations_by_label[str(query.winner_label)]
    return _RenderedScene(
        image=image,
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
        diagram_style_meta=dict(diagram_style_meta),
        panel_style_meta=dict(panel_style_meta),
        line_color_meta=dict(line_color_meta),
        line_colors=tuple(line_colors),
        relations_by_label=dict(relations_by_label),
        panel_bboxes=dict(panel_bboxes),
        plot_bboxes=dict(plot_bboxes),
        target_domain=_format_interval(winner_relation.domain),
        target_range=_format_interval(winner_relation.range),
        target_interval="" if query.target_interval is None else _format_interval(query.target_interval),
    )


def _relation_trace_payload(relation: _RelationSpec) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "relation_id": str(relation.relation_id),
        "draw_kind": str(relation.draw_kind),
        "domain": [float(relation.domain[0]), float(relation.domain[1])],
        "range": [float(relation.range[0]), float(relation.range[1])],
        "domain_text": _format_interval(relation.domain),
        "range_text": _format_interval(relation.range),
        "is_function": bool(relation.is_function),
        "is_one_to_one": bool(relation.is_one_to_one),
        "symmetry_axes": [str(axis) for axis in relation.symmetry_axes],
        "symmetric_about_x_axis": "x_axis" in set(relation.symmetry_axes),
        "symmetric_about_y_axis": "y_axis" in set(relation.symmetry_axes),
        "symmetric_about_origin": "origin" in set(relation.symmetry_axes),
    }
    if relation.points:
        payload["points"] = [[float(x), float(y)] for x, y in relation.points]
    if relation.center is not None:
        payload["center"] = [float(relation.center[0]), float(relation.center[1])]
    if relation.radii is not None:
        payload["radii"] = [float(relation.radii[0]), float(relation.radii[1])]
    if relation.x_range is not None:
        payload["x_range"] = [float(relation.x_range[0]), float(relation.x_range[1])]
    if relation.y_range is not None:
        payload["y_range"] = [float(relation.y_range[0]), float(relation.y_range[1])]
    if relation.vertex is not None:
        payload["vertex"] = [float(relation.vertex[0]), float(relation.vertex[1])]
    if relation.draw_kind in {"parabola_up", "sideways_parabola"}:
        payload["coefficient"] = float(relation.coefficient)
    return payload


def _build_complexity(query_id: str) -> Any:
    weights = resolve_geometry_complexity_weights(
        _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        task_id=TASK_ID,
    )
    reasoning = {
        "function_status_label": 0.46,
        "one_to_one_status_label": 0.62,
        "domain_match_label": 0.54,
        "range_match_label": 0.58,
        "y_axis_symmetry_label": 0.60,
        "x_axis_symmetry_label": 0.62,
        "origin_symmetry_label": 0.68,
        MONOTONIC_INTERVAL_INCREASING_LABEL: 0.58,
        MONOTONIC_INTERVAL_DECREASING_LABEL: 0.60,
        SIGN_INTERVAL_POSITIVE_LABEL: 0.54,
        SIGN_INTERVAL_NEGATIVE_LABEL: 0.56,
    }[str(query_id)]
    ambiguity = {
        "function_status_label": 0.36,
        "one_to_one_status_label": 0.52,
        "domain_match_label": 0.46,
        "range_match_label": 0.50,
        "y_axis_symmetry_label": 0.50,
        "x_axis_symmetry_label": 0.54,
        "origin_symmetry_label": 0.60,
        MONOTONIC_INTERVAL_INCREASING_LABEL: 0.46,
        MONOTONIC_INTERVAL_DECREASING_LABEL: 0.48,
        SIGN_INTERVAL_POSITIVE_LABEL: 0.42,
        SIGN_INTERVAL_NEGATIVE_LABEL: 0.44,
    }[str(query_id)]
    return build_geometry_task_complexity(
        weights=weights,
        components={
            "visual_scan": 0.82,
            "analytical_reasoning": clamp_unit_interval(float(reasoning)),
            "ambiguity": clamp_unit_interval(float(ambiguity)),
            "output_burden": 0.22,
        },
    )


class GeometryAnalyticalFunctionPropertyLabelTask:
    """Select the labeled relation matching one function-property query."""

    task_id = TASK_ID
    domain = "geometry"
    task_group = "analytical"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query = _resolve_query(int(instance_seed), params=params)
        rendered_scene = _render_scene(query, instance_seed=int(instance_seed), params=params)

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "evidence_hint_selected_panel_bbox",
                "answer_hint_option_letter",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        evidence_value = [list(rendered_scene.panel_bboxes[str(query.winner_label)])]
        json_example, json_example_answer_only = resolve_prompt_json_examples(
            _PROMPT_DEFAULTS,
            evidence_value=evidence_value,
            answer_type="option_letter",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "target_domain": str(rendered_scene.target_domain),
                "target_range": str(rendered_scene.target_range),
                "target_interval": str(rendered_scene.target_interval),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint_selected_panel_bbox"]),
                "answer_hint": str(prompt_defaults["answer_hint_option_letter"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="option_letter", value=str(query.winner_label))
        evidence_gt = TypedValue(type="bbox_set", value=evidence_value)
        winner_relation = rendered_scene.relations_by_label[str(query.winner_label)]
        relations_trace = {
            str(label): _relation_trace_payload(rendered_scene.relations_by_label[str(label)])
            for label in query.label_pool
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_analytical_function_property_grid",
                "entities": [
                    {
                        "label": str(label),
                        "panel_bbox": list(rendered_scene.panel_bboxes[str(label)]),
                        "plot_bbox": list(rendered_scene.plot_bboxes[str(label)]),
                        "relation": dict(relations_trace[str(label)]),
                    }
                    for label in query.label_pool
                ],
                "relations": {
                    "query_id": str(query.query_id),
                    "winner_label": str(query.winner_label),
                    "target_domain": str(rendered_scene.target_domain),
                    "target_range": str(rendered_scene.target_range),
                    "target_interval": str(rendered_scene.target_interval),
                },
            },
            "query_spec": {
                "query_id": str(query.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query.query_id),
                    "query_id_probabilities": dict(query.query_id_probabilities),
                    "winner_label": str(query.winner_label),
                    "winner_label_probabilities": dict(query.winner_label_probabilities),
                    "candidate_label_pool": list(query.label_pool),
                    "target_domain": str(rendered_scene.target_domain),
                    "target_range": str(rendered_scene.target_range),
                    "target_interval": str(rendered_scene.target_interval),
                },
            },
            "render_spec": {
                "canvas_width": int(rendered_scene.image.size[0]),
                "canvas_height": int(rendered_scene.image.size[1]),
                "coord_space": "pixel",
                "technical_diagram_style": dict(rendered_scene.diagram_style_meta),
                "background_style": dict(rendered_scene.background_meta),
                "post_image_noise": dict(rendered_scene.post_noise_meta),
                "panel_style": dict(rendered_scene.panel_style_meta),
                "line_colors": [list(color) for color in rendered_scene.line_colors],
                "line_color_selection": dict(rendered_scene.line_color_meta),
                "panel_count": int(_PANEL_COUNT),
                "panel_columns": int(_PANEL_COLUMNS),
                "panel_rows": int(_PANEL_ROWS),
                "graph_unit_bounds": {"x": [int(_GRID_MIN), int(_GRID_MAX)], "y": [int(_GRID_MIN), int(_GRID_MAX)]},
            },
            "render_map": {
                "panel_bboxes": dict(rendered_scene.panel_bboxes),
                "plot_bboxes": dict(rendered_scene.plot_bboxes),
                "technical_diagram_frame_mode": str(rendered_scene.diagram_style_meta.get("frame_mode", "none")),
                "coord_space": "pixel",
            },
            "execution_trace": {
                "query_id": str(query.query_id),
                "answer_type": "option_letter",
                "answer_value": str(query.winner_label),
                "winner_label": str(query.winner_label),
                "winner_relation": dict(_relation_trace_payload(winner_relation)),
                "relations_by_label": dict(relations_trace),
                "query_id_probabilities": dict(query.query_id_probabilities),
                "winner_label_probabilities": dict(query.winner_label_probabilities),
                "target_interval": str(rendered_scene.target_interval),
            },
            "witness_symbolic": {
                "type": "function_property_panel_selection",
                "query_id": str(query.query_id),
                "answer_label": str(query.winner_label),
                "target_domain": str(rendered_scene.target_domain),
                "target_range": str(rendered_scene.target_range),
                "target_interval": str(rendered_scene.target_interval),
                "relations_by_label": dict(relations_trace),
            },
            "projected_evidence": {
                "type": "bbox_set",
                "bbox_set": list(evidence_value),
                "panel_bbox_by_label": dict(rendered_scene.panel_bboxes),
                "plot_bbox_by_label": dict(rendered_scene.plot_bboxes),
            },
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=rendered_scene.image,
            image_id="img_0",
            trace_payload=trace_payload,
            complexity=_build_complexity(str(query.query_id)),
            task_versions=default_task_versions(),
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class GeometryAnalyticalRelationPropertyLabelTask(
    MultiFixedGeometryQueryTaskMixin,
    GeometryAnalyticalFunctionPropertyLabelTask,
):
    """Choose the panel matching one requested coordinate-relation property."""

    task_id = "task_geometry__function_panels__relation_property_label"
    fixed_query_ids = SUPPORTED_QUERY_IDS
    public_scene_id = "function_panels"
