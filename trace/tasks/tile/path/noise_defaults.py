"""Visual-variation defaults for the tile/path task family."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from ....core.task_group_config import get_task_group_defaults
from ....core.visual.noise import PRISM_STYLE_VALUE_RANGES


def _fallback_noise_defaults() -> Dict[str, Any]:
    """Return safe fallback defaults if config is missing or invalid."""
    return {
        "apply_prob": 0.0,
        "edit_types": ["blur", "downsample", "jpeg", "noise"],
        "edit_count_range": [1, 2],
        "value_ranges": deepcopy(PRISM_STYLE_VALUE_RANGES),
    }


def _load_family_noise_defaults() -> Dict[str, Any]:
    cfg = get_task_group_defaults("tile", "path")
    visual = cfg.get("visual", {})
    if not isinstance(visual, dict):
        return _fallback_noise_defaults()
    noise = visual.get("noise", {})
    if not isinstance(noise, dict):
        return _fallback_noise_defaults()
    return dict(noise)


# Family-level post-image noise defaults shared by tile/path tasks.
POST_IMAGE_NOISE_DEFAULTS: Dict[str, Any] = _load_family_noise_defaults()
