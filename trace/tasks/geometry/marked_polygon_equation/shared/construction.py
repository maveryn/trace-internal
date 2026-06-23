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
]
