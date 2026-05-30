"""Chart-domain visual-default loader helpers."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from ...shared.font_assets import font_asset_version, sample_font_family
from ...shared.visual_defaults import default_noise_fallback, load_task_group_background_defaults, load_task_group_noise_defaults


def solid_light_background_fallback() -> Dict[str, Any]:
    """Return the canonical low-structure chart background fallback."""

    return {
        "enabled": True,
        "styles": {
            "solid_light": {
                "kind": "solid",
                "color": [248, 248, 248],
            }
        },
        "weights": {"solid_light": 1.0},
    }


def load_chart_background_defaults(*, task_group: str) -> Dict[str, Any]:
    """Load chart-task background config with the canonical fallback."""

    return load_task_group_background_defaults(
        domain="charts",
        task_group=str(task_group),
        fallback=solid_light_background_fallback(),
        merge_with_fallback=True,
    )


def load_chart_noise_defaults(*, task_group: str, apply_prob: float) -> Dict[str, Any]:
    """Load chart-task post-image noise config with the canonical fallback."""

    return load_task_group_noise_defaults(
        domain="charts",
        task_group=str(task_group),
        fallback=default_noise_fallback(apply_prob=float(apply_prob)),
        merge_with_fallback=False,
    )


def sample_chart_font_family(
    *,
    instance_seed: int,
    namespace: str,
    params: Mapping[str, Any],
    exclude_tags: Sequence[str] = ("display",),
) -> str:
    """Sample one chart text font family from the shared vendored font pool."""

    return str(
        sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=str(namespace),
            params=params,
            exclude_tags=tuple(str(tag) for tag in exclude_tags),
            explicit_key="chart_font_family",
            weights_key="chart_font_family_weights",
        )
    )


def chart_font_asset_metadata(chart_font_family: str) -> Dict[str, str]:
    """Return trace metadata for the sampled chart text font."""

    return {
        "font_asset_version": str(font_asset_version()),
        "chart_font_family": str(chart_font_family),
    }


__all__ = [
    "chart_font_asset_metadata",
    "load_chart_background_defaults",
    "load_chart_noise_defaults",
    "sample_chart_font_family",
    "solid_light_background_fallback",
]
