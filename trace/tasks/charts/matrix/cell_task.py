"""Base matrix chart task implementation."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...shared.config_defaults import required_group_defaults
from ...shared.font_assets import font_asset_version
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
)
from .cell_common import (
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    TASK_ID,
    _COMPLEXITY_WEIGHTS,
    _GEN_DEFAULTS,
    _PROMPT_DEFAULTS,
    _REASONING_LOAD_BY_VARIANT,
    _SCENE_LOAD_BY_VARIANT,
    _decoupled_sampling_params,
    _resolve_comparison,
    _resolve_extremum_direction,
    _resolve_grid_style,
    _resolve_header_layout,
    _resolve_palette_variant,
    _resolve_query_axis,
    _resolve_query_id,
    _resolve_render_params,
    _resolve_scene_variant,
    _support_sampling_params,
)
from .cell_rendering import _render_matrix
from .cell_sampling import _construct_dataset


def _json_examples(query_id: str, *, prompt_defaults: Mapping[str, Any]) -> Tuple[str, str]:
    return (
        str(prompt_defaults[f"json_example_{str(query_id)}"]),
        str(prompt_defaults[f"json_example_answer_only_{str(query_id)}"]),
    )


def _annotation_bboxes(
    *,
    rendered_scene: _RenderedMatrix,
    annotation_cell_ids: Sequence[str],
    annotation_header_keys: Sequence[str],
) -> Tuple[List[List[float]], List[Dict[str, Any]]]:
    del annotation_header_keys
    bboxes: List[List[float]] = []
    entries: List[Dict[str, Any]] = []
    for cell_id in annotation_cell_ids:
        bbox = list(rendered_scene.cell_bbox_map[str(cell_id)])
        bboxes.append(list(bbox))
        entries.append({"role": "cell", "id": str(cell_id), "bbox": list(bbox)})
    return bboxes, entries


class ChartsMatrixCellQueryTask:
    """Answer questions over printed values in annotated matrix charts."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "matrix"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                return self._generate_once(int(instance_seed) + int(attempt), params=params)
            except ValueError as exc:
                last_error = exc
                continue
        raise ValueError(f"could not construct unique-answer matrix task for {self.task_id}: {last_error}")

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        support_params = _support_sampling_params(params, query_id_probabilities=query_id_probabilities)
        scene_params = _decoupled_sampling_params(support_params, divisor=2, explicit_keys=("scene_variant", "scene_variant_weights"))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            scene_params,
            query_id=str(query_id),
            instance_seed=int(instance_seed),
        )
        palette_params = _decoupled_sampling_params(support_params, divisor=3, explicit_keys=("palette_variant", "palette_variant_weights"))
        palette_variant, palette_variant_probabilities = _resolve_palette_variant(palette_params, instance_seed=int(instance_seed))
        header_params = _decoupled_sampling_params(support_params, divisor=5, explicit_keys=("header_layout", "header_layout_weights"))
        header_layout, header_layout_probabilities = _resolve_header_layout(header_params, instance_seed=int(instance_seed))
        grid_params = _decoupled_sampling_params(support_params, divisor=7, explicit_keys=("grid_style", "grid_style_weights"))
        grid_style, grid_style_probabilities = _resolve_grid_style(grid_params, instance_seed=int(instance_seed))

        query_axis = "row"
        query_axis_probabilities: Dict[str, float] = {}
        if str(query_id) in {"axis_extremum_label", "threshold_cell_count"}:
            axis_params = _decoupled_sampling_params(support_params, divisor=11, explicit_keys=("query_axis", "query_axis_weights"))
            query_axis, query_axis_probabilities = _resolve_query_axis(axis_params, instance_seed=int(instance_seed))
        extremum_direction = "highest"
        extremum_probabilities: Dict[str, float] = {}
        if str(query_id) == "axis_extremum_label":
            extremum_params = _decoupled_sampling_params(
                support_params,
                divisor=13,
                explicit_keys=("extremum_direction", "extremum_direction_weights"),
            )
            extremum_direction, extremum_probabilities = _resolve_extremum_direction(
                extremum_params,
                instance_seed=int(instance_seed),
            )
        comparison = "at_least"
        comparison_probabilities: Dict[str, float] = {}
        if str(query_id) == "threshold_cell_count":
            comparison_params = _decoupled_sampling_params(
                support_params,
                divisor=17,
                explicit_keys=("comparison", "comparison_weights"),
            )
            comparison, comparison_probabilities = _resolve_comparison(comparison_params, instance_seed=int(instance_seed))

        dataset_params = {**dict(support_params), "_enable_unanswerable": bool(getattr(self, "supports_unanswerable", False))}
        dataset = _construct_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            query_axis=str(query_axis),
            extremum_direction=str(extremum_direction),
            comparison=str(comparison),
            params=dataset_params,
            instance_seed=int(instance_seed),
        )
        render_style_params = {**dict(params), "_render_style_seed": int(instance_seed)}
        render_params = _resolve_render_params(render_style_params)
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = _render_matrix(
            background,
            scene_title=str(dataset["scene_title"]),
            scene_variant=str(scene_variant),
            palette_variant=str(palette_variant),
            header_layout=str(header_layout),
            grid_style=str(grid_style),
            row_labels=list(dataset["row_labels"]),
            column_labels=list(dataset["column_labels"]),
            cells=list(dataset["cells"]),
            value_min=int(dataset["value_min"]),
            value_max=int(dataset["value_max"]),
            scene_meta=dict(dataset["scene_meta"]),
            render_params=render_params,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_confusion_matrix_counts",
                "object_description_annotated_heatmap_table",
                "object_description_correlation_matrix_signed",
                "object_description_triangular_pairwise_matrix",
                "object_description_clustered_block_matrix",
                "answer_hint_integer",
                "answer_hint_label",
                "annotation_hint_axis_extremum_label",
                "annotation_hint_off_diagonal_confusion_label",
                "annotation_hint_threshold_cell_count",
                "json_example_axis_extremum_label",
                "json_example_off_diagonal_confusion_label",
                "json_example_threshold_cell_count",
                "json_example_answer_only_axis_extremum_label",
                "json_example_answer_only_off_diagonal_confusion_label",
                "json_example_answer_only_threshold_cell_count",
                "unanswerable_instruction",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _json_examples(str(query_id), prompt_defaults=prompt_defaults)
        qparams = dict(dataset["question_params"])
        answer_hint = (
            str(prompt_defaults["answer_hint_label"])
            if str(dataset["answer_type"]) == "string"
            else str(prompt_defaults["answer_hint_integer"])
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(scene_variant)}"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(query_id)}"]),
                "answer_hint": answer_hint,
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "row_label": str(qparams.get("row_label", "")),
                "column_label": str(qparams.get("column_label", "")),
                "query_axis": str(qparams.get("query_axis", "")),
                "axis_label": str(qparams.get("axis_label", "")),
                "answer_axis": str(qparams.get("answer_axis", "")),
                "extremum_phrase": str(qparams.get("extremum_phrase", "")),
                "selection_phrase": str(qparams.get("selection_phrase", "")),
                "comparison_phrase": str(qparams.get("comparison_phrase", "")),
                "threshold_value": str(qparams.get("threshold_value", "")),
                "unanswerable_instruction": (
                    str(prompt_defaults["unanswerable_instruction"])
                    if bool(getattr(self, "supports_unanswerable", False))
                    else ""
                ),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        annotation_cell_ids = [str(cell_id) for cell_id in dataset["annotation_cell_ids"]]
        support_header_keys = [str(key) for key in dataset["annotation_header_keys"]]
        annotation_bboxes, annotation_entries = _annotation_bboxes(
            rendered_scene=rendered_scene,
            annotation_cell_ids=annotation_cell_ids,
            annotation_header_keys=support_header_keys,
        )
        projected_annotation = {
            "bbox_set": list(annotation_bboxes),
            "entries": [dict(entry) for entry in annotation_entries],
            "cell_ids": list(annotation_cell_ids),
        }
        answer_gt = TypedValue(type=str(dataset["answer_type"]), value=dataset["answer_value"])
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))

        cell_count = int(dataset["row_count"]) * int(dataset["column_count"])
        active_cell_count = len([cell for cell in dataset["cells"] if bool(cell["active"])])
        annotation_scan = normalize_int_with_bounds(len(annotation_bboxes), [3, 28])
        grid_scan = normalize_int_with_bounds(int(cell_count), [36, 144])
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BY_VARIANT[str(query_id)])
            + (0.10 * float(annotation_scan))
            + (0.08 * normalize_int_with_bounds(active_cell_count, [36, 144]))
        )
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": float(grid_scan),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )
        query_params = {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "palette_variant": str(palette_variant),
            "header_layout": str(header_layout),
            "grid_style": str(grid_style),
            "query_id_probabilities": dict(query_id_probabilities),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "palette_variant_probabilities": dict(palette_variant_probabilities),
            "header_layout_probabilities": dict(header_layout_probabilities),
            "grid_style_probabilities": dict(grid_style_probabilities),
            "row_count": int(dataset["row_count"]),
            "column_count": int(dataset["column_count"]),
            "query_axis": str(query_axis),
            **dict(qparams),
        }
        if query_axis_probabilities:
            query_params["query_axis_probabilities"] = dict(query_axis_probabilities)
        if extremum_probabilities:
            query_params["extremum_direction_probabilities"] = dict(extremum_probabilities)
        if comparison_probabilities:
            query_params["comparison_probabilities"] = dict(comparison_probabilities)

        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_annotated_matrix",
                "entities": [dict(item) for item in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "answer_value": dataset["answer_value"],
                    "answer_row_index": int(dataset["answer_row_index"]),
                    "answer_column_index": int(dataset["answer_column_index"]),
                    "annotation_cell_ids": list(annotation_cell_ids),
                    "support_header_keys": list(support_header_keys),
                    "answerability": "unanswerable" if bool(dataset["is_unanswerable"]) else "answerable",
                    **({"absence_proof": dict(dataset["absence_proof"])} if bool(dataset["is_unanswerable"]) else {}),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "scene_variant": str(scene_variant),
                "palette_variant": str(palette_variant),
                "header_layout": str(header_layout),
                "grid_style": str(grid_style),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "row_count": int(dataset["row_count"]),
                "column_count": int(dataset["column_count"]),
                "value_min": int(dataset["value_min"]),
                "value_max": int(dataset["value_max"]),
                "layout_jitter": dict(render_params.layout_jitter_meta),
                "font_assets": {
                    "asset_version": font_asset_version(),
                    "chart_font_family": str(render_params.font_family),
                },
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "panel_bbox_px": list(rendered_scene.panel_bbox_px),
                "title_bbox_px": list(rendered_scene.title_bbox_px),
                "matrix_bbox_px": list(rendered_scene.matrix_bbox_px),
                "legend_bbox_px": list(rendered_scene.legend_bbox_px),
                "cell_bboxes_px": dict(rendered_scene.cell_bbox_map),
                "row_label_bboxes_px": dict(rendered_scene.row_label_bbox_map),
                "column_label_bboxes_px": dict(rendered_scene.column_label_bbox_map),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "question_format": "matrix_cell_query",
                "scene_title": str(dataset["scene_title"]),
                "row_count": int(dataset["row_count"]),
                "column_count": int(dataset["column_count"]),
                "row_labels": list(dataset["row_labels"]),
                "column_labels": list(dataset["column_labels"]),
                "values": [
                    [None if value is None else int(value) for value in row]
                    for row in dataset["values"]
                ],
                "cells": [dict(cell) for cell in dataset["cells"]],
                "cells_by_id": {str(key): dict(value) for key, value in dict(dataset["cells_by_id"]).items()},
                "answer_value": dataset["answer_value"],
                "answer_type": str(dataset["answer_type"]),
                "answer_row_index": int(dataset["answer_row_index"]),
                "answer_column_index": int(dataset["answer_column_index"]),
                "annotation_cell_ids": list(annotation_cell_ids),
                "support_header_keys": list(support_header_keys),
                "query_axis": str(query_axis),
                "extremum_direction": str(extremum_direction),
                "comparison": str(comparison),
                "extremum_rank": int(dataset.get("extremum_rank", 0)),
                "scene_meta": dict(dataset["scene_meta"]),
                "annotation_semantics": str(query_id),
                "answerability": "unanswerable" if bool(dataset["is_unanswerable"]) else "answerable",
                **({"absence_proof": dict(dataset["absence_proof"])} if bool(dataset["is_unanswerable"]) else {}),
            },
            "witness_symbolic": {
                "type": "matrix_cell_witness",
                "candidate_cell_ids": list(annotation_cell_ids),
                "support_header_keys": list(support_header_keys),
                "answer_value": dataset["answer_value"],
                "answer_row_index": int(dataset["answer_row_index"]),
                "answer_column_index": int(dataset["answer_column_index"]),
                "answerability": "unanswerable" if bool(dataset["is_unanswerable"]) else "answerable",
                **({"absence_proof": dict(dataset["absence_proof"])} if bool(dataset["is_unanswerable"]) else {}),
            },
            "projected_annotation": dict(projected_annotation),
            "background": background_meta,
            "post_image_noise": dict(post_noise_meta),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(query_id),
        )
