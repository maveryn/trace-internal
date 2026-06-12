"""Calendar event-grid page tasks with date-slot lookup and category counts."""

from __future__ import annotations

import calendar
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from .....core.scene_config import get_scene_defaults
from .....core.seed import hash64, spawn_rng
from .....core.types import TypedValue
from .....core.visual.background import make_background_canvas
from .....core.visual.noise import apply_post_image_noise
from ....base import TaskOutput
from ....shared.config_defaults import group_default, required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ....shared.deterministic_sampling import resolve_selection_index
from ....shared.output_metadata import default_task_versions
from ....shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ....shared.time_artifact_style import (
    SUPPORTED_TIME_ARTIFACT_CALENDAR_TEXT_COLOR_MODES,
    SUPPORTED_TIME_ARTIFACT_COLOR_NAMES,
    SUPPORTED_TIME_ARTIFACT_STYLE_VARIANTS,
    build_time_artifact_calendar_theme,
)
from ....shared.time_artifact_task_support import resolve_time_artifact_named_variant
from ....shared.time_format import month_name
from ...shared.calendar_scene import (
    CalendarEventChipSpec,
    CalendarRenderParams,
    SUPPORTED_PAGE_CALENDAR_SCENE_VARIANTS,
    render_month_calendar_event_grid_scene,
    resolve_calendar_render_params,
)
from ...shared.visual_defaults import load_pages_scene_background_defaults, load_pages_scene_noise_defaults


TASK_ID = "pages_calendar_event_grid_base"
DATE_SLOT_CATEGORY_TASK_ID = "task_pages__calendar_event_grid__date_slot_category_label"
CATEGORY_SLOT_DAY_COUNT_TASK_ID = "task_pages__calendar_event_grid__category_slot_day_count"
DATE_FOR_CATEGORY_SLOT_TASK_ID = "task_pages__calendar_event_grid__date_for_category_slot_label"
PUBLIC_SCENE_ID = "calendar_event_grid"

DATE_SLOT_CATEGORY_QUERY_ID = "date_slot_category_label"
CATEGORY_SLOT_DAY_COUNT_QUERY_ID = "category_slot_day_count"
DATE_FOR_CATEGORY_SLOT_QUERY_ID = "date_for_category_slot_label"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    DATE_SLOT_CATEGORY_QUERY_ID,
    CATEGORY_SLOT_DAY_COUNT_QUERY_ID,
    DATE_FOR_CATEGORY_SLOT_QUERY_ID,
)
SUPPORTED_EVENT_GRID_LAYOUT_MODES: Tuple[str, ...] = (
    "center_clean",
    "free_jitter_clean",
    "left_with_side_note",
    "right_with_side_note",
    "top_with_bottom_note",
)
SUPPORTED_EVENT_GRID_TITLE_MODES: Tuple[str, ...] = (
    "generic",
    "full_month_year",
)
SUPPORTED_EVENT_GRID_SURFACE_MODES: Tuple[str, ...] = ("light", "dark")
SUPPORTED_EVENT_GRID_TEXT_COLOR_MODES: Tuple[str, ...] = SUPPORTED_TIME_ARTIFACT_CALENDAR_TEXT_COLOR_MODES

EVENT_SLOT_SPECS: Tuple[Tuple[str, str], ...] = (
    ("top", "Top"),
    ("mid", "Mid"),
    ("end", "End"),
)
EVENT_CATEGORY_LABELS: Tuple[str, ...] = (
    "Arts",
    "Civic",
    "Culture",
    "Finance",
    "Health",
    "Policy",
    "Science",
    "Sports",
    "Tech",
    "Travel",
)
_CHIP_FILL_PALETTE: Tuple[Tuple[int, int, int], ...] = (
    (226, 240, 255),
    (222, 245, 233),
    (255, 237, 213),
    (245, 226, 255),
    (255, 228, 232),
    (224, 246, 250),
    (245, 239, 211),
    (230, 234, 255),
)


@dataclass(frozen=True)
class _EventGridDefaults:
    """Stable fallback defaults for event-grid calendar scenes."""

    year_min: int = 2022
    year_max: int = 2030
    target_count_support: Tuple[int, ...] = (2, 3, 4, 5, 6)
    min_random_extra_chips: int = 10
    max_random_extra_chips: int = 18
    canvas_width: int = 980
    canvas_height: int = 780
    outer_margin_px: int = 34
    title_height_px: int = 62
    title_bottom_gap_px: int = 12
    weekday_header_height_px: int = 32
    weekday_grid_gap_px: int = 8
    cell_gap_px: int = 7
    panel_corner_radius_px: int = 16
    panel_outline_width_px: int = 3
    cell_corner_radius_px: int = 10
    cell_outline_width_px: int = 2
    title_font_size_px: int = 30
    weekday_font_size_px: int = 15
    date_font_size_px: int = 20
    marker_inset_px: int = 8
    marker_outline_width_px: int = 2


