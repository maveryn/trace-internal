"""Runtime rendering helpers for radar chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ....shared.font_assets import font_asset_version
from ....shared.text_rendering import temporary_default_font_family
from .profile_common import _Dataset, _Rendered, _sample_chart_font_family
from .profile_rendering import _render_dataset


@dataclass(frozen=True)
class RadarRenderResult:
    rendered_scene: _Rendered
    chart_font_family: str

    @property
    def image(self):
        return self.rendered_scene.image


def render_radar_dataset(
    *,
    dataset: _Dataset,
    params: Mapping[str, Any],
    instance_seed: int,
) -> RadarRenderResult:
    chart_font_family = _sample_chart_font_family(int(instance_seed), params)
    with temporary_default_font_family(str(chart_font_family)):
        rendered_scene = _render_dataset(dataset, params=params, instance_seed=int(instance_seed))
    return RadarRenderResult(rendered_scene=rendered_scene, chart_font_family=str(chart_font_family))


def font_assets_payload(*, chart_font_family: str) -> dict[str, str]:
    return {
        "font_asset_version": font_asset_version(),
        "chart_font_family": str(chart_font_family),
    }


__all__ = ["RadarRenderResult", "font_assets_payload", "render_radar_dataset"]
