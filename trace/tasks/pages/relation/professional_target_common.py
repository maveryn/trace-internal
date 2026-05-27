"""Shared ScreenSpot-style GUI relation target task implementation."""

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
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import resolve_render_int
from ...shared.text_rendering import load_font
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.public_query_task import rewrite_pages_query_output
from .gui_relation_common import (
    SUPPORTED_SCENE_VARIANTS,
    SUPPORTED_STYLE_VARIANTS,
    _bbox_list,
    _clamp_unit,
    _draw_app_chrome,
    _draw_badge,
    _draw_text_center_fit,
    _draw_text_left,
    _normalize_str_support as _unused_normalize,
    _rounded_rect,
    _theme,
)


BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]
_GUIDE_CODES: Tuple[str, ...] = ("K1", "M2", "R3", "T4", "V5")
_ACTION_SYMBOLS: Tuple[str, ...] = ("@", "%", "&", "#", "*")
_ACCENT_FILLS: Tuple[Color, ...] = (
    (225, 239, 255),
    (231, 246, 236),
    (255, 239, 216),
    (246, 230, 242),
    (228, 246, 247),
)
_ACCENT_LINES: Tuple[Color, ...] = (
    (93, 142, 205),
    (92, 158, 110),
    (208, 139, 54),
    (174, 105, 164),
    (69, 145, 157),
)


@dataclass(frozen=True)
class ProfessionalVariantSpec:
    name: str
    layout: str
    scene_title: str
    context_title: str
    guide_title: str
    header_title: str
    context_kind: str
    guide_kind: str
    header_kind: str
    control_role: str
    context_pool_key: str
    action_pool_key: str
    cue_pool_key: str
    context_pool: Tuple[str, ...]
    action_pool: Tuple[str, ...]
    cue_pool: Tuple[str, ...]
    instruction_templates: Tuple[str, ...]


@dataclass(frozen=True)
class ProfessionalTaskDefinition:
    task_id: str
    scene_kind: str
    question_format: str
    supported_query_ids: Tuple[str, ...]
    variants: Tuple[ProfessionalVariantSpec, ...]


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
    context_count: int = 5
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
class _ControlSpec:
    control_id: str
    candidate_label: str
    role: str
    display_text: str
    context_label: str
    action_label: str
    cue_label: str
    code_label: str
    context_index: int
    action_index: int
    order_index: int


@dataclass(frozen=True)
class _ResolvedQuery:
    task_id: str
    query_id: str
    scene_variant: str
    style_variant: str
    variant_spec: ProfessionalVariantSpec
    controls: Tuple[_ControlSpec, ...]
    target_control_id: str
    target_label: str
    context_label: str
    action_label: str
    cue_label: str
    code_label: str
    instruction_text: str
    guide_order: Tuple[int, ...]
    context_count: int
    context_count_range: Tuple[int, int]
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


def _relation_defaults(task_id: str) -> Tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], Dict[str, float]]:
    task_group_defaults = get_task_group_defaults("pages", "relation")
    gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        task_group_defaults if isinstance(task_group_defaults, Mapping) else {},
        task_id=str(task_id),
    )
    visual_defaults = task_group_defaults.get("visual", {}) if isinstance(task_group_defaults, Mapping) else {}
    background_defaults = dict(visual_defaults.get("background", {})) if isinstance(visual_defaults.get("background"), Mapping) else {}
    noise_defaults = dict(visual_defaults.get("noise", {})) if isinstance(visual_defaults.get("noise"), Mapping) else {}
    complexity_weights = {
        str(key): float(value)
        for key, value in resolve_task_group_section_defaults(task_group_defaults, "complexity", task_id=str(task_id))
        .get("criteria_weights", {})
        .items()
        if float(value) > 0.0
    }
    return gen_defaults, render_defaults, prompt_defaults, background_defaults, noise_defaults, complexity_weights