@dataclass(frozen=True)
class _ResolvedEventGridQuery:
    """Resolved semantic and visual support for one event-grid query."""

    query_id: str
    scene_variant: str
    style_variant: str
    accent_color_name: str
    layout_mode: str
    title_mode: str
    surface_mode: str
    text_color_mode: str
    year: int
    month: int
    month_name: str
    days_in_month: int
    row_count: int
    slot_id: str
    slot_label: str
    category_label: str
    target_date: int | None
    target_count: int | None
    event_chips: Tuple[CalendarEventChipSpec, ...]
    matching_chip_keys: Tuple[str, ...]
    query_id_probabilities: Dict[str, float]
    category_probabilities: Dict[str, float]
    slot_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]
    layout_mode_probabilities: Dict[str, float]
    title_mode_probabilities: Dict[str, float]
    surface_mode_probabilities: Dict[str, float]
    text_color_mode_probabilities: Dict[str, float]


_DEFAULTS = _EventGridDefaults()
_SCENE_DEFAULTS = get_scene_defaults("pages", PUBLIC_SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=DATE_SLOT_CATEGORY_TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_pages_scene_background_defaults(scene_id=PUBLIC_SCENE_ID)
POST_IMAGE_NOISE_DEFAULTS = load_pages_scene_noise_defaults(scene_id=PUBLIC_SCENE_ID, apply_prob=0.0)


def _chip_key(day: int, slot_id: str) -> str:
    return f"date_{int(day)}__slot_{str(slot_id)}"


def _slot_label(slot_id: str) -> str:
    labels = {str(slot): str(label) for slot, label in EVENT_SLOT_SPECS}
    if str(slot_id) not in labels:
        raise ValueError(f"unsupported event slot id: {slot_id}")
    return labels[str(slot_id)]


def _uniform_probability(values: Sequence[str | int]) -> Dict[str, float]:
    resolved = tuple(str(value) for value in values)
    if not resolved:
        return {}
    probability = 1.0 / float(len(resolved))
    return {str(value): float(probability) for value in resolved}


def _resolve_named_variant(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Tuple[str, ...],
    namespace: str,
) -> Tuple[str, Dict[str, float]]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{namespace}")
    return resolve_time_artifact_named_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported=tuple(str(value) for value in supported),
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace=str(namespace),
    )


def _resolve_int_support(params: Mapping[str, Any], default_key: str, fallback: Sequence[int]) -> Tuple[int, ...]:
    raw = params.get(str(default_key), group_default(_GEN_DEFAULTS, str(default_key), tuple(int(value) for value in fallback)))
    values = tuple(int(value) for value in raw)
    if not values:
        raise ValueError(f"{default_key} must contain at least one value")
    return tuple(values)


def _resolve_category_labels(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("event_category_labels", group_default(_GEN_DEFAULTS, "event_category_labels", EVENT_CATEGORY_LABELS))
    labels: List[str] = []
    for value in raw:
        label = str(value).strip()
        if label and label not in labels:
            labels.append(label)
    if len(labels) < 4:
        raise ValueError("event_category_labels must contain at least four distinct visible labels")
    return tuple(labels)


def _resolve_query_id(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    explicit = params.get("query_id", params.get("query_variant"))
    supported = set(SUPPORTED_QUERY_IDS)
    if explicit is not None and str(explicit) != "default":
        if str(explicit) not in supported:
            raise ValueError(f"unsupported calendar event-grid query_id: {explicit}")
        return str(explicit), {str(explicit): 1.0}
    return _resolve_named_variant(
        instance_seed=int(instance_seed),
        params=params,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        supported=SUPPORTED_QUERY_IDS,
        namespace="query_id",
    )


def _resolve_choice(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    explicit_key: str,
    values: Sequence[str],
    namespace: str,
) -> Tuple[str, Dict[str, float]]:
    explicit = params.get(str(explicit_key))
    value_set = {str(value) for value in values}
    if explicit is not None:
        if str(explicit) not in value_set:
            raise ValueError(f"unsupported {explicit_key}: {explicit}")
        return str(explicit), {str(explicit): 1.0}
    probabilities = _uniform_probability(tuple(str(value) for value in values))
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.{namespace}",
    )
    return str(tuple(values)[int(index) % len(values)]), dict(probabilities)


def _resolve_target_count(instance_seed: int, params: Mapping[str, Any]) -> Tuple[int, Dict[str, float]]:
    support = _resolve_int_support(params, "target_count_support", _DEFAULTS.target_count_support)
    explicit = params.get("target_count")
    if explicit is not None:
        value = int(explicit)
        if value not in set(support):
            raise ValueError(f"target_count must be in {list(support)}")
        return int(value), {str(value): 1.0}
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.target_count",
    )
    return int(support[int(index) % len(support)]), _uniform_probability(support)


