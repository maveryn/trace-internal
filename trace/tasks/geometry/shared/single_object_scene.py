"""Reusable scene setup helpers for single-object geometry tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from PIL import Image, ImageDraw

from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...shared.geometry_primitives import Point
from .graph_paper import graph_spacing_from_cells, resolve_graph_cells_per_side, resolve_square_canvas_size
from .graph_rendering import (
    FALLBACK_GRAPH_STYLE,
    build_graph_coordinate_frame,
    enforce_graph_paper_background,
    resolve_graph_style_from_params,
    scaled_graph_style_for_scene,
)


@dataclass(frozen=True)
class GraphSceneContext:
    """Resolved render/grid context for one single-object geometry scene."""

    canvas_size: int
    graph_cells: int
    graph_spacing: int
    graph_frame: Dict[str, Any]
    graph_origin: Point
    graph_style: Dict[str, Any]
    scene_scale: int
    render_params: Dict[str, Any]


def resolve_graph_scene_context(
    rng,
    *,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    background_defaults: Mapping[str, Any],
    fallback_canvas_min: int,
    fallback_canvas_max: int,
    fallback_cells_min: int,
    fallback_cells_max: int,
    require_graph_paper_background: bool = True,
    graph_style_overrides: Mapping[str, Any] | None = None,
) -> GraphSceneContext:
    """Resolve deterministic graph-space scene parameters for one instance."""
    canvas_size = resolve_square_canvas_size(
        rng,
        params=params,
        render_defaults=render_defaults,
        fallback_min=int(fallback_canvas_min),
        fallback_max=int(fallback_canvas_max),
    )
    graph_cells = resolve_graph_cells_per_side(
        rng,
        params=params,
        render_defaults=render_defaults,
        canvas_size=int(canvas_size),
        fallback_min=int(fallback_cells_min),
        fallback_max=int(fallback_cells_max),
        min_spacing_px=4,
    )
    graph_spacing = graph_spacing_from_cells(
        canvas_size=int(canvas_size),
        graph_cells=int(graph_cells),
        min_spacing_px=4,
    )
    base_graph_style = resolve_graph_style_from_params(
        params,
        default_background_config=background_defaults,
        fallback_style=FALLBACK_GRAPH_STYLE,
    )
    scene_scale = int(max(1, int(base_graph_style.get("scene_supersample_scale", 1))))
    graph_style = dict(base_graph_style)
    if isinstance(graph_style_overrides, Mapping):
        graph_style.update(dict(graph_style_overrides))
    graph_style["spacing"] = int(graph_spacing)
    outer_margin_px = int(max(0, int(graph_style.get("outer_margin_px", 0))))
    graph_frame = build_graph_coordinate_frame(
        canvas_size=int(canvas_size),
        spacing=int(graph_spacing),
        target_cells=int(graph_cells),
        outer_margin_px=int(outer_margin_px),
        origin_fraction_x=float(graph_style.get("origin_fraction_x", 0.5)),
        origin_fraction_y=float(graph_style.get("origin_fraction_y", 0.5)),
    )
    graph_origin = (
        float(graph_frame["origin_pixel"][0]),
        float(graph_frame["origin_pixel"][1]),
    )
    render_graph_style = scaled_graph_style_for_scene(graph_style, scene_scale=int(scene_scale))
    if bool(require_graph_paper_background):
        render_params = enforce_graph_paper_background(params, graph_style=render_graph_style)
    else:
        render_params = dict(params)
    return GraphSceneContext(
        canvas_size=int(canvas_size),
        graph_cells=int(graph_cells),
        graph_spacing=int(graph_spacing),
        graph_frame=dict(graph_frame),
        graph_origin=(float(graph_origin[0]), float(graph_origin[1])),
        graph_style=dict(graph_style),
        scene_scale=int(scene_scale),
        render_params=dict(render_params),
    )


def make_graph_scene_canvas(
    *,
    instance_seed: int,
    context: GraphSceneContext,
    background_defaults: Mapping[str, Any],
    require_graph_paper: bool = True,
) -> Tuple[Image.Image, ImageDraw.ImageDraw, Dict[str, Any]]:
    """Create one background image + draw handle for one resolved scene context."""
    render_canvas_size = int(context.canvas_size) * int(context.scene_scale)
    image, background_meta = make_background_canvas(
        canvas_size=int(render_canvas_size),
        instance_seed=int(instance_seed),
        params=dict(context.render_params),
        default_config=background_defaults,
        fallback_color=(248, 248, 248),
    )
    if bool(require_graph_paper) and str(background_meta.get("selected_style", "")) != "graph_paper":
        raise RuntimeError("geometry measurement tasks must render on graph_paper backgrounds")
    return image, ImageDraw.Draw(image), dict(background_meta)


def finalize_graph_scene_image(
    image: Image.Image,
    *,
    instance_seed: int,
    context: GraphSceneContext,
    background_meta: Mapping[str, Any],
    noise_defaults: Mapping[str, Any],
) -> Tuple[Image.Image, Dict[str, Any], Dict[str, Any]]:
    """Downscale supersampled render, attach metadata, and apply post-noise."""
    out_image = image
    if int(context.scene_scale) > 1:
        out_image = out_image.resize(
            (int(context.canvas_size), int(context.canvas_size)),
            resample=Image.Resampling.LANCZOS,
        )
    background = dict(background_meta)
    render_style_spec = background.get("style_spec", {})
    selected_style = str(background.get("selected_style", ""))
    if str(selected_style) == "graph_paper":
        resolved_style_spec = dict(context.graph_style)
        if isinstance(render_style_spec, Mapping):
            for key in (
                "base_color",
                "line_color",
                "major_line_color",
                "axis_color",
                "center_point_color",
                "origin_label_color",
                "color_variation_enabled",
                "color_variation_applied",
                "color_variation_sampled",
                "base_color_jitter",
                "line_color_jitter",
                "major_line_darken_range",
                "axis_darken_range",
                "center_point_darken_extra_range",
                "origin_label_darken_extra_range",
            ):
                if key in render_style_spec:
                    resolved_style_spec[key] = render_style_spec[key]
    else:
        resolved_style_spec = dict(render_style_spec) if isinstance(render_style_spec, Mapping) else {}
    background["style_spec"] = resolved_style_spec
    background["render_scale"] = int(context.scene_scale)
    out_image, noise_meta = apply_post_image_noise(
        out_image,
        instance_seed=int(instance_seed),
        params=dict(context.render_params),
        default_config=noise_defaults,
    )
    return out_image, background, dict(noise_meta)
