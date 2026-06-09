"""Database-schema page tasks grounded in entity, field, and relationship semantics."""

from __future__ import annotations

import json
import math
import re
from copy import deepcopy
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.drawing import draw_centered_text, draw_dashed_line, draw_rounded_rect
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import resolve_layout_jitter, resolve_render_int
from ...shared.text_rendering import fit_font_to_box, load_font
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ...shared.text_legibility import draw_text_traced
from ..shared.complexity import (
    build_pages_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_pages_complexity_weights,
)
from ..shared.diagram.common import (
    projected_diagram_bbox_annotation,
    resolve_jittered_diagram_panel_geometry,
    round_diagram_bbox,
)
from ..shared.diagram.visual_defaults import load_diagrams_background_defaults, load_diagrams_noise_defaults
from ..shared.public_query_task import rewrite_pages_query_output


SCENE_ID = "schema"
FIELD_ROLE_COUNT_TASK_ID = "task_pages__schema__field_role_count"
RELATIONSHIP_COUNT_TASK_ID = "task_pages__schema__relationship_count"
RELATIONSHIP_ENDPOINT_TASK_ID = "task_pages__schema__relationship_endpoint_label"
RELATIONSHIP_CARDINALITY_TASK_ID = "task_pages__schema__relationship_cardinality_label"

_LAYOUT_VARIANTS: Tuple[str, ...] = ("grid", "layered", "radial")
_STYLE_VARIANTS: Tuple[str, ...] = (
    "green_erd",
    "violet_cards",
    "monochrome_sql",
    "amber_blueprint",
)
_CONTEXT_VARIANTS: Tuple[str, ...] = (
    "clinic",
    "commerce",
    "event_ops",
    "game_platform",
    "library",
    "training",
)
_FIELD_QUERY_IDS: Tuple[str, ...] = ("all_field_count", "attribute_field_count")
_REL_QUERY_IDS: Tuple[str, ...] = ("total_relationship_count",)
_ENDPOINT_QUERY_IDS: Tuple[str, ...] = ("target_table_for_relationship_label",)
_CARDINALITY_QUERY_IDS: Tuple[str, ...] = ("relationship_cardinality_between_tables",)
_TASK_QUERY_IDS: Dict[str, Tuple[str, ...]] = {
    FIELD_ROLE_COUNT_TASK_ID: _FIELD_QUERY_IDS,
    RELATIONSHIP_COUNT_TASK_ID: _REL_QUERY_IDS,
    RELATIONSHIP_ENDPOINT_TASK_ID: _ENDPOINT_QUERY_IDS,
    RELATIONSHIP_CARDINALITY_TASK_ID: _CARDINALITY_QUERY_IDS,
}
_TASK_KEYS: Dict[str, str] = {
    "all_field_count": "all_field_count_query",
    "attribute_field_count": "attribute_field_count_query",
    "total_relationship_count": "total_relationship_count_query",
    "target_table_for_relationship_label": "relationship_endpoint_label_query",
    "relationship_cardinality_between_tables": "relationship_cardinality_label_query",
}

_CONTEXTS: Dict[str, Dict[str, Any]] = {
    "clinic": {
        "title": "Clinic database schema",
    "tables": {
            "Patient": ["first_name", "last_name", "birth_date", "phone", "email", "insurance_code", "preferred_language"],
            "Doctor": ["first_name", "last_name", "specialty", "license_no", "contact_phone", "active_flag", "shift_code"],
            "Appointment": ["visit_date", "reason", "status", "room_no", "checked_in_at", "duration_min", "triage_level"],
            "MedicalRecord": ["diagnosis", "treatment", "notes", "record_date", "priority", "signed_at", "review_status"],
            "Prescription": ["drug_name", "dosage", "refills", "start_date", "end_date", "instructions", "pharmacy_code"],
            "LabResult": ["test_name", "result_value", "unit", "reported_at", "flag", "sample_code", "reference_range"],
            "Department": ["dept_name", "floor", "phone_ext", "manager_name", "open_hours", "wing", "budget_code"],
            "Invoice": ["invoice_no", "amount_due", "issued_at", "paid_flag", "billing_code", "due_date", "claim_status"],
        },
        "relations": [
            ("Appointment", "Patient", "for"),
            ("Appointment", "Doctor", "scheduled_with"),
            ("MedicalRecord", "Patient", "belongs_to"),
            ("Prescription", "MedicalRecord", "written_for"),
            ("LabResult", "MedicalRecord", "attached_to"),
            ("Doctor", "Department", "member_of"),
            ("Invoice", "Patient", "billed_to"),
            ("Invoice", "Appointment", "covers"),
            ("LabResult", "Patient", "reports_on"),
        ],
    },
    "commerce": {
        "title": "Commerce database schema",
        "tables": {
            "Customer": ["full_name", "email", "tier", "signup_date", "phone", "region", "loyalty_points"],
            "Order": ["order_no", "ordered_at", "status", "ship_method", "subtotal", "tax_amount", "coupon_code"],
            "OrderItem": ["quantity", "unit_price", "discount", "line_status", "packed_flag", "sku_note", "serial_no"],
            "Product": ["sku", "product_name", "category", "list_price", "active_flag", "weight_oz", "brand_name"],
            "Shipment": ["tracking_no", "carrier", "ship_date", "delivery_status", "postage", "zone", "delivery_note"],
            "Payment": ["method", "paid_at", "amount", "authorization_code", "captured_flag", "currency", "processor"],
            "Warehouse": ["warehouse_name", "city", "capacity", "region", "manager_name", "dock_count", "temperature_zone"],
            "ReturnCase": ["case_no", "opened_at", "reason", "resolution", "refund_amount", "closed_flag", "rma_code"],
        },
        "relations": [
            ("Order", "Customer", "placed_by"),
            ("OrderItem", "Order", "part_of"),
            ("OrderItem", "Product", "contains"),
            ("Shipment", "Order", "ships"),
            ("Payment", "Order", "pays_for"),
            ("Product", "Warehouse", "stocked_at"),
            ("ReturnCase", "OrderItem", "returns"),
            ("Shipment", "Warehouse", "sent_from"),
            ("ReturnCase", "Customer", "opened_by"),
        ],
    },
    "event_ops": {
        "title": "Event operations schema",
        "tables": {
            "Event": ["event_name", "event_date", "location", "capacity", "status", "theme", "weather_plan"],
            "Venue": ["venue_name", "address", "room_count", "city", "contact_phone", "max_capacity", "parking_code"],
            "Ticket": ["ticket_code", "price", "seat_label", "sold_at", "ticket_type", "scan_status", "gate_name"],
            "Member": ["member_name", "joined_at", "membership_type", "email", "phone", "status", "renewal_date"],
            "Newsletter": ["issue_title", "sent_date", "topic", "open_rate", "editor", "segment", "subject_line"],
            "Sponsor": ["sponsor_name", "level", "pledge_amount", "contact_name", "logo_status", "sector", "booth_code"],
            "Session": ["session_title", "start_time", "duration_min", "room", "topic", "track", "capacity"],
            "Speaker": ["speaker_name", "affiliation", "bio_status", "rating", "email", "speaker_type", "travel_status"],
        },
        "relations": [
            ("Event", "Venue", "hosted_at"),
            ("Ticket", "Event", "admits_to"),
            ("Newsletter", "Member", "sent_to"),
            ("Member", "Event", "attends"),
            ("Sponsor", "Event", "funds"),
            ("Session", "Event", "included_in"),
            ("Session", "Speaker", "presented_by"),
            ("Ticket", "Member", "held_by"),
            ("Speaker", "Sponsor", "represents"),
        ],
    },
    "game_platform": {
        "title": "Game platform schema",
        "tables": {
            "Player": ["username", "rank_level", "region", "joined_at", "status", "display_name", "avatar_code"],
            "Game": ["game_title", "genre", "release_year", "rating", "platform", "active_flag", "publisher_name"],
            "Match": ["started_at", "duration_sec", "match_status", "map_name", "score_limit", "season_code", "queue_type"],
            "Score": ["points", "combo_count", "achieved_at", "rank_delta", "bonus", "verified_flag", "score_source"],
            "Team": ["team_name", "division", "founded_year", "team_color", "captain_name", "region", "home_server"],
            "Tournament": ["tournament_name", "start_date", "prize_pool", "format", "round_count", "status", "sponsor_code"],
            "Achievement": ["badge_name", "rarity", "earned_points", "created_at", "category", "icon_code", "unlock_rule"],
            "Device": ["device_name", "os_name", "last_seen_at", "client_version", "trusted_flag", "region", "device_token"],
        },
        "relations": [
            ("Match", "Game", "uses"),
            ("Score", "Match", "from_match"),
            ("Score", "Player", "earned_by"),
            ("Player", "Team", "member_of"),
            ("Team", "Tournament", "competes_in"),
            ("Achievement", "Player", "awarded_to"),
            ("Device", "Player", "owned_by"),
            ("Match", "Tournament", "scheduled_for"),
            ("Achievement", "Game", "defined_for"),
        ],
    },
    "library": {
        "title": "Library database schema",
        "tables": {
            "Book": ["title", "isbn", "published_year", "language", "shelf_code", "page_count", "binding_type"],
            "Author": ["author_name", "country", "birth_year", "genre_focus", "agent_name", "active_flag", "award_count"],
            "Publisher": ["publisher_name", "city", "founded_year", "phone", "imprint", "website", "catalog_code"],
            "Borrower": ["borrower_name", "email", "member_since", "status", "phone", "grade_level", "card_status"],
            "Loan": ["loan_date", "due_date", "returned_at", "renewal_count", "fine_amount", "loan_status", "checkout_desk"],
            "LibrarySection": ["section_name", "floor", "aisle", "capacity", "curator", "open_flag", "quiet_zone"],
            "HoldRequest": ["requested_at", "expires_at", "queue_position", "request_status", "notify_flag", "pickup_code", "priority"],
            "Review": ["rating", "review_text", "posted_at", "helpful_count", "visibility", "source", "moderation_status"],
        },
        "relations": [
            ("Book", "Author", "written_by"),
            ("Book", "Publisher", "published_by"),
            ("Book", "LibrarySection", "located_in"),
            ("Loan", "Book", "borrows"),
            ("Loan", "Borrower", "checked_out_by"),
            ("HoldRequest", "Book", "reserves"),
            ("HoldRequest", "Borrower", "requested_by"),
            ("Review", "Book", "reviews"),
            ("Review", "Borrower", "written_by"),
        ],
    },
    "training": {
        "title": "Training program schema",
        "tables": {
            "Athlete": ["athlete_name", "birth_date", "level", "email", "dominant_side", "status", "jersey_no"],
            "Coach": ["coach_name", "certification", "phone", "specialty", "hire_date", "active_flag", "license_code"],
            "TrainingSession": ["session_date", "start_time", "duration_min", "focus_area", "intensity", "notes", "weather"],
            "WorkoutPlan": ["plan_name", "created_at", "cycle_length", "goal", "version_no", "approved_flag", "plan_status"],
            "Exercise": ["exercise_name", "category", "target_area", "equipment", "default_reps", "difficulty", "tempo"],
            "Feedback": ["comment", "score", "created_at", "mood", "follow_up", "reviewed_flag", "coach_note"],
            "ProgressMetric": ["metric_name", "value", "unit", "measured_at", "trend", "baseline_value", "goal_value"],
            "Team": ["team_name", "age_group", "division", "season", "color", "region", "practice_field"],
        },
        "relations": [
            ("TrainingSession", "Athlete", "for_athlete"),
            ("TrainingSession", "Coach", "led_by"),
            ("TrainingSession", "WorkoutPlan", "uses_plan"),
            ("WorkoutPlan", "Exercise", "contains"),
            ("Feedback", "TrainingSession", "about"),
            ("Feedback", "Coach", "written_by"),
            ("ProgressMetric", "Athlete", "measures"),
            ("Athlete", "Team", "plays_for"),
            ("Coach", "Team", "coaches"),
        ],
    },
}

