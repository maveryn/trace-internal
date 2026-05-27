"""Count customers standing at market shops or stalls with a named sign category."""

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
from ..shared.task_support import style_weights as _shared_style_weights
from ..shared.task_support import setting_weights as _shared_setting_weights
from ..shared.task_support import render_params as _shared_render_params
from ..shared.task_support import sample_count as _shared_sample_count
from ..shared.task_support import uniform_string_probability_map as _uniform_string_probability_map
from ..shared.task_support import bounds as _shared_bounds
from ..shared.object_library import STYLE_IDS
from ..shared.urban_market_scene import (
    MARKET_SETTING_IDS,
    MARKET_SHOP_LABELS,
    MARKET_SHOP_TYPES,
    MarketCustomerSpec,
    MarketShopSpec,
    customer_bbox_map,
    market_shop_display_name,
    render_urban_market_scene,
    serialize_urban_market_scene,
    shop_bbox_map,
    sort_market_bboxes,
    urban_market_scene_entities,
)


TASK_ID = "task_illustrations__market__customer_at_shop_count"
SCENE_ID = "market"
QUERY_ID = "customer_at_shop_type_count"
_CUSTOMER_OBJECT_TYPES: Tuple[str, ...] = ("person", "pedestrian_with_bag")


@dataclass(frozen=True)
class _Defaults:
    shop_count_min: int = 8
    shop_count_max: int = 12
    customer_count_min: int = 6
    customer_count_max: int = 12
    target_count_min: int = 1
    target_count_max: int = 5
    canvas_width: int = 1280
    canvas_height: int = 960
    render_scale: int = 2


@dataclass(frozen=True)
class _SampleSpec:
    shop_type: str
    shop_name: str
    shop_label: str
    target_count: int
    shop_count: int
    customer_count: int
    shop_specs: Tuple[MarketShopSpec, ...]
    customer_specs: Tuple[MarketCustomerSpec, ...]
    shop_type_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    shop_count_probabilities: Dict[str, float]
    customer_count_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)




def _shop_type_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("shop_type_support", group_default(_GEN_DEFAULTS, "shop_type_support", MARKET_SHOP_TYPES))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("shop_type_support must be a sequence")
    supported = tuple(str(value) for value in raw if str(value) in set(MARKET_SHOP_TYPES))
    if len(supported) < 2:
        raise ValueError("shop_type_support must contain at least two market shop types")
    return tuple(dict.fromkeys(supported))






