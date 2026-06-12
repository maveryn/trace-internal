"""Synthetic GUI navigation-path target task."""

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
from ...shared.text_rendering import load_font
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ...shared.text_legibility import draw_text_traced
from ..shared.gui_render_params import resolve_gui_window_render_params
from trace.tasks.shared.fixed_query import FixedPagesQueryTaskMixin
from ..shared.public_query_task import rewrite_pages_query_output
from .gui_relation_common import (
    SUPPORTED_SCENE_VARIANTS,
    SUPPORTED_STYLE_VARIANTS,
    _bbox_list,
    _clamp_unit,
    _draw_app_chrome,
    _draw_badge,
    _draw_control_button,
    _draw_text_center_fit,
    _draw_text_left,
    _normalize_str_support,
    _rounded_rect,
    _theme,
)


TASK_ID = "pages_navigation_flow_path_target_source"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "menu_path_target_label",
    "sidebar_tree_target_label",
    "ribbon_group_command_label",
)
_BALANCE_SALT = 72119
_NAV_COMMAND_SYMBOLS: Tuple[str, ...] = ("@", "%", "&", "#")
_SIDEBAR_ITEM_SYMBOLS: Tuple[str, ...] = ("@", "%", "&", "#")

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
    badge_size_px: int = 24
    title_font_size_px: int = 24
    body_font_size_px: int = 16
    small_font_size_px: int = 13
    label_font_size_px: int = 16
    candidate_label_pool: Tuple[str, ...] = tuple(chr(ord("A") + idx) for idx in range(26))
    nav_menu_pool: Tuple[str, ...] = ("File", "Edit", "View")
    nav_submenu_pool: Tuple[str, ...] = ("Arrange", "Inspect")
    nav_menu_group_pool: Tuple[str, ...] = ("Primary", "Advanced")
    nav_command_pool: Tuple[str, ...] = ("Align", "Duplicate", "Export", "Preview")
    nav_sidebar_section_pool: Tuple[str, ...] = ("Workspace", "Assets", "Settings", "Reports")
    nav_sidebar_group_pool: Tuple[str, ...] = ("Pinned", "Recent", "Shared")
    nav_sidebar_item_pool: Tuple[str, ...] = ("Overview", "Timeline", "Details")
    nav_ribbon_tab_pool: Tuple[str, ...] = ("Home", "Insert", "Review", "Analyze", "Share")
    nav_ribbon_group_pool: Tuple[str, ...] = ("Arrange", "Inspect", "Publish")
    nav_ribbon_command_pool: Tuple[str, ...] = ("Compare", "Filter", "Attach", "Sync")


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
class _ControlSpec:
    control_id: str
    candidate_label: str
    role: str
    display_text: str
    nav_kind: str
    path_keys: Tuple[str, ...]
    order_index: int


@dataclass(frozen=True)
class _ResolvedQuery:
    query_id: str
    scene_variant: str
    style_variant: str
    controls: Tuple[_ControlSpec, ...]
    target_control_id: str
    target_label: str
    path_labels: Tuple[str, ...]
    path_display: str
    command_label: str
    menu_command_count: int
    menu_command_count_range: Tuple[int, int]
    ribbon_tab_count: int
    ribbon_tab_count_range: Tuple[int, int]
    ribbon_group_count: int
    ribbon_group_count_range: Tuple[int, int]
    ribbon_command_count: int
    ribbon_command_count_range: Tuple[int, int]
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
    window_bbox_px: List[float]
    profile: Any
    theme: Any


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


def _decoupled_params(params: Mapping[str, Any], *, divisor: int, namespace: str) -> Mapping[str, Any]:
    _ = int(divisor), namespace
    return params


def _support_selection_index(params: Mapping[str, Any], *, instance_seed: int, namespace: str) -> int:
    return int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:{namespace}"))


def _resolve_axis_bounds(
    params: Mapping[str, Any],
    *,
    exact_key: str,
    min_key: str,
    max_key: str,
    fallback_exact: int,
    fallback_min: int,
    fallback_max: int,
) -> Tuple[int, int]:
    if str(exact_key) in params or str(exact_key) in _GEN_DEFAULTS:
        value = int(params.get(str(exact_key), group_default(_GEN_DEFAULTS, str(exact_key), int(fallback_exact))))
        return int(value), int(value)
    min_value = int(params.get(str(min_key), group_default(_GEN_DEFAULTS, str(min_key), int(fallback_min))))
    max_value = int(params.get(str(max_key), group_default(_GEN_DEFAULTS, str(max_key), int(fallback_max))))
    if int(min_value) > int(max_value):
        raise ValueError(f"{min_key} must be <= {max_key} for {TASK_ID}")
    return int(min_value), int(max_value)


def _resolve_menu_command_count(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    candidate_label_capacity: int,
) -> Tuple[int, Tuple[int, int]]:
    min_value, max_value = _resolve_axis_bounds(
        params,
        exact_key="menu_command_count",
        min_key="menu_command_count_min",
        max_key="menu_command_count_max",
        fallback_exact=2,
        fallback_min=2,
        fallback_max=2,
    )
    candidates = [
        int(value)
        for value in range(int(min_value), int(max_value) + 1)
        if 2 * 2 * 2 * int(value) <= int(candidate_label_capacity)
    ]
    if not candidates:
        raise ValueError(
            "menu command count requires more unique candidate labels than available "
            f"for {TASK_ID}: 2x2x2x{min_value}..{max_value} > {candidate_label_capacity}"
        )
    selected_index = _support_selection_index(params, instance_seed=int(instance_seed), namespace="menu_command_count") % len(candidates)
    return int(candidates[int(selected_index)]), (int(min_value), int(max_value))


