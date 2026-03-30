"""Shared structured-document dataset construction and render-param helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default
from .common import resolve_documents_axis_variant
from .text_generation import (
    build_form_field_values,
    build_invoice_field_values,
    build_receipt_field_values,
)


SUPPORTED_DOCUMENT_FIELD_TASK_VARIANTS: Tuple[str, ...] = (
    "lookup_identifier",
    "lookup_name",
    "lookup_date",
    "lookup_contact",
    "lookup_amount",
)
SUPPORTED_DOCUMENT_SCENE_VARIANTS: Tuple[str, ...] = (
    "form_sheet",
    "invoice_sheet",
    "receipt_sheet",
)


@dataclass(frozen=True)
class DocumentDefaults:
    """Stable fallback defaults for structured-document readout tasks."""

    canvas_width: int = 1280
    canvas_height: int = 920
    sheet_page_width_px: int = 960
    sheet_page_height_px: int = 760
    receipt_page_width_px: int = 520
    receipt_page_height_px: int = 760
    page_shadow_offset_px: int = 14
    page_corner_radius_px: int = 20
    field_corner_radius_px: int = 14
    page_outline_width_px: int = 2
    field_outline_width_px: int = 2
    title_font_size_px: int = 42
    section_font_size_px: int = 24
    label_font_size_px: int = 22
    value_font_size_px: int = 28
    page_fill_rgb: Tuple[int, int, int] = (251, 250, 246)
    page_outline_rgb: Tuple[int, int, int] = (120, 126, 138)
    page_shadow_rgb: Tuple[int, int, int] = (221, 224, 230)
    field_fill_rgb: Tuple[int, int, int] = (255, 255, 255)
    field_outline_rgb: Tuple[int, int, int] = (202, 207, 214)
    label_fill_rgb: Tuple[int, int, int] = (60, 66, 76)
    label_stroke_rgb: Tuple[int, int, int] = (255, 255, 255)
    value_fill_rgb: Tuple[int, int, int] = (24, 29, 35)
    divider_rgb: Tuple[int, int, int] = (214, 217, 224)


@dataclass(frozen=True)
class DocumentRenderParams:
    """Resolved rendering parameters for structured-document scenes."""

    canvas_width: int
    canvas_height: int
    sheet_page_width_px: int
    sheet_page_height_px: int
    receipt_page_width_px: int
    receipt_page_height_px: int
    page_shadow_offset_px: int
    page_corner_radius_px: int
    field_corner_radius_px: int
    page_outline_width_px: int
    field_outline_width_px: int
    title_font_size_px: int
    section_font_size_px: int
    label_font_size_px: int
    value_font_size_px: int
    page_fill_rgb: Tuple[int, int, int]
    page_outline_rgb: Tuple[int, int, int]
    page_shadow_rgb: Tuple[int, int, int]
    field_fill_rgb: Tuple[int, int, int]
    field_outline_rgb: Tuple[int, int, int]
    label_fill_rgb: Tuple[int, int, int]
    label_stroke_rgb: Tuple[int, int, int]
    value_fill_rgb: Tuple[int, int, int]
    divider_rgb: Tuple[int, int, int]


_FIELD_TEMPLATES_BY_SCENE: Dict[str, Tuple[Dict[str, str], ...]] = {
    "form_sheet": (
        {"field_id": "applicant_name", "field_label": "Applicant Name", "question_name": "applicant name", "field_category": "lookup_name"},
        {"field_id": "reference_id", "field_label": "Reference ID", "question_name": "reference ID", "field_category": "lookup_identifier"},
        {"field_id": "submission_date", "field_label": "Submission Date", "question_name": "submission date", "field_category": "lookup_date"},
        {"field_id": "contact_phone", "field_label": "Phone", "question_name": "phone number", "field_category": "lookup_contact"},
        {"field_id": "contact_email", "field_label": "Email", "question_name": "email address", "field_category": "lookup_contact"},
        {"field_id": "department", "field_label": "Department", "question_name": "department", "field_category": "lookup_name"},
        {"field_id": "city", "field_label": "City", "question_name": "city", "field_category": "lookup_name"},
        {"field_id": "fee_amount", "field_label": "Fee Amount", "question_name": "fee amount", "field_category": "lookup_amount"},
        {"field_id": "reviewer_name", "field_label": "Reviewer", "question_name": "reviewer name", "field_category": "lookup_name"},
    ),
    "invoice_sheet": (
        {"field_id": "vendor_name", "field_label": "Vendor", "question_name": "vendor name", "field_category": "lookup_name"},
        {"field_id": "customer_name", "field_label": "Customer", "question_name": "customer name", "field_category": "lookup_name"},
        {"field_id": "invoice_number", "field_label": "Invoice Number", "question_name": "invoice number", "field_category": "lookup_identifier"},
        {"field_id": "account_id", "field_label": "Account ID", "question_name": "account ID", "field_category": "lookup_identifier"},
        {"field_id": "issue_date", "field_label": "Issue Date", "question_name": "issue date", "field_category": "lookup_date"},
        {"field_id": "due_date", "field_label": "Due Date", "question_name": "due date", "field_category": "lookup_date"},
        {"field_id": "contact_email", "field_label": "Contact Email", "question_name": "contact email", "field_category": "lookup_contact"},
        {"field_id": "contact_phone", "field_label": "Phone", "question_name": "phone number", "field_category": "lookup_contact"},
        {"field_id": "city", "field_label": "City", "question_name": "city", "field_category": "lookup_name"},
        {"field_id": "tax_amount", "field_label": "Tax", "question_name": "tax amount", "field_category": "lookup_amount"},
        {"field_id": "total_due", "field_label": "Total Due", "question_name": "total due", "field_category": "lookup_amount"},
    ),
    "receipt_sheet": (
        {"field_id": "store_name", "field_label": "Store Name", "question_name": "store name", "field_category": "lookup_name"},
        {"field_id": "receipt_number", "field_label": "Receipt No.", "question_name": "receipt number", "field_category": "lookup_identifier"},
        {"field_id": "purchase_date", "field_label": "Purchase Date", "question_name": "purchase date", "field_category": "lookup_date"},
        {"field_id": "cashier_name", "field_label": "Cashier", "question_name": "cashier name", "field_category": "lookup_name"},
        {"field_id": "member_id", "field_label": "Member ID", "question_name": "member ID", "field_category": "lookup_identifier"},
        {"field_id": "contact_phone", "field_label": "Phone", "question_name": "phone number", "field_category": "lookup_contact"},
        {"field_id": "contact_email", "field_label": "Email", "question_name": "email address", "field_category": "lookup_contact"},
        {"field_id": "tax_amount", "field_label": "Tax", "question_name": "tax amount", "field_category": "lookup_amount"},
        {"field_id": "total_paid", "field_label": "Total Paid", "question_name": "total paid", "field_category": "lookup_amount"},
    ),
}
_VALUE_BUILDERS = {
    "form_sheet": build_form_field_values,
    "invoice_sheet": build_invoice_field_values,
    "receipt_sheet": build_receipt_field_values,
}


def resolve_document_task_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic task variant for one documents readout task."""

    return resolve_documents_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DOCUMENT_FIELD_TASK_VARIANTS,
        task_id=str(task_id),
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        balance_flag_key="balanced_task_variant_sampling",
        axis_namespace="task_variant",
    )


