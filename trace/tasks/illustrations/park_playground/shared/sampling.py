"""Shared sampling helpers for park/playground illustration tasks."""

from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Sequence, Tuple

from .....core.query_ids import SINGLE_QUERY_ID
from ....shared.config_defaults import group_default
from ....shared.deterministic_sampling import resolve_selection_index
from ....shared.fixed_query import select_task_query_id
from ...shared.object_library import STYLE_IDS
from ...shared.task_support import (
    bounds,
    render_params as _shared_render_params,
    sample_count,
    spawned_task_rng,
    style_weights as _shared_style_weights,
    uniform_string_probability_map,
)
from .defaults import CountDefaults
from .state import (
    ActivitySampleSpec,
    AreaSampleSpec,
    EquipmentSampleSpec,
    EquipmentUseSampleSpec,
    PARK_EQUIPMENT_TYPES,
    PARK_PERSON_ACTIVITIES,
    PARK_SETTING_IDS,
    PARK_ZONE_TYPES,
    ParkEquipmentSpec,
    ParkPersonSpec,
    park_activity_display_name,
    park_equipment_display_name,
    park_zone_display_name,
)


DEFAULT_TARGET_EQUIPMENT: Tuple[str, ...] = ("slide", "swing_set", "seesaw")
USAGE_EQUIPMENT_LABELS: Dict[str, str] = {
    "slide": "slides",
    "swing_set": "swings",
    "seesaw": "seesaws",
}
EQUIPMENT_ACTIVITY: Dict[str, str] = {
    "slide": "standing",
    "swing_set": "sitting",
    "seesaw": "sitting",
    "climbing_frame": "standing",
}


def activity_support(params: Mapping[str, Any], defaults: Mapping[str, Any], *, fallback: Sequence[str]) -> Tuple[str, ...]:
    """Resolve supported park person activity ids."""

    raw = params.get("activity_support", group_default(defaults, "activity_support", fallback))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("activity_support must be a sequence")
    support = tuple(str(value) for value in raw if str(value) in set(PARK_PERSON_ACTIVITIES))
    if len(support) < 2:
        raise ValueError("activity_support must contain at least two activities")
    return tuple(dict.fromkeys(support))


def equipment_support(params: Mapping[str, Any], defaults: Mapping[str, Any], *, fallback: Sequence[str] = PARK_EQUIPMENT_TYPES) -> Tuple[str, ...]:
    """Resolve supported park playground equipment ids."""

    raw = params.get("equipment_type_support", group_default(defaults, "equipment_type_support", fallback))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("equipment_type_support must be a sequence")
    support = tuple(str(value) for value in raw if str(value) in set(PARK_EQUIPMENT_TYPES))
    if len(support) < 2:
        raise ValueError("equipment_type_support must contain at least two equipment types")
    return tuple(dict.fromkeys(support))


def zone_support(params: Mapping[str, Any], defaults: Mapping[str, Any], *, fallback: Sequence[str] = PARK_ZONE_TYPES) -> Tuple[str, ...]:
    """Resolve supported semantic park zone ids."""

    raw = params.get("zone_support", group_default(defaults, "zone_support", fallback))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("zone_support must be a sequence")
    support = tuple(str(value) for value in raw if str(value) in set(PARK_ZONE_TYPES))
    if len(support) < 2:
        raise ValueError("zone_support must contain at least two park zones")
    return tuple(dict.fromkeys(support))


def support_choice(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    support: Sequence[str],
    explicit_key: str,
) -> Tuple[str, Dict[str, float]]:
    """Choose one supported semantic operand with an explicit override or seed."""

    values = tuple(str(value) for value in support if str(value))
    if not values:
        raise ValueError(f"{explicit_key} support must not be empty")
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        selected = str(explicit)
        if selected not in set(values):
            raise ValueError(f"{explicit_key} is outside configured support")
        return selected, uniform_string_probability_map(values, selected=selected)
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    return str(values[int(index) % len(values)]), uniform_string_probability_map(values)


def render_params(params: Mapping[str, Any], render_defaults: Mapping[str, Any], *, fallback_width: int, fallback_height: int, fallback_scale: int) -> Dict[str, int]:
    """Resolve park canvas render parameters."""

    return _shared_render_params(
        params,
        render_defaults,
        prefix="park",
        fallback_width=fallback_width,
        fallback_height=fallback_height,
        fallback_scale=fallback_scale,
    )


