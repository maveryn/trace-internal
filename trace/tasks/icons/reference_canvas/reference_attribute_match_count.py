"""Count scene icons matching selected reference-icon attributes."""

from __future__ import annotations

from ...registry import register_task
from .shared.reference_match_count import (
    ATTRIBUTE_MATCH_TASK_ID,
    _ATTRIBUTE_MATCH_ALIASES,
    _ATTRIBUTE_MATCH_VARIANTS,
    _ReferenceAttributeMatchCountTaskBase,
)


@register_task
class IconsReferenceCanvasReferenceAttributeMatchCountTask(_ReferenceAttributeMatchCountTaskBase):
    """Count scene icons matching selected reference attributes."""

    task_id = ATTRIBUTE_MATCH_TASK_ID
    domain = "icons"
    supported_variants = _ATTRIBUTE_MATCH_VARIANTS
    variant_aliases = _ATTRIBUTE_MATCH_ALIASES
    scene_kind = "icons_reference_attribute_match_count"


__all__ = ["IconsReferenceCanvasReferenceAttributeMatchCountTask"]