def _resolve_ribbon_counts(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    candidate_label_capacity: int,
) -> Tuple[int, Tuple[int, int], int, Tuple[int, int], int, Tuple[int, int]]:
    tab_min, tab_max = _resolve_axis_bounds(
        params,
        exact_key="ribbon_tab_count",
        min_key="ribbon_tab_count_min",
        max_key="ribbon_tab_count_max",
        fallback_exact=3,
        fallback_min=3,
        fallback_max=3,
    )
    group_min, group_max = _resolve_axis_bounds(
        params,
        exact_key="ribbon_group_count",
        min_key="ribbon_group_count_min",
        max_key="ribbon_group_count_max",
        fallback_exact=2,
        fallback_min=2,
        fallback_max=2,
    )
    command_min, command_max = _resolve_axis_bounds(
        params,
        exact_key="ribbon_command_count",
        min_key="ribbon_command_count_min",
        max_key="ribbon_command_count_max",
        fallback_exact=2,
        fallback_min=2,
        fallback_max=2,
    )
    candidates = [
        (int(tab_count), int(group_count), int(command_count))
        for tab_count in range(int(tab_min), int(tab_max) + 1)
        for group_count in range(int(group_min), int(group_max) + 1)
        for command_count in range(int(command_min), int(command_max) + 1)
        if int(tab_count) * int(group_count) * int(command_count) <= int(candidate_label_capacity)
    ]
    if not candidates:
        raise ValueError(
            "ribbon tab/group/command counts require more unique candidate labels than available "
            f"for {TASK_ID}: {tab_min}..{tab_max} x {group_min}..{group_max} x "
            f"{command_min}..{command_max} > {candidate_label_capacity}"
        )
    selected_index = _support_selection_index(params, instance_seed=int(instance_seed), namespace="ribbon_count_tuple") % len(candidates)
    tab_count, group_count, command_count = candidates[int(selected_index)]
    return (
        int(tab_count),
        (int(tab_min), int(tab_max)),
        int(group_count),
        (int(group_min), int(group_max)),
        int(command_count),
        (int(command_min), int(command_max)),
    )


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


def _base_control_specs(
    *,
    query_id: str,
    menus: Sequence[str],
    submenus: Sequence[str],
    menu_groups: Sequence[str],
    menu_commands: Sequence[str],
    sidebar_sections: Sequence[str],
    sidebar_groups: Sequence[str],
    sidebar_items: Sequence[str],
    ribbon_tabs: Sequence[str],
    ribbon_groups: Sequence[str],
    ribbon_commands: Sequence[str],
) -> Tuple[_ControlSpec, ...]:
    controls: List[_ControlSpec] = []
    order = 0
    if str(query_id) == "menu_path_target_label":
        for menu_index, menu in enumerate(menus):
            for submenu_index, submenu in enumerate(submenus):
                for group_index, group in enumerate(menu_groups):
                    for command_index, command in enumerate(menu_commands):
                        controls.append(
                            _ControlSpec(
                                control_id=f"menu_{menu_index:02d}_{submenu_index:02d}_{group_index:02d}_{command_index:02d}",
                                candidate_label="",
                                role="menu_item",
                                display_text=str(_NAV_COMMAND_SYMBOLS[int(command_index) % len(_NAV_COMMAND_SYMBOLS)]),
                                nav_kind="menu_path",
                                path_keys=(str(menu), str(submenu), str(group), str(command)),
                                order_index=int(order),
                            )
                        )
                        order += 1
        return tuple(controls)
    if str(query_id) == "sidebar_tree_target_label":
        for section_index, section in enumerate(sidebar_sections):
            for group_index, group in enumerate(sidebar_groups):
                for item_index, item in enumerate(sidebar_items):
                    controls.append(
                        _ControlSpec(
                            control_id=f"sidebar_{section_index:02d}_{group_index:02d}_{item_index:02d}",
                            candidate_label="",
                            role="sidebar_tree_item",
                            display_text=str(_SIDEBAR_ITEM_SYMBOLS[int(item_index) % len(_SIDEBAR_ITEM_SYMBOLS)]),
                            nav_kind="sidebar_tree",
                            path_keys=(str(section), str(group), str(item)),
                            order_index=int(order),
                        )
                    )
                    order += 1
        return tuple(controls)
    for tab_index, tab in enumerate(ribbon_tabs):
        for group_index, group in enumerate(ribbon_groups):
            for command_index, command in enumerate(ribbon_commands):
                controls.append(
                    _ControlSpec(
                        control_id=f"ribbon_{tab_index:02d}_{group_index:02d}_{command_index:02d}",
                        candidate_label="",
                        role="ribbon_command",
                        display_text=str(_NAV_COMMAND_SYMBOLS[int(command_index) % len(_NAV_COMMAND_SYMBOLS)]),
                        nav_kind="ribbon_group",
                        path_keys=(str(tab), str(group), str(command)),
                        order_index=int(order),
                    )
                )
                order += 1
    return tuple(controls)


