"""Select the result of applying one geometric transform to a curated icon."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, load_scene_generation_rendering_prompt_defaults
from ...shared.fixed_query import select_task_query_id
from ...shared.labeling import LABEL_POOL_A_L
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import build_prompt_query_spec
from ..shared.annotation import bbox_map_annotation
from ..shared.icon_transform import IDENTITY_TRANSFORM_ID

from .shared.annotations import bbox_map_roles, matching_scene_cell
from .shared.defaults import SingleTransformOptionsDefaults
from .shared.prompts import render_single_transform_prompt_artifacts
from .shared.rendering import sample_and_render_single_transform_scene
from .shared.sampling import resolve_fixed_option_count
from .shared.styles import resolve_single_transform_render_params, single_transform_style_trace


TASK_ID = "task_icons__single_transform_options__geometric_transform_result_label"
DOMAIN = "icons"
SCENE_ID = "single_transform_options"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "rotate_90_clockwise_result_label",
    "rotate_90_counterclockwise_result_label",
    "rotate_180_result_label",
    "flip_horizontal_result_label",
    "flip_vertical_result_label",
)
_QUERY_TO_TRANSFORM: Dict[str, str] = {
    "rotate_90_clockwise_result_label": "rot270",
    "rotate_90_counterclockwise_result_label": "rot90",
    "rotate_180_result_label": "rot180",
    "flip_horizontal_result_label": "flip_h",
    "flip_vertical_result_label": "flip_v",
}
_QUERY_TO_CUE: Dict[str, str] = {
    "rotate_90_clockwise_result_label": "Rotate 90 CW",
    "rotate_90_counterclockwise_result_label": "Rotate 90 CCW",
    "rotate_180_result_label": "Rotate 180",
    "flip_horizontal_result_label": "Flip horizontal",
    "flip_vertical_result_label": "Flip vertical",
}


_DEFAULTS = SingleTransformOptionsDefaults()
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    DOMAIN,
    SCENE_ID,
    task_id=TASK_ID,
)


def _select_query(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float], Dict[str, Any]]:
    """Select and validate the public operation branch."""

    return select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id=SUPPORTED_QUERY_IDS[0],
        task_id=TASK_ID,
        namespace=f"{TASK_ID}.query",
    )


def _resolve_answer_index(rng, *, params: Mapping[str, Any], labels: Sequence[str]) -> Tuple[int, Dict[str, float]]:
    """Resolve the unique correct option position."""

    label_set = {str(value) for value in labels}
    if params.get("answer_index") is not None:
        index = int(params["answer_index"])
        if not 0 <= index < len(labels):
            raise ValueError("answer_index out of range")
        return index, {str(label): (1.0 if i == index else 0.0) for i, label in enumerate(labels)}
    if params.get("answer_label") is not None:
        label = str(params["answer_label"]).strip().upper()
        if label not in label_set:
            raise ValueError("answer_label is not supported by the sampled option count")
        index = int(list(str(value) for value in labels).index(label))
        return index, {str(candidate): (1.0 if str(candidate) == label else 0.0) for candidate in labels}
    index = int(rng.randrange(len(labels)))
    probability = 1.0 / float(len(labels))
    return index, {str(label): float(probability) for label in labels}


@register_task
class IconsSingleTransformOptionsGeometricTransformResultLabelTask:
    """Select the labeled result of applying one geometric transform."""

    task_id = TASK_ID
    domain = DOMAIN
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic transform-result option instance."""

        query_id, query_probabilities, task_params = _select_query(int(instance_seed), params)
        scene_rng = spawn_rng(int(instance_seed), "scene")
        option_count = resolve_fixed_option_count(
            task_params,
            generation_defaults=_GEN_DEFAULTS,
            fallback_defaults=_DEFAULTS,
        )
        labels = tuple(str(value) for value in LABEL_POOL_A_L[: int(option_count)])
        answer_index, answer_label_probabilities = _resolve_answer_index(scene_rng, params=task_params, labels=labels)
        target_transform_id = str(_QUERY_TO_TRANSFORM[str(query_id)])
        operation_cue = str(_QUERY_TO_CUE[str(query_id)])
        render_params = resolve_single_transform_render_params(
            params=task_params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        pool_manifest = str(
            task_params.get("pool_manifest", group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest))
        )
        transform_check_size_px = int(
            task_params.get(
                "transform_check_size_px",
                group_default(_GEN_DEFAULTS, "transform_check_size_px", _DEFAULTS.transform_check_size_px),
            )
        )

        scene_payload = None
        image = None
        last_error: Exception | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                scene_payload, image = sample_and_render_single_transform_scene(
                    scene_rng,
                    instance_seed=int(instance_seed),
                    option_count=int(option_count),
                    answer_index=int(answer_index),
                    target_transform_id=str(target_transform_id),
                    operation_cue=str(operation_cue),
                    pool_manifest=str(pool_manifest),
                    transform_check_size_px=int(transform_check_size_px),
                    render_params=render_params,
                )
                break
            except Exception as exc:
                last_error = exc
                continue
        if scene_payload is None or image is None:
            raise RuntimeError(f"failed to generate {self.task_id} instance") from last_error

        prompt_defaults, prompt_artifacts = render_single_transform_prompt_artifacts(
            instance_seed=int(instance_seed),
            prompt_defaults=_PROMPT_DEFAULTS,
            operation_key=str(query_id),
        )

        selected_cell = matching_scene_cell(scene_payload.scene_cells)
        annotation_artifacts = bbox_map_annotation(
            bbox_map_roles(
                reference_cell=scene_payload.reference_cell,
                selected_cell=selected_cell,
            )
        )
        answer_gt = TypedValue(type="option_letter", value=str(scene_payload.answer_label))
        annotation_gt = TypedValue(
            type=str(annotation_artifacts["annotation_type"]),
            value=dict(annotation_artifacts["annotation_value"]),
        )
        query_spec = build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(query_id),
            params={
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id_probabilities": dict(query_probabilities),
                "answer_label_probabilities": dict(answer_label_probabilities),
                "object_count": int(scene_payload.object_count),
                "pool_manifest": str(pool_manifest),
                "transform_check_size_px": int(transform_check_size_px),
                "target_transform_id": str(scene_payload.target_transform_id),
                "operation_cue": str(scene_payload.operation_cue),
                "answer_label": str(scene_payload.answer_label),
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_single_transform_options_result_label",
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "entities": [dict(scene_payload.reference_cell), *[dict(item) for item in scene_payload.scene_cells]],
                "relations": {
                    "target": "option_transform_equals_reference_after_operation",
                    "operation_cue": str(scene_payload.operation_cue),
                    "target_transform_id": str(scene_payload.target_transform_id),
                    "answer_label": str(scene_payload.answer_label),
                    "answer_transform_id": str(selected_cell["transform_id"]),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene_payload.panel_geometry),
                },
            },
            "query_spec": dict(query_spec),
            "render_spec": {
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "canvas_size": [int(render_params["canvas_width"]), int(render_params["canvas_height"])],
                "coord_space": "pixel",
                "panel_geometry": dict(scene_payload.panel_geometry),
                "style": single_transform_style_trace(
                    render_params=render_params,
                    sampled_palette_rgb=scene_payload.sampled_palette_rgb,
                ),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {
                    "reference_icon": dict(scene_payload.reference_cell),
                    "answer_label": str(scene_payload.answer_label),
                    "selected_option": dict(selected_cell),
                    "scene_cells": [dict(item) for item in scene_payload.scene_cells],
                },
            },
            "execution_trace": {
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "query_id_probabilities": dict(query_probabilities),
                "scene_variant": "reference_icon_with_transform_result_options",
                "question_format": "select_transformed_reference_icon_option",
                "object_count": int(scene_payload.object_count),
                "cell_labels": list(scene_payload.cell_labels),
                "answer": str(scene_payload.answer_label),
                "answer_label": str(scene_payload.answer_label),
                "answer_label_probabilities": dict(answer_label_probabilities),
                "icon_id": str(scene_payload.icon_id),
                "operation_cue": str(scene_payload.operation_cue),
                "target_transform_id": str(scene_payload.target_transform_id),
                "option_transform_ids_by_label": {
                    str(cell["label"]): str(cell["transform_id"])
                    for cell in scene_payload.scene_cells
                },
                "annotation_roles": ["reference_icon", "selected_option"],
            },
            "witness_symbolic": {
                "reference_icon_id": str(scene_payload.icon_id),
                "reference_transform_id": IDENTITY_TRANSFORM_ID,
                "target_transform_id": str(scene_payload.target_transform_id),
                "selected_option_label": str(scene_payload.answer_label),
                "selected_option_transform_id": str(selected_cell["transform_id"]),
                "reference_icon_bbox": list(scene_payload.reference_cell["icon_bbox_xyxy"]),
                "selected_option_bbox": list(selected_cell["cell_bbox_xyxy"]),
            },
            "projected_annotation": dict(annotation_artifacts["projected_annotation"]),
        }
        trace_payload["query_spec"]["template_id"] = str(prompt_defaults["bundle_id"])
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["IconsSingleTransformOptionsGeometricTransformResultLabelTask", "TASK_ID", "SUPPORTED_QUERY_IDS"]
