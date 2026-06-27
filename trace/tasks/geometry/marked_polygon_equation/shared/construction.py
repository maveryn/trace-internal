"""Algebraic construction families for marked polygon equation tasks."""

from __future__ import annotations

from typing import Callable, Tuple

from .state import MarkedEquationCase

DEGREE_SYMBOL = chr(176)
Builder = Callable[[int], MarkedEquationCase]


def _variant(variant_index: int, *, modulo: int = 29) -> int:
    return int(variant_index) % int(modulo)


def _linear_label(coefficient: int, variable_name: str, offset: int) -> str:
    if int(offset) == 0:
        return f"{int(coefficient)}{variable_name}"
    sign = "+" if int(offset) > 0 else "-"
    return f"{int(coefficient)}{variable_name}{sign}{abs(int(offset))}"


def _angle_label(coefficient: int, variable_name: str, offset: int) -> str:
    return f"({_linear_label(int(coefficient), str(variable_name), int(offset))}){DEGREE_SYMBOL}"


def _degree_label(value: int) -> str:
    return f"{int(value)}{DEGREE_SYMBOL}"


def _side_distractors(index: int, *, variable_name: str = "y") -> dict[str, str]:
    return {
        "side_bc": str(9 + (index * 3) % 23),
        "side_cd": _linear_label(1 + (index % 2), variable_name, 4 + (index * 5) % 17),
    }


def _triangle_angle_distractors(index: int) -> dict[str, str]:
    return {
        "angle_A": _degree_label(35 + (index * 7) % 72),
        "angle_C": _angle_label(1 + (index % 2), "y", 18 + (index * 5) % 24),
    }


def _quadrilateral_angle_distractors(index: int) -> dict[str, str]:
    return {
        "angle_B": _degree_label(58 + (index * 5) % 74),
        "angle_D": _angle_label(1 + (index % 3), "y", 24 + (index * 7) % 31),
    }


def _triangle_apex_angle_distractor(index: int) -> dict[str, str]:
    return {"angle_A": _degree_label(42 + (index * 7) % 70)}


def isosceles_equal_side_variable(variant_index: int) -> MarkedEquationCase:
    index = _variant(variant_index)
    answer = 4 + index
    coefficient = 2 + (index % 3)
    offset = 1 + ((index * 2) % 11)
    return MarkedEquationCase(
        construction_family="isosceles_triangle_equal_side_variable",
        draw_kind="triangle_equal_sides",
        answer=answer,
        target_name="x",
        variable_name="x",
        shape_kind="triangle",
        relation="isosceles_equal_sides_expression",
        formula_schema="equal_side_expression_variable",
        labels={
            "left_side": _linear_label(coefficient, "x", offset),
            "right_side": str(coefficient * answer + offset),
        },
        distractor_labels=_triangle_angle_distractors(index),
    )


def equilateral_equal_side_variable(variant_index: int) -> MarkedEquationCase:
    index = _variant(variant_index)
    answer = 3 + index
    coefficient = 2 + (index % 4)
    offset = 2 + ((index * 3) % 9)
    side_value = coefficient * answer + offset
    return MarkedEquationCase(
        construction_family="equilateral_triangle_equal_side_variable",
        draw_kind="equilateral_sides",
        answer=answer,
        target_name="x",
        variable_name="x",
        shape_kind="triangle",
        relation="equilateral_equal_sides_expression",
        formula_schema="equal_side_expression_variable",
        labels={
            "left_side": _linear_label(coefficient, "x", offset),
            "right_side": str(side_value),
            "base_side": str(side_value),
        },
        distractor_labels=_triangle_angle_distractors(index),
    )


def marked_polygon_equal_side_variable(variant_index: int) -> MarkedEquationCase:
    index = _variant(variant_index)
    answer = 5 + index
    coefficient = 2 + (index % 3)
    offset = 3 + ((index * 5) % 13)
    return MarkedEquationCase(
        construction_family="marked_polygon_equal_side_variable",
        draw_kind="polygon_equal_sides",
        answer=answer,
        target_name="x",
        variable_name="x",
        shape_kind="quadrilateral",
        relation="marked_polygon_equal_sides_expression",
        formula_schema="equal_side_expression_variable",
        labels={
            "left_side": _linear_label(coefficient, "x", offset),
            "right_side": _linear_label(coefficient - 1, "x", offset + answer),
        },
        distractor_labels=_quadrilateral_angle_distractors(index),
    )


