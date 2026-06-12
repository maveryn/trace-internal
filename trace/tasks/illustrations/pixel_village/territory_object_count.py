"""Count target objects inside a named pixel-village territory."""

from __future__ import annotations

from ...registry import register_task
from .shared.counting import PixelVillageTerritoryObjectCountBase


@register_task
class IllustrationsPixelVillageTerritoryObjectCountTask(PixelVillageTerritoryObjectCountBase):
    """Count target objects inside a named pixel-village territory."""


__all__ = ["IllustrationsPixelVillageTerritoryObjectCountTask"]
