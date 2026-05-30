"""Count objects on one side of a uniquely named object."""

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
from ..shared.mixed_task_common import (
    MIXED_QUERY_OBJECT_TYPES,
    display_name_for_object_type,
    relation_side,
    render_mixed_scene_from_types,
    scene_entities,
    serialize_mixed_scene,
    sort_object_bboxes,
)


TASK_ID = "task_illustrations__object_field__named_object_side_count"
SCENE_ID = "object_field"
QUERY_ID = "named_object_side_count"
RELATION_SUPPORT: Tuple[str, ...] = ("left", "right", "above", "below")


@dataclass(frozen=True)
class _Defaults:
    object_count_min: int = 8
    object_count_max: int = 14
    target_count_min: int = 1
    target_count_max: int = 9
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
class _QueryChoice:
    reference_type: str
    reference_name: str
    relation: str
    reference_type_probabilities: Dict[str, float]
    relation_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _SampleSpec:
    query: _QueryChoice
    object_count: int
    object_types: Tuple[str, ...]
    object_count_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "relation")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _object_type_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("reference_type_support", group_default(_GEN_DEFAULTS, "reference_type_support", MIXED_QUERY_OBJECT_TYPES))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("reference_type_support must be a sequence")
    supported = tuple(str(value) for value in raw if str(value) in set(MIXED_QUERY_OBJECT_TYPES))
    if not supported:
        raise ValueError("reference_type_support resolved no supported object types")
    return tuple(dict.fromkeys(supported))


def _relation_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("relation_support", group_default(_GEN_DEFAULTS, "relation_support", RELATION_SUPPORT))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("relation_support must be a sequence")
    supported = tuple(str(value) for value in raw if str(value) in set(RELATION_SUPPORT))
    if not supported:
        raise ValueError("relation_support resolved no supported side relations")
    return tuple(dict.fromkeys(supported))




def _query_choice(*, instance_seed: int, params: Mapping[str, Any]) -> _QueryChoice:
    reference_support = _object_type_support(params)
    relations = _relation_support(params)
    selection_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:query")
    explicit_reference = params.get("reference_type")
    if explicit_reference is not None:
        reference_type = str(explicit_reference)
        if reference_type not in set(reference_support):
            raise ValueError(f"reference_type must be one of {reference_support}")
    else:
        reference_type = str(reference_support[int(selection_index) % len(reference_support)])
    explicit_relation = params.get("relation")
    if explicit_relation is not None:
        relation = str(explicit_relation)
        if relation not in set(relations):
            raise ValueError(f"relation must be one of {relations}")
    else:
        relation_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:relation")
        relation = str(relations[int(relation_index) % len(relations)])
    return _QueryChoice(
        reference_type=str(reference_type),
        reference_name=display_name_for_object_type(str(reference_type)),
        relation=str(relation),
        reference_type_probabilities=_uniform_string_probability_map(reference_support, selected=str(reference_type) if explicit_reference is not None else None),
        relation_probabilities=_uniform_string_probability_map(relations, selected=str(relation) if explicit_relation is not None else None),
    )


def _object_count_bounds(params: Mapping[str, Any]) -> Tuple[int, int]:
    low = int(params.get("object_count_min", group_default(_GEN_DEFAULTS, "object_count_min", _DEFAULTS.object_count_min)))
    high = int(params.get("object_count_max", group_default(_GEN_DEFAULTS, "object_count_max", _DEFAULTS.object_count_max)))
    if low < 4 or high < low:
        raise ValueError("invalid object_count range")
    return int(low), int(high)


def _target_count_bounds(params: Mapping[str, Any]) -> Tuple[int, int]:
    low = int(params.get("target_count_min", group_default(_GEN_DEFAULTS, "target_count_min", _DEFAULTS.target_count_min)))
    high = int(params.get("target_count_max", group_default(_GEN_DEFAULTS, "target_count_max", _DEFAULTS.target_count_max)))
    if low < 0 or high < low:
        raise ValueError("invalid target_count range")
    return int(low), int(high)


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int) -> _SampleSpec:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:sample", int(attempt_index))
    query = _query_choice(instance_seed=int(instance_seed), params=params)
    object_min, object_max = _object_count_bounds(params)
    support = tuple(range(int(object_min), int(object_max) + 1))
    explicit_object_count = params.get("object_count")
    if explicit_object_count is not None:
        object_count = int(explicit_object_count)
        if object_count not in set(support):
            raise ValueError("object_count is outside configured support")
    else:
        selection_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:object_count")
        object_count = int(support[int(selection_index) % len(support)])
    distractor_pool = [value for value in MIXED_QUERY_OBJECT_TYPES if str(value) != str(query.reference_type)]
    object_types_for_scene = [str(query.reference_type)]
    for _ in range(int(object_count) - 1):
        object_types_for_scene.append(str(rng.choice(tuple(distractor_pool))))
    rng.shuffle(object_types_for_scene)
    return _SampleSpec(
        query=query,
        object_count=int(object_count),
        object_types=tuple(object_types_for_scene),
        object_count_probabilities=dict(uniform_probability_map(support, selected=int(object_count) if explicit_object_count is not None else None)),
    )


