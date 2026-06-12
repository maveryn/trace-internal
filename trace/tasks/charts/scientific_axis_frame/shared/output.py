
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping

from PIL import Image

from trace.tasks.charts.scientific_axis_frame.shared.axis_frame_query import (
    TICK_SPACING_QUERY_IDS,
    _Dataset,
    _REASONING_LOAD_BY_QUERY,
    _tick_count_bounds,
)
from trace.tasks.charts.scientific_axis_frame.shared.prompts import build_prompt_artifacts, dynamic_slots
from trace.tasks.charts.scientific_axis_frame.shared.runtime import (
    AxisFrameRenderResult,
    font_assets_payload,
    render_axis_frame_dataset,
)
from trace.tasks.shared.prompt_variants import PromptTraceArtifacts, build_prompt_query_spec


@dataclass(frozen=True)
class AxisFrameTaskComponents:
    prompt: str
    prompt_variants: Dict[str, str]
    answer_type: str
    answer_value: int
    annotation_type: str
    annotation_value: Dict[str, List[float]]
    image: Image.Image
    query_id: str
    trace_payload: Dict[str, Any]


def annotation_payload(*, dataset: _Dataset, rendered: AxisFrameRenderResult) -> Dict[str, Any]:
    rendered_scene = rendered.rendered_scene
    if str(dataset.query.query_id) in set(TICK_SPACING_QUERY_IDS):
        first_key, next_key = dataset.query.annotation_keys
        bbox_map = {
            "first_tick": list(rendered_scene.tick_label_bboxes_px[str(first_key)]),
            "next_tick": list(rendered_scene.tick_label_bboxes_px[str(next_key)]),
        }
    else:
        min_key, max_key = dataset.query.annotation_keys
        bbox_map = {
            "min_tick": list(rendered_scene.tick_label_bboxes_px[str(min_key)]),
            "max_tick": list(rendered_scene.tick_label_bboxes_px[str(max_key)]),
        }
    return {
        "type": "keyed_bbox_map",
        "bbox_map": dict(bbox_map),
        "projected": {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(bbox_map),
            "pixel_keyed_bbox_map": dict(bbox_map),
        },
    }




def build_trace_payload(
    *,
    dataset: _Dataset,
    rendered: AxisFrameRenderResult,
    prompt_artifacts: PromptTraceArtifacts,
    query_id: str,
    query_id_probabilities: Mapping[str, float],
    annotation_payload: Mapping[str, Any],
) -> Dict[str, Any]:
    rendered_scene = rendered.rendered_scene
    execution_trace = {
        "query_id": str(query_id),
        "scene_id": "scientific_axis_frame",
        "question_format": "scientific_axis_frame",
        "answer_value": int(dataset.query.answer),
        "answer_type": str(dataset.query.answer_type),
        "x_tick_values": [int(value) for value in dataset.x_axis.values],
        "y_tick_values": [int(value) for value in dataset.y_axis.values],
        "x_tick_step": int(dataset.x_axis.step),
        "y_tick_step": int(dataset.y_axis.step),
        "x_axis_span": int(dataset.x_axis.values[-1] - dataset.x_axis.values[0]),
        "y_axis_span": int(dataset.y_axis.values[-1] - dataset.y_axis.values[0]),
        "series_points": [[round(float(x), 3), round(float(y), 3)] for x, y in dataset.series_points],
        "annotation_tick_keys": list(dataset.query.annotation_keys),
        "query_params": dict(dataset.query.trace),
        "query_id_probabilities": dict(query_id_probabilities),
    }
    return {
        "scene_ir": {
            "scene_kind": "chart_scientific_axis_frame",
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": {
                "query_id": str(query_id),
                "scene_id": "scientific_axis_frame",
                "annotation_tick_keys": list(dataset.query.annotation_keys),
            },
        },
        "query_spec": build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(query_id),
            params={
                "query_id": str(query_id),
                "scene_id": "scientific_axis_frame",
                "query_id_probabilities": dict(query_id_probabilities),
                **dict(dataset.query.trace),
            },
        ),
        "render_spec": {
            "canvas_width": int(rendered.image.size[0]),
            "canvas_height": int(rendered.image.size[1]),
            "coord_space": "pixel",
            "scene_id": "scientific_axis_frame",
            "plot_bbox_px": list(rendered_scene.plot_bbox_px),
            "font_assets": font_assets_payload(chart_font_family=rendered.chart_font_family),
            **dict(rendered_scene.render_meta),
        },
        "render_map": {
            "image_id": "img0",
            "plot_bbox_px": list(rendered_scene.plot_bbox_px),
            "tick_label_bboxes_px": dict(rendered_scene.tick_label_bboxes_px),
            "axis_label_bboxes_px": dict(rendered_scene.axis_label_bboxes_px),
        },
        "execution_trace": dict(execution_trace),
        "witness_symbolic": {
            "type": "axis_tick_label_witness",
            "tick_keys": list(dataset.query.annotation_keys),
            "answer": int(dataset.query.answer),
        },
        "projected_annotation": dict(annotation_payload["projected"]),
    }


def build_axis_frame_task_components(
    *,
    dataset: _Dataset,
    params: Mapping[str, Any],
    instance_seed: int,
    query_id: str,
    query_id_probabilities: Mapping[str, float],
) -> AxisFrameTaskComponents:
    rendered = render_axis_frame_dataset(
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
        query_id_probabilities=query_id_probabilities,
        annotation_payload=annotation,
    )
    return AxisFrameTaskComponents(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        answer_type=str(dataset.query.answer_type),
        answer_value=int(dataset.query.answer),
        annotation_type=str(annotation["type"]),
        annotation_value=dict(annotation["bbox_map"]),
        image=rendered.image,
        query_id=str(query_id),
        trace_payload=trace_payload,
    )


