"""Tile shortest-path task aligned to the shared rectangular tile-board contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from PIL import ImageDraw

from trace.core.seed import spawn_rng
from trace.core.scene_config import get_scene_defaults
from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.shared.bbox_projection import pixel_anchor_map_from_bboxes
from trace.tasks.shared.color_format import format_named_color_with_hex
from trace.tasks.shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_required_float_bounds,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_json_example import resolve_prompt_json_examples
from .shared.grid_graph import cell_id
from .shared.board_size_sampling import resolve_square_board_dimensions
from .shared.maze_sampling import sample_unique_shortest_path_maze, validate_open_path_entities
from .shared.maze_scene import open_adjacency_by_cell
from .shared.rectangular_board import (
    RectangularTileSpec,
    build_rectangular_board_background,
    build_rectangular_board_render_spec,
    rectangular_board_label_font_family,
    rectangular_board_tile_style,
    render_rectangular_tile_board,
    resolve_rectangular_board_layout,
)
from .shared.tile_colors import named_tile_color
from .shared.tile_annotation import coordinate_path_annotation_artifacts
from .shared.tile_scene import build_tile_cell_entities
from .shared.visual_defaults import load_tile_background_defaults, load_tile_noise_defaults


Coord = Tuple[int, int]

_OBSTACLE_RGB = (0, 0, 0)
_OPEN_RGB = (250, 250, 250)
_START_RGB = named_tile_color("green")
_GOAL_RGB = named_tile_color("red")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable defaults for the tile shortest-path task."""

    rows: int = 7
    cols: int = 7
    board_size_min: int = 7
    board_size_max: int = 7
    target_shortest_len_min: int = 4
    target_shortest_len_max: int = 13
    obstacle_prob_min: float = 0.16
    obstacle_prob_max: float = 0.36
    short_side_px_min: int = 32
    short_side_px_max: int = 48
    aspect_ratio_min: float = 1.0
    aspect_ratio_max: float = 1.0
    outer_padding_fraction_min: float = 0.08
    outer_padding_fraction_max: float = 0.12
    placement_jitter_fraction_min: float = 0.02
    placement_jitter_fraction_max: float = 0.06


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_scene_defaults("puzzles", "cell_board_path")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, dict) else {},
    task_id="cell_board_shortest_path_internal",
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_tile_background_defaults(scene_id="path")
POST_IMAGE_NOISE_DEFAULTS = load_tile_noise_defaults(scene_id="path", apply_prob=0.0)


def _sample_square_tile_spec(rng, *, short_side_px_min: int, short_side_px_max: int) -> RectangularTileSpec:
    """Return one square tile spec for equal-cost grid-path rendering."""
    short_side_px = int(rng.randint(int(short_side_px_min), int(short_side_px_max)))
    return RectangularTileSpec(
        short_side_px=int(short_side_px),
        aspect_ratio=1.0,
        orientation="square",
        tile_width_px=int(short_side_px),
        tile_height_px=int(short_side_px),
    )


def _build_fill_colors_by_coord(
    *,
    rows: int,
    cols: int,
    blocked,
    start: Coord,
    goal: Coord,
) -> Dict[Coord, Tuple[int, int, int]]:
    """Build per-cell fill colors for one shortest-path board scene."""
    fill_colors: Dict[Coord, Tuple[int, int, int]] = {}
    for row in range(int(rows)):
        for col in range(int(cols)):
            coord = (int(row), int(col))
            if bool(blocked[row][col]):
                fill = _OBSTACLE_RGB
            elif coord == (int(start[0]), int(start[1])):
                fill = _START_RGB
            elif coord == (int(goal[0]), int(goal[1])):
                fill = _GOAL_RGB
            else:
                fill = _OPEN_RGB
            fill_colors[coord] = tuple(int(channel) for channel in fill)
    return fill_colors


