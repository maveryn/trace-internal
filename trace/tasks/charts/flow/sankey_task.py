"""Base Sankey flow chart task implementation."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...shared.config_defaults import required_group_defaults
from ...shared.font_assets import font_asset_version
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import temporary_default_font_family
from ..shared.complexity import build_chart_complexity, clamp_unit_interval, normalize_int_with_bounds
from ..shared.sampling_defaults import support_sampling_params_for_uniform_query_cycle
from .sankey_common import (
    NODE_SIDE_TOTAL_QUERY_IDS,
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    SUPPORTED_QUERY_IDS,
    TASK_ID,
    _COMPLEXITY_WEIGHTS,
    _GEN_DEFAULTS,
    _PROMPT_DEFAULTS,
    _REASONING_LOAD_BY_VARIANT,
    _SCENE_VARIANT_LOADS,
    _resolve_render_params,
    _sample_chart_font_family,
)
from .sankey_rendering import _render_sankey
from .sankey_sampling import _construct_dataset, _resolve_query_id, _resolve_scene_variant

def _json_examples(query_id: str, *, prompt_defaults: Mapping[str, Any]) -> Tuple[str, str]:
    return (
        str(prompt_defaults[f"json_example_{str(query_id)}"]),
        str(prompt_defaults[f"json_example_answer_only_{str(query_id)}"]),
    )


class ChartsFlowSankeyPathValueTask:
    """Answer path arithmetic questions over a weighted Sankey-style chart."""

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
        chart_font_family = _sample_chart_font_family(int(instance_seed), params)
        with temporary_default_font_family(str(chart_font_family)):
            rendered_scene = _render_sankey(
                background,
                scene_title=str(dataset["scene_title"]),
                sources=list(dataset["sources"]),
                middles=list(dataset["middles"]),
                targets=list(dataset["targets"]),
                paths=list(dataset["paths"]),
                render_params=render_params,
                value_min=int(dataset["value_min"]),
                value_max=int(dataset["value_max"]),
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
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_three_column_sankey",
                "answer_hint",
                "annotation_hint",
                "json_example_source_to_target_total_flow",
                "json_example_path_bottleneck_value",
                "json_example_path_flow_difference",
                "json_example_source_outgoing_total_flow",
                "json_example_target_incoming_total_flow",
                "json_example_answer_only_source_to_target_total_flow",
                "json_example_answer_only_path_bottleneck_value",
                "json_example_answer_only_path_flow_difference",
                "json_example_answer_only_source_outgoing_total_flow",
                "json_example_answer_only_target_incoming_total_flow",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _json_examples(str(query_id), prompt_defaults=prompt_defaults)
        query = dict(dataset["query"])
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_three_column_sankey"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "source_label": str(query.get("source_label", "")),
                "middle_label": str(query.get("middle_label", "")),
                "target_label": str(query.get("target_label", "")),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        annotation_segment_ids = [str(segment_id) for segment_id in query["annotation_segment_ids"]]
        answer_gt = TypedValue(type="integer", value=int(dataset["answer_value"]))
        annotation_bboxes = [list(rendered_scene.segment_label_bbox_map[str(segment_id)]) for segment_id in annotation_segment_ids]
        projected_annotation = {
            "type": "bbox_set",
            "bbox_set": list(annotation_bboxes),
            "pixel_bbox_set": list(annotation_bboxes),
            "segment_ids": list(annotation_segment_ids),
            "segment_label_bbox_map": {
                str(segment_id): list(rendered_scene.segment_label_bbox_map[str(segment_id)])
                for segment_id in annotation_segment_ids
            },
            "segment_bbox_map": {
                str(segment_id): list(rendered_scene.segment_bbox_map[str(segment_id)])
                for segment_id in annotation_segment_ids
            },
        }
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))

        annotation_scan = normalize_int_with_bounds(len(annotation_segment_ids), [2, 8])
        path_scan = normalize_int_with_bounds(int(dataset["path_count"]), list(dataset["path_count_bounds"]))
        node_bounds = [
            int(dataset["source_count_bounds"][0]) + int(dataset["middle_count_bounds"][0]) + int(dataset["target_count_bounds"][0]),
            int(dataset["source_count_bounds"][1]) + int(dataset["middle_count_bounds"][1]) + int(dataset["target_count_bounds"][1]),
        ]
        node_scan = normalize_int_with_bounds(
            int(dataset["source_count"]) + int(dataset["middle_count"]) + int(dataset["target_count"]),
            node_bounds,
        )
        visual_scan = clamp_unit_interval((0.70 * float(path_scan)) + (0.30 * float(node_scan)))
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BY_VARIANT[str(query_id)])
            + (0.10 * float(annotation_scan))
        )
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
            "middle_count": int(dataset["middle_count"]),
            "target_count": int(dataset["target_count"]),
            "path_count": int(dataset["path_count"]),
            "max_paths_per_node_side": int(dataset["max_paths_per_node_side"]),
            "path_side_counts": dict(dataset["path_side_counts"]),
            "source_label": str(query.get("source_label", "")),
            "middle_label": str(query.get("middle_label", "")),
            "target_label": str(query.get("target_label", "")),
            "route_count": int(query.get("route_count", 1)),
            "query_path_ids": [str(path_id) for path_id in query["query_path_ids"]],
            "incoming_total": int(query["incoming_total"]) if "incoming_total" in query else None,
            "outgoing_total": int(query["outgoing_total"]) if "outgoing_total" in query else None,
            "node_side": str(query.get("node_side", "")),
            "connected_count": int(query["connected_count"]) if "connected_count" in query else None,
            "node_side_total": int(query["node_side_total"]) if "node_side_total" in query else None,
        }

        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_sankey",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                "answer_value": int(dataset["answer_value"]),
                "query_path_ids": [str(path_id) for path_id in query["query_path_ids"]],
                "annotation_segment_ids": list(annotation_segment_ids),
                "incoming_total": int(query["incoming_total"]) if "incoming_total" in query else None,
                "outgoing_total": int(query["outgoing_total"]) if "outgoing_total" in query else None,
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
                "middle_count": int(dataset["middle_count"]),
                "target_count": int(dataset["target_count"]),
                "path_count": int(dataset["path_count"]),
                "max_paths_per_node_side": int(dataset["max_paths_per_node_side"]),
                "value_min": int(dataset["value_min"]),
                "value_max": int(dataset["value_max"]),
                "min_flow_width_px": int(render_params.min_flow_width_px),
                "max_flow_width_px": int(render_params.max_flow_width_px),
                "layout_jitter": dict(render_params.layout_jitter_meta),
                "background_style": dict(background_meta),
                "font_asset_version": font_asset_version(),
                "chart_font_family": str(chart_font_family),
                "font_assets": {
                    "font_asset_version": font_asset_version(),
                    "chart_font_family": str(chart_font_family),
                },
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "panel_bbox_px": list(rendered_scene.panel_bbox_px),
                "title_bbox_px": list(rendered_scene.title_bbox_px),
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "node_bboxes_px": dict(rendered_scene.node_bbox_map),
                "node_label_bboxes_px": dict(rendered_scene.node_label_bbox_map),
                "segment_bboxes_px": dict(rendered_scene.segment_bbox_map),
                "segment_label_bboxes_px": dict(rendered_scene.segment_label_bbox_map),
                "segment_centers_px": dict(rendered_scene.segment_center_map),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "query_id_probabilities": dict(query_id_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "question_format": "sankey_node_side_total_value"
                if str(query_id) in NODE_SIDE_TOTAL_QUERY_IDS
                else "sankey_path_value",
                "scene_title": str(dataset["scene_title"]),
                "sources": [dict(node) for node in dataset["sources"]],
                "middles": [dict(node) for node in dataset["middles"]],
                "targets": [dict(node) for node in dataset["targets"]],
                "paths": [dict(path) for path in dataset["paths"]],
                "paths_by_id": {str(key): dict(value) for key, value in dict(dataset["paths_by_id"]).items()},
                "source_count": int(dataset["source_count"]),
                "middle_count": int(dataset["middle_count"]),
                "target_count": int(dataset["target_count"]),
                "path_count": int(dataset["path_count"]),
                "max_paths_per_node_side": int(dataset["max_paths_per_node_side"]),
                "path_side_counts": dict(dataset["path_side_counts"]),
                "value_min": int(dataset["value_min"]),
                "value_max": int(dataset["value_max"]),
                "answer_value": int(dataset["answer_value"]),
                "answer_type": "integer",
                "query_path_ids": [str(path_id) for path_id in query["query_path_ids"]],
                "annotation_segment_ids": list(annotation_segment_ids),
                "query_path_details": [dict(path) for path in query["path_details"]],
                "incoming_total": int(query["incoming_total"]) if "incoming_total" in query else None,
                "outgoing_total": int(query["outgoing_total"]) if "outgoing_total" in query else None,
                "node_side": str(query.get("node_side", "")),
                "connected_count": int(query["connected_count"]) if "connected_count" in query else None,
                "node_side_total": int(query["node_side_total"]) if "node_side_total" in query else None,
                "expression": str(query["expression"]),
                "annotation_semantics": str(query_id),
            },
            "witness_symbolic": {
                "type": "sankey_node_side_total_value_witness"
                if str(query_id) in NODE_SIDE_TOTAL_QUERY_IDS
                else "sankey_path_value_witness",
                "query_path_ids": [str(path_id) for path_id in query["query_path_ids"]],
                "annotation_segment_ids": list(annotation_segment_ids),
                "answer_value": int(dataset["answer_value"]),
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
            query_id=str(query_id),
        )
