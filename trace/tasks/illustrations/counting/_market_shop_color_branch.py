"""Count market shops or stalls by signboard, awning, or facade color."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...shared.color_format import format_named_color_with_hex
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.named_colors import available_named_colors, named_color
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.task_support import style_weights as _shared_style_weights
from ..shared.task_support import setting_weights as _shared_setting_weights
from ..shared.task_support import render_params as _shared_render_params
from ..shared.task_support import sample_count as _shared_sample_count
from ..shared.task_support import uniform_string_probability_map as _uniform_string_probability_map
from ..shared.task_support import bounds as _shared_bounds
from ..shared.task_support import query_support as _shared_query_support
from ..shared.object_library import STYLE_IDS
from ..shared.urban_market_scene import (
    MARKET_SETTING_IDS,
    MARKET_SHOP_TYPES,
    MarketShopSpec,
    render_urban_market_scene,
    serialize_urban_market_scene,
    shop_awning_bbox_map,
    shop_bbox_map,
    shop_facade_bbox_map,
    shop_sign_bbox_map,
    sort_market_bboxes,
    urban_market_scene_entities,
)


TASK_ID = "private_market_shop_color"
SCENE_ID = "market"
QUERY_IDS: Tuple[str, ...] = (
    "signboard_color_count",
    "awning_color_count",
    "facade_color_count",
)
_QUERY_SURFACES: Dict[str, Dict[str, str]] = {
    "signboard_color_count": {
        "surface_key": "signboard",
        "surface_name": "signboard",
        "bbox_name": "signboard",
    },
    "awning_color_count": {
        "surface_key": "awning",
        "surface_name": "awning",
        "bbox_name": "awning",
    },
    "facade_color_count": {
        "surface_key": "facade",
        "surface_name": "storefront facade",
        "bbox_name": "facade",
    },
}
DEFAULT_COLOR_SUPPORT: Tuple[str, ...] = ("red", "blue", "green", "orange", "purple", "cyan", "magenta")


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
    query_id: str
    surface_key: str
    surface_name: str
    color_name: str
    color_rgb: Tuple[int, int, int]
    color_label: str
    target_count: int
    shop_count: int
    shop_specs: Tuple[MarketShopSpec, ...]
    query_probabilities: Dict[str, float]
    color_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    shop_count_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)










def _color_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    known = {str(name) for name, _rgb in available_named_colors()}
    raw = params.get("color_name_support", group_default(_GEN_DEFAULTS, "color_name_support", DEFAULT_COLOR_SUPPORT))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("color_name_support must be a sequence")
    support = tuple(str(value).strip().lower() for value in raw if str(value).strip().lower() in known)
    if len(support) < 2:
        raise ValueError("color_name_support must contain at least two canonical colors")
    return tuple(dict.fromkeys(support))


def _shop_type_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("shop_type_support", group_default(_GEN_DEFAULTS, "shop_type_support", MARKET_SHOP_TYPES))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("shop_type_support must be a sequence")
    support = tuple(str(value) for value in raw if str(value) in set(MARKET_SHOP_TYPES))
    if len(support) < 2:
        raise ValueError("shop_type_support must contain at least two market shop types")
    return tuple(dict.fromkeys(support))








def _color_attributes(*, surface_colors: Mapping[str, str]) -> Dict[str, Any]:
    attrs: Dict[str, Any] = {}
    for surface_key, color_name in surface_colors.items():
        rgb = tuple(int(channel) for channel in named_color(str(color_name)))
        label = format_named_color_with_hex(str(color_name), rgb)
        attrs[f"{surface_key}_color_name"] = str(color_name)
        attrs[f"{surface_key}_color_rgb"] = list(rgb)
        attrs[f"{surface_key}_color_label"] = str(label)
    return attrs


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int) -> _SampleSpec:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:sample", int(attempt_index))
    base_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:cycle")
    query_support = _shared_query_support(params, _GEN_DEFAULTS, QUERY_IDS)
    explicit_query = params.get("query_id")
    if explicit_query is not None:
        query_id = str(explicit_query)
        if query_id not in set(query_support):
            raise ValueError("query_id is outside configured support")
        query_probabilities = _uniform_string_probability_map(query_support, selected=query_id)
    else:
        query_id = str(query_support[int(base_index // 5) % len(query_support)])
        query_probabilities = _uniform_string_probability_map(query_support)
    query_info = _QUERY_SURFACES[str(query_id)]

    color_support = _color_support(params)
    explicit_color = params.get("color_name")
    if explicit_color is not None:
        color_name = str(explicit_color).strip().lower()
        if color_name not in set(color_support):
            raise ValueError("color_name is outside configured support")
        color_probabilities = _uniform_string_probability_map(color_support, selected=color_name)
    else:
        color_name = str(color_support[int(base_index // 15) % len(color_support)])
        color_probabilities = _uniform_string_probability_map(color_support)
    color_rgb = tuple(int(channel) for channel in named_color(str(color_name)))
    color_label = format_named_color_with_hex(str(color_name), color_rgb)

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
    shop_min, shop_max = _shared_bounds(params, _GEN_DEFAULTS, "shop_count_min", "shop_count_max", _DEFAULTS.shop_count_min, _DEFAULTS.shop_count_max)
    shop_low = max(int(shop_min), int(target_count) + 4)
    shop_count, shop_probabilities = _shared_sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:shop_count",
        low=int(shop_low),
        high=int(shop_max),
        explicit_key="shop_count",
        cycle_index=int(base_index // max(1, target_max - target_min + 1)),
    )

    shop_support = _shop_type_support(params)
    non_target_colors = tuple(value for value in color_support if value != str(color_name))
    surface_keys = ("signboard", "awning", "facade")
    specs: list[MarketShopSpec] = []
    for index in range(int(shop_count)):
        surface_colors = {surface_key: str(rng.choice(color_support)) for surface_key in surface_keys}
        if index < int(target_count):
            surface_colors[str(query_info["surface_key"])] = str(color_name)
            role = "target"
        else:
            surface_colors[str(query_info["surface_key"])] = str(rng.choice(non_target_colors))
            role = "distractor"
        specs.append(
            MarketShopSpec(
                shop_type=str(rng.choice(shop_support)),
                item_types=(),
                role=str(role),
                attributes=_color_attributes(surface_colors=surface_colors),
            )
        )
    rng.shuffle(specs)

    return _SampleSpec(
        query_id=str(query_id),
        surface_key=str(query_info["surface_key"]),
        surface_name=str(query_info["surface_name"]),
        color_name=str(color_name),
        color_rgb=color_rgb,
        color_label=str(color_label),
        target_count=int(target_count),
        shop_count=int(shop_count),
        shop_specs=tuple(specs),
        query_probabilities=dict(query_probabilities),
        color_probabilities=dict(color_probabilities),
        target_count_probabilities=dict(target_probabilities),
        shop_count_probabilities=dict(shop_probabilities),
    )


def _surface_bbox_map(scene, surface_key: str) -> Dict[str, list[float]]:
    if str(surface_key) == "signboard":
        return shop_sign_bbox_map(scene)
    if str(surface_key) == "awning":
        return shop_awning_bbox_map(scene)
    if str(surface_key) == "facade":
        return shop_facade_bbox_map(scene)
    raise ValueError(f"unsupported shop color surface: {surface_key}")


def _build_complexity(sample: _SampleSpec) -> TaskComplexity:
    visual_scan = (int(sample.shop_count) - _DEFAULTS.shop_count_min) / max(1, _DEFAULTS.shop_count_max - _DEFAULTS.shop_count_min)
    answer_load = (int(sample.target_count) - _DEFAULTS.target_count_min) / max(1, _DEFAULTS.target_count_max - _DEFAULTS.target_count_min)
    surface_load = {"signboard": 0.50, "awning": 0.65, "facade": 0.75}.get(str(sample.surface_key), 0.65)
    score = 0.50 * max(0.0, min(1.0, visual_scan)) + 0.30 * max(0.0, min(1.0, answer_load)) + 0.20 * float(surface_load)
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "visual_scan": round(float(visual_scan), 6),
            "answer_load": round(float(answer_load), 6),
            "surface_load": round(float(surface_load), 6),
            "shop_count": int(sample.shop_count),
            "target_count": int(sample.target_count),
            "query_id": str(sample.query_id),
            "surface_key": str(sample.surface_key),
            "color_name": str(sample.color_name),
        },
    )


class MarketShopColorBranch:
    """Count market shops or stalls with a queried colored shop surface."""

    task_id = TASK_ID
    branch_id = "market_shop_color"
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
            except Exception as exc:  # pragma: no cover
                last_error = exc
                sample = None
                scene = None
        if scene is None or sample is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        serialized_scene, shop_bboxes, item_bboxes = serialize_urban_market_scene(scene)
        surface_attr = f"{sample.surface_key}_color_name"
        counted_shop_ids = tuple(
            str(shop.shop_id)
            for shop in scene.shops
            if str(shop.attributes.get(surface_attr)) == str(sample.color_name)
        )
        if len(counted_shop_ids) != int(sample.target_count):
            raise RuntimeError("rendered shop color count did not match sample target")
        surface_bboxes = _surface_bbox_map(scene, sample.surface_key)
        evidence_value = sort_market_bboxes(surface_bboxes, counted_shop_ids)
        color_assignments = {
            str(shop.shop_id): {
                "signboard_color_name": str(shop.attributes.get("signboard_color_name")),
                "awning_color_name": str(shop.attributes.get("awning_color_name")),
                "facade_color_name": str(shop.attributes.get("facade_color_name")),
            }
            for shop in scene.shops
        }

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_shop_color_attribute_count",
                "evidence_hint_shop_color_attribute_count",
                "json_example_shop_color_attribute_count",
                "json_example_answer_only_shop_color_attribute_count",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        slots = {
            "shop_count": int(sample.shop_count),
            "surface_name": str(sample.surface_name),
            "color_label": str(sample.color_label),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_shop_color_attribute_count"]).format(
                surface_name=str(sample.surface_name),
                color_label=str(sample.color_label),
            ),
            "evidence_hint": str(prompt_defaults["evidence_hint_shop_color_attribute_count"]).format(
                surface_name=str(sample.surface_name),
                color_label=str(sample.color_label),
            ),
            "json_example": str(prompt_defaults["json_example_shop_color_attribute_count"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_shop_color_attribute_count"]),
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
                "entities": urban_market_scene_entities(scene),
                "relations": {
                    "query_variant": str(sample.query_id),
                    "query_id": str(sample.query_id),
                    "target_surface": str(sample.surface_key),
                    "target_color_name": str(sample.color_name),
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
                    "surface_key": str(sample.surface_key),
                    "surface_name": str(sample.surface_name),
                    "color_name": str(sample.color_name),
                    "color_rgb": list(sample.color_rgb),
                    "color_label": str(sample.color_label),
                    "target_count": int(sample.target_count),
                    "shop_count": int(sample.shop_count),
                    "query_probabilities": dict(sample.query_probabilities),
                    "color_probabilities": dict(sample.color_probabilities),
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
                "shop_sign_bboxes_px": shop_sign_bbox_map(scene),
                "shop_awning_bboxes_px": shop_awning_bbox_map(scene),
                "shop_facade_bboxes_px": shop_facade_bbox_map(scene),
                "item_bboxes_px": item_bboxes,
                "color_assignments": color_assignments,
                "counted_shop_ids": list(counted_shop_ids),
                "surface_bboxes_by_id_px": surface_bboxes,
                "shop_bboxes_by_id_px": shop_bbox_map(scene),
            },
            "execution_trace": {
                "query_variant": str(sample.query_id),
                "query_id": str(sample.query_id),
                "scene_id": SCENE_ID,
                "setting_id": str(scene.setting_id),
                "target_surface": str(sample.surface_key),
                "target_surface_name": str(sample.surface_name),
                "target_color_name": str(sample.color_name),
                "target_color_rgb": list(sample.color_rgb),
                "target_color_label": str(sample.color_label),
                "target_count": int(sample.target_count),
                "shop_count": int(sample.shop_count),
                "counted_shop_ids": list(counted_shop_ids),
                "color_assignments": color_assignments,
                "shops": serialized_scene[0]["shops"],
                "items": serialized_scene[0]["items"],
            },
            "witness_symbolic": {
                "counted_shop_ids": list(counted_shop_ids),
                "target_surface": str(sample.surface_key),
                "target_color_name": str(sample.color_name),
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


__all__ = ["MarketShopColorBranch"]