def _normalize_support(
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    *,
    key: str,
    fallback: Sequence[str],
    task_id: str,
) -> Tuple[str, ...]:
    raw_values = params.get(str(key), group_default(gen_defaults, str(key), fallback))
    support: List[str] = []
    for raw_value in raw_values:
        value = str(raw_value).strip()
        if value and value not in support:
            support.append(value)
    if not support:
        raise ValueError(f"{key} must not be empty for {task_id}")
    return tuple(str(value) for value in support)


def _decoupled_params(params: Mapping[str, Any], *, task_id: str, divisor: int, namespace: str) -> Mapping[str, Any]:
    _ = task_id, int(divisor), namespace
    return params


def _support_selection_index(
    params: Mapping[str, Any],
    *,
    task_id: str,
    supported_query_ids: Sequence[str],
    instance_seed: int,
    namespace: str,
) -> int:
    _ = supported_query_ids
    return int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}:{namespace}"))


def _resolve_context_count(
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    *,
    task_id: str,
    supported_query_ids: Sequence[str],
    instance_seed: int,
) -> Tuple[int, Tuple[int, int]]:
    if "context_count" in params or "context_count" in gen_defaults:
        value = int(params.get("context_count", group_default(gen_defaults, "context_count", _DEFAULTS.context_count)))
        min_value = max_value = int(value)
    else:
        min_value = int(params.get("context_count_min", group_default(gen_defaults, "context_count_min", _DEFAULTS.context_count)))
        max_value = int(params.get("context_count_max", group_default(gen_defaults, "context_count_max", _DEFAULTS.context_count)))
    if int(min_value) > int(max_value):
        raise ValueError(f"context_count_min must be <= context_count_max for {task_id}")
    if int(min_value) < 2 or int(max_value) > 5:
        raise ValueError(f"context_count range must stay within 2..5 for {task_id}, got {min_value}..{max_value}")
    span = int(max_value) - int(min_value) + 1
    selected = int(min_value) + (
        _support_selection_index(
            params,
            task_id=str(task_id),
            supported_query_ids=supported_query_ids,
            instance_seed=int(instance_seed),
            namespace="context_count",
        )
        % max(1, int(span))
    )
    return int(selected), (int(min_value), int(max_value))


def _resolve_named_axis(
    rng,
    *,
    task_id: str,
    gen_defaults: Mapping[str, Any],
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
        gen_defaults=gen_defaults,
        supported_variants=supported,
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
    )
    balanced = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=supported,
        balance_flag_key=str(balance_flag_key),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        sampling_namespace=f"{task_id}:{namespace}",
    )
    return str(balanced), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_render_params(
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    *,
    instance_seed: int | None = None,
) -> _RenderParams:
    values = asdict(_DEFAULTS)

    def _int_value(key: str) -> int:
        return resolve_render_int(
            params,
            render_defaults,
            str(key),
            int(values[str(key)]),
            instance_seed=instance_seed,
            namespace="pages.professional",
        )

    return _RenderParams(
        canvas_width=_int_value("canvas_width"),
        canvas_height=_int_value("canvas_height"),
        window_margin_px=_int_value("window_margin_px"),
        title_bar_height_px=_int_value("title_bar_height_px"),
        menu_bar_height_px=_int_value("menu_bar_height_px"),
        corner_radius_px=_int_value("corner_radius_px"),
        control_corner_radius_px=_int_value("control_corner_radius_px"),
        control_outline_width_px=_int_value("control_outline_width_px"),
        badge_size_px=_int_value("badge_size_px"),
        title_font_size_px=_int_value("title_font_size_px"),
        body_font_size_px=_int_value("body_font_size_px"),
        small_font_size_px=_int_value("small_font_size_px"),
        label_font_size_px=_int_value("label_font_size_px"),
    )


