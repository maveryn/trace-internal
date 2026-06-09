"""Count people standing in one named terminal queue."""

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
    TRANSIT_PERSON_POSES,
    TRANSIT_SERVICE_POINT_IDS,
    TransitPersonSpec,
    render_transit_terminal_scene,
    serialize_transit_scene,
    sort_transit_bboxes,
    transit_person_bbox_map,
    transit_scene_entities,
    transit_service_point_display_name,
)


TASK_ID = "private_terminal_queue_person"
SCENE_ID = "transit_terminal"
QUERY_IDS: Tuple[str, ...] = (
    "person_in_queue_count",
)
_PERSON_POSES_NO_LUGGAGE: Tuple[str, ...] = tuple(pose for pose in TRANSIT_PERSON_POSES if pose != "with_luggage")


@dataclass(frozen=True)
class _Defaults:
    background_person_count_min: int = 6
    background_person_count_max: int = 12
    distractor_queue_count_min: int = 3
    distractor_queue_count_max: int = 7
    target_count_min: int = 2
    target_count_max: int = 7
    canvas_width: int = 1280
    canvas_height: int = 900
    render_scale: int = 2


@dataclass(frozen=True)
class _SampleSpec:
    query_id: str
    service_point_id: str
    service_point_name: str
    target_count: int
    distractor_queue_count: int
    background_person_count: int
    person_count: int
    person_specs: Tuple[TransitPersonSpec, ...]
    query_probabilities: Dict[str, float]
    service_point_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    distractor_queue_count_probabilities: Dict[str, float]
    background_person_count_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)




def _service_point_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("service_point_support", group_default(_GEN_DEFAULTS, "service_point_support", TRANSIT_SERVICE_POINT_IDS))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("service_point_support must be a sequence")
    support = tuple(str(value) for value in raw if str(value) in set(TRANSIT_SERVICE_POINT_IDS))
    if len(support) < 2:
        raise ValueError("service_point_support must contain at least two service points")
    return tuple(dict.fromkeys(support))


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int) -> _SampleSpec:
    rng = spawned_task_rng(int(instance_seed), TASK_ID, int(attempt_index))
    base_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:cycle")
    query_values = _shared_query_support(params, _GEN_DEFAULTS, QUERY_IDS)
    service_values = _service_point_support(params)
    area_values = area_support(params, _GEN_DEFAULTS, fallback=TRANSIT_BOARDING_AREA_IDS)
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

    explicit_service_point = params.get("service_point_id")
    if explicit_service_point is not None:
        service_point_id = str(explicit_service_point)
        if service_point_id not in set(service_values):
            raise ValueError("service_point_id is outside configured support")
        service_index = int(service_values.index(service_point_id))
        service_point_probabilities = uniform_string_probability_map(service_values, selected=service_point_id)
    else:
        service_index = int(base_index // max(1, len(query_values))) % len(service_values)
        service_point_id = str(service_values[service_index])
        service_point_probabilities = uniform_string_probability_map(service_values)

    target_count, target_probabilities = sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:target_count",
        low=int(target_min),
        high=int(target_max),
        explicit_key="target_count",
        cycle_index=int(base_index // max(1, len(query_values) * len(service_values))) + 2 * int(service_index) + int(query_index),
    )
    distractor_min, distractor_max = bounds(
        params,
        _GEN_DEFAULTS,
        "distractor_queue_count_min",
        "distractor_queue_count_max",
        _DEFAULTS.distractor_queue_count_min,
        _DEFAULTS.distractor_queue_count_max,
    )
    distractor_queue_count, distractor_queue_count_probabilities = sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:distractor_queue_count",
        low=int(distractor_min),
        high=int(distractor_max),
        explicit_key="distractor_queue_count",
        cycle_index=int(base_index // max(1, len(query_values) * len(service_values) * int(target_max - target_min + 1))),
    )
    background_min, background_max = bounds(
        params,
        _GEN_DEFAULTS,
        "background_person_count_min",
        "background_person_count_max",
        _DEFAULTS.background_person_count_min,
        _DEFAULTS.background_person_count_max,
    )
    background_person_count, background_person_count_probabilities = sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:background_person_count",
        low=int(background_min),
        high=int(background_max),
        explicit_key="background_person_count",
        cycle_index=int(base_index // max(1, len(query_values) * len(service_values) * int(target_max - target_min + 1) * int(distractor_max - distractor_min + 1))),
    )

    distractor_services = [str(value) for value in service_values if str(value) != str(service_point_id)]
    if not distractor_services:
        raise ValueError("queue person task needs distractor service points")
    person_specs = [
        TransitPersonSpec(
            area_id="concourse",
            role="target",
            attributes={"pose_id": "standing", "queue_member": True, "service_point_id": str(service_point_id)},
        )
        for _ in range(int(target_count))
    ]
    for index in range(int(distractor_queue_count)):
        distractor_service = str(distractor_services[index % len(distractor_services)])
        person_specs.append(
            TransitPersonSpec(
                area_id="concourse",
                role="distractor",
                attributes={"pose_id": "standing", "queue_member": True, "service_point_id": str(distractor_service)},
            )
        )
    person_area_values = tuple(area_values) + ("concourse",)
    for _ in range(int(background_person_count)):
        person_specs.append(
            TransitPersonSpec(
                area_id=str(rng.choice(person_area_values)),
                role="decor",
                attributes={"pose_id": str(rng.choice(_PERSON_POSES_NO_LUGGAGE))},
            )
        )
    rng.shuffle(person_specs)
    return _SampleSpec(
        query_id=str(query_id),
        service_point_id=str(service_point_id),
        service_point_name=transit_service_point_display_name(str(service_point_id)),
        target_count=int(target_count),
        distractor_queue_count=int(distractor_queue_count),
        background_person_count=int(background_person_count),
        person_count=int(len(person_specs)),
        person_specs=tuple(person_specs),
        query_probabilities=dict(query_probabilities),
        service_point_probabilities=dict(service_point_probabilities),
        target_count_probabilities=dict(target_probabilities),
        distractor_queue_count_probabilities=dict(distractor_queue_count_probabilities),
        background_person_count_probabilities=dict(background_person_count_probabilities),
    )


def _build_complexity(sample: _SampleSpec) -> TaskComplexity:
    queue_scan = (int(sample.target_count) + int(sample.distractor_queue_count) - _DEFAULTS.target_count_min - _DEFAULTS.distractor_queue_count_min) / max(1, (_DEFAULTS.target_count_max - _DEFAULTS.target_count_min) + (_DEFAULTS.distractor_queue_count_max - _DEFAULTS.distractor_queue_count_min))
    answer_load = (int(sample.target_count) - _DEFAULTS.target_count_min) / max(1, _DEFAULTS.target_count_max - _DEFAULTS.target_count_min)
    background_clutter = (int(sample.background_person_count) - _DEFAULTS.background_person_count_min) / max(1, _DEFAULTS.background_person_count_max - _DEFAULTS.background_person_count_min)
    score = 0.42 * max(0.0, min(1.0, queue_scan)) + 0.34 * max(0.0, min(1.0, answer_load)) + 0.24 * max(0.0, min(1.0, background_clutter))
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "queue_scan": round(float(queue_scan), 6),
            "answer_load": round(float(answer_load), 6),
            "background_clutter": round(float(background_clutter), 6),
        },
    )


