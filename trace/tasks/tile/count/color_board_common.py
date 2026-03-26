"""Shared rectangular color-board scaffolding for tile/count tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...shared.bbox_projection import BBox
from ...shared.color_format import format_named_color_with_hex, rgb_to_hex
from ...shared.config_defaults import resolve_required_float_bounds, resolve_required_int_bounds
from ...shared.prompt_json_example import build_prompt_json_examples
from ..shared.rectangular_board import (
    RectangularBoardLayout,
    RectangularTileSpec,
    render_rectangular_tile_board,
    resolve_rectangular_board_layout,
    sample_rectangular_tile_spec,
)
from ..shared.tile_colors import NamedColor, sample_named_tile_palette
from ..shared.tile_scene import build_tile_cell_entities


Coord = Tuple[int, int]


@dataclass(frozen=True)
class RectangularColorBoardTaskDefaults:
    """Stable defaults shared by rectangular color-board count tasks."""

    rows_min: int = 3
    rows_max: int = 8
    cols_min: int = 3
    cols_max: int = 8
    palette_size_min: int = 3
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
class RectangularColorBoardScene:
    """One rendered rectangular tile board with named colors."""

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


def build_rectangular_color_board_scene(
    instance_seed: int,
    *,
    task_rng,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    background_defaults: Mapping[str, Any],
    noise_defaults: Mapping[str, Any],
    defaults: RectangularColorBoardTaskDefaults,
) -> RectangularColorBoardScene:
    """Sample and render one rectangular named-color board."""
    rows_min, rows_max = resolve_required_int_bounds(
        params,
        generation_defaults,
        min_key="rows_min",
        max_key="rows_max",
        fallback_min=int(defaults.rows_min),
        fallback_max=int(defaults.rows_max),
        context="generation defaults for rectangular color-board task",
    )
    cols_min, cols_max = resolve_required_int_bounds(
        params,
        generation_defaults,
        min_key="cols_min",
        max_key="cols_max",
        fallback_min=int(defaults.cols_min),
        fallback_max=int(defaults.cols_max),
        context="generation defaults for rectangular color-board task",
    )
    palette_size_min, palette_size_max = resolve_required_int_bounds(
        params,
        generation_defaults,
        min_key="palette_size_min",
        max_key="palette_size_max",
        fallback_min=int(defaults.palette_size_min),
        fallback_max=int(defaults.palette_size_max),
        context="generation defaults for rectangular color-board task",
    )
    short_side_px_min, short_side_px_max = resolve_required_int_bounds(
        params,
        rendering_defaults,
        min_key="short_side_px_min",
        max_key="short_side_px_max",
        fallback_min=int(defaults.short_side_px_min),
        fallback_max=int(defaults.short_side_px_max),
        context="rendering defaults for rectangular color-board task",
    )
    aspect_ratio_min, aspect_ratio_max = resolve_required_float_bounds(
        params,
        rendering_defaults,
        min_key="aspect_ratio_min",
        max_key="aspect_ratio_max",
        fallback_min=float(defaults.aspect_ratio_min),
        fallback_max=float(defaults.aspect_ratio_max),
        context="rendering defaults for rectangular color-board task",
    )
    outer_padding_fraction_min, outer_padding_fraction_max = resolve_required_float_bounds(
        params,
        rendering_defaults,
        min_key="outer_padding_fraction_min",
        max_key="outer_padding_fraction_max",
        fallback_min=float(defaults.outer_padding_fraction_min),
        fallback_max=float(defaults.outer_padding_fraction_max),
        context="rendering defaults for rectangular color-board task",
    )
    placement_jitter_fraction_min, placement_jitter_fraction_max = resolve_required_float_bounds(
        params,
        rendering_defaults,
        min_key="placement_jitter_fraction_min",
        max_key="placement_jitter_fraction_max",
        fallback_min=float(defaults.placement_jitter_fraction_min),
        fallback_max=float(defaults.placement_jitter_fraction_max),
        context="rendering defaults for rectangular color-board task",
    )

    rows = int(task_rng.randint(int(rows_min), int(rows_max)))
    cols = int(task_rng.randint(int(cols_min), int(cols_max)))
    palette_size = int(task_rng.randint(int(palette_size_min), int(palette_size_max)))
    palette = sample_named_tile_palette(task_rng, palette_size=int(palette_size))
    if len(palette) < int(palette_size):
        raise ValueError(f"requested palette_size={palette_size} exceeds available named tile colors")

    board_colors = sample_color_board(
        task_rng,
        rows=int(rows),
        cols=int(cols),
        palette=palette,
    )
    tile_spec = sample_rectangular_tile_spec(
        task_rng,
        short_side_px_min=int(short_side_px_min),
        short_side_px_max=int(short_side_px_max),
        aspect_ratio_min=float(aspect_ratio_min),
        aspect_ratio_max=float(aspect_ratio_max),
    )
    layout = resolve_rectangular_board_layout(
        task_rng,
        rows=int(rows),
        cols=int(cols),
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
            for coord, (_name, rgb) in board_colors.items()
        },
    )
    image, post_noise_meta = apply_post_image_noise(
        base_image,
        instance_seed=int(instance_seed),
        params=dict(params),
        default_config=noise_defaults,
    )

    return RectangularColorBoardScene(
        rows=int(rows),
        cols=int(cols),
        palette_size=int(palette_size),
        palette=list(palette),
        board_colors=dict(board_colors),
        tile_spec=tile_spec,
        layout=layout,
        image=image,
        bbox_map=dict(bbox_map),
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
    )


def build_palette_trace(palette: Sequence[NamedColor]) -> List[Dict[str, Any]]:
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


def build_rectangular_color_board_render_spec(scene: RectangularColorBoardScene) -> Dict[str, Any]:
    """Build shared render metadata for one rectangular color-board scene."""
    return {
        "coord_space": "tile_grid",
        "tiling_type": "rectangular_tiling",
        "canvas_width_px": int(scene.layout.canvas_width_px),
        "canvas_height_px": int(scene.layout.canvas_height_px),
        "rows": int(scene.rows),
        "cols": int(scene.cols),
        "tile_width_px": int(scene.layout.tile_width_px),
        "tile_height_px": int(scene.layout.tile_height_px),
        "board_origin_px": [int(scene.layout.board_origin_x_px), int(scene.layout.board_origin_y_px)],
        "board_size_px": [int(scene.layout.board_width_px), int(scene.layout.board_height_px)],
        "coordinate_gutters_px": {
            "left": int(scene.layout.left_label_gutter_px),
            "top": int(scene.layout.top_label_gutter_px),
        },
        "outer_padding_px": {
            "x": int(scene.layout.outer_padding_x_px),
            "y": int(scene.layout.outer_padding_y_px),
        },
        "placement_offset_px": {
            "x": int(scene.layout.placement_offset_x_px),
            "y": int(scene.layout.placement_offset_y_px),
        },
        "label_style": {
            "font_size_px": int(scene.layout.label_font_size_px),
            "stroke_width_px": int(scene.layout.label_stroke_width_px),
        },
        "tile_outline_width_px": int(scene.layout.tile_outline_width_px),
        "tile_aspect_ratio": round(float(scene.tile_spec.aspect_ratio), 6),
        "tile_orientation": str(scene.tile_spec.orientation),
        "background_style": dict(scene.background_meta),
        "post_image_noise": dict(scene.post_noise_meta),
    }


def build_color_board_scene_entities(
    scene: RectangularColorBoardScene,
    *,
    query_color_name: str,
    extra_attrs_by_coord: Mapping[Coord, Mapping[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    """Build scene entities for one rectangular color board with query annotations."""
    extra_attrs = dict(extra_attrs_by_coord) if isinstance(extra_attrs_by_coord, Mapping) else {}
    attrs_by_coord: Dict[Coord, Dict[str, Any]] = {}
    for coord, (name, rgb) in scene.board_colors.items():
        attrs: Dict[str, Any] = {
            "color_name": str(name),
            "fill_rgb": [int(rgb[0]), int(rgb[1]), int(rgb[2])],
            "is_query_match": bool(str(name) == str(query_color_name)),
        }
        per_coord = extra_attrs.get(coord, {})
        if isinstance(per_coord, Mapping):
            attrs.update({str(key): value for key, value in per_coord.items()})
        attrs_by_coord[(int(coord[0]), int(coord[1]))] = attrs
    return build_tile_cell_entities(
        rows=int(scene.rows),
        cols=int(scene.cols),
        attrs_by_coord=attrs_by_coord,
    )


def resolve_prompt_json_examples(
    prompt_defaults: Mapping[str, Any],
    *,
    evidence_value: Any,
    answer_type: str,
) -> Tuple[str, str]:
    """Resolve task-specific prompt examples with generated fallback."""
    json_example = prompt_defaults.get("json_example")
    json_example_answer_only = prompt_defaults.get("json_example_answer_only")
    if isinstance(json_example, str) and json_example.strip() and isinstance(json_example_answer_only, str) and json_example_answer_only.strip():
        return str(json_example), str(json_example_answer_only)
    generated_json_example, generated_json_example_answer_only = build_prompt_json_examples(
        evidence_value=evidence_value,
        answer_type=str(answer_type),
    )
    if not (isinstance(json_example, str) and json_example.strip()):
        json_example = str(generated_json_example)
    if not (isinstance(json_example_answer_only, str) and json_example_answer_only.strip()):
        json_example_answer_only = str(generated_json_example_answer_only)
    return str(json_example), str(json_example_answer_only)


__all__ = [
    "Coord",
    "RectangularColorBoardScene",
    "RectangularColorBoardTaskDefaults",
    "build_color_board_scene_entities",
    "build_palette_trace",
    "build_rectangular_color_board_render_spec",
    "build_rectangular_color_board_scene",
    "resolve_prompt_json_examples",
    "sample_color_board",
]
