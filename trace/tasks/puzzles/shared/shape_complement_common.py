"""Shared dataset builders for rectangular complement polyomino puzzles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default, resolve_required_int_bounds
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.mcq import option_label_for_index


Cells = Tuple[Tuple[int, int], ...]

SUPPORTED_PUZZLE_RECTANGLE_COMPLEMENT_MATCHING_POLICIES: Tuple[str, ...] = (
    "exact_orientation",
    "rotation_reflection_allowed",
)


@dataclass(frozen=True)
class PuzzleShapeComplementDefaults:
    """Stable fallback defaults for rectangular complement sampling."""

    option_count_min: int = 6
    option_count_max: int = 6
    target_width_min: int = 4
    target_width_max: int = 6
    target_height_min: int = 4
    target_height_max: int = 6
    cutout_cell_count_min: int = 3
    cutout_cell_count_max: int = 7
    transform_allowed_cutout_cell_count_min: int = 5
    shape_bbox_max_dim: int = 6


def _resolve_int_param(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
    fallback: int,
) -> int:
    """Resolve one integer generation or rendering parameter."""

    return int(params.get(str(key), group_default(defaults, str(key), int(fallback))))


def _canonicalize_cells(cells: Iterable[Tuple[int, int]]) -> Cells:
    """Shift one cell set so its minimum x/y is `(0, 0)`."""

    sorted_cells = sorted((int(x), int(y)) for x, y in cells)
    if not sorted_cells:
        raise ValueError("shape-complement cells cannot be empty")
    min_x = min(x for x, _ in sorted_cells)
    min_y = min(y for _, y in sorted_cells)
    return tuple(sorted((int(x - min_x), int(y - min_y)) for x, y in sorted_cells))


def shape_complement_bbox_dims(cells: Iterable[Tuple[int, int]]) -> Tuple[int, int]:
    """Return `(width, height)` for one canonical cell set."""

    canonical = _canonicalize_cells(cells)
    max_x = max(int(x) for x, _ in canonical)
    max_y = max(int(y) for _, y in canonical)
    return int(max_x + 1), int(max_y + 1)


_D4_TRANSFORMS: Tuple[str, ...] = (
    "identity",
    "rotate_90",
    "rotate_180",
    "rotate_270",
    "flip_horizontal",
    "flip_vertical",
    "flip_main_diagonal",
    "flip_anti_diagonal",
)


def _apply_d4_transform(cells: Cells, transform_name: str) -> Cells:
    """Apply one square-grid rotation/reflection transform and canonicalize it."""

    selected = str(transform_name)

    def _map_cell(cell_x: int, cell_y: int) -> Tuple[int, int]:
        x, y = int(cell_x), int(cell_y)
        if selected == "identity":
            return x, y
        if selected == "rotate_90":
            return y, -x
        if selected == "rotate_180":
            return -x, -y
        if selected == "rotate_270":
            return -y, x
        if selected == "flip_horizontal":
            return -x, y
        if selected == "flip_vertical":
            return x, -y
        if selected == "flip_main_diagonal":
            return y, x
        if selected == "flip_anti_diagonal":
            return -y, -x
        raise ValueError(f"unsupported D4 transform: {transform_name}")

    return _canonicalize_cells(_map_cell(int(cell_x), int(cell_y)) for cell_x, cell_y in cells)


def _unique_d4_transforms(cells: Cells) -> Tuple[Dict[str, Any], ...]:
    """Return unique rotation/reflection transforms for one cell shape."""

    canonical = _canonicalize_cells(cells)
    seen: set[Cells] = set()
    transforms: List[Dict[str, Any]] = []
    for transform_name in _D4_TRANSFORMS:
        transformed = _apply_d4_transform(canonical, str(transform_name))
        if transformed in seen:
            continue
        seen.add(transformed)
        transforms.append(
            {
                "transform": str(transform_name),
                "cells": transformed,
            }
        )
    return tuple(transforms)


def shape_complement_d4_signature(cells: Iterable[Tuple[int, int]]) -> Cells:
    """Return a canonical equivalence signature under rotation and reflection."""

    canonical = _canonicalize_cells(cells)
    return min(tuple(payload["cells"]) for payload in _unique_d4_transforms(canonical))


def _neighbors(cell: Tuple[int, int]) -> Tuple[Tuple[int, int], ...]:
    """Return edge-neighbor coordinates for one cell."""

    x, y = int(cell[0]), int(cell[1])
    return ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))


def _is_connected(cells: Iterable[Tuple[int, int]]) -> bool:
    """Return whether one non-empty cell set is edge-connected."""

    cell_set = {(int(x), int(y)) for x, y in cells}
    if not cell_set:
        return False
    start = next(iter(cell_set))
    seen = {start}
    stack = [start]
    while stack:
        current = stack.pop()
        for neighbor in _neighbors(current):
            if neighbor in cell_set and neighbor not in seen:
                seen.add(neighbor)
                stack.append(neighbor)
    return len(seen) == len(cell_set)


def _sample_connected_subset(
    *,
    source_cells: Cells,
    area: int,
    rng,
) -> Cells:
    """Sample a connected subset from a fixed cell support, preserving coordinates."""

    source_set = {(int(x), int(y)) for x, y in source_cells}
    if int(area) > len(source_set):
        raise ValueError("connected subset area cannot exceed source cell count")
    for _ in range(800):
        start = rng.choice(list(source_set))
        cells = {start}
        while len(cells) < int(area):
            frontier = {
                neighbor
                for cell in cells
                for neighbor in _neighbors(cell)
                if neighbor in source_set and neighbor not in cells
            }
            if not frontier:
                break
            frontier_list = list(frontier)
            rng.shuffle(frontier_list)
            cells.add(frontier_list[0])
        if len(cells) == int(area) and _is_connected(cells):
            return tuple(sorted((int(x), int(y)) for x, y in cells))
    raise RuntimeError("failed to sample connected shape-complement subset")


def _sample_connected_shape(
    *,
    area: int,
    target_bbox_max_dim: int,
    preferred_bbox: Tuple[int, int] | None,
    rng,
) -> Cells:
    """Sample one connected polyomino with bounded footprint."""

    for _ in range(1000):
        cells = {(0, 0)}
        while len(cells) < int(area):
            frontier = {
                neighbor
                for cell in cells
                for neighbor in _neighbors(cell)
                if neighbor not in cells
            }
            frontier_list = list(frontier)
            rng.shuffle(frontier_list)
            cells.add(frontier_list[0])
        canonical = _canonicalize_cells(cells)
        width, height = shape_complement_bbox_dims(canonical)
        if max(int(width), int(height)) > int(target_bbox_max_dim):
            continue
        if preferred_bbox is not None and (
            abs(int(width) - int(preferred_bbox[0])) > 1
            or abs(int(height) - int(preferred_bbox[1])) > 1
        ):
            continue
        return canonical
    raise RuntimeError("failed to sample connected shape-complement polyomino")


def _resolve_count_range(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleShapeComplementDefaults,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    task_id: str,
) -> Tuple[int, Tuple[int, int]]:
    """Resolve one deterministic integer within an inclusive configured support."""

    lower, upper = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
        context=f"{task_id} {min_key}/{max_key} bounds",
    )
    selection = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:{min_key}:{max_key}",
        )
    )
    chosen = int(lower + (selection % (int(upper) - int(lower) + 1)))
    return int(chosen), (int(lower), int(upper))


def _resolve_correct_option_index(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    option_count: int,
) -> int:
    """Resolve a balanced correct-option slot without aliasing query ids."""

    explicit = params.get("correct_option_index")
    if explicit is not None:
        index = int(explicit)
        if not 0 <= int(index) < int(option_count):
            raise ValueError("correct_option_index must fall inside the option-count range")
        return int(index)

    selection = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:correct_option_index",
        )
    )
    return int(selection % int(option_count))


def _build_rectangle_complement(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleShapeComplementDefaults,
    task_id: str,
    rng,
    cutout_cell_count_floor: int | None = None,
) -> Dict[str, Any]:
    """Build the rectangular target with one missing connected piece."""

    width, width_range = _resolve_count_range(
        params,
        instance_seed=int(instance_seed),
        gen_defaults=gen_defaults,
        defaults=defaults,
        min_key="target_width_min",
        max_key="target_width_max",
        fallback_min=int(defaults.target_width_min),
        fallback_max=int(defaults.target_width_max),
        task_id=task_id,
    )
    height, height_range = _resolve_count_range(
        params,
        instance_seed=int(instance_seed),
        gen_defaults=gen_defaults,
        defaults=defaults,
        min_key="target_height_min",
        max_key="target_height_max",
        fallback_min=int(defaults.target_height_min),
        fallback_max=int(defaults.target_height_max),
        task_id=task_id,
    )
    cutout_count, cutout_count_range = _resolve_count_range(
        params,
        instance_seed=int(instance_seed),
        gen_defaults=gen_defaults,
        defaults=defaults,
        min_key="cutout_cell_count_min",
        max_key="cutout_cell_count_max",
        fallback_min=int(defaults.cutout_cell_count_min),
        fallback_max=int(defaults.cutout_cell_count_max),
        task_id=task_id,
    )
    if cutout_cell_count_floor is not None:
        floor = int(cutout_cell_count_floor)
        lower = max(int(cutout_count_range[0]), int(floor))
        upper = int(cutout_count_range[1])
        if int(lower) > int(upper):
            raise ValueError("transform-allowed cutout-cell floor exceeds cutout_cell_count_max")
        selection = int(
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}:cutout_cell_count_floor:{int(lower)}",
            )
        )
        cutout_count = int(lower + (selection % (int(upper) - int(lower) + 1)))
        cutout_count_range = (int(lower), int(upper))
    target_cells = tuple((x, y) for y in range(int(height)) for x in range(int(width)))
    for _ in range(800):
        placed_cutout = _sample_connected_subset(source_cells=target_cells, area=int(cutout_count), rng=rng)
        remaining = tuple(sorted(set(target_cells) - set(placed_cutout)))
        if remaining and _is_connected(remaining):
            return {
                "target_cells": target_cells,
                "remaining_cells": remaining,
                "cutout_cells_in_target": tuple(sorted(placed_cutout)),
                "cutout_cells": _canonicalize_cells(placed_cutout),
                "target_bbox_dims": (int(width), int(height)),
                "target_cell_count": int(len(target_cells)),
                "target_width_range": [int(width_range[0]), int(width_range[1])],
                "target_height_range": [int(height_range[0]), int(height_range[1])],
                "cutout_cell_count_range": [int(cutout_count_range[0]), int(cutout_count_range[1])],
                "target_generation_kind": "rectangle",
            }
    raise RuntimeError("failed to construct rectangle complement puzzle")


def build_shape_complement_dataset_for_variant(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleShapeComplementDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Construct one deterministic rectangular complement puzzle dataset."""

    selected_variant = str(query_id)
    if selected_variant not in set(SUPPORTED_PUZZLE_RECTANGLE_COMPLEMENT_MATCHING_POLICIES):
        raise ValueError(f"unsupported rectangular complement matching policy: {query_id}")

    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")
    option_count, option_count_range = _resolve_count_range(
        params,
        instance_seed=int(instance_seed),
        gen_defaults=gen_defaults,
        defaults=defaults,
        min_key="option_count_min",
        max_key="option_count_max",
        fallback_min=int(defaults.option_count_min),
        fallback_max=int(defaults.option_count_max),
        task_id=task_id,
    )
    transform_allowed = bool(selected_variant == "rotation_reflection_allowed")
    transform_cutout_floor = int(
        params.get(
            "transform_allowed_cutout_cell_count_min",
            group_default(
                gen_defaults,
                "transform_allowed_cutout_cell_count_min",
                int(defaults.transform_allowed_cutout_cell_count_min),
            ),
        )
    )
    base = _build_rectangle_complement(
        params=params,
        instance_seed=int(instance_seed),
        gen_defaults=gen_defaults,
        defaults=defaults,
        task_id=task_id,
        rng=rng,
        cutout_cell_count_floor=int(transform_cutout_floor) if bool(transform_allowed) else None,
    )

    cutout_cells: Cells = tuple((int(x), int(y)) for x, y in base["cutout_cells"])
    cutout_count = int(len(cutout_cells))
    preferred_bbox = shape_complement_bbox_dims(cutout_cells)
    max_dim = int(params.get("shape_bbox_max_dim", group_default(gen_defaults, "shape_bbox_max_dim", defaults.shape_bbox_max_dim)))
    matching_policy = "rotation_reflection_allowed" if bool(transform_allowed) else "exact_orientation"
    correct_transform_payload = {"transform": "identity", "cells": cutout_cells}
    if bool(transform_allowed):
        unique_transforms = list(_unique_d4_transforms(cutout_cells))
        non_identity_transforms = [
            payload for payload in unique_transforms
            if tuple(payload["cells"]) != cutout_cells
        ]
        transform_pool = non_identity_transforms or unique_transforms
        transform_index = int(
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}:correct_option_transform",
            )
        ) % max(1, len(transform_pool))
        correct_transform_payload = dict(transform_pool[int(transform_index)])
    correct_option_cells: Cells = tuple((int(x), int(y)) for x, y in correct_transform_payload["cells"])
    correct_d4_signature = shape_complement_d4_signature(cutout_cells)

    distractor_shapes: List[Cells] = []
    seen_shapes = {correct_option_cells}
    seen_d4_signatures = {correct_d4_signature}
    attempts = 0
    while len(distractor_shapes) < int(option_count - 1) and attempts < 4000:
        attempts += 1
        active_preferred_bbox = preferred_bbox if int(attempts) <= 1200 else None
        try:
            candidate = _sample_connected_shape(
                area=int(cutout_count),
                target_bbox_max_dim=max(int(max_dim), max(preferred_bbox) + 1),
                preferred_bbox=active_preferred_bbox,
                rng=rng,
            )
        except RuntimeError:
            break
        if bool(transform_allowed):
            candidate_d4_signature = shape_complement_d4_signature(candidate)
            if candidate_d4_signature in seen_d4_signatures:
                continue
            seen_d4_signatures.add(candidate_d4_signature)
        else:
            if candidate in seen_shapes:
                continue
        seen_shapes.add(candidate)
        distractor_shapes.append(candidate)
    if len(distractor_shapes) < int(option_count - 1):
        raise RuntimeError("failed to construct enough shape-complement distractors")

    rng.shuffle(distractor_shapes)
    correct_option_index = _resolve_correct_option_index(
        params=params,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        option_count=int(option_count),
    )
    answer_option_label = option_label_for_index(int(correct_option_index))
    correct_option_panel_id = f"option_panel_{int(correct_option_index + 1)}"

    option_shapes = list(distractor_shapes[: int(option_count - 1)])
    option_shapes.insert(int(correct_option_index), correct_option_cells)
    option_specs: List[Dict[str, Any]] = []
    for option_index, option_cells in enumerate(option_shapes):
        option_panel_id = f"option_panel_{int(option_index + 1)}"
        matches_under_policy = (
            shape_complement_d4_signature(option_cells) == correct_d4_signature
            if bool(transform_allowed)
            else tuple(option_cells) == tuple(cutout_cells)
        )
        option_specs.append(
            {
                "option_panel_id": str(option_panel_id),
                "option_label": str(option_label_for_index(int(option_index))),
                "cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in option_cells],
                "cell_count": int(len(option_cells)),
                "bbox_dims": list(shape_complement_bbox_dims(option_cells)),
                "is_correct": bool(option_index == int(correct_option_index)),
                "matches_under_policy": bool(matches_under_policy),
                "candidate_kind": "correct_cutout_piece" if option_index == int(correct_option_index) else "same_area_distractor",
            }
        )

    target_cells = tuple((int(x), int(y)) for x, y in base["target_cells"])
    remaining_cells = tuple((int(x), int(y)) for x, y in base["remaining_cells"])
    cutout_cells_in_target = tuple((int(x), int(y)) for x, y in base["cutout_cells_in_target"])
    target_bbox_dims = tuple(int(value) for value in base["target_bbox_dims"])

    return {
        "query_id": str(selected_variant),
        "option_specs": list(option_specs),
        "option_count": int(option_count),
        "option_count_range": [int(option_count_range[0]), int(option_count_range[1])],
        "target_cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in target_cells],
        "remaining_cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in remaining_cells],
        "cutout_cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in cutout_cells],
        "cutout_cells_in_target": [[int(cell_x), int(cell_y)] for cell_x, cell_y in cutout_cells_in_target],
        "cutout_cell_count": int(cutout_count),
        "cutout_cell_count_range": list(base["cutout_cell_count_range"]),
        "target_bbox_dims": [int(target_bbox_dims[0]), int(target_bbox_dims[1])],
        "target_cell_count": int(len(target_cells)),
        "target_generation_kind": str(base["target_generation_kind"]),
        "matching_policy": str(matching_policy),
        "allowed_transforms": list(_D4_TRANSFORMS) if bool(transform_allowed) else ["identity"],
        "correct_option_transform": str(correct_transform_payload["transform"]),
        "answer_option_label": str(answer_option_label),
        "correct_option_index": int(correct_option_index),
        "correct_option_panel_id": str(correct_option_panel_id),
        "valid_option_panel_ids": [str(correct_option_panel_id)],
        "solver_trace": {
            "query_id": str(selected_variant),
            "matching_policy": str(matching_policy),
            "target_generation_kind": str(base["target_generation_kind"]),
            "target_cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in target_cells],
            "remaining_cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in remaining_cells],
            "cutout_cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in cutout_cells],
            "cutout_cells_in_target": [[int(cell_x), int(cell_y)] for cell_x, cell_y in cutout_cells_in_target],
            "cutout_d4_signature": [[int(cell_x), int(cell_y)] for cell_x, cell_y in correct_d4_signature],
            "correct_option_transform": str(correct_transform_payload["transform"]),
            "correct_option_index": int(correct_option_index),
            "correct_option_label": str(answer_option_label),
            "correct_option_panel_id": str(correct_option_panel_id),
            "option_shape_signatures": {
                str(spec["option_panel_id"]): [list(cell) for cell in spec["cells"]]
                for spec in option_specs
            },
        },
    }


__all__ = [
    "PuzzleShapeComplementDefaults",
    "SUPPORTED_PUZZLE_RECTANGLE_COMPLEMENT_MATCHING_POLICIES",
    "build_shape_complement_dataset_for_variant",
    "shape_complement_bbox_dims",
    "shape_complement_d4_signature",
]
