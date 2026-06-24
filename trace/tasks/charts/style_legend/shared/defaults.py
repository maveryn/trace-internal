"""Config and deterministic selection helpers for the style-legend scene."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from trace.core.scene_config import get_scene_defaults
from trace.core.seed import spawn_rng
from trace.tasks.charts.shared.visual_defaults import (
    load_chart_scene_background_defaults,
    load_chart_scene_noise_defaults,
)
from trace.tasks.shared.config_defaults import (
    group_default,
    resolve_required_int_bounds,
    split_scene_generation_rendering_prompt_defaults,
)
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.render_variation import resolve_render_int, resolve_render_rgb

from .state import RGB, SCENE_ID, SCENE_NAMESPACE, SUPPORTED_LEGEND_POSITIONS, SUPPORTED_STYLE_PALETTE_MODES


SCENE_DEFAULTS = get_scene_defaults("charts", SCENE_ID)
GEN_DEFAULTS, RENDER_DEFAULTS, PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    SCENE_DEFAULTS if isinstance(SCENE_DEFAULTS, Mapping) else {},
    task_id=SCENE_NAMESPACE,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_scene_background_defaults(scene_id=SCENE_ID)
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)


def gen_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(GEN_DEFAULTS, str(key), int(fallback))))


def render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


def resolve_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(
        resolve_render_int(
            params,
            RENDER_DEFAULTS,
            str(key),
            int(fallback),
            instance_seed=render_style_seed(params),
            namespace=SCENE_NAMESPACE,
        )
    )


def resolve_rgb(params: Mapping[str, Any], key: str, fallback: RGB) -> RGB:
    return resolve_render_rgb(
        params,
        RENDER_DEFAULTS,
        str(key),
        fallback,
        instance_seed=render_style_seed(params),
        namespace=SCENE_NAMESPACE,
    )


def selection_index(params: Mapping[str, Any], *, instance_seed: int, namespace: str) -> int:
    return abs(int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))))


def balanced_choice(values: Sequence[Any], params: Mapping[str, Any], *, instance_seed: int, namespace: str) -> Any:
    support = tuple(values)
    if not support:
        raise ValueError(f"empty support for {namespace}")
    index = selection_index(params, instance_seed=int(instance_seed), namespace=str(namespace))
    return support[int(index) % len(support)]


def normalize_weights(raw: Mapping[str, float]) -> dict[str, float]:
    clean = {str(key): float(value) for key, value in raw.items() if float(value) > 0.0}
    total = float(sum(clean.values()))
    if total <= 0.0:
        return {}
    return {str(key): float(value) / total for key, value in sorted(clean.items())}


def resolve_axis_choice(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    supported: Sequence[str],
    explicit_key: str,
    weights_key: str,
    balance_key: str,
    namespace: str,
    fallback_weights: Mapping[str, float],
) -> tuple[str, dict[str, float]]:
    explicit = params.get(str(explicit_key), group_default(GEN_DEFAULTS, str(explicit_key), None))
    supported_values = tuple(str(value) for value in supported)
    if explicit is not None:
        value = str(explicit)
        if value not in set(supported_values):
            raise ValueError(f"unsupported {explicit_key}: {value}")
        return value, {value: 1.0}
    raw_weights = params.get(str(weights_key), group_default(GEN_DEFAULTS, str(weights_key), fallback_weights))
    weights = normalize_weights(raw_weights if isinstance(raw_weights, Mapping) else fallback_weights)
    candidates = tuple(value for value in supported_values if float(weights.get(value, 0.0)) > 0.0)
    if not candidates:
        candidates = supported_values
        weights = {str(value): 1.0 / float(len(candidates)) for value in candidates}
    if bool(params.get(str(balance_key), group_default(GEN_DEFAULTS, str(balance_key), False))):
        return str(balanced_choice(candidates, params, instance_seed=int(instance_seed), namespace=str(namespace))), dict(weights)
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.{namespace}")
    total = sum(float(weights.get(value, 0.0)) for value in candidates)
    pick = rng.random() * float(total)
    running = 0.0
    for value in candidates:
        running += float(weights.get(value, 0.0))
        if pick <= running:
            return str(value), dict(weights)
    return str(candidates[-1]), dict(weights)


def resolve_palette_mode(params: Mapping[str, Any], *, instance_seed: int) -> tuple[str, dict[str, float]]:
    return resolve_axis_choice(
        params,
        instance_seed=int(instance_seed),
        supported=SUPPORTED_STYLE_PALETTE_MODES,
        explicit_key="style_palette_mode",
        weights_key="style_palette_mode_weights",
        balance_key="balanced_style_palette_mode_sampling",
        namespace="style_palette_mode",
        fallback_weights={"grayscale": 7.0, "muted_color": 2.0, "colorblind_safe": 1.0},
    )


def resolve_legend_position(params: Mapping[str, Any], *, instance_seed: int) -> tuple[str, dict[str, float]]:
    return resolve_axis_choice(
        params,
        instance_seed=int(instance_seed),
        supported=SUPPORTED_LEGEND_POSITIONS,
        explicit_key="legend_position",
        weights_key="legend_position_weights",
        balance_key="balanced_legend_position_sampling",
        namespace="legend_position",
        fallback_weights={"right": 3.0, "top": 1.0},
    )


def count_from_range(
    params: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    instance_seed: int,
    namespace: str,
) -> int:
    low, high = resolve_required_int_bounds(
        params,
        GEN_DEFAULTS,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
        context=f"generation defaults for {SCENE_NAMESPACE}",
    )
    if int(low) > int(high):
        raise ValueError(f"empty count range for {namespace}")
    return int(
        balanced_choice(
            tuple(range(int(low), int(high) + 1)),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.{namespace}",
        )
    )
