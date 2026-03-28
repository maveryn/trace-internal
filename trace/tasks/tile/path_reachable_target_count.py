"""Count reachable marked targets on a blocked square tile board."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from PIL import ImageDraw

from ...core.seed import spawn_rng
from ...core.task_group_config import get_task_group_defaults
from ...core.types import TypedValue
from ...core.visual.background import make_background_canvas
from ...core.visual.noise import apply_post_image_noise
from ..base import TaskOutput
from ..registry import register_task
from ..shared.bbox_projection import pixel_anchor_map_from_bboxes
from ..shared.color_format import format_named_color_with_hex
from ..shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_required_float_bounds,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ..shared.deterministic_sampling import resolve_selection_index
from ..shared.output_metadata import default_task_versions
from ..shared.prompt_json_example import resolve_prompt_json_examples
from ..shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from .shared.grid_graph import cell_id, coord_adjacency_to_cell_ids, open_grid_adjacency
from .shared.complexity import (
    build_tile_complexity,
    normalize_float_with_bounds,
    normalize_int_with_bounds,
    resolve_tile_complexity_weights,
)
from .shared.reachability_board import sample_reachability_board
from .shared.rectangular_board import (
    RectangularTileSpec,
    build_rectangular_board_render_spec,
    render_rectangular_tile_board,
    resolve_rectangular_board_layout,
)
from .shared.tile_colors import named_tile_color
from .shared.tile_evidence import coordinate_set_evidence_artifacts, sort_coords_row_major
from .shared.tile_scene import build_tile_cell_entities
from .shared.visual_defaults import load_tile_background_defaults, load_tile_noise_defaults


Coord = Tuple[int, int]

_OBSTACLE_RGB = (0, 0, 0)
_OPEN_RGB = (250, 250, 250)
_START_RGB = named_tile_color("green")
_TARGET_RGB = named_tile_color("red")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable defaults for reachable-target counting on square boards."""

    rows: int = 7
    cols: int = 7
    target_reachable_target_count_min: int = 0
    target_reachable_target_count_max: int = 6
    obstacle_prob_min: float = 0.16
    obstacle_prob_max: float = 0.36
    reachable_fraction_min: float = 0.20
    reachable_fraction_max: float = 0.85
    short_side_px_min: int = 32
    short_side_px_max: int = 48
    aspect_ratio_min: float = 1.0
    aspect_ratio_max: float = 1.0
    outer_padding_fraction_min: float = 0.08
    outer_padding_fraction_max: float = 0.12
    placement_jitter_fraction_min: float = 0.02
    placement_jitter_fraction_max: float = 0.06


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("tile", "path")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, dict) else {},
    task_id="task_tile_path_reachable_target_count",
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_tile_background_defaults(task_group="path")
POST_IMAGE_NOISE_DEFAULTS = load_tile_noise_defaults(task_group="path", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_tile_complexity_weights(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, dict) else {},
    task_id="task_tile_path_reachable_target_count",
)


def _sample_square_tile_spec(rng, *, short_side_px_min: int, short_side_px_max: int) -> RectangularTileSpec:
    """Return one square tile spec for equal-cost movement rendering."""
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
    target_coords,
) -> Dict[Coord, Tuple[int, int, int]]:
    """Build per-cell role colors for one reachable-target board scene."""
    target_coord_set = {(int(row), int(col)) for row, col in target_coords}
    fill_colors: Dict[Coord, Tuple[int, int, int]] = {}
    for row in range(int(rows)):
        for col in range(int(cols)):
            coord = (int(row), int(col))
            if bool(blocked[row][col]):
                fill = _OBSTACLE_RGB
            elif coord == (int(start[0]), int(start[1])):
                fill = _START_RGB
            elif coord in target_coord_set:
                fill = _TARGET_RGB
            else:
                fill = _OPEN_RGB
            fill_colors[coord] = tuple(int(channel) for channel in fill)
    return fill_colors


