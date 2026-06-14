"""Sampling and render-default helpers for environment illustrations."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from ....shared.config_defaults import group_default
from ....shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.object_library import STYLE_IDS
from ...shared.style_registry import resolve_art_style_weights

from .rendering import ENVIRONMENT_THEME_IDS, effective_environment_object_count


FEATURE_TYPES_BY_THEME: Dict[str, tuple[str, ...]] = {
    "park_road": ("road",),
    "river_meadow": ("river",),
    "road_and_river": ("road", "river"),
    "canal_city": ("river",),
    "skyline_street": ("road",),
}

ENVIRONMENT_SETTING_NAMES: Dict[str, str] = {
    "park_road": "a park road setting",
    "river_meadow": "a meadow river setting",
    "road_and_river": "an outdoor setting with both a road and a river",
    "canal_city": "a city canal setting",
    "skyline_street": "a city street setting",
}


def style_weights(params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> Dict[str, float]:
    """Resolve render-only art-style weights for the environment scene."""

    return resolve_art_style_weights(params, render_defaults, style_ids=STYLE_IDS)


def environment_render_params(
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    *,
    fallback: Mapping[str, Any],
) -> Dict[str, Any]:
    """Resolve scene-level environment rendering parameters from task and scene defaults."""

    return {
        "canvas_width": int(
            params.get("canvas_width", group_default(render_defaults, "environment_canvas_width", int(fallback["canvas_width"])))
        ),
        "canvas_height": int(
            params.get("canvas_height", group_default(render_defaults, "environment_canvas_height", int(fallback["canvas_height"])))
        ),
        "object_size_min_px": int(
            params.get(
                "object_size_min_px",
                group_default(render_defaults, "environment_object_size_min_px", int(fallback["object_size_min_px"])),
            )
        ),
        "object_size_max_px": int(
            params.get(
                "object_size_max_px",
                group_default(render_defaults, "environment_object_size_max_px", int(fallback["object_size_max_px"])),
            )
        ),
        "min_gap_px": int(params.get("min_gap_px", group_default(render_defaults, "environment_min_gap_px", int(fallback["min_gap_px"])))),
        "max_overlap_fraction": float(
            params.get(
                "max_overlap_fraction",
                group_default(render_defaults, "environment_max_overlap_fraction", float(fallback["max_overlap_fraction"])),
            )
        ),
        "placement_max_attempts": int(
            params.get(
                "placement_max_attempts",
                group_default(render_defaults, "environment_placement_max_attempts", int(fallback["placement_max_attempts"])),
            )
        ),
        "render_scale": int(params.get("render_scale", group_default(render_defaults, "environment_render_scale", int(fallback["render_scale"])))),
        "skyline_building_min": int(params.get("skyline_building_min", group_default(render_defaults, "skyline_building_min", int(fallback.get("skyline_building_min", 7))))),
        "skyline_building_max": int(params.get("skyline_building_max", group_default(render_defaults, "skyline_building_max", int(fallback.get("skyline_building_max", 14))))),
    }


def environment_setting_name(theme_id: str) -> str:
    """Return prompt-facing text for one environment theme."""

    return ENVIRONMENT_SETTING_NAMES.get(str(theme_id), "an illustrated outdoor scene")


def theme_support(
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    *,
    fallback: Sequence[str] = ENVIRONMENT_THEME_IDS,
) -> tuple[str, ...]:
    """Resolve supported environment themes from params/defaults."""

    raw = params.get("theme_support", group_default(generation_defaults, "theme_support", tuple(fallback)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("theme_support must be a sequence")
    supported = tuple(str(value) for value in raw if str(value) in set(ENVIRONMENT_THEME_IDS))
    if not supported:
        raise ValueError("theme_support resolved no supported environment themes")
    return tuple(dict.fromkeys(supported))


def global_feature_type_probabilities(themes: Sequence[str], *, selected: str | None = None) -> Dict[str, float]:
    """Return road/river probabilities induced by the configured theme support."""

    if selected is not None:
        return {str(selected): 1.0}
    weights = {"road": 0.0, "river": 0.0}
    for theme in themes:
        support = FEATURE_TYPES_BY_THEME[str(theme)]
        probability = 1.0 / float(len(support))
        for feature_type in support:
            weights[str(feature_type)] += probability
    total = sum(weights.values())
    return {key: value / total for key, value in sorted(weights.items()) if value > 0.0}


def int_bounds(
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    *,
    low_key: str,
    high_key: str,
    fallback_low: int,
    fallback_high: int,
) -> tuple[int, int]:
    """Resolve an inclusive integer range from params/defaults/fallbacks."""

    if "target_count_min" in params or "target_count_max" in params:
        low = int(params.get("target_count_min", fallback_low))
        high = int(params.get("target_count_max", fallback_high))
    else:
        low = int(params.get(low_key, group_default(generation_defaults, low_key, fallback_low)))
        high = int(params.get(high_key, group_default(generation_defaults, high_key, fallback_high)))
    if low < 0 or high < low:
        raise ValueError(f"invalid {low_key}/{high_key} range")
    return int(low), int(high)


def sample_count_support(
    *,
    params: Mapping[str, Any],
    support: Sequence[int],
    explicit_key: str,
    cycle_index: int,
) -> tuple[int, Dict[str, float]]:
    """Sample one count from a configured support range."""

    values = tuple(int(value) for value in support)
    if not values:
        raise ValueError(f"{explicit_key} has empty support")
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        value = int(explicit)
        if value not in set(values):
            raise ValueError(f"{explicit_key} is outside configured support")
        return int(value), dict(uniform_probability_map(values, selected=int(value)))
    value = int(values[int(cycle_index) % len(values)])
    return int(value), dict(uniform_probability_map(values))


def sample_object_count(
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    *,
    fallback_min: int,
    fallback_max: int,
    instance_seed: int,
    namespace: str,
) -> tuple[int, Dict[str, float]]:
    """Resolve and sample the requested environment foreground-object count."""

    low = int(params.get("object_count_min", group_default(generation_defaults, "object_count_min", int(fallback_min))))
    high = int(params.get("object_count_max", group_default(generation_defaults, "object_count_max", int(fallback_max))))
    if low < 0 or high < low:
        raise ValueError("invalid object_count_min/object_count_max range")
    return sample_count_support(
        params=params,
        support=tuple(range(int(low), int(high) + 1)),
        explicit_key="object_count",
        cycle_index=resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace)),
    )


def capped_object_count_probabilities(
    requested_probabilities: Mapping[str, float],
    theme_probabilities: Mapping[str, float],
) -> Dict[str, float]:
    """Map requested object-count probabilities through theme-specific caps."""

    normalized_theme_probabilities = {
        str(theme): max(0.0, float(probability))
        for theme, probability in theme_probabilities.items()
        if float(probability) > 0.0
    }
    if not normalized_theme_probabilities:
        normalized_theme_probabilities = {str(ENVIRONMENT_THEME_IDS[0]): 1.0}
    theme_total = sum(float(value) for value in normalized_theme_probabilities.values())
    capped: Dict[str, float] = {}
    for theme, theme_probability in normalized_theme_probabilities.items():
        theme_weight = float(theme_probability) / max(1e-9, float(theme_total))
        for requested_count, probability in requested_probabilities.items():
            actual_count = effective_environment_object_count(str(theme), int(requested_count))
            capped[str(actual_count)] = float(capped.get(str(actual_count), 0.0)) + float(theme_weight) * float(probability)
    return dict(sorted(capped.items(), key=lambda item: int(item[0])))


__all__ = [
    "ENVIRONMENT_SETTING_NAMES",
    "FEATURE_TYPES_BY_THEME",
    "capped_object_count_probabilities",
    "environment_render_params",
    "environment_setting_name",
    "global_feature_type_probabilities",
    "int_bounds",
    "sample_count_support",
    "sample_object_count",
    "style_weights",
    "theme_support",
]