def style_weights(params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> Dict[str, float]:
    """Resolve illustration style weights."""

    return _shared_style_weights(params, render_defaults, style_ids=STYLE_IDS)


def setting_weights(params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> Dict[str, float]:
    """Resolve park setting weights."""

    raw = params.get("park_setting_weights", group_default(render_defaults, "park_setting_weights", {setting: 1.0 for setting in PARK_SETTING_IDS}))
    if not isinstance(raw, Mapping):
        raise ValueError("park_setting_weights must be a mapping")
    return {str(key): max(0.0, float(value)) for key, value in raw.items()}


def usage_label(equipment_type: str) -> str:
    """Return the prompt-facing plural label for equipment use."""

    return USAGE_EQUIPMENT_LABELS.get(str(equipment_type), str(equipment_type).replace("_", " ") + "s")


def usage_activity(equipment_type: str) -> str:
    """Return the person activity used when a person is using equipment."""

    return EQUIPMENT_ACTIVITY.get(str(equipment_type), "standing")


def target_equipment_support(params: Mapping[str, Any], defaults: Mapping[str, Any], equipment_values: Sequence[str]) -> Tuple[str, ...]:
    """Resolve supported target equipment for equipment-use counts."""

    raw = params.get("equipment_use_target_support", group_default(defaults, "equipment_use_target_support", DEFAULT_TARGET_EQUIPMENT))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("equipment_use_target_support must be a sequence")
    available = set(str(value) for value in equipment_values)
    support = tuple(str(value) for value in raw if str(value) in available)
    if not support:
        raise ValueError("equipment_use_target_support resolved no supported target equipment")
    return tuple(dict.fromkeys(support))


def sample_activity_people(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    attempt_index: int,
    namespace: str,
    query_support: Sequence[str],
    generation_defaults: Mapping[str, Any],
    defaults: CountDefaults,
) -> ActivitySampleSpec:
    """Sample one activity predicate with exact target and distractor people."""

    query_id, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=tuple(str(value) for value in query_support),
        default_query_id=SINGLE_QUERY_ID,
        task_id=str(namespace),
        namespace=f"{namespace}:query",
    )
    rng = spawned_task_rng(int(instance_seed), str(namespace), int(attempt_index))
    activities = activity_support(task_params, generation_defaults, fallback=PARK_PERSON_ACTIVITIES)
    target_activity, activity_probabilities = support_choice(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}:target_activity",
        support=activities,
        explicit_key="target_activity",
    )
    target_min, target_max = bounds(
        task_params,
        generation_defaults,
        "target_count_min",
        "target_count_max",
        defaults.target_count_min,
        defaults.target_count_max,
    )
    target_count, target_probabilities = sample_count(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}:target_count",
        low=int(target_min),
        high=int(target_max),
        explicit_key="target_count",
    )
    person_min, person_max = bounds(
        task_params,
        generation_defaults,
        "person_count_min",
        "person_count_max",
        defaults.person_count_min,
        defaults.person_count_max,
    )
    person_count, person_probabilities = sample_count(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}:person_count",
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


def sample_area_people(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    attempt_index: int,
    namespace: str,
    query_support: Sequence[str],
    generation_defaults: Mapping[str, Any],
    defaults: CountDefaults,
) -> AreaSampleSpec:
    """Sample one target area and construct exact target/distractor people."""

    query_id, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=tuple(str(value) for value in query_support),
        default_query_id=SINGLE_QUERY_ID,
        task_id=str(namespace),
        namespace=f"{namespace}:query",
    )
    rng = spawned_task_rng(int(instance_seed), str(namespace), int(attempt_index))
    zones = zone_support(task_params, generation_defaults, fallback=PARK_ZONE_TYPES)
    target_zone, zone_probabilities = support_choice(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}:target_zone",
        support=zones,
        explicit_key="target_zone",
    )
    target_min, target_max = bounds(
        task_params,
        generation_defaults,
        "target_count_min",
        "target_count_max",
        defaults.target_count_min,
        defaults.target_count_max,
    )
    target_count, target_probabilities = sample_count(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}:target_count",
        low=int(target_min),
        high=int(target_max),
        explicit_key="target_count",
    )
    person_min, person_max = bounds(
        task_params,
        generation_defaults,
        "person_count_min",
        "person_count_max",
        defaults.person_count_min,
        defaults.person_count_max,
    )
    person_count, person_probabilities = sample_count(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}:person_count",
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


