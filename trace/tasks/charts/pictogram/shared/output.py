
from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.charts.pictogram.shared.runtime import PictogramRenderResult, font_assets_payload
from trace.tasks.charts.pictogram.shared.waffle_chart import (
    _Dataset,
    _REASONING_LOAD_BY_VARIANT,
    _SCENE_VARIANT_LOADS,
    _annotation_for_query,
)
from trace.tasks.shared.prompt_variants import PromptTraceArtifacts, build_prompt_query_spec


def annotation_payload(*, dataset: _Dataset, rendered: PictogramRenderResult) -> dict[str, Any]:
    annotation_category_ids = [str(value) for value in dataset.query.annotation_category_ids]
    category_id_to_label = {category.category_id: str(category.label) for category in dataset.categories}
    annotation_labels = [str(category_id_to_label[category_id]) for category_id in annotation_category_ids]
    annotation_type, annotation_value, projected_annotation = _annotation_for_query(
        query_id=str(dataset.query_id),
        annotation_category_ids=annotation_category_ids,
        category_id_to_label=category_id_to_label,
        category_bboxes_px=rendered.rendered_scene.category_bboxes_px,
    )
    return {
        "type": str(annotation_type),
        "value": annotation_value,
        "projected_annotation": dict(projected_annotation),
        "category_ids": list(annotation_category_ids),
        "labels": list(annotation_labels),
        "category_id_to_label": dict(category_id_to_label),
    }




def build_trace_payload(
    *,
    dataset: _Dataset,
    rendered: PictogramRenderResult,
    prompt_artifacts: PromptTraceArtifacts,
    annotation_payload: Mapping[str, Any],
) -> dict[str, Any]:
    qparams = dict(dataset.query.params)
    category_id_to_label = dict(annotation_payload["category_id_to_label"])
    totals_by_category = {category.label: int(category.total) for category in dataset.categories}
    mark_counts_by_category = {category.label: int(category.mark_count) for category in dataset.categories}
    query_params = {
        "query_id": str(dataset.query_id),
        "query_id_probabilities": dict(dataset.query_id_probabilities),
        "scene_variant": str(dataset.scene_variant),
        "scene_variant_probabilities": dict(dataset.scene_variant_probabilities),
        "glyph_name": str(dataset.glyph_name),
        "glyph_probabilities": dict(dataset.glyph_probabilities),
        "unit_scale": int(dataset.unit_scale),
        "category_count": int(len(dataset.categories)),
        "answer_value": int(dataset.query.answer),
        **dict(qparams),
    }
    return {
        "scene_ir": {
            "scene_kind": "pictogram",
            "entities": [dict(entity) for entity in rendered.rendered_scene.entities],
            "relations": {
                "query_id": str(dataset.query_id),
                "scene_variant": str(dataset.scene_variant),
                "unit_scale": int(dataset.unit_scale),
                "answer_value": int(dataset.query.answer),
                "annotation_category_ids": list(annotation_payload["category_ids"]),
            },
        },
        "query_spec": build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(dataset.query_id),
            params=dict(query_params),
        ),
        "render_spec": {
            "scene_variant": str(dataset.scene_variant),
            "canvas_width": int(rendered.image.size[0]),
            "canvas_height": int(rendered.image.size[1]),
            "unit_scale": int(dataset.unit_scale),
            "glyph_name": str(dataset.glyph_name),
            "category_labels": [str(category.label) for category in dataset.categories],
            "font_assets": font_assets_payload(chart_font_family=rendered.chart_font_family),
            "render_meta": dict(rendered.rendered_scene.render_meta),
            "post_image_noise": dict(rendered.post_noise_meta),
        },
        "render_map": {
            "plot_bbox_px": list(rendered.rendered_scene.plot_bbox_px),
            "legend_bbox_px": list(rendered.rendered_scene.legend_bbox_px),
            "category_bboxes_px": dict(rendered.rendered_scene.category_bboxes_px),
            "mark_bboxes_px": dict(rendered.rendered_scene.mark_bboxes_px),
        },
        "execution_trace": {
            "query_id": str(dataset.query_id),
            "question_format": "pictogram_quantity",
            "scene_variant": str(dataset.scene_variant),
            "unit_scale": int(dataset.unit_scale),
            "category_count": int(len(dataset.categories)),
            "categories": [str(category.label) for category in dataset.categories],
            "category_id_to_label": dict(category_id_to_label),
            "mark_counts_by_category": dict(mark_counts_by_category),
            "totals_by_category": dict(totals_by_category),
            "answer_value": int(dataset.query.answer),
            "answer_type": str(dataset.query.answer_type),
            "annotation_category_ids": list(annotation_payload["category_ids"]),
            "annotation_labels": list(annotation_payload["labels"]),
            **dict(qparams),
        },
        "witness_symbolic": {
            "type": "pictogram_quantity_witness",
            "answer_value": int(dataset.query.answer),
            "annotation_category_ids": list(annotation_payload["category_ids"]),
        },
        "projected_annotation": dict(annotation_payload["projected_annotation"]),
        "background": dict(rendered.background_meta),
        "post_image_noise": dict(rendered.post_noise_meta),
    }


