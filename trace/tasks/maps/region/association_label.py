"""Maps region task that identifies one labeled region from a choropleth legend query."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

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
from ..shared.common import projected_map_bbox_evidence
from ..shared.complexity import (
    build_maps_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_maps_complexity_weights,
)
from ..shared.region_common import (
    MapRegionDefaults,
    SUPPORTED_MAP_REGION_TASK_VARIANTS,
    build_region_dataset_for_variant,
    resolve_region_render_params,
    resolve_region_scene_variant,
    resolve_region_task_variant,
)
from ..shared.region_scene import render_region_map_scene
from ..shared.visual_defaults import load_maps_background_defaults, load_maps_noise_defaults


TASK_ID = "task_maps_region_association_label"
_SUPPORTED_TASK_VARIANTS: Tuple[str, ...] = SUPPORTED_MAP_REGION_TASK_VARIANTS
_REASONING_LOAD_BASE_BY_VARIANT = {
    "max_category_region": 0.28,
    "min_category_region": 0.28,
    "matches_legend_bin": 0.34,
}
_SCENE_LOAD_BY_VARIANT = {
    "map_strip": 0.10,
    "map_card": 0.16,
    "map_outline": 0.13,
}

_DEFAULTS = MapRegionDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("maps", "region")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_maps_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_maps_background_defaults(task_group="region")
POST_IMAGE_NOISE_DEFAULTS = load_maps_noise_defaults(task_group="region", apply_prob=0.0)


@register_task
class MapsRegionAssociationLabelTask:
    """Return the labeled region that matches one legend-based association query."""

    task_id = TASK_ID
    domain = "maps"
    task_group = "region"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        task_variant, task_variant_probabilities = resolve_region_task_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        scene_variant, scene_variant_probabilities = resolve_region_scene_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        dataset = build_region_dataset_for_variant(
            task_variant=str(task_variant),
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
        )
        render_params = resolve_region_render_params(params, render_defaults=_RENDER_DEFAULTS)
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_region_map_scene(
            background,
            scene_variant=str(scene_variant),
            grid_cols=int(dataset["grid_cols"]),
            grid_rows=int(dataset["grid_rows"]),
            region_specs=list(dataset["region_specs"]),
            legend_specs=list(dataset["legend_specs"]),
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
                "object_description_map_strip",
                "object_description_map_card",
                "object_description_map_outline",
                "evidence_hint_max_category_region",
                "evidence_hint_min_category_region",
                "evidence_hint_matches_legend_bin",
                "json_example_max_category_region",
                "json_example_min_category_region",
                "json_example_matches_legend_bin",
                "json_example_answer_only_max_category_region",
                "json_example_answer_only_min_category_region",
                "json_example_answer_only_matches_legend_bin",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        evidence_hint = str(prompt_defaults[f"evidence_hint_{str(task_variant)}"])
        json_example = str(prompt_defaults[f"json_example_{str(task_variant)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(task_variant)}"])

        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            task_variant_key=str(task_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "question_text": str(dataset["question_text"]),
                "query_category_label": str(dataset["query_category_label"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(evidence_hint),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_region_bbox_id = str(dataset["answer_region_bbox_id"])
        evidence_projection = projected_map_bbox_evidence(
            rendered_scene.region_bbox_map,
            [str(answer_region_bbox_id)],
        )
        evidence_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in evidence_projection["bbox_set"]
        ]
        answer_value = str(dataset["answer_region_label"])
        answer_gt = TypedValue(type="option_letter", value=str(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        region_scan = normalize_int_with_bounds(int(dataset["region_count"]), list(dataset["region_count_range"]))
        grid_scan = normalize_int_with_bounds(int(dataset["grid_cols"] * dataset["grid_rows"]), [24, 35])
        category_scan = normalize_int_with_bounds(int(dataset["category_count"]), [4, 4])
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BASE_BY_VARIANT[str(task_variant)])
            + (0.14 * float(region_scan))
            + (0.10 * float(category_scan))
        )
        complexity = build_maps_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": max(float(region_scan), float(grid_scan)),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"map_region_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "task_variant": str(task_variant),
                    "scene_variant": str(scene_variant),
                    "answer_region_label": str(answer_value),
                    "answer_region_id": str(dataset["answer_region_id"]),
                    "answer_region_bbox_id": str(answer_region_bbox_id),
                    "view_family": str(dataset["view_family"]),
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
                    "grid_cols": int(dataset["grid_cols"]),
                    "grid_rows": int(dataset["grid_rows"]),
                    "grid_cols_range": list(dataset["grid_cols_range"]),
                    "grid_rows_range": list(dataset["grid_rows_range"]),
                    "region_count": int(dataset["region_count"]),
                    "region_count_range": list(dataset["region_count_range"]),
                    "category_count": int(dataset["category_count"]),
                    "query_category_label": str(dataset["query_category_label"]),
                    "color_min_distance": float(dataset["color_min_distance"]),
                    "color_distance_space": str(dataset["color_distance_space"]),
                },
            },
            "render_spec": {
                "scene_variant": str(scene_variant),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "map_panel_width_px": int(render_params.map_panel_width_px),
                "map_panel_height_px": int(render_params.map_panel_height_px),
                "legend_panel_width_px": int(render_params.legend_panel_width_px),
                "legend_panel_height_px": int(render_params.legend_panel_height_px),
                "panel_gap_px": int(render_params.panel_gap_px),
                "region_border_width_px": int(render_params.region_border_width_px),
                "outer_border_width_px": int(render_params.outer_border_width_px),
            },
            "render_map": {
                "region_bboxes_px": dict(rendered_scene.region_bbox_map),
                "legend_entry_bboxes_px": dict(rendered_scene.legend_entry_bbox_map),
                "map_bbox_px": list(rendered_scene.map_bbox_px),
                "legend_bbox_px": list(rendered_scene.legend_bbox_px),
                "divider_bbox_px": list(rendered_scene.divider_bbox_px),
            },
            "execution_trace": {
                "task_variant": str(task_variant),
                "scene_variant": str(scene_variant),
                "question_format": str(dataset["question_format"]),
                "view_family": str(dataset["view_family"]),
                "grid_cols": int(dataset["grid_cols"]),
                "grid_rows": int(dataset["grid_rows"]),
                "grid_cols_range": list(dataset["grid_cols_range"]),
                "grid_rows_range": list(dataset["grid_rows_range"]),
                "region_count": int(dataset["region_count"]),
                "region_count_range": list(dataset["region_count_range"]),
                "category_count": int(dataset["category_count"]),
                "category_labels": list(dataset["category_labels"]),
                "query_category_label": str(dataset["query_category_label"]),
                "question_text": str(dataset["question_text"]),
                "region_specs": [dict(spec) for spec in dataset["region_specs"]],
                "legend_specs": [dict(spec) for spec in dataset["legend_specs"]],
                "answer_region_label": str(answer_value),
                "answer_region_id": str(dataset["answer_region_id"]),
                "answer_region_bbox_id": str(answer_region_bbox_id),
                "supporting_region_bbox_ids": [str(answer_region_bbox_id)],
                "color_min_distance": float(dataset["color_min_distance"]),
                "color_distance_space": str(dataset["color_distance_space"]),
            },
            "witness_symbolic": {
                "type": "id_set",
                "ids": [str(dataset["answer_region_id"])],
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


__all__ = ["MapsRegionAssociationLabelTask"]
