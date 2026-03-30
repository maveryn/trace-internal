"""Shared checkbox-selection builders for documents-domain tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import hash64, spawn_rng
from ...shared.deterministic_sampling import resolve_selection_index
from .common import resolve_documents_axis_variant
from .document_common import DOCUMENT_SCENE_TITLES
from .text_generation import (
    sample_company_name,
    sample_date,
    sample_identifier,
    sample_person_name,
)


SUPPORTED_DOCUMENT_SELECTION_TASK_VARIANTS: Tuple[str, ...] = (
    "checked_box_count",
    "unchecked_box_count",
)
SUPPORTED_DOCUMENT_SELECTION_SCENE_VARIANTS: Tuple[str, ...] = (
    "form_sheet",
    "invoice_sheet",
    "receipt_sheet",
)
_QUESTION_TEXT_BY_VARIANT = {
    "checked_box_count": "In the {section_label} section, how many checkboxes are checked?",
    "unchecked_box_count": "In the {section_label} section, how many checkboxes are not checked?",
}
_CONTEXT_FIELDS_BY_SCENE = {
    "form_sheet": (
        {"field_id": "applicant_name", "field_label": "Applicant Name"},
        {"field_id": "reference_id", "field_label": "Reference ID"},
        {"field_id": "submission_date", "field_label": "Submission Date"},
        {"field_id": "department", "field_label": "Department"},
    ),
    "invoice_sheet": (
        {"field_id": "vendor_name", "field_label": "Vendor"},
        {"field_id": "invoice_number", "field_label": "Invoice Number"},
        {"field_id": "due_date", "field_label": "Due Date"},
    ),
    "receipt_sheet": (
        {"field_id": "store_name", "field_label": "Store Name"},
        {"field_id": "receipt_number", "field_label": "Receipt No."},
        {"field_id": "purchase_date", "field_label": "Purchase Date"},
    ),
}
_CHECKBOX_GROUPS_BY_SCENE = {
    "form_sheet": (
        {
            "section_id": "contact_preferences",
            "section_label": "Contact Preferences",
            "items": ("Email Updates", "SMS Alerts", "Phone Calls", "Paper Copies"),
        },
        {
            "section_id": "submission_flags",
            "section_label": "Submission Flags",
            "items": ("Rush Review", "Weekend Pickup", "ID Copy Attached", "Digital Receipt"),
        },
    ),
    "invoice_sheet": (
        {
            "section_id": "delivery_options",
            "section_label": "Delivery Options",
            "items": ("Standard Delivery", "Priority Delivery", "Signature Required", "Weekend Dropoff"),
        },
        {
            "section_id": "billing_flags",
            "section_label": "Billing Flags",
            "items": ("Paid Deposit", "Paper Invoice", "Auto Renew", "Tax Exempt"),
        },
    ),
    "receipt_sheet": (
        {
            "section_id": "service_options",
            "section_label": "Service Options",
            "items": ("Gift Receipt", "Email Copy", "Bag Requested", "Loyalty Applied"),
        },
        {
            "section_id": "follow_up",
            "section_label": "Follow-up",
            "items": ("Survey Invite", "Return Reminder", "Warranty Note", "Text Updates"),
        },
    ),
}


def _resolve_target_count(
    params: Mapping[str, Any] | None,
    *,
    instance_seed: int,
    task_id: str,
) -> tuple[int, str]:
    """Resolve the queried checkbox count from the fixed `0..4` support.

    `_sampling_index` remains the highest-priority override so tests and any
    future balanced collectors can cycle the tiny support explicitly. When that
    override is absent, combine two deterministic hashes of the already-hashed
    `instance_seed` to keep the support decorrelated from the task-variant
    selector under the task-review seed stream.
    """

    support_size = 5
    params = params or {}
    if params.get("_sampling_index") is not None:
        selection_index = int(
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.target_count",
            )
        )
        return int(selection_index % support_size), "balanced_sampling_index_mod_support"

    combined_index = abs(int(hash64(int(instance_seed), f"{task_id}.target_count", 1))) + abs(
        int(hash64(int(instance_seed), f"{task_id}.target_count", 3))
    )
    return int(combined_index % support_size), "combined_hash_mod_support"


def resolve_document_selection_task_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic selection task variant."""

    return resolve_documents_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DOCUMENT_SELECTION_TASK_VARIANTS,
        task_id=str(task_id),
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        balance_flag_key="balanced_task_variant_sampling",
        axis_namespace="task_variant",
    )


