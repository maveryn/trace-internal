"""Count construction workers matching visible safety-gear conditions."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.task_support import query_support as _shared_query_support
from ..shared.construction_site_scene import (
    ConstructionEquipmentSpec,
    ConstructionMaterialSpec,
    ConstructionWorkerSpec,
    construction_color_display_name,
    construction_color_hex,
    construction_scene_entities,
    construction_worker_bbox_map,
    render_construction_site_scene,
    serialize_construction_scene,
    sort_construction_bboxes,
)
from ..shared.construction_task_common import (
    bounds,
    color_support,
    equipment_support,
    material_support,
    render_params,
    sample_count,
    setting_weights,
    spawned_task_rng,
    style_weights,
    tool_support,
    uniform_string_probability_map,
)


TASK_ID = "task_illustrations__construction_site__worker_attribute_count"
SCENE_ID = "construction_site"
QUERY_IDS: Tuple[str, ...] = (
    "hard_hat_color_worker_count",
    "vest_color_worker_count",
    "tool_holding_worker_count",
)


@dataclass(frozen=True)
class _Defaults:
    worker_count_min: int = 9
    worker_count_max: int = 15
    target_count_min: int = 2
    target_count_max: int = 7
    material_count_min: int = 5
    material_count_max: int = 8
    equipment_count_min: int = 3
    equipment_count_max: int = 5
    canvas_width: int = 1280
    canvas_height: int = 900
    render_scale: int = 2


@dataclass(frozen=True)
class _SampleSpec:
    query_id: str
    target_color: str | None
    target_count: int
    worker_count: int
    worker_specs: Tuple[ConstructionWorkerSpec, ...]
    material_specs: Tuple[ConstructionMaterialSpec, ...]
    equipment_specs: Tuple[ConstructionEquipmentSpec, ...]
    match_phrase: str
    query_probabilities: Dict[str, float]
    color_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    worker_count_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_scene_defaults("illustrations", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)




def _sample_spec(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int) -> _SampleSpec:
    rng = spawned_task_rng(int(instance_seed), TASK_ID, int(attempt_index))
    base_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:cycle")
    query_values = _shared_query_support(params, _GEN_DEFAULTS, QUERY_IDS)
    colors = color_support(params, _GEN_DEFAULTS)
    tools = tool_support(params, _GEN_DEFAULTS)

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

    if "color" in query_id:
        color_index = int(base_index // max(1, len(query_values))) % len(colors)
        target_color = str(params.get("target_color", colors[color_index]))
        if target_color not in set(colors):
            raise ValueError("target_color is outside configured support")
        color_probabilities = uniform_string_probability_map(colors, selected=target_color)
    else:
        target_color = None
        color_probabilities = uniform_string_probability_map(colors)

    target_min, target_max = bounds(params, _GEN_DEFAULTS, "target_count_min", "target_count_max", _DEFAULTS.target_count_min, _DEFAULTS.target_count_max)
    target_count, target_count_probabilities = sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:target_count",
        low=int(target_min),
        high=int(target_max),
        explicit_key="target_count",
        cycle_index=int(base_index // max(1, len(query_values) * len(colors))) + int(query_index),
    )
    worker_min, worker_max = bounds(params, _GEN_DEFAULTS, "worker_count_min", "worker_count_max", _DEFAULTS.worker_count_min, _DEFAULTS.worker_count_max)
    worker_low = max(int(worker_min), int(target_count) + 2)
    worker_count, worker_count_probabilities = sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:worker_count",
        low=int(worker_low),
        high=int(worker_max),
        explicit_key="worker_count",
        cycle_index=int(base_index // max(1, len(query_values) * len(colors) * int(target_max - target_min + 1))),
    )

    non_target_colors = [str(color) for color in colors if str(color) != str(target_color)]
    if not non_target_colors:
        raise ValueError("worker safety task needs at least one non-target color")
    worker_specs = []
    if query_id == "hard_hat_color_worker_count":
        match_phrase = f"workers wearing {construction_color_display_name(target_color)} hard hats"
        for _ in range(int(target_count)):
            worker_specs.append(
                ConstructionWorkerSpec(
                    hard_hat_color=target_color,
                    vest_color=str(rng.choice(colors)),
                    tool_type=str(rng.choice(tools)) if rng.random() < 0.45 else None,
                    role="target",
                )
            )
        for _ in range(int(worker_count) - int(target_count)):
            worker_specs.append(
                ConstructionWorkerSpec(
                    hard_hat_color=str(rng.choice(tuple(non_target_colors))),
                    vest_color=str(rng.choice(colors)),
                    tool_type=str(rng.choice(tools)) if rng.random() < 0.40 else None,
                    role="distractor",
                )
            )
    elif query_id == "vest_color_worker_count":
        match_phrase = f"workers wearing {construction_color_display_name(target_color)} safety vests"
        for _ in range(int(target_count)):
            worker_specs.append(
                ConstructionWorkerSpec(
                    hard_hat_color=str(rng.choice(colors)),
                    vest_color=target_color,
                    tool_type=str(rng.choice(tools)) if rng.random() < 0.45 else None,
                    role="target",
                )
            )
        for _ in range(int(worker_count) - int(target_count)):
            worker_specs.append(
                ConstructionWorkerSpec(
                    hard_hat_color=str(rng.choice(colors)),
                    vest_color=str(rng.choice(tuple(non_target_colors))),
                    tool_type=str(rng.choice(tools)) if rng.random() < 0.40 else None,
                    role="distractor",
                )
            )
    else:
        match_phrase = "workers holding a tool"
        for _ in range(int(target_count)):
            worker_specs.append(
                ConstructionWorkerSpec(
                    hard_hat_color=str(rng.choice(colors)),
                    vest_color=str(rng.choice(colors)),
                    tool_type=str(rng.choice(tools)),
                    role="target",
                )
            )
        for _ in range(int(worker_count) - int(target_count)):
            worker_specs.append(
                ConstructionWorkerSpec(
                    hard_hat_color=str(rng.choice(colors)),
                    vest_color=str(rng.choice(colors)),
                    tool_type=None,
                    role="distractor",
                )
            )
    rng.shuffle(worker_specs)

    material_min, material_max = bounds(params, _GEN_DEFAULTS, "material_count_min", "material_count_max", _DEFAULTS.material_count_min, _DEFAULTS.material_count_max)
    material_count = int(rng.randint(int(material_min), int(material_max)))
    materials = material_support(params, _GEN_DEFAULTS)
    material_specs = tuple(ConstructionMaterialSpec(material_type=str(rng.choice(materials)), role="decor") for _ in range(material_count))
    equipment_min, equipment_max = bounds(params, _GEN_DEFAULTS, "equipment_count_min", "equipment_count_max", _DEFAULTS.equipment_count_min, _DEFAULTS.equipment_count_max)
    equipment_count = int(rng.randint(int(equipment_min), int(equipment_max)))
    equipment_values = equipment_support(params, _GEN_DEFAULTS)
    equipment_specs = tuple(ConstructionEquipmentSpec(equipment_type=str(rng.choice(equipment_values)), role="decor") for _ in range(equipment_count))

    return _SampleSpec(
        query_id=str(query_id),
        target_color=target_color if "color" in query_id else None,
        target_count=int(target_count),
        worker_count=int(worker_count),
        worker_specs=tuple(worker_specs),
        material_specs=tuple(material_specs),
        equipment_specs=tuple(equipment_specs),
        match_phrase=str(match_phrase),
        query_probabilities=dict(query_probabilities),
        color_probabilities=dict(color_probabilities),
        target_count_probabilities=dict(target_count_probabilities),
        worker_count_probabilities=dict(worker_count_probabilities),
    )




@register_task
class IllustrationsCountingWorkerSafetyGearCountTask:
    """Count workers matching a visible hard-hat, vest, or tool condition."""

    task_id = TASK_ID
    domain = "illustrations"
    scene_id = "counting"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        sample: _SampleSpec | None = None
        scene = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                sample = _sample_spec(instance_seed=int(instance_seed), params=params, attempt_index=int(attempt))
                scene_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:scene", int(attempt))
                rp = render_params(params, _RENDER_DEFAULTS, fallback_width=_DEFAULTS.canvas_width, fallback_height=_DEFAULTS.canvas_height, fallback_scale=_DEFAULTS.render_scale)
                scene = render_construction_site_scene(
                    rng=scene_rng,
                    worker_specs=sample.worker_specs,
                    material_specs=sample.material_specs,
                    equipment_specs=sample.equipment_specs,
                    canvas_width=int(rp["canvas_width"]),
                    canvas_height=int(rp["canvas_height"]),
                    render_scale=int(rp["render_scale"]),
                    setting_weights=setting_weights(params, _RENDER_DEFAULTS),
                    style_weights=style_weights(params, _RENDER_DEFAULTS),
                    instance_seed=int(instance_seed),
                    font_params={**dict(_RENDER_DEFAULTS), **dict(params)},
                )
                break
            except Exception as exc:  # pragma: no cover
                last_error = exc
                sample = None
                scene = None
        if scene is None or sample is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        if sample.query_id == "hard_hat_color_worker_count":
            counted_worker_ids = tuple(str(worker.worker_id) for worker in scene.workers if str(worker.hard_hat_color) == str(sample.target_color))
        elif sample.query_id == "vest_color_worker_count":
            counted_worker_ids = tuple(str(worker.worker_id) for worker in scene.workers if str(worker.vest_color) == str(sample.target_color))
        else:
            counted_worker_ids = tuple(str(worker.worker_id) for worker in scene.workers if worker.tool_type)
        if len(counted_worker_ids) != int(sample.target_count):
            raise RuntimeError("rendered worker count did not match sample target")
        annotation_value = sort_construction_bboxes(construction_worker_bbox_map(scene), counted_worker_ids)
        serialized_scene, bbox_map = serialize_construction_scene(scene)

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_worker_safety_gear",
                "annotation_hint_worker_safety_gear",
                "json_example_worker_safety_gear",
                "json_example_answer_only_worker_safety_gear",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        slots = {
            "worker_count": int(sample.worker_count),
            "color_label": construction_color_display_name(str(sample.target_color or "")),
            "match_phrase": str(sample.match_phrase),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_worker_safety_gear"]).format(match_phrase=str(sample.match_phrase)),
            "annotation_hint": str(prompt_defaults["annotation_hint_worker_safety_gear"]).format(match_phrase=str(sample.match_phrase)),
            "json_example": str(prompt_defaults["json_example_worker_safety_gear"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_worker_safety_gear"]),
        }
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            scene_id=self.scene_id,
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
                "entities": construction_scene_entities(scene),
                "relations": {"query_id": str(sample.query_id), "match_phrase": str(sample.match_phrase)},
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_id": str(sample.query_id),
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "target_color": str(sample.target_color) if sample.target_color else None,
                    "target_color_label": construction_color_display_name(str(sample.target_color)) if sample.target_color else None,
                    "target_color_hex": construction_color_hex(str(sample.target_color)) if sample.target_color else None,
                    "match_phrase": str(sample.match_phrase),
                    "target_count": int(sample.target_count),
                    "worker_count": int(sample.worker_count),
                    "query_id_probabilities": dict(sample.query_probabilities),
                    "query_probabilities": dict(sample.query_probabilities),
                    "color_probabilities": dict(sample.color_probabilities),
                    "target_count_probabilities": dict(sample.target_count_probabilities),
                    "worker_count_probabilities": dict(sample.worker_count_probabilities),
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
                "bboxes_px": bbox_map,
                "worker_bboxes_px": construction_worker_bbox_map(scene),
                "counted_worker_ids": list(counted_worker_ids),
            },
            "execution_trace": {
                "query_id": str(sample.query_id),
                "scene_id": SCENE_ID,
                "query_id_probabilities": dict(sample.query_probabilities),
                "target_count": int(sample.target_count),
                "worker_count": int(sample.worker_count),
                "target_color_label": construction_color_display_name(str(sample.target_color)) if sample.target_color else None,
                "target_color_hex": construction_color_hex(str(sample.target_color)) if sample.target_color else None,
                "worker_color_counts": {
                    "hard_hat": dict(Counter(str(worker.hard_hat_color) for worker in scene.workers)),
                    "vest": dict(Counter(str(worker.vest_color) for worker in scene.workers)),
                },
                "tool_holding_count": sum(1 for worker in scene.workers if worker.tool_type),
                "counted_worker_ids": list(counted_worker_ids),
                "scene": serialized_scene[0],
            },
            "witness_symbolic": {"counted_worker_ids": list(counted_worker_ids), "answer": int(sample.target_count)},
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
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sample.query_id),
        )


__all__ = ["IllustrationsCountingWorkerSafetyGearCountTask"]
