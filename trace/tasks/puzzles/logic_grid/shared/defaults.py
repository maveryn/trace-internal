"""Config-resolution helpers for logic-grid puzzle tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.sampling import support_probability_map, weighted_support_choice
from trace.core.seed import spawn_rng
from trace.tasks.puzzles.shared.unit_size_jitter import (
    resolve_puzzle_unit_size_scale,
    scale_puzzle_px,
)
from trace.tasks.shared.config_defaults import group_default, resolve_required_int_bounds
from trace.tasks.shared.render_variation import resolve_render_int, resolve_render_rgb

from .state import DEFAULTS, SCENE_VARIANTS, LogicGridDefaults, LogicGridRenderParams


def resolve_render_params(
    params: Mapping[str, Any],
    *,
    rendering_defaults: Mapping[str, Any],
    instance_seed: int,
) -> LogicGridRenderParams:
    """Resolve one render-parameter record from scene defaults and params."""

    def _int(key: str, fallback: int) -> int:
        return resolve_render_int(
            params,
            rendering_defaults,
            str(key),
            int(fallback),
            instance_seed=int(instance_seed),
            namespace="puzzles.logic_grid.render",
        )

    def _triple(key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        return resolve_render_rgb(
            params,
            rendering_defaults,
            str(key),
            fallback,
            instance_seed=int(instance_seed),
            namespace="puzzles.logic_grid.render",
        )

    unit_scale, unit_meta = resolve_puzzle_unit_size_scale(
        params,
        rendering_defaults,
        instance_seed=int(instance_seed),
        namespace="puzzles.logic_grid.unit_size",
    )
    defaults = DEFAULTS
    return LogicGridRenderParams(
        canvas_width=int(_int("canvas_width", defaults.canvas_width)),
        canvas_height=int(_int("canvas_height", defaults.canvas_height)),
        scene_margin_left_px=int(_int("scene_margin_left_px", defaults.scene_margin_left_px)),
        scene_margin_right_px=int(_int("scene_margin_right_px", defaults.scene_margin_right_px)),
        scene_margin_top_px=int(_int("scene_margin_top_px", defaults.scene_margin_top_px)),
        scene_margin_bottom_px=int(_int("scene_margin_bottom_px", defaults.scene_margin_bottom_px)),
        cell_size_px=scale_puzzle_px(_int("cell_size_px", defaults.cell_size_px), unit_scale, min_px=20),
        cell_gap_px=scale_puzzle_px(_int("cell_gap_px", defaults.cell_gap_px), unit_scale, min_px=2),
        board_panel_padding_px=scale_puzzle_px(
            _int("board_panel_padding_px", defaults.board_panel_padding_px),
            unit_scale,
            min_px=10,
        ),
        board_to_options_gap_px=scale_puzzle_px(
            _int("board_to_options_gap_px", defaults.board_to_options_gap_px),
            unit_scale,
            min_px=22,
        ),
        option_panel_width_px=int(_int("option_panel_width_px", defaults.option_panel_width_px)),
        option_panel_height_px=int(_int("option_panel_height_px", defaults.option_panel_height_px)),
        option_gap_px=int(_int("option_gap_px", defaults.option_gap_px)),
        option_symbol_box_size_px=scale_puzzle_px(
            _int("option_symbol_box_size_px", defaults.option_symbol_box_size_px),
            unit_scale,
            min_px=46,
        ),
        option_label_gap_px=int(_int("option_label_gap_px", defaults.option_label_gap_px)),
        slot_corner_radius_px=scale_puzzle_px(
            _int("slot_corner_radius_px", defaults.slot_corner_radius_px),
            unit_scale,
            min_px=6,
        ),
        border_width_px=int(_int("border_width_px", defaults.border_width_px)),
        panel_corner_radius_px=int(_int("panel_corner_radius_px", defaults.panel_corner_radius_px)),
        value_font_size_px=scale_puzzle_px(
            _int("value_font_size_px", defaults.value_font_size_px),
            unit_scale,
            min_px=18,
        ),
        option_label_font_size_px=int(_int("option_label_font_size_px", defaults.option_label_font_size_px)),
        panel_fill_rgb=_triple("panel_fill_rgb", (248, 249, 252)),
        cell_fill_rgb=_triple("cell_fill_rgb", (252, 252, 255)),
        unknown_cell_fill_rgb=_triple("unknown_cell_fill_rgb", (242, 246, 255)),
        option_panel_fill_rgb=_triple("option_panel_fill_rgb", (251, 251, 255)),
        option_symbol_fill_rgb=_triple("option_symbol_fill_rgb", (252, 252, 255)),
        border_color_rgb=_triple("border_color_rgb", (86, 94, 108)),
        text_color_rgb=_triple("text_color_rgb", (30, 34, 40)),
        text_stroke_rgb=_triple("text_stroke_rgb", (255, 255, 255)),
        accent_color_rgb=_triple("accent_color_rgb", (54, 102, 180)),
        unit_size_jitter=dict(unit_meta),
    )


def resolve_board_size_bounds(
    params: Mapping[str, Any],
    *,
    generation_defaults: Mapping[str, Any],
    defaults: LogicGridDefaults = DEFAULTS,
) -> Tuple[int, int]:
    """Resolve inclusive board-size bounds for one logic-grid task."""

    return resolve_required_int_bounds(
        params,
        generation_defaults,
        min_key="board_size_min",
        max_key="board_size_max",
        fallback_min=int(defaults.board_size_min),
        fallback_max=int(defaults.board_size_max),
        context="logic-grid board-size bounds",
    )


def resolve_option_count(
    params: Mapping[str, Any],
    *,
    generation_defaults: Mapping[str, Any],
    defaults: LogicGridDefaults = DEFAULTS,
) -> int:
    """Resolve the fixed option count used by logic-grid option panels."""

    value = int(params.get("option_count", group_default(generation_defaults, "option_count", defaults.option_count)))
    if int(value) != 6:
        raise ValueError("logic-grid tasks require exactly six options")
    return int(value)


def sample_board_size(
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    defaults: LogicGridDefaults = DEFAULTS,
) -> tuple[int, Dict[str, float]]:
    """Sample board size from the configured inclusive support."""

    low, high = resolve_board_size_bounds(
        params,
        generation_defaults=generation_defaults,
        defaults=defaults,
    )
    explicit = params.get("board_size")
    support = tuple(range(int(low), int(high) + 1))
    if explicit is not None:
        selected = int(explicit)
        if selected not in set(support):
            raise ValueError(f"board_size must fall inside [{low}, {high}]")
        return int(selected), support_probability_map(support, selected=selected, sort_keys=True)
    rng = spawn_rng(int(instance_seed), str(namespace))
    selected, probabilities = weighted_support_choice(rng, support, sort_keys=True)
    return int(selected), dict(probabilities)


def sample_scene_variant(
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    support: Sequence[str] = SCENE_VARIANTS,
) -> tuple[str, Dict[str, float]]:
    """Sample nonsemantic scene chrome from explicit scene-variant support."""

    variants = tuple(str(value) for value in support)
    explicit = params.get("scene_variant")
    if explicit is not None:
        selected = str(explicit)
        if selected not in set(variants):
            raise ValueError(f"unsupported scene_variant: {selected}")
        return selected, support_probability_map(variants, selected=selected)
    raw_weights = generation_defaults.get("scene_variant_weights")
    weights = raw_weights if isinstance(raw_weights, Mapping) else None
    rng = spawn_rng(int(instance_seed), str(namespace))
    selected, probabilities = weighted_support_choice(rng, variants, weights=weights)
    return str(selected), dict(probabilities)