def _resolve_year_month(instance_seed: int, params: Mapping[str, Any]) -> Tuple[int, int, int, int]:
    explicit_year = params.get("year")
    explicit_month = params.get("month")
    if (explicit_year is None) != (explicit_month is None):
        raise ValueError("year and month must be provided together for calendar event-grid tasks")
    if explicit_year is not None and explicit_month is not None:
        year = int(explicit_year)
        month = int(explicit_month)
    else:
        year_min = int(params.get("year_min", _GEN_DEFAULTS.get("year_min", _DEFAULTS.year_min)))
        year_max = int(params.get("year_max", _GEN_DEFAULTS.get("year_max", _DEFAULTS.year_max)))
        if year_min > year_max:
            raise ValueError("year_min must be <= year_max")
        year_span = int(year_max - year_min + 1)
        year_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.year",
        )
        month_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.month",
        )
        year = int(year_min + (int(year_index) % int(year_span)))
        month = int(1 + (int(month_index) % 12))
    start_weekday_index, days_in_month = calendar.monthrange(int(year), int(month))
    row_count = len(calendar.Calendar(firstweekday=0).monthdayscalendar(int(year), int(month)))
    return int(year), int(month), int(days_in_month), int(row_count)


def _resolve_calendar_panel_bbox(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    render_params: CalendarRenderParams,
    layout_mode: str,
) -> Tuple[Tuple[float, float, float, float], Dict[str, Any]]:
    explicit_panel_bbox = params.get("calendar_event_grid_panel_bbox_px", params.get("calendar_panel_bbox_px"))
    if explicit_panel_bbox is not None:
        if not isinstance(explicit_panel_bbox, Sequence) or isinstance(explicit_panel_bbox, (str, bytes)) or len(explicit_panel_bbox) < 4:
            raise ValueError("calendar_event_grid_panel_bbox_px must be a four-coordinate sequence")
        bbox = tuple(float(value) for value in explicit_panel_bbox[:4])
        return bbox, {
            "layout_placement": {
                "mode": "explicit_bbox",
                "enabled": False,
                "panel_size_px": [round(float(bbox[2] - bbox[0]), 3), round(float(bbox[3] - bbox[1]), 3)],
                "final_origin_px": [round(float(bbox[0]), 3), round(float(bbox[1]), 3)],
            }
        }

    canvas_w = float(render_params.canvas_width)
    canvas_h = float(render_params.canvas_height)
    margin = float(render_params.outer_margin_px)
    panel_w = canvas_w - (2.0 * margin)
    panel_h = canvas_h - (2.0 * margin)
    if str(layout_mode) == "left_with_side_note":
        panel_w = min(panel_w, canvas_w * 0.78)
        x0 = margin
        y0 = margin
    elif str(layout_mode) == "right_with_side_note":
        panel_w = min(panel_w, canvas_w * 0.78)
        x0 = canvas_w - margin - panel_w
        y0 = margin
    elif str(layout_mode) == "top_with_bottom_note":
        panel_h = min(panel_h, canvas_h * 0.82)
        x0 = margin
        y0 = margin
    elif str(layout_mode) == "free_jitter_clean":
        rng = spawn_rng(int(instance_seed), f"{TASK_ID}.calendar_event_grid_panel_bbox")
        jitter_x = float(rng.randint(-14, 14))
        jitter_y = float(rng.randint(-12, 12))
        x0 = margin + jitter_x
        y0 = margin + jitter_y
    elif str(layout_mode) == "center_clean":
        x0 = margin
        y0 = margin
    else:
        raise ValueError(f"unsupported calendar event-grid layout_mode: {layout_mode}")
    x0 = max(8.0, min(canvas_w - panel_w - 8.0, float(x0)))
    y0 = max(8.0, min(canvas_h - panel_h - 8.0, float(y0)))
    bbox = (float(x0), float(y0), float(x0 + panel_w), float(y0 + panel_h))
    free_x = max(0.0, float(canvas_w - panel_w))
    free_y = max(0.0, float(canvas_h - panel_h))
    default_x0 = float(free_x * 0.5)
    default_y0 = float(free_y * 0.5)
    return bbox, {
        "layout_placement": {
            "mode": "fractional_free_area",
            "enabled": True,
            "layout_mode": str(layout_mode),
            "panel_size_px": [round(float(panel_w), 3), round(float(panel_h), 3)],
            "content_size_px": [round(float(panel_w), 3), round(float(panel_h), 3)],
            "free_space_px": [round(float(free_x), 3), round(float(free_y), 3)],
            "sampled_fractions": {
                "x": round(float(x0 / free_x), 6) if float(free_x) > 0.0 else 0.0,
                "y": round(float(y0 / free_y), 6) if float(free_y) > 0.0 else 0.0,
            },
            "final_origin_px": [round(float(x0), 3), round(float(y0), 3)],
            "dx_dy_from_centered_px": [
                round(float(x0 - default_x0), 3),
                round(float(y0 - default_y0), 3),
            ],
        }
    }


