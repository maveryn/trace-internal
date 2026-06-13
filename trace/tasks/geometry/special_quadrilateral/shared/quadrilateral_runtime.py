"""Special-quadrilateral theorem measurement tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from trace.core.seed import spawn_rng
from trace.core.scene_config import get_scene_defaults
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.shared.config_defaults import (
    required_group_defaults,
    split_scene_generation_rendering_prompt_defaults,
)

SCENE_ID = "special_quadrilateral"
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from trace.tasks.shared.prompt_json_example import build_keyed_point_prompt_json_examples
from trace.tasks.shared.text_legibility import draw_text_traced
from trace.tasks.shared.text_rendering import load_font
from trace.tasks.geometry.shared.diagram_style import prepare_geometry_diagram_style_and_background
from trace.tasks.geometry.shared.measurement_rendering import bbox_from_points, pad_bbox
from trace.tasks.geometry.shared.metadata_serialization import geometry_json_ready as _json_ready
from trace.tasks.geometry.shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS
from trace.tasks.geometry.shared.scene_transform import LazySceneTransform
from trace.tasks.geometry.shared.vector2d import add_scaled as _add, mid as _mid, point_to_list as _point_to_list, sub as _sub, unit as _unit

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

PROMPT_BUNDLE_ID = "geometry_special_quadrilateral_v0"
DIAGONAL_OBJECTIVE = "diagonal_angle_value"
ALGEBRAIC_OBJECTIVE = "algebraic_angle_value"
SEGMENT_OBJECTIVE = "segment_length_value"
DEGREE_SYMBOL = chr(176)

_SCENE_DEFAULTS = get_scene_defaults("geometry", "special_quadrilateral")

_DIAGONAL_QUERY_IDS: Tuple[str, ...] = (
    "rhombus_vertex_angle_bisected_by_diagonal",
    "kite_vertex_angle_bisected_by_symmetry_diagonal",
    "rhombus_diagonal_perpendicular_complement",
)
_ALGEBRAIC_QUERY_IDS: Tuple[str, ...] = (
    "parallelogram_opposite_angle_expression",
    "parallelogram_consecutive_angle_expression",
    "rhombus_diagonal_half_angle_expression",
    "kite_opposite_angle_expression",
)
_SEGMENT_QUERY_IDS: Tuple[str, ...] = (
    "parallelogram_opposite_side_expression",
    "rhombus_all_sides_expression",
    "kite_adjacent_equal_side_expression",
    "parallelogram_diagonal_bisection_expression",
)


@dataclass(frozen=True)
class _LinearExpression:
    coefficient: int
    constant: int

    def evaluate(self, x_value: int) -> int:
        return int(self.coefficient) * int(x_value) + int(self.constant)

    def display(self, *, degree: bool = False) -> str:
        coefficient = int(self.coefficient)
        constant = int(self.constant)
        if coefficient == 1:
            body = "x"
        elif coefficient == -1:
            body = "-x"
        else:
            body = f"{coefficient}x"
        if constant > 0:
            body = f"{body}+{constant}"
        elif constant < 0:
            body = f"{body}{constant}"
        if degree:
            return f"({body}){DEGREE_SYMBOL}"
        return body


@dataclass(frozen=True)
class _Case:
    query_id: str
    shape_kind: str
    answer: int
    target_name: str
    target_label: str
    support_label: str
    theorem: str
    x_value: int | None = None
    target_expression: _LinearExpression | None = None
    support_expression: _LinearExpression | None = None
    extra_label: str = ""


@dataclass(frozen=True)
class _ResolvedProblem:
    objective_key: str
    query_id: str
    case: _Case
    query_probabilities: Dict[str, float]
    case_index: int
    layout_seed: int


@dataclass(frozen=True)
class SpecialQuadrilateralArtifact:
    prompt: str
    answer_type: str
    answer_value: Any
    annotation_type: str
    annotation_value: Any
    image: Image.Image
    trace_payload: Dict[str, Any]
    task_versions: Dict[str, str]
    query_id: str
    prompt_variants: Dict[str, Any]


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
    accent_color: Color
    muted_color: Color
    fill_color: Color
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
    vertices: Dict[str, Point]
    annotation_points: Dict[str, Point]
    point_label_bboxes: Dict[str, BBox]
    readout_bboxes: Dict[str, BBox]
    construction_bboxes: Dict[str, BBox]
    render_map: Dict[str, Any]


_DIAGONAL_CASES: Tuple[_Case, ...] = (
    _Case(
        "rhombus_vertex_angle_bisected_by_diagonal",
        "rhombus",
        35,
        "angle BDO",
        "35" + DEGREE_SYMBOL,
        "35" + DEGREE_SYMBOL,
        "rhombus_diagonal_bisects_vertex_angle",
    ),
    _Case(
        "rhombus_vertex_angle_bisected_by_diagonal",
        "rhombus",
        45,
        "angle BDO",
        "45" + DEGREE_SYMBOL,
        "45" + DEGREE_SYMBOL,
        "rhombus_diagonal_bisects_vertex_angle",
    ),
    _Case(
        "rhombus_vertex_angle_bisected_by_diagonal",
        "rhombus",
        55,
        "angle BDO",
        "55" + DEGREE_SYMBOL,
        "55" + DEGREE_SYMBOL,
        "rhombus_diagonal_bisects_vertex_angle",
    ),
    _Case(
        "rhombus_vertex_angle_bisected_by_diagonal",
        "rhombus",
        25,
        "angle BDO",
        "25" + DEGREE_SYMBOL,
        "25" + DEGREE_SYMBOL,
        "rhombus_diagonal_bisects_vertex_angle",
    ),
    _Case(
        "rhombus_vertex_angle_bisected_by_diagonal",
        "rhombus",
        65,
        "angle BDO",
        "65" + DEGREE_SYMBOL,
        "65" + DEGREE_SYMBOL,
        "rhombus_diagonal_bisects_vertex_angle",
    ),
    _Case(
        "kite_vertex_angle_bisected_by_symmetry_diagonal",
        "kite",
        30,
        "angle BAC",
        "30" + DEGREE_SYMBOL,
        "30" + DEGREE_SYMBOL,
        "kite_symmetry_diagonal_bisects_vertex_angle",
    ),
    _Case(
        "kite_vertex_angle_bisected_by_symmetry_diagonal",
        "kite",
        40,
        "angle BAC",
        "40" + DEGREE_SYMBOL,
        "40" + DEGREE_SYMBOL,
        "kite_symmetry_diagonal_bisects_vertex_angle",
    ),
    _Case(
        "kite_vertex_angle_bisected_by_symmetry_diagonal",
        "kite",
        50,
        "angle BAC",
        "50" + DEGREE_SYMBOL,
        "50" + DEGREE_SYMBOL,
        "kite_symmetry_diagonal_bisects_vertex_angle",
    ),
    _Case(
        "kite_vertex_angle_bisected_by_symmetry_diagonal",
        "kite",
        25,
        "angle BAC",
        "25" + DEGREE_SYMBOL,
        "25" + DEGREE_SYMBOL,
        "kite_symmetry_diagonal_bisects_vertex_angle",
    ),
    _Case(
        "kite_vertex_angle_bisected_by_symmetry_diagonal",
        "kite",
        55,
        "angle BAC",
        "55" + DEGREE_SYMBOL,
        "55" + DEGREE_SYMBOL,
        "kite_symmetry_diagonal_bisects_vertex_angle",
    ),
    _Case(
        "rhombus_diagonal_perpendicular_complement",
        "rhombus",
        30,
        "angle ABO",
        "30" + DEGREE_SYMBOL,
        "60" + DEGREE_SYMBOL,
        "rhombus_diagonals_are_perpendicular",
    ),
    _Case(
        "rhombus_diagonal_perpendicular_complement",
        "rhombus",
        40,
        "angle ABO",
        "40" + DEGREE_SYMBOL,
        "50" + DEGREE_SYMBOL,
        "rhombus_diagonals_are_perpendicular",
    ),
    _Case(
        "rhombus_diagonal_perpendicular_complement",
        "rhombus",
        55,
        "angle ABO",
        "55" + DEGREE_SYMBOL,
        "35" + DEGREE_SYMBOL,
        "rhombus_diagonals_are_perpendicular",
    ),
    _Case(
        "rhombus_diagonal_perpendicular_complement",
        "rhombus",
        20,
        "angle ABO",
        "20" + DEGREE_SYMBOL,
        "70" + DEGREE_SYMBOL,
        "rhombus_diagonals_are_perpendicular",
    ),
    _Case(
        "rhombus_diagonal_perpendicular_complement",
        "rhombus",
        65,
        "angle ABO",
        "65" + DEGREE_SYMBOL,
        "25" + DEGREE_SYMBOL,
        "rhombus_diagonals_are_perpendicular",
    ),
)

_ALGEBRAIC_CASES: Tuple[_Case, ...] = (
    _Case(
        "parallelogram_opposite_angle_expression",
        "parallelogram",
        45,
        "angle BCD",
        _LinearExpression(2, 25).display(degree=True),
        _LinearExpression(3, 15).display(degree=True),
        "opposite_angles_of_a_parallelogram_are_equal",
        x_value=10,
        target_expression=_LinearExpression(2, 25),
        support_expression=_LinearExpression(3, 15),
    ),
    _Case(
        "parallelogram_opposite_angle_expression",
        "parallelogram",
        60,
        "angle BCD",
        _LinearExpression(1, 42).display(degree=True),
        _LinearExpression(2, 24).display(degree=True),
        "opposite_angles_of_a_parallelogram_are_equal",
        x_value=18,
        target_expression=_LinearExpression(1, 42),
        support_expression=_LinearExpression(2, 24),
    ),
    _Case(
        "parallelogram_opposite_angle_expression",
        "parallelogram",
        70,
        "angle BCD",
        _LinearExpression(4, 30).display(degree=True),
        _LinearExpression(3, 40).display(degree=True),
        "opposite_angles_of_a_parallelogram_are_equal",
        x_value=10,
        target_expression=_LinearExpression(4, 30),
        support_expression=_LinearExpression(3, 40),
    ),
    _Case(
        "parallelogram_opposite_angle_expression",
        "parallelogram",
        80,
        "angle BCD",
        _LinearExpression(5, 20).display(degree=True),
        _LinearExpression(2, 56).display(degree=True),
        "opposite_angles_of_a_parallelogram_are_equal",
        x_value=12,
        target_expression=_LinearExpression(5, 20),
        support_expression=_LinearExpression(2, 56),
    ),
    _Case(
        "parallelogram_opposite_angle_expression",
        "parallelogram",
        95,
        "angle BCD",
        _LinearExpression(3, 50).display(degree=True),
        _LinearExpression(4, 35).display(degree=True),
        "opposite_angles_of_a_parallelogram_are_equal",
        x_value=15,
        target_expression=_LinearExpression(3, 50),
        support_expression=_LinearExpression(4, 35),
    ),
    _Case(
        "parallelogram_consecutive_angle_expression",
        "parallelogram",
        120,
        "angle ABC",
        _LinearExpression(3, 60).display(degree=True),
        _LinearExpression(2, 20).display(degree=True),
        "consecutive_angles_of_a_parallelogram_are_supplementary",
        x_value=20,
        target_expression=_LinearExpression(3, 60),
        support_expression=_LinearExpression(2, 20),
    ),
    _Case(
        "parallelogram_consecutive_angle_expression",
        "parallelogram",
        110,
        "angle ABC",
        _LinearExpression(2, 74).display(degree=True),
        _LinearExpression(3, 16).display(degree=True),
        "consecutive_angles_of_a_parallelogram_are_supplementary",
        x_value=18,
        target_expression=_LinearExpression(2, 74),
        support_expression=_LinearExpression(3, 16),
    ),
    _Case(
        "parallelogram_consecutive_angle_expression",
        "parallelogram",
        100,
        "angle ABC",
        _LinearExpression(3, 40).display(degree=True),
        _LinearExpression(2, 40).display(degree=True),
        "consecutive_angles_of_a_parallelogram_are_supplementary",
        x_value=20,
        target_expression=_LinearExpression(3, 40),
        support_expression=_LinearExpression(2, 40),
    ),
    _Case(
        "parallelogram_consecutive_angle_expression",
        "parallelogram",
        130,
        "angle ABC",
        _LinearExpression(4, 70).display(degree=True),
        _LinearExpression(2, 20).display(degree=True),
        "consecutive_angles_of_a_parallelogram_are_supplementary",
        x_value=15,
        target_expression=_LinearExpression(4, 70),
        support_expression=_LinearExpression(2, 20),
    ),
    _Case(
        "parallelogram_consecutive_angle_expression",
        "parallelogram",
        105,
        "angle ABC",
        _LinearExpression(5, 55).display(degree=True),
        _LinearExpression(4, 35).display(degree=True),
        "consecutive_angles_of_a_parallelogram_are_supplementary",
        x_value=10,
        target_expression=_LinearExpression(5, 55),
        support_expression=_LinearExpression(4, 35),
    ),
    _Case(
        "rhombus_diagonal_half_angle_expression",
        "rhombus",
        42,
        "angle ABO",
        _LinearExpression(4, 2).display(degree=True),
        _LinearExpression(3, 12).display(degree=True),
        "rhombus_diagonal_bisects_vertex_angle",
        x_value=10,
        target_expression=_LinearExpression(4, 2),
        support_expression=_LinearExpression(3, 12),
    ),
    _Case(
        "rhombus_diagonal_half_angle_expression",
        "rhombus",
        50,
        "angle ABO",
        _LinearExpression(2, 28).display(degree=True),
        _LinearExpression(3, 17).display(degree=True),
        "rhombus_diagonal_bisects_vertex_angle",
        x_value=11,
        target_expression=_LinearExpression(2, 28),
        support_expression=_LinearExpression(3, 17),
    ),
    _Case(
        "rhombus_diagonal_half_angle_expression",
        "rhombus",
        35,
        "angle ABO",
        _LinearExpression(3, 20).display(degree=True),
        _LinearExpression(2, 25).display(degree=True),
        "rhombus_diagonal_bisects_vertex_angle",
        x_value=5,
        target_expression=_LinearExpression(3, 20),
        support_expression=_LinearExpression(2, 25),
    ),
    _Case(
        "rhombus_diagonal_half_angle_expression",
        "rhombus",
        45,
        "angle ABO",
        _LinearExpression(4, 13).display(degree=True),
        _LinearExpression(5, 5).display(degree=True),
        "rhombus_diagonal_bisects_vertex_angle",
        x_value=8,
        target_expression=_LinearExpression(4, 13),
        support_expression=_LinearExpression(5, 5),
    ),
    _Case(
        "rhombus_diagonal_half_angle_expression",
        "rhombus",
        60,
        "angle ABO",
        _LinearExpression(2, 40).display(degree=True),
        _LinearExpression(3, 30).display(degree=True),
        "rhombus_diagonal_bisects_vertex_angle",
        x_value=10,
        target_expression=_LinearExpression(2, 40),
        support_expression=_LinearExpression(3, 30),
    ),
    _Case(
        "kite_opposite_angle_expression",
        "kite",
        75,
        "angle ABC",
        _LinearExpression(2, 51).display(degree=True),
        _LinearExpression(3, 39).display(degree=True),
        "opposite_non_vertex_angles_of_this_kite_are_equal",
        x_value=12,
        target_expression=_LinearExpression(2, 51),
        support_expression=_LinearExpression(3, 39),
    ),
    _Case(
        "kite_opposite_angle_expression",
        "kite",
        90,
        "angle ABC",
        _LinearExpression(1, 68).display(degree=True),
        _LinearExpression(2, 46).display(degree=True),
        "opposite_non_vertex_angles_of_this_kite_are_equal",
        x_value=22,
        target_expression=_LinearExpression(1, 68),
        support_expression=_LinearExpression(2, 46),
    ),
    _Case(
        "kite_opposite_angle_expression",
        "kite",
        60,
        "angle ABC",
        _LinearExpression(2, 36).display(degree=True),
        _LinearExpression(1, 48).display(degree=True),
        "opposite_non_vertex_angles_of_this_kite_are_equal",
        x_value=12,
        target_expression=_LinearExpression(2, 36),
        support_expression=_LinearExpression(1, 48),
    ),
    _Case(
        "kite_opposite_angle_expression",
        "kite",
        80,
        "angle ABC",
        _LinearExpression(3, 38).display(degree=True),
        _LinearExpression(2, 52).display(degree=True),
        "opposite_non_vertex_angles_of_this_kite_are_equal",
        x_value=14,
        target_expression=_LinearExpression(3, 38),
        support_expression=_LinearExpression(2, 52),
    ),
    _Case(
        "kite_opposite_angle_expression",
        "kite",
        100,
        "angle ABC",
        _LinearExpression(2, 60).display(degree=True),
        _LinearExpression(3, 40).display(degree=True),
        "opposite_non_vertex_angles_of_this_kite_are_equal",
        x_value=20,
        target_expression=_LinearExpression(2, 60),
        support_expression=_LinearExpression(3, 40),
    ),
)

_SEGMENT_CASES: Tuple[_Case, ...] = (
    _Case(
        "parallelogram_opposite_side_expression",
        "parallelogram",
        17,
        "segment BC",
        _LinearExpression(3, -1).display(),
        _LinearExpression(2, 5).display(),
        "opposite_sides_of_a_parallelogram_are_equal",
        x_value=6,
        target_expression=_LinearExpression(3, -1),
        support_expression=_LinearExpression(2, 5),
    ),
    _Case(
        "parallelogram_opposite_side_expression",
        "parallelogram",
        24,
        "segment BC",
        _LinearExpression(2, 10).display(),
        _LinearExpression(3, 3).display(),
        "opposite_sides_of_a_parallelogram_are_equal",
        x_value=7,
        target_expression=_LinearExpression(2, 10),
        support_expression=_LinearExpression(3, 3),
    ),
    _Case(
        "parallelogram_opposite_side_expression",
        "parallelogram",
        20,
        "segment BC",
        _LinearExpression(2, 4).display(),
        _LinearExpression(1, 12).display(),
        "opposite_sides_of_a_parallelogram_are_equal",
        x_value=8,
        target_expression=_LinearExpression(2, 4),
        support_expression=_LinearExpression(1, 12),
    ),
    _Case(
        "parallelogram_opposite_side_expression",
        "parallelogram",
        28,
        "segment BC",
        _LinearExpression(3, 1).display(),
        _LinearExpression(2, 10).display(),
        "opposite_sides_of_a_parallelogram_are_equal",
        x_value=9,
        target_expression=_LinearExpression(3, 1),
        support_expression=_LinearExpression(2, 10),
    ),
    _Case(
        "parallelogram_opposite_side_expression",
        "parallelogram",
        32,
        "segment BC",
        _LinearExpression(2, 12).display(),
        _LinearExpression(3, 2).display(),
        "opposite_sides_of_a_parallelogram_are_equal",
        x_value=10,
        target_expression=_LinearExpression(2, 12),
        support_expression=_LinearExpression(3, 2),
    ),
    _Case(
        "rhombus_all_sides_expression",
        "rhombus",
        20,
        "segment CD",
        _LinearExpression(2, 4).display(),
        _LinearExpression(1, 12).display(),
        "all_sides_of_a_rhombus_are_equal",
        x_value=8,
        target_expression=_LinearExpression(2, 4),
        support_expression=_LinearExpression(1, 12),
    ),
    _Case(
        "rhombus_all_sides_expression",
        "rhombus",
        27,
        "segment CD",
        _LinearExpression(3, 6).display(),
        _LinearExpression(2, 13).display(),
        "all_sides_of_a_rhombus_are_equal",
        x_value=7,
        target_expression=_LinearExpression(3, 6),
        support_expression=_LinearExpression(2, 13),
    ),
    _Case(
        "rhombus_all_sides_expression",
        "rhombus",
        18,
        "segment CD",
        _LinearExpression(2, 8).display(),
        _LinearExpression(1, 13).display(),
        "all_sides_of_a_rhombus_are_equal",
        x_value=5,
        target_expression=_LinearExpression(2, 8),
        support_expression=_LinearExpression(1, 13),
    ),
    _Case(
        "rhombus_all_sides_expression",
        "rhombus",
        24,
        "segment CD",
        _LinearExpression(3, 3).display(),
        _LinearExpression(2, 10).display(),
        "all_sides_of_a_rhombus_are_equal",
        x_value=7,
        target_expression=_LinearExpression(3, 3),
        support_expression=_LinearExpression(2, 10),
    ),
    _Case(
        "rhombus_all_sides_expression",
        "rhombus",
        30,
        "segment CD",
        _LinearExpression(2, 12).display(),
        _LinearExpression(3, 3).display(),
        "all_sides_of_a_rhombus_are_equal",
        x_value=9,
        target_expression=_LinearExpression(2, 12),
        support_expression=_LinearExpression(3, 3),
    ),
    _Case(
        "kite_adjacent_equal_side_expression",
        "kite",
        18,
        "segment AD",
        _LinearExpression(2, 6).display(),
        _LinearExpression(1, 12).display(),
        "adjacent_marked_sides_of_a_kite_are_equal",
        x_value=6,
        target_expression=_LinearExpression(2, 6),
        support_expression=_LinearExpression(1, 12),
    ),
    _Case(
        "kite_adjacent_equal_side_expression",
        "kite",
        25,
        "segment AD",
        _LinearExpression(3, 1).display(),
        _LinearExpression(2, 9).display(),
        "adjacent_marked_sides_of_a_kite_are_equal",
        x_value=8,
        target_expression=_LinearExpression(3, 1),
        support_expression=_LinearExpression(2, 9),
    ),
    _Case(
        "kite_adjacent_equal_side_expression",
        "kite",
        20,
        "segment AD",
        _LinearExpression(2, 8).display(),
        _LinearExpression(3, 2).display(),
        "adjacent_marked_sides_of_a_kite_are_equal",
        x_value=6,
        target_expression=_LinearExpression(2, 8),
        support_expression=_LinearExpression(3, 2),
    ),
    _Case(
        "kite_adjacent_equal_side_expression",
        "kite",
        22,
        "segment AD",
        _LinearExpression(3, 1).display(),
        _LinearExpression(2, 8).display(),
        "adjacent_marked_sides_of_a_kite_are_equal",
        x_value=7,
        target_expression=_LinearExpression(3, 1),
        support_expression=_LinearExpression(2, 8),
    ),
    _Case(
        "kite_adjacent_equal_side_expression",
        "kite",
        28,
        "segment AD",
        _LinearExpression(2, 12).display(),
        _LinearExpression(3, 4).display(),
        "adjacent_marked_sides_of_a_kite_are_equal",
        x_value=8,
        target_expression=_LinearExpression(2, 12),
        support_expression=_LinearExpression(3, 4),
    ),
    _Case(
        "parallelogram_diagonal_bisection_expression",
        "parallelogram",
        23,
        "segment OC",
        _LinearExpression(2, 9).display(),
        _LinearExpression(3, 2).display(),
        "diagonals_of_a_parallelogram_bisect_each_other",
        x_value=7,
        target_expression=_LinearExpression(2, 9),
        support_expression=_LinearExpression(3, 2),
    ),
    _Case(
        "parallelogram_diagonal_bisection_expression",
        "parallelogram",
        32,
        "segment OC",
        _LinearExpression(3, 5).display(),
        _LinearExpression(2, 14).display(),
        "diagonals_of_a_parallelogram_bisect_each_other",
        x_value=9,
        target_expression=_LinearExpression(3, 5),
        support_expression=_LinearExpression(2, 14),
    ),
    _Case(
        "parallelogram_diagonal_bisection_expression",
        "parallelogram",
        18,
        "segment OC",
        _LinearExpression(2, 6).display(),
        _LinearExpression(3, 0).display(),
        "diagonals_of_a_parallelogram_bisect_each_other",
        x_value=6,
        target_expression=_LinearExpression(2, 6),
        support_expression=_LinearExpression(3, 0),
    ),
    _Case(
        "parallelogram_diagonal_bisection_expression",
        "parallelogram",
        26,
        "segment OC",
        _LinearExpression(3, 5).display(),
        _LinearExpression(2, 12).display(),
        "diagonals_of_a_parallelogram_bisect_each_other",
        x_value=7,
        target_expression=_LinearExpression(3, 5),
        support_expression=_LinearExpression(2, 12),
    ),
    _Case(
        "parallelogram_diagonal_bisection_expression",
        "parallelogram",
        30,
        "segment OC",
        _LinearExpression(2, 12).display(),
        _LinearExpression(3, 3).display(),
        "diagonals_of_a_parallelogram_bisect_each_other",
        x_value=9,
        target_expression=_LinearExpression(2, 12),
        support_expression=_LinearExpression(3, 3),
    ),
)



def cases_for_objective(objective_key: str) -> Tuple[_Case, ...]:
    if objective_key == DIAGONAL_OBJECTIVE:
        return _DIAGONAL_CASES
    if objective_key == ALGEBRAIC_OBJECTIVE:
        return _ALGEBRAIC_CASES
    if objective_key == SEGMENT_OBJECTIVE:
        return _SEGMENT_CASES
    raise ValueError(f"unknown special quadrilateral objective: {objective_key}")


def all_query_ids_for_objective(objective_key: str) -> Tuple[str, ...]:
    return tuple(sorted({case.query_id for case in cases_for_objective(objective_key)}))


def _offset_from_segment(a: Point, b: Point, distance: float) -> Point:
    ux, uy = _unit(_sub(b, a))
    return (-uy * float(distance), ux * float(distance))


def _draw_text_centered(ctx: _RenderContext, text: str, center: Point, *, small: bool = True) -> BBox:
    font = ctx.small_font if bool(small) else ctx.font
    draw_text_traced(
        ctx.draw,
        (float(center[0]), float(center[1])),
        str(text),
        anchor="mm",
        font=font,
        fill=ctx.label_color,
        stroke_width=max(0, int(ctx.label_stroke_width)),
        stroke_fill=ctx.label_stroke_color,
        role="readout",
        required=False,
    )
    bbox = ctx.draw.textbbox(
        (float(center[0]), float(center[1])),
        str(text),
        anchor="mm",
        font=font,
        stroke_width=max(0, int(ctx.label_stroke_width)),
    )
    return pad_bbox(bbox, 3.0, width=ctx.width, height=ctx.height)


def _draw_vertex_labels(ctx: _RenderContext, vertices: Mapping[str, Point]) -> Dict[str, BBox]:
    center = (
        sum(point[0] for point in vertices.values()) / float(len(vertices)),
        sum(point[1] for point in vertices.values()) / float(len(vertices)),
    )
    label_bboxes: Dict[str, BBox] = {}
    for label, point in vertices.items():
        direction = _unit(_sub(point, center))
        label_center = _add(point, direction, 26.0)
        label_bboxes[str(label)] = _draw_text_centered(ctx, str(label), label_center, small=True)
    return label_bboxes


def _draw_angle_marker(
    ctx: _RenderContext,
    *,
    vertex: Point,
    ray_a: Point,
    ray_b: Point,
    label: str,
    radius: float = 34.0,
) -> tuple[BBox, BBox, Point]:
    vector_a = _unit(_sub(ray_a, vertex))
    vector_b = _unit(_sub(ray_b, vertex))
    angle_a = math.atan2(vector_a[1], vector_a[0])
    angle_b = math.atan2(vector_b[1], vector_b[0])
    delta = ((angle_b - angle_a + math.pi) % (2.0 * math.pi)) - math.pi
    if abs(delta) > math.pi * 0.92:
        delta = -math.copysign((2.0 * math.pi) - abs(delta), delta)
    steps = max(8, int(abs(delta) / (math.pi / 20.0)))
    arc_points: list[Point] = []
    for step in range(steps + 1):
        theta = angle_a + delta * (float(step) / float(steps))
        arc_points.append((float(vertex[0]) + radius * math.cos(theta), float(vertex[1]) + radius * math.sin(theta)))
    ctx.draw.line(arc_points, fill=ctx.accent_color, width=max(2, int(ctx.line_width) - 1), joint="curve")
    bisector = _unit((vector_a[0] + vector_b[0], vector_a[1] + vector_b[1]))
    if math.hypot(bisector[0], bisector[1]) <= 1e-6:
        bisector = _unit(_sub((ctx.width / 2.0, ctx.height / 2.0), vertex))
    label_center = _add(vertex, bisector, radius + 24.0)
    label_bbox = _draw_text_centered(ctx, str(label), label_center, small=True)
    arc_bbox = bbox_from_points(arc_points, width=ctx.width, height=ctx.height, pad=4.0)
    annotation_point = _add(vertex, bisector, radius * 0.45)
    return arc_bbox, label_bbox, annotation_point


def _draw_segment_label(
    ctx: _RenderContext,
    *,
    a: Point,
    b: Point,
    text: str,
    offset: float,
) -> BBox:
    center = _mid(a, b)
    label_center = _add(center, _offset_from_segment(a, b, offset))
    return _draw_text_centered(ctx, str(text), label_center, small=True)


def _draw_tick(ctx: _RenderContext, a: Point, b: Point, *, offset: float = 0.0, count: int = 1) -> BBox:
    center = _mid(a, b)
    tangent = _unit(_sub(b, a))
    normal = (-tangent[1], tangent[0])
    tick_points: list[Point] = []
    spacing = 10.0
    for index in range(int(count)):
        shift = (float(index) - (float(count) - 1.0) / 2.0) * spacing
        tick_center = _add(_add(center, tangent, shift), normal, offset)
        p0 = _add(tick_center, normal, -9.0)
        p1 = _add(tick_center, normal, 9.0)
        ctx.draw.line((p0, p1), fill=ctx.accent_color, width=max(2, int(ctx.line_width) - 1))
        tick_points.extend([p0, p1])
    return bbox_from_points(tick_points, width=ctx.width, height=ctx.height, pad=3.0)


def _draw_right_angle_marker(
    ctx: _RenderContext,
    center: Point,
    *,
    size: float = 18.0,
    ray_a: Point | None = None,
    ray_b: Point | None = None,
) -> BBox:
    x, y = float(center[0]), float(center[1])
    if ray_a is None or ray_b is None:
        points = [(x, y - size), (x + size, y - size), (x + size, y)]
    else:
        u = _unit(_sub(ray_a, center))
        v = _unit(_sub(ray_b, center))
        p1 = _add(center, u, size)
        p2 = _add(p1, v, size)
        p3 = _add(center, v, size)
        points = [p1, p2, p3]
    ctx.draw.line(points, fill=ctx.accent_color, width=max(2, int(ctx.line_width) - 1))
    return bbox_from_points(points, width=ctx.width, height=ctx.height, pad=3.0)


def _base_vertices(shape_kind: str, *, width: int, height: int, instance_seed: int) -> Dict[str, Point]:
    rng = spawn_rng(int(instance_seed), f"{SCENE_ID}.{shape_kind}.layout")
    jitter_x = rng.uniform(-24.0, 24.0)
    jitter_y = rng.uniform(-18.0, 18.0)
    scale = rng.uniform(0.92, 1.06)
    center = (float(width) / 2.0 + jitter_x, float(height) / 2.0 + jitter_y)

    if shape_kind == "rhombus":
        offsets = {
            "A": (0.0, -150.0),
            "B": (190.0, 0.0),
            "C": (0.0, 150.0),
            "D": (-190.0, 0.0),
        }
    elif shape_kind == "kite":
        offsets = {
            "A": (0.0, -170.0),
            "B": (180.0, 0.0),
            "C": (0.0, 160.0),
            "D": (-145.0, 0.0),
        }
    elif shape_kind == "parallelogram":
        offsets = {
            "A": (-190.0, 105.0),
            "B": (170.0, 105.0),
            "C": (245.0, -105.0),
            "D": (-115.0, -105.0),
        }
    else:
        raise ValueError(f"unknown special quadrilateral shape: {shape_kind}")

    return {label: (center[0] + dx * scale, center[1] + dy * scale) for label, (dx, dy) in offsets.items()}


def _transformed_base_vertices(ctx: _RenderContext, shape_kind: str, *, instance_seed: int) -> Dict[str, Point]:
    vertices = _base_vertices(shape_kind, width=ctx.width, height=ctx.height, instance_seed=instance_seed)
    ctx.scene_transform.resolve(tuple(vertices.values()))
    return ctx.scene_transform.keyed_points(vertices)


def _draw_base_shape(ctx: _RenderContext, vertices: Mapping[str, Point], *, shape_kind: str) -> Dict[str, BBox]:
    polygon = [vertices[label] for label in ("A", "B", "C", "D")]
    ctx.draw.polygon(polygon, fill=ctx.fill_color)
    ctx.draw.line(polygon + [polygon[0]], fill=ctx.line_color, width=ctx.line_width, joint="curve")
    bboxes: Dict[str, BBox] = {
        "outline": bbox_from_points(polygon, width=ctx.width, height=ctx.height, pad=ctx.line_width + 2)
    }
    if shape_kind == "rhombus":
        bboxes["tick_AB"] = _draw_tick(ctx, vertices["A"], vertices["B"], count=1)
        bboxes["tick_BC"] = _draw_tick(ctx, vertices["B"], vertices["C"], count=1)
        bboxes["tick_CD"] = _draw_tick(ctx, vertices["C"], vertices["D"], count=1)
        bboxes["tick_DA"] = _draw_tick(ctx, vertices["D"], vertices["A"], count=1)
    elif shape_kind == "kite":
        bboxes["tick_AB"] = _draw_tick(ctx, vertices["A"], vertices["B"], count=1)
        bboxes["tick_AD"] = _draw_tick(ctx, vertices["A"], vertices["D"], count=1)
        bboxes["tick_BC"] = _draw_tick(ctx, vertices["B"], vertices["C"], count=2)
        bboxes["tick_CD"] = _draw_tick(ctx, vertices["C"], vertices["D"], count=2)
    else:
        bboxes["tick_AB"] = _draw_tick(ctx, vertices["A"], vertices["B"], count=1)
        bboxes["tick_CD"] = _draw_tick(ctx, vertices["C"], vertices["D"], count=1)
        bboxes["tick_BC"] = _draw_tick(ctx, vertices["B"], vertices["C"], count=2)
        bboxes["tick_DA"] = _draw_tick(ctx, vertices["D"], vertices["A"], count=2)
    return bboxes


def _draw_diagonal_case(ctx: _RenderContext, problem: _ResolvedProblem) -> _RenderedScene:
    vertices = _transformed_base_vertices(ctx, problem.case.shape_kind, instance_seed=problem.layout_seed)
    construction_bboxes = _draw_base_shape(ctx, vertices, shape_kind=problem.case.shape_kind)
    readout_bboxes: Dict[str, BBox] = {}
    extra_annotation_points: Dict[str, Point] = {}

    if problem.case.query_id == "rhombus_vertex_angle_bisected_by_diagonal":
        ctx.draw.line((vertices["B"], vertices["D"]), fill=ctx.secondary_color, width=max(2, ctx.line_width - 1))
        o = _mid(vertices["B"], vertices["D"])
        construction_bboxes["diagonal_BD"] = bbox_from_points((vertices["B"], vertices["D"]), width=ctx.width, height=ctx.height, pad=4.0)
        readout_bboxes["point_label_O"] = _draw_text_centered(ctx, "O", _add(o, (0.0, 22.0)), small=True)
        _, readout_bboxes["support_angle_label"], _ = _draw_angle_marker(
            ctx, vertex=vertices["B"], ray_a=vertices["A"], ray_b=o, label=problem.case.support_label
        )
        _, readout_bboxes["target_angle_label"], _ = _draw_angle_marker(
            ctx, vertex=vertices["D"], ray_a=o, ray_b=vertices["A"], label="?"
        )
        extra_annotation_points["O"] = o
    elif problem.case.query_id == "kite_vertex_angle_bisected_by_symmetry_diagonal":
        ctx.draw.line((vertices["A"], vertices["C"]), fill=ctx.secondary_color, width=max(2, ctx.line_width - 1))
        construction_bboxes["symmetry_diagonal_AC"] = bbox_from_points(
            (vertices["A"], vertices["C"]), width=ctx.width, height=ctx.height, pad=4.0
        )
        _, readout_bboxes["support_angle_label"], _ = _draw_angle_marker(
            ctx, vertex=vertices["A"], ray_a=vertices["D"], ray_b=vertices["C"], label=problem.case.support_label
        )
        _, readout_bboxes["target_angle_label"], _ = _draw_angle_marker(
            ctx, vertex=vertices["A"], ray_a=vertices["C"], ray_b=vertices["B"], label="?"
        )
    else:
        ctx.draw.line((vertices["A"], vertices["C"]), fill=ctx.secondary_color, width=max(2, ctx.line_width - 1))
        ctx.draw.line((vertices["B"], vertices["D"]), fill=ctx.secondary_color, width=max(2, ctx.line_width - 1))
        o = _mid(vertices["A"], vertices["C"])
        construction_bboxes["diagonal_AC"] = bbox_from_points((vertices["A"], vertices["C"]), width=ctx.width, height=ctx.height, pad=4.0)
        construction_bboxes["diagonal_BD"] = bbox_from_points((vertices["B"], vertices["D"]), width=ctx.width, height=ctx.height, pad=4.0)
        construction_bboxes["right_angle"] = _draw_right_angle_marker(ctx, o, ray_a=vertices["A"], ray_b=vertices["B"])
        readout_bboxes["point_label_O"] = _draw_text_centered(ctx, "O", _add(o, (0.0, 22.0)), small=True)
        _, readout_bboxes["support_angle_label"], _ = _draw_angle_marker(
            ctx, vertex=vertices["A"], ray_a=vertices["B"], ray_b=vertices["C"], label=problem.case.support_label
        )
        _, readout_bboxes["target_angle_label"], _ = _draw_angle_marker(
            ctx, vertex=vertices["B"], ray_a=vertices["A"], ray_b=vertices["D"], label="?"
        )
        extra_annotation_points["O"] = o

    point_label_bboxes = _draw_vertex_labels(ctx, vertices)
    annotation = {**dict(vertices), **extra_annotation_points}
    render_map = {
        "vertices": {key: _point_to_list(point) for key, point in vertices.items()},
        "readout_bboxes": _json_ready(readout_bboxes),
        "construction_bboxes": _json_ready(construction_bboxes),
        "point_label_bboxes": _json_ready(point_label_bboxes),
    }
    return _RenderedScene(ctx.image, dict(vertices), dict(annotation), point_label_bboxes, readout_bboxes, construction_bboxes, render_map)


def _draw_algebraic_case(ctx: _RenderContext, problem: _ResolvedProblem) -> _RenderedScene:
    vertices = _transformed_base_vertices(ctx, problem.case.shape_kind, instance_seed=problem.layout_seed)
    construction_bboxes = _draw_base_shape(ctx, vertices, shape_kind=problem.case.shape_kind)
    readout_bboxes: Dict[str, BBox] = {}
    extra_annotation_points: Dict[str, Point] = {}

    if problem.case.query_id == "parallelogram_opposite_angle_expression":
        _, readout_bboxes["support_angle_label"], _ = _draw_angle_marker(
            ctx, vertex=vertices["A"], ray_a=vertices["B"], ray_b=vertices["D"], label=problem.case.support_label
        )
        _, readout_bboxes["target_angle_label"], _ = _draw_angle_marker(
            ctx, vertex=vertices["C"], ray_a=vertices["D"], ray_b=vertices["B"], label=problem.case.target_label
        )
    elif problem.case.query_id == "parallelogram_consecutive_angle_expression":
        _, readout_bboxes["support_angle_label"], _ = _draw_angle_marker(
            ctx, vertex=vertices["A"], ray_a=vertices["B"], ray_b=vertices["D"], label=problem.case.support_label
        )
        _, readout_bboxes["target_angle_label"], _ = _draw_angle_marker(
            ctx, vertex=vertices["B"], ray_a=vertices["C"], ray_b=vertices["A"], label=problem.case.target_label
        )
    elif problem.case.query_id == "rhombus_diagonal_half_angle_expression":
        ctx.draw.line((vertices["B"], vertices["D"]), fill=ctx.secondary_color, width=max(2, ctx.line_width - 1))
        o = _mid(vertices["B"], vertices["D"])
        construction_bboxes["diagonal_BD"] = bbox_from_points((vertices["B"], vertices["D"]), width=ctx.width, height=ctx.height, pad=4.0)
        readout_bboxes["point_label_O"] = _draw_text_centered(ctx, "O", _add(o, (0.0, 22.0)), small=True)
        _, readout_bboxes["support_angle_label"], _ = _draw_angle_marker(
            ctx, vertex=vertices["B"], ray_a=vertices["A"], ray_b=o, label=problem.case.support_label
        )
        _, readout_bboxes["target_angle_label"], _ = _draw_angle_marker(
            ctx, vertex=vertices["B"], ray_a=o, ray_b=vertices["C"], label=problem.case.target_label
        )
        extra_annotation_points["O"] = o
    else:
        _, readout_bboxes["target_angle_label"], _ = _draw_angle_marker(
            ctx, vertex=vertices["B"], ray_a=vertices["A"], ray_b=vertices["C"], label=problem.case.target_label
        )
        _, readout_bboxes["support_angle_label"], _ = _draw_angle_marker(
            ctx, vertex=vertices["D"], ray_a=vertices["C"], ray_b=vertices["A"], label=problem.case.support_label
        )

    point_label_bboxes = _draw_vertex_labels(ctx, vertices)
    annotation = {**dict(vertices), **extra_annotation_points}
    render_map = {
        "vertices": {key: _point_to_list(point) for key, point in vertices.items()},
        "readout_bboxes": _json_ready(readout_bboxes),
        "construction_bboxes": _json_ready(construction_bboxes),
        "point_label_bboxes": _json_ready(point_label_bboxes),
    }
    return _RenderedScene(ctx.image, dict(vertices), dict(annotation), point_label_bboxes, readout_bboxes, construction_bboxes, render_map)


def _draw_segment_case(ctx: _RenderContext, problem: _ResolvedProblem) -> _RenderedScene:
    vertices = _transformed_base_vertices(ctx, problem.case.shape_kind, instance_seed=problem.layout_seed)
    construction_bboxes = _draw_base_shape(ctx, vertices, shape_kind=problem.case.shape_kind)
    readout_bboxes: Dict[str, BBox] = {}
    extra_annotation_points: Dict[str, Point] = {}

    if problem.case.query_id == "parallelogram_opposite_side_expression":
        readout_bboxes["support_segment_label"] = _draw_segment_label(
            ctx, a=vertices["D"], b=vertices["A"], text=problem.case.support_label, offset=-34.0
        )
        readout_bboxes["target_segment_label"] = _draw_segment_label(
            ctx, a=vertices["B"], b=vertices["C"], text=problem.case.target_label, offset=34.0
        )
    elif problem.case.query_id == "rhombus_all_sides_expression":
        readout_bboxes["support_segment_label"] = _draw_segment_label(
            ctx, a=vertices["A"], b=vertices["B"], text=problem.case.support_label, offset=-34.0
        )
        readout_bboxes["target_segment_label"] = _draw_segment_label(
            ctx, a=vertices["C"], b=vertices["D"], text=problem.case.target_label, offset=34.0
        )
    elif problem.case.query_id == "kite_adjacent_equal_side_expression":
        readout_bboxes["support_segment_label"] = _draw_segment_label(
            ctx, a=vertices["A"], b=vertices["B"], text=problem.case.support_label, offset=-34.0
        )
        readout_bboxes["target_segment_label"] = _draw_segment_label(
            ctx, a=vertices["A"], b=vertices["D"], text=problem.case.target_label, offset=34.0
        )
    else:
        ctx.draw.line((vertices["A"], vertices["C"]), fill=ctx.secondary_color, width=max(2, ctx.line_width - 1))
        o = _mid(vertices["A"], vertices["C"])
        construction_bboxes["diagonal_AC"] = bbox_from_points((vertices["A"], vertices["C"]), width=ctx.width, height=ctx.height, pad=4.0)
        point_radius = max(3, int(ctx.line_width))
        ctx.draw.ellipse((o[0] - point_radius, o[1] - point_radius, o[0] + point_radius, o[1] + point_radius), fill=ctx.accent_color)
        readout_bboxes["support_segment_label"] = _draw_segment_label(
            ctx, a=vertices["A"], b=o, text=problem.case.support_label, offset=-30.0
        )
        readout_bboxes["target_segment_label"] = _draw_segment_label(
            ctx, a=o, b=vertices["C"], text=problem.case.target_label, offset=30.0
        )
        readout_bboxes["intersection_label"] = _draw_text_centered(ctx, "O", _add(o, (0.0, 24.0)), small=True)
        extra_annotation_points["O"] = o

    point_label_bboxes = _draw_vertex_labels(ctx, vertices)
    annotation = {**dict(vertices), **extra_annotation_points}
    render_map = {
        "vertices": {key: _point_to_list(point) for key, point in vertices.items()},
        "readout_bboxes": _json_ready(readout_bboxes),
        "construction_bboxes": _json_ready(construction_bboxes),
        "point_label_bboxes": _json_ready(point_label_bboxes),
    }
    return _RenderedScene(ctx.image, dict(vertices), dict(annotation), point_label_bboxes, readout_bboxes, construction_bboxes, render_map)


def _select_problem(
    *,
    objective_key: str,
    query_id: str,
    query_probabilities: Mapping[str, float],
    instance_seed: int,
    runtime_namespace: str,
) -> _ResolvedProblem:
    cases = tuple(case for case in cases_for_objective(objective_key) if case.query_id == str(query_id))
    if not cases:
        raise ValueError(f"no special quadrilateral cases for objective={objective_key!r}, query={query_id!r}")
    case_rng = spawn_rng(int(instance_seed), f"{runtime_namespace}.{query_id}.case")
    case_index = int(case_rng.randrange(len(cases)))
    return _ResolvedProblem(
        objective_key=str(objective_key),
        query_id=str(query_id),
        case=cases[case_index],
        query_probabilities={str(key): float(value) for key, value in query_probabilities.items()},
        case_index=int(case_index),
        layout_seed=int(instance_seed),
    )


def _build_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
) -> _RenderContext:
    width = int(params.get("canvas_width", rendering_defaults.get("canvas_width", 760)))
    height = int(params.get("canvas_height", rendering_defaults.get("canvas_height", 560)))
    background, background_meta, diagram_style, diagram_style_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        canvas_width=width,
        canvas_height=height,
        allow_dark=False,
        require_grid=False,
    )
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    line_width = int(params.get("line_width", rendering_defaults.get("line_width", 3)))
    font_size = int(params.get("label_font_size", rendering_defaults.get("label_font_size", 22)))
    small_font_size = int(params.get("small_label_font_size", rendering_defaults.get("small_label_font_size", 18)))
    return _RenderContext(
        image=image,
        draw=draw,
        width=width,
        height=height,
        line_color=tuple(int(value) for value in diagram_style.stroke_rgb),
        secondary_color=tuple(int(value) for value in diagram_style.secondary_stroke_rgb),
        label_color=tuple(int(value) for value in diagram_style.label_rgb),
        label_stroke_color=tuple(int(value) for value in diagram_style.label_stroke_rgb),
        accent_color=tuple(int(value) for value in diagram_style.accent_rgb),
        muted_color=tuple(int(value) for value in diagram_style.grid_major_rgb),
        fill_color=tuple(int(value) for value in diagram_style.panel_alt_fill_rgb),
        line_width=max(2, line_width),
        label_stroke_width=max(1, int(diagram_style.label_stroke_width_px)),
        font=load_font(font_size),
        small_font=load_font(small_font_size),
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


def _render_problem(problem: _ResolvedProblem, ctx: _RenderContext) -> _RenderedScene:
    if problem.objective_key == DIAGONAL_OBJECTIVE:
        return _draw_diagonal_case(ctx, problem)
    if problem.objective_key == ALGEBRAIC_OBJECTIVE:
        return _draw_algebraic_case(ctx, problem)
    if problem.objective_key == SEGMENT_OBJECTIVE:
        return _draw_segment_case(ctx, problem)
    raise ValueError(f"unknown special quadrilateral objective: {problem.objective_key}")


def _make_prompt_examples(annotation_keys: Sequence[str], *, answer: int) -> tuple[str, str]:
    return build_keyed_point_prompt_json_examples(annotation_keys=annotation_keys, answer=int(answer))


def _answer_hint_for_objective(objective_key: str, prompt_defaults: Mapping[str, Any]) -> str:
    if objective_key == SEGMENT_OBJECTIVE:
        return str(prompt_defaults["answer_hint_integer_length"])
    return str(prompt_defaults["answer_hint_integer_angle"])


class SpecialQuadrilateralRuntime:
    """Scene-local renderer/runtime for special-quadrilateral diagrams."""

    domain = "geometry"

    def generate_artifact(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        max_attempts: int,
        runtime_namespace: str,
        objective_key: str,
        task_prompt_key: str,
        query_id: str,
        query_id_probabilities: Mapping[str, float],
    ) -> SpecialQuadrilateralArtifact:
        _generation_defaults, rendering_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
            _SCENE_DEFAULTS,
            task_id=str(runtime_namespace),
        )
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                attempt_seed = int(instance_seed) + int(attempt)
                problem = _select_problem(
                    objective_key=str(objective_key),
                    query_id=str(query_id),
                    query_probabilities=query_id_probabilities,
                    instance_seed=attempt_seed,
                    runtime_namespace=str(runtime_namespace),
                )
                ctx = _build_context(
                    instance_seed=attempt_seed,
                    params=params,
                    rendering_defaults=rendering_defaults,
                )
                rendered = _render_problem(problem, ctx)
                break
            except Exception as exc:
                last_error = exc
                continue
        else:
            raise RuntimeError(f"failed to generate special quadrilateral artifact for {runtime_namespace}") from last_error

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
                "object_description",
                "json_output_contract",
                "json_output_contract_answer_only",
                "annotation_hint",
                "answer_hint_integer_angle",
                "answer_hint_integer_length",
            ),
            context=f"prompt defaults for {runtime_namespace}",
        )
        annotation_keys = tuple(rendered.annotation_points.keys())
        json_example, json_example_answer_only = _make_prompt_examples(annotation_keys, answer=int(problem.case.answer))
        annotation_key_list = ", ".join(f'"{key}"' for key in annotation_keys)
        annotation_hint = str(prompt_defaults["annotation_hint"]).format(annotation_keys=annotation_key_list)
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(task_prompt_key),
            query_key=str(problem.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "target_name": str(problem.case.target_name),
                "shape_kind": str(problem.case.shape_kind),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(annotation_hint),
                "answer_hint": _answer_hint_for_objective(str(objective_key), prompt_defaults),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        annotation_value = {key: _point_to_list(point) for key, point in rendered.annotation_points.items()}
        vertices_payload = {key: _point_to_list(point) for key, point in rendered.vertices.items()}
        expression_payload: Dict[str, Any] = {}
        if problem.case.target_expression is not None and problem.case.support_expression is not None:
            expression_payload = {
                "x_value": int(problem.case.x_value or 0),
                "target_expression": {
                    "coefficient": int(problem.case.target_expression.coefficient),
                    "constant": int(problem.case.target_expression.constant),
                    "value": int(problem.case.target_expression.evaluate(int(problem.case.x_value or 0))),
                    "display": str(problem.case.target_label),
                },
                "support_expression": {
                    "coefficient": int(problem.case.support_expression.coefficient),
                    "constant": int(problem.case.support_expression.constant),
                    "value": int(problem.case.support_expression.evaluate(int(problem.case.x_value or 0))),
                    "display": str(problem.case.support_label),
                },
            }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "task_id": str(runtime_namespace),
                "query_id": str(problem.query_id),
                "entities": [
                    {
                        "type": str(problem.case.shape_kind),
                        "labels": ["A", "B", "C", "D"],
                        "vertices": dict(vertices_payload),
                    },
                ],
                "relations": {
                    "theorem": str(problem.case.theorem),
                    "query_id": str(problem.query_id),
                },
            },
            "query_spec": {
                "task_id": str(runtime_namespace),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "params": {
                    "query_id": str(problem.query_id),
                    "query_id_probabilities": dict(problem.query_probabilities),
                    "case_index": int(problem.case_index),
                },
            },
            "render_spec": {
                "task_id": str(runtime_namespace),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "canvas": {"width": int(ctx.width), "height": int(ctx.height)},
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
                "task_id": str(runtime_namespace),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "shape_kind": str(problem.case.shape_kind),
                "target_name": str(problem.case.target_name),
                "target_label": str(problem.case.target_label),
                "support_label": str(problem.case.support_label),
                "theorem": str(problem.case.theorem),
                "answer": int(problem.case.answer),
                "annotation_roles": list(annotation_keys),
                **dict(expression_payload),
            },
            "witness_symbolic": {
                "task_id": str(runtime_namespace),
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "target_name": str(problem.case.target_name),
                "theorem": str(problem.case.theorem),
                "answer": int(problem.case.answer),
                **dict(expression_payload),
            },
            "projected_annotation": {
                "type": "keyed_point_map",
                "keyed_point_map": dict(annotation_value),
                "pixel_keyed_point_map": dict(annotation_value),
            },
        }
        return SpecialQuadrilateralArtifact(
            prompt=str(prompt_artifacts.prompt),
            answer_type="integer",
            answer_value=int(problem.case.answer),
            annotation_type="keyed_point_map",
            annotation_value=dict(annotation_value),
            image=image,
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            query_id=str(problem.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = [
    "ALGEBRAIC_OBJECTIVE",
    "DIAGONAL_OBJECTIVE",
    "SCENE_ID",
    "SEGMENT_OBJECTIVE",
    "SpecialQuadrilateralArtifact",
    "SpecialQuadrilateralRuntime",
]
