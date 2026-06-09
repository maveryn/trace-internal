"""Base task implementation for 3D bar-grid chart tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.seed import hash64
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...shared.config_defaults import group_default, required_group_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import temporary_default_font_family
from ..shared.complexity import build_chart_complexity, normalize_int_with_bounds
from ..shared.visual_defaults import chart_font_asset_metadata, sample_chart_font_family
from .grid_common import (
    AXIS_GAP_QUERY_IDS,
    AXIS_TOTAL_QUERY_IDS,
    CONDITION_COUNT_QUERY_IDS,
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    SCENE_ID,
    SUPPORTED_QUERY_IDS,
    TASK_ID,
    _COMPLEXITY_WEIGHTS,
    _PROMPT_DEFAULTS,
    _QUERY_REASONING_LOAD,
    _RENDER_DEFAULTS,
    _public_task_param_overrides,
)
from .grid_rendering import _render_bar_grid
from .grid_sampling import _build_dataset, _sample_query_id


def _make_prompt(
    *,
    query_id: str,
    prompt_defaults: Mapping[str, Any],
    slots: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[str, Dict[str, str], Dict[str, Any], Dict[str, Any], str]:
    prompt_selection = render_task_prompt_variants(
        domain="charts",
        task_group="three_d_bar",
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots=slots,
        instance_seed=int(instance_seed),
    )
    artifacts = build_prompt_trace_artifacts(prompt_selection)
    return (
        str(artifacts.prompt),
        dict(artifacts.prompt_variants),
        dict(artifacts.prompt_variant),
        dict(artifacts.prompt_variants_for_trace),
        str(artifacts.prompt_variant_active_key),
    )


class ChartsThreeDBarGridQueryTask:
    """Generate one 3D bar-grid chart query."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "three_d_bar"
    allowed_query_ids: Tuple[str, ...] = AXIS_TOTAL_QUERY_IDS
    default_dataset_enabled = False

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        query_id = _sample_query_id(params, allowed_query_ids=self.allowed_query_ids, instance_seed=int(instance_seed))
        if query_id not in set(SUPPORTED_QUERY_IDS):
            raise ValueError(f"unsupported 3D bar query_id: {query_id}")
        dataset, ranges = _build_dataset(query_id=str(query_id), params=params, instance_seed=int(instance_seed))
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_integer",
                "object_description",
                "annotation_hint_axis_total_value",
                "annotation_hint_axis_gap_value",
                "annotation_hint_condition_count",
                "json_example_axis_total_value",
                "json_example_axis_gap_value",
                "json_example_condition_count",
                "json_example_answer_only_axis_total_value",
                "json_example_answer_only_axis_gap_value",
                "json_example_answer_only_condition_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )

        background, background_meta = make_background_canvas(
            canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 1120))),
            canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 760))),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        chart_font_family = sample_chart_font_family(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.chart_font",
            params=params,
        )
        with temporary_default_font_family(str(chart_font_family)):
            rendered = _render_bar_grid(
                background,
                dataset=dataset,
                params=params,
                instance_seed=int(instance_seed),
            )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        trace_by_id = {str(trace["bar_id"]): trace for trace in rendered.bar_traces}
        annotation_points = [
            list(trace_by_id[str(bar_id)]["top_center_px"])
            for bar_id in dataset.query.annotation_bar_ids
            if str(bar_id) in trace_by_id
        ]
        task_prompt_group = (
            "axis_total_value"
            if str(query_id) in set(AXIS_TOTAL_QUERY_IDS)
            else "axis_gap_value"
            if str(query_id) in set(AXIS_GAP_QUERY_IDS)
            else "condition_count"
        )
        query_trace = dict(dataset.query.trace)
        slots = {
            "object_description": str(prompt_defaults["object_description"]),
            "series_label": str(query_trace.get("series_label", "")),
            "series_label_a": str(query_trace.get("series_label_a", "")),
            "series_label_b": str(query_trace.get("series_label_b", "")),
            "category_label": str(query_trace.get("category_label", "")),
            "category_label_a": str(query_trace.get("category_label_a", "")),
            "category_label_b": str(query_trace.get("category_label_b", "")),
            "start_category_label": str(query_trace.get("start_category_label", "")),
            "end_category_label": str(query_trace.get("end_category_label", "")),
            "comparison_phrase": str(query_trace.get("comparison_phrase", "")),
            "threshold": str(query_trace.get("threshold", "")),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(prompt_defaults[f"annotation_hint_{task_prompt_group}"]),
            "answer_hint": str(prompt_defaults["answer_hint_integer"]),
            "json_example": str(prompt_defaults[f"json_example_{task_prompt_group}"]),
            "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{task_prompt_group}"]),
        }
        prompt, prompt_variants, prompt_variant, prompt_variants_for_trace, active_prompt_key = _make_prompt(
            query_id=str(query_id),
            prompt_defaults=prompt_defaults,
            slots=slots,
            instance_seed=int(instance_seed),
        )

        values_by_category = {
            str(x_label): {
                str(series_label): int(
                    next(
                        bar.value
                        for bar in dataset.bars
                        if str(bar.x_label) == str(x_label) and str(bar.series_label) == str(series_label)
                    )
                )
                for series_label in dataset.series_labels
            }
            for x_label in dataset.x_labels
        }
        query_params = {
            "query_id": str(query_id),
            "public_task_id": str(self.task_id),
            "category_count": int(len(dataset.x_labels)),
            "series_count": int(len(dataset.series_labels)),
            "category_labels": [str(label) for label in dataset.x_labels],
            "series_labels": [str(label) for label in dataset.series_labels],
            "annotation_bar_ids": [str(bar_id) for bar_id in dataset.query.annotation_bar_ids],
            "answer_value": int(dataset.query.answer),
            **dict(ranges),
            **dict(query_trace),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_three_d_bar_grid",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": dict(query_params),
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_variant),
                "prompt_variant_active_key": str(active_prompt_key),
                "prompt_variants": dict(prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "coord_space": "pixel",
                "scene_variant": "three_d_bar_grid",
                "background_style": dict(background_meta),
                "font_assets": chart_font_asset_metadata(str(chart_font_family)),
                "post_image_noise": dict(post_noise_meta),
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "y_axis_max": int(rendered.y_axis_max),
                "y_ticks": [int(tick) for tick in rendered.y_ticks],
                "layout_jitter": dict(rendered.layout_jitter_meta),
                "bar_style": dict(rendered.bar_style_meta),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "bar_traces": [dict(trace) for trace in rendered.bar_traces],
                "legend_traces": [dict(trace) for trace in rendered.legend_traces],
            },
            "execution_trace": {
                "query_id": str(query_id),
                "answer_value": int(dataset.query.answer),
                "question_format": "numeric_open",
                "values_by_category": dict(values_by_category),
                "annotation_bar_ids": [str(bar_id) for bar_id in dataset.query.annotation_bar_ids],
                **dict(query_params),
            },
            "witness_symbolic": {
                "type": "three_d_bar_grid_values",
                "annotation_bar_ids": [str(bar_id) for bar_id in dataset.query.annotation_bar_ids],
            },
            "projected_annotation": {
                "type": "point_set",
                "point_set": list(annotation_points),
                "pixel_point_set": list(annotation_points),
            },
        }
        bar_count = int(len(dataset.x_labels) * len(dataset.series_labels))
        min_bar_count = int(ranges["category_count_range"][0]) * int(ranges["series_count_range"][0])
        max_bar_count = int(ranges["category_count_range"][1]) * int(ranges["series_count_range"][1])
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(bar_count), (int(min_bar_count), int(max_bar_count))),
                "reasoning_load": float(_QUERY_REASONING_LOAD[str(query_id)]),
                "annotation_count": normalize_int_with_bounds(
                    int(len(dataset.query.annotation_bar_ids)),
                    (1, max(1, int(max_bar_count))),
                ),
                "scene_variant_load": 0.78,
            },
        )
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=TypedValue(type="integer", value=int(dataset.query.answer)),
            annotation_gt=TypedValue(type="point_set", value=[list(point) for point in annotation_points]),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_variants),
        )

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
        attempts = max(1, int(max_attempts))
        last_error: Exception | None = None
        for attempt in range(attempts):
            attempt_seed = int(instance_seed) if attempt == 0 else int(hash64(int(instance_seed), "charts.three_d_bar.retry", int(attempt)))
            try:
                return self._generate_once(int(attempt_seed), params=params)
            except ValueError as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")
