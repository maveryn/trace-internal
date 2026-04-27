"""Distribution density task that returns the winning violin label."""

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
from ..shared.param_overrides import apply_task_variant_overrides
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TaskVariant = str

TASK_ID = "task_charts_distribution_density_label"
SCENE_VARIANT = "violin"
_SUPPORTED_TASK_VARIANTS: Tuple[str, ...] = (
    "highest_mode",
    "lowest_mode",
    "bimodal_label",
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
    "highest_mode": 0.20,
    "lowest_mode": 0.20,
    "bimodal_label": 1.0,
}


def _resolve_task_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the violin density-label query variant."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_TASK_VARIANTS,
        task_id=TASK_ID,
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        balance_flag_key="balanced_task_variant_sampling",
        axis_namespace="task_variant",
    )


@register_task
class ChartsDistributionDensityLabelTask:
    """Return the label of the violin plot matching one density-shape query."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "distribution"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        base_params = dict(params)
        task_variant, task_variant_probabilities = _resolve_task_variant(base_params, instance_seed=int(instance_seed))
        effective_params = apply_task_variant_overrides(base_params, task_variant=str(task_variant))
        mark_style = resolve_chart_mark_colors(
            effective_params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_RENDER_DEFAULTS_FALLBACK,
            instance_seed=int(instance_seed),
            scene_variant=SCENE_VARIANT,
            mark_count=1,
        )
        violins, answer_label, evidence_values, trace_extras = build_density_dataset_for_variant(
            task_variant=str(task_variant),
            params=effective_params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
            mark_style=mark_style,
        )
        render_params = resolve_chart_render_params_for_task(
            {**dict(effective_params), **mark_style},
            render_defaults=_RENDER_DEFAULTS,
            defaults=_RENDER_DEFAULTS_FALLBACK,
        )

        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=effective_params,
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
            params=effective_params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "task_family_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "object_description_violin",
                "evidence_hint_highest_mode",
                "evidence_hint_lowest_mode",
                "evidence_hint_bimodal_label",
                "json_example_highest_mode",
                "json_example_lowest_mode",
                "json_example_bimodal_label",
                "json_example_answer_only_highest_mode",
                "json_example_answer_only_lowest_mode",
                "json_example_answer_only_bimodal_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            task_variant_key=str(task_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_violin"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(task_variant)}"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults[f"json_example_{str(task_variant)}"]),
                "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{str(task_variant)}"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="option_letter", value=str(answer_label))
        evidence_gt = TypedValue(type="integer_list", value=[int(value) for value in evidence_values])
        evidence_projection = projected_mark_evidence(rendered_scene, [str(answer_label)])
        label_centers = {
            str(mark["label"]): list(mark["label_center_px"])
            for mark in rendered_scene.mark_traces
        }
        trace_generation_meta = {
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
        }

        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_violin_distribution",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "task_variant": str(task_variant),
                    "scene_variant": SCENE_VARIANT,
                    "answer_label": str(answer_label),
                    "evidence_values": [int(value) for value in evidence_values],
                },
            },
            "query_spec": {
                "task_variant": str(task_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "task_variant": str(task_variant),
                    "scene_variant": SCENE_VARIANT,
                    "task_variant_probabilities": dict(task_variant_probabilities),
                    "category_count": int(trace_extras["category_count"]),
                    "category_count_range": list(trace_extras["category_count_range"]),
                    "value_range": list(trace_extras["value_range"]),
                    **dict(trace_generation_meta),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": SCENE_VARIANT,
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
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
                "task_variant": str(task_variant),
                "scene_variant": SCENE_VARIANT,
                "answer_label": str(answer_label),
                "evidence_values": [int(value) for value in evidence_values],
                "labels": [str(mark["label"]) for mark in rendered_scene.mark_traces],
                "category_count": int(trace_extras["category_count"]),
                "category_count_range": list(trace_extras["category_count_range"]),
                "value_range": list(trace_extras["value_range"]),
                "support_by_label": dict(trace_extras["support_by_label"]),
                **dict(trace_generation_meta),
                "task_variant_probabilities": dict(task_variant_probabilities),
                "question_format": "label_open",
                "mark_color_sampling_policy": str(mark_style["sampling_policy"]),
                "mark_fill_rgb": list(mark_style["mark_fill_rgb"]),
                "mark_outline_rgb": list(mark_style["mark_outline_rgb"]),
                **{
                    str(key): value
                    for key, value in mark_style.items()
                    if key not in {"sampling_policy", "mark_fill_rgb", "mark_outline_rgb"}
                },
            },
            "witness_symbolic": {
                "type": "integer_list",
                "value": [int(value) for value in evidence_values],
            },
            "projected_evidence": {
                "integer_list": [int(value) for value in evidence_values],
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
                "reasoning_load": float(_REASONING_LOAD_BY_VARIANT[str(task_variant)]),
                "scene_variant_load": 0.80,
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
            task_variant=str(task_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["ChartsDistributionDensityLabelTask"]
