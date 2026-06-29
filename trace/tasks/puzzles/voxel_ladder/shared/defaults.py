"""Default resolution helpers for voxel-ladder rendering and sampling."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.seed import spawn_rng
from trace.tasks.puzzles.shared.unit_size_jitter import (
    resolve_puzzle_unit_size_scale,
    scale_puzzle_px,
)
from trace.tasks.shared.config_defaults import group_default

from .state import Color, RenderParams


def to_int(value: Any, fallback: int) -> int:
    """Coerce value to int with a stable fallback."""

    try:
        return int(value)
    except Exception:
        return int(fallback)


def get_int_range(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
) -> tuple[int, int]:
    """Resolve an inclusive integer support from params/defaults."""

    lower = to_int(
        params.get(min_key, group_default(defaults, min_key, fallback_min)),
        fallback_min,
    )
    upper = to_int(
        params.get(max_key, group_default(defaults, max_key, fallback_max)),
        fallback_max,
    )
    if lower > upper:
        raise ValueError(f"{min_key} must be <= {max_key}")
    return int(lower), int(upper)


def normalize_rgb(value: Any, fallback: Color) -> Color:
    """Normalize an RGB-like config value."""

    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return (
            max(0, min(255, to_int(value[0], fallback[0]))),
            max(0, min(255, to_int(value[1], fallback[1]))),
            max(0, min(255, to_int(value[2], fallback[2]))),
        )
    return tuple(int(channel) for channel in fallback)


def rgb_option(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
    fallback: Color,
    *,
    seed: int,
) -> Color:
    """Resolve a color, sampling from `<key>_options` when configured."""

    raw = params.get(str(key), group_default(defaults, str(key), fallback))
    options = params.get(
        f"{key}_options", group_default(defaults, f"{key}_options", None)
    )
    if isinstance(options, list) and options:
        rng = spawn_rng(int(seed), f"voxel_ladder.render.{key}")
        return normalize_rgb(options[int(rng.randrange(len(options)))], fallback)
    return normalize_rgb(raw, fallback)


def resolve_render_params(
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    *,
    instance_seed: int,
) -> RenderParams:
    """Resolve voxel-ladder render parameters from config and params."""

    unit_scale, unit_meta = resolve_puzzle_unit_size_scale(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace="puzzles.voxel_ladder.unit_size",
    )
    cube_width = scale_puzzle_px(
        to_int(
            params.get(
                "cube_width_px", group_default(render_defaults, "cube_width_px", 72)
            ),
            72,
        ),
        unit_scale,
        min_px=50,
    )
    cube_height = max(26, int(round(float(cube_width) * 0.50)))
    cube_depth = max(30, int(round(float(cube_width) * 0.58)))
    return RenderParams(
        canvas_width=max(
            900,
            to_int(
                params.get(
                    "canvas_width",
                    group_default(render_defaults, "canvas_width", 1040),
                ),
                1040,
            ),
        ),
        canvas_height=max(
            720,
            to_int(
                params.get(
                    "canvas_height",
                    group_default(render_defaults, "canvas_height", 800),
                ),
                800,
            ),
        ),
        board_left_px=max(
            40,
            to_int(
                params.get(
                    "board_left_px",
                    group_default(render_defaults, "board_left_px", 72),
                ),
                72,
            ),
        ),
        board_top_px=max(
            40,
            to_int(
                params.get(
                    "board_top_px",
                    group_default(render_defaults, "board_top_px", 76),
                ),
                76,
            ),
        ),
        board_width_px=max(
            580,
            to_int(
                params.get(
                    "board_width_px",
                    group_default(render_defaults, "board_width_px", 860),
                ),
                860,
            ),
        ),
        board_height_px=max(
            560,
            to_int(
                params.get(
                    "board_height_px",
                    group_default(render_defaults, "board_height_px", 640),
                ),
                640,
            ),
        ),
        option_panel_width_px=max(
            240,
            to_int(
                params.get(
                    "option_panel_width_px",
                    group_default(render_defaults, "option_panel_width_px", 300),
                ),
                300,
            ),
        ),
        cube_width_px=int(cube_width),
        cube_height_px=int(cube_height),
        cube_depth_px=int(cube_depth),
        label_font_size_px=max(
            16,
            scale_puzzle_px(
                to_int(
                    params.get(
                        "label_font_size_px",
                        group_default(render_defaults, "label_font_size_px", 26),
                    ),
                    26,
                ),
                unit_scale,
                min_px=16,
            ),
        ),
        option_font_size_px=max(
            16,
            to_int(
                params.get(
                    "option_font_size_px",
                    group_default(render_defaults, "option_font_size_px", 24),
                ),
                24,
            ),
        ),
        panel_fill_rgb=rgb_option(
            params,
            render_defaults,
            "panel_fill_rgb",
            (248, 250, 252),
            seed=int(instance_seed),
        ),
        panel_border_rgb=rgb_option(
            params,
            render_defaults,
            "panel_border_rgb",
            (82, 91, 105),
            seed=int(instance_seed),
        ),
        text_rgb=rgb_option(
            params,
            render_defaults,
            "text_rgb",
            (24, 28, 35),
            seed=int(instance_seed),
        ),
        text_stroke_rgb=rgb_option(
            params,
            render_defaults,
            "text_stroke_rgb",
            (255, 255, 255),
            seed=int(instance_seed),
        ),
        neutral_top_rgb=rgb_option(
            params,
            render_defaults,
            "neutral_top_rgb",
            (179, 185, 192),
            seed=int(instance_seed),
        ),
        start_top_rgb=rgb_option(
            params,
            render_defaults,
            "start_top_rgb",
            (86, 128, 235),
            seed=int(instance_seed),
        ),
        goal_top_rgb=rgb_option(
            params,
            render_defaults,
            "goal_top_rgb",
            (236, 92, 88),
            seed=int(instance_seed),
        ),
        checkpoint_top_rgb=rgb_option(
            params,
            render_defaults,
            "checkpoint_top_rgb",
            (96, 222, 111),
            seed=int(instance_seed),
        ),
        ladder_rgb=rgb_option(
            params,
            render_defaults,
            "ladder_rgb",
            (33, 37, 42),
            seed=int(instance_seed),
        ),
        shadow_rgb=rgb_option(
            params,
            render_defaults,
            "shadow_rgb",
            (222, 226, 232),
            seed=int(instance_seed),
        ),
        unit_size_scale=float(unit_scale),
        unit_size_jitter=dict(unit_meta),
    )
