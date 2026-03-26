"""Single-board rectangular-tile color-count task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import pixel_anchor_map_from_bboxes
from ...shared.color_format import format_named_color_with_hex, rgb_to_hex
from ...shared.config_defaults import (
    required_group_defaults,
    resolve_required_float_bounds,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.rectangular_board import (
    render_rectangular_tile_board,
    resolve_rectangular_board_layout,
    sample_rectangular_tile_spec,
)
from ..shared.tile_colors import sample_named_tile_palette
from ..shared.tile_evidence import coordinate_set_evidence_artifacts, sort_coords_row_major
from ..shared.tile_scene import build_tile_cell_entities
from .background_defaults import POST_IMAGE_BACKGROUND_DEFAULTS
from .noise_defaults import POST_IMAGE_NOISE_DEFAULTS


Coord = Tuple[int, int]


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable defaults for the rectangular tile color-count task."""

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


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("tile", "count")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, dict) else {},
    task_id="task_tile_count_color_count",
)


def _sample_color_board(
    rng,
    *,
    rows: int,
    cols: int,
    palette: Sequence[Tuple[str, Tuple[int, int, int]]],
) -> Dict[Coord, Tuple[str, Tuple[int, int, int]]]:
    """Sample one board while guaranteeing each palette color appears at least once."""
    coords = [(int(row), int(col)) for row in range(int(rows)) for col in range(int(cols))]
    shuffled = list(coords)
    rng.shuffle(shuffled)
    board: Dict[Coord, Tuple[str, Tuple[int, int, int]]] = {}
    palette_list = [(str(name), (int(rgb[0]), int(rgb[1]), int(rgb[2]))) for name, rgb in palette]
    for coord, color_spec in zip(shuffled, palette_list):
        board[(int(coord[0]), int(coord[1]))] = color_spec
    for coord in shuffled[len(palette_list) :]:
        name, rgb = rng.choice(palette_list)
        board[(int(coord[0]), int(coord[1]))] = (str(name), (int(rgb[0]), int(rgb[1]), int(rgb[2])))
    return board


