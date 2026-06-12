"""Concept-map page tasks grounded in visible branch membership."""

from __future__ import annotations

import json
import math
from copy import deepcopy
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
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
from ..shared.diagram.common import (
    projected_diagram_bbox_annotation,
    resolve_jittered_diagram_panel_geometry,
    round_diagram_bbox,
)
from ..shared.diagram.visual_defaults import load_diagrams_background_defaults, load_diagrams_noise_defaults
from ..shared.page_semantic_assets import (
    page_semantic_asset_ids,
    page_semantic_asset_label,
    page_semantic_asset_manifest_metadata,
    render_page_semantic_asset_rgba,
)
from ..shared.public_query_task import rewrite_pages_query_output


SCENE_ID = "concept_map"
BRANCH_CHILD_COUNT_TASK_ID = "task_pages__concept_map__branch_child_count"
MARKED_CHILD_COUNT_TASK_ID = "task_pages__concept_map__marked_child_count"
ORDERED_CHILD_LABEL_TASK_ID = "task_pages__concept_map__ordered_child_label"

_LAYOUT_VARIANTS: Tuple[str, ...] = ("radial_mind_map", "left_right_map", "clustered_map")
_STYLE_VARIANTS: Tuple[str, ...] = ("bright_notes", "ink_outline", "soft_cards", "technical_pastel")
_NODE_SHAPE_PROFILES: Tuple[str, ...] = ("mixed_hub_circle", "oval_branch_mix", "mixed_cards_ovals")
_CHILD_NODE_SHAPES: Tuple[str, ...] = ("rounded_rect", "ellipse", "pill")
_CONTEXT_VARIANTS: Tuple[str, ...] = (
    "travel_plans",
    "career_options",
    "climate_actions",
    "community_groups",
    "shopping_tips",
    "science_topics",
)
_QUERY_IDS: Dict[str, Tuple[str, ...]] = {
    BRANCH_CHILD_COUNT_TASK_ID: ("branch_child_count",),
    MARKED_CHILD_COUNT_TASK_ID: ("marked_child_count",),
    ORDERED_CHILD_LABEL_TASK_ID: ("nth_child_label",),
}
_TASK_KEYS: Dict[str, str] = {
    "branch_child_count": "branch_child_count_query",
    "nth_child_label": "nth_child_label_query",
    "marked_child_count": "marked_child_count_query",
}

_MARKERS: Tuple[Dict[str, Any], ...] = tuple(
    {
        "marker_id": str(marker_id),
        "label": page_semantic_asset_label(str(marker_id)),
        "semantic_id": str(marker_id),
    }
    for marker_id in page_semantic_asset_ids(semantic_role="marker", allowed_use="filter")
)

_PALETTES: Dict[str, Dict[str, Any]] = {
    "bright_notes": {
        "panel_fill": (255, 255, 250),
        "panel_outline": (190, 197, 212),
        "central_fill": (43, 59, 128),
        "central_outline": (21, 31, 78),
        "central_text": (255, 255, 255),
        "node_text": (33, 41, 58),
        "muted_text": (92, 102, 122),
        "connector": (90, 102, 132),
        "branch_fills": (
            (255, 218, 104),
            (255, 149, 164),
            (136, 212, 151),
            (153, 191, 255),
            (218, 164, 255),
            (255, 185, 114),
            (126, 223, 215),
            (231, 226, 118),
        ),
    },
    "ink_outline": {
        "panel_fill": (248, 247, 241),
        "panel_outline": (72, 77, 88),
        "central_fill": (45, 48, 56),
        "central_outline": (20, 22, 28),
        "central_text": (255, 255, 250),
        "node_text": (32, 34, 38),
        "muted_text": (78, 82, 90),
        "connector": (78, 82, 90),
        "branch_fills": (
            (245, 237, 193),
            (237, 210, 208),
            (209, 231, 214),
            (207, 224, 238),
            (229, 213, 236),
            (238, 221, 199),
            (207, 231, 228),
            (229, 228, 201),
        ),
    },
    "soft_cards": {
        "panel_fill": (245, 249, 252),
        "panel_outline": (174, 191, 204),
        "central_fill": (45, 94, 111),
        "central_outline": (24, 60, 74),
        "central_text": (255, 255, 255),
        "node_text": (31, 47, 58),
        "muted_text": (84, 106, 116),
        "connector": (88, 126, 139),
        "branch_fills": (
            (188, 225, 232),
            (244, 207, 199),
            (208, 231, 197),
            (214, 218, 246),
            (246, 221, 183),
            (217, 205, 238),
            (194, 231, 216),
            (241, 220, 224),
        ),
    },
    "technical_pastel": {
        "panel_fill": (247, 248, 252),
        "panel_outline": (148, 158, 179),
        "central_fill": (63, 73, 105),
        "central_outline": (34, 41, 68),
        "central_text": (255, 255, 255),
        "node_text": (35, 42, 60),
        "muted_text": (76, 86, 111),
        "connector": (88, 99, 130),
        "branch_fills": (
            (228, 235, 255),
            (255, 228, 230),
            (226, 244, 233),
            (245, 235, 255),
            (255, 238, 211),
            (224, 245, 246),
            (240, 236, 211),
            (233, 230, 248),
        ),
    },
}

