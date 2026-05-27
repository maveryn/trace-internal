"""Synthetic GUI command-intent target task."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import hash64, spawn_rng
from ....core.task_group_config import get_task_group_defaults, resolve_task_group_section_defaults
from ....core.types import TaskComplexity, TypedValue
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
from ..shared.gui_render_params import resolve_gui_window_render_params
from ..shared.public_query_task import rewrite_pages_query_output
from .gui_relation_common import (
    SUPPORTED_SCENE_VARIANTS,
    SUPPORTED_STYLE_VARIANTS,
    _bbox_list,
    _clamp_unit,
    _draw_app_chrome,
    _draw_control_button,
    _draw_text_center_fit,
    _draw_text_left,
    _normalize_str_support,
    _rounded_rect,
    _theme,
)


TASK_ID = "task_pages__command_matrix__command_intent_target_label"
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    "command_intent_target_label",
    "dual_guide_command_label",
)
_INTENT_CATEGORY_BY_SOURCE_VARIANT = {
    "create_insert_command_label": "create_insert",
    "select_choose_command_label": "select_choose",
    "view_toggle_command_label": "view_toggle",
    "edit_transform_command_label": "edit_transform",
    "format_style_command_label": "format_style",
}
_SUPPORTED_INTENT_CATEGORIES: Tuple[str, ...] = (
    "create_insert",
    "select_choose",
    "view_toggle",
    "edit_transform",
    "format_style",
)
_INTENT_CATEGORY_AXIS_SIZE = len(_SUPPORTED_INTENT_CATEGORIES)
_TASK_BALANCE_AXIS_SIZE = len(SUPPORTED_QUERY_VARIANTS) * _INTENT_CATEGORY_AXIS_SIZE
_BALANCE_SALT = 84127
_ACTION_SYMBOLS: Tuple[str, ...] = ("@", "%", "&", "#", "*")
_ACTION_CODE_LABELS: Tuple[str, ...] = ("K1", "M2", "R3", "T4", "V5")
_CODE_ACCENT_FILLS: Tuple[Tuple[int, int, int], ...] = (
    (246, 229, 172),
    (203, 230, 255),
    (215, 236, 200),
    (239, 219, 255),
    (255, 220, 207),
)
_CODE_ACCENT_LINES: Tuple[Tuple[int, int, int], ...] = (
    (168, 121, 32),
    (64, 129, 179),
    (82, 139, 76),
    (132, 91, 166),
    (184, 93, 72),
)
_ACTION_CUE_LABELS: Dict[str, str] = {
    "Create": "blank start",
    "Insert": "inside page",
    "Import": "external source",
    "Add": "join set",
    "Upload": "send out",
    "Select": "active mark",
    "Choose": "final choice",
    "Check": "tick box",
    "Pick": "quick choice",
    "Highlight": "visual emphasis",
    "Show": "visible mode",
    "Hide": "masked mode",
    "Zoom": "closer view",
    "Preview": "trial view",
    "Expand": "wide open",
    "Copy": "second copy",
    "Delete": "remove item",
    "Move": "new place",
    "Rotate": "turn angle",
    "Resize": "scale bounds",
    "Format": "layout rules",
    "Align": "straight line",
    "Color": "hue swap",
    "Size": "dimension set",
    "Style": "visual theme",
}
_INSTRUCTION_CUE_TEMPLATES: Tuple[str, ...] = (
    'the "{cue}" intent for "{object}"',
    '"{object}" under the "{cue}" intent',
    'use intent cue "{cue}" for "{object}"',
)
_DUAL_GUIDE_INSTRUCTION_TEMPLATES: Tuple[str, ...] = (
    'the intent cue "{action_cue}" for object cue "{object_cue}"',
    'object cue "{object_cue}" under intent cue "{action_cue}"',
    'use action cue "{action_cue}" with object cue "{object_cue}"',
)
_OBJECT_CUE_LABELS: Dict[str, str] = {
    "Document": "draft set",
    "Chart": "data view",
    "Layer": "stack level",
    "File": "stored item",
    "Project": "work bundle",
}

BBox = Tuple[float, float, float, float]


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
    intent_object_pool: Tuple[str, ...] = ("Document", "Chart", "Layer", "File", "Project")
    intent_create_insert_action_pool: Tuple[str, ...] = ("Create", "Insert", "Import", "Add", "Upload")
    intent_select_choose_action_pool: Tuple[str, ...] = ("Select", "Choose", "Check", "Pick", "Highlight")
    intent_view_toggle_action_pool: Tuple[str, ...] = ("Show", "Hide", "Zoom", "Preview", "Expand")
    intent_edit_transform_action_pool: Tuple[str, ...] = ("Copy", "Delete", "Move", "Rotate", "Resize")
    intent_format_style_action_pool: Tuple[str, ...] = ("Format", "Align", "Color", "Size", "Style")


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
    object_label: str
    object_cue_label: str
    action_label: str
    action_cue_label: str
    action_code_label: str
    action_symbol: str
    row_index: int
    action_index: int
    order_index: int


@dataclass(frozen=True)
class _ResolvedQuery:
    query_variant: str
    intent_category: str
    scene_variant: str
    style_variant: str
    controls: Tuple[_ControlSpec, ...]
    target_control_id: str
    target_label: str
    object_label: str
    object_cue_label: str
    action_label: str
    instruction_cue_label: str
    instruction_code_label: str
    instruction_text: str
    instruction_template_index: int
    action_symbol: str
    guide_support_id: str
    object_guide_support_id: str
    row_support_id: str
    action_support_id: str
    guide_order: Tuple[int, ...]
    candidate_label_pool: Tuple[str, ...]
    query_variant_probabilities: Dict[str, float]
    intent_category_probabilities: Dict[str, float]
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
_TASK_GROUP_DEFAULTS = get_task_group_defaults("pages", "relation")
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


def _action_pool_for_category(params: Mapping[str, Any], intent_category: str) -> Tuple[str, ...]:
    key_by_category = {
        "create_insert": "intent_create_insert_action_pool",
        "select_choose": "intent_select_choose_action_pool",
        "view_toggle": "intent_view_toggle_action_pool",
        "edit_transform": "intent_edit_transform_action_pool",
        "format_style": "intent_format_style_action_pool",
    }
    key = key_by_category[str(intent_category)]
    return _normalize_str_support(params, key, getattr(_DEFAULTS, key))[:5]


def _object_cue_for_label(object_label: str) -> str:
    label = str(object_label)
    fallback = f"{label.lower()} cue"
    return str(_OBJECT_CUE_LABELS.get(label, fallback))


def _instruction_for_target(
    *,
    cue_label: str,
    object_label: str,
    object_cue_label: str,
    query_variant: str,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, int]:
    explicit = params.get("instruction_text")
    if explicit is not None:
        return str(explicit), 0
    if str(query_variant) == "dual_guide_command_label":
        template_index = abs(
            int(
                hash64(
                    int(instance_seed),
                    f"{TASK_ID}:dual_instruction:{str(cue_label)}:{str(object_cue_label)}",
                    _BALANCE_SALT,
                )
            )
        ) % len(_DUAL_GUIDE_INSTRUCTION_TEMPLATES)
        return (
            str(_DUAL_GUIDE_INSTRUCTION_TEMPLATES[int(template_index)]).format(
                action_cue=str(cue_label),
                object_cue=str(object_cue_label),
            ),
            int(template_index),
        )
    template_index = abs(
        int(hash64(int(instance_seed), f"{TASK_ID}:instruction:{str(cue_label)}:{str(object_label)}", _BALANCE_SALT))
    ) % len(_INSTRUCTION_CUE_TEMPLATES)
    return (
        str(_INSTRUCTION_CUE_TEMPLATES[int(template_index)]).format(cue=str(cue_label), object=str(object_label)),
        int(template_index),
    )


def _base_control_specs(
    *,
    objects: Sequence[str],
    actions: Sequence[str],
) -> Tuple[_ControlSpec, ...]:
    controls: List[_ControlSpec] = []
    order = 0
    for row_index, object_label in enumerate(objects):
        object_cue_label = _object_cue_for_label(str(object_label))
        for action_index, action_label in enumerate(actions):
            symbol = str(_ACTION_SYMBOLS[int(action_index) % len(_ACTION_SYMBOLS)])
            cue_label = str(_ACTION_CUE_LABELS.get(str(action_label), str(action_label).lower()))
            code_label = str(_ACTION_CODE_LABELS[int(action_index) % len(_ACTION_CODE_LABELS)])
            controls.append(
                _ControlSpec(
                    control_id=f"intent_{row_index:02d}_{action_index:02d}",
                    candidate_label="",
                    role="command_matrix_cell",
                    display_text=symbol,
                    object_label=str(object_label),
                    object_cue_label=str(object_cue_label),
                    action_label=str(action_label),
                    action_cue_label=str(cue_label),
                    action_code_label=str(code_label),
                    action_symbol=symbol,
                    row_index=int(row_index),
                    action_index=int(action_index),
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
        raise ValueError("candidate_label_pool must cover all command intent controls")
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
                object_label=str(control.object_label),
                object_cue_label=str(control.object_cue_label),
                action_label=str(control.action_label),
                action_cue_label=str(control.action_cue_label),
                action_code_label=str(control.action_code_label),
                action_symbol=str(control.action_symbol),
                row_index=int(control.row_index),
                action_index=int(control.action_index),
                order_index=int(control.order_index),
            )
        )
    return tuple(assigned)


def _resolve_query_variant(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve the public command-intent query variant, accepting old category names."""

    explicit = params.get("query_variant")
    if explicit is not None and str(explicit) in _INTENT_CATEGORY_BY_SOURCE_VARIANT:
        return "command_intent_target_label", {"command_intent_target_label": 1.0}
    return _resolve_named_axis(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        supported=SUPPORTED_QUERY_VARIANTS,
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        balance_flag_key="balanced_query_variant_sampling",
        namespace="query_variant",
    )


