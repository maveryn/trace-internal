"""Single-board rectangular-tile gravity max-drop task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ...core.seed import spawn_rng
from ...core.task_group_config import get_task_group_defaults
from ...core.types import TypedValue
from ..base import TaskOutput
from ..registry import register_task
from ..shared.bbox_projection import pixel_anchor_map_from_bboxes
from ..shared.color_format import format_named_color_with_hex, rgb_to_hex
from ..shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ..shared.deterministic_sampling import resolve_selection_index
from ..shared.output_metadata import default_task_versions
from ..shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from .shared.grid_graph import cell_id
from .shared.complexity import (
    build_tile_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_tile_complexity_weights,
)
from .shared.named_color_board import (
    Coord,
    RectangularNamedColorBoardTaskDefaults,
    build_color_board_scene_entities,
    build_palette_trace,
    build_rectangular_named_color_board_render_spec,
    build_rectangular_named_color_board_scene,
)
from .shared.tile_colors import NamedColor, sample_named_tile_palette
from .shared.tile_evidence import coordinate_path_evidence_artifacts
from .shared.visual_defaults import load_tile_background_defaults, load_tile_noise_defaults


WHITE: NamedColor = ("white", (255, 255, 255))
BLACK: NamedColor = ("black", (0, 0, 0))


@dataclass(frozen=True)
class _TaskDefaults(RectangularNamedColorBoardTaskDefaults):
    """Stable defaults for the tile gravity transition task."""

    target_max_drop_min: int = 1


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("tile", "transition")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, dict) else {},
    task_id="task_tile_transition_gravity_max_drop",
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_tile_background_defaults(task_group="transition")
POST_IMAGE_NOISE_DEFAULTS = load_tile_noise_defaults(task_group="transition", apply_prob=0.5)
_COMPLEXITY_WEIGHTS = resolve_tile_complexity_weights(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, dict) else {},
    task_id="task_tile_transition_gravity_max_drop",
)


def _eligible_board_shapes(
    *,
    rows_min: int,
    rows_max: int,
    cols_min: int,
    cols_max: int,
    target_max_drop: int,
) -> List[Tuple[int, int]]:
    """Return board shapes that can realize the requested maximum drop distance."""
    return [
        (int(rows), int(cols))
        for rows in range(int(rows_min), int(rows_max) + 1)
        for cols in range(int(cols_min), int(cols_max) + 1)
        if int(rows) >= int(target_max_drop) + 2
    ]


def _winner_obstacle_height(rng, *, rows: int, target_max_drop: int) -> int:
    """Sample a bottom obstacle height that keeps the winning drop feasible."""
    max_height = int(rows) - int(target_max_drop) - 1
    if int(max_height) < 1:
        raise ValueError("winning obstacle height requires rows >= target_max_drop + 2")
    return int(rng.randint(1, int(max_height)))


def _non_winner_drop(rng, *, target_max_drop: int) -> int:
    """Sample a strictly smaller drop distance for non-winning columns."""
    if int(target_max_drop) <= 1:
        return 0
    return int(rng.randint(0, int(target_max_drop) - 1))


def _non_winner_obstacle_height(rng, *, rows: int, drop: int) -> int:
    """Sample any obstacle height that keeps the non-winning drop feasible."""
    max_height = int(rows) - int(drop) - 1
    return int(rng.randint(0, int(max_height)))


def _vertical_path(*, source: Coord, final: Coord) -> List[Coord]:
    """Return the inclusive vertical path from source to final."""
    if int(source[1]) != int(final[1]):
        raise ValueError("gravity paths must stay within one column")
    if int(source[0]) > int(final[0]):
        raise ValueError("gravity path source row must be above or equal to final row")
    return [
        (int(row), int(source[1]))
        for row in range(int(source[0]), int(final[0]) + 1)
    ]


def _build_gravity_board(
    rng,
    *,
    rows: int,
    cols: int,
    drop_color: NamedColor,
    target_max_drop: int,
) -> Tuple[Dict[Coord, NamedColor], List[int], List[Coord], List[Coord], List[int], int]:
    """Construct one board with exactly one uniquely farthest-falling tile."""
    if int(target_max_drop) < 1:
        raise ValueError("target_max_drop must be >= 1")

    winner_col = int(rng.randint(0, int(cols) - 1))
    obstacle_heights: List[int] = []
    source_cells: List[Coord] = []
    final_cells: List[Coord] = []
    drops: List[int] = []

    for col in range(int(cols)):
        if int(col) == int(winner_col):
            drop = int(target_max_drop)
            obstacle_height = _winner_obstacle_height(
                rng,
                rows=int(rows),
                target_max_drop=int(target_max_drop),
            )
        else:
            drop = _non_winner_drop(rng, target_max_drop=int(target_max_drop))
            obstacle_height = _non_winner_obstacle_height(
                rng,
                rows=int(rows),
                drop=int(drop),
            )
        final_row = int(rows) - int(obstacle_height) - 1
        source_row = int(final_row) - int(drop)
        obstacle_heights.append(int(obstacle_height))
        source_cells.append((int(source_row), int(col)))
        final_cells.append((int(final_row), int(col)))
        drops.append(int(drop))

    board_colors: Dict[Coord, NamedColor] = {
        (int(row), int(col)): WHITE
        for row in range(int(rows))
        for col in range(int(cols))
    }
    for col, obstacle_height in enumerate(obstacle_heights):
        for row in range(int(rows) - int(obstacle_height), int(rows)):
            board_colors[(int(row), int(col))] = BLACK
    for col, source in enumerate(source_cells):
        board_colors[(int(source[0]), int(source[1]))] = drop_color
        if int(drops[col]) < 0:
            raise RuntimeError("drop distances must be non-negative")

    if int(max(drops)) != int(target_max_drop):
        raise RuntimeError("constructed board does not realize target_max_drop")
    if int(sum(1 for drop in drops if int(drop) == int(target_max_drop))) != 1:
        raise RuntimeError("constructed board must have a unique max-drop column")

    return board_colors, obstacle_heights, source_cells, final_cells, drops, winner_col


@register_task
class TileGravityMaxDropTask:
    """Return the unique maximum drop distance under a straight-down gravity transition."""

    task_id = "task_tile_transition_gravity_max_drop"
    domain = "tile"
    task_group = "transition"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        task_rng = spawn_rng(instance_seed, "task")
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
        target_max_drop_min = int(
            params.get(
                "target_max_drop_min",
                group_default(_GEN_DEFAULTS, "target_max_drop_min", int(_DEFAULTS.target_max_drop_min)),
            )
        )
        default_target_max_drop_max = max(1, int(rows_max) - 2)
        target_max_drop_max = int(
            params.get(
                "target_max_drop_max",
                group_default(
                    _GEN_DEFAULTS,
                    "target_max_drop_max",
                    int(default_target_max_drop_max),
                ),
            )
        )
        effective_target_max_drop_max = min(
            int(target_max_drop_max),
            int(default_target_max_drop_max),
        )
        if int(target_max_drop_min) > int(effective_target_max_drop_max):
            raise ValueError("target_max_drop_min must be <= the effective target max")

        target_selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}:target_max_drop",
        )
        target_range_size = max(
            1,
            int(effective_target_max_drop_max) - int(target_max_drop_min) + 1,
        )
        target_max_drop = int(target_max_drop_min) + (
            int(target_selection_index) % int(target_range_size)
        )

        eligible_shapes = _eligible_board_shapes(
            rows_min=int(rows_min),
            rows_max=int(rows_max),
            cols_min=int(cols_min),
            cols_max=int(cols_max),
            target_max_drop=int(target_max_drop),
        )
        if not eligible_shapes:
            raise RuntimeError("failed to find any board shape supporting the target max-drop answer")
        shape_selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}:board_shape",
        )
        rows, cols = eligible_shapes[int(shape_selection_index) % len(eligible_shapes)]

        drop_palette = sample_named_tile_palette(task_rng, palette_size=1)
        if len(drop_palette) != 1:
            raise ValueError("gravity task requires exactly one sampled drop color")
        drop_color_name, drop_color_rgb = drop_palette[0]
        obstacle_color_name, obstacle_color_rgb = BLACK
        board_color_name, board_color_rgb = WHITE
        palette = [WHITE, BLACK, (str(drop_color_name), (int(drop_color_rgb[0]), int(drop_color_rgb[1]), int(drop_color_rgb[2])))]

        board_colors, obstacle_heights, source_cells, final_cells, drops, winner_col = _build_gravity_board(
            task_rng,
            rows=int(rows),
            cols=int(cols),
            drop_color=(str(drop_color_name), (int(drop_color_rgb[0]), int(drop_color_rgb[1]), int(drop_color_rgb[2]))),
            target_max_drop=int(target_max_drop),
        )

        scene = build_rectangular_named_color_board_scene(
            instance_seed,
            task_rng=task_rng,
            params=params,
            generation_defaults=_GEN_DEFAULTS,
            rendering_defaults=_RENDER_DEFAULTS,
            background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
            noise_defaults=POST_IMAGE_NOISE_DEFAULTS,
            defaults=_DEFAULTS,
            rows=int(rows),
            cols=int(cols),
            palette=palette,
            board_colors=board_colors,
        )

        winner_source = source_cells[int(winner_col)]
        winner_final = final_cells[int(winner_col)]
        winner_path = _vertical_path(
            source=(int(winner_source[0]), int(winner_source[1])),
            final=(int(winner_final[0]), int(winner_final[1])),
        )
        evidence_artifacts = coordinate_path_evidence_artifacts(
            coords=winner_path,
            bbox_map=scene.bbox_map,
        )
        answer_value = int(drops[int(winner_col)])
        if int(answer_value) != int(target_max_drop):
            raise RuntimeError("constructed winner path does not match target max-drop answer")

        drop_color_hex = rgb_to_hex(drop_color_rgb)
        drop_color_label = format_named_color_with_hex(drop_color_name, drop_color_rgb)
        obstacle_color_hex = rgb_to_hex(obstacle_color_rgb)
        obstacle_color_label = format_named_color_with_hex(obstacle_color_name, obstacle_color_rgb)
        board_color_hex = rgb_to_hex(board_color_rgb)

        winner_path_set = {(int(row), int(col)) for row, col in winner_path}
        source_cell_set = {(int(source[0]), int(source[1])) for source in source_cells}
        obstacle_cell_set = {
            (int(row), int(col))
            for col, obstacle_height in enumerate(obstacle_heights)
            for row in range(int(rows) - int(obstacle_height), int(rows))
        }
        winner_source_id = cell_id((int(winner_source[0]), int(winner_source[1])))
        scene_entities = build_color_board_scene_entities(
            scene,
            query_color_name=str(drop_color_name),
            extra_attrs_by_coord={
                (int(row), int(col)): {
                    "role": (
                        "drop_tile"
                        if (int(row), int(col)) in source_cell_set
                        else "obstacle"
                        if (int(row), int(col)) in obstacle_cell_set
                        else "empty"
                    ),
                    "is_winning_path": bool((int(row), int(col)) in winner_path_set),
                    "is_winning_source": bool(cell_id((int(row), int(col))) == str(winner_source_id)),
                }
                for row in range(int(rows))
                for col in range(int(cols))
            },
        )

        columns_trace = [
            {
                "column": int(col),
                "obstacle_height": int(obstacle_heights[col]),
                "source_coord": [int(source_cells[col][0]), int(source_cells[col][1])],
                "final_coord": [int(final_cells[col][0]), int(final_cells[col][1])],
                "drop_distance": int(drops[col]),
                "is_winner": bool(int(col) == int(winner_col)),
            }
            for col in range(int(cols))
        ]

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
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "rows": int(scene.rows),
                "cols": int(scene.cols),
                "drop_color": str(drop_color_label),
                "obstacle_color": str(obstacle_color_label),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=instance_seed,
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        trace_payload = {
            "scene_ir": {
                "scene_kind": "rectangular_tile_board",
                "entities": scene_entities,
                "relations": {},
            },
            "query_spec": {
                "task_variant": "gravity_max_drop",
                "template_id": "gravity_max_drop_v1",
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "dsl_program": [
                    {"out": "cells", "op": "select", "entity_type": "tile_cell"},
                    {
                        "out": "drop_tiles",
                        "op": "filter",
                        "in": "cells",
                        "predicate": {"role": "drop_tile"},
                    },
                    {
                        "out": "transitions",
                        "op": "apply_gravity",
                        "in": "drop_tiles",
                        "direction": "down",
                        "blocking_role": "obstacle",
                    },
                    {
                        "out": "winner",
                        "op": "argmax",
                        "in": "transitions",
                        "value": "drop_distance",
                        "tie_break": "reject_non_unique",
                    },
                    {
                        "out": "evidence",
                        "op": "project_path_coords",
                        "in": "winner",
                        "coord_space": "tile_grid",
                        "coord_type": "grid_point_path",
                    },
                    {"out": "answer", "op": "read_attr", "in": "winner", "attr": "drop_distance"},
                ],
            },
            "render_spec": {
                **build_rectangular_named_color_board_render_spec(scene),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": pixel_anchor_map_from_bboxes(scene.bbox_map),
            },
            "execution_trace": {
                "task_variant": "gravity_max_drop",
                "rows": int(scene.rows),
                "cols": int(scene.cols),
                "palette": list(build_palette_trace(scene.palette)),
                "palette_size": int(scene.palette_size),
                "board_color_name": str(board_color_name),
                "board_color_hex": str(board_color_hex),
                "obstacle_color_name": str(obstacle_color_name),
                "obstacle_color_hex": str(obstacle_color_hex),
                "obstacle_color_label": str(obstacle_color_label),
                "drop_color_name": str(drop_color_name),
                "drop_color_rgb": [int(drop_color_rgb[0]), int(drop_color_rgb[1]), int(drop_color_rgb[2])],
                "drop_color_hex": str(drop_color_hex),
                "drop_color_label": str(drop_color_label),
                "construction_strategy": "uniform_target_max_drop_with_unique_winner",
                "target_max_drop": int(target_max_drop),
                "target_max_drop_range": [
                    int(target_max_drop_min),
                    int(effective_target_max_drop_max),
                ],
                "unique_max": True,
                "winner_col": int(winner_col),
                "winner_source_coord": [int(winner_source[0]), int(winner_source[1])],
                "winner_final_coord": [int(winner_final[0]), int(winner_final[1])],
                "winner_path_coords": [[int(row), int(col)] for row, col in winner_path],
                "winner_path_ids": list(evidence_artifacts["witness_symbolic"]["ids"]),
                "obstacle_heights": [int(value) for value in obstacle_heights],
                "source_cells": [[int(row), int(col)] for row, col in source_cells],
                "final_cells": [[int(row), int(col)] for row, col in final_cells],
                "drops": [int(value) for value in drops],
                "columns": list(columns_trace),
                "answer_value": int(answer_value),
            },
            "witness_symbolic": dict(evidence_artifacts["witness_symbolic"]),
            "projected_evidence": dict(evidence_artifacts["projected_evidence"]),
        }

        obstacle_columns = int(sum(1 for value in obstacle_heights if int(value) > 0))
        min_board_cell_count = int(rows_min) * int(cols_min)
        max_board_cell_count = int(rows_max) * int(cols_max)
        complexity = build_tile_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": (
                    0.60
                    * normalize_int_with_bounds(
                        int(scene.rows) * int(scene.cols),
                        (int(min_board_cell_count), int(max_board_cell_count)),
                    )
                    + 0.40
                    * clamp_unit_interval(
                        float(obstacle_columns) / float(max(1, int(scene.cols)))
                    )
                ),
                "reasoning_load": (
                    0.75
                    * normalize_int_with_bounds(
                        int(answer_value),
                        (int(target_max_drop_min), int(effective_target_max_drop_max)),
                    )
                    + 0.25
                    * clamp_unit_interval(
                        float(obstacle_columns) / float(max(1, int(scene.cols)))
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
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant="gravity_max_drop",
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
