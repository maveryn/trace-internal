"""Count non-anchor icons whose centers lie between two marked anchors."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.seed import spawn_rng
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, load_scene_generation_rendering_prompt_defaults
from ...shared.counting_sampling import resolve_counting_target_and_distractor_triplet
from ...shared.fixed_query import select_task_query_id
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import build_prompt_query_spec

from .shared.annotations import matching_icon_bbox_set_annotation
from .shared.defaults import DOMAIN, SCENE_ID, TwoAnchorDefaults
from .shared.output import two_anchor_render_spec
from .shared.prompts import render_two_anchor_prompt_artifacts
from .shared.rendering import sample_and_render_two_anchor_scene
from .shared.styles import resolve_two_anchor_render_params


TASK_ID = "task_icons__two_anchor__between_anchors_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "inside_vertical_strip",
    "inside_horizontal_strip",
)
_QUERY_TO_AXIS: Dict[str, str] = {
    "inside_vertical_strip": "vertical",
    "inside_horizontal_strip": "horizontal",
}


_DEFAULTS = TwoAnchorDefaults()
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    DOMAIN,
    SCENE_ID,
    task_id=TASK_ID,
)


def _select_query(instance_seed: int, params: Mapping[str, Any]) -> tuple[str, Dict[str, float], Dict[str, Any]]:
    """Select the user-facing strip orientation query."""

    return select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id=SUPPORTED_QUERY_IDS[0],
        task_id=TASK_ID,
        namespace=f"{TASK_ID}.query",
    )


def _resolve_rotation_candidates(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Resolve scene icon rotations from task params or scene defaults."""

    raw = params.get(
        "rotation_candidates_degrees",
        group_default(_GEN_DEFAULTS, "rotation_candidates_degrees", list(_DEFAULTS.rotation_candidates_degrees)),
    )
    if not isinstance(raw, (list, tuple)):
        raise ValueError("rotation_candidates_degrees must be a sequence")
    rotations = tuple(int(value) % 360 for value in raw)
    if not rotations:
        raise ValueError("rotation_candidates_degrees must contain at least one entry")
    return rotations


