"""Puzzle spatial task for MathVision-style cube-structure counting."""

from __future__ import annotations

from dataclasses import replace
from itertools import product
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.named_colors import available_named_colors, darken_color, named_color
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.block_stack_scene import render_puzzle_block_comparison_scene, render_puzzle_block_structure_scene
from ..shared.common import projected_puzzle_bbox_annotation, resolve_puzzle_axis_variant
from ..shared.complexity import (
    build_puzzle_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_puzzle_complexity_weights,
)
from ..shared.fixed_query_task import FixedPuzzleQueryVariantTaskMixin
from ..shared.params import resolve_puzzle_int_param
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.spatial_blocks_common import (
    cube_records_from_height_rows,
    resolve_block_scene_variant,
    resolve_block_stack_render_params,
    total_cubes_from_height_rows,
)
from ..shared.solid_view_query import SolidViewCountGenerator
from ..shared.solid_view_query import SolidViewProjectionConsistencyGenerator
from ..shared.solid_view_query import SolidViewProjectionMatchGenerator
from ..shared.visual_defaults import load_puzzle_background_defaults, load_puzzle_noise_defaults


TASK_ID = "puzzles_spatial_cube_structure_internal"
CUBE_COUNT_TASK_ID = "task_puzzles__voxel_cube__cube_count"
CUBE_STRUCTURE_CHANGE_COUNT_TASK_ID = "task_puzzles__voxel_cube__cube_structure_change_count"
CUBE_PAINTED_FACE_COUNT_TASK_ID = "task_puzzles__voxel_cube__cube_painted_face_count"
CUBE_VISIBLE_PROJECTION_COUNT_TASK_ID = "task_puzzles__voxel_cube__cube_visible_projection_count"
CUBE_PROJECTION_MATCH_TASK_ID = "task_puzzles__voxel_cube__cube_projection_match_label"
CUBE_PROJECTION_CONSISTENCY_TASK_ID = "task_puzzles__voxel_cube__cube_projection_consistency_label"

INTERNAL_QUERY_IDS: Tuple[str, ...] = (
    "total_cube_count",
    "missing_to_complete_cuboid_count",
    "removed_cube_count",
    "painted_exterior_face_count",
    "exact_k_painted_faces_cube_count",
    "view_visible_count",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "cube_count",
    "cube_structure_change_count",
    "painted_face_count",
    "visible_cube_count",
    "projection_match_label",
    "projection_consistency_label",
)
CHANGE_TYPES: Tuple[str, ...] = ("missing_to_complete", "removed")
PAINTED_QUERY_TYPES: Tuple[str, ...] = ("exterior_face_total", "exact_k_faces_cube_count")
_INTERNAL_TO_PUBLIC_QUERY_ID: Dict[str, str] = {
    "total_cube_count": "cube_count",
    "missing_to_complete_cuboid_count": "cube_structure_change_count",
    "removed_cube_count": "cube_structure_change_count",
    "painted_exterior_face_count": "painted_face_count",
    "exact_k_painted_faces_cube_count": "painted_face_count",
    "view_visible_count": "visible_cube_count",
}
_CHANGE_TYPE_TO_INTERNAL: Dict[str, str] = {
    "missing_to_complete": "missing_to_complete_cuboid_count",
    "removed": "removed_cube_count",
}
_PAINTED_QUERY_TO_INTERNAL: Dict[str, str] = {
    "exterior_face_total": "painted_exterior_face_count",
    "exact_k_faces_cube_count": "exact_k_painted_faces_cube_count",
}
_INTERNAL_TO_CHANGE_TYPE: Dict[str, str] = {
    str(internal): str(change_type)
    for change_type, internal in _CHANGE_TYPE_TO_INTERNAL.items()
}
_INTERNAL_TO_PAINTED_QUERY: Dict[str, str] = {
    str(internal): str(query_type)
    for query_type, internal in _PAINTED_QUERY_TO_INTERNAL.items()
}
_SOLID_VIEW_SOURCE_QUERY_IDS: Tuple[str, ...] = (
    "view_visible_count",
    "top_view_visible_count",
    "front_view_visible_count",
    "right_view_visible_count",
)

_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "spatial")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_puzzle_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_puzzle_background_defaults(task_group="spatial")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="spatial", apply_prob=0.0)
_DEFAULT_CUBE_COLOR_NAME_SUPPORT: Tuple[str, ...] = ("orange", "blue", "green", "purple", "cyan", "magenta", "brown")


def _axis_positive_count(probabilities: Mapping[str, float], supported_values: Sequence[str]) -> int:
    return max(1, len([str(value) for value in supported_values if float(probabilities.get(str(value), 0.0)) > 0.0]))


def _object_description_key(*, internal_query_id: str, scene_variant: str) -> str:
    """Resolve the prompt object description key for one cube-structure query."""

    if str(internal_query_id) in {
        "total_cube_count",
        "painted_exterior_face_count",
        "exact_k_painted_faces_cube_count",
    }:
        return f"object_description_single_stack_{str(scene_variant)}"
    if str(internal_query_id) in {"missing_to_complete_cuboid_count", "removed_cube_count"}:
        return f"object_description_change_pair_{str(scene_variant)}"
    return f"object_description_{str(scene_variant)}"


def _decouple_sampling_by_divisor(params: Mapping[str, Any], *, divisor: int) -> Mapping[str, Any]:
    _ = int(divisor)
    return params


def _resolve_public_query_axis(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float], bool]:
    variant_params = dict(params)
    source_query_id = False
    explicit_variant = variant_params.get("query_id")
    if explicit_variant is not None:
        variant = str(explicit_variant).strip()
        if variant in set(INTERNAL_QUERY_IDS):
            variant_params["query_id"] = str(_INTERNAL_TO_PUBLIC_QUERY_ID[variant])
            source_query_id = True
        elif variant in set(_SOLID_VIEW_SOURCE_QUERY_IDS):
            variant_params["query_id"] = "visible_cube_count"
            source_query_id = True
    selected_query, probabilities = resolve_puzzle_axis_variant(
        params=variant_params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_QUERY_IDS,
        task_id=TASK_ID,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )
    return str(selected_query), dict(probabilities), bool(source_query_id)


def _resolve_subquery_axis(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    supported_values: Sequence[str],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    axis_namespace: str,
) -> Tuple[str, Dict[str, float]]:
    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=tuple(str(value) for value in supported_values),
        task_id=TASK_ID,
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        axis_namespace=str(axis_namespace),
    )