_CONTEXTS: Dict[str, Dict[str, Any]] = {
    "travel_plans": {
        "title": "Travel planning concept map",
        "central": "Travel Plans",
        "branches": {
            "Domestic": ["New York", "Denver", "Austin", "Seattle", "Miami", "Chicago", "Boston", "Phoenix"],
            "International": ["Paris", "Tokyo", "Lisbon", "Toronto", "Seoul", "Dublin", "Madrid", "Cairo"],
            "Tickets": ["Rail Pass", "Flight Hold", "Seat Map", "Boarding", "Upgrade", "Refund", "Transfer", "Voucher"],
            "Lodging": ["Hotel", "Hostel", "Cabin", "Apartment", "Resort", "Guesthouse", "Inn", "Suite"],
            "Activities": ["Museum", "Garden", "Boat Tour", "Market", "Hiking", "Theater", "Food Walk", "Stadium"],
            "Transport": ["Metro", "Taxi", "Rental Car", "Bike Share", "Ferry", "Shuttle", "Tram", "Bus Pass"],
            "Packing": ["Passport", "Charger", "Camera", "Jacket", "Snacks", "Adapter", "Notebook", "Umbrella"],
            "Budget": ["Meals", "Tickets", "Hotel Tax", "Tips", "Transit", "Insurance", "Tours", "Souvenirs"],
        },
    },
    "career_options": {
        "title": "Career transition concept map",
        "central": "Career Options",
        "branches": {
            "Media": ["Commentator", "Host", "Producer", "Editor", "Podcaster", "Reviewer", "Reporter", "Analyst"],
            "Coaching": ["Youth Coach", "Trainer", "Scout", "Mentor", "Playbook", "Camp Lead", "Skills Coach", "Tutor"],
            "Business": ["Agent", "Sponsor", "Founder", "Consultant", "Advisor", "Investor", "Manager", "Recruiter"],
            "Education": ["Teacher", "Lecturer", "Workshop", "Curriculum", "Seminar", "Coach Cert", "Tutor", "Course"],
            "Community": ["Volunteer", "Ambassador", "Fundraiser", "Outreach", "Board Seat", "Program Lead", "Clinic", "Mentor"],
            "Health": ["Therapist", "Nutrition", "Wellness", "Recovery", "Strength", "Mindset", "Balance", "Mobility"],
            "Creative": ["Author", "Designer", "Video", "Branding", "Photography", "Podcast", "Storytelling", "Studio"],
            "Operations": ["Planner", "Director", "Scheduler", "Coordinator", "Logistics", "Facilities", "Compliance", "Events"],
        },
    },
    "climate_actions": {
        "title": "Climate action concept map",
        "central": "Climate Action",
        "branches": {
            "Weather": ["Heat Wave", "Flood", "Storm", "Drought", "Smoke", "Wind", "Cold Snap", "Humidity"],
            "Energy": ["Solar", "Wind Power", "Storage", "Grid", "Retrofit", "Metering", "Backup", "Efficiency"],
            "Water": ["Rain Garden", "Reuse", "Drainage", "Reservoir", "Irrigation", "Leak Audit", "Filter", "Drought Plan"],
            "Transport": ["Carpool", "EV Bus", "Bike Lane", "Rail", "Walk Route", "Charging", "Shuttle", "Transit Card"],
            "Food": ["Compost", "Local Farm", "Cold Chain", "Menu Shift", "Food Bank", "Garden", "Storage", "Waste Log"],
            "Buildings": ["Insulation", "Cool Roof", "Shade", "Window Film", "Heat Pump", "Sensor", "Ventilation", "Audit"],
            "Policy": ["Permit", "Grant", "Code", "Target", "Report", "Dashboard", "Budget", "Review"],
            "Outreach": ["Workshop", "Newsletter", "Survey", "Hotline", "School Visit", "Poster", "Volunteer", "Briefing"],
        },
    },
    "community_groups": {
        "title": "Community organization concept map",
        "central": "Local Network",
        "branches": {
            "Nonprofits": ["Food Pantry", "Youth Arts", "Legal Aid", "Book Bank", "Shelter", "Green Team", "Free Clinic", "Music Fund"],
            "Schools": ["High School", "Art Club", "Library Lab", "STEM Camp", "Parent Board", "Tutoring", "Chess Club", "Drama Room"],
            "Health": ["Clinic", "Counseling", "Dental Van", "Nutrition", "Wellness Fair", "Blood Drive", "Care Line", "Pharmacy"],
            "Safety": ["Watch Team", "Fire Dept", "CERT", "Hotline", "Crossing Guard", "Shelter Map", "Alert Desk", "First Aid"],
            "Culture": ["Museum", "Choir", "Dance Class", "Film Night", "Theater", "Festival", "Gallery", "Poetry"],
            "Parks": ["Trail Crew", "Gardeners", "Tree Board", "Playground", "Dog Park", "Clean Up", "Picnic", "Bird Walk"],
            "Housing": ["Tenant Help", "Repair Crew", "Rent Clinic", "New Units", "Survey", "Co-op", "Shelter Link", "Mediation"],
            "Jobs": ["Resume Lab", "Apprentice", "Job Fair", "Career Desk", "Training", "Mentor Net", "Startup", "Internship"],
        },
    },
    "shopping_tips": {
        "title": "Shopping advice concept map",
        "central": "Shopping Tips",
        "branches": {
            "Authenticity": ["Serial Code", "Receipt", "Logo Check", "Seller Rating", "Material", "Packaging", "Warranty", "Photo Match"],
            "Budget": ["Coupon", "Price Alert", "Bundle", "Cashback", "Clearance", "Tax", "Shipping", "Return Fee"],
            "Quality": ["Stitching", "Weight", "Reviews", "Fit", "Durability", "Finish", "Color Fast", "Battery"],
            "Safety": ["Recall", "Age Label", "Seal", "Ingredient", "Voltage", "Allergy", "Certification", "Warning"],
            "Timing": ["Holiday", "Restock", "Preorder", "Season End", "Flash Sale", "Launch Day", "Weekend", "Closeout"],
            "Delivery": ["Pickup", "Tracking", "Locker", "Courier", "Signature", "Rush", "Packaging", "Delay"],
            "Sustainability": ["Repair", "Refill", "Used", "Rental", "Local", "Organic", "Recycled", "Low Waste"],
            "Comparison": ["Size Chart", "Feature List", "Warranty", "Unit Price", "Sample", "Trial", "Spec Sheet", "Benchmark"],
        },
    },
    "science_topics": {
        "title": "Science topic concept map",
        "central": "Science Topics",
        "branches": {
            "Astronomy": ["Leo", "Regulus", "Orion", "Rigel", "Taurus", "Aldebaran", "Virgo", "Spica"],
            "Circuits": ["Resistor", "Capacitor", "Switch", "Diode", "Battery", "Current", "Voltage", "Ground"],
            "Ecosystems": ["Grass", "Frog", "Snake", "Hawk", "Sunlight", "Soil", "Mushroom", "Water"],
            "Anatomy": ["Heart", "Lung", "Neuron", "Muscle", "Kidney", "Tendon", "Artery", "Nerve"],
            "Materials": ["Copper", "Glass", "Plastic", "Steel", "Ceramic", "Rubber", "Carbon", "Silicon"],
            "Forces": ["Friction", "Gravity", "Tension", "Lift", "Drag", "Torque", "Impulse", "Pressure"],
            "Waves": ["Amplitude", "Period", "Crest", "Trough", "Frequency", "Phase", "Medium", "Echo"],
            "Earth": ["Core", "Mantle", "Crust", "Fault", "Magma", "Mineral", "Glacier", "Delta"],
        },
    },
}

_TASK_GROUP_DEFAULTS = get_scene_defaults("pages", "concept_map")
POST_IMAGE_BACKGROUND_DEFAULTS = load_diagrams_background_defaults(scene_id="concept_map")
POST_IMAGE_NOISE_DEFAULTS = load_diagrams_noise_defaults(scene_id="concept_map", apply_prob=0.30)


