"""Task assembly for parallel-coordinates chart tasks."""

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
from ...shared.text_rendering import temporary_default_font_family
from ..shared.complexity import build_chart_complexity, clamp_unit_interval, normalize_int_with_bounds
from .profile_common import (
    CONDITION_QUERY_IDS,
    CROSSING_QUERY_IDS,
    _COMPLEXITY_WEIGHTS,
    _PROMPT_DEFAULTS,
    _QUERY_LOADS,
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    SCENE_ID,
    TASK_ID,
    Point,
    _Dataset,
    _Rendered,
    _public_task_param_overrides,
    _resolve_query_id,
    _resolve_render_params,
    _sample_chart_font_family,
)
from .profile_rendering import _render_parallel_coordinates
from .profile_sampling import _build_dataset

def _bbox_center(bbox: Sequence[float]) -> Tuple[float, float]:
    if len(bbox) != 4:
        raise ValueError(f"expected bbox with 4 values, got {bbox}")
    return (float(bbox[0] + bbox[2]) / 2.0, float(bbox[1] + bbox[3]) / 2.0)

def _round_point(x: float, y: float) -> Point:
    return [round(float(x), 2), round(float(y), 2)]

def _axis_point(dataset: _Dataset, rendered: _Rendered, profile_id: str, axis_index: int) -> Tuple[float, float]:
    bbox = rendered.point_bboxes_px[f"{profile_id}:axis_{int(axis_index)}"]
    return _bbox_center(bbox)

def _segment_midpoint(dataset: _Dataset, rendered: _Rendered, profile_id: str) -> Point:
    x0, y0 = _axis_point(dataset, rendered, str(profile_id), int(dataset.query.axis_i))
    x1, y1 = _axis_point(dataset, rendered, str(profile_id), int(dataset.query.axis_j))
    return _round_point((float(x0) + float(x1)) / 2.0, (float(y0) + float(y1)) / 2.0)

def _crossing_point(dataset: _Dataset, rendered: _Rendered, first_profile_id: str, second_profile_id: str) -> Point:
    axis_i = int(dataset.query.axis_i)
    axis_j = int(dataset.query.axis_j)
    x0, y0 = _axis_point(dataset, rendered, str(first_profile_id), axis_i)
    x1, y1 = _axis_point(dataset, rendered, str(first_profile_id), axis_j)
    _, other_y0 = _axis_point(dataset, rendered, str(second_profile_id), axis_i)
    _, other_y1 = _axis_point(dataset, rendered, str(second_profile_id), axis_j)
    first_delta = float(y1) - float(y0)
    second_delta = float(other_y1) - float(other_y0)
    denom = float(first_delta) - float(second_delta)
    if abs(float(denom)) < 1e-9:
        return _round_point((float(x0) + float(x1)) / 2.0, (float(y0) + float(y1)) / 2.0)
    t = (float(other_y0) - float(y0)) / float(denom)
    t = max(0.0, min(1.0, float(t)))
    return _round_point(float(x0) + (float(x1) - float(x0)) * t, float(y0) + first_delta * t)

def _annotation_points(dataset: _Dataset, rendered: _Rendered) -> Tuple[str, Dict[str, Point] | List[Point]]:
    profiles_by_id = {str(profile.profile_id): profile for profile in dataset.profiles}
    if str(dataset.query.query_id) in CROSSING_QUERY_IDS:
        points: List[Point] = [
            _crossing_point(dataset, rendered, str(first_profile_id), str(second_profile_id))
            for first_profile_id, second_profile_id in dataset.query.crossing_pairs
        ]
        return "point_set", list(points)

    points_by_label: Dict[str, Point] = {}
    for profile_id in dataset.query.annotation_profile_ids:
        profile = profiles_by_id[str(profile_id)]
        points_by_label[str(profile.label)] = _segment_midpoint(dataset, rendered, str(profile_id))
    return "keyed_point_map", dict(points_by_label)

