"""Shared section-local relation builders for documents-domain tasks."""

from __future__ import annotations

import datetime as dt
from random import Random
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from .common import (
    build_document_field_specs,
    build_document_section_specs,
    resolve_documents_axis_variant,
)
from .document_common import DOCUMENT_SCENE_TITLES
from .text_generation import (
    format_currency_from_cents,
    sample_company_name,
    sample_email,
    sample_identifier,
    sample_person_name,
    sample_phone_number,
)


SUPPORTED_DOCUMENT_RELATION_TASK_VARIANTS: Tuple[str, ...] = (
    "earliest_date_in_section",
    "latest_date_in_section",
    "largest_amount_in_section",
    "smallest_amount_in_section",
)
_COMPARISON_KIND_BY_VARIANT = {
    "earliest_date_in_section": "date",
    "latest_date_in_section": "date",
    "largest_amount_in_section": "amount",
    "smallest_amount_in_section": "amount",
}
_SUPPORTED_SCENES_BY_VARIANT = {
    "earliest_date_in_section": ("form_sheet", "invoice_sheet", "receipt_sheet"),
    "latest_date_in_section": ("form_sheet", "invoice_sheet", "receipt_sheet"),
    "largest_amount_in_section": ("invoice_sheet", "receipt_sheet"),
    "smallest_amount_in_section": ("invoice_sheet", "receipt_sheet"),
}
_QUESTION_TEXT_BY_VARIANT = {
    "earliest_date_in_section": "In the {section_label} section, what is the earliest date shown? Return the exact date shown.",
    "latest_date_in_section": "In the {section_label} section, what is the latest date shown? Return the exact date shown.",
    "largest_amount_in_section": "In the {section_label} section, what is the largest amount shown? Return the exact amount shown.",
    "smallest_amount_in_section": "In the {section_label} section, what is the smallest amount shown? Return the exact amount shown.",
}
_TARGET_SECTION_BY_SCENE_AND_KIND = {
    "form_sheet": {"date": ("schedule", "Schedule")},
    "invoice_sheet": {
        "date": ("dates", "Dates"),
        "amount": ("billing_summary", "Billing Summary"),
    },
    "receipt_sheet": {
        "date": ("dates", "Dates"),
        "amount": ("totals", "Totals"),
    },
}
_FIELD_TEMPLATES_BY_SCENE: Dict[str, Tuple[Dict[str, str], ...]] = {
    "form_sheet": (
        {
            "field_id": "applicant_name",
            "field_label": "Applicant Name",
            "section_id": "profile",
            "section_label": "Profile",
            "comparison_kind": "other",
        },
        {
            "field_id": "reference_id",
            "field_label": "Reference ID",
            "section_id": "profile",
            "section_label": "Profile",
            "comparison_kind": "other",
        },
        {
            "field_id": "department",
            "field_label": "Department",
            "section_id": "profile",
            "section_label": "Profile",
            "comparison_kind": "other",
        },
        {
            "field_id": "contact_phone",
            "field_label": "Phone",
            "section_id": "contact",
            "section_label": "Contact",
            "comparison_kind": "other",
        },
        {
            "field_id": "contact_email",
            "field_label": "Email",
            "section_id": "contact",
            "section_label": "Contact",
            "comparison_kind": "other",
        },
        {
            "field_id": "submission_date",
            "field_label": "Submission Date",
            "section_id": "schedule",
            "section_label": "Schedule",
            "comparison_kind": "date",
        },
        {
            "field_id": "review_date",
            "field_label": "Review Date",
            "section_id": "schedule",
            "section_label": "Schedule",
            "comparison_kind": "date",
        },
        {
            "field_id": "approval_date",
            "field_label": "Approval Date",
            "section_id": "schedule",
            "section_label": "Schedule",
            "comparison_kind": "date",
        },
        {
            "field_id": "processing_fee",
            "field_label": "Processing Fee",
            "section_id": "filing",
            "section_label": "Filing",
            "comparison_kind": "other",
        },
    ),
    "invoice_sheet": (
        {
            "field_id": "vendor_name",
            "field_label": "Vendor",
            "section_id": "parties",
            "section_label": "Parties",
            "comparison_kind": "other",
        },
        {
            "field_id": "customer_name",
            "field_label": "Customer",
            "section_id": "parties",
            "section_label": "Parties",
            "comparison_kind": "other",
        },
        {
            "field_id": "invoice_number",
            "field_label": "Invoice Number",
            "section_id": "parties",
            "section_label": "Parties",
            "comparison_kind": "other",
        },
        {
            "field_id": "account_id",
            "field_label": "Account ID",
            "section_id": "account",
            "section_label": "Account",
            "comparison_kind": "other",
        },
        {
            "field_id": "contact_email",
            "field_label": "Contact Email",
            "section_id": "account",
            "section_label": "Account",
            "comparison_kind": "other",
        },
        {
            "field_id": "issue_date",
            "field_label": "Issue Date",
            "section_id": "dates",
            "section_label": "Dates",
            "comparison_kind": "date",
        },
        {
            "field_id": "service_date",
            "field_label": "Service Date",
            "section_id": "dates",
            "section_label": "Dates",
            "comparison_kind": "date",
        },
        {
            "field_id": "due_date",
            "field_label": "Due Date",
            "section_id": "dates",
            "section_label": "Dates",
            "comparison_kind": "date",
        },
        {
            "field_id": "subtotal_amount",
            "field_label": "Subtotal",
            "section_id": "billing_summary",
            "section_label": "Billing Summary",
            "comparison_kind": "amount",
        },
        {
            "field_id": "tax_amount",
            "field_label": "Tax",
            "section_id": "billing_summary",
            "section_label": "Billing Summary",
            "comparison_kind": "amount",
        },
        {
            "field_id": "total_due",
            "field_label": "Total Due",
            "section_id": "billing_summary",
            "section_label": "Billing Summary",
            "comparison_kind": "amount",
        },
    ),
    "receipt_sheet": (
        {
            "field_id": "store_name",
            "field_label": "Store Name",
            "section_id": "store_details",
            "section_label": "Store Details",
            "comparison_kind": "other",
        },
        {
            "field_id": "receipt_number",
            "field_label": "Receipt No.",
            "section_id": "store_details",
            "section_label": "Store Details",
            "comparison_kind": "other",
        },
        {
            "field_id": "cashier_name",
            "field_label": "Cashier",
            "section_id": "store_details",
            "section_label": "Store Details",
            "comparison_kind": "other",
        },
        {
            "field_id": "purchase_date",
            "field_label": "Purchase Date",
            "section_id": "dates",
            "section_label": "Dates",
            "comparison_kind": "date",
        },
        {
            "field_id": "pickup_date",
            "field_label": "Pickup Date",
            "section_id": "dates",
            "section_label": "Dates",
            "comparison_kind": "date",
        },
        {
            "field_id": "return_date",
            "field_label": "Return Date",
            "section_id": "dates",
            "section_label": "Dates",
            "comparison_kind": "date",
        },
        {
            "field_id": "subtotal_amount",
            "field_label": "Subtotal",
            "section_id": "totals",
            "section_label": "Totals",
            "comparison_kind": "amount",
        },
        {
            "field_id": "tax_amount",
            "field_label": "Tax",
            "section_id": "totals",
            "section_label": "Totals",
            "comparison_kind": "amount",
        },
        {
            "field_id": "total_paid",
            "field_label": "Total Paid",
            "section_id": "totals",
            "section_label": "Totals",
            "comparison_kind": "amount",
        },
    ),
}


