"""Base scatter cluster chart task implementation."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from ....core.seed import spawn_rng
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
from ...shared.text_rendering import temporary_default_font_family
from ..shared.complexity import build_chart_complexity, clamp_unit_interval, normalize_int_with_bounds
from .cluster_common import (
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    TASK_ID,
    _COMPLEXITY_WEIGHTS,
    _PROMPT_DEFAULTS,
    _REASONING_LOAD_BY_VARIANT,
    _SCENE_LOAD_BY_VARIANT,
    _SUPPORTED_AREA_RANK_QUERY_IDS,
    _SUPPORTED_SPREAD_AXES,
    _gen_int,
    _is_area_rank_query,
    _resolve_render_params,
    _sample_chart_font_family,
)
from .cluster_dataset import (
    _dataset_for_area_rank,
    _dataset_for_centroid_option,
    _dataset_for_separation,
    _dataset_for_spread,
    _dataset_for_trend,
)
from .cluster_rendering import _render_scatter
from .cluster_sampling import (
    _resolve_query_id,
    _resolve_separation_extremum,
    _resolve_spread_axis,
    _resolve_spread_extremum,
    _resolve_trend_direction,
    _sample_cluster_labels,
    _support_sampling_params,
    _target_answer_label,
    _target_option_count,
    _target_option_label,
    _option_labels_for_count,
)

def _build_prompt_slots(dataset: _Dataset, prompt_defaults: Mapping[str, Any]) -> Dict[str, str]:
    trace = dict(dataset.query.trace)
    is_centroid_option = str(dataset.query.query_id) == "centroid_option_selection_label"
    is_area_rank = _is_area_rank_query(str(dataset.query.query_id))
    return {
        "object_description": str(
            prompt_defaults["object_description_area_envelope_scatter"]
            if is_area_rank
            else prompt_defaults["object_description_single_scatter"]
        ),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "annotation_hint": str(
            prompt_defaults["annotation_hint_centroid_option_selection_label"]
            if is_centroid_option
            else prompt_defaults["annotation_hint_cluster_area_rank_label"]
            if is_area_rank
            else prompt_defaults["annotation_hint"]
        ),
        "answer_hint": str(prompt_defaults["answer_hint_option_letter"] if is_centroid_option else prompt_defaults["answer_hint"]),
        "json_example": str(
            prompt_defaults["json_example_centroid_option_selection_label"]
            if is_centroid_option
            else prompt_defaults["json_example_cluster_area_rank_label"]
            if is_area_rank
            else prompt_defaults["json_example"]
        ),
        "json_example_answer_only": str(
            prompt_defaults["json_example_answer_only_option_letter"]
            if is_centroid_option
            else prompt_defaults["json_example_answer_only"]
        ),
        "trend_direction_phrase": str(trace.get("trend_direction", "")),
        "reference_cluster_label": str(trace.get("reference_cluster_label", "")),
        "separation_extremum_phrase": "closest to" if str(trace.get("separation_extremum")) == "closest" else "farthest from",
        "spread_axis_phrase": str(trace.get("spread_axis", "")),
        "spread_extremum_phrase": str(trace.get("spread_extremum", "")),
        "area_rank_phrase": str(trace.get("area_rank_phrase", "")),
        "target_cluster_label": str(trace.get("target_cluster_label", "")),
    }


class ChartsScatterClusterQueryTask:
    """Answer cluster and trend questions over a scatter plot."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "scatter"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        support_params = _support_sampling_params(params, query_id_probabilities=query_id_probabilities)
        cluster_min = _gen_int(params, "cluster_count_min", 5)
        cluster_max = _gen_int(params, "cluster_count_max", 8)
        cluster_count_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.cluster_count")
        cluster_count = int(cluster_count_rng.randint(int(cluster_min), int(cluster_max)))
        cluster_count = max(4, min(8, int(cluster_count)))
        labels = _sample_cluster_labels(cluster_count=int(cluster_count), instance_seed=int(instance_seed))
        points_min = _gen_int(params, "points_per_cluster_min", 8)
        points_max = _gen_int(params, "points_per_cluster_max", 12)
        point_count_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.point_count")
        points_per_cluster = int(point_count_rng.randint(int(points_min), int(points_max)))
        answer_label = _target_answer_label(support_params, instance_seed=int(instance_seed), labels=labels)

        if str(query_id) == "cluster_trend_direction_label":
            trend_direction, trend_direction_probabilities = _resolve_trend_direction(
                support_params,
                instance_seed=int(instance_seed),
            )
            dataset = _dataset_for_trend(
                params=params,
                instance_seed=int(instance_seed),
                labels=labels,
                answer_label=str(answer_label),
                points_per_cluster=int(points_per_cluster),
                trend_direction=str(trend_direction),
                trend_direction_probabilities=trend_direction_probabilities,
            )
        elif str(query_id) == "cluster_separation_extremum_label":
            separation_extremum, separation_extremum_probabilities = _resolve_separation_extremum(
                support_params,
                instance_seed=int(instance_seed),
            )
            dataset = _dataset_for_separation(
                params=params,
                instance_seed=int(instance_seed),
                labels=labels,
                answer_label=str(answer_label),
                points_per_cluster=int(points_per_cluster),
                separation_extremum=str(separation_extremum),
                separation_extremum_probabilities=separation_extremum_probabilities,
            )
        elif str(query_id) == "cluster_spread_extremum_label":
            spread_axis, spread_axis_probabilities = _resolve_spread_axis(support_params, instance_seed=int(instance_seed))
            spread_params = dict(support_params)
            sampling_index = spread_params.get("_sample_cursor")
            if sampling_index is not None and spread_params.get("spread_axis") is None:
                spread_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(_SUPPORTED_SPREAD_AXES))
            spread_extremum, spread_extremum_probabilities = _resolve_spread_extremum(
                spread_params,
                instance_seed=int(instance_seed),
            )
            dataset = _dataset_for_spread(
                params=params,
                instance_seed=int(instance_seed),
                labels=labels,
                answer_label=str(answer_label),
                points_per_cluster=int(points_per_cluster),
                spread_axis=str(spread_axis),
                spread_extremum=str(spread_extremum),
                spread_axis_probabilities=spread_axis_probabilities,
                spread_extremum_probabilities=spread_extremum_probabilities,
            )
        elif _is_area_rank_query(str(query_id)):
            dataset = _dataset_for_area_rank(
                params=params,
                instance_seed=int(instance_seed),
                labels=labels,
                points_per_cluster=int(points_per_cluster),
                query_id=str(query_id),
            )
        else:
            option_count = _target_option_count(
                support_params,
                instance_seed=int(instance_seed),
            )
            option_labels = _option_labels_for_count(int(option_count))
            answer_option_label = _target_option_label(
                support_params,
                instance_seed=int(instance_seed),
                cluster_count=int(cluster_count),
                option_labels=option_labels,
            )
            dataset = _dataset_for_centroid_option(
                params=params,
                instance_seed=int(instance_seed),
                labels=labels,
                target_cluster_label=str(answer_label),
                points_per_cluster=int(points_per_cluster),
                answer_option_label=str(answer_option_label),
                option_labels=option_labels,
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
        chart_font_family = _sample_chart_font_family(int(instance_seed), params)
        with temporary_default_font_family(str(chart_font_family)):
            rendered = _render_scatter(background, dataset=dataset, render_params=render_params)
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "annotation_hint",
                "annotation_hint_centroid_option_selection_label",
                "annotation_hint_cluster_area_rank_label",
                "json_example",
                "json_example_centroid_option_selection_label",
                "json_example_cluster_area_rank_label",
                "json_example_answer_only",
                "json_example_answer_only_option_letter",
                "object_description_single_scatter",
                "object_description_area_envelope_scatter",
                "answer_hint_option_letter",
            ],
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots=_build_prompt_slots(dataset, prompt_defaults),
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        annotation_cluster_labels = [str(label) for label in dataset.query.annotation_cluster_labels]
        annotation_point_ids = [
            str(point.point_id)
            for cluster in dataset.clusters
            if str(cluster.cluster_label) in set(annotation_cluster_labels)
            for point in cluster.points
        ]
        if str(dataset.query.query_id) == "centroid_option_selection_label":
            target_cluster_label = str(dataset.query.trace["target_cluster_label"])
            annotation_bbox_map: Dict[str, List[float]] = {
                "target_cluster": list(rendered.cluster_bboxes[str(target_cluster_label)]),
                "selected_option_marker": list(rendered.option_bboxes[str(dataset.query.answer_label)]),
            }
        elif str(dataset.query.query_id) == "cluster_separation_extremum_label":
            reference_label = str(dataset.query.trace["reference_cluster_label"])
            annotation_bbox_map = {
                "reference_cluster": list(rendered.cluster_bboxes[str(reference_label)]),
                "answer_cluster": list(rendered.cluster_bboxes[str(dataset.query.answer_label)]),
            }
        else:
            annotation_bbox_map = {
                "answer_cluster": list(rendered.cluster_bboxes[str(dataset.query.answer_label)])
            }
        answer_gt = TypedValue(type=str(dataset.query.answer_type), value=str(dataset.query.answer_label))
        annotation_gt = TypedValue(type="keyed_bbox_map", value=dict(annotation_bbox_map))
        projected_annotation = {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(annotation_bbox_map),
            "pixel_keyed_bbox_map": dict(annotation_bbox_map),
            "point_ids": list(annotation_point_ids),
            "cluster_labels": list(annotation_cluster_labels),
            "cluster_bboxes": {
                str(label): list(rendered.cluster_bboxes[str(label)])
                for label in annotation_cluster_labels
            },
            "option_bboxes": dict(rendered.option_bboxes),
            "option_centers_px": dict(rendered.option_centers_px),
            "cluster_envelope_bboxes": dict(rendered.cluster_envelope_bboxes),
        }

        total_points = int(sum(len(cluster.points) for cluster in dataset.clusters))
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(total_points), [24, 60]),
                "reasoning_load": clamp_unit_interval(float(_REASONING_LOAD_BY_VARIANT[str(query_id)])),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(dataset.scene_variant)]),
            },
        )
        values_by_cluster = {
            str(cluster.cluster_label): {
                "center": [round(float(cluster.center_x), 3), round(float(cluster.center_y), 3)],
                "slope": round(float(cluster.slope), 4),
                "spread_x": round(float(cluster.spread_x), 3),
                "spread_y": round(float(cluster.spread_y), 3),
                "area_envelope": (
                    {
                        "center": [round(float(cluster.area_envelope.center_x), 3), round(float(cluster.area_envelope.center_y), 3)],
                        "radius_x": round(float(cluster.area_envelope.radius_x), 3),
                        "radius_y": round(float(cluster.area_envelope.radius_y), 3),
                        "angle_degrees": round(float(cluster.area_envelope.angle_degrees), 3),
                        "area_value": round(float(cluster.area_envelope.area_value), 4),
                    }
                    if cluster.area_envelope is not None
                    else None
                ),
                "points": [
                    {
                        "point_id": str(point.point_id),
                        "x_value": round(float(point.x_value), 3),
                        "y_value": round(float(point.y_value), 3),
                    }
                    for point in cluster.points
                ],
            }
            for cluster in dataset.clusters
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_scatter_cluster",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                "query_id": str(query_id),
                "scene_variant": str(dataset.scene_variant),
                "answer": str(dataset.query.answer_label),
                "annotation_point_ids": list(annotation_point_ids),
                "annotation_cluster_labels": list(annotation_cluster_labels),
                "option_labels": [str(marker.option_label) for marker in dataset.option_markers],
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
                    "scene_variant": str(dataset.scene_variant),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "scene_variant_probabilities": {str(dataset.scene_variant): 1.0},
                    "cluster_count": int(cluster_count),
                    "points_per_cluster": int(points_per_cluster),
                    **dict(dataset.query.trace),
                },
            },
            "render_spec": {
                "scene_variant": str(dataset.scene_variant),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "point_radius_px": int(render_params.point_radius_px),
                "layout_jitter": dict(render_params.layout_jitter_meta),
                "font_asset_version": font_asset_version(),
                "chart_font_family": str(chart_font_family),
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "point_bboxes_px": dict(rendered.point_bboxes),
                "cluster_bboxes_px": dict(rendered.cluster_bboxes),
                "cluster_envelope_bboxes_px": dict(rendered.cluster_envelope_bboxes),
                "cluster_label_bboxes_px": dict(rendered.cluster_label_bboxes),
                "legend_bboxes_px": dict(rendered.legend_bboxes),
                "option_bboxes_px": dict(rendered.option_bboxes),
                "option_centers_px": dict(rendered.option_centers_px),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(dataset.scene_variant),
                "question_format": "scatter_cluster_query",
                "answer": str(dataset.query.answer_label),
                "answer_type": str(dataset.query.answer_type),
                "cluster_labels": list(labels),
                "cluster_count": int(cluster_count),
                "points_per_cluster": int(points_per_cluster),
                "total_point_count": int(total_points),
                "option_labels": [str(marker.option_label) for marker in dataset.option_markers],
                "values_by_cluster": dict(values_by_cluster),
                "annotation_point_ids": list(annotation_point_ids),
                "annotation_cluster_labels": list(annotation_cluster_labels),
                "query_id_probabilities": dict(query_id_probabilities),
                **dict(dataset.query.trace),
            },
            "witness_symbolic": {
                "type": "scatter_cluster_witness",
                "point_ids": list(annotation_point_ids),
                "cluster_labels": list(annotation_cluster_labels),
                "answer": str(dataset.query.answer_label),
            },
            "projected_annotation": dict(projected_annotation),
            "background": background_meta,
            "post_image_noise": dict(post_noise_meta),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
