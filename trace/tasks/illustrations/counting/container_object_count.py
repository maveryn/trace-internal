"""Count indoor objects inside a named container."""

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
from ..shared.indoor_task_common import (
    INDOOR_CONTAINER_TYPES,
    INDOOR_OBJECT_TYPES,
    INDOOR_SURFACE_TYPES,
    IndoorObjectSpec,
    container_bbox_map,
    container_interior_bbox_map,
    furniture_bbox_map,
    indoor_scene_entities,
    indoor_setting_name,
    placement_map,
    render_indoor_scene_from_specs,
    serialize_indoor_scene,
    sort_bboxes_by_ids,
    surface_bbox_map,
    surface_support_bbox_map,
    theme_support,
    typed_support,
    uniform_string_probability_map,
)


TASK_ID = "task_illustrations__indoor_room__container_object_count"
SCENE_ID = "indoor_room"
QUERY_ID = "container_object_count"


@dataclass(frozen=True)
class _Defaults:
    object_count_min: int = 8
    object_count_max: int = 12
    target_count_min: int = 0
    target_count_max: int = 4
    canvas_width: int = 1280
    canvas_height: int = 840
    object_size_min_px: int = 50
    object_size_max_px: int = 82
    render_scale: int = 2


@dataclass(frozen=True)
class _SampleSpec:
    theme_id: str
    container_type: str
    target_count: int
    object_count: int
    specs: Tuple[IndoorObjectSpec, ...]
    theme_probabilities: Dict[str, float]
    container_type_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    object_count_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _bounds(params: Mapping[str, Any], low_key: str, high_key: str, fallback_low: int, fallback_high: int) -> Tuple[int, int]:
    low = int(params.get(low_key, group_default(_GEN_DEFAULTS, low_key, fallback_low)))
    high = int(params.get(high_key, group_default(_GEN_DEFAULTS, high_key, fallback_high)))
    if low < 0 or high < low:
        raise ValueError(f"invalid {low_key}/{high_key} bounds")
    return int(low), int(high)




def _sample_string(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    support: Sequence[str],
    explicit_key: str,
    cycle_index: int | None = None,
) -> Tuple[str, Dict[str, float]]:
    values = tuple(str(value) for value in support)
    if not values:
        raise ValueError(f"{explicit_key} has no feasible support")
    explicit = params.get(explicit_key)
    if explicit is not None:
        value = str(explicit)
        if value not in set(values):
            raise ValueError(f"{explicit_key} must be one of {values}")
        return value, uniform_string_probability_map(values, selected=value)
    index = (
        int(cycle_index)
        if cycle_index is not None
        else resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=namespace)
    )
    value = str(values[int(index) % len(values)])
    return value, uniform_string_probability_map(values)


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int) -> _SampleSpec:
    container_support = typed_support(
        params,
        _GEN_DEFAULTS,
        param_key="container_type_support",
        default_key="container_type_support",
        fallback=INDOOR_CONTAINER_TYPES,
        error_name="container_type_support",
    )
    base_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:cycle:2")
    target_min, target_max = _bounds(params, "target_count_min", "target_count_max", _DEFAULTS.target_count_min, _DEFAULTS.target_count_max)
    target_support_len = int(target_max) - int(target_min) + 1
    container_support_len = len(container_support)
    theme_support_values = theme_support(params, _GEN_DEFAULTS)
    theme_id, theme_probabilities = _sample_string(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:theme",
        support=theme_support_values,
        explicit_key="theme_id",
        cycle_index=int(base_index) // max(1, target_support_len * container_support_len),
    )
    container_type, container_probabilities = _sample_string(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:container",
        support=container_support,
        explicit_key="container_type",
        cycle_index=int(base_index) // max(1, target_support_len),
    )
    target_count, target_probabilities = _shared_sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:target_count:balanced",
        low=int(target_min),
        high=int(target_max),
        explicit_key="target_count",
        cycle_index=int(base_index),
    )
    object_min, object_max = _bounds(params, "object_count_min", "object_count_max", _DEFAULTS.object_count_min, _DEFAULTS.object_count_max)
    object_low = max(int(object_min), int(target_count) + 2)
    object_count, object_probabilities = _shared_sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:object_count",
        low=int(object_low),
        high=int(object_max),
        explicit_key="object_count",
        cycle_index=int(base_index) // max(1, target_support_len),
    )
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:spec", int(attempt_index))
    specs = [
        IndoorObjectSpec(str(rng.choice(INDOOR_OBJECT_TYPES)), "container", str(container_type), "target")
        for _ in range(int(target_count))
    ]
    distractor_containers = tuple(value for value in INDOOR_CONTAINER_TYPES if str(value) != str(container_type))
    distractor_targets = [("container", target) for target in distractor_containers] + [
        ("surface", target) for target in INDOOR_SURFACE_TYPES
    ]
    for _ in range(int(object_count) - int(target_count)):
        placement_kind, target_type = rng.choice(tuple(distractor_targets))
        specs.append(IndoorObjectSpec(str(rng.choice(INDOOR_OBJECT_TYPES)), str(placement_kind), str(target_type), "distractor"))
    rng.shuffle(specs)
    return _SampleSpec(
        theme_id=str(theme_id),
        container_type=str(container_type),
        target_count=int(target_count),
        object_count=int(object_count),
        specs=tuple(specs),
        theme_probabilities=dict(theme_probabilities),
        container_type_probabilities=dict(container_probabilities),
        target_count_probabilities=dict(target_probabilities),
        object_count_probabilities=dict(object_probabilities),
    )