@register_task
class IconsTwoAnchorBetweenAnchorsCountTask:
    """Count icons inside the vertical or horizontal strip between two anchors."""

    task_id = TASK_ID
    domain = DOMAIN
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic two-anchor strip-count instance."""

        query_id, query_probabilities, task_params = _select_query(int(instance_seed), params)
        strip_axis = str(_QUERY_TO_AXIS[str(query_id)])
        scene_rng = spawn_rng(int(instance_seed), "scene")

        (
            object_count,
            object_count_probabilities,
            target_count,
            target_count_probabilities,
            distractor_count,
            distractor_count_probabilities,
        ) = resolve_counting_target_and_distractor_triplet(
            scene_rng,
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            fallback_total_min=_DEFAULTS.object_count_min,
            fallback_total_max=_DEFAULTS.object_count_max,
            fallback_target_min=_DEFAULTS.target_count_min,
            fallback_target_max=_DEFAULTS.target_count_max,
            fallback_distractor_min=_DEFAULTS.distractor_count_min,
            fallback_distractor_max=_DEFAULTS.distractor_count_max,
        )
        distractor_margin_over_target = int(
            task_params.get(
                "distractor_margin_over_target",
                group_default(_GEN_DEFAULTS, "distractor_margin_over_target", _DEFAULTS.distractor_margin_over_target),
            )
        )
        render_params = resolve_two_anchor_render_params(
            params=task_params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        pool_manifest = str(
            task_params.get("pool_manifest", group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest))
        )
        rotation_candidates = _resolve_rotation_candidates(task_params)

        scene_payload = None
        image = None
        last_error: Exception | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                scene_payload, image = sample_and_render_two_anchor_scene(
                    scene_rng,
                    instance_seed=int(instance_seed),
                    strip_axis=str(strip_axis),
                    object_count=int(object_count),
                    target_count=int(target_count),
                    distractor_count=int(distractor_count),
                    pool_manifest=str(pool_manifest),
                    rotation_candidates=tuple(rotation_candidates),
                    render_params=render_params,
                )
                break
            except Exception as exc:
                last_error = exc
                continue
        if scene_payload is None or image is None:
            raise RuntimeError(f"failed to generate {self.task_id} instance") from last_error

        _prompt_defaults, prompt_artifacts = render_two_anchor_prompt_artifacts(
            instance_seed=int(instance_seed),
            prompt_defaults=_PROMPT_DEFAULTS,
            query_key=str(query_id),
        )
        annotation_artifacts = matching_icon_bbox_set_annotation(scene_payload.matching_bboxes)
        answer_gt = TypedValue(type="integer", value=int(scene_payload.target_count))
        annotation_gt = TypedValue(
            type=str(annotation_artifacts["annotation_type"]),
            value=list(annotation_artifacts["annotation_value"]),
        )
        query_spec = build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(query_id),
            params={
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id_probabilities": dict(query_probabilities),
                "object_count": int(object_count),
                "object_count_probabilities": dict(object_count_probabilities),
                "target_count": int(target_count),
                "target_count_probabilities": dict(target_count_probabilities),
                "distractor_count": int(distractor_count),
                "distractor_count_probabilities": dict(distractor_count_probabilities),
                "distractor_margin_over_target": int(distractor_margin_over_target),
                "pool_manifest": str(pool_manifest),
                "rotation_candidates_degrees": [int(value) for value in rotation_candidates],
                "strip_axis": str(strip_axis),
                "strip_boundary_margin_px": int(render_params["strip_boundary_margin_px"]),
                "strip_span_ratio_min": float(render_params["strip_span_ratio_min"]),
                "strip_span_ratio_max": float(render_params["strip_span_ratio_max"]),
                "strip_outside_ratio_min": float(render_params["strip_outside_ratio_min"]),
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_two_anchor_strip_relation",
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "entities": [
                    dict(scene_payload.anchor_instances[0]),
                    dict(scene_payload.anchor_instances[1]),
                    *[dict(entity) for entity in scene_payload.scene_instances],
                ],
                "relations": {
                    "counting_target": "candidate_icon_centers_in_strip_between_two_anchors",
                    "strip_axis": str(strip_axis),
                    "anchor_icon_id": str(scene_payload.anchor_icon_id),
                    "matching_scene_indices": [int(value) for value in scene_payload.matching_scene_indices],
                    "strip_boundary_margin_px": int(scene_payload.strip_boundary_margin_px),
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
                **two_anchor_render_spec(
                    render_params=render_params,
                    panel_geometry=scene_payload.panel_geometry,
                    sampled_palette_rgb=scene_payload.sampled_palette_rgb,
                ),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {
                    "anchor_a": dict(scene_payload.anchor_instances[0]),
                    "anchor_b": dict(scene_payload.anchor_instances[1]),
                    "matching_scene_boxes": list(annotation_artifacts["annotation_value"]),
                },
            },
            "execution_trace": {
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "query_id_probabilities": dict(query_probabilities),
                "scene_variant": "scene_two_anchors_strip",
                "question_format": "count_scene_icon_centers_in_strip_between_two_anchors",
                "strip_axis": str(strip_axis),
                "object_count": int(scene_payload.object_count),
                "object_count_probabilities": dict(object_count_probabilities),
                "target_count": int(scene_payload.target_count),
                "target_count_probabilities": dict(target_count_probabilities),
                "distractor_count": int(scene_payload.distractor_count),
                "distractor_count_probabilities": dict(distractor_count_probabilities),
                "distractor_margin_over_target": int(distractor_margin_over_target),
                "anchor_icon_id": str(scene_payload.anchor_icon_id),
                "anchor_tint_rgb": list(scene_payload.anchor_tint_rgb),
                "anchor_rotation_degrees": int(scene_payload.anchor_rotation_degrees),
                "anchor_a_center_xy": [float(scene_payload.anchor_a_center_xy[0]), float(scene_payload.anchor_a_center_xy[1])],
                "anchor_b_center_xy": [float(scene_payload.anchor_b_center_xy[0]), float(scene_payload.anchor_b_center_xy[1])],
                "scene_icon_ids": list(scene_payload.scene_icon_ids),
                "scene_tints_rgb": [list(color) for color in scene_payload.scene_tints_rgb],
                "scene_rotations_degrees": [int(value) for value in scene_payload.scene_rotations_degrees],
                "matching_scene_indices": [int(value) for value in scene_payload.matching_scene_indices],
                "strip_boundary_margin_px": int(scene_payload.strip_boundary_margin_px),
            },
            "witness_symbolic": {
                "query_id": str(query_id),
                "strip_axis": str(strip_axis),
                "anchor_a_center_xy": [float(scene_payload.anchor_a_center_xy[0]), float(scene_payload.anchor_a_center_xy[1])],
                "anchor_b_center_xy": [float(scene_payload.anchor_b_center_xy[0]), float(scene_payload.anchor_b_center_xy[1])],
                "matching_scene_indices": [int(value) for value in scene_payload.matching_scene_indices],
                "strip_boundary_margin_px": int(scene_payload.strip_boundary_margin_px),
            },
            "projected_annotation": dict(annotation_artifacts["projected_annotation"]),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
        )


__all__ = ["IconsTwoAnchorBetweenAnchorsCountTask"]