def _resolve_title_text(
    *,
    instance_seed: int,
    title_mode: str,
    month: int,
    year: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, Any]]:
    explicit = params.get("calendar_event_grid_title_text")
    if explicit is not None:
        text = str(explicit).strip()
        if not text:
            raise ValueError("calendar_event_grid_title_text must not be empty")
        return text, {"mode": "explicit"}
    if str(title_mode) == "full_month_year":
        return f"{month_name(int(month))} {int(year)}", {"mode": "full_month_year"}
    if str(title_mode) != "generic":
        raise ValueError(f"unsupported calendar event-grid title_mode: {title_mode}")
    options = ("Event Calendar", "News Grid", "Daily Highlights", "Month Board")
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.title_text",
    )
    return str(options[int(index) % len(options)]), {"mode": "generic"}


def _chip_fill(category_label: str, *, instance_seed: int) -> Tuple[int, int, int]:
    index = abs(int(hash64(int(instance_seed), str(category_label), 50921)))
    return tuple(int(value) for value in _CHIP_FILL_PALETTE[int(index) % len(_CHIP_FILL_PALETTE)])


def _make_chip(
    *,
    day: int,
    slot_id: str,
    category_label: str,
    instance_seed: int,
) -> CalendarEventChipSpec:
    return CalendarEventChipSpec(
        day=int(day),
        slot_id=str(slot_id),
        slot_label=str(_slot_label(str(slot_id))),
        category_label=str(category_label),
        fill_rgb=_chip_fill(str(category_label), instance_seed=int(instance_seed)),
        text_rgb=(20, 34, 48),
    )


