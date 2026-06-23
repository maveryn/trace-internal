"""Neutral trace-output helpers for scatter-facet-grid chart scenes."""

from __future__ import annotations

from typing import Any, Sequence

from .rendering import all_panel_points, font_assets_payload
from .state import Dataset, Panel, Point, ScatterFacetRenderResult


def point_records(points: Sequence[Point]) -> list[dict[str, Any]]:
    return [
        {
            "point_id": str(point.point_id),
            "panel_label": str(point.panel_label),
            "x_value": round(float(point.x_value), 3),
            "y_value": round(float(point.y_value), 3),
            "layer": str(point.layer),
        }
        for point in points
    ]


def panel_records(panels: Sequence[Panel]) -> list[dict[str, Any]]:
    return [
        {
            "label": str(panel.label),
            "color_rgb": [int(channel) for channel in panel.color_rgb],
            "target_density_score": round(float(panel.target_density_score), 5),
            "target_point_count": int(panel.target_point_count),
            "target_spread": round(float(panel.target_spread), 3),
            "background_points": point_records(panel.background_points),
            "target_points": point_records(panel.target_points),
            "distractor_points": point_records(panel.distractor_points),
        }
        for panel in panels
    ]


def render_spec(rendered: ScatterFacetRenderResult) -> dict[str, Any]:
    font_assets = font_assets_payload(chart_font_family=rendered.chart_font_family)
    return {
        "canvas_width": int(rendered.render_params.canvas_width),
        "canvas_height": int(rendered.render_params.canvas_height),
        "coord_space": "pixel",
        "layout_id": "",
        "point_radius_px": int(rendered.render_params.point_radius_px),
        "layout_jitter": dict(rendered.render_params.layout_jitter_meta),
        "font_asset_version": str(font_assets["font_asset_version"]),
        "chart_font_family": str(font_assets["chart_font_family"]),
        "font_assets": dict(font_assets),
        "post_image_noise": dict(rendered.post_noise_meta),
    }


def render_map(rendered: ScatterFacetRenderResult) -> dict[str, Any]:
    rendered_scene = rendered.rendered_scene
    return {
        "image_id": "img0",
        "panel_bboxes_px": dict(rendered_scene.panel_bboxes),
        "panel_label_bboxes_px": dict(rendered_scene.panel_label_bboxes),
        "target_region_bboxes_px": dict(rendered_scene.region_bboxes),
        "density_region_bboxes_px": dict(rendered_scene.density_region_bboxes),
        "point_bboxes_px": dict(rendered_scene.point_bboxes),
        "point_centers_px": dict(rendered_scene.point_centers),
        "title_bbox_px": list(rendered_scene.title_bbox_px),
        "x_axis_label_bbox_px": list(rendered_scene.x_axis_label_bbox_px),
        "y_axis_label_bbox_px": list(rendered_scene.y_axis_label_bbox_px),
    }


def base_execution_record(dataset: Dataset) -> dict[str, Any]:
    total_points = len([point for panel in dataset.panels for point in all_panel_points(panel)])
    return {
        "scene_variant": "facet_grid",
        "answer": str(dataset.query.answer_label),
        "answer_type": "string",
        "panel_labels": [str(panel.label) for panel in dataset.panels],
        "panels": panel_records(dataset.panels),
        "target_region": str(dataset.query.target_region),
        "target_region_phrase": str(dataset.query.trace["target_region_phrase"]),
        "panel_count": int(len(dataset.panels)),
        "layout_id": str(dataset.layout_id),
        "layout_rows": int(dataset.rows),
        "layout_cols": int(dataset.cols),
        "total_point_count": int(total_points),
        "annotation_point_ids": list(dataset.query.annotation_point_ids),
        **dict(dataset.query.trace),
    }


__all__ = ["base_execution_record", "panel_records", "point_records", "render_map", "render_spec"]
