"""Default resolution helpers for word-search puzzle tasks."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from trace.tasks.puzzles.shared.unit_size_jitter import (
    resolve_puzzle_unit_size_scale,
    scale_puzzle_px,
)
from trace.tasks.shared.color_distance import coerce_rgb
from trace.tasks.shared.config_defaults import (
    group_default,
)

from .state import WordSearchRenderParams


def get_int_param(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
    fallback: int,
) -> int:
    """Resolve one integer parameter from params/defaults."""

    return int(params.get(str(key), group_default(defaults, str(key), int(fallback))))


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

    low = get_int_param(params, defaults, str(min_key), int(fallback_min))
    high = get_int_param(params, defaults, str(max_key), int(fallback_max))
    if low > high:
        raise ValueError(f"{min_key} must be <= {max_key}")
    return int(low), int(high)


def resolve_render_params(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    instance_seed: int,
) -> WordSearchRenderParams:
    """Resolve word-search render parameters with unit-size jitter."""

    unit_scale, unit_meta = resolve_puzzle_unit_size_scale(
        params,
        defaults,
        instance_seed=int(instance_seed),
        namespace="puzzles.word_search.unit_size",
    )
    return WordSearchRenderParams(
        canvas_width=int(defaults.get("canvas_width", 1180)),
        canvas_height=int(defaults.get("canvas_height", 880)),
        cell_size_px=scale_puzzle_px(
            defaults.get("cell_size_px", 58), unit_scale, min_px=42
        ),
        header_size_px=scale_puzzle_px(
            defaults.get("header_size_px", 46), unit_scale, min_px=32
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
        option_panel_width_px=scale_puzzle_px(
            defaults.get("option_panel_width_px", 270), unit_scale, min_px=190
        ),
        option_panel_height_px=scale_puzzle_px(
            defaults.get("option_panel_height_px", 58), unit_scale, min_px=42
        ),
        option_gap_px=scale_puzzle_px(
            defaults.get("option_gap_px", 12), unit_scale, min_px=8
        ),
        option_font_size_px=scale_puzzle_px(
            defaults.get("option_font_size_px", 20), unit_scale, min_px=15
        ),
        word_chip_height_px=scale_puzzle_px(
            defaults.get("word_chip_height_px", 44), unit_scale, min_px=34
        ),
        word_chip_gap_px=scale_puzzle_px(
            defaults.get("word_chip_gap_px", 10), unit_scale, min_px=6
        ),
        letter_font_size_px=scale_puzzle_px(
            defaults.get("letter_font_size_px", 24), unit_scale, min_px=18
        ),
        index_font_size_px=scale_puzzle_px(
            defaults.get("index_font_size_px", 17), unit_scale, min_px=13
        ),
        panel_fill_rgb=coerce_rgb(defaults.get("panel_fill_rgb"), (250, 251, 253)),
        grid_fill_rgb=coerce_rgb(defaults.get("grid_fill_rgb"), (255, 255, 255)),
        header_fill_rgb=coerce_rgb(defaults.get("header_fill_rgb"), (239, 243, 248)),
        grid_line_rgb=coerce_rgb(defaults.get("grid_line_rgb"), (93, 102, 116)),
        text_rgb=coerce_rgb(defaults.get("text_rgb"), (26, 31, 39)),
        text_stroke_rgb=coerce_rgb(defaults.get("text_stroke_rgb"), (255, 255, 255)),
        option_fill_rgb=coerce_rgb(defaults.get("option_fill_rgb"), (255, 250, 224)),
        option_border_rgb=coerce_rgb(defaults.get("option_border_rgb"), (54, 96, 168)),
        chip_fill_rgb=coerce_rgb(defaults.get("chip_fill_rgb"), (234, 245, 239)),
        chip_border_rgb=coerce_rgb(defaults.get("chip_border_rgb"), (68, 122, 103)),
        unit_size_jitter=dict(unit_meta),
    )


def resize_canvas_to_content(render_params, *, dataset, rng) -> WordSearchRenderParams:
    """Shrink canvas around the grid plus any side-panel content."""

    cell = int(render_params.cell_size_px)
    header = int(render_params.header_size_px)
    padding = int(render_params.panel_padding_px)
    rows = int(dataset.rows)
    cols = int(dataset.cols)
    grid_w = int(header + cols * cell)
    grid_h = int(header + rows * cell)
    side_panel = bool(dataset.option_specs or dataset.word_bank)
    side_width = int(render_params.option_panel_width_px) if side_panel else 0
    side_gap = 38 if side_panel else 0
    content_w = int(grid_w + side_gap + side_width)
    content_h = max(
        grid_h,
        len(dataset.option_specs)
        * (
            int(render_params.option_panel_height_px) + int(render_params.option_gap_px)
        ),
        len(dataset.word_bank)
        * (
            int(render_params.word_chip_height_px) + int(render_params.word_chip_gap_px)
        ),
    )
    panel_w = int(content_w + 2 * padding)
    panel_h = int(content_h + 2 * padding)
    margin = 34
    slack_x = int(rng.randrange(28, 91))
    slack_y = int(rng.randrange(24, 81))
    return replace(
        render_params,
        canvas_width=min(
            int(render_params.canvas_width), max(520, panel_w + 2 * margin + slack_x)
        ),
        canvas_height=min(
            int(render_params.canvas_height), max(460, panel_h + 2 * margin + slack_y)
        ),
    )


__all__ = [
    "get_int_param",
    "get_int_range",
    "resize_canvas_to_content",
    "resolve_render_params",
]
