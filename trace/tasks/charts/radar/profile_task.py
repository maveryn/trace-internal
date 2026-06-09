"""Task assembly for radar chart profile tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from ....core.types import TypedValue
from ...base import TaskOutput
from ...shared.config_defaults import required_group_defaults
from ...shared.font_assets import font_asset_version
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import temporary_default_font_family
from ..shared.complexity import build_chart_complexity, clamp_unit_interval, normalize_int_with_bounds
from .profile_common import (
    SCENE_ID,
    TASK_ID,
    Point,
    _COMPLEXITY_WEIGHTS,
    _PROMPT_DEFAULTS,
    _REASONING_LOAD_BY_VARIANT,
    _SCENE_LOAD_BY_VARIANT,
    _Dataset,
    _Rendered,
    _resolve_gen_int,
    _resolve_int,
    _resolve_query_id,
    _sample_chart_font_family,
)
from .profile_rendering import _render_dataset
from .profile_sampling import _build_dataset, _support_sampling_params

def _point_center_from_bbox(bbox: Sequence[float]) -> Point:
    if len(bbox) != 4:
        raise ValueError(f"expected bbox with 4 values, got {bbox}")
    return [
        round((float(bbox[0]) + float(bbox[2])) / 2.0, 2),
        round((float(bbox[1]) + float(bbox[3])) / 2.0, 2),
    ]

def _point_for_id(rendered: _Rendered, point_id: str) -> Point:
    bbox = rendered.point_bboxes.get(str(point_id))
    if bbox is None:
        raise KeyError(f"missing radar point bbox for {point_id}")
    return _point_center_from_bbox(bbox)

def _annotation_for_query(dataset: _Dataset, rendered: _Rendered) -> Tuple[str, List[Any], Dict[str, Any]]:
    query_id = str(dataset.query.query_id)
    if query_id in {"highlighted_metric_threshold_panel_count", "matching_condition_panel_count"}:
        panel_labels = [str(value) for value in dataset.query.trace.get("matching_panel_labels", [])]
        boxes = [list(rendered.panel_bboxes[str(label)]) for label in panel_labels]
        return "bbox_set", list(boxes), {
            "type": "bbox_set",
            "bbox_set": list(boxes),
            "annotation_panel_labels": list(panel_labels),
            "annotation_point_ids": list(dataset.query.annotation_point_ids),
        }
    if query_id == "threshold_metric_count_for_panel":
        points = [_point_for_id(rendered, str(point_id)) for point_id in dataset.query.annotation_point_ids]
        return "point_set", list(points), {
            "type": "point_set",
            "point_set": list(points),
            "pixel_point_set": list(points),
            "annotation_point_ids": list(dataset.query.annotation_point_ids),
            "annotation_metric_labels": list(dataset.query.trace.get("matching_metric_labels", [])),
        }
    if query_id == "profile_advantage_count":
        point_ids = [str(value) for value in dataset.query.annotation_point_ids]
        if len(point_ids) % 2 != 0:
            raise ValueError("profile_advantage_count annotation must contain paired profile points")
        pairs = [
            [_point_for_id(rendered, point_ids[index]), _point_for_id(rendered, point_ids[index + 1])]
            for index in range(0, len(point_ids), 2)
        ]
        return "point_pair_set", list(pairs), {
            "type": "point_pair_set",
            "point_pair_set": list(pairs),
            "pixel_point_pair_set": list(pairs),
            "annotation_point_ids": list(point_ids),
            "advantage_metric_labels": list(dataset.query.trace.get("advantage_metric_labels", [])),
        }
    raise ValueError(f"unsupported radar annotation query_id: {query_id}")

class ChartsRadarMultiplotQueryTask:
    """Answer comparison and filtering queries on radar chart displays."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "radar"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        support_params = _support_sampling_params(
            params,
            query_id_probabilities=query_id_probabilities,
        )
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

        chart_font_family = _sample_chart_font_family(int(instance_seed), params)
        with temporary_default_font_family(str(chart_font_family)):
            rendered = _render_dataset(dataset, params=params, instance_seed=int(instance_seed))
        annotation_type, annotation_value, projected_annotation = _annotation_for_query(dataset, rendered)
        if not annotation_value:
            raise RuntimeError(f"{self.task_id} produced empty annotation")

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_label",
                "answer_hint_count",
                "object_description_small_multiple_radar",
                "object_description_single_radar_multi_profile",
                "annotation_hint_highlighted_metric_threshold_panel_count",
                "annotation_hint_threshold_metric_count_for_panel",
                "annotation_hint_profile_advantage_count",
                "annotation_hint_matching_condition_panel_count",
                "json_example_highlighted_metric_threshold_panel_count",
                "json_example_threshold_metric_count_for_panel",
                "json_example_profile_advantage_count",
                "json_example_matching_condition_panel_count",
                "json_example_answer_only_highlighted_metric_threshold_panel_count",
                "json_example_answer_only_threshold_metric_count_for_panel",
                "json_example_answer_only_profile_advantage_count",
                "json_example_answer_only_matching_condition_panel_count",
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
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(dataset.query.scene_variant)}"]),
                "metric_label": str(dataset.query.metric_label),
                "panel_label": str(dataset.query.panel_label),
                "profile_a_label": str(dataset.query.profile_a_label),
                "profile_b_label": str(dataset.query.profile_b_label),
                "threshold_value": str(dataset.query.threshold_value),
                "minimum_metric_count": str(dataset.query.minimum_metric_count),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(query_id)}"]),
                "answer_hint": str(prompt_defaults[str(answer_hint_key)]),
                "json_example": str(prompt_defaults[f"json_example_{str(query_id)}"]),
                "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{str(query_id)}"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type=str(dataset.query.answer_type), value=dataset.query.answer)
        annotation_gt = TypedValue(type=str(annotation_type), value=list(annotation_value))
        values_by_panel_profile = {
            str(panel.panel_label): {
                str(profile.profile_label): dict(profile.values)
                for profile in panel.profiles
            }
            for panel in dataset.panels
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"chart_radar_{str(dataset.query.scene_variant)}",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(dataset.query.scene_variant),
                    "answer": dataset.query.answer,
                    "annotation_point_ids": list(dataset.query.annotation_point_ids),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query_id),
                    "scene_variant": str(dataset.query.scene_variant),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "metric_count": int(len(dataset.metrics)),
                    "panel_count": int(len(dataset.panels)),
                    "question_format": "radar_profile_query",
                },
            },
            "render_spec": {
                "canvas_width": _resolve_int(params, "canvas_width", 1600),
                "canvas_height": _resolve_int(params, "canvas_height", 1000),
                "coord_space": "pixel",
                "scene_variant": str(dataset.query.scene_variant),
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "font_assets": {
                    "font_asset_version": font_asset_version(),
                    "chart_font_family": str(chart_font_family),
                },
                **dict(rendered.render_meta),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "point_bboxes_px": dict(rendered.point_bboxes),
                "panel_bboxes_px": dict(rendered.panel_bboxes),
                "panel_title_bboxes_px": dict(rendered.panel_title_bboxes),
                "legend_bboxes_px": dict(rendered.legend_bboxes),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(dataset.query.scene_variant),
                "answer": dataset.query.answer,
                "answer_type": str(dataset.query.answer_type),
                "metrics": list(dataset.metrics),
                "metric_count": int(len(dataset.metrics)),
                "panel_labels": [str(panel.panel_label) for panel in dataset.panels if str(panel.panel_label)],
                "panel_count": int(len(dataset.panels)),
                "values_by_panel_profile": values_by_panel_profile,
                "annotation_point_ids": list(dataset.query.annotation_point_ids),
                "query_id_probabilities": dict(query_id_probabilities),
                "question_format": "radar_profile_query",
                **dict(dataset.query.trace),
            },
            "witness_symbolic": {
                "type": "radar_vertices",
                "point_ids": list(dataset.query.annotation_point_ids),
                "answer": dataset.query.answer,
            },
            "projected_annotation": dict(projected_annotation),
        }

        visual_max = max(
            int(_resolve_gen_int(params, "panel_count_max", 8)) * int(_resolve_gen_int(params, "metric_count_max", 7)),
            2 * int(_resolve_gen_int(params, "metric_count_max", 7)),
        )
        visual_count = int(len(dataset.panels)) * int(len(dataset.metrics)) * max(
            1,
            max(len(panel.profiles) for panel in dataset.panels),
        )
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(visual_count), [10, int(visual_max)]),
                "reasoning_load": clamp_unit_interval(float(_REASONING_LOAD_BY_VARIANT[str(query_id)])),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(dataset.query.scene_variant)]),
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
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            scene_id=SCENE_ID,
        )
