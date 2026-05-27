"""Count market shops or stalls with a named sign category."""

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
    MARKET_SETTING_IDS,
    MARKET_SHOP_LABELS,
    MARKET_SHOP_TYPES,
    MarketShopSpec,
    market_shop_display_name,
    render_urban_market_scene,
    serialize_urban_market_scene,
    shop_bbox_map,
    sort_market_bboxes,
    urban_market_scene_entities,
)


TASK_ID = "private_market_shop_category"
SCENE_ID = "market"
QUERY_ID = "shop_category_count"


@dataclass(frozen=True)
class _Defaults:
    shop_count_min: int = 12
    shop_count_max: int = 18
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
    shop_specs: Tuple[MarketShopSpec, ...]
    shop_type_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    shop_count_probabilities: Dict[str, float]


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
    shop_support = _shop_type_support(params)
    explicit_shop_type = params.get("shop_type")
    if explicit_shop_type is not None:
        shop_type = str(explicit_shop_type)
        if shop_type not in set(shop_support):
            raise ValueError("shop_type is outside configured support")
        shop_type_probabilities = _uniform_string_probability_map(shop_support, selected=shop_type)
    else:
        shop_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:shop_type")
        shop_type = str(shop_support[int(shop_index) % len(shop_support)])
        shop_type_probabilities = _uniform_string_probability_map(shop_support)

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
    shop_low = max(int(shop_min), int(target_count) + 3)
    shop_count, shop_count_probabilities = _shared_sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:shop_count",
        low=int(shop_low),
        high=int(shop_max),
        explicit_key="shop_count",
    )
    if int(target_count) >= int(shop_count):
        raise ValueError("target_count must be smaller than shop_count")

    distractor_types = [value for value in shop_support if value != str(shop_type)]
    shop_specs = [MarketShopSpec(shop_type=str(shop_type), item_types=(), role="target") for _ in range(int(target_count))]
    for _ in range(int(shop_count) - int(target_count)):
        shop_specs.append(MarketShopSpec(shop_type=str(rng.choice(tuple(distractor_types))), item_types=(), role="distractor"))
    rng.shuffle(shop_specs)

    return _SampleSpec(
        shop_type=str(shop_type),
        shop_name=market_shop_display_name(str(shop_type)),
        shop_label=str(MARKET_SHOP_LABELS.get(str(shop_type), str(shop_type).upper())),
        target_count=int(target_count),
        shop_count=int(shop_count),
        shop_specs=tuple(shop_specs),
        shop_type_probabilities=dict(shop_type_probabilities),
        target_count_probabilities=dict(target_probabilities),
        shop_count_probabilities=dict(shop_count_probabilities),
    )








def _build_complexity(sample: _SampleSpec) -> TaskComplexity:
    visual_scan = (int(sample.shop_count) - _DEFAULTS.shop_count_min) / max(1, _DEFAULTS.shop_count_max - _DEFAULTS.shop_count_min)
    answer_load = (int(sample.target_count) - _DEFAULTS.target_count_min) / max(1, _DEFAULTS.target_count_max - _DEFAULTS.target_count_min)
    score = 0.60 * max(0.0, min(1.0, visual_scan)) + 0.40 * max(0.0, min(1.0, answer_load))
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "visual_scan": round(float(visual_scan), 6),
            "answer_load": round(float(answer_load), 6),
            "shop_count": int(sample.shop_count),
            "target_count": int(sample.target_count),
            "shop_type": str(sample.shop_type),
        },
    )


class MarketShopCategoryBranch:
    """Count shops or stalls with a named sign category in an urban market."""

    task_id = TASK_ID
    branch_id = "market_shop_category"
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
                    layout_mode="sign_dense",
                )
                break
            except Exception as exc:  # pragma: no cover - retry behavior exercised by smoke tests.
                last_error = exc
                sample = None
                scene = None
        if scene is None or sample is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        serialized_scene, shop_bboxes, item_bboxes = serialize_urban_market_scene(scene)
        counted_shop_ids = tuple(str(shop.shop_id) for shop in scene.shops if str(shop.shop_type) == str(sample.shop_type))
        if len(counted_shop_ids) != int(sample.target_count):
            raise RuntimeError("rendered shop category count did not match sample target")
        evidence_value = sort_market_bboxes(shop_bboxes, counted_shop_ids)
        shop_type_counts: Dict[str, int] = {}
        for shop in scene.shops:
            shop_type_counts[str(shop.shop_type)] = int(shop_type_counts.get(str(shop.shop_type), 0)) + 1

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_shop_category_count",
                "evidence_hint_shop_category_count",
                "json_example_shop_category_count",
                "json_example_answer_only_shop_category_count",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        slots = {
            "shop_count": int(sample.shop_count),
            "shop_name": str(sample.shop_name),
            "shop_label": str(sample.shop_label),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_shop_category_count"]).format(shop_label=str(sample.shop_label), shop_name=str(sample.shop_name)),
            "evidence_hint": str(prompt_defaults["evidence_hint_shop_category_count"]).format(shop_label=str(sample.shop_label), shop_name=str(sample.shop_name)),
            "json_example": str(prompt_defaults["json_example_shop_category_count"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_shop_category_count"]),
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
                    "shop_type_probabilities": dict(sample.shop_type_probabilities),
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
                "shop_type_counts": dict(shop_type_counts),
                "counted_shop_ids": list(counted_shop_ids),
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
                "shop_type_counts": dict(shop_type_counts),
                "counted_shop_ids": list(counted_shop_ids),
                "shops": serialized_scene[0]["shops"],
                "items": serialized_scene[0]["items"],
            },
            "witness_symbolic": {
                "counted_shop_ids": list(counted_shop_ids),
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
