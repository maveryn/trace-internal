"""Diagrams set task that sums numeric tokens across queried overlap regions."""

from __future__ import annotations

import json
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
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
from ..shared.common import projected_diagram_bbox_evidence
from ..shared.complexity import (
    build_diagrams_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_diagrams_complexity_weights,
)
from ..shared.set_common import (
    SUPPORTED_DIAGRAM_SET_SCENE_VARIANTS,
    SUPPORTED_DIAGRAM_SET_TASK_VARIANTS,
    build_set_region_sum_dataset,
    resolve_set_render_params,
    resolve_set_scene_variant,
    resolve_set_task_variant,
    sample_set_fill_colors,
)
from ..shared.set_scene import render_set_scene
from ..shared.visual_defaults import load_diagrams_background_defaults, load_diagrams_noise_defaults


TASK_ID = "task_diagrams_set_diagram_region_sum_value"
_SUPPORTED_TASK_VARIANTS: Tuple[str, ...] = SUPPORTED_DIAGRAM_SET_TASK_VARIANTS
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = SUPPORTED_DIAGRAM_SET_SCENE_VARIANTS
_REASONING_LOAD_BASE_BY_VARIANT = {
    "sum_only_in_named_set": 0.18,
    "sum_in_named_set": 0.35,
    "sum_in_named_union": 0.56,
    "sum_in_named_intersection": 0.42,
    "sum_in_exactly_two_sets": 0.48,
}
_SCENE_LOAD_BY_VARIANT = {"set_diagram": 0.14}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("diagrams", "set_diagram")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_diagrams_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_diagrams_background_defaults(task_group="set_diagram")
POST_IMAGE_NOISE_DEFAULTS = load_diagrams_noise_defaults(task_group="set_diagram", apply_prob=0.0)


