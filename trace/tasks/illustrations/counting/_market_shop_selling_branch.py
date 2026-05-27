"""Count market shops or stalls that sell a named item."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
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
    MARKET_ITEM_ALLOWED_SHOPS,
    MARKET_QUERY_ITEM_TYPES,
    MARKET_SETTING_IDS,
    MARKET_SHOP_INVENTORY_TYPES,
    MARKET_SHOP_TYPES,
    MarketShopSpec,
    item_bbox_map,
    market_item_display_name,
    render_urban_market_scene,
    serialize_urban_market_scene,
    shop_bbox_map,
    sort_market_bboxes,
    urban_market_scene_entities,
)


TASK_ID = "private_market_shop_selling"
SCENE_ID = "market"
QUERY_ID = "shop_selling_object_count"


@dataclass(frozen=True)
class _Defaults:
    shop_count_min: int = 6
    shop_count_max: int = 9
    target_count_min: int = 1
    target_count_max: int = 5
    items_per_shop_min: int = 3
    items_per_shop_max: int = 5
    canvas_width: int = 1280
    canvas_height: int = 960
    render_scale: int = 2


@dataclass(frozen=True)
class _SampleSpec:
    target_item_type: str
    target_item_name: str
    target_count: int
    shop_count: int
    shop_specs: Tuple[MarketShopSpec, ...]
    target_item_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    shop_count_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)




def _item_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("target_item_type_support", group_default(_GEN_DEFAULTS, "target_item_type_support", MARKET_QUERY_ITEM_TYPES))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("target_item_type_support must be a sequence")
    supported = tuple(str(value) for value in raw if str(value) in set(MARKET_QUERY_ITEM_TYPES))
    if not supported:
        raise ValueError("target_item_type_support resolved no supported market items")
    return tuple(dict.fromkeys(supported))






def _choose_distinct_items(
    *,
    rng,
    shop_type: str,
    target_item_type: str | None,
    item_count: int,
    role: str,
) -> Tuple[str, ...]:
    inventory = tuple(str(value) for value in MARKET_SHOP_INVENTORY_TYPES[str(shop_type)])
    selected: list[str] = []
    if target_item_type is not None:
        selected.append(str(target_item_type))
    pool = [item for item in inventory if item not in set(selected) and item != str(target_item_type)]
    if len(pool) < max(0, int(item_count) - len(selected)):
        pool = [item for item in MARKET_QUERY_ITEM_TYPES if item not in set(selected) and item != str(target_item_type)]
    rng.shuffle(pool)
    selected.extend(pool[: max(0, int(item_count) - len(selected))])
    if len(selected) < int(item_count):
        raise ValueError(f"not enough inventory items for {role} shop {shop_type}")
    rng.shuffle(selected)
    return tuple(str(value) for value in selected[: int(item_count)])


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int) -> _SampleSpec:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:sample", int(attempt_index))
    item_support = _item_support(params)
    explicit_item = params.get("target_item_type")
    if explicit_item is not None:
        target_item_type = str(explicit_item)
        if target_item_type not in set(item_support):
            raise ValueError("target_item_type is outside configured support")
        item_probabilities = _uniform_string_probability_map(item_support, selected=target_item_type)
    else:
        item_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:target_item")
        target_item_type = str(item_support[int(item_index) % len(item_support)])
        item_probabilities = _uniform_string_probability_map(item_support)

    target_min, target_max = _shared_bounds(params, _GEN_DEFAULTS, "target_count_min", "target_count_max", _DEFAULTS.target_count_min, _DEFAULTS.target_count_max)
    target_count, target_probabilities = _shared_sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:target_count",
        low=int(target_min),
        high=int(target_max),
        explicit_key="target_count",
    )
    shop_min, shop_max = _shared_bounds(params, _GEN_DEFAULTS, "shop_count_min", "shop_count_max", _DEFAULTS.shop_count_min, _DEFAULTS.shop_count_max)
    shop_low = max(int(shop_min), int(target_count) + 2)
    shop_count, shop_probabilities = _shared_sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:shop_count",
        low=int(shop_low),
        high=int(shop_max),
        explicit_key="shop_count",
    )
    item_count_min, item_count_max = _shared_bounds(
        params,
        _GEN_DEFAULTS,
        "items_per_shop_min",
        "items_per_shop_max",
        _DEFAULTS.items_per_shop_min,
        _DEFAULTS.items_per_shop_max,
    )
    allowed_target_shops = tuple(str(value) for value in MARKET_ITEM_ALLOWED_SHOPS[str(target_item_type)])
    if not allowed_target_shops:
        raise ValueError(f"target item has no allowed shops: {target_item_type}")

    shop_specs: list[MarketShopSpec] = []
    for _ in range(int(target_count)):
        shop_type = str(rng.choice(allowed_target_shops))
        item_count = min(int(rng.randint(int(item_count_min), int(item_count_max))), len(MARKET_SHOP_INVENTORY_TYPES[str(shop_type)]))
        items = _choose_distinct_items(
            rng=rng,
            shop_type=str(shop_type),
            target_item_type=str(target_item_type),
            item_count=int(item_count),
            role="target",
        )
        shop_specs.append(MarketShopSpec(shop_type=str(shop_type), item_types=items, role="target"))

    non_target_shops = tuple(str(value) for value in MARKET_SHOP_TYPES)
    for _ in range(int(shop_count) - int(target_count)):
        candidate_types = [
            shop_type
            for shop_type in non_target_shops
            if any(item != str(target_item_type) for item in MARKET_SHOP_INVENTORY_TYPES[str(shop_type)])
        ]
        shop_type = str(rng.choice(tuple(candidate_types)))
        item_count = min(int(rng.randint(int(item_count_min), int(item_count_max))), len(MARKET_SHOP_INVENTORY_TYPES[str(shop_type)]))
        items = _choose_distinct_items(
            rng=rng,
            shop_type=str(shop_type),
            target_item_type=None,
            item_count=int(item_count),
            role="distractor",
        )
        items = tuple(item for item in items if item != str(target_item_type))
        if len(items) < int(item_count):
            replacement_pool = [
                item
                for item in MARKET_SHOP_INVENTORY_TYPES[str(shop_type)]
                if item != str(target_item_type) and item not in set(items)
            ]
            if len(replacement_pool) < int(item_count) - len(items):
                replacement_pool.extend(
                    item
                    for item in MARKET_QUERY_ITEM_TYPES
                    if item != str(target_item_type) and item not in set(items)
                )
            rng.shuffle(replacement_pool)
            items = tuple(list(items) + replacement_pool[: int(item_count) - len(items)])
        shop_specs.append(MarketShopSpec(shop_type=str(shop_type), item_types=tuple(items[: int(item_count)]), role="distractor"))

    rng.shuffle(shop_specs)
    return _SampleSpec(
        target_item_type=str(target_item_type),
        target_item_name=market_item_display_name(str(target_item_type)),
        target_count=int(target_count),
        shop_count=int(shop_count),
        shop_specs=tuple(shop_specs),
        target_item_probabilities=dict(item_probabilities),
        target_count_probabilities=dict(target_probabilities),
        shop_count_probabilities=dict(shop_probabilities),
    )








def _build_complexity(sample: _SampleSpec) -> TaskComplexity:
    visual_scan = (int(sample.shop_count) - _DEFAULTS.shop_count_min) / max(1, _DEFAULTS.shop_count_max - _DEFAULTS.shop_count_min)
    answer_load = (int(sample.target_count) - _DEFAULTS.target_count_min) / max(1, _DEFAULTS.target_count_max - _DEFAULTS.target_count_min)
    inventory_load = sum(len(spec.item_types) for spec in sample.shop_specs) / max(1.0, float(int(sample.shop_count) * _DEFAULTS.items_per_shop_max))
    score = 0.45 * max(0.0, min(1.0, visual_scan)) + 0.35 * max(0.0, min(1.0, answer_load)) + 0.20 * max(0.0, min(1.0, inventory_load))
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "visual_scan": round(float(visual_scan), 6),
            "answer_load": round(float(answer_load), 6),
            "inventory_load": round(float(inventory_load), 6),
            "shop_count": int(sample.shop_count),
            "target_count": int(sample.target_count),
            "target_item_type": str(sample.target_item_type),
        },
    )


class MarketShopSellingBranch:
    """Count shops or stalls that sell a named item in an urban market."""

    task_id = TASK_ID
    branch_id = "market_shop_selling"
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
                render_params = _shared_render_params(params, _RENDER_DEFAULTS, prefix="urban_market", fallback_width=_DEFAULTS.canvas_width, fallback_height=_DEFAULTS.canvas_height, fallback_scale=_DEFAULTS.render_scale)
                scene_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:scene", int(attempt))
                scene = render_urban_market_scene(
                    rng=scene_rng,
                    shop_specs=sample.shop_specs,
                    canvas_width=int(render_params["canvas_width"]),
                    canvas_height=int(render_params["canvas_height"]),
                    render_scale=int(render_params["render_scale"]),
                    style_weights=_shared_style_weights(params, _RENDER_DEFAULTS, style_ids=STYLE_IDS),
                    setting_weights=_shared_setting_weights(params, _RENDER_DEFAULTS, key="urban_market_setting_weights", setting_ids=MARKET_SETTING_IDS),
                )
                break
            except Exception as exc:  # pragma: no cover - retry behavior exercised by smoke tests.
                last_error = exc
                sample = None
                scene = None
        if scene is None or sample is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        serialized_scene, shop_bboxes, item_bboxes = serialize_urban_market_scene(scene)
        shop_inventory = {str(shop.shop_id): tuple(str(item_type) for item_type in shop.item_types) for shop in scene.shops}
        counted_shop_ids = tuple(
            str(shop.shop_id)
            for shop in scene.shops
            if str(sample.target_item_type) in set(str(item_type) for item_type in shop.item_types)
        )
        if len(counted_shop_ids) != int(sample.target_count):
            raise RuntimeError("rendered shop inventory count did not match sample target")
        counted_item_ids = tuple(
            str(item.item_id)
            for item in scene.items
            if str(item.item_type) == str(sample.target_item_type) and str(item.shop_id) in set(counted_shop_ids)
        )
        evidence_value = sort_market_bboxes(shop_bboxes, counted_shop_ids)
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_shop_selling_object_count",
                "evidence_hint_shop_selling_object_count",
                "json_example_shop_selling_object_count",
                "json_example_answer_only_shop_selling_object_count",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        slots = {
            "shop_count": int(sample.shop_count),
            "item_name": str(sample.target_item_name),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_shop_selling_object_count"]).format(item_name=str(sample.target_item_name)),
            "evidence_hint": str(prompt_defaults["evidence_hint_shop_selling_object_count"]).format(item_name=str(sample.target_item_name)),
            "json_example": str(prompt_defaults["json_example_shop_selling_object_count"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_shop_selling_object_count"]),
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
        trace_payload = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "entities": urban_market_scene_entities(scene),
                "relations": {
                    "query_variant": "default",
                    "query_id": QUERY_ID,
                    "target_item_type": str(sample.target_item_type),
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
                    "target_item_type": str(sample.target_item_type),
                    "target_item_name": str(sample.target_item_name),
                    "target_count": int(sample.target_count),
                    "target_shop_count": int(sample.target_count),
                    "shop_count": int(sample.shop_count),
                    "target_item_probabilities": dict(sample.target_item_probabilities),
                    "target_count_probabilities": dict(sample.target_count_probabilities),
                    "shop_count_probabilities": dict(sample.shop_count_probabilities),
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
                "shop_inventory": {str(shop_id): list(items) for shop_id, items in shop_inventory.items()},
                "counted_shop_ids": list(counted_shop_ids),
                "counted_item_ids": list(counted_item_ids),
                "item_bboxes_by_id_px": item_bbox_map(scene),
                "shop_bboxes_by_id_px": shop_bbox_map(scene),
            },
            "execution_trace": {
                "query_variant": "default",
                "query_id": QUERY_ID,
                "scene_id": SCENE_ID,
                "setting_id": str(scene.setting_id),
                "target_item_type": str(sample.target_item_type),
                "target_item_name": str(sample.target_item_name),
                "target_count": int(sample.target_count),
                "target_shop_count": int(sample.target_count),
                "shop_count": int(sample.shop_count),
                "counted_shop_ids": list(counted_shop_ids),
                "counted_item_ids": list(counted_item_ids),
                "shop_inventory": {str(shop_id): list(items) for shop_id, items in shop_inventory.items()},
                "shops": serialized_scene[0]["shops"],
                "items": serialized_scene[0]["items"],
            },
            "witness_symbolic": {
                "counted_shop_ids": list(counted_shop_ids),
                "target_item_type": str(sample.target_item_type),
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


__all__ = ["MarketShopSellingBranch"]