_FIELD_TYPES: Tuple[str, ...] = ("int", "str", "date", "bool", "float", "time")
_CARDINALITY_SPECS: Dict[str, Dict[str, str]] = {
    "one_to_many": {
        "description": "one-to-many",
        "source_marker": "*",
        "target_marker": "1",
    },
    "optional_many": {
        "description": "optional-many",
        "source_marker": "0..*",
        "target_marker": "1",
    },
    "one_to_one": {
        "description": "one-to-one",
        "source_marker": "1",
        "target_marker": "1",
    },
}
_CARDINALITY_ORDER: Tuple[str, ...] = ("one_to_many", "optional_many", "one_to_one")

_STYLE_PALETTES: Dict[str, Dict[str, Any]] = {
    "green_erd": {
        "panel_fill": (248, 252, 246),
        "panel_border": (69, 110, 77),
        "title": (31, 67, 45),
        "table_fill": (255, 255, 252),
        "table_alt": (244, 251, 242),
        "header_fill": (196, 224, 177),
        "header_text": (23, 59, 35),
        "row_text": (28, 43, 34),
        "muted_text": (78, 92, 82),
        "border": (75, 119, 78),
        "edge": (84, 111, 81),
        "label_fill": (255, 255, 250),
    },
    "violet_cards": {
        "panel_fill": (252, 249, 255),
        "panel_border": (101, 82, 142),
        "title": (57, 45, 93),
        "table_fill": (255, 255, 255),
        "table_alt": (247, 243, 255),
        "header_fill": (218, 208, 248),
        "header_text": (50, 40, 87),
        "row_text": (37, 33, 55),
        "muted_text": (91, 82, 116),
        "border": (105, 89, 160),
        "edge": (94, 86, 134),
        "label_fill": (255, 255, 255),
    },
    "monochrome_sql": {
        "panel_fill": (248, 248, 246),
        "panel_border": (66, 69, 73),
        "title": (29, 32, 36),
        "table_fill": (255, 255, 255),
        "table_alt": (241, 243, 244),
        "header_fill": (218, 222, 226),
        "header_text": (27, 31, 35),
        "row_text": (30, 34, 38),
        "muted_text": (82, 87, 92),
        "border": (74, 78, 84),
        "edge": (71, 76, 82),
        "label_fill": (255, 255, 255),
    },
    "amber_blueprint": {
        "panel_fill": (255, 250, 239),
        "panel_border": (121, 83, 49),
        "title": (70, 47, 32),
        "table_fill": (255, 255, 251),
        "table_alt": (255, 246, 226),
        "header_fill": (244, 204, 139),
        "header_text": (68, 44, 20),
        "row_text": (45, 35, 27),
        "muted_text": (104, 80, 55),
        "border": (133, 91, 54),
        "edge": (116, 88, 64),
        "label_fill": (255, 252, 243),
    },
}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("pages", "schema")
POST_IMAGE_BACKGROUND_DEFAULTS = load_diagrams_background_defaults(task_group="schema")
POST_IMAGE_NOISE_DEFAULTS = load_diagrams_noise_defaults(task_group="schema", apply_prob=0.35)


def _resolve_defaults_for_task(task_id: str) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        task_id=str(task_id),
    )
    weights = resolve_pages_complexity_weights(
        _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        task_id=str(task_id),
    )
    return gen_defaults, render_defaults, prompt_defaults, weights


def _snake_case(label: str) -> str:
    text = re.sub(r"(?<!^)(?=[A-Z])", "_", str(label)).replace(" ", "_")
    return re.sub(r"[^a-z0-9_]+", "", text.lower()).strip("_")


def _infer_field_type(field_name: str, rng) -> str:
    name = str(field_name).lower()
    if name.endswith("_id") or "count" in name or "year" in name or "capacity" in name or "level" in name:
        return "int"
    if "date" in name or name.endswith("_at") or "since" in name or "opened" in name or "closed" in name:
        return "date"
    if name.endswith("_flag") or name.startswith("active") or name.endswith("status_flag"):
        return "bool"
    if "amount" in name or "price" in name or "rate" in name or "rating" in name or "value" in name:
        return "float"
    return str(rng.choice(_FIELD_TYPES[:3]))


def _resolve_axis(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    supported_values: Sequence[str],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    instance_seed: int,
    task_id: str,
    namespace: str,
) -> tuple[str, Dict[str, float]]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.{namespace}")
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=gen_defaults,
        supported_variants=[str(value) for value in supported_values],
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
    )
    balanced = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=[str(value) for value in supported_values],
        balance_flag_key=str(balance_flag_key),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        sampling_namespace=f"{task_id}:{namespace}",
    )
    return str(balanced), {str(key): float(value) for key, value in probabilities.items()}


def _draw_text_in_box(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    text: str,
    max_size_px: int,
    min_size_px: int,
    fill: Sequence[int],
    bold: bool = True,
    stroke_fill: Sequence[int] = (255, 255, 255),
    padding_px: int = 4,
    align: str = "center",
) -> list[float]:
    left, top, right, bottom = [float(value) for value in bbox]
    font = fit_font_to_box(
        draw,
        text=str(text),
        max_width=max(1.0, float(right - left - (2 * int(padding_px)))),
        max_height=max(1.0, float(bottom - top - (2 * int(padding_px)))),
        bold=bool(bold),
        min_size_px=int(min_size_px),
        max_size_px=int(max_size_px),
        fill_ratio=0.94,
    )
    if str(align) == "left":
        tb = draw.textbbox((0, 0), str(text), font=font, stroke_width=1)
        tx = float(left + int(padding_px))
        ty = float(top + (0.5 * (bottom - top - (float(tb[3]) - float(tb[1])))) - float(tb[1]))
        draw_text_traced(draw,
            (tx, ty),
            str(text),
            font=font,
            fill=tuple(int(value) for value in fill),
            stroke_width=1,
            stroke_fill=tuple(int(value) for value in stroke_fill),
         role="readout", required=False,)
        return [
            round(float(tx + tb[0]), 3),
            round(float(ty + tb[1]), 3),
            round(float(tx + tb[2]), 3),
            round(float(ty + tb[3]), 3),
        ]
    return draw_centered_text(
        draw,
        text=str(text),
        center=(0.5 * (float(left) + float(right)), 0.5 * (float(top) + float(bottom))),
        font=font,
        fill=tuple(int(value) for value in fill),
        stroke_fill=tuple(int(value) for value in stroke_fill),
        stroke_width=1,
    )


def _union_bbox(bboxes: Iterable[Sequence[float]], *, padding: float = 0.0) -> list[float]:
    resolved = [[float(value) for value in bbox] for bbox in bboxes if len(bbox) >= 4]
    if not resolved:
        return [0.0, 0.0, 0.0, 0.0]
    return [
        round(min(bbox[0] for bbox in resolved) - float(padding), 3),
        round(min(bbox[1] for bbox in resolved) - float(padding), 3),
        round(max(bbox[2] for bbox in resolved) + float(padding), 3),
        round(max(bbox[3] for bbox in resolved) + float(padding), 3),
    ]