def isosceles_altitude_base_split_variable(variant_index: int) -> MarkedEquationCase:
    index = _variant(variant_index)
    answer = 4 + index
    coefficient = 2 + (index % 3)
    offset = 2 + ((index * 3) % 10)
    return MarkedEquationCase(
        construction_family="isosceles_altitude_base_split_variable",
        draw_kind="isosceles_altitude_base_split",
        answer=answer,
        target_name="x",
        variable_name="x",
        shape_kind="triangle",
        relation="isosceles_altitude_base_split_expression",
        formula_schema="equal_segment_expression_variable",
        labels={
            "left_base": _linear_label(coefficient, "x", offset),
            "right_base": str(coefficient * answer + offset),
        },
        distractor_labels={"angle_A": _degree_label(44 + (index * 7) % 62)},
    )


def marked_equal_angles_variable(variant_index: int) -> MarkedEquationCase:
    index = _variant(variant_index)
    answer = 6 + index
    coefficient = 2 + (index % 3)
    offset = 18 + ((index * 4) % 17)
    return MarkedEquationCase(
        construction_family="marked_equal_angles_variable",
        draw_kind="polygon_equal_angles",
        answer=answer,
        target_name="x",
        variable_name="x",
        shape_kind="quadrilateral",
        relation="marked_equal_angles_expression",
        formula_schema="equal_angle_expression_variable",
        labels={
            "angle_a": _angle_label(coefficient, "x", offset),
            "angle_b": _angle_label(coefficient - 1, "x", offset + answer),
        },
        distractor_labels={**_side_distractors(index), **_quadrilateral_angle_distractors(index)},
    )


def isosceles_base_angle_variable(variant_index: int) -> MarkedEquationCase:
    index = _variant(variant_index)
    answer = 5 + index
    coefficient = 2 + (index % 3)
    offset = 15 + ((index * 5) % 19)
    return MarkedEquationCase(
        construction_family="isosceles_triangle_base_angle_variable",
        draw_kind="isosceles_base_angles",
        answer=answer,
        target_name="x",
        variable_name="x",
        shape_kind="triangle",
        relation="isosceles_base_angles_expression",
        formula_schema="equal_angle_expression_variable",
        labels={
            "angle_a": _angle_label(coefficient, "x", offset),
            "angle_b": _angle_label(coefficient - 1, "x", offset + answer),
        },
        distractor_labels={
            "side_bc": str(10 + (index * 5) % 28),
            **_triangle_apex_angle_distractor(index),
        },
    )


def equilateral_median_right_angle_variable(variant_index: int) -> MarkedEquationCase:
    index = _variant(variant_index, modulo=23)
    answer = 4 + index
    coefficient = 2 + (index % 3)
    offset = 90 - coefficient * answer
    return MarkedEquationCase(
        construction_family="equilateral_median_right_angle_variable",
        draw_kind="equilateral_median_right_angle",
        answer=answer,
        target_name="y",
        variable_name="y",
        shape_kind="triangle",
        relation="equilateral_median_perpendicular_expression",
        formula_schema="right_angle_expression_variable",
        labels={"right_angle_expression": _angle_label(coefficient, "y", offset)},
        distractor_labels={"side_ab": str(12 + (index * 4) % 24), "angle_A": _degree_label(60)},
    )


def isosceles_side_from_expression(variant_index: int) -> MarkedEquationCase:
    index = _variant(variant_index)
    answer = 12 + index
    coefficient = 2 + (index % 3)
    offset = 2 + ((index * 2) % 9)
    return MarkedEquationCase(
        construction_family="isosceles_triangle_side_from_expression",
        draw_kind="triangle_equal_sides",
        answer=answer,
        target_name="AB",
        variable_name="x",
        shape_kind="triangle",
        relation="isosceles_side_length_from_expression",
        formula_schema="equal_side_expression_length",
        labels={
            "left_side": _linear_label(coefficient, "x", offset),
            "right_side": str(answer),
        },
        distractor_labels=_triangle_angle_distractors(index),
    )


def equilateral_side_from_expression(variant_index: int) -> MarkedEquationCase:
    index = _variant(variant_index)
    answer = 15 + index
    coefficient = 2 + (index % 4)
    offset = 1 + ((index * 3) % 10)
    return MarkedEquationCase(
        construction_family="equilateral_triangle_side_from_expression",
        draw_kind="equilateral_sides",
        answer=answer,
        target_name="AB",
        variable_name="x",
        shape_kind="triangle",
        relation="equilateral_side_length_from_expression",
        formula_schema="equal_side_expression_length",
        labels={
            "left_side": _linear_label(coefficient, "x", offset),
            "right_side": str(answer),
            "base_side": str(answer),
        },
        distractor_labels=_triangle_angle_distractors(index),
    )


