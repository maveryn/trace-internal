"""Select the exact or altered patch option for a park/playground illustration."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.seed import spawn_rng
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.annotation_artifacts import bbox_annotation_artifacts
from ...shared.config_defaults import load_scene_generation_rendering_prompt_defaults, required_group_defaults
from ...shared.fixed_query import select_task_query_id
from ...shared.output_metadata import default_task_versions
from ..shared.canvas_profiles import MAX_RECONSTRUCTION_OUTPUT_PIXELS
from ..shared.cutouts import DEFAULT_OPTION_LABELS, FRAMELESS_ILLUSTRATION_PATCH_STYLE, style_trace
from ..shared.option_rendering import sample_visual_label_font_trace
from ..shared.patch_membership import (
    ALTERED_PATCH_QUERY_ID,
    EXACT_SOURCE_PATCH_QUERY_ID,
    PATCH_MEMBERSHIP_QUERY_IDS,
    alteration_trace,
    compose_source_patch_membership_options,
    downscale_patch_membership_artifacts,
)
from .shared.annotations import park_decor_bbox_map, park_scene_entities, serialize_park_scene
from .shared.defaults import CountDefaults
from .shared.prompts import build_park_prompt_artifacts
from .shared.rendering import render_park_playground_scene
from .shared.sampling import render_params, setting_weights, spawned_task_rng, style_weights
from .shared.source_images import (
    SourcePatchMembershipDefaults,
    SourcePatchMembershipSampleSpec,
    draw_added_park_object,
    editable_patch_objects,
    float_param,
    int_param,
    option_count_support,
    sample_source_patch_membership_spec,
)


TASK_ID = "task_illustrations__park_playground__source_patch_membership_label"
SCENE_ID = "park_playground"
QUERY_IDS: Tuple[str, ...] = PATCH_MEMBERSHIP_QUERY_IDS
PROMPT_QUERY_KEYS: Dict[str, str] = {
    EXACT_SOURCE_PATCH_QUERY_ID: EXACT_SOURCE_PATCH_QUERY_ID,
    ALTERED_PATCH_QUERY_ID: ALTERED_PATCH_QUERY_ID,
}

_DEFAULTS = SourcePatchMembershipDefaults()
_COUNT_DEFAULTS = CountDefaults(
    person_count_min=_DEFAULTS.source_person_count_min,
    person_count_max=_DEFAULTS.source_person_count_max,
    equipment_count_min=_DEFAULTS.source_equipment_count_min,
    equipment_count_max=_DEFAULTS.source_equipment_count_max,
    canvas_width=_DEFAULTS.canvas_width,
    canvas_height=_DEFAULTS.canvas_height,
    render_scale=_DEFAULTS.render_scale,
)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    "illustrations",
    SCENE_ID,
    task_id=TASK_ID,
)


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int) -> SourcePatchMembershipSampleSpec:
    """Sample one complete source scene and a source/altered patch query."""

    query_id, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=QUERY_IDS,
        default_query_id=EXACT_SOURCE_PATCH_QUERY_ID,
        task_id=TASK_ID,
        namespace=f"{TASK_ID}:query",
    )
    return sample_source_patch_membership_spec(
        instance_seed=int(instance_seed),
        params=task_params,
        attempt_index=int(attempt_index),
        namespace=TASK_ID,
        branch_id=str(query_id),
        branch_probabilities=dict(query_probabilities),
        generation_defaults=_GEN_DEFAULTS,
        defaults=_DEFAULTS,
        branch_to_prompt_key=PROMPT_QUERY_KEYS,
    )


@register_task
class IllustrationsParkPlaygroundSourcePatchMembershipLabelTask:
    """Select the source-exact or altered patch option for a complete park scene."""

    task_id = TASK_ID
    domain = "illustrations"
    supported_query_ids = QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Render a complete park scene with exact/altered patch membership options."""

        last_error: Exception | None = None
        sample: SourcePatchMembershipSampleSpec | None = None
        source_scene = None
        artifacts = None
        label_font_trace: Dict[str, Any] | None = None
        min_crop_detail_score = float_param(params, _GEN_DEFAULTS, "min_crop_detail_score", _DEFAULTS.min_crop_detail_score)
        min_patch_difference_score = float_param(params, _GEN_DEFAULTS, "min_patch_difference_score", _DEFAULTS.min_patch_difference_score)
        min_changed_fraction = float_param(params, _GEN_DEFAULTS, "min_changed_fraction", _DEFAULTS.min_changed_fraction)
        max_changed_fraction = float_param(params, _GEN_DEFAULTS, "max_changed_fraction", _DEFAULTS.max_changed_fraction)
        min_edit_objects = int_param(params, _GEN_DEFAULTS, "min_edit_objects", _DEFAULTS.min_edit_objects)
        max_edit_objects = int_param(params, _GEN_DEFAULTS, "max_edit_objects", _DEFAULTS.max_edit_objects)

        for attempt in range(max(1, int(max_attempts))):
            try:
                sample = _sample_spec(instance_seed=int(instance_seed), params=params, attempt_index=int(attempt))
                scene_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:source_scene", int(attempt))
                rp = render_params(
                    {
                        **dict(params),
                        "canvas_width": int(sample.source_size[0]),
                        "canvas_height": int(sample.source_size[1]),
                    },
                    _RENDER_DEFAULTS,
                    fallback_width=_COUNT_DEFAULTS.canvas_width,
                    fallback_height=_COUNT_DEFAULTS.canvas_height,
                    fallback_scale=_COUNT_DEFAULTS.render_scale,
                    instance_seed=int(instance_seed),
                    namespace=f"{TASK_ID}:source_profile",
                )
                source_scene = render_park_playground_scene(
                    rng=scene_rng,
                    person_specs=sample.person_specs,
                    equipment_specs=sample.equipment_specs,
                    canvas_width=int(rp["canvas_width"]),
                    canvas_height=int(rp["canvas_height"]),
                    render_scale=int(rp["render_scale"]),
                    setting_weights=setting_weights(params, _RENDER_DEFAULTS),
                    style_weights=style_weights(params, _RENDER_DEFAULTS),
                )
                option_rng = spawned_task_rng(int(instance_seed), f"{TASK_ID}:patch_options", int(attempt))
                label_font_trace = sample_visual_label_font_trace(
                    namespace_prefix=TASK_ID,
                    instance_seed=int(instance_seed),
                    params={**dict(_RENDER_DEFAULTS), **dict(params)},
                    namespace_suffix="patch_option_labels",
                    explicit_key="patch_label_font_family",
                    weights_key="patch_label_font_weights",
                )
                artifacts = compose_source_patch_membership_options(
                    source_image=source_scene.image.convert("RGB"),
                    rng=option_rng,
                    query_id=str(sample.branch_id),
                    correct_index=int(sample.correct_index),
                    option_count=int(sample.option_count),
                    patch_size=sample.patch_size,
                    crop_margin_px=int(sample.crop_margin_px),
                    edit_objects=editable_patch_objects(source_scene),
                    frame_style=FRAMELESS_ILLUSTRATION_PATCH_STYLE,
                    label_font_family=str(label_font_trace["font_family"]),
                    min_crop_detail_score=float(min_crop_detail_score),
                    min_patch_difference_score=float(min_patch_difference_score),
                    min_changed_fraction=float(min_changed_fraction),
                    max_changed_fraction=float(max_changed_fraction),
                    min_edit_objects=int(min_edit_objects),
                    max_edit_objects=int(max_edit_objects),
                    draw_added_object=draw_added_park_object,
                )
                artifacts = downscale_patch_membership_artifacts(
                    artifacts,
                    max_pixels=MAX_RECONSTRUCTION_OUTPUT_PIXELS,
                )
                break
            except Exception as exc:  # pragma: no cover - retry surface is seed/layout dependent.
                last_error = exc
                sample = None
                source_scene = None
                artifacts = None
                label_font_trace = None
        if sample is None or source_scene is None or artifacts is None or label_font_trace is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        serialized_scene, person_bboxes = serialize_park_scene(source_scene)
        decor_bboxes = park_decor_bbox_map(source_scene)
        answer_label = str(artifacts.selected_label)
        annotation_artifacts = bbox_annotation_artifacts(artifacts.selected_option_bbox)
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_source_patch_membership",
                "annotation_hint_source_patch_membership",
                "json_example_source_patch_membership",
                "json_example_answer_only_source_patch_membership",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_artifacts = build_park_prompt_artifacts(
            domain=self.domain,
            scene_id=SCENE_ID,
            prompt_defaults=prompt_defaults,
            prompt_query_key=str(sample.prompt_branch_key),
            slots={
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint_source_patch_membership"]),
                "answer_hint": str(prompt_defaults["answer_hint_source_patch_membership"]),
                "json_example": str(prompt_defaults["json_example_source_patch_membership"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only_source_patch_membership"]),
            },
            instance_seed=int(instance_seed),
        )
        alteration_payload = alteration_trace(artifacts.option_alterations)
        option_source_crop_boxes = {
            str(label): [int(coord) for coord in box]
            for label, box in artifacts.option_source_crop_boxes.items()
        }
        trace_payload = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "scene_kind": "park_playground_source_patch_membership_label",
                "entities": park_scene_entities(source_scene),
                "relations": {
                    "query_id": str(sample.branch_id),
                    "prompt_query_key": str(sample.prompt_branch_key),
                    "answer_label": answer_label,
                    "selected_provenance": str(artifacts.option_provenance[answer_label]),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(sample.branch_id),
                "prompt_query_key": str(sample.prompt_branch_key),
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(sample.branch_id),
                    "prompt_query_key": str(sample.prompt_branch_key),
                    "source_person_count": int(sample.source_person_count),
                    "source_person_count_probabilities": dict(sample.source_person_count_probabilities),
                    "source_equipment_count": int(sample.source_equipment_count),
                    "source_equipment_count_probabilities": dict(sample.source_equipment_count_probabilities),
                    "option_count": int(sample.option_count),
                    "option_count_support": [int(value) for value in option_count_support(params, _GEN_DEFAULTS, fallback=_DEFAULTS.option_count_support)],
                    "option_count_probabilities": dict(sample.option_count_probabilities),
                    "option_labels": list(DEFAULT_OPTION_LABELS[: int(sample.option_count)]),
                    "answer_label": answer_label,
                    "correct_index": int(sample.correct_index),
                    "correct_index_probabilities": dict(sample.correct_index_probabilities),
                    "patch_size": [int(sample.patch_size[0]), int(sample.patch_size[1])],
                    "source_size": [int(sample.source_size[0]), int(sample.source_size[1])],
                    **dict(sample.source_profile_trace),
                    "crop_margin_px": int(sample.crop_margin_px),
                    "min_crop_detail_score": float(min_crop_detail_score),
                    "min_patch_difference_score": float(min_patch_difference_score),
                    "min_changed_fraction": float(min_changed_fraction),
                    "max_changed_fraction": float(max_changed_fraction),
                    "min_edit_objects": int(min_edit_objects),
                    "max_edit_objects": int(max_edit_objects),
                    "query_id_probabilities": dict(sample.branch_probabilities),
                    "query_probabilities": dict(sample.branch_probabilities),
                },
            },
            "render_spec": {
                "canvas_size": [int(artifacts.image.width), int(artifacts.image.height)],
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "source_scene_canvas_size": [int(source_scene.canvas_width), int(source_scene.canvas_height)],
                "source_profile": dict(sample.source_profile_trace),
                "style": {
                    "source_setting_id": str(source_scene.setting_id),
                    "source_style_id": str(source_scene.style_id),
                    "source_render_scale": int(source_scene.render_scale),
                    "source_layout": dict(source_scene.layout),
                    "patch_frame_style": style_trace(FRAMELESS_ILLUSTRATION_PATCH_STYLE),
                    "patch_label_font": dict(label_font_trace),
                },
            },
            "render_map": {
                "image_id": "img0",
                "reference_image_bbox_px": list(artifacts.source_image_bbox),
                "option_bboxes_px_by_label": {str(key): list(value) for key, value in artifacts.option_bboxes.items()},
                "selected_option_bbox_px": list(artifacts.selected_option_bbox),
                "source_person_bboxes_px": person_bboxes,
                "source_decor_bboxes_px": decor_bboxes,
                "source_scene_canvas_size": [int(source_scene.canvas_width), int(source_scene.canvas_height)],
                "source_size": [int(sample.source_size[0]), int(sample.source_size[1])],
                "option_source_crop_boxes_px_by_label": option_source_crop_boxes,
                "option_provenance_by_label": dict(artifacts.option_provenance),
                "selected_provenance": str(artifacts.option_provenance[answer_label]),
                "option_alterations_by_label": alteration_payload,
                "option_grid_shape": [int(artifacts.option_grid_shape[0]), int(artifacts.option_grid_shape[1])],
                "candidate_crop_count": int(artifacts.candidate_crop_count),
                "pre_downscale_canvas_size": [int(value) for value in artifacts.pre_downscale_canvas_size],
                "output_scale_xy": [float(value) for value in artifacts.output_scale_xy],
            },
            "execution_trace": {
                "query_id": str(sample.branch_id),
                "prompt_query_key": str(sample.prompt_branch_key),
                "scene_id": SCENE_ID,
                "answer": answer_label,
                "answer_label": answer_label,
                "correct_index": int(sample.correct_index),
                "selected_provenance": str(artifacts.option_provenance[answer_label]),
                "option_labels": list(DEFAULT_OPTION_LABELS[: int(sample.option_count)]),
                "option_provenance_by_label": dict(artifacts.option_provenance),
                "option_source_crop_boxes_px_by_label": option_source_crop_boxes,
                "option_alterations_by_label": alteration_payload,
                "source_scene": serialized_scene[0],
            },
            "witness_symbolic": {
                "selected_option": list(artifacts.selected_option_bbox),
                "answer_label": answer_label,
                "selected_provenance": str(artifacts.option_provenance[answer_label]),
            },
            "projected_annotation": {
                **dict(annotation_artifacts.projected_annotation),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="option_letter", value=answer_label),
            annotation_gt=annotation_artifacts.annotation_gt,
            image=artifacts.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sample.branch_id),
        )


__all__ = [
    "ALTERED_PATCH_QUERY_ID",
    "EXACT_SOURCE_PATCH_QUERY_ID",
    "IllustrationsParkPlaygroundSourcePatchMembershipLabelTask",
    "QUERY_IDS",
    "TASK_ID",
    "_sample_spec",
]
