"""Scene-local sampling primitives for polyomino missing-piece puzzles."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from trace.core.seed import spawn_rng
from trace.core.sampling import integer_range_choice
from trace.tasks.shared.mcq import option_label_for_index

from .defaults import complement_generation_param_map
from .rules import (
    D4_TRANSFORMS,
    canonicalize_polyomino_cells,
    d4_signature,
    is_connected_cells,
    neighbors,
    polyomino_bbox_dims,
    polyomino_cell_count,
    shape_bbox_dims,
    translate_polyomino_cells,
    unique_d4_transforms,
)
from .state import DEFAULTS, Cell, Cells


def _labels_for_option_count(option_count: int) -> Tuple[str, ...]:
    """Return the option labels visible in a generated option panel."""

    return tuple(option_label_for_index(index) for index in range(int(option_count)))


def _option_index_for_label(*, option_count: int, answer_label: str) -> int:
    """Map an answer label to its visible option index."""

    labels = _labels_for_option_count(int(option_count))
    if str(answer_label) not in set(labels):
        raise ValueError(f"answer_label must be one of {labels}")
    return int(labels.index(str(answer_label)))


def _json_cell_list(cells: Iterable[Cell]) -> List[List[int]]:
    """Return cells as a JSON-ready sorted list."""

    return [[int(x), int(y)] for x, y in sorted((int(x), int(y)) for x, y in cells)]


def build_rectangle_complement_dataset(
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    instance_seed: int,
    transform_allowed: bool,
    option_count: int,
    answer_label: str,
    namespace_base: str,
) -> Dict[str, Any]:
    """Build a rectangular target with one missing connected option piece."""

    rng = spawn_rng(int(instance_seed), f"{str(namespace_base)}.rectangle_complement")
    correct_option_index = _option_index_for_label(
        option_count=int(option_count),
        answer_label=str(answer_label),
    )
    merged_params = {**dict(generation_defaults), **dict(params)}
    helper_params = complement_generation_param_map(merged_params)
    base = _build_rectangle_target(
        params=helper_params,
        rng=rng,
        transform_allowed=bool(transform_allowed),
    )

    cutout_cells: Cells = tuple((int(x), int(y)) for x, y in base["cutout_cells"])
    cutout_count = int(len(cutout_cells))
    preferred_bbox = shape_bbox_dims(cutout_cells)
    max_dim = int(helper_params.get("shape_bbox_max_dim", DEFAULTS.complement_shape_bbox_max_dim))
    correct_payload = {"transform": "identity", "cells": cutout_cells}
    if bool(transform_allowed):
        transforms = list(unique_d4_transforms(cutout_cells))
        non_identity = [payload for payload in transforms if tuple(payload["cells"]) != cutout_cells]
        transform_pool = non_identity or transforms
        correct_payload = dict(rng.choice(transform_pool))
    correct_option_cells: Cells = tuple((int(x), int(y)) for x, y in correct_payload["cells"])
    correct_d4_signature = d4_signature(cutout_cells)

    distractor_shapes: List[Cells] = []
    seen_shapes = {correct_option_cells}
    seen_d4_signatures = {correct_d4_signature}
    attempts = 0
    while len(distractor_shapes) < int(option_count - 1) and attempts < 4000:
        attempts += 1
        active_preferred = preferred_bbox if int(attempts) <= 1200 else None
        try:
            candidate = _sample_connected_shape(
                area=int(cutout_count),
                target_bbox_max_dim=max(int(max_dim), max(preferred_bbox) + 1),
                preferred_bbox=active_preferred,
                rng=rng,
            )
        except RuntimeError:
            break
        if bool(transform_allowed):
            candidate_d4_signature = d4_signature(candidate)
            if candidate_d4_signature in seen_d4_signatures:
                continue
            seen_d4_signatures.add(candidate_d4_signature)
        else:
            if candidate in seen_shapes:
                continue
        seen_shapes.add(candidate)
        distractor_shapes.append(candidate)
    if len(distractor_shapes) < int(option_count - 1):
        raise RuntimeError("failed to construct enough rectangle-complement distractors")

    rng.shuffle(distractor_shapes)
    option_shapes = list(distractor_shapes[: int(option_count - 1)])
    option_shapes.insert(int(correct_option_index), correct_option_cells)
    option_specs = _option_specs(
        option_shapes,
        correct_option_index=int(correct_option_index),
        cutout_cells=cutout_cells,
        transform_allowed=bool(transform_allowed),
        correct_d4_signature=correct_d4_signature,
    )
    target_cells = tuple((int(x), int(y)) for x, y in base["target_cells"])
    remaining_cells = tuple((int(x), int(y)) for x, y in base["remaining_cells"])
    cutout_cells_in_target = tuple((int(x), int(y)) for x, y in base["cutout_cells_in_target"])
    return {
        "target_cells": _json_cell_list(target_cells),
        "remaining_cells": _json_cell_list(remaining_cells),
        "visible_target_cells": _json_cell_list(remaining_cells),
        "cutout_cells": _json_cell_list(cutout_cells),
        "cutout_cells_in_target": _json_cell_list(cutout_cells_in_target),
        "missing_cells": _json_cell_list(cutout_cells_in_target),
        "marked_cells": _json_cell_list(cutout_cells_in_target),
        "cutout_cell_count": int(cutout_count),
        "cutout_cell_count_range": list(base["cutout_cell_count_range"]),
        "target_bbox_dims": list(base["target_bbox_dims"]),
        "target_cell_count": int(len(target_cells)),
        "target_generation_kind": "rectangle",
        "option_specs": list(option_specs),
        "option_count": int(option_count),
        "option_count_range": [int(option_count), int(option_count)],
        "allowed_transforms": list(D4_TRANSFORMS) if bool(transform_allowed) else ["identity"],
        "correct_option_transform": str(correct_payload["transform"]),
        "answer_option_label": str(answer_label),
        "correct_option_index": int(correct_option_index),
        "correct_option_panel_id": f"option_panel_{int(correct_option_index + 1)}",
        "valid_option_panel_ids": [f"option_panel_{int(correct_option_index + 1)}"],
        "solver_trace": {
            "transform_allowed": bool(transform_allowed),
            "target_generation_kind": "rectangle",
            "target_cells": _json_cell_list(target_cells),
            "remaining_cells": _json_cell_list(remaining_cells),
            "cutout_cells": _json_cell_list(cutout_cells),
            "cutout_cells_in_target": _json_cell_list(cutout_cells_in_target),
            "correct_option_cells": _json_cell_list(correct_option_cells),
            "correct_option_transform": str(correct_payload["transform"]),
            "valid_option_panel_ids": [f"option_panel_{int(correct_option_index + 1)}"],
        },
    }


def _option_specs(
    option_shapes: Sequence[Cells],
    *,
    correct_option_index: int,
    cutout_cells: Cells | None = None,
    transform_allowed: bool = False,
    correct_d4_signature: Cells | None = None,
) -> List[Dict[str, Any]]:
    """Serialize visible option shapes with correctness metadata."""

    specs: List[Dict[str, Any]] = []
    for option_index, shape in enumerate(option_shapes):
        matches_under_policy = bool(option_index == int(correct_option_index))
        if cutout_cells is not None:
            matches_under_policy = (
                d4_signature(shape) == correct_d4_signature
                if bool(transform_allowed)
                else tuple(shape) == tuple(cutout_cells)
            )
        specs.append(
            {
                "option_panel_id": f"option_panel_{int(option_index + 1)}",
                "option_label": option_label_for_index(int(option_index)),
                "cells": _json_cell_list(shape),
                "cell_count": int(polyomino_cell_count(shape)),
                "bbox_dims": list(polyomino_bbox_dims(shape)),
                "is_correct": bool(option_index == int(correct_option_index)),
                "matches_under_policy": bool(matches_under_policy),
            }
        )
    return specs


def _build_rectangle_target(
    *,
    params: Mapping[str, Any],
    rng,
    transform_allowed: bool,
) -> Dict[str, Any]:
    """Build the rectangular target and connected cutout cells."""

    width, width_range = _sample_range(
        rng,
        params=params,
        min_key="target_width_min",
        max_key="target_width_max",
        fallback_min=DEFAULTS.complement_target_width_min,
        fallback_max=DEFAULTS.complement_target_width_max,
    )
    height, height_range = _sample_range(
        rng,
        params=params,
        min_key="target_height_min",
        max_key="target_height_max",
        fallback_min=DEFAULTS.complement_target_height_min,
        fallback_max=DEFAULTS.complement_target_height_max,
    )
    cutout_count, cutout_count_range = _sample_range(
        rng,
        params=params,
        min_key="cutout_cell_count_min",
        max_key="cutout_cell_count_max",
        fallback_min=DEFAULTS.complement_cutout_cell_count_min,
        fallback_max=DEFAULTS.complement_cutout_cell_count_max,
    )
    if bool(transform_allowed):
        floor = int(
            params.get(
                "transform_allowed_cutout_cell_count_min",
                DEFAULTS.complement_transform_allowed_cutout_cell_count_min,
            )
        )
        lower = max(int(cutout_count_range[0]), int(floor))
        upper = int(cutout_count_range[1])
        if lower > upper:
            raise ValueError("transform-allowed cutout-cell floor exceeds configured maximum")
        cutout_count, cutout_probabilities = integer_range_choice(rng, lower, upper)
        del cutout_probabilities
        cutout_count_range = (int(lower), int(upper))

    target_cells = tuple((x, y) for y in range(int(height)) for x in range(int(width)))
    for _attempt in range(800):
        placed_cutout = _sample_connected_subset(
            source_cells=target_cells,
            area=int(cutout_count),
            rng=rng,
        )
        remaining = tuple(sorted(set(target_cells) - set(placed_cutout)))
        if remaining and is_connected_cells(remaining):
            return {
                "target_cells": target_cells,
                "remaining_cells": remaining,
                "cutout_cells_in_target": tuple(sorted(placed_cutout)),
                "cutout_cells": canonicalize_polyomino_cells(placed_cutout),
                "target_bbox_dims": (int(width), int(height)),
                "target_cell_count": int(len(target_cells)),
                "target_width_range": [int(width_range[0]), int(width_range[1])],
                "target_height_range": [int(height_range[0]), int(height_range[1])],
                "cutout_cell_count_range": [
                    int(cutout_count_range[0]),
                    int(cutout_count_range[1]),
                ],
            }
    raise RuntimeError("failed to construct rectangle-complement target")


def _sample_range(
    rng,
    *,
    params: Mapping[str, Any],
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
) -> Tuple[int, Tuple[int, int]]:
    """Sample an integer from an inclusive local range."""

    lower = int(params.get(str(min_key), int(fallback_min)))
    upper = int(params.get(str(max_key), int(fallback_max)))
    selected, probabilities = integer_range_choice(rng, lower, upper)
    del probabilities
    return int(selected), (int(lower), int(upper))


def _sample_connected_subset(*, source_cells: Cells, area: int, rng) -> Cells:
    """Sample a connected subset from a fixed cell support."""

    source_set = {(int(x), int(y)) for x, y in source_cells}
    if int(area) > len(source_set):
        raise ValueError("connected subset area cannot exceed source cell count")
    for _attempt in range(800):
        start = rng.choice(list(source_set))
        cells = {start}
        while len(cells) < int(area):
            frontier = {
                neighbor
                for cell in cells
                for neighbor in neighbors(cell)
                if neighbor in source_set and neighbor not in cells
            }
            if not frontier:
                break
            frontier_list = list(frontier)
            rng.shuffle(frontier_list)
            cells.add(frontier_list[0])
        if len(cells) == int(area) and is_connected_cells(cells):
            return tuple(sorted((int(x), int(y)) for x, y in cells))
    raise RuntimeError("failed to sample connected subset")


def _sample_connected_shape(
    *,
    area: int,
    target_bbox_max_dim: int,
    preferred_bbox: Tuple[int, int] | None,
    rng,
) -> Cells:
    """Sample one connected polyomino with bounded footprint."""

    for _attempt in range(1000):
        cells = {(0, 0)}
        while len(cells) < int(area):
            frontier = {
                neighbor
                for cell in cells
                for neighbor in neighbors(cell)
                if neighbor not in cells
            }
            frontier_list = list(frontier)
            rng.shuffle(frontier_list)
            cells.add(frontier_list[0])
        canonical = canonicalize_polyomino_cells(cells)
        width, height = shape_bbox_dims(canonical)
        if max(int(width), int(height)) > int(target_bbox_max_dim):
            continue
        if preferred_bbox is not None and (
            abs(int(width) - int(preferred_bbox[0])) > 1
            or abs(int(height) - int(preferred_bbox[1])) > 1
        ):
            continue
        return canonical
    raise RuntimeError("failed to sample connected distractor shape")


__all__ = [
    "build_rectangle_complement_dataset",
]
