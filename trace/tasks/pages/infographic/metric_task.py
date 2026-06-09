"""Task wrappers and output assembly for infographic metric-card page tasks."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults
from ...shared.fixed_query import explicit_query_id_param, normalize_query_id_params
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.complexity import build_pages_complexity, normalize_int_with_bounds
from ..shared.fixed_query_task import rewrite_pages_public_task_output
from ..shared.page_semantic_assets import page_semantic_asset_label, page_semantic_asset_manifest_metadata
from ..shared.public_query_task import rewrite_pages_query_output
from .metric_common import (
    COLUMN_PROFILE_COMPARISON_VARIANTS,
    FACT_LOOKUP_VARIANTS,
    FILTERED_METRIC_TOTAL_VARIANTS,
    FILTERED_SECTION_EXTREMUM_VARIANTS,
    METRIC_RANKED_ITEM_VARIANTS,
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    SCENE_ID,
    SECTION_RANKED_TOTAL_VARIANTS,
    SUPPORTED_QUERY_IDS,
    TASK_ID,
    _COMPLEXITY_WEIGHTS,
    _PROMPT_DEFAULTS,
    _REASONING_LOAD_BY_VARIANT,
    _RENDER_DEFAULTS,
    _quote_label,
    _quoted_label_list,
)
from .metric_dataset import _build_dataset, _resolve_query_id
from .metric_rendering import _render_infographic


def _icon_prompt_label(icon_kind: str) -> str:
    if not str(icon_kind).strip():
        return ""
    label = page_semantic_asset_label(str(icon_kind))
    return str(label).removesuffix(" icon")


def _annotation_keyed_bboxes(
    *,
    card_traces: Sequence[Mapping[str, Any]],
    target_labels: Sequence[str],
    section_bboxes: Mapping[str, Sequence[float]] | None = None,
    section_title_bboxes: Mapping[str, Sequence[float]] | None = None,
    annotation_targets: Sequence[Mapping[str, Any]] | None = None,
) -> Dict[str, List[float]]:
    by_label = {str(card["label"]): dict(card) for card in card_traces}
    section_map = {
        str(section): [float(value) for value in bbox]
        for section, bbox in dict(section_bboxes or {}).items()
    }
    section_title_map = {
        str(section): [float(value) for value in bbox]
        for section, bbox in dict(section_title_bboxes or {}).items()
    }
    keyed_bboxes: Dict[str, List[float]] = {}
    if annotation_targets is not None and len(annotation_targets) > 0:
        for target in annotation_targets:
            bbox_kind = str(target.get("bbox_kind", "card"))
            if str(bbox_kind) == "section":
                section = str(target["section"])
                if section not in section_map:
                    raise ValueError(f"unknown infographic annotation section: {section}")
                key = str(target.get("key", section))
                keyed_bboxes[str(key)] = [float(value) for value in section_map[section]]
                continue
            if str(bbox_kind) == "section_title":
                section = str(target["section"])
                if section not in section_title_map:
                    raise ValueError(f"unknown infographic annotation section title: {section}")
                key = str(target.get("key", "section_title"))
                keyed_bboxes[str(key)] = [float(value) for value in section_title_map[section]]
                continue
            label = str(target["label"])
            if label not in by_label:
                raise ValueError(f"unknown infographic annotation label: {label}")
            card = by_label[label]
            bbox_key = {
                "label": "label_bbox_px",
                "value": "value_bbox_px",
                "card": "card_bbox_px",
                "caption": "caption_bbox_px",
            }.get(str(bbox_kind), "card_bbox_px")
            key = str(target.get("key", label))
            keyed_bboxes[str(key)] = [float(value) for value in card[str(bbox_key)]]
        return keyed_bboxes
    for label in target_labels:
        card = by_label[str(label)]
        keyed_bboxes[str(label)] = [float(value) for value in card["card_bbox_px"]]
    return keyed_bboxes


def _build_prompt_examples(*, answer_type: str, query_id: str) -> Tuple[str, str]:
    example_answer: int | str
    example_annotation: Dict[str, List[int]]
    if str(answer_type) != "string":
        example_answer = 64
        example_annotation = {
            "Atlas": [108, 164, 248, 258],
            "Beacon": [398, 164, 538, 258],
        }
    elif str(query_id) == "value_for_named_item":
        example_answer = "64"
        example_annotation = {"Atlas": [108, 164, 248, 258]}
    elif str(query_id) == "item_for_named_value":
        example_answer = "Atlas"
        example_annotation = {"Atlas": [108, 164, 248, 258]}
    elif str(query_id) == "detail_for_named_item":
        example_answer = "Ref 42"
        example_annotation = {"Atlas": [108, 164, 248, 258]}
    elif str(query_id) in METRIC_RANKED_ITEM_VARIANTS:
        example_answer = "Atlas"
        example_annotation = {
            "target_metric": [108, 164, 180, 188],
            "target_value": [108, 196, 168, 230],
        }
        if str(query_id).endswith("_in_section_label"):
            example_annotation = {
                "section_title": [80, 120, 220, 150],
                **example_annotation,
            }
    else:
        example_answer = "Program Totals"
        example_annotation = {
            "Atlas": [108, 164, 248, 258],
            "Beacon": [398, 164, 538, 258],
        }
    answer_and_annotation = {
        "annotation": dict(example_annotation),
        "answer": example_answer,
    }
    answer_only = {"answer": example_answer}
    return (
        json.dumps(answer_and_annotation, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
    )


class PagesInfographicMetricArithmeticValueTask:
    """Compute arithmetic over printed values in a poster-style infographic."""

    task_id = TASK_ID
    domain = "pages"
    task_group = "infographic"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        dataset = _build_dataset(query_id=str(query_id), params=params, instance_seed=int(instance_seed))

        canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 940)))
        canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 900)))
        background, background_meta = make_background_canvas(
            canvas_width=int(canvas_width),
            canvas_height=int(canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        render_params = dict(_RENDER_DEFAULTS)
        if params.get("infographic_style") is not None:
            render_params["infographic_style"] = params["infographic_style"]
        rendered = _render_infographic(
            background,
            cards=dataset["cards"],
            section_titles=dataset["section_titles"],
            section_card_counts=dataset["section_card_counts"],
            render_defaults=render_params,
            instance_seed=int(instance_seed),
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "answer_hint_label",
                "annotation_hint",
                "annotation_hint_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        answer_type = str(dataset.get("answer_type", "integer"))
        answer_value_for_trace: int | str
        if answer_type == "string":
            answer_value_for_trace = str(dataset["answer_value"])
        else:
            answer_value_for_trace = int(dataset["answer_value"])
        json_example, json_example_answer_only = _build_prompt_examples(answer_type=answer_type, query_id=str(query_id))
        target_labels = [str(label) for label in dataset["target_labels"]]
        target_values = [int(value) for value in dataset["target_values"]]
        target_groups = {
            str(key): [str(label) for label in value]
            for key, value in dict(dataset["target_groups"]).items()
        }
        target_sections = [str(section) for section in dataset["target_sections"]]
        excluded_labels = [str(label) for label in dataset["excluded_labels"]]
        target_extrema = [str(extremum) for extremum in dataset["target_extrema"]]
        extrema_operation = str(dataset["extrema_operation"])
        extrema_operation_phrase = "absolute difference" if str(extrema_operation) == "absolute_difference" else str(extrema_operation)
        answer_hint_key = "answer_hint_label" if answer_type == "string" else "answer_hint"
        annotation_hint_key = "annotation_hint_label" if answer_type == "string" else "annotation_hint"
        answer_hint = str(prompt_defaults.get(answer_hint_key, prompt_defaults["answer_hint"]))
        annotation_hint = str(prompt_defaults.get(annotation_hint_key, prompt_defaults["annotation_hint"]))
        if str(query_id) in METRIC_RANKED_ITEM_VARIANTS:
            ranked_annotation_key = (
                "annotation_hint_metric_ranked_item_scoped"
                if target_sections
                else "annotation_hint_metric_ranked_item"
            )
            annotation_hint = str(_PROMPT_DEFAULTS.get(ranked_annotation_key, annotation_hint))
        group_a_labels = target_groups.get("group_a", target_groups.get("section_a", []))
        group_b_labels = target_groups.get("group_b", target_groups.get("section_b", []))
        if not group_a_labels:
            group_a_labels = target_labels[: max(1, len(target_labels) // 2)]
        if not group_b_labels:
            group_b_labels = target_labels[max(1, len(target_labels) // 2) :]
        prompt_slots = {
            "target_label": _quote_label(target_labels[0]),
            "target_label_a": _quote_label(target_labels[0]),
            "target_label_b": _quote_label(target_labels[1]) if len(target_labels) > 1 else "",
            "target_labels": _quoted_label_list(target_labels),
            "target_group_a": _quoted_label_list(group_a_labels),
            "target_group_b": _quoted_label_list(group_b_labels),
            "target_section": _quote_label(target_sections[0]) if target_sections else "",
            "target_section_a": _quote_label(target_sections[0]) if len(target_sections) >= 1 else "",
            "target_section_b": _quote_label(target_sections[1]) if len(target_sections) >= 2 else "",
            "target_extremum_a": str(target_extrema[0]) if len(target_extrema) >= 1 else "",
            "target_extremum_b": str(target_extrema[1]) if len(target_extrema) >= 2 else "",
            "extrema_operation": str(extrema_operation_phrase),
            "rank_direction": str(dataset.get("rank_direction", "")),
            "rank_ordinal": str(dataset.get("rank_ordinal", "")),
            "rank_order_phrase": (
                "highest to lowest"
                if str(dataset.get("rank_direction", "")) == "highest"
                else "lowest to highest"
            ),
            "rank_position": str(dataset.get("rank_position", "")),
            "excluded_labels": _quoted_label_list(excluded_labels) if excluded_labels else "",
            "filter_icon_kind": _icon_prompt_label(str(dataset.get("filter_icon_kind", ""))),
            "comparison_icon_kind": _icon_prompt_label(str(dataset.get("comparison_icon_kind", ""))),
            "target_value": _quote_label(str(dataset.get("target_value_text", ""))) if dataset.get("target_value_text") else "",
            "target_detail": _quote_label(str(dataset.get("target_detail_text", ""))) if dataset.get("target_detail_text") else "",
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(annotation_hint),
            "answer_hint": str(answer_hint),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        }
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots=prompt_slots,
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        annotation_targets = [dict(item) for item in list(dataset.get("annotation_targets", []))]
        annotation_keyed_bboxes = _annotation_keyed_bboxes(
            card_traces=rendered.card_traces,
            target_labels=target_labels,
            section_bboxes=rendered.section_bboxes,
            section_title_bboxes=rendered.section_title_bboxes,
            annotation_targets=annotation_targets,
        )
        annotation_bboxes = [list(bbox) for bbox in annotation_keyed_bboxes.values()]
        answer_gt = TypedValue(type=answer_type, value=answer_value_for_trace)
        annotation_gt = TypedValue(type="keyed_bbox_map", value=dict(annotation_keyed_bboxes))

        label_bbox_map = {
            str(card["label"]): [float(value) for value in card["label_bbox_px"]]
            for card in rendered.card_traces
        }
        value_bbox_map = {
            str(card["label"]): [float(value) for value in card["value_bbox_px"]]
            for card in rendered.card_traces
        }
        card_bbox_map = {
            str(card["label"]): [float(value) for value in card["card_bbox_px"]]
            for card in rendered.card_traces
        }
        caption_bbox_map = {
            str(card["label"]): [float(value) for value in card["caption_bbox_px"]]
            for card in rendered.card_traces
        }
        section_title_bbox_map = {
            str(section): [float(value) for value in bbox]
            for section, bbox in rendered.section_title_bboxes.items()
        }

        trace_payload = {
            "scene_ir": {
                "scene_id": SCENE_ID,
                "scene_kind": "pages_infographic_metric_cards",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(query_id),
                    "target_labels": list(target_labels),
                    "target_values": list(target_values),
                    "target_groups": dict(target_groups),
                    "target_sections": list(target_sections),
                    "excluded_labels": list(excluded_labels),
                    "target_extrema": list(target_extrema),
                    "extrema_operation": str(extrema_operation),
                    "rank_direction": str(dataset.get("rank_direction", "")),
                    "rank_ordinal": str(dataset.get("rank_ordinal", "")),
                    "rank_position": int(dataset.get("rank_position", 0)),
                    "rank_scope": str(dataset.get("rank_scope", "")),
                    "ranked_candidates": [dict(item) for item in dataset.get("ranked_candidates", [])],
                    "filter_icon_kind": str(dataset.get("filter_icon_kind", "")),
                    "filter_icon_label": _icon_prompt_label(str(dataset.get("filter_icon_kind", ""))),
                    "comparison_icon_kind": str(dataset.get("comparison_icon_kind", "")),
                    "comparison_icon_label": _icon_prompt_label(str(dataset.get("comparison_icon_kind", ""))),
                    "filtered_section_totals": dict(dataset.get("filtered_section_totals", {})),
                    "target_value_text": str(dataset.get("target_value_text", "")),
                    "target_detail_text": str(dataset.get("target_detail_text", "")),
                    "annotation_targets": [dict(item) for item in annotation_targets],
                    "answer_value": answer_value_for_trace,
                    "answer_type": str(answer_type),
                    "arithmetic_expression": str(dataset["arithmetic_expression"]),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query_id),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "card_count": int(dataset["card_count"]),
                    "section_count": int(dataset["section_count"]),
                    "target_labels": list(target_labels),
                    "target_values": list(target_values),
                    "target_groups": dict(target_groups),
                    "target_sections": list(target_sections),
                    "excluded_labels": list(excluded_labels),
                    "target_extrema": list(target_extrema),
                    "extrema_operation": str(extrema_operation),
                    "rank_direction": str(dataset.get("rank_direction", "")),
                    "rank_ordinal": str(dataset.get("rank_ordinal", "")),
                    "rank_position": int(dataset.get("rank_position", 0)),
                    "rank_scope": str(dataset.get("rank_scope", "")),
                    "ranked_candidates": [dict(item) for item in dataset.get("ranked_candidates", [])],
                    "filter_icon_kind": str(dataset.get("filter_icon_kind", "")),
                    "filter_icon_label": _icon_prompt_label(str(dataset.get("filter_icon_kind", ""))),
                    "comparison_icon_kind": str(dataset.get("comparison_icon_kind", "")),
                    "comparison_icon_label": _icon_prompt_label(str(dataset.get("comparison_icon_kind", ""))),
                    "filtered_section_totals": dict(dataset.get("filtered_section_totals", {})),
                    "target_value_text": str(dataset.get("target_value_text", "")),
                    "target_detail_text": str(dataset.get("target_detail_text", "")),
                    "annotation_targets": [dict(item) for item in annotation_targets],
                    "target_answer": answer_value_for_trace,
                    "answer_type": str(answer_type),
                },
            },
            "render_spec": {
                "canvas_width": int(canvas_width),
                "canvas_height": int(canvas_height),
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "scene_variant": str(rendered.layout_jitter_meta.get("infographic_style", "card_wall")),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "layout_jitter": dict(rendered.layout_jitter_meta),
                "section_bboxes_px": dict(rendered.section_bboxes),
                "section_title_bboxes_px": dict(section_title_bbox_map),
                "text_style": {
                    "title_font_size_px": int(group_default(_RENDER_DEFAULTS, "title_font_size_px", 30)),
                    "label_font_size_px": int(group_default(_RENDER_DEFAULTS, "label_font_size_px", 18)),
                    "caption_font_size_px": int(group_default(_RENDER_DEFAULTS, "caption_font_size_px", 13)),
                },
                "page_text_resources": dict(dataset.get("page_text_resources", {})),
                "page_semantic_assets": page_semantic_asset_manifest_metadata(
                    semantic_role="metric_icon",
                    allowed_use="filter",
                ),
            },
            "render_map": {
                "image_id": "img0",
                "card_bboxes_px": dict(card_bbox_map),
                "label_bboxes_px": dict(label_bbox_map),
                "value_bboxes_px": dict(value_bbox_map),
                "caption_bboxes_px": dict(caption_bbox_map),
                "section_title_bboxes_px": dict(section_title_bbox_map),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "answer_value": answer_value_for_trace,
                "answer_type": str(answer_type),
                "arithmetic_expression": str(dataset["arithmetic_expression"]),
                "target_labels": list(target_labels),
                "target_values": list(target_values),
                "target_groups": dict(target_groups),
                "target_sections": list(target_sections),
                "excluded_labels": list(excluded_labels),
                "target_extrema": list(target_extrema),
                "extrema_operation": str(extrema_operation),
                "rank_direction": str(dataset.get("rank_direction", "")),
                "rank_ordinal": str(dataset.get("rank_ordinal", "")),
                "rank_position": int(dataset.get("rank_position", 0)),
                "rank_scope": str(dataset.get("rank_scope", "")),
                "ranked_candidates": [dict(item) for item in dataset.get("ranked_candidates", [])],
                "rank_direction_probabilities": dict(dataset.get("rank_direction_probabilities", {})),
                "rank_position_probabilities": dict(dataset.get("rank_position_probabilities", {})),
                "filter_icon_kind": str(dataset.get("filter_icon_kind", "")),
                "filter_icon_label": _icon_prompt_label(str(dataset.get("filter_icon_kind", ""))),
                "comparison_icon_kind": str(dataset.get("comparison_icon_kind", "")),
                "comparison_icon_label": _icon_prompt_label(str(dataset.get("comparison_icon_kind", ""))),
                "filtered_section_totals": {
                    str(section): int(total)
                    for section, total in dict(dataset.get("filtered_section_totals", {})).items()
                },
                "target_value_text": str(dataset.get("target_value_text", "")),
                "target_detail_text": str(dataset.get("target_detail_text", "")),
                "annotation_targets": [dict(item) for item in annotation_targets],
                "labels": [str(label) for label in dataset["labels"]],
                "values_by_label": {str(label): int(value) for label, value in dataset["values_by_label"].items()},
                "cards": [dict(card) for card in rendered.card_traces],
                "card_count": int(dataset["card_count"]),
                "card_count_range": list(dataset["card_count_range"]),
                "card_count_probabilities": dict(dataset["card_count_probabilities"]),
                "section_count": int(dataset["section_count"]),
                "section_count_range": list(dataset["section_count_range"]),
                "section_count_probabilities": dict(dataset["section_count_probabilities"]),
                "section_titles": [str(title) for title in dataset["section_titles"]],
                "section_card_counts": [int(value) for value in dataset["section_card_counts"]],
                "section_totals": {str(section): int(value) for section, value in dataset["section_totals"].items()},
                "target_operand_count": int(dataset["target_operand_count"]),
                "target_operand_count_range": list(dataset["target_operand_count_range"]),
                "target_operand_count_probabilities": dict(dataset["target_operand_count_probabilities"]),
                "query_id_probabilities": dict(query_id_probabilities),
                "question_format": "label_open" if answer_type == "string" else "numeric_open",
                "percent_mode": bool(dataset["percent_mode"]),
                "value_min": int(dataset["value_min"]),
                "value_max": int(dataset["value_max"]),
                "percent_value_min": int(dataset["percent_value_min"]),
                "percent_value_max": int(dataset["percent_value_max"]),
            },
            "witness_symbolic": {
                "type": "metric_card_keyed_set",
                "labels": list(target_labels),
                "annotation_keys": list(annotation_keyed_bboxes.keys()),
                "groups": dict(target_groups),
                "sections": list(target_sections),
                "excluded_labels": list(excluded_labels),
                "extrema": list(target_extrema),
                "extrema_operation": str(extrema_operation),
                "rank_direction": str(dataset.get("rank_direction", "")),
                "rank_ordinal": str(dataset.get("rank_ordinal", "")),
                "rank_position": int(dataset.get("rank_position", 0)),
                "rank_scope": str(dataset.get("rank_scope", "")),
                "ranked_candidates": [dict(item) for item in dataset.get("ranked_candidates", [])],
                "filter_icon_kind": str(dataset.get("filter_icon_kind", "")),
                "filter_icon_label": _icon_prompt_label(str(dataset.get("filter_icon_kind", ""))),
                "comparison_icon_kind": str(dataset.get("comparison_icon_kind", "")),
                "comparison_icon_label": _icon_prompt_label(str(dataset.get("comparison_icon_kind", ""))),
                "values": list(target_values),
                "expression": str(dataset["arithmetic_expression"]),
                "annotation_targets": [dict(item) for item in annotation_targets],
            },
            "projected_annotation": {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(annotation_keyed_bboxes),
                "pixel_keyed_bbox_map": dict(annotation_keyed_bboxes),
                "bbox_set": list(annotation_bboxes),
                "pixel_bbox_set": list(annotation_bboxes),
                "label_bbox_map": dict(label_bbox_map),
                "value_bbox_map": dict(value_bbox_map),
                "card_bbox_map": dict(card_bbox_map),
                "caption_bbox_map": dict(caption_bbox_map),
                "section_title_bbox_map": dict(section_title_bbox_map),
                "target_labels": list(target_labels),
                "annotation_keys": list(annotation_keyed_bboxes.keys()),
                "annotation_targets": [dict(item) for item in annotation_targets],
            },
        }

        reasoning_load = float(_REASONING_LOAD_BY_VARIANT[str(query_id)])
        if str(query_id) == "sum_named_metrics":
            reasoning_load = min(
                1.0,
                reasoning_load
                + (0.14 * normalize_int_with_bounds(int(dataset["target_operand_count"]), dataset["target_operand_count_range"])),
            )
        complexity = build_pages_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(dataset["card_count"]), dataset["card_count_range"]),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": normalize_int_with_bounds(int(dataset["section_count"]), dataset["section_count_range"]),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


def _scoped_infographic_params(
    params: Mapping[str, Any],
    *,
    allowed_query_ids: Sequence[str],
) -> Dict[str, Any]:
    """Restrict the shared infographic generator to one public task's query set."""

    allowed = tuple(str(value) for value in allowed_query_ids if str(value).strip())
    allowed_set = set(allowed)
    explicit_query = explicit_query_id_param(params)
    scoped = normalize_query_id_params(params)
    if explicit_query is not None and str(explicit_query) not in allowed_set:
        raise ValueError(f"unsupported query id for infographic task: {explicit_query}")
    scoped["_supported_query_ids"] = tuple(allowed)
    if explicit_query is None:
        scoped.pop("query_id_weights", None)
    return scoped


