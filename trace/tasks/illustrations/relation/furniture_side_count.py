"""Count indoor objects on one side of named furniture."""

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
    INDOOR_FURNITURE_TYPES,
    INDOOR_OBJECT_TYPES,
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


TASK_ID = "task_illustrations__indoor_room__furniture_side_count"
SCENE_ID = "indoor_room"
QUERY_ID = "furniture_side_count"
RELATION_SUPPORT: Tuple[str, ...] = ("left", "right", "above", "below")
OPPOSITE_RELATION: Dict[str, str] = {"left": "right", "right": "left", "above": "below", "below": "above"}
VALID_FURNITURE_RELATION_PAIRS: Tuple[Tuple[str, str], ...] = (
    ("table", "left"),
    ("table", "right"),
    ("table", "above"),
    ("table", "below"),
    ("sofa", "above"),
    ("sofa", "below"),
    ("cabinet", "above"),
    ("cabinet", "below"),
)


@dataclass(frozen=True)
class _Defaults:
    object_count_min: int = 8
    object_count_max: int = 14
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
    furniture_type: str
    relation: str
    object_type: str
    object_name: str
    target_count: int
    object_count: int
    specs: Tuple[IndoorObjectSpec, ...]
    theme_probabilities: Dict[str, float]
    furniture_type_probabilities: Dict[str, float]
    relation_probabilities: Dict[str, float]
    object_type_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    object_count_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "relation")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _decoupled_sampling_params(
    params: Mapping[str, Any],
    *,
    multiplier: int,
    offset: int,
    block_divisor: int = 1,
) -> Mapping[str, Any]:
    """No-op hook for local cycling call sites."""

    _ = int(multiplier), int(offset), int(block_divisor)
    return params






