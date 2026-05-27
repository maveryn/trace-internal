"""Shared dataset builders and render defaults for spatial block-stack puzzles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.render_variation import resolve_render_float, resolve_render_int, resolve_render_rgb
from .common import resolve_puzzle_axis_variant


SUPPORTED_PUZZLE_BLOCK_SCENE_VARIANTS: Tuple[str, ...] = (
    "stack_strip",
    "stack_card",
    "stack_outline",
)
SUPPORTED_PUZZLE_BLOCK_REMOVAL_VARIANTS: Tuple[str, ...] = ("cube_removal_count",)


def _resolve_int_param(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
    fallback: int,
) -> int:
    """Resolve one integer generation or rendering parameter."""

    return int(params.get(str(key), group_default(defaults, str(key), int(fallback))))


@dataclass(frozen=True)
class PuzzleCubeRemovalDefaults:
    """Default generation bounds for cube-removal block-stack puzzles."""

    width_min: int = 2
    width_max: int = 4
    depth_min: int = 2
    depth_max: int = 4
    original_max_height_min: int = 2
    original_max_height_max: int = 5
    total_cubes_max: int = 22
    removal_count_min: int = 1
    removal_count_max: int = 5


@dataclass(frozen=True)
class PuzzleBlockStackRenderParams:
    """Resolved rendering knobs for block-stack scenes."""

    canvas_width: int
    canvas_height: int
    scene_margin_left_px: int
    scene_margin_right_px: int
    scene_margin_top_px: int
    scene_margin_bottom_px: int
    structure_padding_px: int
    structure_pair_gap_px: int
    caption_gap_px: int
    caption_font_size_px: int
    panel_corner_radius_px: int
    border_width_px: int
    arrow_width_px: int
    arrow_head_length_px: int
    arrow_head_width_px: int
    view_orientation_index: int
    voxel_scale: float
    panel_fill_rgb: Tuple[int, int, int]
    border_color_rgb: Tuple[int, int, int]
    face_top_rgb: Tuple[int, int, int]
    face_right_rgb: Tuple[int, int, int]
    face_left_rgb: Tuple[int, int, int]
    face_shadow_rgb: Tuple[int, int, int]
    instruction_fill_rgb: Tuple[int, int, int]
    caption_fill_rgb: Tuple[int, int, int]
    caption_stroke_rgb: Tuple[int, int, int]
    arrow_rgb: Tuple[int, int, int]


def resolve_block_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the visual block-stack scene variant."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_PUZZLE_BLOCK_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def resolve_cube_removal_query_id(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic block-comparison variant."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_PUZZLE_BLOCK_REMOVAL_VARIANTS,
        task_id=str(task_id),
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def resolve_block_stack_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    instance_seed: int | None = None,
) -> PuzzleBlockStackRenderParams:
    """Resolve rendering params for block-stack scenes."""

    def _int(key: str, fallback: int) -> int:
        return resolve_render_int(
            params,
            render_defaults,
            str(key),
            int(fallback),
            instance_seed=instance_seed,
            namespace="puzzle_block_stack_render",
        )

    def _rgb(key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        return resolve_render_rgb(
            params,
            render_defaults,
            str(key),
            fallback,
            instance_seed=instance_seed,
            namespace="puzzle_block_stack_render",
        )

    def _float(key: str, fallback: float) -> float:
        return resolve_render_float(
            params,
            render_defaults,
            str(key),
            float(fallback),
            instance_seed=instance_seed,
            namespace="puzzle_block_stack_render",
        )

    return PuzzleBlockStackRenderParams(
        canvas_width=int(_int("canvas_width", 1200)),
        canvas_height=int(_int("canvas_height", 760)),
        scene_margin_left_px=int(_int("scene_margin_left_px", 64)),
        scene_margin_right_px=int(_int("scene_margin_right_px", 64)),
        scene_margin_top_px=int(_int("scene_margin_top_px", 56)),
        scene_margin_bottom_px=int(_int("scene_margin_bottom_px", 56)),
        structure_padding_px=int(_int("structure_padding_px", 44)),
        structure_pair_gap_px=int(_int("structure_pair_gap_px", 96)),
        caption_gap_px=int(_int("caption_gap_px", 16)),
        caption_font_size_px=int(_int("caption_font_size_px", 30)),
        panel_corner_radius_px=int(_int("panel_corner_radius_px", 30)),
        border_width_px=int(_int("border_width_px", 3)),
        arrow_width_px=int(_int("arrow_width_px", 6)),
        arrow_head_length_px=int(_int("arrow_head_length_px", 18)),
        arrow_head_width_px=int(_int("arrow_head_width_px", 18)),
        view_orientation_index=int(_int("view_orientation_index", 0)) % 2,
        voxel_scale=float(max(0.50, min(1.00, _float("voxel_scale", 1.0)))),
        panel_fill_rgb=_rgb("panel_fill_rgb", (248, 249, 252)),
        border_color_rgb=_rgb("border_color_rgb", (86, 94, 108)),
        face_top_rgb=_rgb("face_top_rgb", (240, 194, 108)),
        face_right_rgb=_rgb("face_right_rgb", (213, 161, 73)),
        face_left_rgb=_rgb("face_left_rgb", (187, 136, 56)),
        face_shadow_rgb=_rgb("face_shadow_rgb", (150, 104, 38)),
        instruction_fill_rgb=_rgb("instruction_fill_rgb", (238, 243, 250)),
        caption_fill_rgb=_rgb("caption_fill_rgb", (32, 38, 46)),
        caption_stroke_rgb=_rgb("caption_stroke_rgb", (255, 255, 255)),
        arrow_rgb=_rgb("arrow_rgb", (75, 88, 107)),
    )


def cube_face_visibility_from_height_rows(
    height_rows: Sequence[Sequence[int]],
    *,
    row_index: int,
    col_index: int,
    level_index: int,
) -> Dict[str, bool]:
    """Return which faces of one cube are visible in the fixed isometric view."""

    height = int(height_rows[int(row_index)][int(col_index)])
    row_count = int(len(height_rows))
    col_count = int(len(height_rows[0])) if row_count else 0
    right_neighbor_height = 0
    if int(col_index) + 1 < int(col_count):
        right_neighbor_height = int(height_rows[int(row_index)][int(col_index) + 1])
    front_neighbor_height = 0
    if int(row_index) + 1 < int(row_count):
        front_neighbor_height = int(height_rows[int(row_index) + 1][int(col_index)])
    return {
        "top": int(level_index) == int(height) - 1,
        "right": int(level_index) >= int(right_neighbor_height),
        "front": int(level_index) >= int(front_neighbor_height),
    }


def cube_records_from_height_rows(height_rows: Sequence[Sequence[int]]) -> List[Dict[str, Any]]:
    """Expand one height map into deterministic per-cube visibility records."""

    records: List[Dict[str, Any]] = []
    cube_index = 0
    for row_index, row in enumerate(height_rows):
        for col_index, raw_height in enumerate(row):
            height = int(raw_height)
            for level_index in range(int(height)):
                cube_index += 1
                visible_faces = cube_face_visibility_from_height_rows(
                    height_rows,
                    row_index=int(row_index),
                    col_index=int(col_index),
                    level_index=int(level_index),
                )
                records.append(
                    {
                        "cube_id": f"cube_{int(cube_index)}",
                        "row_index": int(row_index),
                        "col_index": int(col_index),
                        "level_index": int(level_index),
                        "visible_faces": dict(visible_faces),
                        "is_hidden": bool(not any(bool(value) for value in visible_faces.values())),
                    }
                )
    return records


def total_cubes_from_height_rows(height_rows: Sequence[Sequence[int]]) -> int:
    """Return the total occupied cube count for one height grid."""

    return int(sum(int(value) for row in height_rows for value in row))


def _zero_height_rows(row_count: int, col_count: int) -> List[List[int]]:
    """Return a zero-filled height grid."""

    return [[0 for _ in range(int(col_count))] for _ in range(int(row_count))]


def _removed_cube_records(
    *,
    original_height_rows: Sequence[Sequence[int]],
    remaining_height_rows: Sequence[Sequence[int]],
) -> List[Dict[str, Any]]:
    """Return deterministic metadata for cubes removed from the original stack."""

    removed_records: List[Dict[str, Any]] = []
    removed_index = 0
    for row_index, row in enumerate(original_height_rows):
        for col_index, original_height in enumerate(row):
            remaining_height = int(remaining_height_rows[int(row_index)][int(col_index)])
            for level_index in range(int(remaining_height), int(original_height)):
                removed_index += 1
                removed_records.append(
                    {
                        "removed_cube_id": f"removed_cube_{int(removed_index)}",
                        "row_index": int(row_index),
                        "col_index": int(col_index),
                        "level_index": int(level_index),
                    }
                )
    return removed_records


def _distribute_removals_across_columns(
    *,
    original_height_rows: Sequence[Sequence[int]],
    target_removal_count: int,
    rng,
) -> List[List[int]]:
    """Distribute a target number of removals across columns without emptying any column."""

    row_count = int(len(original_height_rows))
    col_count = int(len(original_height_rows[0])) if row_count else 0
    removal_rows = _zero_height_rows(int(row_count), int(col_count))
    remaining = int(target_removal_count)
    while int(remaining) > 0:
        feasible_positions = [
            (int(row_index), int(col_index))
            for row_index, row in enumerate(original_height_rows)
            for col_index, original_height in enumerate(row)
            if int(removal_rows[int(row_index)][int(col_index)]) < int(original_height) - 1
        ]
        if not feasible_positions:
            raise RuntimeError("cube-removal sampler resolved no feasible removable columns")
        chosen_row, chosen_col = feasible_positions[int(rng.randint(0, len(feasible_positions) - 1))]
        removal_rows[int(chosen_row)][int(chosen_col)] += 1
        remaining -= 1
    return removal_rows


def build_cube_removal_dataset_for_variant(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleCubeRemovalDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Build one deterministic cube-removal comparison dataset."""

    del query_id
    rng = spawn_rng(int(instance_seed), f"{task_id}.cube_removal_dataset")
    width_min = int(params.get("width_min", group_default(gen_defaults, "width_min", int(defaults.width_min))))
    width_max = int(params.get("width_max", group_default(gen_defaults, "width_max", int(defaults.width_max))))
    depth_min = int(params.get("depth_min", group_default(gen_defaults, "depth_min", int(defaults.depth_min))))
    depth_max = int(params.get("depth_max", group_default(gen_defaults, "depth_max", int(defaults.depth_max))))
    original_max_height_min = int(
        params.get(
            "original_max_height_min",
            group_default(gen_defaults, "original_max_height_min", int(defaults.original_max_height_min)),
        )
    )
    original_max_height_max = int(
        params.get(
            "original_max_height_max",
            group_default(gen_defaults, "original_max_height_max", int(defaults.original_max_height_max)),
        )
    )
    total_cubes_max = int(
        params.get("total_cubes_max", group_default(gen_defaults, "total_cubes_max", int(defaults.total_cubes_max)))
    )
    removal_count_min = int(
        params.get("removal_count_min", group_default(gen_defaults, "removal_count_min", int(defaults.removal_count_min)))
    )
    removal_count_max = int(
        params.get("removal_count_max", group_default(gen_defaults, "removal_count_max", int(defaults.removal_count_max)))
    )

    explicit_target_removal_count = params.get("target_removal_count")
    if explicit_target_removal_count is not None:
        target_removal_count = int(explicit_target_removal_count)
        if not (int(removal_count_min) <= int(target_removal_count) <= int(removal_count_max)):
            raise ValueError("target_removal_count is outside the configured removal-count support")
    else:
        removal_support = list(range(int(removal_count_min), int(removal_count_max) + 1))
        selection_index = int(
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}:target_removal_count",
            )
        )
        target_removal_count = int(removal_support[int(selection_index) % len(removal_support)])

    for _ in range(1000):
        if int(target_removal_count) >= 4:
            col_count = int(rng.randint(max(int(width_min), 3), int(width_max)))
            row_count = int(rng.randint(max(int(depth_min), 3), int(depth_max)))
            original_max_height = int(rng.randint(max(int(original_max_height_min), 3), int(original_max_height_max)))
        else:
            col_count = int(rng.randint(int(width_min), int(width_max)))
            row_count = int(rng.randint(int(depth_min), int(depth_max)))
            original_max_height = int(rng.randint(int(original_max_height_min), int(original_max_height_max)))

        max_removable_capacity = int(row_count * col_count * max(0, int(original_max_height) - 1))
        if int(max_removable_capacity) < int(target_removal_count):
            continue

        original_height_rows = [
            [int(rng.randint(1, int(original_max_height))) for _ in range(int(col_count))]
            for _ in range(int(row_count))
        ]
        original_total = int(total_cubes_from_height_rows(original_height_rows))
        removable_capacity = int(original_total - (int(row_count) * int(col_count)))

        while int(removable_capacity) < int(target_removal_count):
            feasible_raise_positions = [
                (int(row_index), int(col_index))
                for row_index, row in enumerate(original_height_rows)
                for col_index, height in enumerate(row)
                if int(height) < int(original_max_height)
            ]
            if not feasible_raise_positions:
                break
            if int(original_total) >= int(total_cubes_max):
                break
            chosen_row, chosen_col = feasible_raise_positions[int(rng.randint(0, len(feasible_raise_positions) - 1))]
            original_height_rows[int(chosen_row)][int(chosen_col)] += 1
            original_total += 1
            removable_capacity += 1

        if int(original_total) > int(total_cubes_max):
            continue
        if int(removable_capacity) < int(target_removal_count):
            continue

        removal_rows = _distribute_removals_across_columns(
            original_height_rows=original_height_rows,
            target_removal_count=int(target_removal_count),
            rng=rng,
        )
        remaining_height_rows = [
            [
                int(original_height_rows[int(row_index)][int(col_index)] - removal_rows[int(row_index)][int(col_index)])
                for col_index in range(int(col_count))
            ]
            for row_index in range(int(row_count))
        ]
        remaining_total = int(total_cubes_from_height_rows(remaining_height_rows))
        if int(remaining_total) <= 0:
            continue

        changed_column_count = sum(
            1
            for row_index in range(int(row_count))
            for col_index in range(int(col_count))
            if int(removal_rows[int(row_index)][int(col_index)]) > 0
        )
        removed_cube_records = _removed_cube_records(
            original_height_rows=original_height_rows,
            remaining_height_rows=remaining_height_rows,
        )
        if int(len(removed_cube_records)) != int(target_removal_count):
            continue

        original_cube_records = cube_records_from_height_rows(original_height_rows)
        remaining_cube_records = cube_records_from_height_rows(remaining_height_rows)
        return {
            "original_height_rows": [[int(value) for value in row] for row in original_height_rows],
            "remaining_height_rows": [[int(value) for value in row] for row in remaining_height_rows],
            "row_count": int(row_count),
            "col_count": int(col_count),
            "row_count_range": [int(depth_min), int(depth_max)],
            "col_count_range": [int(width_min), int(width_max)],
            "original_max_height": int(original_max_height),
            "original_max_height_range": [int(original_max_height_min), int(original_max_height_max)],
            "original_total_cubes": int(original_total),
            "remaining_total_cubes": int(remaining_total),
            "total_cubes_max": int(total_cubes_max),
            "removal_count": int(target_removal_count),
            "removal_count_range": [int(removal_count_min), int(removal_count_max)],
            "changed_column_count": int(changed_column_count),
            "original_cube_records": [dict(record) for record in original_cube_records],
            "remaining_cube_records": [dict(record) for record in remaining_cube_records],
            "removed_cube_records": [dict(record) for record in removed_cube_records],
            "original_structure_bbox_id": "original_structure",
            "remaining_structure_bbox_id": "remaining_structure",
            "solver_trace": {
                "row_count": int(row_count),
                "col_count": int(col_count),
                "original_max_height": int(original_max_height),
                "target_removal_count": int(target_removal_count),
                "changed_column_count": int(changed_column_count),
                "removal_rows": [[int(value) for value in row] for row in removal_rows],
            },
            "question_format": "cube_removal_count",
            "view_family": "isometric_block_comparison",
        }
    raise RuntimeError("unable to sample a cube-removal block comparison within configured bounds")


__all__ = [
    "PuzzleBlockStackRenderParams",
    "PuzzleCubeRemovalDefaults",
    "SUPPORTED_PUZZLE_BLOCK_REMOVAL_VARIANTS",
    "SUPPORTED_PUZZLE_BLOCK_SCENE_VARIANTS",
    "build_cube_removal_dataset_for_variant",
    "cube_face_visibility_from_height_rows",
    "cube_records_from_height_rows",
    "resolve_block_scene_variant",
    "resolve_block_stack_render_params",
    "resolve_cube_removal_query_id",
    "total_cubes_from_height_rows",
]
