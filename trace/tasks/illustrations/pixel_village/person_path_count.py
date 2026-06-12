"""Count people placed directly on path tiles in a top-down pixel village."""

from __future__ import annotations

from ...registry import register_task
from .shared.counting import PixelVillagePersonPathCountBase


@register_task
class IllustrationsPixelVillagePersonPathCountTask(PixelVillagePersonPathCountBase):
    """Count people placed directly on path tiles in a top-down pixel village."""


__all__ = ["IllustrationsPixelVillagePersonPathCountTask"]
