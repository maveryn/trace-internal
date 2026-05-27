"""Count people using named playground equipment in a park/playground scene."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
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
from ..shared.park_playground_scene import (
    PARK_PERSON_ACTIVITIES,
    ParkEquipmentSpec,
    ParkPersonSpec,
    park_decor_bbox_map,
    park_person_bbox_map,
    park_scene_entities,
    render_park_playground_scene,
    serialize_park_scene,
    sort_park_bboxes,
)
from ..shared.park_task_common import (
    bounds,
    equipment_support,
    render_params,
    sample_count,
    setting_weights,
    spawned_task_rng,
    style_weights,
    uniform_string_probability_map,
)


TASK_ID = "private_park_person_equipment_use"
SCENE_ID = "park_playground"
QUERY_IDS: Tuple[str, ...] = (
    "person_using_slide_count",
    "person_using_swing_set_count",
    "person_using_seesaw_count",
)
_QUERY_EQUIPMENT: Dict[str, str] = {
    "person_using_slide_count": "slide",
    "person_using_swing_set_count": "swing_set",
    "person_using_seesaw_count": "seesaw",
}
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


@dataclass(frozen=True)
class _Defaults:
    equipment_count_min: int = 4
    equipment_count_max: int = 7
    person_count_min: int = 8
    person_count_max: int = 14
    target_count_min: int = 1
    target_count_max: int = 5
    canvas_width: int = 1280
    canvas_height: int = 900
    render_scale: int = 2


@dataclass(frozen=True)
class _SampleSpec:
    query_id: str
    equipment_type: str
    equipment_name: str
    target_count: int
    equipment_count: int
    person_count: int
    equipment_specs: Tuple[ParkEquipmentSpec, ...]
    person_specs: Tuple[ParkPersonSpec, ...]
    query_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    equipment_count_probabilities: Dict[str, float]
    person_count_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)




def _usage_label(equipment_type: str) -> str:
    return _USAGE_EQUIPMENT_LABELS.get(str(equipment_type), str(equipment_type).replace("_", " ") + "s")


def _usage_activity(equipment_type: str) -> str:
    return _EQUIPMENT_ACTIVITY.get(str(equipment_type), "standing")


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int) -> _SampleSpec:
    rng = spawned_task_rng(int(instance_seed), TASK_ID, int(attempt_index))
    base_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:cycle")
    query_values = _shared_query_support(params, _GEN_DEFAULTS, QUERY_IDS)
    equipment_values = equipment_support(params, _GEN_DEFAULTS, fallback=("slide", "swing_set", "seesaw", "climbing_frame"))
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
    equipment_type = str(_QUERY_EQUIPMENT[str(query_id)])
    if equipment_type not in set(equipment_values):
        raise ValueError("query equipment is outside configured equipment support")

    target_count, target_probabilities = sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:target_count",
        low=int(target_min),
        high=int(target_max),
        explicit_key="target_count",
        cycle_index=int(base_index),
    )

    equipment_min, equipment_max = bounds(
        params,
        _GEN_DEFAULTS,
        "equipment_count_min",
        "equipment_count_max",
        _DEFAULTS.equipment_count_min,
        _DEFAULTS.equipment_count_max,
    )
    distractor_equipment = [str(value) for value in equipment_values if str(value) != str(equipment_type)]
    if not distractor_equipment:
        raise ValueError("person-using-equipment task needs at least one distractor equipment type")
    target_equipment_count = max(1, min(3, int(math.ceil(float(target_count) / 2.0))))
    equipment_low = max(int(equipment_min), int(target_equipment_count) + min(2, len(distractor_equipment)))
    equipment_count, equipment_count_probabilities = sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:equipment_count",
        low=int(equipment_low),
        high=int(equipment_max),
        explicit_key="equipment_count",
        cycle_index=int(base_index // max(1, len(query_values) * int(target_max - target_min + 1))),
    )

    person_min, person_max = bounds(
        params,
        _GEN_DEFAULTS,
        "person_count_min",
        "person_count_max",
        _DEFAULTS.person_count_min,
        _DEFAULTS.person_count_max,
    )
    person_low = max(int(person_min), int(target_count) + 3)
    person_count, person_count_probabilities = sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:person_count",
        low=int(person_low),
        high=int(person_max),
        explicit_key="person_count",
        cycle_index=int(base_index // max(1, len(query_values) * int(target_max - target_min + 1) * max(1, int(equipment_max - equipment_min + 1)))),
    )

    equipment_specs = [
        ParkEquipmentSpec(equipment_type=str(equipment_type), role="target_user_equipment")
        for _ in range(int(target_equipment_count))
    ]
    for index in range(int(equipment_count) - int(target_equipment_count)):
        if index < len(distractor_equipment):
            distractor = str(distractor_equipment[index])
        else:
            distractor = str(rng.choice(tuple(distractor_equipment)))
        equipment_specs.append(ParkEquipmentSpec(equipment_type=str(distractor), role="distractor"))
    rng.shuffle(equipment_specs)

    person_specs = [
        ParkPersonSpec(
            activity=_usage_activity(str(equipment_type)),
            role="target",
            attributes={
                "using_equipment_type": str(equipment_type),
                "using_equipment_name": _usage_label(str(equipment_type)),
                "suppress_activity_support": True,
            },
        )
        for _ in range(int(target_count))
    ]
    actual_distractor_equipment = sorted({str(spec.equipment_type) for spec in equipment_specs if str(spec.equipment_type) != str(equipment_type)})
    usage_distractor_types = [value for value in actual_distractor_equipment if value in {"slide", "swing_set", "seesaw", "climbing_frame"}]
    remaining_persons = int(person_count) - int(target_count)
    usage_distractor_count = min(max(0, remaining_persons - 2), min(4, max(1, len(usage_distractor_types)))) if usage_distractor_types else 0
    for index in range(int(usage_distractor_count)):
        distractor_type = str(usage_distractor_types[index % len(usage_distractor_types)])
        person_specs.append(
            ParkPersonSpec(
                activity=_usage_activity(str(distractor_type)),
                role="distractor_equipment_user",
                attributes={
                    "using_equipment_type": str(distractor_type),
                    "using_equipment_name": _usage_label(str(distractor_type)),
                    "suppress_activity_support": True,
                },
            )
        )
    normal_activities = tuple(value for value in PARK_PERSON_ACTIVITIES if value != "playing_ball")
    for _ in range(int(person_count) - len(person_specs)):
        person_specs.append(ParkPersonSpec(activity=str(rng.choice(normal_activities)), role="distractor"))
    rng.shuffle(person_specs)

    return _SampleSpec(
        query_id=str(query_id),
        equipment_type=str(equipment_type),
        equipment_name=_usage_label(str(equipment_type)),
        target_count=int(target_count),
        equipment_count=int(equipment_count),
        person_count=int(person_count),
        equipment_specs=tuple(equipment_specs),
        person_specs=tuple(person_specs),
        query_probabilities=dict(query_probabilities),
        target_count_probabilities=dict(target_probabilities),
        equipment_count_probabilities=dict(equipment_count_probabilities),
        person_count_probabilities=dict(person_count_probabilities),
    )


def _build_complexity(sample: _SampleSpec) -> TaskComplexity:
    person_scan = (int(sample.person_count) - _DEFAULTS.person_count_min) / max(1, _DEFAULTS.person_count_max - _DEFAULTS.person_count_min)
    answer_load = (int(sample.target_count) - _DEFAULTS.target_count_min) / max(1, _DEFAULTS.target_count_max - _DEFAULTS.target_count_min)
    equipment_load = (int(sample.equipment_count) - _DEFAULTS.equipment_count_min) / max(1, _DEFAULTS.equipment_count_max - _DEFAULTS.equipment_count_min)
    score = 0.42 * max(0.0, min(1.0, person_scan)) + 0.36 * max(0.0, min(1.0, answer_load)) + 0.22 * max(0.0, min(1.0, equipment_load))
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "person_scan": round(float(person_scan), 6),
            "answer_load": round(float(answer_load), 6),
            "equipment_load": round(float(equipment_load), 6),
            "equipment_type": str(sample.equipment_type),
            "target_count": int(sample.target_count),
            "equipment_count": int(sample.equipment_count),
            "person_count": int(sample.person_count),
        },
    )


class ParkPersonEquipmentUseBranch:
    """Count people using a named playground equipment type."""

    task_id = TASK_ID
    branch_id = "park_person_equipment_use"
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
                scene = render_park_playground_scene(
                    rng=scene_rng,
                    person_specs=sample.person_specs,
                    equipment_specs=sample.equipment_specs,
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

        serialized_scene, person_bboxes = serialize_park_scene(scene)
        decor_bboxes = park_decor_bbox_map(scene)
        counted_person_ids = tuple(
            str(person.person_id)
            for person in scene.persons
            if str(person.attributes.get("using_equipment_type", "")) == str(sample.equipment_type)
        )
        if len(counted_person_ids) != int(sample.target_count):
            raise RuntimeError("rendered person-using-equipment count did not match sample target")
        evidence_value = sort_park_bboxes(park_person_bbox_map(scene), counted_person_ids)
        usage_counts = dict(Counter(str(person.attributes.get("using_equipment_type", "none")) for person in scene.persons))
        equipment_counts = dict(Counter(str(item.decor_type) for item in scene.decor if str(item.decor_id).startswith("equipment_")))

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_person_using_equipment",
                "evidence_hint_person_using_equipment",
                "json_example_person_using_equipment",
                "json_example_answer_only_person_using_equipment",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        slots = {
            "person_count": int(sample.person_count),
            "equipment_name": str(sample.equipment_name),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_person_using_equipment"]).format(equipment_name=str(sample.equipment_name)),
            "evidence_hint": str(prompt_defaults["evidence_hint_person_using_equipment"]).format(equipment_name=str(sample.equipment_name)),
            "json_example": str(prompt_defaults["json_example_person_using_equipment"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_person_using_equipment"]),
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
                "entities": park_scene_entities(scene),
                "relations": {
                    "query_variant": str(sample.query_id),
                    "query_id": str(sample.query_id),
                    "target_equipment_type": str(sample.equipment_type),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_variant": str(sample.query_id),
                "query_id": str(sample.query_id),
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "equipment_type": str(sample.equipment_type),
                    "equipment_name": str(sample.equipment_name),
                    "target_count": int(sample.target_count),
                    "equipment_count": int(sample.equipment_count),
                    "person_count": int(sample.person_count),
                    "query_probabilities": dict(sample.query_probabilities),
                    "query_variant_probabilities": dict(sample.query_probabilities),
                    "target_count_probabilities": dict(sample.target_count_probabilities),
                    "equipment_count_probabilities": dict(sample.equipment_count_probabilities),
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
                "decor_bboxes_px": decor_bboxes,
                "counted_person_ids": list(counted_person_ids),
            },
            "execution_trace": {
                "query_variant": str(sample.query_id),
                "query_id": str(sample.query_id),
                "scene_id": SCENE_ID,
                "target_equipment_type": str(sample.equipment_type),
                "target_equipment_name": str(sample.equipment_name),
                "target_count": int(sample.target_count),
                "equipment_count": int(sample.equipment_count),
                "person_count": int(sample.person_count),
                "usage_counts": usage_counts,
                "equipment_counts": equipment_counts,
                "query_variant_probabilities": dict(sample.query_probabilities),
                "counted_person_ids": list(counted_person_ids),
                "persons": serialized_scene[0]["persons"],
                "decor": serialized_scene[0]["decor"],
                "setting_id": str(scene.setting_id),
                "layout": dict(scene.layout),
            },
            "witness_symbolic": {
                "counted_person_ids": list(counted_person_ids),
                "target_equipment_type": str(sample.equipment_type),
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
            query_variant=str(sample.query_id),
            scene_id=SCENE_ID,
            query_id=str(sample.query_id),
        )


__all__ = ["ParkPersonEquipmentUseBranch"]
