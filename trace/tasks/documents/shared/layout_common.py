"""Shared layout-reasoning builders for documents-domain tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.seed import spawn_rng
from .common import (
    build_document_field_specs,
    build_document_section_specs,
    resolve_documents_axis_variant,
)
from .document_common import DOCUMENT_SCENE_TITLES
from .sectioned_document_common import (
    SECTIONED_DOCUMENT_FIELD_COUNT_RANGE,
    SECTIONED_DOCUMENT_FIELD_TEMPLATES_BY_SCENE,
    SUPPORTED_SECTIONED_DOCUMENT_SCENE_VARIANTS,
    build_sectioned_document_values,
)


SUPPORTED_DOCUMENT_LAYOUT_TASK_VARIANTS: Tuple[str, ...] = (
    "section_of_field_label",
    "section_of_field_value",
    "section_of_label_value_pair",
)
SUPPORTED_DOCUMENT_LAYOUT_SCENE_VARIANTS: Tuple[str, ...] = SUPPORTED_SECTIONED_DOCUMENT_SCENE_VARIANTS
_QUESTION_TEXT_BY_VARIANT = {
    "section_of_field_label": (
        "Which section contains the field labeled {field_label}? Return the exact section title shown."
    ),
    "section_of_field_value": (
        "Which section contains the value {field_value}? Return the exact section title shown."
    ),
    "section_of_label_value_pair": (
        "Which section contains the field labeled {field_label} with value {field_value}? "
        "Return the exact section title shown."
    ),
}


def resolve_document_layout_task_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic layout task variant for one documents task."""

    return resolve_documents_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DOCUMENT_LAYOUT_TASK_VARIANTS,
        task_id=str(task_id),
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        balance_flag_key="balanced_task_variant_sampling",
        axis_namespace="task_variant",
    )


def resolve_document_layout_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the visual scene variant for one documents layout task."""

    return resolve_documents_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DOCUMENT_LAYOUT_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def build_document_section_membership_dataset(
    *,
    task_variant: str,
    scene_variant: str,
    instance_seed: int,
    task_id: str,
) -> Dict[str, Any]:
    """Build one section-membership dataset for the documents layout family."""

    templates = list(SECTIONED_DOCUMENT_FIELD_TEMPLATES_BY_SCENE[str(scene_variant)])
    for attempt in range(96):
        value_rng = spawn_rng(int(instance_seed), f"{task_id}.layout_values", index=int(attempt))
        visible_values, _ = build_sectioned_document_values(str(scene_variant), value_rng)
        field_specs = build_document_field_specs(templates, visible_values=visible_values)
        if field_specs is None or len(field_specs) != len(templates):
            continue
        section_specs = build_document_section_specs(field_specs)
        if len(section_specs) < 3:
            continue

        query_rng = spawn_rng(int(instance_seed), f"{task_id}.layout_query", index=int(attempt))
        query_field = dict(field_specs[int(query_rng.randrange(len(field_specs)))])
        question_text = str(_QUESTION_TEXT_BY_VARIANT[str(task_variant)]).format(
            field_label=str(query_field["field_label"]),
            field_value=str(query_field["field_value"]),
        )
        return {
            "scene_variant": str(scene_variant),
            "task_variant": str(task_variant),
            "scene_title": str(DOCUMENT_SCENE_TITLES[str(scene_variant)]),
            "question_text": str(question_text),
            "question_format": "document_section_membership_label",
            "view_family": "structured_document",
            "field_specs": list(field_specs),
            "section_specs": list(section_specs),
            "field_count": int(len(field_specs)),
            "field_count_range": list(SECTIONED_DOCUMENT_FIELD_COUNT_RANGE),
            "query_field_id": str(query_field["field_id"]),
            "query_field_label": str(query_field["field_label"]),
            "query_field_value": str(query_field["field_value"]),
            "query_section_id": str(query_field["section_id"]),
            "query_section_label": str(query_field["section_label"]),
            "query_section_label_bbox_id": str(query_field["section_id"]),
        }
    raise ValueError("failed to build a section-membership document scene with unique visible values")


__all__ = [
    "SUPPORTED_DOCUMENT_LAYOUT_SCENE_VARIANTS",
    "SUPPORTED_DOCUMENT_LAYOUT_TASK_VARIANTS",
    "build_document_section_membership_dataset",
    "resolve_document_layout_scene_variant",
    "resolve_document_layout_task_variant",
]
