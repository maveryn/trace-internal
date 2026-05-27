"""Count construction material stacks or bundles of a requested type."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.construction_site_scene import (
    ConstructionEquipmentSpec,
    ConstructionMaterialSpec,
    ConstructionWorkerSpec,
    construction_color_display_name,
    construction_equipment_bbox_map,
    construction_material_bbox_map,
    construction_material_display_name,
    construction_scene_entities,
    render_construction_site_scene,
    serialize_construction_scene,
    sort_construction_bboxes,
)
from ..shared.construction_task_common import (
    bounds,
    color_support,
    equipment_support,
    material_support,
    query_support,
    render_params,
    sample_count,
    setting_weights,
    spawned_task_rng,
    style_weights,
    tool_support,
    uniform_string_probability_map,
)


TASK_ID = "task_illustrations__construction_site__material_stack_count"
SCENE_ID = "construction_site"
QUERY_IDS: Tuple[str, ...] = (
    "brick_stack_count",
    "pipe_bundle_count",
    "lumber_stack_count",
    "cement_bag_stack_count",
)
_QUERY_TO_MATERIAL: Dict[str, str] = {
    "brick_stack_count": "brick_stack",
    "pipe_bundle_count": "pipe_bundle",
    "lumber_stack_count": "lumber_stack",
    "cement_bag_stack_count": "cement_bag_stack",
}


@dataclass(frozen=True)
class _Defaults:
    material_count_min: int = 8
    material_count_max: int = 14
    target_count_min: int = 2
    target_count_max: int = 7
    worker_count_min: int = 5
    worker_count_max: int = 9
    equipment_count_min: int = 3
    equipment_count_max: int = 5
    canvas_width: int = 1280
    canvas_height: int = 900
    render_scale: int = 2


@dataclass(frozen=True)
class _SampleSpec:
    query_id: str
    target_material_type: str
    target_count: int
    material_count: int
    worker_count: int
    equipment_count: int
    material_specs: Tuple[ConstructionMaterialSpec, ...]
    worker_specs: Tuple[ConstructionWorkerSpec, ...]
    equipment_specs: Tuple[ConstructionEquipmentSpec, ...]
    material_name: str
    query_probabilities: Dict[str, float]
    material_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    material_count_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int) -> _SampleSpec:
    rng = spawned_task_rng(int(instance_seed), TASK_ID, int(attempt_index))
    base_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:cycle")
    query_values = query_support(params, _GEN_DEFAULTS, QUERY_IDS)
    materials = material_support(params, _GEN_DEFAULTS)
    colors = color_support(params, _GEN_DEFAULTS)
    tools = tool_support(params, _GEN_DEFAULTS)
    equipment_values = equipment_support(params, _GEN_DEFAULTS)

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
    target_material = str(_QUERY_TO_MATERIAL[str(query_id)])
    if target_material not in set(materials):
        raise ValueError("query_id targets a material outside configured material_type_support")
    material_probabilities = uniform_string_probability_map(materials, selected=target_material)

    target_min, target_max = bounds(
        params,
        _GEN_DEFAULTS,
        "target_count_min",
        "target_count_max",
        _DEFAULTS.target_count_min,
        _DEFAULTS.target_count_max,
    )
    target_count, target_count_probabilities = sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:target_count",
        low=int(target_min),
        high=int(target_max),
        explicit_key="target_count",
        cycle_index=int(base_index // max(1, len(query_values))) + int(query_index),
    )
    material_min, material_max = bounds(
        params,
        _GEN_DEFAULTS,
        "material_count_min",
        "material_count_max",
        _DEFAULTS.material_count_min,
        _DEFAULTS.material_count_max,
    )
    material_low = max(int(material_min), int(target_count) + 2)
    material_count, material_count_probabilities = sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:material_count",
        low=int(material_low),
        high=int(material_max),
        explicit_key="material_count",
        cycle_index=int(base_index // max(1, len(query_values) * int(target_max - target_min + 1))),
    )

    non_target_materials = [str(value) for value in materials if str(value) != str(target_material)]
    if not non_target_materials:
        raise ValueError("material stack task needs at least one non-target material type")
    material_specs = [ConstructionMaterialSpec(material_type=target_material, role="target") for _ in range(int(target_count))]
    material_specs.extend(
        ConstructionMaterialSpec(material_type=str(rng.choice(tuple(non_target_materials))), role="distractor")
        for _ in range(int(material_count) - int(target_count))
    )
    rng.shuffle(material_specs)

    worker_min, worker_max = bounds(params, _GEN_DEFAULTS, "worker_count_min", "worker_count_max", _DEFAULTS.worker_count_min, _DEFAULTS.worker_count_max)
    worker_count = int(rng.randint(int(worker_min), int(worker_max)))
    worker_specs = tuple(
        ConstructionWorkerSpec(
            hard_hat_color=str(rng.choice(colors)),
            vest_color=str(rng.choice(colors)),
            tool_type=str(rng.choice(tools)) if rng.random() < 0.42 else None,
            role="decor",
        )
        for _ in range(worker_count)
    )
    equipment_min, equipment_max = bounds(
        params,
        _GEN_DEFAULTS,
        "equipment_count_min",
        "equipment_count_max",
        _DEFAULTS.equipment_count_min,
        _DEFAULTS.equipment_count_max,
    )
    equipment_count = int(rng.randint(int(equipment_min), int(equipment_max)))
    equipment_specs = tuple(
        ConstructionEquipmentSpec(equipment_type=str(rng.choice(equipment_values)), role="decor")
        for _ in range(equipment_count)
    )

    return _SampleSpec(
        query_id=str(query_id),
        target_material_type=str(target_material),
        target_count=int(target_count),
        material_count=int(material_count),
        worker_count=int(worker_count),
        equipment_count=int(equipment_count),
        material_specs=tuple(material_specs),
        worker_specs=tuple(worker_specs),
        equipment_specs=tuple(equipment_specs),
        material_name=construction_material_display_name(str(target_material)),
        query_probabilities=dict(query_probabilities),
        material_probabilities=dict(material_probabilities),
        target_count_probabilities=dict(target_count_probabilities),
        material_count_probabilities=dict(material_count_probabilities),
    )


def _build_complexity(sample: _SampleSpec) -> TaskComplexity:
    visual_scan = (int(sample.material_count) - _DEFAULTS.material_count_min) / max(1, _DEFAULTS.material_count_max - _DEFAULTS.material_count_min)
    answer_load = (int(sample.target_count) - _DEFAULTS.target_count_min) / max(1, _DEFAULTS.target_count_max - _DEFAULTS.target_count_min)
    scene_clutter = (int(sample.worker_count) + int(sample.equipment_count) - (_DEFAULTS.worker_count_min + _DEFAULTS.equipment_count_min)) / max(
        1,
        (_DEFAULTS.worker_count_max + _DEFAULTS.equipment_count_max) - (_DEFAULTS.worker_count_min + _DEFAULTS.equipment_count_min),
    )
    score = 0.42 * max(0.0, min(1.0, visual_scan)) + 0.38 * max(0.0, min(1.0, answer_load)) + 0.20 * max(0.0, min(1.0, scene_clutter))
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "visual_scan": round(float(visual_scan), 6),
            "answer_load": round(float(answer_load), 6),
            "scene_clutter": round(float(scene_clutter), 6),
            "query_id": str(sample.query_id),
            "target_count": int(sample.target_count),
            "material_count": int(sample.material_count),
        },
    )


@register_task
class IllustrationsCountingMaterialStackTypeCountTask:
    """Count construction material stacks or bundles of one requested type."""

    task_id = TASK_ID
    domain = "illustrations"
    task_group = "counting"
    default_dataset_enabled = True

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
                )
                break
            except Exception as exc:  # pragma: no cover
                last_error = exc
                sample = None
                scene = None
        if scene is None or sample is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        counted_material_ids = tuple(
            str(material.material_id)
            for material in scene.materials
            if str(material.material_type) == str(sample.target_material_type)
        )
        if len(counted_material_ids) != int(sample.target_count):
            raise RuntimeError("rendered material count did not match sample target")
        evidence_value = sort_construction_bboxes(construction_material_bbox_map(scene), counted_material_ids)
        serialized_scene, bbox_map = serialize_construction_scene(scene)

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_material_stack_type",
                "evidence_hint_material_stack_type",
                "json_example_material_stack_type",
                "json_example_answer_only_material_stack_type",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        slots = {
            "worker_count": int(sample.worker_count),
            "material_name": str(sample.material_name),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_material_stack_type"]).format(material_name=str(sample.material_name)),
            "evidence_hint": str(prompt_defaults["evidence_hint_material_stack_type"]).format(material_name=str(sample.material_name)),
            "json_example": str(prompt_defaults["json_example_material_stack_type"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_material_stack_type"]),
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
        material_counts = dict(Counter(str(material.material_type) for material in scene.materials))
        trace_payload = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "entities": construction_scene_entities(scene),
                "relations": {
                    "query_id": str(sample.query_id),
                    "target_material_type": str(sample.target_material_type),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_id": str(sample.query_id),
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "target_material_type": str(sample.target_material_type),
                    "target_count": int(sample.target_count),
                    "material_count": int(sample.material_count),
                    "query_id_probabilities": dict(sample.query_probabilities),
                    "query_probabilities": dict(sample.query_probabilities),
                    "material_probabilities": dict(sample.material_probabilities),
                    "target_count_probabilities": dict(sample.target_count_probabilities),
                    "material_count_probabilities": dict(sample.material_count_probabilities),
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
                "material_bboxes_px": construction_material_bbox_map(scene),
                "equipment_bboxes_px": construction_equipment_bbox_map(scene),
                "counted_material_ids": list(counted_material_ids),
            },
            "execution_trace": {
                "query_id": str(sample.query_id),
                "scene_id": SCENE_ID,
                "query_id_probabilities": dict(sample.query_probabilities),
                "target_count": int(sample.target_count),
                "material_count": int(sample.material_count),
                "target_material_type": str(sample.target_material_type),
                "material_type_counts": material_counts,
                "counted_material_ids": list(counted_material_ids),
                "scene": serialized_scene[0],
            },
            "witness_symbolic": {"counted_material_ids": list(counted_material_ids), "answer": int(sample.target_count)},
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


__all__ = ["IllustrationsCountingMaterialStackTypeCountTask"]
