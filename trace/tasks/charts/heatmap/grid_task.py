"""Generation pipeline for heatmap chart tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping

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
from ..shared.sampling_defaults import support_sampling_params_for_uniform_query_cycle
from .grid_common import (
    TASK_ID,
    _COLORBAR_THRESHOLD_QUERY_IDS,
    _COMPLEXITY_WEIGHTS,
    _GEN_DEFAULTS,
    _PROMPT_DEFAULTS,
    _REASONING_LOAD_BY_VARIANT,
    _SCENE_LOAD_BY_VARIANT,
    _SUPPORTED_QUERY_IDS,
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    _condition_support,
    _is_continuous_colorbar_query,
)
from .grid_dataset import _construct_dataset
from .grid_rendering import _render_heatmap, _resolve_render_params
from .grid_sampling import (
    _decoupled_sampling_params,
    _resolve_condition_kind,
    _resolve_extremum_direction,
    _resolve_query_axis,
    _resolve_query_id,
    _resolve_scene_variant,
)


def _json_examples(query_id: str, *, prompt_defaults: Mapping[str, Any]) -> Tuple[str, str]:
    return (
        str(prompt_defaults[f"json_example_{str(query_id)}"]),
        str(prompt_defaults[f"json_example_answer_only_{str(query_id)}"]),
    )


class _ChartsHeatmapGridQueryTaskBase:
    """Answer label questions over color/intensity heatmap grids."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "heatmap"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        support_params = support_sampling_params_for_uniform_query_cycle(
            params,
            gen_defaults=_GEN_DEFAULTS,
            query_id_probabilities=query_id_probabilities,
            supported_query_ids=_SUPPORTED_QUERY_IDS,
        )
        if _is_continuous_colorbar_query(str(query_id)):
            requested_scene = params.get("scene_variant")
            if requested_scene is not None and str(requested_scene) != "continuous_colorbar_heatmap":
                raise ValueError("continuous colorbar heatmap tasks require scene_variant='continuous_colorbar_heatmap'")
            scene_variant = "continuous_colorbar_heatmap"
            scene_variant_probabilities = {"continuous_colorbar_heatmap": 1.0}
        else:
            requested_scene = params.get("scene_variant")
            if requested_scene is not None and str(requested_scene) == "continuous_colorbar_heatmap":
                raise ValueError("scene_variant='continuous_colorbar_heatmap' is only valid for colorbar count tasks")
            scene_variant, scene_variant_probabilities = _resolve_scene_variant(support_params, instance_seed=int(instance_seed))
        query_axis = "row"
        query_axis_probabilities: Dict[str, float] = {}
        if str(query_id) in {"axis_condition_extremum_label", "axis_cell_extremum_label"}:
            query_axis, query_axis_probabilities = _resolve_query_axis(
                support_params,
                instance_seed=int(instance_seed),
            )
        condition_kind = ""
        condition_probabilities: Dict[str, float] = {}
        if str(query_id) in {"axis_condition_extremum_label", "condition_run_extremum_label"}:
            condition_params = _decoupled_sampling_params(
                support_params,
                divisor=2,
                explicit_keys=("condition_kind", "condition_kind_weights"),
            )
            condition_kind, condition_probabilities = _resolve_condition_kind(
                condition_params,
                scene_variant=str(scene_variant),
                instance_seed=int(instance_seed),
            )
        else:
            condition_kind = _condition_support(str(scene_variant))[0]
        extremum_direction = ""
        extremum_probabilities: Dict[str, float] = {}
        if str(query_id) == "axis_cell_extremum_label":
            extremum_params = _decoupled_sampling_params(
                support_params,
                divisor=2,
                explicit_keys=("extremum_direction", "extremum_direction_weights"),
            )
            extremum_direction, extremum_probabilities = _resolve_extremum_direction(
                extremum_params,
                instance_seed=int(instance_seed),
            )
        else:
            extremum_direction = "hottest"

        dataset_params = {**dict(support_params), "_enable_unanswerable": bool(getattr(self, "supports_unanswerable", False))}
        dataset = _construct_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            query_axis=str(query_axis),
            condition_kind=str(condition_kind),
            extremum_direction=str(extremum_direction),
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
        rendered_scene = _render_heatmap(
            background,
            scene_title=str(dataset["scene_title"]),
            scene_variant=str(scene_variant),
            row_labels=list(dataset["row_labels"]),
            column_labels=list(dataset["column_labels"]),
            cells=list(dataset["cells"]),
            render_params=render_params,
            colorbar_ticks=tuple(int(value) for value in dataset.get("colorbar_ticks", ())),
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
                "object_description_intensity_heatmap",
                "object_description_signed_change_heatmap",
                "object_description_calendar_heatmap",
                "object_description_continuous_colorbar_heatmap",
                "answer_hint_label",
                "answer_hint_count",
                "annotation_hint_axis_condition_extremum_label",
                "annotation_hint_axis_cell_extremum_label",
                "annotation_hint_condition_run_extremum_label",
                "annotation_hint_colorbar_threshold_cell_count",
                "annotation_hint_colorbar_interval_cell_count",
                "json_example_axis_condition_extremum_label",
                "json_example_axis_cell_extremum_label",
                "json_example_condition_run_extremum_label",
                "json_example_colorbar_threshold_cell_count",
                "json_example_colorbar_interval_cell_count",
                "json_example_answer_only_axis_condition_extremum_label",
                "json_example_answer_only_axis_cell_extremum_label",
                "json_example_answer_only_condition_run_extremum_label",
                "json_example_answer_only_colorbar_threshold_cell_count",
                "json_example_answer_only_colorbar_interval_cell_count",
                "unanswerable_instruction",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        example_key = "colorbar_threshold_cell_count" if str(query_id) in set(_COLORBAR_THRESHOLD_QUERY_IDS) else str(query_id)
        example_key = "colorbar_interval_cell_count" if str(query_id) == "colorbar_interval_cell_count" else str(example_key)
        json_example, json_example_answer_only = _json_examples(str(example_key), prompt_defaults=prompt_defaults)
        qparams = dict(dataset["question_params"])
        answer_hint = (
            str(prompt_defaults["answer_hint_count"])
            if _is_continuous_colorbar_query(str(query_id))
            else str(prompt_defaults["answer_hint_label"])
        )
        annotation_hint_key = (
            "annotation_hint_colorbar_threshold_cell_count"
            if str(query_id) in set(_COLORBAR_THRESHOLD_QUERY_IDS)
            else (
                "annotation_hint_colorbar_interval_cell_count"
                if str(query_id) == "colorbar_interval_cell_count"
                else f"annotation_hint_{str(query_id)}"
            )
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
                "annotation_hint": str(prompt_defaults[str(annotation_hint_key)]),
                "answer_hint": str(answer_hint),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "condition_phrase": str(qparams.get("condition_phrase", "")),
                "threshold_value": str(qparams.get("threshold_value", "")),
                "lower_bound": str(qparams.get("lower_bound", "")),
                "upper_bound": str(qparams.get("upper_bound", "")),
                "query_axis": str(qparams.get("query_axis", "")),
                "answer_axis": str(qparams.get("answer_axis", "")),
                "axis_label": str(qparams.get("axis_label", "")),
                "column_label": str(qparams.get("column_label", "")),
                "row_label": str(qparams.get("row_label", "")),
                "extremum_phrase": str(qparams.get("extremum_phrase", "")),
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
        annotation_bboxes = [list(rendered_scene.cell_bbox_map[str(cell_id)]) for cell_id in annotation_cell_ids]
        projected_annotation = {
            "bbox_set": list(annotation_bboxes),
            "bbox_map": {str(cell_id): list(rendered_scene.cell_bbox_map[str(cell_id)]) for cell_id in annotation_cell_ids},
            "cell_ids": list(annotation_cell_ids),
        }
        answer_gt = TypedValue(type=str(dataset["answer_type"]), value=dataset["answer_value"])
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))

        annotation_scan = normalize_int_with_bounds(len(annotation_cell_ids), [1, 16])
        grid_scan = normalize_int_with_bounds(int(dataset["row_count"]) * int(dataset["column_count"]), [35, 120])
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BY_VARIANT[str(query_id)])
            + (0.14 * float(annotation_scan))
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
            "query_id_probabilities": dict(query_id_probabilities),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "row_count": int(dataset["row_count"]),
            "column_count": int(dataset["column_count"]),
            "row_count_probabilities": dict(dataset["row_count_probabilities"]),
            "column_count_probabilities": dict(dataset["column_count_probabilities"]),
            "heat_bin_count": int(dataset["heat_bin_count"]),
            "query_axis": str(dataset["query_axis"]),
            **dict(qparams),
        }
        if condition_probabilities:
            query_params["condition_kind_probabilities"] = dict(condition_probabilities)
        if extremum_probabilities:
            query_params["extremum_direction_probabilities"] = dict(extremum_probabilities)
        if query_axis_probabilities:
            query_params["query_axis_probabilities"] = dict(query_axis_probabilities)

        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_heatmap",
                "entities": [dict(item) for item in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "query_axis": str(query_axis),
                    "answer_value": dataset["answer_value"],
                    "answer_row_index": int(dataset["answer_row_index"]),
                    "answer_column_index": int(dataset["answer_column_index"]),
                    "annotation_cell_ids": list(annotation_cell_ids),
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
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "row_count": int(dataset["row_count"]),
                "column_count": int(dataset["column_count"]),
                "heat_bin_count": int(dataset["heat_bin_count"]),
                "colorbar_value_min": dataset.get("colorbar_value_min"),
                "colorbar_value_max": dataset.get("colorbar_value_max"),
                "colorbar_ticks": list(dataset.get("colorbar_ticks", [])),
                "cell_gap_px": int(render_params.cell_gap_px),
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
                "grid_bbox_px": list(rendered_scene.grid_bbox_px),
                "legend_bbox_px": list(rendered_scene.legend_bbox_px),
                "cell_bboxes_px": dict(rendered_scene.cell_bbox_map),
                "row_label_bboxes_px": dict(rendered_scene.row_label_bbox_map),
                "column_label_bboxes_px": dict(rendered_scene.column_label_bbox_map),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "question_format": "heatmap_query",
                "scene_title": str(dataset["scene_title"]),
                "row_count": int(dataset["row_count"]),
                "column_count": int(dataset["column_count"]),
                "row_labels": list(dataset["row_labels"]),
                "column_labels": list(dataset["column_labels"]),
                "heat_bin_count": int(dataset["heat_bin_count"]),
                "colorbar_value_min": dataset.get("colorbar_value_min"),
                "colorbar_value_max": dataset.get("colorbar_value_max"),
                "colorbar_ticks": list(dataset.get("colorbar_ticks", [])),
                "values": [[int(value) for value in row] for row in dataset["values"]],
                "cells": [dict(cell) for cell in dataset["cells"]],
                "cells_by_id": {str(key): dict(value) for key, value in dict(dataset["cells_by_id"]).items()},
                "answer_value": dataset["answer_value"],
                "answer_type": str(dataset["answer_type"]),
                "answer_row_index": int(dataset["answer_row_index"]),
                "answer_column_index": int(dataset["answer_column_index"]),
                "annotation_cell_ids": list(annotation_cell_ids),
                "query_axis": str(query_axis),
                "condition_kind": str(dataset["condition_kind"]),
                "extremum_direction": str(extremum_direction),
                **dict(qparams),
                "annotation_semantics": str(query_id),
                "answerability": "unanswerable" if bool(dataset["is_unanswerable"]) else "answerable",
                **({"absence_proof": dict(dataset["absence_proof"])} if bool(dataset["is_unanswerable"]) else {}),
            },
            "witness_symbolic": {
                "type": "heatmap_witness",
                "candidate_cell_ids": list(annotation_cell_ids),
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