def _with_candidate_labels(
    controls: Sequence[_ControlSpec],
    *,
    target_control_id: str,
    target_label: str,
    candidate_label_pool: Sequence[str],
    instance_seed: int,
) -> Tuple[_ControlSpec, ...]:
    if len(controls) > len(candidate_label_pool):
        raise ValueError("candidate_label_pool must cover all navigation controls")
    remaining_labels = [str(value) for value in candidate_label_pool if str(value) != str(target_label)]
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.candidate_labels")
    rng.shuffle(remaining_labels)
    assigned: List[_ControlSpec] = []
    cursor = 0
    for control in controls:
        label = str(target_label) if str(control.control_id) == str(target_control_id) else str(remaining_labels[int(cursor)])
        if str(control.control_id) != str(target_control_id):
            cursor += 1
        assigned.append(
            _ControlSpec(
                control_id=str(control.control_id),
                candidate_label=str(label),
                role=str(control.role),
                display_text=str(control.display_text),
                nav_kind=str(control.nav_kind),
                path_keys=tuple(str(value) for value in control.path_keys),
                order_index=int(control.order_index),
            )
        )
    return tuple(assigned)


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
    candidate_label_pool = _normalize_str_support(params, "candidate_label_pool", _DEFAULTS.candidate_label_pool)
    menus = _normalize_str_support(params, "nav_menu_pool", _DEFAULTS.nav_menu_pool)[:2]
    submenus = _normalize_str_support(params, "nav_submenu_pool", _DEFAULTS.nav_submenu_pool)[:2]
    menu_groups = _normalize_str_support(params, "nav_menu_group_pool", _DEFAULTS.nav_menu_group_pool)[:2]
    menu_command_count, menu_command_count_range = _resolve_menu_command_count(
        params,
        instance_seed=int(instance_seed),
        candidate_label_capacity=len(candidate_label_pool),
    )
    menu_commands = _normalize_str_support(params, "nav_command_pool", _DEFAULTS.nav_command_pool)[: int(menu_command_count)]
    sidebar_sections = _normalize_str_support(params, "nav_sidebar_section_pool", _DEFAULTS.nav_sidebar_section_pool)[:3]
    sidebar_groups = _normalize_str_support(params, "nav_sidebar_group_pool", _DEFAULTS.nav_sidebar_group_pool)[:2]
    sidebar_items = _normalize_str_support(params, "nav_sidebar_item_pool", _DEFAULTS.nav_sidebar_item_pool)[:2]
    (
        ribbon_tab_count,
        ribbon_tab_count_range,
        ribbon_group_count,
        ribbon_group_count_range,
        ribbon_command_count,
        ribbon_command_count_range,
    ) = _resolve_ribbon_counts(
        params,
        instance_seed=int(instance_seed),
        candidate_label_capacity=len(candidate_label_pool),
    )
    ribbon_tabs = _normalize_str_support(params, "nav_ribbon_tab_pool", _DEFAULTS.nav_ribbon_tab_pool)[: int(ribbon_tab_count)]
    ribbon_groups = _normalize_str_support(params, "nav_ribbon_group_pool", _DEFAULTS.nav_ribbon_group_pool)[: int(ribbon_group_count)]
    ribbon_commands = _normalize_str_support(params, "nav_ribbon_command_pool", _DEFAULTS.nav_ribbon_command_pool)[: int(ribbon_command_count)]
    if (
        len(menus) < 2
        or len(submenus) < 2
        or len(menu_groups) < 2
        or len(menu_commands) < 2
        or len(sidebar_sections) < 3
        or len(sidebar_groups) < 2
        or len(sidebar_items) < 2
        or len(ribbon_tabs) < 3
        or len(ribbon_groups) < 2
        or len(ribbon_commands) < 2
    ):
        raise ValueError("GUI navigation pools are too small for the active scene")
    controls_without_labels = _base_control_specs(
        query_id=str(query_id),
        menus=menus,
        submenus=submenus,
        menu_groups=menu_groups,
        menu_commands=menu_commands,
        sidebar_sections=sidebar_sections,
        sidebar_groups=sidebar_groups,
        sidebar_items=sidebar_items,
        ribbon_tabs=ribbon_tabs,
        ribbon_groups=ribbon_groups,
        ribbon_commands=ribbon_commands,
    )
    target_index = _support_selection_index(params, instance_seed=int(instance_seed), namespace=f"target.{query_id}") % len(controls_without_labels)
    target = controls_without_labels[int(target_index)]
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
        controls_without_labels,
        target_control_id=str(target.control_id),
        target_label=str(target_label),
        candidate_label_pool=candidate_label_pool,
        instance_seed=int(instance_seed),
    )
    path_labels = tuple(str(value) for value in target.path_keys)
    return _ResolvedQuery(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        controls=tuple(controls),
        target_control_id=str(target.control_id),
        target_label=str(target_label),
        path_labels=path_labels,
        path_display=" > ".join(path_labels),
        command_label=str(path_labels[-1]),
        menu_command_count=int(menu_command_count),
        menu_command_count_range=tuple(int(value) for value in menu_command_count_range),
        ribbon_tab_count=int(ribbon_tab_count),
        ribbon_tab_count_range=tuple(int(value) for value in ribbon_tab_count_range),
        ribbon_group_count=int(ribbon_group_count),
        ribbon_group_count_range=tuple(int(value) for value in ribbon_group_count_range),
        ribbon_command_count=int(ribbon_command_count),
        ribbon_command_count_range=tuple(int(value) for value in ribbon_command_count_range),
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
) -> None:
    support_bboxes[str(support_id)] = _bbox_list(bbox)
    support_records.append(
        {
            "support_id": str(support_id),
            "support_kind": str(support_kind),
            "display_text": str(display_text),
            "bbox_px": _bbox_list(bbox),
        }
    )


