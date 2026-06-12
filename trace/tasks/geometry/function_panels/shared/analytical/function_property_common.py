"""Shared constants and records for analytical function-panel property tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image

from ......core.scene_config import get_scene_defaults
from .....shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from ....shared.coordinate_panel_grid import CoordinatePanelStyle
from ....shared.noise_defaults import load_geometry_noise_defaults

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
INTERVAL_PROPERTY_VARIANTS: Tuple[str, ...] = SIGN_INTERVAL_VARIANTS
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "function_status_label",
    "one_to_one_status_label",
    "range_match_label",
    "x_axis_symmetry_label",
    *INTERVAL_PROPERTY_VARIANTS,
)
DEFAULT_LABEL_POOL: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")

_SCENE_DEFAULTS = get_scene_defaults("geometry", "function_panels")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_POST_IMAGE_NOISE_DEFAULTS = load_geometry_noise_defaults(scene_id="analytical")
_GRID_MIN = -5
_GRID_MAX = 5
_MAX_PANEL_COUNT = 6
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
    panel_count_probabilities: Dict[str, float]
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
    panel_columns: int
    panel_rows: int
    panel_count_probabilities: Dict[str, float]
    target_domain: str
    target_range: str
    target_interval: str


__all__ = [
    "Point",
    "BBox",
    "TASK_ID",
    "MONOTONIC_INTERVAL_INCREASING_LABEL",
    "MONOTONIC_INTERVAL_DECREASING_LABEL",
    "SIGN_INTERVAL_POSITIVE_LABEL",
    "SIGN_INTERVAL_NEGATIVE_LABEL",
    "MONOTONIC_INTERVAL_VARIANTS",
    "SIGN_INTERVAL_VARIANTS",
    "INTERVAL_PROPERTY_VARIANTS",
    "SUPPORTED_QUERY_IDS",
    "DEFAULT_LABEL_POOL",
    "_SCENE_DEFAULTS",
    "_GEN_DEFAULTS",
    "_RENDER_DEFAULTS",
    "_PROMPT_DEFAULTS",
    "_POST_IMAGE_NOISE_DEFAULTS",
    "_GRID_MIN",
    "_GRID_MAX",
    "_MAX_PANEL_COUNT",
    "Color",
    "_PANEL_STYLES",
    "_LINE_COLOR_PALETTES",
    "_RelationSpec",
    "_ResolvedQuery",
    "_RenderedScene",
]
