"""Config resolution for transparent-sheet overlay puzzle scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.sampling import (
    support_probability_map,
    weighted_support_choice,
)
from trace.core.seed import spawn_rng
from trace.tasks.puzzles.shared.unit_size_jitter import (
    resolve_puzzle_unit_size_scale,
    scale_puzzle_px,
)
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.render_variation import resolve_render_int, resolve_render_rgb

from .state import SUPPORTED_MARK_SHAPES, SUPPORTED_SCENE_VARIANTS


@dataclass(frozen=True)
class OverlayRenderParams:
    """Resolved rendering knobs for transparent-sheet overlay scenes."""

    canvas_width: int
    canvas_height: int
    scene_margin_left_px: int
    scene_margin_right_px: int
    scene_margin_top_px: int
    scene_margin_bottom_px: int
    reference_panel_height_px: int
    reference_panel_padding_px: int
    source_paper_size_px: int
    source_gap_px: int
    reference_to_options_gap_px: int
    option_paper_size_px: int
    option_gap_px: int
    option_row_gap_px: int
    option_label_gap_px: int
    paper_corner_radius_px: int
    panel_corner_radius_px: int
    border_width_px: int
    option_label_font_size_px: int
    combine_symbol_font_size_px: int
    panel_fill_rgb: Tuple[int, int, int]
    paper_fill_rgb: Tuple[int, int, int]
    paper_shadow_rgb: Tuple[int, int, int]
    border_color_rgb: Tuple[int, int, int]
    text_color_rgb: Tuple[int, int, int]
    text_stroke_rgb: Tuple[int, int, int]
    mark_fill_rgb: Tuple[int, int, int]
    mark_outline_rgb: Tuple[int, int, int]
    mark_shape: str
    mark_shape_probabilities: Dict[str, float]
    instruction_fill_rgb: Tuple[int, int, int]
    unit_size_jitter: Dict[str, Any]


def _support_from_config(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    options_key: str,
    fallback: Sequence[str],
) -> tuple[str, ...]:
    """Return one explicit string support from params, config, or fallback."""

    raw = params.get(str(options_key), group_default(defaults, str(options_key), None))
    if raw is None:
        return tuple(str(item) for item in fallback)
    values = tuple(str(item).strip() for item in raw if str(item).strip())
    if not values:
        raise ValueError(f"{options_key} must contain at least one value")
    return values


def _select_supported_value(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    explicit_key: str,
    weights_key: str,
    options_key: str,
    fallback: Sequence[str],
    instance_seed: int,
    namespace: str,
) -> tuple[str, dict[str, float]]:
    """Select one configured support value using explicit or weighted sampling."""

    support = _support_from_config(
        params,
        defaults,
        options_key=str(options_key),
        fallback=tuple(fallback),
    )
    explicit = params.get(str(explicit_key), group_default(defaults, str(explicit_key), None))
    if explicit is not None:
        selected = str(explicit)
        if selected not in set(support):
            raise ValueError(f"{explicit_key} must be one of {support}")
        return selected, support_probability_map(support, selected=selected)

    raw_weights = params.get(str(weights_key), group_default(defaults, str(weights_key), None))
    weights = {
        str(key): float(value)
        for key, value in raw_weights.items()
    } if isinstance(raw_weights, Mapping) else None
    rng = spawn_rng(int(instance_seed), str(namespace))
    selected, probabilities = weighted_support_choice(
        rng,
        support,
        weights=weights,
        sort_keys=False,
    )
    return str(selected), dict(probabilities)


def resolve_scene_variant(
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    *,
    instance_seed: int,
    namespace: str,
) -> tuple[str, dict[str, float]]:
    """Resolve one overlay visual scene treatment."""

    return _select_supported_value(
        params,
        generation_defaults,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        options_key="scene_variant_options",
        fallback=SUPPORTED_SCENE_VARIANTS,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.scene_variant",
    )


def resolve_render_params(
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    *,
    instance_seed: int,
    namespace: str,
) -> OverlayRenderParams:
    """Resolve rendering parameters and visual mark-style metadata."""

    def _int(key: str, fallback: int) -> int:
        return resolve_render_int(
            params,
            render_defaults,
            str(key),
            int(fallback),
            instance_seed=int(instance_seed),
            namespace="puzzle_overlay_render",
        )

    def _triple(key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        return resolve_render_rgb(
            params,
            render_defaults,
            str(key),
            fallback,
            instance_seed=int(instance_seed),
            namespace="puzzle_overlay_render",
        )

    mark_shape, mark_shape_probabilities = _select_supported_value(
        params,
        render_defaults,
        explicit_key="mark_shape",
        weights_key="mark_shape_weights",
        options_key="mark_shape_options",
        fallback=SUPPORTED_MARK_SHAPES,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.mark_shape",
    )
    unit_size_scale, unit_size_jitter = resolve_puzzle_unit_size_scale(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace="puzzles.overlay.unit_size",
    )

    return OverlayRenderParams(
        canvas_width=int(_int("canvas_width", 1200)),
        canvas_height=int(_int("canvas_height", 860)),
        scene_margin_left_px=int(_int("scene_margin_left_px", 64)),
        scene_margin_right_px=int(_int("scene_margin_right_px", 64)),
        scene_margin_top_px=int(_int("scene_margin_top_px", 56)),
        scene_margin_bottom_px=int(_int("scene_margin_bottom_px", 56)),
        reference_panel_height_px=scale_puzzle_px(
            _int("reference_panel_height_px", 294),
            unit_size_scale,
            min_px=180,
        ),
        reference_panel_padding_px=scale_puzzle_px(
            _int("reference_panel_padding_px", 24),
            unit_size_scale,
            min_px=12,
        ),
        source_paper_size_px=scale_puzzle_px(
            _int("source_paper_size_px", 158),
            unit_size_scale,
            min_px=80,
        ),
        source_gap_px=scale_puzzle_px(
            _int("source_gap_px", 120),
            unit_size_scale,
            min_px=48,
        ),
        reference_to_options_gap_px=scale_puzzle_px(
            _int("reference_to_options_gap_px", 34),
            unit_size_scale,
            min_px=18,
        ),
        option_paper_size_px=scale_puzzle_px(
            _int("option_paper_size_px", 158),
            unit_size_scale,
            min_px=80,
        ),
        option_gap_px=scale_puzzle_px(
            _int("option_gap_px", 22),
            unit_size_scale,
            min_px=12,
        ),
        option_row_gap_px=scale_puzzle_px(
            _int("option_row_gap_px", 22),
            unit_size_scale,
            min_px=12,
        ),
        option_label_gap_px=scale_puzzle_px(
            _int("option_label_gap_px", 12),
            unit_size_scale,
            min_px=8,
        ),
        paper_corner_radius_px=scale_puzzle_px(
            _int("paper_corner_radius_px", 18),
            unit_size_scale,
            min_px=8,
        ),
        panel_corner_radius_px=int(_int("panel_corner_radius_px", 28)),
        border_width_px=scale_puzzle_px(
            _int("border_width_px", 3),
            unit_size_scale,
            min_px=2,
        ),
        option_label_font_size_px=scale_puzzle_px(
            _int("option_label_font_size_px", 28),
            unit_size_scale,
            min_px=20,
        ),
        combine_symbol_font_size_px=scale_puzzle_px(
            _int("combine_symbol_font_size_px", 46),
            unit_size_scale,
            min_px=24,
        ),
        panel_fill_rgb=_triple("panel_fill_rgb", (248, 249, 252)),
        paper_fill_rgb=_triple("paper_fill_rgb", (255, 252, 245)),
        paper_shadow_rgb=_triple("paper_shadow_rgb", (236, 230, 215)),
        border_color_rgb=_triple("border_color_rgb", (86, 94, 108)),
        text_color_rgb=_triple("text_color_rgb", (30, 34, 40)),
        text_stroke_rgb=_triple("text_stroke_rgb", (255, 255, 255)),
        mark_fill_rgb=_triple("mark_fill_rgb", (53, 96, 164)),
        mark_outline_rgb=_triple("mark_outline_rgb", (36, 48, 66)),
        mark_shape=str(mark_shape),
        mark_shape_probabilities=dict(mark_shape_probabilities),
        instruction_fill_rgb=_triple("instruction_fill_rgb", (238, 243, 250)),
        unit_size_jitter=dict(unit_size_jitter),
    )


__all__ = [
    "OverlayRenderParams",
    "resolve_render_params",
    "resolve_scene_variant",
]
