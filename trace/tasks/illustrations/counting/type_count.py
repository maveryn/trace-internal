"""Count objects of one named type in a mixed illustration scene."""

from __future__ import annotations

from collections import Counter
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
from ..shared.task_support import uniform_string_probability_map as _uniform_string_probability_map
from ..shared.task_support import bounds as _shared_bounds
from ..shared.mixed_task_common import (
    MIXED_QUERY_OBJECT_TYPES,
    display_name_for_object_type,
    render_mixed_scene_from_types,
    scene_entities,
    serialize_mixed_scene,
    sort_object_bboxes,
)


TASK_ID = "task_illustrations__object_field__object_type_count"
SCENE_ID = "object_field"
QUERY_ID = "type_count"


@dataclass(frozen=True)
class _Defaults:
    object_count_min: int = 11
    object_count_max: int = 20
    target_count_min: int = 1
    target_count_max: int = 10
    canvas_width: int = 1280
    canvas_height: int = 840
    outer_margin_px: int = 42
    object_size_min_px: int = 74
    object_size_max_px: int = 128
    object_min_gap_px: int = 8
    max_overlap_fraction: float = 0.02
    placement_max_attempts: int = 180
    render_scale: int = 2


@dataclass(frozen=True)
class _SampleSpec:
    object_type: str
    object_name: str
    target_count: int
    object_count: int
    object_types: Tuple[str, ...]
    object_type_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    object_count_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _object_type_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("object_type_support", group_default(_GEN_DEFAULTS, "object_type_support", MIXED_QUERY_OBJECT_TYPES))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("object_type_support must be a sequence")
    supported = tuple(str(value) for value in raw if str(value) in set(MIXED_QUERY_OBJECT_TYPES))
    if not supported:
        raise ValueError("object_type_support resolved no supported object types")
    return tuple(dict.fromkeys(supported))






def _sample_spec(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int) -> _SampleSpec:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:sample", int(attempt_index))
    object_support = _object_type_support(params)
    object_min, object_max = _shared_bounds(params, _GEN_DEFAULTS, "object_count_min", "object_count_max", _DEFAULTS.object_count_min, _DEFAULTS.object_count_max)
    target_min, target_max = _shared_bounds(params, _GEN_DEFAULTS, "target_count_min", "target_count_max", _DEFAULTS.target_count_min, _DEFAULTS.target_count_max)
    selection_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:query")

    explicit_object_type = params.get("object_type")
    if explicit_object_type is not None:
        object_type = str(explicit_object_type)
        if object_type not in set(object_support):
            raise ValueError(f"object_type must be one of {object_support}")
    else:
        object_type = str(object_support[int(selection_index) % len(object_support)])

    target_support = tuple(range(int(target_min), int(target_max) + 1))
    explicit_target = params.get("target_count")
    if explicit_target is not None:
        target_count = int(explicit_target)
        if target_count not in set(target_support):
            raise ValueError("target_count is outside configured support")
    else:
        target_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:target_count")
        target_count = int(target_support[int(target_index) % len(target_support)])

    min_object_count = max(int(object_min), int(target_count) + 2)
    object_count_support = tuple(range(int(min_object_count), int(object_max) + 1))
    if not object_count_support:
        raise ValueError("object_count range leaves no room for type-count distractors")
    explicit_object_count = params.get("object_count")
    if explicit_object_count is not None:
        object_count = int(explicit_object_count)
        if object_count not in set(object_count_support):
            raise ValueError("object_count is outside feasible support")
    else:
        count_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:object_count")
        object_count = int(object_count_support[int(count_index) % len(object_count_support)])

    distractor_pool = [value for value in object_support if str(value) != str(object_type)]
    if len(distractor_pool) < 2:
        raise ValueError("type-count task needs at least two distractor object types")
    object_types_for_scene = [str(object_type)] * int(target_count)
    for _ in range(int(object_count) - int(target_count)):
        object_types_for_scene.append(str(rng.choice(tuple(distractor_pool))))
    rng.shuffle(object_types_for_scene)
    return _SampleSpec(
        object_type=str(object_type),
        object_name=display_name_for_object_type(str(object_type)),
        target_count=int(target_count),
        object_count=int(object_count),
        object_types=tuple(object_types_for_scene),
        object_type_probabilities=_uniform_string_probability_map(object_support, selected=str(object_type) if explicit_object_type is not None else None),
        target_count_probabilities=dict(uniform_probability_map(target_support, selected=int(target_count) if explicit_target is not None else None)),
        object_count_probabilities=dict(uniform_probability_map(object_count_support, selected=int(object_count) if explicit_object_count is not None else None)),
    )