def _point_bbox(points: Sequence[tuple[float, float]], *, padding: float = 0.0) -> list[float]:
    if not points:
        return [0.0, 0.0, 0.0, 0.0]
    return [
        round(min(float(point[0]) for point in points) - float(padding), 3),
        round(min(float(point[1]) for point in points) - float(padding), 3),
        round(max(float(point[0]) for point in points) + float(padding), 3),
        round(max(float(point[1]) for point in points) + float(padding), 3),
    ]


def _rounded_point(point: Sequence[float]) -> list[float]:
    return [round(float(value), 3) for value in point[:2]]


def _build_tables_and_relationships(
    *,
    rng,
    context: Mapping[str, Any],
    table_count: int,
    field_count_min: int,
    field_count_max: int,
    relationship_count_min: int,
    relationship_count_max: int,
    target_relationship_count: int | None = None,
) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]]]:
    table_items = list((context.get("tables") or {}).items())
    if int(table_count) > len(table_items):
        raise ValueError("table_count exceeds available schema context tables")
    selected = rng.sample(table_items, int(table_count))

    tables: list[Dict[str, Any]] = []
    for index, (label, attr_pool) in enumerate(selected):
        table_id = f"t{index}"
        table_slug = _snake_case(str(label))
        max_attr_count = max(1, int(field_count_max) - 1)
        min_attr_count = max(1, int(field_count_min) - 1)
        attr_count = int(rng.randint(min_attr_count, max_attr_count))
        attrs = rng.sample(list(attr_pool), min(attr_count, len(attr_pool)))
        fields: list[Dict[str, Any]] = [
            {
                "field_id": f"{table_id}.pk",
                "table_id": table_id,
                "name": f"{table_slug}_id",
                "type": "int",
                "role": "PK",
                "references_table_id": None,
            }
        ]
        for attr_index, attr_name in enumerate(attrs):
            fields.append(
                {
                    "field_id": f"{table_id}.a{attr_index}",
                    "table_id": table_id,
                    "name": str(attr_name),
                    "type": _infer_field_type(str(attr_name), rng),
                    "role": "ATTR",
                    "references_table_id": None,
                }
            )
        tables.append(
            {
                "table_id": table_id,
                "label": str(label),
                "slug": table_slug,
                "fields": fields,
            }
        )

    table_by_label = {str(table["label"]): table for table in tables}
    table_by_id = {str(table["table_id"]): table for table in tables}
    candidate_relations = [
        item for item in list(context.get("relations") or [])
        if str(item[0]) in table_by_label and str(item[1]) in table_by_label
    ]
    rng.shuffle(candidate_relations)
    max_possible = max(1, len(candidate_relations))
    if target_relationship_count is not None:
        rel_count = max(
            1,
            min(
                max_possible,
                int(relationship_count_max),
                max(int(relationship_count_min), int(target_relationship_count)),
            ),
        )
    else:
        rel_count = min(max_possible, int(rng.randint(int(relationship_count_min), int(relationship_count_max))))
    selected_relations = candidate_relations[:rel_count]
    if not selected_relations and len(tables) >= 2:
        selected_relations = [(tables[0]["label"], tables[1]["label"], "relates_to")]

    relationships: list[Dict[str, Any]] = []
    for rel_index, (source_label, target_label, rel_label) in enumerate(selected_relations):
        source = table_by_label[str(source_label)]
        target = table_by_label[str(target_label)]
        source_id = str(source["table_id"])
        target_id = str(target["table_id"])
        fk_name = f"{target['slug']}_id"
        existing_fk = next(
            (
                field for field in source["fields"]
                if str(field["role"]) == "FK" and str(field.get("references_table_id")) == target_id
            ),
            None,
        )
        if existing_fk is None:
            fk_field = {
                "field_id": f"{source_id}.fk{rel_index}",
                "table_id": source_id,
                "name": fk_name,
                "type": "int",
                "role": "FK",
                "references_table_id": target_id,
            }
            source["fields"].append(fk_field)
        else:
            fk_field = existing_fk
        cardinality_kind = _CARDINALITY_ORDER[int(rel_index) % len(_CARDINALITY_ORDER)]
        relationships.append(
            {
                "relationship_id": f"r{rel_index}",
                "source_table_id": source_id,
                "target_table_id": target_id,
                "source_label": str(source_label),
                "target_label": str(target_label),
                "label": str(rel_label),
                "source_field_id": str(fk_field["field_id"]),
                "target_field_id": str(table_by_id[target_id]["fields"][0]["field_id"]),
                "cardinality_kind": cardinality_kind,
                "source_marker": _CARDINALITY_SPECS[cardinality_kind]["source_marker"],
                "target_marker": _CARDINALITY_SPECS[cardinality_kind]["target_marker"],
            }
        )

    return tables, relationships