class TerminalQueuePersonBranch:
    """Count people standing in one named terminal queue."""

    task_id = TASK_ID
    branch_id = "terminal_queue_person"
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
                    canvas_width=int(rp["canvas_width"]),
                    canvas_height=int(rp["canvas_height"]),
                    render_scale=int(rp["render_scale"]),
                    setting_weights=setting_weights(params, _RENDER_DEFAULTS),
                    style_weights=style_weights(params, _RENDER_DEFAULTS),
                    show_service_points=True,
                )
                break
            except Exception as exc:  # pragma: no cover
                last_error = exc
                sample = None
                scene = None
        if scene is None or sample is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        serialized_scene, person_bboxes = serialize_transit_scene(scene)
        counted_person_ids = tuple(
            str(person.person_id)
            for person in scene.persons
            if bool(person.attributes.get("queue_member")) and str(person.attributes.get("service_point_id")) == str(sample.service_point_id)
        )
        if len(counted_person_ids) != int(sample.target_count):
            raise RuntimeError("rendered queue person count did not match sample target")
        annotation_value = sort_transit_bboxes(transit_person_bbox_map(scene), counted_person_ids)
        queue_counts = dict(Counter(str(person.attributes.get("service_point_id")) for person in scene.persons if bool(person.attributes.get("queue_member"))))

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_queue_person",
                "annotation_hint_queue_person",
                "json_example_queue_person",
                "json_example_answer_only_queue_person",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        slots = {
            "person_count": int(sample.person_count),
            "service_point_name": str(sample.service_point_name),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_queue_person"]).format(service_point_name=str(sample.service_point_name)),
            "annotation_hint": str(prompt_defaults["annotation_hint_queue_person"]).format(service_point_name=str(sample.service_point_name)),
            "json_example": str(prompt_defaults["json_example_queue_person"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_queue_person"]),
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
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            preferred_mode="answer_and_annotation",
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        trace_payload = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "entities": transit_scene_entities(scene),
                "relations": {
                    "query_id": str(sample.query_id),
                    "target_service_point_id": str(sample.service_point_id),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_id": str(sample.query_id),
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "service_point_id": str(sample.service_point_id),
                    "service_point_name": str(sample.service_point_name),
                    "target_count": int(sample.target_count),
                    "distractor_queue_count": int(sample.distractor_queue_count),
                    "background_person_count": int(sample.background_person_count),
                    "person_count": int(sample.person_count),
                    "query_probabilities": dict(sample.query_probabilities),
                    "service_point_probabilities": dict(sample.service_point_probabilities),
                    "target_count_probabilities": dict(sample.target_count_probabilities),
                    "distractor_queue_count_probabilities": dict(sample.distractor_queue_count_probabilities),
                    "background_person_count_probabilities": dict(sample.background_person_count_probabilities),
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
                "counted_person_ids": list(counted_person_ids),
            },
            "execution_trace": {
                "query_id": str(sample.query_id),
                "scene_id": SCENE_ID,
                "target_service_point_id": str(sample.service_point_id),
                "target_service_point_name": str(sample.service_point_name),
                "target_count": int(sample.target_count),
                "distractor_queue_count": int(sample.distractor_queue_count),
                "background_person_count": int(sample.background_person_count),
                "person_count": int(sample.person_count),
                "queue_counts": {str(key): int(value) for key, value in queue_counts.items()},
                "counted_person_ids": list(counted_person_ids),
                "areas": serialized_scene[0]["areas"],
                "service_points": serialized_scene[0]["service_points"],
                "persons": serialized_scene[0]["persons"],
                "luggage": serialized_scene[0]["luggage"],
                "decor": serialized_scene[0]["decor"],
                "setting_id": str(scene.setting_id),
                "layout": dict(scene.layout),
            },
            "witness_symbolic": {
                "counted_person_ids": list(counted_person_ids),
                "target_service_point_id": str(sample.service_point_id),
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
            query_id=str(sample.query_id),
        )


__all__ = ["TerminalQueuePersonBranch"]
