"""Shared sectioned-document field templates and typed value builders."""

from __future__ import annotations

import datetime as dt
from random import Random
from typing import Dict, Tuple

from .text_generation import (
    format_currency_from_cents,
    sample_company_name,
    sample_email,
    sample_identifier,
    sample_person_name,
    sample_phone_number,
)


SUPPORTED_SECTIONED_DOCUMENT_SCENE_VARIANTS: Tuple[str, ...] = (
    "form_sheet",
    "invoice_sheet",
    "receipt_sheet",
)
SECTIONED_DOCUMENT_FIELD_TEMPLATES_BY_SCENE: Dict[str, Tuple[Dict[str, str], ...]] = {
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
            "field_id": "reviewer_name",
            "field_label": "Reviewer",
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
            "field_id": "registration_fee",
            "field_label": "Registration Fee",
            "section_id": "fees",
            "section_label": "Fees",
            "comparison_kind": "amount",
        },
        {
            "field_id": "service_fee",
            "field_label": "Service Fee",
            "section_id": "fees",
            "section_label": "Fees",
            "comparison_kind": "amount",
        },
        {
            "field_id": "discount_amount",
            "field_label": "Discount",
            "section_id": "fees",
            "section_label": "Fees",
            "comparison_kind": "amount",
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
            "comparison_kind": "other",
        },
        {
            "field_id": "service_date",
            "field_label": "Service Date",
            "section_id": "dates",
            "section_label": "Dates",
            "comparison_kind": "other",
        },
        {
            "field_id": "due_date",
            "field_label": "Due Date",
            "section_id": "dates",
            "section_label": "Dates",
            "comparison_kind": "other",
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
            "field_id": "discount_amount",
            "field_label": "Discount",
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
            "section_id": "purchase_info",
            "section_label": "Purchase Info",
            "comparison_kind": "other",
        },
        {
            "field_id": "member_id",
            "field_label": "Member ID",
            "section_id": "purchase_info",
            "section_label": "Purchase Info",
            "comparison_kind": "other",
        },
        {
            "field_id": "register_id",
            "field_label": "Register ID",
            "section_id": "purchase_info",
            "section_label": "Purchase Info",
            "comparison_kind": "other",
        },
        {
            "field_id": "items_total",
            "field_label": "Items Total",
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
            "field_id": "discount_amount",
            "field_label": "Discount",
            "section_id": "totals",
            "section_label": "Totals",
            "comparison_kind": "amount",
        },
    ),
}
SECTIONED_DOCUMENT_AMOUNT_SECTION_BY_SCENE = {
    "form_sheet": ("fees", "Fees"),
    "invoice_sheet": ("billing_summary", "Billing Summary"),
    "receipt_sheet": ("totals", "Totals"),
}
SECTIONED_DOCUMENT_FIELD_COUNT_RANGE = [
    min(
        len(SECTIONED_DOCUMENT_FIELD_TEMPLATES_BY_SCENE["form_sheet"]),
        len(SECTIONED_DOCUMENT_FIELD_TEMPLATES_BY_SCENE["receipt_sheet"]),
    ),
    len(SECTIONED_DOCUMENT_FIELD_TEMPLATES_BY_SCENE["invoice_sheet"]),
]
_DEPARTMENTS: Tuple[str, ...] = (
    "Operations",
    "Finance",
    "Support",
    "Planning",
    "Enrollment",
)


def _build_form_sectioned_values(rng: Random) -> Tuple[Dict[str, str], Dict[str, int]]:
    """Return visible values plus numeric fee amounts for form-sheet sectioned scenes."""

    applicant_name = sample_person_name(rng)
    registration_cents = rng.randint(5600, 15800)
    service_cents = rng.randint(1800, 7600)
    discount_cents = rng.randint(200, 1800)
    visible = {
        "applicant_name": applicant_name,
        "reference_id": sample_identifier(rng, prefix="REF", digits=5),
        "department": str(rng.choice(_DEPARTMENTS)),
        "reviewer_name": sample_person_name(rng),
        "contact_phone": sample_phone_number(rng),
        "contact_email": sample_email(rng, local_hint=applicant_name),
        "registration_fee": format_currency_from_cents(registration_cents),
        "service_fee": format_currency_from_cents(service_cents),
        "discount_amount": format_currency_from_cents(discount_cents),
    }
    amounts = {
        "registration_fee": registration_cents,
        "service_fee": service_cents,
        "discount_amount": discount_cents,
    }
    return visible, amounts