def _choose_furniture_relation(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    furniture_support: Sequence[str],
    relation_support: Sequence[str],
) -> Tuple[str, str, Dict[str, float], Dict[str, float]]:
    explicit_furniture = params.get("furniture_type")
    explicit_relation = params.get("relation")
    furniture_values = tuple(str(value) for value in furniture_support)
    relation_values = tuple(str(value) for value in relation_support)
    pairs = tuple(
        (furniture, relation)
        for furniture, relation in VALID_FURNITURE_RELATION_PAIRS
        if furniture in set(furniture_values) and relation in set(relation_values)
    )
    if explicit_furniture is not None:
        explicit_furniture = str(explicit_furniture)
        if explicit_furniture not in set(furniture_values):
            raise ValueError(f"furniture_type must be one of {furniture_values}")
        pairs = tuple(pair for pair in pairs if pair[0] == explicit_furniture)
    if explicit_relation is not None:
        explicit_relation = str(explicit_relation)
        if explicit_relation not in set(relation_values):
            raise ValueError(f"relation must be one of {relation_values}")
        pairs = tuple(pair for pair in pairs if pair[1] == explicit_relation)
    if not pairs:
        raise ValueError("no feasible furniture/relation pair for indoor relation task")
    if explicit_furniture is not None and explicit_relation is not None:
        furniture_type, relation = str(explicit_furniture), str(explicit_relation)
    else:
        index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:furniture_relation")
        furniture_type, relation = pairs[int(index) % len(pairs)]

    furniture_probabilities: Dict[str, float] = {}
    relation_probabilities: Dict[str, float] = {}
    if explicit_furniture is not None:
        furniture_probabilities[str(furniture_type)] = 1.0
    else:
        for furniture, _relation in pairs:
            furniture_probabilities[str(furniture)] = furniture_probabilities.get(str(furniture), 0.0) + 1.0 / float(len(pairs))
    if explicit_relation is not None:
        relation_probabilities[str(relation)] = 1.0
    else:
        for _furniture, pair_relation in pairs:
            relation_probabilities[str(pair_relation)] = relation_probabilities.get(str(pair_relation), 0.0) + 1.0 / float(len(pairs))
    return str(furniture_type), str(relation), dict(sorted(furniture_probabilities.items())), dict(sorted(relation_probabilities.items()))


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int) -> _SampleSpec:
    furniture_support = typed_support(
        params,
        _GEN_DEFAULTS,
        param_key="furniture_type_support",
        default_key="furniture_type_support",
        fallback=INDOOR_FURNITURE_TYPES,
        error_name="furniture_type_support",
    )
    relation_support = typed_support(
        params,
        _GEN_DEFAULTS,
        param_key="relation_support",
        default_key="relation_support",
        fallback=RELATION_SUPPORT,
        error_name="relation_support",
    )
    object_support = typed_support(
        params,
        _GEN_DEFAULTS,
        param_key="object_type_support",
        default_key="indoor_object_type_support",
        fallback=INDOOR_OBJECT_TYPES,
        error_name="object_type_support",
    )
    theme_id, theme_probabilities = support_choice(
        params=_decoupled_sampling_params(params, multiplier=5, offset=2, block_divisor=4),
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:theme",
        support=theme_support(params, _GEN_DEFAULTS),
        explicit_key="theme_id",
    )
    furniture_type, relation, furniture_probabilities, relation_probabilities = _choose_furniture_relation(
        params=_decoupled_sampling_params(params, multiplier=3, offset=1, block_divisor=6),
        instance_seed=int(instance_seed),
        furniture_support=furniture_support,
        relation_support=relation_support,
    )
    object_type, object_type_probabilities = support_choice(
        params=_decoupled_sampling_params(params, multiplier=7, offset=3, block_divisor=20),
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:object_type",
        support=object_support,
        explicit_key="object_type",
    )
    target_min, target_max = _shared_bounds(params, _GEN_DEFAULTS, "target_count_min", "target_count_max", _DEFAULTS.target_count_min, _DEFAULTS.target_count_max)
    target_count, target_probabilities = _shared_sample_count(
        params=_decoupled_sampling_params(params, multiplier=1, offset=0),
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:target_count",
        low=int(target_min),
        high=int(target_max),
        explicit_key="target_count",
    )
    object_min, object_max = _shared_bounds(params, _GEN_DEFAULTS, "object_count_min", "object_count_max", _DEFAULTS.object_count_min, _DEFAULTS.object_count_max)
    object_low = max(int(object_min), int(target_count) + 4)
    object_count, object_probabilities = _shared_sample_count(
        params=_decoupled_sampling_params(params, multiplier=5, offset=5, block_divisor=6),
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:object_count",
        low=int(object_low),
        high=int(object_max),
        explicit_key="object_count",
    )
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:spec", int(attempt_index))
    target_region = f"{furniture_type}:{relation}"
    distractor_region = f"{furniture_type}:{OPPOSITE_RELATION[str(relation)]}"
    specs = [
        IndoorObjectSpec(str(object_type), "region", str(target_region), "target")
        for _ in range(int(target_count))
    ]
    non_target_types = tuple(value for value in object_support if str(value) != str(object_type)) or tuple(
        value for value in INDOOR_OBJECT_TYPES if str(value) != str(object_type)
    )
    distractor_kinds = (
        ("same_type_opposite_region", max(1, min(2, int(object_count) - int(target_count)))),
        ("other_type_target_region", max(1, min(3, int(object_count) - int(target_count)))),
    )
    for kind, count in distractor_kinds:
        for _ in range(int(count)):
            if len(specs) >= int(object_count):
                break
            if str(kind) == "same_type_opposite_region":
                specs.append(IndoorObjectSpec(str(object_type), "region", str(distractor_region), "distractor"))
            else:
                specs.append(IndoorObjectSpec(str(rng.choice(non_target_types)), "region", str(target_region), "distractor"))
    while len(specs) < int(object_count):
        specs.append(IndoorObjectSpec(str(rng.choice(non_target_types)), "region", str(distractor_region), "distractor"))
    rng.shuffle(specs)
    return _SampleSpec(
        theme_id=str(theme_id),
        furniture_type=str(furniture_type),
        relation=str(relation),
        object_type=str(object_type),
        object_name=display_name(str(object_type)),
        target_count=int(target_count),
        object_count=int(object_count),
        specs=tuple(specs),
        theme_probabilities=dict(theme_probabilities),
        furniture_type_probabilities=dict(furniture_probabilities),
        relation_probabilities=dict(relation_probabilities),
        object_type_probabilities=dict(object_type_probabilities),
        target_count_probabilities=dict(target_probabilities),
        object_count_probabilities=dict(object_probabilities),
    )


