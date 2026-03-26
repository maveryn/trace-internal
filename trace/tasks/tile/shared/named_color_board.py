"""Shared named-color board sampling and rendering helpers for tile tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...shared.bbox_projection import BBox
from ...shared.color_format import format_named_color_with_hex, rgb_to_hex
from ...shared.config_defaults import resolve_required_float_bounds, resolve_required_int_bounds
from .rectangular_board import (
    RectangularBoardLayout,
    RectangularTileSpec,
    build_rectangular_board_render_spec,
    render_rectangular_tile_board,
    resolve_rectangular_board_layout,
    sample_rectangular_tile_spec,
)
from .tile_colors import NamedColor, sample_named_tile_palette


Coord = Tuple[int, int]


@dataclass(frozen=True)
class RectangularNamedColorBoardTaskDefaults:
    """Stable defaults shared by rectangular named-color board tasks."""

    rows_min: int = 3
    rows_max: int = 7
    cols_min: int = 3
    cols_max: int = 7
    palette_size_min: int = 2
    palette_size_max: int = 6
    short_side_px_min: int = 32
    short_side_px_max: int = 48
    aspect_ratio_min: float = 1.0
    aspect_ratio_max: float = 2.0
    outer_padding_fraction_min: float = 0.08
    outer_padding_fraction_max: float = 0.12
    placement_jitter_fraction_min: float = 0.02
    placement_jitter_fraction_max: float = 0.06


@dataclass(frozen=True)
class RectangularNamedColorBoardScene:
    """One rendered rectangular tile board with named-color fills."""

    rows: int
    cols: int
    palette_size: int
    palette: Sequence[NamedColor]
    board_colors: Mapping[Coord, NamedColor]
    tile_spec: RectangularTileSpec
    layout: RectangularBoardLayout
    image: Image.Image
    bbox_map: Mapping[str, BBox]
    background_meta: Mapping[str, Any]
    post_noise_meta: Mapping[str, Any]


def sample_color_board(
    rng,
    *,
    rows: int,
    cols: int,
    palette: Sequence[NamedColor],
) -> Dict[Coord, NamedColor]:
    """Sample one board while guaranteeing each palette color appears at least once."""
    coords = [(int(row), int(col)) for row in range(int(rows)) for col in range(int(cols))]
    shuffled = list(coords)
    rng.shuffle(shuffled)
    board: Dict[Coord, NamedColor] = {}
    palette_list = [(str(name), (int(rgb[0]), int(rgb[1]), int(rgb[2]))) for name, rgb in palette]
    for coord, color_spec in zip(shuffled, palette_list):
        board[(int(coord[0]), int(coord[1]))] = color_spec
    for coord in shuffled[len(palette_list) :]:
        name, rgb = rng.choice(palette_list)
        board[(int(coord[0]), int(coord[1]))] = (str(name), (int(rgb[0]), int(rgb[1]), int(rgb[2])))
    return board


def _derive_palette_from_board(board_colors: Mapping[Coord, NamedColor]) -> Sequence[NamedColor]:
    """Derive one stable palette ordering from row-major first occurrence."""
    ordered_coords = sorted(
        [(int(row), int(col)) for row, col in board_colors.keys()],
        key=lambda item: (int(item[0]), int(item[1])),
    )
    seen = set()
    palette = []
    for coord in ordered_coords:
        name, rgb = board_colors[coord]
        if str(name) in seen:
            continue
        seen.add(str(name))
        palette.append((str(name), (int(rgb[0]), int(rgb[1]), int(rgb[2]))))
    return tuple(palette)


def build_rectangular_named_color_board_scene(
    instance_seed: int,
    *,
    task_rng,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    background_defaults: Mapping[str, Any],
    noise_defaults: Mapping[str, Any],
    defaults: RectangularNamedColorBoardTaskDefaults,
    rows: int | None = None,
    cols: int | None = None,
    palette: Sequence[NamedColor] | None = None,
    board_colors: Mapping[Coord, NamedColor] | None = None,
) -> RectangularNamedColorBoardScene:
    """Sample or render one rectangular named-color board scene."""
    rows_min, rows_max = resolve_required_int_bounds(
        params,
        generation_defaults,
        min_key="rows_min",
        max_key="rows_max",
        fallback_min=int(defaults.rows_min),
        fallback_max=int(defaults.rows_max),
        context="generation defaults for rectangular named-color board task",
    )
    cols_min, cols_max = resolve_required_int_bounds(
        params,
        generation_defaults,
        min_key="cols_min",
        max_key="cols_max",
        fallback_min=int(defaults.cols_min),
        fallback_max=int(defaults.cols_max),
        context="generation defaults for rectangular named-color board task",
    )
    palette_size_min, palette_size_max = resolve_required_int_bounds(
        params,
        generation_defaults,
        min_key="palette_size_min",
        max_key="palette_size_max",
        fallback_min=int(defaults.palette_size_min),
        fallback_max=int(defaults.palette_size_max),
        context="generation defaults for rectangular named-color board task",
    )
    short_side_px_min, short_side_px_max = resolve_required_int_bounds(
        params,
        rendering_defaults,
        min_key="short_side_px_min",
        max_key="short_side_px_max",
        fallback_min=int(defaults.short_side_px_min),
        fallback_max=int(defaults.short_side_px_max),
        context="rendering defaults for rectangular named-color board task",
    )
    aspect_ratio_min, aspect_ratio_max = resolve_required_float_bounds(
        params,
        rendering_defaults,
        min_key="aspect_ratio_min",
        max_key="aspect_ratio_max",
        fallback_min=float(defaults.aspect_ratio_min),
        fallback_max=float(defaults.aspect_ratio_max),
        context="rendering defaults for rectangular named-color board task",
    )
    outer_padding_fraction_min, outer_padding_fraction_max = resolve_required_float_bounds(
        params,
        rendering_defaults,
        min_key="outer_padding_fraction_min",
        max_key="outer_padding_fraction_max",
        fallback_min=float(defaults.outer_padding_fraction_min),
        fallback_max=float(defaults.outer_padding_fraction_max),
        context="rendering defaults for rectangular named-color board task",
    )
    placement_jitter_fraction_min, placement_jitter_fraction_max = resolve_required_float_bounds(
        params,
        rendering_defaults,
        min_key="placement_jitter_fraction_min",
        max_key="placement_jitter_fraction_max",
        fallback_min=float(defaults.placement_jitter_fraction_min),
        fallback_max=float(defaults.placement_jitter_fraction_max),
        context="rendering defaults for rectangular named-color board task",
    )

    resolved_rows = int(rows) if rows is not None else int(task_rng.randint(int(rows_min), int(rows_max)))
    resolved_cols = int(cols) if cols is not None else int(task_rng.randint(int(cols_min), int(cols_max)))

    if palette is None:
        palette_size = int(task_rng.randint(int(palette_size_min), int(palette_size_max)))
        resolved_palette = sample_named_tile_palette(task_rng, palette_size=int(palette_size))
        if len(resolved_palette) < int(palette_size):
            raise ValueError(f"requested palette_size={palette_size} exceeds available named tile colors")
    else:
        resolved_palette = [
            (str(name), (int(rgb[0]), int(rgb[1]), int(rgb[2])))
            for name, rgb in palette
        ]
        palette_size = int(len(resolved_palette))

    if board_colors is None:
        resolved_board_colors = sample_color_board(
            task_rng,
            rows=int(resolved_rows),
            cols=int(resolved_cols),
            palette=resolved_palette,
        )
    else:
        resolved_board_colors = {
            (int(row), int(col)): (str(name), (int(rgb[0]), int(rgb[1]), int(rgb[2])))
            for (row, col), (name, rgb) in board_colors.items()
        }
        expected_coords = {
            (int(row), int(col))
            for row in range(int(resolved_rows))
            for col in range(int(resolved_cols))
        }
        if set(resolved_board_colors.keys()) != expected_coords:
            raise ValueError("board_colors must cover the full dense rectangular board")
        if palette is None:
            resolved_palette = list(_derive_palette_from_board(resolved_board_colors))
            palette_size = int(len(resolved_palette))

    tile_spec = sample_rectangular_tile_spec(
        task_rng,
        short_side_px_min=int(short_side_px_min),
        short_side_px_max=int(short_side_px_max),
        aspect_ratio_min=float(aspect_ratio_min),
        aspect_ratio_max=float(aspect_ratio_max),
    )
    layout = resolve_rectangular_board_layout(
        task_rng,
        rows=int(resolved_rows),
        cols=int(resolved_cols),
        tile_width_px=int(tile_spec.tile_width_px),
        tile_height_px=int(tile_spec.tile_height_px),
        outer_padding_fraction_min=float(outer_padding_fraction_min),
        outer_padding_fraction_max=float(outer_padding_fraction_max),
        placement_jitter_fraction_min=float(placement_jitter_fraction_min),
        placement_jitter_fraction_max=float(placement_jitter_fraction_max),
    )

    base_image, background_meta = make_background_canvas(
        canvas_width=int(layout.canvas_width_px),
        canvas_height=int(layout.canvas_height_px),
        instance_seed=int(instance_seed),
        params=dict(params),
        default_config=background_defaults,
        fallback_color=(246, 246, 246),
    )
    draw = ImageDraw.Draw(base_image)
    bbox_map = render_rectangular_tile_board(
        draw,
        layout=layout,
        fill_colors_by_coord={
            coord: (int(rgb[0]), int(rgb[1]), int(rgb[2]))
            for coord, (_name, rgb) in resolved_board_colors.items()
        },
    )
    image, post_noise_meta = apply_post_image_noise(
        base_image,
        instance_seed=int(instance_seed),
        params=dict(params),
        default_config=noise_defaults,
    )

    return RectangularNamedColorBoardScene(
        rows=int(resolved_rows),
        cols=int(resolved_cols),
        palette_size=int(palette_size),
        palette=list(resolved_palette),
        board_colors=dict(resolved_board_colors),
        tile_spec=tile_spec,
        layout=layout,
        image=image,
        bbox_map=dict(bbox_map),
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
    )


def build_palette_trace(palette: Sequence[NamedColor]) -> list[dict[str, Any]]:
    """Serialize one deterministic named-color palette for trace metadata."""
    return [
        {
            "name": str(name),
            "rgb": [int(rgb[0]), int(rgb[1]), int(rgb[2])],
            "hex": str(rgb_to_hex(rgb)),
            "label": str(format_named_color_with_hex(name, rgb)),
        }
        for name, rgb in palette
    ]


def build_rectangular_named_color_board_render_spec(scene: RectangularNamedColorBoardScene) -> Dict[str, Any]:
    """Build shared render metadata for one rectangular named-color board scene."""
    return build_rectangular_board_render_spec(
        rows=int(scene.rows),
        cols=int(scene.cols),
        layout=scene.layout,
        tile_spec=scene.tile_spec,
        background_meta=scene.background_meta,
        post_noise_meta=scene.post_noise_meta,
    )


__all__ = [
    "Coord",
    "RectangularNamedColorBoardScene",
    "RectangularNamedColorBoardTaskDefaults",
    "build_palette_trace",
    "build_rectangular_named_color_board_render_spec",
    "build_rectangular_named_color_board_scene",
    "sample_color_board",
]