def marked_polygon_side_from_expression(variant_index: int) -> MarkedEquationCase:
    index = _variant(variant_index)
    answer = 18 + index
    coefficient = 2 + (index % 3)
    offset = 2 + ((index * 5) % 12)
    return MarkedEquationCase(
        construction_family="marked_polygon_side_from_expression",
        draw_kind="polygon_equal_sides",
        answer=answer,
        target_name="AB",
        variable_name="x",
        shape_kind="quadrilateral",
        relation="marked_polygon_side_length_from_expression",
        formula_schema="equal_side_expression_length",
        labels={
            "left_side": _linear_label(coefficient, "x", offset),
            "right_side": str(answer),
        },
        distractor_labels=_quadrilateral_angle_distractors(index),
    )


def equilateral_median_side_length_from_expression(variant_index: int) -> MarkedEquationCase:
    index = _variant(variant_index)
    x_value = 3 + index
    answer = 3 * x_value + 1
    return MarkedEquationCase(
        construction_family="equilateral_median_side_length_from_expression",
        draw_kind="equilateral_median_sides",
        answer=answer,
        target_name="each side",
        variable_name="x",
        shape_kind="triangle",
        relation="equilateral_median_side_length_from_expression",
        formula_schema="equal_side_expression_length",
        labels={
            "left_side": "3x+1",
            "right_side": _linear_label(4, "x", 1 - x_value),
            "base_side": "?",
        },
        distractor_labels={"angle_A": _degree_label(60), "angle_B": _degree_label(60)},
    )


def marked_equal_angle_from_expression(variant_index: int) -> MarkedEquationCase:
    index = _variant(variant_index, modulo=18)
    answer = 42 + 4 * index
    x_value = 5 + (index % 11)
    coefficient = 2 + (index % 3)
    offset = answer - coefficient * x_value
    return MarkedEquationCase(
        construction_family="marked_equal_angle_from_expression",
        draw_kind="polygon_equal_angles",
        answer=answer,
        target_name="angle A",
        variable_name="x",
        shape_kind="quadrilateral",
        relation="marked_equal_angle_measure_from_expression",
        formula_schema="equal_angle_expression_measure",
        labels={
            "angle_a": _angle_label(coefficient, "x", offset),
            "angle_b": _angle_label(1, "x", answer - x_value),
        },
        distractor_labels={**_side_distractors(index), **_quadrilateral_angle_distractors(index)},
    )


def isosceles_angle_from_expression(variant_index: int) -> MarkedEquationCase:
    index = _variant(variant_index, modulo=18)
    answer = 40 + 4 * index
    x_value = 4 + (index % 12)
    coefficient = 2 + (index % 3)
    offset = answer - coefficient * x_value
    return MarkedEquationCase(
        construction_family="isosceles_triangle_angle_from_expression",
        draw_kind="isosceles_base_angles",
        answer=answer,
        target_name="angle B",
        variable_name="x",
        shape_kind="triangle",
        relation="isosceles_angle_measure_from_expression",
        formula_schema="equal_angle_expression_measure",
        labels={
            "angle_a": _angle_label(coefficient, "x", offset),
            "angle_b": _angle_label(1, "x", answer - x_value),
        },
        distractor_labels={
            "side_bc": str(11 + (index * 3) % 29),
            **_triangle_apex_angle_distractor(index),
        },
    )


def triangle_angle_sum_variable(variant_index: int) -> MarkedEquationCase:
    index = _variant(variant_index, modulo=97)
    answer = 3 + (index % 71)
    coefficient = 2 + (index % 3)
    angle_b = 40 + (index * 7) % 31
    angle_c = 36 + (index * 11) % 30
    angle_a = 180 - angle_b - angle_c
    offset = angle_a - coefficient * answer
    return MarkedEquationCase(
        construction_family="triangle_angle_sum_variable",
        draw_kind="angle_sum_triangle",
        answer=answer,
        target_name="x",
        variable_name="x",
        shape_kind="triangle",
        relation="triangle_interior_angle_sum_variable",
        formula_schema="polygon_angle_sum_variable",
        labels={
            "angle_A": _angle_label(coefficient, "x", offset),
            "angle_B": _degree_label(angle_b),
            "angle_C": _degree_label(angle_c),
        },
        distractor_labels={"side_bc": _linear_label(1 + (index % 2), "y", 6 + (index * 5) % 18)},
    )


