"""Runtime helpers for mixed-infographic page scene-package tasks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image

from .....core.scene_config import get_scene_defaults
from .....core.types import TypedValue
from .....core.visual.noise import apply_post_image_noise
from ....base import TaskOutput
from ....shared.config_defaults import required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ....shared.output_metadata import default_task_versions
from ....shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ....shared.visual_style.information_scene import make_information_scene_background
from ...shared.information_style import resolve_pages_information_style
from ...shared.page_visual_assets import page_visual_asset_version
from ...shared.visual_defaults import load_pages_scene_noise_defaults
from .layout import (
    NATIVE_LAYOUT_MODES,
    NATIVE_LAYOUT_MODE_WEIGHTS,
    _RenderParams,
    _resolve_native_layout_mode,
    _resolve_native_text_block_count,
    _resolve_render_params,
)
from .model import (
    ADDITIVE_FIELD_LABELS,
    MODULE_KINDS,
    NUMERIC_FIELD_LABELS,
    _MixedInfographicSpec,
)
from .rendering import (
    _RenderedMixedInfographic,
    _render_mixed_infographic,
    _resolve_mixed_font_profile,
)
from .sampling import (
    resolve_int_support as _resolve_int_support,
    resolve_named_variant as _resolve_named_variant,
    resolve_supported_int as _resolve_supported_int,
)
from .spec import _build_mixed_spec
from .targets import (
    _select_condition_target,
    _select_extremum_target,
    _select_page_field_extremum_target,
    _select_ranked_target,
    _select_target,
    _select_total_target,
    _select_two_field_condition_target,
    _select_two_module_total_comparison_target,
)


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


@dataclass(frozen=True)
class _MixedSceneContext:
    task_id: str
    query_id: str
    gen_defaults: Dict[str, Any]
    render_defaults: Dict[str, Any]
    prompt_defaults: Dict[str, Any]
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


_SCENE_DEFAULTS = get_scene_defaults("pages", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=MIXED_INFOGRAPHIC_TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_pages_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.5)


def _mixed_task_defaults(task_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    gen_defaults, render_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
        _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
        task_id=str(task_id),
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
        resource_namespace=MIXED_INFOGRAPHIC_TASK_ID,
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
        allow_dark=True,
    )
    background, background_meta = make_information_scene_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=style,
        instance_seed=int(instance_seed),
        namespace=f"pages.{SCENE_ID}.information_scene_background",
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
    prompt_selection = render_scene_prompt_variants(
        domain="pages",
        scene_id=SCENE_ID,
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




class PagesMixedInfographicModuleFieldValueLabelTask:
    """Read a visible value from one module on a dense mixed infographic page."""

    task_id = MIXED_INFOGRAPHIC_MODULE_FIELD_VALUE_TASK_ID
    domain = "pages"
    scene_id = SCENE_ID
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
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(ctx.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


class PagesMixedInfographicModuleFieldExtremumItemLabelTask:
    """Find the item with the highest or lowest visible value in one mixed infographic module."""

    task_id = MIXED_INFOGRAPHIC_FIELD_EXTREMUM_TASK_ID
    domain = "pages"
    scene_id = SCENE_ID
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
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(ctx.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


class PagesMixedInfographicModuleFieldRankedItemLabelTask:
    """Find the item at a requested numeric rank in one mixed infographic module field."""

    task_id = MIXED_INFOGRAPHIC_FIELD_RANKED_TASK_ID
    domain = "pages"
    scene_id = SCENE_ID
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
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(ctx.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


class PagesMixedInfographicPageFieldExtremumModuleLabelTask:
    """Find the module with the highest or lowest value for one shared field across the page."""

    task_id = MIXED_INFOGRAPHIC_PAGE_FIELD_EXTREMUM_TASK_ID
    domain = "pages"
    scene_id = SCENE_ID
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
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(ctx.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


class PagesMixedInfographicModuleTwoFieldConditionItemLabelTask:
    """Find the item satisfying one numeric condition and one categorical condition in a module."""

    task_id = MIXED_INFOGRAPHIC_TWO_FIELD_CONDITION_TASK_ID
    domain = "pages"
    scene_id = SCENE_ID
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
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(ctx.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


class PagesMixedInfographicModuleConditionItemCountTask:
    """Count items in one mixed infographic module whose field value satisfies a numeric condition."""

    task_id = MIXED_INFOGRAPHIC_CONDITION_COUNT_TASK_ID
    domain = "pages"
    scene_id = SCENE_ID
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
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(ctx.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


class PagesMixedInfographicModuleFieldTotalValueTask:
    """Sum one additive numeric field across all items in one mixed infographic module."""

    task_id = MIXED_INFOGRAPHIC_FIELD_TOTAL_TASK_ID
    domain = "pages"
    scene_id = SCENE_ID
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
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(ctx.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


class PagesMixedInfographicTwoModuleFieldTotalComparisonModuleLabelTask:
    """Compare totals for one additive field across two mixed infographic modules."""

    task_id = MIXED_INFOGRAPHIC_TWO_MODULE_TOTAL_COMPARISON_TASK_ID
    domain = "pages"
    scene_id = SCENE_ID
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