def _build_complexity(*, object_count: int, target_count: int, relation: str) -> TaskComplexity:
    visual_scan = (int(object_count) - _DEFAULTS.object_count_min) / max(1, _DEFAULTS.object_count_max - _DEFAULTS.object_count_min)
    answer_load = min(1.0, float(target_count) / max(1.0, float(object_count - 1)))
    relation_load = 0.9 if str(relation) in {"above", "below"} else 0.75
    score = 0.45 * max(0.0, min(1.0, visual_scan)) + 0.35 * max(0.0, min(1.0, answer_load)) + 0.20 * relation_load
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "visual_scan": round(float(visual_scan), 6),
            "answer_load": round(float(answer_load), 6),
            "relation_load": round(float(relation_load), 6),
        },
    )


@register_task
class IllustrationsRelationNamedObjectSideCountTask:
    """Count objects left/right/above/below a uniquely named object type."""

    task_id = TASK_ID
    domain = "illustrations"
    task_group = "relation"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        target_min, target_max = _target_count_bounds(params)
        last_error: Exception | None = None
        sample: _SampleSpec | None = None
        scene = None
        counted_ids: Tuple[str, ...] = ()
        reference_id: str | None = None
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
                serialized_objects, object_bboxes, _part_bboxes = serialize_mixed_scene(scene)
                refs = [obj for obj in serialized_objects if str(obj["object_type"]) == str(sample.query.reference_type)]
                if len(refs) != 1:
                    raise ValueError("reference type is not unique after rendering")
                reference_id = str(refs[0]["object_id"])
                reference_bbox = object_bboxes[reference_id]
                counted_ids = tuple(
                    str(obj["object_id"])
                    for obj in serialized_objects
                    if str(obj["object_id"]) != reference_id
                    and relation_side(object_bboxes[str(obj["object_id"])], reference_bbox)[str(sample.query.relation)]
                )
                if int(target_min) <= len(counted_ids) <= int(target_max):
                    break
                raise ValueError(f"target side count {len(counted_ids)} outside {target_min}..{target_max}")
            except Exception as exc:  # pragma: no cover
                last_error = exc
                sample = None
                scene = None
                counted_ids = ()
                reference_id = None
        if scene is None or sample is None or reference_id is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        serialized_objects, object_bboxes, part_bboxes = serialize_mixed_scene(scene)
        evidence_value = sort_object_bboxes(object_bboxes, counted_ids)
        answer = int(len(counted_ids))

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_named_side",
                "evidence_hint_named_side",
                "json_example_named_side",
                "json_example_answer_only_named_side",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        relation_word = {
            "left": "to the left of",
            "right": "to the right of",
            "above": "above",
            "below": "below",
        }.get(str(sample.query.relation), str(sample.query.relation))
        slots = {
            "object_count": int(sample.object_count),
            "reference_object_name": str(sample.query.reference_name),
            "relation_word": str(relation_word),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_named_side"]).format(
                reference_object_name=str(sample.query.reference_name),
                relation_word=str(relation_word),
            ),
            "evidence_hint": str(prompt_defaults["evidence_hint_named_side"]).format(
                reference_object_name=str(sample.query.reference_name),
                relation_word=str(relation_word),
            ),
            "json_example": str(prompt_defaults["json_example_named_side"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_named_side"]),
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
                "relations": {
                    "query_id": QUERY_ID,
                    "reference_object_id": str(reference_id),
                    "reference_type": str(sample.query.reference_type),
                    "relation": str(sample.query.relation),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_id": QUERY_ID,
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "reference_type": str(sample.query.reference_type),
                    "reference_object_name": str(sample.query.reference_name),
                    "reference_object_id": str(reference_id),
                    "relation": str(sample.query.relation),
                    "target_count": int(answer),
                    "object_count": int(sample.object_count),
                    "reference_type_probabilities": dict(sample.query.reference_type_probabilities),
                    "relation_probabilities": dict(sample.query.relation_probabilities),
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
                "reference_object_id": str(reference_id),
                "counted_object_ids": list(counted_ids),
            },
            "execution_trace": {
                "query_id": QUERY_ID,
                "scene_id": SCENE_ID,
                "reference_type": str(sample.query.reference_type),
                "reference_object_name": str(sample.query.reference_name),
                "reference_object_id": str(reference_id),
                "relation": str(sample.query.relation),
                "target_count": int(answer),
                "object_count": int(sample.object_count),
                "object_type_counts": dict(Counter(str(obj["object_type"]) for obj in serialized_objects)),
                "counted_object_ids": list(counted_ids),
                "background_id": str(scene.background_id),
            },
            "witness_symbolic": {
                "reference_object_id": str(reference_id),
                "counted_object_ids": list(counted_ids),
                "relation": str(sample.query.relation),
                "answer": int(answer),
            },
            "projected_evidence": {"bbox_set": list(evidence_value)},
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="integer", value=int(answer)),
            evidence_gt=TypedValue(type="bbox_set", value=list(evidence_value)),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(object_count=int(sample.object_count), target_count=int(answer), relation=str(sample.query.relation)),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
        )


__all__ = ["IllustrationsRelationNamedObjectSideCountTask"]
