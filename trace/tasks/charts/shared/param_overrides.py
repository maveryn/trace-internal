"""Shared task-local parameter override helpers for chart tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping


def merge_mapping_overrides(base: Mapping[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    """Return one shallow merged params mapping."""

    merged = dict(base)
    for key, value in override.items():
        merged[str(key)] = value
    return merged


def apply_task_variant_overrides(params: Mapping[str, Any], *, task_variant: str) -> Dict[str, Any]:
    """Apply optional task-variant-specific params overrides."""

    variant_overrides = params.get("task_variant_overrides")
    if not isinstance(variant_overrides, Mapping):
        return dict(params)
    override = variant_overrides.get(str(task_variant))
    if not isinstance(override, Mapping):
        return dict(params)
    filtered = {
        str(key): value
        for key, value in override.items()
        if str(key) != "scene_variant_overrides"
    }
    return merge_mapping_overrides(params, filtered)


def apply_scene_variant_overrides(
    params: Mapping[str, Any],
    *,
    task_variant: str,
    scene_variant: str,
) -> Dict[str, Any]:
    """Apply optional scene-specific overrides nested under one task variant."""

    variant_overrides = params.get("task_variant_overrides")
    if not isinstance(variant_overrides, Mapping):
        return dict(params)
    task_variant_override = variant_overrides.get(str(task_variant))
    if not isinstance(task_variant_override, Mapping):
        return dict(params)
    scene_variant_overrides = task_variant_override.get("scene_variant_overrides")
    if not isinstance(scene_variant_overrides, Mapping):
        return dict(params)
    override = scene_variant_overrides.get(str(scene_variant))
    if not isinstance(override, Mapping):
        return dict(params)
    return merge_mapping_overrides(params, override)
