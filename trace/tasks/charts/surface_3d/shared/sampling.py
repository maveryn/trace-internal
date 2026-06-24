"""Neutral sampling helpers for synthetic 3D chart scenes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from trace.core.seed import spawn_rng
from trace.tasks.charts.shared.label_assets import (
    resolve_chart_entity_labels,
    resolve_chart_panel_labels,
    validate_chart_label_namespaces,
)
from trace.tasks.shared.deterministic_sampling import resolve_selection_index

from .defaults import GEN_DEFAULTS, generation_int


TIME_POOL: tuple[int, ...] = (2018, 2019, 2020, 2021, 2022, 2023, 2024)
PALETTE: tuple[tuple[int, int, int], ...] = (
    (42, 104, 178),
    (216, 92, 74),
    (54, 148, 96),
    (139, 91, 183),
    (218, 143, 43),
    (75, 156, 190),
    (186, 85, 130),
    (108, 123, 60),
)


def choice_index(params: Mapping[str, Any], *, instance_seed: int, namespace: str) -> int:
    """Resolve a deterministic index for one scene-local sampling decision."""

    return int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=str(namespace),
        )
    )


def balanced_int(
    *,
    low: int,
    high: int,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> int:
    """Sample an integer uniformly across an inclusive support."""

    if int(low) > int(high):
        raise ValueError(f"invalid integer support for {namespace}")
    span = int(high) - int(low) + 1
    return int(low) + (choice_index(params, instance_seed=int(instance_seed), namespace=str(namespace)) % span)


def balanced_choice(
    values: Sequence[Any],
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> Any:
    """Select one value from a non-empty finite support."""

    support = list(values)
    if not support:
        raise ValueError(f"empty support for {namespace}")
    return support[choice_index(params, instance_seed=int(instance_seed), namespace=str(namespace)) % len(support)]


def sample_entity_labels(count: int, *, instance_seed: int, namespace: str) -> tuple[str, ...]:
    """Sample compact visible labels for point, series, and surface axes."""

    rng = spawn_rng(int(instance_seed), f"surface_3d.{namespace}.labels")
    resolved = resolve_chart_entity_labels(
        rng,
        count=int(count),
        min_chars=2,
        max_chars=6,
        allow_spaces=False,
    )
    return tuple(str(label) for label in resolved.labels)


def _resolved_label_metadata(resolved: Any) -> dict[str, Any]:
    return {
        "label_variant": str(resolved.label_variant),
        "label_pool_kind": str(resolved.label_pool_kind),
        "label_source_kind": str(resolved.label_source_kind),
        "label_bucket": str(resolved.label_bucket),
        "label_manifest": str(resolved.label_manifest),
        "label_filter": dict(resolved.label_filter),
        "label_bucket_probabilities": dict(resolved.label_bucket_probabilities),
    }


def sample_panel_labels(
    count: int,
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    reserved_labels: Sequence[str] = (),
) -> tuple[tuple[str, ...], dict[str, Any]]:
    """Sample panel labels while keeping namespaces distinct."""

    resolved = resolve_chart_panel_labels(
        spawn_rng(int(instance_seed), "surface_3d.panel.labels"),
        count=int(count),
        min_chars=1,
        max_chars=10,
        allow_spaces=False,
        variant_weights=params.get(
            "panel_label_variant_weights",
            GEN_DEFAULTS.get(
                "panel_label_variant_weights",
                {
                    "named_compact": 1.0,
                    "technical_topics": 1.0,
                    "condition_labels": 0.75,
                    "temporal_sequence": 0.25,
                    "report_topics": 0.5,
                },
            ),
        ),
        reserved_labels=tuple(str(label) for label in reserved_labels),
    )
    collision_check = validate_chart_label_namespaces(
        panel_labels=resolved.labels,
        other_label_groups={"reserved_labels": tuple(str(label) for label in reserved_labels)},
        context="3D panel labels",
    )
    return tuple(str(label) for label in resolved.labels), {
        "panel_label_resolution": _resolved_label_metadata(resolved),
        "panel_label_collision_check": dict(collision_check),
    }


def configured_count(params: Mapping[str, Any], key: str, fallback: int) -> int:
    """Resolve one count parameter from scene generation defaults."""

    return generation_int(params, str(key), int(fallback))


__all__ = [
    "PALETTE",
    "TIME_POOL",
    "balanced_choice",
    "balanced_int",
    "choice_index",
    "configured_count",
    "sample_entity_labels",
    "sample_panel_labels",
]
