"""Defaults for the marked-polygon-equation scene package."""

from __future__ import annotations

from trace.core.scene_config import get_scene_defaults
from trace.tasks.geometry.shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS

DOMAIN = "geometry"
SCENE_ID = "marked_polygon_equation"
SCENE_KIND = "marked_polygon_equation_diagram"
SCENE_VARIANT = "algebraic_marked_polygon"
PROMPT_BUNDLE_ID = "geometry_geo3k_marked_equations_v0"

SCENE_DEFAULTS = get_scene_defaults(DOMAIN, SCENE_ID)

__all__ = [
    "DOMAIN",
    "PROMPT_BUNDLE_ID",
    "POST_IMAGE_NOISE_DEFAULTS",
    "SCENE_DEFAULTS",
    "SCENE_ID",
    "SCENE_KIND",
    "SCENE_VARIANT",
]