def _query_probabilities_from_output(output: TaskOutput, query_id: str) -> Dict[str, float]:
    payload = output.trace_payload if isinstance(output.trace_payload, Mapping) else {}
    execution = payload.get("execution_trace") if isinstance(payload, Mapping) else {}
    if isinstance(execution, Mapping) and isinstance(execution.get("query_id_probabilities"), Mapping):
        return {str(key): float(value) for key, value in execution["query_id_probabilities"].items()}
    return {str(query_id): 1.0}


class _PagesInfographicPublicTaskMixin:
    default_dataset_enabled = True
    allowed_query_ids: Sequence[str] = ()

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        scoped_params = _scoped_infographic_params(
            params,
            allowed_query_ids=tuple(self.allowed_query_ids),
        )
        output = super().generate(  # type: ignore[misc]
            int(instance_seed),
            params=scoped_params,
            max_attempts=int(max_attempts),
        )
        query_id = str(output.query_id)
        return rewrite_pages_public_task_output(
            output,
            task_id=str(self.task_id),
            query_id=str(query_id),
            scene_id=SCENE_ID,
            query_probabilities=_query_probabilities_from_output(output, query_id),
        )


@register_task
class PagesInfographicSumNamedMetricsValueTask(
    _PagesInfographicPublicTaskMixin,
    PagesInfographicMetricArithmeticValueTask,
):
    """Compute the sum of named infographic metric values."""

    task_id = "task_pages__infographic__sum_named_metrics_value"
    allowed_query_ids = ("sum_named_metrics",)


