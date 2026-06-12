"""Puzzle topology task that counts open ropes, closed loops, or knotted components."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Mapping

from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.common import projected_puzzle_bbox_annotation
from trace.tasks.shared.fixed_query import rewrite_fixed_puzzle_query_output
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.string_topology_common import (
    PuzzleStringTopologyDefaults,
    SUPPORTED_PUZZLE_STRING_TOPOLOGY_QUERY_IDS,
    build_string_topology_dataset_for_variant,
    resolve_string_topology_render_params,
    resolve_string_topology_scene_variant,
    resolve_string_topology_query_id,
)
from ..shared.string_topology_scene import render_puzzle_string_topology_scene
from ..shared.visual_defaults import load_puzzle_noise_defaults


TASK_ID = "puzzles_topology_string_component_internal"
STRING_COMPONENT_COUNT_TASK_ID = "task_puzzles__string_topology__string_component_count"
_REASONING_LOAD_BASE_BY_VARIANT = {
    "open_rope_count": 0.36,
    "closed_loop_count": 0.40,
    "knotted_component_count": 0.48,
}
_SCENE_LOAD_BY_VARIANT = {
    "string_strip": 0.14,
    "string_card": 0.20,
    "string_outline": 0.17,
}

_DEFAULTS = PuzzleStringTopologyDefaults()
_TASK_GROUP_DEFAULTS = get_scene_defaults("puzzles", "topology")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(scene_id="topology", apply_prob=0.0)


def _advance_sampling(params: Mapping[str, Any], axis_size: int) -> Mapping[str, Any]:
    """Return params unchanged for axis-selection call sites."""

    _ = int(axis_size)
    return params


class _PuzzlesTopologyStringComponentBaseTask:
    """Count string-component features from a rope topology diagram."""

    task_id = TASK_ID
    domain = "puzzles"
    scene_id = "topology"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = resolve_string_topology_query_id(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        scene_params: Mapping[str, Any] = params
        if "query_id" not in params:
            scene_params = _advance_sampling(params, len(SUPPORTED_PUZZLE_STRING_TOPOLOGY_QUERY_IDS))
        scene_variant, scene_variant_probabilities = resolve_string_topology_scene_variant(
            scene_params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        dataset_params: Mapping[str, Any] = scene_params
        if "scene_variant" not in params:
            dataset_params = _advance_sampling(scene_params, len(_SCENE_LOAD_BY_VARIANT))
        dataset = build_string_topology_dataset_for_variant(
            query_id=str(query_id),
            params=dataset_params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
        )
        render_params = resolve_string_topology_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        scene_style, scene_style_meta = resolve_puzzle_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.string_topology_background",
        )
        render_params = replace(
            render_params,
            panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            card_fill_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
            border_color_rgb=tuple(int(value) for value in scene_style.panel_border_rgb),
            rope_shadow_rgb=tuple(int(value) for value in scene_style.notebook_line_rgb),
            gap_fill_rgb=tuple(int(value) for value in scene_style.background_rgb),
        )
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered_scene = render_puzzle_string_topology_scene(
            background,
            scene_variant=str(scene_variant),
            component_specs=list(dataset["component_specs"]),
            visual_group_specs=list(dataset["visual_group_specs"]),
            crossing_specs=list(dataset["crossing_specs"]),
            render_params=render_params,
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
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "object_description_string_strip",
                "object_description_string_card",
                "object_description_string_outline",
                "annotation_hint_open_rope_count",
                "annotation_hint_closed_loop_count",
                "annotation_hint_knotted_component_count",
                "json_example_open_rope_count",
                "json_example_closed_loop_count",
                "json_example_knotted_component_count",
                "json_example_answer_only_open_rope_count",
                "json_example_answer_only_closed_loop_count",
                "json_example_answer_only_knotted_component_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        annotation_hint = str(prompt_defaults[f"annotation_hint_{str(query_id)}"])
        json_example = str(prompt_defaults[f"json_example_{str(query_id)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(query_id)}"])

        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            scene_id=self.scene_id,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(annotation_hint),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        supporting_item_ids = [str(value) for value in dataset["supporting_item_ids"]]
        annotation_source = rendered_scene.component_bbox_map
        annotation_projection = projected_puzzle_bbox_annotation(annotation_source, list(supporting_item_ids))
        annotation_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in annotation_projection["bbox_set"]
        ]
        answer_value = int(dataset["answer_value"])
        if len(annotation_bboxes) != int(answer_value):
            raise ValueError("string topology annotation projection does not match answer count")
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))

        visual_scan = float(normalize_int_with_bounds(int(dataset["visual_group_count"]), list(dataset["visual_group_count_range"])))
        answer_support = [int(value) for value in dataset["target_answer_support"]]
        answer_bounds = [min(answer_support), max(answer_support)]
        answer_load = float(normalize_int_with_bounds(int(answer_value), answer_bounds)) if len(set(answer_support)) > 1 else 0.0
        reasoning_load = min(1.0, float(_REASONING_LOAD_BASE_BY_VARIANT[str(query_id)]) + (0.18 * answer_load))

        annotation_source_name = "component_bboxes_px"
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"puzzle_topology_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "answer_value": int(answer_value),
                    "supporting_item_ids": list(supporting_item_ids),
                    "topology_rule": str(dataset["topology_rule"]),
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
                    "scene_variant": str(scene_variant),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "visual_group_count": int(dataset["visual_group_count"]),
                    "component_count": int(dataset["component_count"]),
                    "object_count": int(dataset["object_count"]),
                    "object_count_probabilities": dict(dataset["object_count_probabilities"]),
                    "target_count": int(dataset["target_count"]),
                    "target_answer": int(dataset["target_answer"]),
                    "target_count_probabilities": dict(dataset["target_count_probabilities"]),
                    "distractor_count": int(dataset["distractor_count"]),
                    "distractor_count_probabilities": dict(dataset["distractor_count_probabilities"]),
                    "open_rope_count": int(dataset["open_rope_count"]),
                    "closed_loop_count": int(dataset["closed_loop_count"]),
                    "knotted_component_count": int(dataset["knotted_component_count"]),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "scene_style": dict(scene_style_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "group_min_gap_px": int(render_params.group_min_gap_px),
                "layout": "random_open_canvas",
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "visual_group_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.visual_group_bbox_map.items()
                },
                "component_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.component_bbox_map.items()
                },
                "crossing_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.crossing_bbox_map.items()
                },
                "annotation_source": str(annotation_source_name),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "question_format": str(dataset["question_format"]),
                "view_family": str(dataset["view_family"]),
                "topology_rule": str(dataset["topology_rule"]),
                "component_specs": [dict(component) for component in dataset["component_specs"]],
                "visual_group_specs": [dict(group) for group in dataset["visual_group_specs"]],
                "crossing_specs": [dict(crossing) for crossing in dataset["crossing_specs"]],
                "component_count": int(dataset["component_count"]),
                "component_count_range": list(dataset["component_count_range"]),
                "visual_group_count": int(dataset["visual_group_count"]),
                "visual_group_count_range": list(dataset["visual_group_count_range"]),
                "object_count": int(dataset["object_count"]),
                "object_count_range": list(dataset["object_count_range"]),
                "object_count_probabilities": dict(dataset["object_count_probabilities"]),
                "target_count": int(dataset["target_count"]),
                "target_answer": int(dataset["target_answer"]),
                "target_count_range": list(dataset["target_count_range"]),
                "target_count_probabilities": dict(dataset["target_count_probabilities"]),
                "distractor_count": int(dataset["distractor_count"]),
                "distractor_count_range": list(dataset["distractor_count_range"]),
                "distractor_count_probabilities": dict(dataset["distractor_count_probabilities"]),
                "open_rope_count": int(dataset["open_rope_count"]),
                "open_rope_count_range": list(dataset["open_rope_count_range"]),
                "closed_loop_count": int(dataset["closed_loop_count"]),
                "closed_loop_count_range": list(dataset["closed_loop_count_range"]),
                "knotted_component_count": int(dataset["knotted_component_count"]),
                "knotted_component_count_range": list(dataset["knotted_component_count_range"]),
                "target_answer_support": [int(value) for value in dataset["target_answer_support"]],
                "target_answer_probabilities": dict(dataset["target_answer_probabilities"]),
                "answer_value": int(answer_value),
                "supporting_item_ids": list(supporting_item_ids),
                "supporting_annotation_source": str(annotation_source_name),
                "query_id_probabilities": dict(query_id_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "solver_trace": dict(dataset["solver_trace"]),
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(annotation_bboxes),
            },
            "projected_annotation": dict(annotation_projection),
            "answer_gt": answer_gt.to_dict(),
            "annotation_gt": annotation_gt.to_dict(),
        }

        component_specs = [dict(component) for component in dataset["component_specs"]]
        if str(query_id) == "open_rope_count":
            expected = sum(1 for component in component_specs if bool(component.get("open_ended")))
        elif str(query_id) == "closed_loop_count":
            expected = sum(1 for component in component_specs if bool(component["closed"]))
        else:
            expected = sum(1 for component in component_specs if int(component.get("knot_count", 0)) > 0)
        if int(expected) != int(answer_value):
            raise ValueError("string topology answer drifted from component metadata")

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class PuzzlesTopologyStringComponentCountTask(_PuzzlesTopologyStringComponentBaseTask):
    """Count one sampled string-component predicate in a string-topology diagram."""

    task_id = STRING_COMPONENT_COUNT_TASK_ID

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        effective_params: Dict[str, Any] = dict(params)
        if effective_params.get("query_id") is None:
            for key in ("query_id", "query_variant"):
                if effective_params.get(key) is not None:
                    effective_params["query_id"] = str(effective_params[key])
                    break
        output = super().generate(
            int(instance_seed),
            params=effective_params,
            max_attempts=int(max_attempts),
        )
        return rewrite_fixed_puzzle_query_output(
            output,
            query_id=str(output.query_id),
            scene_id="string_topology",
        )


__all__ = [
    "PuzzlesTopologyStringComponentCountTask",
]