def _sample_spec(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int) -> _SampleSpec:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:sample", int(attempt_index))
    base_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:target_count")
    shop_support = _shop_type_support(params)
    explicit_shop_type = params.get("shop_type")
    if explicit_shop_type is not None:
        shop_type = str(explicit_shop_type)
        if shop_type not in set(shop_support):
            raise ValueError("shop_type is outside configured support")
        shop_type_probabilities = _uniform_string_probability_map(shop_support, selected=shop_type)
    else:
        shop_type = str(shop_support[(int(base_index) // 5) % len(shop_support)])
        shop_type_probabilities = _uniform_string_probability_map(shop_support)

    target_min, target_max = _shared_bounds(params, _GEN_DEFAULTS, "target_count_min", "target_count_max", _DEFAULTS.target_count_min, _DEFAULTS.target_count_max)
    target_count, target_probabilities = _shared_sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:target_count",
        low=int(target_min),
        high=int(target_max),
        explicit_key="target_count",
        cycle_index=int(base_index),
    )
    customer_min, customer_max = _shared_bounds(
        params,
        _GEN_DEFAULTS,
        "customer_count_min",
        "customer_count_max",
        _DEFAULTS.customer_count_min,
        _DEFAULTS.customer_count_max,
    )
    customer_low = max(int(customer_min), int(target_count) + 3)
    customer_count, customer_probabilities = _shared_sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:customer_count",
        low=int(customer_low),
        high=int(customer_max),
        explicit_key="customer_count",
        cycle_index=int(base_index) // max(1, int(target_max - target_min + 1)),
    )
    max_target_shop_count = max(1, min(3, int(target_count)))
    target_shop_count = int(rng.randint(1, int(max_target_shop_count)))
    shop_min, shop_max = _shared_bounds(params, _GEN_DEFAULTS, "shop_count_min", "shop_count_max", _DEFAULTS.shop_count_min, _DEFAULTS.shop_count_max)
    shop_low = max(int(shop_min), int(target_shop_count) + 3)
    shop_count, shop_probabilities = _shared_sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:shop_count",
        low=int(shop_low),
        high=int(shop_max),
        explicit_key="shop_count",
        cycle_index=int(base_index) // max(1, int(target_max - target_min + 1) * 2),
    )

    distractor_types = [value for value in shop_support if value != str(shop_type)]
    shop_specs: list[MarketShopSpec] = [
        MarketShopSpec(shop_type=str(shop_type), item_types=(), role="target_customer_shop")
        for _ in range(int(target_shop_count))
    ]
    for _ in range(int(shop_count) - int(target_shop_count)):
        shop_specs.append(MarketShopSpec(shop_type=str(rng.choice(tuple(distractor_types))), item_types=(), role="distractor"))
    rng.shuffle(shop_specs)
    present_distractor_types = tuple(
        sorted({str(spec.shop_type) for spec in shop_specs if str(spec.shop_type) != str(shop_type)})
    )
    if not present_distractor_types:
        raise ValueError("customer distractors require at least one non-target shop type")

    customer_specs: list[MarketCustomerSpec] = []
    for _ in range(int(target_count)):
        customer_specs.append(
            MarketCustomerSpec(
                shop_type=str(shop_type),
                role="target",
                object_type=str(rng.choice(_CUSTOMER_OBJECT_TYPES)),
            )
        )
    for _ in range(int(customer_count) - int(target_count)):
        customer_specs.append(
            MarketCustomerSpec(
                shop_type=str(rng.choice(tuple(present_distractor_types))),
                role="distractor",
                object_type=str(rng.choice(_CUSTOMER_OBJECT_TYPES)),
            )
        )
    rng.shuffle(customer_specs)

    return _SampleSpec(
        shop_type=str(shop_type),
        shop_name=market_shop_display_name(str(shop_type)),
        shop_label=str(MARKET_SHOP_LABELS.get(str(shop_type), str(shop_type).upper())),
        target_count=int(target_count),
        shop_count=int(shop_count),
        customer_count=int(customer_count),
        shop_specs=tuple(shop_specs),
        customer_specs=tuple(customer_specs),
        shop_type_probabilities=dict(shop_type_probabilities),
        target_count_probabilities=dict(target_probabilities),
        shop_count_probabilities=dict(shop_probabilities),
        customer_count_probabilities=dict(customer_probabilities),
    )








def _build_complexity(sample: _SampleSpec) -> TaskComplexity:
    visual_scan = (int(sample.customer_count) - _DEFAULTS.customer_count_min) / max(1, _DEFAULTS.customer_count_max - _DEFAULTS.customer_count_min)
    shop_scan = (int(sample.shop_count) - _DEFAULTS.shop_count_min) / max(1, _DEFAULTS.shop_count_max - _DEFAULTS.shop_count_min)
    answer_load = (int(sample.target_count) - _DEFAULTS.target_count_min) / max(1, _DEFAULTS.target_count_max - _DEFAULTS.target_count_min)
    score = 0.40 * max(0.0, min(1.0, visual_scan)) + 0.30 * max(0.0, min(1.0, shop_scan)) + 0.30 * max(0.0, min(1.0, answer_load))
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "visual_scan": round(float(visual_scan), 6),
            "shop_scan": round(float(shop_scan), 6),
            "answer_load": round(float(answer_load), 6),
            "shop_count": int(sample.shop_count),
            "customer_count": int(sample.customer_count),
            "target_count": int(sample.target_count),
            "shop_type": str(sample.shop_type),
        },
    )


