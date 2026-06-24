"""Defaults and constants for split-triangle trig-chain scene packages."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.scene_config import get_scene_defaults
from trace.tasks.geometry.shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS
from trace.tasks.shared.config_defaults import split_scene_generation_rendering_prompt_defaults

from .state import DOMAIN, SCENE_ID

PROMPT_BUNDLE_ID = "geometry_split_triangle_trig_chain_v1"
SCENE_PROMPT_KEY = "split_triangle_trig_chain_scene"
TASK_PROMPT_KEY = "side_length_value_query"
SCENE_KIND = "split_triangle_trig_chain"

_SCENE_DEFAULTS = get_scene_defaults(DOMAIN, SCENE_ID)


def load_split_triangle_trig_defaults(namespace: str) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    """Load scene defaults using the public task namespace supplied by the caller."""

    return split_scene_generation_rendering_prompt_defaults(
        _SCENE_DEFAULTS,
        task_id=str(namespace),
    )


__all__ = [
    "DOMAIN",
    "POST_IMAGE_NOISE_DEFAULTS",
    "PROMPT_BUNDLE_ID",
    "SCENE_ID",
    "SCENE_KIND",
    "SCENE_PROMPT_KEY",
    "TASK_PROMPT_KEY",
    "load_split_triangle_trig_defaults",
]