def sample_equipment_users(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    attempt_index: int,
    namespace: str,
    query_support: Sequence[str],
    generation_defaults: Mapping[str, Any],
    defaults: CountDefaults,
) -> EquipmentUseSampleSpec:
    """Sample one equipment-use predicate with exact target people."""

    query_id, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=tuple(str(value) for value in query_support),
        default_query_id=SINGLE_QUERY_ID,
        task_id=str(namespace),
        namespace=f"{namespace}:query",
    )
    rng = spawned_task_rng(int(instance_seed), str(namespace), int(attempt_index))
    equipment_values = equipment_support(task_params, generation_defaults, fallback=("slide", "swing_set", "seesaw", "climbing_frame"))
    target_values = target_equipment_support(task_params, generation_defaults, equipment_values)
    target_equipment, equipment_probabilities = support_choice(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}:target_equipment_type",
        support=target_values,
        explicit_key="target_equipment_type",
    )
    target_min, target_max = bounds(
        task_params,
        generation_defaults,
        "target_count_min",
        "target_count_max",
        defaults.target_count_min,
        defaults.target_count_max,
    )
    target_count, target_probabilities = sample_count(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}:target_count",
        low=int(target_min),
        high=int(target_max),
        explicit_key="target_count",
    )
    equipment_min, equipment_max = bounds(
        task_params,
        generation_defaults,
        "equipment_count_min",
        "equipment_count_max",
        defaults.equipment_count_min,
        defaults.equipment_count_max,
    )
    distractor_equipment = [str(value) for value in equipment_values if str(value) != str(target_equipment)]
    if not distractor_equipment:
        raise ValueError("equipment-use count needs at least one distractor equipment type")
    target_equipment_count = max(1, min(3, int(math.ceil(float(target_count) / 2.0))))
    equipment_count, equipment_count_probabilities = sample_count(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}:equipment_count",
        low=max(int(equipment_min), int(target_equipment_count) + min(2, len(distractor_equipment))),
        high=int(equipment_max),
        explicit_key="equipment_count",
    )
    person_min, person_max = bounds(
        task_params,
        generation_defaults,
        "person_count_min",
        "person_count_max",
        defaults.person_count_min,
        defaults.person_count_max,
    )
    person_count, person_probabilities = sample_count(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}:person_count",
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
            activity=usage_activity(str(target_equipment)),
            role="target",
            attributes={
                "using_equipment_type": str(target_equipment),
                "using_equipment_name": usage_label(str(target_equipment)),
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
                activity=usage_activity(distractor_type),
                role="distractor_equipment_user",
                attributes={
                    "using_equipment_type": distractor_type,
                    "using_equipment_name": usage_label(distractor_type),
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
        equipment_name=usage_label(str(target_equipment)),
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


def sample_equipment_items(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    attempt_index: int,
    namespace: str,
    query_support: Sequence[str],
    generation_defaults: Mapping[str, Any],
    defaults: CountDefaults,
) -> EquipmentSampleSpec:
    """Sample one equipment type with exact target and distractor equipment."""

    query_id, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=tuple(str(value) for value in query_support),
        default_query_id=SINGLE_QUERY_ID,
        task_id=str(namespace),
        namespace=f"{namespace}:query",
    )
    rng = spawned_task_rng(int(instance_seed), str(namespace), int(attempt_index))
    equipment_values = equipment_support(task_params, generation_defaults, fallback=PARK_EQUIPMENT_TYPES)
    target_equipment, equipment_probabilities = support_choice(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}:target_equipment_type",
        support=equipment_values,
        explicit_key="target_equipment_type",
    )
    target_min, target_max = bounds(
        task_params,
        generation_defaults,
        "target_count_min",
        "target_count_max",
        defaults.target_count_min,
        defaults.target_count_max,
    )
    target_count, target_probabilities = sample_count(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}:target_count",
        low=int(target_min),
        high=int(target_max),
        explicit_key="target_count",
    )
    equipment_min, equipment_max = bounds(
        task_params,
        generation_defaults,
        "equipment_count_min",
        "equipment_count_max",
        defaults.equipment_count_min,
        defaults.equipment_count_max,
    )
    equipment_count, equipment_count_probabilities = sample_count(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}:equipment_count",
        low=max(int(equipment_min), int(target_count) + 2),
        high=int(equipment_max),
        explicit_key="equipment_count",
    )
    person_min, person_max = bounds(
        task_params,
        generation_defaults,
        "person_count_min",
        "person_count_max",
        defaults.person_count_min,
        defaults.person_count_max,
    )
    person_count, person_probabilities = sample_count(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}:person_count",
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


__all__ = [
    "activity_support",
    "bounds",
    "equipment_support",
    "sample_activity_people",
    "sample_area_people",
    "render_params",
    "sample_equipment_items",
    "sample_equipment_users",
    "sample_count",
    "setting_weights",
    "spawned_task_rng",
    "style_weights",
    "support_choice",
    "target_equipment_support",
    "uniform_string_probability_map",
    "usage_activity",
    "usage_label",
    "zone_support",
]
