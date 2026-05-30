"""Shared section-local arithmetic builders for page-domain form-section tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from .common import (
    build_document_field_specs,
    build_document_section_specs,
    resolve_pages_axis_variant,
)
from .document_common import DOCUMENT_SCENE_TITLES
from .sectioned_document_common import (
    SECTIONED_DOCUMENT_AMOUNT_SECTION_BY_SCENE,
    SECTIONED_DOCUMENT_FIELD_COUNT_RANGE,
    SECTIONED_DOCUMENT_FIELD_TEMPLATES_BY_SCENE,
    SUPPORTED_SECTIONED_DOCUMENT_SCENE_VARIANTS,
    build_sectioned_document_values,
)
from .text_generation import format_currency_from_cents


SUPPORTED_DOCUMENT_ARITHMETIC_QUERY_IDS: Tuple[str, ...] = (
    "sum_two_amounts_in_section",
    "difference_two_amounts_in_section",
    "sum_minus_amount_in_section",
)
SUPPORTED_DOCUMENT_ARITHMETIC_SCENE_VARIANTS: Tuple[str, ...] = SUPPORTED_SECTIONED_DOCUMENT_SCENE_VARIANTS
_QUESTION_TEXT_BY_VARIANT = {
    "sum_two_amounts_in_section": (
        "In the {section_label} section, what is {first_label} plus {second_label}? "
        "Use currency notation with exactly two digits after the decimal point."
    ),
    "difference_two_amounts_in_section": (
        "In the {section_label} section, what is {first_label} minus {second_label}? "
        "Use currency notation with exactly two digits after the decimal point."
    ),
    "sum_minus_amount_in_section": (
        "In the {section_label} section, what is {first_label} plus {second_label} minus {third_label}? "
        "Use currency notation with exactly two digits after the decimal point."
    ),
}
_OPERAND_COUNT_BY_VARIANT = {
    "sum_two_amounts_in_section": 2,
    "difference_two_amounts_in_section": 2,
    "sum_minus_amount_in_section": 3,
}
_OPERATORS_BY_VARIANT = {
    "sum_two_amounts_in_section": ("+",),
    "difference_two_amounts_in_section": ("-",),
    "sum_minus_amount_in_section": ("+", "-"),
}


def _apply_expression(*, start_value: int, operators: Sequence[str], remaining_values: Sequence[int]) -> int:
    """Return the integer-cent result of the configured left-to-right expression."""

    result = int(start_value)
    for operator, value in zip(operators, remaining_values):
        if str(operator) == "+":
            result += int(value)
        elif str(operator) == "-":
            result -= int(value)
        else:
            raise ValueError(f"unsupported arithmetic operator '{operator}'")
    return int(result)


def _sample_operand_specs(
    *,
    candidate_specs: Sequence[Mapping[str, Any]],
    amount_cents: Mapping[str, int],
    query_id: str,
    instance_seed: int,
    task_id: str,
    attempt: int,
) -> list[Dict[str, Any]]:
    """Sample expression operands from all amount candidates in the queried section."""

    operand_count = int(_OPERAND_COUNT_BY_VARIANT[str(query_id)])
    if len(candidate_specs) < operand_count:
        raise ValueError(
            f"scene_variant candidate pool has {len(candidate_specs)} amount fields; "
            f"query_id='{query_id}' requires {operand_count}"
        )
    operand_rng = spawn_rng(
        int(instance_seed),
        f"{task_id}.arithmetic_operands.{query_id}",
        index=int(attempt),
    )
    sampled = [dict(spec) for spec in operand_rng.sample(list(candidate_specs), operand_count)]
    if str(query_id) == "difference_two_amounts_in_section":
        sampled = sorted(
            sampled,
            key=lambda spec: int(amount_cents[str(spec["field_id"])]),
            reverse=True,
        )
    return sampled


def resolve_document_arithmetic_query_id(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic arithmetic query id for one form-section page task."""

    return resolve_pages_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DOCUMENT_ARITHMETIC_QUERY_IDS,
        task_id=str(task_id),
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def resolve_document_arithmetic_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the visual scene variant for one form-section arithmetic task."""

    return resolve_pages_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DOCUMENT_ARITHMETIC_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def build_document_section_expression_dataset(
    *,
    query_id: str,
    scene_variant: str,
    instance_seed: int,
    task_id: str,
) -> Dict[str, Any]:
    """Build one section-local arithmetic-expression dataset for the pages domain."""

    templates = list(SECTIONED_DOCUMENT_FIELD_TEMPLATES_BY_SCENE[str(scene_variant)])
    target_section_id, target_section_label = SECTIONED_DOCUMENT_AMOUNT_SECTION_BY_SCENE[str(scene_variant)]
    operators = tuple(str(operator) for operator in _OPERATORS_BY_VARIANT[str(query_id)])

    for attempt in range(96):
        value_rng = spawn_rng(int(instance_seed), f"{task_id}.arithmetic_values", index=int(attempt))
        visible_values, amount_cents = build_sectioned_document_values(str(scene_variant), value_rng)
        field_specs = build_document_field_specs(templates, visible_values=visible_values)
        if field_specs is None or len(field_specs) != len(templates):
            continue
        seen_values = {str(spec["field_value"]) for spec in field_specs}

        candidate_specs = [
            spec
            for spec in field_specs
            if str(spec["section_id"]) == str(target_section_id)
            and str(spec["comparison_kind"]) == "amount"
        ]
        if len(candidate_specs) <= len(operators):
            raise ValueError(f"scene_variant='{scene_variant}' has too few amount fields in the target section")
        candidate_values = [int(amount_cents[str(spec["field_id"])]) for spec in candidate_specs]
        if len(candidate_values) != len(set(candidate_values)):
            continue

        operand_specs = _sample_operand_specs(
            candidate_specs=candidate_specs,
            amount_cents=amount_cents,
            query_id=str(query_id),
            instance_seed=int(instance_seed),
            task_id=str(task_id),
            attempt=int(attempt),
        )
        operand_cents = [int(amount_cents[str(spec["field_id"])]) for spec in operand_specs]
        result_cents = _apply_expression(
            start_value=int(operand_cents[0]),
            operators=operators,
            remaining_values=list(operand_cents[1:]),
        )
        if int(result_cents) <= 0:
            continue
        result_value = format_currency_from_cents(int(result_cents))
        if str(result_value) in seen_values:
            continue

        section_specs = build_document_section_specs(field_specs)

        question_text = str(_QUESTION_TEXT_BY_VARIANT[str(query_id)]).format(
            section_label=str(target_section_label),
            first_label=str(operand_specs[0]["field_label"]),
            second_label=str(operand_specs[1]["field_label"]),
            third_label=str(operand_specs[2]["field_label"]) if len(operand_specs) >= 3 else "",
        )
        return {
            "scene_variant": str(scene_variant),
            "query_id": str(query_id),
            "scene_title": str(DOCUMENT_SCENE_TITLES[str(scene_variant)]),
            "question_text": str(question_text),
            "question_format": "document_section_expression_value",
            "view_family": "structured_document",
            "field_specs": list(field_specs),
            "section_specs": list(section_specs),
            "field_count": int(len(field_specs)),
            "field_count_range": list(SECTIONED_DOCUMENT_FIELD_COUNT_RANGE),
            "query_section_id": str(target_section_id),
            "query_section_label": str(target_section_label),
            "target_amount_candidate_count": int(len(candidate_specs)),
            "target_amount_candidate_field_ids": [str(spec["field_id"]) for spec in candidate_specs],
            "operand_field_ids": [str(spec["field_id"]) for spec in operand_specs],
            "operand_field_labels": [str(spec["field_label"]) for spec in operand_specs],
            "operand_field_values": [str(spec["field_value"]) for spec in operand_specs],
            "operand_value_bbox_ids": [str(spec["value_bbox_id"]) for spec in operand_specs],
            "operator_sequence": list(operators),
            "expression_operand_cents": list(operand_cents),
            "result_cents": int(result_cents),
            "result_value": str(result_value),
        }
    raise ValueError("failed to build a section-expression document scene with unique visible values")


__all__ = [
    "SUPPORTED_DOCUMENT_ARITHMETIC_SCENE_VARIANTS",
    "SUPPORTED_DOCUMENT_ARITHMETIC_QUERY_IDS",
    "build_document_section_expression_dataset",
    "resolve_document_arithmetic_scene_variant",
    "resolve_document_arithmetic_query_id",
]