def _build_complexity(sample: _SampleSpec) -> TaskComplexity:
    visual_scan = (int(sample.object_count) - _DEFAULTS.object_count_min) / max(1, _DEFAULTS.object_count_max - _DEFAULTS.object_count_min)
    answer_load = (int(sample.target_count) - _DEFAULTS.target_count_min) / max(1, _DEFAULTS.target_count_max - _DEFAULTS.target_count_min)
    type_diversity = len(set(sample.object_types)) / max(1.0, float(sample.object_count))
    score = 0.45 * max(0.0, min(1.0, visual_scan)) + 0.35 * max(0.0, min(1.0, answer_load)) + 0.20 * max(0.0, min(1.0, type_diversity))
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "visual_scan": round(float(visual_scan), 6),
            "answer_load": round(float(answer_load), 6),
            "type_diversity": round(float(type_diversity), 6),
            "object_count": int(sample.object_count),
            "target_count": int(sample.target_count),
            "object_type": str(sample.object_type),
        },
    )


@register_task
class IllustrationsCountingTypeCountTask:
    """Count objects of one named type in a mixed illustration."""

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
            "outer_margin_px": _DEFAULTS.outer_margin_px,
            "object_size_min_px": _DEFAULTS.object_size_min_px,
            "object_size_max_px": _DEFAULTS.object_size_max_px,
            "object_min_gap_px": _DEFAULTS.object_min_gap_px,
            "max_overlap_fraction": _DEFAULTS.max_overlap_fraction,
            "placement_max_attempts": _DEFAULTS.placement_max_attempts,
            "render_scale": _DEFAULTS.render_scale,
        }
        for attempt in range(max(1, int(max_attempts))):
            try:
                sample = _sample_spec(instance_seed=int(instance_seed), params=params, attempt_index=int(attempt))
                scene = render_mixed_scene_from_types(
                    task_id=TASK_ID,
                    instance_seed=int(instance_seed),
                    attempt_index=int(attempt),
                    object_types_for_scene=sample.object_types,
                    params=params,
                    render_defaults=_RENDER_DEFAULTS,
                    fallback=fallback,
                )
                break
            except Exception as exc:  # pragma: no cover - retry behavior exercised by smoke tests.
                last_error = exc
                sample = None
                scene = None
        if scene is None or sample is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        serialized_objects, object_bboxes, part_bboxes = serialize_mixed_scene(scene)
        counted_ids = tuple(str(obj["object_id"]) for obj in serialized_objects if str(obj["object_type"]) == str(sample.object_type))
        if len(counted_ids) != int(sample.target_count):
            raise RuntimeError("rendered type count did not match sample target")
        evidence_value = sort_object_bboxes(object_bboxes, counted_ids)

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_type_count",
                "evidence_hint_type_count",
                "json_example_type_count",
                "json_example_answer_only_type_count",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        slots = {
            "object_count": int(sample.object_count),
            "object_name": str(sample.object_name),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_type_count"]).format(object_name=str(sample.object_name)),
            "evidence_hint": str(prompt_defaults["evidence_hint_type_count"]).format(object_name=str(sample.object_name)),
            "json_example": str(prompt_defaults["json_example_type_count"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_type_count"]),
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
                "entities": scene_entities(scene),
                "relations": {"query_id": "default", "query_id": QUERY_ID, "object_type": str(sample.object_type)},
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_id": QUERY_ID,
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "object_type": str(sample.object_type),
                    "object_name": str(sample.object_name),
                    "target_count": int(sample.target_count),
                    "object_count": int(sample.object_count),
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
                    "background_id": str(scene.background_id),
                    "background_layout": dict(scene.background_layout),
                    "style_ids": [str(placement.style_id) for placement in scene.placements],
                    "render_scale": int(scene.render_scale),
                    "content_bbox": [round(float(v), 3) for v in scene.content_bbox],
                },
            },
            "render_map": {
                "image_id": "img0",
                "object_bboxes_px": object_bboxes,
                "part_bboxes_px": part_bboxes,
                "counted_object_ids": list(counted_ids),
            },
            "execution_trace": {
                "query_id": QUERY_ID,
                "scene_id": SCENE_ID,
                "object_type": str(sample.object_type),
                "object_name": str(sample.object_name),
                "target_count": int(sample.target_count),
                "object_count": int(sample.object_count),
                "object_type_counts": dict(Counter(sample.object_types)),
                "counted_object_ids": list(counted_ids),
                "background_id": str(scene.background_id),
            },
            "witness_symbolic": {
                "counted_object_ids": list(counted_ids),
                "object_type": str(sample.object_type),
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


__all__ = ["IllustrationsCountingTypeCountTask"]
