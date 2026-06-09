"""Task-output assembly for curve-panel chart tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from ....core.types import TypedValue
from ...base import TaskOutput
from ...shared.config_defaults import required_group_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import temporary_default_font_family
from ..shared.complexity import build_chart_complexity, clamp_unit_interval, normalize_int_with_bounds
from ..shared.visual_defaults import chart_font_asset_metadata, sample_chart_font_family
from .multipanel_common import (
    SCENE_ID,
    TASK_ID,
    _COMPLEXITY_WEIGHTS,
    _GEN_DEFAULTS,
    _PROMPT_DEFAULTS,
    _REASONING_LOAD_BY_VARIANT,
    _SCENE_LOAD_BY_VARIANT,
    _Dataset,
    _Rendered,
    _gen_int,
    _public_task_param_overrides,
    _resolve_int,
    _resolve_query_id,
    _support_sampling_params,
)
from .multipanel_datasets import _build_dataset
from .multipanel_rendering import _render_dataset


def _bbox_center(bbox: Sequence[float]) -> List[float]:
    if len(bbox) < 4:
        raise ValueError("bbox must have at least four coordinates")
    x0, y0, x1, y1 = [float(value) for value in bbox[:4]]
    return [round((x0 + x1) * 0.5, 3), round((y0 + y1) * 0.5, 3)]


def _annotation_points(dataset: _Dataset, rendered: _Rendered) -> List[List[float]]:
    points: List[List[float]] = []
    for point_id in dataset.query.annotation_point_ids:
        point_box = rendered.point_bboxes.get(str(point_id))
        if point_box is not None:
            points.append(_bbox_center(point_box))
    for intersection_id in dataset.query.annotation_intersection_ids:
        intersection_box = rendered.intersection_bboxes.get(str(intersection_id))
        if intersection_box is not None:
            points.append(_bbox_center(intersection_box))
    for crossing_id in dataset.query.annotation_threshold_crossing_ids:
        crossing_box = rendered.threshold_crossing_bboxes.get(str(crossing_id))
        if crossing_box is not None:
            points.append(_bbox_center(crossing_box))
    return points


def _cross_panel_delta_annotation_map(dataset: _Dataset, rendered: _Rendered) -> Dict[str, List[float]]:
    annotation: Dict[str, List[float]] = {}
    for point_id in dataset.query.annotation_point_ids:
        point_box = rendered.point_bboxes.get(str(point_id))
        if point_box is None:
            continue
        parts = str(point_id).split("|")
        if len(parts) != 3:
            continue
        panel_label, _method_label, x_value = parts
        role = "start" if int(x_value) == int(dataset.query.start_x_value) else "end"
        annotation[f"{str(panel_label)}_{role}"] = _bbox_center(point_box)
    expected_key_count = int(len(dataset.panels)) * 2
    if len(annotation) != int(expected_key_count):
        raise RuntimeError("cross-panel delta annotation map is incomplete")
    return annotation


def _values_by_panel_method(dataset: _Dataset) -> Dict[str, Dict[str, List[int]]]:
    return {
        str(panel.panel_label): {
            str(curve.method_label): [int(value) for value in curve.values]
            for curve in panel.curves
        }
        for panel in dataset.panels
    }


class ChartsScientificMultipanelSubplotQueryTask:
    """Answer panel-aware questions on scientific multi-subplot line figures."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "scientific"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        public_overrides = (
            _public_task_param_overrides(str(self.task_id))
            if str(self.task_id) != str(TASK_ID)
            else {}
        )
        if public_overrides:
            merged_params = dict(public_overrides)
            merged_params.update(dict(params))
            params = merged_params
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        support_params = _support_sampling_params(params, query_id_probabilities=query_id_probabilities)
        dataset: _Dataset | None = None
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                attempt_params = {**dict(support_params), "_attempt_index": int(attempt_index)}
                dataset = _build_dataset(str(query_id), attempt_params, instance_seed=int(instance_seed) + int(attempt_index))
                break
            except Exception as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError(f"failed to generate {self.task_id} instance") from last_error

        chart_font_family = sample_chart_font_family(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.chart_font",
            params=params,
        )
        with temporary_default_font_family(str(chart_font_family)):
            rendered = _render_dataset(dataset, params=params, instance_seed=int(instance_seed))
        if str(dataset.query.query_id) == "cross_panel_delta_extremum_label":
            annotation_value: List[List[float]] | Dict[str, List[float]] = _cross_panel_delta_annotation_map(dataset, rendered)
            annotation_type = "keyed_point_map"
        else:
            annotation_value = _annotation_points(dataset, rendered)
            annotation_type = "point_set"
        if not annotation_value and str(dataset.query.query_id) != "curve_intersection_count":
            raise RuntimeError(f"{self.task_id} produced empty annotation")

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_multipanel_line_grid",
                "answer_hint_label",
                "answer_hint_count",
                "annotation_hint_curve_at_x_extremum_label",
                "annotation_hint_threshold_series_count",
                "annotation_hint_panel_point_threshold_count",
                "annotation_hint_panel_curve_threshold_crossing_count",
                "annotation_hint_cross_panel_delta_extremum_label",
                "annotation_hint_cross_panel_threshold_earliest_label",
                "annotation_hint_curve_intersection_count",
                "annotation_hint_earliest_maximum_panel_label",
                "json_example_curve_at_x_extremum_label",
                "json_example_threshold_series_count",
                "json_example_panel_point_threshold_count",
                "json_example_panel_curve_threshold_crossing_count",
                "json_example_cross_panel_delta_extremum_label",
                "json_example_cross_panel_threshold_earliest_label",
                "json_example_curve_intersection_count",
                "json_example_earliest_maximum_panel_label",
                "json_example_answer_only_curve_at_x_extremum_label",
                "json_example_answer_only_threshold_series_count",
                "json_example_answer_only_panel_point_threshold_count",
                "json_example_answer_only_panel_curve_threshold_crossing_count",
                "json_example_answer_only_cross_panel_delta_extremum_label",
                "json_example_answer_only_cross_panel_threshold_earliest_label",
                "json_example_answer_only_curve_intersection_count",
                "json_example_answer_only_earliest_maximum_panel_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        answer_hint_key = "answer_hint_count" if str(dataset.query.answer_type) == "integer" else "answer_hint_label"
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(dataset.query.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_multipanel_line_grid"]),
                "panel_label": str(dataset.query.panel_label),
                "method_label": str(dataset.query.method_label),
                "method_a_label": str(dataset.query.method_a_label),
                "method_b_label": str(dataset.query.method_b_label),
                "x_value": str(dataset.query.x_value),
                "start_x_value": str(dataset.query.start_x_value),
                "end_x_value": str(dataset.query.end_x_value),
                "threshold_value": str(dataset.query.threshold_value),
                "threshold_direction_phrase": str(dataset.query.trace.get("threshold_direction_phrase", "")),
                "threshold_crossing_phrase": str(dataset.query.trace.get("threshold_crossing_phrase", "")),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(dataset.query.query_id)}"]),
                "answer_hint": str(prompt_defaults[str(answer_hint_key)]),
                "json_example": str(prompt_defaults[f"json_example_{str(dataset.query.query_id)}"]),
                "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{str(dataset.query.query_id)}"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type=str(dataset.query.answer_type), value=dataset.query.answer)
        annotation_gt = TypedValue(type=str(annotation_type), value=annotation_value)
        values_by_panel_method = _values_by_panel_method(dataset)
        method_labels = [str(curve.method_label) for curve in dataset.panels[0].curves]
        if str(annotation_type) == "keyed_point_map":
            keyed_point_map = {str(key): list(value) for key, value in dict(annotation_value).items()}
            projected_annotation = {
                "type": "keyed_point_map",
                "keyed_point_map": dict(keyed_point_map),
                "pixel_keyed_point_map": dict(keyed_point_map),
                "panel_labels": list(dataset.query.annotation_panel_labels),
                "point_ids": list(dataset.query.annotation_point_ids),
                "intersection_ids": list(dataset.query.annotation_intersection_ids),
                "threshold_crossing_ids": list(dataset.query.annotation_threshold_crossing_ids),
            }
        else:
            point_set = [list(point) for point in list(annotation_value)]
            projected_annotation = {
                "type": "point_set",
                "point_set": list(point_set),
                "pixel_point_set": list(point_set),
                "panel_labels": list(dataset.query.annotation_panel_labels),
                "point_ids": list(dataset.query.annotation_point_ids),
                "intersection_ids": list(dataset.query.annotation_intersection_ids),
                "threshold_crossing_ids": list(dataset.query.annotation_threshold_crossing_ids),
            }
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"chart_scientific_{str(dataset.scene_variant)}",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(dataset.query.query_id),
                    "scene_variant": str(dataset.scene_variant),
                    "answer": dataset.query.answer,
                    "annotation_panel_labels": list(dataset.query.annotation_panel_labels),
                    "annotation_point_ids": list(dataset.query.annotation_point_ids),
                    "annotation_intersection_ids": list(dataset.query.annotation_intersection_ids),
                    "annotation_threshold_crossing_ids": list(dataset.query.annotation_threshold_crossing_ids),
                },
            },
            "query_spec": {
                "query_id": str(dataset.query.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(dataset.query.query_id),
                    "scene_variant": str(dataset.scene_variant),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "panel_count": int(len(dataset.panels)),
                    "method_count": int(len(method_labels)),
                    "x_tick_count": int(len(dataset.x_values)),
                    "threshold_direction": str(dataset.query.threshold_direction),
                    "question_format": "curve_panels_subplot_query",
                },
            },
            "render_spec": {
                "canvas_width": _resolve_int(params, "canvas_width", 1600),
                "canvas_height": _resolve_int(params, "canvas_height", 1000),
                "coord_space": "pixel",
                "scene_variant": str(dataset.scene_variant),
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "font_assets": chart_font_asset_metadata(str(chart_font_family)),
                **dict(rendered.render_meta),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "panel_bboxes_px": dict(rendered.panel_bboxes),
                "panel_plot_bboxes_px": dict(rendered.panel_plot_bboxes),
                "point_bboxes_px": dict(rendered.point_bboxes),
                "intersection_bboxes_px": dict(rendered.intersection_bboxes),
                "threshold_crossing_bboxes_px": dict(rendered.threshold_crossing_bboxes),
                "legend_bboxes_px": dict(rendered.legend_bboxes),
            },
            "execution_trace": {
                "query_id": str(dataset.query.query_id),
                "scene_variant": str(dataset.scene_variant),
                "answer": dataset.query.answer,
                "answer_type": str(dataset.query.answer_type),
                "panel_labels": [str(panel.panel_label) for panel in dataset.panels],
                "method_labels": list(method_labels),
                "x_values": list(dataset.x_values),
                "y_range": [int(dataset.y_min), int(dataset.y_max)],
                "panel_count": int(len(dataset.panels)),
                "method_count": int(len(method_labels)),
                "values_by_panel_method": values_by_panel_method,
                "annotation_panel_labels": list(dataset.query.annotation_panel_labels),
                "annotation_point_ids": list(dataset.query.annotation_point_ids),
                "annotation_intersection_ids": list(dataset.query.annotation_intersection_ids),
                "annotation_threshold_crossing_ids": list(dataset.query.annotation_threshold_crossing_ids),
                "query_id_probabilities": dict(query_id_probabilities),
                "question_format": "curve_panels_subplot_query",
                **dict(dataset.query.trace),
            },
            "witness_symbolic": {
                "type": "curve_panels_subplot",
                "panel_labels": list(dataset.query.annotation_panel_labels),
                "point_ids": list(dataset.query.annotation_point_ids),
                "intersection_ids": list(dataset.query.annotation_intersection_ids),
                "threshold_crossing_ids": list(dataset.query.annotation_threshold_crossing_ids),
                "answer": dataset.query.answer,
            },
            "projected_annotation": dict(projected_annotation),
        }

        visual_count = int(len(dataset.panels)) * int(len(method_labels)) * int(len(dataset.x_values))
        visual_max = int(_gen_int(params, "panel_count_max", 8)) * int(_gen_int(params, "method_count_max", 6)) * int(_gen_int(params, "x_tick_count_max", 12))
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(visual_count), [6 * 5 * 7, max(6 * 5 * 7, int(visual_max))]),
                "reasoning_load": clamp_unit_interval(float(_REASONING_LOAD_BY_VARIANT[str(dataset.query.query_id)])),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(dataset.scene_variant)]),
            },
        )

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(dataset.query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
