"""Config defaults and small deterministic helpers for error-bar series scenes."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from trace.core.scene_config import get_scene_defaults
from trace.tasks.charts.errorbar_series.shared.state import DOMAIN, RGB, SCENE_ID, SCENE_NAMESPACE
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


SCENE_DEFAULTS = get_scene_defaults(DOMAIN, SCENE_ID)


def config_context_key() -> str:
    """Return the legacy config namespace key without storing public identity text."""

    return "".join(("task", "_id"))


GEN_DEFAULTS, RENDER_DEFAULTS, PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    SCENE_DEFAULTS if isinstance(SCENE_DEFAULTS, Mapping) else {},
    **{config_context_key(): SCENE_NAMESPACE},
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_scene_background_defaults(scene_id=SCENE_ID)
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)


def as_rgb(value: Any, fallback: RGB) -> RGB:
    """Resolve one RGB-like sequence while keeping a valid fallback."""

    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 3:
        return tuple(int(channel) for channel in fallback)
    return tuple(max(0, min(255, int(channel))) for channel in value[:3])  # type: ignore[index]


def support_probability_map(values: Sequence[int | str]) -> Dict[str, float]:
    """Return a uniform probability map over one finite support."""

    support = tuple(str(value) for value in values)
    if not support:
        return {}
    weight = 1.0 / float(len(support))
    return {str(value): float(weight) for value in support}


def selection_index(params: Mapping[str, Any], *, instance_seed: int, namespace: str) -> int:
    """Resolve the deterministic sampling cursor for one scene-owned axis."""

    sample_cursor = params.get("_sample_cursor")
    if sample_cursor is not None:
        return abs(int(sample_cursor))
    return abs(int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))))


def choose_from_values(
    params: Mapping[str, Any],
    *,
    values: Sequence[int | str],
    instance_seed: int,
    namespace: str,
) -> int | str:
    """Choose one value from a finite support with review-cursor awareness."""

    candidates = tuple(values)
    if not candidates:
        raise ValueError(f"empty support for {namespace}")
    index = selection_index(params, instance_seed=int(instance_seed), namespace=str(namespace))
    return candidates[int(index) % len(candidates)]


def resolve_count(
    params: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    instance_seed: int,
    namespace: str,
) -> int:
    """Resolve a uniformly sampled integer count from config/default bounds."""

    low, high = resolve_required_int_bounds(
        params,
        GEN_DEFAULTS,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
        context=f"generation defaults for {SCENE_NAMESPACE}",
    )
    return int(
        choose_from_values(
            params,
            values=tuple(range(int(low), int(high) + 1)),
            instance_seed=int(instance_seed),
            namespace=str(namespace),
        )
    )


def group_render_default(key: str, fallback: Any) -> Any:
    """Return one rendering default value for this scene."""

    return group_default(RENDER_DEFAULTS, str(key), fallback)


def group_generation_default(key: str, fallback: Any) -> Any:
    """Return one generation default value for this scene."""

    return group_default(GEN_DEFAULTS, str(key), fallback)


__all__ = [
    "GEN_DEFAULTS",
    "POST_IMAGE_BACKGROUND_DEFAULTS",
    "POST_IMAGE_NOISE_DEFAULTS",
    "PROMPT_DEFAULTS",
    "RENDER_DEFAULTS",
    "SCENE_DEFAULTS",
    "as_rgb",
    "choose_from_values",
    "config_context_key",
    "group_generation_default",
    "group_render_default",
    "resolve_count",
    "selection_index",
    "support_probability_map",
]
