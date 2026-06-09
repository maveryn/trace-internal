"""Count indoor objects of a named type on a named surface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.task_support import sample_count as _shared_sample_count
from ..shared.task_support import bounds as _shared_bounds
from ..shared.indoor_task_common import (
    INDOOR_CONTAINER_TYPES,
    INDOOR_OBJECT_TYPES,
    INDOOR_SURFACE_TYPES,
    IndoorObjectSpec,
    container_bbox_map,
    container_interior_bbox_map,
    display_name,
    furniture_bbox_map,
    indoor_scene_entities,
    indoor_setting_name,
    placement_map,
    render_indoor_scene_from_specs,
    serialize_indoor_scene,
    sort_bboxes_by_ids,
    support_choice,
    surface_bbox_map,
    surface_support_bbox_map,
    theme_support,
    typed_support,
)


TASK_ID = "task_illustrations__indoor_room__surface_object_count"
SCENE_ID = "indoor_room"
QUERY_ID = "object_type_on_surface_count"


@dataclass(frozen=True)
class _Defaults:
    object_count_min: int = 10
    object_count_max: int = 16
    target_count_min: int = 1
    target_count_max: int = 6
    canvas_width: int = 1280
    canvas_height: int = 840
    object_size_min_px: int = 52
    object_size_max_px: int = 86
    render_scale: int = 2


@dataclass(frozen=True)
class _SampleSpec:
    theme_id: str
    surface_type: str
    object_type: str
    object_name: str
    target_count: int
    object_count: int
    specs: Tuple[IndoorObjectSpec, ...]
    theme_probabilities: Dict[str, float]
    surface_type_probabilities: Dict[str, float]
    object_type_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    object_count_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)






def _sample_spec(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int) -> _SampleSpec:
    object_support = typed_support(
        params,
        _GEN_DEFAULTS,
        param_key="object_type_support",
        default_key="indoor_object_type_support",
        fallback=INDOOR_OBJECT_TYPES,
        error_name="object_type_support",
    )
    surface_support = typed_support(
        params,
        _GEN_DEFAULTS,
        param_key="surface_type_support",
        default_key="surface_type_support",
        fallback=INDOOR_SURFACE_TYPES,
        error_name="surface_type_support",
    )
    theme_id, theme_probabilities = support_choice(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:theme",
        support=theme_support(params, _GEN_DEFAULTS),
        explicit_key="theme_id",
    )
    surface_type, surface_probabilities = support_choice(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:surface",
        support=surface_support,
        explicit_key="surface_type",
    )
    object_type, object_type_probabilities = support_choice(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:object_type",
        support=object_support,
        explicit_key="object_type",
    )
    target_min, target_max = _shared_bounds(params, _GEN_DEFAULTS, "target_count_min", "target_count_max", _DEFAULTS.target_count_min, _DEFAULTS.target_count_max)
    target_count, target_probabilities = _shared_sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:target_count",
        low=int(target_min),
        high=int(target_max),
        explicit_key="target_count",
    )
    object_min, object_max = _shared_bounds(params, _GEN_DEFAULTS, "object_count_min", "object_count_max", _DEFAULTS.object_count_min, _DEFAULTS.object_count_max)
    object_low = max(int(object_min), int(target_count) + 4)
    object_count, object_count_probabilities = _shared_sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:object_count",
        low=int(object_low),
        high=int(object_max),
        explicit_key="object_count",
    )
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:spec", int(attempt_index))
    specs = [
        IndoorObjectSpec(str(object_type), "surface", str(surface_type), "target")
        for _ in range(int(target_count))
    ]
    non_target_types = tuple(value for value in object_support if str(value) != str(object_type)) or tuple(
        value for value in INDOOR_OBJECT_TYPES if str(value) != str(object_type)
    )
    other_surfaces = tuple(value for value in INDOOR_SURFACE_TYPES if str(value) != str(surface_type))
    distractor_kinds = [
        ("same_type_other_surface", max(1, min(2, int(object_count) - int(target_count)))),
        ("other_type_target_surface", max(1, min(3, int(object_count) - int(target_count)))),
    ]
    for kind, count in distractor_kinds:
        for _ in range(int(count)):
            if len(specs) >= int(object_count):
                break
            if kind == "same_type_other_surface":
                specs.append(IndoorObjectSpec(str(object_type), "surface", str(rng.choice(other_surfaces)), "distractor"))
            else:
                specs.append(IndoorObjectSpec(str(rng.choice(non_target_types)), "surface", str(surface_type), "distractor"))
    while len(specs) < int(object_count):
        placement_kind = str(rng.choice(("surface", "container")))
        if placement_kind == "surface":
            target = str(rng.choice(other_surfaces))
        else:
            target = str(rng.choice(INDOOR_CONTAINER_TYPES))
        specs.append(IndoorObjectSpec(str(rng.choice(non_target_types)), placement_kind, target, "distractor"))
    rng.shuffle(specs)
    return _SampleSpec(
        theme_id=str(theme_id),
        surface_type=str(surface_type),
        object_type=str(object_type),
        object_name=display_name(str(object_type)),
        target_count=int(target_count),
        object_count=int(object_count),
        specs=tuple(specs),
        theme_probabilities=dict(theme_probabilities),
        surface_type_probabilities=dict(surface_probabilities),
        object_type_probabilities=dict(object_type_probabilities),
        target_count_probabilities=dict(target_probabilities),
        object_count_probabilities=dict(object_count_probabilities),
    )


def _build_complexity(sample: _SampleSpec) -> TaskComplexity:
    visual_scan = (int(sample.object_count) - _DEFAULTS.object_count_min) / max(1, _DEFAULTS.object_count_max - _DEFAULTS.object_count_min)
    answer_load = (int(sample.target_count) - _DEFAULTS.target_count_min) / max(1, _DEFAULTS.target_count_max - _DEFAULTS.target_count_min)
    compound_query_load = 0.9
    score = 0.42 * max(0.0, min(1.0, visual_scan)) + 0.33 * max(0.0, min(1.0, answer_load)) + 0.25 * compound_query_load
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "visual_scan": round(float(visual_scan), 6),
            "answer_load": round(float(answer_load), 6),
            "compound_query_load": round(float(compound_query_load), 6),
        },
    )


@register_task
class IllustrationsCountingObjectTypeOnSurfaceCountTask:
    """Count objects of one type on a named indoor surface."""

    task_id = TASK_ID
    domain = "illustrations"
    task_group = "counting"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        sample: _SampleSpec | None = None
        scene = None
        fallback = {
            "canvas_width": _DEFAULTS.canvas_width,
            "canvas_height": _DEFAULTS.canvas_height,
            "object_size_min_px": _DEFAULTS.object_size_min_px,
            "object_size_max_px": _DEFAULTS.object_size_max_px,
            "render_scale": _DEFAULTS.render_scale,
        }
        for attempt in range(max(1, int(max_attempts))):
            try:
                sample = _sample_spec(instance_seed=int(instance_seed), params=params, attempt_index=int(attempt))
                scene = render_indoor_scene_from_specs(
                    task_id=TASK_ID,
                    instance_seed=int(instance_seed),
                    attempt_index=int(attempt),
                    specs=sample.specs,
                    theme_id=str(sample.theme_id),
                    params=params,
                    render_defaults=_RENDER_DEFAULTS,
                    fallback=fallback,
                )
                break
            except Exception as exc:  # pragma: no cover
                last_error = exc
                sample = None
                scene = None
        if scene is None or sample is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        serialized_objects, object_bboxes, part_bboxes = serialize_indoor_scene(scene)
        counted_ids = tuple(
            str(placement.object_id)
            for placement in scene.placements
            if str(placement.surface_type) == str(sample.surface_type)
            and str(placement.object_type) == str(sample.object_type)
        )
        if len(counted_ids) != int(sample.target_count):
            raise RuntimeError("rendered type-on-surface count did not match sample target")
        annotation_value = sort_bboxes_by_ids(object_bboxes, counted_ids)
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_object_type_on_surface",
                "annotation_hint_object_type_on_surface",
                "json_example_object_type_on_surface",
                "json_example_answer_only_object_type_on_surface",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        slots = {
            "object_count": int(sample.object_count),
            "room_setting": indoor_setting_name(str(scene.theme_id)),
            "object_name": str(sample.object_name),
            "surface_name": str(sample.surface_type),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_object_type_on_surface"]).format(
                object_name=str(sample.object_name),
                surface_name=str(sample.surface_type),
            ),
            "annotation_hint": str(prompt_defaults["annotation_hint_object_type_on_surface"]).format(
                object_name=str(sample.object_name),
                surface_name=str(sample.surface_type),
            ),
            "json_example": str(prompt_defaults["json_example_object_type_on_surface"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_object_type_on_surface"]),
        }
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=QUERY_ID,
            slots=slots,
            instance_seed=int(instance_seed),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            preferred_mode="answer_and_annotation",
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        trace_payload = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "entities": indoor_scene_entities(scene),
                "relations": {
                    "query_id": QUERY_ID,
                    "surface_type": str(sample.surface_type),
                    "object_type": str(sample.object_type),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_id": QUERY_ID,
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "theme": str(sample.theme_id),
                    "theme_id": str(sample.theme_id),
                    "surface_type": str(sample.surface_type),
                    "surface_name": str(sample.surface_type),
                    "object_type": str(sample.object_type),
                    "object_name": str(sample.object_name),
                    "target_count": int(sample.target_count),
                    "object_count": int(sample.object_count),
                    "theme_probabilities": dict(sample.theme_probabilities),
                    "surface_type_probabilities": dict(sample.surface_type_probabilities),
                    "object_type_probabilities": dict(sample.object_type_probabilities),
                    "target_count_probabilities": dict(sample.target_count_probabilities),
                    "object_count_probabilities": dict(sample.object_count_probabilities),
                },
            },
            "render_spec": {
                "canvas_size": [int(scene.canvas_width), int(scene.canvas_height)],
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "style": {
                    "theme_id": str(scene.theme_id),
                    "style_id": str(scene.style_id),
                    "render_scale": int(scene.render_scale),
                },
            },
            "render_map": {
                "image_id": "img0",
                "object_bboxes_px": object_bboxes,
                "part_bboxes_px": part_bboxes,
                "surface_bboxes_px": surface_bbox_map(scene),
                "surface_support_bboxes_px": surface_support_bbox_map(scene),
                "container_bboxes_px": container_bbox_map(scene),
                "container_interior_bboxes_px": container_interior_bbox_map(scene),
                "furniture_bboxes_px": furniture_bbox_map(scene),
                "placements": placement_map(scene),
                "counted_object_ids": list(counted_ids),
            },
            "execution_trace": {
                "query_id": QUERY_ID,
                "scene_id": SCENE_ID,
                "theme_id": str(scene.theme_id),
                "theme": str(scene.theme_id),
                "surface_type": str(sample.surface_type),
                "object_type": str(sample.object_type),
                "object_name": str(sample.object_name),
                "target_count": int(sample.target_count),
                "object_count": int(sample.object_count),
                "counted_object_ids": list(counted_ids),
                "object_types": {str(obj["object_id"]): str(obj["object_type"]) for obj in serialized_objects},
            },
            "witness_symbolic": {
                "counted_object_ids": list(counted_ids),
                "surface_type": str(sample.surface_type),
                "object_type": str(sample.object_type),
                "answer": int(sample.target_count),
            },
            "projected_annotation": {"bbox_set": list(annotation_value)},
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="integer", value=int(sample.target_count)),
            annotation_gt=TypedValue(type="bbox_set", value=list(annotation_value)),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(sample),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
        )


__all__ = ["IllustrationsCountingObjectTypeOnSurfaceCountTask"]