def quadrilateral_angle_sum_variable(variant_index: int) -> MarkedEquationCase:
    index = _variant(variant_index, modulo=97)
    answer = 3 + (index % 71)
    coefficient = 2 + (index % 4)
    angle_b = 66 + (index * 5) % 42
    angle_c = 58 + (index * 7) % 39
    angle_d = 52 + (index * 11) % 37
    angle_a = 360 - angle_b - angle_c - angle_d
    offset = angle_a - coefficient * answer
    return MarkedEquationCase(
        construction_family="quadrilateral_angle_sum_variable",
        draw_kind="angle_sum_quadrilateral",
        answer=answer,
        target_name="x",
        variable_name="x",
        shape_kind="quadrilateral",
        relation="quadrilateral_interior_angle_sum_variable",
        formula_schema="polygon_angle_sum_variable",
        labels={
            "angle_A": _angle_label(coefficient, "x", offset),
            "angle_B": _degree_label(angle_b),
            "angle_C": _degree_label(angle_c),
            "angle_D": _degree_label(angle_d),
        },
        distractor_labels={"side_bc": str(12 + (index * 3) % 26), "side_cd": _linear_label(1, "y", 5 + index % 15)},
    )


def triangle_angle_sum_angle_measure(variant_index: int) -> MarkedEquationCase:
    index = _variant(variant_index, modulo=97)
    x_value = 4 + (index % 53)
    answer = 35 + (index * 5) % 55
    angle_a = 44 + (index * 7) % 42
    angle_c = 180 - answer - angle_a
    if angle_c < 30:
        angle_a = 180 - answer - 35
        angle_c = 35
    coefficient = 2 + (index % 3)
    return MarkedEquationCase(
        construction_family="triangle_angle_sum_angle_measure",
        draw_kind="angle_sum_triangle",
        answer=answer,
        target_name="angle B",
        variable_name="x",
        shape_kind="triangle",
        relation="triangle_interior_angle_sum_target_angle",
        formula_schema="polygon_angle_sum_angle_measure",
        labels={
            "angle_A": _angle_label(coefficient, "x", angle_a - coefficient * x_value),
            "angle_B": _angle_label(1, "x", answer - x_value),
            "angle_C": _degree_label(angle_c),
        },
        distractor_labels={"side_ac": str(9 + (index * 4) % 24)},
    )


def quadrilateral_angle_sum_angle_measure(variant_index: int) -> MarkedEquationCase:
    index = _variant(variant_index, modulo=97)
    x_value = 4 + (index % 53)
    answer = 50 + (index * 5) % 67
    angle_a = 68 + (index * 7) % 39
    angle_c = 58 + (index * 3) % 37
    angle_d = 360 - answer - angle_a - angle_c
    if angle_d < 45:
        angle_c = 45
        angle_d = 360 - answer - angle_a - angle_c
    coefficient = 2 + (index % 3)
    return MarkedEquationCase(
        construction_family="quadrilateral_angle_sum_angle_measure",
        draw_kind="angle_sum_quadrilateral",
        answer=answer,
        target_name="angle B",
        variable_name="x",
        shape_kind="quadrilateral",
        relation="quadrilateral_interior_angle_sum_target_angle",
        formula_schema="polygon_angle_sum_angle_measure",
        labels={
            "angle_A": _degree_label(angle_a),
            "angle_B": _angle_label(1, "x", answer - x_value),
            "angle_C": _degree_label(angle_c),
            "angle_D": _angle_label(coefficient, "x", angle_d - coefficient * x_value),
        },
        distractor_labels={"side_ab": _linear_label(1, "y", 8 + (index * 3) % 17), "side_cd": str(14 + index % 25)},
    )


__all__ = [
    "Builder",
    "equilateral_equal_side_variable",
    "equilateral_median_right_angle_variable",
    "equilateral_median_side_length_from_expression",
    "equilateral_side_from_expression",
    "isosceles_altitude_base_split_variable",
    "isosceles_angle_from_expression",
    "isosceles_base_angle_variable",
    "isosceles_equal_side_variable",
    "isosceles_side_from_expression",
    "marked_equal_angle_from_expression",
    "marked_equal_angles_variable",
    "marked_polygon_equal_side_variable",
    "marked_polygon_side_from_expression",
    "quadrilateral_angle_sum_angle_measure",
    "quadrilateral_angle_sum_variable",
    "triangle_angle_sum_angle_measure",
    "triangle_angle_sum_variable",
]
