"""Analytical intersection-property label task with sampled mini coordinate panels."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.sampling import normalize_positive_weights, weighted_choice
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
    panel_bbox_for_index,
    plot_bbox_for_panel,
)
from ..shared.background_defaults import load_geometry_background_defaults
from ..shared.fixed_query_task import MultiFixedGeometryQueryTaskMixin
from ..shared.noise_defaults import load_geometry_noise_defaults
from ..shared.option_count import panel_grid_shape_for_option_count, resolve_geometry_option_count

Point = Tuple[float, float]
LineSegment = Tuple[Point, Point]
CircleSpec = Tuple[Point, float]
BBox = Tuple[int, int, int, int]

TASK_ID = "geometry_analytical_intersection_property_label_base"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "line_circle_tangent_label",
    "line_circle_two_intersections_label",
    "circle_circle_two_intersections_label",
)
DEFAULT_LABEL_POOL: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G", "H", "I")

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "analytical")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_POST_IMAGE_NOISE_DEFAULTS = load_geometry_noise_defaults(task_group="analytical")
_BACKGROUND_DEFAULTS = load_geometry_background_defaults(task_group="analytical")
_GRID_MIN = -5
_GRID_MAX = 5
_MAX_PANEL_COUNT = 9
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
_OBJECT_COLOR_PALETTES: Tuple[Tuple[Color, Color], ...] = (
    ((27, 96, 168), (196, 82, 42)),
    ((32, 126, 88), (147, 74, 165)),
    ((8, 119, 153), (205, 73, 89)),
    ((83, 87, 176), (184, 126, 26)),
    ((29, 131, 130), (178, 62, 123)),
    ((92, 104, 38), (185, 78, 45)),
    ((24, 105, 164), (183, 91, 42)),
    ((22, 129, 114), (117, 80, 178)),
    ((68, 112, 132), (176, 66, 104)),
)
_INTERSECTION_COLORS: Tuple[Color, ...] = (
    (36, 42, 52),
    (54, 58, 68),
    (45, 67, 63),
)


@dataclass(frozen=True)
class _PanelSpec:
    """One rendered object pair and its symbolic intersection properties."""

    pair_id: str
    pair_kind: str
    relation_class: str
    line_segments: Tuple[LineSegment, ...]
    circles: Tuple[CircleSpec, ...]
    intersection_points: Tuple[Point, ...]
    intersection_quadrants: Tuple[str, ...]


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved task axes for one generated instance."""

    query_id: str
    query_id_probabilities: Dict[str, float]
    winner_label: str
    winner_label_probabilities: Dict[str, float]
    label_pool: Tuple[str, ...]
    panel_count_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered image plus traceable panel metadata."""

    image: Image.Image
    background_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]
    panel_style_meta: Dict[str, Any]
    panels_by_label: Dict[str, _PanelSpec]
    panel_bboxes: Dict[str, List[int]]
    plot_bboxes: Dict[str, List[int]]
    intersection_point_bboxes: Dict[str, List[List[int]]]
    panel_columns: int
    panel_rows: int
    panel_count_probabilities: Dict[str, float]
    target_quadrant: str
    object_color_meta: Dict[str, Any]
    object_colors: Tuple[Color, ...]
    intersection_color_meta: Dict[str, Any]
    intersection_color: Color


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
    if len(label_pool) not in {4, 6, 9} or len(set(label_pool)) != len(label_pool):
        raise ValueError("intersection_property_label requires four, six, or nine unique candidate labels")
    return label_pool


def _visible_panel_labels(label_pool: Sequence[str], *, winner_label: str, panel_count: int) -> Tuple[str, ...]:
    labels = tuple(str(label) for label in label_pool[: int(panel_count)])
    if str(winner_label) in set(labels):
        return labels
    return tuple([str(winner_label), *[label for label in labels if str(label) != str(winner_label)]])[: int(panel_count)]


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


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
    label_pool = _resolve_label_pool(params)
    supported_counts = tuple(count for count in (4, 6, 9) if int(count) <= len(label_pool))
    panel_count, panel_count_probabilities = resolve_geometry_option_count(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        field_name="panel_count",
        supported_counts=supported_counts,
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
    )
    winner_label, winner_label_probabilities = _resolve_winner_label(
        params,
        instance_seed=int(instance_seed),
        query_id=str(query_id),
        label_pool=label_pool,
    )
    visible_labels = _visible_panel_labels(label_pool, winner_label=str(winner_label), panel_count=int(panel_count))
    return _ResolvedQuery(
        query_id=str(query_id),
        query_id_probabilities=dict(query_id_probabilities),
        winner_label=str(winner_label),
        winner_label_probabilities=dict(winner_label_probabilities),
        label_pool=tuple(visible_labels),
        panel_count_probabilities=dict(panel_count_probabilities),
    )


def _quadrant(point: Point) -> str:
    x, y = float(point[0]), float(point[1])
    if x > 0 and y > 0:
        return "I"
    if x < 0 and y > 0:
        return "II"
    if x < 0 and y < 0:
        return "III"
    if x > 0 and y < 0:
        return "IV"
    return "axis"


def _intersection_quadrants(points: Sequence[Point]) -> Tuple[str, ...]:
    quadrants: List[str] = []
    for point in points:
        value = _quadrant(point)
        if value != "axis" and value not in quadrants:
            quadrants.append(str(value))
    return tuple(quadrants)


def _line_circle_intersections(center: Point, radius: float, line_y: float) -> Tuple[Point, ...]:
    cx, cy = float(center[0]), float(center[1])
    offset = float(line_y) - float(cy)
    radicand = (float(radius) ** 2) - (float(offset) ** 2)
    if radicand < -1e-7:
        return ()
    if abs(radicand) <= 1e-7:
        return ((cx, float(line_y)),)
    delta = math.sqrt(max(0.0, float(radicand)))
    return ((cx - delta, float(line_y)), (cx + delta, float(line_y)))


def _circle_circle_intersections(circle_a: CircleSpec, circle_b: CircleSpec) -> Tuple[Point, ...]:
    (x0, y0), r0 = circle_a
    (x1, y1), r1 = circle_b
    dx = float(x1) - float(x0)
    dy = float(y1) - float(y0)
    d = math.hypot(dx, dy)
    if d <= 1e-9:
        return ()
    if d > float(r0) + float(r1) + 1e-7:
        return ()
    if d < abs(float(r0) - float(r1)) - 1e-7:
        return ()
    a = ((float(r0) ** 2) - (float(r1) ** 2) + (d**2)) / (2.0 * d)
    h2 = (float(r0) ** 2) - (a**2)
    xm = float(x0) + (a * dx / d)
    ym = float(y0) + (a * dy / d)
    if abs(h2) <= 1e-7:
        return ((xm, ym),)
    if h2 < 0.0:
        return ()
    h = math.sqrt(h2)
    rx = -dy * (h / d)
    ry = dx * (h / d)
    return ((xm + rx, ym + ry), (xm - rx, ym - ry))


def _line_circle_panel(pair_id: str, *, center: Point, radius: float, line_y: float, relation_class: str) -> _PanelSpec:
    line_left = max(float(_GRID_MIN) + 0.5, float(center[0]) - float(radius) - 1.7)
    line_right = min(float(_GRID_MAX) - 0.5, float(center[0]) + float(radius) + 1.7)
    intersections = _line_circle_intersections(center, float(radius), float(line_y))
    return _PanelSpec(
        pair_id=str(pair_id),
        pair_kind="line_circle",
        relation_class=str(relation_class),
        line_segments=(((line_left, float(line_y)), (line_right, float(line_y))),),
        circles=((center, float(radius)),),
        intersection_points=tuple(intersections),
        intersection_quadrants=_intersection_quadrants(intersections),
    )


def _circle_circle_panel(
    pair_id: str,
    *,
    circle_a: CircleSpec,
    circle_b: CircleSpec,
    relation_class: str,
) -> _PanelSpec:
    intersections = _circle_circle_intersections(circle_a, circle_b)
    return _PanelSpec(
        pair_id=str(pair_id),
        pair_kind="circle_circle",
        relation_class=str(relation_class),
        line_segments=(),
        circles=(circle_a, circle_b),
        intersection_points=tuple(intersections),
        intersection_quadrants=_intersection_quadrants(intersections),
    )


def _line_circle_tangent_bank() -> Tuple[_PanelSpec, ...]:
    return (
        _line_circle_panel("line_circle_tangent_top", center=(0.0, 0.0), radius=2.2, line_y=2.2, relation_class="tangent"),
        _line_circle_panel("line_circle_tangent_bottom", center=(-0.8, -0.4), radius=1.8, line_y=-2.2, relation_class="tangent"),
        _line_circle_panel("line_circle_tangent_shifted_top", center=(1.0, 0.7), radius=2.1, line_y=2.8, relation_class="tangent"),
        _line_circle_panel("line_circle_tangent_shifted_bottom", center=(-1.1, 0.5), radius=1.9, line_y=-1.4, relation_class="tangent"),
    )


def _line_circle_secant_bank() -> Tuple[_PanelSpec, ...]:
    return (
        _line_circle_panel("line_circle_secant_center", center=(0.0, 0.0), radius=2.4, line_y=0.0, relation_class="two_intersections"),
        _line_circle_panel("line_circle_secant_upper", center=(-0.5, 0.2), radius=2.0, line_y=1.2, relation_class="two_intersections"),
        _line_circle_panel("line_circle_secant_lower", center=(1.0, -0.2), radius=1.9, line_y=-1.1, relation_class="two_intersections"),
        _line_circle_panel("line_circle_secant_high", center=(-1.0, 0.6), radius=2.2, line_y=1.9, relation_class="two_intersections"),
    )


def _line_circle_disjoint_bank() -> Tuple[_PanelSpec, ...]:
    return (
        _line_circle_panel("line_circle_disjoint_top", center=(0.0, 0.0), radius=1.7, line_y=2.7, relation_class="no_intersection"),
        _line_circle_panel("line_circle_disjoint_bottom", center=(-0.8, -0.5), radius=1.8, line_y=-3.1, relation_class="no_intersection"),
        _line_circle_panel("line_circle_disjoint_shifted_top", center=(1.0, 0.6), radius=1.5, line_y=3.0, relation_class="no_intersection"),
        _line_circle_panel("line_circle_disjoint_shifted_bottom", center=(1.2, -0.1), radius=1.4, line_y=-2.2, relation_class="no_intersection"),
    )


def _circle_circle_two_intersection_bank() -> Tuple[_PanelSpec, ...]:
    return (
        _circle_circle_panel(
            "circle_circle_two_horizontal",
            circle_a=((-1.2, 0.0), 1.9),
            circle_b=((1.2, 0.0), 1.9),
            relation_class="two_intersections",
        ),
        _circle_circle_panel(
            "circle_circle_two_diagonal",
            circle_a=((-1.4, -0.5), 2.0),
            circle_b=((1.1, 0.7), 2.0),
            relation_class="two_intersections",
        ),
        _circle_circle_panel(
            "circle_circle_two_low",
            circle_a=((-1.0, -1.0), 1.8),
            circle_b=((1.4, -1.0), 1.8),
            relation_class="two_intersections",
        ),
        _circle_circle_panel(
            "circle_circle_two_high",
            circle_a=((-1.1, 1.0), 1.7),
            circle_b=((1.2, 1.0), 1.7),
            relation_class="two_intersections",
        ),
    )


def _circle_circle_tangent_bank() -> Tuple[_PanelSpec, ...]:
    return (
        _circle_circle_panel(
            "circle_circle_tangent_center",
            circle_a=((-2.0, 0.0), 2.0),
            circle_b=((2.0, 0.0), 2.0),
            relation_class="tangent",
        ),
        _circle_circle_panel(
            "circle_circle_tangent_low",
            circle_a=((-1.8, -0.8), 1.8),
            circle_b=((1.8, -0.8), 1.8),
            relation_class="tangent",
        ),
        _circle_circle_panel(
            "circle_circle_tangent_upper",
            circle_a=((-1.6, 1.0), 1.6),
            circle_b=((1.6, 1.0), 1.6),
            relation_class="tangent",
        ),
        _circle_circle_panel(
            "circle_circle_tangent_vertical",
            circle_a=((0.0, -1.8), 1.6),
            circle_b=((0.0, 1.4), 1.6),
            relation_class="tangent",
        ),
    )


def _circle_circle_disjoint_bank() -> Tuple[_PanelSpec, ...]:
    return (
        _circle_circle_panel(
            "circle_circle_disjoint_wide",
            circle_a=((-2.5, 0.0), 1.5),
            circle_b=((2.5, 0.0), 1.5),
            relation_class="no_intersection",
        ),
        _circle_circle_panel(
            "circle_circle_disjoint_diagonal",
            circle_a=((-2.0, -1.0), 1.3),
            circle_b=((2.0, 1.0), 1.3),
            relation_class="no_intersection",
        ),
        _circle_circle_panel(
            "circle_circle_disjoint_nested",
            circle_a=((0.0, 0.0), 2.7),
            circle_b=((0.8, 0.2), 0.8),
            relation_class="no_intersection",
        ),
        _circle_circle_panel(
            "circle_circle_disjoint_nested_offset",
            circle_a=((-0.4, 0.2), 2.5),
            circle_b=((1.0, -0.5), 0.7),
            relation_class="no_intersection",
        ),
    )


def _template_index(params: Mapping[str, Any], *, instance_seed: int, query_id: str, support_size: int) -> int:
    selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.panel_template.{query_id}",
    )
    return int(selection_index) % max(1, int(support_size))


def _shuffled_without_winner(panels: Sequence[_PanelSpec], *, winner: _PanelSpec, rng) -> List[_PanelSpec]:
    distractors = [panel for panel in panels if str(panel.pair_id) != str(winner.pair_id)]
    rng.shuffle(distractors)
    return distractors


def _build_panels(query: _ResolvedQuery, *, instance_seed: int, params: Mapping[str, Any]) -> Dict[str, _PanelSpec]:
    query_id = str(query.query_id)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.panels.{query_id}")

    if query_id == "line_circle_tangent_label":
        winners = _line_circle_tangent_bank()
        winner = winners[_template_index(params, instance_seed=int(instance_seed), query_id=query_id, support_size=len(winners))]
        distractors = list(_line_circle_secant_bank() + _line_circle_disjoint_bank())
        rng.shuffle(distractors)
    elif query_id == "line_circle_two_intersections_label":
        winners = _line_circle_secant_bank()
        winner = winners[_template_index(params, instance_seed=int(instance_seed), query_id=query_id, support_size=len(winners))]
        distractors = list(_line_circle_tangent_bank() + _line_circle_disjoint_bank())
        rng.shuffle(distractors)
    elif query_id == "circle_circle_two_intersections_label":
        winners = _circle_circle_two_intersection_bank()
        winner = winners[_template_index(params, instance_seed=int(instance_seed), query_id=query_id, support_size=len(winners))]
        distractors = list(_circle_circle_tangent_bank() + _circle_circle_disjoint_bank())
        rng.shuffle(distractors)
    else:
        raise ValueError(f"unsupported query_id: {query_id}")

    panels_by_label: Dict[str, _PanelSpec] = {}
    distractor_iter = iter(distractors)
    for label in query.label_pool:
        if str(label) == str(query.winner_label):
            panels_by_label[str(label)] = winner
        else:
            panels_by_label[str(label)] = next(distractor_iter)
    _validate_unique_answer(query, panels_by_label)
    return panels_by_label


def _matches_query(query: _ResolvedQuery, panel: _PanelSpec, *, target_quadrant: str) -> bool:
    query_id = str(query.query_id)
    if query_id == "line_circle_tangent_label":
        return str(panel.pair_kind) == "line_circle" and str(panel.relation_class) == "tangent"
    if query_id == "line_circle_two_intersections_label":
        return str(panel.pair_kind) == "line_circle" and len(panel.intersection_points) == 2
    if query_id == "circle_circle_two_intersections_label":
        return str(panel.pair_kind) == "circle_circle" and len(panel.intersection_points) == 2
    raise ValueError(f"unsupported query_id: {query_id}")


def _color_triplet(value: Any) -> Color:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 3:
        raise ValueError("object colors must be RGB triples")
    return tuple(max(0, min(255, int(channel))) for channel in value)  # type: ignore[return-value]


def _resolve_panel_style(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[CoordinatePanelStyle, Dict[str, Any]]:
    explicit_index = params.get("panel_style_index")
    if explicit_index is not None:
        style_index = int(explicit_index) % len(_PANEL_STYLES)
        style = _PANEL_STYLES[int(style_index)]
        return style, {
            "source": "params",
            "style_index": int(style_index),
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


def _resolve_object_colors(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[Tuple[Color, ...], Dict[str, Any]]:
    explicit = params.get("object_colors")
    if explicit is not None:
        if not isinstance(explicit, Sequence) or isinstance(explicit, (str, bytes)):
            raise ValueError("object_colors must be a sequence of RGB triples")
        colors = tuple(_color_triplet(color) for color in explicit)
        if len(colors) < 2:
            raise ValueError("object_colors must contain at least two colors")
        return colors, {
            "source": "params",
            "palette_index": None,
            "order": "as_provided",
            "colors": [list(color) for color in colors],
        }

    selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.object_colors",
    )
    palette_index = int(selection_index) % len(_OBJECT_COLOR_PALETTES)
    colors = tuple(_OBJECT_COLOR_PALETTES[int(palette_index)])
    order_index = (int(selection_index) // len(_OBJECT_COLOR_PALETTES)) % 2
    if int(order_index) == 1:
        colors = tuple(reversed(colors))
    return colors, {
        "source": "selection_index",
        "selection_index": int(selection_index),
        "palette_index": int(palette_index),
        "order": "reversed" if int(order_index) == 1 else "forward",
        "colors": [list(color) for color in colors],
    }


def _resolve_intersection_color(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[Color, Dict[str, Any]]:
    explicit = params.get("intersection_color")
    if explicit is not None:
        color = _color_triplet(explicit)
        return color, {
            "source": "params",
            "color_index": None,
            "color": list(color),
        }

    selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.intersection_color",
    )
    color_index = int(selection_index) % len(_INTERSECTION_COLORS)
    color = _INTERSECTION_COLORS[int(color_index)]
    return color, {
        "source": "selection_index",
        "selection_index": int(selection_index),
        "color_index": int(color_index),
        "color": list(color),
    }


def _validate_unique_answer(query: _ResolvedQuery, panels_by_label: Mapping[str, _PanelSpec]) -> None:
    winner = panels_by_label[str(query.winner_label)]
    target_quadrant = str(winner.intersection_quadrants[0]) if winner.intersection_quadrants else ""
    matches = [
        str(label)
        for label, panel in panels_by_label.items()
        if _matches_query(query, panel, target_quadrant=target_quadrant)
    ]
    if matches != [str(query.winner_label)]:
        raise RuntimeError(f"intersection_property_label answer is not unique: {matches}")


def _draw_circle(
    draw: ImageDraw.ImageDraw,
    *,
    circle: CircleSpec,
    plot_bbox: BBox,
    config: CoordinatePanelConfig,
    color: Tuple[int, int, int],
    line_width: int,
) -> None:
    center, radius = circle
    center_px = graph_point_to_panel_pixel(center, plot_bbox=plot_bbox, config=config)
    plot_scale = float(plot_bbox[2] - plot_bbox[0]) / float(_GRID_MAX - _GRID_MIN)
    radius_px = float(radius) * float(plot_scale)
    draw.ellipse(
        (
            center_px[0] - radius_px,
            center_px[1] - radius_px,
            center_px[0] + radius_px,
            center_px[1] + radius_px,
        ),
        outline=color,
        width=int(line_width),
    )


def _draw_line_segment(
    draw: ImageDraw.ImageDraw,
    *,
    segment: LineSegment,
    plot_bbox: BBox,
    config: CoordinatePanelConfig,
    color: Tuple[int, int, int],
    line_width: int,
) -> None:
    pixel_points = [
        graph_point_to_panel_pixel(point, plot_bbox=plot_bbox, config=config)
        for point in segment
    ]
    draw.line(pixel_points, fill=color, width=int(line_width), joint="curve")
    draw_endpoint(draw, pixel_points[0], color=color, radius=max(3, int(line_width)))
    draw_endpoint(draw, pixel_points[-1], color=color, radius=max(3, int(line_width)))


def _draw_panel_spec(
    draw: ImageDraw.ImageDraw,
    panel: _PanelSpec,
    *,
    plot_bbox: BBox,
    config: CoordinatePanelConfig,
    line_width: int,
    object_colors: Sequence[Color],
    intersection_color: Color,
) -> None:
    for index, circle in enumerate(panel.circles):
        _draw_circle(
            draw,
            circle=circle,
            plot_bbox=plot_bbox,
            config=config,
            color=object_colors[int(index) % len(object_colors)],
            line_width=int(line_width),
        )
    for index, segment in enumerate(panel.line_segments):
        color_index = int(index + len(panel.circles)) % len(object_colors)
        _draw_line_segment(
            draw,
            segment=segment,
            plot_bbox=plot_bbox,
            config=config,
            color=object_colors[color_index],
            line_width=int(line_width),
        )
    for point in panel.intersection_points:
        point_px = graph_point_to_panel_pixel(point, plot_bbox=plot_bbox, config=config)
        draw_endpoint(
            draw,
            point_px,
            color=intersection_color,
            radius=max(3, int(line_width)),
            outline=(255, 255, 255),
        )


def _point_bbox(point: Point, *, plot_bbox: BBox, config: CoordinatePanelConfig, canvas_size: Tuple[int, int], radius: int = 7) -> List[int]:
    point_px = graph_point_to_panel_pixel(point, plot_bbox=plot_bbox, config=config)
    width, height = int(canvas_size[0]), int(canvas_size[1])
    return [
        max(0, min(width, int(round(float(point_px[0]) - float(radius))))),
        max(0, min(height, int(round(float(point_px[1]) - float(radius))))),
        max(0, min(width, int(round(float(point_px[0]) + float(radius))))),
        max(0, min(height, int(round(float(point_px[1]) + float(radius))))),
    ]


def _render_scene(query: _ResolvedQuery, *, instance_seed: int, params: Mapping[str, Any]) -> _RenderedScene:
    canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 1024)))
    canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 1024)))
    line_width = int(params.get("line_width", group_default(_RENDER_DEFAULTS, "line_width", 4)))
    canvas_width = max(720, int(canvas_width))
    canvas_height = max(520, int(canvas_height))
    line_width = max(2, int(line_width))

    image, background_meta = make_background_canvas(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=_BACKGROUND_DEFAULTS,
        fallback_color=(248, 250, 252),
    )
    draw = ImageDraw.Draw(image)
    panels_by_label = _build_panels(query, instance_seed=int(instance_seed), params=params)
    panel_style, panel_style_meta = _resolve_panel_style(params, instance_seed=int(instance_seed))
    object_colors, object_color_meta = _resolve_object_colors(params, instance_seed=int(instance_seed))
    intersection_color, intersection_color_meta = _resolve_intersection_color(params, instance_seed=int(instance_seed))
    panel_columns, panel_rows = panel_grid_shape_for_option_count(len(query.label_pool))
    panel_config = CoordinatePanelConfig(
        grid_min=_GRID_MIN,
        grid_max=_GRID_MAX,
        columns=int(panel_columns),
        rows=int(panel_rows),
    )
    layout = coordinate_panel_layout(int(canvas_width), int(canvas_height), config=panel_config)
    panel_bboxes: Dict[str, List[int]] = {}
    plot_bboxes: Dict[str, List[int]] = {}
    intersection_point_bboxes: Dict[str, List[List[int]]] = {}

    for index, label in enumerate(query.label_pool):
        panel_bbox = panel_bbox_for_index(layout, int(index), config=panel_config)
        plot_bbox = plot_bbox_for_panel(panel_bbox)
        panel_bboxes[str(label)] = [int(value) for value in panel_bbox]
        plot_bboxes[str(label)] = [int(value) for value in plot_bbox]
        draw_coordinate_panel_grid(
            draw,
            panel_bbox=panel_bbox,
            plot_bbox=plot_bbox,
            label=str(label),
            config=panel_config,
            style=panel_style,
        )
        panel = panels_by_label[str(label)]
        _draw_panel_spec(
            draw,
            panel,
            plot_bbox=plot_bbox,
            config=panel_config,
            line_width=int(line_width),
            object_colors=object_colors,
            intersection_color=intersection_color,
        )
        intersection_point_bboxes[str(label)] = [
            _point_bbox(point, plot_bbox=plot_bbox, config=panel_config, canvas_size=(int(canvas_width), int(canvas_height)))
            for point in panel.intersection_points
        ]

    image, post_noise_meta = apply_post_image_noise(
        image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=_POST_IMAGE_NOISE_DEFAULTS,
    )
    winner_panel = panels_by_label[str(query.winner_label)]
    target_quadrant = str(winner_panel.intersection_quadrants[0]) if winner_panel.intersection_quadrants else ""
    return _RenderedScene(
        image=image,
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
        panel_style_meta=dict(panel_style_meta),
        panels_by_label=dict(panels_by_label),
        panel_bboxes=dict(panel_bboxes),
        plot_bboxes=dict(plot_bboxes),
        intersection_point_bboxes=dict(intersection_point_bboxes),
        panel_columns=int(panel_columns),
        panel_rows=int(panel_rows),
        panel_count_probabilities=dict(query.panel_count_probabilities),
        target_quadrant=str(target_quadrant),
        object_color_meta=dict(object_color_meta),
        object_colors=tuple(object_colors),
        intersection_color_meta=dict(intersection_color_meta),
        intersection_color=tuple(intersection_color),
    )


def _panel_trace_payload(panel: _PanelSpec) -> Dict[str, Any]:
    return {
        "pair_id": str(panel.pair_id),
        "pair_kind": str(panel.pair_kind),
        "relation_class": str(panel.relation_class),
        "intersection_count": int(len(panel.intersection_points)),
        "intersection_points": [[round(float(x), 4), round(float(y), 4)] for x, y in panel.intersection_points],
        "intersection_quadrants": list(panel.intersection_quadrants),
        "line_segments": [
            [[round(float(a[0]), 4), round(float(a[1]), 4)], [round(float(b[0]), 4), round(float(b[1]), 4)]]
            for a, b in panel.line_segments
        ],
        "circles": [
            {"center": [round(float(center[0]), 4), round(float(center[1]), 4)], "radius": round(float(radius), 4)}
            for center, radius in panel.circles
        ],
    }


def _build_complexity(query_id: str) -> Any:
    weights = resolve_geometry_complexity_weights(
        _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        task_id=TASK_ID,
    )
    reasoning = {
        "line_circle_tangent_label": 0.58,
        "line_circle_two_intersections_label": 0.50,
        "circle_circle_two_intersections_label": 0.64,
    }[str(query_id)]
    ambiguity = {
        "line_circle_tangent_label": 0.56,
        "line_circle_two_intersections_label": 0.46,
        "circle_circle_two_intersections_label": 0.60,
    }[str(query_id)]
    return build_geometry_task_complexity(
        weights=weights,
        components={
            "visual_scan": 0.84,
            "analytical_reasoning": clamp_unit_interval(float(reasoning)),
            "ambiguity": clamp_unit_interval(float(ambiguity)),
            "output_burden": 0.24,
        },
    )


class GeometryAnalyticalIntersectionPropertyLabelTask:
    """Select the labeled coordinate panel matching one intersection-property query."""

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
                "annotation_hint_selected_panel_and_intersections",
                "answer_hint_option_letter",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        annotation_value = [
            list(rendered_scene.panel_bboxes[str(query.winner_label)]),
            *list(rendered_scene.intersection_point_bboxes[str(query.winner_label)]),
        ]
        json_example, json_example_answer_only = resolve_prompt_json_examples(
            _PROMPT_DEFAULTS,
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
                "target_quadrant": str(rendered_scene.target_quadrant),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint_selected_panel_and_intersections"]),
                "answer_hint": str(prompt_defaults["answer_hint_option_letter"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="option_letter", value=str(query.winner_label))
        annotation_gt = TypedValue(type="bbox_set", value=annotation_value)
        winner_panel = rendered_scene.panels_by_label[str(query.winner_label)]
        panels_trace = {
            str(label): _panel_trace_payload(rendered_scene.panels_by_label[str(label)])
            for label in query.label_pool
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_analytical_intersection_property_grid",
                "entities": [
                    {
                        "label": str(label),
                        "panel_bbox": list(rendered_scene.panel_bboxes[str(label)]),
                        "plot_bbox": list(rendered_scene.plot_bboxes[str(label)]),
                        "intersection_point_bboxes": list(rendered_scene.intersection_point_bboxes[str(label)]),
                        "object_pair": dict(panels_trace[str(label)]),
                    }
                    for label in query.label_pool
                ],
                "relations": {
                    "query_id": str(query.query_id),
                    "winner_label": str(query.winner_label),
                    "target_quadrant": str(rendered_scene.target_quadrant),
                    "object_colors": [list(color) for color in rendered_scene.object_colors],
                    "intersection_color": list(rendered_scene.intersection_color),
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
                    "panel_count_probabilities": dict(query.panel_count_probabilities),
                    "target_quadrant": str(rendered_scene.target_quadrant),
                },
            },
            "render_spec": {
                "canvas_width": int(rendered_scene.image.size[0]),
                "canvas_height": int(rendered_scene.image.size[1]),
                "coord_space": "pixel",
                "background_style": dict(rendered_scene.background_meta),
                "post_image_noise": dict(rendered_scene.post_noise_meta),
                "panel_style": dict(rendered_scene.panel_style_meta),
                "object_colors": [list(color) for color in rendered_scene.object_colors],
                "object_color_selection": dict(rendered_scene.object_color_meta),
                "intersection_color": list(rendered_scene.intersection_color),
                "intersection_color_selection": dict(rendered_scene.intersection_color_meta),
                "panel_count": int(len(query.label_pool)),
                "panel_count_probabilities": dict(rendered_scene.panel_count_probabilities),
                "panel_columns": int(rendered_scene.panel_columns),
                "panel_rows": int(rendered_scene.panel_rows),
                "graph_unit_bounds": {"x": [int(_GRID_MIN), int(_GRID_MAX)], "y": [int(_GRID_MIN), int(_GRID_MAX)]},
            },
            "render_map": {
                "panel_bboxes": dict(rendered_scene.panel_bboxes),
                "plot_bboxes": dict(rendered_scene.plot_bboxes),
                "intersection_point_bboxes": dict(rendered_scene.intersection_point_bboxes),
                "coord_space": "pixel",
            },
            "execution_trace": {
                "query_id": str(query.query_id),
                "answer_type": "option_letter",
                "answer_value": str(query.winner_label),
                "winner_label": str(query.winner_label),
                "winner_pair": dict(_panel_trace_payload(winner_panel)),
                "panels_by_label": dict(panels_trace),
                "target_quadrant": str(rendered_scene.target_quadrant),
                "query_id_probabilities": dict(query.query_id_probabilities),
                "winner_label_probabilities": dict(query.winner_label_probabilities),
                "panel_count_probabilities": dict(query.panel_count_probabilities),
            },
            "witness_symbolic": {
                "type": "intersection_property_panel_selection",
                "query_id": str(query.query_id),
                "answer_label": str(query.winner_label),
                "target_quadrant": str(rendered_scene.target_quadrant),
                "winner_pair": dict(_panel_trace_payload(winner_panel)),
                "panels_by_label": dict(panels_trace),
            },
            "projected_annotation": {
                "type": "bbox_set",
                "bbox_set": list(annotation_value),
                "panel_bbox_by_label": dict(rendered_scene.panel_bboxes),
                "plot_bbox_by_label": dict(rendered_scene.plot_bboxes),
                "intersection_point_bboxes_by_label": dict(rendered_scene.intersection_point_bboxes),
            },
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=rendered_scene.image,
            image_id="img_0",
            trace_payload=trace_payload,
            complexity=_build_complexity(str(query.query_id)),
            task_versions=default_task_versions(),
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class GeometryAnalyticalIntersectionPropertyPublicLabelTask(
    MultiFixedGeometryQueryTaskMixin,
    GeometryAnalyticalIntersectionPropertyLabelTask,
):
    """Choose the panel matching the requested intersection property."""

    task_id = "task_geometry__function_panels__intersection_property_label"
    fixed_query_ids = (
        "line_circle_tangent_label",
        "line_circle_two_intersections_label",
        "circle_circle_two_intersections_label",
    )
    scene_id = "function_panels"
    public_scene_id = "function_panels"