def _resolve_defaults_for_task(task_id: str) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        task_id=str(task_id),
    )
    return gen_defaults, render_defaults, prompt_defaults, weights


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
        supported_variants=[str(item) for item in supported_values],
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
    )
    balanced = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=[str(item) for item in supported_values],
        balance_flag_key=str(balance_flag_key),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        sampling_namespace=f"{task_id}:{namespace}",
    )
    return str(balanced), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _bbox_center(bbox: Sequence[float]) -> tuple[float, float]:
    return ((float(bbox[0]) + float(bbox[2])) * 0.5, (float(bbox[1]) + float(bbox[3])) * 0.5)


def _node_bbox(center: tuple[float, float], width: float, height: float) -> list[float]:
    cx, cy = float(center[0]), float(center[1])
    return round_diagram_bbox((cx - width / 2.0, cy - height / 2.0, cx + width / 2.0, cy + height / 2.0))


def _resolve_node_shape_profile(instance_seed: int) -> tuple[str, str]:
    profile = _NODE_SHAPE_PROFILES[abs(int(instance_seed)) % len(_NODE_SHAPE_PROFILES)]
    central_shape = {
        "mixed_hub_circle": "circle",
        "oval_branch_mix": "ellipse",
        "mixed_cards_ovals": "pill",
    }[profile]
    return str(profile), str(central_shape)