def _build_prompt_slots(dataset: _Dataset, prompt_defaults: Mapping[str, Any]) -> Dict[str, Any]:
    is_label = str(dataset.query.answer_type) == "string"
    axis_i_label = str(dataset.metrics[int(dataset.query.axis_i)])
    axis_j_label = str(dataset.metrics[int(dataset.query.axis_j)])
    slots: Dict[str, Any] = {
        "object_description": str(prompt_defaults["object_description_parallel_coordinates"]),
        "axis_i": axis_i_label,
        "axis_j": axis_j_label,
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_defaults["answer_hint_label" if is_label else "answer_hint_count"]),
        "annotation_hint": str(prompt_defaults["annotation_hint_label" if is_label else "annotation_hint_condition_count"]),
        "json_example": str(prompt_defaults["json_example_label" if is_label else "json_example_condition_count"]),
        "json_example_answer_only": str(prompt_defaults["json_example_answer_only_label" if is_label else "json_example_answer_only_count"]),
    }
    if dataset.query.threshold is not None:
        slots["threshold"] = int(dataset.query.threshold)
    if str(dataset.query.query_id) == "above_on_both_axes":
        slots["condition_phrase"] = "above"
        slots["condition_detail"] = f"above {int(dataset.query.threshold)} on both axes"
    elif str(dataset.query.query_id) == "below_on_both_axes":
        slots["condition_phrase"] = "below"
        slots["condition_detail"] = f"below {int(dataset.query.threshold)} on both axes"
    elif str(dataset.query.query_id) == "above_on_one_below_on_other":
        slots["condition_phrase"] = "mixed"
        slots["condition_detail"] = f"above {int(dataset.query.threshold)} on {axis_i_label} and below {int(dataset.query.threshold)} on {axis_j_label}"
    elif str(dataset.query.query_id) == "largest_increase_between_axes":
        slots["delta_phrase"] = "largest increase"
    elif str(dataset.query.query_id) == "largest_decrease_between_axes":
        slots["delta_phrase"] = "largest decrease"
    elif str(dataset.query.query_id) == "largest_absolute_change_between_axes":
        slots["delta_phrase"] = "largest absolute change"
    elif str(dataset.query.query_id) == "crossings_involving_profile_between_axes":
        reference = str(dataset.query.params["reference_profile_label"])
        slots["reference_profile"] = reference
    if str(dataset.query.query_id) in CROSSING_QUERY_IDS:
        slots["annotation_hint"] = str(prompt_defaults["annotation_hint_crossing_count"])
        slots["json_example"] = str(prompt_defaults["json_example_crossing_count"])
    elif str(dataset.query.query_id) in CONDITION_QUERY_IDS:
        slots["annotation_hint"] = str(prompt_defaults["annotation_hint_condition_count"])
        slots["json_example"] = str(prompt_defaults["json_example_condition_count"])
    return slots

