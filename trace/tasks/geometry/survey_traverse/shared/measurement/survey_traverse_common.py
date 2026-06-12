"""Common records and geometry helpers for survey traverse tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Tuple

from PIL import Image, ImageDraw

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

SCENE_ID = "survey_traverse"
BEARING_NAMESPACE = "survey_traverse.bearing_angle"
ELEVATION_NAMESPACE = "survey_traverse.station_elevation"
AREA_NAMESPACE = "survey_traverse.traverse_area"
PROMPT_BUNDLE_ID = "geometry_survey_traverse_v0"
DEGREE_SYMBOL = chr(176)

QUERY_IDS: Tuple[str, ...] = (
    "bearing_from_back_bearing",
    "closed_traverse_missing_bearing",
)
ELEVATION_QUERY_IDS: Tuple[str, ...] = (
    "leveling_station_elevation",
    "slope_distance_elevation_change",
)
AREA_QUERY_IDS: Tuple[str, ...] = (
    "coordinate_traverse_area",
    "offset_trapezoid_area",
)
BEARING_SUPPORT: Tuple[int, ...] = (
    20,
    30,
    40,
    50,
    60,
    70,
    80,
    100,
    110,
    120,
    130,
    140,
    150,
    160,
    200,
    210,
    220,
    230,
    240,
    250,
    260,
    280,
    290,
    300,
    310,
    320,
    330,
    340,
)
TURN_SUPPORT: Tuple[int, ...] = (35, 45, 55, 65, 75, 85, 95, 105, 115, 125)
_ANNOTATION_KEYS: Tuple[str, ...] = (
    "station_a",
    "station_b",
    "reference_north",
    "target_direction",
)
_CLOSED_ANNOTATION_KEYS: Tuple[str, ...] = (
    "station_a",
    "station_b",
    "reference_north",
    "target_direction",
    "turn_vertex",
)
_ELEVATION_ANNOTATION_KEYS: Tuple[str, ...] = (
    "reference_station",
    "target_station",
    "measurement_line",
    "field_note_region",
)
_AREA_ANNOTATION_KEYS: Tuple[str, ...] = (
    "traverse_region",
    "field_note_region",
    "area_reference_region",
)

_LEVELING_CASES: Tuple[Tuple[int, int, int], ...] = (
    (120, 4, 7),
    (96, 6, 2),
    (142, 3, 8),
    (88, 5, 9),
    (135, 7, 4),
    (105, 2, 6),
    (160, 8, 3),
    (118, 9, 5),
    (175, 4, 10),
    (132, 6, 11),
)
_SLOPE_ELEVATION_CASES: Tuple[Tuple[int, int, int], ...] = (
    (100, 80, 2),
    (120, 60, -3),
    (96, 100, 1),
    (150, 40, -4),
    (82, 80, 3),
    (135, 100, -2),
    (110, 60, 4),
    (170, 40, -5),
    (92, 120, 1),
    (148, 80, -3),
)
_COORDINATE_TRAVERSE_CASES: Tuple[Tuple[int, int, int, int, int, int, int, int], ...] = (
    (0, 0, 6, 0, 7, 4, 0, 6),
    (0, 0, 8, 0, 8, 5, 0, 7),
    (0, 0, 5, 0, 7, 6, 0, 8),
    (0, 0, 9, 0, 8, 4, 0, 6),
    (0, 0, 7, 0, 9, 6, 0, 8),
    (0, 0, 10, 0, 8, 4, 0, 6),
)
_OFFSET_TRAPEZOID_CASES: Tuple[Tuple[int, int, int, int, int, int, int], ...] = (
    (20, 40, 60, 3, 5, 4, 2),
    (30, 60, 90, 2, 4, 7, 5),
    (20, 50, 80, 4, 6, 3, 5),
    (25, 50, 75, 6, 2, 4, 8),
    (40, 80, 120, 3, 6, 5, 2),
    (30, 70, 100, 5, 3, 6, 4),
)

@dataclass(frozen=True)
class _ResolvedProblem:
    query_id: str
    answer: int
    known_bearing: int
    given_bearing: int
    station_labels: Tuple[str, str, str]
    turn_angle: int | None
    turn_direction: str | None
    query_probabilities: Dict[str, float]
    bearing_probabilities: Dict[str, float]
    turn_probabilities: Dict[str, float]

@dataclass(frozen=True)
class _ResolvedElevationProblem:
    query_id: str
    answer: int
    reference_elevation: int
    target_elevation: int
    station_labels: Tuple[str, str, str]
    backsight: int | None
    foresight: int | None
    height_of_instrument: int | None
    slope_distance: int | None
    rise_per_20: int | None
    total_rise: int | None
    query_probabilities: Dict[str, float]
    case_probabilities: Dict[str, float]

@dataclass(frozen=True)
class _ResolvedAreaProblem:
    query_id: str
    answer: int
    station_labels: Tuple[str, str, str, str]
    coordinate_points: Tuple[Tuple[int, int], ...]
    chainages: Tuple[int, ...]
    offsets: Tuple[int, ...]
    formula_family: str
    query_probabilities: Dict[str, float]
    case_probabilities: Dict[str, float]

@dataclass
class _RenderContext:
    image: Image.Image
    draw: ImageDraw.ImageDraw
    width: int
    height: int
    line_color: Color
    secondary_color: Color
    guide_color: Color
    label_color: Color
    label_stroke_color: Color
    panel_fill: Color
    panel_alt_fill: Color
    accent_color: Color
    secondary_accent_color: Color
    line_width: int
    label_stroke_width: int
    font: Any
    small_font: Any
    tiny_font: Any
    diagram_style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]

@dataclass(frozen=True)
class _RenderedSurveyScene:
    image: Image.Image
    annotation_keyed_points: Dict[str, Point]
    annotation_roles: Tuple[str, ...]
    scene_entities: Tuple[Dict[str, Any], ...]
    label_bboxes: Dict[str, BBox]
    render_map: Dict[str, Any]
    witness: Dict[str, Any]

@dataclass(frozen=True)
class _RenderedSurveyAreaScene:
    image: Image.Image
    annotation_bboxes: Dict[str, BBox]
    scene_entities: Tuple[Dict[str, Any], ...]
    label_bboxes: Dict[str, BBox]
    render_map: Dict[str, Any]
    witness: Dict[str, Any]

def _normalize_bearing(value: int | float) -> int:
    return int(round(float(value))) % 360

def _bearing_to_unit_vector(bearing_degrees: int | float) -> Point:
    theta = math.radians(float(bearing_degrees))
    return (math.sin(theta), -math.cos(theta))


__all__ = [
    '_ResolvedProblem',
    '_ResolvedElevationProblem',
    '_ResolvedAreaProblem',
    '_RenderContext',
    '_RenderedSurveyScene',
    '_RenderedSurveyAreaScene',
    '_normalize_bearing',
    '_bearing_to_unit_vector',
    'Point',
    'BBox',
    'Color',
    'SCENE_ID',
    'SCENE_ID',
    'BEARING_NAMESPACE',
    'ELEVATION_NAMESPACE',
    'AREA_NAMESPACE',
    'PROMPT_BUNDLE_ID',
    'DEGREE_SYMBOL',
]