def _build_event_chips(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
    days_in_month: int,
    slot_id: str,
    category_label: str,
    category_labels: Sequence[str],
    target_count: int,
) -> Tuple[Tuple[CalendarEventChipSpec, ...], int | None, Tuple[str, ...]]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.event_chips")
    slots = tuple(str(slot) for slot, _ in EVENT_SLOT_SPECS)
    categories = tuple(str(value) for value in category_labels)
    chip_by_day_slot: Dict[Tuple[int, str], str] = {}
    matching_keys: List[str] = []
    target_date: int | None = None

    if str(query_id) in {DATE_SLOT_CATEGORY_QUERY_ID, DATE_FOR_CATEGORY_SLOT_QUERY_ID}:
        target_date = int(params.get("target_date", 1 + (resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}.target_date") % int(days_in_month))))
        if int(target_date) < 1 or int(target_date) > int(days_in_month):
            raise ValueError("target_date must be within the sampled month")
        chip_by_day_slot[(int(target_date), str(slot_id))] = str(category_label)
        matching_keys.append(_chip_key(int(target_date), str(slot_id)))
    else:
        day_pool = list(range(1, int(days_in_month) + 1))
        rng.shuffle(day_pool)
        selected_days = sorted(day_pool[: int(target_count)])
        for day in selected_days:
            chip_by_day_slot[(int(day), str(slot_id))] = str(category_label)
            matching_keys.append(_chip_key(int(day), str(slot_id)))

    same_category_other_slot_count = min(4, max(2, int(days_in_month) // 9))
    same_slot_other_category_count = min(6, max(3, int(days_in_month) // 6))
    random_extra_min = int(_GEN_DEFAULTS.get("min_random_extra_chips", _DEFAULTS.min_random_extra_chips))
    random_extra_max = int(_GEN_DEFAULTS.get("max_random_extra_chips", _DEFAULTS.max_random_extra_chips))
    if random_extra_min > random_extra_max:
        raise ValueError("min_random_extra_chips must be <= max_random_extra_chips")
    random_extra_count = int(rng.randint(int(random_extra_min), int(random_extra_max)))

    other_slots = [slot for slot in slots if str(slot) != str(slot_id)]
    other_categories = [label for label in categories if str(label) != str(category_label)]
    for _ in range(same_category_other_slot_count):
        day = int(rng.randint(1, int(days_in_month)))
        slot = str(rng.choice(other_slots))
        chip_by_day_slot.setdefault((day, slot), str(category_label))
    for _ in range(same_slot_other_category_count):
        day = int(rng.randint(1, int(days_in_month)))
        category = str(rng.choice(other_categories))
        chip_by_day_slot.setdefault((day, str(slot_id)), str(category))
    for _ in range(random_extra_count):
        day = int(rng.randint(1, int(days_in_month)))
        slot = str(rng.choice(slots))
        category = str(rng.choice(categories))
        if (
            str(query_id) in {CATEGORY_SLOT_DAY_COUNT_QUERY_ID, DATE_FOR_CATEGORY_SLOT_QUERY_ID}
            and str(slot) == str(slot_id)
            and str(category) == str(category_label)
        ):
            category = str(rng.choice(other_categories))
        chip_by_day_slot.setdefault((day, slot), category)

    chips = tuple(
        _make_chip(
            day=int(day),
            slot_id=str(slot),
            category_label=str(category),
            instance_seed=int(instance_seed),
        )
        for (day, slot), category in sorted(chip_by_day_slot.items(), key=lambda item: (int(item[0][0]), str(item[0][1])))
    )
    return chips, target_date, tuple(str(key) for key in matching_keys)


def _resolve_query(instance_seed: int, params: Mapping[str, Any]) -> _ResolvedEventGridQuery:
    query_id, query_probs = _resolve_query_id(int(instance_seed), params)
    scene_variant, scene_probs = _resolve_named_variant(
        instance_seed=int(instance_seed),
        params=params,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_PAGE_CALENDAR_SCENE_VARIANTS,
        namespace="scene_variant",
    )
    style_variant, style_probs = _resolve_named_variant(
        instance_seed=int(instance_seed),
        params=params,
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_TIME_ARTIFACT_STYLE_VARIANTS,
        namespace="style_variant",
    )
    accent_color_name, accent_probs = _resolve_named_variant(
        instance_seed=int(instance_seed),
        params=params,
        explicit_key="accent_color_name",
        weights_key="accent_color_name_weights",
        balance_flag_key="balanced_accent_color_name_sampling",
        supported=SUPPORTED_TIME_ARTIFACT_COLOR_NAMES,
        namespace="accent_color_name",
    )
    layout_mode, layout_probs = _resolve_named_variant(
        instance_seed=int(instance_seed),
        params=params,
        explicit_key="layout_mode",
        weights_key="layout_mode_weights",
        balance_flag_key="balanced_layout_mode_sampling",
        supported=SUPPORTED_EVENT_GRID_LAYOUT_MODES,
        namespace="layout_mode",
    )
    title_mode, title_probs = _resolve_named_variant(
        instance_seed=int(instance_seed),
        params=params,
        explicit_key="title_mode",
        weights_key="title_mode_weights",
        balance_flag_key="balanced_title_mode_sampling",
        supported=SUPPORTED_EVENT_GRID_TITLE_MODES,
        namespace="title_mode",
    )
    surface_mode, surface_probs = _resolve_named_variant(
        instance_seed=int(instance_seed),
        params=params,
        explicit_key="surface_mode",
        weights_key="surface_mode_weights",
        balance_flag_key="balanced_surface_mode_sampling",
        supported=SUPPORTED_EVENT_GRID_SURFACE_MODES,
        namespace="surface_mode",
    )
    text_color_mode, text_color_probs = _resolve_named_variant(
        instance_seed=int(instance_seed),
        params=params,
        explicit_key="text_color_mode",
        weights_key="text_color_mode_weights",
        balance_flag_key="balanced_text_color_mode_sampling",
        supported=SUPPORTED_EVENT_GRID_TEXT_COLOR_MODES,
        namespace="text_color_mode",
    )
    category_labels = _resolve_category_labels(params)
    slot_id, slot_probs = _resolve_named_variant(
        instance_seed=int(instance_seed),
        params=params,
        explicit_key="slot_id",
        weights_key="slot_id_weights",
        balance_flag_key="balanced_slot_id_sampling",
        supported=tuple(slot for slot, _ in EVENT_SLOT_SPECS),
        namespace="slot_id",
    )
    category_label, category_probs = _resolve_choice(
        instance_seed=int(instance_seed),
        params=params,
        explicit_key="category_label",
        values=category_labels,
        namespace="category_label",
    )
    target_count, target_count_probs = _resolve_target_count(int(instance_seed), params)
    year, month, days_in_month, row_count = _resolve_year_month(int(instance_seed), params)
    event_chips, target_date, matching_keys = _build_event_chips(
        instance_seed=int(instance_seed),
        params=params,
        query_id=str(query_id),
        days_in_month=int(days_in_month),
        slot_id=str(slot_id),
        category_label=str(category_label),
        category_labels=tuple(str(value) for value in category_labels),
        target_count=int(target_count),
    )
    return _ResolvedEventGridQuery(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        accent_color_name=str(accent_color_name),
        layout_mode=str(layout_mode),
        title_mode=str(title_mode),
        surface_mode=str(surface_mode),
        text_color_mode=str(text_color_mode),
        year=int(year),
        month=int(month),
        month_name=str(month_name(int(month))),
        days_in_month=int(days_in_month),
        row_count=int(row_count),
        slot_id=str(slot_id),
        slot_label=str(_slot_label(str(slot_id))),
        category_label=str(category_label),
        target_date=(int(target_date) if target_date is not None else None),
        target_count=(int(target_count) if str(query_id) == CATEGORY_SLOT_DAY_COUNT_QUERY_ID else None),
        event_chips=tuple(event_chips),
        matching_chip_keys=tuple(str(key) for key in matching_keys),
        query_id_probabilities=dict(query_probs),
        category_probabilities=dict(category_probs),
        slot_probabilities=dict(slot_probs),
        target_count_probabilities=dict(target_count_probs),
        scene_variant_probabilities=dict(scene_probs),
        style_variant_probabilities=dict(style_probs),
        accent_color_name_probabilities=dict(accent_probs),
        layout_mode_probabilities=dict(layout_probs),
        title_mode_probabilities=dict(title_probs),
        surface_mode_probabilities=dict(surface_probs),
        text_color_mode_probabilities=dict(text_color_probs),
    )


def _prompt_slots(query: _ResolvedEventGridQuery, prompt_defaults: Mapping[str, Any]) -> Dict[str, str]:
    answer_hint_key = f"answer_hint_{query.query_id}"
    annotation_hint_key = f"annotation_hint_{query.query_id}"
    object_description_key = f"object_description_{query.query_id}"
    json_example_key = f"json_example_{query.query_id}"
    json_example_answer_only_key = f"json_example_answer_only_{query.query_id}"
    object_description = str(prompt_defaults[object_description_key]).format(
        category_label=str(query.category_label),
        slot_label=str(query.slot_label),
    )
    slots = {
        "object_description": str(object_description),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "annotation_hint": str(prompt_defaults[annotation_hint_key]),
        "answer_hint": str(prompt_defaults[answer_hint_key]),
        "json_example": str(prompt_defaults[json_example_key]),
        "json_example_answer_only": str(prompt_defaults[json_example_answer_only_key]),
        "date_number": str(int(query.target_date or 1)),
        "slot_label": str(query.slot_label),
        "category_label": str(query.category_label),
    }
    return dict(slots)


class BaseCalendarEventGridTask:
    """Reason over category/event chips inside one month calendar grid."""

    domain = "pages"
    fixed_query_id = ""

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        if str(self.fixed_query_id).strip():
            params = _forced_query_params(params, query_id=str(self.fixed_query_id))
        query = _resolve_query(int(instance_seed), params=params)
        render_params = resolve_calendar_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_values=asdict(_DEFAULTS),
            instance_seed=int(instance_seed),
        )
        calendar_theme = build_time_artifact_calendar_theme(
            accent_color_name=str(query.accent_color_name),
            style_variant=str(query.style_variant),
            surface_mode=str(query.surface_mode),
            text_color_mode=str(query.text_color_mode),
        )
        panel_bbox, panel_layout_meta = _resolve_calendar_panel_bbox(
            instance_seed=int(instance_seed),
            params=params,
            render_params=render_params,
            layout_mode=str(query.layout_mode),
        )
        title_text, title_meta = _resolve_title_text(
            instance_seed=int(instance_seed),
            title_mode=str(query.title_mode),
            month=int(query.month),
            year=int(query.year),
            params=params,
        )
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        image = background.copy().convert("RGB")
        rendered_scene = render_month_calendar_event_grid_scene(
            image,
            year=int(query.year),
            month=int(query.month),
            event_chips=tuple(query.event_chips),
            slot_order=tuple(slot for slot, _ in EVENT_SLOT_SPECS),
            scene_variant=str(query.scene_variant),
            render_params=render_params,
            visual_theme=calendar_theme,
            panel_bbox_px=panel_bbox,
            title_text=str(title_text),
        )
        image, post_noise_meta = apply_post_image_noise(
            image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        answer_gt: TypedValue
        annotation_gt: TypedValue
        if str(query.query_id) in {DATE_SLOT_CATEGORY_QUERY_ID, DATE_FOR_CATEGORY_SLOT_QUERY_ID}:
            if query.target_date is None:
                raise ValueError("date-slot query requires target_date")
            chip_key = _chip_key(int(query.target_date), str(query.slot_id))
            annotation_gt = TypedValue(
                type="keyed_bbox_map",
                value={
                    "date_cell": [
                        round(float(value), 3)
                        for value in rendered_scene.date_cell_bboxes_by_day[int(query.target_date)]
                    ],
                    "event_chip": [
                        round(float(value), 3)
                        for value in rendered_scene.event_chip_bboxes_by_key[str(chip_key)]
                    ],
                },
            )
            if str(query.query_id) == DATE_SLOT_CATEGORY_QUERY_ID:
                answer_gt = TypedValue(type="string", value=str(query.category_label))
            else:
                answer_gt = TypedValue(type="integer", value=int(query.target_date))
        else:
            annotation_boxes = [
                [round(float(value), 3) for value in rendered_scene.event_chip_bboxes_by_key[str(key)]]
                for key in query.matching_chip_keys
            ]
            annotation_gt = TypedValue(type="bbox_set", value=[list(box) for box in annotation_boxes])
            answer_gt = TypedValue(type="integer", value=int(len(query.matching_chip_keys)))

        answer_hint_key = f"answer_hint_{query.query_id}"
        annotation_hint_key = f"annotation_hint_{query.query_id}"
        object_description_key = f"object_description_{query.query_id}"
        json_example_key = f"json_example_{query.query_id}"
        json_example_answer_only_key = f"json_example_answer_only_{query.query_id}"
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                object_description_key,
                answer_hint_key,
                annotation_hint_key,
                json_example_key,
                json_example_answer_only_key,
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        slots = _prompt_slots(query, prompt_defaults)
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=PUBLIC_SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots=slots,
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        event_chip_records = []
        for chip in query.event_chips:
            key = _chip_key(int(chip.day), str(chip.slot_id))
            bbox = rendered_scene.event_chip_bboxes_by_key.get(str(key))
            event_chip_records.append(
                {
                    "chip_key": str(key),
                    "date_number": int(chip.day),
                    "slot_id": str(chip.slot_id),
                    "slot_label": str(chip.slot_label),
                    "category_label": str(chip.category_label),
                    "bbox_px": [round(float(value), 3) for value in bbox] if bbox is not None else None,
                }
            )

        query_params = {
            "query_id": str(query.query_id),
            "scene_id": PUBLIC_SCENE_ID,
            "scene_variant": str(query.scene_variant),
            "style_variant": str(query.style_variant),
            "accent_color_name": str(query.accent_color_name),
            "layout_mode": str(query.layout_mode),
            "title_mode": str(query.title_mode),
            "surface_mode": str(query.surface_mode),
            "text_color_mode": str(query.text_color_mode),
            "visible_title_text": str(rendered_scene.title_text),
            "year": int(query.year),
            "month": int(query.month),
            "month_name": str(query.month_name),
            "days_in_month": int(query.days_in_month),
            "row_count": int(query.row_count),
            "slot_id": str(query.slot_id),
            "slot_label": str(query.slot_label),
            "category_label": str(query.category_label),
            "event_category_labels": [str(value) for value in _resolve_category_labels(params)],
            "target_date": int(query.target_date) if query.target_date is not None else None,
            "target_count": int(query.target_count) if query.target_count is not None else None,
            "matching_chip_keys": [str(key) for key in query.matching_chip_keys],
            "query_id_probabilities": dict(query.query_id_probabilities),
            "category_probabilities": dict(query.category_probabilities),
            "slot_probabilities": dict(query.slot_probabilities),
            "target_count_probabilities": dict(query.target_count_probabilities),
            "scene_variant_probabilities": dict(query.scene_variant_probabilities),
            "style_variant_probabilities": dict(query.style_variant_probabilities),
            "accent_color_name_probabilities": dict(query.accent_color_name_probabilities),
            "layout_mode_probabilities": dict(query.layout_mode_probabilities),
            "title_mode_probabilities": dict(query.title_mode_probabilities),
            "surface_mode_probabilities": dict(query.surface_mode_probabilities),
            "text_color_mode_probabilities": dict(query.text_color_mode_probabilities),
        }
        trace_payload = {
            "scene_ir": {
                "scene_id": PUBLIC_SCENE_ID,
                "scene_kind": "pages_calendar_event_grid",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": dict(query_params),
            },
            "query_spec": {
                "query_id": str(query.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_id": PUBLIC_SCENE_ID,
                "scene_variant": str(query.scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": [round(float(value), 3) for value in rendered_scene.scene_bbox_px],
                "calendar_event_grid_style": {
                    "accent_color_name": str(query.accent_color_name),
                    "style_variant": str(query.style_variant),
                    "surface_mode": str(query.surface_mode),
                    "text_color_mode": str(query.text_color_mode),
                    "layout_mode": str(query.layout_mode),
                    "title_mode": str(query.title_mode),
                    "title": dict(title_meta),
                    "panel_layout": dict(panel_layout_meta),
                    "row_count": int(query.row_count),
                    "slot_order": [str(slot) for slot, _ in EVENT_SLOT_SPECS],
                    "title_text": str(rendered_scene.title_text),
                    "resolved_colors_rgb": {
                        "panel_fill": [int(value) for value in calendar_theme.panel_fill_rgb],
                        "panel_outline": [int(value) for value in calendar_theme.panel_outline_rgb],
                        "title_text": [int(value) for value in calendar_theme.title_text_rgb],
                        "weekday_fill": [int(value) for value in calendar_theme.weekday_fill_rgb],
                        "weekday_text": [int(value) for value in calendar_theme.weekday_text_rgb],
                        "grid_line": [int(value) for value in calendar_theme.grid_line_rgb],
                        "date_text": [int(value) for value in calendar_theme.date_text_rgb],
                    },
                },
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": [round(float(value), 3) for value in rendered_scene.scene_bbox_px],
                "calendar_panel_bbox_px": [round(float(value), 3) for value in rendered_scene.panel_bbox_px],
                "calendar_event_grid_panel_bbox_px": [round(float(value), 3) for value in rendered_scene.panel_bbox_px],
                "date_cells_by_day": {
                    str(day): [round(float(value), 3) for value in bbox]
                    for day, bbox in rendered_scene.date_cell_bboxes_by_day.items()
                },
                "event_chips_by_key": {
                    str(key): [round(float(value), 3) for value in bbox]
                    for key, bbox in rendered_scene.event_chip_bboxes_by_key.items()
                },
                "event_chip_records": [dict(record) for record in event_chip_records],
                "matching_chip_keys": [str(key) for key in query.matching_chip_keys],
                "target_date": int(query.target_date) if query.target_date is not None else None,
            },
            "execution_trace": {
                **dict(query_params),
                "event_chip_records": [dict(record) for record in event_chip_records],
                "answer_value": answer_gt.value,
            },
            "witness_symbolic": {
                "type": str(annotation_gt.type),
                "value": annotation_gt.value,
            },
            "projected_annotation": {
                str(annotation_gt.type): annotation_gt.value,
            },
        }

        visual_scan = min(1.0, 0.24 + (0.015 * float(len(query.event_chips))) + (0.06 * float(query.row_count - 4)))
        ambiguity = min(1.0, 0.22 + (0.05 * float(len(query.matching_chip_keys))) + (0.08 if query.target_date is None else 0.0))
        clutter = min(1.0, 0.20 + (0.018 * float(len(query.event_chips))))
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=PUBLIC_SCENE_ID,
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


def _forced_query_params(params: Mapping[str, Any], *, query_id: str) -> Dict[str, Any]:
    merged = dict(params)
    explicit = merged.get("query_id", merged.get("query_variant"))
    if explicit is not None and str(explicit) != str(query_id):
        raise ValueError(f"query_id must be {query_id!r} for this public task")
    merged["query_id"] = str(query_id)
    merged.pop("query_variant", None)
    return merged


__all__ = [
    "BaseCalendarEventGridTask",
    "CATEGORY_SLOT_DAY_COUNT_QUERY_ID",
    "CATEGORY_SLOT_DAY_COUNT_TASK_ID",
    "DATE_FOR_CATEGORY_SLOT_QUERY_ID",
    "DATE_FOR_CATEGORY_SLOT_TASK_ID",
    "DATE_SLOT_CATEGORY_QUERY_ID",
    "DATE_SLOT_CATEGORY_TASK_ID",
    "EVENT_CATEGORY_LABELS",
    "EVENT_SLOT_SPECS",
    "PUBLIC_SCENE_ID",
    "SUPPORTED_EVENT_GRID_LAYOUT_MODES",
    "SUPPORTED_EVENT_GRID_SURFACE_MODES",
    "SUPPORTED_EVENT_GRID_TEXT_COLOR_MODES",
    "SUPPORTED_EVENT_GRID_TITLE_MODES",
    "SUPPORTED_QUERY_IDS",
]
