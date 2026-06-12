"""Rendering orchestration for the graph node-link scene."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from trace.core.visual.background import make_background_canvas
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.graph.shared.graph_scene import render_graph_scene
from trace.tasks.graph.shared.visual_defaults import load_graph_scene_background_defaults, load_graph_scene_noise_defaults

from .state import SCENE_ID


@dataclass(frozen=True)
class NodeLinkRenderedSample:
    """Rendered node-link sample plus non-semantic rendering metadata."""

    rendered_scene: Any
    image: Any
    background_meta: dict[str, Any]
    post_noise_meta: dict[str, Any]


def render_node_link_sample(
    *,
    sample: Any,
    layout_variant: str,
    layout_transform_variant: str,
    render_params: Any,
    layout_seed: int,
    directed: bool,
    params: Mapping[str, Any],
    instance_seed: int,
    scene_id: str = SCENE_ID,
) -> NodeLinkRenderedSample:
    """Render one graph sample and apply scene-local background/noise policy."""

    background_defaults = load_graph_scene_background_defaults(scene_id=str(scene_id))
    noise_defaults = load_graph_scene_noise_defaults(scene_id=str(scene_id), apply_prob=0.5)
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=background_defaults,
    )
    rendered_scene = render_graph_scene(
        graph_sample=sample,
        layout_variant=str(layout_variant),
        layout_transform_variant=str(layout_transform_variant),
        render_params=render_params,
        layout_seed=int(layout_seed),
        scene_title="Graph",
        directed=bool(directed),
        base_image=background,
    )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=noise_defaults,
    )
    return NodeLinkRenderedSample(
        rendered_scene=rendered_scene,
        image=image,
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
    )


__all__ = ["NodeLinkRenderedSample", "render_node_link_sample"]
