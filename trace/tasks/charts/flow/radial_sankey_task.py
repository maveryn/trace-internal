"""Base radial Sankey chart task implementation."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...shared.config_defaults import required_group_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import temporary_default_font_family
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
)
from ..shared.sampling_defaults import support_sampling_params_for_uniform_query_cycle
from ..shared.visual_defaults import chart_font_asset_metadata, sample_chart_font_family
from .radial_sankey_common import (
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    SCENE_ID,
    SUPPORTED_QUERY_IDS,
    TASK_ID,
    TRANSFER_TOTAL_QUERY_IDS,
    _COMPLEXITY_WEIGHTS,
    _GEN_DEFAULTS,
    _PROMPT_DEFAULTS,
    _REASONING_LOAD_BY_VARIANT,
    _SCENE_VARIANT_LOADS,
    _resolve_query_id,
    _resolve_render_params,
    _resolve_scene_variant,
)
from .radial_sankey_rendering import _render_radial_sankey
from .radial_sankey_sampling import _construct_dataset


def _json_examples(query_id: str, *, prompt_defaults: Mapping[str, Any]) -> Tuple[str, str]:
    return (
        str(prompt_defaults[f"json_example_{str(query_id)}"]),
        str(prompt_defaults[f"json_example_answer_only_{str(query_id)}"]),
    )


class ChartsFlowRadialSankeyTask:
    """Answer endpoint-selection and transfer-total questions over a radial Sankey chart."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "flow"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        support_params = support_sampling_params_for_uniform_query_cycle(
            params,
            gen_defaults=_GEN_DEFAULTS,
            query_id_probabilities=query_id_probabilities,
            supported_query_ids=SUPPORTED_QUERY_IDS,
        )
        dataset = _construct_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            params=support_params,
            instance_seed=int(instance_seed),
        )
        render_style_params = {**dict(params), "_render_style_seed": int(instance_seed)}
        render_params = _resolve_render_params(render_style_params)
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        chart_font_family = sample_chart_font_family(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.chart_font",
            params=params,
        )
        with temporary_default_font_family(str(chart_font_family)):
            rendered_scene = _render_radial_sankey(
                background,
                scene_title=str(dataset["scene_title"]),
                sources=list(dataset["sources"]),
                targets=list(dataset["targets"]),
                links=list(dataset["links"]),
                render_params=render_params,
                value_min=int(dataset["value_min"]),
                value_max=int(dataset["value_max"]),
                instance_seed=int(instance_seed),
            )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "radial_scene_key",
                "radial_task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_radial_chord_sankey",
                "radial_answer_hint_value",
                "radial_answer_hint_label",
                "radial_annotation_hint",
                "json_example_source_to_targets_total",
                "json_example_sources_to_target_total",
                "json_example_largest_target_for_source",
                "json_example_largest_source_for_target",
                "json_example_answer_only_source_to_targets_total",
                "json_example_answer_only_sources_to_target_total",
                "json_example_answer_only_largest_target_for_source",
                "json_example_answer_only_largest_source_for_target",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        query = dict(dataset["query"])
        json_example, json_example_answer_only = _json_examples(str(query_id), prompt_defaults=prompt_defaults)
        answer_hint = (
            str(prompt_defaults["radial_answer_hint_value"])
            if str(dataset["answer_type"]) == "integer"
            else str(prompt_defaults["radial_answer_hint_label"])
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["radial_scene_key"]),
            task_key=str(prompt_defaults["radial_task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_radial_chord_sankey"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["radial_annotation_hint"]),
                "answer_hint": str(answer_hint),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "source_label": str(query.get("source_label", "")),
                "target_label": str(query.get("target_label", "")),
                "source_labels": str(query.get("source_labels_joined", "")),
                "target_labels": str(query.get("target_labels_joined", "")),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        annotation_link_ids = [str(link_id) for link_id in query["annotation_link_ids"]]
        annotation_node_ids = [str(node_id) for node_id in query.get("annotation_node_ids", [])]
        annotation_bboxes = [
            list(rendered_scene.link_label_bbox_map[str(link_id)])
            for link_id in annotation_link_ids
        ] + [
            list(rendered_scene.node_bbox_map[str(node_id)])
            for node_id in annotation_node_ids
        ]
        projected_annotation = {
            "type": "bbox_set",
            "bbox_set": list(annotation_bboxes),
            "pixel_bbox_set": list(annotation_bboxes),
            "link_ids": list(annotation_link_ids),
            "node_ids": list(annotation_node_ids),
            "link_label_bbox_map": {
                str(link_id): list(rendered_scene.link_label_bbox_map[str(link_id)])
                for link_id in annotation_link_ids
            },
            "node_bbox_map": {
                str(node_id): list(rendered_scene.node_bbox_map[str(node_id)])
                for node_id in annotation_node_ids
            },
        }

        if str(dataset["answer_type"]) == "integer":
            answer_gt = TypedValue(type="integer", value=int(dataset["answer_value"]))
        else:
            answer_gt = TypedValue(type="string", value=str(dataset["answer_value"]))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))

        annotation_scan = normalize_int_with_bounds(len(annotation_bboxes), [2, 7])
        link_scan = normalize_int_with_bounds(int(dataset["link_count"]), list(dataset["link_count_bounds"]))
        node_bounds = [
            int(dataset["source_count_bounds"][0]) + int(dataset["target_count_bounds"][0]),
            int(dataset["source_count_bounds"][1]) + int(dataset["target_count_bounds"][1]),
        ]
        node_scan = normalize_int_with_bounds(int(dataset["source_count"]) + int(dataset["target_count"]), node_bounds)
        visual_scan = clamp_unit_interval((0.65 * float(link_scan)) + (0.35 * float(node_scan)))
        reasoning_load = clamp_unit_interval(float(_REASONING_LOAD_BY_VARIANT[str(query_id)]) + (0.10 * float(annotation_scan)))
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": float(visual_scan),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(scene_variant)]),
            },
        )

        query_params = {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "query_id_probabilities": dict(query_id_probabilities),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "source_count": int(dataset["source_count"]),
            "target_count": int(dataset["target_count"]),
            "link_count": int(dataset["link_count"]),
            "max_links_per_node_side": int(dataset["max_links_per_node_side"]),
            "link_side_counts": dict(dataset["link_side_counts"]),
            "source_label": str(query.get("source_label", "")),
            "target_label": str(query.get("target_label", "")),
            "source_labels": [str(value) for value in query.get("source_labels", [])],
            "target_labels": [str(value) for value in query.get("target_labels", [])],
            "source_labels_joined": str(query.get("source_labels_joined", "")),
            "target_labels_joined": str(query.get("target_labels_joined", "")),
            "group_size": int(query.get("group_size", 0)),
            "query_link_ids": [str(link_id) for link_id in query["query_link_ids"]],
            "comparison_link_ids": [str(link_id) for link_id in query.get("comparison_link_ids", [])],
        }

        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_radial_sankey",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "answer_value": dataset["answer_value"],
                    "query_link_ids": [str(link_id) for link_id in query["query_link_ids"]],
                    "annotation_link_ids": list(annotation_link_ids),
                    "annotation_node_ids": list(annotation_node_ids),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "scene_variant": str(scene_variant),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "source_count": int(dataset["source_count"]),
                "target_count": int(dataset["target_count"]),
                "link_count": int(dataset["link_count"]),
                "max_links_per_node_side": int(dataset["max_links_per_node_side"]),
                "value_min": int(dataset["value_min"]),
                "value_max": int(dataset["value_max"]),
                "min_flow_width_px": int(render_params.min_flow_width_px),
                "max_flow_width_px": int(render_params.max_flow_width_px),
                "flow_alpha": int(render_params.flow_alpha),
                "radial_color_scheme": str(render_params.color_scheme_name),
                "flow_palette_rgb": [list(color) for color in render_params.flow_palette_rgb],
                "source_node_fill_rgb": list(render_params.source_node_fill_rgb),
                "target_node_fill_rgb": list(render_params.target_node_fill_rgb),
                "ring_line_rgb": list(render_params.ring_line_rgb),
                "layout_jitter": dict(render_params.layout_jitter_meta),
                "background_style": dict(background_meta),
                "font_assets": chart_font_asset_metadata(str(chart_font_family)),
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "panel_bbox_px": list(rendered_scene.panel_bbox_px),
                "title_bbox_px": list(rendered_scene.title_bbox_px),
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "node_bboxes_px": dict(rendered_scene.node_bbox_map),
                "node_label_bboxes_px": dict(rendered_scene.node_label_bbox_map),
                "link_bboxes_px": dict(rendered_scene.link_bbox_map),
                "link_label_bboxes_px": dict(rendered_scene.link_label_bbox_map),
                "link_centers_px": dict(rendered_scene.link_center_map),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "query_id_probabilities": dict(query_id_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "question_format": "radial_sankey_transfer_total_value"
                if str(query_id) in TRANSFER_TOTAL_QUERY_IDS
                else "radial_sankey_dominant_endpoint_label",
                "scene_title": str(dataset["scene_title"]),
                "sources": [dict(node) for node in dataset["sources"]],
                "targets": [dict(node) for node in dataset["targets"]],
                "links": [dict(link) for link in dataset["links"]],
                "links_by_id": {str(key): dict(value) for key, value in dict(dataset["links_by_id"]).items()},
                "source_count": int(dataset["source_count"]),
                "target_count": int(dataset["target_count"]),
                "link_count": int(dataset["link_count"]),
                "max_links_per_node_side": int(dataset["max_links_per_node_side"]),
                "link_side_counts": dict(dataset["link_side_counts"]),
                "value_min": int(dataset["value_min"]),
                "value_max": int(dataset["value_max"]),
                "answer_value": dataset["answer_value"],
                "answer_type": str(dataset["answer_type"]),
                "query_link_ids": [str(link_id) for link_id in query["query_link_ids"]],
                "comparison_link_ids": [str(link_id) for link_id in query.get("comparison_link_ids", [])],
                "annotation_link_ids": list(annotation_link_ids),
                "annotation_node_ids": list(annotation_node_ids),
                "query_link_details": [dict(link) for link in query["link_details"]],
                "source_label": str(query.get("source_label", "")),
                "target_label": str(query.get("target_label", "")),
                "source_labels": [str(value) for value in query.get("source_labels", [])],
                "target_labels": [str(value) for value in query.get("target_labels", [])],
                "group_size": int(query.get("group_size", 0)),
                "expression": str(query["expression"]),
                "annotation_semantics": str(query_id),
            },
            "witness_symbolic": {
                "type": "radial_sankey_transfer_total_value_witness"
                if str(query_id) in TRANSFER_TOTAL_QUERY_IDS
                else "radial_sankey_dominant_endpoint_label_witness",
                "query_link_ids": [str(link_id) for link_id in query["query_link_ids"]],
                "annotation_link_ids": list(annotation_link_ids),
                "annotation_node_ids": list(annotation_node_ids),
                "answer_value": dataset["answer_value"],
                "expression": str(query["expression"]),
            },
            "projected_annotation": dict(projected_annotation),
            "background": background_meta,
            "post_image_noise": dict(post_noise_meta),
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
        )
