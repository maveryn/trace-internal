"""Document-style static map task that returns a visible landmark or zone label."""

from __future__ import annotations

import json
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
from ..shared.diagram.common import projected_diagram_bbox_sequence_annotation
from ..shared.diagram.complexity import (
    build_diagrams_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_diagrams_complexity_weights,
)
from ..shared.diagram.map_common import (
    MapDefaults,
    SUPPORTED_DOCUMENT_MAP_SCENE_VARIANTS,
    SUPPORTED_DOCUMENT_MAP_QUERY_IDS,
    build_map_navigation_dataset,
    resolve_map_render_params,
    resolve_map_scene_variant,
    resolve_map_query_id,
)
from ..shared.diagram.map_scene import render_map_scene
from ..shared.diagram.visual_defaults import load_diagrams_background_defaults, load_diagrams_noise_defaults
from ..shared.fixed_query_task import FixedPagesQueryTaskMixin
from ..shared.public_query_task import rewrite_pages_query_output


TASK_ID = "pages_map_navigation_source"
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = SUPPORTED_DOCUMENT_MAP_QUERY_IDS
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = SUPPORTED_DOCUMENT_MAP_SCENE_VARIANTS
_REASONING_LOAD_BASE_BY_VARIANT = {
    "destination_after_directions": 0.64,
    "landmark_after_route_step": 0.56,
}
_SCENE_LOAD_BY_VARIANT = {"campus_map": 0.26}

_DEFAULTS = MapDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("pages", "map")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_diagrams_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_diagrams_background_defaults(task_group="map")
POST_IMAGE_NOISE_DEFAULTS = load_diagrams_noise_defaults(task_group="map", apply_prob=0.0)


