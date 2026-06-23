"""Sampling primitives for sequence-strip icon scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Tuple

from ...shared.icon_assets import resolve_icon_pool
from ...shared.icon_style import sample_single_icon_tint

from .rendering import resolve_sequence_canvas_size


@dataclass(frozen=True)
class SequenceIconAppearanceSample:
    """Scene-level icon, tint, cell, and canvas choices for one sequence row."""

    sequence_icon_id: str
    tint_rgb: Tuple[int, int, int]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    cell_box_width_px: int
    cell_box_height_px: int
    canvas_width: int
    canvas_height: int


def sample_sequence_icon_appearance(
    rng,
    *,
    pool_manifest: str,
    render_params: Mapping[str, Any],
    sequence_length: int,
    empty_pool_message: str,
) -> SequenceIconAppearanceSample:
    """Sample reusable visual choices for a single horizontal sequence row."""

    pool = list(resolve_icon_pool(str(pool_manifest)))
    if not pool:
        raise ValueError(str(empty_pool_message))
    sequence_icon_id = str(rng.choice(pool))
    tint_rgb, sampled_palette_rgb = sample_single_icon_tint(
        rng,
        channel_min=int(render_params["color_channel_min"]),
        channel_max=int(render_params["color_channel_max"]),
        anchor_colors=(
            tuple(int(v) for v in render_params["background_color_rgb"]),
            tuple(int(v) for v in render_params["panel_fill_rgb"]),
            tuple(int(v) for v in render_params["panel_border_rgb"]),
            tuple(int(v) for v in render_params["header_text_rgb"]),
        ),
        min_color_distance=float(render_params["min_color_distance"]),
        distance_space=str(render_params["color_distance_space"]),
    )
    cell_box_width_px = int(
        rng.randint(
            int(render_params["cell_box_width_min_px"]),
            int(render_params["cell_box_width_max_px"]),
        )
    )
    cell_box_height_px = int(
        rng.randint(
            int(render_params["cell_box_height_min_px"]),
            int(render_params["cell_box_height_max_px"]),
        )
    )
    canvas_width, canvas_height = resolve_sequence_canvas_size(
        sequence_length=int(sequence_length),
        cell_box_width_px=int(cell_box_width_px),
        cell_box_height_px=int(cell_box_height_px),
        render_params=render_params,
    )
    return SequenceIconAppearanceSample(
        sequence_icon_id=str(sequence_icon_id),
        tint_rgb=tuple(int(value) for value in tint_rgb),
        sampled_palette_rgb=tuple(tuple(int(channel) for channel in color) for color in sampled_palette_rgb),
        cell_box_width_px=int(cell_box_width_px),
        cell_box_height_px=int(cell_box_height_px),
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
    )


__all__ = ["SequenceIconAppearanceSample", "sample_sequence_icon_appearance"]
