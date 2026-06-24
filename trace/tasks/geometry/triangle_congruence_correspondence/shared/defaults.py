"""Scene defaults for triangle-congruence correspondence tasks."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.scene_config import get_scene_defaults
from trace.tasks.geometry.shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS
from trace.tasks.shared.config_defaults import split_scene_generation_rendering_prompt_defaults

from .state import SCENE_ID

_SCENE_DEFAULTS = get_scene_defaults("geometry", SCENE_ID)


def load_triangle_congruence_defaults(owner: str) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    """Load generation, rendering, and prompt defaults for one public entry."""

    return split_scene_generation_rendering_prompt_defaults(
        _SCENE_DEFAULTS,
        task_id=str(owner),
    )


__all__ = ["POST_IMAGE_NOISE_DEFAULTS", "load_triangle_congruence_defaults"]
