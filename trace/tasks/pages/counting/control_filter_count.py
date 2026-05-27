"""Synthetic GUI control-set counting task."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from ....core.seed import hash64, spawn_rng
from ....core.task_group_config import get_task_group_defaults, resolve_task_group_section_defaults
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import draw_text_centered, fit_font_to_box, load_font
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.gui_render_params import resolve_gui_window_render_params


TASK_ID = "gui_counting_control_filter_internal"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "disabled_controls_in_group_count",
    "selected_enabled_controls_in_group_count",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "office_document",
    "creative_workspace",
    "developer_ide",
    "cad_workspace",
    "scientific_plotter",
    "os_file_manager",
)
SUPPORTED_STYLE_VARIANTS: Tuple[str, ...] = ("standard", "compact", "contrast", "cool", "warm", "sage")
_BALANCE_SALT = 40279

BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]


@dataclass(frozen=True)
class _TaskDefaults:
    canvas_width: int = 1280
    canvas_height: int = 800
    window_margin_px: int = 42
    title_bar_height_px: int = 46
    menu_bar_height_px: int = 34
    corner_radius_px: int = 16
    control_corner_radius_px: int = 8
    control_outline_width_px: int = 2
    badge_size_px: int = 28
    title_font_size_px: int = 24
    body_font_size_px: int = 17
    small_font_size_px: int = 13
    label_font_size_px: int = 18
    group_name_pool: Tuple[str, ...] = ("Layout", "Editing", "Review", "Output")
    state_count_support: Tuple[int, ...] = (2, 3, 4, 5, 6)
    candidate_label_pool: Tuple[str, ...] = tuple(chr(ord("A") + idx) for idx in range(26))


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    window_margin_px: int
    title_bar_height_px: int
    menu_bar_height_px: int
    corner_radius_px: int
    control_corner_radius_px: int
    control_outline_width_px: int
    badge_size_px: int
    title_font_size_px: int
    body_font_size_px: int
    small_font_size_px: int
    label_font_size_px: int


@dataclass(frozen=True)
class _Theme:
    name: str
    app_fill: Color
    title_bar: Color
    title_text: Color
    chrome_line: Color
    panel_fill: Color
    panel_alt_fill: Color
    control_fill: Color
    control_outline: Color
    control_text: Color
    muted_text: Color
    disabled_fill: Color
    disabled_outline: Color
    selected_fill: Color
    selected_outline: Color
    accent: Color
    accent_alt: Color
    badge_fill: Color
    badge_text: Color
    workspace_line: Color


@dataclass(frozen=True)
class _AppProfile:
    app_title: str
    window_title: str
    primary_tab: str
    secondary_tab: str
    workspace_title: str
    status_text: str


@dataclass(frozen=True)
class _CommandOption:
    command_key: str
    display_text: str
    icon_kind: str


@dataclass(frozen=True)
class _ControlSpec:
    control_id: str
    candidate_label: str
    group_name: str
    group_index: int
    order_in_group: int
    global_order_index: int
    command: _CommandOption
    enabled: bool
    selected: bool
    is_reference: bool


@dataclass(frozen=True)
class _ResolvedQuery:
    query_id: str
    scene_variant: str
    style_variant: str
    controls: Tuple[_ControlSpec, ...]
    group_names: Tuple[str, ...]
    target_group_name: str
    target_group_index: int
    reference_label: str
    answer_value: int
    evidence_control_ids: Tuple[str, ...]
    state_count_support: Tuple[int, ...]
    candidate_label_pool: Tuple[str, ...]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedScene:
    control_bboxes_by_id: Dict[str, List[float]]
    badge_bboxes_by_id: Dict[str, List[float]]
    group_bboxes_by_name: Dict[str, List[float]]
    control_records: Tuple[Dict[str, Any], ...]
    scene_bbox_px: List[float]
    window_bbox_px: List[float]
    profile: _AppProfile
    theme: _Theme


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("pages", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = {
    str(key): float(value)
    for key, value in resolve_task_group_section_defaults(_TASK_GROUP_DEFAULTS, "complexity", task_id=TASK_ID)
    .get("criteria_weights", {})
    .items()
    if float(value) > 0.0
}
_VISUAL_DEFAULTS = _TASK_GROUP_DEFAULTS.get("visual", {}) if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {}
POST_IMAGE_BACKGROUND_DEFAULTS = (
    dict(_VISUAL_DEFAULTS.get("background", {})) if isinstance(_VISUAL_DEFAULTS.get("background"), Mapping) else {}
)
POST_IMAGE_NOISE_DEFAULTS = (
    dict(_VISUAL_DEFAULTS.get("noise", {})) if isinstance(_VISUAL_DEFAULTS.get("noise"), Mapping) else {}
)

_APP_PROFILES: Dict[str, _AppProfile] = {
    "office_document": _AppProfile("Document Studio", "Quarterly Review", "Home", "Review", "Control Center", "Edited now"),
    "creative_workspace": _AppProfile("Canvas Lab", "Campaign Layout", "Design", "Assets", "Tool Controls", "RGB / 100%"),
    "developer_ide": _AppProfile("Code Desk", "trace_app.py", "Build", "Debug", "Command Palette", "main / clean"),
    "cad_workspace": _AppProfile("Model Works", "Bracket Assembly", "Sketch", "Inspect", "Model Tools", "Units: mm"),
    "scientific_plotter": _AppProfile("Lab Plot", "Sensor Run 18", "Analyze", "Plot", "Analysis Tools", "Sample 2.4k"),
    "os_file_manager": _AppProfile("File Center", "Research Folder", "Files", "View", "Folder Actions", "23 items"),
}

_COMMAND_OPTIONS: Tuple[_CommandOption, ...] = (
    _CommandOption("open_panel", "Open", "folder"),
    _CommandOption("save_file", "Save", "save"),
    _CommandOption("sync_now", "Sync", "sync"),
    _CommandOption("share_item", "Share", "share"),
    _CommandOption("search_view", "Search", "search"),
    _CommandOption("filter_rows", "Filter", "filter"),
    _CommandOption("sort_list", "Sort", "sort"),
    _CommandOption("copy_item", "Copy", "copy"),
    _CommandOption("paste_item", "Paste", "paste"),
    _CommandOption("group_items", "Group", "group"),
    _CommandOption("align_left", "Align", "align"),
    _CommandOption("crop_item", "Crop", "crop"),
    _CommandOption("rotate_item", "Rotate", "rotate"),
    _CommandOption("measure_item", "Measure", "measure"),
    _CommandOption("zoom_fit", "Fit", "zoom"),
    _CommandOption("preview_item", "Preview", "preview"),
    _CommandOption("validate_item", "Check", "check"),
    _CommandOption("export_item", "Export", "export"),
    _CommandOption("print_item", "Print", "print"),
    _CommandOption("lock_item", "Lock", "lock"),
    _CommandOption("bookmark_item", "Bookmark", "bookmark"),
    _CommandOption("comment_item", "Comment", "comment"),
    _CommandOption("settings_item", "Settings", "settings"),
    _CommandOption("history_item", "History", "history"),
    _CommandOption("run_action", "Run", "run"),
    _CommandOption("inspect_item", "Inspect", "inspect"),
)


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _bbox_list(bbox: BBox) -> List[float]:
    return [round(float(value), 3) for value in bbox]


def _measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> Tuple[float, float]:
    try:
        bbox = draw.textbbox((0, 0), str(text), font=font)
        return (float(bbox[2] - bbox[0]), float(bbox[3] - bbox[1]))
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        return (float(width), float(height))


def _draw_text_left(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    bbox: BBox,
    fill: Color,
    max_size_px: int,
    min_size_px: int = 8,
    bold: bool = False,
) -> None:
    x1, y1, x2, y2 = [float(value) for value in bbox]
    font = fit_font_to_box(
        draw,
        text=str(text),
        max_width=max(1.0, float(x2 - x1)),
        max_height=max(1.0, float(y2 - y1)),
        bold=bool(bold),
        min_size_px=int(min_size_px),
        max_size_px=int(max_size_px),
        fill_ratio=0.96,
    )
    _width, height = _measure_text(draw, str(text), font)
    y = float(y1) + max(0.0, (float(y2 - y1) - float(height)) / 2.0) - 1.0
    draw.text((float(x1), float(y)), str(text), fill=fill, font=font)


def _draw_text_center_fit(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    bbox: BBox,
    fill: Color,
    max_size_px: int,
    min_size_px: int = 8,
    bold: bool = False,
) -> None:
    x1, y1, x2, y2 = [float(value) for value in bbox]
    font = fit_font_to_box(
        draw,
        text=str(text),
        max_width=max(1.0, float(x2 - x1)),
        max_height=max(1.0, float(y2 - y1)),
        bold=bool(bold),
        min_size_px=int(min_size_px),
        max_size_px=int(max_size_px),
        fill_ratio=0.90,
    )
    draw_text_centered(
        draw,
        text=str(text),
        center=((float(x1) + float(x2)) / 2.0, (float(y1) + float(y2)) / 2.0),
        font=font,
        fill=fill,
        stroke_width=0,
    )


def _rounded_rect(
    draw: ImageDraw.ImageDraw,
    bbox: BBox,
    *,
    radius: int,
    fill: Color,
    outline: Color | None = None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(
        [float(value) for value in bbox],
        radius=max(0, int(radius)),
        fill=fill,
        outline=outline,
        width=max(1, int(width)),
    )


def _theme(style_variant: str) -> _Theme:
    if str(style_variant) == "cool":
        return _Theme(
            name="cool",
            app_fill=(253, 254, 255),
            title_bar=(49, 80, 112),
            title_text=(255, 255, 255),
            chrome_line=(198, 211, 224),
            panel_fill=(244, 248, 252),
            panel_alt_fill=(235, 244, 250),
            control_fill=(255, 255, 255),
            control_outline=(177, 196, 213),
            control_text=(35, 48, 63),
            muted_text=(85, 101, 118),
            disabled_fill=(231, 236, 241),
            disabled_outline=(164, 179, 193),
            selected_fill=(225, 241, 255),
            selected_outline=(38, 113, 171),
            accent=(38, 113, 171),
            accent_alt=(64, 142, 137),
            badge_fill=(35, 58, 84),
            badge_text=(255, 255, 255),
            workspace_line=(216, 226, 236),
        )
    if str(style_variant) == "warm":
        return _Theme(
            name="warm",
            app_fill=(255, 254, 250),
            title_bar=(116, 77, 49),
            title_text=(255, 255, 255),
            chrome_line=(219, 207, 193),
            panel_fill=(250, 247, 241),
            panel_alt_fill=(244, 238, 228),
            control_fill=(255, 255, 252),
            control_outline=(207, 186, 164),
            control_text=(55, 44, 34),
            muted_text=(112, 93, 73),
            disabled_fill=(236, 231, 224),
            disabled_outline=(177, 160, 145),
            selected_fill=(255, 238, 219),
            selected_outline=(159, 90, 45),
            accent=(159, 90, 45),
            accent_alt=(46, 126, 119),
            badge_fill=(75, 55, 41),
            badge_text=(255, 255, 255),
            workspace_line=(229, 219, 207),
        )
    if str(style_variant) == "sage":
        return _Theme(
            name="sage",
            app_fill=(253, 255, 253),
            title_bar=(53, 92, 79),
            title_text=(255, 255, 255),
            chrome_line=(198, 216, 208),
            panel_fill=(244, 250, 247),
            panel_alt_fill=(234, 245, 240),
            control_fill=(255, 255, 255),
            control_outline=(174, 199, 188),
            control_text=(35, 53, 47),
            muted_text=(80, 104, 96),
            disabled_fill=(230, 238, 234),
            disabled_outline=(160, 181, 172),
            selected_fill=(222, 244, 234),
            selected_outline=(41, 123, 100),
            accent=(41, 123, 100),
            accent_alt=(166, 91, 65),
            badge_fill=(35, 65, 55),
            badge_text=(255, 255, 255),
            workspace_line=(216, 228, 223),
        )
    if str(style_variant) == "compact":
        return _Theme(
            name="compact",
            app_fill=(251, 252, 253),
            title_bar=(45, 53, 67),
            title_text=(250, 252, 255),
            chrome_line=(203, 209, 218),
            panel_fill=(242, 245, 248),
            panel_alt_fill=(232, 240, 240),
            control_fill=(255, 255, 255),
            control_outline=(173, 185, 195),
            control_text=(38, 44, 55),
            muted_text=(91, 99, 112),
            disabled_fill=(230, 233, 237),
            disabled_outline=(186, 192, 200),
            selected_fill=(221, 244, 242),
            selected_outline=(0, 126, 145),
            accent=(0, 126, 145),
            accent_alt=(225, 90, 71),
            badge_fill=(31, 39, 51),
            badge_text=(255, 255, 255),
            workspace_line=(215, 222, 230),
        )
    if str(style_variant) == "contrast":
        return _Theme(
            name="contrast",
            app_fill=(250, 250, 247),
            title_bar=(34, 34, 38),
            title_text=(255, 255, 255),
            chrome_line=(184, 184, 178),
            panel_fill=(241, 241, 236),
            panel_alt_fill=(229, 239, 246),
            control_fill=(255, 255, 252),
            control_outline=(83, 92, 103),
            control_text=(26, 28, 32),
            muted_text=(77, 81, 88),
            disabled_fill=(224, 224, 218),
            disabled_outline=(152, 152, 146),
            selected_fill=(246, 226, 230),
            selected_outline=(184, 53, 71),
            accent=(184, 53, 71),
            accent_alt=(24, 121, 108),
            badge_fill=(34, 34, 38),
            badge_text=(255, 255, 255),
            workspace_line=(201, 202, 197),
        )
    return _Theme(
        name="standard",
        app_fill=(255, 255, 255),
        title_bar=(63, 78, 104),
        title_text=(255, 255, 255),
        chrome_line=(205, 211, 220),
        panel_fill=(246, 248, 250),
        panel_alt_fill=(237, 243, 248),
        control_fill=(255, 255, 255),
        control_outline=(186, 196, 210),
        control_text=(40, 48, 61),
        muted_text=(91, 101, 117),
        disabled_fill=(231, 235, 240),
        disabled_outline=(178, 187, 199),
        selected_fill=(225, 239, 255),
        selected_outline=(43, 114, 197),
        accent=(43, 114, 197),
        accent_alt=(213, 111, 54),
        badge_fill=(36, 47, 64),
        badge_text=(255, 255, 255),
        workspace_line=(219, 225, 233),
    )


def _normalize_int_support(params: Mapping[str, Any], key: str, fallback: Sequence[int]) -> Tuple[int, ...]:
    raw_values = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), fallback))
    support: List[int] = []
    for raw_value in raw_values:
        value = int(raw_value)
        if value not in support:
            support.append(value)
    if not support:
        raise ValueError(f"{key} must not be empty for {TASK_ID}")
    return tuple(int(value) for value in support)


def _normalize_str_support(params: Mapping[str, Any], key: str, fallback: Sequence[str]) -> Tuple[str, ...]:
    raw_values = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), fallback))
    support: List[str] = []
    for raw_value in raw_values:
        value = str(raw_value).strip()
        if value and value not in support:
            support.append(value)
    if not support:
        raise ValueError(f"{key} must not be empty for {TASK_ID}")
    return tuple(str(value) for value in support)


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
    balanced = apply_balanced_variant_sampling(
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
    return str(balanced), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _select_indices(*, instance_seed: int, namespace: str, count: int, size: int) -> Tuple[int, ...]:
    if int(count) > int(size):
        raise ValueError("cannot select more control indices than group size")
    indices = list(range(int(size)))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{namespace}")
    rng.shuffle(indices)
    return tuple(sorted(int(value) for value in indices[: int(count)]))


def _select_values(
    *,
    instance_seed: int,
    namespace: str,
    values: Sequence[Tuple[int, int]],
    count: int,
) -> Tuple[Tuple[int, int], ...]:
    if int(count) > len(values):
        raise ValueError("cannot select more values than population size")
    shuffled = list(values)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{namespace}")
    rng.shuffle(shuffled)
    return tuple(sorted(shuffled[: int(count)]))


def _group_query_state_sets(
    *,
    instance_seed: int,
    query_id: str,
    target_group_index: int,
    target_group_size: int,
    answer_value: int,
    group_sizes: Sequence[int],
) -> Tuple[set[Tuple[int, int]], set[Tuple[int, int]]]:
    disabled: set[Tuple[int, int]] = set()
    selected: set[Tuple[int, int]] = set()
    target_indices = _select_indices(
        instance_seed=int(instance_seed),
        namespace=f"target_state.{query_id}.{target_group_index}",
        count=int(answer_value),
        size=int(target_group_size),
    )
    target_keys = {(int(target_group_index), int(idx)) for idx in target_indices}
    if str(query_id) == "disabled_controls_in_group_count":
        disabled.update(target_keys)
    elif str(query_id) == "selected_enabled_controls_in_group_count":
        selected.update(target_keys)

    for group_index, group_size in enumerate(group_sizes):
        if str(query_id) == "selected_enabled_controls_in_group_count":
            group_keys = [(int(group_index), int(idx)) for idx in range(int(group_size))]
            if int(group_index) == int(target_group_index):
                remaining = [key for key in group_keys if key not in target_keys]
                distractor_count = min(2, len(remaining))
                for key in _select_values(
                    instance_seed=int(instance_seed) + int(group_index),
                    namespace=f"selected_disabled_target_distractors.{group_index}",
                    values=remaining,
                    count=distractor_count,
                ):
                    disabled.add(key)
                    selected.add(key)
                continue

            selected_enabled_count = min(2, len(group_keys))
            selected_enabled = set(
                _select_values(
                    instance_seed=int(instance_seed) + (53 * int(group_index)),
                    namespace=f"selected_enabled_group_distractors.{group_index}",
                    values=group_keys,
                    count=selected_enabled_count,
                )
            )
            selected.update(selected_enabled)
            remaining = [key for key in group_keys if key not in selected_enabled]
            selected_disabled_count = min(1, len(remaining))
            for key in _select_values(
                instance_seed=int(instance_seed) + (97 * int(group_index)),
                namespace=f"selected_disabled_group_distractors.{group_index}",
                values=remaining,
                count=selected_disabled_count,
            ):
                disabled.add(key)
                selected.add(key)
            continue

        non_target_state_count = 1 + int(
            _support_selection_index(
                {"query_id": query_id},
                instance_seed=int(instance_seed) + int(group_index),
                namespace=f"state_distractors.{group_index}",
            )
            % 2
        )
        if int(group_index) == int(target_group_index):
            distractor_count = 1 if int(group_size) - int(answer_value) >= 2 else 0
        else:
            distractor_count = min(non_target_state_count, max(0, int(group_size) - 1))
        if distractor_count <= 0:
            continue
        choices = _select_indices(
            instance_seed=int(instance_seed) + (97 * int(group_index)),
            namespace=f"distractor_state.{query_id}.{group_index}",
            count=int(distractor_count),
            size=int(group_size),
        )
        for idx in choices:
            key = (int(group_index), int(idx))
            if key in disabled or key in selected:
                continue
            if str(query_id) == "disabled_controls_in_group_count":
                selected.add(key)
            elif str(query_id) == "selected_enabled_controls_in_group_count":
                disabled.add(key)
                selected.add(key)
    return disabled, selected


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query")
    query_id, query_id_probabilities = _resolve_named_axis(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        supported=SUPPORTED_QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        namespace="query_id",
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        rng,
        instance_seed=int(instance_seed),
        params=_decoupled_params(params, divisor=len(SUPPORTED_QUERY_IDS), namespace="scene_variant"),
        supported=SUPPORTED_SCENE_VARIANTS,
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

    group_names = _normalize_str_support(params, "group_name_pool", _DEFAULTS.group_name_pool)
    if len(group_names) != 4:
        raise ValueError(f"{TASK_ID} requires exactly four group names")
    state_count_support = _normalize_int_support(params, "state_count_support", _DEFAULTS.state_count_support)
    answer_support = _normalize_int_support(
        params,
        f"{query_id}_state_count_support",
        state_count_support,
    )
    candidate_label_pool = _normalize_str_support(params, "candidate_label_pool", _DEFAULTS.candidate_label_pool)

    explicit_answer_value = params.get("answer_value")
    if explicit_answer_value is not None:
        answer_value = int(explicit_answer_value)
        if int(answer_value) not in set(int(value) for value in answer_support):
            raise ValueError("answer_value must be in the active answer support")
    else:
        answer_value = int(
            answer_support[
                _support_selection_index(params, instance_seed=int(instance_seed), namespace=f"answer_value.{query_id}")
                % len(answer_support)
            ]
        )

    target_group_index = int(
        _support_selection_index(params, instance_seed=int(instance_seed), namespace=f"target_group.{query_id}")
        % len(group_names)
    )
    if str(query_id) == "selected_enabled_controls_in_group_count":
        target_group_size = 8
    elif str(query_id) == "disabled_controls_in_group_count":
        target_group_size = min(8, max(int(answer_value) + 2, 6))
    else:
        target_group_size = min(8, max(int(answer_value) + 2, 6))

    group_sizes: List[int] = []
    for group_index in range(len(group_names)):
        if int(group_index) == int(target_group_index):
            group_sizes.append(int(target_group_size))
        elif str(query_id) == "selected_enabled_controls_in_group_count":
            group_sizes.append(6)
        elif str(query_id) == "disabled_controls_in_group_count":
            group_sizes.append(5)
        else:
            group_sizes.append(4 + int((group_index + target_group_index + answer_value) % 3))
    total_controls = int(sum(group_sizes))
    if total_controls > len(candidate_label_pool):
        raise ValueError("candidate_label_pool must cover all rendered GUI controls")
    if total_controls > len(_COMMAND_OPTIONS):
        raise ValueError("not enough command options for rendered GUI controls")

    command_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.commands")
    command_options = list(_COMMAND_OPTIONS)
    command_rng.shuffle(command_options)
    disabled_set, selected_set = _group_query_state_sets(
        instance_seed=int(instance_seed),
        query_id=str(query_id),
        target_group_index=int(target_group_index),
        target_group_size=int(target_group_size),
        answer_value=int(answer_value),
        group_sizes=group_sizes,
    )

    controls: List[_ControlSpec] = []
    label_index = 0
    evidence_ids: List[str] = []
    reference_label = ""
    for group_index, group_name in enumerate(group_names):
        for order_in_group in range(int(group_sizes[int(group_index)])):
            label = str(candidate_label_pool[int(label_index)])
            control_id = f"control_{str(label).lower()}"
            disabled = (int(group_index), int(order_in_group)) in disabled_set
            selected = (int(group_index), int(order_in_group)) in selected_set
            is_reference = False
            if str(query_id) == "disabled_controls_in_group_count":
                if int(group_index) == int(target_group_index) and bool(disabled):
                    evidence_ids.append(str(control_id))
            elif str(query_id) == "selected_enabled_controls_in_group_count":
                if int(group_index) == int(target_group_index) and bool(selected) and not bool(disabled):
                    evidence_ids.append(str(control_id))

            controls.append(
                _ControlSpec(
                    control_id=str(control_id),
                    candidate_label=str(label),
                    group_name=str(group_name),
                    group_index=int(group_index),
                    order_in_group=int(order_in_group),
                    global_order_index=int(label_index),
                    command=command_options[int(label_index)],
                    enabled=not bool(disabled),
                    selected=bool(selected),
                    is_reference=bool(is_reference),
                )
            )
            label_index += 1

    if len(evidence_ids) != int(answer_value):
        raise RuntimeError(
            f"GUI counting evidence cardinality does not match answer for {query_id}: "
            f"{len(evidence_ids)} != {answer_value}"
        )

    return _ResolvedQuery(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        controls=tuple(controls),
        group_names=tuple(str(value) for value in group_names),
        target_group_name=str(group_names[int(target_group_index)]),
        target_group_index=int(target_group_index),
        reference_label=str(reference_label),
        answer_value=int(answer_value),
        evidence_control_ids=tuple(str(value) for value in evidence_ids),
        state_count_support=tuple(int(value) for value in answer_support),
        candidate_label_pool=tuple(str(value) for value in candidate_label_pool),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
    )


def _draw_app_chrome(
    draw: ImageDraw.ImageDraw,
    *,
    query: _ResolvedQuery,
    render_params: _RenderParams,
    theme: _Theme,
) -> Tuple[BBox, _AppProfile]:
    profile = _APP_PROFILES[str(query.scene_variant)]
    m = int(render_params.window_margin_px)
    width = int(render_params.canvas_width)
    height = int(render_params.canvas_height)
    window = (float(m), float(m - 6), float(width - m), float(height - m + 6))
    _rounded_rect(draw, window, radius=int(render_params.corner_radius_px), fill=theme.app_fill, outline=theme.chrome_line, width=2)

    title_bar = (window[0], window[1], window[2], window[1] + int(render_params.title_bar_height_px))
    draw.rounded_rectangle(
        [title_bar[0], title_bar[1], title_bar[2], title_bar[3] + int(render_params.corner_radius_px)],
        radius=int(render_params.corner_radius_px),
        fill=theme.title_bar,
    )
    draw.rectangle(
        [title_bar[0], title_bar[3] - int(render_params.corner_radius_px), title_bar[2], title_bar[3]],
        fill=theme.title_bar,
    )
    dot_y = (title_bar[1] + title_bar[3]) / 2.0
    for idx, color in enumerate(((221, 91, 84), (229, 174, 65), (88, 174, 104))):
        draw.ellipse([window[0] + 18 + idx * 22, dot_y - 6, window[0] + 30 + idx * 22, dot_y + 6], fill=color)
    title_font = load_font(int(render_params.title_font_size_px), bold=True)
    draw.text((window[0] + 98, title_bar[1] + 10), str(profile.app_title), fill=theme.title_text, font=title_font)
    small_font = load_font(int(render_params.small_font_size_px), bold=False)
    draw.text((window[2] - 255, title_bar[1] + 16), str(profile.window_title), fill=theme.title_text, font=small_font)

    menu_y1 = title_bar[3]
    menu_y2 = menu_y1 + int(render_params.menu_bar_height_px)
    draw.rectangle([window[0], menu_y1, window[2], menu_y2], fill=theme.panel_fill, outline=theme.chrome_line)
    tab_font = load_font(int(render_params.small_font_size_px), bold=True)
    tab_x = window[0] + 26
    for idx, tab in enumerate(("File", str(profile.primary_tab), str(profile.secondary_tab), "View", "Help")):
        fill = theme.accent if idx == 1 else theme.muted_text
        draw.text((tab_x, menu_y1 + 9), tab, fill=fill, font=tab_font)
        tab_x += 86 if idx else 64

    content_bbox = (window[0] + 22, menu_y2 + 18, window[2] - 22, window[3] - 18)
    return content_bbox, profile


def _draw_mini_icon(
    draw: ImageDraw.ImageDraw,
    *,
    kind: str,
    bbox: BBox,
    stroke: Color,
    accent: Color,
    disabled: bool,
) -> None:
    x1, y1, x2, y2 = [float(value) for value in bbox]
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    color = stroke
    accent_color = accent if not bool(disabled) else stroke
    selector = int(abs(hash64(0, str(kind), 19)) % 6)
    if selector == 0:
        draw.rectangle([x1 + 5, y1 + 6, x2 - 5, y2 - 6], outline=color, width=2)
        draw.line([(x1 + 9, cy), (x2 - 9, cy)], fill=accent_color, width=2)
    elif selector == 1:
        draw.ellipse([x1 + 5, y1 + 5, x2 - 9, y2 - 9], outline=color, width=2)
        draw.line([(cx + 6, cy + 6), (x2 - 4, y2 - 4)], fill=accent_color, width=2)
    elif selector == 2:
        draw.polygon([(cx, y1 + 4), (x2 - 5, cy), (cx, y2 - 4), (x1 + 5, cy)], outline=color)
        draw.line([(x1 + 10, cy), (x2 - 10, cy)], fill=accent_color, width=2)
    elif selector == 3:
        draw.line([(x1 + 7, y2 - 7), (x2 - 7, y1 + 7)], fill=color, width=2)
        draw.line([(x1 + 10, y1 + 10), (x2 - 10, y1 + 10)], fill=accent_color, width=2)
        draw.line([(x1 + 10, y2 - 10), (x2 - 10, y2 - 10)], fill=accent_color, width=2)
    elif selector == 4:
        for idx in range(3):
            yy = y1 + 9 + idx * 9
            draw.line([(x1 + 7, yy), (x2 - 7, yy)], fill=color if idx != 1 else accent_color, width=2)
    else:
        draw.arc([x1 + 6, y1 + 6, x2 - 6, y2 - 6], start=35, end=320, fill=color, width=2)
        draw.polygon([(x2 - 11, y1 + 10), (x2 - 5, y1 + 6), (x2 - 7, y1 + 16)], fill=accent_color)


def _draw_candidate_badge(
    draw: ImageDraw.ImageDraw,
    *,
    control_bbox: BBox,
    label: str,
    render_params: _RenderParams,
    theme: _Theme,
) -> List[float]:
    size = max(20, int(render_params.badge_size_px))
    x1, y1, _x2, _y2 = [float(value) for value in control_bbox]
    badge = (x1 + 7.0, y1 + 7.0, x1 + 7.0 + float(size), y1 + 7.0 + float(size))
    draw.ellipse([float(value) for value in badge], fill=theme.badge_fill, outline=(255, 255, 255), width=2)
    font = fit_font_to_box(
        draw,
        text=str(label),
        max_width=float(size) * 0.72,
        max_height=float(size) * 0.70,
        bold=True,
        min_size_px=9,
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
    theme: _Theme,
) -> None:
    disabled = not bool(control.enabled)
    selected = bool(control.selected)
    fill = theme.disabled_fill if disabled else (theme.selected_fill if selected else theme.control_fill)
    outline = theme.disabled_outline if disabled else (theme.selected_outline if selected else theme.control_outline)
    width = 3 if selected or bool(control.is_reference) else int(render_params.control_outline_width_px)
    _rounded_rect(
        draw,
        bbox,
        radius=int(render_params.control_corner_radius_px),
        fill=fill,
        outline=outline,
        width=int(width),
    )
    x1, y1, x2, y2 = [float(value) for value in bbox]
    icon_box = (x1 + 12.0, y1 + 34.0, x1 + 46.0, y1 + 68.0)
    text_fill = theme.muted_text if disabled else theme.control_text
    _draw_mini_icon(
        draw,
        kind=str(control.command.icon_kind),
        bbox=icon_box,
        stroke=text_fill,
        accent=theme.accent,
        disabled=bool(disabled),
    )
    _draw_text_left(
        draw,
        text=str(control.command.display_text),
        bbox=(x1 + 54.0, y1 + 37.0, x2 - 12.0, y1 + 65.0),
        fill=text_fill,
        max_size_px=int(render_params.small_font_size_px + 2),
        bold=False,
    )
    if disabled:
        draw.line([(x1 + 10.0, y2 - 11.0), (x2 - 10.0, y1 + 11.0)], fill=theme.disabled_outline, width=3)
    if selected:
        mark_x = x2 - 30.0
        mark_y = y1 + 14.0
        draw.line([(mark_x, mark_y + 8.0), (mark_x + 7.0, mark_y + 15.0), (mark_x + 20.0, mark_y)], fill=theme.selected_outline, width=3)
    if bool(control.is_reference):
        draw.rectangle([x1 + 3.0, y1 + 3.0, x2 - 3.0, y2 - 3.0], outline=theme.accent_alt, width=2)


def _render_gui_count_scene(
    image: Image.Image,
    *,
    query: _ResolvedQuery,
    render_params: _RenderParams,
) -> _RenderedScene:
    draw = ImageDraw.Draw(image)
    theme = _theme(str(query.style_variant))
    content_bbox, profile = _draw_app_chrome(draw, query=query, render_params=render_params, theme=theme)
    x1, y1, x2, y2 = [float(value) for value in content_bbox]

    title_bar = (x1 + 18.0, y1 + 10.0, x2 - 18.0, y1 + 52.0)
    _rounded_rect(draw, title_bar, radius=10, fill=theme.panel_alt_fill, outline=theme.chrome_line, width=1)
    _draw_text_left(
        draw,
        text=str(profile.workspace_title),
        bbox=(title_bar[0] + 18.0, title_bar[1] + 8.0, title_bar[0] + 360.0, title_bar[3] - 8.0),
        fill=theme.control_text,
        max_size_px=int(render_params.body_font_size_px),
        bold=True,
    )
    status_font = load_font(int(render_params.small_font_size_px), bold=False)
    draw.text((title_bar[2] - 150.0, title_bar[1] + 14.0), str(profile.status_text), fill=theme.muted_text, font=status_font)

    board = (x1 + 18.0, title_bar[3] + 14.0, x2 - 18.0, y2 - 16.0)
    group_gap = 18.0
    group_w = (board[2] - board[0] - group_gap) / 2.0
    group_h = (board[3] - board[1] - group_gap) / 2.0
    group_bboxes: Dict[str, List[float]] = {}
    control_bboxes: Dict[str, List[float]] = {}
    badge_bboxes: Dict[str, List[float]] = {}

    controls_by_group: Dict[str, List[_ControlSpec]] = {str(name): [] for name in query.group_names}
    for control in query.controls:
        controls_by_group[str(control.group_name)].append(control)

    group_font = load_font(int(render_params.body_font_size_px), bold=True)
    count_font = load_font(int(render_params.small_font_size_px), bold=False)
    for group_index, group_name in enumerate(query.group_names):
        row = int(group_index) // 2
        col = int(group_index) % 2
        gx1 = board[0] + col * (group_w + group_gap)
        gy1 = board[1] + row * (group_h + group_gap)
        group_bbox = (gx1, gy1, gx1 + group_w, gy1 + group_h)
        panel_fill = theme.panel_alt_fill if group_index % 2 == 0 else theme.panel_fill
        _rounded_rect(draw, group_bbox, radius=12, fill=panel_fill, outline=theme.chrome_line, width=1)
        draw.text((gx1 + 18.0, gy1 + 14.0), str(group_name), fill=theme.control_text, font=group_font)
        draw.text((group_bbox[2] - 92.0, gy1 + 18.0), f"{len(controls_by_group[str(group_name)])} controls", fill=theme.muted_text, font=count_font)
        group_bboxes[str(group_name)] = _bbox_list(group_bbox)

        controls = controls_by_group[str(group_name)]
        cols = 4
        gap = 10.0
        pad_x = 17.0
        control_w = (group_w - (2 * pad_x) - (gap * (cols - 1))) / float(cols)
        control_h = 82.0
        start_y = gy1 + 55.0
        for local_index, control in enumerate(controls):
            c_row = int(local_index) // cols
            c_col = int(local_index) % cols
            cx1 = gx1 + pad_x + c_col * (control_w + gap)
            cy1 = start_y + c_row * (control_h + gap)
            bbox = (cx1, cy1, cx1 + control_w, cy1 + control_h)
            _draw_control(draw, bbox=bbox, control=control, render_params=render_params, theme=theme)
            badge_bboxes[str(control.control_id)] = _draw_candidate_badge(
                draw,
                control_bbox=bbox,
                label=str(control.candidate_label),
                render_params=render_params,
                theme=theme,
            )
            control_bboxes[str(control.control_id)] = _bbox_list(bbox)

    control_records: List[Dict[str, Any]] = []
    for control in query.controls:
        control_records.append(
            {
                "control_id": str(control.control_id),
                "candidate_label": str(control.candidate_label),
                "group_name": str(control.group_name),
                "group_index": int(control.group_index),
                "order_in_group": int(control.order_in_group),
                "global_order_index": int(control.global_order_index),
                "command_key": str(control.command.command_key),
                "display_text": str(control.command.display_text),
                "icon_kind": str(control.command.icon_kind),
                "enabled": bool(control.enabled),
                "selected": bool(control.selected),
                "is_reference": bool(control.is_reference),
                "bbox_px": list(control_bboxes[str(control.control_id)]),
                "candidate_label_bbox_px": list(badge_bboxes[str(control.control_id)]),
            }
        )

    m = int(render_params.window_margin_px)
    window_bbox = [float(m), float(m - 6), float(render_params.canvas_width - m), float(render_params.canvas_height - m + 6)]
    return _RenderedScene(
        control_bboxes_by_id={str(key): list(value) for key, value in control_bboxes.items()},
        badge_bboxes_by_id={str(key): list(value) for key, value in badge_bboxes.items()},
        group_bboxes_by_name={str(key): list(value) for key, value in group_bboxes.items()},
        control_records=tuple(control_records),
        scene_bbox_px=[0.0, 0.0, float(render_params.canvas_width), float(render_params.canvas_height)],
        window_bbox_px=_bbox_list(tuple(window_bbox)),
        profile=profile,
        theme=theme,
    )


def _prompt_json_examples() -> Tuple[str, str]:
    answer_and_evidence = {"evidence": [[96, 218, 221, 300], [233, 218, 358, 300], [370, 310, 495, 392]], "answer": 3}
    answer_only = {"answer": 3}
    return (
        json.dumps(answer_and_evidence, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
    )


def _build_complexity(query: _ResolvedQuery) -> TaskComplexity:
    if not _COMPLEXITY_WEIGHTS:
        raise ValueError(f"missing positive complexity criteria weights for {TASK_ID}")
    total_controls = len(query.controls)
    scan = (float(total_controls) - 16.0) / 10.0
    if str(query.query_id) == "selected_enabled_controls_in_group_count":
        state_filtering = 0.86
        grouping = 0.58
    else:
        state_filtering = 0.72
        grouping = 0.56
    output_burden = min(1.0, float(len(query.evidence_control_ids)) / 8.0)
    components = {
        "visual_scan": _clamp_unit(scan),
        "state_filtering": _clamp_unit(state_filtering + (0.06 * output_burden)),
        "grouping": _clamp_unit(grouping),
        "output_burden": _clamp_unit(output_burden),
    }
    missing = [key for key in _COMPLEXITY_WEIGHTS if key not in components]
    if missing:
        raise ValueError(f"GUI counting complexity is missing active criteria: {missing}")
    total_weight = sum(float(value) for value in _COMPLEXITY_WEIGHTS.values())
    score = sum(float(_COMPLEXITY_WEIGHTS[key]) * float(components[key]) for key in _COMPLEXITY_WEIGHTS) / float(total_weight)
    return TaskComplexity(
        complexity_score=_clamp_unit(score),
        complexity_components={str(key): float(_clamp_unit(components[str(key)])) for key in _COMPLEXITY_WEIGHTS},
    )


class GuiCountingControlFilterCountTask:
    """Count GUI controls that satisfy one visible state or grouping condition."""

    task_id = TASK_ID
    domain = "pages"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query = _resolve_query(int(instance_seed), params=params)
        render_params = resolve_gui_window_render_params(
            params,
            defaults=_DEFAULTS,
            render_defaults=_RENDER_DEFAULTS,
            task_id=TASK_ID,
            render_params_cls=_RenderParams,
            instance_seed=int(instance_seed),
        )
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        image = background.copy().convert("RGB")
        rendered = _render_gui_count_scene(image, query=query, render_params=render_params)
        image, post_noise_meta = apply_post_image_noise(
            image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        evidence_bboxes = [
            list(rendered.control_bboxes_by_id[str(control_id)])
            for control_id in query.evidence_control_ids
        ]
        answer_gt = TypedValue(type="integer", value=int(query.answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        prompt_defaults_source = dict(_PROMPT_DEFAULTS)
        prompt_defaults_override = params.get("_prompt_defaults_override")
        if isinstance(prompt_defaults_override, Mapping):
            prompt_defaults_source.update(dict(prompt_defaults_override))
        prompt_defaults = required_group_defaults(
            prompt_defaults_source,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "object_description",
                "json_output_contract",
                "json_output_contract_answer_only",
                "evidence_hint",
                "answer_hint",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _prompt_json_examples()
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "group_name": str(query.target_group_name),
                "reference_label": str(query.reference_label),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        group_records: List[Dict[str, Any]] = []
        for group_index, group_name in enumerate(query.group_names):
            members = [
                str(control.control_id)
                for control in query.controls
                if int(control.group_index) == int(group_index)
            ]
            group_records.append(
                {
                    "group_name": str(group_name),
                    "group_index": int(group_index),
                    "control_ids": list(members),
                    "bbox_px": list(rendered.group_bboxes_by_name[str(group_name)]),
                }
            )
        control_records = [dict(record) for record in rendered.control_records]
        matched_records = [
            dict(record)
            for record in control_records
            if str(record["control_id"]) in set(str(value) for value in query.evidence_control_ids)
        ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": "gui_grouped_control_board",
                "entities": [
                    {
                        "entity_id": str(record["control_id"]),
                        "entity_type": "gui_control",
                        "attrs": {
                            "candidate_label": str(record["candidate_label"]),
                            "group_name": str(record["group_name"]),
                            "group_index": int(record["group_index"]),
                            "order_in_group": int(record["order_in_group"]),
                            "global_order_index": int(record["global_order_index"]),
                            "command_key": str(record["command_key"]),
                            "display_text": str(record["display_text"]),
                            "icon_kind": str(record["icon_kind"]),
                            "enabled": bool(record["enabled"]),
                            "selected": bool(record["selected"]),
                            "is_reference": bool(record["is_reference"]),
                            "bbox_px": list(record["bbox_px"]),
                        },
                    }
                    for record in control_records
                ],
                "relations": {
                    "query_id": str(query.query_id),
                    "scene_variant": str(query.scene_variant),
                    "style_variant": str(query.style_variant),
                    "target_group_name": str(query.target_group_name),
                    "target_group_index": int(query.target_group_index),
                    "reference_label": str(query.reference_label),
                    "answer_value": int(query.answer_value),
                    "evidence_control_ids": [str(value) for value in query.evidence_control_ids],
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
                    "target_group_name": str(query.target_group_name),
                    "reference_label": str(query.reference_label),
                    "answer_value": int(query.answer_value),
                    "state_count_support": [int(value) for value in query.state_count_support],
                    "candidate_label_pool": [str(value) for value in query.candidate_label_pool],
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
                "window_bbox_px": list(rendered.window_bbox_px),
                "scene_bbox_px": list(rendered.scene_bbox_px),
                "render_params": asdict(render_params),
                "theme": {
                    "name": str(rendered.theme.name),
                    "accent_rgb": [int(value) for value in rendered.theme.accent],
                    "accent_alt_rgb": [int(value) for value in rendered.theme.accent_alt],
                    "selected_outline_rgb": [int(value) for value in rendered.theme.selected_outline],
                    "disabled_fill_rgb": [int(value) for value in rendered.theme.disabled_fill],
                    "badge_fill_rgb": [int(value) for value in rendered.theme.badge_fill],
                },
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered.scene_bbox_px),
                "window_bbox_px": list(rendered.window_bbox_px),
                "app_profile": asdict(rendered.profile),
                "group_bboxes_by_name": dict(rendered.group_bboxes_by_name),
                "control_bboxes_by_id": dict(rendered.control_bboxes_by_id),
                "candidate_label_badge_bboxes_by_id": dict(rendered.badge_bboxes_by_id),
                "evidence_control_ids": [str(value) for value in query.evidence_control_ids],
            },
            "execution_trace": {
                "query_id": str(query.query_id),
                "scene_variant": str(query.scene_variant),
                "style_variant": str(query.style_variant),
                "answer_value": int(query.answer_value),
                "target_group_name": str(query.target_group_name),
                "target_group_index": int(query.target_group_index),
                "reference_label": str(query.reference_label),
                "group_records": list(group_records),
                "controls": list(control_records),
                "matching_control_ids": [str(value) for value in query.evidence_control_ids],
                "matching_controls": list(matched_records),
                "total_control_count": int(len(query.controls)),
                "query_id_probabilities": dict(query.query_id_probabilities),
                "scene_variant_probabilities": dict(query.scene_variant_probabilities),
                "style_variant_probabilities": dict(query.style_variant_probabilities),
                "question_format": "gui_control_filter_count",
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "evidence_control_ids": [str(value) for value in query.evidence_control_ids],
                "value": list(evidence_bboxes),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
            },
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(query),
            task_versions=default_task_versions(),
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GuiCountingControlFilterCountTask", "SUPPORTED_QUERY_IDS"]