def _build_invoice_sectioned_values(rng: Random) -> Tuple[Dict[str, str], Dict[str, int]]:
    """Return visible values plus numeric billing-summary amounts for invoice sectioned scenes."""

    vendor_name = sample_company_name(rng)
    issue_offset = rng.randint(0, 18)
    service_offset = issue_offset + rng.randint(2, 8)
    due_offset = service_offset + rng.randint(8, 24)
    issue_date = dt.date(2026, 3, 1) + dt.timedelta(days=issue_offset)
    service_date = dt.date(2026, 3, 1) + dt.timedelta(days=service_offset)
    due_date = dt.date(2026, 3, 1) + dt.timedelta(days=due_offset)
    subtotal_cents = rng.randint(12600, 33600)
    tax_cents = rng.randint(500, 2600)
    discount_cents = rng.randint(300, 2200)
    visible = {
        "vendor_name": vendor_name,
        "customer_name": sample_person_name(rng),
        "invoice_number": sample_identifier(rng, prefix="INV", digits=5),
        "account_id": sample_identifier(rng, prefix="ACC", digits=4),
        "contact_email": sample_email(rng, local_hint=vendor_name),
        "issue_date": issue_date.strftime("%Y-%m-%d"),
        "service_date": service_date.strftime("%Y-%m-%d"),
        "due_date": due_date.strftime("%Y-%m-%d"),
        "subtotal_amount": format_currency_from_cents(subtotal_cents),
        "tax_amount": format_currency_from_cents(tax_cents),
        "discount_amount": format_currency_from_cents(discount_cents),
    }
    amounts = {
        "subtotal_amount": subtotal_cents,
        "tax_amount": tax_cents,
        "discount_amount": discount_cents,
    }
    return visible, amounts


def _build_receipt_sectioned_values(rng: Random) -> Tuple[Dict[str, str], Dict[str, int]]:
    """Return visible values plus numeric total-section amounts for receipt sectioned scenes."""

    store_name = sample_company_name(rng)
    purchase_offset = rng.randint(0, 20)
    purchase_date = dt.date(2026, 4, 1) + dt.timedelta(days=purchase_offset)
    items_total_cents = rng.randint(2600, 9800)
    tax_cents = rng.randint(120, 980)
    discount_cents = rng.randint(100, 900)
    visible = {
        "store_name": store_name,
        "receipt_number": sample_identifier(rng, prefix="R", digits=5),
        "cashier_name": sample_person_name(rng),
        "purchase_date": purchase_date.strftime("%b %d, %Y"),
        "member_id": sample_identifier(rng, prefix="M", digits=4),
        "register_id": sample_identifier(rng, prefix="REG", digits=3),
        "items_total": format_currency_from_cents(items_total_cents),
        "tax_amount": format_currency_from_cents(tax_cents),
        "discount_amount": format_currency_from_cents(discount_cents),
    }
    amounts = {
        "items_total": items_total_cents,
        "tax_amount": tax_cents,
        "discount_amount": discount_cents,
    }
    return visible, amounts


_SECTIONED_DOCUMENT_VALUE_BUILDERS = {
    "form_sheet": _build_form_sectioned_values,
    "invoice_sheet": _build_invoice_sectioned_values,
    "receipt_sheet": _build_receipt_sectioned_values,
}


def build_sectioned_document_values(scene_variant: str, rng: Random) -> Tuple[Dict[str, str], Dict[str, int]]:
    """Return visible values plus numeric amount fields for one sectioned document scene."""

    return _SECTIONED_DOCUMENT_VALUE_BUILDERS[str(scene_variant)](rng)


__all__ = [
    "SECTIONED_DOCUMENT_AMOUNT_SECTION_BY_SCENE",
    "SECTIONED_DOCUMENT_FIELD_COUNT_RANGE",
    "SECTIONED_DOCUMENT_FIELD_TEMPLATES_BY_SCENE",
    "SUPPORTED_SECTIONED_DOCUMENT_SCENE_VARIANTS",
    "build_sectioned_document_values",
]
