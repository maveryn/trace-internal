"""State containers for scatter-facet-grid chart scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PIL import Image


DOMAIN = "charts"
SCENE_ID = "scatter_facet_grid"
SCENE_NAMESPACE = "charts_scatter_facet_grid"

SUPPORTED_LAYOUTS: tuple[str, ...] = ("2x3", "3x3", "3x4")
TARGET_REGIONS: tuple[str, ...] = ("upper_right", "upper_left", "lower_right", "lower_left")
REGION_PHRASE_BY_REGION: dict[str, str] = {
    "upper_right": "upper-right",
    "upper_left": "upper-left",
    "lower_right": "lower-right",
    "lower_left": "lower-left",
}

RGB = tuple[int, int, int]


@dataclass(frozen=True)
class Point:
    point_id: str
    panel_label: str
    x_value: float
    y_value: float
    layer: str


@dataclass(frozen=True)
class Panel:
    label: str
    color_rgb: RGB
    background_points: tuple[Point, ...]
    target_points: tuple[Point, ...]
    distractor_points: tuple[Point, ...]
    target_density_score: float
    target_point_count: int
    target_spread: float


@dataclass(frozen=True)
class Query:
    target_region: str
    answer_label: str
    annotation_point_ids: tuple[str, ...]
    trace: dict[str, Any]


@dataclass(frozen=True)
class Dataset:
    panels: tuple[Panel, ...]
    query: Query
    rows: int
    cols: int
    layout_id: str
    label_resolution: Any


@dataclass(frozen=True)
class RenderParams:
    canvas_width: int
    canvas_height: int
    grid_left_px: int
    grid_right_px: int
    grid_top_px: int
    grid_bottom_px: int
    panel_gap_x_px: int
    panel_gap_y_px: int
    axis_line_width_px: int
    grid_line_width_px: int
    point_radius_px: int
    title_font_size_px: int
    panel_label_font_size_px: int
    axis_label_font_size_px: int
    tick_font_size_px: int
    background_point_rgb: RGB
    foreground_stroke_rgb: RGB
    region_tint_rgb: RGB
    axis_color_rgb: RGB
    grid_color_rgb: RGB
    text_color_rgb: RGB
    text_stroke_rgb: RGB
    panel_fill_rgb: RGB
    panel_border_rgb: RGB
    layout_jitter_meta: dict[str, Any]


@dataclass(frozen=True)
class RenderedScene:
    image: Image.Image
    entities: tuple[dict[str, Any], ...]
    panel_bboxes: dict[str, list[float]]
    panel_label_bboxes: dict[str, list[float]]
    region_bboxes: dict[str, list[float]]
    density_region_bboxes: dict[str, list[float]]
    point_bboxes: dict[str, list[float]]
    point_centers: dict[str, list[float]]
    title_bbox_px: list[float]
    x_axis_label_bbox_px: list[float]
    y_axis_label_bbox_px: list[float]
    title_text: str


@dataclass(frozen=True)
class ScatterFacetRenderResult:
    image: Image.Image
    rendered_scene: RenderedScene
    render_params: RenderParams
    background_meta: dict[str, Any]
    post_noise_meta: dict[str, Any]
    chart_font_family: str


__all__ = [
    "DOMAIN",
    "REGION_PHRASE_BY_REGION",
    "SCENE_ID",
    "SCENE_NAMESPACE",
    "SUPPORTED_LAYOUTS",
    "TARGET_REGIONS",
    "Dataset",
    "Panel",
    "Point",
    "Query",
    "RGB",
    "RenderedScene",
    "RenderParams",
    "ScatterFacetRenderResult",
]
