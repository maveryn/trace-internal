"""Shared scene state for combo-mark chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from PIL import Image

from trace.core.sampling import normalize_positive_weights, weighted_choice
from trace.core.seed import spawn_rng
from trace.tasks.charts.shared.visual_defaults import (
    load_chart_scene_background_defaults,
    load_chart_scene_noise_defaults,
)
from trace.tasks.shared.config_defaults import (
    group_default,
    load_scene_generation_rendering_prompt_defaults,
)


DOMAIN = "charts"
SCENE_ID = "combo_mark"
SCENE_NAMESPACE = "charts.combo_mark"
PROMPT_BUNDLE_ID = "charts_combo_mark_v1"

GENERATION_DEFAULTS, RENDERING_DEFAULTS, PROMPT_DEFAULTS = (
    load_scene_generation_rendering_prompt_defaults(DOMAIN, SCENE_ID)
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_scene_background_defaults(scene_id=SCENE_ID)
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)

SCENE_VARIANTS: tuple[str, ...] = (
    "bar_line_shared_axis",
    "bar_line_dual_axis",
    "stacked_bar_line",
    "area_line_overlay",
)


@dataclass(frozen=True)
class RenderParams:
    canvas_width: int
    canvas_height: int
    plot_left: int
    plot_right: int
    plot_top: int
    plot_bottom: int
    axis_width: int
    grid_width: int
    line_width: int
    point_radius: int
    tick_font_size: int
    label_font_size: int
    value_font_size: int
    legend_font_size: int
    primary_rgb: tuple[int, int, int]
    primary_alt_rgb: tuple[int, int, int]
    line_rgb: tuple[int, int, int]
    area_rgb: tuple[int, int, int]
    axis_rgb: tuple[int, int, int]
    grid_rgb: tuple[int, int, int]
    text_rgb: tuple[int, int, int]
    panel_rgb: tuple[int, int, int]
    layout_jitter_meta: Mapping[str, Any]


@dataclass(frozen=True)
class ComboScene:
    image: Image.Image
    labels: tuple[str, ...]
    primary_values: tuple[int, ...]
    line_values: tuple[int, ...]
    primary_points: tuple[tuple[float, float], ...]
    line_points: tuple[tuple[float, float], ...]
    entities: tuple[dict[str, Any], ...]
    scene_variant: str
    primary_name: str
    line_name: str
    primary_axis_max: int
    line_axis_max: int
    plot_bbox: tuple[int, int, int, int]
    legend_bbox: tuple[float, float, float, float]


@dataclass(frozen=True)
class ComboDataset:
    labels: tuple[str, ...]
    primary_values: tuple[int, ...]
    line_values: tuple[int, ...]
    primary_name: str
    line_name: str
    scene_variant: str
    label_count_range: tuple[int, int]
    scene_variant_probabilities: dict[str, float]


def int_bounds(params: Mapping[str, Any], low_key: str, high_key: str, fallback: tuple[int, int]) -> tuple[int, int]:
    low = int(params.get(low_key, group_default(GENERATION_DEFAULTS, low_key, int(fallback[0]))))
    high = int(params.get(high_key, group_default(GENERATION_DEFAULTS, high_key, int(fallback[1]))))
    if low > high:
        raise ValueError(f"{low_key} must be <= {high_key}")
    return low, high


def choose_scene_variant(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    allowed_variants: Sequence[str] | None = None,
    sampling_divisor: int = 1,
) -> tuple[str, dict[str, float], dict[str, Any]]:
    support = tuple(str(value) for value in (allowed_variants or SCENE_VARIANTS))
    requested = params.get("scene_variant")
    if requested is not None:
        selected = str(requested)
        if selected not in set(support):
            raise ValueError(f"unsupported scene_variant: {selected}; supported: {support}")
        stripped = dict(params)
        stripped.pop("scene_variant", None)
        return selected, {item: (1.0 if item == selected else 0.0) for item in support}, stripped

    raw_weights = params.get("scene_variant_weights", group_default(GENERATION_DEFAULTS, "scene_variant_weights", None))
    if isinstance(raw_weights, Mapping):
        probabilities = normalize_positive_weights(
            {str(key): float(value) for key, value in raw_weights.items() if str(key) in set(support)},
            default_keys=support,
        )
    else:
        probabilities = normalize_positive_weights({}, default_keys=support)
    sample_cursor = params.get("_sample_cursor")
    positives = [key for key in support if float(probabilities.get(str(key), 0.0)) > 0.0]
    if sample_cursor is not None and positives:
        index = abs(int(sample_cursor)) // max(1, int(sampling_divisor))
        selected = str(positives[int(index) % len(positives)])
        next_params = dict(params)
        next_params["_sample_cursor"] = abs(int(sample_cursor)) // max(1, int(sampling_divisor) * len(positives))
        return selected, dict(probabilities), next_params
    rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.scene_variant")
    return str(weighted_choice(rng, probabilities, sort_keys=True)), dict(probabilities), dict(params)


__all__ = [
    "ComboDataset",
    "ComboScene",
    "DOMAIN",
    "GENERATION_DEFAULTS",
    "POST_IMAGE_BACKGROUND_DEFAULTS",
    "POST_IMAGE_NOISE_DEFAULTS",
    "PROMPT_BUNDLE_ID",
    "PROMPT_DEFAULTS",
    "RENDERING_DEFAULTS",
    "RenderParams",
    "SCENE_ID",
    "SCENE_NAMESPACE",
    "SCENE_VARIANTS",
    "choose_scene_variant",
    "int_bounds",
]
