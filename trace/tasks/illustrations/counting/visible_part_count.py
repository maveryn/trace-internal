"""Count visible semantic parts in a mixed synthetic-object illustration scene."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.sampling import normalize_positive_weights, weighted_choice
from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.mixed_object_scene import (
    choose_background_id,
    render_mixed_object_scene,
    resolve_content_bbox,
    sample_placements,
    scene_entities,
)
from ..shared.object_library import (
    PART_PLURALS,
    STYLE_IDS,
    family_for_object,
    object_types_without_part,
    object_types_with_part,
    part_count_for_object,
    serialize_object,
    supported_part_kinds,
)


TASK_ID = "task_illustrations__object_field__visible_part_count"
QUERY_ID = "visible_part_count"
SCENE_ID = "object_field"


@dataclass(frozen=True)
class _Defaults:
    object_count_min: int = 6
    object_count_max: int = 9
    target_count_min: int = 1
    target_count_max: int = 6
    distractor_count_min: int = 2
    max_target_object_repeats: int = 3
    min_family_count: int = 2
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
    part_kind: str
    target_count: int
    object_types: Tuple[str, ...]
    object_count: int
    target_object_types: Tuple[str, ...]
    distractor_object_types: Tuple[str, ...]
    part_kind_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    object_count_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _positive_style_weights(params: Mapping[str, Any]) -> Dict[str, float]:
    raw = params.get("style_weights", group_default(_RENDER_DEFAULTS, "style_weights", {style: 1.0 for style in STYLE_IDS}))
    if not isinstance(raw, Mapping):
        raise ValueError("style_weights must be a mapping")
    return normalize_positive_weights({str(key): float(value) for key, value in raw.items()}, default_keys=STYLE_IDS)


def _positive_background_weights(params: Mapping[str, Any]) -> Dict[str, float]:
    raw = params.get(
        "background_weights",
        group_default(
            _RENDER_DEFAULTS,
            "background_weights",
            {"studio": 1.0, "meadow": 1.0, "sky_ground": 1.0, "tabletop": 1.0, "paper": 1.0, "shelf": 1.0},
        ),
    )
    if not isinstance(raw, Mapping):
        raise ValueError("background_weights must be a mapping")
    return {str(key): float(value) for key, value in raw.items()}


def _query_part_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("part_kind_support", group_default(_GEN_DEFAULTS, "part_kind_support", supported_part_kinds()))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("part_kind_support must be a sequence")
    supported = tuple(str(value) for value in raw if str(value) in set(supported_part_kinds()))
    if not supported:
        raise ValueError("part_kind_support resolved no supported part kinds")
    return tuple(sorted(dict.fromkeys(supported)))


def _target_count_bounds(params: Mapping[str, Any]) -> Tuple[int, int]:
    low = int(params.get("target_count_min", group_default(_GEN_DEFAULTS, "target_count_min", _DEFAULTS.target_count_min)))
    high = int(params.get("target_count_max", group_default(_GEN_DEFAULTS, "target_count_max", _DEFAULTS.target_count_max)))
    if low < 1 or high < low:
        raise ValueError("invalid target_count range for visible part count")
    return low, high


def _object_count_bounds(params: Mapping[str, Any]) -> Tuple[int, int]:
    low = int(params.get("object_count_min", group_default(_GEN_DEFAULTS, "object_count_min", _DEFAULTS.object_count_min)))
    high = int(params.get("object_count_max", group_default(_GEN_DEFAULTS, "object_count_max", _DEFAULTS.object_count_max)))
    if low < 3 or high < low:
        raise ValueError("invalid object_count range for visible part count")
    return low, high


def _can_make_count(part_kind: str, target_count: int, *, max_repeats: int, max_objects: int) -> bool:
    values = [part_count_for_object(object_type, part_kind) for object_type in object_types_with_part(part_kind)]
    expanded = [int(value) for value in values for _ in range(max(1, int(max_repeats))) if int(value) > 0]
    reachable = {(0, 0)}
    for value in expanded:
        next_values = set(reachable)
        for total, count in reachable:
            if count + 1 <= int(max_objects):
                next_values.add((total + int(value), count + 1))
        reachable = next_values
    return any(total == int(target_count) and count > 0 for total, count in reachable)


def _feasible_target_counts(part_kind: str, params: Mapping[str, Any]) -> Tuple[int, ...]:
    low, high = _target_count_bounds(params)
    _obj_min, obj_max = _object_count_bounds(params)
    distractor_min = int(params.get("distractor_count_min", group_default(_GEN_DEFAULTS, "distractor_count_min", _DEFAULTS.distractor_count_min)))
    max_repeats = int(params.get("max_target_object_repeats", group_default(_GEN_DEFAULTS, "max_target_object_repeats", _DEFAULTS.max_target_object_repeats)))
    max_target_objects = max(1, int(obj_max) - max(0, int(distractor_min)))
    return tuple(
        value
        for value in range(int(low), int(high) + 1)
        if _can_make_count(str(part_kind), int(value), max_repeats=int(max_repeats), max_objects=int(max_target_objects))
    )


def _compose_target_objects(part_kind: str, target_count: int, *, params: Mapping[str, Any], rng) -> Tuple[str, ...]:
    candidates = tuple(object_types_with_part(str(part_kind)))
    max_repeats = int(params.get("max_target_object_repeats", group_default(_GEN_DEFAULTS, "max_target_object_repeats", _DEFAULTS.max_target_object_repeats)))
    _obj_min, obj_max = _object_count_bounds(params)
    distractor_min = int(params.get("distractor_count_min", group_default(_GEN_DEFAULTS, "distractor_count_min", _DEFAULTS.distractor_count_min)))
    max_target_objects = max(1, int(obj_max) - max(0, int(distractor_min)))

    def search(remaining: int, chosen: List[str], repeat_counts: Dict[str, int]) -> Tuple[str, ...] | None:
        if int(remaining) == 0:
            return tuple(chosen) if chosen else None
        if int(remaining) < 0 or len(chosen) >= int(max_target_objects):
            return None
        ordered = list(candidates)
        rng.shuffle(ordered)
        ordered.sort(key=lambda item: (part_count_for_object(str(item), str(part_kind)) > int(remaining), rng.random()))
        for object_type in ordered:
            count = part_count_for_object(str(object_type), str(part_kind))
            if count <= 0 or count > int(remaining):
                continue
            if int(repeat_counts.get(str(object_type), 0)) >= int(max_repeats):
                continue
            next_counts = dict(repeat_counts)
            next_counts[str(object_type)] = int(next_counts.get(str(object_type), 0)) + 1
            result = search(int(remaining) - int(count), [*chosen, str(object_type)], next_counts)
            if result is not None:
                return result
        return None

    result = search(int(target_count), [], {})
    if result is None:
        raise ValueError(f"could not compose target objects for {part_kind}={target_count}")
    return tuple(result)


def _resolve_part_and_target(*, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, int, Dict[str, float], Dict[str, float]]:
    support = _query_part_support(params)
    explicit_part = params.get("part_kind")
    selection_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:part_target")
    part_weights = params.get("part_kind_weights", group_default(_GEN_DEFAULTS, "part_kind_weights", {part: 1.0 for part in support}))
    if not isinstance(part_weights, Mapping):
        raise ValueError("part_kind_weights must be a mapping")
    part_probabilities = normalize_positive_weights(
        {str(key): float(value) for key, value in part_weights.items() if str(key) in set(support)},
        default_keys=support,
    )
    if explicit_part is not None:
        part_kind = str(explicit_part)
        if part_kind not in set(support):
            raise ValueError(f"part_kind must be one of {support}")
    elif bool(params.get("balanced_sampling", group_default(_GEN_DEFAULTS, "balanced_sampling", True))):
        part_kind = str(support[int(selection_index) % len(support)])
    else:
        rng = spawn_rng(int(instance_seed), f"{TASK_ID}:part_kind")
        part_kind = str(weighted_choice(rng, part_probabilities, sort_keys=True))

    feasible_counts = _feasible_target_counts(str(part_kind), params)
    if not feasible_counts:
        raise ValueError(f"no feasible target counts for part kind {part_kind}")
    explicit_target = params.get("target_count")
    if explicit_target is not None:
        target_count = int(explicit_target)
        if target_count not in set(feasible_counts):
            raise ValueError(f"target_count {target_count} is not feasible for {part_kind}")
    else:
        target_index = int(selection_index) // max(1, len(support))
        target_count = int(feasible_counts[int(target_index) % len(feasible_counts)])
    target_probabilities = uniform_probability_map(feasible_counts, selected=int(target_count) if explicit_target is not None else None)
    return (
        str(part_kind),
        int(target_count),
        {str(key): float(value) for key, value in sorted(part_probabilities.items())},
        dict(target_probabilities),
    )


def _resolve_sample_spec(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int) -> _SampleSpec:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:sample", int(attempt_index))
    part_kind, target_count, part_probs, target_probs = _resolve_part_and_target(instance_seed=int(instance_seed), params=params)
    target_objects = _compose_target_objects(str(part_kind), int(target_count), params=params, rng=rng)
    object_min, object_max = _object_count_bounds(params)
    distractor_min = int(params.get("distractor_count_min", group_default(_GEN_DEFAULTS, "distractor_count_min", _DEFAULTS.distractor_count_min)))
    min_family_count = int(params.get("min_family_count", group_default(_GEN_DEFAULTS, "min_family_count", _DEFAULTS.min_family_count)))
    min_object_count = max(int(object_min), len(target_objects) + max(0, int(distractor_min)))
    if min_object_count > int(object_max):
        raise ValueError("target composition leaves no room for required distractors")

    explicit_object_count = params.get("object_count")
    object_support = tuple(range(int(min_object_count), int(object_max) + 1))
    if explicit_object_count is not None:
        object_count = int(explicit_object_count)
        if object_count not in set(object_support):
            raise ValueError("object_count is not feasible for selected part/target count")
    else:
        selection_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:object_count")
        part_support_len = max(1, len(_query_part_support(params)))
        feasible_count_len = max(1, len(_feasible_target_counts(str(part_kind), params)))
        object_count = int(object_support[(int(selection_index) // (part_support_len * feasible_count_len)) % len(object_support)])
    distractor_count = int(object_count) - len(target_objects)
    distractor_pool = list(object_types_without_part(str(part_kind)))
    if not distractor_pool:
        raise ValueError(f"no distractor object types without part kind {part_kind}")
    selected_distractors: List[str] = []
    current_families = {family_for_object(object_type) for object_type in target_objects}
    for _ in range(int(distractor_count)):
        pool = list(distractor_pool)
        if len(current_families) < int(min_family_count):
            family_filtered = [obj for obj in pool if family_for_object(obj) not in current_families]
            if family_filtered:
                pool = family_filtered
        obj = str(rng.choice(tuple(pool)))
        selected_distractors.append(obj)
        current_families.add(family_for_object(obj))
    all_objects = [*target_objects, *selected_distractors]
    rng.shuffle(all_objects)
    return _SampleSpec(
        part_kind=str(part_kind),
        target_count=int(target_count),
        object_types=tuple(str(value) for value in all_objects),
        object_count=int(object_count),
        target_object_types=tuple(str(value) for value in target_objects),
        distractor_object_types=tuple(str(value) for value in selected_distractors),
        part_kind_probabilities=dict(part_probs),
        target_count_probabilities=dict(target_probs),
        object_count_probabilities=dict(uniform_probability_map(object_support, selected=int(object_count) if explicit_object_count is not None else None)),
    )


def _render_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "canvas_width": int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        "canvas_height": int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        "outer_margin_px": int(params.get("outer_margin_px", group_default(_RENDER_DEFAULTS, "outer_margin_px", _DEFAULTS.outer_margin_px))),
        "object_size_min_px": int(params.get("object_size_min_px", group_default(_RENDER_DEFAULTS, "object_size_min_px", _DEFAULTS.object_size_min_px))),
        "object_size_max_px": int(params.get("object_size_max_px", group_default(_RENDER_DEFAULTS, "object_size_max_px", _DEFAULTS.object_size_max_px))),
        "object_min_gap_px": int(params.get("object_min_gap_px", group_default(_RENDER_DEFAULTS, "object_min_gap_px", _DEFAULTS.object_min_gap_px))),
        "max_overlap_fraction": float(params.get("max_overlap_fraction", group_default(_RENDER_DEFAULTS, "max_overlap_fraction", _DEFAULTS.max_overlap_fraction))),
        "placement_max_attempts": int(params.get("placement_max_attempts", group_default(_RENDER_DEFAULTS, "placement_max_attempts", _DEFAULTS.placement_max_attempts))),
        "render_scale": int(params.get("render_scale", group_default(_RENDER_DEFAULTS, "render_scale", _DEFAULTS.render_scale))),
    }


def _sort_part_bboxes(parts: Sequence[Any]) -> List[List[float]]:
    ordered = sorted(parts, key=lambda part: (float(part.bbox_xyxy[1]), float(part.bbox_xyxy[0]), str(part.part_id)))
    return [[round(float(v), 3) for v in part.bbox_xyxy] for part in ordered]


def _build_complexity(*, sample: _SampleSpec, distractor_part_count: int) -> TaskComplexity:
    object_scan = (int(sample.object_count) - _DEFAULTS.object_count_min) / max(1, _DEFAULTS.object_count_max - _DEFAULTS.object_count_min)
    answer_load = (int(sample.target_count) - _DEFAULTS.target_count_min) / max(1, _DEFAULTS.target_count_max - _DEFAULTS.target_count_min)
    distractor_load = min(1.0, float(distractor_part_count) / max(1.0, float(sample.target_count + distractor_part_count)))
    score = 0.45 * max(0.0, min(1.0, object_scan)) + 0.35 * max(0.0, min(1.0, answer_load)) + 0.20 * max(0.0, min(1.0, distractor_load))
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "visual_scan": round(float(object_scan), 6),
            "answer_load": round(float(answer_load), 6),
            "distractor_part_fraction": round(float(distractor_load), 6),
            "object_count": int(sample.object_count),
            "target_count": int(sample.target_count),
            "queried_part_kind": str(sample.part_kind),
        },
    )


@register_task
class IllustrationsCountingVisiblePartCountTask:
    """Count visible object parts in a mixed synthetic illustration."""

    task_id = TASK_ID
    domain = "illustrations"
    task_group = "counting"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        render_params = _render_params(params)
        last_error: Exception | None = None
        scene = None
        sample = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                sample = _resolve_sample_spec(instance_seed=int(instance_seed), params=params, attempt_index=int(attempt))
                content_bbox = resolve_content_bbox(
                    canvas_width=int(render_params["canvas_width"]),
                    canvas_height=int(render_params["canvas_height"]),
                    margin_px=int(render_params["outer_margin_px"]),
                )
                scene_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:scene", int(attempt))
                background_weights = _positive_background_weights(params)
                background_id = choose_background_id(scene_rng, background_weights, object_types=sample.object_types)
                placements = sample_placements(
                    object_types=sample.object_types,
                    rng=scene_rng,
                    canvas_width=int(render_params["canvas_width"]),
                    canvas_height=int(render_params["canvas_height"]),
                    content_bbox=content_bbox,
                    object_size_min_px=int(render_params["object_size_min_px"]),
                    object_size_max_px=int(render_params["object_size_max_px"]),
                    min_gap_px=int(render_params["object_min_gap_px"]),
                    max_overlap_fraction=float(render_params["max_overlap_fraction"]),
                    placement_max_attempts=int(render_params["placement_max_attempts"]),
                    style_weights=_positive_style_weights(params),
                    background_id=str(background_id),
                )
                scene = render_mixed_object_scene(
                    placements=placements,
                    rng=scene_rng,
                    canvas_width=int(render_params["canvas_width"]),
                    canvas_height=int(render_params["canvas_height"]),
                    background_weights=background_weights,
                    render_scale=int(render_params["render_scale"]),
                    content_bbox=content_bbox,
                    background_id=str(background_id),
                )
                break
            except Exception as exc:  # pragma: no cover - exercised by max_attempts smoke tests.
                last_error = exc
                continue
        if scene is None or sample is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        counted_parts = [
            part
            for rendered_object in scene.objects
            for part in rendered_object.parts
            if str(part.part_kind) == str(sample.part_kind)
        ]
        if len(counted_parts) != int(sample.target_count):
            raise RuntimeError(
                f"visible part count mismatch for {sample.part_kind}: rendered {len(counted_parts)} expected {sample.target_count}"
            )
        evidence_value = _sort_part_bboxes(counted_parts)
        counted_part_ids = [str(part.part_id) for part in sorted(counted_parts, key=lambda part: (float(part.bbox_xyxy[1]), float(part.bbox_xyxy[0]), str(part.part_id)))]
        distractor_part_count = sum(
            1
            for rendered_object in scene.objects
            for part in rendered_object.parts
            if str(part.part_kind) != str(sample.part_kind)
        )
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "evidence_hint",
                "json_example",
                "json_example_answer_only",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        part_plural = PART_PLURALS.get(str(sample.part_kind), f"{sample.part_kind}s")
        slots = {
            "part_kind": str(sample.part_kind),
            "part_plural": str(part_plural),
            "object_count": int(sample.object_count),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint"]).format(part_plural=str(part_plural), part_kind=str(sample.part_kind)),
            "evidence_hint": str(prompt_defaults["evidence_hint"]).format(part_plural=str(part_plural), part_kind=str(sample.part_kind)),
            "json_example": str(prompt_defaults["json_example"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
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
        serialized_objects = [serialize_object(obj) for obj in scene.objects]
        object_bboxes = {obj["object_id"]: list(obj["bbox"]) for obj in serialized_objects}
        part_bboxes = {
            part["part_id"]: list(part["bbox"])
            for obj in serialized_objects
            for part in obj["parts"]
        }
        trace_payload = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "entities": scene_entities(scene),
                "relations": {
                    "query_id": QUERY_ID,
                    "queried_part_kind": str(sample.part_kind),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_id": QUERY_ID,
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "part_kind": str(sample.part_kind),
                    "part_plural": str(part_plural),
                    "target_count": int(sample.target_count),
                    "object_count": int(sample.object_count),
                    "part_kind_probabilities": dict(sample.part_kind_probabilities),
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
                "counted_part_ids": list(counted_part_ids),
            },
            "execution_trace": {
                "query_id": QUERY_ID,
                "scene_id": SCENE_ID,
                "part_kind": str(sample.part_kind),
                "part_plural": str(part_plural),
                "target_count": int(sample.target_count),
                "object_count": int(sample.object_count),
                "object_types": list(sample.object_types),
                "target_object_types": list(sample.target_object_types),
                "distractor_object_types": list(sample.distractor_object_types),
                "counted_part_ids": list(counted_part_ids),
                "background_id": str(scene.background_id),
            },
            "witness_symbolic": {
                "counted_part_ids": list(counted_part_ids),
                "queried_part_kind": str(sample.part_kind),
                "answer": int(sample.target_count),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_value),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="integer", value=int(sample.target_count)),
            evidence_gt=TypedValue(type="bbox_set", value=list(evidence_value)),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(sample=sample, distractor_part_count=int(distractor_part_count)),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
        )


__all__ = [
    "IllustrationsCountingVisiblePartCountTask",
]