def _format_date(value: dt.date, *, style: str) -> str:
    """Format one date object using the scene-specific visible style."""

    if str(style) == "iso":
        return value.strftime("%Y-%m-%d")
    if str(style) == "slash":
        return value.strftime("%m/%d/%Y")
    if str(style) == "long":
        return value.strftime("%b %d, %Y")
    raise ValueError(f"unsupported date style '{style}'")


def _ordered_dates(anchor: dt.date, offsets: Sequence[int]) -> Sequence[dt.date]:
    """Return one ordered sequence of dates from the provided offsets."""

    return [anchor + dt.timedelta(days=int(offset)) for offset in offsets]


def _build_form_relation_values(rng: Random) -> Tuple[Dict[str, str], Dict[str, int]]:
    """Return visible values plus comparison scalars for form-sheet relation scenes."""

    applicant_name = sample_person_name(rng)
    submission_offset = rng.randint(0, 24)
    review_offset = submission_offset + rng.randint(3, 12)
    approval_offset = review_offset + rng.randint(4, 16)
    schedule_dates = _ordered_dates(
        dt.date(2026, 2, 1),
        [submission_offset, review_offset, approval_offset],
    )
    visible = {
        "applicant_name": applicant_name,
        "reference_id": sample_identifier(rng, prefix="REF", digits=5),
        "department": str(rng.choice(("Operations", "Planning", "Support", "Enrollment"))),
        "contact_phone": sample_phone_number(rng),
        "contact_email": sample_email(rng, local_hint=applicant_name),
        "submission_date": _format_date(schedule_dates[0], style="slash"),
        "review_date": _format_date(schedule_dates[1], style="slash"),
        "approval_date": _format_date(schedule_dates[2], style="slash"),
        "processing_fee": format_currency_from_cents(rng.randint(2500, 14800)),
    }
    comparable = {
        "submission_date": schedule_dates[0].toordinal(),
        "review_date": schedule_dates[1].toordinal(),
        "approval_date": schedule_dates[2].toordinal(),
    }
    return visible, comparable