def _draw_menu_path_scene(
    draw: ImageDraw.ImageDraw,
    *,
    query: _ResolvedQuery,
    workspace: BBox,
    render_params: _RenderParams,
    theme: Any,
    control_bboxes: Dict[str, List[float]],
    badge_bboxes: Dict[str, List[float]],
    support_bboxes: Dict[str, List[float]],
    support_records: List[Dict[str, Any]],
) -> None:
    header_font = load_font(int(render_params.body_font_size_px), bold=True)
    draw_text_traced(draw,(workspace[0] + 18.0, workspace[1] + 14.0), "Menu Navigator", fill=theme.control_text, font=header_font, role="readout", required=False)
    controls_by_menu: Dict[str, List[_ControlSpec]] = {}
    for control in query.controls:
        controls_by_menu.setdefault(str(control.path_keys[0]), []).append(control)
    command_symbols: Dict[str, str] = {}
    for control in query.controls:
        command_symbols.setdefault(str(control.path_keys[-1]), str(control.display_text))
    legend_items = list(command_symbols.items())[:4]
    legend_x1 = workspace[0] + 250.0
    legend_x2 = workspace[2] - 18.0
    legend_y1 = workspace[1] + 12.0
    legend_w = (legend_x2 - legend_x1) / max(1, len(legend_items))
    for legend_index, (command, symbol) in enumerate(legend_items):
        legend_bbox = (
            legend_x1 + legend_index * legend_w,
            legend_y1,
            legend_x1 + (legend_index + 1) * legend_w - 8.0,
            legend_y1 + 36.0,
        )
        _rounded_rect(draw, legend_bbox, radius=8, fill=theme.panel_alt_fill, outline=theme.chrome_line)
        _draw_text_center_fit(
            draw,
            text=f"{symbol} {command}",
            bbox=(legend_bbox[0] + 6.0, legend_bbox[1] + 4.0, legend_bbox[2] - 6.0, legend_bbox[3] - 4.0),
            fill=theme.control_text,
            max_size_px=int(render_params.small_font_size_px),
            bold=True,
        )
    menus = list(controls_by_menu.keys())
    menu_x1 = workspace[0] + 18.0
    menu_y1 = workspace[1] + 58.0
    menu_h = 38.0
    menu_w = (workspace[2] - workspace[0] - 36.0) / float(len(menus))
    body_y1 = menu_y1 + menu_h + 12.0
    for menu_index, menu in enumerate(menus):
        mx1 = menu_x1 + menu_index * menu_w
        menu_bbox = (mx1, menu_y1, mx1 + menu_w - 10.0, menu_y1 + menu_h)
        _rounded_rect(draw, menu_bbox, radius=8, fill=theme.selected_fill if menu_index % 2 == 0 else theme.panel_alt_fill, outline=theme.chrome_line)
        _draw_text_center_fit(draw, text=str(menu), bbox=(menu_bbox[0] + 8.0, menu_bbox[1] + 5.0, menu_bbox[2] - 8.0, menu_bbox[3] - 5.0), fill=theme.control_text, max_size_px=int(render_params.small_font_size_px), bold=True)
        _add_support(support_bboxes, support_records, f"support_menu_{menu_index}", "menu_root", str(menu), menu_bbox)
        submenu_groups: Dict[str, List[_ControlSpec]] = {}
        for control in controls_by_menu[str(menu)]:
            submenu_groups.setdefault(str(control.path_keys[1]), []).append(control)
        submenu_items = list(submenu_groups.items())
        panel_bbox = (mx1, body_y1, mx1 + menu_w - 10.0, workspace[3] - 18.0)
        _rounded_rect(draw, panel_bbox, radius=8, fill=theme.control_fill, outline=theme.chrome_line)
        sub_h = (panel_bbox[3] - panel_bbox[1] - 22.0) / float(len(submenu_items))
        for submenu_index, (submenu, controls) in enumerate(submenu_items):
            sy1 = panel_bbox[1] + 12.0 + submenu_index * sub_h
            submenu_bbox = (panel_bbox[0] + 12.0, sy1, panel_bbox[2] - 12.0, sy1 + 28.0)
            _rounded_rect(draw, submenu_bbox, radius=7, fill=theme.panel_alt_fill, outline=theme.chrome_line)
            _draw_text_left(draw, text=str(submenu), bbox=(submenu_bbox[0] + 10.0, submenu_bbox[1] + 4.0, submenu_bbox[2] - 10.0, submenu_bbox[3] - 4.0), fill=theme.control_text, max_size_px=int(render_params.small_font_size_px), bold=True)
            _add_support(support_bboxes, support_records, f"support_menu_{menu_index}_submenu_{submenu_index}", "submenu", str(submenu), submenu_bbox)
            by_group: Dict[str, List[_ControlSpec]] = {}
            for control in controls:
                by_group.setdefault(str(control.path_keys[2]), []).append(control)
            group_items = list(by_group.items())
            group_h = (sub_h - 44.0) / max(1, len(group_items))
            for group_index, (group, group_controls) in enumerate(group_items):
                gy1 = submenu_bbox[3] + 8.0 + group_index * group_h
                group_bbox = (submenu_bbox[0], gy1, submenu_bbox[2], gy1 + group_h - 6.0)
                _rounded_rect(draw, group_bbox, radius=7, fill=theme.panel_fill if group_index % 2 == 0 else theme.app_fill, outline=theme.chrome_line)
                _draw_text_left(
                    draw,
                    text=str(group),
                    bbox=(group_bbox[0] + 8.0, group_bbox[1] + 4.0, group_bbox[0] + 112.0, group_bbox[3] - 4.0),
                    fill=theme.muted_text,
                    max_size_px=int(render_params.small_font_size_px),
                    bold=True,
                )
                _add_support(support_bboxes, support_records, f"support_menu_{menu_index}_submenu_{submenu_index}_group_{group_index}", "menu_group", str(group), group_bbox)
                controls_sorted = sorted(group_controls, key=lambda item: int(item.order_index))
                controls_x1 = group_bbox[0] + 122.0
                control_w = (group_bbox[2] - controls_x1 - 8.0) / max(1, len(controls_sorted))
                for command_index, control in enumerate(controls_sorted):
                    bx1 = controls_x1 + command_index * control_w
                    bbox = (bx1, group_bbox[1] + 6.0, bx1 + control_w - 8.0, group_bbox[3] - 6.0)
                    badge_bboxes[str(control.control_id)] = _draw_control_button(draw, bbox=bbox, control=control, render_params=render_params, theme=theme)
                    control_bboxes[str(control.control_id)] = _bbox_list(bbox)


