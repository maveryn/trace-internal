"""Synthetic web-page action target task for GUI relation grounding."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import hash64, spawn_rng
from ....core.scene_config import get_scene_defaults, resolve_scene_section_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import resolve_render_int
from ...shared.text_rendering import draw_text_centered, fit_font_to_box, load_font
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ...shared.text_legibility import draw_text_traced
from trace.tasks.shared.fixed_query import FixedPagesQueryTaskMixin
from ..shared.public_query_task import rewrite_pages_query_output
from .gui_relation_common import (
    SUPPORTED_STYLE_VARIANTS,
    _bbox_list,
    _clamp_unit,
    _draw_text_center_fit,
    _draw_text_left,
    _normalize_str_support,
    _rounded_rect,
)


TASK_ID = "pages_web_action_target_source"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "click_target_label",
    "type_field_label",
    "select_option_label",
)
SUPPORTED_WEB_SCENE_VARIANTS: Tuple[str, ...] = (
    "shop_catalog",
    "travel_booking",
    "support_center",
    "learning_portal",
    "finance_portal",
    "content_cms",
)
_BALANCE_SALT = 112573
_GUIDE_CODE_LABELS: Tuple[str, ...] = ("K1", "M2", "R3", "T4", "V5", "X6")
_GUIDE_CUE_LABELS: Tuple[str, ...] = (
    "next step",
    "follow-up",
    "priority route",
    "review flag",
    "saved setting",
    "quick change",
)

BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]


@dataclass(frozen=True)
class _TaskDefaults:
    canvas_width: int = 1280
    canvas_height: int = 800
    browser_margin_px: int = 34
    browser_bar_height_px: int = 58
    instruction_height_px: int = 60
    corner_radius_px: int = 14
    control_corner_radius_px: int = 8
    control_outline_width_px: int = 2
    badge_size_px: int = 24
    title_font_size_px: int = 24
    body_font_size_px: int = 16
    small_font_size_px: int = 13
    label_font_size_px: int = 16
    candidate_label_pool: Tuple[str, ...] = tuple(chr(ord("A") + idx) for idx in range(26))
    web_item_pool: Tuple[str, ...] = (
        "Trail Jacket",
        "Desk Lamp",
        "Noise Filter",
        "Canvas Tote",
        "Graph Notebook",
        "Travel Mug",
        "Studio Headset",
        "Cable Kit",
    )
    web_click_action_pool: Tuple[str, ...] = ("Details", "Compare", "Save", "Open")
    web_click_category_pool: Tuple[str, ...] = ("Audio", "Office", "Travel", "Home", "Outdoor", "Creative")
    web_click_status_pool: Tuple[str, ...] = ("Ready", "Backorder", "Featured", "Clearance", "Reserved", "Limited")
    web_section_pool: Tuple[str, ...] = ("Account", "Traveler", "Billing", "Delivery", "Notifications")
    web_field_pool: Tuple[str, ...] = ("Email", "Phone", "City", "Reference", "Notes")
    web_option_group_pool: Tuple[str, ...] = ("Delivery speed", "Plan type", "Seat zone", "Alert channel")
    web_option_pool: Tuple[str, ...] = ("Standard", "Priority", "Economy", "Window", "Monthly", "Email")


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    browser_margin_px: int
    browser_bar_height_px: int
    instruction_height_px: int
    corner_radius_px: int
    control_corner_radius_px: int
    control_outline_width_px: int
    badge_size_px: int
    title_font_size_px: int
    body_font_size_px: int
    small_font_size_px: int
    label_font_size_px: int


@dataclass(frozen=True)
class _WebTheme:
    name: str
    page_fill: Color
    browser_fill: Color
    browser_line: Color
    chrome_fill: Color
    nav_fill: Color
    panel_fill: Color
    panel_alt_fill: Color
    control_fill: Color
    control_outline: Color
    text: Color
    muted_text: Color
    accent: Color
    accent_alt: Color
    instruction_fill: Color
    instruction_line: Color
    badge_fill: Color
    badge_text: Color


@dataclass(frozen=True)
class _WebProfile:
    site_name: str
    url_path: str
    page_title: str
    nav_items: Tuple[str, ...]
    status_text: str


@dataclass(frozen=True)
class _ControlSpec:
    control_id: str
    candidate_label: str
    role: str
    display_text: str
    context_label: str
    context_display_label: str
    context_attribute_1: str
    context_attribute_2: str
    action_label: str
    action_cue_label: str
    action_code_label: str
    support_id: str
    support_kind: str
    row_index: int
    col_index: int
    order_index: int


@dataclass(frozen=True)
class _GuideEntry:
    support_id: str
    support_kind: str
    cue_label: str
    code_label: str
    action_label: str
    col_index: int
    order_index: int


@dataclass(frozen=True)
class _ResolvedQuery:
    query_id: str
    scene_variant: str
    style_variant: str
    controls: Tuple[_ControlSpec, ...]
    target_control_id: str
    target_label: str
    context_label: str
    action_label: str
    instruction_cue_label: str
    instruction_code_label: str
    instruction_text: str
    instruction_template_index: int
    guide_entries: Tuple[_GuideEntry, ...]
    instruction_support_id: str
    guide_support_id: str
    context_support_id: str
    context_support_kind: str
    candidate_label_pool: Tuple[str, ...]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedScene:
    control_bboxes_by_id: Dict[str, List[float]]
    badge_bboxes_by_id: Dict[str, List[float]]
    support_bboxes_by_id: Dict[str, List[float]]
    control_records: Tuple[Dict[str, Any], ...]
    support_records: Tuple[Dict[str, Any], ...]
    scene_bbox_px: List[float]
    browser_bbox_px: List[float]
    profile: _WebProfile
    theme: _WebTheme


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_scene_defaults("pages", "relation")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_VISUAL_DEFAULTS = _TASK_GROUP_DEFAULTS.get("visual", {}) if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {}
POST_IMAGE_BACKGROUND_DEFAULTS = (
    dict(_VISUAL_DEFAULTS.get("background", {})) if isinstance(_VISUAL_DEFAULTS.get("background"), Mapping) else {}
)
POST_IMAGE_NOISE_DEFAULTS = (
    dict(_VISUAL_DEFAULTS.get("noise", {})) if isinstance(_VISUAL_DEFAULTS.get("noise"), Mapping) else {}
)


_WEB_PROFILES: Dict[str, _WebProfile] = {
    "shop_catalog": _WebProfile(
        "MarketLane",
        "/catalog/deals",
        "Product Picks",
        ("Deals", "Orders", "Saved", "Help"),
        "8 items",
    ),
    "travel_booking": _WebProfile(
        "TripNest",
        "/book/stays",
        "Trip Planner",
        ("Flights", "Stays", "Cars", "Trips"),
        "Draft trip",
    ),
    "support_center": _WebProfile(
        "Assistly",
        "/support/tickets",
        "Support Queue",
        ("Inbox", "Customers", "Reports", "Macros"),
        "12 open",
    ),
    "learning_portal": _WebProfile(
        "CoursePad",
        "/learn/dashboard",
        "Learning Hub",
        ("Courses", "Calendar", "Grades", "Messages"),
        "3 due",
    ),
    "finance_portal": _WebProfile(
        "LedgerWay",
        "/payments/settings",
        "Payment Center",
        ("Cards", "Bills", "Transfers", "Settings"),
        "Secure",
    ),
    "content_cms": _WebProfile(
        "PublishKit",
        "/cms/articles",
        "Editorial Desk",
        ("Drafts", "Assets", "Review", "Publish"),
        "Autosaved",
    ),
}


def _theme(style_variant: str) -> _WebTheme:
    if str(style_variant) == "cool":
        return _WebTheme(
            name="cool",
            page_fill=(243, 248, 252),
            browser_fill=(255, 255, 255),
            browser_line=(196, 210, 224),
            chrome_fill=(233, 241, 249),
            nav_fill=(236, 244, 252),
            panel_fill=(255, 255, 255),
            panel_alt_fill=(245, 249, 253),
            control_fill=(255, 255, 255),
            control_outline=(176, 194, 212),
            text=(33, 46, 62),
            muted_text=(84, 99, 117),
            accent=(39, 113, 172),
            accent_alt=(62, 142, 137),
            instruction_fill=(234, 244, 255),
            instruction_line=(39, 113, 172),
            badge_fill=(194, 48, 58),
            badge_text=(255, 255, 255),
        )
    if str(style_variant) == "warm":
        return _WebTheme(
            name="warm",
            page_fill=(250, 248, 243),
            browser_fill=(255, 255, 252),
            browser_line=(216, 203, 188),
            chrome_fill=(244, 238, 229),
            nav_fill=(248, 241, 231),
            panel_fill=(255, 255, 252),
            panel_alt_fill=(250, 246, 239),
            control_fill=(255, 255, 252),
            control_outline=(204, 184, 162),
            text=(54, 43, 33),
            muted_text=(109, 91, 72),
            accent=(159, 90, 45),
            accent_alt=(47, 126, 119),
            instruction_fill=(255, 241, 226),
            instruction_line=(159, 90, 45),
            badge_fill=(152, 53, 63),
            badge_text=(255, 255, 255),
        )
    if str(style_variant) == "sage":
        return _WebTheme(
            name="sage",
            page_fill=(244, 250, 247),
            browser_fill=(255, 255, 255),
            browser_line=(196, 215, 207),
            chrome_fill=(234, 244, 239),
            nav_fill=(235, 246, 241),
            panel_fill=(255, 255, 255),
            panel_alt_fill=(245, 250, 248),
            control_fill=(255, 255, 255),
            control_outline=(174, 198, 187),
            text=(34, 52, 46),
            muted_text=(80, 103, 95),
            accent=(41, 123, 100),
            accent_alt=(166, 91, 65),
            instruction_fill=(233, 247, 241),
            instruction_line=(41, 123, 100),
            badge_fill=(178, 46, 58),
            badge_text=(255, 255, 255),
        )
    if str(style_variant) == "compact":
        return _WebTheme(
            name="compact",
            page_fill=(246, 249, 250),
            browser_fill=(255, 255, 255),
            browser_line=(197, 207, 214),
            chrome_fill=(235, 241, 244),
            nav_fill=(236, 245, 244),
            panel_fill=(255, 255, 255),
            panel_alt_fill=(241, 246, 247),
            control_fill=(255, 255, 255),
            control_outline=(169, 183, 193),
            text=(32, 42, 50),
            muted_text=(83, 94, 105),
            accent=(0, 127, 141),
            accent_alt=(204, 83, 62),
            instruction_fill=(238, 248, 246),
            instruction_line=(0, 127, 141),
            badge_fill=(190, 38, 46),
            badge_text=(255, 255, 255),
        )
    if str(style_variant) == "contrast":
        return _WebTheme(
            name="contrast",
            page_fill=(249, 248, 244),
            browser_fill=(255, 255, 252),
            browser_line=(188, 185, 175),
            chrome_fill=(239, 238, 231),
            nav_fill=(245, 239, 228),
            panel_fill=(255, 255, 252),
            panel_alt_fill=(244, 241, 233),
            control_fill=(255, 255, 252),
            control_outline=(85, 89, 94),
            text=(29, 31, 34),
            muted_text=(78, 82, 89),
            accent=(174, 54, 74),
            accent_alt=(31, 126, 108),
            instruction_fill=(255, 243, 231),
            instruction_line=(174, 54, 74),
            badge_fill=(34, 34, 38),
            badge_text=(255, 255, 255),
        )
    return _WebTheme(
        name="standard",
        page_fill=(244, 248, 252),
        browser_fill=(255, 255, 255),
        browser_line=(197, 207, 220),
        chrome_fill=(234, 240, 248),
        nav_fill=(236, 242, 250),
        panel_fill=(255, 255, 255),
        panel_alt_fill=(246, 249, 253),
        control_fill=(255, 255, 255),
        control_outline=(181, 193, 209),
        text=(34, 45, 60),
        muted_text=(87, 100, 118),
        accent=(45, 112, 196),
        accent_alt=(220, 118, 54),
        instruction_fill=(235, 244, 255),
        instruction_line=(45, 112, 196),
        badge_fill=(206, 46, 58),
        badge_text=(255, 255, 255),
    )


def _decoupled_params(params: Mapping[str, Any], *, divisor: int, namespace: str) -> Mapping[str, Any]:
    _ = int(divisor), namespace
    return params


def _support_selection_index(params: Mapping[str, Any], *, instance_seed: int, namespace: str) -> int:
    return int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:{namespace}"))


def _resolve_named_axis(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    supported: Tuple[str, ...],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    namespace: str,
) -> Tuple[str, Dict[str, float]]:
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=supported,
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=supported,
        balance_flag_key=str(balance_flag_key),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        sampling_namespace=f"{TASK_ID}:{namespace}",
    )
    return str(selected), dict(probabilities)


def _resolve_query_id(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    return _resolve_named_axis(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        supported=SUPPORTED_QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        namespace="query_id",
    )


def _resolve_axis_bounds(
    params: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
) -> Tuple[int, int]:
    min_value = int(params.get(str(min_key), group_default(_GEN_DEFAULTS, str(min_key), int(fallback_min))))
    max_value = int(params.get(str(max_key), group_default(_GEN_DEFAULTS, str(max_key), int(fallback_max))))
    if int(min_value) > int(max_value):
        raise ValueError(f"{min_key} must be <= {max_key} for {TASK_ID}")
    return int(min_value), int(max_value)


def _resolve_count(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    namespace: str,
) -> int:
    min_value, max_value = _resolve_axis_bounds(
        params,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
    )
    span = int(max_value) - int(min_value) + 1
    return int(min_value) + (_support_selection_index(params, instance_seed=int(instance_seed), namespace=str(namespace)) % max(1, span))


def _resolve_render_params(params: Mapping[str, Any], *, instance_seed: int) -> _RenderParams:
    values = asdict(_DEFAULTS)

    def _int_value(key: str) -> int:
        return int(
            resolve_render_int(
                params,
                _RENDER_DEFAULTS,
                str(key),
                int(values[str(key)]),
                instance_seed=instance_seed,
                namespace=TASK_ID,
            )
        )

    return _RenderParams(
        canvas_width=_int_value("canvas_width"),
        canvas_height=_int_value("canvas_height"),
        browser_margin_px=_int_value("browser_margin_px"),
        browser_bar_height_px=_int_value("browser_bar_height_px"),
        instruction_height_px=_int_value("instruction_height_px"),
        corner_radius_px=_int_value("corner_radius_px"),
        control_corner_radius_px=_int_value("control_corner_radius_px"),
        control_outline_width_px=_int_value("control_outline_width_px"),
        badge_size_px=_int_value("badge_size_px"),
        title_font_size_px=_int_value("title_font_size_px"),
        body_font_size_px=_int_value("body_font_size_px"),
        small_font_size_px=_int_value("small_font_size_px"),
        label_font_size_px=_int_value("label_font_size_px"),
    )


def _sample_values(values: Sequence[str], *, count: int, rng) -> Tuple[str, ...]:
    support = [str(value) for value in values if str(value).strip()]
    if int(count) > len(support):
        raise ValueError(f"not enough GUI web support values: requested {count}, have {len(support)}")
    rng.shuffle(support)
    return tuple(support[: int(count)])


def _sample_click_attribute_pairs(params: Mapping[str, Any], *, count: int, rng) -> Tuple[Tuple[str, str], ...]:
    categories = _normalize_str_support(params, "web_click_category_pool", _DEFAULTS.web_click_category_pool)
    statuses = _normalize_str_support(params, "web_click_status_pool", _DEFAULTS.web_click_status_pool)
    pairs = [(str(category), str(status)) for category in categories for status in statuses]
    if int(count) > len(pairs):
        raise ValueError(f"not enough click attribute pairs: requested {count}, have {len(pairs)}")
    rng.shuffle(pairs)
    return tuple(pairs[: int(count)])


def _base_click_controls(params: Mapping[str, Any], *, instance_seed: int, rng) -> Tuple[_ControlSpec, ...]:
    item_count = _resolve_count(
        params,
        instance_seed=int(instance_seed),
        min_key="web_click_item_count_min",
        max_key="web_click_item_count_max",
        fallback_min=4,
        fallback_max=6,
        namespace="click.item_count",
    )
    action_count = _resolve_count(
        params,
        instance_seed=int(instance_seed),
        min_key="web_click_action_count_min",
        max_key="web_click_action_count_max",
        fallback_min=3,
        fallback_max=4,
        namespace="click.action_count",
    )
    items = _sample_values(
        _normalize_str_support(params, "web_item_pool", _DEFAULTS.web_item_pool),
        count=int(item_count),
        rng=rng,
    )
    actions = _sample_values(
        _normalize_str_support(params, "web_click_action_pool", _DEFAULTS.web_click_action_pool),
        count=int(action_count),
        rng=rng,
    )
    attribute_pairs = _sample_click_attribute_pairs(params, count=int(item_count), rng=rng)
    controls: List[_ControlSpec] = []
    for row_index, item_label in enumerate(items):
        category, status = attribute_pairs[int(row_index)]
        context_label = f'category "{category}" and status "{status}"'
        visual_order = list(range(len(actions)))
        spawn_rng(int(instance_seed), f"{TASK_ID}.click.button_order.{row_index}").shuffle(visual_order)
        visual_slot_by_col = {int(col_index): int(slot_index) for slot_index, col_index in enumerate(visual_order)}
        for col_index, action_label in enumerate(actions):
            controls.append(
                _ControlSpec(
                    control_id=f"click_{row_index}_{col_index}",
                    candidate_label="",
                    role="web_button",
                    display_text=str(action_label),
                    context_label=str(context_label),
                    context_display_label=str(item_label),
                    context_attribute_1=str(category),
                    context_attribute_2=str(status),
                    action_label=str(action_label),
                    action_cue_label="",
                    action_code_label="",
                    support_id=f"support_click_card_{row_index}",
                    support_kind="item_card",
                    row_index=int(row_index),
                    col_index=int(col_index),
                    order_index=int(visual_slot_by_col[int(col_index)]),
                )
            )
    return tuple(controls)


def _base_type_controls(params: Mapping[str, Any], *, instance_seed: int, rng) -> Tuple[_ControlSpec, ...]:
    section_count = _resolve_count(
        params,
        instance_seed=int(instance_seed),
        min_key="web_type_section_count_min",
        max_key="web_type_section_count_max",
        fallback_min=3,
        fallback_max=4,
        namespace="type.section_count",
    )
    field_count = _resolve_count(
        params,
        instance_seed=int(instance_seed),
        min_key="web_type_field_count_min",
        max_key="web_type_field_count_max",
        fallback_min=3,
        fallback_max=4,
        namespace="type.field_count",
    )
    sections = _sample_values(
        _normalize_str_support(params, "web_section_pool", _DEFAULTS.web_section_pool),
        count=int(section_count),
        rng=rng,
    )
    fields = _sample_values(
        _normalize_str_support(params, "web_field_pool", _DEFAULTS.web_field_pool),
        count=int(field_count),
        rng=rng,
    )
    controls: List[_ControlSpec] = []
    order_index = 0
    for row_index, section_label in enumerate(sections):
        for col_index, field_label in enumerate(fields):
            controls.append(
                _ControlSpec(
                    control_id=f"type_{row_index}_{col_index}",
                    candidate_label="",
                    role="web_input",
                    display_text=f"Enter {str(field_label).lower()}",
                    context_label=str(section_label),
                    context_display_label=str(section_label),
                    context_attribute_1="",
                    context_attribute_2="",
                    action_label=str(field_label),
                    action_cue_label="",
                    action_code_label="",
                    support_id=f"support_type_section_{row_index}",
                    support_kind="form_section",
                    row_index=int(row_index),
                    col_index=int(col_index),
                    order_index=int(order_index),
                )
            )
            order_index += 1
    return tuple(controls)


def _base_select_controls(params: Mapping[str, Any], *, instance_seed: int, rng) -> Tuple[_ControlSpec, ...]:
    group_count = _resolve_count(
        params,
        instance_seed=int(instance_seed),
        min_key="web_select_group_count_min",
        max_key="web_select_group_count_max",
        fallback_min=3,
        fallback_max=4,
        namespace="select.group_count",
    )
    option_count = _resolve_count(
        params,
        instance_seed=int(instance_seed),
        min_key="web_select_option_count_min",
        max_key="web_select_option_count_max",
        fallback_min=3,
        fallback_max=4,
        namespace="select.option_count",
    )
    groups = _sample_values(
        _normalize_str_support(params, "web_option_group_pool", _DEFAULTS.web_option_group_pool),
        count=int(group_count),
        rng=rng,
    )
    options = _sample_values(
        _normalize_str_support(params, "web_option_pool", _DEFAULTS.web_option_pool),
        count=int(option_count),
        rng=rng,
    )
    controls: List[_ControlSpec] = []
    order_index = 0
    for row_index, group_label in enumerate(groups):
        for col_index, option_label in enumerate(options):
            controls.append(
                _ControlSpec(
                    control_id=f"select_{row_index}_{col_index}",
                    candidate_label="",
                    role="web_option",
                    display_text=str(option_label),
                    context_label=str(group_label),
                    context_display_label=str(group_label),
                    context_attribute_1="",
                    context_attribute_2="",
                    action_label=str(option_label),
                    action_cue_label="",
                    action_code_label="",
                    support_id=f"support_select_group_{row_index}",
                    support_kind="option_group",
                    row_index=int(row_index),
                    col_index=int(col_index),
                    order_index=int(order_index),
                )
            )
            order_index += 1
    return tuple(controls)


def _instruction_for_target(
    *,
    query_id: str,
    target: _ControlSpec,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, int]:
    explicit = params.get("instruction_text")
    if explicit is not None:
        return str(explicit), 0
    if str(query_id) == "type_field_label":
        templates = (
            'In "{context}", use the field cue "{cue}" from the guide',
            'Enter text for "{context}" using guide cue "{cue}"',
            'Use the input in "{context}" whose guide cue is "{cue}"',
        )
    elif str(query_id) == "select_option_label":
        templates = (
            'For "{context}", use the option cue "{cue}" from the guide',
            'Choose the option for "{context}" with guide cue "{cue}"',
            'Set "{context}" according to guide cue "{cue}"',
        )
    else:
        templates = (
            'For the item with {context}, use the action cue "{cue}" from the guide',
            'Click the control on the item with {context} and guide cue "{cue}"',
            'Use the guided action for the item with {context} and cue "{cue}"',
        )
    index = _support_selection_index(params, instance_seed=int(instance_seed), namespace=f"instruction.{query_id}") % len(templates)
    return (
        str(templates[int(index)]).format(cue=str(target.action_cue_label), context=str(target.context_label)),
        int(index),
    )


def _guide_support_kind(query_id: str) -> str:
    if str(query_id) == "type_field_label":
        return "field_guide_card"
    if str(query_id) == "select_option_label":
        return "option_guide_card"
    return "action_guide_card"


def _coded_display_text(query_id: str, code_label: str) -> str:
    if str(query_id) == "type_field_label":
        return "Enter value"
    if str(query_id) == "select_option_label":
        return str(code_label)
    return str(code_label)


def _with_guide_codes(
    controls: Sequence[_ControlSpec],
    *,
    query_id: str,
    instance_seed: int,
) -> Tuple[Tuple[_ControlSpec, ...], Tuple[_GuideEntry, ...]]:
    columns = sorted({int(control.col_index) for control in controls})
    if len(columns) > min(len(_GUIDE_CODE_LABELS), len(_GUIDE_CUE_LABELS)):
        raise ValueError(f"not enough guide codes/cues for {TASK_ID}")
    code_labels = list(_GUIDE_CODE_LABELS)
    cue_labels = list(_GUIDE_CUE_LABELS)
    spawn_rng(int(instance_seed), f"{TASK_ID}.guide_codes.{query_id}").shuffle(code_labels)
    spawn_rng(int(instance_seed), f"{TASK_ID}.guide_cues.{query_id}").shuffle(cue_labels)
    action_by_col = {
        int(col_index): str(next(control.action_label for control in controls if int(control.col_index) == int(col_index)))
        for col_index in columns
    }
    code_by_col = {int(col_index): str(code_labels[index]) for index, col_index in enumerate(columns)}
    cue_by_col = {int(col_index): str(cue_labels[index]) for index, col_index in enumerate(columns)}
    guide_entries = [
        _GuideEntry(
            support_id=f"support_guide_{int(col_index)}",
            support_kind=_guide_support_kind(str(query_id)),
            cue_label=str(cue_by_col[int(col_index)]),
            code_label=str(code_by_col[int(col_index)]),
            action_label=str(action_by_col[int(col_index)]),
            col_index=int(col_index),
            order_index=index,
        )
        for index, col_index in enumerate(columns)
    ]
    order = list(range(len(guide_entries)))
    spawn_rng(int(instance_seed), f"{TASK_ID}.guide_order.{query_id}").shuffle(order)
    shuffled_entries = tuple(guide_entries[index] for index in order)
    coded_controls: List[_ControlSpec] = []
    for control in controls:
        col_index = int(control.col_index)
        code_label = str(code_by_col[col_index])
        cue_label = str(cue_by_col[col_index])
        coded_controls.append(
            _ControlSpec(
                control_id=str(control.control_id),
                candidate_label=str(control.candidate_label),
                role=str(control.role),
                display_text=_coded_display_text(str(query_id), code_label),
                context_label=str(control.context_label),
                context_display_label=str(control.context_display_label),
                context_attribute_1=str(control.context_attribute_1),
                context_attribute_2=str(control.context_attribute_2),
                action_label=str(control.action_label),
                action_cue_label=str(cue_label),
                action_code_label=str(code_label),
                support_id=str(control.support_id),
                support_kind=str(control.support_kind),
                row_index=int(control.row_index),
                col_index=int(control.col_index),
                order_index=int(control.order_index),
            )
        )
    return tuple(coded_controls), shuffled_entries


def _with_candidate_labels(
    controls: Sequence[_ControlSpec],
    *,
    target_control_id: str,
    target_label: str,
    candidate_label_pool: Sequence[str],
    instance_seed: int,
) -> Tuple[_ControlSpec, ...]:
    labels = [str(value) for value in candidate_label_pool]
    if str(target_label) not in labels:
        raise ValueError(f"target_label must be in candidate_label_pool for {TASK_ID}")
    if len(controls) > len(labels):
        raise ValueError(f"candidate_label_pool has {len(labels)} labels for {len(controls)} controls in {TASK_ID}")
    remaining = [label for label in labels if str(label) != str(target_label)]
    spawn_rng(int(instance_seed), f"{TASK_ID}.candidate_labels").shuffle(remaining)
    out: List[_ControlSpec] = []
    next_index = 0
    for control in controls:
        label = str(target_label) if str(control.control_id) == str(target_control_id) else str(remaining[next_index])
        if str(control.control_id) != str(target_control_id):
            next_index += 1
        out.append(
            _ControlSpec(
                control_id=str(control.control_id),
                candidate_label=str(label),
                role=str(control.role),
                display_text=str(control.display_text),
                context_label=str(control.context_label),
                context_display_label=str(control.context_display_label),
                context_attribute_1=str(control.context_attribute_1),
                context_attribute_2=str(control.context_attribute_2),
                action_label=str(control.action_label),
                action_cue_label=str(control.action_cue_label),
                action_code_label=str(control.action_code_label),
                support_id=str(control.support_id),
                support_kind=str(control.support_kind),
                row_index=int(control.row_index),
                col_index=int(control.col_index),
                order_index=int(control.order_index),
            )
        )
    return tuple(out)


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query")
    query_id, query_id_probabilities = _resolve_query_id(rng, instance_seed=int(instance_seed), params=params)
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        rng,
        instance_seed=int(instance_seed),
        params=_decoupled_params(params, divisor=len(SUPPORTED_QUERY_IDS), namespace="scene_variant"),
        supported=SUPPORTED_WEB_SCENE_VARIANTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        namespace="scene_variant",
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        rng,
        instance_seed=int(instance_seed),
        params=_decoupled_params(params, divisor=len(SUPPORTED_QUERY_IDS), namespace="style_variant"),
        supported=SUPPORTED_STYLE_VARIANTS,
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        namespace="style_variant",
    )

    if str(query_id) == "type_field_label":
        base_controls = _base_type_controls(params, instance_seed=int(instance_seed), rng=rng)
    elif str(query_id) == "select_option_label":
        base_controls = _base_select_controls(params, instance_seed=int(instance_seed), rng=rng)
    else:
        base_controls = _base_click_controls(params, instance_seed=int(instance_seed), rng=rng)
    if not base_controls:
        raise ValueError(f"{TASK_ID} generated no target controls")
    coded_controls, guide_entries = _with_guide_codes(
        base_controls,
        query_id=str(query_id),
        instance_seed=int(instance_seed),
    )

    target_index = _support_selection_index(params, instance_seed=int(instance_seed), namespace=f"target.{query_id}") % len(coded_controls)
    target_without_label = coded_controls[int(target_index)]
    candidate_label_pool = _normalize_str_support(params, "candidate_label_pool", _DEFAULTS.candidate_label_pool)
    target_label = str(
        params.get(
            "target_label",
            candidate_label_pool[
                _support_selection_index(params, instance_seed=int(instance_seed), namespace=f"answer_label.{query_id}")
                % len(candidate_label_pool)
            ],
        )
    )
    controls = _with_candidate_labels(
        coded_controls,
        target_control_id=str(target_without_label.control_id),
        target_label=str(target_label),
        candidate_label_pool=candidate_label_pool,
        instance_seed=int(instance_seed),
    )
    target = next(control for control in controls if str(control.control_id) == str(target_without_label.control_id))
    instruction_text, instruction_template_index = _instruction_for_target(
        query_id=str(query_id),
        target=target,
        instance_seed=int(instance_seed),
        params=params,
    )
    return _ResolvedQuery(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        controls=tuple(controls),
        target_control_id=str(target.control_id),
        target_label=str(target_label),
        context_label=str(target.context_label),
        action_label=str(target.action_label),
        instruction_cue_label=str(target.action_cue_label),
        instruction_code_label=str(target.action_code_label),
        instruction_text=str(instruction_text),
        instruction_template_index=int(instruction_template_index),
        guide_entries=tuple(guide_entries),
        instruction_support_id="support_instruction",
        guide_support_id=f"support_guide_{int(target.col_index)}",
        context_support_id=str(target.support_id),
        context_support_kind=str(target.support_kind),
        candidate_label_pool=tuple(str(value) for value in candidate_label_pool),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
    )


def _add_support(
    support_bboxes: Dict[str, List[float]],
    support_records: List[Dict[str, Any]],
    support_id: str,
    support_kind: str,
    display_text: str,
    bbox: BBox,
    attrs: Mapping[str, Any] | None = None,
) -> None:
    if str(support_id) in support_bboxes:
        return
    support_bboxes[str(support_id)] = _bbox_list(bbox)
    record = {
        "support_id": str(support_id),
        "support_kind": str(support_kind),
        "display_text": str(display_text),
        "bbox_px": _bbox_list(bbox),
    }
    if attrs:
        record.update({str(key): value for key, value in attrs.items()})
    support_records.append(record)


def _draw_browser_frame(
    draw: ImageDraw.ImageDraw,
    *,
    query: _ResolvedQuery,
    render_params: _RenderParams,
    theme: _WebTheme,
) -> Tuple[BBox, _WebProfile, BBox]:
    profile = _WEB_PROFILES[str(query.scene_variant)]
    m = float(render_params.browser_margin_px)
    width = float(render_params.canvas_width)
    height = float(render_params.canvas_height)
    browser = (m, m - 6.0, width - m, height - m + 6.0)
    _rounded_rect(draw, browser, radius=int(render_params.corner_radius_px), fill=theme.browser_fill, outline=theme.browser_line, width=2)
    bar_h = float(render_params.browser_bar_height_px)
    bar = (browser[0], browser[1], browser[2], browser[1] + bar_h)
    draw.rounded_rectangle([bar[0], bar[1], bar[2], bar[3] + int(render_params.corner_radius_px)], radius=int(render_params.corner_radius_px), fill=theme.chrome_fill)
    draw.rectangle([bar[0], bar[3] - int(render_params.corner_radius_px), bar[2], bar[3]], fill=theme.chrome_fill)
    for idx, fill in enumerate(((226, 78, 69), (236, 178, 67), (88, 176, 98))):
        draw.ellipse([bar[0] + 18.0 + idx * 22.0, bar[1] + 18.0, bar[0] + 30.0 + idx * 22.0, bar[1] + 30.0], fill=fill)
    address = (bar[0] + 104.0, bar[1] + 13.0, bar[2] - 266.0, bar[1] + 41.0)
    _rounded_rect(draw, address, radius=14, fill=(255, 255, 255), outline=theme.browser_line, width=1)
    _draw_text_left(
        draw,
        text=f"https://{profile.site_name.lower()}.example{profile.url_path}",
        bbox=(address[0] + 16.0, address[1] + 5.0, address[2] - 16.0, address[3] - 5.0),
        fill=theme.muted_text,
        max_size_px=int(render_params.small_font_size_px),
    )
    status = (bar[2] - 238.0, bar[1] + 13.0, bar[2] - 26.0, bar[1] + 41.0)
    _rounded_rect(draw, status, radius=14, fill=(255, 255, 255), outline=theme.browser_line, width=1)
    _draw_text_center_fit(
        draw,
        text=str(profile.status_text),
        bbox=(status[0] + 8.0, status[1] + 4.0, status[2] - 8.0, status[3] - 4.0),
        fill=theme.muted_text,
        max_size_px=int(render_params.small_font_size_px),
        bold=True,
    )

    page_header = (browser[0], bar[3], browser[2], bar[3] + 66.0)
    draw.rectangle([page_header[0], page_header[1], page_header[2], page_header[3]], fill=theme.page_fill)
    logo = (page_header[0] + 26.0, page_header[1] + 16.0, page_header[0] + 54.0, page_header[1] + 44.0)
    _rounded_rect(draw, logo, radius=8, fill=theme.accent, outline=None)
    draw_text_centered(
        draw,
        text=str(profile.site_name)[:1],
        center=((logo[0] + logo[2]) / 2.0, (logo[1] + logo[3]) / 2.0),
        font=load_font(int(render_params.small_font_size_px), bold=True),
        fill=(255, 255, 255),
    )
    draw_text_traced(draw,(page_header[0] + 66.0, page_header[1] + 14.0), str(profile.site_name), fill=theme.text, font=load_font(int(render_params.body_font_size_px), bold=True), role="readout", required=False)
    nav_x = page_header[0] + 238.0
    for idx, nav_label in enumerate(profile.nav_items):
        nav_w = 92.0 if len(str(nav_label)) <= 8 else 118.0
        nav_bbox = (nav_x, page_header[1] + 18.0, nav_x + nav_w, page_header[1] + 46.0)
        if idx == 0:
            _rounded_rect(draw, nav_bbox, radius=14, fill=theme.nav_fill, outline=theme.accent, width=1)
            fill = theme.text
        else:
            fill = theme.muted_text
        _draw_text_center_fit(
            draw,
            text=str(nav_label),
            bbox=(nav_bbox[0] + 8.0, nav_bbox[1] + 4.0, nav_bbox[2] - 8.0, nav_bbox[3] - 4.0),
            fill=fill,
            max_size_px=int(render_params.small_font_size_px),
            bold=True,
        )
        nav_x += nav_w + 8.0
    draw.line([browser[0], page_header[3], browser[2], page_header[3]], fill=theme.browser_line, width=1)
    content = (browser[0] + 24.0, page_header[3] + 18.0, browser[2] - 24.0, browser[3] - 20.0)
    return content, profile, browser


def _draw_instruction(
    draw: ImageDraw.ImageDraw,
    *,
    content_bbox: BBox,
    query: _ResolvedQuery,
    render_params: _RenderParams,
    theme: _WebTheme,
    support_bboxes: Dict[str, List[float]],
    support_records: List[Dict[str, Any]],
) -> BBox:
    x1, y1, x2, _y2 = [float(value) for value in content_bbox]
    instruction = (x1, y1, x2, y1 + float(render_params.instruction_height_px))
    _rounded_rect(draw, instruction, radius=12, fill=theme.instruction_fill, outline=theme.instruction_line, width=2)
    draw_text_traced(draw,(instruction[0] + 20.0, instruction[1] + 10.0), "Action instruction", fill=theme.muted_text, font=load_font(int(render_params.small_font_size_px), bold=True), role="readout", required=False)
    _draw_text_left(
        draw,
        text=str(query.instruction_text),
        bbox=(instruction[0] + 20.0, instruction[1] + 30.0, instruction[2] - 20.0, instruction[3] - 8.0),
        fill=theme.text,
        max_size_px=int(render_params.body_font_size_px),
        bold=True,
    )
    _add_support(
        support_bboxes,
        support_records,
        str(query.instruction_support_id),
        "instruction_banner",
        str(query.instruction_text),
        instruction,
    )
    return instruction


def _draw_action_guide(
    draw: ImageDraw.ImageDraw,
    *,
    content_bbox: BBox,
    top_y: float,
    query: _ResolvedQuery,
    render_params: _RenderParams,
    theme: _WebTheme,
    support_bboxes: Dict[str, List[float]],
    support_records: List[Dict[str, Any]],
) -> BBox:
    x1, _y1, x2, _y2 = [float(value) for value in content_bbox]
    guide_h = 74.0
    guide = (x1, float(top_y), x2, float(top_y) + guide_h)
    _rounded_rect(draw, guide, radius=12, fill=theme.panel_alt_fill, outline=theme.browser_line, width=1)
    title = "Action Guide"
    if str(query.query_id) == "type_field_label":
        title = "Field Guide"
    elif str(query.query_id) == "select_option_label":
        title = "Option Guide"
    _draw_text_left(
        draw,
        text=title,
        bbox=(guide[0] + 18.0, guide[1] + 14.0, guide[0] + 178.0, guide[3] - 14.0),
        fill=theme.text,
        max_size_px=int(render_params.body_font_size_px),
        bold=True,
    )
    entries = tuple(query.guide_entries)
    if not entries:
        return guide
    gap = 10.0
    card_x1 = guide[0] + 190.0
    card_w = (guide[2] - card_x1 - 18.0 - gap * (len(entries) - 1)) / float(len(entries))
    for slot_index, entry in enumerate(entries):
        card = (
            card_x1 + slot_index * (card_w + gap),
            guide[1] + 12.0,
            card_x1 + slot_index * (card_w + gap) + card_w,
            guide[3] - 12.0,
        )
        _rounded_rect(draw, card, radius=8, fill=theme.control_fill, outline=theme.accent if slot_index % 2 == 0 else theme.accent_alt, width=2)
        _draw_text_center_fit(
            draw,
            text=str(entry.cue_label),
            bbox=(card[0] + 8.0, card[1] + 5.0, card[2] - 8.0, card[1] + 27.0),
            fill=theme.text,
            max_size_px=int(render_params.small_font_size_px),
            bold=True,
        )
        _draw_text_center_fit(
            draw,
            text=f"key {entry.code_label}",
            bbox=(card[0] + 8.0, card[1] + 28.0, card[2] - 8.0, card[3] - 5.0),
            fill=theme.muted_text,
            max_size_px=int(render_params.small_font_size_px),
        )
        _add_support(
            support_bboxes,
            support_records,
            str(entry.support_id),
            str(entry.support_kind),
            str(entry.cue_label),
            card,
            attrs={
                "cue_label": str(entry.cue_label),
                "code_label": str(entry.code_label),
                "action_label": str(entry.action_label),
                "col_index": int(entry.col_index),
                "guide_slot": int(slot_index),
            },
        )
    return guide


def _draw_candidate_badge(
    draw: ImageDraw.ImageDraw,
    *,
    control_bbox: BBox,
    label: str,
    render_params: _RenderParams,
    theme: _WebTheme,
) -> List[float]:
    x1, y1, x2, y2 = [float(value) for value in control_bbox]
    size = max(18, min(int(render_params.badge_size_px), int(min(float(x2 - x1), float(y2 - y1)) - 8.0)))
    badge = (x1 + 6.0, y1 + 6.0, x1 + 6.0 + float(size), y1 + 6.0 + float(size))
    _rounded_rect(draw, badge, radius=5, fill=theme.badge_fill, outline=(255, 255, 255), width=2)
    font = fit_font_to_box(
        draw,
        text=str(label),
        max_width=float(size) * 0.70,
        max_height=float(size) * 0.70,
        bold=True,
        min_size_px=8,
        max_size_px=int(render_params.label_font_size_px),
        fill_ratio=1.0,
    )
    draw_text_centered(
        draw,
        text=str(label),
        center=((badge[0] + badge[2]) / 2.0, (badge[1] + badge[3]) / 2.0),
        font=font,
        fill=theme.badge_text,
    )
    return _bbox_list(badge)


def _draw_control(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: BBox,
    control: _ControlSpec,
    render_params: _RenderParams,
    theme: _WebTheme,
) -> List[float]:
    role = str(control.role)
    if role == "web_button":
        fill = theme.control_fill
        text_fill = theme.text
        outline = theme.control_outline
        _rounded_rect(draw, bbox, radius=int(render_params.control_corner_radius_px), fill=fill, outline=outline, width=int(render_params.control_outline_width_px))
        text_bbox = (bbox[0] + 36.0, bbox[1] + 5.0, bbox[2] - 10.0, bbox[3] - 5.0)
    elif role == "web_option":
        _rounded_rect(draw, bbox, radius=18, fill=theme.control_fill, outline=theme.control_outline, width=int(render_params.control_outline_width_px))
        dot = (bbox[0] + 38.0, bbox[1] + 14.0, bbox[0] + 50.0, bbox[1] + 26.0)
        draw.ellipse([float(value) for value in dot], fill=theme.panel_alt_fill, outline=theme.accent, width=2)
        text_fill = theme.text
        text_bbox = (bbox[0] + 58.0, bbox[1] + 6.0, bbox[2] - 10.0, bbox[3] - 6.0)
    else:
        _rounded_rect(draw, bbox, radius=int(render_params.control_corner_radius_px), fill=theme.control_fill, outline=theme.control_outline, width=int(render_params.control_outline_width_px))
        text_fill = theme.muted_text
        text_bbox = (bbox[0] + 38.0, bbox[1] + 7.0, bbox[2] - 12.0, bbox[3] - 7.0)
    _draw_text_left(
        draw,
        text=str(control.display_text),
        bbox=text_bbox,
        fill=text_fill,
        max_size_px=int(render_params.small_font_size_px),
        bold=(role != "web_input"),
    )
    return _draw_candidate_badge(draw, control_bbox=bbox, label=str(control.candidate_label), render_params=render_params, theme=theme)


def _render_click_scene(
    draw: ImageDraw.ImageDraw,
    *,
    query: _ResolvedQuery,
    content_bbox: BBox,
    profile: _WebProfile,
    render_params: _RenderParams,
    theme: _WebTheme,
    control_bboxes: Dict[str, List[float]],
    badge_bboxes: Dict[str, List[float]],
    support_bboxes: Dict[str, List[float]],
    support_records: List[Dict[str, Any]],
) -> None:
    x1, y1, x2, y2 = [float(value) for value in content_bbox]
    instruction = _draw_instruction(draw, content_bbox=content_bbox, query=query, render_params=render_params, theme=theme, support_bboxes=support_bboxes, support_records=support_records)
    guide = _draw_action_guide(draw, content_bbox=content_bbox, top_y=instruction[3] + 10.0, query=query, render_params=render_params, theme=theme, support_bboxes=support_bboxes, support_records=support_records)
    work_y1 = guide[3] + 16.0
    draw_text_traced(draw,(x1 + 2.0, work_y1), str(profile.page_title), fill=theme.text, font=load_font(int(render_params.title_font_size_px), bold=True), role="readout", required=False)
    grid_y1 = work_y1 + 42.0
    controls_by_row: Dict[int, List[_ControlSpec]] = {}
    for control in query.controls:
        controls_by_row.setdefault(int(control.row_index), []).append(control)
    row_count = len(controls_by_row)
    col_count = 2
    gap = 16.0
    card_w = (x2 - x1 - gap * (col_count - 1)) / float(col_count)
    card_h = (y2 - grid_y1 - gap * (max(1, (row_count + 1) // 2) - 1)) / float(max(1, (row_count + 1) // 2))
    for row_index, controls in sorted(controls_by_row.items()):
        grid_row = row_index // col_count
        grid_col = row_index % col_count
        card = (
            x1 + grid_col * (card_w + gap),
            grid_y1 + grid_row * (card_h + gap),
            x1 + grid_col * (card_w + gap) + card_w,
            grid_y1 + grid_row * (card_h + gap) + card_h,
        )
        _rounded_rect(draw, card, radius=12, fill=theme.panel_fill, outline=theme.browser_line, width=1)
        stripe = (card[0], card[1], card[2], card[1] + 7.0)
        draw.rectangle([float(value) for value in stripe], fill=theme.accent_alt if row_index % 2 else theme.accent)
        title_bbox = (card[0] + 18.0, card[1] + 14.0, card[2] - 18.0, card[1] + 38.0)
        _draw_text_left(draw, text=str(controls[0].context_display_label), bbox=title_bbox, fill=theme.text, max_size_px=int(render_params.body_font_size_px), bold=True)
        meta = f"Category: {controls[0].context_attribute_1}   Status: {controls[0].context_attribute_2}"
        _draw_text_left(draw, text=meta, bbox=(card[0] + 18.0, card[1] + 40.0, card[2] - 18.0, card[1] + 62.0), fill=theme.muted_text, max_size_px=int(render_params.small_font_size_px))
        _add_support(
            support_bboxes,
            support_records,
            str(controls[0].support_id),
            str(controls[0].support_kind),
            str(controls[0].context_display_label),
            card,
            attrs={
                "context_label": str(controls[0].context_label),
                "context_display_label": str(controls[0].context_display_label),
                "category": str(controls[0].context_attribute_1),
                "status": str(controls[0].context_attribute_2),
                "row_index": int(row_index),
            },
        )
        button_gap = 10.0
        button_h = 34.0
        button_w = (card[2] - card[0] - 36.0 - button_gap * (len(controls) - 1)) / float(len(controls))
        by_visual_slot = sorted(controls, key=lambda value: int(value.order_index))
        for col_index, control in enumerate(by_visual_slot):
            button = (
                card[0] + 18.0 + col_index * (button_w + button_gap),
                card[3] - 14.0 - button_h,
                card[0] + 18.0 + col_index * (button_w + button_gap) + button_w,
                card[3] - 14.0,
            )
            badge_bboxes[str(control.control_id)] = _draw_control(draw, bbox=button, control=control, render_params=render_params, theme=theme)
            control_bboxes[str(control.control_id)] = _bbox_list(button)


def _render_type_scene(
    draw: ImageDraw.ImageDraw,
    *,
    query: _ResolvedQuery,
    content_bbox: BBox,
    profile: _WebProfile,
    render_params: _RenderParams,
    theme: _WebTheme,
    control_bboxes: Dict[str, List[float]],
    badge_bboxes: Dict[str, List[float]],
    support_bboxes: Dict[str, List[float]],
    support_records: List[Dict[str, Any]],
) -> None:
    x1, y1, x2, y2 = [float(value) for value in content_bbox]
    instruction = _draw_instruction(draw, content_bbox=content_bbox, query=query, render_params=render_params, theme=theme, support_bboxes=support_bboxes, support_records=support_records)
    guide = _draw_action_guide(draw, content_bbox=content_bbox, top_y=instruction[3] + 10.0, query=query, render_params=render_params, theme=theme, support_bboxes=support_bboxes, support_records=support_records)
    work_y1 = guide[3] + 16.0
    draw_text_traced(draw,(x1 + 2.0, work_y1), str(profile.page_title), fill=theme.text, font=load_font(int(render_params.title_font_size_px), bold=True), role="readout", required=False)
    grid_y1 = work_y1 + 42.0
    controls_by_section: Dict[int, List[_ControlSpec]] = {}
    for control in query.controls:
        controls_by_section.setdefault(int(control.row_index), []).append(control)
    section_count = len(controls_by_section)
    panel_cols = 2
    gap = 16.0
    panel_w = (x2 - x1 - gap * (panel_cols - 1)) / float(panel_cols)
    panel_h = (y2 - grid_y1 - gap * (max(1, (section_count + 1) // 2) - 1)) / float(max(1, (section_count + 1) // 2))
    for section_index, controls in sorted(controls_by_section.items()):
        panel_row = section_index // panel_cols
        panel_col = section_index % panel_cols
        panel = (
            x1 + panel_col * (panel_w + gap),
            grid_y1 + panel_row * (panel_h + gap),
            x1 + panel_col * (panel_w + gap) + panel_w,
            grid_y1 + panel_row * (panel_h + gap) + panel_h,
        )
        _rounded_rect(draw, panel, radius=12, fill=theme.panel_fill, outline=theme.browser_line, width=1)
        _draw_text_left(draw, text=str(controls[0].context_label), bbox=(panel[0] + 16.0, panel[1] + 14.0, panel[2] - 16.0, panel[1] + 42.0), fill=theme.text, max_size_px=int(render_params.body_font_size_px), bold=True)
        _add_support(
            support_bboxes,
            support_records,
            str(controls[0].support_id),
            str(controls[0].support_kind),
            str(controls[0].context_label),
            panel,
            attrs={"context_label": str(controls[0].context_label), "row_index": int(section_index)},
        )
        sorted_controls = sorted(controls, key=lambda value: int(value.col_index))
        field_gap = 10.0
        field_h = min(58.0, (panel[3] - panel[1] - 58.0 - field_gap * (len(sorted_controls) - 1)) / float(len(sorted_controls)))
        for field_index, control in enumerate(sorted_controls):
            fy1 = panel[1] + 52.0 + field_index * (field_h + field_gap)
            label_bbox = (panel[0] + 18.0, fy1, panel[0] + 160.0, fy1 + field_h)
            input_bbox = (panel[0] + 172.0, fy1, panel[2] - 18.0, fy1 + field_h)
            _draw_text_left(draw, text=f"Key {control.action_code_label}", bbox=(label_bbox[0], label_bbox[1] + 6.0, label_bbox[2], label_bbox[3] - 6.0), fill=theme.text, max_size_px=int(render_params.small_font_size_px), bold=True)
            badge_bboxes[str(control.control_id)] = _draw_control(draw, bbox=input_bbox, control=control, render_params=render_params, theme=theme)
            control_bboxes[str(control.control_id)] = _bbox_list((label_bbox[0], label_bbox[1], input_bbox[2], input_bbox[3]))


def _render_select_scene(
    draw: ImageDraw.ImageDraw,
    *,
    query: _ResolvedQuery,
    content_bbox: BBox,
    profile: _WebProfile,
    render_params: _RenderParams,
    theme: _WebTheme,
    control_bboxes: Dict[str, List[float]],
    badge_bboxes: Dict[str, List[float]],
    support_bboxes: Dict[str, List[float]],
    support_records: List[Dict[str, Any]],
) -> None:
    x1, y1, x2, y2 = [float(value) for value in content_bbox]
    instruction = _draw_instruction(draw, content_bbox=content_bbox, query=query, render_params=render_params, theme=theme, support_bboxes=support_bboxes, support_records=support_records)
    guide = _draw_action_guide(draw, content_bbox=content_bbox, top_y=instruction[3] + 10.0, query=query, render_params=render_params, theme=theme, support_bboxes=support_bboxes, support_records=support_records)
    work_y1 = guide[3] + 16.0
    draw_text_traced(draw,(x1 + 2.0, work_y1), str(profile.page_title), fill=theme.text, font=load_font(int(render_params.title_font_size_px), bold=True), role="readout", required=False)
    grid_y1 = work_y1 + 42.0
    controls_by_group: Dict[int, List[_ControlSpec]] = {}
    for control in query.controls:
        controls_by_group.setdefault(int(control.row_index), []).append(control)
    group_count = len(controls_by_group)
    gap = 14.0
    group_h = (y2 - grid_y1 - gap * (group_count - 1)) / float(max(1, group_count))
    for group_index, controls in sorted(controls_by_group.items()):
        group = (x1, grid_y1 + group_index * (group_h + gap), x2, grid_y1 + group_index * (group_h + gap) + group_h)
        _rounded_rect(draw, group, radius=12, fill=theme.panel_fill, outline=theme.browser_line, width=1)
        title_bbox = (group[0] + 18.0, group[1] + 14.0, group[0] + 240.0, group[3] - 14.0)
        _draw_text_left(draw, text=str(controls[0].context_label), bbox=(title_bbox[0], title_bbox[1], title_bbox[2], title_bbox[1] + 28.0), fill=theme.text, max_size_px=int(render_params.body_font_size_px), bold=True)
        _draw_text_left(draw, text="Choose one", bbox=(title_bbox[0], title_bbox[1] + 31.0, title_bbox[2], title_bbox[3]), fill=theme.muted_text, max_size_px=int(render_params.small_font_size_px))
        _add_support(
            support_bboxes,
            support_records,
            str(controls[0].support_id),
            str(controls[0].support_kind),
            str(controls[0].context_label),
            title_bbox,
            attrs={"context_label": str(controls[0].context_label), "row_index": int(group_index)},
        )
        sorted_controls = sorted(controls, key=lambda value: int(value.col_index))
        option_gap = 12.0
        option_w = (group[2] - group[0] - 280.0 - option_gap * (len(sorted_controls) - 1)) / float(len(sorted_controls))
        option_h = min(46.0, group_h - 28.0)
        for option_index, control in enumerate(sorted_controls):
            option = (
                group[0] + 260.0 + option_index * (option_w + option_gap),
                group[1] + (group_h - option_h) / 2.0,
                group[0] + 260.0 + option_index * (option_w + option_gap) + option_w,
                group[1] + (group_h + option_h) / 2.0,
            )
            badge_bboxes[str(control.control_id)] = _draw_control(draw, bbox=option, control=control, render_params=render_params, theme=theme)
            control_bboxes[str(control.control_id)] = _bbox_list(option)


def _render_web_scene(
    image: Image.Image,
    *,
    query: _ResolvedQuery,
    render_params: _RenderParams,
) -> _RenderedScene:
    draw = ImageDraw.Draw(image)
    theme = _theme(str(query.style_variant))
    content_bbox, profile, browser_bbox = _draw_browser_frame(draw, query=query, render_params=render_params, theme=theme)
    control_bboxes: Dict[str, List[float]] = {}
    badge_bboxes: Dict[str, List[float]] = {}
    support_bboxes: Dict[str, List[float]] = {}
    support_records: List[Dict[str, Any]] = []
    if str(query.query_id) == "type_field_label":
        _render_type_scene(
            draw,
            query=query,
            content_bbox=content_bbox,
            profile=profile,
            render_params=render_params,
            theme=theme,
            control_bboxes=control_bboxes,
            badge_bboxes=badge_bboxes,
            support_bboxes=support_bboxes,
            support_records=support_records,
        )
    elif str(query.query_id) == "select_option_label":
        _render_select_scene(
            draw,
            query=query,
            content_bbox=content_bbox,
            profile=profile,
            render_params=render_params,
            theme=theme,
            control_bboxes=control_bboxes,
            badge_bboxes=badge_bboxes,
            support_bboxes=support_bboxes,
            support_records=support_records,
        )
    else:
        _render_click_scene(
            draw,
            query=query,
            content_bbox=content_bbox,
            profile=profile,
            render_params=render_params,
            theme=theme,
            control_bboxes=control_bboxes,
            badge_bboxes=badge_bboxes,
            support_bboxes=support_bboxes,
            support_records=support_records,
        )

    control_records: List[Dict[str, Any]] = []
    for control in query.controls:
        control_records.append(
            {
                "control_id": str(control.control_id),
                "candidate_label": str(control.candidate_label),
                "role": str(control.role),
                "display_text": str(control.display_text),
                "context_label": str(control.context_label),
                "context_display_label": str(control.context_display_label),
                "context_attribute_1": str(control.context_attribute_1),
                "context_attribute_2": str(control.context_attribute_2),
                "action_label": str(control.action_label),
                "action_cue_label": str(control.action_cue_label),
                "action_code_label": str(control.action_code_label),
                "support_id": str(control.support_id),
                "support_kind": str(control.support_kind),
                "row_index": int(control.row_index),
                "col_index": int(control.col_index),
                "order_index": int(control.order_index),
                "bbox_px": list(control_bboxes[str(control.control_id)]),
                "candidate_label_bbox_px": list(badge_bboxes[str(control.control_id)]),
            }
        )
    return _RenderedScene(
        control_bboxes_by_id={str(key): list(value) for key, value in control_bboxes.items()},
        badge_bboxes_by_id={str(key): list(value) for key, value in badge_bboxes.items()},
        support_bboxes_by_id={str(key): list(value) for key, value in support_bboxes.items()},
        control_records=tuple(control_records),
        support_records=tuple(dict(record) for record in support_records),
        scene_bbox_px=[0.0, 0.0, float(render_params.canvas_width), float(render_params.canvas_height)],
        browser_bbox_px=_bbox_list(browser_bbox),
        profile=profile,
        theme=theme,
    )


def _annotation_roles_for_query(query_id: str) -> Tuple[str, str, str, str]:
    """Return prompt-facing annotation role names for one web-action query."""

    if str(query_id) == "click_target_label":
        return ("instruction_banner", "action_key_guide", "item_card", "target_button")
    if str(query_id) == "type_field_label":
        return ("instruction_banner", "field_key_guide", "form_section", "target_input")
    return ("instruction_banner", "option_key_guide", "option_group", "target_option")


def _prompt_json_examples(*, query_id: str) -> Tuple[str, str]:
    instruction_role, guide_role, context_role, target_role = _annotation_roles_for_query(str(query_id))
    answer_and_annotation = {
        "annotation": {
            str(instruction_role): [80, 150, 1200, 210],
            str(guide_role): [210, 222, 430, 278],
            str(context_role): [92, 310, 590, 430],
            str(target_role): [410, 378, 560, 418],
        },
        "answer": "G",
    }
    answer_only = {"answer": "G"}
    return (
        json.dumps(answer_and_annotation, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
    )


def _web_profile_dict(profile: _WebProfile) -> Dict[str, Any]:
    return {
        "site_name": str(profile.site_name),
        "url_path": str(profile.url_path),
        "page_title": str(profile.page_title),
        "nav_items": [str(value) for value in profile.nav_items],
        "status_text": str(profile.status_text),
    }




class PagesRelationWebActionTargetLabelTask:
    """Identify the labeled web control matching a visible action instruction."""

    task_id = TASK_ID
    domain = "pages"
    scene_id = "relation"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query = _resolve_query(int(instance_seed), params=params)
        render_params = _resolve_render_params(params, instance_seed=int(instance_seed))
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        image = background.copy().convert("RGB")
        rendered = _render_web_scene(image, query=query, render_params=render_params)
        image, post_noise_meta = apply_post_image_noise(
            image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        target_bbox = list(rendered.control_bboxes_by_id[str(query.target_control_id)])
        annotation_support_ids = (
            str(query.instruction_support_id),
            str(query.guide_support_id),
            str(query.context_support_id),
        )
        instruction_role, guide_role, context_role, target_role = _annotation_roles_for_query(str(query.query_id))
        annotation_bbox_map: Dict[str, List[float]] = {
            str(instruction_role): list(rendered.support_bboxes_by_id[str(query.instruction_support_id)]),
            str(guide_role): list(rendered.support_bboxes_by_id[str(query.guide_support_id)]),
            str(context_role): list(rendered.support_bboxes_by_id[str(query.context_support_id)]),
            str(target_role): list(target_bbox),
        }
        annotation_role_support_ids: Dict[str, str] = {
            str(instruction_role): str(query.instruction_support_id),
            str(guide_role): str(query.guide_support_id),
            str(context_role): str(query.context_support_id),
            str(target_role): str(query.target_control_id),
        }
        answer_gt = TypedValue(type="option_letter", value=str(query.target_label))
        annotation_gt = TypedValue(type="keyed_bbox_map", value=dict(annotation_bbox_map))

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "object_description",
                "json_output_contract",
                "json_output_contract_answer_only",
                f"annotation_hint_{str(query.query_id)}",
                "answer_hint",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _prompt_json_examples(query_id=str(query.query_id))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            scene_id=self.scene_id,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "instruction_text": str(query.instruction_text),
                "context_label": str(query.context_label),
                "action_label": str(query.action_label),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(query.query_id)}"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        control_records = [dict(record) for record in rendered.control_records]
        support_records = [dict(record) for record in rendered.support_records]
        target_record = next(record for record in control_records if str(record["control_id"]) == str(query.target_control_id))
        annotation_support_records = [
            next(record for record in support_records if str(record["support_id"]) == str(support_id))
            for support_id in annotation_support_ids
        ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": "gui_web_action_target",
                "entities": [
                    {
                        "entity_id": str(record["control_id"]),
                        "entity_type": "web_control",
                        "attrs": {
                            "candidate_label": str(record["candidate_label"]),
                            "role": str(record["role"]),
                            "display_text": str(record["display_text"]),
                            "context_label": str(record["context_label"]),
                            "context_display_label": str(record["context_display_label"]),
                            "context_attribute_1": str(record["context_attribute_1"]),
                            "context_attribute_2": str(record["context_attribute_2"]),
                            "action_label": str(record["action_label"]),
                            "action_cue_label": str(record["action_cue_label"]),
                            "action_code_label": str(record["action_code_label"]),
                            "bbox_px": list(record["bbox_px"]),
                        },
                    }
                    for record in control_records
                ],
                "relations": {
                    "query_id": str(query.query_id),
                    "scene_variant": str(query.scene_variant),
                    "style_variant": str(query.style_variant),
                    "target_control_id": str(query.target_control_id),
                    "target_label": str(query.target_label),
                    "context_label": str(query.context_label),
                    "context_display_label": str(target_record["context_display_label"]),
                    "context_attribute_1": str(target_record["context_attribute_1"]),
                    "context_attribute_2": str(target_record["context_attribute_2"]),
                    "action_label": str(query.action_label),
                    "instruction_cue_label": str(query.instruction_cue_label),
                    "instruction_code_label": str(query.instruction_code_label),
                    "instruction_text": str(query.instruction_text),
                    "instruction_template_index": int(query.instruction_template_index),
                    "instruction_support_id": str(query.instruction_support_id),
                    "guide_support_id": str(query.guide_support_id),
                    "guide_entries": [asdict(entry) for entry in query.guide_entries],
                    "context_support_id": str(query.context_support_id),
                    "context_support_kind": str(query.context_support_kind),
                    "annotation_support_ids": [str(value) for value in annotation_support_ids],
                    "annotation_role_support_ids": dict(annotation_role_support_ids),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                },
            },
            "query_spec": {
                "query_id": str(query.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query.query_id),
                    "scene_variant": str(query.scene_variant),
                    "style_variant": str(query.style_variant),
                    "target_control_id": str(query.target_control_id),
                    "target_label": str(query.target_label),
                    "context_label": str(query.context_label),
                    "context_display_label": str(target_record["context_display_label"]),
                    "context_attribute_1": str(target_record["context_attribute_1"]),
                    "context_attribute_2": str(target_record["context_attribute_2"]),
                    "action_label": str(query.action_label),
                    "instruction_cue_label": str(query.instruction_cue_label),
                    "instruction_code_label": str(query.instruction_code_label),
                    "instruction_text": str(query.instruction_text),
                    "instruction_template_index": int(query.instruction_template_index),
                    "instruction_support_id": str(query.instruction_support_id),
                    "guide_support_id": str(query.guide_support_id),
                    "guide_entries": [asdict(entry) for entry in query.guide_entries],
                    "context_support_id": str(query.context_support_id),
                    "context_support_kind": str(query.context_support_kind),
                    "candidate_label_pool": [str(value) for value in query.candidate_label_pool],
                    "annotation_role_support_ids": dict(annotation_role_support_ids),
                    "query_id_probabilities": dict(query.query_id_probabilities),
                    "scene_variant_probabilities": dict(query.scene_variant_probabilities),
                    "style_variant_probabilities": dict(query.style_variant_probabilities),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_variant": str(query.scene_variant),
                "style_variant": str(query.style_variant),
                "browser_bbox_px": list(rendered.browser_bbox_px),
                "scene_bbox_px": list(rendered.scene_bbox_px),
                "render_params": asdict(render_params),
                "theme": {
                    "name": str(rendered.theme.name),
                    "accent_rgb": [int(value) for value in rendered.theme.accent],
                    "accent_alt_rgb": [int(value) for value in rendered.theme.accent_alt],
                    "badge_fill_rgb": [int(value) for value in rendered.theme.badge_fill],
                },
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered.scene_bbox_px),
                "browser_bbox_px": list(rendered.browser_bbox_px),
                "web_profile": _web_profile_dict(rendered.profile),
                "control_bboxes_by_id": dict(rendered.control_bboxes_by_id),
                "candidate_label_badge_bboxes_by_id": dict(rendered.badge_bboxes_by_id),
                "support_bboxes_by_id": dict(rendered.support_bboxes_by_id),
                "target_control_id": str(query.target_control_id),
                "guide_entries": [asdict(entry) for entry in query.guide_entries],
                "annotation_support_ids": [str(value) for value in annotation_support_ids],
                "annotation_role_support_ids": dict(annotation_role_support_ids),
            },
            "execution_trace": {
                "query_id": str(query.query_id),
                "scene_variant": str(query.scene_variant),
                "style_variant": str(query.style_variant),
                "target_control_id": str(query.target_control_id),
                "target_label": str(query.target_label),
                "context_label": str(query.context_label),
                "context_display_label": str(target_record["context_display_label"]),
                "context_attribute_1": str(target_record["context_attribute_1"]),
                "context_attribute_2": str(target_record["context_attribute_2"]),
                "action_label": str(query.action_label),
                "instruction_cue_label": str(query.instruction_cue_label),
                "instruction_code_label": str(query.instruction_code_label),
                "instruction_text": str(query.instruction_text),
                "instruction_template_index": int(query.instruction_template_index),
                "instruction_support_id": str(query.instruction_support_id),
                "guide_support_id": str(query.guide_support_id),
                "guide_entries": [asdict(entry) for entry in query.guide_entries],
                "context_support_id": str(query.context_support_id),
                "context_support_kind": str(query.context_support_kind),
                "annotation_support_ids": [str(value) for value in annotation_support_ids],
                "annotation_role_support_ids": dict(annotation_role_support_ids),
                "annotation_support_records": [dict(record) for record in annotation_support_records],
                "target_control": dict(target_record),
                "controls": list(control_records),
                "support_records": list(support_records),
                "total_control_count": int(len(query.controls)),
                "query_id_probabilities": dict(query.query_id_probabilities),
                "scene_variant_probabilities": dict(query.scene_variant_probabilities),
                "style_variant_probabilities": dict(query.style_variant_probabilities),
                "question_format": "gui_web_action_target_label",
            },
            "witness_symbolic": {
                "type": "keyed_bbox_map",
                "annotation_support_ids": [str(value) for value in annotation_support_ids],
                "annotation_role_support_ids": dict(annotation_role_support_ids),
                "target_control_id": str(query.target_control_id),
                "value": dict(annotation_bbox_map),
            },
            "projected_annotation": {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(annotation_bbox_map),
                "pixel_keyed_bbox_map": dict(annotation_bbox_map),
            },
        }

        output = TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
        return rewrite_pages_query_output(
            output,
            query_id=str(query.query_id),
            scene_id="web_action",
            query_probabilities=query.query_id_probabilities,
        )


@register_task
class PagesWebActionClickTargetLabelTask(FixedPagesQueryTaskMixin):
    """Identify the clickable target described by a web-page action cue."""

    task_id = "task_pages__web_action__click_target_label"
    domain = "pages"
    scene_id = "relation"
    public_scene_id = "web_action"
    fixed_query_id = "click_target_label"
    source_task_cls = PagesRelationWebActionTargetLabelTask


@register_task
class PagesWebActionTypeFieldLabelTask(FixedPagesQueryTaskMixin):
    """Identify the input field described by a web-page action cue."""

    task_id = "task_pages__web_action__type_field_label"
    domain = "pages"
    scene_id = "relation"
    public_scene_id = "web_action"
    fixed_query_id = "type_field_label"
    source_task_cls = PagesRelationWebActionTargetLabelTask


@register_task
class PagesWebActionSelectOptionLabelTask(FixedPagesQueryTaskMixin):
    """Identify the selectable option described by a web-page action cue."""

    task_id = "task_pages__web_action__select_option_label"
    domain = "pages"
    scene_id = "relation"
    public_scene_id = "web_action"
    fixed_query_id = "select_option_label"
    source_task_cls = PagesRelationWebActionTargetLabelTask


__all__ = [
    "PagesRelationWebActionTargetLabelTask",
    "PagesWebActionClickTargetLabelTask",
    "PagesWebActionSelectOptionLabelTask",
    "PagesWebActionTypeFieldLabelTask",
    "SUPPORTED_QUERY_IDS",
]
