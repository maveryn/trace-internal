"""Single-board rectangular-tile reachable-region-size task."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, Mapping, Tuple

from PIL import ImageDraw

from trace.core.seed import spawn_rng
from trace.core.task_group_config import get_task_group_defaults
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
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_json_example import resolve_prompt_json_examples
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from .shared.grid_graph import (
    cell_id,
    coord_adjacency_to_cell_ids,
    open_grid_adjacency,
)
from .shared.complexity import (
    build_tile_complexity,
    normalize_float_with_bounds,
    normalize_int_with_bounds,
    resolve_tile_complexity_weights,
)
from .shared.reachability_board import sample_reachability_board
from .shared.rectangular_board import (
    build_rectangular_board_background,
    build_rectangular_board_render_spec,
    render_rectangular_tile_board,
    resolve_rectangular_board_layout,
    sample_rectangular_tile_spec,
)
from .shared.tile_colors import available_named_tile_colors
from .shared.tile_evidence import coordinate_set_evidence_artifacts
from .shared.tile_scene import build_tile_cell_entities
from .shared.visual_defaults import load_tile_background_defaults, load_tile_noise_defaults


Coord = Tuple[int, int]

_OBSTACLE_RGB = (0, 0, 0)
_OPEN_RGB = (250, 250, 250)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable defaults for the rectangular tile reachability task."""

    rows_min: int = 3
    rows_max: int = 7
    cols_min: int = 3
    cols_max: int = 7
    short_side_px_min: int = 32
    short_side_px_max: int = 48
    aspect_ratio_min: float = 1.0
    aspect_ratio_max: float = 2.0
    outer_padding_fraction_min: float = 0.08
    outer_padding_fraction_max: float = 0.12
    placement_jitter_fraction_min: float = 0.02
    placement_jitter_fraction_max: float = 0.06
    obstacle_fraction_min: float = 0.12
    obstacle_fraction_max: float = 0.38
    reachable_fraction_min: float = 0.20
    reachable_fraction_max: float = 0.85
    answer_min: int = 3
    answer_max: int = 8


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "cell_board_reachability")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, dict) else {},
    task_id="cell_board_region_size_internal",
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_tile_background_defaults(task_group="reachability")
POST_IMAGE_NOISE_DEFAULTS = load_tile_noise_defaults(task_group="reachability", apply_prob=0.5)
_COMPLEXITY_WEIGHTS = resolve_tile_complexity_weights(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, dict) else {},
    task_id="cell_board_region_size_internal",
)


def _eligible_board_shapes(
    *,
    rows_min: int,
    rows_max: int,
    cols_min: int,
    cols_max: int,
    target_answer: int,
    reachable_fraction_min: float,
    reachable_fraction_max: float,
) -> list[Coord]:
    """Return board shapes whose reachable-fraction bounds can support the target answer."""
    eligible: list[Coord] = []
    for rows in range(int(rows_min), int(rows_max) + 1):
        for cols in range(int(cols_min), int(cols_max) + 1):
            board_cell_count = int(rows) * int(cols)
            min_supported = int(math.ceil(float(reachable_fraction_min) * float(board_cell_count)))
            max_supported = int(math.floor(float(reachable_fraction_max) * float(board_cell_count)))
            if int(min_supported) <= int(target_answer) <= int(max_supported):
                eligible.append((int(rows), int(cols)))
    return eligible


