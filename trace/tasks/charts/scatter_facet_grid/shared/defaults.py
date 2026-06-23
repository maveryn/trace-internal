"""Config and default-resolution helpers for scatter-facet-grid scenes."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.scene_config import get_scene_defaults
from trace.tasks.charts.shared.visual_defaults import (
    load_chart_scene_background_defaults,
    load_chart_scene_noise_defaults,
)
from trace.tasks.shared.config_defaults import (
    group_default,
    split_scene_generation_rendering_prompt_defaults,
)
from trace.tasks.shared.render_variation import resolve_render_int, resolve_render_rgb

from .state import RGB, SCENE_ID, SCENE_NAMESPACE


SCENE_DEFAULTS = get_scene_defaults("charts", SCENE_ID)
GEN_DEFAULTS, RENDER_DEFAULTS, PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    SCENE_DEFAULTS if isinstance(SCENE_DEFAULTS, Mapping) else {},
    task_id=SCENE_NAMESPACE,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_scene_background_defaults(scene_id=SCENE_ID)
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)


def render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


def gen_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(GEN_DEFAULTS, str(key), int(fallback))))


def gen_float(params: Mapping[str, Any], key: str, fallback: float) -> float:
    return float(params.get(str(key), group_default(GEN_DEFAULTS, str(key), float(fallback))))


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
        tuple(int(channel) for channel in fallback),
        instance_seed=render_style_seed(params),
        namespace=SCENE_NAMESPACE,
    )


__all__ = [
    "GEN_DEFAULTS",
    "POST_IMAGE_BACKGROUND_DEFAULTS",
    "POST_IMAGE_NOISE_DEFAULTS",
    "PROMPT_DEFAULTS",
    "RENDER_DEFAULTS",
    "SCENE_DEFAULTS",
    "gen_float",
    "gen_int",
    "group_default",
    "render_style_seed",
    "resolve_int",
    "resolve_rgb",
]
