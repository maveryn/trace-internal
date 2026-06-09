"""Count all objects in a dense synthetic 3D object cluster."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from ....core.seed import spawn_rng
from ....core.task_group_config import (
    get_domain_defaults,
    get_task_group_defaults,
    resolve_task_group_section_defaults,
)
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.object_scene import _resolve_render_params, render_object_scene_3d
from ..shared.task_support import resolve_axis_variant as _shared_resolve_axis_variant
from .object_cluster_instance_count import (
    COUNTABLE_SHAPE_TYPES,
    SCENE_ID,
    SUPPORTED_SCENE_VARIANTS,
    _build_cluster_dataset,
    _build_complexity,
    _configured_int,
    _count_bounds,
    _object_plural,
    _resolve_weighted_count,
    _uniform_string_probability_map,
)
from ..shared.object_resources import OBJECT_CLUSTER_NAME_BY_SHAPE_TYPE


TASK_ID = "task_three_d__object_cluster__total_object_count"
SUPPORTED_QUERY_IDS = ("total_object_count",)
COMPOSITION_MODE = "single_type_cluster"


def _resolve_total_object_count(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
) -> tuple[int, Dict[str, float]]:
    minimum, maximum = _count_bounds(
        params=params,
        gen_defaults=gen_defaults,
        minimum_key="object_count_min",
        maximum_key="object_count_max",
        fallback_minimum=_configured_int(params, gen_defaults, "single_type_count_min", 6),
        fallback_maximum=_configured_int(params, gen_defaults, "single_type_count_max", 25),
        lower=6,
        upper=25,
    )
    return _resolve_weighted_count(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        explicit_key="object_count",
        weights_key="object_count_weights",
        minimum=int(minimum),
        maximum=int(maximum),
        namespace=f"{TASK_ID}.object_count",
    )


def _resolve_primary_shape(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
) -> tuple[str, Dict[str, float]]:
    shape_support = tuple(str(shape) for shape in COUNTABLE_SHAPE_TYPES)
    explicit_shape = params.get("primary_shape_type", params.get("target_shape_type"))
    if explicit_shape is not None:
        primary_shape_type = str(explicit_shape)
        if primary_shape_type not in set(shape_support):
            raise ValueError(f"unsupported primary_shape_type: {primary_shape_type}")
    else:
        shape_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.primary_shape_type",
        )
        primary_shape_type = str(shape_support[abs(int(shape_index)) % len(shape_support)])
    return primary_shape_type, _uniform_string_probability_map(
        shape_support,
        selected=str(primary_shape_type) if explicit_shape is not None else None,
    )


def _build_total_complexity(
    *,
    object_count: int,
    scene_variant: str,
    complexity_defaults: Mapping[str, Any],
) -> TaskComplexity:
    return _build_complexity(
        object_count=int(object_count),
        target_count=int(object_count),
        distractor_count=0,
        scene_variant=str(scene_variant),
        composition_mode=COMPOSITION_MODE,
        complexity_defaults=complexity_defaults,
    )


_TASK_GROUP_DEFAULTS = get_task_group_defaults("three_d", "spatial")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_DEFAULTS = resolve_task_group_section_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    "complexity",
    task_id=TASK_ID,
)
_DOMAIN_DEFAULTS = get_domain_defaults("three_d")
_VISUAL_DEFAULTS = _DOMAIN_DEFAULTS.get("visual", {}) if isinstance(_DOMAIN_DEFAULTS, Mapping) else {}
_BACKGROUND_DEFAULTS = _VISUAL_DEFAULTS.get("background", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}
_NOISE_DEFAULTS = _VISUAL_DEFAULTS.get("noise", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}


@register_task
class ThreeDObjectClusterTotalObjectCountTask:
    """Count every visible object in a homogeneous dense object cluster."""

    task_id = TASK_ID
    domain = "three_d"
    task_group = "spatial"
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
        object_count, object_count_probabilities = _resolve_total_object_count(
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        primary_shape_type, primary_shape_probabilities = _resolve_primary_shape(
            params=params,
            instance_seed=int(instance_seed),
        )

        render_params = _resolve_render_params(params, render_defaults=_RENDER_DEFAULTS)
        dataset = _build_cluster_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            composition_mode=COMPOSITION_MODE,
            target_shape_type=str(primary_shape_type),
            target_count=int(object_count),
            object_count=int(object_count),
            render_params=render_params,
            instance_seed=int(instance_seed),
        )
        object_ids = [str(spec["object_id"]) for spec in sorted(dataset["object_specs"], key=lambda item: str(item["object_id"]))]
        primary_object_name = str(
            OBJECT_CLUSTER_NAME_BY_SHAPE_TYPE.get(str(primary_shape_type), str(primary_shape_type).replace("_", " "))
        )

        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=_BACKGROUND_DEFAULTS,
        )
        rendered = render_object_scene_3d(
            background,
            dataset=dataset,
            render_params=render_params,
            draw_candidate_labels=False,
            compute_single_annotation=False,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=_NOISE_DEFAULTS,
        )
        annotation_bboxes = [list(rendered.object_bboxes_px[str(object_id)]) for object_id in object_ids]

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
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_value = int(object_count)
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        annotation_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_bboxes])
        complexity = _build_total_complexity(
            object_count=int(object_count),
            scene_variant=str(scene_variant),
            complexity_defaults=_COMPLEXITY_DEFAULTS,
        )
        solver_trace = dict(dataset["solver_trace"])
        solver_trace.update(
            {
                "count_predicate": "is_countable_object == true",
                "primary_shape_type": str(primary_shape_type),
                "primary_object_name": str(primary_object_name),
                "primary_object_plural": _object_plural(str(primary_object_name)),
                "answer_value": int(answer_value),
                "object_count": int(object_count),
                "target_count": int(object_count),
                "distractor_count": 0,
                "counted_object_ids": list(object_ids),
                "unique_integer_answer": True,
            }
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "three_d_object_cluster_total_count",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "cluster_composition_mode": COMPOSITION_MODE,
                    "object_count": int(object_count),
                    "countable_object_count": int(object_count),
                    "distractor_count": 0,
                    "cluster_object_pool_size": len(COUNTABLE_SHAPE_TYPES),
                    "primary_shape_type": str(primary_shape_type),
                    "primary_object_name": str(primary_object_name),
                    "primary_object_plural": _object_plural(str(primary_object_name)),
                    "counted_object_ids": list(object_ids),
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
                    "composition_mode": COMPOSITION_MODE,
                    "composition_mode_probabilities": {COMPOSITION_MODE: 1.0},
                    "object_count": int(object_count),
                    "object_count_probabilities": dict(object_count_probabilities),
                    "primary_shape_type": str(primary_shape_type),
                    "primary_shape_type_probabilities": dict(primary_shape_probabilities),
                    "cluster_object_pool_size": len(COUNTABLE_SHAPE_TYPES),
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
                "room_extent": float(render_params.room_extent),
                "full_bleed_floor": bool(render_params.full_bleed_floor),
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered.scene_bbox_px),
                "room_bbox_px": list(rendered.room_bbox_px),
                "object_bboxes_px": dict(rendered.object_bboxes_px),
                "object_centers_px": dict(rendered.object_centers_px),
                "counted_object_bboxes_px": {
                    str(object_id): list(rendered.object_bboxes_px[str(object_id)])
                    for object_id in object_ids
                },
                "counted_object_centers_px": {
                    str(object_id): list(rendered.object_centers_px[str(object_id)])
                    for object_id in object_ids
                },
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "cluster_composition_mode": COMPOSITION_MODE,
                "object_count": int(object_count),
                "target_count": int(object_count),
                "distractor_count": 0,
                "answer_value": int(answer_value),
                "primary_shape_type": str(primary_shape_type),
                "primary_object_name": str(primary_object_name),
                "primary_object_plural": _object_plural(str(primary_object_name)),
                "counted_object_ids": list(object_ids),
                "object_specs": [dict(spec) for spec in dataset["object_specs"]],
                "shape_counts": dict(dataset["shape_counts"]),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "question_format": str(query_id),
                "solver_trace": dict(solver_trace),
            },
            "witness_symbolic": {
                "type": "counted_object_set",
                "object_ids": list(object_ids),
                "answer_value": int(answer_value),
            },
            "projected_annotation": {
                "type": "bbox_set",
                "bbox_set": [list(bbox) for bbox in annotation_bboxes],
                "pixel_bbox_set": [list(bbox) for bbox in annotation_bboxes],
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
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
        )


__all__ = ["ThreeDObjectClusterTotalObjectCountTask"]
