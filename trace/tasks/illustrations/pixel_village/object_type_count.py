"""Count approved public object categories in a top-down pixel village."""

from __future__ import annotations

from ...registry import register_task
from .shared.counting import PixelVillageObjectTypeCountBase


@register_task
class IllustrationsPixelVillageObjectTypeCountTask(PixelVillageObjectTypeCountBase):
    """Count approved public object categories in a top-down pixel village."""


__all__ = ["IllustrationsPixelVillageObjectTypeCountTask"]
