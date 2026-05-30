"""Map-region count tasks for chart-domain visual reasoning."""

from __future__ import annotations

from typing import Any, Dict, List

from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults
from ...shared.font_assets import font_asset_version, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import temporary_default_font_family
from ..shared.complexity import build_chart_complexity, clamp_unit_interval, normalize_int_with_bounds
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin, MergedChartQueryVariantTaskMixin
from .choropleth_assets import WORLD_MAP_ASSET_ID as _WORLD_MAP_ASSET_ID
from .choropleth_assets import load_geographic_map_asset as _load_geographic_map_asset
from .choropleth_assets import load_world_map_asset as _load_world_map_asset
from .choropleth_assets import normalize_geographic_map_variant as _normalize_geographic_map_variant
from .choropleth_config import (
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    SUPPORTED_ADJACENT_QUERY_IDS,
    SUPPORTED_GROUP_FILTERED_VALUE_QUERY_IDS,
    SUPPORTED_MARKER_QUERY_IDS,
    SUPPORTED_MARKER_RENDER_VARIANTS,
    SUPPORTED_QUERY_IDS,
    SUPPORTED_REGION_CATEGORY_QUERY_IDS,
    SUPPORTED_REGION_SET_VALUE_QUERY_IDS,
    SUPPORTED_REGION_VALUE_QUERY_IDS,
    SUPPORTED_SCENE_VARIANTS,
    SUPPORTED_WORLD_FILTERED_QUERY_IDS,
    TASK_ID,
    _COMPLEXITY_WEIGHTS,
    _PROMPT_DEFAULTS,
    _REASONING_LOAD_BY_VARIANT,
    _SCENE_VARIANT_LOADS,
    _SUPPORTED_ADJACENT_QUERY_IDS,
    _SUPPORTED_REGION_CATEGORY_QUERY_IDS,
    _SUPPORTED_REGION_VALUE_QUERY_IDS,
    _SUPPORTED_WORLD_FILTERED_QUERY_IDS,
    _is_categorical_query_id,
    _is_group_filtered_value_query_id,
    _is_marker_query_id,
    _is_region_sum_value_query_id,
    _json_examples,
    _public_task_param_overrides,
    _resolve_query_id,
    _resolve_scene_variant,
    _support_sampling_params,
)
from .choropleth_dataset import _construct_dataset
from .choropleth_geography import (
    _border_segment_key,
    _border_segment_length,
    _centroid_lonlat_from_rings,
    _geographic_border_neighbors,
    _geographic_shared_border_lengths,
    _region_boundary_segments,
    _selected_geographic_region_adjacency,
    _synthetic_region_adjacency,
    _world_country_shared_border_lengths,
    _world_filtered_region_candidates,
)
from .choropleth_geometry import (
    _balanced_int,
    _choose_random,
    _grid_pair_support,
    _grid_points,
    _neighbors,
    _polygon_bbox,
    _polygon_center,
    _reading_order_region_ids,
    _region_polygon,
    _region_sort_key,
    _sample_connected_cells,
    _shrink_polygon,
)
from .choropleth_marker_rendering import _render_marker_layer
from .choropleth_rendering import (
    _render_choropleth_map,
    _render_world_choropleth_map,
    _resolve_render_params,
)
class ChartsMapChoroplethRegionCountTask:
    """Answer count questions over an irregular choropleth region map."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "map"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
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
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        support_params = _support_sampling_params(
            params,
            query_id_probabilities=query_id_probabilities,
        )
        dataset = _construct_dataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            params=support_params,
            instance_seed=int(instance_seed),
        )
        render_style_params = {**dict(params), "_render_style_seed": int(instance_seed)}
        render_params = _resolve_render_params(
            render_style_params,
            query_id=str(query_id),
            legend_count=len(dataset["legend_bins"]),
        )
        chart_font_family = sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.chart_font",
            params=params,
            explicit_key="chart_font_family",
            weights_key="chart_font_family_weights",
        )
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        categorical = _is_categorical_query_id(str(query_id))
        marker_task = _is_marker_query_id(str(query_id))
        show_region_value_labels = _is_region_sum_value_query_id(str(query_id))
        marker_bboxes_by_region: Dict[str, List[List[float]]] = {}
        marker_group_bbox_map: Dict[str, List[float]] = {}
        marker_render_meta: Dict[str, Any] = {}
        with temporary_default_font_family(str(chart_font_family)):
            if str(scene_variant) == "geographic_region_map":
                rendered_scene = _render_world_choropleth_map(
                    background,
                    scene_title=str(dataset["scene_title"]),
                    map_asset_id=str(dataset.get("map_asset_id") or _WORLD_MAP_ASSET_ID),
                    regions=list(dataset["regions"]),
                    legend_bins=list(dataset["legend_bins"]),
                    render_params=render_params,
                    instance_seed=int(instance_seed),
                    categorical=bool(categorical),
                    draw_color_legend=not bool(marker_task),
                    neutral_regions=bool(marker_task),
                    show_region_value_labels=bool(show_region_value_labels),
                )
            else:
                rendered_scene = _render_choropleth_map(
                    background,
                    scene_title=str(dataset["scene_title"]),
                    rows=int(dataset["rows"]),
                    cols=int(dataset["cols"]),
                    regions=list(dataset["regions"]),
                    legend_bins=list(dataset["legend_bins"]),
                    render_params=render_params,
                    instance_seed=int(instance_seed),
                    categorical=bool(categorical),
                    draw_color_legend=not bool(marker_task),
                    neutral_regions=bool(marker_task),
                    show_region_value_labels=bool(show_region_value_labels),
                )
            if bool(marker_task):
                rendered_scene, marker_bboxes_by_region, marker_group_bbox_map, marker_render_meta = _render_marker_layer(
                    rendered_scene,
                    dataset=dataset,
                    render_params=render_params,
                    params=render_style_params,
                    instance_seed=int(instance_seed),
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
                "object_description_synthetic_region_map",
                "object_description_geographic_region_map",
                "object_description_geographic_categorical_map",
                "object_description_region_value_map",
                "object_description_geographic_group_value_map",
                "object_description_marker_map",
                "answer_hint_count",
                "answer_hint_label",
                "answer_hint_value",
                "evidence_hint_region_count",
                "evidence_hint_region_value",
                "evidence_hint_marker",
                "json_example_numeric_threshold_region_count",
                "json_example_numeric_interval_region_count",
                "json_example_categorical_region_count",
                "json_example_continent_region_count",
                "json_example_continent_category_region_count",
                "json_example_continent_threshold_region_count",
                "json_example_named_region_set_total_value",
                "json_example_group_filtered_region_value",
                "json_example_adjacent_same_category_count",
                "json_example_adjacent_category_count",
                "json_example_adjacent_numeric_threshold_count",
                "json_example_marker_region_threshold_count",
                "json_example_marker_region_extremum_label",
                "json_example_answer_only_numeric_threshold_region_count",
                "json_example_answer_only_numeric_interval_region_count",
                "json_example_answer_only_categorical_region_count",
                "json_example_answer_only_continent_region_count",
                "json_example_answer_only_continent_category_region_count",
                "json_example_answer_only_continent_threshold_region_count",
                "json_example_answer_only_named_region_set_total_value",
                "json_example_answer_only_group_filtered_region_value",
                "json_example_answer_only_adjacent_same_category_count",
                "json_example_answer_only_adjacent_category_count",
                "json_example_answer_only_adjacent_numeric_threshold_count",
                "json_example_answer_only_marker_region_threshold_count",
                "json_example_answer_only_marker_region_extremum_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _json_examples(str(query_id), prompt_defaults=prompt_defaults)
        qparams = dict(dataset["question_params"])
        if bool(marker_task):
            object_description = str(
                dataset.get("map_object_description")
                or prompt_defaults["object_description_marker_map"]
            )
        elif _is_group_filtered_value_query_id(str(query_id)):
            object_description = str(prompt_defaults["object_description_geographic_group_value_map"])
        elif _is_region_sum_value_query_id(str(query_id)):
            object_description = str(prompt_defaults["object_description_region_value_map"])
        elif str(scene_variant) == "geographic_region_map" and bool(categorical):
            asset_description = str(dataset.get("map_object_description") or "")
            object_description = (
                asset_description.replace("colored by value and a color legend", "colored by category and a category legend")
                if asset_description
                else str(prompt_defaults["object_description_geographic_categorical_map"])
            )
        else:
            object_description = str(
                dataset.get("map_object_description")
                or prompt_defaults.get(
                    f"object_description_{str(scene_variant)}",
                    prompt_defaults["object_description_synthetic_region_map"],
                )
            )
        region_noun = str(dataset.get("map_region_noun") or ("countries" if str(scene_variant) == "geographic_region_map" else "regions"))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str("marker_map" if bool(marker_task) else prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(
                    prompt_defaults["evidence_hint_marker"]
                    if bool(marker_task)
                    else (
                        prompt_defaults["evidence_hint_region_value"]
                        if _is_region_sum_value_query_id(str(query_id))
                        else prompt_defaults["evidence_hint_region_count"]
                    )
                ),
                "answer_hint": str(
                    prompt_defaults["answer_hint_label"]
                    if str(dataset["answer_type"]) == "string"
                    else (
                        prompt_defaults["answer_hint_value"]
                        if _is_region_sum_value_query_id(str(query_id))
                        else prompt_defaults["answer_hint_count"]
                    )
                ),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "region_noun": str(region_noun),
                "continent_label": str(qparams.get("continent_label", "")),
                "reference_country_label": str(qparams.get("reference_country_label", "")),
                "threshold_phrase": str(qparams.get("threshold_phrase", "")),
                "interval_phrase": str(qparams.get("interval_phrase", "")),
                "category_label": str(qparams.get("category_label", "")),
                "extremum_word": str(qparams.get("extremum_word", "")),
                "region_set_name": str(qparams.get("region_set_name", "")),
                "region_set_label_list": str(qparams.get("region_set_label_list", "")),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_region_ids = [str(region_id) for region_id in dataset["evidence_region_ids"]]
        if bool(marker_task):
            evidence_bboxes = [
                list(marker_group_bbox_map[str(region_id)])
                for region_id in evidence_region_ids
            ]
        else:
            evidence_bboxes = [list(rendered_scene.region_bbox_map[str(region_id)]) for region_id in evidence_region_ids]
        projected_evidence = {
            "type": "bbox_set",
            "bbox_set": list(evidence_bboxes),
            "pixel_bbox_set": list(evidence_bboxes),
            "bbox_map": (
                {str(region_id): list(marker_group_bbox_map[str(region_id)]) for region_id in evidence_region_ids}
                if bool(marker_task)
                else {str(region_id): list(rendered_scene.region_bbox_map[str(region_id)]) for region_id in evidence_region_ids}
            ),
            "region_ids": list(evidence_region_ids),
            **({"marker_bboxes_by_region": {str(region_id): list(marker_bboxes_by_region.get(str(region_id), [])) for region_id in evidence_region_ids}} if bool(marker_task) else {}),
        }
        answer_gt = TypedValue(
            type=str(dataset["answer_type"]),
            value=(str(dataset["answer_value"]) if str(dataset["answer_type"]) == "string" else int(dataset["answer_value"])),
        )
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        evidence_scan = normalize_int_with_bounds(len(evidence_region_ids), [1, 16])
        region_scan = normalize_int_with_bounds(int(dataset["region_count"]), [14, 28])
        legend_scan = normalize_int_with_bounds(len(dataset["legend_bins"]), [3, 6])
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BY_VARIANT[str(query_id)])
            + (0.10 * float(evidence_scan))
            + (0.06 * float(legend_scan))
        )
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": float(region_scan),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(scene_variant)]),
            },
        )
        query_params = {
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "query_id_probabilities": dict(query_id_probabilities),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "geographic_map_variant": str(dataset.get("geographic_map_variant") or ""),
            "geographic_map_variant_probabilities": dict(dataset.get("geographic_map_variant_probabilities", {})),
            "region_count": int(dataset["region_count"]),
            "legend_bin_count": int(len(dataset["legend_bins"])),
            "target_count": int(dataset["target_count"]),
            "target_count_probabilities": dict(dataset["target_count_probabilities"]),
            **dict(qparams),
        }

        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_marker_map" if bool(marker_task) else "chart_region_map",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "answer_value": str(dataset["answer_value"]) if str(dataset["answer_type"]) == "string" else int(dataset["answer_value"]),
                    "evidence_region_ids": list(evidence_region_ids),
                    "target_bin_indices": [int(value) for value in dataset["target_bin_indices"]],
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
                "map_asset_id": str(dataset.get("map_asset_id") or ""),
                "geographic_map_variant": str(dataset.get("geographic_map_variant") or ""),
                "geographic_map_variant_probabilities": dict(dataset.get("geographic_map_variant_probabilities", {})),
                "map_display_name": str(dataset.get("map_display_name") or ""),
                "map_region_noun": str(dataset.get("map_region_noun") or ""),
                "map_source": dict(dataset.get("map_source", {})),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "rows": int(dataset["rows"]),
                "cols": int(dataset["cols"]),
                "active_cells": [[int(row), int(col)] for row, col in dataset["active_cells"]],
                "selected_region_ids": [str(region["region_id"]) for region in dataset["regions"]],
                "legend_bins": [dict(item) for item in dataset["legend_bins"]],
                "legend_position": str(render_params.legend_position),
                "legend_position_probabilities": dict(render_params.legend_position_probabilities),
                "show_region_value_labels": bool(show_region_value_labels),
                **({"marker_render": dict(marker_render_meta)} if bool(marker_task) else {}),
                "map_palette_rgb": [[int(channel) for channel in color] for color in render_params.map_palette_rgb],
                "map_palette_variant": str(render_params.map_palette_variant),
                "map_palette_variant_probabilities": dict(render_params.map_palette_variant_probabilities),
                "background_style": dict(background_meta),
                "font_assets": {
                    "font_asset_version": font_asset_version(),
                    "chart_font_family": str(chart_font_family),
                },
                "region_gap_px": int(render_params.region_gap_px),
                "layout_jitter": dict(render_params.layout_jitter_meta),
                "map_render_style": dict(rendered_scene.render_meta),
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "panel_bbox_px": list(rendered_scene.panel_bbox_px),
                "title_bbox_px": list(rendered_scene.title_bbox_px),
                "map_bbox_px": list(rendered_scene.map_bbox_px),
                "legend_bbox_px": list(rendered_scene.legend_bbox_px),
                "region_bboxes_px": dict(rendered_scene.region_bbox_map),
                "region_centers_px": dict(rendered_scene.region_center_map),
                "legend_entry_bboxes_px": dict(rendered_scene.legend_entry_bbox_map),
                **({"marker_group_bboxes_px": dict(marker_group_bbox_map), "marker_bboxes_px": dict(marker_bboxes_by_region)} if bool(marker_task) else {}),
                **(
                    {"world_projection_bbox_px": list(rendered_scene.render_meta["world_projection_bbox_px"])}
                    if "world_projection_bbox_px" in rendered_scene.render_meta
                    else {}
                ),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "question_format": (
                    "map_marker_query"
                    if bool(marker_task)
                    else ("map_region_value" if _is_region_sum_value_query_id(str(query_id)) else "map_region_count")
                ),
                "scene_title": str(dataset["scene_title"]),
                "map_asset_id": str(dataset.get("map_asset_id") or ""),
                "geographic_map_variant": str(dataset.get("geographic_map_variant") or ""),
                "map_display_name": str(dataset.get("map_display_name") or ""),
                "map_region_noun": str(dataset.get("map_region_noun") or ""),
                "rows": int(dataset["rows"]),
                "cols": int(dataset["cols"]),
                "region_count": int(dataset["region_count"]),
                "active_cells": [[int(row), int(col)] for row, col in dataset["active_cells"]],
                "legend_bins": [dict(item) for item in dataset["legend_bins"]],
                "regions": [dict(item) for item in dataset["regions"]],
                "regions_by_id": {str(key): dict(value) for key, value in dict(dataset["regions_by_id"]).items()},
                "answer_value": str(dataset["answer_value"]) if str(dataset["answer_type"]) == "string" else int(dataset["answer_value"]),
                "answer_type": str(dataset["answer_type"]),
                "evidence_region_ids": list(evidence_region_ids),
                "target_bin_indices": [int(value) for value in dataset["target_bin_indices"]],
                "nonmatching_bin_indices": [int(value) for value in dataset["nonmatching_bin_indices"]],
                "threshold_direction": str(dataset["threshold_direction"]),
                "evidence_semantics": str(query_id),
            },
            "witness_symbolic": {
                "type": (
                    "map_marker_witness"
                    if bool(marker_task)
                    else ("map_region_value_witness" if _is_region_sum_value_query_id(str(query_id)) else "map_region_count_witness")
                ),
                "candidate_region_ids": list(evidence_region_ids),
                "answer_value": str(dataset["answer_value"]) if str(dataset["answer_type"]) == "string" else int(dataset["answer_value"]),
            },
            "projected_evidence": dict(projected_evidence),
            "background": background_meta,
            "post_image_noise": dict(post_noise_meta),
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=str("marker_map" if bool(marker_task) else "region_map"),
            query_id=str(query_id),
        )

@register_task
class ChartsMapLegendPredicateRegionCountTask(
    MergedChartQueryVariantTaskMixin,
    ChartsMapChoroplethRegionCountTask,
):
    """Count map regions satisfying a numeric or categorical legend predicate."""

    task_id = "task_charts__region_map__legend_predicate_region_count"
    allowed_query_ids = _SUPPORTED_REGION_VALUE_QUERY_IDS + _SUPPORTED_REGION_CATEGORY_QUERY_IDS

@register_task
class ChartsMapContinentFilteredCountTask(
    MergedChartQueryVariantTaskMixin,
    ChartsMapChoroplethRegionCountTask,
):
    """Count world-map regions after applying a continent filter."""

    task_id = "task_charts__region_map__continent_filtered_count"
    allowed_query_ids = _SUPPORTED_WORLD_FILTERED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        fixed_params = dict(params)
        fixed_params["scene_variant"] = "geographic_region_map"
        fixed_params["geographic_map_variant"] = "world_countries"
        return super().generate(int(instance_seed), params=fixed_params, max_attempts=int(max_attempts))

@register_task
class ChartsMapNamedRegionSetTotalValueTask(
    FixedChartQueryVariantTaskMixin,
    ChartsMapChoroplethRegionCountTask,
):
    """Sum visible integer values over a named set of labeled map regions."""

    task_id = "task_charts__region_map__named_region_set_total_value"
    fixed_query_id = "named_region_set_total_value"

@register_task
class ChartsMapGroupFilteredRegionValueTask(
    FixedChartQueryVariantTaskMixin,
    ChartsMapChoroplethRegionCountTask,
):
    """Sum visible integer values for a geographic group satisfying a value condition."""

    task_id = "task_charts__region_map__group_filtered_region_value"
    fixed_query_id = "group_filtered_region_value"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        fixed_params = dict(params)
        fixed_params["scene_variant"] = "geographic_region_map"
        fixed_params["geographic_map_variant"] = "world_countries"
        return super().generate(int(instance_seed), params=fixed_params, max_attempts=int(max_attempts))

@register_task
class ChartsMapAdjacentConditionCountTask(
    MergedChartQueryVariantTaskMixin,
    ChartsMapChoroplethRegionCountTask,
):
    """Count highlighted-region neighbors satisfying a legend condition."""

    task_id = "task_charts__region_map__adjacent_condition_count"
    allowed_query_ids = _SUPPORTED_ADJACENT_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        fixed_params = dict(params)
        fixed_params["scene_variant"] = "synthetic_region_map"
        return super().generate(int(instance_seed), params=fixed_params, max_attempts=int(max_attempts))

@register_task
class ChartsMapMarkerRegionThresholdCountTask(
    FixedChartQueryVariantTaskMixin,
    ChartsMapChoroplethRegionCountTask,
):
    """Count map regions whose marker-encoded value satisfies a threshold."""

    task_id = "task_charts__marker_map__marker_region_threshold_count"
    fixed_query_id = "marker_region_threshold_count"

@register_task
class ChartsMapMarkerRegionExtremumLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsMapChoroplethRegionCountTask,
):
    """Identify the labeled map region with the largest or smallest marker value."""

    task_id = "task_charts__marker_map__marker_region_extremum_label"
    fixed_query_id = "marker_region_extremum_label"


__all__ = [
    'ChartsMapChoroplethRegionCountTask',
    'ChartsMapAdjacentConditionCountTask',
    'ChartsMapContinentFilteredCountTask',
    'ChartsMapGroupFilteredRegionValueTask',
    'ChartsMapLegendPredicateRegionCountTask',
    'ChartsMapMarkerRegionExtremumLabelTask',
    'ChartsMapMarkerRegionThresholdCountTask',
    'ChartsMapNamedRegionSetTotalValueTask',
    'SUPPORTED_ADJACENT_QUERY_IDS',
    'SUPPORTED_GROUP_FILTERED_VALUE_QUERY_IDS',
    'SUPPORTED_MARKER_RENDER_VARIANTS',
    'SUPPORTED_MARKER_QUERY_IDS',
    'SUPPORTED_REGION_SET_VALUE_QUERY_IDS',
    'SUPPORTED_REGION_CATEGORY_QUERY_IDS',
    'SUPPORTED_REGION_VALUE_QUERY_IDS',
    'SUPPORTED_SCENE_VARIANTS',
    'SUPPORTED_QUERY_IDS',
    'SUPPORTED_WORLD_FILTERED_QUERY_IDS',
]