class ChartsParallelCoordinatesProfileTask:
    """Generate parallel-coordinates profile chart questions."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "parallel_coordinates"
    default_dataset_enabled = True

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
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                return self._generate_once(int(instance_seed) + int(attempt), params=dict(params))
            except Exception as exc:
                last_error = exc
                continue
        raise RuntimeError(f"failed to generate {self.task_id} after {max_attempts} attempts: {last_error}")

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        dataset = _build_dataset(
            params=params,
            instance_seed=int(instance_seed),
            query_id=str(query_id),
            query_id_probabilities=query_id_probabilities,
        )
        render_params = _resolve_render_params({**dict(params), "_render_style_seed": int(instance_seed)})
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        chart_font_family = _sample_chart_font_family(int(instance_seed), params)
        with temporary_default_font_family(str(chart_font_family)):
            rendered = _render_parallel_coordinates(background, dataset=dataset, render_params=render_params)
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
                "answer_hint_label",
                "answer_hint_count",
                "annotation_hint_label",
                "annotation_hint_condition_count",
                "annotation_hint_crossing_count",
                "json_example_label",
                "json_example_condition_count",
                "json_example_crossing_count",
                "json_example_answer_only_label",
                "json_example_answer_only_count",
                "object_description_parallel_coordinates",
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

        annotation_type, annotation_points = _annotation_points(dataset, rendered)
        answer_value: int | str = int(dataset.query.answer) if str(dataset.query.answer_type) == "integer" else str(dataset.query.answer)
        answer_gt = TypedValue(type=str(dataset.query.answer_type), value=answer_value)
        annotation_gt = TypedValue(type=str(annotation_type), value=annotation_points)
        profiles_by_id = {profile.profile_id: profile for profile in dataset.profiles}
        axis_pair = [int(dataset.query.axis_i), int(dataset.query.axis_j)]
        profile_rows = [
            {
                "profile_id": str(profile.profile_id),
                "label": str(profile.label),
                "values": [int(value) for value in profile.values],
                "color_rgb": list(profile.color_rgb),
            }
            for profile in dataset.profiles
        ]
        profile_labels = [str(profiles_by_id[str(value)].label) for value in dataset.query.annotation_profile_ids]
        projected_annotation: Dict[str, Any] = {
            "type": str(annotation_type),
            "profile_ids": [str(value) for value in dataset.query.annotation_profile_ids],
            "profile_labels": list(profile_labels),
            "axis_pair": list(axis_pair),
            "segment_bboxes": {
                str(key): list(value)
                for key, value in rendered.segment_bboxes_px.items()
                if any(str(key).startswith(str(profile_id) + ":") for profile_id in dataset.query.annotation_profile_ids)
            },
        }
        if str(annotation_type) == "keyed_point_map":
            keyed_point_map = dict(annotation_points) if isinstance(annotation_points, dict) else {}
            projected_annotation.update(
                {
                    "keyed_point_map": dict(keyed_point_map),
                    "pixel_keyed_point_map": dict(keyed_point_map),
                    "point_set": list(keyed_point_map.values()),
                    "pixel_point_set": list(keyed_point_map.values()),
                }
            )
        else:
            point_set = list(annotation_points) if isinstance(annotation_points, list) else []
            projected_annotation.update(
                {
                    "point_set": list(point_set),
                    "pixel_point_set": list(point_set),
                    "crossing_pair_labels": [
                        [str(profiles_by_id[str(first)].label), str(profiles_by_id[str(second)].label)]
                        for first, second in dataset.query.crossing_pairs
                    ],
                }
            )
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(len(dataset.profiles) * len(dataset.metrics), [20, 54]),
                "reasoning_load": clamp_unit_interval(_QUERY_LOADS[str(query_id)]),
                "scene_variant_load": 0.68,
            },
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_parallel_coords",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(dataset.scene_variant),
                    "answer": answer_value,
                    "axis_pair": list(axis_pair),
                    "annotation_profile_ids": [str(value) for value in dataset.query.annotation_profile_ids],
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(dataset.query.params),
            },
            "render_spec": {
                "scene_variant": str(dataset.scene_variant),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "axis_x_px": {str(key): float(value) for key, value in rendered.axis_x_px.items()},
                "line_width_px": int(render_params.line_width_px),
                "point_radius_px": int(render_params.point_radius_px),
                "layout_jitter": dict(render_params.layout_jitter_meta),
                "font_assets": {
                    "font_asset_version": font_asset_version(),
                    "chart_font_family": str(chart_font_family),
                },
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "axis_x_px": {str(key): float(value) for key, value in rendered.axis_x_px.items()},
                "point_bboxes_px": dict(rendered.point_bboxes_px),
                "segment_bboxes_px": dict(rendered.segment_bboxes_px),
                "profile_bboxes_px": dict(rendered.profile_bboxes_px),
                "label_bboxes_px": dict(rendered.label_bboxes_px),
                "threshold_bboxes_px": {str(key): list(value) for key, value in rendered.threshold_bboxes_px.items()},
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(dataset.scene_variant),
                "question_format": "parallel_coords_query",
                "answer": answer_value,
                "answer_type": str(dataset.query.answer_type),
                "axis_i": int(dataset.query.axis_i),
                "axis_j": int(dataset.query.axis_j),
                "axis_i_label": str(dataset.metrics[int(dataset.query.axis_i)]),
                "axis_j_label": str(dataset.metrics[int(dataset.query.axis_j)]),
                "metrics": [str(value) for value in dataset.metrics],
                "profiles": list(profile_rows),
                "threshold": dataset.query.threshold,
                "reference_profile_id": dataset.query.reference_profile_id,
                "annotation_profile_ids": [str(value) for value in dataset.query.annotation_profile_ids],
                "crossing_pairs": [list(pair) for pair in dataset.query.crossing_pairs],
                **dict(dataset.query.params),
            },
            "witness_symbolic": {
                "type": "parallel_coordinates_witness",
                "answer": answer_value,
                "axis_pair": list(axis_pair),
                "profile_ids": [str(value) for value in dataset.query.annotation_profile_ids],
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
            scene_id=SCENE_ID,
        )