def _build_invoice_relation_values(rng: Random) -> Tuple[Dict[str, str], Dict[str, int]]:
    """Return visible values plus comparison scalars for invoice relation scenes."""

    vendor_name = sample_company_name(rng)
    issue_offset = rng.randint(0, 16)
    service_offset = issue_offset + rng.randint(1, 8)
    due_offset = service_offset + rng.randint(8, 24)
    date_values = _ordered_dates(dt.date(2026, 3, 1), [issue_offset, service_offset, due_offset])
    subtotal_cents = rng.randint(11800, 33600)
    tax_cents = rng.randint(480, 2650)
    total_due_cents = subtotal_cents + tax_cents
    visible = {
        "vendor_name": vendor_name,
        "customer_name": sample_person_name(rng),
        "invoice_number": sample_identifier(rng, prefix="INV", digits=5),
        "account_id": sample_identifier(rng, prefix="ACC", digits=4),
        "contact_email": sample_email(rng, local_hint=vendor_name),
        "issue_date": _format_date(date_values[0], style="iso"),
        "service_date": _format_date(date_values[1], style="iso"),
        "due_date": _format_date(date_values[2], style="iso"),
        "subtotal_amount": format_currency_from_cents(subtotal_cents),
        "tax_amount": format_currency_from_cents(tax_cents),
        "total_due": format_currency_from_cents(total_due_cents),
    }
    comparable = {
        "issue_date": date_values[0].toordinal(),
        "service_date": date_values[1].toordinal(),
        "due_date": date_values[2].toordinal(),
        "subtotal_amount": subtotal_cents,
        "tax_amount": tax_cents,
        "total_due": total_due_cents,
    }
    return visible, comparable


def _build_receipt_relation_values(rng: Random) -> Tuple[Dict[str, str], Dict[str, int]]:
    """Return visible values plus comparison scalars for receipt relation scenes."""

    store_name = sample_company_name(rng)
    purchase_offset = rng.randint(0, 20)
    pickup_offset = purchase_offset + rng.randint(1, 5)
    return_offset = pickup_offset + rng.randint(5, 18)
    date_values = _ordered_dates(dt.date(2026, 4, 1), [purchase_offset, pickup_offset, return_offset])
    subtotal_cents = rng.randint(2100, 9800)
    tax_cents = rng.randint(120, 980)
    total_paid_cents = subtotal_cents + tax_cents
    visible = {
        "store_name": store_name,
        "receipt_number": sample_identifier(rng, prefix="R", digits=5),
        "cashier_name": sample_person_name(rng),
        "purchase_date": _format_date(date_values[0], style="long"),
        "pickup_date": _format_date(date_values[1], style="long"),
        "return_date": _format_date(date_values[2], style="long"),
        "subtotal_amount": format_currency_from_cents(subtotal_cents),
        "tax_amount": format_currency_from_cents(tax_cents),
        "total_paid": format_currency_from_cents(total_paid_cents),
    }
    comparable = {
        "purchase_date": date_values[0].toordinal(),
        "pickup_date": date_values[1].toordinal(),
        "return_date": date_values[2].toordinal(),
        "subtotal_amount": subtotal_cents,
        "tax_amount": tax_cents,
        "total_paid": total_paid_cents,
    }
    return visible, comparable


_VALUE_BUILDERS = {
    "form_sheet": _build_form_relation_values,
    "invoice_sheet": _build_invoice_relation_values,
    "receipt_sheet": _build_receipt_relation_values,
}