def _resolve_scene_geometry(
    *,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> tuple[int, int, tuple[float, float, float, float], tuple[float, float, float, float], tuple[float, float, float, float], Dict[str, Any]]:
    canvas_width = resolve_render_int(
        params,
        render_defaults,
        "canvas_width",
        1300,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.render",
    )
    canvas_height = resolve_render_int(
        params,
        render_defaults,
        "canvas_height",
        950,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.render",
    )
    outer_margin = resolve_render_int(
        params,
        render_defaults,
        "outer_margin_px",
        44,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.render",
    )
    title_band = resolve_render_int(
        params,
        render_defaults,
        "title_band_height_px",
        62,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.render",
    )
    panel_padding = resolve_render_int(
        params,
        render_defaults,
        "panel_padding_px",
        24,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.render",
    )
    jitter = resolve_layout_jitter(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.schema",
    )
    panel, title_bbox, content, jitter_meta = resolve_jittered_diagram_panel_geometry(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        outer_margin_px=int(outer_margin),
        title_band_height_px=int(title_band),
        panel_padding_px=int(panel_padding),
        layout_jitter_meta=jitter,
    )
    return int(canvas_width), int(canvas_height), panel, title_bbox, content, jitter_meta


def _table_height(*, field_count: int, render_defaults: Mapping[str, Any]) -> float:
    header_h = float(group_default(render_defaults, "table_header_height_px", 34))
    row_h = float(group_default(render_defaults, "field_row_height_px", 24))
    return float(header_h + (row_h * int(field_count)))


def _assign_table_layout(
    *,
    tables: list[Dict[str, Any]],
    relationships: list[Dict[str, Any]],
    content_bbox: Sequence[float],
    layout_variant: str,
    render_defaults: Mapping[str, Any],
) -> None:
    del relationships
    left, top, right, bottom = [float(value) for value in content_bbox]
    n = max(1, len(tables))
    table_w_base = float(group_default(render_defaults, "table_width_px", 188))
    max_table_w = float(group_default(render_defaults, "table_width_max_px", 218))
    min_table_w = float(group_default(render_defaults, "table_width_min_px", 164))
    if str(layout_variant) == "radial":
        cx = 0.5 * (left + right)
        cy = 0.5 * (top + bottom)
        radius_x = max(150.0, 0.39 * (right - left))
        radius_y = max(130.0, 0.34 * (bottom - top))
        for idx, table in enumerate(tables):
            angle = (-math.pi / 2.0) + (2.0 * math.pi * float(idx) / float(n))
            field_count = len(table["fields"])
            table_h = _table_height(field_count=field_count, render_defaults=render_defaults)
            table_w = max(min_table_w, min(max_table_w, table_w_base))
            tx = cx + (radius_x * math.cos(angle))
            ty = cy + (radius_y * math.sin(angle))
            x0 = max(left + 4.0, min(right - table_w - 4.0, tx - (0.5 * table_w)))
            y0 = max(top + 4.0, min(bottom - table_h - 4.0, ty - (0.5 * table_h)))
            table["bbox"] = [round(x0, 3), round(y0, 3), round(x0 + table_w, 3), round(y0 + table_h, 3)]
        return

    if str(layout_variant) == "layered":
        cols = min(3, max(2, int(math.ceil(math.sqrt(n)))))
    else:
        cols = min(4, max(2, int(math.ceil(math.sqrt(n * 1.18)))))
    rows = int(math.ceil(float(n) / float(cols)))
    cell_w = float(right - left) / float(cols)
    cell_h = float(bottom - top) / float(rows)
    for idx, table in enumerate(tables):
        col = int(idx % cols)
        row = int(idx // cols)
        if str(layout_variant) == "layered" and rows > 1 and col % 2 == 1:
            y_shift = 0.12 * cell_h
        else:
            y_shift = 0.0
        field_count = len(table["fields"])
        table_h = _table_height(field_count=field_count, render_defaults=render_defaults)
        table_w = max(min_table_w, min(max_table_w, min(table_w_base, cell_w * 0.78)))
        x0 = left + (col * cell_w) + (0.5 * (cell_w - table_w))
        y0 = top + (row * cell_h) + (0.5 * (cell_h - table_h)) + y_shift
        y0 = max(top + 3.0, min(bottom - table_h - 3.0, y0))
        table["bbox"] = [round(x0, 3), round(y0, 3), round(x0 + table_w, 3), round(y0 + table_h, 3)]


def _anchor_point(source_bbox: Sequence[float], target_bbox: Sequence[float]) -> tuple[float, float]:
    sx0, sy0, sx1, sy1 = [float(value) for value in source_bbox]
    tx0, ty0, tx1, ty1 = [float(value) for value in target_bbox]
    scx = 0.5 * (sx0 + sx1)
    scy = 0.5 * (sy0 + sy1)
    tcx = 0.5 * (tx0 + tx1)
    tcy = 0.5 * (ty0 + ty1)
    dx = tcx - scx
    dy = tcy - scy
    if abs(dx) / max(1.0, sx1 - sx0) > abs(dy) / max(1.0, sy1 - sy0):
        return (sx1 if dx >= 0 else sx0, scy)
    return (scx, sy1 if dy >= 0 else sy0)


def _edge_points(
    *,
    source_bbox: Sequence[float],
    target_bbox: Sequence[float],
    layout_variant: str,
    relationship_index: int,
) -> list[tuple[float, float]]:
    start = _anchor_point(source_bbox, target_bbox)
    end = _anchor_point(target_bbox, source_bbox)
    if str(layout_variant) == "radial":
        sx, sy = start
        ex, ey = end
        mx = 0.5 * (sx + ex)
        my = 0.5 * (sy + ey)
        dx = ex - sx
        dy = ey - sy
        length = max(1.0, math.hypot(dx, dy))
        offset = (28.0 if int(relationship_index) % 2 == 0 else -28.0)
        control = (mx + ((-dy / length) * offset), my + ((dx / length) * offset))
        points: list[tuple[float, float]] = []
        for step in range(9):
            t = float(step) / 8.0
            x = ((1 - t) ** 2 * sx) + (2 * (1 - t) * t * control[0]) + (t ** 2 * ex)
            y = ((1 - t) ** 2 * sy) + (2 * (1 - t) * t * control[1]) + (t ** 2 * ey)
            points.append((float(x), float(y)))
        return points
    sx, sy = start
    ex, ey = end
    if abs(sx - ex) < 12.0 or abs(sy - ey) < 12.0:
        return [start, end]
    if str(layout_variant) == "layered":
        mid_x = 0.5 * (sx + ex)
        return [start, (mid_x, sy), (mid_x, ey), end]
    mid_y = 0.5 * (sy + ey)
    return [start, (sx, mid_y), (ex, mid_y), end]


def _draw_polyline(
    draw: ImageDraw.ImageDraw,
    *,
    points: Sequence[tuple[float, float]],
    fill: Sequence[int],
    width: int,
    dashed: bool,
) -> list[float]:
    clean = [(float(x), float(y)) for x, y in points]
    if len(clean) < 2:
        return [0.0, 0.0, 0.0, 0.0]
    for start, end in zip(clean, clean[1:]):
        if dashed:
            draw_dashed_line(
                draw,
                start=start,
                end=end,
                fill=fill,
                width=max(1, int(width)),
                dash_px=9.0,
                gap_px=6.0,
            )
        else:
            draw.line([start, end], fill=tuple(int(value) for value in fill), width=max(1, int(width)))
    return _point_bbox(clean, padding=max(8.0, float(width) + 5.0))


def _relationship_label_bbox(points: Sequence[tuple[float, float]], label: str, *, index: int) -> list[float]:
    if not points:
        return [0.0, 0.0, 0.0, 0.0]
    point = points[len(points) // 2]
    width = max(58.0, min(122.0, 8.6 * len(str(label)) + 20.0))
    height = 24.0
    x_offset = 0.0
    y_offset = -16.0 if int(index) % 2 == 0 else 16.0
    return [
        round(float(point[0]) - (0.5 * width) + x_offset, 3),
        round(float(point[1]) - (0.5 * height) + y_offset, 3),
        round(float(point[0]) + (0.5 * width) + x_offset, 3),
        round(float(point[1]) + (0.5 * height) + y_offset, 3),
    ]


def _draw_marker(
    draw: ImageDraw.ImageDraw,
    *,
    center: tuple[float, float],
    text: str,
    palette: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
) -> list[float]:
    width = max(24.0, min(38.0, 8.0 * len(str(text)) + 10.0))
    height = 20.0
    cx, cy = center
    bbox = [float(cx - (0.5 * width)), float(cy - (0.5 * height)), float(cx + (0.5 * width)), float(cy + (0.5 * height))]
    draw.rounded_rectangle(
        tuple(bbox),
        radius=8,
        fill=tuple(int(value) for value in palette["label_fill"]),
        outline=tuple(int(value) for value in palette["edge"]),
        width=1,
    )
    _draw_text_in_box(
        draw,
        bbox=bbox,
        text=str(text),
        max_size_px=int(group_default(render_defaults, "marker_font_size_px", 12)),
        min_size_px=8,
        fill=palette["row_text"],
        bold=True,
        stroke_fill=palette["label_fill"],
        padding_px=3,
    )
    return round_diagram_bbox(bbox)


def _draw_table(
    draw: ImageDraw.ImageDraw,
    *,
    table: Mapping[str, Any],
    palette: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    style_variant: str,
) -> tuple[list[float], Dict[str, list[float]]]:
    bbox = [float(value) for value in table["bbox"]]
    left, top, right, bottom = bbox
    header_h = float(group_default(render_defaults, "table_header_height_px", 34))
    row_h = float(group_default(render_defaults, "field_row_height_px", 24))
    radius = int(group_default(render_defaults, "table_corner_radius_px", 10))
    border_width = int(group_default(render_defaults, "table_border_width_px", 2))
    if str(style_variant) == "monochrome_sql":
        draw.rectangle(tuple(bbox), fill=tuple(palette["table_fill"]), outline=tuple(palette["border"]), width=border_width)
    else:
        draw_rounded_rect(
            draw,
            tuple(bbox),
            radius=radius,
            fill=palette["table_fill"],
            outline=palette["border"],
            width=border_width,
        )
    header_bbox = [left, top, right, top + header_h]
    if str(style_variant) == "monochrome_sql":
        draw.rectangle(tuple(header_bbox), fill=tuple(palette["header_fill"]), outline=tuple(palette["border"]), width=1)
    else:
        draw.rounded_rectangle(
            tuple(header_bbox),
            radius=radius,
            fill=tuple(palette["header_fill"]),
            outline=tuple(palette["border"]),
            width=1,
        )
        draw.rectangle((left, top + (header_h * 0.55), right, top + header_h), fill=tuple(palette["header_fill"]))
        draw.line((left, top + header_h, right, top + header_h), fill=tuple(palette["border"]), width=1)
    _draw_text_in_box(
        draw,
        bbox=header_bbox,
        text=str(table["label"]),
        max_size_px=int(group_default(render_defaults, "table_header_font_size_px", 17)),
        min_size_px=10,
        fill=palette["header_text"],
        bold=True,
        stroke_fill=palette["header_fill"],
        padding_px=6,
    )
    field_bboxes: Dict[str, list[float]] = {}
    for index, field in enumerate(table["fields"]):
        row_top = top + header_h + (index * row_h)
        row_bbox = [left, row_top, right, min(bottom, row_top + row_h)]
        fill = palette["table_alt"] if int(index) % 2 else palette["table_fill"]
        draw.rectangle(tuple(row_bbox), fill=tuple(fill), outline=tuple(palette["border"]), width=1)
        type_bbox = [left + 5.0, row_top + 2.0, left + 37.0, row_top + row_h - 2.0]
        role_bbox = [right - 36.0, row_top + 3.0, right - 5.0, row_top + row_h - 3.0]
        name_bbox = [left + 40.0, row_top + 2.0, right - 39.0, row_top + row_h - 2.0]
        _draw_text_in_box(
            draw,
            bbox=type_bbox,
            text=str(field["type"]),
            max_size_px=int(group_default(render_defaults, "field_type_font_size_px", 10)),
            min_size_px=7,
            fill=palette["muted_text"],
            bold=False,
            stroke_fill=fill,
            padding_px=1,
        )
        _draw_text_in_box(
            draw,
            bbox=name_bbox,
            text=str(field["name"]),
            max_size_px=int(group_default(render_defaults, "field_font_size_px", 13)),
            min_size_px=8,
            fill=palette["row_text"],
            bold=False,
            stroke_fill=fill,
            padding_px=2,
            align="left",
        )
        role = str(field["role"])
        if role in {"PK", "FK"}:
            role_fill = (255, 244, 191) if role == "PK" else (224, 236, 255)
            draw.rounded_rectangle(tuple(role_bbox), radius=6, fill=role_fill, outline=tuple(palette["border"]), width=1)
            _draw_text_in_box(
                draw,
                bbox=role_bbox,
                text=role,
                max_size_px=int(group_default(render_defaults, "role_font_size_px", 10)),
                min_size_px=7,
                fill=palette["row_text"],
                bold=True,
                stroke_fill=role_fill,
                padding_px=2,
            )
        field_bboxes[str(field["field_id"])] = round_diagram_bbox(row_bbox)
    return round_diagram_bbox(bbox), field_bboxes


def _render_scene(
    *,
    base_image: Image.Image,
    title: str,
    tables: list[Dict[str, Any]],
    relationships: list[Dict[str, Any]],
    panel_bbox: Sequence[float],
    title_bbox: Sequence[float],
    layout_variant: str,
    style_variant: str,
    render_defaults: Mapping[str, Any],
) -> tuple[Image.Image, Dict[str, Any]]:
    image = base_image.convert("RGB")
    draw = ImageDraw.Draw(image)
    palette = _STYLE_PALETTES[str(style_variant)]
    panel_radius = int(group_default(render_defaults, "panel_corner_radius_px", 22))
    draw_rounded_rect(
        draw,
        tuple(float(value) for value in panel_bbox),
        radius=panel_radius,
        fill=palette["panel_fill"],
        outline=palette["panel_border"],
        width=2,
    )
    _draw_text_in_box(
        draw,
        bbox=title_bbox,
        text=str(title),
        max_size_px=int(group_default(render_defaults, "title_font_size_px", 28)),
        min_size_px=14,
        fill=palette["title"],
        bold=True,
        stroke_fill=palette["panel_fill"],
        padding_px=12,
    )
    table_by_id = {str(table["table_id"]): table for table in tables}
    relationship_bboxes: Dict[str, list[float]] = {}
    relationship_point_pairs: Dict[str, list[list[float]]] = {}
    relationship_polylines: Dict[str, list[list[float]]] = {}
    relationship_label_bboxes: Dict[str, list[float]] = {}
    marker_bboxes: Dict[str, list[float]] = {}
    edge_width = int(group_default(render_defaults, "relationship_width_px", 3))

    for index, relationship in enumerate(relationships):
        source = table_by_id[str(relationship["source_table_id"])]
        target = table_by_id[str(relationship["target_table_id"])]
        points = _edge_points(
            source_bbox=source["bbox"],
            target_bbox=target["bbox"],
            layout_variant=str(layout_variant),
            relationship_index=int(index),
        )
        rounded_points = [_rounded_point((x, y)) for x, y in points]
        relationship["points"] = [tuple(point) for point in rounded_points]
        relationship_point_pairs[str(relationship["relationship_id"])] = [
            list(rounded_points[0]),
            list(rounded_points[-1]),
        ]
        relationship_polylines[str(relationship["relationship_id"])] = [list(point) for point in rounded_points]
        dashed = str(relationship["cardinality_kind"]) == "optional_many"
        edge_bbox = _draw_polyline(
            draw,
            points=points,
            fill=palette["edge"],
            width=edge_width,
            dashed=dashed,
        )
        relationship_bboxes[str(relationship["relationship_id"])] = edge_bbox

    table_bboxes: Dict[str, list[float]] = {}
    field_bboxes: Dict[str, list[float]] = {}
    for table in tables:
        table_bbox, per_field = _draw_table(
            draw,
            table=table,
            palette=palette,
            render_defaults=render_defaults,
            style_variant=str(style_variant),
        )
        table_bboxes[str(table["table_id"])] = table_bbox
        field_bboxes.update(per_field)

    for index, relationship in enumerate(relationships):
        points = list(relationship.get("points") or [])
        if not points:
            continue
        label_bbox = _relationship_label_bbox(points, str(relationship["label"]), index=int(index))
        draw.rounded_rectangle(
            tuple(label_bbox),
            radius=8,
            fill=tuple(palette["label_fill"]),
            outline=tuple(palette["edge"]),
            width=1,
        )
        _draw_text_in_box(
            draw,
            bbox=label_bbox,
            text=str(relationship["label"]),
            max_size_px=int(group_default(render_defaults, "relationship_label_font_size_px", 12)),
            min_size_px=7,
            fill=palette["row_text"],
            bold=True,
            stroke_fill=palette["label_fill"],
            padding_px=3,
        )
        relationship_label_bboxes[str(relationship["relationship_id"])] = round_diagram_bbox(label_bbox)
        first = points[0]
        last = points[-1]
        source_marker = _draw_marker(
            draw,
            center=(float(first[0]), float(first[1])),
            text=str(relationship["source_marker"]),
            palette=palette,
            render_defaults=render_defaults,
        )
        target_marker = _draw_marker(
            draw,
            center=(float(last[0]), float(last[1])),
            text=str(relationship["target_marker"]),
            palette=palette,
            render_defaults=render_defaults,
        )
        marker_bboxes[f"{relationship['relationship_id']}:source"] = source_marker
        marker_bboxes[f"{relationship['relationship_id']}:target"] = target_marker

    return image, {
        "table_bboxes_px": dict(table_bboxes),
        "field_bboxes_px": dict(field_bboxes),
        "relationship_bboxes_px": dict(relationship_bboxes),
        "relationship_point_pairs_px": dict(relationship_point_pairs),
        "relationship_polylines_px": dict(relationship_polylines),
        "relationship_label_bboxes_px": dict(relationship_label_bboxes),
        "cardinality_marker_bboxes_px": dict(marker_bboxes),
    }


def _relationship_degree_map(relationships: Sequence[Mapping[str, Any]]) -> Dict[str, list[Dict[str, Any]]]:
    degree: Dict[str, list[Dict[str, Any]]] = {}
    for relationship in relationships:
        for table_id in (str(relationship["source_table_id"]), str(relationship["target_table_id"])):
            degree.setdefault(table_id, []).append(dict(relationship))
    return degree


def _bbox_area(bbox: Sequence[float]) -> float:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def _bbox_intersection_area(a: Sequence[float], b: Sequence[float]) -> float:
    ax0, ay0, ax1, ay1 = [float(value) for value in a]
    bx0, by0, bx1, by1 = [float(value) for value in b]
    return max(0.0, min(ax1, bx1) - max(ax0, bx0)) * max(0.0, min(ay1, by1) - max(ay0, by0))


def _relationship_label_overlap_score(
    *,
    label_bbox: Sequence[float],
    table_bboxes: Sequence[Sequence[float]],
) -> float:
    label_area = max(1.0, _bbox_area(label_bbox))
    overlap = sum(_bbox_intersection_area(label_bbox, table_bbox) for table_bbox in table_bboxes)
    return round(float(overlap) / float(label_area), 6)


def _select_relationship_endpoint_query(
    *,
    query_id: str,
    rng,
    tables: Sequence[Mapping[str, Any]],
    relationships: Sequence[Mapping[str, Any]],
    layout_variant: str,
    answer_index: int,
) -> Dict[str, Any]:
    table_by_id = {str(table["table_id"]): dict(table) for table in tables}
    relation_key_counts: Dict[tuple[str, str], int] = {}
    for relationship in relationships:
        key = (str(relationship["source_label"]), str(relationship["label"]))
        relation_key_counts[key] = relation_key_counts.get(key, 0) + 1

    scored: list[tuple[float, str, str, str, int, Dict[str, Any], list[float]]] = []
    all_table_bboxes = [list(table["bbox"]) for table in table_by_id.values()]
    for index, relationship in enumerate(relationships):
        source_id = str(relationship["source_table_id"])
        target_id = str(relationship["target_table_id"])
        if source_id not in table_by_id or target_id not in table_by_id:
            continue
        key = (str(relationship["source_label"]), str(relationship["label"]))
        if relation_key_counts.get(key, 0) != 1:
            continue
        points = _edge_points(
            source_bbox=table_by_id[source_id]["bbox"],
            target_bbox=table_by_id[target_id]["bbox"],
            layout_variant=str(layout_variant),
            relationship_index=int(index),
        )
        label_bbox = round_diagram_bbox(
            _relationship_label_bbox(points, str(relationship["label"]), index=int(index))
        )
        scored.append(
            (
                _relationship_label_overlap_score(label_bbox=label_bbox, table_bboxes=all_table_bboxes),
                str(relationship["source_label"]),
                str(relationship["label"]),
                str(relationship["target_label"]),
                int(index),
                dict(relationship),
                list(label_bbox),
            )
        )
    if not scored:
        for index, relationship in enumerate(relationships):
            source_id = str(relationship["source_table_id"])
            target_id = str(relationship["target_table_id"])
            if source_id not in table_by_id or target_id not in table_by_id:
                continue
            points = _edge_points(
                source_bbox=table_by_id[source_id]["bbox"],
                target_bbox=table_by_id[target_id]["bbox"],
                layout_variant=str(layout_variant),
                relationship_index=int(index),
            )
            label_bbox = round_diagram_bbox(
                _relationship_label_bbox(points, str(relationship["label"]), index=int(index))
            )
            scored.append(
                (
                    _relationship_label_overlap_score(label_bbox=label_bbox, table_bboxes=all_table_bboxes),
                    str(relationship["source_label"]),
                    str(relationship["label"]),
                    str(relationship["target_label"]),
                    int(index),
                    dict(relationship),
                    list(label_bbox),
                )
            )
    if not scored:
        raise ValueError("schema endpoint query requires at least one relationship")

    scored.sort(key=lambda item: (item[0], item[1], item[2], item[3], item[4]))
    best_score = float(scored[0][0])
    low_overlap_candidates = [item for item in scored if float(item[0]) == best_score]
    _, _, _, _, relationship_index, selected, label_bbox = low_overlap_candidates[
        int(abs(int(answer_index)) + rng.randrange(max(1, len(low_overlap_candidates)))) % len(low_overlap_candidates)
    ]
    return {
        "query_id": str(query_id),
        "task_key": _TASK_KEYS[str(query_id)],
        "relationship_id": str(selected["relationship_id"]),
        "relationship_index": int(relationship_index),
        "source_table_id": str(selected["source_table_id"]),
        "target_table_id": str(selected["target_table_id"]),
        "source_table_label": str(selected["source_label"]),
        "target_table_label": str(selected["target_label"]),
        "relationship_label": str(selected["label"]),
        "relationship_label_overlap_score": float(best_score),
        "relationship_label_bbox_estimate_px": list(label_bbox),
        "answer": str(selected["target_label"]),
    }


def _select_relationship_cardinality_query(
    *,
    query_id: str,
    rng,
    tables: Sequence[Mapping[str, Any]],
    relationships: Sequence[Mapping[str, Any]],
    answer_index: int,
) -> Dict[str, Any]:
    table_by_id = {str(table["table_id"]): dict(table) for table in tables}
    pair_counts: Dict[tuple[str, str], int] = {}
    for relationship in relationships:
        pair = (str(relationship["source_table_id"]), str(relationship["target_table_id"]))
        pair_counts[pair] = int(pair_counts.get(pair, 0)) + 1

    candidates: list[tuple[str, str, str, int, Dict[str, Any]]] = []
    for index, relationship in enumerate(relationships):
        source_id = str(relationship["source_table_id"])
        target_id = str(relationship["target_table_id"])
        if source_id not in table_by_id or target_id not in table_by_id:
            continue
        if int(pair_counts.get((source_id, target_id), 0)) != 1:
            continue
        candidates.append(
            (
                str(relationship["cardinality_kind"]),
                str(relationship["source_label"]),
                str(relationship["target_label"]),
                int(index),
                dict(relationship),
            )
        )
    if not candidates:
        raise ValueError("schema cardinality query requires a unique directed relationship between two tables")

    target_kind = str(_CARDINALITY_ORDER[abs(int(answer_index)) % len(_CARDINALITY_ORDER)])
    preferred = [candidate for candidate in candidates if str(candidate[0]) == str(target_kind)]
    pool = preferred if preferred else candidates
    pool.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    _, _, _, relationship_index, selected = pool[
        int(abs(int(answer_index)) + rng.randrange(max(1, len(pool)))) % len(pool)
    ]
    return {
        "query_id": str(query_id),
        "task_key": _TASK_KEYS[str(query_id)],
        "relationship_id": str(selected["relationship_id"]),
        "relationship_index": int(relationship_index),
        "source_table_id": str(selected["source_table_id"]),
        "target_table_id": str(selected["target_table_id"]),
        "source_table_label": str(selected["source_label"]),
        "target_table_label": str(selected["target_label"]),
        "relationship_label": str(selected["label"]),
        "cardinality_kind": str(selected["cardinality_kind"]),
        "source_cardinality_marker": str(selected["source_marker"]),
        "target_cardinality_marker": str(selected["target_marker"]),
        "answer": str(selected["cardinality_kind"]),
    }


def _build_query(
    *,
    task_id: str,
    query_id: str,
    rng,
    tables: list[Dict[str, Any]],
    relationships: list[Dict[str, Any]],
    layout_variant: str,
    answer_index: int,
) -> Dict[str, Any]:
    if str(task_id) == FIELD_ROLE_COUNT_TASK_ID:
        if str(query_id) == "attribute_field_count":
            target_count = 2 + (abs(int(answer_index)) % 5)
            ranked_tables = sorted(
                tables,
                key=lambda candidate: (
                    abs(len([field for field in candidate["fields"] if str(field["role"]) == "ATTR"]) - int(target_count)),
                    str(candidate["label"]),
                ),
            )
            best_distance = abs(
                len([field for field in ranked_tables[0]["fields"] if str(field["role"]) == "ATTR"]) - int(target_count)
            )
            eligible = [
                table for table in ranked_tables
                if abs(len([field for field in table["fields"] if str(field["role"]) == "ATTR"]) - int(target_count)) == best_distance
            ]
            table = rng.choice(eligible)
            fields = [field for field in table["fields"] if str(field["role"]) == "ATTR"]
            return {
                "query_id": str(query_id),
                "task_key": _TASK_KEYS[str(query_id)],
                "table_id": str(table["table_id"]),
                "table_label": str(table["label"]),
                "field_role_description": "ordinary attribute fields",
                "answer": int(len(fields)),
                "annotation_field_ids": [str(field["field_id"]) for field in fields],
            }
        target_count = 3 + (abs(int(answer_index)) % 7)
        ranked_tables = sorted(
            tables,
            key=lambda candidate: (abs(len(candidate["fields"]) - int(target_count)), str(candidate["label"])),
        )
        best_distance = abs(len(ranked_tables[0]["fields"]) - int(target_count))
        eligible = [
            table for table in ranked_tables
            if abs(len(table["fields"]) - int(target_count)) == best_distance
        ]
        table = rng.choice(eligible)
        fields = list(table["fields"])
        return {
            "query_id": str(query_id),
            "task_key": _TASK_KEYS[str(query_id)],
            "table_id": str(table["table_id"]),
            "table_label": str(table["label"]),
            "field_role_description": "fields",
            "answer": int(len(fields)),
            "annotation_field_ids": [str(field["field_id"]) for field in fields],
        }

    if str(task_id) == RELATIONSHIP_ENDPOINT_TASK_ID:
        return _select_relationship_endpoint_query(
            query_id=str(query_id),
            rng=rng,
            tables=tables,
            relationships=relationships,
            layout_variant=str(layout_variant),
            answer_index=int(answer_index),
        )

    if str(task_id) == RELATIONSHIP_CARDINALITY_TASK_ID:
        return _select_relationship_cardinality_query(
            query_id=str(query_id),
            rng=rng,
            tables=tables,
            relationships=relationships,
            answer_index=int(answer_index),
        )

    matched = list(relationships)
    return {
        "query_id": str(query_id),
        "task_key": _TASK_KEYS[str(query_id)],
        "answer": int(len(matched)),
        "annotation_relationship_ids": [str(rel["relationship_id"]) for rel in matched],
    }


def _build_prompt_json_examples(*, answer_type: str, annotation_kind: str) -> tuple[str, str]:
    answer_only: Dict[str, Any] = {"answer": "Order"}
    if str(answer_type) == "integer":
        answer_only = {"answer": 3}
    if str(annotation_kind) == "relationship_cardinality":
        answer_only = {"answer": "one_to_many"}
    if str(annotation_kind) == "relationship":
        annotation: Any = [
            [[150, 180], [330, 260]],
            [[420, 260], [610, 360]],
        ]
    elif str(annotation_kind) == "relationship_endpoint":
        annotation = {
            "source_table": [90, 120, 250, 300],
            "relationship_label": [320, 210, 410, 236],
            "target_table": [480, 150, 650, 330],
        }
    elif str(annotation_kind) == "relationship_cardinality":
        annotation = {
            "source_table": [90, 120, 250, 300],
            "target_table": [480, 150, 650, 330],
            "source_cardinality_marker": [270, 202, 300, 226],
            "target_cardinality_marker": [440, 202, 470, 226],
        }
    else:
        annotation = [[90, 120, 220, 146], [240, 168, 390, 194]]
    with_annotation = {"annotation": annotation, "answer": answer_only["answer"]}
    return (
        json.dumps(with_annotation, separators=(",", ":")),
        json.dumps(answer_only, separators=(",", ":")),
    )


def _build_scene_and_query(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, float], Dict[str, float], Dict[str, float], Dict[str, float]]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.schema_scene")
    supported_queries = _TASK_QUERY_IDS[str(task_id)]
    query_id, query_probabilities = _resolve_axis(
        params=params,
        gen_defaults=gen_defaults,
        supported_values=supported_queries,
        explicit_key="query_id",
        weights_key="query_weights",
        balance_flag_key="balanced_query_sampling",
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        namespace="query_id",
    )
    context_id, context_probabilities = _resolve_axis(
        params=params,
        gen_defaults=gen_defaults,
        supported_values=_CONTEXT_VARIANTS,
        explicit_key="context_id",
        weights_key="context_weights",
        balance_flag_key="balanced_context_sampling",
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        namespace="context_id",
    )
    layout_variant, layout_probabilities = _resolve_axis(
        params=params,
        gen_defaults=gen_defaults,
        supported_values=_LAYOUT_VARIANTS,
        explicit_key="layout_variant",
        weights_key="layout_weights",
        balance_flag_key="balanced_layout_sampling",
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        namespace="layout_variant",
    )
    style_variant, style_probabilities = _resolve_axis(
        params=params,
        gen_defaults=gen_defaults,
        supported_values=_STYLE_VARIANTS,
        explicit_key="style_variant",
        weights_key="style_weights",
        balance_flag_key="balanced_style_sampling",
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        namespace="style_variant",
    )
    table_min, table_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="table_count_min",
        max_key="table_count_max",
        fallback_min=5,
        fallback_max=8,
        context=f"{task_id} schema table count",
    )
    field_min, field_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="field_count_min",
        max_key="field_count_max",
        fallback_min=4,
        fallback_max=7,
        context=f"{task_id} schema field count",
    )
    rel_min, rel_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="relationship_count_min",
        max_key="relationship_count_max",
        fallback_min=5,
        fallback_max=9,
        context=f"{task_id} schema relationship count",
    )
    table_count = int(rng.randint(int(table_min), int(table_max)))
    context = _CONTEXTS[str(context_id)]
    sampling_index = abs(int(instance_seed))
    target_relationship_count = None
    if str(task_id) == RELATIONSHIP_COUNT_TASK_ID:
        target_relationship_count = int(rel_min) + (abs(int(sampling_index)) % (int(rel_max) - int(rel_min) + 1))
    tables, relationships = _build_tables_and_relationships(
        rng=rng,
        context=context,
        table_count=int(table_count),
        field_count_min=int(field_min),
        field_count_max=int(field_max),
        relationship_count_min=int(rel_min),
        relationship_count_max=int(rel_max),
        target_relationship_count=target_relationship_count,
    )
    canvas_width, canvas_height, panel, title_bbox, content, jitter_meta = _resolve_scene_geometry(
        params=params,
        render_defaults=render_defaults,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
    )
    _assign_table_layout(
        tables=tables,
        relationships=relationships,
        content_bbox=content,
        layout_variant=str(layout_variant),
        render_defaults=render_defaults,
    )
    query = _build_query(
        task_id=str(task_id),
        query_id=str(query_id),
        rng=rng,
        tables=tables,
        relationships=relationships,
        layout_variant=str(layout_variant),
        answer_index=int(sampling_index),
    )
    scene = {
        "scene_id": SCENE_ID,
        "context_id": str(context_id),
        "scene_title": str(context["title"]),
        "layout_variant": str(layout_variant),
        "style_variant": str(style_variant),
        "table_count": int(len(tables)),
        "relationship_count": int(len(relationships)),
        "field_count": int(sum(len(table["fields"]) for table in tables)),
        "tables": [deepcopy(table) for table in tables],
        "relationships": [deepcopy(rel) for rel in relationships],
        "canvas_width": int(canvas_width),
        "canvas_height": int(canvas_height),
        "panel_bbox": list(panel),
        "title_bbox": list(title_bbox),
        "content_bbox": list(content),
        "layout_jitter": dict(jitter_meta),
    }
    return scene, query, query_probabilities, context_probabilities, layout_probabilities, style_probabilities