@register_task
class IllustrationsCountingCustomerAtShopTypeCountTask:
    """Count customers at shops or stalls with a named market sign."""

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
                render_params = _shared_render_params(params, _RENDER_DEFAULTS, prefix="urban_market", fallback_width=_DEFAULTS.canvas_width, fallback_height=_DEFAULTS.canvas_height, fallback_scale=_DEFAULTS.render_scale)
                scene_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:scene", int(attempt))
                scene = render_urban_market_scene(
                    rng=scene_rng,
                    shop_specs=sample.shop_specs,
                    customer_specs=sample.customer_specs,
                    canvas_width=int(render_params["canvas_width"]),
                    canvas_height=int(render_params["canvas_height"]),
                    render_scale=int(render_params["render_scale"]),
                    style_weights=_shared_style_weights(params, _RENDER_DEFAULTS, style_ids=STYLE_IDS),
                    setting_weights=_shared_setting_weights(params, _RENDER_DEFAULTS, key="urban_market_setting_weights", setting_ids=MARKET_SETTING_IDS),
                    layout_mode="customer_plaza",
                    include_generic_decor=False,
                )
                break
            except Exception as exc:  # pragma: no cover - retry behavior exercised by smoke tests.
                last_error = exc
                sample = None
                scene = None
        if scene is None or sample is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        serialized_scene, shop_bboxes, item_bboxes = serialize_urban_market_scene(scene)
        customer_bboxes = customer_bbox_map(scene)
        customers = [
            decor
            for decor in scene.decor
            if str(decor.decor_type) == "customer" and str(decor.attributes.get("near_shop_type")) == str(sample.shop_type)
        ]
        counted_customer_ids = tuple(str(customer.decor_id) for customer in customers)
        if len(counted_customer_ids) != int(sample.target_count):
            raise RuntimeError("rendered customer count did not match sample target")
        evidence_value = sort_market_bboxes(customer_bboxes, counted_customer_ids)
        customer_counts_by_shop_type: Dict[str, int] = {}
        for decor in scene.decor:
            if str(decor.decor_type) != "customer":
                continue
            key = str(decor.attributes.get("near_shop_type"))
            customer_counts_by_shop_type[key] = int(customer_counts_by_shop_type.get(key, 0)) + 1

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_customer_at_shop_type",
                "evidence_hint_customer_at_shop_type",
                "json_example_customer_at_shop_type",
                "json_example_answer_only_customer_at_shop_type",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        slots = {
            "shop_count": int(sample.shop_count),
            "shop_name": str(sample.shop_name),
            "shop_label": str(sample.shop_label),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_customer_at_shop_type"]).format(shop_label=str(sample.shop_label), shop_name=str(sample.shop_name)),
            "evidence_hint": str(prompt_defaults["evidence_hint_customer_at_shop_type"]).format(shop_label=str(sample.shop_label), shop_name=str(sample.shop_name)),
            "json_example": str(prompt_defaults["json_example_customer_at_shop_type"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_customer_at_shop_type"]),
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
        customer_records = [
            record for record in serialized_scene[0]["decor"] if str(record.get("decor_type")) == "customer"
        ]
        trace_payload = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "entities": urban_market_scene_entities(scene),
                "relations": {
                    "query_variant": "default",
                    "query_id": QUERY_ID,
                    "target_shop_type": str(sample.shop_type),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_variant": "default",
                "query_id": QUERY_ID,
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "shop_type": str(sample.shop_type),
                    "shop_name": str(sample.shop_name),
                    "shop_label": str(sample.shop_label),
                    "target_count": int(sample.target_count),
                    "shop_count": int(sample.shop_count),
                    "customer_count": int(sample.customer_count),
                    "shop_type_probabilities": dict(sample.shop_type_probabilities),
                    "target_count_probabilities": dict(sample.target_count_probabilities),
                    "shop_count_probabilities": dict(sample.shop_count_probabilities),
                    "customer_count_probabilities": dict(sample.customer_count_probabilities),
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
                    "layout": scene.layout,
                },
            },
            "render_map": {
                "image_id": "img0",
                "shop_bboxes_px": shop_bboxes,
                "item_bboxes_px": item_bboxes,
                "customer_bboxes_px": customer_bboxes,
                "customer_counts_by_shop_type": dict(customer_counts_by_shop_type),
                "counted_customer_ids": list(counted_customer_ids),
                "shop_bboxes_by_id_px": shop_bbox_map(scene),
            },
            "execution_trace": {
                "query_variant": "default",
                "query_id": QUERY_ID,
                "scene_id": SCENE_ID,
                "setting_id": str(scene.setting_id),
                "target_shop_type": str(sample.shop_type),
                "target_shop_name": str(sample.shop_name),
                "target_shop_label": str(sample.shop_label),
                "target_count": int(sample.target_count),
                "shop_count": int(sample.shop_count),
                "customer_count": int(sample.customer_count),
                "customer_counts_by_shop_type": dict(customer_counts_by_shop_type),
                "counted_customer_ids": list(counted_customer_ids),
                "shops": serialized_scene[0]["shops"],
                "items": serialized_scene[0]["items"],
                "customers": customer_records,
            },
            "witness_symbolic": {
                "counted_customer_ids": list(counted_customer_ids),
                "target_shop_type": str(sample.shop_type),
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
            query_variant="default",
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
        )