class TileShortestPathTask:
    """Return shortest-path length with coordinate-grounded path annotation."""

    task_id = "cell_board_shortest_path_internal"
    domain = "puzzles"
    scene_id = "cell_board_path"
    default_dataset_enabled = False

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        rows, cols, board_metadata = resolve_square_board_dimensions(
            params=params,
            generation_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            fallback_rows=int(_DEFAULTS.rows),
            fallback_cols=int(_DEFAULTS.cols),
            fallback_board_size_min=int(_DEFAULTS.board_size_min),
            fallback_board_size_max=int(_DEFAULTS.board_size_max),
        )
        target_shortest_len_min = int(
            params.get(
                "target_shortest_len_min",
                group_default(_GEN_DEFAULTS, "target_shortest_len_min", _DEFAULTS.target_shortest_len_min),
            )
        )
        target_shortest_len_max = int(
            params.get(
                "target_shortest_len_max",
                group_default(_GEN_DEFAULTS, "target_shortest_len_max", _DEFAULTS.target_shortest_len_max),
            )
        )
        if int(target_shortest_len_min) > int(target_shortest_len_max):
            raise ValueError("target_shortest_len_min must be <= target_shortest_len_max")
        obstacle_prob_min, obstacle_prob_max = resolve_required_float_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="obstacle_prob_min",
            max_key="obstacle_prob_max",
            fallback_min=float(_DEFAULTS.obstacle_prob_min),
            fallback_max=float(_DEFAULTS.obstacle_prob_max),
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
        if abs(float(aspect_ratio_min) - 1.0) > 1e-9 or abs(float(aspect_ratio_max) - 1.0) > 1e-9:
            raise ValueError(f"{self.task_id} requires square tiles; set aspect_ratio_min=max=1.0")
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

        target_range_size = max(1, int(target_shortest_len_max) - int(target_shortest_len_min) + 1)
        target_selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}:target_shortest_len",
        )
        target_shortest_len = int(target_shortest_len_min) + (int(target_selection_index) % int(target_range_size))

        task_rng = spawn_rng(instance_seed, "task")
        blocked, start, goal, path, shortest_len = sample_unique_shortest_path_maze(
            task_rng,
            rows=rows,
            cols=cols,
            min_shortest_len=target_shortest_len,
            target_shortest_len=target_shortest_len,
            obstacle_prob_min=obstacle_prob_min,
            obstacle_prob_max=obstacle_prob_max,
            # Exact target-length sampling is harder than simple minimum-length rejection,
            # so widen the internal search budget in proportion to the target range width.
            max_attempts=int(max_attempts) * int(target_range_size),
        )
        validate_open_path_entities(
            blocked=blocked,
            start=start,
            goal=goal,
            path=path,
        )
        tile_spec = _sample_square_tile_spec(
            task_rng,
            short_side_px_min=int(short_side_px_min),
            short_side_px_max=int(short_side_px_max),
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

        base_image, background_meta, scene_style, panel_chrome_mode = build_rectangular_board_background(
            canvas_width=int(layout.canvas_width_px),
            canvas_height=int(layout.canvas_height_px),
            instance_seed=instance_seed,
            namespace="puzzles.cell_board.shortest_path",
            params=params,
            rendering_defaults=_RENDER_DEFAULTS,
        )
        draw = ImageDraw.Draw(base_image)
        fill_colors_by_coord = _build_fill_colors_by_coord(
            rows=int(rows),
            cols=int(cols),
            blocked=blocked,
            start=(int(start[0]), int(start[1])),
            goal=(int(goal[0]), int(goal[1])),
        )
        bbox_map = render_rectangular_tile_board(
            draw,
            layout=layout,
            fill_colors_by_coord=fill_colors_by_coord,
            scene_style=scene_style,
            panel_chrome_mode=str(panel_chrome_mode),
            label_font_family=rectangular_board_label_font_family(background_meta),
            tile_style=rectangular_board_tile_style(background_meta),
        )
        image = base_image
        image, post_noise_meta = apply_post_image_noise(
            image,
            instance_seed=instance_seed,
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        annotation_artifacts = coordinate_path_annotation_artifacts(
            coords=path,
            bbox_map=bbox_map,
        )
        path_ids = list(annotation_artifacts["private_witness"]["ids"])

        all_prompt_defaults = dict(_PROMPT_DEFAULTS if isinstance(_PROMPT_DEFAULTS, dict) else {})
        prompt_defaults = required_group_defaults(
            all_prompt_defaults,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "annotation_hint",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_bundle_id = str(prompt_defaults["bundle_id"])
        prompt_scene_key = str(prompt_defaults["scene_key"])
        prompt_task_key = str(prompt_defaults["task_key"])
        json_example, json_example_answer_only = resolve_prompt_json_examples(
            all_prompt_defaults,
            annotation_value=[[120, 120], [168, 120], [168, 168], [216, 168]],
            answer_type="integer",
        )
        obstacle_color_label = format_named_color_with_hex("black", _OBSTACLE_RGB)
        start_color_label = format_named_color_with_hex("green", _START_RGB)
        goal_color_label = format_named_color_with_hex("red", _GOAL_RGB)
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            scene_id=self.scene_id,
            bundle_id=prompt_bundle_id,
            scene_key=prompt_scene_key,
            task_key=prompt_task_key,
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "rows": int(rows),
                "cols": int(cols),
                "obstacle_color": str(obstacle_color_label),
                "start_color": str(start_color_label),
                "goal_color": str(goal_color_label),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=instance_seed,
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        prompt = str(prompt_artifacts.prompt)
        prompt_variants = dict(prompt_artifacts.prompt_variants)

        adjacency_open = open_adjacency_by_cell(
            rows=rows,
            cols=cols,
            blocked=blocked,
        )
        blocked_coords = [
            [int(row), int(col)]
            for row in range(int(rows))
            for col in range(int(cols))
            if bool(blocked[row][col])
        ]
        blocked_ids = [cell_id((int(row), int(col))) for row, col in blocked_coords]
        path_coords = [[int(row), int(col)] for row, col in path]
        path_coord_set = {(int(row), int(col)) for row, col in path}
        scene_entities = build_tile_cell_entities(
            rows=rows,
            cols=cols,
            attrs_by_coord={
                (int(row), int(col)): {
                    "blocked": bool(blocked[row][col]),
                    "is_open": not bool(blocked[row][col]),
                    "is_start": bool((int(row), int(col)) == (int(start[0]), int(start[1]))),
                    "is_goal": bool((int(row), int(col)) == (int(goal[0]), int(goal[1]))),
                    "is_on_shortest_path": bool((int(row), int(col)) in path_coord_set),
                    "fill_rgb": list(fill_colors_by_coord[(int(row), int(col))]),
                }
                for row in range(int(rows))
                for col in range(int(cols))
            },
        )

        render_map = {
            "image_id": "img0",
            "anchors": pixel_anchor_map_from_bboxes(bbox_map),
        }

        trace_payload = {
            "scene_ir": {
                "scene_kind": "rectangular_tile_path_board",
                "entities": scene_entities,
                "relations": {"adjacency_open": adjacency_open},
            },
            "query_spec": {
                "query_id": "shortest_path",
                "template_id": "shortest_path_v0",
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "dsl_program": [
                    {"out": "cells", "op": "select", "entity_type": "tile_cell"},
                    {
                        "out": "open_cells",
                        "op": "filter",
                        "in": "cells",
                        "predicate": {"blocked": False},
                    },
                    {
                        "out": "path",
                        "op": "shortest_path",
                        "relation": "adjacency_open",
                        "start": cell_id(start),
                        "goal": cell_id(goal),
                    },
                    {
                        "out": "annotation",
                        "op": "project_coords",
                        "in": "path",
                        "source_coord_space": "tile_grid",
                        "coord_space": "image_pixel",
                        "coord_type": "point_sequence",
                        "ordering": "path_order",
                    },
                    {"out": "answer", "op": "path_length", "in": "path"},
                ],
            },
            "render_spec": build_rectangular_board_render_spec(
                rows=int(rows),
                cols=int(cols),
                layout=layout,
                tile_spec=tile_spec,
                background_meta=background_meta,
                post_noise_meta=post_noise_meta,
            ),
            "render_map": render_map,
            "execution_trace": {
                "query_id": "shortest_path",
                "rows": int(rows),
                "cols": int(cols),
                **dict(board_metadata),
                "target_shortest_len": target_shortest_len,
                "target_shortest_len_range": [int(target_shortest_len_min), int(target_shortest_len_max)],
                "shortest_path_len": shortest_len,
                "obstacle_color_name": "black",
                "obstacle_color_rgb": list(_OBSTACLE_RGB),
                "obstacle_color_label": str(obstacle_color_label),
                "start_color_name": "green",
                "start_color_rgb": list(_START_RGB),
                "start_color_label": str(start_color_label),
                "goal_color_name": "red",
                "goal_color_rgb": list(_GOAL_RGB),
                "goal_color_label": str(goal_color_label),
                "start_coord": [int(start[0]), int(start[1])],
                "start_id": cell_id(start),
                "goal_coord": [int(goal[0]), int(goal[1])],
                "goal_id": cell_id(goal),
                "blocked_coords": list(blocked_coords),
                "blocked_ids": list(blocked_ids),
                "path_coords": list(path_coords),
                "path_ids": list(path_ids),
                "path_cell_count": len(path_ids),
                "answer_value": int(shortest_len),
            },
            "witness_symbolic": dict(annotation_artifacts["witness_symbolic"]),
            "projected_annotation": dict(annotation_artifacts["projected_annotation"]),
        }

        blocked_ratio = sum(sum(1 for value in row if value) for row in blocked) / float(rows * cols)

        return TaskOutput(
            prompt=prompt,
            answer_gt=TypedValue(type="integer", value=int(shortest_len)),
            annotation_gt=TypedValue(
                type=str(annotation_artifacts["annotation_type"]),
                value=list(annotation_artifacts["annotation_value"]),
            ),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            query_id="shortest_path",
            prompt_variants=prompt_variants,
        )
