"""Dense mixed-infographic page lookup task."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.font_assets import font_asset_version, font_role_trace, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import fit_font_to_box, load_font
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ...shared.visual_style.information_scene import make_information_scene_background
from ..shared.complexity import build_pages_complexity, normalize_int_with_bounds, resolve_pages_complexity_weights
from ..shared.information_style import resolve_pages_information_style
from ..shared.legible_text import darken_surface_for_light_text, draw_required_page_text
from ..shared.page_visual_assets import (
    PageVisualAssetSelection,
    page_visual_asset_version,
    render_page_visual_asset_rgba,
    sample_page_visual_asset,
)
from ..shared.page_text_resources import (
    PageTextBatch,
    page_text_resource_metadata,
    sample_page_context_batch,
    sample_page_label_batch,
)
from ..shared.visual_defaults import load_pages_noise_defaults


MIXED_INFOGRAPHIC_TASK_ID = "task_pages__mixed_infographic_page__module_field_value_label"
MIXED_INFOGRAPHIC_MODULE_FIELD_VALUE_TASK_ID = MIXED_INFOGRAPHIC_TASK_ID
MIXED_INFOGRAPHIC_FIELD_EXTREMUM_TASK_ID = "task_pages__mixed_infographic_page__module_field_extremum_item_label"
MIXED_INFOGRAPHIC_FIELD_RANKED_TASK_ID = "task_pages__mixed_infographic_page__module_field_ranked_item_label"
MIXED_INFOGRAPHIC_TWO_FIELD_CONDITION_TASK_ID = "task_pages__mixed_infographic_page__module_two_field_condition_item_label"
MIXED_INFOGRAPHIC_CONDITION_COUNT_TASK_ID = "task_pages__mixed_infographic_page__module_condition_item_count"
MIXED_INFOGRAPHIC_FIELD_TOTAL_TASK_ID = "task_pages__mixed_infographic_page__module_field_total_value"
MIXED_INFOGRAPHIC_PAGE_FIELD_EXTREMUM_TASK_ID = "task_pages__mixed_infographic_page__page_field_extremum_module_label"
MIXED_INFOGRAPHIC_TWO_MODULE_TOTAL_COMPARISON_TASK_ID = (
    "task_pages__mixed_infographic_page__two_module_field_total_comparison_module_label"
)
TASK_GROUP = "infographic"
SCENE_ID = "mixed_infographic_page"
QUERY_ID = "module_field_value_label"
MODULE_FIELD_VALUE_QUERY_ID = QUERY_ID
FIELD_EXTREMUM_QUERY_ID = "module_field_extremum_item_label"
FIELD_RANKED_QUERY_ID = "module_field_ranked_item_label"
TWO_FIELD_CONDITION_QUERY_ID = "module_two_field_condition_item_label"
CONDITION_COUNT_QUERY_ID = "module_condition_item_count"
FIELD_TOTAL_QUERY_ID = "module_field_total_value"
PAGE_FIELD_EXTREMUM_QUERY_ID = "page_field_extremum_module_label"
TWO_MODULE_TOTAL_COMPARISON_QUERY_ID = "two_module_field_total_comparison_module_label"
QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
FIELD_EXTREMUM_QUERY_IDS: Tuple[str, ...] = (FIELD_EXTREMUM_QUERY_ID,)
FIELD_RANKED_QUERY_IDS: Tuple[str, ...] = (FIELD_RANKED_QUERY_ID,)
TWO_FIELD_CONDITION_QUERY_IDS: Tuple[str, ...] = (TWO_FIELD_CONDITION_QUERY_ID,)
CONDITION_COUNT_QUERY_IDS: Tuple[str, ...] = (CONDITION_COUNT_QUERY_ID,)
FIELD_TOTAL_QUERY_IDS: Tuple[str, ...] = (FIELD_TOTAL_QUERY_ID,)
PAGE_FIELD_EXTREMUM_QUERY_IDS: Tuple[str, ...] = (PAGE_FIELD_EXTREMUM_QUERY_ID,)
TWO_MODULE_TOTAL_COMPARISON_QUERY_IDS: Tuple[str, ...] = (TWO_MODULE_TOTAL_COMPARISON_QUERY_ID,)
SCENE_VARIANTS: Tuple[str, ...] = (
    "masonry_report",
    "dashboard_blocks",
    "poster_sections",
    "compact_newsletter",
    "collage_board",
    "radial_mosaic",
)
MODULE_KINDS: Tuple[str, ...] = (
    "fact_grid",
    "profile_cards",
    "icon_metric_list",
    "comparison_strip",
    "ranked_list",
    "timeline_snippet",
    "callout_stats",
    "mini_table",
    "radial_bubbles",
    "ring_summary",
)
NATIVE_LAYOUT_MODES: Tuple[str, ...] = (
    "footer_only",
    "top_right_callout",
    "top_left_callout",
    "left_side_rail",
    "right_side_rail",
    "poster_anchor_strip",
    "corner_stamp",
)
NATIVE_LAYOUT_MODE_WEIGHTS: Dict[str, float] = {
    "footer_only": 0.18,
    "top_right_callout": 0.16,
    "top_left_callout": 0.14,
    "left_side_rail": 0.16,
    "right_side_rail": 0.16,
    "poster_anchor_strip": 0.12,
    "corner_stamp": 0.08,
}


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    outer_margin_px: int
    header_height_px: int
    gap_px: int
    corner_radius_px: int
    outline_width_px: int
    title_font_size_px: int
    subtitle_font_size_px: int
    module_title_font_size_px: int
    label_font_size_px: int
    value_font_size_px: int
    field_font_size_px: int
    native_text_footer_height_px: int
    page_backdrop_blend_scale: float


@dataclass(frozen=True)
class _MixedField:
    field_id: str
    label: str


@dataclass(frozen=True)
class _MixedItem:
    item_id: str
    label: str
    visual_asset_selection: PageVisualAssetSelection
    values_by_field_id: Dict[str, str]


@dataclass(frozen=True)
class _MixedModule:
    module_id: str
    kind: str
    title: str
    accent_rgb: Tuple[int, int, int]
    section_asset_selection: PageVisualAssetSelection
    fields: Tuple[_MixedField, ...]
    items: Tuple[_MixedItem, ...]


@dataclass(frozen=True)
class _InfographicTextBlock:
    block_id: str
    kind: str
    text: str
    placement_region: str
    font_role: str


@dataclass(frozen=True)
class _MixedInfographicSpec:
    title: str
    subtitle: str
    hero_asset_selection: PageVisualAssetSelection
    modules: Tuple[_MixedModule, ...]
    text_blocks: Tuple[_InfographicTextBlock, ...]
    text_resource_metadata: Dict[str, Any]


@dataclass(frozen=True)
class _MixedFontProfile:
    readout_family: str
    section_header_family: str
    accent_context_family: str
    module_title_families_by_id: Dict[str, str]


@dataclass(frozen=True)
class _RenderedMixedInfographic:
    image: Image.Image
    entities: List[Dict[str, Any]]
    page_bbox_px: List[float]
    title_bbox_px: List[float]
    module_bboxes_px: Dict[str, List[float]]
    module_title_bboxes_px: Dict[str, List[float]]
    item_label_bboxes_px: Dict[str, Dict[str, List[float]]]
    field_label_bboxes_px: Dict[str, Dict[str, List[float]]]
    value_cell_bboxes_px: Dict[str, Dict[str, Dict[str, List[float]]]]
    icon_bboxes_px: Dict[str, Dict[str, List[float]]]
    section_asset_bboxes_px: Dict[str, List[float]]
    decorative_asset_bboxes_px: Dict[str, List[float]]
    text_block_bboxes_px: Dict[str, List[float]]
    text_blocks: List[Dict[str, Any]]
    font_profile_meta: Dict[str, Any]
    layout_meta: Dict[str, Any]


@dataclass(frozen=True)
class _NativeLayoutPlan:
    mode: str
    title_bbox_px: List[float]
    subtitle_bbox_px: List[float]
    content_bbox_px: List[float]
    footer_bbox_px: List[float]
    block_slots_px: Dict[str, List[float]]
    block_regions: Dict[str, str]
    hero_slot_px: List[float] | None
    hero_text_box_px: List[float] | None
    hero_block_id: str | None
    meta: Dict[str, Any]


@dataclass(frozen=True)
class _MixedSceneContext:
    task_id: str
    query_id: str
    gen_defaults: Dict[str, Any]
    render_defaults: Dict[str, Any]
    prompt_defaults: Dict[str, Any]
    complexity_weights: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    scene_variant: str
    scene_variant_probabilities: Dict[str, float]
    native_layout_mode: str
    native_layout_mode_probabilities: Dict[str, float]
    module_count: int
    module_count_support: Tuple[int, ...]
    module_count_probabilities: Dict[str, float]
    item_count_support: Tuple[int, ...]
    field_count_support: Tuple[int, ...]
    native_text_block_count: int
    native_text_block_count_support: Tuple[int, ...]
    native_text_block_count_probabilities: Dict[str, float]
    spec: _MixedInfographicSpec
    rendered: _RenderedMixedInfographic
    image: Image.Image
    render_params: _RenderParams
    background_meta: Dict[str, Any]
    style_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]
    modules_payload: Tuple[Dict[str, Any], ...]


_TEXT_BLOCK_KIND_ORDER: Tuple[str, ...] = (
    "paragraph_note",
    "summary_note",
    "caption_strip",
    "source_line",
    "callout_quote",
    "badge_note",
)
_FIELD_VALUE_BANKS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("Reach", ("18k", "24k", "31k", "39k", "46k", "52k", "68k", "74k", "83k", "91k")),
    ("Rate", ("12%", "18%", "23%", "27%", "34%", "41%", "48%", "56%", "63%", "72%")),
    ("Score", ("54", "61", "67", "73", "79", "84", "88", "92", "96", "101")),
    ("Cost", ("$18", "$24", "$31", "$46", "$58", "$64", "$72", "$86", "$97", "$113")),
    ("Index", ("A14", "B27", "C35", "D48", "E52", "F69", "G74", "H83", "J91", "K06")),
    ("Status", ("Open", "Ready", "Pilot", "Active", "Paused", "Review", "Queued", "Live")),
    ("Zone", ("North", "South", "East", "West", "Central", "Harbor", "Uptown", "Riverside")),
    ("Level", ("Basic", "Core", "Plus", "Prime", "Select", "Elite", "Gold", "Platinum")),
    ("Window", ("Q1", "Q2", "Q3", "Q4", "Early", "Mid", "Late", "Night")),
    ("Rank", ("#1", "#2", "#3", "#4", "#5", "#6", "#7", "#8")),
    ("Count", ("14", "19", "22", "28", "33", "37", "42", "49", "55", "62")),
    ("Trend", ("Up", "Flat", "Down", "Mixed", "Rising", "Stable", "Cooling", "Shifting")),
)
NUMERIC_FIELD_LABELS: Tuple[str, ...] = ("Reach", "Rate", "Score", "Cost", "Count", "Rank")
CATEGORICAL_FIELD_LABELS: Tuple[str, ...] = ("Status", "Zone", "Level", "Window", "Trend")
ADDITIVE_FIELD_LABELS: Tuple[str, ...] = ("Score", "Count")
CONDITION_OPERATORS: Tuple[str, ...] = ("above", "below", "at_least")
RANK_ORDINALS: Dict[int, str] = {1: "first", 2: "second", 3: "third", 4: "fourth"}
_ACCENTS: Tuple[Tuple[int, int, int], ...] = (
    (59, 122, 177),
    (46, 142, 112),
    (190, 93, 78),
    (126, 102, 183),
    (196, 142, 61),
    (72, 132, 151),
    (166, 83, 116),
    (86, 139, 76),
)


_TASK_GROUP_DEFAULTS = get_task_group_defaults("pages", TASK_GROUP)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=MIXED_INFOGRAPHIC_TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_pages_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=MIXED_INFOGRAPHIC_TASK_ID)
POST_IMAGE_NOISE_DEFAULTS = load_pages_noise_defaults(task_group=TASK_GROUP, apply_prob=0.5)


def _mixed_task_defaults(task_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        task_id=str(task_id),
    )
    complexity_weights = resolve_pages_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=str(task_id))
    return dict(gen_defaults), dict(render_defaults), dict(prompt_defaults), dict(complexity_weights)


def _resolve_named_variant(
    *,
    task_id: str,
    gen_defaults: Mapping[str, Any],
    params: Mapping[str, Any],
    instance_seed: int,
    supported: Sequence[str],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    namespace: str,
) -> Tuple[str, Dict[str, float]]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.{namespace}")
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=gen_defaults,
        supported_variants=[str(value) for value in supported],
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
    )
    balanced = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=[str(value) for value in supported],
        balance_flag_key=str(balance_flag_key),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        sampling_namespace=f"{task_id}.{namespace}",
    )
    if str(balanced) != str(selected) and params.get(str(explicit_key)) is not None:
        return str(balanced), {str(key): (1.0 if str(key) == str(balanced) else 0.0) for key in supported}
    return str(balanced), dict(probabilities)


def _resolve_int_support(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    key: str,
    fallback: Sequence[int],
) -> Tuple[int, ...]:
    raw_values = params.get(str(key), group_default(gen_defaults, str(key), fallback))
    values: List[int] = []
    for raw_value in raw_values:
        value = int(raw_value)
        if value not in values:
            values.append(value)
    if not values:
        raise ValueError(f"{key} must not be empty")
    return tuple(int(value) for value in values)


def _resolve_supported_int(
    *,
    task_id: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    explicit_key: str,
    support_key: str,
    fallback: Sequence[int],
    instance_seed: int,
    namespace: str,
) -> Tuple[int, Tuple[int, ...], Dict[str, float]]:
    support = _resolve_int_support(params=params, gen_defaults=gen_defaults, key=support_key, fallback=fallback)
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(support):
            raise ValueError(f"{explicit_key} must be in {support} for {task_id}")
        return int(selected), tuple(support), {str(int(selected)): 1.0}
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.{namespace}")
    selected = int(support[int(index) % len(support)])
    probability = 1.0 / float(len(support))
    return int(selected), tuple(support), {str(value): float(probability) for value in support}


def _resolve_native_text_block_count(
    *,
    task_id: str,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[int, Tuple[int, ...], Dict[str, float]]:
    return _resolve_supported_int(
        task_id=str(task_id),
        params=params,
        gen_defaults=render_defaults,
        explicit_key="native_text_block_count",
        support_key="native_text_block_count_support",
        fallback=(4, 5),
        instance_seed=int(instance_seed),
        namespace="native_text_block_count",
    )


def _resolve_native_layout_mode(
    *,
    task_id: str,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[str, Dict[str, float]]:
    defaults = dict(render_defaults)
    defaults.setdefault("native_layout_mode_weights", dict(NATIVE_LAYOUT_MODE_WEIGHTS))
    defaults.setdefault("balanced_native_layout_mode_sampling", False)
    return _resolve_named_variant(
        task_id=str(task_id),
        gen_defaults=defaults,
        params=params,
        instance_seed=int(instance_seed),
        supported=NATIVE_LAYOUT_MODES,
        explicit_key="native_layout_mode",
        weights_key="native_layout_mode_weights",
        balance_flag_key="balanced_native_layout_mode_sampling",
        namespace="native_layout_mode",
    )


def _build_infographic_text_blocks(
    *,
    count: int,
    instance_seed: int,
    paragraph_batch: PageTextBatch,
    note_batch: PageTextBatch,
) -> Tuple[_InfographicTextBlock, ...]:
    rng = spawn_rng(int(instance_seed), f"{MIXED_INFOGRAPHIC_TASK_ID}.native_text_blocks")
    target_count = max(4, min(5, int(count)))
    kinds = [kind for kind in _TEXT_BLOCK_KIND_ORDER if str(kind) != "paragraph_note"]
    rng.shuffle(kinds)
    placement_regions = ["header_callout", "footer_badge", "footer_source"]
    blocks: List[_InfographicTextBlock] = []
    used_phrases: set[str] = set()
    paragraph_phrases = list(paragraph_batch.values)
    for index, region in enumerate(("paragraph_left", "paragraph_right")):
        text = str(paragraph_phrases[int(index) % len(paragraph_phrases)])
        used_phrases.add(str(text))
        blocks.append(
            _InfographicTextBlock(
                block_id=f"text_block_{len(blocks) + 1}",
                kind="paragraph_note",
                text=str(text),
                placement_region=str(region),
                font_role="context",
            )
        )
    note_phrases = list(note_batch.values)
    note_cursor = 0
    for index in range(target_count):
        if len(blocks) >= target_count:
            break
        kind = str(kinds[int(index) % len(kinds)])
        while note_cursor < len(note_phrases) and str(note_phrases[note_cursor]) in used_phrases:
            note_cursor += 1
        text = str(note_phrases[int(note_cursor) % len(note_phrases)])
        note_cursor += 1
        used_phrases.add(str(text))
        blocks.append(
            _InfographicTextBlock(
                block_id=f"text_block_{len(blocks) + 1}",
                kind=str(kind),
                text=str(text),
                placement_region=str(placement_regions[int(index) % len(placement_regions)]),
                font_role="context",
            )
        )
    return tuple(blocks)


def _sample_distinct_font_family(
    *,
    role: str,
    instance_seed: int,
    namespace: str,
    params: Mapping[str, Any],
    explicit_key: str,
    weights_key: str,
    avoid: Sequence[str],
) -> str:
    avoided = {str(value) for value in avoid if str(value)}
    first = ""
    for offset in range(8):
        family = sample_font_family(
            role=str(role),
            instance_seed=int(instance_seed),
            namespace=f"{namespace}.{offset}",
            params=params,
            explicit_key=str(explicit_key),
            weights_key=str(weights_key),
        )
        if not first:
            first = str(family)
        if str(family) not in avoided:
            return str(family)
    return str(first)


def _resolve_mixed_font_profile(
    *,
    modules: Sequence[_MixedModule],
    params: Mapping[str, Any],
    instance_seed: int,
) -> _MixedFontProfile:
    readout_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{MIXED_INFOGRAPHIC_TASK_ID}.font_profile.readout",
        params=params,
        explicit_key="mixed_infographic_readout_font_family",
        weights_key="mixed_infographic_readout_font_family_weights",
    )
    section_header_family = _sample_distinct_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{MIXED_INFOGRAPHIC_TASK_ID}.font_profile.section_header",
        params=params,
        explicit_key="mixed_infographic_section_header_font_family",
        weights_key="mixed_infographic_section_header_font_family_weights",
        avoid=(str(readout_family),),
    )
    accent_context_family = _sample_distinct_font_family(
        role="context",
        instance_seed=int(instance_seed),
        namespace=f"{MIXED_INFOGRAPHIC_TASK_ID}.font_profile.accent_context",
        params=params,
        explicit_key="mixed_infographic_context_font_family",
        weights_key="mixed_infographic_context_font_family_weights",
        avoid=(str(readout_family), str(section_header_family)),
    )
    title_families = (str(section_header_family), str(readout_family))
    module_title_families_by_id = {
        str(module.module_id): str(title_families[int(index) % len(title_families)])
        for index, module in enumerate(modules)
    }
    return _MixedFontProfile(
        readout_family=str(readout_family),
        section_header_family=str(section_header_family),
        accent_context_family=str(accent_context_family),
        module_title_families_by_id=dict(module_title_families_by_id),
    )


def _font_profile_metadata(font_profile: _MixedFontProfile) -> Dict[str, Any]:
    return {
        "asset_version": font_asset_version(),
        "policy": "mixed_infographic_three_family_profile",
        "answer_bearing_policy": "field_labels_item_labels_and_values_use_readout_family",
        "readout_family": str(font_profile.readout_family),
        "section_header_family": str(font_profile.section_header_family),
        "accent_context_family": str(font_profile.accent_context_family),
        "role_traces": {
            "readout": font_role_trace(str(font_profile.readout_family), role="readout"),
            "section_header": font_role_trace(str(font_profile.section_header_family), role="readout"),
            "accent_context": font_role_trace(str(font_profile.accent_context_family), role="context"),
        },
        "module_title_families_by_id": dict(font_profile.module_title_families_by_id),
    }


def _resolve_render_params(params: Mapping[str, Any], defaults: Mapping[str, Any]) -> _RenderParams:
    def _int_value(key: str, fallback: int, *, minimum: int = 1) -> int:
        return max(int(minimum), int(params.get(key, group_default(defaults, key, fallback))))

    def _float_value(key: str, fallback: float, *, minimum: float = 0.0, maximum: float = 1.0) -> float:
        value = float(params.get(key, group_default(defaults, key, fallback)))
        return max(float(minimum), min(float(maximum), value))

    return _RenderParams(
        canvas_width=_int_value("canvas_width", 1040, minimum=520),
        canvas_height=_int_value("canvas_height", 1320, minimum=700),
        outer_margin_px=_int_value("outer_margin_px", 36, minimum=12),
        header_height_px=_int_value("header_height_px", 106, minimum=64),
        gap_px=_int_value("gap_px", 14, minimum=6),
        corner_radius_px=_int_value("corner_radius_px", 10, minimum=0),
        outline_width_px=_int_value("outline_width_px", 2, minimum=1),
        title_font_size_px=_int_value("title_font_size_px", 32, minimum=16),
        subtitle_font_size_px=_int_value("subtitle_font_size_px", 17, minimum=10),
        module_title_font_size_px=_int_value("module_title_font_size_px", 17, minimum=10),
        label_font_size_px=_int_value("label_font_size_px", 13, minimum=8),
        value_font_size_px=_int_value("value_font_size_px", 14, minimum=8),
        field_font_size_px=_int_value("field_font_size_px", 11, minimum=7),
        native_text_footer_height_px=_int_value("native_text_footer_height_px", 138, minimum=92),
        page_backdrop_blend_scale=_float_value("page_backdrop_blend_scale", 0.35),
    )


def _blend_rgb(color_a: Sequence[int], color_b: Sequence[int], weight_b: float) -> Tuple[int, int, int]:
    weight = max(0.0, min(1.0, float(weight_b)))
    return tuple(
        int(round((float(color_a[index]) * (1.0 - weight)) + (float(color_b[index]) * weight)))
        for index in range(3)
    )


def _text_bbox(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    font: Any,
    *,
    stroke_width: int = 0,
) -> List[float]:
    try:
        return [
            float(value)
            for value in draw.textbbox((float(xy[0]), float(xy[1])), str(text), font=font, stroke_width=int(stroke_width))
        ]
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        return [float(xy[0]), float(xy[1]), float(xy[0]) + float(width), float(xy[1]) + float(height)]


def _draw_fitted_text(
    draw: ImageDraw.ImageDraw,
    *,
    box: Sequence[float],
    text: str,
    max_size_px: int,
    bold: bool,
    fill_rgb: Sequence[int],
    surface_rgbs: Sequence[Sequence[int]],
    instance_seed: int,
    namespace: str,
    role: str,
    align: str = "left",
    stroke_width: int = 1,
    font_family: str | None = None,
) -> List[float]:
    x0, y0, x1, y1 = [float(value) for value in box]
    font = fit_font_to_box(
        draw,
        text=str(text),
        max_width=max(8.0, x1 - x0),
        max_height=max(8.0, y1 - y0),
        bold=bool(bold),
        font_family=font_family,
        min_size_px=7,
        max_size_px=max(7, int(max_size_px)),
        fill_ratio=0.92,
    )
    probe = _text_bbox(draw, (x0, y0), str(text), font, stroke_width=max(0, int(stroke_width)))
    text_w = float(probe[2] - probe[0])
    text_h = float(probe[3] - probe[1])
    if str(align) == "center":
        tx = x0 + max(0.0, (x1 - x0 - text_w) / 2.0)
    elif str(align) == "right":
        tx = x1 - text_w
    else:
        tx = x0
    ty = y0 + max(0.0, (y1 - y0 - text_h) / 2.0)
    return draw_required_page_text(
        draw,
        (float(tx), float(ty)),
        str(text),
        font,
        role=str(role),
        surface_rgbs=surface_rgbs,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
        preferred_rgbs=(tuple(int(value) for value in fill_rgb),),
        stroke_width=max(0, int(stroke_width)),
    )


def _unique_value(
    *,
    rng: Any,
    field_label: str,
    values: Sequence[str],
    used_values: set[str],
    counter: int,
) -> str:
    candidates = [str(value) for value in values]
    rng.shuffle(candidates)
    for candidate in candidates:
        if str(candidate) not in used_values:
            used_values.add(str(candidate))
            return str(candidate)
    while True:
        fallback_base = int(counter)
        if str(field_label) == "Reach":
            fallback = f"{fallback_base}k"
        elif str(field_label) == "Rate":
            fallback = f"{fallback_base}%"
        elif str(field_label) == "Cost":
            fallback = f"${fallback_base}"
        elif str(field_label) == "Rank":
            fallback = f"#{fallback_base}"
        elif str(field_label) in {"Score", "Count"}:
            fallback = str(fallback_base)
        else:
            fallback = f"{str(field_label)[:2].upper()}{fallback_base:03d}"
        counter += 1
        if fallback not in used_values:
            used_values.add(str(fallback))
            return str(fallback)


def _build_mixed_spec(
    *,
    module_count: int,
    item_count_support: Sequence[int],
    field_count_support: Sequence[int],
    native_text_block_count: int,
    instance_seed: int,
    allow_categorical_value_reuse: bool = False,
    ensure_shared_numeric_field: bool = False,
    shared_numeric_field_label: str | None = None,
    shared_numeric_field_choices: Sequence[str] | None = None,
) -> _MixedInfographicSpec:
    rng = spawn_rng(int(instance_seed), f"{MIXED_INFOGRAPHIC_TASK_ID}.spec")
    title_batch = sample_page_context_batch(
        rng,
        role="mixed_infographic_title",
        count=1,
        manifest_names=("phrases/headlines.txt",),
    )
    subtitle_batch = sample_page_context_batch(
        rng,
        role="mixed_infographic_subtitle",
        count=1,
        manifest_names=("phrases/captions.txt", "phrases/legend_notes.txt"),
    )
    module_title_batch = sample_page_label_batch(
        rng,
        role="mixed_infographic_module_title",
        count=int(module_count),
        manifest_name="categories/product_labels.txt",
        min_chars=3,
        max_chars=16,
        allow_spaces=True,
        allow_punctuation=False,
    )
    max_item_count = int(module_count) * max(int(value) for value in item_count_support)
    item_label_batch = sample_page_label_batch(
        rng,
        role="mixed_infographic_item_label",
        count=max_item_count,
        manifest_name="categories/abstract_group_labels.txt",
        min_chars=3,
        max_chars=14,
        allow_spaces=True,
        allow_punctuation=False,
        exclude=module_title_batch.values,
    )
    paragraph_batch = sample_page_context_batch(
        rng,
        role="mixed_infographic_paragraph_note",
        count=2,
        manifest_names=("paragraphs/context_long_blocks.txt", "paragraphs/context_template_blocks.txt"),
    )
    note_batch = sample_page_context_batch(
        rng,
        role="mixed_infographic_native_note",
        count=6,
        manifest_names=(
            "phrases/callout_phrases.txt",
            "phrases/source_notes.txt",
            "phrases/captions.txt",
            "phrases/sidebar_notes.txt",
        ),
    )
    text_resource_meta = page_text_resource_metadata(
        title_batch,
        subtitle_batch,
        module_title_batch,
        item_label_batch,
        paragraph_batch,
        note_batch,
    )
    module_titles = list(module_title_batch.values)
    item_labels = list(item_label_batch.values)
    field_banks = list(_FIELD_VALUE_BANKS)
    kinds = list(MODULE_KINDS)
    visual_asset_rng = spawn_rng(int(instance_seed), f"{MIXED_INFOGRAPHIC_TASK_ID}.page_visual_assets")
    hero_asset_selection = sample_page_visual_asset(visual_asset_rng, role="hero_anchor")
    rng.shuffle(field_banks)
    rng.shuffle(kinds)
    shared_numeric_label = ""
    shared_numeric_module_count = 0
    if bool(ensure_shared_numeric_field):
        shared_numeric_choices = tuple(str(label) for label in (shared_numeric_field_choices or NUMERIC_FIELD_LABELS))
        invalid_shared_labels = [label for label in shared_numeric_choices if str(label) not in set(NUMERIC_FIELD_LABELS)]
        if invalid_shared_labels:
            raise ValueError("shared_numeric_field_choices must be supported numeric mixed-infographic fields")
        requested_shared_label = str(shared_numeric_field_label) if shared_numeric_field_label is not None else ""
        if requested_shared_label and requested_shared_label not in set(NUMERIC_FIELD_LABELS):
            raise ValueError("shared_numeric_field_label must be a supported numeric mixed-infographic field")
        if requested_shared_label and requested_shared_label not in set(shared_numeric_choices):
            raise ValueError("shared_numeric_field_label must be allowed by shared_numeric_field_choices")
        shared_numeric_label = requested_shared_label or str(
            shared_numeric_choices[int(rng.randrange(len(shared_numeric_choices)))]
        )
        shared_numeric_module_count = min(int(module_count), max(3, int(math.ceil(float(module_count) * 0.45))))
    if int(module_count) >= 4:
        required_kinds = ("radial_bubbles", "ring_summary")
        required_start = max(0, int(module_count) - len(required_kinds))
        for offset, required_kind in enumerate(required_kinds):
            if required_kind in kinds:
                kinds.remove(required_kind)
            kinds.insert(required_start + int(offset), required_kind)
    if int(module_count) > len(module_titles):
        raise ValueError("module_count exceeds available unique module titles")
    used_values: set[str] = set()
    used_items = 0
    fallback_counter = 1
    modules: List[_MixedModule] = []
    for module_index in range(int(module_count)):
        module_kind = str(kinds[int(module_index) % len(kinds)])
        section_asset_selection = sample_page_visual_asset(visual_asset_rng, role="section_illustration")
        item_count = int(item_count_support[int(rng.randrange(len(item_count_support)))])
        field_count = int(field_count_support[int(rng.randrange(len(field_count_support)))])
        if module_kind in {"radial_bubbles", "ring_summary"}:
            item_count = min(int(item_count), 3)
            field_count = 1
        elif module_kind in {"profile_cards", "callout_stats"}:
            item_count = min(int(item_count), 3)
            field_count = min(int(field_count), 2)
        bank_offset = int(rng.randrange(len(field_banks)))
        module_fields: List[_MixedField] = []
        for field_index in range(int(field_count)):
            label = str(field_banks[(bank_offset + field_index) % len(field_banks)][0])
            module_fields.append(_MixedField(field_id=f"field_{field_index + 1}", label=label))
        if bool(ensure_shared_numeric_field) and int(module_index) < int(shared_numeric_module_count):
            module_fields[0] = _MixedField(field_id=str(module_fields[0].field_id), label=str(shared_numeric_label))
        if not any(str(field.label) in set(NUMERIC_FIELD_LABELS) for field in module_fields):
            used_labels = {str(field.label) for field in module_fields}
            preferred_numeric_labels = ("Score", "Count", "Reach", "Rate", "Cost", "Rank")
            replacement_label = next(
                label for label in preferred_numeric_labels if str(label) not in used_labels or len(module_fields) == 1
            )
            module_fields[0] = _MixedField(field_id=str(module_fields[0].field_id), label=str(replacement_label))
        module_items: List[_MixedItem] = []
        for item_index in range(int(item_count)):
            if used_items >= len(item_labels):
                item_label = f"Item {used_items + 1}"
            else:
                item_label = str(item_labels[used_items])
            used_items += 1
            values_by_field_id: Dict[str, str] = {}
            for field_index, field in enumerate(module_fields):
                bank = next(values for label, values in field_banks if str(label) == str(field.label))
                if bool(allow_categorical_value_reuse) and str(field.label) in set(CATEGORICAL_FIELD_LABELS):
                    repeat_pool_size = min(len(bank), 2 if int(item_count) <= 4 else 3)
                    value = str(bank[(int(module_index) + int(field_index) + int(item_index)) % int(repeat_pool_size)])
                else:
                    value = _unique_value(
                        rng=rng,
                        field_label=str(field.label),
                        values=bank,
                        used_values=used_values,
                        counter=fallback_counter,
                    )
                    fallback_counter += 1
                values_by_field_id[str(field.field_id)] = str(value)
            module_items.append(
                _MixedItem(
                    item_id=f"item_{item_index + 1}",
                    label=str(item_label),
                    visual_asset_selection=sample_page_visual_asset(
                        visual_asset_rng,
                        role="badge_spot",
                        render_modes=("monochrome",),
                    ),
                    values_by_field_id=dict(values_by_field_id),
                )
            )
        modules.append(
            _MixedModule(
                module_id=f"module_{module_index + 1}",
                kind=str(module_kind),
                title=str(module_titles[int(module_index)]),
                accent_rgb=tuple(int(value) for value in _ACCENTS[int(module_index) % len(_ACCENTS)]),
                section_asset_selection=section_asset_selection,
                fields=tuple(module_fields),
                items=tuple(module_items),
            )
        )
    return _MixedInfographicSpec(
        title=str(title_batch.values[0]),
        subtitle=str(subtitle_batch.values[0]),
        hero_asset_selection=hero_asset_selection,
        modules=tuple(modules),
        text_blocks=_build_infographic_text_blocks(
            count=int(native_text_block_count),
            instance_seed=int(instance_seed),
            paragraph_batch=paragraph_batch,
            note_batch=note_batch,
        ),
        text_resource_metadata=dict(text_resource_meta),
    )


def _layout_slots(
    *,
    render_params: _RenderParams,
    scene_variant: str,
    module_count: int,
    instance_seed: int,
    content_bbox: Sequence[float],
    footer_bbox: Sequence[float],
) -> Tuple[List[List[float]], Dict[str, Any]]:
    gap = float(render_params.gap_px)
    left, top, right, bottom = [float(value) for value in content_bbox]
    width = right - left
    height = bottom - top
    slots: List[List[float]] = []
    variant = str(scene_variant)
    rng = spawn_rng(int(instance_seed), f"{MIXED_INFOGRAPHIC_TASK_ID}.layout.{variant}.{module_count}")

    def _clamp_slot(slot: Sequence[float]) -> List[float]:
        x0, y0, x1, y1 = [float(value) for value in slot]
        min_w = min(220.0, max(160.0, width * 0.18))
        min_h = 142.0
        x0 = max(left, min(right - min_w, x0))
        y0 = max(top, min(bottom - min_h, y0))
        x1 = max(x0 + min_w, min(right, x1))
        y1 = max(y0 + min_h, min(bottom, y1))
        return [float(x0), float(y0), float(x1), float(y1)]

    def _scaled_slot(frac: Sequence[float]) -> List[float]:
        x0, y0, x1, y1 = [float(value) for value in frac]
        return _clamp_slot(
            [
                left + x0 * width,
                top + y0 * height,
                left + x1 * width,
                top + y1 * height,
            ]
        )

    def _jitter_slots(base_slots: Sequence[Sequence[float]], *, amount: float) -> List[List[float]]:
        jittered: List[List[float]] = []
        for index, slot in enumerate(base_slots):
            x0, y0, x1, y1 = [float(value) for value in slot]
            slot_w = x1 - x0
            slot_h = y1 - y0
            dx = (float(rng.random()) - 0.5) * float(amount) * min(gap * 2.6, slot_w * 0.08)
            dy = (float(rng.random()) - 0.5) * float(amount) * min(gap * 2.8, slot_h * 0.08)
            grow_x = (float(rng.random()) - 0.5) * float(amount) * min(gap * 1.6, slot_w * 0.04)
            grow_y = (float(rng.random()) - 0.5) * float(amount) * min(gap * 1.8, slot_h * 0.04)
            if index % 3 == 1:
                dy += min(gap * 0.55, slot_h * 0.025)
            elif index % 3 == 2:
                dy -= min(gap * 0.35, slot_h * 0.02)
            jittered.append(_clamp_slot([x0 + dx - grow_x, y0 + dy - grow_y, x1 + dx + grow_x, y1 + dy + grow_y]))
        return jittered

    def _append_grid(*, count: int, cols: int, grid_left: float, grid_top: float, grid_width: float, grid_height: float) -> None:
        rows = max(1, int(math.ceil(float(count) / float(cols))))
        cell_h = (float(grid_height) - float(rows - 1) * gap) / float(rows)
        for index in range(int(count)):
            row = int(index // cols)
            default_col = int(index % cols)
            remaining = int(count) - int(row) * int(cols)
            row_cols = int(cols) if int(remaining) >= int(cols) else int(remaining)
            row_cols = max(1, int(row_cols))
            col = int(default_col) if int(row_cols) == int(cols) else int(index - int(row) * int(cols))
            cell_w = (float(grid_width) - float(row_cols - 1) * gap) / float(row_cols)
            x0 = float(grid_left) + float(col) * (cell_w + gap)
            y0 = float(grid_top) + float(row) * (cell_h + gap)
            slots.append([x0, y0, x0 + cell_w, y0 + cell_h])

    irregular_patterns: Dict[str, Tuple[Tuple[float, float, float, float], ...]] = {
        "collage_board": (
            (0.00, 0.00, 0.36, 0.22),
            (0.39, 0.02, 0.66, 0.20),
            (0.69, 0.00, 1.00, 0.29),
            (0.02, 0.26, 0.41, 0.50),
            (0.44, 0.24, 0.72, 0.48),
            (0.75, 0.33, 1.00, 0.56),
            (0.00, 0.56, 0.30, 0.86),
            (0.33, 0.52, 0.67, 0.83),
            (0.70, 0.61, 1.00, 0.90),
        ),
        "radial_mosaic": (
            (0.34, 0.22, 0.69, 0.52),
            (0.02, 0.01, 0.35, 0.21),
            (0.67, 0.02, 0.98, 0.22),
            (0.00, 0.27, 0.32, 0.50),
            (0.72, 0.28, 1.00, 0.51),
            (0.05, 0.57, 0.36, 0.84),
            (0.39, 0.55, 0.67, 0.86),
            (0.70, 0.58, 0.98, 0.86),
            (0.17, 0.86, 0.83, 1.00),
        ),
    }

    if variant in irregular_patterns:
        slots = [_scaled_slot(pattern) for pattern in irregular_patterns[str(variant)][: int(module_count)]]
        slots = _jitter_slots(slots, amount=1.0)
    elif variant == "poster_sections":
        hero_h = min(210.0, max(170.0, height * 0.18))
        slots.append([left, top, right, top + hero_h])
        remaining = int(module_count) - 1
        _append_grid(
            count=remaining,
            cols=2,
            grid_left=left,
            grid_top=top + hero_h + gap,
            grid_width=width,
            grid_height=height - hero_h - gap,
        )
    elif variant == "compact_newsletter":
        _append_grid(count=int(module_count), cols=2, grid_left=left, grid_top=top, grid_width=width, grid_height=height)
    elif variant == "dashboard_blocks" and int(module_count) >= 7:
        top_h = min(270.0, max(230.0, height * 0.23))
        top_w = (width - gap) / 2.0
        slots.append([left, top, left + top_w, top + top_h])
        slots.append([left + top_w + gap, top, right, top + top_h])
        remaining = int(module_count) - 2
        _append_grid(
            count=remaining,
            cols=3,
            grid_left=left,
            grid_top=top + top_h + gap,
            grid_width=width,
            grid_height=height - top_h - gap,
        )
    else:
        _append_grid(count=int(module_count), cols=3, grid_left=left, grid_top=top, grid_width=width, grid_height=height)

    if variant not in irregular_patterns:
        slots = _jitter_slots(slots, amount=0.45 if variant in {"masonry_report", "dashboard_blocks"} else 0.28)

    return slots[: int(module_count)], {
        "scene_variant": str(scene_variant),
        "module_count": int(module_count),
        "placement_mode": "irregular_fractional_slots" if variant in irregular_patterns else "jittered_structured_slots",
        "content_bbox_px": [left, top, right, bottom],
        "native_text_footer_bbox_px": [float(value) for value in footer_bbox],
        "native_text_footer_height_px": int(render_params.native_text_footer_height_px),
        "slot_bboxes_px": [list(slot) for slot in slots[: int(module_count)]],
        "layout_jitter_seed": int(instance_seed),
    }


def _set_alpha_opacity(image: Image.Image, opacity: float) -> Image.Image:
    alpha_scale = max(0.0, min(1.0, float(opacity)))
    if alpha_scale >= 0.999:
        return image
    adjusted = image.copy()
    alpha = adjusted.getchannel("A").point(lambda value: int(round(float(value) * alpha_scale)))
    adjusted.putalpha(alpha)
    return adjusted


def _draw_visual_asset(
    image: Image.Image,
    *,
    selection: PageVisualAssetSelection,
    bbox: Sequence[float],
    tint_rgb: Sequence[int],
    opacity: float = 1.0,
) -> List[float]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    asset = render_page_visual_asset_rgba(
        selection.asset,
        size_px=(max(1, int(round(x1 - x0))), max(1, int(round(y1 - y0)))),
        tint_rgb=tuple(int(value) for value in tint_rgb),
    )
    asset = _set_alpha_opacity(asset, float(opacity))
    px = int(round(x0 + max(0.0, (x1 - x0 - asset.width) / 2.0)))
    py = int(round(y0 + max(0.0, (y1 - y0 - asset.height) / 2.0)))
    image.alpha_composite(asset, (px, py))
    return [float(px), float(py), float(px + asset.width), float(py + asset.height)]


def _draw_module_section_asset(
    image: Image.Image,
    *,
    module: _MixedModule,
    bbox: Sequence[float],
    header_height: float,
    opacity: float = 0.18,
) -> List[float]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    width = max(1.0, x1 - x0)
    height = max(1.0, y1 - y0)
    size = min(max(42.0, width * 0.24), max(42.0, height * 0.26), 98.0)
    asset_box = [
        x1 - size - max(10.0, width * 0.035),
        y0 + float(header_height) + max(8.0, height * 0.035),
        x1 - max(10.0, width * 0.035),
        y0 + float(header_height) + max(8.0, height * 0.035) + size,
    ]
    return _draw_visual_asset(
        image,
        selection=module.section_asset_selection,
        bbox=asset_box,
        tint_rgb=module.accent_rgb,
        opacity=float(opacity),
    )


def _module_surface_rgb(style: Any, accent_rgb: Sequence[int], module_id: str) -> Tuple[int, int, int]:
    index_text = "".join(ch for ch in str(module_id) if ch.isdigit())
    index = int(index_text or 0)
    accent_weight = 0.12 + 0.04 * float(index % 4)
    alt_weight = 0.24 + 0.09 * float((index + 1) % 3)
    base = _blend_rgb(style.panel_fill_rgb, style.surface_alt_rgb, alt_weight)
    return _blend_rgb(base, accent_rgb, accent_weight)


def _draw_page_backdrops(
    draw: ImageDraw.ImageDraw,
    *,
    page_bbox: Sequence[float],
    style: Any,
    instance_seed: int,
    blend_scale: float,
) -> List[Dict[str, Any]]:
    x0, y0, x1, y1 = [float(value) for value in page_bbox]
    width = x1 - x0
    height = y1 - y0
    rng = spawn_rng(int(instance_seed), f"{MIXED_INFOGRAPHIC_TASK_ID}.page_backdrops")
    backdrop_meta: List[Dict[str, Any]] = []
    scale = max(0.0, min(1.0, float(blend_scale)))
    colors = (
        _blend_rgb(style.surface_rgb, style.accent_rgb, 0.13 * scale),
        _blend_rgb(style.surface_rgb, style.surface_alt_rgb, 0.58 * scale),
        _blend_rgb(style.surface_rgb, style.header_rgb, 0.10 * scale),
    )
    polygons = (
        (
            (x0 + width * 0.03, y0 + height * 0.10),
            (x0 + width * 0.55, y0 + height * 0.06),
            (x0 + width * 0.50, y0 + height * 0.27),
            (x0 + width * 0.02, y0 + height * 0.31),
        ),
        (
            (x0 + width * 0.58, y0 + height * 0.16),
            (x0 + width * 0.98, y0 + height * 0.12),
            (x0 + width * 0.95, y0 + height * 0.44),
            (x0 + width * 0.63, y0 + height * 0.38),
        ),
        (
            (x0 + width * 0.08, y0 + height * 0.66),
            (x0 + width * 0.93, y0 + height * 0.58),
            (x0 + width * 0.97, y0 + height * 0.92),
            (x0 + width * 0.04, y0 + height * 0.96),
        ),
    )
    for index, polygon in enumerate(polygons):
        dx = (float(rng.random()) - 0.5) * width * 0.025
        dy = (float(rng.random()) - 0.5) * height * 0.018
        shifted = tuple((float(px) + dx, float(py) + dy) for px, py in polygon)
        fill = tuple(int(value) for value in colors[int(index) % len(colors)])
        draw.polygon(shifted, fill=fill)
        backdrop_meta.append(
            {
                "kind": "irregular_page_band",
                "polygon_px": [[float(px), float(py)] for px, py in shifted],
                "fill_rgb": [int(value) for value in fill],
                "blend_scale": float(scale),
            }
        )
    return backdrop_meta


def _bbox_overlap_area(a: Sequence[float], b: Sequence[float]) -> float:
    ax0, ay0, ax1, ay1 = [float(value) for value in a]
    bx0, by0, bx1, by1 = [float(value) for value in b]
    overlap_w = max(0.0, min(ax1, bx1) - max(ax0, bx0))
    overlap_h = max(0.0, min(ay1, by1) - max(ay0, by0))
    return float(overlap_w * overlap_h)


def _footer_text_slot(footer_bbox: Sequence[float], region: str) -> List[float]:
    x0, y0, x1, y1 = [float(value) for value in footer_bbox]
    gap = 12.0
    width = x1 - x0
    paragraph_bottom = y1 - 38.0
    half_w = (width - gap) / 2.0
    small_w = (width - 2.0 * gap) / 3.0
    regions = {
        "paragraph_left": [x0, y0, x0 + half_w, paragraph_bottom],
        "paragraph_right": [x0 + half_w + gap, y0, x1, paragraph_bottom],
        "footer_badge": [x0, paragraph_bottom + 8.0, x0 + small_w, y1],
        "footer_source": [x0 + small_w + gap, paragraph_bottom + 8.0, x0 + 2.0 * small_w + gap, y1],
        "footer_note": [x0 + 2.0 * (small_w + gap), paragraph_bottom + 8.0, x1, y1],
    }
    return [float(value) for value in regions.get(str(region), regions["footer_note"])]


def _resolve_native_layout(
    *,
    page_bbox: Sequence[float],
    render_params: _RenderParams,
    native_layout_mode: str,
    text_blocks: Sequence[_InfographicTextBlock],
) -> _NativeLayoutPlan:
    x0, y0, x1, y1 = [float(value) for value in page_bbox]
    gap = float(render_params.gap_px)
    header_bottom = y0 + float(render_params.header_height_px)
    footer_h = float(render_params.native_text_footer_height_px)
    default_content = [x0, header_bottom + gap, x1, y1 - footer_h]
    default_footer = [x0, default_content[3] + gap * 0.45, x1, y1]
    title_box = [x0 + 22.0, y0 + 12.0, x1 - 22.0, y0 + 55.0]
    subtitle_box = [x0 + 22.0, y0 + 58.0, x1 - 22.0, y0 + 88.0]
    block_slots: Dict[str, List[float]] = {}
    block_regions: Dict[str, str] = {}
    hero_slot: List[float] | None = None
    hero_text_box: List[float] | None = None
    hero_block_id: str | None = None

    paragraphs = [block for block in text_blocks if str(block.kind) == "paragraph_note"]
    small_blocks = [block for block in text_blocks if str(block.kind) != "paragraph_note"]

    def _assign_block(block: _InfographicTextBlock | None, slot: Sequence[float], region: str) -> None:
        if block is None:
            return
        block_slots[str(block.block_id)] = [float(value) for value in slot]
        block_regions[str(block.block_id)] = str(region)

    def _assign_footer_blocks(footer_bbox: Sequence[float], *, paragraph_blocks: Sequence[_InfographicTextBlock], note_blocks: Sequence[_InfographicTextBlock]) -> None:
        footer_regions = ("footer_badge", "footer_source", "footer_note")
        for index, block in enumerate(paragraph_blocks[:2]):
            region = "paragraph_left" if int(index) == 0 else "paragraph_right"
            _assign_block(block, _footer_text_slot(footer_bbox, region), region)
        for index, block in enumerate(note_blocks):
            region = footer_regions[int(index) % len(footer_regions)]
            _assign_block(block, _footer_text_slot(footer_bbox, region), region)

    content_bbox = list(default_content)
    footer_bbox = list(default_footer)
    mode = str(native_layout_mode)
    note_blocks = list(small_blocks)

    if mode == "top_right_callout":
        callout = [x1 - 318.0, y0 + 16.0, x1 - 24.0, y0 + 86.0]
        title_box[2] = max(title_box[0] + 360.0, callout[0] - 18.0)
        subtitle_box[2] = title_box[2]
        hero_block = note_blocks.pop(0) if note_blocks else None
        _assign_block(hero_block, callout, "top_right_callout")
        if hero_block is not None:
            hero_block_id = str(hero_block.block_id)
            hero_slot = [callout[0] + 9.0, callout[1] + 8.0, callout[0] + 64.0, callout[3] - 8.0]
            hero_text_box = [callout[0] + 72.0, callout[1] + 5.0, callout[2] - 10.0, callout[3] - 5.0]
        _assign_footer_blocks(footer_bbox, paragraph_blocks=paragraphs, note_blocks=note_blocks)
    elif mode == "top_left_callout":
        callout = [x0 + 24.0, y0 + 16.0, x0 + 318.0, y0 + 86.0]
        title_box[0] = min(title_box[2] - 360.0, callout[2] + 18.0)
        subtitle_box[0] = title_box[0]
        hero_block = note_blocks.pop(0) if note_blocks else None
        _assign_block(hero_block, callout, "top_left_callout")
        if hero_block is not None:
            hero_block_id = str(hero_block.block_id)
            hero_slot = [callout[0] + 9.0, callout[1] + 8.0, callout[0] + 64.0, callout[3] - 8.0]
            hero_text_box = [callout[0] + 72.0, callout[1] + 5.0, callout[2] - 10.0, callout[3] - 5.0]
        _assign_footer_blocks(footer_bbox, paragraph_blocks=paragraphs, note_blocks=note_blocks)
    elif mode in {"left_side_rail", "right_side_rail"}:
        rail_w = min(212.0, max(176.0, (x1 - x0) * 0.20))
        rail_left = x0 + 16.0 if mode == "left_side_rail" else x1 - rail_w - 16.0
        rail_right = rail_left + rail_w
        rail_top = header_bottom + gap
        rail_bottom = y1 - 16.0
        if mode == "left_side_rail":
            content_bbox = [rail_right + gap, rail_top, x1, y1 - footer_h]
        else:
            content_bbox = [x0, rail_top, rail_left - gap, y1 - footer_h]
        footer_bbox = [content_bbox[0], content_bbox[3] + gap * 0.45, content_bbox[2], y1]
        rail_inner = [rail_left, rail_top, rail_right, rail_bottom]
        hero_block = note_blocks.pop(0) if note_blocks else None
        hero_slot_box = [rail_inner[0], rail_inner[1], rail_inner[2], rail_inner[1] + 92.0]
        _assign_block(hero_block, hero_slot_box, f"{mode}_hero_note")
        if hero_block is not None:
            hero_block_id = str(hero_block.block_id)
            hero_slot = [hero_slot_box[0] + 10.0, hero_slot_box[1] + 10.0, hero_slot_box[0] + 58.0, hero_slot_box[1] + 58.0]
            hero_text_box = [hero_slot_box[0] + 12.0, hero_slot_box[1] + 60.0, hero_slot_box[2] - 12.0, hero_slot_box[3] - 8.0]
        paragraph_top = hero_slot_box[3] + gap
        available_h = max(250.0, rail_inner[3] - paragraph_top - gap)
        paragraph_h = min(270.0, (available_h - gap) / 2.0)
        for index, block in enumerate(paragraphs[:2]):
            py0 = paragraph_top + float(index) * (paragraph_h + gap)
            _assign_block(block, [rail_inner[0], py0, rail_inner[2], py0 + paragraph_h], f"{mode}_paragraph_{index + 1}")
        _assign_footer_blocks(footer_bbox, paragraph_blocks=(), note_blocks=note_blocks)
    elif mode == "poster_anchor_strip":
        strip = [x0 + 20.0, header_bottom + gap * 0.35, x1 - 20.0, header_bottom + gap * 0.35 + 108.0]
        content_bbox = [x0, strip[3] + gap, x1, y1 - footer_h]
        footer_bbox = [x0, content_bbox[3] + gap * 0.45, x1, y1]
        hero_block = note_blocks.pop(0) if note_blocks else None
        _assign_block(hero_block, strip, "poster_anchor_strip")
        if hero_block is not None:
            hero_block_id = str(hero_block.block_id)
            hero_slot = [strip[0] + 16.0, strip[1] + 12.0, strip[0] + 102.0, strip[3] - 12.0]
            hero_text_box = [strip[0] + 122.0, strip[1] + 14.0, strip[2] - 18.0, strip[3] - 14.0]
        _assign_footer_blocks(footer_bbox, paragraph_blocks=paragraphs, note_blocks=note_blocks)
    elif mode == "corner_stamp":
        stamp = [x1 - 238.0, y0 + 15.0, x1 - 24.0, y0 + 68.0]
        title_box[2] = max(title_box[0] + 360.0, stamp[0] - 14.0)
        subtitle_box[2] = title_box[2]
        hero_block = note_blocks.pop(0) if note_blocks else None
        _assign_block(hero_block, stamp, "corner_stamp")
        if hero_block is not None:
            hero_block_id = str(hero_block.block_id)
            hero_slot = [stamp[0] + 8.0, stamp[1] + 7.0, stamp[0] + 48.0, stamp[3] - 7.0]
            hero_text_box = [stamp[0] + 56.0, stamp[1] + 5.0, stamp[2] - 8.0, stamp[3] - 5.0]
        _assign_footer_blocks(footer_bbox, paragraph_blocks=paragraphs, note_blocks=note_blocks)
    else:
        mode = "footer_only"
        _assign_footer_blocks(footer_bbox, paragraph_blocks=paragraphs, note_blocks=note_blocks)

    meta = {
        "native_layout_mode": str(mode),
        "title_bbox_px": list(title_box),
        "subtitle_bbox_px": list(subtitle_box),
        "content_bbox_px": list(content_bbox),
        "native_text_footer_bbox_px": list(footer_bbox),
        "native_text_block_slots_px": {str(key): list(value) for key, value in block_slots.items()},
        "native_text_block_regions": dict(block_regions),
        "hero_block_id": hero_block_id,
        "hero_slot_px": list(hero_slot) if hero_slot is not None else None,
        "hero_text_box_px": list(hero_text_box) if hero_text_box is not None else None,
    }
    return _NativeLayoutPlan(
        mode=str(mode),
        title_bbox_px=list(title_box),
        subtitle_bbox_px=list(subtitle_box),
        content_bbox_px=list(content_bbox),
        footer_bbox_px=list(footer_bbox),
        block_slots_px={str(key): list(value) for key, value in block_slots.items()},
        block_regions=dict(block_regions),
        hero_slot_px=list(hero_slot) if hero_slot is not None else None,
        hero_text_box_px=list(hero_text_box) if hero_text_box is not None else None,
        hero_block_id=hero_block_id,
        meta=meta,
    )


def _wrap_text_lines(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    font: Any,
    max_width: float,
) -> List[str]:
    words = str(text).split()
    if not words:
        return [""]
    lines: List[str] = []
    current = str(words[0])
    for word in words[1:]:
        candidate = f"{current} {word}"
        bbox = _text_bbox(draw, (0.0, 0.0), candidate, font, stroke_width=1)
        if float(bbox[2] - bbox[0]) <= float(max_width):
            current = candidate
        else:
            lines.append(str(current))
            current = str(word)
    lines.append(str(current))
    return lines


def _draw_wrapped_fitted_text(
    draw: ImageDraw.ImageDraw,
    *,
    box: Sequence[float],
    text: str,
    max_size_px: int,
    bold: bool,
    fill_rgb: Sequence[int],
    surface_rgbs: Sequence[Sequence[int]],
    instance_seed: int,
    namespace: str,
    role: str,
    stroke_width: int = 1,
    font_family: str | None = None,
) -> List[float]:
    x0, y0, x1, y1 = [float(value) for value in box]
    max_width = max(8.0, x1 - x0)
    max_height = max(8.0, y1 - y0)
    selected_font = None
    selected_lines: List[str] = []
    selected_line_gap = 2.0
    for size_px in range(max(8, int(max_size_px)), 7, -1):
        font = load_font(int(size_px), bold=bool(bold), font_family=font_family)
        lines = _wrap_text_lines(draw, text=str(text), font=font, max_width=max_width * 0.95)
        line_heights = [
            max(
                1.0,
                _text_bbox(draw, (0.0, 0.0), line, font, stroke_width=max(0, int(stroke_width)))[3]
                - _text_bbox(draw, (0.0, 0.0), line, font, stroke_width=max(0, int(stroke_width)))[1],
            )
            for line in lines
        ]
        line_gap = max(2.0, float(size_px) * 0.18)
        total_height = sum(line_heights) + max(0, len(lines) - 1) * line_gap
        if total_height <= max_height * 0.95:
            selected_font = font
            selected_lines = list(lines)
            selected_line_gap = float(line_gap)
            break
    if selected_font is None:
        selected_font = load_font(8, bold=bool(bold), font_family=font_family)
        selected_lines = _wrap_text_lines(draw, text=str(text), font=selected_font, max_width=max_width * 0.95)
        selected_line_gap = 2.0

    current_y = y0
    drawn_bboxes: List[List[float]] = []
    for line in selected_lines:
        draw.text(
            (float(x0), float(current_y)),
            str(line),
            font=selected_font,
            fill=tuple(int(value) for value in fill_rgb),
        )
        bbox = _text_bbox(draw, (float(x0), float(current_y)), str(line), selected_font, stroke_width=0)
        drawn_bboxes.append([float(value) for value in bbox])
        current_y = float(bbox[3]) + selected_line_gap
        if current_y > y1:
            break
    if not drawn_bboxes:
        return [float(x0), float(y0), float(x0), float(y0)]
    return [
        min(bbox[0] for bbox in drawn_bboxes),
        min(bbox[1] for bbox in drawn_bboxes),
        max(bbox[2] for bbox in drawn_bboxes),
        max(bbox[3] for bbox in drawn_bboxes),
    ]


def _draw_native_text_blocks(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    *,
    text_blocks: Sequence[_InfographicTextBlock],
    native_layout: _NativeLayoutPlan,
    hero_asset_selection: PageVisualAssetSelection,
    style: Any,
    font_profile: _MixedFontProfile,
    instance_seed: int,
) -> Tuple[Dict[str, List[float]], List[Dict[str, Any]], Dict[str, List[float]]]:
    text_block_bboxes: Dict[str, List[float]] = {}
    text_block_meta: List[Dict[str, Any]] = []
    decorative_asset_bboxes: Dict[str, List[float]] = {}
    occupied: List[List[float]] = []
    accent_cycle = (
        style.accent_rgb,
        style.header_rgb,
        style.callout_border_rgb,
        style.connector_rgb,
    )

    for index, block in enumerate(text_blocks):
        slot = [float(value) for value in native_layout.block_slots_px.get(str(block.block_id), ())]
        if not slot:
            continue
        while any(_bbox_overlap_area(slot, existing) > 0.0 for existing in occupied):
            slot = [slot[0], slot[1] + 2.0, slot[2], slot[3] + 2.0]
        accent = tuple(int(value) for value in accent_cycle[int(index) % len(accent_cycle)])
        if str(block.kind) == "paragraph_note":
            fill = _blend_rgb((246, 249, 252), accent, 0.07)
            outline = _blend_rgb(style.panel_border_rgb, accent, 0.28)
            radius = 10
        elif str(block.kind) == "source_line":
            fill = _blend_rgb(style.surface_rgb, style.surface_alt_rgb, 0.45)
            outline = _blend_rgb(style.guide_rgb, accent, 0.12)
            radius = 5
        elif str(block.kind) == "badge_note":
            fill = _blend_rgb(style.callout_fill_rgb, accent, 0.20)
            outline = _blend_rgb(style.callout_border_rgb, accent, 0.24)
            radius = 14
        else:
            fill = _blend_rgb(style.panel_fill_rgb, accent, 0.10)
            outline = _blend_rgb(style.panel_border_rgb, accent, 0.22)
            radius = 8
        draw.rounded_rectangle(
            tuple(slot),
            radius=int(radius),
            fill=fill,
            outline=outline,
            width=1,
        )
        if str(block.kind) == "paragraph_note":
            draw.rectangle((slot[0] + 8.0, slot[1] + 9.0, slot[0] + 13.0, slot[3] - 9.0), fill=accent)
            draw.line((slot[0] + 24.0, slot[1] + 15.0, slot[2] - 14.0, slot[1] + 15.0), fill=outline, width=1)
            text_box = (slot[0] + 24.0, slot[1] + 23.0, slot[2] - 14.0, slot[3] - 12.0)
            block_font_family = str(font_profile.readout_family)
            text_bbox = _draw_wrapped_fitted_text(
                draw,
                box=text_box,
                text=str(block.text),
                max_size_px=16,
                bold=True,
                fill_rgb=(10, 14, 22),
                surface_rgbs=(fill, style.surface_rgb),
                instance_seed=int(instance_seed),
                namespace=f"{MIXED_INFOGRAPHIC_TASK_ID}.{block.block_id}.native_text",
                role="mixed_infographic_native_context_text",
                stroke_width=1,
                font_family=block_font_family,
            )
        elif native_layout.hero_block_id == str(block.block_id) and native_layout.hero_slot_px is not None:
            decorative_asset_bboxes["hero_anchor"] = _draw_visual_asset(
                image,
                selection=hero_asset_selection,
                bbox=native_layout.hero_slot_px,
                tint_rgb=accent,
                opacity=0.94,
            )
            text_box = tuple(native_layout.hero_text_box_px or [slot[0] + 12.0, slot[1] + 5.0, slot[2] - 10.0, slot[3] - 5.0])
            block_font_family = str(font_profile.accent_context_family)
            text_bbox = _draw_fitted_text(
                draw,
                box=text_box,
                text=str(block.text),
                max_size_px=13,
                bold=str(block.kind) in {"summary_note", "callout_quote"},
                fill_rgb=style.text_rgb,
                surface_rgbs=(fill, style.surface_rgb),
                instance_seed=int(instance_seed),
                namespace=f"{MIXED_INFOGRAPHIC_TASK_ID}.{block.block_id}.native_text",
                role="mixed_infographic_native_context_text",
                align="left",
                stroke_width=1,
                font_family=block_font_family,
            )
        elif str(block.kind) == "badge_note":
            draw.ellipse(
                (slot[0] + 7.0, slot[1] + 8.0, slot[0] + 19.0, slot[1] + 20.0),
                fill=accent,
            )
            text_box = (slot[0] + 25.0, slot[1] + 4.0, slot[2] - 8.0, slot[3] - 4.0)
            block_font_family = str(font_profile.accent_context_family)
            text_bbox = _draw_fitted_text(
                draw,
                box=text_box,
                text=str(block.text),
                max_size_px=12,
                bold=True,
                fill_rgb=style.text_rgb,
                surface_rgbs=(fill, style.surface_rgb),
                instance_seed=int(instance_seed),
                namespace=f"{MIXED_INFOGRAPHIC_TASK_ID}.{block.block_id}.native_text",
                role="mixed_infographic_native_context_text",
                align="center",
                stroke_width=1,
                font_family=block_font_family,
            )
        else:
            draw.rectangle((slot[0] + 7.0, slot[1] + 7.0, slot[0] + 10.0, slot[3] - 7.0), fill=accent)
            text_box = (slot[0] + 16.0, slot[1] + 4.0, slot[2] - 8.0, slot[3] - 4.0)
            block_font_family = str(font_profile.accent_context_family)
            text_bbox = _draw_fitted_text(
                draw,
                box=text_box,
                text=str(block.text),
                max_size_px=12,
                bold=str(block.kind) in {"summary_note", "callout_quote"},
                fill_rgb=style.muted_text_rgb if str(block.kind) == "source_line" else style.text_rgb,
                surface_rgbs=(fill, style.surface_rgb),
                instance_seed=int(instance_seed),
                namespace=f"{MIXED_INFOGRAPHIC_TASK_ID}.{block.block_id}.native_text",
                role="mixed_infographic_native_context_text",
                align="left",
                stroke_width=1,
                font_family=block_font_family,
            )
        bbox = [float(value) for value in slot]
        text_block_bboxes[str(block.block_id)] = list(bbox)
        occupied.append(list(bbox))
        text_block_meta.append(
            {
                "block_id": str(block.block_id),
                "kind": str(block.kind),
                "text": str(block.text),
                "placement_region": str(native_layout.block_regions.get(str(block.block_id), block.placement_region)),
                "font_role": str(block.font_role),
                "font_family": str(block_font_family),
                "bbox_px": list(bbox),
                "text_bbox_px": [float(value) for value in text_bbox],
                "fill_rgb": [int(value) for value in fill],
                "outline_rgb": [int(value) for value in outline],
            }
        )
    return text_block_bboxes, text_block_meta, decorative_asset_bboxes


def _draw_module_shell(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    title: str,
    accent_rgb: Sequence[int],
    module_kind: str,
    style: Any,
    render_params: _RenderParams,
    instance_seed: int,
    module_id: str,
    font_profile: _MixedFontProfile,
) -> Tuple[List[float], List[float]]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    fill = _module_surface_rgb(style, accent_rgb, str(module_id))
    border = tuple(int(value) for value in style.panel_border_rgb)
    header_h = min(46.0, max(34.0, (y1 - y0) * 0.16))
    header_fill = darken_surface_for_light_text(_blend_rgb(style.header_rgb, accent_rgb, 0.22))

    if str(module_kind) in {"radial_bubbles", "ring_summary"}:
        draw.ellipse(
            (x0, y0, x1, y1),
            fill=fill,
            outline=border,
            width=max(1, int(render_params.outline_width_px)),
        )
        inset = min(18.0, max(8.0, (x1 - x0) * 0.04))
        draw.ellipse(
            (x0 + inset, y0 + inset, x1 - inset, y1 - inset),
            outline=_blend_rgb(fill, accent_rgb, 0.32),
            width=2,
        )
        title_box = (x0 + 25.0, y0 + 10.0, x1 - 25.0, y0 + header_h + 5.0)
        draw.rounded_rectangle(
            title_box,
            radius=max(10, int(render_params.corner_radius_px) + 4),
            fill=header_fill,
        )
        title_text_box = (title_box[0] + 8.0, title_box[1] + 4.0, title_box[2] - 8.0, title_box[3] - 4.0)
    else:
        radius = max(0, int(render_params.corner_radius_px))
        if str(module_kind) == "callout_stats":
            radius += 10
        draw.rounded_rectangle(
            (x0, y0, x1, y1),
            radius=radius,
            fill=fill,
            outline=border,
            width=max(1, int(render_params.outline_width_px)),
        )
        if str(module_kind) == "timeline_snippet":
            draw.polygon(
                (
                    (x1 - 54.0, y0),
                    (x1, y0),
                    (x1, y0 + 54.0),
                    (x1 - 28.0, y0 + 32.0),
                ),
                fill=_blend_rgb(fill, accent_rgb, 0.28),
            )
        elif str(module_kind) == "profile_cards":
            draw.ellipse(
                (x1 - 76.0, y1 - 76.0, x1 - 18.0, y1 - 18.0),
                outline=_blend_rgb(fill, accent_rgb, 0.30),
                width=3,
            )
        draw.rounded_rectangle(
            (x0, y0, x1, y0 + header_h),
            radius=radius,
            fill=header_fill,
        )
        draw.rectangle((x0, y0 + header_h - 5.0, x1, y0 + header_h), fill=header_fill)
        draw.rectangle((x0, y0, x0 + 7.0, y1), fill=tuple(int(value) for value in accent_rgb))
        title_text_box = (x0 + 16.0, y0 + 5.0, x1 - 12.0, y0 + header_h - 5.0)

    title_bbox = _draw_fitted_text(
        draw,
        box=title_text_box,
        text=str(title),
        max_size_px=int(render_params.module_title_font_size_px),
        bold=True,
        fill_rgb=style.header_text_rgb,
        surface_rgbs=(header_fill,),
        instance_seed=int(instance_seed),
        namespace=f"{MIXED_INFOGRAPHIC_TASK_ID}.{module_id}.title",
        role="mixed_infographic_module_title",
        stroke_width=1,
        font_family=str(font_profile.module_title_families_by_id.get(str(module_id), font_profile.section_header_family)),
    )
    return [float(x0), float(y0), float(x1), float(y1)], [float(value) for value in title_bbox]


def _draw_table_like_module(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    *,
    module: _MixedModule,
    bbox: Sequence[float],
    header_height: float,
    style: Any,
    render_params: _RenderParams,
    instance_seed: int,
    font_profile: _MixedFontProfile,
) -> Tuple[Dict[str, List[float]], Dict[str, List[float]], Dict[str, Dict[str, List[float]]], Dict[str, List[float]]]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    pad = 10.0
    top = y0 + float(header_height) + pad
    left = x0 + pad + 4.0
    right = x1 - pad
    bottom = y1 - pad
    field_h = min(28.0, max(18.0, (bottom - top) * 0.16))
    row_count = max(1, len(module.items))
    row_h = max(14.0, (bottom - top - field_h) / float(row_count))
    label_col_w = min((right - left) * 0.42, 118.0)
    field_w = max(34.0, (right - left - label_col_w) / float(max(1, len(module.fields))))
    guide_rgb = tuple(int(value) for value in style.guide_rgb)
    item_bboxes: Dict[str, List[float]] = {}
    field_bboxes: Dict[str, List[float]] = {}
    value_bboxes: Dict[str, Dict[str, List[float]]] = {}
    icon_bboxes: Dict[str, List[float]] = {}

    draw.rectangle((left, top, right, top + field_h), fill=_blend_rgb(style.surface_alt_rgb, style.accent_rgb, 0.08))
    for field_index, field in enumerate(module.fields):
        fx0 = left + label_col_w + float(field_index) * field_w
        fx1 = fx0 + field_w
        field_bboxes[str(field.field_id)] = _draw_fitted_text(
            draw,
            box=(fx0 + 3.0, top + 3.0, fx1 - 3.0, top + field_h - 3.0),
            text=str(field.label),
            max_size_px=int(render_params.field_font_size_px),
            bold=True,
            fill_rgb=style.muted_text_rgb,
            surface_rgbs=(style.surface_alt_rgb, style.panel_fill_rgb),
            instance_seed=int(instance_seed),
            namespace=f"{MIXED_INFOGRAPHIC_TASK_ID}.{module.module_id}.{field.field_id}.field",
            role="mixed_infographic_field_label",
            align="center",
            stroke_width=1,
            font_family=str(font_profile.readout_family),
        )
        draw.line((fx0, top, fx0, bottom), fill=guide_rgb, width=1)
    draw.line((left, top + field_h, right, top + field_h), fill=guide_rgb, width=1)

    for item_index, item in enumerate(module.items):
        row_top = top + field_h + float(item_index) * row_h
        row_bottom = min(bottom, row_top + row_h)
        if item_index % 2 == 0:
            draw.rectangle((left, row_top, right, row_bottom), fill=_blend_rgb(style.panel_fill_rgb, style.surface_alt_rgb, 0.28))
        icon_box = (left + 3.0, row_top + 5.0, left + 23.0, row_bottom - 5.0)
        icon_bboxes[str(item.item_id)] = _draw_visual_asset(
            image,
            selection=item.visual_asset_selection,
            bbox=icon_box,
            tint_rgb=module.accent_rgb,
        )
        item_bboxes[str(item.item_id)] = _draw_fitted_text(
            draw,
            box=(left + 28.0, row_top + 4.0, left + label_col_w - 5.0, row_bottom - 4.0),
            text=str(item.label),
            max_size_px=int(render_params.label_font_size_px),
            bold=True,
            fill_rgb=style.text_rgb,
            surface_rgbs=(style.panel_fill_rgb, style.surface_alt_rgb),
            instance_seed=int(instance_seed),
            namespace=f"{MIXED_INFOGRAPHIC_TASK_ID}.{module.module_id}.{item.item_id}.item",
            role="mixed_infographic_item_label",
            stroke_width=1,
            font_family=str(font_profile.readout_family),
        )
        value_bboxes[str(item.item_id)] = {}
        for field_index, field in enumerate(module.fields):
            fx0 = left + label_col_w + float(field_index) * field_w
            fx1 = fx0 + field_w
            value = str(item.values_by_field_id[str(field.field_id)])
            value_bboxes[str(item.item_id)][str(field.field_id)] = _draw_fitted_text(
                draw,
                box=(fx0 + 4.0, row_top + 4.0, fx1 - 4.0, row_bottom - 4.0),
                text=value,
                max_size_px=int(render_params.value_font_size_px),
                bold=True,
                fill_rgb=style.text_rgb,
                surface_rgbs=(style.panel_fill_rgb, style.surface_alt_rgb),
                instance_seed=int(instance_seed),
                namespace=f"{MIXED_INFOGRAPHIC_TASK_ID}.{module.module_id}.{item.item_id}.{field.field_id}.value",
                role="mixed_infographic_value_cell",
                align="center",
                stroke_width=1,
                font_family=str(font_profile.readout_family),
            )
        draw.line((left, row_bottom, right, row_bottom), fill=guide_rgb, width=1)
    return item_bboxes, field_bboxes, value_bboxes, icon_bboxes


def _draw_card_like_module(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    *,
    module: _MixedModule,
    bbox: Sequence[float],
    header_height: float,
    style: Any,
    render_params: _RenderParams,
    instance_seed: int,
    font_profile: _MixedFontProfile,
) -> Tuple[Dict[str, List[float]], Dict[str, List[float]], Dict[str, Dict[str, List[float]]], Dict[str, List[float]]]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    pad = 10.0
    top = y0 + float(header_height) + pad
    left = x0 + pad + 4.0
    right = x1 - pad
    bottom = y1 - pad
    chip_h = min(24.0, max(18.0, (bottom - top) * 0.16))
    chip_w = (right - left - max(0, len(module.fields) - 1) * 6.0) / float(max(1, len(module.fields)))
    item_bboxes: Dict[str, List[float]] = {}
    field_bboxes: Dict[str, List[float]] = {}
    value_bboxes: Dict[str, Dict[str, List[float]]] = {}
    icon_bboxes: Dict[str, List[float]] = {}

    for field_index, field in enumerate(module.fields):
        cx0 = left + float(field_index) * (chip_w + 6.0)
        cx1 = cx0 + chip_w
        draw.rounded_rectangle(
            (cx0, top, cx1, top + chip_h),
            radius=5,
            fill=_blend_rgb(style.callout_fill_rgb, module.accent_rgb, 0.10),
            outline=tuple(int(value) for value in style.callout_border_rgb),
            width=1,
        )
        field_bboxes[str(field.field_id)] = _draw_fitted_text(
            draw,
            box=(cx0 + 5.0, top + 3.0, cx1 - 5.0, top + chip_h - 3.0),
            text=str(field.label),
            max_size_px=int(render_params.field_font_size_px),
            bold=True,
            fill_rgb=style.muted_text_rgb,
            surface_rgbs=(style.callout_fill_rgb, style.panel_fill_rgb),
            instance_seed=int(instance_seed),
            namespace=f"{MIXED_INFOGRAPHIC_TASK_ID}.{module.module_id}.{field.field_id}.field",
            role="mixed_infographic_field_label",
            align="center",
            stroke_width=1,
            font_family=str(font_profile.readout_family),
        )

    card_top = top + chip_h + 8.0
    cols = 2 if len(module.items) > 2 and (right - left) > 250.0 else 1
    rows = max(1, int(math.ceil(float(len(module.items)) / float(cols))))
    card_w = (right - left - (cols - 1) * 8.0) / float(cols)
    card_h = max(22.0, (bottom - card_top - (rows - 1) * 8.0) / float(rows))
    for item_index, item in enumerate(module.items):
        row = int(item_index // cols)
        col = int(item_index % cols)
        cx0 = left + float(col) * (card_w + 8.0)
        cy0 = card_top + float(row) * (card_h + 8.0)
        cx1 = cx0 + card_w
        if cy0 >= bottom:
            cy0 = max(card_top, bottom - card_h)
        cy1 = min(bottom, cy0 + card_h)
        draw.rounded_rectangle(
            (cx0, cy0, cx1, cy1),
            radius=7,
            fill=_blend_rgb(style.panel_fill_rgb, style.surface_alt_rgb, 0.45),
            outline=tuple(int(value) for value in style.guide_rgb),
            width=1,
        )
        icon_bboxes[str(item.item_id)] = _draw_visual_asset(
            image,
            selection=item.visual_asset_selection,
            bbox=(cx0 + 6.0, cy0 + 6.0, cx0 + 26.0, cy0 + 26.0),
            tint_rgb=module.accent_rgb,
        )
        label_y0 = cy0 + 5.0
        value_bottom = max(cy0 + 18.0, cy1 - 4.0)
        value_top = min(
            value_bottom - 10.0,
            max(label_y0 + 18.0, min(cy1 - 16.0, cy0 + card_h * 0.58)),
        )
        label_y1 = min(value_top - 8.0, cy0 + 24.0)
        if label_y1 < label_y0 + 8.0:
            label_y1 = label_y0 + 8.0
            value_top = max(value_top, label_y1 + 8.0)

        item_bboxes[str(item.item_id)] = _draw_fitted_text(
            draw,
            box=(cx0 + 31.0, label_y0, cx1 - 6.0, label_y1),
            text=str(item.label),
            max_size_px=int(render_params.label_font_size_px),
            bold=True,
            fill_rgb=style.text_rgb,
            surface_rgbs=(style.panel_fill_rgb, style.surface_alt_rgb),
            instance_seed=int(instance_seed),
            namespace=f"{MIXED_INFOGRAPHIC_TASK_ID}.{module.module_id}.{item.item_id}.item",
            role="mixed_infographic_item_label",
            stroke_width=1,
            font_family=str(font_profile.readout_family),
        )
        value_bboxes[str(item.item_id)] = {}
        value_gap = 4.0
        field_count = max(1, len(module.fields))
        value_w = max(18.0, (cx1 - cx0 - 14.0 - value_gap * float(field_count - 1)) / float(field_count))
        for field_index, field in enumerate(module.fields):
            vx0 = cx0 + 7.0 + float(field_index) * (value_w + value_gap)
            vx1 = min(cx1 - 7.0, vx0 + value_w)
            value = str(item.values_by_field_id[str(field.field_id)])
            value_bboxes[str(item.item_id)][str(field.field_id)] = _draw_fitted_text(
                draw,
                box=(vx0, value_top, vx1, value_bottom),
                text=value,
                max_size_px=int(render_params.value_font_size_px),
                bold=True,
                fill_rgb=style.text_rgb,
                surface_rgbs=(style.panel_fill_rgb, style.surface_alt_rgb),
                instance_seed=int(instance_seed),
                namespace=f"{MIXED_INFOGRAPHIC_TASK_ID}.{module.module_id}.{item.item_id}.{field.field_id}.value",
                role="mixed_infographic_value_cell",
                align="center",
                stroke_width=1,
                font_family=str(font_profile.readout_family),
            )
    return item_bboxes, field_bboxes, value_bboxes, icon_bboxes


def _draw_radial_like_module(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    *,
    module: _MixedModule,
    bbox: Sequence[float],
    header_height: float,
    style: Any,
    render_params: _RenderParams,
    instance_seed: int,
    font_profile: _MixedFontProfile,
) -> Tuple[Dict[str, List[float]], Dict[str, List[float]], Dict[str, Dict[str, List[float]]], Dict[str, List[float]]]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    width = x1 - x0
    height = y1 - y0
    left = x0 + max(22.0, width * 0.10)
    right = x1 - max(22.0, width * 0.10)
    top = y0 + float(header_height) + max(16.0, height * 0.06)
    bottom = y1 - max(18.0, height * 0.09)
    center_x = (left + right) / 2.0
    field_count = max(1, len(module.fields))
    item_count = max(1, len(module.items))
    item_bboxes: Dict[str, List[float]] = {}
    field_bboxes: Dict[str, List[float]] = {}
    value_bboxes: Dict[str, Dict[str, List[float]]] = {}
    icon_bboxes: Dict[str, List[float]] = {}
    surface_rgb = _module_surface_rgb(style, module.accent_rgb, str(module.module_id))

    chip_gap = 7.0
    chip_h = 24.0
    chip_w = min(92.0, max(54.0, (right - left - chip_gap * float(field_count - 1)) / float(field_count)))
    chip_total_w = chip_w * float(field_count) + chip_gap * float(field_count - 1)
    chip_left = center_x - chip_total_w / 2.0
    for field_index, field in enumerate(module.fields):
        cx0 = chip_left + float(field_index) * (chip_w + chip_gap)
        cy0 = top
        cx1 = cx0 + chip_w
        cy1 = cy0 + chip_h
        chip_fill = _blend_rgb(style.callout_fill_rgb, module.accent_rgb, 0.15 + 0.04 * float(field_index % 2))
        draw.rounded_rectangle(
            (cx0, cy0, cx1, cy1),
            radius=12,
            fill=chip_fill,
            outline=_blend_rgb(style.callout_border_rgb, module.accent_rgb, 0.18),
            width=1,
        )
        field_bboxes[str(field.field_id)] = _draw_fitted_text(
            draw,
            box=(cx0 + 5.0, cy0 + 3.0, cx1 - 5.0, cy1 - 3.0),
            text=str(field.label),
            max_size_px=int(render_params.field_font_size_px),
            bold=True,
            fill_rgb=style.muted_text_rgb,
            surface_rgbs=(chip_fill, surface_rgb),
            instance_seed=int(instance_seed),
            namespace=f"{MIXED_INFOGRAPHIC_TASK_ID}.{module.module_id}.{field.field_id}.field",
            role="mixed_infographic_field_label",
            align="center",
            stroke_width=1,
            font_family=str(font_profile.readout_family),
        )

    bubble_area_top = top + chip_h + 12.0
    bubble_area_h = max(18.0, bottom - bubble_area_top)
    cols = 1 if item_count == 1 else 2
    rows = int(math.ceil(float(item_count) / float(cols)))
    bubble_gap = min(10.0, max(3.0, bubble_area_h * 0.08))
    cell_w = max(34.0, (right - left - bubble_gap * float(cols - 1)) / float(cols))
    cell_h = max(10.0, (bubble_area_h - bubble_gap * float(rows - 1)) / float(rows))
    bubble_w = min(cell_w * 0.92, 148.0)
    bubble_h = min(cell_h * 0.88, 112.0)

    for item_index, item in enumerate(module.items):
        row = int(item_index // cols)
        col = int(item_index % cols)
        cell_x0 = left + float(col) * (cell_w + bubble_gap)
        cell_y0 = bubble_area_top + float(row) * (cell_h + bubble_gap)
        cell_x1 = cell_x0 + cell_w
        cell_y1 = min(bottom, cell_y0 + cell_h)
        if item_count == 3 and item_index == 2:
            cell_x0 = left + (right - left - cell_w) / 2.0
            cell_x1 = cell_x0 + cell_w
        cx = (cell_x0 + cell_x1) / 2.0
        cy = (cell_y0 + cell_y1) / 2.0
        bx0 = max(cell_x0, cx - bubble_w / 2.0)
        by0 = max(cell_y0, cy - bubble_h / 2.0)
        bx1 = min(right, bx0 + bubble_w)
        by1 = min(bottom, by0 + bubble_h)
        bx0 = max(cell_x0, bx1 - bubble_w)
        by0 = max(cell_y0, by1 - bubble_h)
        bubble_fill = _blend_rgb(surface_rgb, module.accent_rgb, 0.10 + 0.05 * float(item_index % 3))
        outline = _blend_rgb(style.panel_border_rgb, module.accent_rgb, 0.28)
        if str(module.kind) == "ring_summary":
            draw.rounded_rectangle((bx0, by0, bx1, by1), radius=18, fill=bubble_fill, outline=outline, width=1)
            draw.arc((bx0 + 5.0, by0 + 5.0, bx1 - 5.0, by1 - 5.0), 205, 338, fill=tuple(int(value) for value in module.accent_rgb), width=3)
        else:
            draw.ellipse((bx0, by0, bx1, by1), fill=bubble_fill, outline=outline, width=1)

        value_gap = 5.0
        value_band_h = min(22.0, max(10.0, bubble_h * 0.24))
        value_bottom = by1 - max(5.0, bubble_h * 0.08)
        value_top = max(by0 + 28.0, value_bottom - value_band_h)
        label_y0 = by0 + 7.0
        label_bottom = min(value_top - 5.0, by0 + max(20.0, bubble_h * 0.48))
        label_bottom = max(label_y0 + 8.0, label_bottom)
        icon_size = min(15.0, max(8.0, bubble_h * 0.15))
        icon_y0 = by0 + max(6.0, bubble_h * 0.09)
        icon_bboxes[str(item.item_id)] = _draw_visual_asset(
            image,
            selection=item.visual_asset_selection,
            bbox=(bx0 + 12.0, icon_y0, bx0 + 12.0 + icon_size, icon_y0 + icon_size),
            tint_rgb=module.accent_rgb,
        )
        item_bboxes[str(item.item_id)] = _draw_fitted_text(
            draw,
            box=(bx0 + 30.0, label_y0, bx1 - 12.0, label_bottom),
            text=str(item.label),
            max_size_px=int(render_params.label_font_size_px),
            bold=True,
            fill_rgb=style.text_rgb,
            surface_rgbs=(bubble_fill, surface_rgb),
            instance_seed=int(instance_seed),
            namespace=f"{MIXED_INFOGRAPHIC_TASK_ID}.{module.module_id}.{item.item_id}.item",
            role="mixed_infographic_item_label",
            align="center",
            stroke_width=1,
            font_family=str(font_profile.readout_family),
        )
        value_bboxes[str(item.item_id)] = {}
        value_w = max(9.0, (bx1 - bx0 - 20.0 - value_gap * float(field_count - 1)) / float(field_count))
        value_left = bx0 + 10.0
        for field_index, field in enumerate(module.fields):
            vx0 = value_left + float(field_index) * (value_w + value_gap)
            vx1 = max(vx0 + 8.0, min(bx1 - 8.0, vx0 + value_w))
            vy0 = value_top
            vy1 = max(vy0 + 8.0, value_bottom)
            value_fill = _blend_rgb(style.panel_fill_rgb, module.accent_rgb, 0.08)
            draw.rounded_rectangle(
                (vx0, vy0, vx1, vy1),
                radius=8,
                fill=value_fill,
                outline=_blend_rgb(style.guide_rgb, module.accent_rgb, 0.16),
                width=1,
            )
            value_bboxes[str(item.item_id)][str(field.field_id)] = _draw_fitted_text(
                draw,
                box=(vx0 + 4.0, vy0 + 2.0, vx1 - 4.0, vy1 - 2.0),
                text=str(item.values_by_field_id[str(field.field_id)]),
                max_size_px=int(render_params.value_font_size_px),
                bold=True,
                fill_rgb=style.text_rgb,
                surface_rgbs=(value_fill, bubble_fill),
                instance_seed=int(instance_seed),
                namespace=f"{MIXED_INFOGRAPHIC_TASK_ID}.{module.module_id}.{item.item_id}.{field.field_id}.value",
                role="mixed_infographic_value_cell",
                align="center",
                stroke_width=1,
                font_family=str(font_profile.readout_family),
            )
    return item_bboxes, field_bboxes, value_bboxes, icon_bboxes


def _draw_row_like_module(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    *,
    module: _MixedModule,
    bbox: Sequence[float],
    header_height: float,
    style: Any,
    render_params: _RenderParams,
    instance_seed: int,
    font_profile: _MixedFontProfile,
) -> Tuple[Dict[str, List[float]], Dict[str, List[float]], Dict[str, Dict[str, List[float]]], Dict[str, List[float]]]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    pad = 10.0
    top = y0 + float(header_height) + pad
    left = x0 + pad + 4.0
    right = x1 - pad
    bottom = y1 - pad
    item_bboxes: Dict[str, List[float]] = {}
    field_bboxes: Dict[str, List[float]] = {}
    value_bboxes: Dict[str, Dict[str, List[float]]] = {}
    icon_bboxes: Dict[str, List[float]] = {}
    field_h = min(22.0, max(16.0, (bottom - top) * 0.14))
    label_w = min(128.0, (right - left) * 0.44)
    field_w = max(32.0, (right - left - label_w) / float(max(1, len(module.fields))))
    for field_index, field in enumerate(module.fields):
        fx0 = left + label_w + float(field_index) * field_w
        fx1 = fx0 + field_w
        field_bboxes[str(field.field_id)] = _draw_fitted_text(
            draw,
            box=(fx0 + 3.0, top, fx1 - 3.0, top + field_h),
            text=str(field.label),
            max_size_px=int(render_params.field_font_size_px),
            bold=True,
            fill_rgb=style.muted_text_rgb,
            surface_rgbs=(style.panel_fill_rgb,),
            instance_seed=int(instance_seed),
            namespace=f"{MIXED_INFOGRAPHIC_TASK_ID}.{module.module_id}.{field.field_id}.field",
            role="mixed_infographic_field_label",
            align="center",
            stroke_width=1,
            font_family=str(font_profile.readout_family),
        )
    row_top = top + field_h + 3.0
    row_h = max(15.0, (bottom - row_top) / float(max(1, len(module.items))))
    for item_index, item in enumerate(module.items):
        yy0 = row_top + float(item_index) * row_h
        yy1 = min(bottom, yy0 + row_h - 2.0)
        if str(module.kind) == "ranked_list":
            draw.ellipse((left + 2.0, yy0 + 5.0, left + 25.0, yy0 + 28.0), fill=tuple(int(value) for value in module.accent_rgb))
            icon_bboxes[str(item.item_id)] = _draw_visual_asset(
                image,
                selection=item.visual_asset_selection,
                bbox=(left + 6.0, yy0 + 8.0, left + 21.0, yy0 + 25.0),
                tint_rgb=(255, 255, 255),
            )
        elif str(module.kind) == "timeline_snippet":
            cx = left + 14.0
            cy = yy0 + max(10.0, (yy1 - yy0) / 2.0)
            draw.line((cx, row_top, cx, bottom), fill=tuple(int(value) for value in style.connector_rgb), width=2)
            draw.ellipse((cx - 7.0, cy - 7.0, cx + 7.0, cy + 7.0), fill=tuple(int(value) for value in module.accent_rgb))
            icon_bboxes[str(item.item_id)] = _draw_visual_asset(
                image,
                selection=item.visual_asset_selection,
                bbox=(cx - 5.0, cy - 5.0, cx + 5.0, cy + 5.0),
                tint_rgb=(255, 255, 255),
            )
        else:
            icon_bboxes[str(item.item_id)] = _draw_visual_asset(
                image,
                selection=item.visual_asset_selection,
                bbox=(left + 2.0, yy0 + 4.0, left + 26.0, yy1 - 4.0),
                tint_rgb=module.accent_rgb,
            )
        item_bboxes[str(item.item_id)] = _draw_fitted_text(
            draw,
            box=(left + 31.0, yy0 + 3.0, left + label_w - 4.0, yy1 - 3.0),
            text=str(item.label),
            max_size_px=int(render_params.label_font_size_px),
            bold=True,
            fill_rgb=style.text_rgb,
            surface_rgbs=(style.panel_fill_rgb, style.surface_alt_rgb),
            instance_seed=int(instance_seed),
            namespace=f"{MIXED_INFOGRAPHIC_TASK_ID}.{module.module_id}.{item.item_id}.item",
            role="mixed_infographic_item_label",
            stroke_width=1,
            font_family=str(font_profile.readout_family),
        )
        value_bboxes[str(item.item_id)] = {}
        for field_index, field in enumerate(module.fields):
            fx0 = left + label_w + float(field_index) * field_w
            fx1 = fx0 + field_w
            value_bboxes[str(item.item_id)][str(field.field_id)] = _draw_fitted_text(
                draw,
                box=(fx0 + 3.0, yy0 + 3.0, fx1 - 3.0, yy1 - 3.0),
                text=str(item.values_by_field_id[str(field.field_id)]),
                max_size_px=int(render_params.value_font_size_px),
                bold=True,
                fill_rgb=style.text_rgb,
                surface_rgbs=(style.panel_fill_rgb, style.surface_alt_rgb),
                instance_seed=int(instance_seed),
                namespace=f"{MIXED_INFOGRAPHIC_TASK_ID}.{module.module_id}.{item.item_id}.{field.field_id}.value",
                role="mixed_infographic_value_cell",
                align="center",
                stroke_width=1,
                font_family=str(font_profile.readout_family),
            )
        draw.line((left, yy1, right, yy1), fill=tuple(int(value) for value in style.guide_rgb), width=1)
    return item_bboxes, field_bboxes, value_bboxes, icon_bboxes


def _render_mixed_infographic(
    background: Image.Image,
    *,
    spec: _MixedInfographicSpec,
    scene_variant: str,
    native_layout_mode: str,
    style: Any,
    render_params: _RenderParams,
    instance_seed: int,
    font_profile: _MixedFontProfile,
) -> _RenderedMixedInfographic:
    image = background.convert("RGBA")
    draw = ImageDraw.Draw(image)
    margin = float(render_params.outer_margin_px)
    page_bbox = [
        margin,
        margin,
        float(render_params.canvas_width) - margin,
        float(render_params.canvas_height) - margin,
    ]
    draw.rounded_rectangle(
        tuple(page_bbox),
        radius=max(0, int(render_params.corner_radius_px) + 4),
        fill=tuple(int(value) for value in style.surface_rgb),
        outline=tuple(int(value) for value in style.panel_border_rgb),
        width=max(1, int(render_params.outline_width_px)),
    )
    page_backdrops = _draw_page_backdrops(
        draw,
        page_bbox=page_bbox,
        style=style,
        instance_seed=int(instance_seed),
        blend_scale=float(render_params.page_backdrop_blend_scale),
    )
    native_layout = _resolve_native_layout(
        page_bbox=page_bbox,
        render_params=render_params,
        native_layout_mode=str(native_layout_mode),
        text_blocks=spec.text_blocks,
    )
    title_bbox = _draw_fitted_text(
        draw,
        box=native_layout.title_bbox_px,
        text=str(spec.title),
        max_size_px=int(render_params.title_font_size_px),
        bold=True,
        fill_rgb=style.text_rgb,
        surface_rgbs=(style.surface_rgb,),
        instance_seed=int(instance_seed),
        namespace=f"{MIXED_INFOGRAPHIC_TASK_ID}.page_title",
        role="mixed_infographic_page_title",
        stroke_width=1,
        font_family=str(font_profile.section_header_family),
    )
    _draw_fitted_text(
        draw,
        box=native_layout.subtitle_bbox_px,
        text=str(spec.subtitle),
        max_size_px=int(render_params.subtitle_font_size_px),
        bold=False,
        fill_rgb=style.muted_text_rgb,
        surface_rgbs=(style.surface_rgb,),
        instance_seed=int(instance_seed),
        namespace=f"{MIXED_INFOGRAPHIC_TASK_ID}.page_subtitle",
        role="mixed_infographic_page_subtitle",
        stroke_width=1,
        font_family=str(font_profile.readout_family),
    )
    slots, layout_meta = _layout_slots(
        render_params=render_params,
        scene_variant=str(scene_variant),
        module_count=len(spec.modules),
        instance_seed=int(instance_seed),
        content_bbox=native_layout.content_bbox_px,
        footer_bbox=native_layout.footer_bbox_px,
    )
    layout_meta["page_backdrops"] = list(page_backdrops)
    layout_meta.update(dict(native_layout.meta))
    module_bboxes: Dict[str, List[float]] = {}
    module_title_bboxes: Dict[str, List[float]] = {}
    item_label_bboxes: Dict[str, Dict[str, List[float]]] = {}
    field_label_bboxes: Dict[str, Dict[str, List[float]]] = {}
    value_cell_bboxes: Dict[str, Dict[str, Dict[str, List[float]]]] = {}
    icon_bboxes: Dict[str, Dict[str, List[float]]] = {}
    section_asset_bboxes: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = []

    for module, slot in zip(spec.modules, slots):
        header_h = min(46.0, max(34.0, (float(slot[3]) - float(slot[1])) * 0.16))
        module_bbox, title_box = _draw_module_shell(
            draw,
            bbox=slot,
            title=str(module.title),
            accent_rgb=module.accent_rgb,
            module_kind=str(module.kind),
            style=style,
            render_params=render_params,
            instance_seed=int(instance_seed),
            module_id=str(module.module_id),
            font_profile=font_profile,
        )
        section_asset_bboxes[str(module.module_id)] = _draw_module_section_asset(
            image,
            module=module,
            bbox=slot,
            header_height=header_h,
            opacity=0.17 if str(module.section_asset_selection.asset.render_mode) == "color" else 0.22,
        )
        if str(module.kind) in {"radial_bubbles", "ring_summary"}:
            item_boxes, field_boxes, value_boxes, icon_boxes = _draw_radial_like_module(
                image,
                draw,
                module=module,
                bbox=slot,
                header_height=header_h,
                style=style,
                render_params=render_params,
                instance_seed=int(instance_seed),
                font_profile=font_profile,
            )
        elif str(module.kind) in {"profile_cards", "callout_stats"}:
            item_boxes, field_boxes, value_boxes, icon_boxes = _draw_card_like_module(
                image,
                draw,
                module=module,
                bbox=slot,
                header_height=header_h,
                style=style,
                render_params=render_params,
                instance_seed=int(instance_seed),
                font_profile=font_profile,
            )
        elif str(module.kind) in {"icon_metric_list", "ranked_list", "timeline_snippet"}:
            item_boxes, field_boxes, value_boxes, icon_boxes = _draw_row_like_module(
                image,
                draw,
                module=module,
                bbox=slot,
                header_height=header_h,
                style=style,
                render_params=render_params,
                instance_seed=int(instance_seed),
                font_profile=font_profile,
            )
        else:
            item_boxes, field_boxes, value_boxes, icon_boxes = _draw_table_like_module(
                image,
                draw,
                module=module,
                bbox=slot,
                header_height=header_h,
                style=style,
                render_params=render_params,
                instance_seed=int(instance_seed),
                font_profile=font_profile,
            )
        module_bboxes[str(module.module_id)] = [float(value) for value in module_bbox]
        module_title_bboxes[str(module.module_id)] = [float(value) for value in title_box]
        item_label_bboxes[str(module.module_id)] = dict(item_boxes)
        field_label_bboxes[str(module.module_id)] = dict(field_boxes)
        value_cell_bboxes[str(module.module_id)] = {str(item_id): dict(fields) for item_id, fields in value_boxes.items()}
        icon_bboxes[str(module.module_id)] = dict(icon_boxes)
        entities.append(
            {
                "entity_id": str(module.module_id),
                "kind": "mixed_infographic_module",
                "module_kind": str(module.kind),
                "title": str(module.title),
                "bbox_px": [float(value) for value in module_bbox],
                "title_bbox_px": [float(value) for value in title_box],
                "accent_rgb": [int(value) for value in module.accent_rgb],
                "section_visual_asset_id": str(module.section_asset_selection.asset.asset_id),
                "section_visual_asset_bbox_px": [float(value) for value in section_asset_bboxes[str(module.module_id)]],
                "fields": [
                    {
                        "field_id": str(field.field_id),
                        "label": str(field.label),
                        "bbox_px": [float(value) for value in field_boxes[str(field.field_id)]],
                    }
                    for field in module.fields
                ],
                "items": [
                    {
                        "item_id": str(item.item_id),
                        "label": str(item.label),
                        "visual_asset_id": str(item.visual_asset_selection.asset.asset_id),
                        "visual_asset_source_id": str(item.visual_asset_selection.asset.source_id),
                        "label_bbox_px": [float(value) for value in item_boxes[str(item.item_id)]],
                        "visual_asset_bbox_px": [float(value) for value in icon_boxes[str(item.item_id)]],
                        "values": [
                            {
                                "field_id": str(field.field_id),
                                "field_label": str(field.label),
                                "value": str(item.values_by_field_id[str(field.field_id)]),
                                "bbox_px": [
                                    float(value)
                                    for value in value_boxes[str(item.item_id)][str(field.field_id)]
                                ],
                            }
                            for field in module.fields
                        ],
                    }
                    for item in module.items
                ],
            }
        )

    text_block_bboxes, text_block_meta, decorative_asset_bboxes = _draw_native_text_blocks(
        image,
        draw,
        text_blocks=spec.text_blocks,
        native_layout=native_layout,
        hero_asset_selection=spec.hero_asset_selection,
        style=style,
        font_profile=font_profile,
        instance_seed=int(instance_seed),
    )
    for block_meta in text_block_meta:
        entities.append(
            {
                "entity_id": str(block_meta["block_id"]),
                "kind": "mixed_infographic_text_block",
                "block_kind": str(block_meta["kind"]),
                "text": str(block_meta["text"]),
                "bbox_px": [float(value) for value in block_meta["bbox_px"]],
                "text_bbox_px": [float(value) for value in block_meta["text_bbox_px"]],
                "font_family": str(block_meta["font_family"]),
                "placement_region": str(block_meta["placement_region"]),
            }
        )

    rendered = image.convert("RGB")
    return _RenderedMixedInfographic(
        image=rendered,
        entities=entities,
        page_bbox_px=[float(value) for value in page_bbox],
        title_bbox_px=[float(value) for value in title_bbox],
        module_bboxes_px=module_bboxes,
        module_title_bboxes_px=module_title_bboxes,
        item_label_bboxes_px=item_label_bboxes,
        field_label_bboxes_px=field_label_bboxes,
        value_cell_bboxes_px=value_cell_bboxes,
        icon_bboxes_px=icon_bboxes,
        section_asset_bboxes_px=section_asset_bboxes,
        decorative_asset_bboxes_px=decorative_asset_bboxes,
        text_block_bboxes_px=text_block_bboxes,
        text_blocks=list(text_block_meta),
        font_profile_meta=_font_profile_metadata(font_profile),
        layout_meta=dict(layout_meta),
    )


def _select_target(
    *,
    task_id: str,
    spec: _MixedInfographicSpec,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[_MixedModule, _MixedItem, _MixedField, Dict[str, float], Dict[str, float], Dict[str, float]]:
    module_count = len(spec.modules)
    module_index = int(params["target_module_index"]) if "target_module_index" in params else int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.target_module",
        )
        % int(module_count)
    )
    if module_index < 0 or module_index >= int(module_count):
        raise ValueError("target_module_index out of range")
    module = spec.modules[int(module_index)]
    item_count = len(module.items)
    field_count = len(module.fields)
    item_index = int(params["target_item_index"]) if "target_item_index" in params else int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.target_item.{module_index}",
        )
        % int(item_count)
    )
    field_index = int(params["target_field_index"]) if "target_field_index" in params else int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.target_field.{module_index}.{item_index}",
        )
        % int(field_count)
    )
    if item_index < 0 or item_index >= int(item_count):
        raise ValueError("target_item_index out of range")
    if field_index < 0 or field_index >= int(field_count):
        raise ValueError("target_field_index out of range")
    module_probs = {str(index): 1.0 / float(module_count) for index in range(int(module_count))}
    item_probs = {str(index): 1.0 / float(item_count) for index in range(int(item_count))}
    field_probs = {str(index): 1.0 / float(field_count) for index in range(int(field_count))}
    if "target_module_index" in params:
        module_probs = {str(int(module_index)): 1.0}
    if "target_item_index" in params:
        item_probs = {str(int(item_index)): 1.0}
    if "target_field_index" in params:
        field_probs = {str(int(field_index)): 1.0}
    return module, module.items[int(item_index)], module.fields[int(field_index)], module_probs, item_probs, field_probs


def _parse_mixed_numeric_value(value: str) -> int:
    text = str(value).strip()
    digits = "".join(char for char in text if char.isdigit())
    if not digits:
        raise ValueError(f"mixed infographic value is not numeric: {value!r}")
    return int(digits)


def _field_index(module: _MixedModule, field: _MixedField) -> int:
    for index, candidate in enumerate(module.fields):
        if str(candidate.field_id) == str(field.field_id):
            return int(index)
    raise ValueError("field is not part of module")


def _module_index(spec: _MixedInfographicSpec, module: _MixedModule) -> int:
    for index, candidate in enumerate(spec.modules):
        if str(candidate.module_id) == str(module.module_id):
            return int(index)
    raise ValueError("module is not part of mixed infographic spec")


def _numeric_item_values(module: _MixedModule, field: _MixedField) -> List[Dict[str, Any]]:
    values: List[Dict[str, Any]] = []
    for item in module.items:
        visible_value = str(item.values_by_field_id[str(field.field_id)])
        values.append(
            {
                "item_id": str(item.item_id),
                "item_label": str(item.label),
                "field_id": str(field.field_id),
                "field_label": str(field.label),
                "visible_value": str(visible_value),
                "numeric_value": int(_parse_mixed_numeric_value(str(visible_value))),
            }
        )
    return values


def _categorical_item_values(module: _MixedModule, field: _MixedField) -> List[Dict[str, Any]]:
    values: List[Dict[str, Any]] = []
    for item in module.items:
        visible_value = str(item.values_by_field_id[str(field.field_id)])
        values.append(
            {
                "item_id": str(item.item_id),
                "item_label": str(item.label),
                "field_id": str(field.field_id),
                "field_label": str(field.label),
                "visible_value": str(visible_value),
            }
        )
    return values


def _condition_phrase_for_operator(operator: str) -> str:
    if str(operator) == "above":
        return "above"
    if str(operator) == "below":
        return "below"
    if str(operator) == "at_least":
        return "at least"
    raise ValueError(f"unsupported condition operator: {operator}")


def _numeric_condition_matches(value: int, *, operator: str, threshold_value: int) -> bool:
    if str(operator) == "above":
        return int(value) > int(threshold_value)
    if str(operator) == "below":
        return int(value) < int(threshold_value)
    if str(operator) == "at_least":
        return int(value) >= int(threshold_value)
    raise ValueError(f"unsupported condition operator: {operator}")


def _threshold_candidate_values(unique_values: Sequence[int], *, operator: str) -> List[int]:
    values = [int(value) for value in sorted({int(value) for value in unique_values})]
    if str(operator) == "above":
        return list(values[:-1])
    if str(operator) in {"below", "at_least"}:
        return list(values[1:])
    raise ValueError(f"unsupported condition operator: {operator}")


def _module_field_pairs(
    *,
    spec: _MixedInfographicSpec,
    allowed_field_labels: Sequence[str],
    predicate: Callable[[_MixedModule, _MixedField], bool] | None = None,
) -> List[Tuple[int, _MixedModule, int, _MixedField]]:
    allowed = {str(label) for label in allowed_field_labels}
    pairs: List[Tuple[int, _MixedModule, int, _MixedField]] = []
    for module_index, module in enumerate(spec.modules):
        for field_index, field in enumerate(module.fields):
            if str(field.label) not in allowed:
                continue
            if predicate is not None and not bool(predicate(module, field)):
                continue
            pairs.append((int(module_index), module, int(field_index), field))
    return pairs


def _select_module_field_pair(
    *,
    task_id: str,
    spec: _MixedInfographicSpec,
    params: Mapping[str, Any],
    instance_seed: int,
    allowed_field_labels: Sequence[str],
    predicate: Callable[[_MixedModule, _MixedField], bool] | None = None,
) -> Tuple[_MixedModule, _MixedField, Dict[str, float], Dict[str, float]]:
    pairs = _module_field_pairs(spec=spec, allowed_field_labels=allowed_field_labels, predicate=predicate)
    if not pairs:
        raise ValueError("no eligible module/field pair in mixed infographic scene")

    requested_module_index = params.get("target_module_index")
    requested_field_index = params.get("target_field_index")
    requested_field_label = params.get("target_field_label")

    filtered_pairs = list(pairs)
    if requested_module_index is not None:
        module_index = int(requested_module_index)
        if module_index < 0 or module_index >= len(spec.modules):
            raise ValueError("target_module_index out of range")
        filtered_pairs = [pair for pair in filtered_pairs if int(pair[0]) == int(module_index)]
    if requested_field_index is not None:
        field_index = int(requested_field_index)
        filtered_pairs = [pair for pair in filtered_pairs if int(pair[2]) == int(field_index)]
    if requested_field_label is not None:
        filtered_pairs = [pair for pair in filtered_pairs if str(pair[3].label) == str(requested_field_label)]
    if not filtered_pairs:
        raise ValueError("requested module/field selection is not eligible for this mixed infographic task")

    if requested_module_index is not None and (requested_field_index is not None or requested_field_label is not None):
        selected_pair = filtered_pairs[0]
    else:
        selected_index = int(
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.target_module_field",
            )
            % int(len(filtered_pairs))
        )
        selected_pair = filtered_pairs[int(selected_index)]

    selected_module_index, selected_module, selected_field_index, selected_field = selected_pair
    eligible_module_indices = sorted({int(pair[0]) for pair in pairs})
    module_probs = {
        str(index): (1.0 if requested_module_index is not None and int(index) == int(selected_module_index) else 0.0)
        for index in eligible_module_indices
    }
    if requested_module_index is None:
        probability = 1.0 / float(len(eligible_module_indices))
        module_probs = {str(index): float(probability) for index in eligible_module_indices}

    selected_module_fields = [
        pair for pair in pairs if int(pair[0]) == int(selected_module_index)
    ]
    field_probs = {
        str(pair[2]): (
            1.0
            if (requested_field_index is not None or requested_field_label is not None)
            and int(pair[2]) == int(selected_field_index)
            else 0.0
        )
        for pair in selected_module_fields
    }
    if requested_field_index is None and requested_field_label is None:
        probability = 1.0 / float(len(selected_module_fields))
        field_probs = {str(pair[2]): float(probability) for pair in selected_module_fields}
    return selected_module, selected_field, dict(module_probs), dict(field_probs)


def _has_unique_extremum(module: _MixedModule, field: _MixedField, *, direction: str) -> bool:
    values = _numeric_item_values(module, field)
    if len(values) < 2:
        return False
    numeric_values = [int(value["numeric_value"]) for value in values]
    target_value = max(numeric_values) if str(direction) == "highest" else min(numeric_values)
    return sum(1 for value in numeric_values if int(value) == int(target_value)) == 1


def _select_extremum_target(
    *,
    task_id: str,
    gen_defaults: Mapping[str, Any],
    spec: _MixedInfographicSpec,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[_MixedModule, _MixedField, Dict[str, Any], Dict[str, float], Dict[str, float], Dict[str, float]]:
    direction, direction_probs = _resolve_named_variant(
        task_id=str(task_id),
        gen_defaults=gen_defaults,
        params=params,
        instance_seed=int(instance_seed),
        supported=("highest", "lowest"),
        explicit_key="rank_direction",
        weights_key="rank_direction_weights",
        balance_flag_key="balanced_rank_direction_sampling",
        namespace="rank_direction",
    )
    module, field, module_probs, field_probs = _select_module_field_pair(
        task_id=str(task_id),
        spec=spec,
        params=params,
        instance_seed=int(instance_seed),
        allowed_field_labels=NUMERIC_FIELD_LABELS,
        predicate=lambda candidate_module, candidate_field: _has_unique_extremum(
            candidate_module,
            candidate_field,
            direction=str(direction),
        ),
    )
    values = _numeric_item_values(module, field)
    target_numeric_value = max(int(value["numeric_value"]) for value in values) if str(direction) == "highest" else min(
        int(value["numeric_value"]) for value in values
    )
    winners = [value for value in values if int(value["numeric_value"]) == int(target_numeric_value)]
    if len(winners) != 1:
        raise ValueError("mixed infographic extremum target must be unique")
    target = dict(winners[0])
    target.update(
        {
            "module_id": str(module.module_id),
            "module_title": str(module.title),
            "module_kind": str(module.kind),
            "rank_direction": str(direction),
            "rank_order_phrase": "highest to lowest" if str(direction) == "highest" else "lowest to highest",
            "candidate_values": [dict(value) for value in values],
        }
    )
    return module, field, target, dict(module_probs), dict(field_probs), dict(direction_probs)


def _page_field_values_for_label(
    *,
    spec: _MixedInfographicSpec,
    field_label: str,
) -> List[Dict[str, Any]]:
    values: List[Dict[str, Any]] = []
    for module_index, module in enumerate(spec.modules):
        matching_fields = [field for field in module.fields if str(field.label) == str(field_label)]
        if not matching_fields:
            continue
        field = matching_fields[0]
        for value in _numeric_item_values(module, field):
            values.append(
                {
                    "module_index": int(module_index),
                    "module_id": str(module.module_id),
                    "module_title": str(module.title),
                    "module_kind": str(module.kind),
                    "item_id": str(value["item_id"]),
                    "item_label": str(value["item_label"]),
                    "field_id": str(field.field_id),
                    "field_label": str(field.label),
                    "visible_value": str(value["visible_value"]),
                    "numeric_value": int(value["numeric_value"]),
                }
            )
    return values


def _select_page_field_extremum_target(
    *,
    task_id: str,
    gen_defaults: Mapping[str, Any],
    spec: _MixedInfographicSpec,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[_MixedModule, _MixedField, Dict[str, Any], Dict[str, float], Dict[str, float]]:
    direction, direction_probs = _resolve_named_variant(
        task_id=str(task_id),
        gen_defaults=gen_defaults,
        params=params,
        instance_seed=int(instance_seed),
        supported=("highest", "lowest"),
        explicit_key="rank_direction",
        weights_key="rank_direction_weights",
        balance_flag_key="balanced_rank_direction_sampling",
        namespace="page_field_extremum_direction",
    )
    requested_field_label = params.get("target_field_label")
    candidate_by_label: Dict[str, Dict[str, Any]] = {}
    for field_label in sorted(set(NUMERIC_FIELD_LABELS)):
        if requested_field_label is not None and str(field_label) != str(requested_field_label):
            continue
        values = _page_field_values_for_label(spec=spec, field_label=str(field_label))
        module_ids = sorted({str(value["module_id"]) for value in values})
        if len(module_ids) < 3 or len(values) < 3:
            continue
        numeric_values = [int(value["numeric_value"]) for value in values]
        target_value = max(numeric_values) if str(direction) == "highest" else min(numeric_values)
        winners = [dict(value) for value in values if int(value["numeric_value"]) == int(target_value)]
        if len(winners) != 1:
            continue
        candidate_by_label[str(field_label)] = {
            "field_label": str(field_label),
            "candidate_values": [dict(value) for value in values],
            "winner": dict(winners[0]),
        }
    if not candidate_by_label:
        raise ValueError("no unique page-wide field extremum target in mixed infographic scene")
    labels = sorted(candidate_by_label)
    if requested_field_label is not None:
        selected_label = str(requested_field_label)
    else:
        selected_label = labels[
            int(
                resolve_selection_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    namespace=f"{task_id}.page_field_extremum_field.{direction}",
                )
            )
            % int(len(labels))
        ]
    selected = dict(candidate_by_label[str(selected_label)])
    winner = dict(selected["winner"])
    target_module = next(module for module in spec.modules if str(module.module_id) == str(winner["module_id"]))
    target_field = next(field for field in target_module.fields if str(field.field_id) == str(winner["field_id"]))
    candidate_values = sorted(
        [dict(value) for value in selected["candidate_values"]],
        key=lambda value: (str(value["module_id"]), str(value["item_id"]), str(value["field_id"])),
    )
    target = {
        "module_id": str(winner["module_id"]),
        "module_title": str(winner["module_title"]),
        "module_kind": str(winner["module_kind"]),
        "module_index": int(winner["module_index"]),
        "item_id": str(winner["item_id"]),
        "item_label": str(winner["item_label"]),
        "field_id": str(winner["field_id"]),
        "field_label": str(winner["field_label"]),
        "rank_direction": str(direction),
        "rank_order_phrase": "highest to lowest" if str(direction) == "highest" else "lowest to highest",
        "visible_value": str(winner["visible_value"]),
        "numeric_value": int(winner["numeric_value"]),
        "candidate_values": [dict(value) for value in candidate_values],
        "candidate_module_count": len({str(value["module_id"]) for value in candidate_values}),
        "answer_value": str(winner["module_title"]),
    }
    field_label_probs = _uniform_axis_probabilities(
        labels,
        str(selected_label),
        locked=requested_field_label is not None,
    )
    return target_module, target_field, target, dict(field_label_probs), dict(direction_probs)


def _ranked_numeric_values(module: _MixedModule, field: _MixedField, *, direction: str) -> List[Dict[str, Any]]:
    values = _numeric_item_values(module, field)
    numeric_values = [int(value["numeric_value"]) for value in values]
    if len(values) < 2 or len(set(numeric_values)) != len(values):
        return []
    reverse = str(direction) == "highest"
    return sorted(
        [dict(value) for value in values],
        key=lambda value: (int(value["numeric_value"]), str(value["item_label"])),
        reverse=bool(reverse),
    )


def _select_ranked_target(
    *,
    task_id: str,
    gen_defaults: Mapping[str, Any],
    spec: _MixedInfographicSpec,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[
    _MixedModule,
    _MixedField,
    Dict[str, Any],
    Dict[str, float],
    Dict[str, float],
    Dict[str, float],
    Dict[str, float],
]:
    direction, direction_probs = _resolve_named_variant(
        task_id=str(task_id),
        gen_defaults=gen_defaults,
        params=params,
        instance_seed=int(instance_seed),
        supported=("highest", "lowest"),
        explicit_key="rank_direction",
        weights_key="rank_direction_weights",
        balance_flag_key="balanced_rank_direction_sampling",
        namespace="rank_direction",
    )
    rank_position, rank_position_support, rank_position_probs = _resolve_supported_int(
        task_id=str(task_id),
        params=params,
        gen_defaults=gen_defaults,
        explicit_key="rank_position",
        support_key="rank_position_support",
        fallback=(2, 3),
        instance_seed=int(instance_seed),
        namespace=f"rank_position.{direction}",
    )
    module, field, module_probs, field_probs = _select_module_field_pair(
        task_id=str(task_id),
        spec=spec,
        params=params,
        instance_seed=int(instance_seed),
        allowed_field_labels=NUMERIC_FIELD_LABELS,
        predicate=lambda candidate_module, candidate_field: len(
            _ranked_numeric_values(candidate_module, candidate_field, direction=str(direction))
        )
        >= int(rank_position),
    )
    ranked_values = _ranked_numeric_values(module, field, direction=str(direction))
    if len(ranked_values) < int(rank_position):
        raise ValueError("mixed infographic ranked target requires enough unique numeric values")
    target = dict(ranked_values[int(rank_position) - 1])
    target.update(
        {
            "module_id": str(module.module_id),
            "module_title": str(module.title),
            "module_kind": str(module.kind),
            "rank_direction": str(direction),
            "rank_position": int(rank_position),
            "rank_ordinal": str(RANK_ORDINALS.get(int(rank_position), f"{int(rank_position)}th")),
            "rank_order_phrase": "highest to lowest" if str(direction) == "highest" else "lowest to highest",
            "rank_position_support": [int(value) for value in rank_position_support],
            "ranked_values": [dict(value) for value in ranked_values],
            "candidate_values": [dict(value) for value in ranked_values],
        }
    )
    return (
        module,
        field,
        target,
        dict(module_probs),
        dict(field_probs),
        dict(direction_probs),
        dict(rank_position_probs),
    )


def _uniform_axis_probabilities(values: Sequence[Any], selected: Any, *, locked: bool = False) -> Dict[str, float]:
    keys = sorted({str(value) for value in values})
    if not keys:
        return {}
    if bool(locked):
        return {str(selected): 1.0}
    probability = 1.0 / float(len(keys))
    return {str(key): float(probability) for key in keys}


def _select_two_field_condition_target(
    *,
    task_id: str,
    gen_defaults: Mapping[str, Any],
    spec: _MixedInfographicSpec,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[
    _MixedModule,
    _MixedField,
    _MixedField,
    Dict[str, Any],
    Dict[str, float],
    Dict[str, float],
    Dict[str, float],
    Dict[str, float],
    Dict[str, float],
    Dict[str, float],
]:
    operator, operator_probs = _resolve_named_variant(
        task_id=str(task_id),
        gen_defaults=gen_defaults,
        params=params,
        instance_seed=int(instance_seed),
        supported=CONDITION_OPERATORS,
        explicit_key="condition_operator",
        weights_key="condition_operator_weights",
        balance_flag_key="balanced_condition_operator_sampling",
        namespace="two_field_condition_operator",
    )
    requested_module_index = params.get("target_module_index")
    requested_numeric_field_index = params.get("target_numeric_field_index")
    requested_numeric_field_label = params.get("target_numeric_field_label")
    requested_category_field_index = params.get("target_category_field_index")
    requested_category_field_label = params.get("target_category_field_label")
    requested_category_value = params.get("category_value")

    candidates: List[Dict[str, Any]] = []
    for module_index, module in enumerate(spec.modules):
        if requested_module_index is not None and int(module_index) != int(requested_module_index):
            continue
        numeric_fields = [
            (field_index, field)
            for field_index, field in enumerate(module.fields)
            if str(field.label) in set(NUMERIC_FIELD_LABELS)
        ]
        category_fields = [
            (field_index, field)
            for field_index, field in enumerate(module.fields)
            if str(field.label) in set(CATEGORICAL_FIELD_LABELS)
        ]
        if requested_numeric_field_index is not None:
            numeric_fields = [
                (field_index, field)
                for field_index, field in numeric_fields
                if int(field_index) == int(requested_numeric_field_index)
            ]
        if requested_numeric_field_label is not None:
            numeric_fields = [
                (field_index, field)
                for field_index, field in numeric_fields
                if str(field.label) == str(requested_numeric_field_label)
            ]
        if requested_category_field_index is not None:
            category_fields = [
                (field_index, field)
                for field_index, field in category_fields
                if int(field_index) == int(requested_category_field_index)
            ]
        if requested_category_field_label is not None:
            category_fields = [
                (field_index, field)
                for field_index, field in category_fields
                if str(field.label) == str(requested_category_field_label)
            ]
        for numeric_field_index, numeric_field in numeric_fields:
            numeric_values = _numeric_item_values(module, numeric_field)
            threshold_values = _threshold_candidate_values(
                [int(value["numeric_value"]) for value in numeric_values],
                operator=str(operator),
            )
            if not threshold_values:
                continue
            numeric_by_item = {str(value["item_id"]): dict(value) for value in numeric_values}
            for category_field_index, category_field in category_fields:
                category_values = _categorical_item_values(module, category_field)
                category_by_item = {str(value["item_id"]): dict(value) for value in category_values}
                visible_category_values = sorted({str(value["visible_value"]) for value in category_values})
                for category_value in visible_category_values:
                    if requested_category_value is not None and str(category_value) != str(requested_category_value):
                        continue
                    category_matches = [
                        dict(value) for value in category_values if str(value["visible_value"]) == str(category_value)
                    ]
                    if len(category_matches) < 2:
                        continue
                    category_item_ids = {str(value["item_id"]) for value in category_matches}
                    for threshold_index, threshold_value in enumerate(threshold_values):
                        threshold_visible = next(
                            str(value["visible_value"])
                            for value in numeric_values
                            if int(value["numeric_value"]) == int(threshold_value)
                        )
                        numeric_matches = [
                            dict(value)
                            for value in numeric_values
                            if _numeric_condition_matches(
                                int(value["numeric_value"]),
                                operator=str(operator),
                                threshold_value=int(threshold_value),
                            )
                        ]
                        if len(numeric_matches) < 2:
                            continue
                        numeric_item_ids = {str(value["item_id"]) for value in numeric_matches}
                        matching_ids = sorted(category_item_ids.intersection(numeric_item_ids))
                        if len(matching_ids) != 1:
                            continue
                        matching_item_id = str(matching_ids[0])
                        candidates.append(
                            {
                                "module_index": int(module_index),
                                "module": module,
                                "numeric_field_index": int(numeric_field_index),
                                "numeric_field": numeric_field,
                                "category_field_index": int(category_field_index),
                                "category_field": category_field,
                                "category_value": str(category_value),
                                "threshold_index": int(threshold_index),
                                "threshold_value": int(threshold_value),
                                "threshold_visible": str(threshold_visible),
                                "numeric_matches": [dict(value) for value in numeric_matches],
                                "category_matches": [dict(value) for value in category_matches],
                                "matching_item_id": str(matching_item_id),
                                "matching_numeric_value": dict(numeric_by_item[str(matching_item_id)]),
                                "matching_category_value": dict(category_by_item[str(matching_item_id)]),
                            }
                        )
    if not candidates:
        raise ValueError("no unique two-field condition target in mixed infographic scene")
    selection_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.two_field_condition_target.{operator}",
        )
        % int(len(candidates))
    )
    selected = dict(candidates[int(selection_index)])
    module = selected["module"]
    numeric_field = selected["numeric_field"]
    category_field = selected["category_field"]
    matching_item = next(item for item in module.items if str(item.item_id) == str(selected["matching_item_id"]))
    module_indices = [int(candidate["module_index"]) for candidate in candidates]
    numeric_field_indices = [
        int(candidate["numeric_field_index"])
        for candidate in candidates
        if int(candidate["module_index"]) == int(selected["module_index"])
    ]
    category_field_indices = [
        int(candidate["category_field_index"])
        for candidate in candidates
        if int(candidate["module_index"]) == int(selected["module_index"])
    ]
    category_values = [
        str(candidate["category_value"])
        for candidate in candidates
        if int(candidate["module_index"]) == int(selected["module_index"])
        and int(candidate["category_field_index"]) == int(selected["category_field_index"])
    ]
    threshold_indices = [
        int(candidate["threshold_index"])
        for candidate in candidates
        if int(candidate["module_index"]) == int(selected["module_index"])
        and int(candidate["numeric_field_index"]) == int(selected["numeric_field_index"])
        and int(candidate["category_field_index"]) == int(selected["category_field_index"])
        and str(candidate["category_value"]) == str(selected["category_value"])
    ]
    target = {
        "module_id": str(module.module_id),
        "module_title": str(module.title),
        "module_kind": str(module.kind),
        "item_id": str(matching_item.item_id),
        "item_label": str(matching_item.label),
        "numeric_field_id": str(numeric_field.field_id),
        "numeric_field_label": str(numeric_field.label),
        "category_field_id": str(category_field.field_id),
        "category_field_label": str(category_field.label),
        "category_value": str(selected["category_value"]),
        "condition_operator": str(operator),
        "condition_phrase": str(_condition_phrase_for_operator(str(operator))),
        "threshold_rank_index": int(selected["threshold_index"]),
        "threshold_value": int(selected["threshold_value"]),
        "threshold_visible": str(selected["threshold_visible"]),
        "numeric_matches": [dict(value) for value in selected["numeric_matches"]],
        "category_matches": [dict(value) for value in selected["category_matches"]],
        "matching_numeric_value": dict(selected["matching_numeric_value"]),
        "matching_category_value": dict(selected["matching_category_value"]),
        "answer_value": str(matching_item.label),
    }
    return (
        module,
        numeric_field,
        category_field,
        target,
        _uniform_axis_probabilities(module_indices, int(selected["module_index"]), locked=requested_module_index is not None),
        _uniform_axis_probabilities(
            numeric_field_indices,
            int(selected["numeric_field_index"]),
            locked=requested_numeric_field_index is not None or requested_numeric_field_label is not None,
        ),
        _uniform_axis_probabilities(
            category_field_indices,
            int(selected["category_field_index"]),
            locked=requested_category_field_index is not None or requested_category_field_label is not None,
        ),
        dict(operator_probs),
        _uniform_axis_probabilities(
            category_values,
            str(selected["category_value"]),
            locked=requested_category_value is not None,
        ),
        _uniform_axis_probabilities(threshold_indices, int(selected["threshold_index"])),
    )


def _select_condition_target(
    *,
    task_id: str,
    gen_defaults: Mapping[str, Any],
    spec: _MixedInfographicSpec,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[_MixedModule, _MixedField, Dict[str, Any], Dict[str, float], Dict[str, float], Dict[str, float], Dict[str, float], Dict[str, float]]:
    module, field, module_probs, field_probs = _select_module_field_pair(
        task_id=str(task_id),
        spec=spec,
        params=params,
        instance_seed=int(instance_seed),
        allowed_field_labels=NUMERIC_FIELD_LABELS,
        predicate=lambda candidate_module, candidate_field: len(
            {int(value["numeric_value"]) for value in _numeric_item_values(candidate_module, candidate_field)}
        )
        >= 6,
    )
    operator, operator_probs = _resolve_named_variant(
        task_id=str(task_id),
        gen_defaults=gen_defaults,
        params=params,
        instance_seed=int(instance_seed),
        supported=CONDITION_OPERATORS,
        explicit_key="condition_operator",
        weights_key="condition_operator_weights",
        balance_flag_key="balanced_condition_operator_sampling",
        namespace=f"condition_operator.{module.module_id}.{field.field_id}",
    )
    values = _numeric_item_values(module, field)
    unique_values = sorted({int(value["numeric_value"]) for value in values})
    if len(unique_values) < 2:
        raise ValueError("condition count target needs at least two unique numeric values")
    if str(operator) == "above":
        threshold_candidate_values = unique_values[:-1]
        operator_phrase = "above"
    elif str(operator) == "below":
        threshold_candidate_values = unique_values[1:]
        operator_phrase = "below"
    else:
        threshold_candidate_values = unique_values[1:]
        operator_phrase = "at least"
    if not threshold_candidate_values:
        raise ValueError("condition count target has no useful threshold")
    threshold_candidates: List[Dict[str, Any]] = []
    for threshold_index, candidate_value in enumerate(threshold_candidate_values):
        threshold_value = int(candidate_value)
        threshold_visible = next(
            str(value["visible_value"]) for value in values if int(value["numeric_value"]) == int(threshold_value)
        )
        if str(operator) == "above":
            matches = [value for value in values if int(value["numeric_value"]) > int(threshold_value)]
        elif str(operator) == "below":
            matches = [value for value in values if int(value["numeric_value"]) < int(threshold_value)]
        else:
            matches = [value for value in values if int(value["numeric_value"]) >= int(threshold_value)]
        if not matches or len(matches) == len(values):
            continue
        threshold_candidates.append(
            {
                "threshold_index": int(threshold_index),
                "threshold_value": int(threshold_value),
                "threshold_visible": str(threshold_visible),
                "matching_values": [dict(value) for value in matches],
                "answer_value": int(len(matches)),
            }
        )
    if not threshold_candidates:
        raise ValueError("condition count answer must be nonzero and not all visible items")
    if params.get("threshold_rank_index") is not None:
        threshold_index = int(params["threshold_rank_index"])
        if threshold_index < 0 or threshold_index >= len(threshold_candidate_values):
            raise ValueError("threshold_rank_index out of range")
        matching_candidates = [candidate for candidate in threshold_candidates if int(candidate["threshold_index"]) == int(threshold_index)]
        if not matching_candidates:
            raise ValueError("threshold_rank_index selects an invalid condition count")
        selected_candidate = dict(matching_candidates[0])
        answer_count_probs = {str(int(selected_candidate["answer_value"])): 1.0}
    else:
        candidates_by_answer_count: Dict[int, List[Dict[str, Any]]] = {}
        for candidate in threshold_candidates:
            candidates_by_answer_count.setdefault(int(candidate["answer_value"]), []).append(dict(candidate))
        answer_counts = sorted(candidates_by_answer_count)
        requested_answer_count = params.get("condition_answer_count")
        if requested_answer_count is not None:
            selected_answer_count = int(requested_answer_count)
            if int(selected_answer_count) not in candidates_by_answer_count:
                raise ValueError("condition_answer_count cannot be produced by selected module field")
            answer_count_probs = {str(int(selected_answer_count)): 1.0}
        else:
            answer_count_index = int(
                resolve_selection_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    namespace=f"{task_id}.condition_answer_count.{module.module_id}.{field.field_id}.{operator}",
                )
                % int(len(answer_counts))
            )
            selected_answer_count = int(answer_counts[int(answer_count_index)])
            answer_count_probs = {str(int(answer_count)): 1.0 / float(len(answer_counts)) for answer_count in answer_counts}
        answer_group = candidates_by_answer_count[int(selected_answer_count)]
        threshold_group_index = int(
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.threshold.{module.module_id}.{field.field_id}.{operator}.{selected_answer_count}",
            )
            % int(len(answer_group))
        )
        selected_candidate = dict(answer_group[int(threshold_group_index)])
    threshold_probs = {str(index): 0.0 for index in range(len(threshold_candidate_values))}
    if params.get("threshold_rank_index") is not None:
        threshold_probs[str(int(selected_candidate["threshold_index"]))] = 1.0
    else:
        candidates_by_answer_count = {}
        for candidate in threshold_candidates:
            candidates_by_answer_count.setdefault(int(candidate["answer_value"]), []).append(dict(candidate))
        for answer_count, candidates in candidates_by_answer_count.items():
            answer_probability = float(answer_count_probs.get(str(int(answer_count)), 0.0))
            if answer_probability <= 0.0:
                continue
            threshold_probability = answer_probability / float(len(candidates))
            for candidate in candidates:
                threshold_probs[str(int(candidate["threshold_index"]))] = float(threshold_probability)
    target = {
        "module_id": str(module.module_id),
        "module_title": str(module.title),
        "module_kind": str(module.kind),
        "field_id": str(field.field_id),
        "field_label": str(field.label),
        "condition_operator": str(operator),
        "condition_phrase": str(operator_phrase),
        "threshold_rank_index": int(selected_candidate["threshold_index"]),
        "threshold_value": int(selected_candidate["threshold_value"]),
        "threshold_visible": str(selected_candidate["threshold_visible"]),
        "candidate_values": [dict(value) for value in values],
        "matching_values": [dict(value) for value in selected_candidate["matching_values"]],
        "answer_value": int(selected_candidate["answer_value"]),
    }
    return module, field, target, dict(module_probs), dict(field_probs), dict(operator_probs), dict(threshold_probs), dict(answer_count_probs)


def _select_total_target(
    *,
    task_id: str,
    spec: _MixedInfographicSpec,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[_MixedModule, _MixedField, Dict[str, Any], Dict[str, float], Dict[str, float]]:
    module, field, module_probs, field_probs = _select_module_field_pair(
        task_id=str(task_id),
        spec=spec,
        params=params,
        instance_seed=int(instance_seed),
        allowed_field_labels=ADDITIVE_FIELD_LABELS,
        predicate=lambda candidate_module, candidate_field: len(candidate_module.items) >= 2
        and str(candidate_field.label) in set(ADDITIVE_FIELD_LABELS),
    )
    values = _numeric_item_values(module, field)
    total_value = int(sum(int(value["numeric_value"]) for value in values))
    target = {
        "module_id": str(module.module_id),
        "module_title": str(module.title),
        "module_kind": str(module.kind),
        "field_id": str(field.field_id),
        "field_label": str(field.label),
        "summed_values": [dict(value) for value in values],
        "answer_value": int(total_value),
    }
    return module, field, target, dict(module_probs), dict(field_probs)


def _module_field_total_payload(
    *,
    module_index: int,
    module: _MixedModule,
    field_label: str,
) -> Dict[str, Any] | None:
    matching_fields = [field for field in module.fields if str(field.label) == str(field_label)]
    if not matching_fields or len(module.items) < 2:
        return None
    field = matching_fields[0]
    values = _numeric_item_values(module, field)
    return {
        "module_index": int(module_index),
        "module_id": str(module.module_id),
        "module_title": str(module.title),
        "module_kind": str(module.kind),
        "field_id": str(field.field_id),
        "field_label": str(field.label),
        "summed_values": [dict(value) for value in values],
        "total_value": int(sum(int(value["numeric_value"]) for value in values)),
    }


def _select_two_module_total_comparison_target(
    *,
    task_id: str,
    spec: _MixedInfographicSpec,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[_MixedModule, _MixedField, _MixedModule, _MixedField, Dict[str, Any], Dict[str, float], Dict[str, float]]:
    requested_field_label = params.get("target_field_label")
    requested_module_a_index = params.get("target_module_a_index")
    requested_module_b_index = params.get("target_module_b_index")
    candidates_by_label: Dict[str, List[Dict[str, Any]]] = {}
    for field_label in sorted(set(ADDITIVE_FIELD_LABELS)):
        if requested_field_label is not None and str(field_label) != str(requested_field_label):
            continue
        module_totals = [
            payload
            for module_index, module in enumerate(spec.modules)
            for payload in [_module_field_total_payload(module_index=module_index, module=module, field_label=str(field_label))]
            if payload is not None
        ]
        if len(module_totals) < 2:
            continue
        pairs: List[Dict[str, Any]] = []
        for module_a in module_totals:
            if requested_module_a_index is not None and int(module_a["module_index"]) != int(requested_module_a_index):
                continue
            for module_b in module_totals:
                if int(module_a["module_index"]) == int(module_b["module_index"]):
                    continue
                if requested_module_b_index is not None and int(module_b["module_index"]) != int(requested_module_b_index):
                    continue
                if int(module_a["total_value"]) == int(module_b["total_value"]):
                    continue
                winning_side = "module_a" if int(module_a["total_value"]) > int(module_b["total_value"]) else "module_b"
                winning_module = module_a if str(winning_side) == "module_a" else module_b
                pairs.append(
                    {
                        "field_label": str(field_label),
                        "module_a": dict(module_a),
                        "module_b": dict(module_b),
                        "winning_side": str(winning_side),
                        "answer_value": str(winning_module["module_title"]),
                    }
                )
        if pairs:
            candidates_by_label[str(field_label)] = [dict(pair) for pair in pairs]
    if not candidates_by_label:
        raise ValueError("no unequal two-module total comparison target in mixed infographic scene")
    labels = sorted(candidates_by_label)
    if requested_field_label is not None:
        selected_label = str(requested_field_label)
    else:
        selected_label = labels[
            int(
                resolve_selection_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    namespace=f"{task_id}.two_module_total_field",
                )
            )
            % int(len(labels))
        ]
    pair_candidates = [dict(pair) for pair in candidates_by_label[str(selected_label)]]
    selected_pair = pair_candidates[
        int(
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.two_module_total_pair.{selected_label}",
            )
        )
        % int(len(pair_candidates))
    ]
    module_a_payload = dict(selected_pair["module_a"])
    module_b_payload = dict(selected_pair["module_b"])
    module_a = spec.modules[int(module_a_payload["module_index"])]
    module_b = spec.modules[int(module_b_payload["module_index"])]
    field_a = next(field for field in module_a.fields if str(field.field_id) == str(module_a_payload["field_id"]))
    field_b = next(field for field in module_b.fields if str(field.field_id) == str(module_b_payload["field_id"]))
    pair_keys = [
        f'{int(pair["module_a"]["module_index"])}:{int(pair["module_b"]["module_index"])}'
        for pair in pair_candidates
    ]
    selected_pair_key = f'{int(module_a_payload["module_index"])}:{int(module_b_payload["module_index"])}'
    target = {
        "field_label": str(selected_label),
        "module_a": dict(module_a_payload),
        "module_b": dict(module_b_payload),
        "module_a_total": int(module_a_payload["total_value"]),
        "module_b_total": int(module_b_payload["total_value"]),
        "winning_side": str(selected_pair["winning_side"]),
        "answer_value": str(selected_pair["answer_value"]),
    }
    return (
        module_a,
        field_a,
        module_b,
        field_b,
        dict(target),
        _uniform_axis_probabilities(labels, str(selected_label), locked=requested_field_label is not None),
        _uniform_axis_probabilities(
            pair_keys,
            str(selected_pair_key),
            locked=requested_module_a_index is not None and requested_module_b_index is not None,
        ),
    )


def _build_modules_payload(
    *,
    spec: _MixedInfographicSpec,
    rendered: _RenderedMixedInfographic,
) -> Tuple[Dict[str, Any], ...]:
    modules_payload: List[Dict[str, Any]] = []
    for module in spec.modules:
        modules_payload.append(
            {
                "module_id": str(module.module_id),
                "module_title": str(module.title),
                "module_kind": str(module.kind),
                "bbox_px": [float(value) for value in rendered.module_bboxes_px[str(module.module_id)]],
                "title_bbox_px": [
                    float(value) for value in rendered.module_title_bboxes_px[str(module.module_id)]
                ],
                "section_visual_asset": module.section_asset_selection.to_metadata(),
                "section_visual_asset_bbox_px": [
                    float(value) for value in rendered.section_asset_bboxes_px[str(module.module_id)]
                ],
                "fields": [
                    {
                        "field_id": str(field.field_id),
                        "field_label": str(field.label),
                        "bbox_px": [
                            float(value)
                            for value in rendered.field_label_bboxes_px[str(module.module_id)][str(field.field_id)]
                        ],
                    }
                    for field in module.fields
                ],
                "items": [
                    {
                        "item_id": str(item.item_id),
                        "item_label": str(item.label),
                        "visual_asset": item.visual_asset_selection.to_metadata(),
                        "label_bbox_px": [
                            float(value)
                            for value in rendered.item_label_bboxes_px[str(module.module_id)][str(item.item_id)]
                        ],
                        "visual_asset_bbox_px": [
                            float(value)
                            for value in rendered.icon_bboxes_px[str(module.module_id)][str(item.item_id)]
                        ],
                        "values_by_field_id": dict(item.values_by_field_id),
                        "value_bboxes_px": dict(rendered.value_cell_bboxes_px[str(module.module_id)][str(item.item_id)]),
                    }
                    for item in module.items
                ],
            }
        )
    return tuple(modules_payload)


def _resolve_mixed_scene_context(
    *,
    task_id: str,
    query_ids: Sequence[str],
    params: Mapping[str, Any],
    instance_seed: int,
) -> _MixedSceneContext:
    gen_defaults, render_defaults, prompt_defaults, complexity_weights = _mixed_task_defaults(str(task_id))
    query_id, query_id_probabilities = _resolve_named_variant(
        task_id=str(task_id),
        gen_defaults=gen_defaults,
        params=params,
        instance_seed=int(instance_seed),
        supported=query_ids,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        namespace="query_id",
    )
    scene_variant, scene_variant_probabilities = _resolve_named_variant(
        task_id=str(task_id),
        gen_defaults=gen_defaults,
        params=params,
        instance_seed=int(instance_seed),
        supported=SCENE_VARIANTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        namespace="scene_variant",
    )
    native_layout_mode, native_layout_mode_probabilities = _resolve_native_layout_mode(
        task_id=str(task_id),
        params=params,
        render_defaults=render_defaults,
        instance_seed=int(instance_seed),
    )
    module_count, module_count_support, module_count_probabilities = _resolve_supported_int(
        task_id=str(task_id),
        params=params,
        gen_defaults=gen_defaults,
        explicit_key="module_count",
        support_key="module_count_support",
        fallback=(7, 8, 9),
        instance_seed=int(instance_seed),
        namespace="module_count",
    )
    item_count_support = _resolve_int_support(
        params=params,
        gen_defaults=gen_defaults,
        key="item_count_support",
        fallback=(2, 3, 4),
    )
    field_count_support = _resolve_int_support(
        params=params,
        gen_defaults=gen_defaults,
        key="field_count_support",
        fallback=(2, 3),
    )
    native_text_block_count, native_text_block_count_support, native_text_block_count_probabilities = (
        _resolve_native_text_block_count(
            task_id=str(task_id),
            params=params,
            render_defaults=render_defaults,
            instance_seed=int(instance_seed),
        )
    )
    spec = _build_mixed_spec(
        module_count=int(module_count),
        item_count_support=tuple(item_count_support),
        field_count_support=tuple(field_count_support),
        native_text_block_count=int(native_text_block_count),
        instance_seed=int(instance_seed),
        allow_categorical_value_reuse=str(task_id) == MIXED_INFOGRAPHIC_TWO_FIELD_CONDITION_TASK_ID,
        ensure_shared_numeric_field=str(task_id)
        in {MIXED_INFOGRAPHIC_PAGE_FIELD_EXTREMUM_TASK_ID, MIXED_INFOGRAPHIC_TWO_MODULE_TOTAL_COMPARISON_TASK_ID},
        shared_numeric_field_label=(
            str(params["target_field_label"])
            if str(task_id)
            in {MIXED_INFOGRAPHIC_PAGE_FIELD_EXTREMUM_TASK_ID, MIXED_INFOGRAPHIC_TWO_MODULE_TOTAL_COMPARISON_TASK_ID}
            and params.get("target_field_label") is not None
            else None
        ),
        shared_numeric_field_choices=(
            ADDITIVE_FIELD_LABELS
            if str(task_id) == MIXED_INFOGRAPHIC_TWO_MODULE_TOTAL_COMPARISON_TASK_ID
            else NUMERIC_FIELD_LABELS
        ),
    )
    font_profile = _resolve_mixed_font_profile(modules=spec.modules, params=params, instance_seed=int(instance_seed))
    render_params = _resolve_render_params(params, render_defaults)
    style, style_meta = resolve_pages_information_style(
        instance_seed=int(instance_seed),
        params=render_defaults,
        scene_id=SCENE_ID,
        task_group=TASK_GROUP,
        allow_dark=True,
    )
    background, background_meta = make_information_scene_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=style,
        instance_seed=int(instance_seed),
        namespace=f"pages.{TASK_GROUP}.{SCENE_ID}.information_scene_background",
    )
    rendered = _render_mixed_infographic(
        background,
        spec=spec,
        scene_variant=str(scene_variant),
        native_layout_mode=str(native_layout_mode),
        style=style,
        render_params=render_params,
        instance_seed=int(instance_seed),
        font_profile=font_profile,
    )
    image, post_noise_meta = apply_post_image_noise(
        rendered.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return _MixedSceneContext(
        task_id=str(task_id),
        query_id=str(query_id),
        gen_defaults=dict(gen_defaults),
        render_defaults=dict(render_defaults),
        prompt_defaults=dict(prompt_defaults),
        complexity_weights=dict(complexity_weights),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant=str(scene_variant),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        native_layout_mode=str(native_layout_mode),
        native_layout_mode_probabilities=dict(native_layout_mode_probabilities),
        module_count=int(module_count),
        module_count_support=tuple(int(value) for value in module_count_support),
        module_count_probabilities=dict(module_count_probabilities),
        item_count_support=tuple(int(value) for value in item_count_support),
        field_count_support=tuple(int(value) for value in field_count_support),
        native_text_block_count=int(native_text_block_count),
        native_text_block_count_support=tuple(int(value) for value in native_text_block_count_support),
        native_text_block_count_probabilities=dict(native_text_block_count_probabilities),
        spec=spec,
        rendered=rendered,
        image=image,
        render_params=render_params,
        background_meta=dict(background_meta),
        style_meta=dict(style_meta),
        post_noise_meta=dict(post_noise_meta),
        modules_payload=_build_modules_payload(spec=spec, rendered=rendered),
    )


def _build_prompt_examples(query_id: str) -> Tuple[str, str]:
    if str(query_id) == FIELD_EXTREMUM_QUERY_ID:
        annotation = {
            "module_title": [2, 3, 4, 5],
            "field_label": [4, 5, 6, 7],
            "winning_item": [3, 4, 5, 6],
            "winning_value": [5, 6, 7, 8],
            "candidate_1": [5, 6, 7, 8],
            "candidate_2": [6, 7, 8, 9],
        }
        return (
            json.dumps({"annotation": annotation, "answer": "Atlas"}, separators=(",", ":")),
            json.dumps({"answer": "Atlas"}, separators=(",", ":")),
        )
    if str(query_id) == FIELD_RANKED_QUERY_ID:
        annotation = {
            "module_title": [2, 3, 4, 5],
            "field_label": [4, 5, 6, 7],
            "ranked_item": [3, 4, 5, 6],
            "ranked_value": [5, 6, 7, 8],
            "candidate_1": [5, 6, 7, 8],
            "candidate_2": [6, 7, 8, 9],
            "candidate_3": [7, 8, 9, 10],
        }
        return (
            json.dumps({"annotation": annotation, "answer": "Atlas"}, separators=(",", ":")),
            json.dumps({"answer": "Atlas"}, separators=(",", ":")),
        )
    if str(query_id) == PAGE_FIELD_EXTREMUM_QUERY_ID:
        annotation = {
            "winning_module_title": [2, 3, 4, 5],
            "winning_field_label": [4, 5, 6, 7],
            "winning_item": [3, 4, 5, 6],
            "winning_value": [5, 6, 7, 8],
            "candidate_1": [5, 6, 7, 8],
            "candidate_2": [6, 7, 8, 9],
            "candidate_3": [7, 8, 9, 10],
        }
        return (
            json.dumps({"annotation": annotation, "answer": "Atlas"}, separators=(",", ":")),
            json.dumps({"answer": "Atlas"}, separators=(",", ":")),
        )
    if str(query_id) == TWO_FIELD_CONDITION_QUERY_ID:
        annotation = {
            "module_title": [2, 3, 4, 5],
            "numeric_field_label": [4, 5, 6, 7],
            "category_field_label": [6, 7, 8, 9],
            "matching_item": [3, 4, 5, 6],
            "numeric_value_cell": [5, 6, 7, 8],
            "category_value_cell": [7, 8, 9, 10],
        }
        return (
            json.dumps({"annotation": annotation, "answer": "Atlas"}, separators=(",", ":")),
            json.dumps({"answer": "Atlas"}, separators=(",", ":")),
        )
    if str(query_id) == CONDITION_COUNT_QUERY_ID:
        annotation = [[5, 6, 7, 8], [6, 7, 8, 9]]
        return (
            json.dumps({"annotation": annotation, "answer": 2}, separators=(",", ":")),
            json.dumps({"answer": 2}, separators=(",", ":")),
        )
    if str(query_id) == FIELD_TOTAL_QUERY_ID:
        annotation = [[5, 6, 7, 8], [6, 7, 8, 9], [7, 8, 9, 10]]
        return (
            json.dumps({"annotation": annotation, "answer": 126}, separators=(",", ":")),
            json.dumps({"answer": 126}, separators=(",", ":")),
        )
    if str(query_id) == TWO_MODULE_TOTAL_COMPARISON_QUERY_ID:
        annotation = {
            "module_a_title": [2, 3, 4, 5],
            "module_b_title": [3, 4, 5, 6],
            "field_label_a": [4, 5, 6, 7],
            "field_label_b": [5, 6, 7, 8],
            "module_a_value_1": [6, 7, 8, 9],
            "module_a_value_2": [7, 8, 9, 10],
            "module_b_value_1": [8, 9, 10, 11],
            "module_b_value_2": [9, 10, 11, 12],
        }
        return (
            json.dumps({"annotation": annotation, "answer": "Atlas"}, separators=(",", ":")),
            json.dumps({"answer": "Atlas"}, separators=(",", ":")),
        )
    annotation = {
        "module_title": [2, 3, 4, 5],
        "item_label": [3, 4, 5, 6],
        "field_label": [4, 5, 6, 7],
        "value_cell": [5, 6, 7, 8],
    }
    return (
        json.dumps({"annotation": annotation, "answer": "42k"}, separators=(",", ":")),
        json.dumps({"answer": "42k"}, separators=(",", ":")),
    )


def _mixed_prompt_defaults(ctx: _MixedSceneContext) -> Dict[str, Any]:
    return required_group_defaults(
        ctx.prompt_defaults,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "answer_hint",
            "annotation_hint",
            "object_description",
        ),
        context=f"prompt defaults for {ctx.task_id}",
    )


def _render_mixed_prompt(
    *,
    ctx: _MixedSceneContext,
    slots: Mapping[str, Any],
    instance_seed: int,
) -> Any:
    prompt_defaults = _mixed_prompt_defaults(ctx)
    json_example, json_example_answer_only = _build_prompt_examples(str(ctx.query_id))
    prompt_slots = {
        "object_description": str(prompt_defaults["object_description"]),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_defaults["answer_hint"]),
        "annotation_hint": str(prompt_defaults["annotation_hint"]),
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
    }
    prompt_slots.update({str(key): value for key, value in slots.items()})
    prompt_selection = render_task_prompt_variants(
        domain="pages",
        task_group=TASK_GROUP,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(ctx.query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots=prompt_slots,
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(prompt_selection)


def _mixed_projected_annotation(annotation_type: str, annotation_value: Any) -> Dict[str, Any]:
    if str(annotation_type) == "keyed_bbox_map":
        keyed = {str(key): [float(value) for value in bbox] for key, bbox in dict(annotation_value).items()}
        return {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(keyed),
            "pixel_keyed_bbox_map": dict(keyed),
            "bbox_set": list(keyed.values()),
        }
    bbox_set = [[float(value) for value in bbox] for bbox in list(annotation_value)]
    return {
        "type": "bbox_set",
        "bbox_set": list(bbox_set),
        "pixel_bbox_set": list(bbox_set),
    }


def _build_mixed_trace_payload(
    *,
    ctx: _MixedSceneContext,
    prompt_artifacts: Any,
    prompt_defaults: Mapping[str, Any],
    target_payload: Mapping[str, Any],
    answer_value: Any,
    annotation_type: str,
    annotation_value: Any,
    witness_type: str,
    annotation_keys: Sequence[str],
    query_params_extra: Mapping[str, Any] = {},
    execution_extra: Mapping[str, Any] = {},
) -> Dict[str, Any]:
    target = dict(target_payload)
    query_params = {
        "query_id": str(ctx.query_id),
        "scene_variant": str(ctx.scene_variant),
        "native_layout_mode": str(ctx.native_layout_mode),
        "module_count": int(ctx.module_count),
        "native_text_block_count": int(ctx.native_text_block_count),
        "target": dict(target),
        "target_answer": answer_value,
        "query_id_probabilities": dict(ctx.query_id_probabilities),
        "scene_variant_probabilities": dict(ctx.scene_variant_probabilities),
        "native_layout_mode_probabilities": dict(ctx.native_layout_mode_probabilities),
        "module_count_probabilities": dict(ctx.module_count_probabilities),
        "native_text_block_count_probabilities": dict(ctx.native_text_block_count_probabilities),
    }
    query_params.update(dict(query_params_extra))
    execution_trace = {
        "query_id": str(ctx.query_id),
        "scene_variant": str(ctx.scene_variant),
        "native_layout_mode": str(ctx.native_layout_mode),
        "question_format": str(ctx.query_id),
        "module_count": int(ctx.module_count),
        "module_count_support": [int(value) for value in ctx.module_count_support],
        "item_count_support": [int(value) for value in ctx.item_count_support],
        "field_count_support": [int(value) for value in ctx.field_count_support],
        "native_text_block_count": int(ctx.native_text_block_count),
        "native_text_block_count_support": [int(value) for value in ctx.native_text_block_count_support],
        "target": dict(target),
        "answer_value": answer_value,
        "modules": [dict(module) for module in ctx.modules_payload],
        "page_text_resources": dict(ctx.spec.text_resource_metadata),
        "query_id_probabilities": dict(ctx.query_id_probabilities),
        "scene_variant_probabilities": dict(ctx.scene_variant_probabilities),
        "native_layout_mode_probabilities": dict(ctx.native_layout_mode_probabilities),
        "module_count_probabilities": dict(ctx.module_count_probabilities),
        "native_text_block_count_probabilities": dict(ctx.native_text_block_count_probabilities),
    }
    execution_trace.update(dict(execution_extra))
    return {
        "scene_ir": {
            "scene_id": SCENE_ID,
            "scene_kind": "pages_mixed_infographic_page",
            "entities": [dict(entity) for entity in ctx.rendered.entities],
            "relations": {
                "query_id": str(ctx.query_id),
                "scene_variant": str(ctx.scene_variant),
                "native_layout_mode": str(ctx.native_layout_mode),
                "target": dict(target),
                "answer_value": answer_value,
            },
        },
        "query_spec": {
            "query_id": str(ctx.query_id),
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": dict(query_params),
        },
        "render_spec": {
            "canvas_width": int(ctx.render_params.canvas_width),
            "canvas_height": int(ctx.render_params.canvas_height),
            "coord_space": "pixel",
            "scene_id": SCENE_ID,
            "scene_variant": str(ctx.scene_variant),
            "native_layout_mode": str(ctx.native_layout_mode),
            "background_style": dict(ctx.background_meta),
            "information_scene_style": dict(ctx.style_meta),
            "post_image_noise": dict(ctx.post_noise_meta),
            "page_bbox_px": list(ctx.rendered.page_bbox_px),
            "layout": dict(ctx.rendered.layout_meta),
            "infographic_text_blocks": list(ctx.rendered.text_blocks),
            "font_assets": {
                "mixed_infographic_font_profile": dict(ctx.rendered.font_profile_meta),
            },
            "page_text_resources": dict(ctx.spec.text_resource_metadata),
            "module_kinds": [str(module.kind) for module in ctx.spec.modules],
            "page_visual_assets": {
                "asset_version": page_visual_asset_version(),
                "asset_root": "assets/pages/visual_assets",
                "semantic_policy": "non_answer_visual_context",
                "hero_anchor_drawn": "hero_anchor" in ctx.rendered.decorative_asset_bboxes_px,
                "roles": {
                    "hero_anchor": ctx.spec.hero_asset_selection.to_metadata(),
                    "module_section_assets": {
                        str(module.module_id): module.section_asset_selection.to_metadata()
                        for module in ctx.spec.modules
                    },
                    "item_badge_assets": {
                        str(module.module_id): {
                            str(item.item_id): item.visual_asset_selection.to_metadata()
                            for item in module.items
                        }
                        for module in ctx.spec.modules
                    },
                },
            },
        },
        "render_map": {
            "image_id": "img0",
            "page_bbox_px": list(ctx.rendered.page_bbox_px),
            "module_bboxes_px": dict(ctx.rendered.module_bboxes_px),
            "module_title_bboxes_px": dict(ctx.rendered.module_title_bboxes_px),
            "item_label_bboxes_px": dict(ctx.rendered.item_label_bboxes_px),
            "field_label_bboxes_px": dict(ctx.rendered.field_label_bboxes_px),
            "value_cell_bboxes_px": dict(ctx.rendered.value_cell_bboxes_px),
            "icon_bboxes_px": dict(ctx.rendered.icon_bboxes_px),
            "visual_asset_bboxes_px": {
                "hero_anchor": dict(ctx.rendered.decorative_asset_bboxes_px),
                "module_section_assets": dict(ctx.rendered.section_asset_bboxes_px),
                "item_badge_assets": dict(ctx.rendered.icon_bboxes_px),
            },
            "infographic_text_block_bboxes_px": dict(ctx.rendered.text_block_bboxes_px),
        },
        "execution_trace": dict(execution_trace),
        "witness_symbolic": {
            "type": str(witness_type),
            "target": dict(target),
            "answer_value": answer_value,
            "annotation_keys": [str(key) for key in annotation_keys],
        },
        "projected_annotation": _mixed_projected_annotation(str(annotation_type), annotation_value),
    }


def _mixed_complexity(ctx: _MixedSceneContext, *, lookup_reasoning: float) -> Any:
    max_cells = int(max(ctx.module_count_support) * max(ctx.item_count_support) * max(ctx.field_count_support))
    current_cells = int(sum(len(module.items) * len(module.fields) for module in ctx.spec.modules))
    return build_pages_complexity(
        weights=ctx.complexity_weights,
        components={
            "lookup_reasoning": float(lookup_reasoning),
            "visual_scan": normalize_int_with_bounds(
                current_cells,
                [min(ctx.module_count_support) * min(ctx.item_count_support) * min(ctx.field_count_support), max_cells],
            ),
            "layout_load": {
                "masonry_report": 0.62,
                "dashboard_blocks": 0.70,
                "poster_sections": 0.74,
                "compact_newsletter": 0.78,
                "collage_board": 0.84,
                "radial_mosaic": 0.88,
            }.get(str(ctx.scene_variant), 0.68),
        },
    )


@register_task
class PagesMixedInfographicModuleFieldValueLabelTask:
    """Read a visible value from one module on a dense mixed infographic page."""

    task_id = MIXED_INFOGRAPHIC_MODULE_FIELD_VALUE_TASK_ID
    domain = "pages"
    scene_id = SCENE_ID
    task_group = TASK_GROUP
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        ctx = _resolve_mixed_scene_context(
            task_id=self.task_id,
            query_ids=QUERY_IDS,
            params=params,
            instance_seed=int(instance_seed),
        )
        target_module, target_item, target_field, module_probs, item_probs, field_probs = _select_target(
            task_id=self.task_id,
            spec=ctx.spec,
            params=params,
            instance_seed=int(instance_seed),
        )
        answer_value = str(target_item.values_by_field_id[str(target_field.field_id)])
        module_id = str(target_module.module_id)
        item_id = str(target_item.item_id)
        field_id = str(target_field.field_id)
        annotation_keyed_bboxes = {
            "module_title": [float(value) for value in ctx.rendered.module_title_bboxes_px[module_id]],
            "item_label": [float(value) for value in ctx.rendered.item_label_bboxes_px[module_id][item_id]],
            "field_label": [float(value) for value in ctx.rendered.field_label_bboxes_px[module_id][field_id]],
            "value_cell": [float(value) for value in ctx.rendered.value_cell_bboxes_px[module_id][item_id][field_id]],
        }
        prompt_artifacts = _render_mixed_prompt(
            ctx=ctx,
            slots={
                "module_title": f'"{str(target_module.title)}"',
                "item_label": f'"{str(target_item.label)}"',
                "field_label": f'"{str(target_field.label)}"',
            },
            instance_seed=int(instance_seed),
        )
        prompt_defaults = _mixed_prompt_defaults(ctx)
        target_payload = {
            "module_id": str(target_module.module_id),
            "module_title": str(target_module.title),
            "module_kind": str(target_module.kind),
            "item_id": str(target_item.item_id),
            "item_label": str(target_item.label),
            "field_id": str(target_field.field_id),
            "field_label": str(target_field.label),
            "value": str(answer_value),
        }
        trace_payload = _build_mixed_trace_payload(
            ctx=ctx,
            prompt_artifacts=prompt_artifacts,
            prompt_defaults=prompt_defaults,
            target_payload=target_payload,
            answer_value=str(answer_value),
            annotation_type="keyed_bbox_map",
            annotation_value=dict(annotation_keyed_bboxes),
            witness_type=str(ctx.query_id),
            annotation_keys=list(annotation_keyed_bboxes.keys()),
            query_params_extra={
                "target_module_index_probabilities": dict(module_probs),
                "target_item_index_probabilities": dict(item_probs),
                "target_field_index_probabilities": dict(field_probs),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="string", value=str(answer_value)),
            annotation_gt=TypedValue(type="keyed_bbox_map", value=dict(annotation_keyed_bboxes)),
            image=ctx.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_mixed_complexity(ctx, lookup_reasoning=0.48),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(ctx.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class PagesMixedInfographicModuleFieldExtremumItemLabelTask:
    """Find the item with the highest or lowest visible value in one mixed infographic module."""

    task_id = MIXED_INFOGRAPHIC_FIELD_EXTREMUM_TASK_ID
    domain = "pages"
    scene_id = SCENE_ID
    task_group = TASK_GROUP
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        ctx = _resolve_mixed_scene_context(
            task_id=self.task_id,
            query_ids=FIELD_EXTREMUM_QUERY_IDS,
            params=params,
            instance_seed=int(instance_seed),
        )
        target_module, target_field, target, module_probs, field_probs, direction_probs = _select_extremum_target(
            task_id=self.task_id,
            gen_defaults=ctx.gen_defaults,
            spec=ctx.spec,
            params=params,
            instance_seed=int(instance_seed),
        )
        module_id = str(target_module.module_id)
        field_id = str(target_field.field_id)
        target_item_id = str(target["item_id"])
        annotation_keyed_bboxes: Dict[str, List[float]] = {
            "module_title": [float(value) for value in ctx.rendered.module_title_bboxes_px[module_id]],
            "field_label": [float(value) for value in ctx.rendered.field_label_bboxes_px[module_id][field_id]],
            "winning_item": [float(value) for value in ctx.rendered.item_label_bboxes_px[module_id][target_item_id]],
            "winning_value": [
                float(value)
                for value in ctx.rendered.value_cell_bboxes_px[module_id][target_item_id][field_id]
            ],
        }
        for index, candidate in enumerate(target["candidate_values"], start=1):
            annotation_keyed_bboxes[f"candidate_{index}"] = [
                float(value)
                for value in ctx.rendered.value_cell_bboxes_px[module_id][str(candidate["item_id"])][field_id]
            ]
        prompt_artifacts = _render_mixed_prompt(
            ctx=ctx,
            slots={
                "module_title": f'"{str(target_module.title)}"',
                "field_label": f'"{str(target_field.label)}"',
                "rank_direction": str(target["rank_direction"]),
                "rank_order_phrase": str(target["rank_order_phrase"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_defaults = _mixed_prompt_defaults(ctx)
        trace_payload = _build_mixed_trace_payload(
            ctx=ctx,
            prompt_artifacts=prompt_artifacts,
            prompt_defaults=prompt_defaults,
            target_payload=target,
            answer_value=str(target["item_label"]),
            annotation_type="keyed_bbox_map",
            annotation_value=dict(annotation_keyed_bboxes),
            witness_type=str(ctx.query_id),
            annotation_keys=list(annotation_keyed_bboxes.keys()),
            query_params_extra={
                "target_module_index_probabilities": dict(module_probs),
                "target_field_index_probabilities": dict(field_probs),
                "rank_direction_probabilities": dict(direction_probs),
            },
            execution_extra={"rank_direction": str(target["rank_direction"])},
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="string", value=str(target["item_label"])),
            annotation_gt=TypedValue(type="keyed_bbox_map", value=dict(annotation_keyed_bboxes)),
            image=ctx.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_mixed_complexity(ctx, lookup_reasoning=0.58),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(ctx.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class PagesMixedInfographicModuleFieldRankedItemLabelTask:
    """Find the item at a requested numeric rank in one mixed infographic module field."""

    task_id = MIXED_INFOGRAPHIC_FIELD_RANKED_TASK_ID
    domain = "pages"
    scene_id = SCENE_ID
    task_group = TASK_GROUP
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        ctx = _resolve_mixed_scene_context(
            task_id=self.task_id,
            query_ids=FIELD_RANKED_QUERY_IDS,
            params=params,
            instance_seed=int(instance_seed),
        )
        target_module, target_field, target, module_probs, field_probs, direction_probs, rank_position_probs = (
            _select_ranked_target(
                task_id=self.task_id,
                gen_defaults=ctx.gen_defaults,
                spec=ctx.spec,
                params=params,
                instance_seed=int(instance_seed),
            )
        )
        module_id = str(target_module.module_id)
        field_id = str(target_field.field_id)
        target_item_id = str(target["item_id"])
        annotation_keyed_bboxes: Dict[str, List[float]] = {
            "module_title": [float(value) for value in ctx.rendered.module_title_bboxes_px[module_id]],
            "field_label": [float(value) for value in ctx.rendered.field_label_bboxes_px[module_id][field_id]],
            "ranked_item": [float(value) for value in ctx.rendered.item_label_bboxes_px[module_id][target_item_id]],
            "ranked_value": [
                float(value)
                for value in ctx.rendered.value_cell_bboxes_px[module_id][target_item_id][field_id]
            ],
        }
        for index, candidate in enumerate(target["candidate_values"], start=1):
            annotation_keyed_bboxes[f"candidate_{index}"] = [
                float(value)
                for value in ctx.rendered.value_cell_bboxes_px[module_id][str(candidate["item_id"])][field_id]
            ]
        prompt_artifacts = _render_mixed_prompt(
            ctx=ctx,
            slots={
                "module_title": f'"{str(target_module.title)}"',
                "field_label": f'"{str(target_field.label)}"',
                "rank_ordinal": str(target["rank_ordinal"]),
                "rank_direction": str(target["rank_direction"]),
                "rank_order_phrase": str(target["rank_order_phrase"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_defaults = _mixed_prompt_defaults(ctx)
        trace_payload = _build_mixed_trace_payload(
            ctx=ctx,
            prompt_artifacts=prompt_artifacts,
            prompt_defaults=prompt_defaults,
            target_payload=target,
            answer_value=str(target["item_label"]),
            annotation_type="keyed_bbox_map",
            annotation_value=dict(annotation_keyed_bboxes),
            witness_type=str(ctx.query_id),
            annotation_keys=list(annotation_keyed_bboxes.keys()),
            query_params_extra={
                "target_module_index_probabilities": dict(module_probs),
                "target_field_index_probabilities": dict(field_probs),
                "rank_direction_probabilities": dict(direction_probs),
                "rank_position_probabilities": dict(rank_position_probs),
            },
            execution_extra={
                "rank_direction": str(target["rank_direction"]),
                "rank_position": int(target["rank_position"]),
                "rank_ordinal": str(target["rank_ordinal"]),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="string", value=str(target["item_label"])),
            annotation_gt=TypedValue(type="keyed_bbox_map", value=dict(annotation_keyed_bboxes)),
            image=ctx.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_mixed_complexity(ctx, lookup_reasoning=0.60),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(ctx.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class PagesMixedInfographicPageFieldExtremumModuleLabelTask:
    """Find the module with the highest or lowest value for one shared field across the page."""

    task_id = MIXED_INFOGRAPHIC_PAGE_FIELD_EXTREMUM_TASK_ID
    domain = "pages"
    scene_id = SCENE_ID
    task_group = TASK_GROUP
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        ctx = _resolve_mixed_scene_context(
            task_id=self.task_id,
            query_ids=PAGE_FIELD_EXTREMUM_QUERY_IDS,
            params=params,
            instance_seed=int(instance_seed),
        )
        target_module, target_field, target, field_label_probs, direction_probs = _select_page_field_extremum_target(
            task_id=self.task_id,
            gen_defaults=ctx.gen_defaults,
            spec=ctx.spec,
            params=params,
            instance_seed=int(instance_seed),
        )
        module_id = str(target_module.module_id)
        field_id = str(target_field.field_id)
        item_id = str(target["item_id"])
        annotation_keyed_bboxes: Dict[str, List[float]] = {
            "winning_module_title": [float(value) for value in ctx.rendered.module_title_bboxes_px[module_id]],
            "winning_field_label": [float(value) for value in ctx.rendered.field_label_bboxes_px[module_id][field_id]],
            "winning_item": [float(value) for value in ctx.rendered.item_label_bboxes_px[module_id][item_id]],
            "winning_value": [
                float(value)
                for value in ctx.rendered.value_cell_bboxes_px[module_id][item_id][field_id]
            ],
        }
        for index, candidate in enumerate(target["candidate_values"], start=1):
            annotation_keyed_bboxes[f"candidate_{index}"] = [
                float(value)
                for value in ctx.rendered.value_cell_bboxes_px[str(candidate["module_id"])][str(candidate["item_id"])][
                    str(candidate["field_id"])
                ]
            ]
        prompt_artifacts = _render_mixed_prompt(
            ctx=ctx,
            slots={
                "field_label": f'"{str(target["field_label"])}"',
                "rank_direction": str(target["rank_direction"]),
                "rank_order_phrase": str(target["rank_order_phrase"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_defaults = _mixed_prompt_defaults(ctx)
        trace_payload = _build_mixed_trace_payload(
            ctx=ctx,
            prompt_artifacts=prompt_artifacts,
            prompt_defaults=prompt_defaults,
            target_payload=target,
            answer_value=str(target["answer_value"]),
            annotation_type="keyed_bbox_map",
            annotation_value=dict(annotation_keyed_bboxes),
            witness_type=str(ctx.query_id),
            annotation_keys=list(annotation_keyed_bboxes.keys()),
            query_params_extra={
                "target_field_label_probabilities": dict(field_label_probs),
                "rank_direction_probabilities": dict(direction_probs),
            },
            execution_extra={
                "rank_direction": str(target["rank_direction"]),
                "target_field_label": str(target["field_label"]),
                "candidate_module_count": int(target["candidate_module_count"]),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="string", value=str(target["answer_value"])),
            annotation_gt=TypedValue(type="keyed_bbox_map", value=dict(annotation_keyed_bboxes)),
            image=ctx.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_mixed_complexity(ctx, lookup_reasoning=0.66),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(ctx.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class PagesMixedInfographicModuleTwoFieldConditionItemLabelTask:
    """Find the item satisfying one numeric condition and one categorical condition in a module."""

    task_id = MIXED_INFOGRAPHIC_TWO_FIELD_CONDITION_TASK_ID
    domain = "pages"
    scene_id = SCENE_ID
    task_group = TASK_GROUP
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        ctx = _resolve_mixed_scene_context(
            task_id=self.task_id,
            query_ids=TWO_FIELD_CONDITION_QUERY_IDS,
            params=params,
            instance_seed=int(instance_seed),
        )
        (
            target_module,
            numeric_field,
            category_field,
            target,
            module_probs,
            numeric_field_probs,
            category_field_probs,
            operator_probs,
            category_value_probs,
            threshold_probs,
        ) = _select_two_field_condition_target(
            task_id=self.task_id,
            gen_defaults=ctx.gen_defaults,
            spec=ctx.spec,
            params=params,
            instance_seed=int(instance_seed),
        )
        module_id = str(target_module.module_id)
        item_id = str(target["item_id"])
        numeric_field_id = str(numeric_field.field_id)
        category_field_id = str(category_field.field_id)
        annotation_keyed_bboxes: Dict[str, List[float]] = {
            "module_title": [float(value) for value in ctx.rendered.module_title_bboxes_px[module_id]],
            "numeric_field_label": [
                float(value) for value in ctx.rendered.field_label_bboxes_px[module_id][numeric_field_id]
            ],
            "category_field_label": [
                float(value) for value in ctx.rendered.field_label_bboxes_px[module_id][category_field_id]
            ],
            "matching_item": [float(value) for value in ctx.rendered.item_label_bboxes_px[module_id][item_id]],
            "numeric_value_cell": [
                float(value) for value in ctx.rendered.value_cell_bboxes_px[module_id][item_id][numeric_field_id]
            ],
            "category_value_cell": [
                float(value) for value in ctx.rendered.value_cell_bboxes_px[module_id][item_id][category_field_id]
            ],
        }
        prompt_artifacts = _render_mixed_prompt(
            ctx=ctx,
            slots={
                "module_title": f'"{str(target_module.title)}"',
                "numeric_field_label": f'"{str(numeric_field.label)}"',
                "condition_phrase": str(target["condition_phrase"]),
                "threshold_value": f'"{str(target["threshold_visible"])}"',
                "category_field_label": f'"{str(category_field.label)}"',
                "category_value": f'"{str(target["category_value"])}"',
            },
            instance_seed=int(instance_seed),
        )
        prompt_defaults = _mixed_prompt_defaults(ctx)
        trace_payload = _build_mixed_trace_payload(
            ctx=ctx,
            prompt_artifacts=prompt_artifacts,
            prompt_defaults=prompt_defaults,
            target_payload=target,
            answer_value=str(target["answer_value"]),
            annotation_type="keyed_bbox_map",
            annotation_value=dict(annotation_keyed_bboxes),
            witness_type=str(ctx.query_id),
            annotation_keys=list(annotation_keyed_bboxes.keys()),
            query_params_extra={
                "target_module_index_probabilities": dict(module_probs),
                "target_numeric_field_index_probabilities": dict(numeric_field_probs),
                "target_category_field_index_probabilities": dict(category_field_probs),
                "condition_operator_probabilities": dict(operator_probs),
                "category_value_probabilities": dict(category_value_probs),
                "threshold_rank_index_probabilities": dict(threshold_probs),
            },
            execution_extra={
                "condition_operator": str(target["condition_operator"]),
                "threshold_value": int(target["threshold_value"]),
                "threshold_visible": str(target["threshold_visible"]),
                "category_value": str(target["category_value"]),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="string", value=str(target["answer_value"])),
            annotation_gt=TypedValue(type="keyed_bbox_map", value=dict(annotation_keyed_bboxes)),
            image=ctx.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_mixed_complexity(ctx, lookup_reasoning=0.62),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(ctx.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class PagesMixedInfographicModuleConditionItemCountTask:
    """Count items in one mixed infographic module whose field value satisfies a numeric condition."""

    task_id = MIXED_INFOGRAPHIC_CONDITION_COUNT_TASK_ID
    domain = "pages"
    scene_id = SCENE_ID
    task_group = TASK_GROUP
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        ctx = _resolve_mixed_scene_context(
            task_id=self.task_id,
            query_ids=CONDITION_COUNT_QUERY_IDS,
            params=params,
            instance_seed=int(instance_seed),
        )
        target_module, target_field, target, module_probs, field_probs, operator_probs, threshold_probs, answer_count_probs = (
            _select_condition_target(
                task_id=self.task_id,
                gen_defaults=ctx.gen_defaults,
                spec=ctx.spec,
                params=params,
                instance_seed=int(instance_seed),
            )
        )
        module_id = str(target_module.module_id)
        field_id = str(target_field.field_id)
        annotation_bboxes = [
            [
                float(value)
                for value in ctx.rendered.value_cell_bboxes_px[module_id][str(match["item_id"])][field_id]
            ]
            for match in target["matching_values"]
        ]
        prompt_artifacts = _render_mixed_prompt(
            ctx=ctx,
            slots={
                "module_title": f'"{str(target_module.title)}"',
                "field_label": f'"{str(target_field.label)}"',
                "condition_phrase": str(target["condition_phrase"]),
                "threshold_value": f'"{str(target["threshold_visible"])}"',
            },
            instance_seed=int(instance_seed),
        )
        prompt_defaults = _mixed_prompt_defaults(ctx)
        trace_payload = _build_mixed_trace_payload(
            ctx=ctx,
            prompt_artifacts=prompt_artifacts,
            prompt_defaults=prompt_defaults,
            target_payload=target,
            answer_value=int(target["answer_value"]),
            annotation_type="bbox_set",
            annotation_value=list(annotation_bboxes),
            witness_type=str(ctx.query_id),
            annotation_keys=[str(match["item_id"]) for match in target["matching_values"]],
            query_params_extra={
                "target_module_index_probabilities": dict(module_probs),
                "target_field_index_probabilities": dict(field_probs),
                "condition_operator_probabilities": dict(operator_probs),
                "threshold_rank_index_probabilities": dict(threshold_probs),
                "condition_answer_count_probabilities": dict(answer_count_probs),
            },
            execution_extra={
                "condition_operator": str(target["condition_operator"]),
                "condition_answer_count": int(target["answer_value"]),
                "threshold_value": int(target["threshold_value"]),
                "threshold_visible": str(target["threshold_visible"]),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(target["answer_value"])),
            annotation_gt=TypedValue(type="bbox_set", value=list(annotation_bboxes)),
            image=ctx.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_mixed_complexity(ctx, lookup_reasoning=0.54),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(ctx.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class PagesMixedInfographicModuleFieldTotalValueTask:
    """Sum one additive numeric field across all items in one mixed infographic module."""

    task_id = MIXED_INFOGRAPHIC_FIELD_TOTAL_TASK_ID
    domain = "pages"
    scene_id = SCENE_ID
    task_group = TASK_GROUP
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        ctx = _resolve_mixed_scene_context(
            task_id=self.task_id,
            query_ids=FIELD_TOTAL_QUERY_IDS,
            params=params,
            instance_seed=int(instance_seed),
        )
        target_module, target_field, target, module_probs, field_probs = _select_total_target(
            task_id=self.task_id,
            spec=ctx.spec,
            params=params,
            instance_seed=int(instance_seed),
        )
        module_id = str(target_module.module_id)
        field_id = str(target_field.field_id)
        annotation_bboxes = [
            [
                float(value)
                for value in ctx.rendered.value_cell_bboxes_px[module_id][str(value_payload["item_id"])][field_id]
            ]
            for value_payload in target["summed_values"]
        ]
        prompt_artifacts = _render_mixed_prompt(
            ctx=ctx,
            slots={
                "module_title": f'"{str(target_module.title)}"',
                "field_label": f'"{str(target_field.label)}"',
            },
            instance_seed=int(instance_seed),
        )
        prompt_defaults = _mixed_prompt_defaults(ctx)
        trace_payload = _build_mixed_trace_payload(
            ctx=ctx,
            prompt_artifacts=prompt_artifacts,
            prompt_defaults=prompt_defaults,
            target_payload=target,
            answer_value=int(target["answer_value"]),
            annotation_type="bbox_set",
            annotation_value=list(annotation_bboxes),
            witness_type=str(ctx.query_id),
            annotation_keys=[str(value_payload["item_id"]) for value_payload in target["summed_values"]],
            query_params_extra={
                "target_module_index_probabilities": dict(module_probs),
                "target_field_index_probabilities": dict(field_probs),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(target["answer_value"])),
            annotation_gt=TypedValue(type="bbox_set", value=list(annotation_bboxes)),
            image=ctx.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_mixed_complexity(ctx, lookup_reasoning=0.56),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(ctx.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class PagesMixedInfographicTwoModuleFieldTotalComparisonModuleLabelTask:
    """Compare totals for one additive field across two mixed infographic modules."""

    task_id = MIXED_INFOGRAPHIC_TWO_MODULE_TOTAL_COMPARISON_TASK_ID
    domain = "pages"
    scene_id = SCENE_ID
    task_group = TASK_GROUP
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        ctx = _resolve_mixed_scene_context(
            task_id=self.task_id,
            query_ids=TWO_MODULE_TOTAL_COMPARISON_QUERY_IDS,
            params=params,
            instance_seed=int(instance_seed),
        )
        module_a, field_a, module_b, field_b, target, field_label_probs, module_pair_probs = (
            _select_two_module_total_comparison_target(
                task_id=self.task_id,
                spec=ctx.spec,
                params=params,
                instance_seed=int(instance_seed),
            )
        )
        module_a_id = str(module_a.module_id)
        module_b_id = str(module_b.module_id)
        field_a_id = str(field_a.field_id)
        field_b_id = str(field_b.field_id)
        annotation_keyed_bboxes: Dict[str, List[float]] = {
            "module_a_title": [float(value) for value in ctx.rendered.module_title_bboxes_px[module_a_id]],
            "module_b_title": [float(value) for value in ctx.rendered.module_title_bboxes_px[module_b_id]],
            "field_label_a": [float(value) for value in ctx.rendered.field_label_bboxes_px[module_a_id][field_a_id]],
            "field_label_b": [float(value) for value in ctx.rendered.field_label_bboxes_px[module_b_id][field_b_id]],
        }
        for index, value_payload in enumerate(target["module_a"]["summed_values"], start=1):
            annotation_keyed_bboxes[f"module_a_value_{index}"] = [
                float(value)
                for value in ctx.rendered.value_cell_bboxes_px[module_a_id][str(value_payload["item_id"])][field_a_id]
            ]
        for index, value_payload in enumerate(target["module_b"]["summed_values"], start=1):
            annotation_keyed_bboxes[f"module_b_value_{index}"] = [
                float(value)
                for value in ctx.rendered.value_cell_bboxes_px[module_b_id][str(value_payload["item_id"])][field_b_id]
            ]
        prompt_artifacts = _render_mixed_prompt(
            ctx=ctx,
            slots={
                "module_a_title": f'"{str(module_a.title)}"',
                "module_b_title": f'"{str(module_b.title)}"',
                "field_label": f'"{str(target["field_label"])}"',
            },
            instance_seed=int(instance_seed),
        )
        prompt_defaults = _mixed_prompt_defaults(ctx)
        trace_payload = _build_mixed_trace_payload(
            ctx=ctx,
            prompt_artifacts=prompt_artifacts,
            prompt_defaults=prompt_defaults,
            target_payload=target,
            answer_value=str(target["answer_value"]),
            annotation_type="keyed_bbox_map",
            annotation_value=dict(annotation_keyed_bboxes),
            witness_type=str(ctx.query_id),
            annotation_keys=list(annotation_keyed_bboxes.keys()),
            query_params_extra={
                "target_field_label_probabilities": dict(field_label_probs),
                "target_module_pair_probabilities": dict(module_pair_probs),
            },
            execution_extra={
                "target_field_label": str(target["field_label"]),
                "module_a_total": int(target["module_a_total"]),
                "module_b_total": int(target["module_b_total"]),
                "winning_side": str(target["winning_side"]),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="string", value=str(target["answer_value"])),
            annotation_gt=TypedValue(type="keyed_bbox_map", value=dict(annotation_keyed_bboxes)),
            image=ctx.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_mixed_complexity(ctx, lookup_reasoning=0.68),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(ctx.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = [
    "MIXED_INFOGRAPHIC_TASK_ID",
    "MIXED_INFOGRAPHIC_MODULE_FIELD_VALUE_TASK_ID",
    "MIXED_INFOGRAPHIC_FIELD_EXTREMUM_TASK_ID",
    "MIXED_INFOGRAPHIC_FIELD_RANKED_TASK_ID",
    "MIXED_INFOGRAPHIC_TWO_FIELD_CONDITION_TASK_ID",
    "MIXED_INFOGRAPHIC_CONDITION_COUNT_TASK_ID",
    "MIXED_INFOGRAPHIC_FIELD_TOTAL_TASK_ID",
    "MIXED_INFOGRAPHIC_PAGE_FIELD_EXTREMUM_TASK_ID",
    "MIXED_INFOGRAPHIC_TWO_MODULE_TOTAL_COMPARISON_TASK_ID",
    "QUERY_ID",
    "MODULE_FIELD_VALUE_QUERY_ID",
    "FIELD_EXTREMUM_QUERY_ID",
    "FIELD_RANKED_QUERY_ID",
    "TWO_FIELD_CONDITION_QUERY_ID",
    "CONDITION_COUNT_QUERY_ID",
    "FIELD_TOTAL_QUERY_ID",
    "PAGE_FIELD_EXTREMUM_QUERY_ID",
    "TWO_MODULE_TOTAL_COMPARISON_QUERY_ID",
    "SCENE_ID",
    "SCENE_VARIANTS",
    "PagesMixedInfographicModuleFieldValueLabelTask",
    "PagesMixedInfographicModuleFieldExtremumItemLabelTask",
    "PagesMixedInfographicModuleFieldRankedItemLabelTask",
    "PagesMixedInfographicPageFieldExtremumModuleLabelTask",
    "PagesMixedInfographicModuleTwoFieldConditionItemLabelTask",
    "PagesMixedInfographicModuleConditionItemCountTask",
    "PagesMixedInfographicModuleFieldTotalValueTask",
    "PagesMixedInfographicTwoModuleFieldTotalComparisonModuleLabelTask",
]