def _draw_sidebar_tree_scene(
    draw: ImageDraw.ImageDraw,
    *,
    query: _ResolvedQuery,
    workspace: BBox,
    render_params: _RenderParams,
    theme: Any,
    control_bboxes: Dict[str, List[float]],
    badge_bboxes: Dict[str, List[float]],
    support_bboxes: Dict[str, List[float]],
    support_records: List[Dict[str, Any]],
) -> None:
    header_font = load_font(int(render_params.body_font_size_px), bold=True)
    draw_text_traced(draw,(workspace[0] + 18.0, workspace[1] + 14.0), "Sidebar Tree", fill=theme.control_text, font=header_font, role="readout", required=False)
    tree_x1 = workspace[0] + 18.0
    tree_x2 = workspace[0] + 520.0
    tree_y1 = workspace[1] + 54.0
    tree_y2 = workspace[3] - 18.0
    _rounded_rect(draw, (tree_x1, tree_y1, tree_x2, tree_y2), radius=10, fill=theme.control_fill, outline=theme.chrome_line)
    preview_bbox = (tree_x2 + 18.0, tree_y1, workspace[2] - 18.0, tree_y2)
    _rounded_rect(draw, preview_bbox, radius=10, fill=theme.panel_alt_fill, outline=theme.chrome_line)
    _draw_text_center_fit(draw, text="Content Preview", bbox=(preview_bbox[0] + 30.0, preview_bbox[1] + 40.0, preview_bbox[2] - 30.0, preview_bbox[1] + 92.0), fill=theme.muted_text, max_size_px=int(render_params.body_font_size_px), bold=True)

    by_section: Dict[str, List[_ControlSpec]] = {}
    for control in query.controls:
        by_section.setdefault(str(control.path_keys[0]), []).append(control)
    item_symbols: Dict[str, str] = {}
    for control in query.controls:
        item_symbols.setdefault(str(control.path_keys[-1]), str(control.display_text))
    legend_items = list(item_symbols.items())[:4]
    if legend_items:
        legend_title_bbox = (preview_bbox[0] + 28.0, preview_bbox[1] + 126.0, preview_bbox[2] - 28.0, preview_bbox[1] + 154.0)
        _draw_text_left(
            draw,
            text="Item Legend",
            bbox=legend_title_bbox,
            fill=theme.control_text,
            max_size_px=int(render_params.body_font_size_px),
            bold=True,
        )
        legend_x1 = preview_bbox[0] + 28.0
        legend_x2 = preview_bbox[2] - 28.0
        legend_y1 = preview_bbox[1] + 166.0
        legend_w = (legend_x2 - legend_x1) / max(1, min(2, len(legend_items)))
        for legend_index, (item, symbol) in enumerate(legend_items):
            row = legend_index // 2
            col = legend_index % 2
            legend_bbox = (
                legend_x1 + col * legend_w,
                legend_y1 + row * 44.0,
                legend_x1 + (col + 1) * legend_w - 10.0,
                legend_y1 + row * 44.0 + 34.0,
            )
            _rounded_rect(draw, legend_bbox, radius=8, fill=theme.control_fill, outline=theme.chrome_line)
            _draw_text_center_fit(
                draw,
                text=f"{symbol} {item}",
                bbox=(legend_bbox[0] + 8.0, legend_bbox[1] + 4.0, legend_bbox[2] - 8.0, legend_bbox[3] - 4.0),
                fill=theme.control_text,
                max_size_px=int(render_params.small_font_size_px),
                bold=True,
            )
    sections = list(by_section.items())
    section_h = (tree_y2 - tree_y1 - 20.0) / float(len(sections))
    for section_index, (section, section_controls) in enumerate(sections):
        sy1 = tree_y1 + 10.0 + section_index * section_h
        section_bbox = (tree_x1 + 12.0, sy1, tree_x2 - 12.0, sy1 + 28.0)
        _rounded_rect(draw, section_bbox, radius=7, fill=theme.panel_alt_fill, outline=theme.chrome_line)
        _draw_text_left(draw, text=str(section), bbox=(section_bbox[0] + 10.0, section_bbox[1] + 4.0, section_bbox[2] - 10.0, section_bbox[3] - 4.0), fill=theme.control_text, max_size_px=int(render_params.small_font_size_px), bold=True)
        _add_support(support_bboxes, support_records, f"support_sidebar_section_{section_index}", "sidebar_section", str(section), section_bbox)
        by_group: Dict[str, List[_ControlSpec]] = {}
        for control in section_controls:
            by_group.setdefault(str(control.path_keys[1]), []).append(control)
        group_items = list(by_group.items())
        group_h = (section_h - 34.0) / float(len(group_items))
        for group_index, (group, controls) in enumerate(group_items):
            gy1 = section_bbox[3] + 6.0 + group_index * group_h
            group_bbox = (tree_x1 + 28.0, gy1, tree_x2 - 16.0, gy1 + group_h - 4.0)
            _rounded_rect(draw, group_bbox, radius=6, fill=theme.panel_fill if group_index % 2 == 0 else theme.app_fill, outline=theme.chrome_line)
            _draw_text_left(draw, text=f"+ {group}", bbox=(group_bbox[0] + 8.0, group_bbox[1] + 4.0, group_bbox[0] + 110.0, group_bbox[3] - 4.0), fill=theme.muted_text, max_size_px=int(render_params.small_font_size_px), bold=True)
            _add_support(support_bboxes, support_records, f"support_sidebar_section_{section_index}_group_{group_index}", "sidebar_group", str(group), group_bbox)
            items_x1 = group_bbox[0] + 122.0
            item_w = (group_bbox[2] - items_x1 - 10.0) / max(1, len(controls))
            for item_index, control in enumerate(sorted(controls, key=lambda item: int(item.order_index))):
                ix1 = items_x1 + item_index * item_w
                bbox = (ix1, group_bbox[1] + 5.0, ix1 + item_w - 8.0, group_bbox[3] - 5.0)
                badge_bboxes[str(control.control_id)] = _draw_control_button(draw, bbox=bbox, control=control, render_params=render_params, theme=theme)
                control_bboxes[str(control.control_id)] = _bbox_list(bbox)


