"""Shared task-local parameter override helpers for chart tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping


def merge_mapping_overrides(base: Mapping[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    """Return one shallow merged params mapping."""

    merged = dict(base)
    for key, value in override.items():
        merged[str(key)] = value
    return merged


def _variant_override_mapping(
    params: Mapping[str, Any],
    *,
    query_variant: str,
    default_params: Mapping[str, Any] | None,
) -> Dict[str, Any]:
    """Resolve default plus explicit overrides for one query variant."""

    merged: Dict[str, Any] = {}
    default_overrides = default_params.get("query_variant_overrides") if isinstance(default_params, Mapping) else None
    if isinstance(default_overrides, Mapping):
        default_override = default_overrides.get(str(query_variant))
        if isinstance(default_override, Mapping):
            merged.update({str(key): value for key, value in default_override.items()})

    explicit_overrides = params.get("query_variant_overrides")
    if isinstance(explicit_overrides, Mapping):
        explicit_override = explicit_overrides.get(str(query_variant))
        if isinstance(explicit_override, Mapping):
            merged.update({str(key): value for key, value in explicit_override.items()})
    return merged


def apply_query_variant_overrides(
    params: Mapping[str, Any],
    *,
    query_variant: str,
    default_params: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Apply optional query-variant-specific params overrides."""

    override = _variant_override_mapping(params, query_variant=str(query_variant), default_params=default_params)
    if not override:
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
    query_variant: str,
    scene_variant: str,
    default_params: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Apply optional scene-specific overrides nested under one query variant."""

    query_variant_override = _variant_override_mapping(
        params,
        query_variant=str(query_variant),
        default_params=default_params,
    )
    if not query_variant_override:
        return dict(params)
    scene_variant_overrides = query_variant_override.get("scene_variant_overrides")
    if not isinstance(scene_variant_overrides, Mapping):
        return dict(params)
    override = scene_variant_overrides.get(str(scene_variant))
    if not isinstance(override, Mapping):
        return dict(params)
    return merge_mapping_overrides(params, override)