def _build_prompt_json_examples(*, query_id: str) -> tuple[str, str]:
    """Return prompt JSON examples that match the active map-query id."""

    examples = {
        "destination_after_directions": (
            [[188, 310, 314, 368], [426, 310, 552, 368], [426, 478, 552, 536]],
            "Clinic",
        ),
        "landmark_after_route_step": (
            [[214, 388, 340, 446], [452, 388, 578, 446], [690, 388, 816, 446]],
            "Gallery",
        ),
    }
    annotation_bbox, answer_value = examples[str(query_id)]
    answer_and_annotation = {"annotation": annotation_bbox, "answer": str(answer_value)}
    answer_only = {"answer": str(answer_value)}
    return (
        json.dumps(answer_and_annotation, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


class PagesMapNavigationLabelTask:
    """Return an exact visible landmark or zone label from one static printed map."""

    task_id = TASK_ID
    domain = "pages"
    task_group = "map"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = resolve_map_query_id(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        scene_variant, scene_variant_probabilities = resolve_map_scene_variant(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        dataset = build_map_navigation_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
        )
        render_params = resolve_map_render_params(params, render_defaults=_RENDER_DEFAULTS, instance_seed=int(instance_seed))
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_map_scene(
            background,
            scene_title=str(dataset["scene_title"]),
            grid_cols=int(dataset["grid_cols"]),
            grid_rows=int(dataset["grid_rows"]),
            zone_specs=list(dataset["zone_specs"]),
            landmark_specs=list(dataset["landmark_specs"]),
            path_specs=list(dataset["path_specs"]),
            highlighted_route_landmark_ids=[str(item) for item in dataset["highlighted_route_landmark_ids"]],
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
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "annotation_hint_destination_after_directions",
                "annotation_hint_landmark_after_route_step",
                "object_description_campus_map",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(query_id=str(query_id))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_campus_map"]),
                "question_text": str(dataset["question_text"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(query_id)}"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        annotation_bbox_ids = [str(bbox_id) for bbox_id in dataset["annotation_bbox_ids"]]
        annotation_bbox_map = {
            **dict(rendered_scene.landmark_bbox_map),
            **dict(rendered_scene.zone_label_bbox_map),
        }
        annotation_projection = projected_diagram_bbox_sequence_annotation(annotation_bbox_map, annotation_bbox_ids)
        annotation_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in annotation_projection["bbox_sequence"]
        ]
        answer_value = str(dataset["answer_label"])
        answer_gt = TypedValue(type="string", value=str(answer_value))
        annotation_gt = TypedValue(type="bbox_sequence", value=list(annotation_bboxes))

        landmark_scan = normalize_int_with_bounds(int(dataset["landmark_count"]), [8, 14])
        route_scan = normalize_int_with_bounds(len(dataset["route_landmark_ids"]), [1, 6])
        annotation_scan = normalize_int_with_bounds(len(annotation_bbox_ids), [1, 6])
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BASE_BY_VARIANT[str(query_id)])
            + (0.10 * float(route_scan))
            + (0.10 * float(annotation_scan))
        )
        complexity = build_diagrams_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": float(landmark_scan),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"document_map_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "answer_label": str(answer_value),
                    "route_landmark_ids": [str(item) for item in dataset["route_landmark_ids"]],
                    "view_family": str(dataset["view_family"]),
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
                    "landmark_count": int(dataset["landmark_count"]),
                    "route_landmark_count": int(len(dataset["route_landmark_ids"])),
                    "annotation_bbox_count": int(len(annotation_bbox_ids)),
                },
            },
            "render_spec": {
                "scene_variant": str(scene_variant),
                "geometry_seed": int(instance_seed),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "landmark_width_px": int(render_params.landmark_width_px),
                "landmark_height_px": int(render_params.landmark_height_px),
                "path_width_px": int(render_params.path_width_px),
                "highlighted_path_width_px": int(render_params.highlighted_path_width_px),
                "layout_jitter": dict(rendered_scene.layout_jitter_meta),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "panel_bbox_px": list(rendered_scene.panel_bbox_px),
                "title_bbox_px": list(rendered_scene.title_bbox_px),
                "map_bbox_px": list(rendered_scene.map_bbox_px),
                "landmark_bboxes_px": dict(rendered_scene.landmark_bbox_map),
                "landmark_label_bboxes_px": dict(rendered_scene.landmark_label_bbox_map),
                "zone_label_bboxes_px": dict(rendered_scene.zone_label_bbox_map),
                "path_bboxes_px": dict(rendered_scene.path_bbox_map),
                "highlighted_route_bboxes_px": dict(rendered_scene.highlighted_route_bbox_map),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "question_format": str(dataset["question_format"]),
                "view_family": str(dataset["view_family"]),
                "scene_title": str(dataset["scene_title"]),
                "question_text": str(dataset["question_text"]),
                "grid_cols": int(dataset["grid_cols"]),
                "grid_rows": int(dataset["grid_rows"]),
                "landmark_count": int(dataset["landmark_count"]),
                "answer_label": str(answer_value),
                "zone_specs": [dict(spec) for spec in dataset["zone_specs"]],
                "landmark_specs": [dict(spec) for spec in dataset["landmark_specs"]],
                "path_specs": [dict(spec) for spec in dataset["path_specs"]],
                "route_landmark_ids": [str(item) for item in dataset["route_landmark_ids"]],
                "highlighted_route_landmark_ids": [str(item) for item in dataset["highlighted_route_landmark_ids"]],
                "annotation_bbox_ids": list(annotation_bbox_ids),
                "annotation_landmark_bbox_ids": [str(item) for item in dataset["annotation_landmark_bbox_ids"]],
                "annotation_zone_label_bbox_ids": [str(item) for item in dataset["annotation_zone_label_bbox_ids"]],
                "supporting_bbox_ids": list(annotation_bbox_ids),
                "annotation_semantics": str(dataset["annotation_semantics"]),
            },
            "witness_symbolic": {
                "type": "ordered_id_path",
                "ids": [str(item) for item in dataset["route_landmark_ids"]],
            },
            "projected_annotation": dict(annotation_projection),
            "background": background_meta,
            "post_image_noise": post_noise_meta,
        }

        output = TaskOutput(
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
        return rewrite_pages_query_output(
            output,
            query_id=str(query_id),
            scene_id="map",
            query_probabilities=query_id_probabilities,
        )


@register_task
class PagesMapDestinationAfterDirectionsLabelTask(FixedPagesQueryTaskMixin):
    """Identify the destination reached after following visible map directions."""

    task_id = "task_pages__map__destination_after_directions_label"
    domain = "pages"
    task_group = "map"
    public_scene_id = "map"
    fixed_query_id = "destination_after_directions"
    source_task_cls = PagesMapNavigationLabelTask


@register_task
class PagesMapLandmarkAfterRouteStepLabelTask(FixedPagesQueryTaskMixin):
    """Identify the landmark reached after a named route step."""

    task_id = "task_pages__map__landmark_after_route_step_label"
    domain = "pages"
    task_group = "map"
    public_scene_id = "map"
    fixed_query_id = "landmark_after_route_step"
    source_task_cls = PagesMapNavigationLabelTask


__all__ = [
    "PagesMapDestinationAfterDirectionsLabelTask",
    "PagesMapLandmarkAfterRouteStepLabelTask",
    "PagesMapNavigationLabelTask",
]