def _resolve_query_contract(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, str, Dict[str, Any], int]:
    """Resolve public query axis plus the internal construction query."""

    public_query_id, query_id_probabilities, source_query_id = _resolve_public_query_axis(
        params,
        instance_seed=int(instance_seed),
    )
    query_params = dict(params)
    explicit_variant = params.get("query_id")
    if explicit_variant is not None and str(explicit_variant) in set(INTERNAL_QUERY_IDS):
        internal_query_id = str(explicit_variant)
        if internal_query_id in _INTERNAL_TO_CHANGE_TYPE:
            query_params["change_type"] = str(_INTERNAL_TO_CHANGE_TYPE[internal_query_id])
        if internal_query_id in _INTERNAL_TO_PAINTED_QUERY:
            query_params["painted_query"] = str(_INTERNAL_TO_PAINTED_QUERY[internal_query_id])
        subquery_probabilities: Dict[str, float] = {}
        sampling_axis_divisor = 1
    elif str(public_query_id) == "cube_count":
        internal_query_id = "total_cube_count"
        subquery_probabilities = {}
        sampling_axis_divisor = _axis_positive_count(query_id_probabilities, SUPPORTED_QUERY_IDS)
    elif str(public_query_id) == "cube_structure_change_count":
        change_params = _decouple_sampling_by_divisor(
            query_params,
            divisor=_axis_positive_count(query_id_probabilities, SUPPORTED_QUERY_IDS)
            if params.get("query_id") is None
            else 1,
        )
        change_type, change_type_probabilities = _resolve_subquery_axis(
            change_params,
            instance_seed=int(instance_seed),
            supported_values=CHANGE_TYPES,
            explicit_key="change_type",
            weights_key="change_type_weights",
            balance_flag_key="balanced_change_type_sampling",
            axis_namespace="change_type",
        )
        internal_query_id = str(_CHANGE_TYPE_TO_INTERNAL[str(change_type)])
        query_params["change_type"] = str(change_type)
        subquery_probabilities = {"change_type_probabilities": dict(change_type_probabilities)}
        sampling_axis_divisor = (
            _axis_positive_count(query_id_probabilities, SUPPORTED_QUERY_IDS)
            if params.get("query_id") is None
            else 1
        )
        if params.get("change_type") is None:
            sampling_axis_divisor *= _axis_positive_count(change_type_probabilities, CHANGE_TYPES)
    elif str(public_query_id) == "visible_cube_count":
        internal_query_id = "view_visible_count"
        subquery_probabilities = {}
        sampling_axis_divisor = (
            _axis_positive_count(query_id_probabilities, SUPPORTED_QUERY_IDS)
            if params.get("query_id") is None
            else 1
        )
    elif str(public_query_id) == "projection_match_label":
        internal_query_id = "projection_match_label"
        subquery_probabilities = {}
        sampling_axis_divisor = (
            _axis_positive_count(query_id_probabilities, SUPPORTED_QUERY_IDS)
            if params.get("query_id") is None
            else 1
        )
    elif str(public_query_id) == "projection_consistency_label":
        internal_query_id = "projection_consistency_label"
        subquery_probabilities = {}
        sampling_axis_divisor = (
            _axis_positive_count(query_id_probabilities, SUPPORTED_QUERY_IDS)
            if params.get("query_id") is None
            else 1
        )
    else:
        painted_params = _decouple_sampling_by_divisor(
            query_params,
            divisor=_axis_positive_count(query_id_probabilities, SUPPORTED_QUERY_IDS)
            if params.get("query_id") is None
            else 1,
        )
        painted_query, painted_query_probabilities = _resolve_subquery_axis(
            painted_params,
            instance_seed=int(instance_seed),
            supported_values=PAINTED_QUERY_TYPES,
            explicit_key="painted_query",
            weights_key="painted_query_weights",
            balance_flag_key="balanced_painted_query_sampling",
            axis_namespace="painted_query",
        )
        internal_query_id = str(_PAINTED_QUERY_TO_INTERNAL[str(painted_query)])
        query_params["painted_query"] = str(painted_query)
        subquery_probabilities = {"painted_query_probabilities": dict(painted_query_probabilities)}
        sampling_axis_divisor = (
            _axis_positive_count(query_id_probabilities, SUPPORTED_QUERY_IDS)
            if params.get("query_id") is None
            else 1
        )
        if params.get("painted_query") is None:
            sampling_axis_divisor *= _axis_positive_count(painted_query_probabilities, PAINTED_QUERY_TYPES)

    query_params["query_id"] = str(public_query_id)
    query_params["internal_query_id"] = str(internal_query_id)
    if bool(source_query_id):
        query_params["source_query_id"] = str(explicit_variant)
    query_metadata: Dict[str, Any] = {
        "query_id_probabilities": dict(query_id_probabilities),
        "internal_query_id": str(internal_query_id),
        **dict(subquery_probabilities),
    }
    if str(internal_query_id) in _INTERNAL_TO_CHANGE_TYPE:
        query_metadata["change_type"] = str(_INTERNAL_TO_CHANGE_TYPE[str(internal_query_id)])
    if str(internal_query_id) in _INTERNAL_TO_PAINTED_QUERY:
        query_metadata["painted_query"] = str(_INTERNAL_TO_PAINTED_QUERY[str(internal_query_id)])
    return str(public_query_id), str(internal_query_id), dict(query_metadata), int(sampling_axis_divisor)


def _support_range(params: Mapping[str, Any], *, key_min: str, key_max: str, fallback_min: int, fallback_max: int) -> Tuple[int, ...]:
    low = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, str(key_min), int(fallback_min)))
    high = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, str(key_max), int(fallback_max)))
    if int(low) > int(high):
        raise ValueError(f"{key_min}/{key_max} must form a non-empty support")
    return tuple(range(int(low), int(high) + 1))


def _selected_support_value(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    support: Sequence[int],
    explicit_key: str,
    namespace: str,
) -> int:
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in {int(value) for value in support}:
            raise ValueError(f"{explicit_key} must be one of {tuple(int(value) for value in support)}")
        return int(selected)
    selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:{namespace}",
    )
    return int(list(int(value) for value in support)[int(selection_index) % len(support)])


def _readable_edge_cells(row_count: int, col_count: int) -> Tuple[Tuple[int, int], ...]:
    return tuple(
        (int(row_index), int(col_index))
        for row_index in range(int(row_count))
        for col_index in range(int(col_count))
        if int(row_index) == int(row_count) - 1 or int(col_index) == int(col_count) - 1
    )


def _hidden_cube_count(height_rows: Sequence[Sequence[int]]) -> int:
    return sum(1 for record in cube_records_from_height_rows(height_rows) if bool(record["is_hidden"]))


def _actual_max_height(height_rows: Sequence[Sequence[int]]) -> int:
    return max(
        (int(value) for row in height_rows for value in row),
        default=0,
    )