def _draw_ribbon_group_scene(
    draw: ImageDraw.ImageDraw,
    *,
    query: _ResolvedQuery,
    workspace: BBox,
    render_params: _RenderParams,
    theme: Any,
    control_bboxes: Dict[str, List[float]],
    badge_bboxes: Dict[str, List[float]],
    support_bboxes: Dict[str, List[float]],
    support_records: List[Dict[str, Any]],
) -> None:
    header_font = load_font(int(render_params.body_font_size_px), bold=True)
    draw_text_traced(draw,(workspace[0] + 18.0, workspace[1] + 14.0), "Ribbon Workspace", fill=theme.control_text, font=header_font, role="readout", required=False)
    by_tab: Dict[str, List[_ControlSpec]] = {}
    for control in query.controls:
        by_tab.setdefault(str(control.path_keys[0]), []).append(control)
    command_symbols: Dict[str, str] = {}
    for control in query.controls:
        command_symbols.setdefault(str(control.path_keys[-1]), str(control.display_text))
    legend_items = list(command_symbols.items())[:4]
    legend_x1 = workspace[0] + 250.0
    legend_x2 = workspace[2] - 18.0
    legend_y1 = workspace[1] + 12.0
    legend_w = (legend_x2 - legend_x1) / max(1, len(legend_items))
    for legend_index, (command, symbol) in enumerate(legend_items):
        legend_bbox = (
            legend_x1 + legend_index * legend_w,
            legend_y1,
            legend_x1 + (legend_index + 1) * legend_w - 8.0,
            legend_y1 + 36.0,
        )
        _rounded_rect(draw, legend_bbox, radius=8, fill=theme.panel_alt_fill, outline=theme.chrome_line)
        _draw_text_center_fit(
            draw,
            text=f"{symbol} {command}",
            bbox=(legend_bbox[0] + 6.0, legend_bbox[1] + 4.0, legend_bbox[2] - 6.0, legend_bbox[3] - 4.0),
            fill=theme.control_text,
            max_size_px=int(render_params.small_font_size_px),
            bold=True,
        )
    tabs = list(by_tab.items())
    tab_x1 = workspace[0] + 18.0
    tab_x2 = workspace[2] - 18.0
    tab_y1 = workspace[1] + 54.0
    tab_h = 38.0
    tab_w = (tab_x2 - tab_x1) / float(len(tabs))
    ribbon_y1 = tab_y1 + tab_h + 12.0
    ribbon_y2 = workspace[3] - 185.0
    canvas_bbox = (tab_x1, ribbon_y2 + 16.0, tab_x2, workspace[3] - 18.0)
    _rounded_rect(draw, canvas_bbox, radius=10, fill=theme.control_fill, outline=theme.chrome_line)
    for tab_index, (tab, controls_for_tab) in enumerate(tabs):
        tx1 = tab_x1 + tab_index * tab_w
        tab_bbox = (tx1 + 4.0, tab_y1, tx1 + tab_w - 4.0, tab_y1 + tab_h)
        _rounded_rect(draw, tab_bbox, radius=8, fill=theme.selected_fill if tab_index % 2 == 0 else theme.panel_alt_fill, outline=theme.chrome_line)
        _draw_text_center_fit(draw, text=str(tab), bbox=(tab_bbox[0] + 8.0, tab_bbox[1] + 5.0, tab_bbox[2] - 8.0, tab_bbox[3] - 5.0), fill=theme.control_text, max_size_px=int(render_params.small_font_size_px), bold=True)
        _add_support(support_bboxes, support_records, f"support_ribbon_tab_{tab_index}", "ribbon_tab", str(tab), tab_bbox)
        tab_panel = (tx1 + 4.0, ribbon_y1, tx1 + tab_w - 4.0, ribbon_y2)
        _rounded_rect(draw, tab_panel, radius=8, fill=theme.control_fill, outline=theme.chrome_line)
        by_group: Dict[str, List[_ControlSpec]] = {}
        for control in controls_for_tab:
            by_group.setdefault(str(control.path_keys[1]), []).append(control)
        group_items = list(by_group.items())
        group_h = (tab_panel[3] - tab_panel[1] - 14.0) / float(len(group_items))
        for group_index, (group, controls) in enumerate(group_items):
            gy1 = tab_panel[1] + 8.0 + group_index * group_h
            group_bbox = (tab_panel[0] + 10.0, gy1, tab_panel[2] - 10.0, gy1 + group_h - 6.0)
            _rounded_rect(draw, group_bbox, radius=7, fill=theme.panel_alt_fill if group_index % 2 == 0 else theme.panel_fill, outline=theme.chrome_line)
            _draw_text_center_fit(draw, text=str(group), bbox=(group_bbox[0] + 8.0, group_bbox[1] + 4.0, group_bbox[2] - 8.0, group_bbox[1] + 27.0), fill=theme.muted_text, max_size_px=int(render_params.small_font_size_px), bold=True)
            _add_support(support_bboxes, support_records, f"support_ribbon_tab_{tab_index}_group_{group_index}", "ribbon_group", str(group), group_bbox)
            controls_sorted = sorted(controls, key=lambda item: int(item.order_index))
            control_w = (group_bbox[2] - group_bbox[0] - 28.0) / max(1, len(controls_sorted))
            for command_index, control in enumerate(controls_sorted):
                bx1 = group_bbox[0] + 10.0 + command_index * control_w
                bbox = (bx1, group_bbox[1] + 32.0, bx1 + control_w - 8.0, group_bbox[3] - 8.0)
                badge_bboxes[str(control.control_id)] = _draw_control_button(draw, bbox=bbox, control=control, render_params=render_params, theme=theme)
                control_bboxes[str(control.control_id)] = _bbox_list(bbox)