def _build_complexity(sample: _SampleSpec) -> TaskComplexity:
    visual_scan = (int(sample.object_count) - _DEFAULTS.object_count_min) / max(1, _DEFAULTS.object_count_max - _DEFAULTS.object_count_min)
    answer_load = (int(sample.target_count) - _DEFAULTS.target_count_min) / max(1, _DEFAULTS.target_count_max - _DEFAULTS.target_count_min)
    relation_load = 0.85 if str(sample.relation) in {"above", "below"} else 0.75
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
class IllustrationsRelationFurnitureSideCountTask:
    """Count objects left/right/above/below named furniture."""

    task_id = TASK_ID
    domain = "illustrations"
    task_group = "relation"
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
        furniture_id = f"furniture_{sample.furniture_type}"
        counted_ids = tuple(
            str(placement.object_id)
            for placement in scene.placements
            if bool(placement.relations[str(furniture_id)][str(sample.relation)])
            and str(placement.object_type) == str(sample.object_type)
        )
        if len(counted_ids) != int(sample.target_count):
            raise RuntimeError("rendered furniture-side count did not match sample target")
        evidence_value = sort_bboxes_by_ids(object_bboxes, counted_ids)
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_furniture_side",
                "evidence_hint_furniture_side",
                "json_example_furniture_side",
                "json_example_answer_only_furniture_side",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        relation_word = {
            "left": "to the left of",
            "right": "to the right of",
            "above": "above",
            "below": "below",
        }.get(str(sample.relation), str(sample.relation))
        slots = {
            "object_count": int(sample.object_count),
            "room_setting": indoor_setting_name(str(scene.theme_id)),
            "furniture_name": str(sample.furniture_type),
            "object_name": str(sample.object_name),
            "relation_word": str(relation_word),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_furniture_side"]).format(
                object_name=str(sample.object_name),
                relation_word=str(relation_word),
                furniture_name=str(sample.furniture_type),
            ),
            "evidence_hint": str(prompt_defaults["evidence_hint_furniture_side"]).format(
                object_name=str(sample.object_name),
                relation_word=str(relation_word),
                furniture_name=str(sample.furniture_type),
            ),
            "json_example": str(prompt_defaults["json_example_furniture_side"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_furniture_side"]),
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
                "relations": {
                    "query_id": QUERY_ID,
                    "furniture_type": str(sample.furniture_type),
                    "furniture_id": str(furniture_id),
                    "relation": str(sample.relation),
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
                    "furniture_type": str(sample.furniture_type),
                    "furniture_name": str(sample.furniture_type),
                    "furniture_id": str(furniture_id),
                    "relation": str(sample.relation),
                    "object_type": str(sample.object_type),
                    "object_name": str(sample.object_name),
                    "target_count": int(sample.target_count),
                    "object_count": int(sample.object_count),
                    "theme_probabilities": dict(sample.theme_probabilities),
                    "furniture_type_probabilities": dict(sample.furniture_type_probabilities),
                    "relation_probabilities": dict(sample.relation_probabilities),
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
                "target_furniture_id": str(furniture_id),
                "counted_object_ids": list(counted_ids),
            },
            "execution_trace": {
                "query_id": QUERY_ID,
                "scene_id": SCENE_ID,
                "theme_id": str(scene.theme_id),
                "theme": str(scene.theme_id),
                "furniture_type": str(sample.furniture_type),
                "furniture_id": str(furniture_id),
                "relation": str(sample.relation),
                "object_type": str(sample.object_type),
                "object_name": str(sample.object_name),
                "target_count": int(sample.target_count),
                "object_count": int(sample.object_count),
                "counted_object_ids": list(counted_ids),
                "object_types": {str(obj["object_id"]): str(obj["object_type"]) for obj in serialized_objects},
            },
            "witness_symbolic": {
                "counted_object_ids": list(counted_ids),
                "furniture_id": str(furniture_id),
                "relation": str(sample.relation),
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


__all__ = ["IllustrationsRelationFurnitureSideCountTask"]