def _assign_branch_child_shapes(
    branches: list[Dict[str, Any]],
    *,
    shape_profile: str,
    instance_seed: int,
) -> None:
    branch_shape_cycles = {
        "mixed_hub_circle": ("ellipse", "rounded_rect", "pill", "ellipse"),
        "oval_branch_mix": ("ellipse", "pill", "circle", "rounded_rect"),
        "mixed_cards_ovals": ("rounded_rect", "ellipse", "pill", "circle"),
    }
    branch_cycle = branch_shape_cycles[str(shape_profile)]
    child_offset = abs(int(instance_seed // 17)) % len(_CHILD_NODE_SHAPES)
    for branch_index, branch in enumerate(branches):
        branch_shape = branch_cycle[(branch_index + abs(int(instance_seed))) % len(branch_cycle)]
        if str(branch_shape) == "circle" and len(str(branch["label"])) > 11:
            branch_shape = "ellipse"
        branch["shape"] = str(branch_shape)
        for child_index, child in enumerate(branch["children"]):
            child["shape"] = _CHILD_NODE_SHAPES[(branch_index + child_index + child_offset) % len(_CHILD_NODE_SHAPES)]


def _branch_dimensions(branch: Mapping[str, Any], width: float, height: float, render_defaults: Mapping[str, Any]) -> tuple[float, float]:
    if str(branch.get("shape", "rounded_rect")) == "circle":
        diameter = float(group_default(render_defaults, "branch_circle_diameter_px", 86))
        return diameter, diameter
    return float(width), float(height)


def _line_bbox(a: tuple[float, float], b: tuple[float, float], pad: float) -> list[float]:
    return round_diagram_bbox(
        (
            min(float(a[0]), float(b[0])) - float(pad),
            min(float(a[1]), float(b[1])) - float(pad),
            max(float(a[0]), float(b[0])) + float(pad),
            max(float(a[1]), float(b[1])) + float(pad),
        )
    )


def _child_sort_key(child: Mapping[str, Any]) -> tuple[float, float, str]:
    bbox = child["bbox"]
    return (float(bbox[1]), float(bbox[0]), str(child["label"]))


def _has_strict_vertical_child_order(branch: Mapping[str, Any]) -> bool:
    y_positions = [round(float(child["bbox"][1]), 3) for child in branch["children"]]
    return len(set(y_positions)) == len(y_positions)


def _ordinal_label(value: int) -> str:
    value = int(value)
    suffix = "th"
    if value % 100 not in {11, 12, 13}:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def _select_branch_by_answer_index(
    *,
    branches: Sequence[Dict[str, Any]],
    answer_index: int,
    min_count: int,
    max_count: int,
) -> tuple[int, int]:
    target = int(min_count) + (abs(int(answer_index)) % (int(max_count) - int(min_count) + 1))
    eligible = [idx for idx, branch in enumerate(branches) if len(branch["children"]) == int(target)]
    if not eligible:
        closest_distance = min(abs(len(branch["children"]) - int(target)) for branch in branches)
        eligible = [
            idx for idx, branch in enumerate(branches)
            if abs(len(branch["children"]) - int(target)) == int(closest_distance)
        ]
    return int(eligible[abs(int(answer_index)) % len(eligible)]), int(target)


def _build_concept_scene(
    *,
    task_id: str,
    query_id: str,
    context_id: str,
    layout_variant: str,
    style_variant: str,
    rng,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    instance_seed: int,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    branch_min, branch_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="branch_count_min",
        max_key="branch_count_max",
        fallback_min=5,
        fallback_max=7,
        context=f"{task_id} concept-map branch count",
    )
    child_min, child_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="child_count_min",
        max_key="child_count_max",
        fallback_min=3,
        fallback_max=8,
        context=f"{task_id} concept-map child count",
    )
    marker_min, marker_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="marked_count_min",
        max_key="marked_count_max",
        fallback_min=1,
        fallback_max=5,
        context=f"{task_id} concept-map marked count",
    )
    branch_count = int(rng.randint(int(branch_min), int(branch_max)))
    context = _CONTEXTS[str(context_id)]
    branch_items = list(context["branches"].items())
    branch_offset = int(rng.randrange(len(branch_items)))
    selected_branch_items = [branch_items[(branch_offset + idx) % len(branch_items)] for idx in range(branch_count)]
    sampling_index = abs(int(instance_seed))
    forced_branch_index: int | None = None
    forced_count: int | None = None
    forced_marker = _MARKERS[abs(int(sampling_index)) % len(_MARKERS)]

    if str(query_id) == "branch_child_count":
        forced_count = int(child_min) + (abs(int(sampling_index)) % (int(child_max) - int(child_min) + 1))
        forced_branch_index = abs(int(sampling_index // max(1, int(child_max - child_min + 1)))) % int(branch_count)
    elif str(query_id) == "marked_child_count":
        forced_count = int(marker_min) + (abs(int(sampling_index)) % (int(marker_max) - int(marker_min) + 1))
        forced_branch_index = abs(int(sampling_index // max(1, int(marker_max - marker_min + 1)))) % int(branch_count)

    branches: list[Dict[str, Any]] = []
    used_labels: set[str] = set()
    for branch_index, (branch_label, item_pool) in enumerate(selected_branch_items):
        item_count = int(rng.randint(int(child_min), int(child_max)))
        if forced_branch_index is not None and int(branch_index) == int(forced_branch_index):
            item_count = max(int(item_count), int(forced_count or item_count))
            if str(query_id) == "marked_child_count":
                item_count = max(int(item_count), int(forced_count or item_count) + 1)
            item_count = min(int(child_max), int(item_count))
        pool = [str(item) for item in item_pool if str(item) not in used_labels]
        if len(pool) < int(item_count):
            pool = [str(item) for item in item_pool]
        labels = rng.sample(pool, int(item_count))
        for label in labels:
            used_labels.add(str(label))
        marker_ids: list[str] = []
        if str(query_id) == "marked_child_count" and int(branch_index) == int(forced_branch_index):
            forced_positions = set(rng.sample(list(range(int(item_count))), int(forced_count or 1)))
            alternatives = [marker for marker in _MARKERS if marker["marker_id"] != forced_marker["marker_id"]]
            for child_index in range(int(item_count)):
                if int(child_index) in forced_positions:
                    marker_ids.append(str(forced_marker["marker_id"]))
                else:
                    marker_ids.append(str(rng.choice(alternatives)["marker_id"]))
        else:
            for child_index in range(int(item_count)):
                marker_ids.append(str(_MARKERS[(branch_index + child_index + abs(int(instance_seed))) % len(_MARKERS)]["marker_id"]))
        branches.append(
            {
                "branch_id": f"branch_{branch_index}",
                "label": str(branch_label),
                "children": [
                    {
                        "node_id": f"child_{branch_index}_{child_index}",
                        "label": str(label),
                        "marker_id": str(marker_ids[child_index]),
                        "branch_id": f"branch_{branch_index}",
                    }
                    for child_index, label in enumerate(labels)
                ],
            }
        )

    canvas_width = resolve_render_int(params, render_defaults, "canvas_width", 1500, instance_seed=instance_seed, namespace="concept_map")
    canvas_height = resolve_render_int(params, render_defaults, "canvas_height", 1050, instance_seed=instance_seed, namespace="concept_map")
    outer_margin = resolve_render_int(params, render_defaults, "outer_margin_px", 46, instance_seed=instance_seed, namespace="concept_map")
    title_height = resolve_render_int(params, render_defaults, "title_band_height_px", 64, instance_seed=instance_seed, namespace="concept_map")
    panel_padding = resolve_render_int(params, render_defaults, "panel_padding_px", 26, instance_seed=instance_seed, namespace="concept_map")
    jitter_meta = resolve_layout_jitter(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.concept_map.panel",
    )
    panel, title_bbox, content, jitter = resolve_jittered_diagram_panel_geometry(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        outer_margin_px=int(outer_margin),
        title_band_height_px=int(title_height),
        panel_padding_px=int(panel_padding),
        layout_jitter_meta=jitter_meta,
    )

    node_shape_profile = _assign_layout(
        branches=branches,
        central_label=str(context["central"]),
        content_bbox=content,
        layout_variant=str(layout_variant),
        render_defaults=render_defaults,
        instance_seed=int(instance_seed),
    )
    query = _build_query(
        task_id=str(task_id),
        query_id=str(query_id),
        branches=branches,
        answer_index=int(sampling_index),
        marker=forced_marker,
    )
    scene = {
        "scene_id": SCENE_ID,
        "context_id": str(context_id),
        "scene_title": str(context["title"]),
        "central_label": str(context["central"]),
        "layout_variant": str(layout_variant),
        "style_variant": str(style_variant),
        "node_shape_profile": str(node_shape_profile),
        "branch_count": int(len(branches)),
        "child_count": int(sum(len(branch["children"]) for branch in branches)),
        "branches": deepcopy(branches),
        "canvas_width": int(canvas_width),
        "canvas_height": int(canvas_height),
        "panel_bbox": list(panel),
        "title_bbox": list(title_bbox),
        "content_bbox": list(content),
        "layout_jitter": dict(jitter),
    }
    return scene, query


def _assign_layout(
    *,
    branches: list[Dict[str, Any]],
    central_label: str,
    content_bbox: Sequence[float],
    layout_variant: str,
    render_defaults: Mapping[str, Any],
    instance_seed: int,
) -> str:
    content = [float(value) for value in content_bbox]
    width = float(content[2] - content[0])
    height = float(content[3] - content[1])
    shape_profile, central_shape = _resolve_node_shape_profile(int(instance_seed))
    _assign_branch_child_shapes(branches, shape_profile=str(shape_profile), instance_seed=int(instance_seed))
    central_w = float(group_default(render_defaults, "central_node_width_px", 190))
    central_h = float(group_default(render_defaults, "central_node_height_px", 88))
    if str(central_shape) == "circle":
        central_diameter = float(group_default(render_defaults, "central_circle_diameter_px", 146))
        central_w = central_diameter
        central_h = central_diameter
    branch_w = float(group_default(render_defaults, "branch_node_width_px", 168))
    branch_h = float(group_default(render_defaults, "branch_node_height_px", 48))
    child_w = float(group_default(render_defaults, "child_node_width_px", 142))
    child_h = float(group_default(render_defaults, "child_node_height_px", 38))
    cx = float(content[0] + width * 0.5)
    cy = float(content[1] + height * 0.5)
    if str(layout_variant) == "left_right_map":
        cx = float(content[0] + width * 0.50)
    elif str(layout_variant) == "clustered_map":
        cy = float(content[1] + height * 0.38)
    central = {
        "node_id": "central",
        "label": str(central_label),
        "bbox": _node_bbox((cx, cy), central_w, central_h),
        "shape": str(central_shape),
    }

    if str(layout_variant) == "left_right_map":
        _assign_left_right_layout(branches, central, content, branch_w, branch_h, child_w, child_h, render_defaults)
    elif str(layout_variant) == "clustered_map":
        _assign_clustered_layout(branches, central, content, branch_w, branch_h, child_w, child_h, render_defaults)
    else:
        _assign_radial_layout(branches, central, content, branch_w, branch_h, child_w, child_h, render_defaults, int(instance_seed))
    for branch in branches:
        branch["children"].sort(key=_child_sort_key)
    central["label"] = str(central_label)
    for branch in branches:
        branch["central"] = deepcopy(central)
    return str(shape_profile)


def _assign_radial_layout(
    branches: list[Dict[str, Any]],
    central: Dict[str, Any],
    content: Sequence[float],
    branch_w: float,
    branch_h: float,
    child_w: float,
    child_h: float,
    render_defaults: Mapping[str, Any],
    instance_seed: int,
) -> None:
    center = _bbox_center(central["bbox"])
    count = len(branches)
    branch_radius = 235.0
    child_radius = 430.0
    start = -math.pi / 2.0 + ((abs(int(instance_seed)) % 9) - 4) * 0.025
    for index, branch in enumerate(branches):
        angle = float(start + (2.0 * math.pi * index / max(1, count)))
        bx = float(center[0] + math.cos(angle) * branch_radius)
        by = float(center[1] + math.sin(angle) * branch_radius)
        bw, bh = _branch_dimensions(branch, branch_w, branch_h, render_defaults)
        branch["bbox"] = _node_bbox((bx, by), bw, bh)
        branch["anchor"] = (bx, by)
        children = branch["children"]
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        row_step = 43.0
        col_step = child_w + 12.0
        for child_index, child in enumerate(children):
            if abs(cos_a) >= abs(sin_a):
                cols = 2 if len(children) >= 5 else 1
                rows = int(math.ceil(len(children) / cols))
                local_col = child_index % cols
                local_row = child_index // cols
                total_h = (rows - 1) * row_step
                start_y = max(
                    float(content[1] + child_h / 2.0),
                    min(float(content[3] - child_h / 2.0 - total_h), by - total_h / 2.0),
                )
                if cos_a >= 0:
                    rx = float(content[2] - child_w / 2.0 - 8.0 - local_col * col_step)
                else:
                    rx = float(content[0] + child_w / 2.0 + 8.0 + local_col * col_step)
                ry = float(start_y + local_row * row_step)
            else:
                cols = min(4, max(1, len(children)))
                rows = int(math.ceil(len(children) / cols))
                local_col = child_index % cols
                local_row = child_index // cols
                total_w = (cols - 1) * col_step
                start_x = max(
                    float(content[0] + child_w / 2.0),
                    min(float(content[2] - child_w / 2.0 - total_w), bx - total_w / 2.0),
                )
                rx = float(start_x + local_col * col_step)
                if sin_a < 0:
                    ry = float(content[1] + child_h / 2.0 + 8.0 + local_row * row_step)
                else:
                    ry = float(content[3] - child_h / 2.0 - 8.0 - (rows - 1 - local_row) * row_step)
            child["bbox"] = _node_bbox((rx, ry), child_w, child_h)


def _assign_left_right_layout(
    branches: list[Dict[str, Any]],
    central: Dict[str, Any],
    content: Sequence[float],
    branch_w: float,
    branch_h: float,
    child_w: float,
    child_h: float,
    render_defaults: Mapping[str, Any],
) -> None:
    center = _bbox_center(central["bbox"])
    left = [branch for idx, branch in enumerate(branches) if idx % 2 == 0]
    right = [branch for idx, branch in enumerate(branches) if idx % 2 == 1]
    for side, group in (("left", left), ("right", right)):
        if not group:
            continue
        x_branch = float(center[0] - 260.0) if side == "left" else float(center[0] + 260.0)
        x_child = float(content[0] + child_w / 2.0 + 8.0) if side == "left" else float(content[2] - child_w / 2.0 - 8.0)
        child_col_step = float(child_w + 12.0)
        y_min = float(content[1] + 64.0)
        y_max = float(content[3] - 64.0)
        band_height = float((y_max - y_min) / max(1, len(group)))
        for order, branch in enumerate(group):
            band_top = float(y_min + order * band_height)
            band_bottom = float(y_min + (order + 1) * band_height)
            y = float((band_top + band_bottom) * 0.5)
            bw, bh = _branch_dimensions(branch, branch_w, branch_h, render_defaults)
            branch["bbox"] = _node_bbox((x_branch, y), bw, bh)
            branch["anchor"] = (x_branch, y)
            child_count = len(branch["children"])
            cols = 2 if child_count >= 5 else 1
            rows = int(math.ceil(child_count / cols))
            row_step = 43.0
            if rows > 1:
                row_step = min(row_step, max(child_h + 5.0, (band_height - child_h - 12.0) / (rows - 1)))
            total_h = (rows - 1) * row_step
            start_y = max(
                float(band_top + child_h / 2.0 + 4.0),
                min(float(band_bottom - child_h / 2.0 - total_h - 4.0), y - total_h / 2.0),
            )
            for child_index, child in enumerate(branch["children"]):
                local_col = child_index % cols
                local_row = child_index // cols
                if side == "left":
                    child_x = float(x_child + local_col * child_col_step)
                else:
                    child_x = float(x_child - local_col * child_col_step)
                child_y = float(start_y + local_row * row_step)
                child["bbox"] = _node_bbox((child_x, child_y), child_w, child_h)


def _assign_clustered_layout(
    branches: list[Dict[str, Any]],
    central: Dict[str, Any],
    content: Sequence[float],
    branch_w: float,
    branch_h: float,
    child_w: float,
    child_h: float,
    render_defaults: Mapping[str, Any],
) -> None:
    columns = 3 if len(branches) >= 6 else 2
    top_y = float(content[1] + 92.0)
    bottom_y = float(content[3] - 160.0)
    x_gap = float((content[2] - content[0]) / columns)
    for index, branch in enumerate(branches):
        col = index % columns
        row = index // columns
        rows = int(math.ceil(len(branches) / columns))
        bx = float(content[0] + x_gap * (col + 0.5))
        by = top_y if rows <= 1 else top_y + (bottom_y - top_y) * row / max(1, rows - 1)
        bw, bh = _branch_dimensions(branch, branch_w, branch_h, render_defaults)
        branch["bbox"] = _node_bbox((bx, by), bw, bh)
        branch["anchor"] = (bx, by)
        child_count = len(branch["children"])
        cols = 2 if child_count >= 5 else 1
        for child_index, child in enumerate(branch["children"]):
            local_col = child_index % cols
            local_row = child_index // cols
            child_x = bx + (local_col - (cols - 1) / 2.0) * (child_w + 12.0)
            child_y = by + bh / 2.0 + child_h / 2.0 + 10.0 + local_row * 42.0
            child_y = min(float(content[3] - child_h / 2.0), child_y)
            child["bbox"] = _node_bbox((child_x, child_y), child_w, child_h)


def _build_query(
    *,
    task_id: str,
    query_id: str,
    branches: list[Dict[str, Any]],
    answer_index: int,
    marker: Mapping[str, Any],
) -> Dict[str, Any]:
    if str(query_id) == "branch_child_count":
        branch_index, _target = _select_branch_by_answer_index(
            branches=branches,
            answer_index=int(answer_index),
            min_count=2,
            max_count=8,
        )
        branch = branches[int(branch_index)]
        return {
            "query_id": str(query_id),
            "task_key": _TASK_KEYS[str(query_id)],
            "branch_id": str(branch["branch_id"]),
            "branch_label": str(branch["label"]),
            "answer": int(len(branch["children"])),
            "annotation_node_ids": [str(child["node_id"]) for child in branch["children"]],
        }
    if str(task_id) == ORDERED_CHILD_LABEL_TASK_ID:
        desired_rank = 2 + (abs(int(answer_index)) % 4)
        eligible = [branch for branch in branches if len(branch["children"]) > int(desired_rank)]
        if not eligible:
            eligible = [branch for branch in branches if len(branch["children"]) >= 3]
        branch = eligible[abs(int(answer_index)) % len(eligible)]
        ordered = sorted(branch["children"], key=_child_sort_key)
        allowed_ranks = list(range(2, min(5, len(ordered) - 1) + 1))
        if not allowed_ranks:
            allowed_ranks = [min(2, len(ordered))]
        rank = int(allowed_ranks[abs(int(answer_index)) % len(allowed_ranks)])
        target = ordered[int(rank) - 1]
        return {
            "query_id": str(query_id),
            "task_key": _TASK_KEYS[str(query_id)],
            "branch_id": str(branch["branch_id"]),
            "branch_label": str(branch["label"]),
            "answer_node_id": str(target["node_id"]),
            "rank": int(rank),
            "rank_ordinal": _ordinal_label(int(rank)),
            "reading_order": "from top to bottom, breaking ties from left to right",
            "answer": str(target["label"]),
            "annotation_node_ids": [str(branch["branch_id"]), str(target["node_id"])],
            "annotation_role_node_ids": {
                "parent_branch": str(branch["branch_id"]),
                "answer_child": str(target["node_id"]),
            },
        }
    if str(query_id) != "marked_child_count":
        raise ValueError(f"unsupported concept-map query_id for {task_id}: {query_id}")
    target = 1 + (abs(int(answer_index)) % 5)
    eligible = [
        branch for branch in branches
        if sum(1 for child in branch["children"] if str(child["marker_id"]) == str(marker["marker_id"])) == int(target)
    ]
    if not eligible:
        closest_distance = min(
            abs(sum(1 for child in branch["children"] if str(child["marker_id"]) == str(marker["marker_id"])) - int(target))
            for branch in branches
        )
        eligible = [
            branch for branch in branches
            if abs(sum(1 for child in branch["children"] if str(child["marker_id"]) == str(marker["marker_id"])) - int(target))
            == int(closest_distance)
        ]
    branch = eligible[abs(int(answer_index)) % len(eligible)]
    matched = [child for child in branch["children"] if str(child["marker_id"]) == str(marker["marker_id"])]
    return {
        "query_id": str(query_id),
        "task_key": _TASK_KEYS[str(query_id)],
        "branch_id": str(branch["branch_id"]),
        "branch_label": str(branch["label"]),
        "marker_id": str(marker["marker_id"]),
        "marker_label": str(marker["label"]).removesuffix(" marker"),
        "marker_display_label": str(marker["label"]),
        "answer": int(len(matched)),
        "annotation_node_ids": [str(child["node_id"]) for child in matched],
    }


def _draw_node(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    *,
    node: Mapping[str, Any],
    fill: Sequence[int],
    outline: Sequence[int],
    text_fill: Sequence[int],
    font_size: int,
    radius: int,
    border_width: int,
    bold: bool,
    marker: Mapping[str, Any] | None = None,
) -> list[float]:
    bbox = [float(value) for value in node["bbox"]]
    shape = str(node.get("shape", "rounded_rect"))
    if shape in {"circle", "ellipse"}:
        draw.ellipse(tuple(bbox), fill=tuple(fill), outline=tuple(outline), width=int(border_width))
    else:
        draw_rounded_rect(
            draw,
            tuple(bbox),
            radius=int((bbox[3] - bbox[1]) / 2.0) if shape == "pill" else int(radius),
            fill=fill,
            outline=outline,
            width=int(border_width),
        )
    if marker is not None:
        mx0 = float(bbox[0] + 8.0)
        my0 = float(bbox[1] + 0.5 * (bbox[3] - bbox[1]) - 5.5)
        mx1 = float(mx0 + 11.0)
        my1 = float(my0 + 11.0)
        marker_img = render_page_semantic_asset_rgba(
            str(marker["marker_id"]),
            size_px=(max(1, int(round(mx1 - mx0))), max(1, int(round(my1 - my0)))),
            tint_rgb=tuple(int(value) for value in text_fill),
        )
        image.paste(marker_img, (int(round(mx0)), int(round(my0))), marker_img)
    inset = 25.0 if marker is not None else 10.0
    shape_width_factor = 0.90 if shape == "circle" else 0.84 if shape == "ellipse" else 1.0
    font = fit_font_to_box(
        draw,
        text=str(node["label"]),
        max_width=max(12.0, float(bbox[2] - bbox[0] - inset - 8.0) * shape_width_factor),
        max_height=max(12.0, float(bbox[3] - bbox[1] - 8.0)),
        bold=bool(bold),
        min_size_px=8,
        max_size_px=int(font_size),
        fill_ratio=0.94,
    )
    draw_centered_text(
        draw,
        text=str(node["label"]),
        center=(float((bbox[0] + bbox[2] + inset) / 2.0), float((bbox[1] + bbox[3]) / 2.0)),
        font=font,
        fill=text_fill,
        stroke_fill=fill,
        stroke_width=0,
    )
    return round_diagram_bbox(bbox)


def _render_scene(
    *,
    base_image: Image.Image,
    scene: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
) -> tuple[Image.Image, Dict[str, Any]]:
    image = base_image.copy()
    draw = ImageDraw.Draw(image)
    palette = _PALETTES[str(scene["style_variant"])]
    panel = [float(value) for value in scene["panel_bbox"]]
    title_bbox = [float(value) for value in scene["title_bbox"]]
    panel_radius = int(group_default(render_defaults, "panel_corner_radius_px", 24))
    node_radius = int(group_default(render_defaults, "node_corner_radius_px", 14))
    border_width = int(group_default(render_defaults, "node_border_width_px", 2))
    connector_width = int(group_default(render_defaults, "connector_width_px", 3))
    draw_rounded_rect(
        draw,
        tuple(panel),
        radius=int(panel_radius),
        fill=palette["panel_fill"],
        outline=palette["panel_outline"],
        width=2,
    )
    title_font = load_font(int(group_default(render_defaults, "title_font_size_px", 30)), bold=True)
    draw_centered_text(
        draw,
        text=str(scene["scene_title"]),
        center=_bbox_center(title_bbox),
        font=title_font,
        fill=palette["node_text"],
        stroke_fill=palette["panel_fill"],
        stroke_width=0,
    )

    node_bboxes: Dict[str, list[float]] = {}
    connector_bboxes: Dict[str, list[float]] = {}
    marker_by_id = {str(marker["marker_id"]): marker for marker in _MARKERS}
    branch_fills = list(palette["branch_fills"])
    central = scene["branches"][0]["central"]
    central_bbox = _draw_node(
        image,
        draw,
        node=central,
        fill=palette["central_fill"],
        outline=palette["central_outline"],
        text_fill=palette["central_text"],
        font_size=int(group_default(render_defaults, "central_font_size_px", 20)),
        radius=int(node_radius + 5),
        border_width=2,
        bold=True,
    )
    node_bboxes["central"] = central_bbox

    for branch_index, branch in enumerate(scene["branches"]):
        branch_color = branch_fills[int(branch_index) % len(branch_fills)]
        branch_bbox = [float(value) for value in branch["bbox"]]
        start = _bbox_center(central_bbox)
        end = _bbox_center(branch_bbox)
        connector_id = f"central_to_{branch['branch_id']}"
        if int(branch_index) % 3 == 1:
            draw_dashed_line(
                draw,
                start=start,
                end=end,
                fill=palette["connector"],
                width=int(connector_width),
                dash_px=14,
                gap_px=7,
            )
        else:
            draw.line([start, end], fill=tuple(palette["connector"]), width=int(connector_width))
        connector_bboxes[connector_id] = _line_bbox(start, end, connector_width + 3)
        for child_index, child in enumerate(branch["children"]):
            child_bbox = [float(value) for value in child["bbox"]]
            child_start = _bbox_center(branch_bbox)
            child_end = _bbox_center(child_bbox)
            connector_id = f"{branch['branch_id']}_to_{child['node_id']}"
            draw.line([child_start, child_end], fill=tuple(palette["connector"]), width=max(1, int(connector_width - 1)))
            connector_bboxes[connector_id] = _line_bbox(child_start, child_end, connector_width + 2)

        node_bboxes[str(branch["branch_id"])] = _draw_node(
            image,
            draw,
            node=branch,
            fill=branch_color,
            outline=palette["connector"],
            text_fill=palette["node_text"],
            font_size=int(group_default(render_defaults, "branch_font_size_px", 16)),
            radius=int(node_radius),
            border_width=int(border_width),
            bold=True,
        )
        for child in branch["children"]:
            child_fill = tuple(min(255, int(channel) + 28) for channel in branch_color)
            node_bboxes[str(child["node_id"])] = _draw_node(
                image,
                draw,
                node=child,
                fill=child_fill,
                outline=palette["connector"],
                text_fill=palette["node_text"],
                font_size=int(group_default(render_defaults, "child_font_size_px", 13)),
                radius=int(max(8, node_radius - 3)),
                border_width=1,
                bold=False,
                marker=marker_by_id[str(child["marker_id"])],
            )
    node_bboxes["central"] = _draw_node(
        image,
        draw,
        node=central,
        fill=palette["central_fill"],
        outline=palette["central_outline"],
        text_fill=palette["central_text"],
        font_size=int(group_default(render_defaults, "central_font_size_px", 20)),
        radius=int(node_radius + 5),
        border_width=2,
        bold=True,
    )
    return image, {
        "node_bboxes_px": dict(node_bboxes),
        "connector_bboxes_px": dict(connector_bboxes),
    }


def _build_prompt_json_examples(*, answer_type: str) -> tuple[str, str]:
    if str(answer_type) == "string":
        answer = "New York"
        answer_only = {"answer": answer}
        with_annotation = {
            "annotation": {
                "parent_branch": [90, 120, 220, 156],
                "answer_child": [250, 190, 390, 226],
            },
            "answer": answer,
        }
    else:
        answer_only = {"answer": 3}
        with_annotation = {"annotation": [[90, 120, 220, 156], [250, 190, 390, 226]], "answer": 3}
    return (
        json.dumps(with_annotation, separators=(",", ":")),
        json.dumps(answer_only, separators=(",", ":")),
    )


def _build_output(
    *,
    task_id: str,
    domain: str,
    scene_id: str,
    instance_seed: int,
    params: Dict[str, Any],
    max_attempts: int,
) -> TaskOutput:
    del max_attempts
    rng = spawn_rng(int(instance_seed), f"{task_id}.concept_map")
    query_id, query_probabilities = _resolve_axis(
        params=params,
        gen_defaults=gen_defaults,
        supported_values=_QUERY_IDS[str(task_id)],
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
    scene, query = _build_concept_scene(
        task_id=str(task_id),
        query_id=str(query_id),
        context_id=str(context_id),
        layout_variant=str(layout_variant),
        style_variant=str(style_variant),
        rng=rng,
        params=params,
        gen_defaults=gen_defaults,
        render_defaults=render_defaults,
        instance_seed=int(instance_seed),
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
        scene=scene,
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
            "label_answer_hint",
            "annotation_hint_count",
            "annotation_hint_label",
        ),
        context=f"prompt defaults for {task_id}",
    )
    answer_type = "string" if str(task_id) == ORDERED_CHILD_LABEL_TASK_ID else "integer"
    answer_hint = str(prompt_defaults["label_answer_hint"] if answer_type == "string" else prompt_defaults["integer_answer_hint"])
    annotation_hint = str(prompt_defaults["annotation_hint_label"] if answer_type == "string" else prompt_defaults["annotation_hint_count"])
    json_example, json_example_answer_only = _build_prompt_json_examples(answer_type=answer_type)
    slots = {
        "object_description": str(prompt_defaults["object_description"]),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(answer_hint),
        "annotation_hint": str(annotation_hint),
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
    }
    slots.update({str(key): value for key, value in query.items() if key not in {"answer", "annotation_node_ids"}})
    prompt_selection = render_task_prompt_variants(
        domain=str(domain),
        scene_id=str(scene_id),
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
    for node_id in [str(item) for item in query.get("annotation_node_ids", [])]:
        annotation_id = f"node:{node_id}"
        annotation_ids.append(annotation_id)
        bbox_source_map[annotation_id] = render_map["node_bboxes_px"][node_id]
    answer_gt = (
        TypedValue(type="string", value=str(query["answer"]))
        if str(answer_type) == "string"
        else TypedValue(type="integer", value=int(query["answer"]))
    )
    if str(answer_type) == "string":
        annotation_role_node_ids = {
            str(role): str(node_id)
            for role, node_id in dict(query.get("annotation_role_node_ids", {})).items()
        }
        annotation_role_ids = {
            str(role): f"node:{node_id}"
            for role, node_id in annotation_role_node_ids.items()
        }
        annotation_bbox_map = {
            str(role): [round(float(value), 3) for value in bbox_source_map[str(annotation_id)]]
            for role, annotation_id in annotation_role_ids.items()
        }
        annotation_projection = {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(annotation_bbox_map),
            "pixel_keyed_bbox_map": dict(annotation_bbox_map),
        }
        annotation_gt = TypedValue(type="keyed_bbox_map", value=dict(annotation_bbox_map))
    else:
        annotation_role_node_ids = {}
        annotation_role_ids = {}
        annotation_projection = projected_diagram_bbox_annotation(bbox_source_map, annotation_ids)
        annotation_bboxes = [[round(float(value), 3) for value in bbox] for bbox in annotation_projection["bbox_set"]]
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))

    branch_scan = normalize_int_with_bounds(int(scene["branch_count"]), [4, 8])
    child_scan = normalize_int_with_bounds(int(scene["child_count"]), [16, 56])
    annotation_load = normalize_int_with_bounds(len(annotation_ids), [1, 10])
    base_reasoning = {
        "branch_child_count": 0.34,
        "nth_child_label": 0.42,
        "marked_child_count": 0.52,
    }[str(query["query_id"])]

    node_entities: list[Dict[str, Any]] = [
        {
            "entity_id": "central",
            "entity_type": "concept_topic",
            "label": str(scene["central_label"]),
            "shape": str(scene["branches"][0]["central"].get("shape", "rounded_rect")),
            "bbox_id": "node:central",
        }
    ]
    for branch in scene["branches"]:
        node_entities.append(
            {
                "entity_id": str(branch["branch_id"]),
                "entity_type": "concept_branch",
                "label": str(branch["label"]),
                "shape": str(branch.get("shape", "rounded_rect")),
                "bbox_id": f"node:{branch['branch_id']}",
            }
        )
        for child in branch["children"]:
            node_entities.append(
                {
                    "entity_id": str(child["node_id"]),
                    "entity_type": "concept_child",
                    "branch_id": str(branch["branch_id"]),
                    "label": str(child["label"]),
                    "marker_id": str(child["marker_id"]),
                    "shape": str(child.get("shape", "rounded_rect")),
                    "bbox_id": f"node:{child['node_id']}",
                }
            )
    branch_specs = [
        {
            "branch_id": str(branch["branch_id"]),
            "label": str(branch["label"]),
            "shape": str(branch.get("shape", "rounded_rect")),
            "bbox_id": f"node:{branch['branch_id']}",
            "child_node_ids": [str(child["node_id"]) for child in branch["children"]],
            "child_node_shapes": {str(child["node_id"]): str(child.get("shape", "rounded_rect")) for child in branch["children"]},
        }
        for branch in scene["branches"]
    ]
    trace_payload = {
        "scene_ir": {
            "scene_id": SCENE_ID,
            "scene_kind": "pages_concept_map_diagram",
            "entities": node_entities,
            "relations": {
                "query_id": str(query["query_id"]),
                "scene_variant": str(scene["layout_variant"]),
                "layout_variant": str(scene["layout_variant"]),
                "style_variant": str(scene["style_variant"]),
                "node_shape_profile": str(scene["node_shape_profile"]),
                "context_id": str(scene["context_id"]),
                "branch_specs": deepcopy(branch_specs),
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
                "node_shape_profile": str(scene["node_shape_profile"]),
                "branch_count": int(scene["branch_count"]),
                "child_count": int(scene["child_count"]),
            },
        },
        "render_spec": {
            "scene_id": SCENE_ID,
            "query_id": str(query["query_id"]),
            "scene_variant": str(scene["layout_variant"]),
            "layout_variant": str(scene["layout_variant"]),
            "style_variant": str(scene["style_variant"]),
            "node_shape_profile": str(scene["node_shape_profile"]),
            "geometry_seed": int(instance_seed),
            "canvas_width": int(scene["canvas_width"]),
            "canvas_height": int(scene["canvas_height"]),
            "layout_jitter": dict(scene["layout_jitter"]),
            "background_style": dict(background_meta),
            "post_image_noise": dict(post_noise_meta),
            "page_semantic_assets": page_semantic_asset_manifest_metadata(
                semantic_role="marker",
                allowed_use="filter",
            ),
        },
        "render_map": dict(render_map),
        "execution_trace": {
            "query_id": str(query["query_id"]),
            "question_format": str(query["query_id"]),
            "view_family": SCENE_ID,
            "scene_title": str(scene["scene_title"]),
            "central_label": str(scene["central_label"]),
            "context_id": str(scene["context_id"]),
            "layout_variant": str(scene["layout_variant"]),
            "style_variant": str(scene["style_variant"]),
            "node_shape_profile": str(scene["node_shape_profile"]),
            "branch_count": int(scene["branch_count"]),
            "child_count": int(scene["child_count"]),
            "branches": deepcopy(branch_specs),
            "page_semantic_assets": page_semantic_asset_manifest_metadata(
                semantic_role="marker",
                allowed_use="filter",
            ),
            "query": {key: value for key, value in query.items() if key not in {"task_key"}},
            "answer": answer_gt.to_dict(),
            "annotation_ids": list(annotation_ids),
            "annotation_role_ids": dict(annotation_role_ids),
            "annotation_role_node_ids": dict(annotation_role_node_ids),
            "supporting_bbox_ids": list(annotation_ids),
        },
        "witness_symbolic": {
            "type": "keyed_bbox_map" if str(answer_type) == "string" else "bbox_id_set",
            "ids": list(annotation_ids),
            "annotation_role_ids": dict(annotation_role_ids),
            "value": dict(annotation_gt.value) if str(answer_type) == "string" else list(annotation_ids),
        },
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
class PagesConceptMapBranchChildCountTask:
    """Count child items under a named concept-map branch."""

    task_id = BRANCH_CHILD_COUNT_TASK_ID
    domain = "pages"
    scene_id = "concept_map"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return _build_output(
            task_id=self.task_id,
            domain=self.domain,
            scene_id=self.scene_id,
            instance_seed=int(instance_seed),
            params=dict(params),
            max_attempts=int(max_attempts),
        )


@register_task
class PagesConceptMapMarkedChildCountTask:
    """Count child items marked with the queried concept-map marker."""

    task_id = MARKED_CHILD_COUNT_TASK_ID
    domain = "pages"
    scene_id = "concept_map"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return _build_output(
            task_id=self.task_id,
            domain=self.domain,
            scene_id=self.scene_id,
            instance_seed=int(instance_seed),
            params=dict(params),
            max_attempts=int(max_attempts),
        )


@register_task
class PagesConceptMapOrderedChildLabelTask:
    """Read an ordered child label under a named concept-map branch."""

    task_id = ORDERED_CHILD_LABEL_TASK_ID
    domain = "pages"
    scene_id = "concept_map"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return _build_output(
            task_id=self.task_id,
            domain=self.domain,
            scene_id=self.scene_id,
            instance_seed=int(instance_seed),
            params=dict(params),
            max_attempts=int(max_attempts),
        )

__all__ = [
    "BRANCH_CHILD_COUNT_TASK_ID",
    "MARKED_CHILD_COUNT_TASK_ID",
    "ORDERED_CHILD_LABEL_TASK_ID",
    "PagesConceptMapBranchChildCountTask",
    "PagesConceptMapMarkedChildCountTask",
    "PagesConceptMapOrderedChildLabelTask",
]