def resolve_document_relation_task_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic relation task variant for one documents task."""

    return resolve_documents_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DOCUMENT_RELATION_TASK_VARIANTS,
        task_id=str(task_id),
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        balance_flag_key="balanced_task_variant_sampling",
        axis_namespace="task_variant",
    )


def resolve_document_relation_scene_variant(
    params: Mapping[str, Any],
    *,
    task_variant: str,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one scene variant compatible with the active relation variant."""

    supported_scenes = _SUPPORTED_SCENES_BY_VARIANT[str(task_variant)]
    return resolve_documents_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=supported_scenes,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def build_document_section_extremum_dataset(
    *,
    task_variant: str,
    scene_variant: str,
    instance_seed: int,
    task_id: str,
) -> Dict[str, Any]:
    """Build one section-scoped extremum dataset for the documents relation family."""

    if str(scene_variant) not in _SUPPORTED_SCENES_BY_VARIANT[str(task_variant)]:
        raise ValueError(
            f"scene_variant='{scene_variant}' is not supported for task_variant='{task_variant}'"
        )
    templates = list(_FIELD_TEMPLATES_BY_SCENE[str(scene_variant)])
    comparison_kind = str(_COMPARISON_KIND_BY_VARIANT[str(task_variant)])
    target_section_id, target_section_label = _TARGET_SECTION_BY_SCENE_AND_KIND[str(scene_variant)][comparison_kind]

    for attempt in range(64):
        value_rng = spawn_rng(int(instance_seed), f"{task_id}.relation_values", index=int(attempt))
        visible_values, comparable_values = _VALUE_BUILDERS[str(scene_variant)](value_rng)
        field_specs = build_document_field_specs(templates, visible_values=visible_values)
        if field_specs is None or len(field_specs) != len(templates):
            continue

        candidate_specs = [
            spec
            for spec in field_specs
            if str(spec["section_id"]) == str(target_section_id)
            and str(spec["comparison_kind"]) == comparison_kind
        ]
        if len(candidate_specs) < 3:
            continue
        candidate_values = [int(comparable_values[str(spec["field_id"])]) for spec in candidate_specs]
        if len(candidate_values) != len(set(candidate_values)):
            continue

        pick_max = str(task_variant) in {"latest_date_in_section", "largest_amount_in_section"}
        winning_index = max(range(len(candidate_values)), key=candidate_values.__getitem__) if pick_max else min(
            range(len(candidate_values)), key=candidate_values.__getitem__
        )
        winning_field = dict(candidate_specs[int(winning_index)])
        section_specs = build_document_section_specs(field_specs)
        return {
            "scene_variant": str(scene_variant),
            "task_variant": str(task_variant),
            "scene_title": str(DOCUMENT_SCENE_TITLES[str(scene_variant)]),
            "question_text": str(_QUESTION_TEXT_BY_VARIANT[str(task_variant)]).format(
                section_label=str(target_section_label)
            ),
            "question_format": "document_section_extremum_value",
            "view_family": "structured_document",
            "field_specs": list(field_specs),
            "section_specs": list(section_specs),
            "field_count": int(len(field_specs)),
            "field_count_range": [min(len(_FIELD_TEMPLATES_BY_SCENE["form_sheet"]), len(_FIELD_TEMPLATES_BY_SCENE["receipt_sheet"])), len(_FIELD_TEMPLATES_BY_SCENE["invoice_sheet"])],
            "query_section_id": str(target_section_id),
            "query_section_label": str(target_section_label),
            "comparison_kind": comparison_kind,
            "compared_field_ids": [str(spec["field_id"]) for spec in candidate_specs],
            "compared_field_labels": [str(spec["field_label"]) for spec in candidate_specs],
            "compared_field_value_bbox_ids": [str(spec["value_bbox_id"]) for spec in candidate_specs],
            "winning_field_id": str(winning_field["field_id"]),
            "winning_field_label": str(winning_field["field_label"]),
            "winning_field_value": str(winning_field["field_value"]),
            "winning_value_bbox_id": str(winning_field["value_bbox_id"]),
            "winning_sort_value": int(comparable_values[str(winning_field["field_id"])]),
            "candidate_sort_values": {
                str(spec["field_id"]): int(comparable_values[str(spec["field_id"])])
                for spec in candidate_specs
            },
        }
    raise ValueError("failed to build a section-extremum document scene with unique visible values")


__all__ = [
    "SUPPORTED_DOCUMENT_RELATION_TASK_VARIANTS",
    "build_document_section_extremum_dataset",
    "resolve_document_relation_scene_variant",
    "resolve_document_relation_task_variant",
]