def _render_navigation_scene(
    image: Image.Image,
    *,
    query: _ResolvedQuery,
    render_params: _RenderParams,
) -> _RenderedScene:
    draw = ImageDraw.Draw(image)
    theme = _theme(str(query.style_variant))
    content_bbox, profile = _draw_app_chrome(draw, query=query, render_params=render_params, theme=theme)
    x1, y1, x2, y2 = [float(value) for value in content_bbox]
    title_bar = (x1 + 18.0, y1 + 10.0, x2 - 18.0, y1 + 50.0)
    _rounded_rect(draw, title_bar, radius=10, fill=theme.panel_alt_fill, outline=theme.chrome_line, width=1)
    _draw_text_left(
        draw,
        text=str(profile.workspace_title),
        bbox=(title_bar[0] + 18.0, title_bar[1] + 8.0, title_bar[0] + 440.0, title_bar[3] - 8.0),
        fill=theme.control_text,
        max_size_px=int(render_params.body_font_size_px),
        bold=True,
    )
    draw_text_traced(draw,(title_bar[2] - 145.0, title_bar[1] + 13.0), str(profile.status_text), fill=theme.muted_text, font=load_font(int(render_params.small_font_size_px)), role="readout", required=False)

    workspace = (x1 + 18.0, title_bar[3] + 12.0, x2 - 18.0, y2 - 16.0)
    _rounded_rect(draw, workspace, radius=10, fill=theme.panel_fill, outline=theme.chrome_line)
    control_bboxes: Dict[str, List[float]] = {}
    badge_bboxes: Dict[str, List[float]] = {}
    support_bboxes: Dict[str, List[float]] = {}
    support_records: List[Dict[str, Any]] = []

    render_kwargs = {
        "query": query,
        "workspace": workspace,
        "render_params": render_params,
        "theme": theme,
        "control_bboxes": control_bboxes,
        "badge_bboxes": badge_bboxes,
        "support_bboxes": support_bboxes,
        "support_records": support_records,
    }
    if str(query.query_id) == "menu_path_target_label":
        _draw_menu_path_scene(draw, **render_kwargs)
    elif str(query.query_id) == "sidebar_tree_target_label":
        _draw_sidebar_tree_scene(draw, **render_kwargs)
    else:
        _draw_ribbon_group_scene(draw, **render_kwargs)

    control_records: List[Dict[str, Any]] = []
    for control in query.controls:
        control_records.append(
            {
                "control_id": str(control.control_id),
                "candidate_label": str(control.candidate_label),
                "role": str(control.role),
                "display_text": str(control.display_text),
                "nav_kind": str(control.nav_kind),
                "path_keys": [str(value) for value in control.path_keys],
                "order_index": int(control.order_index),
                "bbox_px": list(control_bboxes[str(control.control_id)]),
                "candidate_label_bbox_px": list(badge_bboxes[str(control.control_id)]),
            }
        )
    m = int(render_params.window_margin_px)
    window_bbox = [float(m), float(m - 6), float(render_params.canvas_width - m), float(render_params.canvas_height - m + 6)]
    return _RenderedScene(
        control_bboxes_by_id={str(key): list(value) for key, value in control_bboxes.items()},
        badge_bboxes_by_id={str(key): list(value) for key, value in badge_bboxes.items()},
        support_bboxes_by_id={str(key): list(value) for key, value in support_bboxes.items()},
        control_records=tuple(control_records),
        support_records=tuple(dict(record) for record in support_records),
        scene_bbox_px=[0.0, 0.0, float(render_params.canvas_width), float(render_params.canvas_height)],
        window_bbox_px=_bbox_list(tuple(window_bbox)),
        profile=profile,
        theme=theme,
    )


def _support_ids_for_path(query: _ResolvedQuery) -> Tuple[str, ...]:
    path = tuple(str(value) for value in query.path_labels)
    if str(query.query_id) == "menu_path_target_label":
        menu_values = sorted({str(control.path_keys[0]) for control in query.controls}, key=lambda value: next(control.order_index for control in query.controls if str(control.path_keys[0]) == value))
        menu_index = menu_values.index(path[0])
        submenu_values = sorted({str(control.path_keys[1]) for control in query.controls if str(control.path_keys[0]) == path[0]}, key=lambda value: next(control.order_index for control in query.controls if str(control.path_keys[0]) == path[0] and str(control.path_keys[1]) == value))
        submenu_index = submenu_values.index(path[1])
        group_values = sorted({str(control.path_keys[2]) for control in query.controls if str(control.path_keys[0]) == path[0] and str(control.path_keys[1]) == path[1]}, key=lambda value: next(control.order_index for control in query.controls if str(control.path_keys[0]) == path[0] and str(control.path_keys[1]) == path[1] and str(control.path_keys[2]) == value))
        group_index = group_values.index(path[2])
        return (f"support_menu_{menu_index}", f"support_menu_{menu_index}_submenu_{submenu_index}_group_{group_index}")
    if str(query.query_id) == "sidebar_tree_target_label":
        section_values = sorted({str(control.path_keys[0]) for control in query.controls}, key=lambda value: next(control.order_index for control in query.controls if str(control.path_keys[0]) == value))
        section_index = section_values.index(path[0])
        group_values = sorted({str(control.path_keys[1]) for control in query.controls if str(control.path_keys[0]) == path[0]}, key=lambda value: next(control.order_index for control in query.controls if str(control.path_keys[0]) == path[0] and str(control.path_keys[1]) == value))
        group_index = group_values.index(path[1])
        return (f"support_sidebar_section_{section_index}", f"support_sidebar_section_{section_index}_group_{group_index}")
    tab_values = sorted({str(control.path_keys[0]) for control in query.controls}, key=lambda value: next(control.order_index for control in query.controls if str(control.path_keys[0]) == value))
    tab_index = tab_values.index(path[0])
    group_values = sorted({str(control.path_keys[1]) for control in query.controls if str(control.path_keys[0]) == path[0]}, key=lambda value: next(control.order_index for control in query.controls if str(control.path_keys[0]) == path[0] and str(control.path_keys[1]) == value))
    group_index = group_values.index(path[1])
    return (f"support_ribbon_tab_{tab_index}", f"support_ribbon_tab_{tab_index}_group_{group_index}")


def _annotation_roles_for_query(query_id: str) -> Tuple[str, str, str]:
    """Return prompt-facing annotation role names for one navigation query."""

    if str(query_id) == "menu_path_target_label":
        return ("menu_root", "menu_group", "target_command")
    if str(query_id) == "sidebar_tree_target_label":
        return ("sidebar_section", "sidebar_group", "target_item")
    return ("ribbon_tab", "ribbon_group", "target_command")


