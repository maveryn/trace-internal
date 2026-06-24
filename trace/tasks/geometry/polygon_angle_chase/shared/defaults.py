"""Defaults for the polygon angle-chase scene."""

from __future__ import annotations

from trace.core.scene_config import get_scene_defaults

DOMAIN = "geometry"
SCENE_ID = "polygon_angle_chase"
PROMPT_BUNDLE_ID = "geometry_polygon_angle_chase_v1"

SCENE_DEFAULTS = get_scene_defaults(DOMAIN, SCENE_ID)

__all__ = ["DOMAIN", "PROMPT_BUNDLE_ID", "SCENE_DEFAULTS", "SCENE_ID"]
