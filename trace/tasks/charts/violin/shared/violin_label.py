"""Shared violin-chart scene helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence

from PIL import Image

from .....core.scene_config import get_scene_defaults
from .....core.visual.background import make_background_canvas
from .....core.visual.noise import apply_post_image_noise
from ....shared.config_defaults import required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ....shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ....shared.text_rendering import temporary_default_font_family
from ...shared.chart_scene import render_violin_scene
from ...shared.distribution_chart_common import DistributionChartDefaults, LabeledChartDefaults, projected_mark_annotation
from ...shared.distribution_chart_common import resolve_chart_mark_colors, resolve_chart_render_params_for_task
from ...shared.visual_defaults import (
    chart_font_asset_metadata,
    load_chart_scene_background_defaults,
    load_chart_scene_noise_defaults,
    sample_chart_font_family,
)


BASE_CONFIG_ID = "charts_violin_base"
SCENE_ID = "violin"
SCENE_VARIANT = "violin"

DISTRIBUTION_DEFAULTS = DistributionChartDefaults()
RENDER_DEFAULTS_FALLBACK = LabeledChartDefaults()
SCENE_DEFAULTS = get_scene_defaults("charts", SCENE_ID)
GEN_DEFAULTS, RENDER_DEFAULTS, PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    SCENE_DEFAULTS if isinstance(SCENE_DEFAULTS, Mapping) else {},
    task_id=BASE_CONFIG_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_scene_background_defaults(scene_id=SCENE_ID)
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)


@dataclass(frozen=True)
class ViolinRenderArtifacts:
    image: Image.Image
    rendered_scene: Any
    render_params: Any
    background_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]
    chart_font_family: str
    mark_style: Dict[str, Any]


def resolve_violin_mark_style(params: Mapping[str, Any], *, instance_seed: int) -> Dict[str, Any]:
    """Resolve the shared mark style for one violin scene instance."""

    return dict(
        resolve_chart_mark_colors(
            params,
            render_defaults=RENDER_DEFAULTS,
            defaults=RENDER_DEFAULTS_FALLBACK,
            instance_seed=int(instance_seed),
            scene_variant=SCENE_VARIANT,
            mark_count=1,
        )
    )


def build_violin_render_artifacts(
    *,
    violins: Sequence[Any],
    params: Mapping[str, Any],
    instance_seed: int,
    mark_style: Mapping[str, Any],
) -> ViolinRenderArtifacts:
    """Render a symbolic violin scene and return visual/projection artifacts."""

    render_params = resolve_chart_render_params_for_task(
        {**dict(params), **dict(mark_style)},
        render_defaults=RENDER_DEFAULTS,
        defaults=RENDER_DEFAULTS_FALLBACK,
        instance_seed=int(instance_seed),
    )
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    chart_font_family = sample_chart_font_family(
        instance_seed=int(instance_seed),
        namespace="charts.violin.chart_font",
        params=params,
    )
    with temporary_default_font_family(str(chart_font_family)):
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
    return ViolinRenderArtifacts(
        image=image,
        rendered_scene=rendered_scene,
        render_params=render_params,
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
        chart_font_family=str(chart_font_family),
        mark_style=dict(mark_style),
    )


def build_violin_prompt(
    *,
    prompt_query_key: str,
    instance_seed: int,
) -> Any:
    """Render the external prompt template for one violin prompt branch."""

    prompt_defaults = required_group_defaults(
        PROMPT_DEFAULTS,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "answer_hint",
            "object_description",
            "annotation_hint",
            "json_example",
            "json_example_answer_only",
        ),
        context=f"prompt defaults for {BASE_CONFIG_ID}",
    )
    prompt_selection = render_scene_prompt_variants(
        domain="charts",
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(prompt_query_key),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(prompt_defaults["object_description"]),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(prompt_defaults["annotation_hint"]),
            "answer_hint": str(prompt_defaults["answer_hint"]),
            "json_example": str(prompt_defaults["json_example"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
        },
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(prompt_selection)


def annotation_bboxes_for_label(rendered_scene: Any, answer_label: str) -> list[list[float]]:
    """Project the selected violin label to its minimal bbox annotation."""

    annotation_projection = projected_mark_annotation(rendered_scene, [str(answer_label)])
    return [list(bbox) for bbox in annotation_projection["bbox_set"]]


def label_centers(rendered_scene: Any) -> Dict[str, list[float]]:
    """Return visible label centers keyed by label text."""

    return {
        str(mark["label"]): list(mark["label_center_px"])
        for mark in rendered_scene.mark_traces
    }


def normalize_support_trace(trace_extras: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Normalize symbolic support metadata by label."""

    return {
        str(label): dict(values)
        for label, values in trace_extras["support_by_label"].items()
    }




def render_spec_from_artifacts(artifacts: ViolinRenderArtifacts) -> Dict[str, Any]:
    """Build the scene-level render metadata common to all violin objectives."""

    render_params = artifacts.render_params
    rendered_scene = artifacts.rendered_scene
    mark_style = artifacts.mark_style
    return {
        "canvas_width": int(render_params.canvas_width),
        "canvas_height": int(render_params.canvas_height),
        "coord_space": "pixel",
        "scene_variant": SCENE_VARIANT,
        "background_style": dict(artifacts.background_meta),
        "post_image_noise": dict(artifacts.post_noise_meta),
        "font_assets": chart_font_asset_metadata(str(artifacts.chart_font_family)),
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
    }


