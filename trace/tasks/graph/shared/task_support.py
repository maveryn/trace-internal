"""Shared graph-task support for balanced variants and render defaults."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from .graph_scene import GraphRenderParams
from .style import build_graph_named_color_theme


def resolve_graph_named_variant(
    rng,
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Tuple[str, ...],
    instance_seed: int,
    task_id: str,
    namespace: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced named graph-task variant axis."""

    selected_variant, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=gen_defaults,
        supported_variants=supported,
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
    )
    variant = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected_variant),
        variant_probabilities=probabilities,
        supported_variants=supported,
        balance_flag_key=str(balance_flag_key),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        sampling_namespace=f"{str(task_id)}:{str(namespace)}",
    )
    return str(variant), {str(key): float(value) for key, value in sorted(probabilities.items())}


def resolve_graph_render_params(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    task_id: str,
    render_defaults: Mapping[str, Any],
    fallback_defaults: Any,
    node_color_name: str,
    node_shape_variant: str,
) -> GraphRenderParams:
    """Resolve one concrete graph render-parameter set for a graph task."""

    radius_min = int(
        params.get(
            "node_radius_min_px",
            group_default(render_defaults, "node_radius_min_px", int(getattr(fallback_defaults, "node_radius_min_px"))),
        )
    )
    radius_max = int(
        params.get(
            "node_radius_max_px",
            group_default(render_defaults, "node_radius_max_px", int(getattr(fallback_defaults, "node_radius_max_px"))),
        )
    )
    render_rng = spawn_rng(int(instance_seed), f"{str(task_id)}.render")
    node_radius = int(render_rng.randint(int(radius_min), int(max(radius_min, radius_max))))
    try:
        color_theme = build_graph_named_color_theme(str(node_color_name))
    except Exception:
        color_theme = None

    def _render_value(key: str) -> Any:
        return params.get(key, group_default(render_defaults, key, getattr(fallback_defaults, key)))

    return GraphRenderParams(
        canvas_width=int(_render_value("canvas_width")),
        canvas_height=int(_render_value("canvas_height")),
        outer_margin_px=int(_render_value("outer_margin_px")),
        panel_padding_px=int(_render_value("panel_padding_px")),
        panel_corner_radius_px=int(_render_value("panel_corner_radius_px")),
        panel_title_font_size_px=int(_render_value("panel_title_font_size_px")),
        node_shape_variant=str(node_shape_variant),
        node_radius_px=int(node_radius),
        edge_width_px=int(_render_value("edge_width_px")),
        arrow_length_px=int(_render_value("arrow_length_px")),
        arrow_width_px=int(_render_value("arrow_width_px")),
        node_border_width_px=int(_render_value("node_border_width_px")),
        label_font_size_px=int(_render_value("label_font_size_px")),
        background_color_rgb=tuple(
            int(value)
            for value in (
                color_theme.background_color_rgb if color_theme is not None else _render_value("background_color_rgb")
            )
        ),
        panel_fill_rgb=tuple(
            int(value) for value in (color_theme.panel_fill_rgb if color_theme is not None else _render_value("panel_fill_rgb"))
        ),
        panel_border_rgb=tuple(
            int(value)
            for value in (color_theme.panel_border_rgb if color_theme is not None else _render_value("panel_border_rgb"))
        ),
        title_color_rgb=tuple(
            int(value) for value in (color_theme.title_color_rgb if color_theme is not None else _render_value("title_color_rgb"))
        ),
        edge_color_rgb=tuple(
            int(value) for value in (color_theme.edge_color_rgb if color_theme is not None else _render_value("edge_color_rgb"))
        ),
        node_fill_rgb=tuple(
            int(value) for value in (color_theme.node_fill_rgb if color_theme is not None else _render_value("node_fill_rgb"))
        ),
        node_border_rgb=tuple(
            int(value)
            for value in (color_theme.node_border_rgb if color_theme is not None else _render_value("node_border_rgb"))
        ),
        label_text_rgb=tuple(
            int(value) for value in (color_theme.label_text_rgb if color_theme is not None else _render_value("label_text_rgb"))
        ),
        label_stroke_rgb=tuple(
            int(value)
            for value in (color_theme.label_stroke_rgb if color_theme is not None else _render_value("label_stroke_rgb"))
        ),
    )


__all__ = [
    "resolve_graph_named_variant",
    "resolve_graph_render_params",
]