@register_task
class TileReachableTargetCountTask:
    """Count how many marked targets are reachable from one start tile."""

    task_id = "task_tile_path_reachable_target_count"
    domain = "tile"
    task_group = "path"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        rows = int(params.get("rows", group_default(_GEN_DEFAULTS, "rows", _DEFAULTS.rows)))
        cols = int(params.get("cols", group_default(_GEN_DEFAULTS, "cols", _DEFAULTS.cols)))
        target_reachable_target_count_min = int(
            params.get(
                "target_reachable_target_count_min",
                group_default(
                    _GEN_DEFAULTS,
                    "target_reachable_target_count_min",
                    _DEFAULTS.target_reachable_target_count_min,
                ),
            )
        )
        target_reachable_target_count_max = int(
            params.get(
                "target_reachable_target_count_max",
                group_default(
                    _GEN_DEFAULTS,
                    "target_reachable_target_count_max",
                    _DEFAULTS.target_reachable_target_count_max,
                ),
            )
        )
        if int(target_reachable_target_count_min) < 0:
            raise ValueError("target_reachable_target_count_min must be >= 0")
        if int(target_reachable_target_count_min) > int(target_reachable_target_count_max):
            raise ValueError("target_reachable_target_count_min must be <= target_reachable_target_count_max")

        obstacle_prob_min, obstacle_prob_max = resolve_required_float_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="obstacle_prob_min",
            max_key="obstacle_prob_max",
            fallback_min=float(_DEFAULTS.obstacle_prob_min),
            fallback_max=float(_DEFAULTS.obstacle_prob_max),
            context=f"generation defaults for {self.task_id}",
        )
        reachable_fraction_min, reachable_fraction_max = resolve_required_float_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="reachable_fraction_min",
            max_key="reachable_fraction_max",
            fallback_min=float(_DEFAULTS.reachable_fraction_min),
            fallback_max=float(_DEFAULTS.reachable_fraction_max),
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

        effective_target_reachable_target_count_max = min(
            int(target_reachable_target_count_max),
            max(0, int(rows) * int(cols) - 2),
        )
        if int(effective_target_reachable_target_count_max) < int(target_reachable_target_count_min):
            raise ValueError("reachable-target answer range is infeasible for the configured board size")

        target_range_size = (
            int(effective_target_reachable_target_count_max)
            - int(target_reachable_target_count_min)
            + 1
        )
        target_selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}:target_reachable_target_count",
        )
        target_reachable_target_count = int(target_reachable_target_count_min) + (
            int(target_selection_index) % int(target_range_size)
        )
        total_target_count = max(2, int(target_reachable_target_count) + 1)

        task_rng = spawn_rng(instance_seed, "task")
        board_sample = sample_reachability_board(
            task_rng,
            rows=int(rows),
            cols=int(cols),
            obstacle_fraction_min=float(obstacle_prob_min),
            obstacle_fraction_max=float(obstacle_prob_max),
            reachable_fraction_min=float(reachable_fraction_min),
            reachable_fraction_max=float(reachable_fraction_max),
            max_attempts=max(int(max_attempts) * max(4, int(target_range_size)), int(max_attempts)),
            min_reachable_count=1,
            min_reachable_non_start_count=int(target_reachable_target_count),
            min_unreachable_open_count=int(total_target_count) - int(target_reachable_target_count),
        )

        blocked = board_sample.blocked
        start = board_sample.start_coord
        reachable_non_start_coords = list(board_sample.reachable_non_start_coords)
        unreachable_open_coords = list(board_sample.unreachable_open_coords)
        reachable_coords = list(board_sample.reachable_coords)
        realized_obstacle_fraction = float(board_sample.obstacle_fraction)
        reachable_fraction = float(board_sample.reachable_fraction)

        reachable_target_coords = sort_coords_row_major(
            task_rng.sample(reachable_non_start_coords, k=int(target_reachable_target_count))
            if int(target_reachable_target_count) > 0
            else []
        )
        unreachable_target_count = int(total_target_count) - int(target_reachable_target_count)
        unreachable_target_coords = sort_coords_row_major(
            task_rng.sample(unreachable_open_coords, k=int(unreachable_target_count))
        )
        target_coords = sort_coords_row_major(
            list(reachable_target_coords) + list(unreachable_target_coords)
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

        base_image, background_meta = make_background_canvas(
            canvas_width=int(layout.canvas_width_px),
            canvas_height=int(layout.canvas_height_px),
            instance_seed=instance_seed,
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
            fallback_color=(246, 246, 246),
        )
        draw = ImageDraw.Draw(base_image)
        fill_colors_by_coord = _build_fill_colors_by_coord(
            rows=int(rows),
            cols=int(cols),
            blocked=blocked,
            start=(int(start[0]), int(start[1])),
            target_coords=target_coords,
        )
        bbox_map = render_rectangular_tile_board(
            draw,
            layout=layout,
            fill_colors_by_coord=fill_colors_by_coord,
        )
        image, post_noise_meta = apply_post_image_noise(
            base_image,
            instance_seed=instance_seed,
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        evidence_artifacts = coordinate_set_evidence_artifacts(
            coords=reachable_target_coords,
            bbox_map=bbox_map,
        )
        answer_value = int(len(reachable_target_coords))
        adjacency_open = coord_adjacency_to_cell_ids(
            open_grid_adjacency(rows=int(rows), cols=int(cols), blocked=blocked)
        )

        obstacle_color_label = format_named_color_with_hex("black", _OBSTACLE_RGB)
        start_color_label = format_named_color_with_hex("green", _START_RGB)
        target_color_label = format_named_color_with_hex("red", _TARGET_RGB)
        all_prompt_defaults = dict(_PROMPT_DEFAULTS if isinstance(_PROMPT_DEFAULTS, dict) else {})
        prompt_defaults = required_group_defaults(
            all_prompt_defaults,
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
        json_example, json_example_answer_only = resolve_prompt_json_examples(
            all_prompt_defaults,
            evidence_value=[[0, 2], [2, 1]],
            answer_type="integer",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "rows": int(rows),
                "cols": int(cols),
                "obstacle_color": str(obstacle_color_label),
                "start_color": str(start_color_label),
                "target_color": str(target_color_label),
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

        blocked_coords = [
            [int(row), int(col)]
            for row in range(int(rows))
            for col in range(int(cols))
            if bool(blocked[row][col])
        ]
        start_id = cell_id(start)
        reachable_target_ids = list(evidence_artifacts["witness_symbolic"]["ids"])
        target_coord_set = {(int(row), int(col)) for row, col in target_coords}
        reachable_target_coord_set = {(int(row), int(col)) for row, col in reachable_target_coords}
        unreachable_target_coord_set = {(int(row), int(col)) for row, col in unreachable_target_coords}
        scene_entities = build_tile_cell_entities(
            rows=int(rows),
            cols=int(cols),
            attrs_by_coord={
                (int(row), int(col)): {
                    "blocked": bool(blocked[row][col]),
                    "is_start": bool((int(row), int(col)) == (int(start[0]), int(start[1]))),
                    "is_target": bool((int(row), int(col)) in target_coord_set),
                    "is_reachable_target": bool((int(row), int(col)) in reachable_target_coord_set),
                    "is_unreachable_target": bool((int(row), int(col)) in unreachable_target_coord_set),
                    "fill_rgb": list(fill_colors_by_coord[(int(row), int(col))]),
                }
                for row in range(int(rows))
                for col in range(int(cols))
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "rectangular_tile_reachable_target_board",
                "entities": scene_entities,
                "relations": {"adjacency_open": adjacency_open},
            },
            "query_spec": {
                "task_variant": "reachable_target_count",
                "template_id": "reachable_target_count_v1",
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
                        "out": "targets",
                        "op": "filter",
                        "in": "open_cells",
                        "predicate": {"is_target": True},
                    },
                    {
                        "out": "reachable",
                        "op": "reachable_set",
                        "relation": "adjacency_open",
                        "start": str(start_id),
                    },
                    {
                        "out": "reachable_targets",
                        "op": "intersect",
                        "inputs": ["targets", "reachable"],
                    },
                    {
                        "out": "evidence",
                        "op": "project_coords",
                        "in": "reachable_targets",
                        "coord_space": "tile_grid",
                        "coord_type": "grid_point_set",
                        "ordering": "row_major",
                    },
                    {"out": "answer", "op": "count", "in": "reachable_targets"},
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
            "render_map": {
                "image_id": "img0",
                "anchors": pixel_anchor_map_from_bboxes(bbox_map),
            },
            "execution_trace": {
                "task_variant": "reachable_target_count",
                "rows": int(rows),
                "cols": int(cols),
                "target_reachable_target_count_range": [
                    int(target_reachable_target_count_min),
                    int(effective_target_reachable_target_count_max),
                ],
                "target_reachable_target_count": int(target_reachable_target_count),
                "total_target_count": int(total_target_count),
                "obstacle_color_label": str(obstacle_color_label),
                "start_color_label": str(start_color_label),
                "start_color_rgb": [int(value) for value in _START_RGB],
                "target_color_label": str(target_color_label),
                "target_color_rgb": [int(value) for value in _TARGET_RGB],
                "start_coord": [int(start[0]), int(start[1])],
                "start_id": str(start_id),
                "blocked_coords": list(blocked_coords),
                "blocked_ids": [cell_id((int(coord[0]), int(coord[1]))) for coord in blocked_coords],
                "target_coords": [[int(row), int(col)] for row, col in target_coords],
                "target_ids": [cell_id((int(row), int(col))) for row, col in target_coords],
                "reachable_target_coords": [[int(row), int(col)] for row, col in reachable_target_coords],
                "reachable_target_ids": list(reachable_target_ids),
                "unreachable_target_coords": [[int(row), int(col)] for row, col in unreachable_target_coords],
                "unreachable_target_ids": [
                    cell_id((int(row), int(col))) for row, col in unreachable_target_coords
                ],
                "reachable_coords": [[int(row), int(col)] for row, col in reachable_coords],
                "reachable_ids": [cell_id((int(row), int(col))) for row, col in reachable_coords],
                "answer_value": int(answer_value),
                "obstacle_fraction": float(realized_obstacle_fraction),
                "reachable_fraction": float(reachable_fraction),
            },
            "witness_symbolic": dict(evidence_artifacts["witness_symbolic"]),
            "projected_evidence": dict(evidence_artifacts["projected_evidence"]),
        }

        board_cell_count = int(rows) * int(cols)
        blocked_count = len(blocked_coords)
        max_total_target_count = max(2, int(effective_target_reachable_target_count_max) + 1)
        complexity = build_tile_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": (
                    0.55
                    * normalize_float_with_bounds(
                        float(realized_obstacle_fraction),
                        (float(obstacle_prob_min), float(obstacle_prob_max)),
                    )
                    + 0.45
                    * normalize_int_with_bounds(
                        int(total_target_count),
                        (2, int(max_total_target_count)),
                    )
                ),
                "reasoning_load": (
                    0.65
                    * normalize_int_with_bounds(
                        int(answer_value),
                        (
                            int(target_reachable_target_count_min),
                            int(effective_target_reachable_target_count_max),
                        ),
                    )
                    + 0.35
                    * normalize_float_with_bounds(
                        1.0 - float(reachable_fraction),
                        (1.0 - float(reachable_fraction_max), 1.0 - float(reachable_fraction_min)),
                    )
                ),
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
            task_variant="reachable_target_count",
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
