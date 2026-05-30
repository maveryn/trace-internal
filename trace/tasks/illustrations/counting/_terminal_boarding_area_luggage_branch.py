"""Count standalone luggage of one type in one labeled boarding area."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.task_support import query_support as _shared_query_support
from ..shared.transit_task_common import (
    area_support,
    bounds,
    render_params,
    sample_count,
    setting_weights,
    spawned_task_rng,
    style_weights,
    uniform_string_probability_map,
)
from ..shared.transit_terminal_scene import (
    TRANSIT_BOARDING_AREA_IDS,
    TRANSIT_LUGGAGE_TYPES,
    TRANSIT_PERSON_POSES,
    TransitLuggageSpec,
    TransitPersonSpec,
    render_transit_terminal_scene,
    serialize_transit_scene,
    sort_transit_bboxes,
    transit_area_display_name,
    transit_luggage_bbox_map,
    transit_luggage_display_name,
    transit_scene_entities,
)


TASK_ID = "private_terminal_boarding_area_luggage"
SCENE_ID = "transit_terminal"
QUERY_IDS: Tuple[str, ...] = (
    "luggage_in_boarding_area_count",
)
_PERSON_POSES_NO_LUGGAGE: Tuple[str, ...] = tuple(pose for pose in TRANSIT_PERSON_POSES if pose != "with_luggage")


@dataclass(frozen=True)
class _Defaults:
    luggage_count_min: int = 10
    luggage_count_max: int = 18
    target_count_min: int = 2
    target_count_max: int = 6
    person_count_min: int = 10
    person_count_max: int = 18
    canvas_width: int = 1280
    canvas_height: int = 900
    render_scale: int = 2


@dataclass(frozen=True)
class _SampleSpec:
    query_id: str
    luggage_type: str
    luggage_name: str
    area_id: str
    area_name: str
    target_count: int
    luggage_count: int
    person_count: int
    luggage_specs: Tuple[TransitLuggageSpec, ...]
    person_specs: Tuple[TransitPersonSpec, ...]
    query_probabilities: Dict[str, float]
    luggage_type_probabilities: Dict[str, float]
    area_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    luggage_count_probabilities: Dict[str, float]
    person_count_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)




def _luggage_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("luggage_type_support", group_default(_GEN_DEFAULTS, "luggage_type_support", TRANSIT_LUGGAGE_TYPES))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("luggage_type_support must be a sequence")
    support = tuple(str(value) for value in raw if str(value) in set(TRANSIT_LUGGAGE_TYPES))
    if len(support) < 2:
        raise ValueError("luggage_type_support must contain at least two luggage types")
    return tuple(dict.fromkeys(support))


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int) -> _SampleSpec:
    rng = spawned_task_rng(int(instance_seed), TASK_ID, int(attempt_index))
    base_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:cycle")
    query_values = _shared_query_support(params, _GEN_DEFAULTS, QUERY_IDS)
    area_values = area_support(params, _GEN_DEFAULTS, fallback=TRANSIT_BOARDING_AREA_IDS)
    luggage_values = _luggage_support(params)
    target_min, target_max = bounds(
        params,
        _GEN_DEFAULTS,
        "target_count_min",
        "target_count_max",
        _DEFAULTS.target_count_min,
        _DEFAULTS.target_count_max,
    )

    explicit_query = params.get("query_id")
    if explicit_query is not None:
        query_id = str(explicit_query)
        if query_id not in set(query_values):
            raise ValueError("query_id is outside configured support")
        query_index = int(query_values.index(query_id))
        query_probabilities = uniform_string_probability_map(query_values, selected=query_id)
    else:
        query_index = int(base_index) % len(query_values)
        query_id = str(query_values[query_index])
        query_probabilities = uniform_string_probability_map(query_values)

    explicit_luggage_type = params.get("luggage_type")
    if explicit_luggage_type is not None:
        luggage_type = str(explicit_luggage_type)
        if luggage_type not in set(luggage_values):
            raise ValueError("luggage_type is outside configured support")
        luggage_index = int(luggage_values.index(luggage_type))
        luggage_type_probabilities = uniform_string_probability_map(luggage_values, selected=luggage_type)
    else:
        luggage_index = int(base_index // max(1, len(query_values))) % len(luggage_values)
        luggage_type = str(luggage_values[luggage_index])
        luggage_type_probabilities = uniform_string_probability_map(luggage_values)

    explicit_area = params.get("area_id")
    if explicit_area is not None:
        area_id = str(explicit_area)
        if area_id not in set(area_values):
            raise ValueError("area_id is outside configured support")
        area_index = int(area_values.index(area_id))
        area_probabilities = uniform_string_probability_map(area_values, selected=area_id)
    else:
        area_index = int(base_index // max(1, len(query_values) * len(luggage_values))) % len(area_values)
        area_id = str(area_values[area_index])
        area_probabilities = uniform_string_probability_map(area_values)

    target_count, target_probabilities = sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:target_count",
        low=int(target_min),
        high=int(target_max),
        explicit_key="target_count",
        cycle_index=int(base_index // max(1, len(query_values) * len(luggage_values) * len(area_values))) + 2 * int(luggage_index) + int(area_index) + int(query_index),
    )
    luggage_min, luggage_max = bounds(
        params,
        _GEN_DEFAULTS,
        "luggage_count_min",
        "luggage_count_max",
        _DEFAULTS.luggage_count_min,
        _DEFAULTS.luggage_count_max,
    )
    luggage_low = max(int(luggage_min), int(target_count) + 4)
    luggage_count, luggage_count_probabilities = sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:luggage_count",
        low=int(luggage_low),
        high=int(luggage_max),
        explicit_key="luggage_count",
        cycle_index=int(base_index // max(1, len(query_values) * len(luggage_values) * len(area_values) * int(target_max - target_min + 1))),
    )
    person_min, person_max = bounds(
        params,
        _GEN_DEFAULTS,
        "person_count_min",
        "person_count_max",
        _DEFAULTS.person_count_min,
        _DEFAULTS.person_count_max,
    )
    person_count, person_count_probabilities = sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:person_count",
        low=int(person_min),
        high=int(person_max),
        explicit_key="person_count",
        cycle_index=int(base_index // max(1, len(query_values) * len(luggage_values) * len(area_values) * int(target_max - target_min + 1) * max(1, int(luggage_max - luggage_min + 1)))),
    )

    other_areas = [str(value) for value in area_values if str(value) != str(area_id)]
    other_luggage = [str(value) for value in luggage_values if str(value) != str(luggage_type)]
    if not other_areas or not other_luggage:
        raise ValueError("luggage task needs distractor areas and luggage types")
    luggage_specs = [
        TransitLuggageSpec(area_id=str(area_id), luggage_type=str(luggage_type), role="target")
        for _ in range(int(target_count))
    ]
    mandatory = [
        TransitLuggageSpec(area_id=str(other_areas[0]), luggage_type=str(luggage_type), role="distractor"),
        TransitLuggageSpec(area_id=str(area_id), luggage_type=str(other_luggage[0]), role="distractor"),
    ]
    for spec in mandatory[: max(0, int(luggage_count) - int(target_count))]:
        luggage_specs.append(spec)
    while len(luggage_specs) < int(luggage_count):
        if float(rng.random()) < 0.35:
            distractor_area = str(rng.choice(tuple(other_areas)))
            distractor_type = str(luggage_type)
        elif float(rng.random()) < 0.55:
            distractor_area = str(area_id)
            distractor_type = str(rng.choice(tuple(other_luggage)))
        else:
            distractor_area = str(rng.choice(tuple(other_areas)))
            distractor_type = str(rng.choice(tuple(other_luggage)))
        luggage_specs.append(TransitLuggageSpec(area_id=distractor_area, luggage_type=distractor_type, role="distractor"))
    rng.shuffle(luggage_specs)

    person_specs = tuple(
        TransitPersonSpec(
            area_id="concourse",
            role="decor",
            attributes={"pose_id": str(rng.choice(_PERSON_POSES_NO_LUGGAGE))},
        )
        for _ in range(int(person_count))
    )
    return _SampleSpec(
        query_id=str(query_id),
        luggage_type=str(luggage_type),
        luggage_name=transit_luggage_display_name(str(luggage_type)),
        area_id=str(area_id),
        area_name=transit_area_display_name(str(area_id)),
        target_count=int(target_count),
        luggage_count=int(luggage_count),
        person_count=int(person_count),
        luggage_specs=tuple(luggage_specs),
        person_specs=tuple(person_specs),
        query_probabilities=dict(query_probabilities),
        luggage_type_probabilities=dict(luggage_type_probabilities),
        area_probabilities=dict(area_probabilities),
        target_count_probabilities=dict(target_probabilities),
        luggage_count_probabilities=dict(luggage_count_probabilities),
        person_count_probabilities=dict(person_count_probabilities),
    )


def _build_complexity(sample: _SampleSpec) -> TaskComplexity:
    luggage_scan = (int(sample.luggage_count) - _DEFAULTS.luggage_count_min) / max(1, _DEFAULTS.luggage_count_max - _DEFAULTS.luggage_count_min)
    answer_load = (int(sample.target_count) - _DEFAULTS.target_count_min) / max(1, _DEFAULTS.target_count_max - _DEFAULTS.target_count_min)
    person_clutter = (int(sample.person_count) - _DEFAULTS.person_count_min) / max(1, _DEFAULTS.person_count_max - _DEFAULTS.person_count_min)
    score = 0.42 * max(0.0, min(1.0, luggage_scan)) + 0.34 * max(0.0, min(1.0, answer_load)) + 0.24 * max(0.0, min(1.0, person_clutter))
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "luggage_scan": round(float(luggage_scan), 6),
            "answer_load": round(float(answer_load), 6),
            "person_clutter": round(float(person_clutter), 6),
        },
    )


class TerminalBoardingAreaLuggageBranch:
    """Count standalone luggage of one type in one labeled boarding area."""

    task_id = TASK_ID
    branch_id = "terminal_boarding_area_luggage"
    domain = "illustrations"
    task_group = "counting"
    default_dataset_enabled = False

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        sample: _SampleSpec | None = None
        scene = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                sample = _sample_spec(instance_seed=int(instance_seed), params=params, attempt_index=int(attempt))
                scene_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:scene", int(attempt))
                rp = render_params(
                    params,
                    _RENDER_DEFAULTS,
                    fallback_width=_DEFAULTS.canvas_width,
                    fallback_height=_DEFAULTS.canvas_height,
                    fallback_scale=_DEFAULTS.render_scale,
                )
                scene = render_transit_terminal_scene(
                    rng=scene_rng,
                    person_specs=sample.person_specs,
                    luggage_specs=sample.luggage_specs,
                    canvas_width=int(rp["canvas_width"]),
                    canvas_height=int(rp["canvas_height"]),
                    render_scale=int(rp["render_scale"]),
                    setting_weights=setting_weights(params, _RENDER_DEFAULTS),
                    style_weights=style_weights(params, _RENDER_DEFAULTS),
                )
                break
            except Exception as exc:  # pragma: no cover
                last_error = exc
                sample = None
                scene = None
        if scene is None or sample is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        serialized_scene, person_bboxes = serialize_transit_scene(scene)
        luggage_bboxes = transit_luggage_bbox_map(scene)
        counted_luggage_ids = tuple(
            str(item.luggage_id)
            for item in scene.luggage
            if str(item.area_id) == str(sample.area_id) and str(item.luggage_type) == str(sample.luggage_type)
        )
        if len(counted_luggage_ids) != int(sample.target_count):
            raise RuntimeError("rendered boarding-area luggage count did not match sample target")
        evidence_value = sort_transit_bboxes(luggage_bboxes, counted_luggage_ids)
        luggage_counts = dict(Counter((str(item.area_id), str(item.luggage_type)) for item in scene.luggage))

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_luggage_in_boarding_area",
                "evidence_hint_luggage_in_boarding_area",
                "json_example_luggage_in_boarding_area",
                "json_example_answer_only_luggage_in_boarding_area",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        slots = {
            "person_count": int(sample.person_count),
            "area_name": str(sample.area_name),
            "luggage_name": str(sample.luggage_name),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_luggage_in_boarding_area"]).format(luggage_name=str(sample.luggage_name), area_name=str(sample.area_name)),
            "evidence_hint": str(prompt_defaults["evidence_hint_luggage_in_boarding_area"]).format(luggage_name=str(sample.luggage_name), area_name=str(sample.area_name)),
            "json_example": str(prompt_defaults["json_example_luggage_in_boarding_area"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_luggage_in_boarding_area"]),
        }
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(sample.query_id),
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
                "entities": transit_scene_entities(scene),
                "relations": {
                    "query_id": str(sample.query_id),
                    "target_area_id": str(sample.area_id),
                    "target_luggage_type": str(sample.luggage_type),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_id": str(sample.query_id),
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "area_id": str(sample.area_id),
                    "area_name": str(sample.area_name),
                    "luggage_type": str(sample.luggage_type),
                    "luggage_name": str(sample.luggage_name),
                    "target_count": int(sample.target_count),
                    "luggage_count": int(sample.luggage_count),
                    "person_count": int(sample.person_count),
                    "query_probabilities": dict(sample.query_probabilities),
                    "luggage_type_probabilities": dict(sample.luggage_type_probabilities),
                    "area_probabilities": dict(sample.area_probabilities),
                    "target_count_probabilities": dict(sample.target_count_probabilities),
                    "luggage_count_probabilities": dict(sample.luggage_count_probabilities),
                    "person_count_probabilities": dict(sample.person_count_probabilities),
                },
            },
            "render_spec": {
                "canvas_size": [int(scene.canvas_width), int(scene.canvas_height)],
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "style": {
                    "setting_id": str(scene.setting_id),
                    "style_id": str(scene.style_id),
                    "render_scale": int(scene.render_scale),
                    "layout": dict(scene.layout),
                },
            },
            "render_map": {
                "person_bboxes_px": person_bboxes,
                "luggage_bboxes_px": luggage_bboxes,
                "counted_luggage_ids": list(counted_luggage_ids),
            },
            "execution_trace": {
                "query_id": str(sample.query_id),
                "scene_id": SCENE_ID,
                "target_area_id": str(sample.area_id),
                "target_area_name": str(sample.area_name),
                "target_luggage_type": str(sample.luggage_type),
                "target_luggage_name": str(sample.luggage_name),
                "target_count": int(sample.target_count),
                "luggage_count": int(sample.luggage_count),
                "person_count": int(sample.person_count),
                "luggage_counts": {f"{area}:{kind}": int(count) for (area, kind), count in luggage_counts.items()},
                "counted_luggage_ids": list(counted_luggage_ids),
                "areas": serialized_scene[0]["areas"],
                "service_points": serialized_scene[0]["service_points"],
                "persons": serialized_scene[0]["persons"],
                "luggage": serialized_scene[0]["luggage"],
                "decor": serialized_scene[0]["decor"],
                "setting_id": str(scene.setting_id),
                "layout": dict(scene.layout),
            },
            "witness_symbolic": {
                "counted_luggage_ids": list(counted_luggage_ids),
                "target_area_id": str(sample.area_id),
                "target_luggage_type": str(sample.luggage_type),
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
            query_id=str(sample.query_id),
        )


__all__ = ["TerminalBoardingAreaLuggageBranch"]
