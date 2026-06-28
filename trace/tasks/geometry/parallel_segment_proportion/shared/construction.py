"""Identity-free construction helpers for parallel-segment proportions."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.core.sampling import integer_range_choice, uniform_choice
from trace.core.seed import spawn_rng
from trace.tasks.shared.fixed_query import probability_map

from .defaults import CONSTRUCTION_FAMILIES
from .state import ParallelProportionPlan

VARIABLE_ANSWER_SUPPORT: tuple[int, ...] = tuple(range(3, 41))
SEGMENT_LENGTH_ANSWER_SUPPORT: tuple[int, ...] = tuple(range(6, 61))


def _int_param(params: Mapping[str, Any], key: str, default: int) -> int:
    if key not in params:
        return int(default)
    value = params[key]
    if isinstance(value, bool):
        raise ValueError(f"{key} must be an integer")
    return int(value)


def select_construction_family(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> tuple[str, dict[str, float]]:
    """Select or validate one internal construction family."""

    forced = params.get("construction_family")
    if forced is not None:
        family = str(forced)
        if family not in CONSTRUCTION_FAMILIES:
            raise ValueError(
                f"unsupported construction_family={family!r}; supported: {CONSTRUCTION_FAMILIES}"
            )
        return family, {key: (1.0 if key == family else 0.0) for key in CONSTRUCTION_FAMILIES}

    rng = spawn_rng(int(instance_seed), str(namespace))
    family = str(uniform_choice(rng, CONSTRUCTION_FAMILIES))
    return str(family), probability_map(CONSTRUCTION_FAMILIES)


def select_answer(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    support: Sequence[int],
) -> int:
    """Select or validate one answer from a finite integer support."""

    answer_support = tuple(int(value) for value in support)
    if not answer_support:
        raise ValueError("answer support must not be empty")
    if "answer_value" in params:
        answer = _int_param(params, "answer_value", answer_support[0])
        if answer not in answer_support:
            raise ValueError(f"answer_value={answer!r} is outside supported range")
        return int(answer)
    rng = spawn_rng(int(instance_seed), str(namespace))
    return int(uniform_choice(rng, answer_support))


def select_variant_index(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    modulus: int = 8,
) -> int:
    """Select one construction-detail variant index."""

    if "case_index" in params:
        value = _int_param(params, "case_index", 0)
        if value < 0 or value >= int(modulus):
            raise ValueError(f"case_index must be in [0, {int(modulus) - 1}]")
        return int(value)
    rng = spawn_rng(int(instance_seed), str(namespace))
    selected, _probabilities = integer_range_choice(rng, 0, int(modulus) - 1)
    return int(selected)


def build_variable_plan(
    *,
    construction_family: str,
    answer: int,
    variant_index: int,
) -> ParallelProportionPlan:
    """Build labels for a variable-solving proportion task."""

    offset = 1 + (int(variant_index) % 5)
    ratio = 2 + (int(variant_index) % 2)
    left_top = 4 + (int(variant_index) % 8)
    answer_int = int(answer)
    if construction_family != "triangle_side_splitter":
        raise ValueError(f"unsupported construction_family={construction_family!r}")
    labels = {
        "left_top": str(left_top),
        "left_bottom": f"x+{offset}",
        "right_top": str(ratio * left_top),
        "right_bottom": str(ratio * (answer_int + offset)),
    }

    return ParallelProportionPlan(
        construction_family=str(construction_family),
        answer=float(answer_int),
        target_name="x",
        variable_name="x",
        labels=labels,
        relation="triangle_side_splitter_proportion_expression",
        formula_family="parallel_segment_ratio_variable",
        answer_support=VARIABLE_ANSWER_SUPPORT,
        params={
            "construction_family": str(construction_family),
            "case_index": int(variant_index),
            "answer_value": int(answer_int),
            "expression_offset": int(offset),
            "ratio": int(ratio),
            "left_top_value": int(left_top),
            "solved_variable_value": int(answer_int),
        },
    )


def build_segment_length_plan(
    *,
    construction_family: str,
    answer: int,
    variant_index: int,
) -> ParallelProportionPlan:
    """Build labels for a target-segment length proportion task."""

    offset = 1 + (int(variant_index) % 6)
    ratio = 2 + (int(variant_index) % 2)
    left_top = 4 + (int(variant_index) % 8)
    answer_int = int(answer)
    if construction_family != "triangle_side_splitter":
        raise ValueError(f"unsupported construction_family={construction_family!r}")
    target_name = "AE"
    labels = {
        "left_top": str(left_top),
        "left_bottom": str(ratio * left_top),
        "right_top": f"x+{offset}",
        "right_bottom": str(ratio * answer_int),
    }

    return ParallelProportionPlan(
        construction_family=str(construction_family),
        answer=float(answer_int),
        target_name=str(target_name),
        variable_name="x",
        labels=labels,
        relation="triangle_side_splitter_segment_length_expression",
        formula_family="parallel_segment_ratio_target_length",
        answer_support=SEGMENT_LENGTH_ANSWER_SUPPORT,
        params={
            "construction_family": str(construction_family),
            "case_index": int(variant_index),
            "answer_value": int(answer_int),
            "expression_offset": int(offset),
            "ratio": int(ratio),
            "left_top_value": int(left_top),
            "solved_variable_value": int(answer_int - offset),
            "target_name": str(target_name),
        },
    )


__all__ = [
    "SEGMENT_LENGTH_ANSWER_SUPPORT",
    "VARIABLE_ANSWER_SUPPORT",
    "build_segment_length_plan",
    "build_variable_plan",
    "select_answer",
    "select_construction_family",
    "select_variant_index",
]