def resolve_document_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the visual scene variant for one documents readout task."""

    return resolve_documents_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DOCUMENT_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def resolve_document_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    defaults: DocumentDefaults = DocumentDefaults(),
) -> DocumentRenderParams:
    """Resolve render parameters for structured-document scenes."""

    def _resolve_rgb(key: str, fallback: Sequence[int]) -> Tuple[int, int, int]:
        raw = params.get(key, group_default(render_defaults, key, list(fallback)))
        if not isinstance(raw, Sequence) or len(raw) != 3:
            raise ValueError(f"{key} must resolve to an RGB triple")
        return tuple(int(value) for value in raw)

    return DocumentRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(render_defaults, "canvas_width", defaults.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(render_defaults, "canvas_height", defaults.canvas_height))),
        sheet_page_width_px=int(params.get("sheet_page_width_px", group_default(render_defaults, "sheet_page_width_px", defaults.sheet_page_width_px))),
        sheet_page_height_px=int(params.get("sheet_page_height_px", group_default(render_defaults, "sheet_page_height_px", defaults.sheet_page_height_px))),
        receipt_page_width_px=int(params.get("receipt_page_width_px", group_default(render_defaults, "receipt_page_width_px", defaults.receipt_page_width_px))),
        receipt_page_height_px=int(params.get("receipt_page_height_px", group_default(render_defaults, "receipt_page_height_px", defaults.receipt_page_height_px))),
        page_shadow_offset_px=int(params.get("page_shadow_offset_px", group_default(render_defaults, "page_shadow_offset_px", defaults.page_shadow_offset_px))),
        page_corner_radius_px=int(params.get("page_corner_radius_px", group_default(render_defaults, "page_corner_radius_px", defaults.page_corner_radius_px))),
        field_corner_radius_px=int(params.get("field_corner_radius_px", group_default(render_defaults, "field_corner_radius_px", defaults.field_corner_radius_px))),
        page_outline_width_px=int(params.get("page_outline_width_px", group_default(render_defaults, "page_outline_width_px", defaults.page_outline_width_px))),
        field_outline_width_px=int(params.get("field_outline_width_px", group_default(render_defaults, "field_outline_width_px", defaults.field_outline_width_px))),
        title_font_size_px=int(params.get("title_font_size_px", group_default(render_defaults, "title_font_size_px", defaults.title_font_size_px))),
        section_font_size_px=int(params.get("section_font_size_px", group_default(render_defaults, "section_font_size_px", defaults.section_font_size_px))),
        label_font_size_px=int(params.get("label_font_size_px", group_default(render_defaults, "label_font_size_px", defaults.label_font_size_px))),
        value_font_size_px=int(params.get("value_font_size_px", group_default(render_defaults, "value_font_size_px", defaults.value_font_size_px))),
        page_fill_rgb=_resolve_rgb("page_fill_rgb", defaults.page_fill_rgb),
        page_outline_rgb=_resolve_rgb("page_outline_rgb", defaults.page_outline_rgb),
        page_shadow_rgb=_resolve_rgb("page_shadow_rgb", defaults.page_shadow_rgb),
        field_fill_rgb=_resolve_rgb("field_fill_rgb", defaults.field_fill_rgb),
        field_outline_rgb=_resolve_rgb("field_outline_rgb", defaults.field_outline_rgb),
        label_fill_rgb=_resolve_rgb("label_fill_rgb", defaults.label_fill_rgb),
        label_stroke_rgb=_resolve_rgb("label_stroke_rgb", defaults.label_stroke_rgb),
        value_fill_rgb=_resolve_rgb("value_fill_rgb", defaults.value_fill_rgb),
        divider_rgb=_resolve_rgb("divider_rgb", defaults.divider_rgb),
    )


def build_document_field_lookup_dataset(
    *,
    task_variant: str,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: DocumentDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Build one structured-document field-lookup dataset instance."""

    del params, gen_defaults, defaults
    templates = list(_FIELD_TEMPLATES_BY_SCENE[str(scene_variant)])
    if not templates:
        raise ValueError(f"no field templates configured for scene_variant='{scene_variant}'")

    for attempt in range(64):
        value_rng = spawn_rng(int(instance_seed), f"{task_id}.field_values", index=int(attempt))
        value_builder = _VALUE_BUILDERS[str(scene_variant)]
        value_map = dict(value_builder(value_rng))
        field_specs = []
        seen_values = set()
        for template in templates:
            field_id = str(template["field_id"])
            field_value = str(value_map[field_id]).strip()
            if not field_value:
                break
            if str(field_value) in seen_values:
                break
            seen_values.add(str(field_value))
            field_specs.append(
                {
                    "field_id": field_id,
                    "field_label": str(template["field_label"]),
                    "question_name": str(template["question_name"]),
                    "field_category": str(template["field_category"]),
                    "field_value": field_value,
                    "label_bbox_id": f"{field_id}:label",
                    "value_bbox_id": f"{field_id}:value",
                }
            )
        if len(field_specs) != len(templates):
            continue
        candidates = [spec for spec in field_specs if str(spec["field_category"]) == str(task_variant)]
        if not candidates:
            raise ValueError(f"scene_variant='{scene_variant}' has no fields for task_variant='{task_variant}'")
        query_rng = spawn_rng(int(instance_seed), f"{task_id}.query_field")
        query_field = dict(candidates[int(query_rng.randrange(len(candidates)))])
        question_text = f"What is the {str(query_field['question_name'])}?"
        return {
            "scene_variant": str(scene_variant),
            "task_variant": str(task_variant),
            "scene_title": {
                "form_sheet": "Application Form",
                "invoice_sheet": "Invoice",
                "receipt_sheet": "Receipt",
            }[str(scene_variant)],
            "question_text": str(question_text),
            "field_specs": list(field_specs),
            "query_field_id": str(query_field["field_id"]),
            "query_field_label": str(query_field["field_label"]),
            "query_field_value": str(query_field["field_value"]),
            "query_field_category": str(query_field["field_category"]),
            "query_label_bbox_id": str(query_field["label_bbox_id"]),
            "query_value_bbox_id": str(query_field["value_bbox_id"]),
            "field_count": int(len(field_specs)),
            "field_count_range": [8, 11],
            "question_format": "document_field_lookup",
            "view_family": "structured_document",
        }
    raise ValueError("failed to build a document lookup scene with unique visible field values")


__all__ = [
    "DocumentDefaults",
    "DocumentRenderParams",
    "SUPPORTED_DOCUMENT_FIELD_TASK_VARIANTS",
    "SUPPORTED_DOCUMENT_SCENE_VARIANTS",
    "build_document_field_lookup_dataset",
    "resolve_document_render_params",
    "resolve_document_scene_variant",
    "resolve_document_task_variant",
]
