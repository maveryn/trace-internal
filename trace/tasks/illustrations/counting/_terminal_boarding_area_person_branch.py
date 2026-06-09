"""Count people in one labeled boarding area of a transit terminal."""

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
    TransitPersonSpec,
    render_transit_terminal_scene,
    serialize_transit_scene,
    sort_transit_bboxes,
    transit_area_display_name,
    transit_person_bbox_map,
    transit_scene_entities,
)


TASK_ID = "private_terminal_boarding_area_person"
SCENE_ID = "transit_terminal"
QUERY_IDS: Tuple[str, ...] = (
    "person_in_boarding_area_count",
)


@dataclass(frozen=True)
class _Defaults:
    person_count_min: int = 14
    person_count_max: int = 22
    target_count_min: int = 2
    target_count_max: int = 8
    canvas_width: int = 1280
    canvas_height: int = 900
    render_scale: int = 2


@dataclass(frozen=True)
class _SampleSpec:
    query_id: str
    area_id: str
    area_name: str
    target_count: int
    person_count: int
    person_specs: Tuple[TransitPersonSpec, ...]
    query_probabilities: Dict[str, float]
    area_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    person_count_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)




def _sample_spec(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int) -> _SampleSpec:
    rng = spawned_task_rng(int(instance_seed), TASK_ID, int(attempt_index))
    base_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:cycle")
    query_values = _shared_query_support(params, _GEN_DEFAULTS, QUERY_IDS)
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

    explicit_area = params.get("area_id")
    if explicit_area is not None:
        area_id = str(explicit_area)
        if area_id not in set(area_values):
            raise ValueError("area_id is outside configured support")
        area_index = int(area_values.index(area_id))
        area_probabilities = uniform_string_probability_map(area_values, selected=area_id)
    else:
        area_index = int(base_index // max(1, len(query_values))) % len(area_values)
        area_id = str(area_values[area_index])
        area_probabilities = uniform_string_probability_map(area_values)

    target_count, target_probabilities = sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:target_count",
        low=int(target_min),
        high=int(target_max),
        explicit_key="target_count",
        cycle_index=int(base_index // max(1, len(query_values) * len(area_values))) + 2 * int(area_index) + int(query_index),
    )
    person_min, person_max = bounds(
        params,
        _GEN_DEFAULTS,
        "person_count_min",
        "person_count_max",
        _DEFAULTS.person_count_min,
        _DEFAULTS.person_count_max,
    )
    person_low = max(int(person_min), int(target_count) + 4)
    person_count, person_count_probabilities = sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:person_count",
        low=int(person_low),
        high=int(person_max),
        explicit_key="person_count",
        cycle_index=int(base_index // max(1, len(query_values) * len(area_values) * int(target_max - target_min + 1))),
    )

    distractor_areas = [str(value) for value in area_values if str(value) != str(area_id)]
    if not distractor_areas:
        raise ValueError("boarding-area person task needs at least one distractor area")
    specs = [
        TransitPersonSpec(
            area_id=str(area_id),
            role="target",
            attributes={"pose_id": str(rng.choice(TRANSIT_PERSON_POSES))},
        )
        for _ in range(int(target_count))
    ]
    for index in range(int(person_count) - int(target_count)):
        if index < len(distractor_areas):
            distractor_area = str(distractor_areas[index])
        elif float(rng.random()) < 0.22:
            distractor_area = "concourse"
        else:
            distractor_area = str(rng.choice(tuple(distractor_areas)))
        specs.append(
            TransitPersonSpec(
                area_id=str(distractor_area),
                role="distractor",
                attributes={"pose_id": str(rng.choice(TRANSIT_PERSON_POSES))},
            )
        )
    rng.shuffle(specs)
    return _SampleSpec(
        query_id=str(query_id),
        area_id=str(area_id),
        area_name=transit_area_display_name(str(area_id)),
        target_count=int(target_count),
        person_count=int(person_count),
        person_specs=tuple(specs),
        query_probabilities=dict(query_probabilities),
        area_probabilities=dict(area_probabilities),
        target_count_probabilities=dict(target_probabilities),
        person_count_probabilities=dict(person_count_probabilities),
    )


def _build_complexity(sample: _SampleSpec) -> TaskComplexity:
    visual_scan = (int(sample.person_count) - _DEFAULTS.person_count_min) / max(1, _DEFAULTS.person_count_max - _DEFAULTS.person_count_min)
    answer_load = (int(sample.target_count) - _DEFAULTS.target_count_min) / max(1, _DEFAULTS.target_count_max - _DEFAULTS.target_count_min)
    area_filter_load = 0.76
    score = 0.42 * max(0.0, min(1.0, visual_scan)) + 0.38 * max(0.0, min(1.0, answer_load)) + 0.20 * area_filter_load
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "visual_scan": round(float(visual_scan), 6),
            "answer_load": round(float(answer_load), 6),
            "area_filter_load": round(float(area_filter_load), 6),
        },
    )


class TerminalBoardingAreaPersonBranch:
    """Count people in one labeled boarding area of a transit terminal."""

    task_id = TASK_ID
    branch_id = "terminal_boarding_area_person"
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
                )
                break
            except Exception as exc:  # pragma: no cover
                last_error = exc
                sample = None
                scene = None
        if scene is None or sample is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        serialized_scene, person_bboxes = serialize_transit_scene(scene)
        counted_person_ids = tuple(str(person.person_id) for person in scene.persons if str(person.area_id) == str(sample.area_id))
        if len(counted_person_ids) != int(sample.target_count):
            raise RuntimeError("rendered boarding-area person count did not match sample target")
        annotation_value = sort_transit_bboxes(transit_person_bbox_map(scene), counted_person_ids)
        area_counts = dict(Counter(str(person.area_id) for person in scene.persons))

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_person_at_boarding_area",
                "annotation_hint_person_at_boarding_area",
                "json_example_person_at_boarding_area",
                "json_example_answer_only_person_at_boarding_area",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        slots = {
            "person_count": int(sample.person_count),
            "area_name": str(sample.area_name),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_person_at_boarding_area"]).format(area_name=str(sample.area_name)),
            "annotation_hint": str(prompt_defaults["annotation_hint_person_at_boarding_area"]).format(area_name=str(sample.area_name)),
            "json_example": str(prompt_defaults["json_example_person_at_boarding_area"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_person_at_boarding_area"]),
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
                    "target_area_id": str(sample.area_id),
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
                    "target_count": int(sample.target_count),
                    "person_count": int(sample.person_count),
                    "query_probabilities": dict(sample.query_probabilities),
                    "area_probabilities": dict(sample.area_probabilities),
                    "target_count_probabilities": dict(sample.target_count_probabilities),
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
                "counted_person_ids": list(counted_person_ids),
            },
            "execution_trace": {
                "query_id": str(sample.query_id),
                "scene_id": SCENE_ID,
                "target_area_id": str(sample.area_id),
                "target_area_name": str(sample.area_name),
                "target_count": int(sample.target_count),
                "person_count": int(sample.person_count),
                "area_counts": area_counts,
                "counted_person_ids": list(counted_person_ids),
                "areas": serialized_scene[0]["areas"],
                "persons": serialized_scene[0]["persons"],
                "decor": serialized_scene[0]["decor"],
                "setting_id": str(scene.setting_id),
                "layout": dict(scene.layout),
            },
            "witness_symbolic": {
                "counted_person_ids": list(counted_person_ids),
                "target_area_id": str(sample.area_id),
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


__all__ = ["TerminalBoardingAreaPersonBranch"]