def _distribute_extra_height_on_readable_edges(
    rng,
    *,
    height_rows: List[List[int]],
    remaining: int,
    max_height: int,
) -> bool:
    row_count = int(len(height_rows))
    col_count = int(len(height_rows[0])) if row_count else 0
    readable_cells = _readable_edge_cells(int(row_count), int(col_count))
    while int(remaining) > 0:
        candidates = [
            (int(row_index), int(col_index))
            for row_index, col_index in readable_cells
            if int(height_rows[int(row_index)][int(col_index)]) < int(max_height)
        ]
        if not candidates:
            return False
        row_index, col_index = candidates[int(rng.randint(0, len(candidates) - 1))]
        height_rows[int(row_index)][int(col_index)] += 1
        remaining -= 1
    return True


def _sample_height_rows_with_total(
    rng,
    *,
    target_total: int,
    params: Mapping[str, Any],
    target_max_height: int | None = None,
) -> Tuple[List[List[int]], Dict[str, int]]:
    width_min = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "width_min", 2))
    width_max = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "width_max", 4))
    depth_min = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "depth_min", 2))
    depth_max = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "depth_max", 4))
    height_min = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "height_min", 2))
    height_max = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "height_max", 4))
    for _ in range(600):
        if int(rng.randint(0, 1)) == 0:
            row_count = 1
            col_count = int(rng.randint(int(width_min), int(width_max)))
        else:
            row_count = int(rng.randint(int(depth_min), int(depth_max)))
            col_count = 1
        max_height = (
            int(target_max_height)
            if target_max_height is not None
            else int(rng.randint(int(height_min), int(height_max)))
        )
        if not (int(height_min) <= int(max_height) <= int(height_max)):
            raise ValueError("target_max_height must be within height_min/height_max")
        cell_count = int(row_count * col_count)
        readable_capacity = int(cell_count * max(1, int(max_height)))
        if not (int(cell_count) <= int(target_total) <= int(readable_capacity)):
            continue
        height_rows = [[1 for _ in range(int(col_count))] for _ in range(int(row_count))]
        remaining = int(target_total) - int(cell_count)
        if _distribute_extra_height_on_readable_edges(
            rng,
            height_rows=height_rows,
            remaining=int(remaining),
            max_height=int(max_height),
        ) and int(_hidden_cube_count(height_rows)) == 0 and int(_actual_max_height(height_rows)) == int(max_height):
            return (
                [[int(value) for value in row] for row in height_rows],
                {
                    "row_count": int(row_count),
                    "col_count": int(col_count),
                    "max_height": int(max_height),
                    "readable_wall_stack": True,
                },
            )
    raise RuntimeError("unable to sample cube structure with the requested total")


def _sample_full_and_partial_cuboid(
    rng,
    *,
    missing_count: int,
    params: Mapping[str, Any],
    target_height: int | None = None,
) -> Tuple[List[List[int]], List[List[int]], Dict[str, int], List[Dict[str, int]]]:
    width_min = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "cuboid_width_min", 2))
    width_max = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "cuboid_width_max", 4))
    depth_min = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "cuboid_depth_min", 2))
    depth_max = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "cuboid_depth_max", 4))
    height_min = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "cuboid_height_min", 2))
    height_max = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "cuboid_height_max", 4))
    for _ in range(600):
        if int(rng.randint(0, 1)) == 0:
            row_count = 1
            col_count = int(rng.randint(int(width_min), int(width_max)))
        else:
            row_count = int(rng.randint(int(depth_min), int(depth_max)))
            col_count = 1
        height = (
            int(target_height)
            if target_height is not None
            else int(rng.randint(int(height_min), int(height_max)))
        )
        if not (int(height_min) <= int(height) <= int(height_max)):
            raise ValueError("target_height must be within cuboid_height_min/cuboid_height_max")
        readable_cells = _readable_edge_cells(int(row_count), int(col_count))
        capacity = int(len(readable_cells) * max(0, int(height) - 1))
        if int(capacity) < int(missing_count):
            continue
        full_rows = [[int(height) for _ in range(int(col_count))] for _ in range(int(row_count))]
        partial_rows = [[int(height) for _ in range(int(col_count))] for _ in range(int(row_count))]
        missing_records: List[Dict[str, int]] = []
        remaining = int(missing_count)
        while int(remaining) > 0:
            candidates = [
                (int(row_index), int(col_index))
                for row_index, col_index in readable_cells
                if int(partial_rows[int(row_index)][int(col_index)]) > 1
            ]
            if not candidates:
                break
            row_index, col_index = candidates[int(rng.randint(0, len(candidates) - 1))]
            level_index = int(partial_rows[int(row_index)][int(col_index)] - 1)
            partial_rows[int(row_index)][int(col_index)] -= 1
            missing_records.append(
                {
                    "row_index": int(row_index),
                    "col_index": int(col_index),
                    "level_index": int(level_index),
                }
            )
            remaining -= 1
        if int(remaining) == 0:
            return (
                [[int(value) for value in row] for row in full_rows],
                [[int(value) for value in row] for row in partial_rows],
                {"row_count": int(row_count), "col_count": int(col_count), "height": int(height)},
                [dict(record) for record in missing_records],
            )
    raise RuntimeError("unable to sample complete/partial cuboid with requested missing count")


def _occupied_cubes(height_rows: Sequence[Sequence[int]]) -> Tuple[Tuple[int, int, int], ...]:
    cubes: List[Tuple[int, int, int]] = []
    for row_index, row in enumerate(height_rows):
        for col_index, height in enumerate(row):
            for level_index in range(int(height)):
                cubes.append((int(row_index), int(col_index), int(level_index)))
    return tuple(cubes)


def _exposed_face_counts(height_rows: Sequence[Sequence[int]]) -> Dict[Tuple[int, int, int], int]:
    occupied = set(_occupied_cubes(height_rows))
    directions = (
        (1, 0, 0),
        (-1, 0, 0),
        (0, 1, 0),
        (0, -1, 0),
        (0, 0, 1),
        (0, 0, -1),
    )
    counts: Dict[Tuple[int, int, int], int] = {}
    for cube in sorted(occupied):
        counts[tuple(cube)] = sum(
            1
            for dr, dc, dz in directions
            if (int(cube[0] + dr), int(cube[1] + dc), int(cube[2] + dz)) not in occupied
        )
    return dict(counts)


