"""Runtime rendering helpers for scientific axis-frame tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from PIL import Image

from ....shared.text_rendering import temporary_default_font_family
from ...shared.visual_defaults import chart_font_asset_metadata, sample_chart_font_family
from .axis_frame_query import TASK_ID, _Dataset, _Rendered, _render_dataset


@dataclass(frozen=True)
class AxisFrameRenderResult:
    image: Image.Image
    rendered_scene: _Rendered
    chart_font_family: str


def render_axis_frame_dataset(
    *,
    dataset: _Dataset,
    params: Mapping[str, Any],
    instance_seed: int,
) -> AxisFrameRenderResult:
    chart_font_family = sample_chart_font_family(
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.chart_font",
        params=params,
    )
    with temporary_default_font_family(str(chart_font_family)):
        rendered_scene = _render_dataset(
            dataset,
            params={**dict(params), "_render_style_seed": int(instance_seed)},
            instance_seed=int(instance_seed),
            chart_font_family=str(chart_font_family),
        )
    return AxisFrameRenderResult(
        image=rendered_scene.image,
        rendered_scene=rendered_scene,
        chart_font_family=str(chart_font_family),
    )


def font_assets_payload(*, chart_font_family: str) -> dict[str, Any]:
    return chart_font_asset_metadata(str(chart_font_family))


__all__ = ["AxisFrameRenderResult", "font_assets_payload", "render_axis_frame_dataset"]
