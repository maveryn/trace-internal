
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping

from PIL import Image

from trace.tasks.charts.scatter_facet_grid.shared.facet_grid_query import (
    _Dataset,
    _REASONING_LOAD_BY_QUERY,
    _all_panel_points,
    _panel_records,
)
from trace.tasks.charts.scatter_facet_grid.shared.prompts import build_prompt_artifacts, dynamic_slots
from trace.tasks.charts.scatter_facet_grid.shared.runtime import (
    ScatterFacetRenderResult,
    font_assets_payload,
    render_scatter_facet_dataset,
)
from trace.tasks.shared.prompt_variants import PromptTraceArtifacts, build_prompt_query_spec


@dataclass(frozen=True)
class ScatterFacetTaskComponents:
    prompt: str
    prompt_variants: Dict[str, str]
    answer_type: str
    answer_value: str
    annotation_type: str
    annotation_value: Dict[str, List[float]]
    image: Image.Image
    query_id: str
    trace_payload: Dict[str, Any]


def annotation_payload(*, dataset: _Dataset, rendered: ScatterFacetRenderResult) -> Dict[str, Any]:
    rendered_scene = rendered.rendered_scene
    annotation_bbox_map = {
        "answer_density_region": list(rendered_scene.density_region_bboxes[str(dataset.query.answer_label)])
    }
    return {
        "type": "keyed_bbox_map",
        "keyed_bbox_map": dict(annotation_bbox_map),
        "projected": {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(annotation_bbox_map),
            "pixel_keyed_bbox_map": dict(annotation_bbox_map),
            "answer_panel_label": str(dataset.query.answer_label),
            "annotation_point_ids": list(dataset.query.annotation_point_ids),
        },
    }




def build_trace_payload(
    *,
    dataset: _Dataset,
    rendered: ScatterFacetRenderResult,
    prompt_artifacts: PromptTraceArtifacts,
    query_id: str,
    annotation_payload: Mapping[str, Any],
) -> Dict[str, Any]:
    rendered_scene = rendered.rendered_scene
    total_points = len([point for panel in dataset.panels for point in _all_panel_points(panel)])
    panel_records = _panel_records(dataset.panels)
    query_params = {
        "query_id": str(query_id),
        "scene_variant": "facet_grid",
        **dict(dataset.query.trace),
    }
    return {
        "scene_ir": {
            "scene_kind": "chart_scatter_facet_grid",
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": {
                "query_id": str(query_id),
                "target_region": str(dataset.query.region),
                "answer": str(dataset.query.answer_label),
                "panel_count": int(len(dataset.panels)),
            },
        },
        "query_spec": build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(query_id),
            params=query_params,
        ),
        "render_spec": {
            "scene_variant": "facet_grid",
            "canvas_width": int(rendered.render_params.canvas_width),
            "canvas_height": int(rendered.render_params.canvas_height),
            "coord_space": "pixel",
            "layout_id": str(dataset.layout_id),
            "rows": int(dataset.rows),
            "cols": int(dataset.cols),
            "panel_count": int(len(dataset.panels)),
            "point_radius_px": int(rendered.render_params.point_radius_px),
            "layout_jitter": dict(rendered.render_params.layout_jitter_meta),
            "font_assets": font_assets_payload(chart_font_family=rendered.chart_font_family),
            "post_image_noise": dict(rendered.post_noise_meta),
        },
        "render_map": {
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
        },
        "execution_trace": {
            "query_id": str(query_id),
            "scene_variant": "facet_grid",
            "question_format": "scatter_facet_grid_query",
            "answer": str(dataset.query.answer_label),
            "answer_type": "string",
            "panel_labels": [str(panel.label) for panel in dataset.panels],
            "panels": list(panel_records),
            "target_region": str(dataset.query.region),
            "target_region_phrase": str(dataset.query.trace["target_region_phrase"]),
            "panel_count": int(len(dataset.panels)),
            "layout_id": str(dataset.layout_id),
            "layout_rows": int(dataset.rows),
            "layout_cols": int(dataset.cols),
            "total_point_count": int(total_points),
            "annotation_point_ids": list(dataset.query.annotation_point_ids),
            "title_text": str(rendered_scene.title_text),
            **dict(dataset.query.trace),
        },
        "witness_symbolic": {
            "type": "scatter_facet_grid_witness",
            "answer_panel_label": str(dataset.query.answer_label),
            "target_region": str(dataset.query.region),
            "annotation_point_ids": list(dataset.query.annotation_point_ids),
            "answer": str(dataset.query.answer_label),
        },
        "projected_annotation": dict(annotation_payload["projected"]),
        "background": dict(rendered.background_meta),
        "post_image_noise": dict(rendered.post_noise_meta),
    }


def build_scatter_facet_task_components(
    *,
    dataset: _Dataset,
    params: Mapping[str, Any],
    instance_seed: int,
    query_id: str,
) -> ScatterFacetTaskComponents:
    rendered = render_scatter_facet_dataset(
        dataset=dataset,
        params=params,
        instance_seed=int(instance_seed),
    )
    annotation = annotation_payload(dataset=dataset, rendered=rendered)
    prompt_artifacts = build_prompt_artifacts(
        prompt_query_key=str(query_id),
        dynamic_slot_values=dynamic_slots(dataset=dataset),
        instance_seed=int(instance_seed),
    )
    trace_payload = build_trace_payload(
        dataset=dataset,
        rendered=rendered,
        prompt_artifacts=prompt_artifacts,
        query_id=str(query_id),
        annotation_payload=annotation,
    )
    return ScatterFacetTaskComponents(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        answer_type="string",
        answer_value=str(dataset.query.answer_label),
        annotation_type=str(annotation["type"]),
        annotation_value=dict(annotation["keyed_bbox_map"]),
        image=rendered.image,
        query_id=str(query_id),
        trace_payload=trace_payload,
    )