def _painted_cube_records(height_rows: Sequence[Sequence[int]]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    exposed_counts = _exposed_face_counts(height_rows)
    for cube_index, cube in enumerate(sorted(exposed_counts), start=1):
        records.append(
            {
                "cube_id": f"cube_{int(cube_index)}",
                "row_index": int(cube[0]),
                "col_index": int(cube[1]),
                "level_index": int(cube[2]),
                "painted_face_count": int(exposed_counts[tuple(cube)]),
            }
        )
    return records


def _painted_exterior_face_count_support(
    *,
    params: Mapping[str, Any],
    total_support: Sequence[int],
    target_max_height: int,
) -> Tuple[int, ...]:
    width_min = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "width_min", 2))
    width_max = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "width_max", 4))
    depth_min = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "depth_min", 2))
    depth_max = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "depth_max", 4))
    lengths = sorted(
        set(range(int(width_min), int(width_max) + 1))
        | set(range(int(depth_min), int(depth_max) + 1))
    )
    total_values = {int(value) for value in total_support}
    support: set[int] = set()
    for length in lengths:
        for column_heights in product(range(1, int(target_max_height) + 1), repeat=int(length)):
            if max(int(value) for value in column_heights) != int(target_max_height):
                continue
            if sum(int(value) for value in column_heights) not in total_values:
                continue
            support.add(
                sum(
                    int(face_count)
                    for face_count in _exposed_face_counts([list(int(value) for value in column_heights)]).values()
                )
            )
    if not support:
        raise RuntimeError("unable to resolve painted exterior face support")
    return tuple(sorted(int(value) for value in support))


def _single_structure_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    sampling_axis_divisor: int,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{query_id}")
    answer_params = _decouple_sampling_by_divisor(
        params,
        divisor=int(sampling_axis_divisor),
    )
    total_support = _support_range(
        params,
        key_min="total_cube_count_min",
        key_max="total_cube_count_max",
        fallback_min=8,
        fallback_max=22,
    )
    if str(query_id) == "painted_exterior_face_count":
        total_support = _support_range(
            params,
            key_min="painted_exterior_total_cube_count_min",
            key_max="painted_exterior_total_cube_count_max",
            fallback_min=int(min(total_support)),
            fallback_max=int(max(total_support)),
        )
    target_total = _selected_support_value(
        params=answer_params,
        instance_seed=int(instance_seed),
        support=total_support,
        explicit_key="target_total_cube_count",
        namespace=f"{query_id}.total",
    )
    height_support = _support_range(
        params,
        key_min="height_min",
        key_max="height_max",
        fallback_min=2,
        fallback_max=3,
    )
    if str(query_id) == "painted_exterior_face_count":
        height_support = _support_range(
            params,
            key_min="painted_exterior_height_min",
            key_max="painted_exterior_height_max",
            fallback_min=int(min(height_support)),
            fallback_max=int(max(height_support)),
        )
    target_max_height = _selected_support_value(
        params=answer_params,
        instance_seed=int(instance_seed),
        support=height_support,
        explicit_key="target_max_height",
        namespace=f"{query_id}.max_height",
    )
    painted_face_target_k_support = tuple(
        int(value)
        for value in params.get(
            "painted_face_target_k_support",
            group_default(_GEN_DEFAULTS, "painted_face_target_k_support", (2, 3, 4, 5)),
        )
    )
    exact_answer_support = _support_range(
        params,
        key_min="exact_k_painted_cube_count_min",
        key_max="exact_k_painted_cube_count_max",
        fallback_min=0,
        fallback_max=8,
    )
    target_exact_k_count = None
    if str(query_id) == "exact_k_painted_faces_cube_count":
        target_exact_k_count = _selected_support_value(
            params=answer_params,
            instance_seed=int(instance_seed),
            support=exact_answer_support,
            explicit_key="target_exact_k_painted_faces_cube_count",
            namespace=f"{query_id}.answer",
        )
    painted_answer_support: Tuple[int, ...] = ()
    target_painted_exterior_face_count = None
    if str(query_id) == "painted_exterior_face_count":
        painted_answer_support = _painted_exterior_face_count_support(
            params=params,
            total_support=total_support,
            target_max_height=int(target_max_height),
        )
        target_painted_exterior_face_count = _selected_support_value(
            params=answer_params,
            instance_seed=int(instance_seed),
            support=painted_answer_support,
            explicit_key="target_painted_exterior_face_count",
            namespace=f"{query_id}.answer.height_{int(target_max_height)}",
        )

    for _ in range(3000):
        if str(query_id) in {"exact_k_painted_faces_cube_count", "painted_exterior_face_count"} and params.get("target_total_cube_count") is None:
            sampled_total = int(total_support[int(rng.randint(0, len(total_support) - 1))])
        else:
            sampled_total = int(target_total)
        height_rows, shape_meta = _sample_height_rows_with_total(
            rng,
            target_total=int(sampled_total),
            params=params,
            target_max_height=int(target_max_height),
        )
        cube_records = cube_records_from_height_rows(height_rows)
        painted_records = _painted_cube_records(height_rows)
        total_cubes = int(total_cubes_from_height_rows(height_rows))
        exposed_counts = [int(record["painted_face_count"]) for record in painted_records]
        painted_exterior_face_count = int(sum(exposed_counts))
        if target_painted_exterior_face_count is not None and int(painted_exterior_face_count) != int(target_painted_exterior_face_count):
            continue
        if str(query_id) == "exact_k_painted_faces_cube_count" and params.get("painted_face_target_k") is None:
            painted_face_target_k = int(painted_face_target_k_support[int(rng.randint(0, len(painted_face_target_k_support) - 1))])
        else:
            painted_face_target_k = _selected_support_value(
                params=answer_params,
                instance_seed=int(instance_seed),
                support=painted_face_target_k_support,
                explicit_key="painted_face_target_k",
                namespace=f"{query_id}.painted_face_target_k",
            )
        exact_k_count = int(sum(1 for count in exposed_counts if int(count) == int(painted_face_target_k)))
        if target_exact_k_count is not None and int(exact_k_count) != int(target_exact_k_count):
            continue

        if str(query_id) == "total_cube_count":
            answer_value = int(total_cubes)
            answer_support = list(total_support)
        elif str(query_id) == "painted_exterior_face_count":
            answer_value = int(painted_exterior_face_count)
            answer_support = list(painted_answer_support)
        else:
            answer_value = int(exact_k_count)
            answer_support = list(exact_answer_support)

        return {
            "height_rows": [[int(value) for value in row] for row in height_rows],
            "cube_records": [dict(record) for record in cube_records],
            "painted_cube_records": [dict(record) for record in painted_records],
            "row_count": int(shape_meta["row_count"]),
            "col_count": int(shape_meta["col_count"]),
            "max_height": int(shape_meta["max_height"]),
            "height_support": [int(value) for value in height_support],
            "height_sampling_policy": "seeded_balanced",
            "total_cubes": int(total_cubes),
            "painted_exterior_face_count": int(painted_exterior_face_count),
            "painted_face_target_k": int(painted_face_target_k),
            "exact_k_painted_faces_cube_count": int(exact_k_count),
            "answer_value": int(answer_value),
            "answer_support": [int(value) for value in answer_support],
            "supporting_structure_ids": ["cube_structure"],
            "structure_bbox_id": "cube_structure",
            "question_format": str(query_id),
            "view_family": "isometric_cube_structure",
            "caption": "Cube structure",
            "is_comparison": False,
        }
    raise RuntimeError("unable to sample single cube-structure dataset")


