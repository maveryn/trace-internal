"""Shared constants and records for geometry graphing-count tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ......core.scene_config import get_scene_defaults
from .....shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from ....shared.background_defaults import load_geometry_background_defaults
from ....shared.noise_defaults import load_geometry_noise_defaults

TASK_ID = "geometry_graphing_count_base"

REFERENCE_LINE_CROSSING_COUNT = "reference_line_crossing_count"
TURNING_POINT_COUNT = "turning_point_count"
LOCAL_EXTREMUM_COUNT = "local_extremum_count"

X_AXIS_REFERENCE_LINE = "x_axis"
HORIZONTAL_REFERENCE_LINE = "horizontal_line"
SUPPORTED_REFERENCE_LINE_KINDS: Tuple[str, ...] = (
    X_AXIS_REFERENCE_LINE,
    HORIZONTAL_REFERENCE_LINE,
)
MINIMUM_EXTREMUM = "minimum"
MAXIMUM_EXTREMUM = "maximum"
SUPPORTED_EXTREMUM_KINDS: Tuple[str, ...] = (
    MINIMUM_EXTREMUM,
    MAXIMUM_EXTREMUM,
)

SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "quadratic",
    "absolute_value",
    "cubic",
    "sinusoid",
    "piecewise_linear",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    REFERENCE_LINE_CROSSING_COUNT,
    TURNING_POINT_COUNT,
    LOCAL_EXTREMUM_COUNT,
)
COMPATIBILITY: Dict[str, Sequence[str]] = {
    "quadratic": (REFERENCE_LINE_CROSSING_COUNT,),
    "absolute_value": (REFERENCE_LINE_CROSSING_COUNT,),
    "cubic": (REFERENCE_LINE_CROSSING_COUNT,),
    "sinusoid": (
        REFERENCE_LINE_CROSSING_COUNT,
        TURNING_POINT_COUNT,
        LOCAL_EXTREMUM_COUNT,
    ),
    "piecewise_linear": (
        REFERENCE_LINE_CROSSING_COUNT,
        TURNING_POINT_COUNT,
        LOCAL_EXTREMUM_COUNT,
    ),
}

POST_IMAGE_BACKGROUND_DEFAULTS = load_geometry_background_defaults(scene_id="graphing")
POST_IMAGE_NOISE_DEFAULTS = load_geometry_noise_defaults(scene_id="graphing")

GraphPoint = Tuple[int, int]
GraphPolylinePoint = Tuple[float, float]
_TARGET_COUNT_BALANCE_SALT = 330


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallbacks for graphing-family scenes."""

    canvas_size_min: int = 640
    canvas_size_max: int = 720
    graph_cells_min: int = 20
    graph_cells_max: int = 20
    line_width: int = 4
    guide_line_width: int = 3
    label_font_size_min: int = 16
    label_font_size_max: int = 24
    quadratic_reference_line_crossing_support: Tuple[int, ...] = (2,)
    absolute_value_reference_line_crossing_support: Tuple[int, ...] = (2,)
    cubic_reference_line_crossing_support: Tuple[int, ...] = (2, 3)
    sinusoid_reference_line_crossing_support: Tuple[int, ...] = (3, 4)
    sinusoid_turning_support: Tuple[int, ...] = (3, 4)
    sinusoid_local_extremum_support: Tuple[int, ...] = (2,)
    piecewise_reference_line_crossing_support: Tuple[int, ...] = (2, 3, 4, 5, 6)
    piecewise_turning_support: Tuple[int, ...] = (2, 3, 4, 5, 6)
    piecewise_local_extremum_support: Tuple[int, ...] = (2, 3, 4, 5, 6)
    horizontal_line_support: Tuple[int, ...] = (-4, -3, -2, -1, 1, 2, 3, 4)
    piecewise_intersection_x_positions: Tuple[int, ...] = (-9, -7, -5, -3, -2, -1, 0, 1, 2, 3, 5, 7, 9)
    piecewise_turning_x_positions: Tuple[int, ...] = (-9, -7, -5, -3, -2, -1, 0, 1, 2, 3, 5, 7, 9)


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved scene/query axes plus one balanced count target."""

    scene_variant: str
    query_id: str
    reference_line_kind: str | None
    extremum_kind: str | None
    target_count: int
    scene_variant_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    reference_line_kind_probabilities: Dict[str, float]
    extremum_kind_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _SampledGraphScene:
    """One sampled plotted-function scene before raster rendering."""

    polyline_graph: Tuple[GraphPolylinePoint, ...]
    annotation_graph_points: Tuple[GraphPoint, ...]
    query_line_y: int | None
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]
    execution_trace: Dict[str, Any]
    object_count: int


@dataclass(frozen=True)
class _RenderedGraphScene:
    """Rendered scene plus prompt-facing graph-point annotation artifacts."""

    answer_value: int
    annotation_type: str
    annotation_value: List[List[float]]
    projected_annotation: Dict[str, Any]
    witness_symbolic: Dict[str, Any]
    required_annotation_labels: List[str]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]
    execution_trace: Dict[str, Any]
    object_count: int


_DEFAULTS = _TaskDefaults()
_SCENE_DEFAULTS = get_scene_defaults("geometry", "function_graph")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)

__all__ = [
    "TASK_ID",
    "REFERENCE_LINE_CROSSING_COUNT",
    "TURNING_POINT_COUNT",
    "LOCAL_EXTREMUM_COUNT",
    "X_AXIS_REFERENCE_LINE",
    "HORIZONTAL_REFERENCE_LINE",
    "SUPPORTED_REFERENCE_LINE_KINDS",
    "MINIMUM_EXTREMUM",
    "MAXIMUM_EXTREMUM",
    "SUPPORTED_EXTREMUM_KINDS",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_QUERY_IDS",
    "COMPATIBILITY",
    "POST_IMAGE_BACKGROUND_DEFAULTS",
    "POST_IMAGE_NOISE_DEFAULTS",
    "GraphPoint",
    "GraphPolylinePoint",
    "_TARGET_COUNT_BALANCE_SALT",
    "_TaskDefaults",
    "_ResolvedQuery",
    "_SampledGraphScene",
    "_RenderedGraphScene",
    "_DEFAULTS",
    "_SCENE_DEFAULTS",
    "_GEN_DEFAULTS",
    "_RENDER_DEFAULTS",
    "_PROMPT_DEFAULTS",
]
