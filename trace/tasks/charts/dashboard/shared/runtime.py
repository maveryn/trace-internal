"""Runtime helpers for dashboard chart tasks."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from trace.core.types import TypedValue
from trace.core.visual.background import make_background_canvas
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.charts.dashboard.shared.cross_panel_common import (
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    SCENE_ID,
    _REASONING_LOAD_BY_VARIANT,
    _SCENE_LOAD_BY_VARIANT,
    _Category,
    _Dataset,
    _Panel,
    _Rendered,
    _resolve_context_text_params,
    _resolve_render_params,
)
from trace.tasks.charts.dashboard.shared.cross_panel_rendering import (
    _bbox_map_to_json,
    _nested_bbox_map_to_json,
    _nested_point_map_to_json,
    _render_dashboard,
)
from trace.tasks.shared.font_assets import font_asset_version
from trace.tasks.shared.visual_style.context_layer import context_text_layer_metadata


AnnotationRef = Tuple[str, str]


def render_dataset(
    dataset: _Dataset,
    *,
    params: Mapping[str, Any],
    instance_seed: int,
) -> tuple[_Rendered, Dict[str, Any], Dict[str, Any]]:
    render_style_params = {**dict(params), "_render_style_seed": int(instance_seed)}
    render_params = _resolve_render_params(render_style_params)
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=dict(params),
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    rendered = _render_dashboard(
        background,
        dataset=dataset,
        render_params=render_params,
        params=dict(params),
        instance_seed=int(instance_seed),
    )
    image, post_noise_meta = apply_post_image_noise(
        rendered.image,
        instance_seed=int(instance_seed),
        params=dict(params),
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    rendered = replace(rendered, image=image)
    render_meta = {
        "canvas_width": int(render_params.canvas_width),
        "canvas_height": int(render_params.canvas_height),
        "coord_space": "pixel",
        "panel_count": int(len(dataset.panels)),
        "category_count": int(len(dataset.categories)),
        "layout_jitter": dict(render_params.layout_jitter_meta),
        "font_assets": {
            "asset_version": font_asset_version(),
            "chart_font_family": str(render_params.font_family),
        },
        "context_text_layer": context_text_layer_metadata(
            [],
            enabled=bool(rendered.context_text_layout.get("enabled", True)),
            layout_mode=f"{rendered.context_text_layout.get('layout_mode', 'reserved_context')}:{rendered.context_text_layout.get('placement', 'none')}",
            layout_spec=dict(rendered.context_text_layout),
        )
        | {
            "element_count": int(len(rendered.context_text_elements)),
            "elements": [dict(element) for element in rendered.context_text_elements],
        },
        "post_image_noise": dict(post_noise_meta),
    }
    return rendered, render_meta, {"background": dict(background_meta), "post_image_noise": dict(post_noise_meta)}


def _annotation_records(
    *,
    annotation_refs: Sequence[AnnotationRef],
    rendered: _Rendered,
    panels_by_id: Mapping[str, _Panel],
    categories_by_id: Mapping[str, _Category],
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for panel_id, category_id in annotation_refs:
        records.append(
            {
                "panel_id": str(panel_id),
                "panel_name": str(panels_by_id[str(panel_id)].name),
                "category_id": str(category_id),
                "category_label": str(categories_by_id[str(category_id)].label),
                "point_xy": list(rendered.support_points_px[str(panel_id)][str(category_id)]),
                "bbox_xyxy": list(rendered.support_bboxes_px[str(panel_id)][str(category_id)]),
            }
        )
    return records


def annotation_payload(
    *,
    dataset: _Dataset,
    rendered: _Rendered,
    annotation_kind: str,
) -> tuple[str, Dict[str, List[int]] | List[List[int]], Dict[str, Any], List[AnnotationRef]]:
    annotation_refs = [(str(panel_id), str(category_id)) for panel_id, category_id in dataset.query.annotation_refs]
    panels_by_id = {str(panel.panel_id): panel for panel in dataset.panels}
    categories_by_id = {str(category.category_id): category for category in dataset.categories}
    records = _annotation_records(
        annotation_refs=annotation_refs,
        rendered=rendered,
        panels_by_id=panels_by_id,
        categories_by_id=categories_by_id,
    )

    if str(annotation_kind) == "source_target":
        value = {
            "source_panel": list(rendered.support_points_px[annotation_refs[0][0]][annotation_refs[0][1]]),
            "target_panel": list(rendered.support_points_px[annotation_refs[1][0]][annotation_refs[1][1]]),
        }
        return "keyed_point_map", dict(value), _project_keyed_points(value, records), annotation_refs

    if str(annotation_kind) == "dual_source_target_sum":
        value = {
            "first_source_panel": list(rendered.support_points_px[annotation_refs[0][0]][annotation_refs[0][1]]),
            "second_source_panel": list(rendered.support_points_px[annotation_refs[1][0]][annotation_refs[1][1]]),
            "target_first_category": list(rendered.support_points_px[annotation_refs[2][0]][annotation_refs[2][1]]),
            "target_second_category": list(rendered.support_points_px[annotation_refs[3][0]][annotation_refs[3][1]]),
        }
        return "keyed_point_map", dict(value), _project_keyed_points(value, records), annotation_refs

    if str(annotation_kind) == "label_pair":
        value = (
            {
                "first_panel": list(rendered.support_points_px[annotation_refs[0][0]][annotation_refs[0][1]]),
                "second_panel": list(rendered.support_points_px[annotation_refs[1][0]][annotation_refs[1][1]]),
            }
            if len(annotation_refs) == 2
            else {}
        )
        return "keyed_point_map", dict(value), _project_keyed_points(value, records), annotation_refs

    if str(annotation_kind) == "statement_option":
        value = {
            "first_mark": list(rendered.support_points_px[annotation_refs[0][0]][annotation_refs[0][1]]),
            "second_mark": list(rendered.support_points_px[annotation_refs[1][0]][annotation_refs[1][1]]),
        }
        return "keyed_point_map", dict(value), _project_keyed_points(value, records), annotation_refs

    point_set = [
        list(rendered.support_points_px[str(panel_id)][str(category_id)])
        for panel_id, category_id in annotation_refs
    ]
    return (
        "point_set",
        list(point_set),
        {
            "type": "point_set",
            "point_set": list(point_set),
            "pixel_point_set": list(point_set),
            "annotation_refs": records,
        },
        annotation_refs,
    )


def _project_keyed_points(value: Mapping[str, Sequence[int]], records: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    points = {str(key): [int(point[0]), int(point[1])] for key, point in value.items()}
    return {
        "type": "keyed_point_map",
        "keyed_point_map": dict(points),
        "pixel_keyed_point_map": dict(points),
        "annotation_refs": [dict(record) for record in records],
    }


def answer_typed_value(dataset: _Dataset) -> TypedValue:
    answer_value: int | str = int(dataset.query.answer) if str(dataset.query.answer_type) == "integer" else str(dataset.query.answer)
    return TypedValue(type=str(dataset.query.answer_type), value=answer_value)


def build_trace_scaffold(
    *,
    dataset: _Dataset,
    rendered: _Rendered,
    render_meta: Mapping[str, Any],
    sidecar_meta: Mapping[str, Any],
    projected_annotation: Mapping[str, Any],
    annotation_refs: Sequence[AnnotationRef],
    answer_value: int | str,
) -> Dict[str, Any]:
    categories_by_id = {str(category.category_id): category for category in dataset.categories}
    values_by_panel = {
        str(panel.panel_id): {
            "panel_name": str(panel.name),
            "panel_kind": str(panel.kind),
            "values_by_category_id": {
                str(category_id): int(value)
                for category_id, value in panel.values_by_category_id.items()
            },
            "values_by_category_label": {
                str(categories_by_id[str(category_id)].label): int(value)
                for category_id, value in panel.values_by_category_id.items()
            },
        }
        for panel in dataset.panels
    }
    category_records = [
        {
            "category_id": str(category.category_id),
            "label": str(category.label),
            "color_rgb": list(category.color_rgb),
        }
        for category in dataset.categories
    ]
    panel_records = [
        {
            "panel_id": str(panel.panel_id),
            "panel_kind": str(panel.kind),
            "panel_name": str(panel.name),
        }
        for panel in dataset.panels
    ]
    return {
        "scene_ir": {
            "scene_kind": "chart_mixed_dashboard",
            "entities": [dict(entity) for entity in rendered.entities],
            "relations": {
                "scene_variant": str(dataset.scene_variant),
                "answer": answer_value,
                "annotation_refs": [list(ref) for ref in annotation_refs],
                "answerability": str(dataset.query.params.get("answerability", "answerable")),
                **(
                    {"absence_proof": dict(dataset.query.params["absence_proof"])}
                    if str(dataset.query.params.get("answerability")) == "unanswerable"
                    else {}
                ),
            },
        },
        "render_spec": dict(render_meta),
        "render_map": {
            "image_id": "img0",
            "panel_bboxes_px": _bbox_map_to_json(rendered.panel_bboxes_px),
            "support_bboxes_px": _nested_bbox_map_to_json(rendered.support_bboxes_px),
            "support_points_px": _nested_point_map_to_json(rendered.support_points_px),
            "value_label_bboxes_px": _nested_bbox_map_to_json(rendered.value_label_bboxes_px),
            "option_statement_bboxes_px": _bbox_map_to_json(rendered.option_statement_bboxes_px),
            "context_text_bboxes_px": {
                str(element["context_id"]): [int(value) for value in element["bbox_xyxy"]]
                for element in rendered.context_text_elements
            },
        },
        "execution_trace": {
            "scene_id": SCENE_ID,
            "scene_variant": str(dataset.scene_variant),
            "question_format": "dashboard_cross_panel_query",
            "answer": answer_value,
            "answer_type": str(dataset.query.answer_type),
            "category_count": int(len(dataset.categories)),
            "panel_count": int(len(dataset.panels)),
            "categories": list(category_records),
            "panels": list(panel_records),
            "panel_order": [str(panel.panel_id) for panel in dataset.panels],
            "panel_kinds": [str(panel.kind) for panel in dataset.panels],
            "values_by_panel": dict(values_by_panel),
            "annotation_refs": [list(ref) for ref in annotation_refs],
            **dict(dataset.query.params),
        },
        "witness_symbolic": {
            "type": "dashboard_cross_panel_witness",
            "annotation_refs": [list(ref) for ref in annotation_refs],
            "answer": answer_value,
            "answerability": str(dataset.query.params.get("answerability", "answerable")),
            **(
                {"absence_proof": dict(dataset.query.params["absence_proof"])}
                if str(dataset.query.params.get("answerability")) == "unanswerable"
                else {}
            ),
        },
        "projected_annotation": dict(projected_annotation),
        **dict(sidecar_meta),
    }




