"""Geometry-domain adapter for shared technical-diagram styling."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ...shared.visual_style.technical_diagram import (
    Color,
    TechnicalDiagramStyle,
    make_technical_diagram_background,
    resolve_technical_diagram_style,
    technical_diagram_style_metadata,
)
from .coordinate_panel_grid import CoordinatePanelStyle
from .shape_style import GeometryShapeStyle


GeometryDiagramStyle = TechnicalDiagramStyle


def resolve_geometry_diagram_style(
    *,
    instance_seed: int,
    params: Mapping[str, Any] | None = None,
    scene_id: str,
    task_group: str,
    treatments: Sequence[str] | None = None,
    protected_colors: Sequence[Color] | None = None,
    allow_dark: bool = False,
    require_grid: bool | None = None,
) -> tuple[GeometryDiagramStyle, dict[str, Any]]:
    """Resolve the shared technical style for one geometry scene."""

    resolved_params = params or {}
    return resolve_technical_diagram_style(
        instance_seed=int(instance_seed),
        namespace=f"geometry.{str(task_group)}.{str(scene_id)}.technical_diagram_style",
        treatments=treatments or resolved_params.get("technical_diagram_treatments"),
        treatment_weights=resolved_params.get("technical_diagram_treatment_weights", {}),
        palettes=resolved_params.get("technical_diagram_palettes"),
        palette_weights=resolved_params.get("technical_diagram_palette_weights", {}),
        frame_modes=resolved_params.get("technical_diagram_frame_modes"),
        frame_mode_weights=resolved_params.get("technical_diagram_frame_mode_weights", {}),
        allow_dark=bool(allow_dark),
        require_grid=require_grid,
        protected_colors=protected_colors or (),
    )


def make_geometry_diagram_background(
    *,
    canvas_width: int,
    canvas_height: int,
    style: GeometryDiagramStyle,
    instance_seed: int,
    namespace: str = "geometry.technical_diagram_background",
) -> tuple[Any, dict[str, Any]]:
    """Create a geometry technical-diagram background."""

    return make_technical_diagram_background(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        style=style,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )


def prepare_geometry_diagram_style_and_background(
    *,
    instance_seed: int,
    params: Mapping[str, Any] | None,
    scene_id: str,
    task_group: str,
    canvas_width: int,
    canvas_height: int,
    protected_colors: Sequence[Color] | None = None,
    allow_dark: bool = False,
    require_grid: bool | None = None,
    treatments: Sequence[str] | None = None,
    namespace_suffix: str = "technical_diagram_background",
) -> tuple[Any, dict[str, Any], GeometryDiagramStyle, dict[str, Any]]:
    """Resolve one geometry technical style and create its background before rendering."""

    diagram_style, diagram_style_meta = resolve_geometry_diagram_style(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=str(scene_id),
        task_group=str(task_group),
        treatments=treatments,
        protected_colors=protected_colors or (),
        allow_dark=bool(allow_dark),
        require_grid=require_grid,
    )
    background, background_meta = make_geometry_diagram_background(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        style=diagram_style,
        instance_seed=int(instance_seed),
        namespace=f"geometry.{str(task_group)}.{str(scene_id)}.{str(namespace_suffix)}",
    )
    return background, background_meta, diagram_style, diagram_style_meta


def geometry_diagram_style_metadata(style: GeometryDiagramStyle) -> dict[str, Any]:
    """Serialize a geometry technical-diagram style."""

    return technical_diagram_style_metadata(style)


def geometry_shape_style_from_diagram_style(style: GeometryDiagramStyle) -> GeometryShapeStyle:
    """Map shared technical style roles to geometry ink roles."""

    return GeometryShapeStyle(
        line_color=tuple(int(value) for value in style.stroke_rgb),
        label_color=tuple(int(value) for value in style.label_rgb),
        label_stroke_color=tuple(int(value) for value in style.label_stroke_rgb),
    )


def geometry_coordinate_panel_style_from_diagram_style(style: GeometryDiagramStyle) -> CoordinatePanelStyle:
    """Map shared technical style roles to small coordinate-panel chrome."""

    return CoordinatePanelStyle(
        panel_fill=tuple(int(value) for value in style.panel_fill_rgb),
        panel_outline=tuple(int(value) for value in style.panel_border_rgb),
        plot_fill=tuple(int(value) for value in style.panel_alt_fill_rgb),
        plot_outline=tuple(int(value) for value in style.panel_border_rgb),
        grid_color=tuple(int(value) for value in style.grid_minor_rgb),
        axis_color=tuple(int(value) for value in style.axis_rgb),
        tick_color=tuple(int(value) for value in style.secondary_stroke_rgb),
        text_color=tuple(int(value) for value in style.label_rgb),
        text_stroke_color=tuple(int(value) for value in style.label_stroke_rgb),
    )


def geometry_graph_style_from_diagram_style(
    style: GeometryDiagramStyle,
    *,
    spacing_px: int = 24,
    outer_margin_px: int = 16,
    axis_enabled: bool = True,
) -> dict[str, Any]:
    """Map shared technical style roles to the geometry graph-paper spec shape."""

    return {
        "kind": "grid",
        "base_color": list(style.panel_fill_rgb),
        "line_color": list(style.grid_minor_rgb),
        "spacing": max(4, int(spacing_px)),
        "outer_margin_px": max(0, int(outer_margin_px)),
        "line_width": int(style.grid_minor_width_px),
        "major_every": int(style.major_every),
        "major_line_color": list(style.grid_major_rgb),
        "major_line_width": int(style.grid_major_width_px),
        "axis_enabled": bool(axis_enabled),
        "axis_color": list(style.axis_rgb),
        "axis_line_width": int(style.axis_stroke_width_px),
        "axis_arrows_enabled": bool(axis_enabled),
        "axis_arrow_size": max(8, int(style.axis_stroke_width_px) * 4),
        "center_point_enabled": bool(axis_enabled),
        "center_point_color": list(style.axis_rgb),
        "center_point_radius": max(2, int(style.axis_stroke_width_px) // 2),
        "color_variation_enabled": False,
        "base_color_jitter": [0, 0],
        "line_color_jitter": [0, 0],
        "major_line_darken_range": [0, 0],
        "axis_darken_range": [0, 0],
        "center_point_darken_extra_range": [0, 0],
        "origin_label_darken_extra_range": [0, 0],
        "axis_scale_labels_enabled": True,
        "axis_scale_label_max_abs": 0,
        "origin_label_enabled": False,
        "origin_label_text": "0",
        "origin_label_color": list(style.label_rgb),
        "supersample_scale": 1,
        "scene_supersample_scale": 3,
    }


__all__ = [
    "GeometryDiagramStyle",
    "geometry_coordinate_panel_style_from_diagram_style",
    "geometry_diagram_style_metadata",
    "geometry_graph_style_from_diagram_style",
    "geometry_shape_style_from_diagram_style",
    "make_geometry_diagram_background",
    "prepare_geometry_diagram_style_and_background",
    "resolve_geometry_diagram_style",
]