def _missing_cuboid_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    sampling_axis_divisor: int,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.missing_to_complete_cuboid_count")
    answer_params = _decouple_sampling_by_divisor(
        params,
        divisor=int(sampling_axis_divisor),
    )
    missing_support = _support_range(
        params,
        key_min="missing_cube_count_min",
        key_max="missing_cube_count_max",
        fallback_min=1,
        fallback_max=8,
    )
    target_missing = _selected_support_value(
        params=answer_params,
        instance_seed=int(instance_seed),
        support=missing_support,
        explicit_key="target_missing_cube_count",
        namespace="missing_to_complete_cuboid_count.answer",
    )
    height_support = _support_range(
        params,
        key_min="cuboid_height_min",
        key_max="cuboid_height_max",
        fallback_min=2,
        fallback_max=3,
    )
    target_height = _selected_support_value(
        params=answer_params,
        instance_seed=int(instance_seed),
        support=height_support,
        explicit_key="target_cuboid_height",
        namespace="missing_to_complete_cuboid_count.height",
    )
    full_rows, partial_rows, shape_meta, missing_records = _sample_full_and_partial_cuboid(
        rng,
        missing_count=int(target_missing),
        params=params,
        target_height=int(target_height),
    )
    full_total = int(total_cubes_from_height_rows(full_rows))
    partial_total = int(total_cubes_from_height_rows(partial_rows))
    return {
        "original_height_rows": [[int(value) for value in row] for row in full_rows],
        "remaining_height_rows": [[int(value) for value in row] for row in partial_rows],
        "original_cube_records": [dict(record) for record in cube_records_from_height_rows(full_rows)],
        "remaining_cube_records": [dict(record) for record in cube_records_from_height_rows(partial_rows)],
        "missing_cube_records": [dict(record) for record in missing_records],
        "row_count": int(shape_meta["row_count"]),
        "col_count": int(shape_meta["col_count"]),
        "cuboid_height": int(shape_meta["height"]),
        "height_support": [int(value) for value in height_support],
        "height_sampling_policy": "seeded_balanced",
        "missing_cells_restricted_to_readable_edges": True,
        "original_total_cubes": int(full_total),
        "remaining_total_cubes": int(partial_total),
        "missing_cube_count": int(target_missing),
        "answer_value": int(target_missing),
        "answer_support": [int(value) for value in missing_support],
        "supporting_structure_ids": ["original_structure", "remaining_structure"],
        "original_structure_bbox_id": "original_structure",
        "remaining_structure_bbox_id": "remaining_structure",
        "question_format": "missing_to_complete_cuboid_count",
        "view_family": "isometric_block_completion_comparison",
        "original_caption": "Complete",
        "remaining_caption": "Partial",
        "is_comparison": True,
    }


def _removed_cube_records_from_rows(
    *,
    original_height_rows: Sequence[Sequence[int]],
    remaining_height_rows: Sequence[Sequence[int]],
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    removed_index = 0
    for row_index, row in enumerate(original_height_rows):
        for col_index, original_height in enumerate(row):
            remaining_height = int(remaining_height_rows[int(row_index)][int(col_index)])
            for level_index in range(int(remaining_height), int(original_height)):
                removed_index += 1
                records.append(
                    {
                        "removed_cube_id": f"removed_cube_{int(removed_index)}",
                        "row_index": int(row_index),
                        "col_index": int(col_index),
                        "level_index": int(level_index),
                    }
                )
    return [dict(record) for record in records]


def _sample_readable_removal_pair(
    rng,
    *,
    removed_count: int,
    params: Mapping[str, Any],
    target_max_height: int | None = None,
) -> Tuple[List[List[int]], List[List[int]], Dict[str, int], List[Dict[str, Any]]]:
    total_support = _support_range(
        params,
        key_min="total_cube_count_min",
        key_max="total_cube_count_max",
        fallback_min=8,
        fallback_max=22,
    )
    width_min = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "width_min", 2))
    width_max = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "width_max", 4))
    depth_min = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "depth_min", 2))
    depth_max = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "depth_max", 4))
    height_min = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "height_min", 2))
    height_max = int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "height_max", 4))
    for _ in range(800):
        if int(rng.randint(0, 1)) == 0:
            row_count = 1
            col_count = int(rng.randint(int(width_min), int(width_max)))
        else:
            row_count = int(rng.randint(int(depth_min), int(depth_max)))
            col_count = 1
        max_height = (
            int(target_max_height)
            if target_max_height is not None
            else int(rng.randint(int(height_min), int(height_max)))
        )
        if not (int(height_min) <= int(max_height) <= int(height_max)):
            raise ValueError("target_max_height must be within height_min/height_max")
        cell_count = int(row_count * col_count)
        readable_cells = _readable_edge_cells(int(row_count), int(col_count))
        capacity = int(len(readable_cells) * max(0, int(max_height) - 1))
        if int(capacity) < int(removed_count):
            continue
        original_total_min = max(int(cell_count + removed_count), int(min(total_support)))
        original_total_max = min(int(cell_count + capacity), int(max(total_support)))
        if int(original_total_min) > int(original_total_max):
            continue
        original_total = int(rng.randint(int(original_total_min), int(original_total_max)))
        original_rows = [[1 for _ in range(int(col_count))] for _ in range(int(row_count))]
        if not _distribute_extra_height_on_readable_edges(
            rng,
            height_rows=original_rows,
            remaining=int(original_total - cell_count),
            max_height=int(max_height),
        ):
            continue
        if int(_hidden_cube_count(original_rows)) != 0 or int(_actual_max_height(original_rows)) != int(max_height):
            continue
        remaining_rows = [[int(value) for value in row] for row in original_rows]
        remaining_to_remove = int(removed_count)
        while int(remaining_to_remove) > 0:
            candidates = [
                (int(row_index), int(col_index))
                for row_index, col_index in readable_cells
                if int(remaining_rows[int(row_index)][int(col_index)]) > 1
            ]
            if not candidates:
                break
            row_index, col_index = candidates[int(rng.randint(0, len(candidates) - 1))]
            remaining_rows[int(row_index)][int(col_index)] -= 1
            remaining_to_remove -= 1
        if int(remaining_to_remove) != 0:
            continue
        if int(_hidden_cube_count(remaining_rows)) != 0:
            continue
        removed_records = _removed_cube_records_from_rows(
            original_height_rows=original_rows,
            remaining_height_rows=remaining_rows,
        )
        if int(len(removed_records)) != int(removed_count):
            continue
        return (
            [[int(value) for value in row] for row in original_rows],
            [[int(value) for value in row] for row in remaining_rows],
            {
                "row_count": int(row_count),
                "col_count": int(col_count),
                "max_height": int(max_height),
                "readable_wall_stack": True,
            },
            [dict(record) for record in removed_records],
        )
    raise RuntimeError("unable to sample readable cube-removal pair")