def _build_output(
    *,
    task_id: str,
    domain: str,
    task_group: str,
    instance_seed: int,
    params: Dict[str, Any],
    max_attempts: int,
) -> TaskOutput:
    del max_attempts
    gen_defaults, render_defaults, prompt_defaults, complexity_weights = _resolve_defaults_for_task(str(task_id))
    scene, query, query_probabilities, context_probabilities, layout_probabilities, style_probabilities = _build_scene_and_query(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        render_defaults=render_defaults,
    )
    background, background_meta = make_background_canvas(
        canvas_width=int(scene["canvas_width"]),
        canvas_height=int(scene["canvas_height"]),
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    rendered, render_map = _render_scene(
        base_image=background,
        title=str(scene["scene_title"]),
        tables=list(scene["tables"]),
        relationships=list(scene["relationships"]),
        panel_bbox=list(scene["panel_bbox"]),
        title_bbox=list(scene["title_bbox"]),
        layout_variant=str(scene["layout_variant"]),
        style_variant=str(scene["style_variant"]),
        render_defaults=render_defaults,
    )
    image, post_noise_meta = apply_post_image_noise(
        rendered,
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
            "integer_answer_hint",
            "string_answer_hint",
            "annotation_hint_field_count",
            "annotation_hint_relationship_count",
            "annotation_hint_relationship_endpoint",
            "cardinality_answer_hint",
            "annotation_hint_relationship_cardinality",
        ),
        context=f"prompt defaults for {task_id}",
    )
    answer_type = "integer"
    if str(task_id) == RELATIONSHIP_COUNT_TASK_ID:
        annotation_kind = "relationship"
        answer_hint = str(prompt_defaults["integer_answer_hint"])
        annotation_hint = str(prompt_defaults["annotation_hint_relationship_count"])
    elif str(task_id) == RELATIONSHIP_ENDPOINT_TASK_ID:
        answer_type = "string"
        annotation_kind = "relationship_endpoint"
        answer_hint = str(prompt_defaults["string_answer_hint"])
        annotation_hint = str(prompt_defaults["annotation_hint_relationship_endpoint"])
    elif str(task_id) == RELATIONSHIP_CARDINALITY_TASK_ID:
        answer_type = "string"
        annotation_kind = "relationship_cardinality"
        answer_hint = str(prompt_defaults["cardinality_answer_hint"])
        annotation_hint = str(prompt_defaults["annotation_hint_relationship_cardinality"])
    else:
        annotation_kind = "field"
        answer_hint = str(prompt_defaults["integer_answer_hint"])
        annotation_hint = str(prompt_defaults["annotation_hint_field_count"])
    json_example, json_example_answer_only = _build_prompt_json_examples(
        answer_type=answer_type,
        annotation_kind=str(annotation_kind),
    )
    slots = {
        "object_description": str(prompt_defaults["object_description"]),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(answer_hint),
        "annotation_hint": str(annotation_hint),
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
    }
    slots.update({str(key): value for key, value in query.items() if key not in {"answer", "annotation_field_ids", "annotation_table_ids", "annotation_relationship_ids"}})
    prompt_selection = render_task_prompt_variants(
        domain=str(domain),
        task_group=str(task_group),
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(query["task_key"]),
        query_key=str(query["query_id"]),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots=slots,
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

    bbox_source_map: Dict[str, Sequence[float]] = {}
    annotation_ids: list[str] = []
    annotation_point_pairs: list[list[list[float]]] = []
    for field_id in [str(item) for item in query.get("annotation_field_ids", [])]:
        annotation_id = f"field:{field_id}"
        annotation_ids.append(annotation_id)
        bbox_source_map[annotation_id] = render_map["field_bboxes_px"][field_id]
    for table_id in [str(item) for item in query.get("annotation_table_ids", [])]:
        annotation_id = f"table:{table_id}"
        annotation_ids.append(annotation_id)
        bbox_source_map[annotation_id] = render_map["table_bboxes_px"][table_id]
    for relationship_id in [str(item) for item in query.get("annotation_relationship_ids", [])]:
        annotation_id = f"relationship_points:{relationship_id}"
        annotation_ids.append(annotation_id)
        annotation_point_pairs.append(
            [
                [round(float(value), 3) for value in point]
                for point in render_map["relationship_point_pairs_px"][relationship_id]
            ]
        )
    keyed_bbox_map: Dict[str, list[float]] = {}
    keyed_bbox_ids: Dict[str, str] = {}
    if str(task_id) == RELATIONSHIP_ENDPOINT_TASK_ID:
        relationship_id = str(query["relationship_id"])
        source_table_id = str(query["source_table_id"])
        target_table_id = str(query["target_table_id"])
        keyed_bbox_ids = {
            "source_table": f"table:{source_table_id}",
            "relationship_label": f"relationship_label:{relationship_id}",
            "target_table": f"table:{target_table_id}",
        }
        keyed_bbox_map = {
            "source_table": [round(float(value), 3) for value in render_map["table_bboxes_px"][source_table_id]],
            "relationship_label": [
                round(float(value), 3) for value in render_map["relationship_label_bboxes_px"][relationship_id]
            ],
            "target_table": [round(float(value), 3) for value in render_map["table_bboxes_px"][target_table_id]],
        }
        annotation_ids = [keyed_bbox_ids[key] for key in ("source_table", "relationship_label", "target_table")]
        annotation_projection = {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(keyed_bbox_map),
            "pixel_keyed_bbox_map": dict(keyed_bbox_map),
            "annotation_ids": list(annotation_ids),
            "keyed_annotation_ids": dict(keyed_bbox_ids),
        }
        annotation_bboxes: list[list[float]] = []
    elif str(task_id) == RELATIONSHIP_CARDINALITY_TASK_ID:
        relationship_id = str(query["relationship_id"])
        source_table_id = str(query["source_table_id"])
        target_table_id = str(query["target_table_id"])
        source_marker_id = f"{relationship_id}:source"
        target_marker_id = f"{relationship_id}:target"
        keyed_bbox_ids = {
            "source_table": f"table:{source_table_id}",
            "target_table": f"table:{target_table_id}",
            "source_cardinality_marker": f"cardinality_marker:{source_marker_id}",
            "target_cardinality_marker": f"cardinality_marker:{target_marker_id}",
        }
        keyed_bbox_map = {
            "source_table": [round(float(value), 3) for value in render_map["table_bboxes_px"][source_table_id]],
            "target_table": [round(float(value), 3) for value in render_map["table_bboxes_px"][target_table_id]],
            "source_cardinality_marker": [
                round(float(value), 3) for value in render_map["cardinality_marker_bboxes_px"][source_marker_id]
            ],
            "target_cardinality_marker": [
                round(float(value), 3) for value in render_map["cardinality_marker_bboxes_px"][target_marker_id]
            ],
        }
        annotation_ids = [
            keyed_bbox_ids[key]
            for key in ("source_table", "target_table", "source_cardinality_marker", "target_cardinality_marker")
        ]
        annotation_projection = {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(keyed_bbox_map),
            "pixel_keyed_bbox_map": dict(keyed_bbox_map),
            "annotation_ids": list(annotation_ids),
            "keyed_annotation_ids": dict(keyed_bbox_ids),
        }
        annotation_bboxes = []
    elif str(task_id) == RELATIONSHIP_COUNT_TASK_ID:
        annotation_projection = {
            "type": "point_pair_set",
            "point_pair_set": list(annotation_point_pairs),
            "pixel_point_pair_set": list(annotation_point_pairs),
            "annotation_ids": list(annotation_ids),
        }
        annotation_bboxes: list[list[float]] = []
    else:
        annotation_projection = projected_diagram_bbox_annotation(bbox_source_map, annotation_ids)
        annotation_bboxes = [[round(float(value), 3) for value in bbox] for bbox in annotation_projection["bbox_set"]]
    answer_gt = (
        TypedValue(type="string", value=str(query["answer"]))
        if answer_type == "string"
        else TypedValue(type="integer", value=int(query["answer"]))
    )
    annotation_gt = (
        TypedValue(type="point_pair_set", value=list(annotation_point_pairs))
        if str(task_id) == RELATIONSHIP_COUNT_TASK_ID
        else (
            TypedValue(type="keyed_bbox_map", value=dict(keyed_bbox_map))
            if str(task_id) in {RELATIONSHIP_ENDPOINT_TASK_ID, RELATIONSHIP_CARDINALITY_TASK_ID}
            else TypedValue(type="bbox_set", value=list(annotation_bboxes))
        )
    )

    field_scan = normalize_int_with_bounds(int(scene["field_count"]), [24, 72])
    table_scan = normalize_int_with_bounds(int(scene["table_count"]), [5, 8])
    rel_scan = normalize_int_with_bounds(int(scene["relationship_count"]), [5, 9])
    answer_load = normalize_int_with_bounds(
        int(len(annotation_ids)) if answer_type == "string" else int(answer_gt.value),
        [1, 12],
    )
    base_reasoning = {
        FIELD_ROLE_COUNT_TASK_ID: 0.30,
        RELATIONSHIP_COUNT_TASK_ID: 0.50,
        RELATIONSHIP_ENDPOINT_TASK_ID: 0.56,
        RELATIONSHIP_CARDINALITY_TASK_ID: 0.58,
    }[str(task_id)]
    complexity = build_pages_complexity(
        weights=complexity_weights,
        components={
            "schema_size": clamp_unit_interval((0.55 * field_scan) + (0.45 * table_scan)),
            "relationship_density": float(rel_scan),
            "reasoning_load": clamp_unit_interval(float(base_reasoning) + (0.18 * answer_load)),
        },
    )

    table_entities = []
    for table in scene["tables"]:
        table_entities.append(
            {
                "entity_id": str(table["table_id"]),
                "entity_type": "schema_table",
                "label": str(table["label"]),
                "bbox_id": f"table:{table['table_id']}",
            }
        )
        for field in table["fields"]:
            table_entities.append(
                {
                    "entity_id": str(field["field_id"]),
                    "entity_type": "schema_field",
                    "table_id": str(table["table_id"]),
                    "label": str(field["name"]),
                    "field_type": str(field["type"]),
                    "role": str(field["role"]),
                    "references_table_id": field.get("references_table_id"),
                    "bbox_id": f"field:{field['field_id']}",
                }
            )
    supporting_bbox_ids = [] if str(task_id) == RELATIONSHIP_COUNT_TASK_ID else list(annotation_ids)
    supporting_point_pair_ids = list(annotation_ids) if str(task_id) == RELATIONSHIP_COUNT_TASK_ID else []
    if str(task_id) in {RELATIONSHIP_ENDPOINT_TASK_ID, RELATIONSHIP_CARDINALITY_TASK_ID}:
        witness_symbolic = {
            "type": "keyed_bbox_id_map",
            "ids": dict(keyed_bbox_ids),
            "bboxes": dict(keyed_bbox_map),
        }
    else:
        witness_symbolic = {
            "type": "point_pair_id_set" if str(task_id) == RELATIONSHIP_COUNT_TASK_ID else "bbox_id_set",
            "ids": list(annotation_ids),
            "point_pairs": list(annotation_point_pairs),
        }
    trace_payload = {
        "scene_ir": {
            "scene_id": SCENE_ID,
            "scene_kind": "pages_database_schema_diagram",
            "entities": table_entities,
            "relations": {
                "query_id": str(query["query_id"]),
                "scene_variant": str(scene["layout_variant"]),
                "layout_variant": str(scene["layout_variant"]),
                "style_variant": str(scene["style_variant"]),
                "context_id": str(scene["context_id"]),
                "relationships": [
                    {
                        "relationship_id": str(rel["relationship_id"]),
                        "source_table_id": str(rel["source_table_id"]),
                        "target_table_id": str(rel["target_table_id"]),
                        "source_field_id": str(rel["source_field_id"]),
                        "target_field_id": str(rel["target_field_id"]),
                        "label": str(rel["label"]),
                        "cardinality_kind": str(rel["cardinality_kind"]),
                        "source_marker": str(rel["source_marker"]),
                        "target_marker": str(rel["target_marker"]),
                    }
                    for rel in scene["relationships"]
                ],
            },
        },
        "query_spec": {
            "query_id": str(query["query_id"]),
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": {
                "query_id": str(query["query_id"]),
                "query_id_probabilities": dict(query_probabilities),
                "context_id": str(scene["context_id"]),
                "context_probabilities": dict(context_probabilities),
                "layout_variant": str(scene["layout_variant"]),
                "layout_probabilities": dict(layout_probabilities),
                "style_variant": str(scene["style_variant"]),
                "style_probabilities": dict(style_probabilities),
                "table_count": int(scene["table_count"]),
                "field_count": int(scene["field_count"]),
                "relationship_count": int(scene["relationship_count"]),
                "selected_relationship_id": str(query.get("relationship_id", "")),
                "source_table_label": str(query.get("source_table_label", "")),
                "target_table_label": str(query.get("target_table_label", "")),
                "cardinality_kind": str(query.get("cardinality_kind", "")),
                "source_cardinality_marker": str(query.get("source_cardinality_marker", "")),
                "target_cardinality_marker": str(query.get("target_cardinality_marker", "")),
                **({"answer_support": list(_CARDINALITY_ORDER)} if str(task_id) == RELATIONSHIP_CARDINALITY_TASK_ID else {}),
            },
        },
        "render_spec": {
            "scene_id": SCENE_ID,
            "query_id": str(query["query_id"]),
            "scene_variant": str(scene["layout_variant"]),
            "layout_variant": str(scene["layout_variant"]),
            "style_variant": str(scene["style_variant"]),
            "geometry_seed": int(instance_seed),
            "canvas_width": int(scene["canvas_width"]),
            "canvas_height": int(scene["canvas_height"]),
            "layout_jitter": dict(scene["layout_jitter"]),
            "background_style": dict(background_meta),
            "post_image_noise": dict(post_noise_meta),
        },
        "render_map": dict(render_map),
        "execution_trace": {
            "query_id": str(query["query_id"]),
            "question_format": str(query["query_id"]),
            "view_family": SCENE_ID,
            "scene_title": str(scene["scene_title"]),
            "context_id": str(scene["context_id"]),
            "layout_variant": str(scene["layout_variant"]),
            "style_variant": str(scene["style_variant"]),
            "table_count": int(scene["table_count"]),
            "field_count": int(scene["field_count"]),
            "relationship_count": int(scene["relationship_count"]),
            "tables": [
                {
                    "table_id": str(table["table_id"]),
                    "label": str(table["label"]),
                    "fields": [
                        {key: value for key, value in dict(field).items()}
                        for field in table["fields"]
                    ],
                }
                for table in scene["tables"]
            ],
            "relationships": [
                {key: value for key, value in dict(rel).items() if key != "points"}
                for rel in scene["relationships"]
            ],
            "query": {key: value for key, value in query.items() if key not in {"task_key"}},
            "answer": answer_gt.to_dict(),
            "annotation_ids": list(annotation_ids),
            "supporting_bbox_ids": list(supporting_bbox_ids),
            "supporting_point_pair_ids": list(supporting_point_pair_ids),
        },
        "witness_symbolic": dict(witness_symbolic),
        "projected_annotation": dict(annotation_projection),
        "background": dict(background_meta),
        "post_image_noise": dict(post_noise_meta),
    }
    output = TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        answer_gt=answer_gt,
        annotation_gt=annotation_gt,
        image=image,
        image_id="img0",
        trace_payload=trace_payload,
        complexity=complexity,
        task_versions=default_task_versions(),
        query_id="default",
    )
    return rewrite_pages_query_output(
        output,
        query_id=str(query["query_id"]),
        scene_id=SCENE_ID,
        query_probabilities=query_probabilities,
    )


