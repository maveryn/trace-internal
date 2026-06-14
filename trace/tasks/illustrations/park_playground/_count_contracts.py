"""Private count-contract runners for park/playground task files."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.query_ids import SINGLE_QUERY_ID
from ....core.scene_config import get_scene_defaults
from ...base import TaskOutput
from ...shared.config_defaults import group_default, required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ...shared.fixed_query import select_task_query_id
from ._lifecycle import compose_count_result, render_scene_with_retries
from .shared.annotations import park_decor_bbox_map, park_person_bbox_map, park_scene_entities, serialize_park_scene, sort_park_bboxes
from .shared.sampling import activity_support, bounds, equipment_support, sample_count, spawned_task_rng, support_choice, zone_support
from .shared.state import (
    PARK_EQUIPMENT_TYPES,
    PARK_PERSON_ACTIVITIES,
    PARK_ZONE_TYPES,
    ParkEquipmentSpec,
    ParkPersonSpec,
    park_activity_display_name,
    park_equipment_display_name,
    park_zone_display_name,
)


@dataclass(frozen=True)
class CountDefaults:
    """Numeric scene defaults shared by the count task runners."""

    person_count_min: int = 7
    person_count_max: int = 12
    target_count_min: int = 1
    target_count_max: int = 6
    equipment_count_min: int = 4
    equipment_count_max: int = 7
    canvas_width: int = 1280
    canvas_height: int = 900
    render_scale: int = 2


@dataclass(frozen=True)
class CountRuntime:
    """Resolved config and prompt routing supplied by the public task file."""

    namespace: str
    prompt_query_key: str
    supported_query_ids: Tuple[str, ...]
    defaults: CountDefaults
    generation_defaults: Mapping[str, Any]
    rendering_defaults: Mapping[str, Any]
    prompt_defaults: Mapping[str, Any]


@dataclass(frozen=True)
class ActivitySampleSpec:
    query_id: str
    target_activity: str
    activity_phrase: str
    target_count: int
    person_count: int
    person_specs: Tuple[ParkPersonSpec, ...]
    query_probabilities: Dict[str, float]
    target_activity_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    person_count_probabilities: Dict[str, float]


@dataclass(frozen=True)
class AreaSampleSpec:
    query_id: str
    target_zone: str
    zone_name: str
    target_count: int
    person_count: int
    person_specs: Tuple[ParkPersonSpec, ...]
    query_probabilities: Dict[str, float]
    target_zone_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    person_count_probabilities: Dict[str, float]


@dataclass(frozen=True)
class EquipmentUseSampleSpec:
    query_id: str
    target_equipment_type: str
    equipment_name: str
    target_count: int
    equipment_count: int
    person_count: int
    equipment_specs: Tuple[ParkEquipmentSpec, ...]
    person_specs: Tuple[ParkPersonSpec, ...]
    query_probabilities: Dict[str, float]
    target_equipment_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    equipment_count_probabilities: Dict[str, float]
    person_count_probabilities: Dict[str, float]


@dataclass(frozen=True)
class EquipmentSampleSpec:
    query_id: str
    target_equipment_type: str
    equipment_name: str
    target_count: int
    equipment_count: int
    person_count: int
    equipment_specs: Tuple[ParkEquipmentSpec, ...]
    person_specs: Tuple[ParkPersonSpec, ...]
    query_probabilities: Dict[str, float]
    target_equipment_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    equipment_count_probabilities: Dict[str, float]
    person_count_probabilities: Dict[str, float]


_SCENE_ID = "park_playground"
_DEFAULT_TARGET_EQUIPMENT: Tuple[str, ...] = ("slide", "swing_set", "seesaw")
_USAGE_EQUIPMENT_LABELS: Dict[str, str] = {
    "slide": "slides",
    "swing_set": "swings",
    "seesaw": "seesaws",
}
_EQUIPMENT_ACTIVITY: Dict[str, str] = {
    "slide": "standing",
    "swing_set": "sitting",
    "seesaw": "sitting",
    "climbing_frame": "standing",
}


def build_count_runtime(
    *,
    namespace: str,
    prompt_query_key: str,
    supported_query_ids: Sequence[str],
    defaults: CountDefaults,
) -> CountRuntime:
    """Resolve scene config for one public count task."""

    scene_defaults = get_scene_defaults("illustrations", _SCENE_ID)
    generation_defaults, rendering_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
        scene_defaults if isinstance(scene_defaults, Mapping) else {},
        task_id=str(namespace),
    )
    return CountRuntime(
        namespace=str(namespace),
        prompt_query_key=str(prompt_query_key),
        supported_query_ids=tuple(str(value) for value in supported_query_ids),
        defaults=defaults,
        generation_defaults=generation_defaults,
        rendering_defaults=rendering_defaults,
        prompt_defaults=prompt_defaults,
    )


def sample_activity_people(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int, runtime: CountRuntime) -> ActivitySampleSpec:
    """Sample one activity predicate with exact target and distractor people."""

    query_id, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=runtime.supported_query_ids,
        default_query_id=SINGLE_QUERY_ID,
        task_id=str(runtime.namespace),
        namespace=f"{runtime.namespace}:query",
    )
    rng = spawned_task_rng(int(instance_seed), str(runtime.namespace), int(attempt_index))
    activities = activity_support(task_params, runtime.generation_defaults, fallback=PARK_PERSON_ACTIVITIES)
    target_activity, activity_probabilities = support_choice(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{runtime.namespace}:target_activity",
        support=activities,
        explicit_key="target_activity",
    )
    target_min, target_max = bounds(
        task_params,
        runtime.generation_defaults,
        "target_count_min",
        "target_count_max",
        runtime.defaults.target_count_min,
        runtime.defaults.target_count_max,
    )
    target_count, target_probabilities = sample_count(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{runtime.namespace}:target_count",
        low=int(target_min),
        high=int(target_max),
        explicit_key="target_count",
    )
    person_min, person_max = bounds(
        task_params,
        runtime.generation_defaults,
        "person_count_min",
        "person_count_max",
        runtime.defaults.person_count_min,
        runtime.defaults.person_count_max,
    )
    person_count, person_probabilities = sample_count(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{runtime.namespace}:person_count",
        low=max(int(person_min), int(target_count) + 2),
        high=int(person_max),
        explicit_key="person_count",
    )
    distractors = [str(value) for value in activities if str(value) != str(target_activity)]
    if not distractors:
        raise ValueError("activity count needs at least one distractor activity")
    person_specs = [ParkPersonSpec(activity=str(target_activity), role="target") for _ in range(int(target_count))]
    for index in range(int(person_count) - int(target_count)):
        distractor_activity = str(distractors[index]) if index < len(distractors) else str(rng.choice(tuple(distractors)))
        person_specs.append(ParkPersonSpec(activity=distractor_activity, role="distractor"))
    rng.shuffle(person_specs)
    return ActivitySampleSpec(
        query_id=str(query_id),
        target_activity=str(target_activity),
        activity_phrase=park_activity_display_name(str(target_activity)),
        target_count=int(target_count),
        person_count=int(person_count),
        person_specs=tuple(person_specs),
        query_probabilities=dict(query_probabilities),
        target_activity_probabilities=dict(activity_probabilities),
        target_count_probabilities=dict(target_probabilities),
        person_count_probabilities=dict(person_probabilities),
    )


def sample_area_people(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int, runtime: CountRuntime) -> AreaSampleSpec:
    """Sample one target area and construct exact target/distractor people."""

    query_id, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=runtime.supported_query_ids,
        default_query_id=SINGLE_QUERY_ID,
        task_id=str(runtime.namespace),
        namespace=f"{runtime.namespace}:query",
    )
    rng = spawned_task_rng(int(instance_seed), str(runtime.namespace), int(attempt_index))
    zones = zone_support(task_params, runtime.generation_defaults, fallback=PARK_ZONE_TYPES)
    target_zone, zone_probabilities = support_choice(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{runtime.namespace}:target_zone",
        support=zones,
        explicit_key="target_zone",
    )
    target_min, target_max = bounds(
        task_params,
        runtime.generation_defaults,
        "target_count_min",
        "target_count_max",
        runtime.defaults.target_count_min,
        runtime.defaults.target_count_max,
    )
    target_count, target_probabilities = sample_count(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{runtime.namespace}:target_count",
        low=int(target_min),
        high=int(target_max),
        explicit_key="target_count",
    )
    person_min, person_max = bounds(
        task_params,
        runtime.generation_defaults,
        "person_count_min",
        "person_count_max",
        runtime.defaults.person_count_min,
        runtime.defaults.person_count_max,
    )
    person_count, person_probabilities = sample_count(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{runtime.namespace}:person_count",
        low=max(int(person_min), int(target_count) + 3),
        high=int(person_max),
        explicit_key="person_count",
    )
    distractor_zones = [str(value) for value in zones if str(value) != str(target_zone)]
    if not distractor_zones:
        raise ValueError("area count needs at least one distractor area")
    person_specs = [
        ParkPersonSpec(
            activity=str(rng.choice(PARK_PERSON_ACTIVITIES)),
            role="target",
            attributes={"zone": str(target_zone)},
        )
        for _ in range(int(target_count))
    ]
    for index in range(int(person_count) - int(target_count)):
        zone = str(distractor_zones[index]) if index < len(distractor_zones) else str(rng.choice(tuple(distractor_zones)))
        person_specs.append(
            ParkPersonSpec(
                activity=str(rng.choice(PARK_PERSON_ACTIVITIES)),
                role="distractor",
                attributes={"zone": zone},
            )
        )
    rng.shuffle(person_specs)
    return AreaSampleSpec(
        query_id=str(query_id),
        target_zone=str(target_zone),
        zone_name=park_zone_display_name(str(target_zone)),
        target_count=int(target_count),
        person_count=int(person_count),
        person_specs=tuple(person_specs),
        query_probabilities=dict(query_probabilities),
        target_zone_probabilities=dict(zone_probabilities),
        target_count_probabilities=dict(target_probabilities),
        person_count_probabilities=dict(person_probabilities),
    )


def _usage_label(equipment_type: str) -> str:
    return _USAGE_EQUIPMENT_LABELS.get(str(equipment_type), str(equipment_type).replace("_", " ") + "s")


def _usage_activity(equipment_type: str) -> str:
    return _EQUIPMENT_ACTIVITY.get(str(equipment_type), "standing")


def _target_equipment_support(params: Mapping[str, Any], defaults: Mapping[str, Any], equipment_values: Sequence[str]) -> Tuple[str, ...]:
    raw = params.get("equipment_use_target_support", group_default(defaults, "equipment_use_target_support", _DEFAULT_TARGET_EQUIPMENT))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("equipment_use_target_support must be a sequence")
    available = set(str(value) for value in equipment_values)
    support = tuple(str(value) for value in raw if str(value) in available)
    if not support:
        raise ValueError("equipment_use_target_support resolved no supported target equipment")
    return tuple(dict.fromkeys(support))


def sample_equipment_users(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int, runtime: CountRuntime) -> EquipmentUseSampleSpec:
    """Sample one equipment-use predicate with exact target people."""

    query_id, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=runtime.supported_query_ids,
        default_query_id=SINGLE_QUERY_ID,
        task_id=str(runtime.namespace),
        namespace=f"{runtime.namespace}:query",
    )
    rng = spawned_task_rng(int(instance_seed), str(runtime.namespace), int(attempt_index))
    equipment_values = equipment_support(task_params, runtime.generation_defaults, fallback=("slide", "swing_set", "seesaw", "climbing_frame"))
    target_values = _target_equipment_support(task_params, runtime.generation_defaults, equipment_values)
    target_equipment, equipment_probabilities = support_choice(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{runtime.namespace}:target_equipment_type",
        support=target_values,
        explicit_key="target_equipment_type",
    )
    target_min, target_max = bounds(
        task_params,
        runtime.generation_defaults,
        "target_count_min",
        "target_count_max",
        runtime.defaults.target_count_min,
        runtime.defaults.target_count_max,
    )
    target_count, target_probabilities = sample_count(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{runtime.namespace}:target_count",
        low=int(target_min),
        high=int(target_max),
        explicit_key="target_count",
    )
    equipment_min, equipment_max = bounds(
        task_params,
        runtime.generation_defaults,
        "equipment_count_min",
        "equipment_count_max",
        runtime.defaults.equipment_count_min,
        runtime.defaults.equipment_count_max,
    )
    distractor_equipment = [str(value) for value in equipment_values if str(value) != str(target_equipment)]
    if not distractor_equipment:
        raise ValueError("equipment-use count needs at least one distractor equipment type")
    target_equipment_count = max(1, min(3, int(math.ceil(float(target_count) / 2.0))))
    equipment_count, equipment_count_probabilities = sample_count(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{runtime.namespace}:equipment_count",
        low=max(int(equipment_min), int(target_equipment_count) + min(2, len(distractor_equipment))),
        high=int(equipment_max),
        explicit_key="equipment_count",
    )
    person_min, person_max = bounds(
        task_params,
        runtime.generation_defaults,
        "person_count_min",
        "person_count_max",
        runtime.defaults.person_count_min,
        runtime.defaults.person_count_max,
    )
    person_count, person_probabilities = sample_count(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{runtime.namespace}:person_count",
        low=max(int(person_min), int(target_count) + 3),
        high=int(person_max),
        explicit_key="person_count",
    )
    equipment_specs = [
        ParkEquipmentSpec(equipment_type=str(target_equipment), role="target_user_equipment")
        for _ in range(int(target_equipment_count))
    ]
    for index in range(int(equipment_count) - int(target_equipment_count)):
        equipment_type = str(distractor_equipment[index]) if index < len(distractor_equipment) else str(rng.choice(tuple(distractor_equipment)))
        equipment_specs.append(ParkEquipmentSpec(equipment_type=equipment_type, role="distractor"))
    rng.shuffle(equipment_specs)
    person_specs = [
        ParkPersonSpec(
            activity=_usage_activity(str(target_equipment)),
            role="target",
            attributes={
                "using_equipment_type": str(target_equipment),
                "using_equipment_name": _usage_label(str(target_equipment)),
                "suppress_activity_support": True,
            },
        )
        for _ in range(int(target_count))
    ]
    actual_distractors = sorted({str(spec.equipment_type) for spec in equipment_specs if str(spec.equipment_type) != str(target_equipment)})
    usage_distractors = [value for value in actual_distractors if value in {"slide", "swing_set", "seesaw", "climbing_frame"}]
    remaining_people = int(person_count) - int(target_count)
    usage_distractor_count = min(max(0, remaining_people - 2), min(4, max(1, len(usage_distractors)))) if usage_distractors else 0
    for index in range(int(usage_distractor_count)):
        distractor_type = str(usage_distractors[index % len(usage_distractors)])
        person_specs.append(
            ParkPersonSpec(
                activity=_usage_activity(distractor_type),
                role="distractor_equipment_user",
                attributes={
                    "using_equipment_type": distractor_type,
                    "using_equipment_name": _usage_label(distractor_type),
                    "suppress_activity_support": True,
                },
            )
        )
    normal_activities = tuple(value for value in PARK_PERSON_ACTIVITIES if value != "playing_ball")
    for _ in range(int(person_count) - len(person_specs)):
        person_specs.append(ParkPersonSpec(activity=str(rng.choice(normal_activities)), role="distractor"))
    rng.shuffle(person_specs)
    return EquipmentUseSampleSpec(
        query_id=str(query_id),
        target_equipment_type=str(target_equipment),
        equipment_name=_usage_label(str(target_equipment)),
        target_count=int(target_count),
        equipment_count=int(equipment_count),
        person_count=int(person_count),
        equipment_specs=tuple(equipment_specs),
        person_specs=tuple(person_specs),
        query_probabilities=dict(query_probabilities),
        target_equipment_probabilities=dict(equipment_probabilities),
        target_count_probabilities=dict(target_probabilities),
        equipment_count_probabilities=dict(equipment_count_probabilities),
        person_count_probabilities=dict(person_probabilities),
    )


def sample_equipment_items(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int, runtime: CountRuntime) -> EquipmentSampleSpec:
    """Sample one equipment type with exact target and distractor equipment."""

    query_id, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=runtime.supported_query_ids,
        default_query_id=SINGLE_QUERY_ID,
        task_id=str(runtime.namespace),
        namespace=f"{runtime.namespace}:query",
    )
    rng = spawned_task_rng(int(instance_seed), str(runtime.namespace), int(attempt_index))
    equipment_values = equipment_support(task_params, runtime.generation_defaults, fallback=PARK_EQUIPMENT_TYPES)
    target_equipment, equipment_probabilities = support_choice(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{runtime.namespace}:target_equipment_type",
        support=equipment_values,
        explicit_key="target_equipment_type",
    )
    target_min, target_max = bounds(
        task_params,
        runtime.generation_defaults,
        "target_count_min",
        "target_count_max",
        runtime.defaults.target_count_min,
        runtime.defaults.target_count_max,
    )
    target_count, target_probabilities = sample_count(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{runtime.namespace}:target_count",
        low=int(target_min),
        high=int(target_max),
        explicit_key="target_count",
    )
    equipment_min, equipment_max = bounds(
        task_params,
        runtime.generation_defaults,
        "equipment_count_min",
        "equipment_count_max",
        runtime.defaults.equipment_count_min,
        runtime.defaults.equipment_count_max,
    )
    equipment_count, equipment_count_probabilities = sample_count(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{runtime.namespace}:equipment_count",
        low=max(int(equipment_min), int(target_count) + 2),
        high=int(equipment_max),
        explicit_key="equipment_count",
    )
    person_min, person_max = bounds(
        task_params,
        runtime.generation_defaults,
        "person_count_min",
        "person_count_max",
        runtime.defaults.person_count_min,
        runtime.defaults.person_count_max,
    )
    person_count, person_probabilities = sample_count(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{runtime.namespace}:person_count",
        low=int(person_min),
        high=int(person_max),
        explicit_key="person_count",
    )
    distractor_equipment = [str(value) for value in equipment_values if str(value) != str(target_equipment)]
    if not distractor_equipment:
        raise ValueError("equipment count needs at least one distractor equipment type")
    equipment_specs = [ParkEquipmentSpec(equipment_type=str(target_equipment), role="target") for _ in range(int(target_count))]
    for index in range(int(equipment_count) - int(target_count)):
        equipment_type = str(distractor_equipment[index]) if index < len(distractor_equipment) else str(rng.choice(tuple(distractor_equipment)))
        equipment_specs.append(ParkEquipmentSpec(equipment_type=equipment_type, role="distractor"))
    rng.shuffle(equipment_specs)
    person_specs = tuple(
        ParkPersonSpec(activity=str(rng.choice(PARK_PERSON_ACTIVITIES)), role="decor")
        for _ in range(int(person_count))
    )
    return EquipmentSampleSpec(
        query_id=str(query_id),
        target_equipment_type=str(target_equipment),
        equipment_name=park_equipment_display_name(str(target_equipment)),
        target_count=int(target_count),
        equipment_count=int(equipment_count),
        person_count=int(person_count),
        equipment_specs=tuple(equipment_specs),
        person_specs=tuple(person_specs),
        query_probabilities=dict(query_probabilities),
        target_equipment_probabilities=dict(equipment_probabilities),
        target_count_probabilities=dict(target_probabilities),
        equipment_count_probabilities=dict(equipment_count_probabilities),
        person_count_probabilities=dict(person_probabilities),
    )


def run_activity_people(task: Any, *, instance_seed: int, params: Mapping[str, Any], max_attempts: int, runtime: CountRuntime) -> TaskOutput:
    """Generate, render, and bind one activity count output."""

    sample = sample_activity_people(instance_seed=int(instance_seed), params=params, attempt_index=0, runtime=runtime)
    scene = render_scene_with_retries(
        namespace=str(runtime.namespace),
        instance_seed=int(instance_seed),
        params=params,
        render_defaults=runtime.rendering_defaults,
        fallback_width=runtime.defaults.canvas_width,
        fallback_height=runtime.defaults.canvas_height,
        fallback_scale=runtime.defaults.render_scale,
        max_attempts=int(max_attempts),
        person_specs=sample.person_specs,
    )
    serialized_scene, person_bboxes = serialize_park_scene(scene)
    counted_person_ids = tuple(
        str(person.person_id)
        for person in scene.persons
        if str(person.activity) == str(sample.target_activity)
    )
    if len(counted_person_ids) != int(sample.target_count):
        raise RuntimeError("rendered activity count did not match sampled target count")
    annotation_value = sort_park_bboxes(park_person_bbox_map(scene), counted_person_ids)
    prompt_defaults = required_group_defaults(
        runtime.prompt_defaults,
        [
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "answer_hint_person_activity",
            "annotation_hint_person_activity",
            "json_example_person_activity",
            "json_example_answer_only_person_activity",
        ],
        context=f"prompt defaults for {runtime.namespace}",
    )
    slots = {
        "person_count": int(sample.person_count),
        "activity_phrase": str(sample.activity_phrase),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_defaults["answer_hint_person_activity"]).format(activity_phrase=str(sample.activity_phrase)),
        "annotation_hint": str(prompt_defaults["annotation_hint_person_activity"]).format(activity_phrase=str(sample.activity_phrase)),
        "json_example": str(prompt_defaults["json_example_person_activity"]),
        "json_example_answer_only": str(prompt_defaults["json_example_answer_only_person_activity"]),
    }
    return compose_count_result(
        task=task,
        scene=scene,
        prompt_defaults=prompt_defaults,
        prompt_required_keys=tuple(prompt_defaults.keys()),
        prompt_query_key=runtime.prompt_query_key,
        slots=slots,
        instance_seed=int(instance_seed),
        answer=int(sample.target_count),
        annotation_value=annotation_value,
        render_map={"person_bboxes_px": person_bboxes, "counted_person_ids": list(counted_person_ids)},
        scene_relations={"query_id": str(sample.query_id), "target_activity": str(sample.target_activity)},
        query_params={
            "query_id": str(sample.query_id),
            "target_activity": str(sample.target_activity),
            "activity_phrase": str(sample.activity_phrase),
            "target_count": int(sample.target_count),
            "person_count": int(sample.person_count),
            "query_id_probabilities": dict(sample.query_probabilities),
            "target_activity_probabilities": dict(sample.target_activity_probabilities),
            "target_count_probabilities": dict(sample.target_count_probabilities),
            "person_count_probabilities": dict(sample.person_count_probabilities),
        },
        execution_trace={
            "query_id": str(sample.query_id),
            "scene_id": _SCENE_ID,
            "target_activity": str(sample.target_activity),
            "target_activity_phrase": str(sample.activity_phrase),
            "target_count": int(sample.target_count),
            "person_count": int(sample.person_count),
            "activity_counts": dict(Counter(str(person.activity) for person in scene.persons)),
            "counted_person_ids": list(counted_person_ids),
            "persons": serialized_scene[0]["persons"],
            "decor": serialized_scene[0]["decor"],
            "setting_id": str(scene.setting_id),
            "layout": dict(scene.layout),
        },
        witness_symbolic={"counted_person_ids": list(counted_person_ids), "target_activity": str(sample.target_activity), "answer": int(sample.target_count)},
        scene_entities=park_scene_entities(scene),
    )


def run_area_people(task: Any, *, instance_seed: int, params: Mapping[str, Any], max_attempts: int, runtime: CountRuntime) -> TaskOutput:
    """Generate, render, and bind one area count output."""

    sample = sample_area_people(instance_seed=int(instance_seed), params=params, attempt_index=0, runtime=runtime)
    scene = render_scene_with_retries(
        namespace=str(runtime.namespace),
        instance_seed=int(instance_seed),
        params=params,
        render_defaults=runtime.rendering_defaults,
        fallback_width=runtime.defaults.canvas_width,
        fallback_height=runtime.defaults.canvas_height,
        fallback_scale=runtime.defaults.render_scale,
        max_attempts=int(max_attempts),
        person_specs=sample.person_specs,
        required_zones=(str(sample.target_zone),),
    )
    serialized_scene, person_bboxes = serialize_park_scene(scene)
    counted_person_ids = tuple(
        str(person.person_id)
        for person in scene.persons
        if str(person.attributes.get("zone")) == str(sample.target_zone)
    )
    if len(counted_person_ids) != int(sample.target_count):
        raise RuntimeError("rendered area count did not match sampled target count")
    annotation_value = sort_park_bboxes(park_person_bbox_map(scene), counted_person_ids)
    prompt_defaults = required_group_defaults(
        runtime.prompt_defaults,
        [
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "answer_hint_person_in_park_zone",
            "annotation_hint_person_in_park_zone",
            "json_example_person_in_park_zone",
            "json_example_answer_only_person_in_park_zone",
        ],
        context=f"prompt defaults for {runtime.namespace}",
    )
    slots = {
        "person_count": int(sample.person_count),
        "zone_name": str(sample.zone_name),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_defaults["answer_hint_person_in_park_zone"]).format(zone_name=str(sample.zone_name)),
        "annotation_hint": str(prompt_defaults["annotation_hint_person_in_park_zone"]).format(zone_name=str(sample.zone_name)),
        "json_example": str(prompt_defaults["json_example_person_in_park_zone"]),
        "json_example_answer_only": str(prompt_defaults["json_example_answer_only_person_in_park_zone"]),
    }
    return compose_count_result(
        task=task,
        scene=scene,
        prompt_defaults=prompt_defaults,
        prompt_required_keys=tuple(prompt_defaults.keys()),
        prompt_query_key=runtime.prompt_query_key,
        slots=slots,
        instance_seed=int(instance_seed),
        answer=int(sample.target_count),
        annotation_value=annotation_value,
        render_map={"person_bboxes_px": person_bboxes, "counted_person_ids": list(counted_person_ids)},
        scene_relations={"query_id": str(sample.query_id), "target_zone": str(sample.target_zone)},
        query_params={
            "query_id": str(sample.query_id),
            "target_zone": str(sample.target_zone),
            "zone_name": str(sample.zone_name),
            "target_count": int(sample.target_count),
            "person_count": int(sample.person_count),
            "query_id_probabilities": dict(sample.query_probabilities),
            "target_zone_probabilities": dict(sample.target_zone_probabilities),
            "target_count_probabilities": dict(sample.target_count_probabilities),
            "person_count_probabilities": dict(sample.person_count_probabilities),
        },
        execution_trace={
            "query_id": str(sample.query_id),
            "scene_id": _SCENE_ID,
            "target_zone": str(sample.target_zone),
            "target_zone_name": str(sample.zone_name),
            "target_count": int(sample.target_count),
            "person_count": int(sample.person_count),
            "zone_counts": dict(Counter(str(person.attributes.get("zone")) for person in scene.persons)),
            "counted_person_ids": list(counted_person_ids),
            "persons": serialized_scene[0]["persons"],
            "decor": serialized_scene[0]["decor"],
            "setting_id": str(scene.setting_id),
            "layout": dict(scene.layout),
        },
        witness_symbolic={"counted_person_ids": list(counted_person_ids), "target_zone": str(sample.target_zone), "answer": int(sample.target_count)},
        scene_entities=park_scene_entities(scene),
    )


def run_equipment_users(task: Any, *, instance_seed: int, params: Mapping[str, Any], max_attempts: int, runtime: CountRuntime) -> TaskOutput:
    """Generate, render, and bind one equipment-user count output."""

    sample = sample_equipment_users(instance_seed=int(instance_seed), params=params, attempt_index=0, runtime=runtime)
    scene = render_scene_with_retries(
        namespace=str(runtime.namespace),
        instance_seed=int(instance_seed),
        params=params,
        render_defaults=runtime.rendering_defaults,
        fallback_width=runtime.defaults.canvas_width,
        fallback_height=runtime.defaults.canvas_height,
        fallback_scale=runtime.defaults.render_scale,
        max_attempts=int(max_attempts),
        person_specs=sample.person_specs,
        equipment_specs=sample.equipment_specs,
    )
    serialized_scene, person_bboxes = serialize_park_scene(scene)
    decor_bboxes = park_decor_bbox_map(scene)
    counted_person_ids = tuple(
        str(person.person_id)
        for person in scene.persons
        if str(person.attributes.get("using_equipment_type", "")) == str(sample.target_equipment_type)
    )
    if len(counted_person_ids) != int(sample.target_count):
        raise RuntimeError("rendered equipment-use count did not match sampled target count")
    annotation_value = sort_park_bboxes(park_person_bbox_map(scene), counted_person_ids)
    prompt_defaults = required_group_defaults(
        runtime.prompt_defaults,
        [
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "answer_hint_person_using_equipment",
            "annotation_hint_person_using_equipment",
            "json_example_person_using_equipment",
            "json_example_answer_only_person_using_equipment",
        ],
        context=f"prompt defaults for {runtime.namespace}",
    )
    slots = {
        "person_count": int(sample.person_count),
        "equipment_name": str(sample.equipment_name),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_defaults["answer_hint_person_using_equipment"]).format(equipment_name=str(sample.equipment_name)),
        "annotation_hint": str(prompt_defaults["annotation_hint_person_using_equipment"]).format(equipment_name=str(sample.equipment_name)),
        "json_example": str(prompt_defaults["json_example_person_using_equipment"]),
        "json_example_answer_only": str(prompt_defaults["json_example_answer_only_person_using_equipment"]),
    }
    equipment_counts = dict(Counter(str(item.decor_type) for item in scene.decor if str(item.decor_id).startswith("equipment_")))
    return compose_count_result(
        task=task,
        scene=scene,
        prompt_defaults=prompt_defaults,
        prompt_required_keys=tuple(prompt_defaults.keys()),
        prompt_query_key=runtime.prompt_query_key,
        slots=slots,
        instance_seed=int(instance_seed),
        answer=int(sample.target_count),
        annotation_value=annotation_value,
        render_map={"person_bboxes_px": person_bboxes, "decor_bboxes_px": decor_bboxes, "counted_person_ids": list(counted_person_ids)},
        scene_relations={"query_id": str(sample.query_id), "target_equipment_type": str(sample.target_equipment_type)},
        query_params={
            "query_id": str(sample.query_id),
            "target_equipment_type": str(sample.target_equipment_type),
            "equipment_name": str(sample.equipment_name),
            "target_count": int(sample.target_count),
            "equipment_count": int(sample.equipment_count),
            "person_count": int(sample.person_count),
            "query_id_probabilities": dict(sample.query_probabilities),
            "target_equipment_probabilities": dict(sample.target_equipment_probabilities),
            "target_count_probabilities": dict(sample.target_count_probabilities),
            "equipment_count_probabilities": dict(sample.equipment_count_probabilities),
            "person_count_probabilities": dict(sample.person_count_probabilities),
        },
        execution_trace={
            "query_id": str(sample.query_id),
            "scene_id": _SCENE_ID,
            "target_equipment_type": str(sample.target_equipment_type),
            "target_equipment_name": str(sample.equipment_name),
            "target_count": int(sample.target_count),
            "equipment_count": int(sample.equipment_count),
            "person_count": int(sample.person_count),
            "usage_counts": dict(Counter(str(person.attributes.get("using_equipment_type", "none")) for person in scene.persons)),
            "equipment_counts": equipment_counts,
            "counted_person_ids": list(counted_person_ids),
            "persons": serialized_scene[0]["persons"],
            "decor": serialized_scene[0]["decor"],
            "setting_id": str(scene.setting_id),
            "layout": dict(scene.layout),
        },
        witness_symbolic={"counted_person_ids": list(counted_person_ids), "target_equipment_type": str(sample.target_equipment_type), "answer": int(sample.target_count)},
        scene_entities=park_scene_entities(scene),
    )


def run_equipment_items(task: Any, *, instance_seed: int, params: Mapping[str, Any], max_attempts: int, runtime: CountRuntime) -> TaskOutput:
    """Generate, render, and bind one equipment item count output."""

    sample = sample_equipment_items(instance_seed=int(instance_seed), params=params, attempt_index=0, runtime=runtime)
    scene = render_scene_with_retries(
        namespace=str(runtime.namespace),
        instance_seed=int(instance_seed),
        params=params,
        render_defaults=runtime.rendering_defaults,
        fallback_width=runtime.defaults.canvas_width,
        fallback_height=runtime.defaults.canvas_height,
        fallback_scale=runtime.defaults.render_scale,
        max_attempts=int(max_attempts),
        person_specs=sample.person_specs,
        equipment_specs=sample.equipment_specs,
    )
    serialized_scene, _person_bboxes = serialize_park_scene(scene)
    decor_bboxes = park_decor_bbox_map(scene)
    counted_equipment_ids = tuple(
        str(item.decor_id)
        for item in scene.decor
        if str(item.decor_id).startswith("equipment_") and str(item.decor_type) == str(sample.target_equipment_type)
    )
    if len(counted_equipment_ids) != int(sample.target_count):
        raise RuntimeError("rendered equipment count did not match sampled target count")
    annotation_value = sort_park_bboxes(decor_bboxes, counted_equipment_ids)
    prompt_defaults = required_group_defaults(
        runtime.prompt_defaults,
        [
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "answer_hint_playground_equipment",
            "annotation_hint_playground_equipment",
            "json_example_playground_equipment",
            "json_example_answer_only_playground_equipment",
        ],
        context=f"prompt defaults for {runtime.namespace}",
    )
    slots = {
        "person_count": int(sample.person_count),
        "equipment_name": str(sample.equipment_name),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_defaults["answer_hint_playground_equipment"]).format(equipment_name=str(sample.equipment_name)),
        "annotation_hint": str(prompt_defaults["annotation_hint_playground_equipment"]).format(equipment_name=str(sample.equipment_name)),
        "json_example": str(prompt_defaults["json_example_playground_equipment"]),
        "json_example_answer_only": str(prompt_defaults["json_example_answer_only_playground_equipment"]),
    }
    return compose_count_result(
        task=task,
        scene=scene,
        prompt_defaults=prompt_defaults,
        prompt_required_keys=tuple(prompt_defaults.keys()),
        prompt_query_key=runtime.prompt_query_key,
        slots=slots,
        instance_seed=int(instance_seed),
        answer=int(sample.target_count),
        annotation_value=annotation_value,
        render_map={"decor_bboxes_px": decor_bboxes, "counted_equipment_ids": list(counted_equipment_ids)},
        scene_relations={"query_id": str(sample.query_id), "target_equipment_type": str(sample.target_equipment_type)},
        query_params={
            "query_id": str(sample.query_id),
            "target_equipment_type": str(sample.target_equipment_type),
            "equipment_name": str(sample.equipment_name),
            "target_count": int(sample.target_count),
            "equipment_count": int(sample.equipment_count),
            "person_count": int(sample.person_count),
            "query_id_probabilities": dict(sample.query_probabilities),
            "target_equipment_probabilities": dict(sample.target_equipment_probabilities),
            "target_count_probabilities": dict(sample.target_count_probabilities),
            "equipment_count_probabilities": dict(sample.equipment_count_probabilities),
            "person_count_probabilities": dict(sample.person_count_probabilities),
        },
        execution_trace={
            "query_id": str(sample.query_id),
            "scene_id": _SCENE_ID,
            "target_equipment_type": str(sample.target_equipment_type),
            "target_equipment_name": str(sample.equipment_name),
            "target_count": int(sample.target_count),
            "equipment_count": int(sample.equipment_count),
            "person_count": int(sample.person_count),
            "equipment_counts": dict(Counter(str(item.decor_type) for item in scene.decor if str(item.decor_id).startswith("equipment_"))),
            "counted_equipment_ids": list(counted_equipment_ids),
            "persons": serialized_scene[0]["persons"],
            "decor": serialized_scene[0]["decor"],
            "setting_id": str(scene.setting_id),
            "layout": dict(scene.layout),
        },
        witness_symbolic={"counted_equipment_ids": list(counted_equipment_ids), "target_equipment_type": str(sample.target_equipment_type), "answer": int(sample.target_count)},
        scene_entities=park_scene_entities(scene),
    )


__all__ = [
    "CountDefaults",
    "CountRuntime",
    "build_count_runtime",
    "run_activity_people",
    "run_area_people",
    "run_equipment_items",
    "run_equipment_users",
    "sample_activity_people",
    "sample_area_people",
    "sample_equipment_items",
    "sample_equipment_users",
]
