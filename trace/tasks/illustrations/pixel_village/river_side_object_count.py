"""Count target objects strictly on one side of the pixel-village river."""

from __future__ import annotations

from ...registry import register_task
from .shared.counting import PixelVillageRiverSideObjectCountBase


@register_task
class IllustrationsPixelVillageRiverSideObjectCountTask(PixelVillageRiverSideObjectCountBase):
    """Count target objects strictly on one side of the pixel-village river."""


__all__ = ["IllustrationsPixelVillageRiverSideObjectCountTask"]
