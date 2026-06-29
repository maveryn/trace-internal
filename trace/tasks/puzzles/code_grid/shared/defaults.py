"""Default resolution helpers for code-grid puzzle tasks."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.puzzles.shared.unit_size_jitter import (
    resolve_puzzle_unit_size_scale,
    scale_puzzle_px,
)
from trace.tasks.shared.color_distance import coerce_rgb
from trace.tasks.shared.config_defaults import (
    group_default,
)

from .state import CodeGridRenderParams


def get_int_range(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
) -> tuple[int, int]:
    """Resolve one inclusive integer range from params/defaults."""

    low = int(
        params.get(str(min_key), group_default(defaults, str(min_key), fallback_min))
    )
    high = int(
        params.get(str(max_key), group_default(defaults, str(max_key), fallback_max))
    )
    if low > high:
        raise ValueError(f"{min_key} must be <= {max_key}")
    return int(low), int(high)


def resolve_render_params(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    instance_seed: int,
) -> CodeGridRenderParams:
    """Resolve code-grid render parameters with unit-size jitter."""

    unit_scale, unit_meta = resolve_puzzle_unit_size_scale(
        params,
        defaults,
        instance_seed=int(instance_seed),
        namespace="puzzles.code_grid.unit_size",
    )
    return CodeGridRenderParams(
        canvas_width=int(defaults.get("canvas_width", 900)),
        canvas_height=int(defaults.get("canvas_height", 700)),
        cell_size_px=scale_puzzle_px(
            defaults.get("cell_size_px", 64), unit_scale, min_px=42
        ),
        header_size_px=scale_puzzle_px(
            defaults.get("header_size_px", 48), unit_scale, min_px=32
        ),
        panel_padding_px=scale_puzzle_px(
            defaults.get("panel_padding_px", 28), unit_scale, min_px=18
        ),
        panel_corner_radius_px=scale_puzzle_px(
            defaults.get("panel_corner_radius_px", 18),
            unit_scale,
            min_px=8,
        ),
        grid_line_width_px=scale_puzzle_px(
            defaults.get("grid_line_width_px", 2), unit_scale, min_px=1
        ),
        letter_font_size_px=scale_puzzle_px(
            defaults.get("letter_font_size_px", 28), unit_scale, min_px=18
        ),
        index_font_size_px=scale_puzzle_px(
            defaults.get("index_font_size_px", 19), unit_scale, min_px=13
        ),
        panel_fill_rgb=coerce_rgb(defaults.get("panel_fill_rgb"), (250, 251, 253)),
        grid_fill_rgb=coerce_rgb(defaults.get("grid_fill_rgb"), (255, 255, 255)),
        header_fill_rgb=coerce_rgb(defaults.get("header_fill_rgb"), (239, 243, 248)),
        grid_line_rgb=coerce_rgb(defaults.get("grid_line_rgb"), (93, 102, 116)),
        text_rgb=coerce_rgb(defaults.get("text_rgb"), (26, 31, 39)),
        text_stroke_rgb=coerce_rgb(defaults.get("text_stroke_rgb"), (255, 255, 255)),
        unit_size_jitter=dict(unit_meta),
    )


def resize_canvas_to_content(
    render_params: CodeGridRenderParams,
    *,
    rows: int,
    cols: int,
    rng,
) -> CodeGridRenderParams:
    """Shrink the canvas around the generated grid while preserving jitter slack."""

    cell = int(render_params.cell_size_px)
    header = int(render_params.header_size_px)
    padding = int(render_params.panel_padding_px)
    margin = 34
    grid_w = int(header + int(cols) * cell)
    grid_h = int(header + int(rows) * cell)
    panel_w = int(grid_w + 2 * padding)
    panel_h = int(grid_h + 2 * padding)
    slack_x = int(rng.randrange(28, 91))
    slack_y = int(rng.randrange(24, 81))
    return CodeGridRenderParams(
        **{
            **render_params.__dict__,
            "canvas_width": min(
                int(render_params.canvas_width),
                max(420, int(panel_w + 2 * margin + slack_x)),
            ),
            "canvas_height": min(
                int(render_params.canvas_height),
                max(380, int(panel_h + 2 * margin + slack_y)),
            ),
        }
    )


__all__ = [
    "get_int_range",
    "resize_canvas_to_content",
    "resolve_render_params",
]
