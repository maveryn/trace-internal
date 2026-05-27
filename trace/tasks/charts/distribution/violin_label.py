"""Violin distribution tasks with categorical label answers."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.chart_scene import render_violin_scene
from ..shared.complexity import (
    build_chart_complexity,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.distribution_chart_common import (
    DistributionChartDefaults,
    LabeledChartDefaults,
    build_density_dataset_for_variant,
    projected_mark_evidence,
    resolve_chart_axis_variant,
    resolve_chart_mark_colors,
    resolve_chart_render_params_for_task,
)
from ..shared.fixed_query_task import MergedChartQueryVariantTaskMixin
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


QueryVariant = str

TASK_ID = "charts_distribution_violin_label_base"
SCENE_ID = "violin"
SCENE_VARIANT = "violin"
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "highest_mode",
    "lowest_mode",
    "bimodal_label",
    "widest_support",
    "narrowest_support",
)

_DEFAULTS = DistributionChartDefaults()
_RENDER_DEFAULTS_FALLBACK = LabeledChartDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "distribution")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="distribution")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="distribution", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "highest_mode": 0.45,
    "lowest_mode": 0.45,
    "bimodal_label": 0.55,
    "widest_support": 0.60,
    "narrowest_support": 0.60,
}


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the concrete violin query branch."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_QUERY_IDS,
        task_id=TASK_ID,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


class ChartsDistributionViolinLabelTask:
    """Answer categorical-label questions over one violin-plot panel."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "distribution"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        mark_style = resolve_chart_mark_colors(
            params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_RENDER_DEFAULTS_FALLBACK,
            instance_seed=int(instance_seed),
            scene_variant=SCENE_VARIANT,
            mark_count=1,
        )
        violins, answer_label, evidence_values, trace_extras = build_density_dataset_for_variant(
            query_id=str(query_id),
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
            mark_style=mark_style,
        )
        render_params = resolve_chart_render_params_for_task(
            {**dict(params), **mark_style},
            render_defaults=_RENDER_DEFAULTS,
            defaults=_RENDER_DEFAULTS_FALLBACK,
            instance_seed=int(instance_seed),
        )

        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_violin_scene(
            background,
            violins=violins,
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
                "answer_hint",
                "object_description_violin",
                "evidence_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_violin"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="option_letter", value=str(answer_label))
        evidence_projection = projected_mark_evidence(rendered_scene, [str(answer_label)])
        evidence_bboxes = [list(bbox) for bbox in evidence_projection["bbox_set"]]
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        label_centers = {
            str(mark["label"]): list(mark["label_center_px"])
            for mark in rendered_scene.mark_traces
        }
        support_by_label = {
            str(label): dict(values)
            for label, values in trace_extras["support_by_label"].items()
        }
        mode_values_by_label = {
            str(label): [int(value) for value in values["mode_values"]]
            for label, values in support_by_label.items()
        }
        support_span_by_label = {
            str(label): int(values["support_span"])
            for label, values in support_by_label.items()
        }

        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_violin_distribution",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": SCENE_VARIANT,
                    "answer_label": str(answer_label),
                    "evidence_label": str(answer_label),
                    "evidence_values": [int(value) for value in evidence_values],
                    "generation_profile": str(trace_extras.get("generation_profile", "")),
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
                    "scene_variant": SCENE_VARIANT,
                    "query_id_probabilities": dict(query_id_probabilities),
                    "category_count": int(trace_extras["category_count"]),
                    "category_count_range": list(trace_extras["category_count_range"]),
                    "value_range": list(trace_extras["value_range"]),
                    "answer_label": str(answer_label),
                    "evidence_values": [int(value) for value in evidence_values],
                    "generation_profile": str(trace_extras.get("generation_profile", "")),
                    **{
                        str(key): value
                        for key, value in trace_extras.items()
                        if str(key)
                        not in {
                            "scene_variant",
                            "category_count",
                            "category_count_range",
                            "value_range",
                            "answer_label",
                            "evidence_values",
                            "support_by_label",
                            "generation_profile",
                        }
                    },
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": SCENE_VARIANT,
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "layout_jitter": dict(render_params.layout_jitter_meta or {}),
                "text_style": {
                    "label_font_size_px": int(render_params.label_font_size_px),
                    "tick_font_size_px": int(render_params.tick_font_size_px),
                    "label_stroke_width_px": int(render_params.label_stroke_width_px),
                },
                "axis_style": {
                    "axis_line_width_px": int(render_params.axis_line_width_px),
                    "grid_line_width_px": int(render_params.grid_line_width_px),
                    "tick_length_px": int(render_params.tick_length_px),
                },
                "violin_style": {
                    "mode_line_style": str(render_params.violin_mode_line_style),
                    "fill_style": str(render_params.violin_fill_style),
                    "width_scale": round(float(render_params.violin_width_scale), 4),
                    "smoothing_scale": round(float(render_params.violin_smoothing_scale), 4),
                    "palette_mode": str(render_params.violin_palette_mode),
                    "palette_offset": int(render_params.violin_palette_offset),
                },
                "mark_style": {
                    "sampling_policy": str(mark_style["sampling_policy"]),
                    "mark_fill_rgb": list(mark_style["mark_fill_rgb"]),
                    "mark_outline_rgb": list(mark_style["mark_outline_rgb"]),
                    **{
                        str(key): value
                        for key, value in mark_style.items()
                        if key not in {"sampling_policy", "mark_fill_rgb", "mark_outline_rgb"}
                    },
                },
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "y_axis_max": int(rendered_scene.y_axis_max),
                "y_ticks": [int(value) for value in rendered_scene.y_ticks],
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "label_centers_px": dict(label_centers),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": SCENE_VARIANT,
                "answer_label": str(answer_label),
                "evidence_label": str(answer_label),
                "evidence_values": [int(value) for value in evidence_values],
                "labels": [str(mark["label"]) for mark in rendered_scene.mark_traces],
                "mode_values_by_label": dict(mode_values_by_label),
                "support_span_by_label": dict(support_span_by_label),
                "support_by_label": dict(support_by_label),
                "category_count": int(trace_extras["category_count"]),
                "category_count_range": list(trace_extras["category_count_range"]),
                "value_range": list(trace_extras["value_range"]),
                "query_id_probabilities": dict(query_id_probabilities),
                "question_format": "label_open",
                "mark_color_sampling_policy": str(mark_style["sampling_policy"]),
                "mark_fill_rgb": list(mark_style["mark_fill_rgb"]),
                "mark_outline_rgb": list(mark_style["mark_outline_rgb"]),
                **{
                    str(key): value
                    for key, value in trace_extras.items()
                    if str(key)
                    not in {
                        "scene_variant",
                        "category_count",
                        "category_count_range",
                        "value_range",
                        "answer_label",
                        "evidence_values",
                        "support_by_label",
                    }
                },
            },
            "witness_symbolic": {
                "type": "object_set",
                "value": [str(answer_label)],
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
                **dict(evidence_projection),
            },
        }

        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(
                    int(trace_extras["category_count"]),
                    trace_extras["category_count_range"],
                ),
                "reasoning_load": float(_REASONING_LOAD_BY_VARIANT[str(query_id)]),
                "scene_variant_load": 0.0,
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(query_id),
            scene_id=SCENE_ID,
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class ChartsDistributionViolinDistributionFeatureLabelTask(
    MergedChartQueryVariantTaskMixin,
    ChartsDistributionViolinLabelTask,
):
    """Return the label with a requested violin distribution feature."""

    task_id = "task_charts__violin__distribution_feature_label"
    allowed_query_ids = (
        "highest_mode",
        "lowest_mode",
        "widest_support",
        "narrowest_support",
        "bimodal_label",
    )


__all__ = [
    "ChartsDistributionViolinDistributionFeatureLabelTask",
    "ChartsDistributionViolinLabelTask",
]