@register_task
class PagesInfographicSectionExtremaArithmeticValueTask(
    _PagesInfographicPublicTaskMixin,
    PagesInfographicMetricArithmeticValueTask,
):
    """Compute arithmetic using extrema-selected infographic metric values."""

    task_id = "task_pages__infographic__section_extrema_arithmetic_value"
    allowed_query_ids = ("section_extrema_arithmetic",)


@register_task
class PagesInfographicSectionTotalExtremaDifferenceValueTask(
    _PagesInfographicPublicTaskMixin,
    PagesInfographicMetricArithmeticValueTask,
):
    """Compute the difference between extrema-selected section totals."""

    task_id = "task_pages__infographic__section_total_extrema_difference_value"
    allowed_query_ids = ("section_total_extrema_difference",)


@register_task
class PagesInfographicSectionTotalExceptNamedValueTask(
    _PagesInfographicPublicTaskMixin,
    PagesInfographicMetricArithmeticValueTask,
):
    """Compute a section total after excluding named metric cards."""

    task_id = "task_pages__infographic__section_total_except_named_value"
    allowed_query_ids = ("section_total_except_named",)


@register_task
class PagesInfographicSectionIconTotalValueTask(
    _PagesInfographicPublicTaskMixin,
    PagesInfographicMetricArithmeticValueTask,
):
    """Compute a section total filtered by icon type."""

    task_id = "task_pages__infographic__section_icon_total_value"
    allowed_query_ids = FILTERED_METRIC_TOTAL_VARIANTS