def _build_prompt_json_examples(*, task_variant: str) -> tuple[str, str]:
    """Return prompt JSON examples that match the active set-sum variant."""

    examples = {
        "sum_only_in_named_set": (7, [[300, 326, 329, 367]]),
        "sum_in_named_set": (20, [[300, 326, 329, 367], [559, 267, 589, 309], [451, 506, 481, 548], [559, 420, 589, 462]]),
        "sum_in_named_union": (31, [[300, 326, 329, 367], [818, 326, 847, 367], [559, 267, 589, 309], [451, 506, 481, 548], [667, 506, 697, 548], [559, 420, 589, 462]]),
        "sum_in_named_intersection": (12, [[559, 267, 589, 309], [559, 420, 589, 462]]),
        "sum_in_exactly_two_sets": (18, [[559, 267, 589, 309], [451, 506, 481, 548], [667, 506, 697, 548]]),
    }
    answer_value, evidence_bboxes = examples[str(task_variant)]
    answer_and_evidence = {"evidence": evidence_bboxes, "answer": int(answer_value)}
    answer_only = {"answer": int(answer_value)}
    return (
        json.dumps(answer_and_evidence, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


def _sort_bbox_ids_reading_order(
    bbox_map: Mapping[str, Sequence[float]],
    bbox_ids: Sequence[str],
) -> list[str]:
    """Return bbox ids sorted from top to bottom and then left to right."""

    def _key(bbox_id: str) -> tuple[float, float, str]:
        bbox = [float(value) for value in bbox_map[str(bbox_id)]]
        return (float(bbox[1]), float(bbox[0]), str(bbox_id))

    return sorted((str(bbox_id) for bbox_id in bbox_ids), key=_key)


@register_task
class DiagramsSetRegionSumValueTask:
    """Return the integer sum of digits across queried 3-set overlap regions."""

    task_id = TASK_ID
    domain = "diagrams"
    task_group = "set_diagram"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        task_variant, task_variant_probabilities = resolve_set_task_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        scene_variant, scene_variant_probabilities = resolve_set_scene_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        dataset = build_set_region_sum_dataset(
            task_variant=str(task_variant),
            scene_variant=str(scene_variant),
            params=params,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        render_params = resolve_set_render_params(params, render_defaults=_RENDER_DEFAULTS)
        set_palette = sample_set_fill_colors(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_set_scene(
            background,
            scene_title=str(dataset["scene_title"]),
            set_ids=list(dataset["set_ids"]),
            number_specs=list(dataset["number_specs"]),
            set_fill_rgb_map=dict(set_palette["set_fill_rgb_map"]),
            render_params=render_params,
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
                "task_family_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "evidence_hint",
                "object_description_set_diagram",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(task_variant=str(task_variant))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            task_variant_key=str(task_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_set_diagram"]),
                "question_text": str(dataset["question_text"]),
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

        supporting_bbox_ids = _sort_bbox_ids_reading_order(
            rendered_scene.number_bbox_map,
            [str(value) for value in dataset["supporting_number_bbox_ids"]],
        )
        evidence_projection = projected_diagram_bbox_evidence(rendered_scene.number_bbox_map, supporting_bbox_ids)
        evidence_bboxes = [[round(float(value), 3) for value in bbox] for bbox in evidence_projection["bbox_set"]]
        answer_value = int(dataset["answer_value"])
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        contributing_count = int(len(dataset["contributing_region_ids"]))
        contributing_scan = normalize_int_with_bounds(int(contributing_count), [1, 6])
        answer_magnitude_scan = normalize_int_with_bounds(int(answer_value), [1, 39])
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BASE_BY_VARIANT[str(task_variant)])
            + (0.18 * float(contributing_scan))
            + (0.10 * float(answer_magnitude_scan))
        )
        complexity = build_diagrams_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": clamp_unit_interval(0.42 + (0.32 * float(contributing_scan))),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"diagram_set_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "task_variant": str(task_variant),
                    "scene_variant": str(scene_variant),
                    "view_family": str(dataset["view_family"]),
                    "contributing_region_ids": [str(value) for value in dataset["contributing_region_ids"]],
                    "supporting_number_bbox_ids": [str(value) for value in supporting_bbox_ids],
                },
            },
            "query_spec": {
                "task_variant": str(task_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "task_variant": str(task_variant),
                    "scene_variant": str(scene_variant),
                    "task_variant_probabilities": dict(task_variant_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "set_count": int(dataset["set_count"]),
                    "number_count": int(dataset["number_count"]),
                    "contributing_region_count": int(contributing_count),
                    "query_focus": str(dataset["query_focus"]),
                },
            },
            "render_spec": {
                "scene_variant": str(scene_variant),
                "geometry_seed": int(instance_seed),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "number_slot_width_px": int(render_params.number_slot_width_px),
                "number_slot_height_px": int(render_params.number_slot_height_px),
                "region_outline_width_px": int(render_params.region_outline_width_px),
                "set_fill_alpha": int(render_params.set_fill_alpha),
                "min_set_color_distance": float(set_palette["min_set_color_distance"]),
                "color_distance_space": str(set_palette["color_distance_space"]),
                "set_fill_rgb_map": dict(set_palette["set_fill_rgb_map"]),
            },
            "render_map": {
                "panel_bbox_px": list(rendered_scene.panel_bbox_px),
                "title_bbox_px": list(rendered_scene.title_bbox_px),
                "region_bboxes_px": dict(rendered_scene.region_bbox_map),
                "set_label_bboxes_px": dict(rendered_scene.set_label_bbox_map),
                "number_bboxes_px": dict(rendered_scene.number_bbox_map),
                "number_slot_bboxes_px": dict(rendered_scene.number_slot_bbox_map),
            },
            "execution_trace": {
                "task_variant": str(task_variant),
                "scene_variant": str(scene_variant),
                "question_format": str(dataset["question_format"]),
                "view_family": str(dataset["view_family"]),
                "scene_title": str(dataset["scene_title"]),
                "question_text": str(dataset["question_text"]),
                "set_ids": [str(set_id) for set_id in dataset["set_ids"]],
                "set_count": int(dataset["set_count"]),
                "region_ids": [str(region_id) for region_id in dataset["region_ids"]],
                "number_count": int(dataset["number_count"]),
                "query_focus": str(dataset["query_focus"]),
                "target_sets": [str(value) for value in dataset["target_sets"]],
                "contributing_region_ids": [str(value) for value in dataset["contributing_region_ids"]],
                "answer_value": int(answer_value),
                "region_number_map": dict(dataset["region_number_map"]),
                "number_specs": [dict(spec) for spec in dataset["number_specs"]],
                "supporting_number_bbox_ids": [str(value) for value in supporting_bbox_ids],
                "set_fill_rgb_map": dict(set_palette["set_fill_rgb_map"]),
                "min_set_color_distance": float(set_palette["min_set_color_distance"]),
                "color_distance_space": str(set_palette["color_distance_space"]),
            },
            "witness_symbolic": {
                "type": "id_set",
                "ids": [str(value) for value in supporting_bbox_ids],
            },
            "projected_evidence": dict(evidence_projection),
            "background": background_meta,
            "post_image_noise": post_noise_meta,
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant=str(task_variant),
        )


__all__ = ["DiagramsSetRegionSumValueTask"]