@register_task
class TileColorCountTask:
    """Count the number of tiles matching a queried color."""

    task_id = "task_tile_count_color_count"
    domain = "tile"
    task_group = "count"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        rows_min, rows_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="rows_min",
            max_key="rows_max",
            fallback_min=int(_DEFAULTS.rows_min),
            fallback_max=int(_DEFAULTS.rows_max),
            context=f"generation defaults for {self.task_id}",
        )
        cols_min, cols_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="cols_min",
            max_key="cols_max",
            fallback_min=int(_DEFAULTS.cols_min),
            fallback_max=int(_DEFAULTS.cols_max),
            context=f"generation defaults for {self.task_id}",
        )
        palette_size_min, palette_size_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="palette_size_min",
            max_key="palette_size_max",
            fallback_min=int(_DEFAULTS.palette_size_min),
            fallback_max=int(_DEFAULTS.palette_size_max),
            context=f"generation defaults for {self.task_id}",
        )
        short_side_px_min, short_side_px_max = resolve_required_int_bounds(
            params,
            _RENDER_DEFAULTS,
            min_key="short_side_px_min",
            max_key="short_side_px_max",
            fallback_min=int(_DEFAULTS.short_side_px_min),
            fallback_max=int(_DEFAULTS.short_side_px_max),
            context=f"rendering defaults for {self.task_id}",
        )
        aspect_ratio_min, aspect_ratio_max = resolve_required_float_bounds(
            params,
            _RENDER_DEFAULTS,
            min_key="aspect_ratio_min",
            max_key="aspect_ratio_max",
            fallback_min=float(_DEFAULTS.aspect_ratio_min),
            fallback_max=float(_DEFAULTS.aspect_ratio_max),
            context=f"rendering defaults for {self.task_id}",
        )
        outer_padding_fraction_min, outer_padding_fraction_max = resolve_required_float_bounds(
            params,
            _RENDER_DEFAULTS,
            min_key="outer_padding_fraction_min",
            max_key="outer_padding_fraction_max",
            fallback_min=float(_DEFAULTS.outer_padding_fraction_min),
            fallback_max=float(_DEFAULTS.outer_padding_fraction_max),
            context=f"rendering defaults for {self.task_id}",
        )
        placement_jitter_fraction_min, placement_jitter_fraction_max = resolve_required_float_bounds(
            params,
            _RENDER_DEFAULTS,
            min_key="placement_jitter_fraction_min",
            max_key="placement_jitter_fraction_max",
            fallback_min=float(_DEFAULTS.placement_jitter_fraction_min),
            fallback_max=float(_DEFAULTS.placement_jitter_fraction_max),
            context=f"rendering defaults for {self.task_id}",
        )

        task_rng = spawn_rng(instance_seed, "task")
        rows = int(task_rng.randint(int(rows_min), int(rows_max)))
        cols = int(task_rng.randint(int(cols_min), int(cols_max)))
        palette_size = int(task_rng.randint(int(palette_size_min), int(palette_size_max)))
        palette = sample_named_tile_palette(task_rng, palette_size=int(palette_size))
        if len(palette) < int(palette_size):
            raise ValueError(f"requested palette_size={palette_size} exceeds available named tile colors")

        board_colors = _sample_color_board(
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

        query_color_name, query_color_rgb = task_rng.choice(list(palette))
        query_color_hex = rgb_to_hex(query_color_rgb)
        query_color_label = format_named_color_with_hex(query_color_name, query_color_rgb)
        matching_coords = sort_coords_row_major(
            [
                (int(row), int(col))
                for (row, col), (name, _rgb) in board_colors.items()
                if str(name) == str(query_color_name)
            ]
        )
        if not matching_coords:
            raise RuntimeError("sampled query color must appear at least once on the board")

        base_image, background_meta = make_background_canvas(
            canvas_width=int(layout.canvas_width_px),
            canvas_height=int(layout.canvas_height_px),
            instance_seed=instance_seed,
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
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
            instance_seed=instance_seed,
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        evidence_artifacts = coordinate_set_evidence_artifacts(
            coords=matching_coords,
            bbox_map=bbox_map,
        )
        answer_value = int(len(matching_coords))

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "task_family_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "evidence_hint",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_bundle_id = str(prompt_defaults["bundle_id"])
        prompt_task_family_key = str(prompt_defaults["task_family_key"])
        prompt_task_key = str(prompt_defaults["task_key"])
        json_example, json_example_answer_only = build_prompt_json_examples(
            evidence_value=[[0, 1], [1, 0], [1, 2]],
            answer_type="integer",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=prompt_bundle_id,
            task_family_key=prompt_task_family_key,
            task_key=prompt_task_key,
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "rows": int(rows),
                "cols": int(cols),
                "query_color": str(query_color_label),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=instance_seed,
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        palette_trace = [
            {
                "name": str(name),
                "rgb": [int(rgb[0]), int(rgb[1]), int(rgb[2])],
                "hex": str(rgb_to_hex(rgb)),
                "label": str(format_named_color_with_hex(name, rgb)),
            }
            for name, rgb in palette
        ]
        counts_by_color = {
            str(name): sum(1 for cell_name, _rgb in board_colors.values() if str(cell_name) == str(name))
            for name, _rgb in palette
        }
        scene_entities = build_tile_cell_entities(
            rows=int(rows),
            cols=int(cols),
            attrs_by_coord={
                coord: {
                    "color_name": str(name),
                    "fill_rgb": [int(rgb[0]), int(rgb[1]), int(rgb[2])],
                    "is_query_match": bool(str(name) == str(query_color_name)),
                }
                for coord, (name, rgb) in board_colors.items()
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "rectangular_tile_board",
                "entities": scene_entities,
                "relations": {},
            },
            "query_spec": {
                "task_variant": "color_count",
                "template_id": "color_count_v1",
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "dsl_program": [
                    {"out": "cells", "op": "select", "entity_type": "tile_cell"},
                    {
                        "out": "query_cells",
                        "op": "filter",
                        "in": "cells",
                        "predicate": {"color_name": str(query_color_name)},
                    },
                    {
                        "out": "evidence",
                        "op": "project_coords",
                        "in": "query_cells",
                        "coord_space": "tile_grid",
                        "coord_type": "grid_point_set",
                        "ordering": "row_major",
                    },
                    {"out": "answer", "op": "count", "in": "query_cells"},
                ],
            },
            "render_spec": {
                "coord_space": "tile_grid",
                "tiling_type": "rectangular_tiling",
                "canvas_width_px": int(layout.canvas_width_px),
                "canvas_height_px": int(layout.canvas_height_px),
                "rows": int(rows),
                "cols": int(cols),
                "tile_width_px": int(layout.tile_width_px),
                "tile_height_px": int(layout.tile_height_px),
                "board_origin_px": [int(layout.board_origin_x_px), int(layout.board_origin_y_px)],
                "board_size_px": [int(layout.board_width_px), int(layout.board_height_px)],
                "coordinate_gutters_px": {
                    "left": int(layout.left_label_gutter_px),
                    "top": int(layout.top_label_gutter_px),
                },
                "outer_padding_px": {
                    "x": int(layout.outer_padding_x_px),
                    "y": int(layout.outer_padding_y_px),
                },
                "placement_offset_px": {
                    "x": int(layout.placement_offset_x_px),
                    "y": int(layout.placement_offset_y_px),
                },
                "label_style": {
                    "font_size_px": int(layout.label_font_size_px),
                    "stroke_width_px": int(layout.label_stroke_width_px),
                },
                "tile_outline_width_px": int(layout.tile_outline_width_px),
                "tile_aspect_ratio": round(float(tile_spec.aspect_ratio), 6),
                "tile_orientation": str(tile_spec.orientation),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": pixel_anchor_map_from_bboxes(bbox_map),
            },
            "execution_trace": {
                "task_variant": "color_count",
                "rows": int(rows),
                "cols": int(cols),
                "palette": list(palette_trace),
                "palette_size": int(palette_size),
                "query_color_name": str(query_color_name),
                "query_color_rgb": [int(query_color_rgb[0]), int(query_color_rgb[1]), int(query_color_rgb[2])],
                "query_color_hex": str(query_color_hex),
                "query_color_label": str(query_color_label),
                "counts_by_color_name": dict(counts_by_color),
                "matching_coords": [[int(row), int(col)] for row, col in matching_coords],
                "matching_ids": list(evidence_artifacts["witness_symbolic"]["ids"]),
                "answer_value": int(answer_value),
            },
            "witness_symbolic": dict(evidence_artifacts["witness_symbolic"]),
            "projected_evidence": dict(evidence_artifacts["projected_evidence"]),
        }

        board_cell_count = int(rows) * int(cols)
        complexity = TaskComplexity(
            complexity_score=min(
                1.0,
                max(
                    0.0,
                    (
                        (float(board_cell_count) / 64.0)
                        + (float(palette_size) / 6.0)
                        + (float(answer_value) / float(max(1, board_cell_count)))
                    )
                    / 3.0,
                ),
            ),
            complexity_components={
                "rows": int(rows),
                "cols": int(cols),
                "palette_size": int(palette_size),
                "answer_count": int(answer_value),
                "match_fraction": float(answer_value) / float(max(1, board_cell_count)),
            },
        )

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(answer_value)),
            evidence_gt=TypedValue(
                type=str(evidence_artifacts["evidence_type"]),
                value=list(evidence_artifacts["evidence_value"]),
            ),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant="color_count",
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
