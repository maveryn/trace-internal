"""Task assembly for combo chart panel tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.seed import hash64, spawn_rng
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...shared.config_defaults import group_default
from ...shared.font_assets import font_asset_version, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import temporary_default_font_family
from ..shared.complexity import build_chart_complexity, normalize_int_with_bounds
from .panel_common import (
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    SCENE_ID,
    TASK_ID,
    _COMPLEXITY_WEIGHTS,
    _GEN_DEFAULTS,
    _PROMPT_DEFAULTS,
    _QUERY_REASONING_LOAD,
    _RENDER_DEFAULTS,
    _SCENE_VARIANT_LOADS,
    _SCENE_VARIANTS,
    _axis_choice,
    _as_int_bounds,
    _explicit_axis_selected,
    _public_task_param_overrides,
)
from .panel_rendering import _render_combo_scene, _render_params
from .panel_sampling import (
    _choose_metric_pair,
    _construct_threshold_crossing_values,
    _is_threshold_crossing_query,
    _resolve_query_answer,
    _sample_labels,
    _sample_values,
)

def _merge_prompt_slots(base: Mapping[str, Any], extra: Mapping[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    merged.update(dict(extra))
    return merged

class ChartsComboPanelQueryTask:
    """Shared generator for public combo-chart tasks."""

    domain = "charts"
    task_group = "combo"
    default_dataset_enabled = True
    task_id = TASK_ID
    query_ids: Tuple[str, ...] = ()

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        if not self.query_ids:
            raise ValueError("combo chart task must define query_ids")
        query_id, query_probabilities = _axis_choice(
            params=params,
            instance_seed=int(instance_seed),
            supported=self.query_ids,
            explicit_keys=("query_id", "query_variant"),
            weights_key="query_id_weights",
            balance_key="balanced_query_id_sampling",
            namespace=f"{self.task_id}.query",
        )
        query_axis_explicit = _explicit_axis_selected(
            params,
            ("query_id", "query_variant"),
            self.query_ids,
        )
        scene_variant, scene_probabilities = _axis_choice(
            params=params,
            instance_seed=int(instance_seed),
            supported=_SCENE_VARIANTS,
            explicit_keys=("scene_variant",),
            weights_key="scene_variant_weights",
            balance_key="balanced_scene_variant_sampling",
            namespace=f"{self.task_id}.scene",
            sampling_divisor=max(1, len(self.query_ids)),
        )
        scene_axis_explicit = _explicit_axis_selected(params, ("scene_variant",), _SCENE_VARIANTS)
        target_sampling_divisor = (1 if query_axis_explicit else max(1, len(self.query_ids))) * (
            1 if scene_axis_explicit else max(1, len(_SCENE_VARIANTS))
        )
        label_min, label_max = _as_int_bounds(params, "label_count_min", "label_count_max", (7, 11))
        value_min, value_max = _as_int_bounds(params, "value_min", "value_max", (12, 88))
        rng = spawn_rng(int(instance_seed), f"{self.task_id}.values")
        label_count = int(rng.randint(int(label_min), int(label_max)))
        labels = _sample_labels(rng, label_count)
        primary_values = _sample_values(rng, count=label_count, low=value_min, high=value_max)
        line_values = _sample_values(rng, count=label_count, low=value_min, high=value_max)
        construction_trace: Dict[str, Any] = {}
        if _is_threshold_crossing_query(str(query_id)):
            constructed_values, construction_trace = _construct_threshold_crossing_values(
                query_id=str(query_id),
                label_count=int(label_count),
                value_min=int(value_min),
                value_max=int(value_max),
                params=params,
                instance_seed=int(instance_seed),
                target_sampling_divisor=int(target_sampling_divisor),
            )
            if str(construction_trace["target_series_role"]) == "primary":
                primary_values = tuple(int(value) for value in constructed_values)
            else:
                line_values = tuple(int(value) for value in constructed_values)
        primary_name, line_name = _choose_metric_pair(int(instance_seed))
        background, background_meta = make_background_canvas(
            canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 1080))),
            canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 660))),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        chart_font_family = sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.chart_font",
            params=params,
            explicit_key="chart_font_family",
            weights_key="chart_font_family_weights",
        )
        with temporary_default_font_family(str(chart_font_family)):
            scene = _render_combo_scene(
                background,
                labels=labels,
                primary_values=primary_values,
                line_values=line_values,
                scene_variant=str(scene_variant),
                primary_name=str(primary_name),
                line_name=str(line_name),
                params=params,
                instance_seed=int(instance_seed),
            )
        answer_gt, annotation_points, query_trace, task_key, query_key, answer_hint_key, annotation_hint_key = _resolve_query_answer(
            task_query_ids=self.query_ids,
            query_id=str(query_id),
            scene=scene,
            rng=spawn_rng(int(instance_seed), f"{self.task_id}.query_params"),
            params=params,
            instance_seed=int(instance_seed),
            target_sampling_divisor=int(target_sampling_divisor),
            construction_trace=construction_trace,
        )
        prompt_defaults = dict(_PROMPT_DEFAULTS)
        object_description_key = f"object_description_{scene_variant}"
        if object_description_key not in prompt_defaults:
            raise ValueError(f"missing prompt default '{object_description_key}' for {self.task_id}")
        object_description_template = str(
            params.get(
                object_description_key,
                prompt_defaults[object_description_key],
            )
        )
        object_description = object_description_template.format(
            primary_name=str(primary_name),
            line_name=str(line_name),
        )
        prompt_slots = _merge_prompt_slots(
            {
                "object_description": object_description,
                "primary_name": str(primary_name),
                "line_name": str(line_name),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[answer_hint_key]),
                "annotation_hint": str(prompt_defaults[annotation_hint_key]),
                "json_example": str(prompt_defaults[f"json_example_{task_key}"]),
                "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{task_key}"]),
            },
            query_trace,
        )
        prompt_selection = render_task_prompt_variants(
            domain="charts",
            task_group="combo",
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(task_key),
            query_key=str(query_key),
            slots=prompt_slots,
            instance_seed=int(instance_seed),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        image, post_noise_meta = apply_post_image_noise(
            scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        render_params_for_trace = _render_params(params, instance_seed=int(instance_seed))
        query_params = {
            "query_id": str(query_id),
            "query_id_probabilities": dict(query_probabilities),
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(scene_probabilities),
            "labels": list(labels),
            "primary_name": str(primary_name),
            "line_name": str(line_name),
            "primary_values": [int(value) for value in primary_values],
            "line_values": [int(value) for value in line_values],
            "label_count": int(label_count),
            "label_count_range": [int(label_min), int(label_max)],
            **dict(query_trace),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_combo_panel",
                "entities": [dict(entity) for entity in scene.entities],
                "relations": dict(query_params),
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
                "scene_id": SCENE_ID,
                "scene_variant": str(scene_variant),
                "plot_bbox": list(scene.plot_bbox),
                "primary_axis_max": int(scene.primary_axis_max),
                "line_axis_max": int(scene.line_axis_max),
                "layout_jitter": dict(render_params_for_trace.layout_jitter_meta),
                "text_style": {
                    "tick_font_size_px": int(render_params_for_trace.tick_font_size),
                    "label_font_size_px": int(render_params_for_trace.label_font_size),
                    "value_font_size_px": int(render_params_for_trace.value_font_size),
                    "legend_font_size_px": int(render_params_for_trace.legend_font_size),
                    "font_asset_version": str(font_asset_version()),
                    "chart_font_family": str(chart_font_family),
                    "chart_font_exclude_tags": [],
                },
                "background": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(scene.plot_bbox),
                "legend_bbox_px": list(scene.legend_bbox),
                "context_protected_bboxes_px": {
                    "plot": list(scene.plot_bbox),
                    "legend": list(scene.legend_bbox),
                },
                "primary_points_px": [list(point) for point in scene.primary_points],
                "line_points_px": [list(point) for point in scene.line_points],
                "entities": [dict(entity) for entity in scene.entities],
            },
            "execution_trace": {
                "query_id": str(query_id),
                "question_format": str(task_key),
                "answer": answer_gt.value,
                "answer_type": str(answer_gt.type),
                **dict(query_params),
            },
            "verifier_payload": {
                "answer": answer_gt.value,
                "answer_type": str(answer_gt.type),
                "query_id": str(query_id),
                "primary_values": [int(value) for value in primary_values],
                "line_values": [int(value) for value in line_values],
                "labels": list(labels),
                **dict(query_trace),
            },
            "witness_symbolic": {
                "type": "keyed_point_map",
                "count": int(len(annotation_points)),
            },
            "projected_annotation": {
                "type": "keyed_point_map",
                "keyed_point_map": {str(key): list(point) for key, point in annotation_points.items()},
                "pixel_keyed_point_map": {str(key): list(point) for key, point in annotation_points.items()},
            },
            "background": dict(background_meta),
            "post_image_noise": dict(post_noise_meta),
        }
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(label_count), [int(label_min), int(label_max)]),
                "reasoning_load": float(_QUERY_REASONING_LOAD[str(query_id)]),
                "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(scene_variant)]),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=TypedValue(
                type="keyed_point_map",
                value={str(key): list(point) for key, point in annotation_points.items()},
            ),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
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
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) if attempt == 0 else int(hash64(instance_seed, f"{self.task_id}.retry", attempt))
            try:
                return self._generate_once(attempt_seed, params=params)
            except ValueError as exc:
                last_error = exc
        raise RuntimeError(f"failed to generate {self.task_id}: {last_error}")
