"""Puzzle topology task that counts open ropes, closed loops, or knotted components."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Mapping

from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.puzzles.shared.common import projected_puzzle_bbox_annotation
from trace.tasks.puzzles.shared.scene_style import (
    make_puzzle_scene_background,
    resolve_puzzle_scene_style,
)
from trace.tasks.puzzles.shared.visual_defaults import load_puzzle_noise_defaults
from trace.tasks.shared.config_defaults import (
    load_scene_generation_rendering_prompt_defaults,
    required_group_defaults,
)
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)

from .shared.rendering import render_puzzle_string_topology_scene
from .shared.sampling import (
    PuzzleStringTopologyDefaults,
    build_string_topology_dataset_for_variant,
    resolve_string_topology_render_params,
    resolve_string_topology_scene_variant,
)


DOMAIN = "puzzles"
SCENE_ID = "string_topology"
TASK_ID = "task_puzzles__string_topology__string_component_count"
SUPPORTED_QUERY_IDS = (
    "open_rope_count",
    "closed_loop_count",
    "knotted_component_count",
)
_REASONING_LOAD_BASE_BY_VARIANT = {
    "open_rope_count": 0.36,
    "closed_loop_count": 0.40,
    "knotted_component_count": 0.48,
}
_QUERY_CONSTRUCTION = {
    "open_rope_count": {
        "feature_key": "open_strings",
        "target_component_type": "open_string",
        "target_closed": False,
        "target_knotted": False,
        "target_knot_count": 0,
        "filler_cycle": ("closed_ring", "knotted_loop"),
    },
    "closed_loop_count": {
        "feature_key": "closed_strings",
        "target_component_type": "closed_ring",
        "target_closed": True,
        "target_knotted": False,
        "target_knot_count": 0,
        "filler_cycle": ("open_string", "open_string"),
    },
    "knotted_component_count": {
        "feature_key": "knotted_strings",
        "target_component_type": "knotted_loop",
        "target_closed": True,
        "target_knotted": True,
        "target_knot_count": 1,
        "filler_cycle": ("open_string", "closed_ring", "open_string"),
    },
}
_DEFAULTS = PuzzleStringTopologyDefaults()
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = (
    load_scene_generation_rendering_prompt_defaults(DOMAIN, SCENE_ID, task_id=TASK_ID)
)
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(
    scene_id=SCENE_ID,
    apply_prob=0.0,
)


def _normalize_int_with_bounds(value: int, bounds: list[int] | tuple[int, int]) -> float:
    """Normalize an integer against inclusive bounds for trace difficulty hints."""

    if len(bounds) < 2:
        return 0.0
    low = int(bounds[0])
    high = int(bounds[1])
    if high <= low:
        return 0.0
    return max(0.0, min(1.0, (float(value) - float(low)) / (float(high) - float(low))))


def _supporting_component_ids(
    query_id: str,
    components: list[Mapping[str, Any]],
) -> list[str]:
    """Return ordered component ids that satisfy one task-owned query predicate."""

    if str(query_id) == "open_rope_count":
        return [
            str(component["component_id"])
            for component in components
            if bool(component.get("open_ended", not bool(component.get("closed"))))
        ]
    if str(query_id) == "closed_loop_count":
        return [
            str(component["component_id"])
            for component in components
            if bool(component["closed"])
        ]
    if str(query_id) == "knotted_component_count":
        return [
            str(component["component_id"])
            for component in components
            if int(component.get("knot_count", 0)) > 0
        ]
    raise ValueError(f"unsupported string topology query_id: {query_id}")


@register_task
class PuzzlesStringTopologyComponentCountTask:
    """Count string-component features from a rope topology diagram."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one component-count puzzle and bind bbox-set annotation."""

        query_id, query_id_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SUPPORTED_QUERY_IDS[0],
            task_id=self.task_id,
            namespace=f"{self.task_id}.query_id",
        )
        scene_params: Mapping[str, Any] = task_params
        scene_variant, scene_variant_probabilities = resolve_string_topology_scene_variant(
            scene_params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        construction = dict(_QUERY_CONSTRUCTION[str(query_id)])
        last_error: Exception | None = None
        dataset: Mapping[str, Any] | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                dataset = build_string_topology_dataset_for_variant(
                    target_component_type=str(construction["target_component_type"]),
                    target_closed=bool(construction["target_closed"]),
                    target_knotted=bool(construction["target_knotted"]),
                    target_knot_count=int(construction["target_knot_count"]),
                    filler_cycle=tuple(str(value) for value in construction["filler_cycle"]),
                    params=scene_params,
                    instance_seed=int(instance_seed) + int(attempt_index),
                    gen_defaults=_GEN_DEFAULTS,
                    defaults=_DEFAULTS,
                    namespace="puzzles.string_topology.component_count",
                )
                supporting_ids = _supporting_component_ids(
                    str(query_id),
                    [dict(component) for component in dataset["component_specs"]],
                )
                if len(supporting_ids) != int(dataset["target_count"]):
                    raise RuntimeError(
                        "string topology dataset target-answer construction drifted"
                    )
                break
            except RuntimeError as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError("failed to generate string-topology puzzle instance") from last_error
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
                "object_description_string_strip",
                "object_description_string_card",
                "object_description_string_outline",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])

        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            dynamic_slots={
                "object_description": str(object_description),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        components = [dict(component) for component in dataset["component_specs"]]
        feature_counts = {
            str(key): int(value)
            for key, value in dict(dataset["component_feature_counts"]).items()
        }
        supporting_item_ids = _supporting_component_ids(str(query_id), components)
        annotation_source = rendered_scene.component_bbox_map
        annotation_projection = projected_puzzle_bbox_annotation(annotation_source, list(supporting_item_ids))
        annotation_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in annotation_projection["bbox_set"]
        ]
        answer_value = len(supporting_item_ids)
        if int(feature_counts[str(construction["feature_key"])]) != int(answer_value):
            raise ValueError("string topology feature count does not match selected query")
        if len(annotation_bboxes) != int(answer_value):
            raise ValueError("string topology annotation projection does not match answer count")
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))

        visual_scan = float(
            _normalize_int_with_bounds(
                int(dataset["visual_group_count"]),
                list(dataset["visual_group_count_range"]),
            )
        )
        answer_support = [int(value) for value in dataset["target_answer_support"]]
        answer_bounds = [min(answer_support), max(answer_support)]
        answer_load = (
            float(_normalize_int_with_bounds(int(answer_value), answer_bounds))
            if len(set(answer_support)) > 1
            else 0.0
        )
        reasoning_load = min(1.0, float(_REASONING_LOAD_BASE_BY_VARIANT[str(query_id)]) + (0.18 * answer_load))

        annotation_source_name = "component_bboxes_px"
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"puzzle_string_topology_{str(scene_variant)}",
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
                    "open_rope_count": int(feature_counts["open_strings"]),
                    "closed_loop_count": int(feature_counts["closed_strings"]),
                    "knotted_component_count": int(feature_counts["knotted_strings"]),
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
                "question_format": "string_component_count",
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
                "open_rope_count": int(feature_counts["open_strings"]),
                "open_rope_count_range": list(dataset["component_feature_count_range"]),
                "closed_loop_count": int(feature_counts["closed_strings"]),
                "closed_loop_count_range": list(dataset["component_feature_count_range"]),
                "knotted_component_count": int(feature_counts["knotted_strings"]),
                "knotted_component_count_range": list(dataset["component_feature_count_range"]),
                "target_answer_support": [int(value) for value in dataset["target_answer_support"]],
                "target_answer_probabilities": dict(dataset["target_answer_probabilities"]),
                "answer_value": int(answer_value),
                "supporting_item_ids": list(supporting_item_ids),
                "supporting_annotation_source": str(annotation_source_name),
                "query_id_probabilities": dict(query_id_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "solver_trace": {
                    "query_id": str(query_id),
                    "answer_value": int(answer_value),
                    "supporting_item_ids": list(supporting_item_ids),
                    "component_count": int(dataset["component_count"]),
                    "visual_group_count": int(dataset["visual_group_count"]),
                    "object_count": int(dataset["object_count"]),
                    "target_count": int(dataset["target_count"]),
                    "target_answer": int(dataset["target_answer"]),
                    "distractor_count": int(dataset["distractor_count"]),
                    "open_rope_count": int(feature_counts["open_strings"]),
                    "closed_loop_count": int(feature_counts["closed_strings"]),
                    "knotted_component_count": int(feature_counts["knotted_strings"]),
                    "topology_rule": str(dataset["topology_rule"]),
                },
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
            scene_id=SCENE_ID,
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
__all__ = [
    "PuzzlesStringTopologyComponentCountTask",
    "TASK_ID",
]