@register_task
class PagesSchemaFieldRoleCountTask:
    """Count table fields selected by role in a database schema diagram."""

    task_id = FIELD_ROLE_COUNT_TASK_ID
    domain = "pages"
    task_group = "schema"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return _build_output(
            task_id=self.task_id,
            domain=self.domain,
            task_group=self.task_group,
            instance_seed=int(instance_seed),
            params=dict(params),
            max_attempts=int(max_attempts),
        )


@register_task
class PagesSchemaRelationshipCountTask:
    """Count schema relationships selected by table or cardinality markers."""

    task_id = RELATIONSHIP_COUNT_TASK_ID
    domain = "pages"
    task_group = "schema"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return _build_output(
            task_id=self.task_id,
            domain=self.domain,
            task_group=self.task_group,
            instance_seed=int(instance_seed),
            params=dict(params),
            max_attempts=int(max_attempts),
        )


@register_task
class PagesSchemaRelationshipEndpointLabelTask:
    """Identify the target table reached by a named schema relationship."""

    task_id = RELATIONSHIP_ENDPOINT_TASK_ID
    domain = "pages"
    task_group = "schema"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return _build_output(
            task_id=self.task_id,
            domain=self.domain,
            task_group=self.task_group,
            instance_seed=int(instance_seed),
            params=dict(params),
            max_attempts=int(max_attempts),
        )


@register_task
class PagesSchemaRelationshipCardinalityLabelTask:
    """Identify the cardinality class shown by relationship endpoint markers."""

    task_id = RELATIONSHIP_CARDINALITY_TASK_ID
    domain = "pages"
    task_group = "schema"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return _build_output(
            task_id=self.task_id,
            domain=self.domain,
            task_group=self.task_group,
            instance_seed=int(instance_seed),
            params=dict(params),
            max_attempts=int(max_attempts),
        )


__all__ = [
    "FIELD_ROLE_COUNT_TASK_ID",
    "RELATIONSHIP_CARDINALITY_TASK_ID",
    "RELATIONSHIP_COUNT_TASK_ID",
    "RELATIONSHIP_ENDPOINT_TASK_ID",
    "PagesSchemaFieldRoleCountTask",
    "PagesSchemaRelationshipCardinalityLabelTask",
    "PagesSchemaRelationshipCountTask",
    "PagesSchemaRelationshipEndpointLabelTask",
]