def _removed_cube_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    sampling_axis_divisor: int,
) -> Dict[str, Any]:
    answer_params = _decouple_sampling_by_divisor(
        params,
        divisor=int(sampling_axis_divisor),
    )
    removal_support = _support_range(
        params,
        key_min="removed_cube_count_min",
        key_max="removed_cube_count_max",
        fallback_min=1,
        fallback_max=6,
    )
    target_removed = _selected_support_value(
        params=answer_params,
        instance_seed=int(instance_seed),
        support=removal_support,
        explicit_key="target_removed_cube_count",
        namespace="removed_cube_count.answer",
    )
    height_support = _support_range(
        params,
        key_min="height_min",
        key_max="height_max",
        fallback_min=2,
        fallback_max=3,
    )
    target_max_height = _selected_support_value(
        params=answer_params,
        instance_seed=int(instance_seed),
        support=height_support,
        explicit_key="target_max_height",
        namespace="removed_cube_count.max_height",
    )
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.removed_cube_count")
    original_rows, remaining_rows, shape_meta, removed_cube_records = _sample_readable_removal_pair(
        rng,
        removed_count=int(target_removed),
        params=params,
        target_max_height=int(target_max_height),
    )
    original_total = int(total_cubes_from_height_rows(original_rows))
    remaining_total = int(total_cubes_from_height_rows(remaining_rows))
    changed_column_count = sum(
        1
        for row_index, row in enumerate(original_rows)
        for col_index, height in enumerate(row)
        if int(height) != int(remaining_rows[int(row_index)][int(col_index)])
    )
    return {
        "original_height_rows": [[int(value) for value in row] for row in original_rows],
        "remaining_height_rows": [[int(value) for value in row] for row in remaining_rows],
        "row_count": int(shape_meta["row_count"]),
        "col_count": int(shape_meta["col_count"]),
        "max_height": int(shape_meta["max_height"]),
        "height_support": [int(value) for value in height_support],
        "height_sampling_policy": "seeded_balanced",
        "original_total_cubes": int(original_total),
        "remaining_total_cubes": int(remaining_total),
        "removed_cube_count": int(target_removed),
        "removal_count": int(target_removed),
        "changed_column_count": int(changed_column_count),
        "removed_cells_restricted_to_readable_edges": True,
        "answer_value": int(target_removed),
        "answer_support": [int(value) for value in removal_support],
        "original_cube_records": [dict(record) for record in cube_records_from_height_rows(original_rows)],
        "remaining_cube_records": [dict(record) for record in cube_records_from_height_rows(remaining_rows)],
        "removed_cube_records": [dict(record) for record in removed_cube_records],
        "supporting_structure_ids": ["original_structure", "remaining_structure"],
        "original_structure_bbox_id": "original_structure",
        "remaining_structure_bbox_id": "remaining_structure",
        "question_format": "removed_cube_count",
        "view_family": "isometric_readable_block_comparison",
        "original_caption": "Before",
        "remaining_caption": "After",
        "is_comparison": True,
    }


def _blend_rgb(color: Sequence[int], target: Sequence[int], amount: float) -> Tuple[int, int, int]:
    blend = max(0.0, min(1.0, float(amount)))
    return tuple(
        max(0, min(255, int(round((float(1.0 - blend) * int(color[index])) + (float(blend) * int(target[index]))))))
        for index in range(3)
    )


def _resolve_cube_color(params: Mapping[str, Any], *, instance_seed: int) -> Dict[str, Any]:
    configured_support = params.get(
        "cube_color_name_support",
        group_default(_GEN_DEFAULTS, "cube_color_name_support", _DEFAULT_CUBE_COLOR_NAME_SUPPORT),
    )
    support = tuple(str(value).strip().lower() for value in configured_support if str(value).strip())
    if not support:
        support = tuple(str(name) for name, _rgb in available_named_colors())
    explicit_name = params.get("cube_color_name")
    if explicit_name is not None:
        color_name = str(explicit_name).strip().lower()
        if color_name not in set(support):
            raise ValueError(f"cube_color_name must be one of {support}")
    else:
        selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:cube_color",
        )
        color_name = str(support[int(selection_index) % len(support)])
    base_rgb = tuple(int(value) for value in named_color(str(color_name)))
    top_rgb = _blend_rgb(base_rgb, (255, 255, 255), 0.42)
    right_rgb = _blend_rgb(base_rgb, (255, 255, 255), 0.12)
    left_rgb = darken_color(base_rgb, factor=0.76)
    shadow_rgb = darken_color(base_rgb, factor=0.55)
    return {
        "name": str(color_name),
        "base_rgb": [int(value) for value in base_rgb],
        "face_top_rgb": [int(value) for value in top_rgb],
        "face_right_rgb": [int(value) for value in right_rgb],
        "face_left_rgb": [int(value) for value in left_rgb],
        "face_shadow_rgb": [int(value) for value in shadow_rgb],
    }


def _apply_cube_color(render_params, cube_color: Mapping[str, Any]):
    return replace(
        render_params,
        face_top_rgb=tuple(int(value) for value in cube_color["face_top_rgb"]),
        face_right_rgb=tuple(int(value) for value in cube_color["face_right_rgb"]),
        face_left_rgb=tuple(int(value) for value in cube_color["face_left_rgb"]),
        face_shadow_rgb=tuple(int(value) for value in cube_color["face_shadow_rgb"]),
    )


def _build_dataset(
    query_id: str,
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    sampling_axis_divisor: int,
) -> Dict[str, Any]:
    if str(query_id) == "missing_to_complete_cuboid_count":
        return _missing_cuboid_dataset(
            params=params,
            instance_seed=int(instance_seed),
            sampling_axis_divisor=int(sampling_axis_divisor),
        )
    if str(query_id) == "removed_cube_count":
        return _removed_cube_dataset(
            params=params,
            instance_seed=int(instance_seed),
            sampling_axis_divisor=int(sampling_axis_divisor),
        )
    return _single_structure_dataset(
        query_id=str(query_id),
        params=params,
        instance_seed=int(instance_seed),
        sampling_axis_divisor=int(sampling_axis_divisor),
    )