def _resolve_query(definition: ProfessionalTaskDefinition, instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    task_id = str(definition.task_id)
    gen_defaults, _render_defaults, _prompt_defaults, _bg_defaults, _noise_defaults, _complexity_weights = _relation_defaults(task_id)
    rng = spawn_rng(int(instance_seed), f"{task_id}.query")
    query_id, query_id_probabilities = _resolve_named_axis(
        rng,
        task_id=task_id,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        params=params,
        supported=tuple(definition.supported_query_ids),
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        namespace="query_id",
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        rng,
        task_id=task_id,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        params=_decoupled_params(params, task_id=task_id, divisor=len(definition.supported_query_ids), namespace="scene_variant"),
        supported=SUPPORTED_SCENE_VARIANTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        namespace="scene_variant",
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        rng,
        task_id=task_id,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        params=_decoupled_params(params, task_id=task_id, divisor=len(definition.supported_query_ids), namespace="style_variant"),
        supported=SUPPORTED_STYLE_VARIANTS,
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        namespace="style_variant",
    )
    variant_by_name = {str(spec.name): spec for spec in definition.variants}
    if str(query_id) not in variant_by_name:
        raise ValueError(f"unsupported variant {query_id!r} for {task_id}")
    spec = variant_by_name[str(query_id)]
    candidate_label_pool = _normalize_support(params, gen_defaults, key="candidate_label_pool", fallback=_DEFAULTS.candidate_label_pool, task_id=task_id)
    context_count, context_count_range = _resolve_context_count(
        params,
        gen_defaults,
        task_id=task_id,
        supported_query_ids=definition.supported_query_ids,
        instance_seed=int(instance_seed),
    )
    contexts = _normalize_support(params, gen_defaults, key=str(spec.context_pool_key), fallback=spec.context_pool, task_id=task_id)[:context_count]
    actions = _normalize_support(params, gen_defaults, key=str(spec.action_pool_key), fallback=spec.action_pool, task_id=task_id)[:5]
    cues = _normalize_support(params, gen_defaults, key=str(spec.cue_pool_key), fallback=spec.cue_pool, task_id=task_id)[:5]
    if len(contexts) < context_count or len(actions) < 5 or len(cues) < 5:
        raise ValueError(f"{task_id}/{query_id} requires at least {context_count} contexts plus 5 actions and cues")

    controls_without_labels: List[_ControlSpec] = []
    order = 0
    for context_index, context_label in enumerate(contexts):
        for action_index, action_label in enumerate(actions):
            controls_without_labels.append(
                _ControlSpec(
                    control_id=f"ctx_{context_index:02d}_act_{action_index:02d}",
                    candidate_label="",
                    role=str(spec.control_role),
                    display_text=str(_ACTION_SYMBOLS[int(action_index) % len(_ACTION_SYMBOLS)]),
                    context_label=str(context_label),
                    action_label=str(action_label),
                    cue_label=str(cues[int(action_index)]),
                    code_label=str(_GUIDE_CODES[int(action_index) % len(_GUIDE_CODES)]),
                    context_index=int(context_index),
                    action_index=int(action_index),
                    order_index=int(order),
                )
            )
            order += 1
    target_index = _support_selection_index(
        params,
        task_id=task_id,
        supported_query_ids=definition.supported_query_ids,
        instance_seed=int(instance_seed),
        namespace=f"target.{query_id}",
    ) % len(controls_without_labels)
    target = controls_without_labels[int(target_index)]
    target_label = str(
        params.get(
            "target_label",
            candidate_label_pool[
                _support_selection_index(
                    params,
                    task_id=task_id,
                    supported_query_ids=definition.supported_query_ids,
                    instance_seed=int(instance_seed),
                    namespace=f"answer_label.{query_id}",
                )
                % len(candidate_label_pool)
            ],
        )
    )
    remaining_labels = [str(value) for value in candidate_label_pool if str(value) != str(target_label)]
    label_rng = spawn_rng(int(instance_seed), f"{task_id}.candidate_labels")
    label_rng.shuffle(remaining_labels)
    controls: List[_ControlSpec] = []
    cursor = 0
    for control in controls_without_labels:
        label = str(target_label) if str(control.control_id) == str(target.control_id) else str(remaining_labels[int(cursor)])
        if str(control.control_id) != str(target.control_id):
            cursor += 1
        controls.append(
            _ControlSpec(
                control_id=str(control.control_id),
                candidate_label=str(label),
                role=str(control.role),
                display_text=str(control.display_text),
                context_label=str(control.context_label),
                action_label=str(control.action_label),
                cue_label=str(control.cue_label),
                code_label=str(control.code_label),
                context_index=int(control.context_index),
                action_index=int(control.action_index),
                order_index=int(control.order_index),
            )
        )
    guide_order = list(range(len(actions)))
    spawn_rng(int(instance_seed), f"{task_id}.guide_order.{query_id}").shuffle(guide_order)
    template_index = _support_selection_index(
        params,
        task_id=task_id,
        supported_query_ids=definition.supported_query_ids,
        instance_seed=int(instance_seed),
        namespace=f"instruction_template.{query_id}",
    ) % len(spec.instruction_templates)
    instruction_text = str(spec.instruction_templates[int(template_index)]).format(
        context_label=str(target.context_label),
        cue_label=str(target.cue_label),
        action_label=str(target.action_label),
        code_label=str(target.code_label),
    )
    return _ResolvedQuery(
        task_id=task_id,
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        variant_spec=spec,
        controls=tuple(controls),
        target_control_id=str(target.control_id),
        target_label=str(target_label),
        context_label=str(target.context_label),
        action_label=str(target.action_label),
        cue_label=str(target.cue_label),
        code_label=str(target.code_label),
        instruction_text=str(instruction_text),
        guide_order=tuple(int(value) for value in guide_order),
        context_count=int(context_count),
        context_count_range=tuple(int(value) for value in context_count_range),
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


def _layout_tints(layout: str, theme: Any) -> Tuple[Color, Color, Color]:
    if str(layout) == "property_panel":
        return (theme.panel_alt_fill, (245, 247, 250), theme.selected_fill)
    if str(layout) == "canvas_tool":
        return ((237, 242, 239), (250, 250, 246), (228, 238, 250))
    if str(layout) == "code_workspace":
        return ((238, 241, 246), (249, 250, 252), (232, 241, 250))
    if str(layout) == "file_dialog":
        return ((245, 247, 250), (255, 255, 255), (231, 240, 248))
    return (theme.panel_alt_fill, theme.control_fill, theme.selected_fill)


def _draw_professional_scene(image: Image.Image, *, query: _ResolvedQuery, render_params: _RenderParams) -> _RenderedScene:
    draw = ImageDraw.Draw(image)
    theme = _theme(str(query.style_variant))
    content_bbox, profile = _draw_app_chrome(draw, query=query, render_params=render_params, theme=theme)
    x1, y1, x2, y2 = [float(value) for value in content_bbox]
    spec = query.variant_spec
    pale_fill, surface_fill, selected_fill = _layout_tints(str(spec.layout), theme)

    title_bar = (x1 + 18.0, y1 + 10.0, x2 - 18.0, y1 + 50.0)
    _rounded_rect(draw, title_bar, radius=10, fill=theme.panel_alt_fill, outline=theme.chrome_line, width=1)
    _draw_text_left(
        draw,
        text=str(spec.scene_title),
        bbox=(title_bar[0] + 18.0, title_bar[1] + 8.0, title_bar[0] + 480.0, title_bar[3] - 8.0),
        fill=theme.control_text,
        max_size_px=int(render_params.body_font_size_px),
        bold=True,
    )
    draw.text((title_bar[2] - 150.0, title_bar[1] + 13.0), str(profile.status_text), fill=theme.muted_text, font=load_font(int(render_params.small_font_size_px)))

    workspace = (x1 + 18.0, title_bar[3] + 12.0, x2 - 18.0, y2 - 16.0)
    _rounded_rect(draw, workspace, radius=10, fill=theme.panel_fill, outline=theme.chrome_line)
    support_bboxes: Dict[str, List[float]] = {}
    support_records: List[Dict[str, Any]] = []
    control_bboxes: Dict[str, List[float]] = {}
    badge_bboxes: Dict[str, List[float]] = {}

    guide_y1 = workspace[1] + 14.0
    guide_h = 72.0
    _draw_text_left(
        draw,
        text=str(spec.guide_title),
        bbox=(workspace[0] + 18.0, guide_y1, workspace[0] + 190.0, guide_y1 + 30.0),
        fill=theme.control_text,
        max_size_px=int(render_params.body_font_size_px),
        bold=True,
    )
    guide_x1 = workspace[0] + 205.0
    guide_x2 = workspace[2] - 18.0
    guide_w = (guide_x2 - guide_x1) / 5.0
    actions = sorted({(int(control.action_index), str(control.action_label), str(control.cue_label), str(control.code_label)) for control in query.controls})
    for visual_index, action_index in enumerate(query.guide_order):
        action_tuple = actions[int(action_index)]
        _idx, action_label, cue_label, code_label = action_tuple
        bbox = (
            guide_x1 + visual_index * guide_w,
            guide_y1,
            guide_x1 + (visual_index + 1) * guide_w - 8.0,
            guide_y1 + guide_h,
        )
        fill = _ACCENT_FILLS[int(action_index) % len(_ACCENT_FILLS)]
        outline = _ACCENT_LINES[int(action_index) % len(_ACCENT_LINES)]
        _rounded_rect(draw, bbox, radius=8, fill=fill, outline=outline, width=2)
        _draw_text_center_fit(
            draw,
            text=f"{cue_label}\nKey {code_label}",
            bbox=(bbox[0] + 8.0, bbox[1] + 6.0, bbox[2] - 8.0, bbox[3] - 6.0),
            fill=theme.control_text,
            max_size_px=int(render_params.small_font_size_px),
            bold=True,
        )
        _add_support(support_bboxes, support_records, f"guide_{action_index}", str(spec.guide_kind), f"{cue_label} -> {code_label}", bbox)

    body_y1 = guide_y1 + guide_h + 14.0
    body_y2 = workspace[3] - 18.0
    context_x1 = workspace[0] + 18.0
    context_x2 = workspace[0] + 300.0
    matrix_x1 = context_x2 + 16.0
    matrix_x2 = workspace[2] - 18.0
    context_header = (context_x1, body_y1, context_x2, body_y1 + 36.0)
    matrix_header = (matrix_x1, body_y1, matrix_x2, body_y1 + 36.0)
    _rounded_rect(draw, context_header, radius=8, fill=pale_fill, outline=theme.chrome_line)
    _rounded_rect(draw, matrix_header, radius=8, fill=pale_fill, outline=theme.chrome_line)
    _draw_text_center_fit(draw, text=str(spec.context_title), bbox=context_header, fill=theme.control_text, max_size_px=int(render_params.small_font_size_px), bold=True)
    _draw_text_center_fit(draw, text=str(spec.header_title), bbox=matrix_header, fill=theme.control_text, max_size_px=int(render_params.small_font_size_px), bold=True)

    header_y1 = body_y1 + 46.0
    header_h = 40.0
    row_y1 = header_y1 + header_h + 8.0
    col_w = (matrix_x2 - matrix_x1) / 5.0
    action_indices = sorted({int(control.action_index) for control in query.controls})
    context_indices = sorted({int(control.context_index) for control in query.controls})
    row_h = (body_y2 - row_y1) / float(len(context_indices))
    for action_index in action_indices:
        header_bbox = (
            matrix_x1 + action_index * col_w,
            header_y1,
            matrix_x1 + (action_index + 1) * col_w - 8.0,
            header_y1 + header_h,
        )
        fill = _ACCENT_FILLS[int(action_index) % len(_ACCENT_FILLS)]
        outline = _ACCENT_LINES[int(action_index) % len(_ACCENT_LINES)]
        code_label = next(str(control.code_label) for control in query.controls if int(control.action_index) == int(action_index))
        _rounded_rect(draw, header_bbox, radius=8, fill=fill, outline=outline, width=2)
        _draw_text_center_fit(draw, text=f"Key {code_label}", bbox=header_bbox, fill=theme.control_text, max_size_px=int(render_params.small_font_size_px), bold=True)
        action_label = next(str(control.action_label) for control in query.controls if int(control.action_index) == int(action_index))
        _add_support(support_bboxes, support_records, f"header_{action_index}", str(spec.header_kind), f"{code_label}: {action_label}", header_bbox)

    for context_index in context_indices:
        row_bbox = (
            context_x1,
            row_y1 + context_index * row_h,
            context_x2,
            row_y1 + (context_index + 1) * row_h - 8.0,
        )
        row_fill = selected_fill if context_index % 2 == 0 else surface_fill
        _rounded_rect(draw, row_bbox, radius=8, fill=row_fill, outline=theme.chrome_line)
        context_label = next(str(control.context_label) for control in query.controls if int(control.context_index) == int(context_index))
        prefix = {
            "toolbar_palette": "Mode",
            "property_panel": "Section",
            "canvas_tool": "Object",
            "code_workspace": "Target",
            "file_dialog": "Location",
        }.get(str(spec.layout), "Context")
        if str(spec.layout) == "file_dialog":
            draw.rectangle([row_bbox[0] + 16.0, row_bbox[1] + 16.0, row_bbox[0] + 42.0, row_bbox[1] + 38.0], fill=theme.accent_alt)
        row_text_x = row_bbox[0] + (54.0 if str(spec.layout) == "file_dialog" else 12.0)
        _draw_text_left(
            draw,
            text=f"{prefix}: {context_label}",
            bbox=(row_text_x, row_bbox[1] + 8.0, row_bbox[2] - 10.0, row_bbox[3] - 8.0),
            fill=theme.control_text,
            max_size_px=int(render_params.small_font_size_px),
            bold=True,
        )
        _add_support(support_bboxes, support_records, f"context_{context_index}", str(spec.context_kind), str(context_label), row_bbox)

        if str(spec.layout) == "canvas_tool":
            cx = (row_bbox[0] + row_bbox[2]) / 2.0
            cy = row_bbox[1] + 24.0
            draw.ellipse([cx - 18.0, cy + 10.0, cx + 18.0, cy + 46.0], outline=theme.accent, width=2)
        elif str(spec.layout) == "code_workspace":
            draw.rectangle([row_bbox[0] + 14.0, row_bbox[3] - 18.0, row_bbox[2] - 14.0, row_bbox[3] - 15.0], fill=theme.accent)

    controls_by_pos = {(int(control.context_index), int(control.action_index)): control for control in query.controls}
    for context_index in context_indices:
        for action_index in action_indices:
            control = controls_by_pos[(int(context_index), int(action_index))]
            bbox = (
                matrix_x1 + action_index * col_w,
                row_y1 + context_index * row_h,
                matrix_x1 + (action_index + 1) * col_w - 8.0,
                row_y1 + (context_index + 1) * row_h - 8.0,
            )
            _rounded_rect(
                draw,
                bbox,
                radius=int(render_params.control_corner_radius_px),
                fill=theme.control_fill,
                outline=theme.control_outline,
                width=int(render_params.control_outline_width_px),
            )
            _draw_text_center_fit(
                draw,
                text=str(control.display_text),
                bbox=(bbox[0] + 31.0, bbox[1] + 5.0, bbox[2] - 8.0, bbox[3] - 5.0),
                fill=theme.control_text,
                max_size_px=int(render_params.small_font_size_px),
                bold=True,
            )
            badge_bboxes[str(control.control_id)] = _draw_badge(draw, control_bbox=bbox, label=str(control.candidate_label), render_params=render_params, theme=theme)
            control_bboxes[str(control.control_id)] = _bbox_list(bbox)

    control_records: List[Dict[str, Any]] = []
    for control in query.controls:
        control_records.append(
            {
                "control_id": str(control.control_id),
                "candidate_label": str(control.candidate_label),
                "role": str(control.role),
                "display_text": str(control.display_text),
                "context_label": str(control.context_label),
                "action_label": str(control.action_label),
                "cue_label": str(control.cue_label),
                "code_label": str(control.code_label),
                "context_index": int(control.context_index),
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


def _evidence_support_ids(query: _ResolvedQuery) -> Tuple[str, str, str]:
    target = next(control for control in query.controls if str(control.control_id) == str(query.target_control_id))
    return (f"guide_{int(target.action_index)}", f"context_{int(target.context_index)}", f"header_{int(target.action_index)}")


def _prompt_json_examples() -> Tuple[str, str]:
    answer_and_evidence = {
        "evidence": [[520, 130, 690, 196], [72, 260, 300, 344], [520, 212, 690, 252], [520, 360, 690, 444]],
        "answer": "G",
    }
    answer_only = {"answer": "G"}
    return (
        json.dumps(answer_and_evidence, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
    )


def _build_complexity(query: _ResolvedQuery, complexity_weights: Mapping[str, float]) -> TaskComplexity:
    if not complexity_weights:
        raise ValueError(f"missing positive complexity criteria weights for {query.task_id}")
    layout_base = {
        "toolbar_palette": 0.84,
        "property_panel": 0.88,
        "canvas_tool": 0.92,
        "code_workspace": 0.90,
        "file_dialog": 0.86,
    }.get(str(query.variant_spec.layout), 0.86)
    components = {
        "visual_scan": _clamp_unit((float(len(query.controls)) - 16.0) / 9.0),
        "relational_grounding": 0.98,
        "layout_complexity": float(layout_base),
        "output_burden": 0.48,
    }
    missing = [key for key in complexity_weights if key not in components]
    if missing:
        raise ValueError(f"GUI professional target complexity is missing active criteria: {missing}")
    total_weight = sum(float(value) for value in complexity_weights.values())
    score = sum(float(complexity_weights[key]) * float(components[key]) for key in complexity_weights) / float(total_weight)
    return TaskComplexity(
        complexity_score=_clamp_unit(score),
        complexity_components={str(key): float(_clamp_unit(components[str(key)])) for key in complexity_weights},
    )


class ProfessionalGuiRelationTaskBase:
    """Base class for ScreenSpot-style GUI target grounding tasks."""

    domain = "pages"
    task_group = "relation"
    definition: ProfessionalTaskDefinition

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        definition = self.definition
        task_id = str(definition.task_id)
        gen_defaults, render_defaults, prompt_defaults, background_defaults, noise_defaults, complexity_weights = _relation_defaults(task_id)
        del gen_defaults
        query = _resolve_query(definition, int(instance_seed), params=params)
        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed))
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=background_defaults,
        )
        image = background.copy().convert("RGB")
        rendered = _draw_professional_scene(image, query=query, render_params=render_params)
        image, post_noise_meta = apply_post_image_noise(
            image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=noise_defaults,
        )

        target_record = next(record for record in rendered.control_records if str(record["control_id"]) == str(query.target_control_id))
        evidence_support_ids = _evidence_support_ids(query)
        support_records = [dict(record) for record in rendered.support_records]
        evidence_support_records = [
            next(record for record in support_records if str(record["support_id"]) == str(support_id))
            for support_id in evidence_support_ids
        ]
        evidence_bboxes = [list(record["bbox_px"]) for record in evidence_support_records] + [list(target_record["bbox_px"])]
        answer_gt = TypedValue(type="option_letter", value=str(query.target_label))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        prompt_defaults_required = required_group_defaults(
            prompt_defaults,
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
            context=f"prompt defaults for {task_id}",
        )
        json_example, json_example_answer_only = _prompt_json_examples()
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults_required["bundle_id"]),
            scene_key=str(prompt_defaults_required["scene_key"]),
            task_key=str(prompt_defaults_required["task_key"]),
            query_key=str(query.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults_required["object_description"]),
                "instruction_text": str(query.instruction_text),
                "context_label": str(query.context_label),
                "cue_label": str(query.cue_label),
                "action_label": str(query.action_label),
                "code_label": str(query.code_label),
                "json_output_contract": str(prompt_defaults_required["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults_required["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults_required["evidence_hint"]),
                "answer_hint": str(prompt_defaults_required["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        control_records = [dict(record) for record in rendered.control_records]
        trace_payload = {
            "scene_ir": {
                "scene_kind": str(definition.scene_kind),
                "entities": [
                    {
                        "entity_id": str(record["control_id"]),
                        "entity_type": "gui_control",
                        "attrs": {
                            "candidate_label": str(record["candidate_label"]),
                            "role": str(record["role"]),
                            "display_text": str(record["display_text"]),
                            "context_label": str(record["context_label"]),
                            "action_label": str(record["action_label"]),
                            "cue_label": str(record["cue_label"]),
                            "code_label": str(record["code_label"]),
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
                    "action_label": str(query.action_label),
                    "cue_label": str(query.cue_label),
                    "code_label": str(query.code_label),
                    "instruction_text": str(query.instruction_text),
                    "context_count": int(query.context_count),
                    "evidence_support_ids": [str(value) for value in evidence_support_ids],
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                },
            },
            "query_spec": {
                "query_id": str(query.query_id),
                "template_id": str(prompt_defaults_required["bundle_id"]),
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
                    "action_label": str(query.action_label),
                    "cue_label": str(query.cue_label),
                    "code_label": str(query.code_label),
                    "instruction_text": str(query.instruction_text),
                    "guide_order": [int(value) for value in query.guide_order],
                    "candidate_label_pool": [str(value) for value in query.candidate_label_pool],
                    "context_count": int(query.context_count),
                    "context_count_range": [int(value) for value in query.context_count_range],
                    "action_count": int(len({int(control.action_index) for control in query.controls})),
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
                "evidence_support_ids": [str(value) for value in evidence_support_ids],
            },
            "execution_trace": {
                "query_id": str(query.query_id),
                "scene_variant": str(query.scene_variant),
                "style_variant": str(query.style_variant),
                "target_control_id": str(query.target_control_id),
                "target_label": str(query.target_label),
                "context_label": str(query.context_label),
                "action_label": str(query.action_label),
                "cue_label": str(query.cue_label),
                "code_label": str(query.code_label),
                "instruction_text": str(query.instruction_text),
                "guide_order": [int(value) for value in query.guide_order],
                "evidence_support_ids": [str(value) for value in evidence_support_ids],
                "evidence_support_records": [dict(record) for record in evidence_support_records],
                "target_control": dict(target_record),
                "controls": list(control_records),
                "support_records": list(support_records),
                "total_control_count": int(len(query.controls)),
                "context_count": int(query.context_count),
                "context_count_range": [int(value) for value in query.context_count_range],
                "action_count": int(len({int(control.action_index) for control in query.controls})),
                "query_id_probabilities": dict(query.query_id_probabilities),
                "scene_variant_probabilities": dict(query.scene_variant_probabilities),
                "style_variant_probabilities": dict(query.style_variant_probabilities),
                "question_format": str(definition.question_format),
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
            complexity=_build_complexity(query, complexity_weights),
            task_versions=default_task_versions(),
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
        return rewrite_pages_query_output(
            output,
            query_id=str(query.query_id),
            scene_id="workspace",
            query_probabilities=query.query_id_probabilities,
        )


__all__ = [
    "ProfessionalGuiRelationTaskBase",
    "ProfessionalTaskDefinition",
    "ProfessionalVariantSpec",
]