def _prompt_json_examples(*, query_id: str) -> Tuple[str, str]:
    first_role, second_role, target_role = _annotation_roles_for_query(str(query_id))
    answer_and_annotation = {
        "annotation": {
            str(first_role): [82, 214, 308, 252],
            str(second_role): [104, 270, 286, 302],
            str(target_role): [112, 316, 286, 354],
        },
        "answer": "G",
    }
    answer_only = {"answer": "G"}
    return (
        json.dumps(answer_and_annotation, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
    )




class PagesRelationNavigationPathTargetLabelTask:
    """Identify a labeled GUI target by following a visible navigation path."""

    task_id = TASK_ID
    domain = "pages"
    scene_id = "relation"

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
        rendered = _render_navigation_scene(image, query=query, render_params=render_params)
        image, post_noise_meta = apply_post_image_noise(
            image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        target_bbox = list(rendered.control_bboxes_by_id[str(query.target_control_id)])
        annotation_support_ids = _support_ids_for_path(query)
        first_role, second_role, target_role = _annotation_roles_for_query(str(query.query_id))
        annotation_bbox_map: Dict[str, List[float]] = {
            str(first_role): list(rendered.support_bboxes_by_id[str(annotation_support_ids[0])]),
            str(second_role): list(rendered.support_bboxes_by_id[str(annotation_support_ids[1])]),
            str(target_role): list(target_bbox),
        }
        annotation_role_support_ids: Dict[str, str] = {
            str(first_role): str(annotation_support_ids[0]),
            str(second_role): str(annotation_support_ids[1]),
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
                "path_display": str(query.path_display),
                "path_parent": str(query.path_labels[0]),
                "path_child": str(query.path_labels[1]),
                "command_label": str(query.command_label),
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
                "scene_kind": "gui_navigation_path",
                "entities": [
                    {
                        "entity_id": str(record["control_id"]),
                        "entity_type": "gui_control",
                        "attrs": {
                            "candidate_label": str(record["candidate_label"]),
                            "role": str(record["role"]),
                            "display_text": str(record["display_text"]),
                            "nav_kind": str(record["nav_kind"]),
                            "path_keys": list(record["path_keys"]),
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
                    "path_labels": [str(value) for value in query.path_labels],
                    "path_display": str(query.path_display),
                    "command_label": str(query.command_label),
                    "menu_command_count": int(query.menu_command_count),
                    "ribbon_tab_count": int(query.ribbon_tab_count),
                    "ribbon_group_count": int(query.ribbon_group_count),
                    "ribbon_command_count": int(query.ribbon_command_count),
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
                    "path_labels": [str(value) for value in query.path_labels],
                    "path_display": str(query.path_display),
                    "menu_command_count": int(query.menu_command_count),
                    "menu_command_count_range": [int(value) for value in query.menu_command_count_range],
                    "ribbon_tab_count": int(query.ribbon_tab_count),
                    "ribbon_tab_count_range": [int(value) for value in query.ribbon_tab_count_range],
                    "ribbon_group_count": int(query.ribbon_group_count),
                    "ribbon_group_count_range": [int(value) for value in query.ribbon_group_count_range],
                    "ribbon_command_count": int(query.ribbon_command_count),
                    "ribbon_command_count_range": [int(value) for value in query.ribbon_command_count_range],
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
                "window_bbox_px": list(rendered.window_bbox_px),
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
                "window_bbox_px": list(rendered.window_bbox_px),
                "app_profile": asdict(rendered.profile),
                "control_bboxes_by_id": dict(rendered.control_bboxes_by_id),
                "candidate_label_badge_bboxes_by_id": dict(rendered.badge_bboxes_by_id),
                "support_bboxes_by_id": dict(rendered.support_bboxes_by_id),
                "target_control_id": str(query.target_control_id),
                "annotation_support_ids": [str(value) for value in annotation_support_ids],
                "annotation_role_support_ids": dict(annotation_role_support_ids),
            },
            "execution_trace": {
                "query_id": str(query.query_id),
                "scene_variant": str(query.scene_variant),
                "style_variant": str(query.style_variant),
                "target_control_id": str(query.target_control_id),
                "target_label": str(query.target_label),
                "path_labels": [str(value) for value in query.path_labels],
                "path_display": str(query.path_display),
                "command_label": str(query.command_label),
                "annotation_support_ids": [str(value) for value in annotation_support_ids],
                "annotation_role_support_ids": dict(annotation_role_support_ids),
                "annotation_support_records": [dict(record) for record in annotation_support_records],
                "target_control": dict(target_record),
                "controls": list(control_records),
                "support_records": list(support_records),
                "menu_command_count": int(query.menu_command_count),
                "menu_command_count_range": [int(value) for value in query.menu_command_count_range],
                "ribbon_tab_count": int(query.ribbon_tab_count),
                "ribbon_tab_count_range": [int(value) for value in query.ribbon_tab_count_range],
                "ribbon_group_count": int(query.ribbon_group_count),
                "ribbon_group_count_range": [int(value) for value in query.ribbon_group_count_range],
                "ribbon_command_count": int(query.ribbon_command_count),
                "ribbon_command_count_range": [int(value) for value in query.ribbon_command_count_range],
                "total_control_count": int(len(query.controls)),
                "query_id_probabilities": dict(query.query_id_probabilities),
                "scene_variant_probabilities": dict(query.scene_variant_probabilities),
                "style_variant_probabilities": dict(query.style_variant_probabilities),
                "question_format": "gui_navigation_path_target_label",
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
            scene_id="navigation_flow",
            query_probabilities=query.query_id_probabilities,
        )


@register_task
class PagesNavigationFlowMenuPathTargetLabelTask(FixedPagesQueryTaskMixin):
    """Identify the menu command reached by a visible menu path."""

    task_id = "task_pages__navigation_flow__menu_path_target_label"
    domain = "pages"
    scene_id = "relation"
    public_scene_id = "navigation_flow"
    fixed_query_id = "menu_path_target_label"
    source_task_cls = PagesRelationNavigationPathTargetLabelTask


@register_task
class PagesNavigationFlowSidebarTreeTargetLabelTask(FixedPagesQueryTaskMixin):
    """Identify the sidebar item reached by a visible tree path."""

    task_id = "task_pages__navigation_flow__sidebar_tree_target_label"
    domain = "pages"
    scene_id = "relation"
    public_scene_id = "navigation_flow"
    fixed_query_id = "sidebar_tree_target_label"
    source_task_cls = PagesRelationNavigationPathTargetLabelTask


@register_task
class PagesNavigationFlowRibbonGroupCommandLabelTask(FixedPagesQueryTaskMixin):
    """Identify the ribbon command in a named tab and group."""

    task_id = "task_pages__navigation_flow__ribbon_group_command_label"
    domain = "pages"
    scene_id = "relation"
    public_scene_id = "navigation_flow"
    fixed_query_id = "ribbon_group_command_label"
    source_task_cls = PagesRelationNavigationPathTargetLabelTask


__all__ = [
    "PagesNavigationFlowMenuPathTargetLabelTask",
    "PagesNavigationFlowRibbonGroupCommandLabelTask",
    "PagesNavigationFlowSidebarTreeTargetLabelTask",
    "PagesRelationNavigationPathTargetLabelTask",
    "SUPPORTED_QUERY_IDS",
]
