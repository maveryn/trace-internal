"""Config resolution for Tangram puzzle scenes."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.core.sampling import support_probability_map, weighted_support_choice
from trace.core.seed import spawn_rng
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.render_variation import resolve_render_int, resolve_render_rgb

from .state import SUPPORTED_SCENE_VARIANTS, TangramRenderParams


def _support_from_config(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    options_key: str,
    fallback: Sequence[str],
) -> tuple[str, ...]:
    """Return an explicit support tuple from params/config/fallback."""

    raw = params.get(str(options_key), group_default(defaults, str(options_key), None))
    if raw is None:
        return tuple(str(item) for item in fallback)
    values = tuple(str(item).strip() for item in raw if str(item).strip())
    if not values:
        raise ValueError(f"{options_key} must contain at least one value")
    return values


def resolve_scene_variant(
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> tuple[str, dict[str, float]]:
    """Resolve one Tangram layout variant as non-semantic scene metadata."""

    support = _support_from_config(
        params,
        generation_defaults,
        options_key="scene_variant_options",
        fallback=SUPPORTED_SCENE_VARIANTS,
    )
    explicit = params.get(
        "scene_variant",
        group_default(generation_defaults, "scene_variant", None),
    )
    if explicit is not None:
        selected = str(explicit)
        if selected not in set(support):
            raise ValueError(f"scene_variant must be one of {support}")
        return selected, support_probability_map(support, selected=selected)
    raw_weights = params.get(
        "scene_variant_weights",
        group_default(generation_defaults, "scene_variant_weights", None),
    )
    weights = (
        {str(key): float(value) for key, value in raw_weights.items()}
        if isinstance(raw_weights, Mapping)
        else None
    )
    rng = spawn_rng(int(instance_seed), f"{namespace}.scene_variant")
    selected, probabilities = weighted_support_choice(
        rng,
        support,
        weights=weights,
        sort_keys=False,
    )
    return str(selected), dict(probabilities)


def resolve_tangram_render_params(
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    *,
    instance_seed: int,
    namespace: str,
) -> TangramRenderParams:
    """Resolve one Tangram render parameter bundle."""

    def _int(key: str, fallback: int) -> int:
        return resolve_render_int(
            params,
            render_defaults,
            str(key),
            int(fallback),
            instance_seed=int(instance_seed),
            namespace=f"{namespace}.render",
        )

    def _rgb(key: str, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
        return resolve_render_rgb(
            params,
            render_defaults,
            str(key),
            tuple(fallback),
            instance_seed=int(instance_seed),
            namespace=f"{namespace}.render",
        )

    return TangramRenderParams(
        canvas_width=int(_int("canvas_width", 1040)),
        canvas_height=int(_int("canvas_height", 860)),
        scene_margin_left_px=int(_int("scene_margin_left_px", 46)),
        scene_margin_right_px=int(_int("scene_margin_right_px", 46)),
        scene_margin_top_px=int(_int("scene_margin_top_px", 36)),
        scene_margin_bottom_px=int(_int("scene_margin_bottom_px", 42)),
        assembly_panel_width_px=int(_int("assembly_panel_width_px", 560)),
        assembly_panel_height_px=int(_int("assembly_panel_height_px", 410)),
        assembly_panel_padding_px=int(_int("assembly_panel_padding_px", 40)),
        assembly_to_options_gap_px=int(_int("assembly_to_options_gap_px", 20)),
        option_panel_width_px=int(_int("option_panel_width_px", 142)),
        option_panel_height_px=int(_int("option_panel_height_px", 146)),
        option_gap_px=int(_int("option_gap_px", 18)),
        option_row_gap_px=int(_int("option_row_gap_px", 12)),
        option_shape_box_size_px=int(_int("option_shape_box_size_px", 88)),
        option_label_gap_px=int(_int("option_label_gap_px", 6)),
        panel_corner_radius_px=int(_int("panel_corner_radius_px", 18)),
        content_corner_radius_px=int(_int("content_corner_radius_px", 12)),
        border_width_px=int(_int("border_width_px", 3)),
        seam_width_px=int(_int("seam_width_px", 3)),
        highlight_width_px=int(_int("highlight_width_px", 8)),
        option_label_font_size_px=int(_int("option_label_font_size_px", 24)),
        panel_fill_rgb=_rgb("panel_fill_rgb", (248, 249, 252)),
        assembly_panel_fill_rgb=_rgb("assembly_panel_fill_rgb", (252, 252, 255)),
        option_panel_fill_rgb=_rgb("option_panel_fill_rgb", (251, 251, 255)),
        option_shape_fill_rgb=_rgb("option_shape_fill_rgb", (238, 243, 249)),
        missing_fill_rgb=_rgb("missing_fill_rgb", (18, 20, 24)),
        marked_outline_rgb=_rgb("marked_outline_rgb", (18, 20, 24)),
        border_color_rgb=_rgb("border_color_rgb", (86, 94, 108)),
        seam_color_rgb=_rgb("seam_color_rgb", (42, 49, 59)),
        text_color_rgb=_rgb("text_color_rgb", (30, 34, 40)),
        text_stroke_rgb=_rgb("text_stroke_rgb", (255, 255, 255)),
        instance_seed=int(instance_seed),
    )


__all__ = [
    "resolve_scene_variant",
    "resolve_tangram_render_params",
]
