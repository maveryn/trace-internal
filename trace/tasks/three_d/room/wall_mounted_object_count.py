"""Count wall-mounted objects in a synthetic 3D indoor room scene."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from ....core.seed import spawn_rng
from ....core.scene_config import (
    get_domain_defaults,
    get_scene_defaults,
    resolve_scene_section_defaults,
)
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.object_scene import resolve_object_scene_render_params
from ..shared.task_support import resolve_axis_variant as _shared_resolve_axis_variant
from .wall_mounted_common import (
    QUERY_OBJECT_TYPE_BY_VARIANT,
    ROOM_FRONT_Y,
    SCENE_ID,
    SUPPORTED_QUERY_IDS,
    SUPPORTED_SCENE_VARIANTS,
    TASK_ID,
)
from .wall_mounted_dataset import _build_room_dataset, _resolve_target_count
from .wall_mounted_rendering import render_room_scene_3d

_TASK_GROUP_DEFAULTS = get_scene_defaults("three_d", "room")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_DOMAIN_DEFAULTS = get_domain_defaults("three_d")
_VISUAL_DEFAULTS = _DOMAIN_DEFAULTS.get("visual", {}) if isinstance(_DOMAIN_DEFAULTS, Mapping) else {}
_BACKGROUND_DEFAULTS = _VISUAL_DEFAULTS.get("background", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}
_NOISE_DEFAULTS = _VISUAL_DEFAULTS.get("noise", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}


@register_task
class ThreeDRoomMultiAttributeAndCountTask:
    """Count target objects mounted on walls in a perspective 3D room."""

    task_id = TASK_ID
    domain = "three_d"
    scene_id = "room"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = (
                int(instance_seed)
                if attempt_index == 0
                else int(spawn_rng(int(instance_seed), f"{TASK_ID}.attempt_seed.{attempt_index}").randrange(1, 2**62))
            )
            try:
                return self._generate_once(int(attempt_seed), params=params)
            except Exception as exc:  # pragma: no cover - unlucky sampling fallback.
                last_error = exc
        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts: {last_error}")

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        query_id, query_probabilities = _shared_resolve_axis_variant(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            supported_variants=SUPPORTED_QUERY_IDS,
            explicit_key="query_id",
            weights_key="query_id_weights",
            balance_flag_key="balanced_query_id_sampling",
            axis_namespace="query_id",
        )
        scene_variant, scene_probabilities = _shared_resolve_axis_variant(
            params,
            task_id=TASK_ID,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            supported_variants=SUPPORTED_SCENE_VARIANTS,
            explicit_key="scene_variant",
            weights_key="scene_variant_weights",
            balance_flag_key="balanced_scene_variant_sampling",
            axis_namespace="scene_variant",
        )
        target_count, target_count_probabilities = _resolve_target_count(
            params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        render_params = resolve_object_scene_render_params(params, render_defaults=_RENDER_DEFAULTS)
        dataset = _build_room_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            target_count=int(target_count),
            render_params=render_params,
            instance_seed=int(instance_seed),
        )
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_room_scene_3d(background, dataset=dataset, render_params=render_params)
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "answer_hint",
                "annotation_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        target_plural = str(dataset["target_object_plural"])
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            scene_id=self.scene_id,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "target_plural": target_plural,
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults["answer_hint"]).format(target_plural=target_plural),
                "annotation_hint": str(prompt_defaults["annotation_hint"]).format(target_plural=target_plural),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_value = int(dataset["target_count"])
        annotation_bboxes = [[round(float(value), 3) for value in bbox] for bbox in rendered_scene.annotation_bboxes]
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))
        solver_trace = dict(dataset["solver_trace"])
        trace_payload = {
            "scene_ir": {
                "scene_kind": "three_d_room_scene",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "target_object_type": str(dataset["target_object_type"]),
                    "target_object_plural": str(dataset["target_object_plural"]),
                    "target_count": int(answer_value),
                    "target_object_ids": [str(value) for value in dataset["target_object_ids"]],
                    "wall_object_count": int(dataset["wall_object_count"]),
                    "floor_object_count": int(dataset["floor_object_count"]),
                    "same_type_surface_distractor_count": int(dataset["same_type_surface_distractor_count"]),
                    "support_surface_count": int(dataset["support_surface_count"]),
                    "object_count": int(dataset["object_count"]),
                    "wall_object_type_counts": dict(dataset["wall_object_type_counts"]),
                    "floor_object_type_counts": dict(dataset["floor_object_type_counts"]),
                    "view_family": "synthetic_perspective_3d_room",
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
                    "query_id_probabilities": dict(query_probabilities),
                    "scene_variant": str(scene_variant),
                    "scene_variant_probabilities": dict(scene_probabilities),
                    "target_object_type": str(dataset["target_object_type"]),
                    "target_object_name": str(dataset["target_object_name"]),
                    "target_object_plural": str(dataset["target_object_plural"]),
                    "target_count": int(answer_value),
                    "target_count_probabilities": dict(target_count_probabilities),
                    "object_count": int(dataset["object_count"]),
                    "wall_object_count": int(dataset["wall_object_count"]),
                    "floor_object_count": int(dataset["floor_object_count"]),
                    "same_type_surface_distractor_count": int(dataset["same_type_surface_distractor_count"]),
                    "support_surface_count": int(dataset["support_surface_count"]),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "label_font_size_px": int(render_params.label_font_size_px),
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "room_bbox_px": list(rendered_scene.room_bbox_px),
                "object_bboxes_px": {str(key): list(value) for key, value in rendered_scene.object_bboxes_px.items()},
                "object_centers_px": {str(key): list(value) for key, value in rendered_scene.object_centers_px.items()},
                "wall_object_bboxes_px": {str(key): list(value) for key, value in rendered_scene.wall_object_bboxes_px.items()},
                "wall_object_centers_px": {str(key): list(value) for key, value in rendered_scene.wall_object_centers_px.items()},
                "floor_object_bboxes_px": {str(key): list(value) for key, value in rendered_scene.floor_object_bboxes_px.items()},
                "floor_object_centers_px": {str(key): list(value) for key, value in rendered_scene.floor_object_centers_px.items()},
                "target_object_bboxes_px": {str(key): list(rendered_scene.object_bboxes_px[str(key)]) for key in dataset["target_object_ids"]},
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_id": SCENE_ID,
                "scene_variant": str(scene_variant),
                "target_object_type": str(dataset["target_object_type"]),
                "target_object_name": str(dataset["target_object_name"]),
                "target_object_plural": str(dataset["target_object_plural"]),
                "target_count": int(answer_value),
                "target_object_ids": [str(value) for value in dataset["target_object_ids"]],
                "wall_object_specs": [dict(spec) for spec in dataset["wall_object_specs"]],
                "floor_object_specs": [dict(spec) for spec in dataset["floor_object_specs"]],
                "object_specs": [dict(spec) for spec in dataset["object_specs"]],
                "object_count": int(dataset["object_count"]),
                "wall_object_count": int(dataset["wall_object_count"]),
                "floor_object_count": int(dataset["floor_object_count"]),
                "same_type_floor_distractor_count": int(dataset["same_type_floor_distractor_count"]),
                "same_type_surface_distractor_count": int(dataset["same_type_surface_distractor_count"]),
                "support_surface_count": int(dataset["support_surface_count"]),
                "object_type_counts": dict(dataset["object_type_counts"]),
                "wall_object_type_counts": dict(dataset["wall_object_type_counts"]),
                "floor_object_type_counts": dict(dataset["floor_object_type_counts"]),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "question_format": str(query_id),
                "view_family": "synthetic_perspective_3d_room",
                "solver_trace": dict(solver_trace),
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(value) for value in dataset["target_object_ids"]],
                "answer": int(answer_value),
            },
            "projected_annotation": {
                "bbox_set": [list(bbox) for bbox in annotation_bboxes],
            },
            "background": dict(background_meta),
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
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
        )


__all__ = ["ThreeDRoomMultiAttributeAndCountTask"]