class TileRegionSizeTask:
    """Return the size of the reachable region from one marked start tile."""

    task_id = "cell_board_region_size_internal"
    domain = "puzzles"
    task_group = "cell_board_reachability"
    default_dataset_enabled = False

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
        obstacle_fraction_min, obstacle_fraction_max = resolve_required_float_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="obstacle_fraction_min",
            max_key="obstacle_fraction_max",
            fallback_min=float(_DEFAULTS.obstacle_fraction_min),
            fallback_max=float(_DEFAULTS.obstacle_fraction_max),
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
        answer_min, answer_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="answer_min",
            max_key="answer_max",
            fallback_min=int(_DEFAULTS.answer_min),
            fallback_max=int(_DEFAULTS.answer_max),
            context=f"generation defaults for {self.task_id}",
        )
        if int(answer_min) <= 0:
            raise ValueError(f"answer_min must be > 0 for {self.task_id}")
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

        target_range_size = max(1, int(answer_max) - int(answer_min) + 1)
        target_selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}:target_region_size",
        )
        target_region_size = int(answer_min) + (int(target_selection_index) % int(target_range_size))

        eligible_shapes = _eligible_board_shapes(
            rows_min=int(rows_min),
            rows_max=int(rows_max),
            cols_min=int(cols_min),
            cols_max=int(cols_max),
            target_answer=int(target_region_size),
            reachable_fraction_min=float(reachable_fraction_min),
            reachable_fraction_max=float(reachable_fraction_max),
        )
        if not eligible_shapes:
            raise RuntimeError("failed to find any board shape supporting the target reachable-region answer")
        shape_selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}:board_shape:{int(target_region_size)}",
        )
        ordered_shapes = [
            eligible_shapes[(int(shape_selection_index) + offset) % len(eligible_shapes)]
            for offset in range(len(eligible_shapes))
        ]

        task_rng = spawn_rng(instance_seed, "task")
        start_color_name, start_color_rgb = task_rng.choice(list(available_named_tile_colors()))
        board_sample = None
        sampled_shape: Coord | None = None
        for rows_candidate, cols_candidate in ordered_shapes:
            try:
                board_sample = sample_reachability_board(
                    task_rng,
                    rows=int(rows_candidate),
                    cols=int(cols_candidate),
                    obstacle_fraction_min=float(obstacle_fraction_min),
                    obstacle_fraction_max=float(obstacle_fraction_max),
                    reachable_fraction_min=float(reachable_fraction_min),
                    reachable_fraction_max=float(reachable_fraction_max),
                    max_attempts=max(int(max_attempts), int(max_attempts) * int(target_range_size)),
                    min_reachable_count=int(target_region_size),
                    max_reachable_count=int(target_region_size),
                )
                sampled_shape = (int(rows_candidate), int(cols_candidate))
                break
            except RuntimeError:
                continue
        if board_sample is None or sampled_shape is None:
            raise RuntimeError("failed to sample reachability board for the target reachable-region answer")
        rows, cols = int(sampled_shape[0]), int(sampled_shape[1])
        blocked = board_sample.blocked
        start = board_sample.start_coord
        reachable_coords = list(board_sample.reachable_coords)
        realized_obstacle_fraction = float(board_sample.obstacle_fraction)
        reachable_fraction = float(board_sample.reachable_fraction)
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

        base_image, background_meta, scene_style, panel_chrome_mode = build_rectangular_board_background(
            canvas_width=int(layout.canvas_width_px),
            canvas_height=int(layout.canvas_height_px),
            instance_seed=instance_seed,
            namespace="puzzles.cell_board.region_size",
        )
        draw = ImageDraw.Draw(base_image)
        fill_colors_by_coord = {
            (int(row), int(col)): (
                tuple(int(value) for value in start_color_rgb)
                if (int(row), int(col)) == (int(start[0]), int(start[1]))
                else (_OBSTACLE_RGB if bool(blocked[row][col]) else _OPEN_RGB)
            )
            for row in range(int(rows))
            for col in range(int(cols))
        }
        bbox_map = render_rectangular_tile_board(
            draw,
            layout=layout,
            fill_colors_by_coord=fill_colors_by_coord,
            scene_style=scene_style,
            panel_chrome_mode=str(panel_chrome_mode),
        )
        image, post_noise_meta = apply_post_image_noise(
            base_image,
            instance_seed=instance_seed,
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        evidence_artifacts = coordinate_set_evidence_artifacts(
            coords=reachable_coords,
            bbox_map=bbox_map,
        )
        answer_value = int(len(reachable_coords))
        if int(answer_value) != int(target_region_size):
            raise RuntimeError("sampled reachability board does not match target reachable-region answer")
        adjacency_open = coord_adjacency_to_cell_ids(
            open_grid_adjacency(rows=int(rows), cols=int(cols), blocked=blocked)
        )

        prompt_defaults_all = dict(_PROMPT_DEFAULTS if isinstance(_PROMPT_DEFAULTS, dict) else {})
        prompt_defaults = required_group_defaults(
            prompt_defaults_all,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "evidence_hint",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        obstacle_color_label = format_named_color_with_hex("black", _OBSTACLE_RGB)
        start_color_label = format_named_color_with_hex(str(start_color_name), start_color_rgb)
        json_example, json_example_answer_only = resolve_prompt_json_examples(
            prompt_defaults_all,
            evidence_value=[[120, 120], [168, 120], [168, 168], [168, 216]],
            answer_type="integer",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "rows": int(rows),
                "cols": int(cols),
                "obstacle_color": str(obstacle_color_label),
                "start_color": str(start_color_label),
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
        reachable_ids = list(evidence_artifacts["private_witness"]["ids"])
        reachable_coord_set = {(int(row), int(col)) for row, col in reachable_coords}
        scene_entities = build_tile_cell_entities(
            rows=int(rows),
            cols=int(cols),
            attrs_by_coord={
                (int(row), int(col)): {
                    "blocked": bool(blocked[row][col]),
                    "is_start": bool((int(row), int(col)) == (int(start[0]), int(start[1]))),
                    "is_reachable": bool((int(row), int(col)) in reachable_coord_set),
                    "fill_rgb": list(fill_colors_by_coord[(int(row), int(col))]),
                }
                for row in range(int(rows))
                for col in range(int(cols))
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "rectangular_tile_reachability_board",
                "entities": scene_entities,
                "relations": {"adjacency_open": adjacency_open},
            },
            "query_spec": {
                "query_variant": "region_size",
                "template_id": "region_size_v0",
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
                        "out": "reachable",
                        "op": "reachable_set",
                        "relation": "adjacency_open",
                        "start": str(start_id),
                    },
                    {
                        "out": "evidence",
                        "op": "project_coords",
                        "in": "reachable",
                        "source_coord_space": "tile_grid",
                        "coord_space": "image_pixel",
                        "coord_type": "point_set",
                        "ordering": "row_major",
                    },
                    {"out": "answer", "op": "count", "in": "reachable"},
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
                "query_variant": "region_size",
                "rows": int(rows),
                "cols": int(cols),
                "answer_min": int(answer_min),
                "answer_max": int(answer_max),
                "answer_range": [int(answer_min), int(answer_max)],
                "target_region_size": int(target_region_size),
                "query_selection_strategy": "uniform_over_target_region_size_range_with_rejection",
                "obstacle_color_label": str(obstacle_color_label),
                "start_color_name": str(start_color_name),
                "start_color_rgb": [int(value) for value in start_color_rgb],
                "start_color_label": str(start_color_label),
                "start_coord": [int(start[0]), int(start[1])],
                "start_id": str(start_id),
                "blocked_coords": list(blocked_coords),
                "blocked_ids": [cell_id((int(coord[0]), int(coord[1]))) for coord in blocked_coords],
                "reachable_coords": [[int(row), int(col)] for row, col in reachable_coords],
                "reachable_ids": list(reachable_ids),
                "answer_value": int(answer_value),
                "obstacle_fraction": float(realized_obstacle_fraction),
                "reachable_fraction": float(reachable_fraction),
            },
            "witness_symbolic": dict(evidence_artifacts["witness_symbolic"]),
            "projected_evidence": dict(evidence_artifacts["projected_evidence"]),
        }

        board_cell_count = int(rows) * int(cols)
        blocked_count = len(blocked_coords)
        min_board_cell_count = int(rows_min) * int(cols_min)
        max_board_cell_count = int(rows_max) * int(cols_max)
        complexity = build_tile_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": (
                    0.80
                    * normalize_int_with_bounds(
                        int(board_cell_count),
                        (int(min_board_cell_count), int(max_board_cell_count)),
                    )
                    + 0.20
                    * normalize_float_with_bounds(
                        float(realized_obstacle_fraction),
                        (float(obstacle_fraction_min), float(obstacle_fraction_max)),
                    )
                ),
                "reasoning_load": (
                    0.45
                    * normalize_int_with_bounds(
                        int(board_cell_count),
                        (int(min_board_cell_count), int(max_board_cell_count)),
                    )
                    + 0.30
                    * normalize_int_with_bounds(
                        int(answer_value),
                        (int(answer_min), int(answer_max)),
                    )
                    + 0.10
                    * normalize_int_with_bounds(
                        int(cols),
                        (int(cols_min), int(cols_max)),
                    )
                    + 0.10
                    * normalize_float_with_bounds(
                        1.0 - float(realized_obstacle_fraction),
                        (1.0 - float(obstacle_fraction_max), 1.0 - float(obstacle_fraction_min)),
                    )
                    + 0.05
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
            query_variant="region_size",
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
