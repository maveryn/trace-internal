"""Defaults for the parallel-segment proportion scene."""

from __future__ import annotations

from trace.core.scene_config import get_scene_defaults
from trace.tasks.geometry.shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS

DOMAIN = "geometry"
SCENE_ID = "parallel_segment_proportion"
SCENE_KIND = "geometry_parallel_segment_proportion"
SCENE_VARIANT = "parallel_segment_proportion"
PROMPT_BUNDLE_ID = "geometry_parallel_segment_proportion_v1"

CONSTRUCTION_FAMILIES: tuple[str, str] = (
    "triangle_side_splitter",
    "parallel_transversals",
)

SCENE_DEFAULTS = get_scene_defaults(DOMAIN, SCENE_ID)

__all__ = [
    "CONSTRUCTION_FAMILIES",
    "DOMAIN",
    "POST_IMAGE_NOISE_DEFAULTS",
    "PROMPT_BUNDLE_ID",
    "SCENE_DEFAULTS",
    "SCENE_ID",
    "SCENE_KIND",
    "SCENE_VARIANT",
]
