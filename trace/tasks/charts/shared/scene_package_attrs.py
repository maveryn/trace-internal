"""Helpers for scene-package chart implementation metadata."""

from __future__ import annotations

from typing import Any, MutableMapping


def apply_chart_scene_package_attrs(namespace: MutableMapping[str, Any], *, scene_id: str) -> None:
    """Attach chart scene-package metadata to scene-local task classes.

    Scene-local shared modules are implementation helpers, but tests and local
    diagnostics sometimes instantiate their task classes directly. Public task
    files still own registration; this helper only gives shared implementation
    classes the same domain/scene metadata needed by prompt/style assembly.
    """

    for value in list(namespace.values()):
        if not isinstance(value, type):
            continue
        if not str(value.__name__).startswith("Charts"):
            continue
        if not hasattr(value, "domain"):
            value.domain = "charts"
        if not hasattr(value, "scene_id"):
            value.scene_id = str(scene_id)