class _PuzzlesSpatialCubeStructureBaseTask:
    """Answer integer cube-structure counting questions."""

    task_id = TASK_ID
    domain = "puzzles"
    task_group = "spatial"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        public_query_id, internal_query_id, query_metadata, sampling_axis_divisor = _resolve_query_contract(
            params,
            instance_seed=int(instance_seed),
        )
        if str(public_query_id) == "visible_cube_count":
            solid_params = dict(
                _decouple_sampling_by_divisor(
                    params,
                    divisor=int(sampling_axis_divisor),
                )
            )
            if params.get("query_id") is None:
                solid_params.pop("query_id", None)
            return SolidViewCountGenerator().generate(
                int(instance_seed),
                params=solid_params,
                max_attempts=int(max_attempts),
            )
        if str(public_query_id) == "projection_match_label":
            solid_params = dict(
                _decouple_sampling_by_divisor(
                    params,
                    divisor=int(sampling_axis_divisor),
                )
            )
            solid_params.pop("query_id", None)
            solid_params.pop("query_id", None)
            return SolidViewProjectionMatchGenerator().generate(
                int(instance_seed),
                params=solid_params,
                max_attempts=int(max_attempts),
            )
        if str(public_query_id) == "projection_consistency_label":
            solid_params = dict(
                _decouple_sampling_by_divisor(
                    params,
                    divisor=int(sampling_axis_divisor),
                )
            )
            solid_params.pop("query_id", None)
            solid_params.pop("query_id", None)
            return SolidViewProjectionConsistencyGenerator().generate(
                int(instance_seed),
                params=solid_params,
                max_attempts=int(max_attempts),
            )
        query_id_probabilities = dict(query_metadata["query_id_probabilities"])
        scene_params = _decouple_sampling_by_divisor(
            params,
            divisor=int(sampling_axis_divisor),
        )
        scene_variant, scene_variant_probabilities = resolve_block_scene_variant(
            scene_params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        dataset = _build_dataset(
            str(internal_query_id),
            params=params,
            instance_seed=int(instance_seed),
            sampling_axis_divisor=int(sampling_axis_divisor),
        )
        base_render_params = resolve_block_stack_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        cube_color = _resolve_cube_color(params, instance_seed=int(instance_seed))
        render_params = _apply_cube_color(base_render_params, cube_color)
        scene_style, scene_style_meta = resolve_puzzle_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.cube_voxel_background",
        )
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        if bool(dataset["is_comparison"]):
            rendered_scene = render_puzzle_block_comparison_scene(
                background,
                scene_variant=str(scene_variant),
                original_height_rows=list(dataset["original_height_rows"]),
                original_cube_records=list(dataset["original_cube_records"]),
                remaining_height_rows=list(dataset["remaining_height_rows"]),
                remaining_cube_records=list(dataset["remaining_cube_records"]),
                render_params=render_params,
                original_caption=str(dataset["original_caption"]),
                remaining_caption=str(dataset["remaining_caption"]),
            )
        else:
            rendered_scene = render_puzzle_block_structure_scene(
                background,
                scene_variant=str(scene_variant),
                structure_height_rows=list(dataset["height_rows"]),
                structure_cube_records=list(dataset["cube_records"]),
                render_params=render_params,
                structure_id=str(dataset["structure_bbox_id"]),
                caption=str(dataset["caption"]),
            )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        supporting_structure_ids = [str(item) for item in dataset["supporting_structure_ids"]]
        annotation_projection = projected_puzzle_bbox_annotation(rendered_scene.structure_bbox_map, supporting_structure_ids)
        annotation_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in annotation_projection["bbox_set"]
        ]
        answer_value = int(dataset["answer_value"])
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_integer",
                "object_description_stack_strip",
                "object_description_stack_card",
                "object_description_stack_outline",
                "object_description_single_stack_stack_strip",
                "object_description_single_stack_stack_card",
                "object_description_single_stack_stack_outline",
                "object_description_change_pair_stack_strip",
                "object_description_change_pair_stack_card",
                "object_description_change_pair_stack_outline",
                "annotation_hint_total_cube_count",
                "annotation_hint_missing_to_complete_cuboid_count",
                "annotation_hint_removed_cube_count",
                "annotation_hint_painted_exterior_face_count",
                "annotation_hint_exact_k_painted_faces_cube_count",
                "json_example_total_cube_count",
                "json_example_missing_to_complete_cuboid_count",
                "json_example_removed_cube_count",
                "json_example_painted_exterior_face_count",
                "json_example_exact_k_painted_faces_cube_count",
                "json_example_answer_only_total_cube_count",
                "json_example_answer_only_missing_to_complete_cuboid_count",
                "json_example_answer_only_removed_cube_count",
                "json_example_answer_only_painted_exterior_face_count",
                "json_example_answer_only_exact_k_painted_faces_cube_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(internal_query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(
                    prompt_defaults[
                        _object_description_key(
                            internal_query_id=str(internal_query_id),
                            scene_variant=str(scene_variant),
                        )
                    ]
                ),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(internal_query_id)}"]),
                "answer_hint": str(prompt_defaults["answer_hint_integer"]),
                "json_example": str(prompt_defaults[f"json_example_{str(internal_query_id)}"]),
                "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{str(internal_query_id)}"]),
                "painted_face_count": str(dataset.get("painted_face_target_k", 4)),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        total_for_scan = int(dataset.get("total_cubes", dataset.get("original_total_cubes", 0)))
        answer_support = [int(value) for value in dataset["answer_support"]]
        answer_scan = normalize_int_with_bounds(int(answer_value), [min(answer_support), max(answer_support)])
        total_scan = normalize_int_with_bounds(
            int(total_for_scan),
            [
                int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "total_cube_count_min", 8)),
                int(resolve_puzzle_int_param(params, _GEN_DEFAULTS, "total_cube_count_max", 22)),
            ],
        )
        comparison_load = 0.20 if bool(dataset["is_comparison"]) else 0.0
        variant_reasoning_load = {
            "total_cube_count": 0.34,
            "missing_to_complete_cuboid_count": 0.52,
            "removed_cube_count": 0.48,
            "painted_exterior_face_count": 0.62,
            "exact_k_painted_faces_cube_count": 0.72,
        }[str(internal_query_id)]
        scene_load = {
            "stack_strip": 0.12,
            "stack_card": 0.18,
            "stack_outline": 0.15,
        }[str(scene_variant)]
        complexity = build_puzzle_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": max(float(total_scan), float(answer_scan)),
                "reasoning_load": clamp_unit_interval(float(variant_reasoning_load) + float(comparison_load)),
                "scene_variant_load": float(scene_load),
            },
        )

        render_map: Dict[str, Any] = {
            "image_id": "img0",
            "scene_bbox_px": list(rendered_scene.scene_bbox_px),
            "structure_bboxes_px": {str(key): list(value) for key, value in rendered_scene.structure_bbox_map.items()},
        }
        if bool(dataset["is_comparison"]):
            render_map["original_structure_bbox_px"] = list(rendered_scene.original_structure_bbox_px)
            render_map["remaining_structure_bbox_px"] = list(rendered_scene.remaining_structure_bbox_px)
        else:
            render_map["structure_bbox_px"] = list(rendered_scene.structure_bbox_px)

        helper_solver_trace = dataset.get("solver_trace", {})
        if not isinstance(helper_solver_trace, Mapping):
            helper_solver_trace = {}
        execution_trace = {
            "query_id": str(public_query_id),
            "internal_query_id": str(internal_query_id),
            "scene_variant": str(scene_variant),
            "query_id_probabilities": dict(query_id_probabilities),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "question_format": str(dataset["question_format"]),
            "view_family": str(dataset["view_family"]),
            "answer_value": int(answer_value),
            "answer_support": list(answer_support),
            "supporting_structure_ids": list(supporting_structure_ids),
            "countability_contract": "cube structures are solid wall-like stacks with no floating cubes; every structure uses either one row or one column so each answer-relevant cube column is readable from the fixed isometric view",
            "readability_contract": "single stacks and removed/missing deltas use one-row or one-column footprints with height capped by config so counted cubes and height differences are not hidden behind another row",
            "cube_color": dict(cube_color),
            "solver_trace": {
                "total_cubes": int(dataset.get("total_cubes", dataset.get("remaining_total_cubes", 0))),
                "painted_exterior_face_count": int(dataset.get("painted_exterior_face_count", -1)),
                "painted_face_target_k": int(dataset.get("painted_face_target_k", -1)),
                "exact_k_painted_faces_cube_count": int(dataset.get("exact_k_painted_faces_cube_count", -1)),
                "missing_cube_count": int(dataset.get("missing_cube_count", -1)),
                "removed_cube_count": int(dataset.get("removed_cube_count", -1)),
                **dict(helper_solver_trace),
            },
        }
        for key in ("change_type", "painted_query", "change_type_probabilities", "painted_query_probabilities"):
            if key in query_metadata:
                execution_trace[str(key)] = query_metadata[str(key)]
        execution_trace.update(
            {
                str(key): value
                for key, value in dataset.items()
                if str(key)
                not in {
                    "is_comparison",
                    "answer_support",
                    "supporting_structure_ids",
                    "caption",
                    "original_caption",
                    "remaining_caption",
                    "solver_trace",
                }
            }
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"puzzle_spatial_cube_structure_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(public_query_id),
                    "internal_query_id": str(internal_query_id),
                    "scene_variant": str(scene_variant),
                    "answer_value": int(answer_value),
                    "view_family": str(dataset["view_family"]),
                },
            },
            "query_spec": {
                "query_id": str(public_query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(public_query_id),
                    "internal_query_id": str(internal_query_id),
                    "scene_variant": str(scene_variant),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "answer_support": list(answer_support),
                    **{
                        str(key): value
                        for key, value in query_metadata.items()
                        if str(key) not in {"query_id_probabilities", "internal_query_id"}
                    },
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "scene_style": dict(scene_style_meta),
                "post_image_noise": dict(post_noise_meta),
                "cube_color": dict(cube_color),
                "view_orientation_index": int(render_params.view_orientation_index),
                "voxel_scale": round(float(render_params.voxel_scale), 4),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
            },
            "render_map": dict(render_map),
            "execution_trace": dict(execution_trace),
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(annotation_bboxes),
            },
            "projected_annotation": dict(annotation_projection),
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(public_query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class PuzzlesSpatialCubeCountTask(FixedPuzzleQueryVariantTaskMixin, _PuzzlesSpatialCubeStructureBaseTask):
    """Count all cubes in one visible cube structure."""

    task_id = CUBE_COUNT_TASK_ID
    fixed_query_id = "cube_count"
    public_scene_id = "voxel_cube"


@register_task
class PuzzlesSpatialCubeStructureChangeCountTask(FixedPuzzleQueryVariantTaskMixin, _PuzzlesSpatialCubeStructureBaseTask):
    """Count the cube delta between two related cube structures."""

    task_id = CUBE_STRUCTURE_CHANGE_COUNT_TASK_ID
    fixed_query_id = "cube_structure_change_count"
    public_scene_id = "voxel_cube"


@register_task
class PuzzlesSpatialCubePaintedFaceCountTask(FixedPuzzleQueryVariantTaskMixin, _PuzzlesSpatialCubeStructureBaseTask):
    """Count exterior painted faces or cubes with a target painted-face count."""

    task_id = CUBE_PAINTED_FACE_COUNT_TASK_ID
    fixed_query_id = "painted_face_count"
    public_scene_id = "voxel_cube"


@register_task
class PuzzlesSpatialCubeVisibleProjectionCountTask(FixedPuzzleQueryVariantTaskMixin, _PuzzlesSpatialCubeStructureBaseTask):
    """Count filled cells in an orthographic projection of a cube stack."""

    task_id = CUBE_VISIBLE_PROJECTION_COUNT_TASK_ID
    fixed_query_id = "visible_cube_count"
    public_scene_id = "voxel_cube"


@register_task
class PuzzlesSpatialCubeProjectionMatchLabelTask(FixedPuzzleQueryVariantTaskMixin, _PuzzlesSpatialCubeStructureBaseTask):
    """Select the orthographic projection option matching a cube stack."""

    task_id = CUBE_PROJECTION_MATCH_TASK_ID
    fixed_query_id = "projection_match_label"
    public_scene_id = "voxel_cube"


@register_task
class PuzzlesSpatialCubeProjectionConsistencyLabelTask(FixedPuzzleQueryVariantTaskMixin, _PuzzlesSpatialCubeStructureBaseTask):
    """Select the projection or stack option that resolves cube-view consistency."""

    task_id = CUBE_PROJECTION_CONSISTENCY_TASK_ID
    fixed_query_id = "projection_consistency_label"
    public_scene_id = "voxel_cube"


__all__ = [
    "PuzzlesSpatialCubeCountTask",
    "PuzzlesSpatialCubeStructureChangeCountTask",
    "PuzzlesSpatialCubePaintedFaceCountTask",
    "PuzzlesSpatialCubeVisibleProjectionCountTask",
    "PuzzlesSpatialCubeProjectionMatchLabelTask",
    "PuzzlesSpatialCubeProjectionConsistencyLabelTask",
]