def resolve_document_selection_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the visual scene variant for a selection task."""

    return resolve_documents_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DOCUMENT_SELECTION_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _build_context_field_values(scene_variant: str, rng) -> Dict[str, str]:
    """Return a small typed context-field set for the requested scene."""

    if str(scene_variant) == "form_sheet":
        applicant_name = sample_person_name(rng)
        return {
            "applicant_name": applicant_name,
            "reference_id": sample_identifier(rng, prefix="REF", digits=5),
            "submission_date": sample_date(rng, style="slash"),
            "department": str(rng.choice(("Operations", "Planning", "Support", "Enrollment"))),
        }
    if str(scene_variant) == "invoice_sheet":
        return {
            "vendor_name": sample_company_name(rng),
            "invoice_number": sample_identifier(rng, prefix="INV", digits=5),
            "due_date": sample_date(rng, style="iso"),
        }
    return {
        "store_name": sample_company_name(rng),
        "receipt_number": sample_identifier(rng, prefix="R", digits=5),
        "purchase_date": sample_date(rng, style="long"),
    }


def build_document_checkbox_count_dataset(
    *,
    task_variant: str,
    scene_variant: str,
    instance_seed: int,
    task_id: str,
    params: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Build one checkbox-count dataset for a structured document."""

    scene_variant = str(scene_variant)
    task_variant = str(task_variant)
    group_templates = list(_CHECKBOX_GROUPS_BY_SCENE[scene_variant])
    context_templates = list(_CONTEXT_FIELDS_BY_SCENE[scene_variant])

    context_rng = spawn_rng(int(instance_seed), f"{task_id}.context_fields")
    context_values = _build_context_field_values(scene_variant, context_rng)
    context_field_specs = [
        {
            "field_id": str(template["field_id"]),
            "field_label": str(template["field_label"]),
            "field_value": str(context_values[str(template["field_id"])]),
            "label_bbox_id": f"{template['field_id']}:label",
            "value_bbox_id": f"{template['field_id']}:value",
        }
        for template in context_templates
    ]

    group_rng = spawn_rng(int(instance_seed), f"{task_id}.target_group")
    target_group_index = int(group_rng.randrange(len(group_templates)))
    target_count, query_selection_strategy = _resolve_target_count(
        params,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
    )
    checkbox_sections = []
    evidence_item_ids = []

    for group_index, group_template in enumerate(group_templates):
        section_id = str(group_template["section_id"])
        section_label = str(group_template["section_label"])
        item_labels = [str(item) for item in group_template["items"]]
        item_count = len(item_labels)
        if item_count != 4:
            raise ValueError(f"checkbox section '{section_id}' expected 4 items, got {item_count}")
        checked_count = target_count if task_variant == "checked_box_count" else (item_count - target_count)
        if group_index != target_group_index:
            distractor_rng = spawn_rng(int(instance_seed), f"{task_id}.distractor_checked", index=int(group_index))
            checked_count = int(distractor_rng.randrange(item_count + 1))
        index_rng = spawn_rng(int(instance_seed), f"{task_id}.checked_indices", index=int(group_index))
        checked_indices = set(index_rng.sample(list(range(item_count)), int(checked_count)))
        items = []
        for item_index, item_label in enumerate(item_labels):
            item_id = f"{section_id}:{item_index}"
            checked = bool(item_index in checked_indices)
            checkbox_bbox_id = f"{item_id}:checkbox"
            label_bbox_id = f"{item_id}:label"
            items.append(
                {
                    "item_id": item_id,
                    "label": str(item_label),
                    "checked": checked,
                    "checkbox_bbox_id": checkbox_bbox_id,
                    "label_bbox_id": label_bbox_id,
                }
            )
        if group_index == target_group_index:
            if task_variant == "checked_box_count":
                evidence_item_ids = [str(item["checkbox_bbox_id"]) for item in items if bool(item["checked"])]
            else:
                evidence_item_ids = [str(item["checkbox_bbox_id"]) for item in items if not bool(item["checked"])]
        checkbox_sections.append(
            {
                "section_id": section_id,
                "section_label": section_label,
                "items": items,
            }
        )

    target_group = checkbox_sections[int(target_group_index)]
    return {
        "scene_variant": scene_variant,
        "task_variant": task_variant,
        "scene_title": str(DOCUMENT_SCENE_TITLES[scene_variant]),
        "question_text": str(_QUESTION_TEXT_BY_VARIANT[task_variant]).format(
            section_label=str(target_group["section_label"])
        ),
        "question_format": "document_checkbox_count",
        "view_family": "structured_document",
        "context_field_specs": list(context_field_specs),
        "checkbox_section_specs": list(checkbox_sections),
        "query_section_id": str(target_group["section_id"]),
        "query_section_label": str(target_group["section_label"]),
        "field_count": int(len(context_field_specs)),
        "field_count_range": [3, 4],
        "checkbox_item_count": 4,
        "answer_count": int(target_count),
        "evidence_checkbox_bbox_ids": list(evidence_item_ids),
        "target_checkbox_ids": [str(item["item_id"]) for item in target_group["items"]],
        "target_checkbox_states": {
            str(item["item_id"]): bool(item["checked"])
            for item in target_group["items"]
        },
        "query_selection_strategy": str(query_selection_strategy),
    }


__all__ = [
    "SUPPORTED_DOCUMENT_SELECTION_SCENE_VARIANTS",
    "SUPPORTED_DOCUMENT_SELECTION_TASK_VARIANTS",
    "build_document_checkbox_count_dataset",
    "resolve_document_selection_scene_variant",
    "resolve_document_selection_task_variant",
]
