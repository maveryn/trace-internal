"""Configuration/default helpers for pictogram charts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .....core.scene_config import get_scene_defaults
from ....shared.config_defaults import group_default, split_scene_generation_rendering_prompt_defaults
from ....shared.deterministic_sampling import resolve_selection_index
from ....shared.font_assets import sample_font_family
from ....shared.render_variation import resolve_render_rgb
from ...shared.labeled_chart_common import resolve_chart_axis_variant
from ...shared.visual_defaults import load_chart_scene_background_defaults, load_chart_scene_noise_defaults

from .state import (
    DOMAIN,
    PROMPT_BUNDLE_ID,
    SCENE_ID,
    SCENE_NAMESPACE,
    SUPPORTED_GLYPHS,
    SUPPORTED_SCENE_VARIANTS,
    RGB,
)


_SCENE_DEFAULTS = get_scene_defaults("charts", SCENE_ID)
GEN_DEFAULTS, RENDER_DEFAULTS, PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=SCENE_NAMESPACE,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_scene_background_defaults(scene_id=SCENE_ID)
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)


def support_probability_map(values: Sequence[int], *, selected: int | None = None) -> dict[str, float]:
    support = tuple(int(value) for value in values)
    if not support:
        return {}
    if selected is not None:
        return {str(value): (1.0 if int(value) == int(selected) else 0.0) for value in support}
    probability = 1.0 / float(len(support))
    return {str(value): float(probability) for value in support}


def sample_balanced_int(
    *,
    params: Mapping[str, object],
    instance_seed: int,
    namespace: str,
    low: int,
    high: int,
) -> int:
    low_i = int(low)
    high_i = int(high)
    if low_i > high_i:
        raise ValueError(f"invalid integer support for {namespace}: {low_i}>{high_i}")
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    return int(low_i + (abs(int(index)) % (high_i - low_i + 1)))


def sample_balanced_choice(
    values: Sequence[int],
    *,
    params: Mapping[str, object],
    instance_seed: int,
    namespace: str,
) -> int:
    support = [int(value) for value in values]
    if not support:
        raise ValueError(f"empty support for {namespace}")
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    return int(support[abs(int(index)) % len(support)])


def resolve_scene_variant(params: Mapping[str, object], *, instance_seed: int) -> tuple[str, dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        task_id=SCENE_NAMESPACE,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def resolve_glyph(params: Mapping[str, object], *, instance_seed: int) -> tuple[str, dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_GLYPHS,
        task_id=SCENE_NAMESPACE,
        explicit_key="glyph_name",
        weights_key="glyph_weights",
        balance_flag_key="balanced_glyph_sampling",
        axis_namespace="glyph",
    )


def sample_chart_font_family(instance_seed: int, params: Mapping[str, object]) -> str:
    return str(
        sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.chart_font",
            params=params,
            exclude_tags=("display",),
            explicit_key="chart_font_family",
            weights_key="chart_font_family_weights",
        )
    )


def render_int(params: Mapping[str, object], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(RENDER_DEFAULTS, str(key), int(fallback))))


def render_rgb(params: Mapping[str, object], key: str, fallback: RGB, *, instance_seed: int) -> RGB:
    return resolve_render_rgb(
        params,
        RENDER_DEFAULTS,
        str(key),
        tuple(int(value) for value in fallback),
        instance_seed=int(instance_seed),
        namespace=SCENE_NAMESPACE,
    )


def prompt_bundle_id() -> str:
    return str(PROMPT_DEFAULTS.get("bundle_id", PROMPT_BUNDLE_ID))