@register_task
class PagesInfographicSectionIconTotalDifferenceValueTask(
    _PagesInfographicPublicTaskMixin,
    PagesInfographicMetricArithmeticValueTask,
):
    """Compute the difference between two icon-filtered section totals."""

    task_id = "task_pages__infographic__section_icon_total_difference_value"
    allowed_query_ids = COLUMN_PROFILE_COMPARISON_VARIANTS


@register_task
class PagesInfographicSectionRankedTotalLabelTask(
    _PagesInfographicPublicTaskMixin,
    PagesInfographicMetricArithmeticValueTask,
):
    """Identify a section by rank of its total metric value."""

    task_id = "task_pages__infographic__section_ranked_total_label"
    allowed_query_ids = SECTION_RANKED_TOTAL_VARIANTS


@register_task
class PagesInfographicMetricRankedItemLabelTask(
    _PagesInfographicPublicTaskMixin,
    PagesInfographicMetricArithmeticValueTask,
):
    """Identify a metric card by rank of its printed value."""

    task_id = "task_pages__infographic__metric_ranked_item_label"
    allowed_query_ids = METRIC_RANKED_ITEM_VARIANTS


@register_task
class PagesInfographicSectionIconExtremumLabelTask(
    _PagesInfographicPublicTaskMixin,
    PagesInfographicMetricArithmeticValueTask,
):
    """Identify a section by an icon-filtered aggregate extremum."""

    task_id = "task_pages__infographic__section_icon_extremum_label"
    allowed_query_ids = FILTERED_SECTION_EXTREMUM_VARIANTS


@register_task
class PagesInfographicDetailForNamedItemTask(
    _PagesInfographicPublicTaskMixin,
    PagesInfographicMetricArithmeticValueTask,
):
    """Look up the detail text for one named infographic item."""

    task_id = "task_pages__infographic__detail_for_named_item"
    allowed_query_ids = ("detail_for_named_item",)


@register_task
class PagesInfographicItemForNamedValueTask(
    _PagesInfographicPublicTaskMixin,
    PagesInfographicMetricArithmeticValueTask,
):
    """Look up the item label associated with a named infographic value."""

    task_id = "task_pages__infographic__item_for_named_value"
    allowed_query_ids = ("item_for_named_value",)


@register_task
class PagesInfographicValueForNamedItemTask(
    _PagesInfographicPublicTaskMixin,
    PagesInfographicMetricArithmeticValueTask,
):
    """Look up the visible value for one named infographic item."""

    task_id = "task_pages__infographic__value_for_named_item"
    allowed_query_ids = ("value_for_named_item",)