def _resolve_intent_category(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve the intent-action category used for the command matrix."""

    explicit_variant = params.get("query_variant")
    if explicit_variant is not None and str(explicit_variant) in _INTENT_CATEGORY_BY_SOURCE_VARIANT:
        selected = str(_INTENT_CATEGORY_BY_SOURCE_VARIANT[str(explicit_variant)])
        return selected, {key: (1.0 if key == selected else 0.0) for key in _SUPPORTED_INTENT_CATEGORIES}

    explicit_category = params.get("intent_category")
    if explicit_category is not None:
        selected = str(explicit_category).strip().lower()
        if selected not in _SUPPORTED_INTENT_CATEGORIES:
            raise ValueError(f"unsupported intent_category: {explicit_category}")
        return selected, {key: (1.0 if key == selected else 0.0) for key in _SUPPORTED_INTENT_CATEGORIES}

    return _resolve_named_axis(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        supported=_SUPPORTED_INTENT_CATEGORIES,
        explicit_key="intent_category",
        weights_key="intent_category_weights",
        balance_flag_key="balanced_intent_category_sampling",
        namespace="intent_category",
    )


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query")
    query_variant, query_variant_probabilities = _resolve_query_variant(
        rng,
        instance_seed=int(instance_seed),
        params=params,
    )
    intent_category, intent_category_probabilities = _resolve_intent_category(
        rng,
        instance_seed=int(instance_seed),
        params=params,
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        rng,
        instance_seed=int(instance_seed),
        params=_decoupled_params(params, divisor=_TASK_BALANCE_AXIS_SIZE, namespace="scene_variant"),
        supported=SUPPORTED_SCENE_VARIANTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        namespace="scene_variant",
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        rng,
        instance_seed=int(instance_seed),
        params=_decoupled_params(params, divisor=_TASK_BALANCE_AXIS_SIZE, namespace="style_variant"),
        supported=SUPPORTED_STYLE_VARIANTS,
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        namespace="style_variant",
    )
    candidate_label_pool = _normalize_str_support(params, "candidate_label_pool", _DEFAULTS.candidate_label_pool)
    objects = _normalize_str_support(params, "intent_object_pool", _DEFAULTS.intent_object_pool)[:5]
    actions = _action_pool_for_category(params, str(intent_category))
    if len(objects) < 5 or len(actions) < 5:
        raise ValueError("GUI command intent pools are too small for the active scene")
    controls_without_labels = _base_control_specs(objects=objects, actions=actions)
    target_index = _support_selection_index(params, instance_seed=int(instance_seed), namespace=f"target.{intent_category}") % len(controls_without_labels)
    target = controls_without_labels[int(target_index)]
    target_label = str(
        params.get(
            "target_label",
            candidate_label_pool[
                _support_selection_index(params, instance_seed=int(instance_seed), namespace=f"answer_label.{intent_category}")
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
    target_control = next(control for control in controls if str(control.control_id) == str(target.control_id))
    guide_order = list(range(len(actions)))
    spawn_rng(int(instance_seed), f"{TASK_ID}.guide_order.{intent_category}").shuffle(guide_order)
    instruction_text, instruction_template_index = _instruction_for_target(
        cue_label=str(target_control.action_cue_label),
        object_label=str(target_control.object_label),
        object_cue_label=str(target_control.object_cue_label),
        query_variant=str(query_variant),
        instance_seed=int(instance_seed),
        params=params,
    )
    return _ResolvedQuery(
        query_variant=str(query_variant),
        intent_category=str(intent_category),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        controls=tuple(controls),
        target_control_id=str(target_control.control_id),
        target_label=str(target_label),
        object_label=str(target_control.object_label),
        object_cue_label=str(target_control.object_cue_label),
        action_label=str(target_control.action_label),
        instruction_cue_label=str(target_control.action_cue_label),
        instruction_code_label=str(target_control.action_code_label),
        instruction_text=str(instruction_text),
        instruction_template_index=int(instruction_template_index),
        action_symbol=str(target_control.action_symbol),
        guide_support_id=f"support_intent_guide_{int(target_control.action_index)}",
        object_guide_support_id=(
            f"support_object_guide_{int(target_control.row_index)}"
            if str(query_variant) == "dual_guide_command_label"
            else ""
        ),
        row_support_id=f"support_object_row_{int(target_control.row_index)}",
        action_support_id=f"support_action_header_{int(target_control.action_index)}",
        guide_order=tuple(int(value) for value in guide_order),
        candidate_label_pool=tuple(str(value) for value in candidate_label_pool),
        query_variant_probabilities=dict(query_variant_probabilities),
        intent_category_probabilities=dict(intent_category_probabilities),
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


def _render_command_matrix_scene(
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
    draw.text((title_bar[2] - 145.0, title_bar[1] + 13.0), str(profile.status_text), fill=theme.muted_text, font=load_font(int(render_params.small_font_size_px)))

    workspace = (x1 + 18.0, title_bar[3] + 12.0, x2 - 18.0, y2 - 16.0)
    _rounded_rect(draw, workspace, radius=10, fill=theme.panel_fill, outline=theme.chrome_line)
    draw.text((workspace[0] + 18.0, workspace[1] + 14.0), "Command Matrix", fill=theme.control_text, font=load_font(int(render_params.body_font_size_px), bold=True))

    objects = sorted({str(control.object_label) for control in query.controls}, key=lambda value: next(control.row_index for control in query.controls if str(control.object_label) == value))
    actions = sorted({str(control.action_label) for control in query.controls}, key=lambda value: next(control.action_index for control in query.controls if str(control.action_label) == value))

    grid_x1 = workspace[0] + 28.0
    grid_x2 = workspace[2] - 28.0
    guide_y1 = workspace[1] + 48.0
    guide_h = 50.0
    dual_guide = str(query.query_variant) == "dual_guide_command_label"
    grid_y1 = guide_y1 + guide_h + 8.0
    grid_y2 = workspace[3] - 22.0
    row_header_w = 210.0
    action_header_h = 46.0
    gap = 8.0
    cell_w = (grid_x2 - grid_x1 - row_header_w - gap * (len(actions) + 1)) / float(len(actions))
    cell_h = (grid_y2 - grid_y1 - action_header_h - gap * (len(objects) + 1)) / float(len(objects))

    control_bboxes: Dict[str, List[float]] = {}
    badge_bboxes: Dict[str, List[float]] = {}
    support_bboxes: Dict[str, List[float]] = {}
    support_records: List[Dict[str, Any]] = []
    controls_by_pos = {(int(control.row_index), int(control.action_index)): control for control in query.controls}
    action_meta_by_index = {int(control.action_index): control for control in query.controls if int(control.row_index) == 0}
    object_meta_by_index = {int(control.row_index): control for control in query.controls if int(control.action_index) == 0}

    guide_corner_bbox = (grid_x1, guide_y1, grid_x1 + row_header_w, guide_y1 + guide_h)
    _rounded_rect(draw, guide_corner_bbox, radius=8, fill=theme.panel_alt_fill, outline=theme.chrome_line)
    _draw_text_center_fit(
        draw,
        text="Intent Guide",
        bbox=(guide_corner_bbox[0] + 10.0, guide_corner_bbox[1] + 6.0, guide_corner_bbox[2] - 10.0, guide_corner_bbox[3] - 6.0),
        fill=theme.muted_text,
        max_size_px=int(render_params.small_font_size_px),
        bold=True,
    )
    for guide_slot, action_index in enumerate(query.guide_order):
        control_meta = action_meta_by_index[int(action_index)]
        accent_fill = _CODE_ACCENT_FILLS[int(action_index) % len(_CODE_ACCENT_FILLS)]
        accent_line = _CODE_ACCENT_LINES[int(action_index) % len(_CODE_ACCENT_LINES)]
        gx1 = grid_x1 + row_header_w + gap + guide_slot * (cell_w + gap)
        guide_bbox = (gx1, guide_y1, gx1 + cell_w, guide_y1 + guide_h)
        _rounded_rect(draw, guide_bbox, radius=8, fill=accent_fill, outline=accent_line, width=2)
        _draw_text_center_fit(
            draw,
            text=str(control_meta.action_cue_label),
            bbox=(guide_bbox[0] + 8.0, guide_bbox[1] + 5.0, guide_bbox[2] - 8.0, guide_bbox[1] + 27.0),
            fill=theme.control_text,
            max_size_px=int(render_params.small_font_size_px),
            bold=True,
        )
        _draw_text_center_fit(
            draw,
            text=f"key {control_meta.action_code_label}",
            bbox=(guide_bbox[0] + 8.0, guide_bbox[1] + 27.0, guide_bbox[2] - 8.0, guide_bbox[3] - 5.0),
            fill=theme.muted_text,
            max_size_px=int(render_params.small_font_size_px) - 1,
            bold=False,
        )
        _add_support(
            support_bboxes,
            support_records,
            f"support_intent_guide_{int(action_index)}",
            "intent_cue_card",
            str(control_meta.action_cue_label),
            guide_bbox,
            attrs={
                "action_label": str(control_meta.action_label),
                "action_cue_label": str(control_meta.action_cue_label),
                "action_code_label": str(control_meta.action_code_label),
                "action_symbol": str(control_meta.action_symbol),
                "accent_index": int(action_index),
                "guide_slot": int(guide_slot),
            },
        )

    corner_bbox = (grid_x1, grid_y1, grid_x1 + row_header_w, grid_y1 + action_header_h)
    _rounded_rect(draw, corner_bbox, radius=8, fill=theme.panel_alt_fill, outline=theme.chrome_line)
    _draw_text_center_fit(
        draw,
        text="Object",
        bbox=(corner_bbox[0] + 10.0, corner_bbox[1] + 6.0, corner_bbox[2] - 10.0, corner_bbox[3] - 6.0),
        fill=theme.muted_text,
        max_size_px=int(render_params.small_font_size_px),
        bold=True,
    )

    for action_index, action in enumerate(actions):
        control_meta = action_meta_by_index[int(action_index)]
        accent_fill = _CODE_ACCENT_FILLS[int(action_index) % len(_CODE_ACCENT_FILLS)]
        accent_line = _CODE_ACCENT_LINES[int(action_index) % len(_CODE_ACCENT_LINES)]
        ax1 = grid_x1 + row_header_w + gap + action_index * (cell_w + gap)
        action_bbox = (ax1, grid_y1, ax1 + cell_w, grid_y1 + action_header_h)
        _rounded_rect(draw, action_bbox, radius=8, fill=accent_fill, outline=accent_line, width=2)
        symbol = str(control_meta.action_symbol)
        _draw_text_center_fit(
            draw,
            text=f"{symbol} {control_meta.action_code_label}",
            bbox=(action_bbox[0] + 8.0, action_bbox[1] + 5.0, action_bbox[2] - 8.0, action_bbox[1] + 27.0),
            fill=theme.control_text,
            max_size_px=int(render_params.small_font_size_px),
            bold=True,
        )
        _draw_text_center_fit(
            draw,
            text="header key",
            bbox=(action_bbox[0] + 8.0, action_bbox[1] + 26.0, action_bbox[2] - 8.0, action_bbox[3] - 5.0),
            fill=theme.muted_text,
            max_size_px=int(render_params.small_font_size_px) - 1,
            bold=False,
        )
        _add_support(
            support_bboxes,
            support_records,
            f"support_action_header_{action_index}",
            "action_header",
            str(action),
            action_bbox,
            attrs={
                "action_label": str(action),
                "action_cue_label": str(control_meta.action_cue_label),
                "action_code_label": str(control_meta.action_code_label),
                "action_symbol": str(symbol),
                "accent_index": int(action_index),
            },
        )

    for row_index, object_label in enumerate(objects):
        ry1 = grid_y1 + action_header_h + gap + row_index * (cell_h + gap)
        row_bbox = (grid_x1, ry1, grid_x1 + row_header_w, ry1 + cell_h)
        _rounded_rect(draw, row_bbox, radius=8, fill=theme.selected_fill if row_index % 2 == 0 else theme.panel_alt_fill, outline=theme.chrome_line)
        label_bbox = (row_bbox[0] + 14.0, row_bbox[1] + 8.0, row_bbox[2] - 14.0, row_bbox[3] - 8.0)
        if bool(dual_guide):
            control_meta = object_meta_by_index[int(row_index)]
            cue_bbox = (row_bbox[0] + 10.0, row_bbox[1] + 10.0, row_bbox[0] + 92.0, row_bbox[3] - 10.0)
            _rounded_rect(
                draw,
                cue_bbox,
                radius=7,
                fill=_CODE_ACCENT_FILLS[int(row_index) % len(_CODE_ACCENT_FILLS)],
                outline=_CODE_ACCENT_LINES[int(row_index) % len(_CODE_ACCENT_LINES)],
                width=2,
            )
            _draw_text_center_fit(
                draw,
                text=str(control_meta.object_cue_label),
                bbox=(cue_bbox[0] + 6.0, cue_bbox[1] + 5.0, cue_bbox[2] - 6.0, cue_bbox[3] - 5.0),
                fill=theme.control_text,
                max_size_px=int(render_params.small_font_size_px),
                min_size_px=7,
                bold=True,
            )
            _add_support(
                support_bboxes,
                support_records,
                f"support_object_guide_{int(row_index)}",
                "object_cue_card",
                str(control_meta.object_cue_label),
                cue_bbox,
                attrs={
                    "object_label": str(control_meta.object_label),
                    "object_cue_label": str(control_meta.object_cue_label),
                    "row_index": int(row_index),
                },
            )
            label_bbox = (row_bbox[0] + 100.0, row_bbox[1] + 8.0, row_bbox[2] - 10.0, row_bbox[3] - 8.0)
        _draw_text_center_fit(
            draw,
            text=str(object_label),
            bbox=label_bbox,
            fill=theme.control_text,
            max_size_px=int(render_params.body_font_size_px),
            bold=True,
        )
        _add_support(support_bboxes, support_records, f"support_object_row_{row_index}", "object_row", str(object_label), row_bbox)
        for action_index, _action in enumerate(actions):
            control = controls_by_pos[(int(row_index), int(action_index))]
            cx1 = grid_x1 + row_header_w + gap + action_index * (cell_w + gap)
            cell_bbox = (cx1, ry1, cx1 + cell_w, ry1 + cell_h)
            badge_bboxes[str(control.control_id)] = _draw_control_button(draw, bbox=cell_bbox, control=control, render_params=render_params, theme=theme)
            control_bboxes[str(control.control_id)] = _bbox_list(cell_bbox)

    control_records: List[Dict[str, Any]] = []
    for control in query.controls:
        control_records.append(
            {
                "control_id": str(control.control_id),
                "candidate_label": str(control.candidate_label),
                "role": str(control.role),
                "display_text": str(control.display_text),
                "object_label": str(control.object_label),
                "object_cue_label": str(control.object_cue_label),
                "action_label": str(control.action_label),
                "action_cue_label": str(control.action_cue_label),
                "action_code_label": str(control.action_code_label),
                "action_symbol": str(control.action_symbol),
                "row_index": int(control.row_index),
                "action_index": int(control.action_index),
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


def _prompt_json_examples() -> Tuple[str, str]:
    answer_and_evidence = {
        "evidence": [[290, 150, 480, 190], [70, 240, 270, 310], [290, 200, 480, 235], [290, 320, 480, 390]],
        "answer": "G",
    }
    answer_only = {"answer": "G"}
    return (
        json.dumps(answer_and_evidence, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
    )


def _build_complexity(query: _ResolvedQuery) -> TaskComplexity:
    if not _COMPLEXITY_WEIGHTS:
        raise ValueError(f"missing positive complexity criteria weights for {TASK_ID}")
    components = {
        "visual_scan": _clamp_unit((float(len(query.controls)) - 12.0) / 12.0),
        "relational_grounding": 0.98 if str(query.query_variant) == "dual_guide_command_label" else 0.92,
        "layout_complexity": 0.86 if str(query.query_variant) == "dual_guide_command_label" else 0.78,
        "output_burden": 0.45,
    }
    missing = [key for key in _COMPLEXITY_WEIGHTS if key not in components]
    if missing:
        raise ValueError(f"GUI command-intent complexity is missing active criteria: {missing}")
    total_weight = sum(float(value) for value in _COMPLEXITY_WEIGHTS.values())
    score = sum(float(_COMPLEXITY_WEIGHTS[key]) * float(components[key]) for key in _COMPLEXITY_WEIGHTS) / float(total_weight)
    return TaskComplexity(
        complexity_score=_clamp_unit(score),
        complexity_components={str(key): float(_clamp_unit(components[str(key)])) for key in _COMPLEXITY_WEIGHTS},
    )


@register_task
class PagesRelationCommandIntentTargetLabelTask:
    """Identify a labeled GUI command cell from a static instruction intent."""

    task_id = TASK_ID
    domain = "pages"
    task_group = "relation"

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
        rendered = _render_command_matrix_scene(image, query=query, render_params=render_params)
        image, post_noise_meta = apply_post_image_noise(
            image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        target_bbox = list(rendered.control_bboxes_by_id[str(query.target_control_id)])
        evidence_support_ids = tuple(
            support_id
            for support_id in (
                str(query.guide_support_id),
                str(query.object_guide_support_id),
                str(query.row_support_id),
                str(query.action_support_id),
            )
            if str(support_id)
        )
        evidence_bboxes = [list(rendered.support_bboxes_by_id[str(support_id)]) for support_id in evidence_support_ids] + [target_bbox]
        answer_gt = TypedValue(type="option_letter", value=str(query.target_label))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
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
            query_key=str(query.query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "object_label": str(query.object_label),
                "object_cue_label": str(query.object_cue_label),
                "action_label": str(query.action_label),
                "instruction_cue_label": str(query.instruction_cue_label),
                "instruction_text": str(query.instruction_text),
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

        control_records = [dict(record) for record in rendered.control_records]
        support_records = [dict(record) for record in rendered.support_records]
        target_record = next(record for record in control_records if str(record["control_id"]) == str(query.target_control_id))
        evidence_support_records = [
            next(record for record in support_records if str(record["support_id"]) == str(support_id))
            for support_id in evidence_support_ids
        ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": "gui_command_intent",
                "entities": [
                    {
                        "entity_id": str(record["control_id"]),
                        "entity_type": "gui_control",
                        "attrs": {
                            "candidate_label": str(record["candidate_label"]),
                            "role": str(record["role"]),
                            "display_text": str(record["display_text"]),
                            "object_label": str(record["object_label"]),
                            "object_cue_label": str(record["object_cue_label"]),
                            "action_label": str(record["action_label"]),
                            "action_cue_label": str(record["action_cue_label"]),
                            "action_code_label": str(record["action_code_label"]),
                            "action_symbol": str(record["action_symbol"]),
                            "bbox_px": list(record["bbox_px"]),
                        },
                    }
                    for record in control_records
                ],
                "relations": {
                    "query_variant": str(query.query_variant),
                    "intent_category": str(query.intent_category),
                    "scene_variant": str(query.scene_variant),
                    "style_variant": str(query.style_variant),
                    "target_control_id": str(query.target_control_id),
                    "target_label": str(query.target_label),
                    "object_label": str(query.object_label),
                    "object_cue_label": str(query.object_cue_label),
                    "action_label": str(query.action_label),
                    "instruction_cue_label": str(query.instruction_cue_label),
                    "instruction_code_label": str(query.instruction_code_label),
                    "instruction_text": str(query.instruction_text),
                    "instruction_template_index": int(query.instruction_template_index),
                    "action_symbol": str(query.action_symbol),
                    "guide_support_id": str(query.guide_support_id),
                    "object_guide_support_id": str(query.object_guide_support_id),
                    "evidence_support_ids": [str(value) for value in evidence_support_ids],
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                },
            },
            "query_spec": {
                "query_variant": str(query.query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_variant": str(query.query_variant),
                    "intent_category": str(query.intent_category),
                    "scene_variant": str(query.scene_variant),
                    "style_variant": str(query.style_variant),
                    "target_control_id": str(query.target_control_id),
                    "target_label": str(query.target_label),
                    "object_label": str(query.object_label),
                    "object_cue_label": str(query.object_cue_label),
                    "action_label": str(query.action_label),
                    "instruction_cue_label": str(query.instruction_cue_label),
                    "instruction_code_label": str(query.instruction_code_label),
                    "instruction_text": str(query.instruction_text),
                    "instruction_template_index": int(query.instruction_template_index),
                    "action_symbol": str(query.action_symbol),
                    "guide_support_id": str(query.guide_support_id),
                    "object_guide_support_id": str(query.object_guide_support_id),
                    "guide_order": [int(value) for value in query.guide_order],
                    "candidate_label_pool": [str(value) for value in query.candidate_label_pool],
                    "query_variant_probabilities": dict(query.query_variant_probabilities),
                    "intent_category_probabilities": dict(query.intent_category_probabilities),
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
                "evidence_support_ids": [str(value) for value in evidence_support_ids],
            },
            "execution_trace": {
                "query_variant": str(query.query_variant),
                "intent_category": str(query.intent_category),
                "scene_variant": str(query.scene_variant),
                "style_variant": str(query.style_variant),
                "target_control_id": str(query.target_control_id),
                "target_label": str(query.target_label),
                "object_label": str(query.object_label),
                "object_cue_label": str(query.object_cue_label),
                "action_label": str(query.action_label),
                "instruction_cue_label": str(query.instruction_cue_label),
                "instruction_code_label": str(query.instruction_code_label),
                "instruction_text": str(query.instruction_text),
                "instruction_template_index": int(query.instruction_template_index),
                "action_symbol": str(query.action_symbol),
                "guide_support_id": str(query.guide_support_id),
                "object_guide_support_id": str(query.object_guide_support_id),
                "guide_order": [int(value) for value in query.guide_order],
                "evidence_support_ids": [str(value) for value in evidence_support_ids],
                "evidence_support_records": [dict(record) for record in evidence_support_records],
                "target_control": dict(target_record),
                "controls": list(control_records),
                "support_records": list(support_records),
                "total_control_count": int(len(query.controls)),
                "query_variant_probabilities": dict(query.query_variant_probabilities),
                "intent_category_probabilities": dict(query.intent_category_probabilities),
                "scene_variant_probabilities": dict(query.scene_variant_probabilities),
                "style_variant_probabilities": dict(query.style_variant_probabilities),
                "question_format": "gui_command_intent_target_label",
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "evidence_support_ids": [str(value) for value in evidence_support_ids],
                "target_control_id": str(query.target_control_id),
                "value": list(evidence_bboxes),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
            },
        }

        output = TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(query),
            task_versions=default_task_versions(),
            query_variant=str(query.query_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
        return rewrite_pages_query_output(
            output,
            query_id=str(query.query_variant),
            scene_id="command_matrix",
            query_probabilities=query.query_variant_probabilities,
        )


__all__ = ["PagesRelationCommandIntentTargetLabelTask", "SUPPORTED_QUERY_VARIANTS"]