def _build_complexity(sample: _SampleSpec) -> TaskComplexity:
    visual_scan = (int(sample.object_count) - _DEFAULTS.object_count_min) / max(1, _DEFAULTS.object_count_max - _DEFAULTS.object_count_min)
    answer_load = (int(sample.target_count) - _DEFAULTS.target_count_min) / max(1, _DEFAULTS.target_count_max - _DEFAULTS.target_count_min)
    container_load = {"basket": 0.75, "box": 0.7, "drawer": 0.85}.get(str(sample.container_type), 0.75)
    score = 0.45 * max(0.0, min(1.0, visual_scan)) + 0.35 * max(0.0, min(1.0, answer_load)) + 0.20 * container_load
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "visual_scan": round(float(visual_scan), 6),
            "answer_load": round(float(answer_load), 6),
            "container_load": round(float(container_load), 6),
            "object_count": int(sample.object_count),
            "target_count": int(sample.target_count),
            "container_type": str(sample.container_type),
        },
    )


@register_task
class IllustrationsCountingContainerObjectCountTask:
    """Count objects inside a named indoor container."""

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
                render_params = dict(params)
                render_params["highlight_container_type"] = str(sample.container_type)
                scene = render_indoor_scene_from_specs(
                    task_id=TASK_ID,
                    instance_seed=int(instance_seed),
                    attempt_index=int(attempt),
                    specs=sample.specs,
                    theme_id=str(sample.theme_id),
                    params=render_params,
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
            if str(placement.container_type) == str(sample.container_type)
        )
        if len(counted_ids) != int(sample.target_count):
            raise RuntimeError("rendered container count did not match sample target")
        evidence_value = sort_bboxes_by_ids(object_bboxes, counted_ids)
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_container_object",
                "evidence_hint_container_object",
                "json_example_container_object",
                "json_example_answer_only_container_object",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        slots = {
            "object_count": int(sample.object_count),
            "room_setting": indoor_setting_name(str(scene.theme_id)),
            "container_name": str(sample.container_type),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_container_object"]).format(container_name=str(sample.container_type)),
            "evidence_hint": str(prompt_defaults["evidence_hint_container_object"]).format(container_name=str(sample.container_type)),
            "json_example": str(prompt_defaults["json_example_container_object"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_container_object"]),
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
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            preferred_mode="answer_and_evidence",
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        trace_payload = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "entities": indoor_scene_entities(scene),
                "relations": {"query_id": "default", "query_id": QUERY_ID, "container_type": str(sample.container_type)},
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
                    "container_type": str(sample.container_type),
                    "container_name": str(sample.container_type),
                    "target_count": int(sample.target_count),
                    "object_count": int(sample.object_count),
                    "theme_probabilities": dict(sample.theme_probabilities),
                    "container_type_probabilities": dict(sample.container_type_probabilities),
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
                    "highlight_container_type": str(sample.container_type),
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
                "container_type": str(sample.container_type),
                "container_name": str(sample.container_type),
                "target_count": int(sample.target_count),
                "object_count": int(sample.object_count),
                "counted_object_ids": list(counted_ids),
                "object_types": {str(obj["object_id"]): str(obj["object_type"]) for obj in serialized_objects},
            },
            "witness_symbolic": {
                "counted_object_ids": list(counted_ids),
                "container_type": str(sample.container_type),
                "answer": int(sample.target_count),
            },
            "projected_evidence": {"bbox_set": list(evidence_value)},
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="integer", value=int(sample.target_count)),
            evidence_gt=TypedValue(type="bbox_set", value=list(evidence_value)),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(sample),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
        )


__all__ = ["IllustrationsCountingContainerObjectCountTask"]
