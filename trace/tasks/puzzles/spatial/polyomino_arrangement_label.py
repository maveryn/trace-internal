"""Puzzle spatial task for static polyomino arrangement reasoning."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.mcq import option_label_for_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import resolve_render_int, resolve_render_rgb
from ...shared.text_rendering import draw_text_centered, load_font
from ..shared.assembly_common import (
    PUZZLE_POLYOMINO_PIECE_LIBRARY,
    PuzzleAssemblyDefaults,
    PuzzleAssemblyRenderParams,
    canonicalize_polyomino_cells,
    polyomino_bbox_dims,
    polyomino_cell_count,
    resolve_assembly_render_params,
    translate_polyomino_cells,
    unique_rotations,
)
from ..shared.assembly_scene import _draw_polyomino
from ..shared.common import decouple_axis_sampling, projected_puzzle_bbox_evidence, resolve_puzzle_axis_variant
from ..shared.complexity import (
    build_puzzle_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_puzzle_complexity_weights,
)
from ..shared.fixed_query_task import rewrite_fixed_puzzle_query_output
from ..shared.drawing import draw_rounded_rect
from ..shared.option_layout import centered_option_grid_shape, centered_option_row_counts
from ..shared.option_panels import render_puzzle_option_panel
from ..shared.unit_size_jitter import resolve_puzzle_unit_size_scale, scale_puzzle_px, with_puzzle_unit_size_jitter
from ..shared.shape_complement_common import (
    PuzzleShapeComplementDefaults,
    build_shape_complement_dataset_for_variant,
)
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.visual_defaults import load_puzzle_noise_defaults


TASK_ID = "puzzles_spatial_polyomino_arrangement_internal"
POLYOMINO_MISSING_REGION_PIECE_LABEL_TASK_ID = "task_puzzles__polyomino_missing__polyomino_missing_region_piece_label"
POLYOMINO_MISSING_REGION_SCENE_ID = "polyomino_missing"
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    "marked_region_piece_label",
    "rectangle_complement_piece",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "polyomino_strip",
    "polyomino_card",
    "polyomino_outline",
)
SUPPORTED_COMPLEMENT_MATCHING_POLICIES: Tuple[str, ...] = (
    "exact_orientation",
    "rotation_reflection_allowed",
)
SUPPORTED_MISSING_REGION_QUERY_VARIANTS: Tuple[str, ...] = (
    "marked_region_piece_label",
    "rectangle_complement_piece",
)
_REASONING_LOAD_BASE_BY_VARIANT = {
    "marked_region_piece_label": 0.64,
    "rectangle_complement_piece": 0.52,
}
_SCENE_LOAD_BY_VARIANT = {
    "polyomino_strip": 0.16,
    "polyomino_card": 0.22,
    "polyomino_outline": 0.19,
}
_HIGHLIGHT_FILL_RGB = (255, 239, 164)
_EMPTY_CELL_RGB = (251, 252, 255)
_BOARD_GRID_RGB = (92, 101, 116)
_MARKED_CELL_RGB = (236, 96, 78)
_TARGET_CELL_RGB = (207, 219, 236)
_MISSING_CELL_RGB = (22, 24, 28)


Cells = Tuple[Tuple[int, int], ...]
Cell = Tuple[int, int]


@dataclass(frozen=True)
class _PolyominoArrangementDefaults:
    """Stable fallback defaults for polyomino arrangement variants."""

    marked_option_count_min: int = 4
    marked_option_count_max: int = 6
    marked_target_cell_count_min: int = 18
    marked_target_cell_count_max: int = 36
    marked_target_bbox_max_dim: int = 7
    complement_option_count_min: int = 5
    complement_option_count_max: int = 6
    complement_target_width_min: int = 4
    complement_target_width_max: int = 6
    complement_target_height_min: int = 4
    complement_target_height_max: int = 6
    complement_cutout_cell_count_min: int = 3
    complement_cutout_cell_count_max: int = 7
    complement_transform_allowed_cutout_cell_count_min: int = 5
    complement_shape_bbox_max_dim: int = 6
    board_cell_size_px: int = 36
    board_cell_gap_px: int = 2
    target_cell_size_px: int = 38
    target_cell_gap_px: int = 4


@dataclass(frozen=True)
class _RenderedPolyominoScene:
    """Rendered custom polyomino scene with traced geometry."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    bbox_map: Dict[str, List[float]]


_DEFAULTS = _PolyominoArrangementDefaults()
_ASSEMBLY_DEFAULTS = PuzzleAssemblyDefaults()
_SHAPE_COMPLEMENT_DEFAULTS = PuzzleShapeComplementDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "spatial")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_puzzle_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="spatial", apply_prob=0.0)


def _resolve_query_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic polyomino arrangement variant."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_QUERY_VARIANTS,
        task_id=TASK_ID,
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        balance_flag_key="balanced_query_variant_sampling",
        axis_namespace="query_variant",
    )


def _resolve_scene_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the visual scene variant."""

    scene_params = decouple_axis_sampling(
        params,
        preceding_axis_size=len(SUPPORTED_QUERY_VARIANTS),
        explicit_key="scene_variant",
    )
    return resolve_puzzle_axis_variant(
        params=scene_params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _resolve_complement_matching_policy(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the rectangle-complement matching policy as a subtask parameter."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_COMPLEMENT_MATCHING_POLICIES,
        task_id=TASK_ID,
        explicit_key="matching_policy",
        weights_key="matching_policy_weights",
        balance_flag_key="balanced_matching_policy_sampling",
        axis_namespace="matching_policy",
    )


def _resolve_int_range_choice(
    params: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    instance_seed: int,
    namespace: str,
) -> Tuple[int, Tuple[int, int]]:
    """Resolve one deterministic integer choice from inclusive config bounds."""

    lower, upper = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
        context=f"{TASK_ID} {namespace} bounds",
    )
    selection = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace)))
    return int(lower + (selection % (int(upper) - int(lower) + 1))), (int(lower), int(upper))


def _resolve_correct_option_index(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    option_count: int,
    namespace: str,
    option_count_range: Sequence[int] | None = None,
) -> int:
    """Resolve a balanced correct-option index."""

    explicit = params.get("correct_option_index")
    if explicit is not None:
        index = int(explicit)
        if not 0 <= int(index) < int(option_count):
            raise ValueError("correct_option_index must fall inside the option-count range")
        return int(index)
    _ = option_count_range
    selection = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace)))
    return int(selection % int(option_count))


def _canonical_rotation_signature(cells: Cells) -> Cells:
    """Return a rotation-invariant signature for one polyomino."""

    rotations = tuple(unique_rotations(canonicalize_polyomino_cells(cells)))
    return min(rotations)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _is_connected_cells(cells: Iterable[Cell]) -> bool:
    """Return whether a non-empty cell set is 4-connected."""

    cell_set = {(int(x), int(y)) for x, y in cells}
    if not cell_set:
        return False
    stack = [next(iter(cell_set))]
    seen: set[Cell] = set()
    while stack:
        cell_x, cell_y = stack.pop()
        if (cell_x, cell_y) in seen:
            continue
        seen.add((cell_x, cell_y))
        for delta_x, delta_y in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            candidate = (int(cell_x + delta_x), int(cell_y + delta_y))
            if candidate in cell_set and candidate not in seen:
                stack.append(candidate)
    return len(seen) == len(cell_set)


def _missing_region_is_interior(*, target_cells: set[Cell], missing_cells: set[Cell]) -> bool:
    """Return true when every missing cell is fully surrounded by target cells."""

    if not target_cells or not missing_cells:
        return False
    if not missing_cells <= target_cells:
        return False
    min_x = min(x for x, _ in target_cells)
    max_x = max(x for x, _ in target_cells)
    min_y = min(y for _, y in target_cells)
    max_y = max(y for _, y in target_cells)
    for cell_x, cell_y in missing_cells:
        if int(cell_x) in {int(min_x), int(max_x)} or int(cell_y) in {int(min_y), int(max_y)}:
            return False
        for delta_x, delta_y in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (int(cell_x + delta_x), int(cell_y + delta_y)) not in target_cells:
                return False
    return True


def _piece_indices_covering_cell(
    *,
    target_cells: Cells,
    piece_shapes: Sequence[Cells],
    target_cell: Cell,
) -> set[int]:
    """Enumerate which source piece indices can cover one target cell across valid tilings."""

    target = frozenset((int(x), int(y)) for x, y in target_cells)
    rotations_by_piece = [unique_rotations(canonicalize_polyomino_cells(shape)) for shape in piece_shapes]
    covering: set[int] = set()

    def _search(
        remaining_cells: frozenset[Cell],
        remaining_piece_indices: Tuple[int, ...],
        placed_by_piece: Dict[int, frozenset[Cell]],
    ) -> None:
        if len(covering) > 1:
            return
        if not remaining_cells:
            for piece_index, placed_cells in placed_by_piece.items():
                if target_cell in placed_cells:
                    covering.add(int(piece_index))
            return
        anchor_cell = min(remaining_cells)
        for position, piece_index in enumerate(remaining_piece_indices):
            for rotation in rotations_by_piece[int(piece_index)]:
                for piece_cell in rotation:
                    translated = frozenset(
                        (
                            int(cell_x + anchor_cell[0] - piece_cell[0]),
                            int(cell_y + anchor_cell[1] - piece_cell[1]),
                        )
                        for cell_x, cell_y in rotation
                    )
                    if not translated <= remaining_cells:
                        continue
                    next_indices = remaining_piece_indices[:position] + remaining_piece_indices[position + 1 :]
                    next_remaining = frozenset(cell for cell in remaining_cells if cell not in translated)
                    next_placed = dict(placed_by_piece)
                    next_placed[int(piece_index)] = translated
                    _search(next_remaining, next_indices, next_placed)
                    if len(covering) > 1:
                        return

    _search(target, tuple(range(len(piece_shapes))), {})
    return set(covering)


def _build_marked_region_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    """Build one target silhouette with an interior missing region and piece options."""

    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.marked_region")
    option_count, option_count_range = _resolve_int_range_choice(
        params,
        min_key="marked_option_count_min",
        max_key="marked_option_count_max",
        fallback_min=_DEFAULTS.marked_option_count_min,
        fallback_max=_DEFAULTS.marked_option_count_max,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:marked_option_count",
    )
    target_cell_count_min, target_cell_count_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="marked_target_cell_count_min",
        max_key="marked_target_cell_count_max",
        fallback_min=_DEFAULTS.marked_target_cell_count_min,
        fallback_max=_DEFAULTS.marked_target_cell_count_max,
        context=f"{TASK_ID} marked target-cell-count bounds",
    )
    target_bbox_max_dim = int(
        params.get(
            "marked_target_bbox_max_dim",
            group_default(_GEN_DEFAULTS, "marked_target_bbox_max_dim", _DEFAULTS.marked_target_bbox_max_dim),
        )
    )
    correct_option_index = _resolve_correct_option_index(
        params,
        instance_seed=int(instance_seed),
        option_count=int(option_count),
        namespace=f"{TASK_ID}:marked_correct_option_index",
        option_count_range=option_count_range,
    )

    library = list(canonicalize_polyomino_cells(shape) for shape in PUZZLE_POLYOMINO_PIECE_LIBRARY)
    for _ in range(1000):
        correct_shape = canonicalize_polyomino_cells(rng.choice(library))
        missing_rotation = rng.choice(list(unique_rotations(correct_shape)))
        missing_width, missing_height = polyomino_bbox_dims(missing_rotation)
        min_width = int(missing_width + 2)
        min_height = int(missing_height + 2)
        if min_width > int(target_bbox_max_dim) or min_height > int(target_bbox_max_dim):
            continue
        target_width = int(rng.randrange(min_width, int(target_bbox_max_dim) + 1))
        target_height = int(rng.randrange(min_height, int(target_bbox_max_dim) + 1))
        missing_dx = int(rng.randrange(1, int(target_width - missing_width)))
        missing_dy = int(rng.randrange(1, int(target_height - missing_height)))
        missing_cells = set(translate_polyomino_cells(missing_rotation, missing_dx, missing_dy))
        target_cells = {
            (int(x), int(y))
            for y in range(int(target_height))
            for x in range(int(target_width))
        }

        edge_candidates = [
            cell
            for cell in target_cells
            if cell not in missing_cells
            and (
                int(cell[0]) in {0, int(target_width - 1)}
                or int(cell[1]) in {0, int(target_height - 1)}
            )
            and all(
                (int(cell[0] + dx), int(cell[1] + dy)) not in missing_cells
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            )
        ]
        rng.shuffle(edge_candidates)
        max_remove = max(0, min(5, len(edge_candidates) // 3))
        remove_target = int(rng.randrange(1, max_remove + 1)) if int(max_remove) > 0 else 0
        removed = 0
        for candidate in edge_candidates:
            if int(removed) >= int(remove_target):
                break
            next_target = set(target_cells)
            next_target.remove(candidate)
            visible_cells = set(next_target) - set(missing_cells)
            if not _missing_region_is_interior(target_cells=next_target, missing_cells=set(missing_cells)):
                continue
            if not _is_connected_cells(visible_cells):
                continue
            target_cells = next_target
            removed += 1

        visible_cells = set(target_cells) - set(missing_cells)
        if not _missing_region_is_interior(target_cells=set(target_cells), missing_cells=set(missing_cells)):
            continue
        if not _is_connected_cells(visible_cells):
            continue
        if not int(target_cell_count_min) <= len(target_cells) <= int(target_cell_count_max):
            continue

        option_shapes: List[Cells] = []
        seen_signatures = {_canonical_rotation_signature(correct_shape)}
        distractor_attempts = 0
        while len(option_shapes) < int(option_count - 1) and distractor_attempts < 800:
            distractor_attempts += 1
            candidate = canonicalize_polyomino_cells(rng.choice(library))
            signature = _canonical_rotation_signature(candidate)
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            option_shapes.append(candidate)
        if len(option_shapes) != int(option_count - 1):
            continue

        option_shapes.insert(int(correct_option_index), correct_shape)
        option_specs = []
        for option_index, shape in enumerate(option_shapes):
            option_specs.append(
                {
                    "option_panel_id": f"option_panel_{int(option_index + 1)}",
                    "option_label": option_label_for_index(int(option_index)),
                    "cells": [[int(x), int(y)] for x, y in shape],
                    "cell_count": int(polyomino_cell_count(shape)),
                    "bbox_dims": list(polyomino_bbox_dims(shape)),
                    "is_correct": bool(option_index == int(correct_option_index)),
                }
            )
        target_cells_tuple = canonicalize_polyomino_cells(target_cells)
        missing_cells_tuple = tuple(sorted((int(x), int(y)) for x, y in missing_cells))
        visible_cells_tuple = tuple(sorted((int(x), int(y)) for x, y in visible_cells))
        return {
            "query_variant": "marked_region_piece_label",
            "piece_count": int(option_count),
            "piece_count_range": list(option_count_range),
            "target_cells": [[int(x), int(y)] for x, y in target_cells_tuple],
            "visible_target_cells": [[int(x), int(y)] for x, y in visible_cells_tuple],
            "missing_cells": [[int(x), int(y)] for x, y in missing_cells_tuple],
            "marked_cells": [[int(x), int(y)] for x, y in missing_cells_tuple],
            "target_bbox_dims": list(polyomino_bbox_dims(target_cells_tuple)),
            "target_cell_count": int(polyomino_cell_count(target_cells_tuple)),
            "target_cell_count_range": [int(target_cell_count_min), int(target_cell_count_max)],
            "option_specs": list(option_specs),
            "option_count": int(option_count),
            "option_count_range": list(option_count_range),
            "answer_option_label": option_label_for_index(int(correct_option_index)),
            "correct_option_index": int(correct_option_index),
            "correct_option_panel_id": f"option_panel_{int(correct_option_index + 1)}",
            "solver_trace": {
                "correct_piece_cells": [[int(x), int(y)] for x, y in correct_shape],
                "missing_cells": [[int(x), int(y)] for x, y in missing_cells_tuple],
                "missing_region_interior": True,
            },
        }
    raise RuntimeError("failed to build marked-region polyomino puzzle")


def _shape_complement_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    """Translate polyomino complement-prefixed config into shape-complement helper keys."""

    mapping = {
        "option_count_min": ("complement_option_count_min", _DEFAULTS.complement_option_count_min),
        "option_count_max": ("complement_option_count_max", _DEFAULTS.complement_option_count_max),
        "target_width_min": ("complement_target_width_min", _DEFAULTS.complement_target_width_min),
        "target_width_max": ("complement_target_width_max", _DEFAULTS.complement_target_width_max),
        "target_height_min": ("complement_target_height_min", _DEFAULTS.complement_target_height_min),
        "target_height_max": ("complement_target_height_max", _DEFAULTS.complement_target_height_max),
        "cutout_cell_count_min": ("complement_cutout_cell_count_min", _DEFAULTS.complement_cutout_cell_count_min),
        "cutout_cell_count_max": ("complement_cutout_cell_count_max", _DEFAULTS.complement_cutout_cell_count_max),
        "transform_allowed_cutout_cell_count_min": (
            "complement_transform_allowed_cutout_cell_count_min",
            _DEFAULTS.complement_transform_allowed_cutout_cell_count_min,
        ),
        "shape_bbox_max_dim": ("complement_shape_bbox_max_dim", _DEFAULTS.complement_shape_bbox_max_dim),
    }
    resolved = dict(params)
    for helper_key, (config_key, fallback) in mapping.items():
        if str(helper_key) in resolved:
            continue
        resolved[str(helper_key)] = params.get(
            str(config_key),
            group_default(_GEN_DEFAULTS, str(config_key), fallback),
        )
    return resolved


def _build_rectangle_complement_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    matching_policy: str,
) -> Dict[str, Any]:
    """Build a rectangular complement dataset under the selected matching policy."""

    selected_policy = str(matching_policy)
    if selected_policy not in SUPPORTED_COMPLEMENT_MATCHING_POLICIES:
        raise ValueError(f"unsupported rectangle-complement matching_policy: {matching_policy}")
    helper_params = _shape_complement_params(params)
    helper_params.pop("query_variant", None)
    dataset = build_shape_complement_dataset_for_variant(
        query_variant=selected_policy,
        params=helper_params,
        instance_seed=int(instance_seed),
        gen_defaults={},
        defaults=_SHAPE_COMPLEMENT_DEFAULTS,
        task_id=TASK_ID,
    )
    converted = dict(dataset)
    converted["query_variant"] = "rectangle_complement_piece"
    converted["matching_policy_parameter"] = str(selected_policy)
    converted["target_cells"] = [list(cell) for cell in dataset["target_cells"]]
    converted["visible_target_cells"] = [list(cell) for cell in dataset["remaining_cells"]]
    converted["missing_cells"] = [list(cell) for cell in dataset["cutout_cells_in_target"]]
    converted["marked_cells"] = [list(cell) for cell in dataset["cutout_cells_in_target"]]
    converted["piece_count"] = int(dataset["option_count"])
    converted["piece_count_range"] = list(dataset["option_count_range"])
    converted["solver_trace"] = {
        **dict(dataset.get("solver_trace", {})),
        "public_query_variant": "rectangle_complement_piece",
        "matching_policy_parameter": str(selected_policy),
    }
    return converted


def _resolve_board_render_params(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
) -> Dict[str, Any]:
    """Resolve custom rendering knobs not present in the assembly renderer."""

    def _int(key: str, fallback: int) -> int:
        return int(
            resolve_render_int(
                params,
                _RENDER_DEFAULTS,
                str(key),
                int(fallback),
                instance_seed=int(instance_seed),
                namespace="puzzle_polyomino_arrangement_render",
            )
        )

    def _rgb(key: str, fallback: Sequence[int]) -> Tuple[int, int, int]:
        return tuple(
            int(value)
            for value in resolve_render_rgb(
                params,
                _RENDER_DEFAULTS,
                str(key),
                fallback,
                instance_seed=int(instance_seed),
                namespace="puzzle_polyomino_arrangement_render",
            )
        )

    unit_scale, unit_meta = resolve_puzzle_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="puzzles.polyomino.unit_size",
    )

    return {
        "board_cell_size_px": scale_puzzle_px(_int("board_cell_size_px", _DEFAULTS.board_cell_size_px), unit_scale, min_px=16),
        "board_cell_gap_px": scale_puzzle_px(_int("board_cell_gap_px", _DEFAULTS.board_cell_gap_px), unit_scale, min_px=1),
        "target_cell_size_px": scale_puzzle_px(_int("target_cell_size_px", _DEFAULTS.target_cell_size_px), unit_scale, min_px=16),
        "target_cell_gap_px": scale_puzzle_px(_int("target_cell_gap_px", _DEFAULTS.target_cell_gap_px), unit_scale, min_px=2),
        "unit_size_jitter": dict(unit_meta),
        "highlight_fill_rgb": _rgb("highlight_fill_rgb", _HIGHLIGHT_FILL_RGB),
        "empty_cell_rgb": _rgb("empty_cell_rgb", _EMPTY_CELL_RGB),
        "board_grid_rgb": _rgb("board_grid_rgb", _BOARD_GRID_RGB),
        "marked_cell_rgb": _rgb("marked_cell_rgb", _MARKED_CELL_RGB),
        "target_cell_rgb": _rgb("target_cell_rgb", _TARGET_CELL_RGB),
        "missing_cell_rgb": _rgb("missing_cell_rgb", _MISSING_CELL_RGB),
    }


def _draw_cells_at_origin(
    draw: ImageDraw.ImageDraw,
    *,
    origin_x: float,
    origin_y: float,
    cells: Iterable[Sequence[int]],
    cell_size_px: float,
    cell_gap_px: float,
    fill_rgb: Sequence[int],
    outline_rgb: Sequence[int],
    border_width_px: int,
    cell_corner_radius_px: int,
    marked_cells: set[Cell] | None = None,
    marked_fill_rgb: Sequence[int] | None = None,
) -> Tuple[List[List[float]], Dict[Cell, List[float]]]:
    """Draw one cell set at an explicit origin and return bboxes."""

    marked = set(marked_cells or set())
    marked_fill = tuple(marked_fill_rgb or fill_rgb)
    bboxes: List[List[float]] = []
    bbox_by_cell: Dict[Cell, List[float]] = {}
    for raw_cell in cells:
        cell_x, cell_y = int(raw_cell[0]), int(raw_cell[1])
        left = float(origin_x + int(cell_x) * (float(cell_size_px) + float(cell_gap_px)))
        top = float(origin_y + int(cell_y) * (float(cell_size_px) + float(cell_gap_px)))
        bbox = [round(left, 3), round(top, 3), round(left + float(cell_size_px), 3), round(top + float(cell_size_px), 3)]
        draw_rounded_rect(
            draw,
            tuple(bbox),
            radius=int(cell_corner_radius_px),
            fill=marked_fill if (cell_x, cell_y) in marked else fill_rgb,
            outline=outline_rgb,
            width=int(border_width_px),
        )
        bboxes.append(list(bbox))
        bbox_by_cell[(cell_x, cell_y)] = list(bbox)
    return bboxes, bbox_by_cell


def _render_option_panels(
    draw: ImageDraw.ImageDraw,
    *,
    options: Sequence[Mapping[str, Any]],
    options_left: float,
    options_top: float,
    option_panel_width: float,
    option_panel_height: float,
    option_gap: float,
    option_row_gap: float,
    render_params: PuzzleAssemblyRenderParams,
) -> Tuple[List[Dict[str, Any]], Dict[str, List[float]]]:
    """Render labeled polyomino option panels."""

    option_label_font = load_font(int(render_params.option_label_font_size_px), bold=True)
    option_cols, _ = centered_option_grid_shape(len(options))
    option_row_counts = centered_option_row_counts(len(options), option_cols)
    options_width = float((option_cols * option_panel_width) + max(0, option_cols - 1) * option_gap)
    entities: List[Dict[str, Any]] = []
    bbox_map: Dict[str, List[float]] = {}
    for option_index, option in enumerate(options):
        row_index = int(option_index // option_cols)
        row_option_count = int(option_row_counts[row_index])
        row_base_index = int(sum(option_row_counts[:row_index]))
        col_index = int(option_index - row_base_index)
        row_width = float(row_option_count * option_panel_width + max(0, row_option_count - 1) * option_gap)
        row_left = float(options_left + 0.5 * (options_width - row_width))
        panel_left = float(row_left + col_index * (option_panel_width + option_gap))
        panel_top = float(options_top + row_index * (option_panel_height + option_row_gap))
        panel_bbox = (
            float(panel_left),
            float(panel_top),
            float(panel_left + option_panel_width),
            float(panel_top + option_panel_height),
        )
        option_panel_id = str(option["option_panel_id"])
        rendered = render_puzzle_option_panel(
            draw,
            panel_bbox=panel_bbox,
            option_label=str(option["option_label"]),
            label_font=option_label_font,
            label_center_y_px=float(panel_top + 28.0),
            content_box_size_px=float(render_params.option_shape_box_size_px),
            content_gap_px=float(render_params.option_label_gap_px),
            panel_fill_rgb=render_params.option_panel_fill_rgb,
            content_fill_rgb=render_params.option_shape_fill_rgb,
            border_color_rgb=render_params.border_color_rgb,
            text_color_rgb=render_params.text_color_rgb,
            text_stroke_rgb=render_params.text_stroke_rgb,
            panel_corner_radius_px=int(render_params.panel_corner_radius_px),
            content_corner_radius_px=int(max(12, render_params.panel_corner_radius_px // 2)),
            border_width_px=int(render_params.border_width_px),
        )
        bbox_map[option_panel_id] = list(rendered.panel_bbox)
        entities.append(
            {
                "entity_id": option_panel_id,
                "entity_type": "puzzle_polyomino_option_panel",
                "bbox_px": list(rendered.panel_bbox),
                "attrs": {
                    "option_index": int(option_index),
                    "option_label": str(option["option_label"]),
                    "is_correct": bool(option["is_correct"]),
                },
            }
        )
        poly_bboxes = _draw_polyomino(
            draw,
            bbox=tuple(rendered.content_bbox),
            cells=option["cells"],
            fill_rgb=render_params.shape_fill_rgb,
            outline_rgb=render_params.border_color_rgb,
            border_width_px=max(1, int(render_params.border_width_px)),
            cell_size_px=float(render_params.shape_cell_size_px),
            cell_gap_px=float(render_params.shape_cell_gap_px),
            cell_corner_radius_px=int(render_params.cell_corner_radius_px),
        )
        for cell_index, cell_bbox in enumerate(poly_bboxes, start=1):
            entities.append(
                {
                    "entity_id": f"{option_panel_id}_cell_{int(cell_index)}",
                    "entity_type": "puzzle_polyomino_option_cell",
                    "bbox_px": list(cell_bbox),
                    "attrs": {"option_panel_id": str(option_panel_id), "option_label": str(option["option_label"])},
                }
            )
    return entities, bbox_map


def _render_marked_region_scene(
    background: Image.Image,
    *,
    scene_variant: str,
    dataset: Mapping[str, Any],
    render_params: PuzzleAssemblyRenderParams,
    custom_params: Mapping[str, Any],
) -> _RenderedPolyominoScene:
    """Render the marked-region piece-identification variant."""

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    target_cells = tuple((int(cell[0]), int(cell[1])) for cell in dataset["target_cells"])
    visible_target_cells = tuple(
        (int(cell[0]), int(cell[1]))
        for cell in dataset.get("visible_target_cells", dataset["target_cells"])
    )
    missing_cells = {
        (int(cell[0]), int(cell[1]))
        for cell in dataset.get("missing_cells", dataset.get("marked_cells", []))
    }
    target_width, target_height = polyomino_bbox_dims(target_cells)
    target_cell_size = float(custom_params["target_cell_size_px"])
    target_cell_gap = float(custom_params["target_cell_gap_px"])
    target_width_px = float(target_width * target_cell_size + max(0, target_width - 1) * target_cell_gap)
    target_height_px = float(target_height * target_cell_size + max(0, target_height - 1) * target_cell_gap)
    option_count = int(dataset["option_count"])
    option_panel_width = float(render_params.option_panel_width_px)
    option_panel_height = float(render_params.option_panel_height_px)
    option_gap = float(render_params.option_gap_px)
    option_row_gap = float(render_params.option_row_gap_px)
    option_cols, option_rows = centered_option_grid_shape(option_count)
    options_width = float(option_cols * option_panel_width + max(0, option_cols - 1) * option_gap)
    options_height = float(option_rows * option_panel_height + max(0, option_rows - 1) * option_row_gap)
    content_width = float(max(target_width_px, options_width))
    content_height = float(target_height_px + render_params.piece_to_options_gap_px + options_height)
    usable_width = float(render_params.canvas_width - render_params.scene_margin_left_px - render_params.scene_margin_right_px)
    usable_height = float(render_params.canvas_height - render_params.scene_margin_top_px - render_params.scene_margin_bottom_px)
    content_left = float(render_params.scene_margin_left_px + max(0.0, 0.5 * (usable_width - content_width)))
    content_top = float(render_params.scene_margin_top_px + max(0.0, 0.5 * (usable_height - content_height)))
    target_left = float(content_left + 0.5 * (content_width - target_width_px))
    target_top = float(content_top)
    options_left = float(content_left + 0.5 * (content_width - options_width))
    options_top = float(target_top + target_height_px + render_params.piece_to_options_gap_px)
    panel_padding = float(render_params.piece_panel_padding_px)
    target_panel_bbox = (
        float(target_left - panel_padding),
        float(target_top - panel_padding),
        float(target_left + target_width_px + panel_padding),
        float(target_top + target_height_px + panel_padding),
    )
    options_panel_bbox = (
        float(options_left - panel_padding),
        float(options_top - panel_padding),
        float(options_left + options_width + panel_padding),
        float(options_top + options_height + panel_padding),
    )
    entities: List[Dict[str, Any]] = []
    if str(scene_variant) in {"polyomino_card", "polyomino_outline"}:
        fill = render_params.panel_fill_rgb if str(scene_variant) == "polyomino_card" else (248, 248, 248)
        for panel_id, panel_bbox, panel_role in (
            ("polyomino_target_panel", target_panel_bbox, "target"),
            ("polyomino_options_panel", options_panel_bbox, "options"),
        ):
            draw_rounded_rect(
                draw,
                panel_bbox,
                radius=int(render_params.panel_corner_radius_px),
                fill=fill,
                outline=render_params.border_color_rgb,
                width=int(render_params.border_width_px),
            )
            entities.append(
                {
                    "entity_id": panel_id,
                    "entity_type": "puzzle_polyomino_panel",
                    "bbox_px": [round(float(value), 3) for value in panel_bbox],
                    "attrs": {"panel_role": panel_role, "scene_variant": str(scene_variant)},
                }
            )

    cell_bboxes, bbox_by_cell = _draw_cells_at_origin(
        draw,
        origin_x=float(target_left),
        origin_y=float(target_top),
        cells=visible_target_cells,
        cell_size_px=float(target_cell_size),
        cell_gap_px=float(target_cell_gap),
        fill_rgb=custom_params["target_cell_rgb"],
        outline_rgb=render_params.border_color_rgb,
        border_width_px=max(1, int(render_params.border_width_px)),
        cell_corner_radius_px=int(render_params.cell_corner_radius_px),
    )
    missing_bboxes, missing_bbox_by_cell = _draw_cells_at_origin(
        draw,
        origin_x=float(target_left),
        origin_y=float(target_top),
        cells=missing_cells,
        cell_size_px=float(target_cell_size),
        cell_gap_px=float(target_cell_gap),
        fill_rgb=custom_params["missing_cell_rgb"],
        outline_rgb=render_params.border_color_rgb,
        border_width_px=max(1, int(render_params.border_width_px)),
        cell_corner_radius_px=int(render_params.cell_corner_radius_px),
    )
    bbox_by_cell.update(missing_bbox_by_cell)
    for cell, bbox in zip(visible_target_cells, cell_bboxes):
        entities.append(
            {
                "entity_id": f"target_cell_{int(cell[0])}_{int(cell[1])}",
                "entity_type": "puzzle_polyomino_target_cell",
                "bbox_px": list(bbox),
                "attrs": {"x": int(cell[0]), "y": int(cell[1]), "missing": False},
            }
        )
    del missing_bboxes
    for cell in sorted(missing_cells):
        entities.append(
            {
                "entity_id": f"missing_cell_{int(cell[0])}_{int(cell[1])}",
                "entity_type": "puzzle_polyomino_missing_cell",
                "bbox_px": list(bbox_by_cell[cell]),
                "attrs": {"x": int(cell[0]), "y": int(cell[1]), "missing": True},
            }
        )
    option_entities, option_bbox_map = _render_option_panels(
        draw,
        options=list(dataset["option_specs"]),
        options_left=float(options_left),
        options_top=float(options_top),
        option_panel_width=float(option_panel_width),
        option_panel_height=float(option_panel_height),
        option_gap=float(option_gap),
        option_row_gap=float(option_row_gap),
        render_params=render_params,
    )
    entities.extend(option_entities)
    marked_bbox = [0.0, 0.0, 0.0, 0.0]
    if missing_cells:
        missing_cell_bboxes = [bbox_by_cell[cell] for cell in sorted(missing_cells)]
        marked_bbox = [
            min(float(bbox[0]) for bbox in missing_cell_bboxes),
            min(float(bbox[1]) for bbox in missing_cell_bboxes),
            max(float(bbox[2]) for bbox in missing_cell_bboxes),
            max(float(bbox[3]) for bbox in missing_cell_bboxes),
        ]
    bbox_map = dict(option_bbox_map)
    bbox_map["marked_region"] = [round(float(value), 3) for value in marked_bbox]
    scene_bbox = [
        round(float(min(target_panel_bbox[0], options_panel_bbox[0])), 3),
        round(float(min(target_panel_bbox[1], options_panel_bbox[1])), 3),
        round(float(max(target_panel_bbox[2], options_panel_bbox[2])), 3),
        round(float(max(target_panel_bbox[3], options_panel_bbox[3])), 3),
    ]
    return _RenderedPolyominoScene(image=image, entities=entities, scene_bbox_px=scene_bbox, bbox_map=bbox_map)


class _PuzzlesSpatialPolyominoArrangementBaseTask:
    """Answer static polyomino arrangement questions from options or board state."""

    task_id = TASK_ID
    domain = "puzzles"
    task_group = "spatial"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_variant, query_variant_probabilities = _resolve_query_variant(params, instance_seed=int(instance_seed))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        dataset_params = decouple_axis_sampling(
            params,
            preceding_axis_size=len(SUPPORTED_QUERY_VARIANTS),
            explicit_key="query_variant",
        )
        render_params = resolve_assembly_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_ASSEMBLY_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        scene_id_for_style = POLYOMINO_MISSING_REGION_SCENE_ID
        scene_style, scene_style_meta = resolve_puzzle_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.{scene_id_for_style}.background",
        )
        render_params = replace(
            render_params,
            panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            piece_card_fill_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
            option_panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            option_shape_fill_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
            shape_fill_rgb=tuple(int(value) for value in scene_style.mark_rgb),
            border_color_rgb=tuple(int(value) for value in scene_style.grid_rgb),
            text_color_rgb=tuple(int(value) for value in scene_style.text_rgb),
            text_stroke_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
        )
        custom_render_params = _resolve_board_render_params(params, instance_seed=int(instance_seed))
        custom_render_params = {
            **dict(custom_render_params),
            "highlight_fill_rgb": tuple(int(value) for value in scene_style.step_fill_rgb),
            "empty_cell_rgb": tuple(int(value) for value in scene_style.option_fill_rgb),
            "board_grid_rgb": tuple(int(value) for value in scene_style.grid_rgb),
            "marked_cell_rgb": tuple(int(value) for value in scene_style.mark_rgb),
            "target_cell_rgb": tuple(int(value) for value in scene_style.step_fill_rgb),
        }
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )

        if str(query_variant) == "marked_region_piece_label":
            dataset = _build_marked_region_dataset(params=dataset_params, instance_seed=int(instance_seed))
            rendered_scene = _render_marked_region_scene(
                background,
                scene_variant=str(scene_variant),
                dataset=dataset,
                render_params=render_params,
                custom_params=custom_render_params,
            )
            evidence_item_ids = [str(dataset["correct_option_panel_id"]), "marked_region"]
            question_format = "polyomino_marked_region_piece"
            view_family = "polyomino_marked_target_piece_option_puzzle"
        elif str(query_variant) == "rectangle_complement_piece":
            matching_policy, matching_policy_probabilities = _resolve_complement_matching_policy(
                dataset_params,
                instance_seed=int(instance_seed),
            )
            dataset = _build_rectangle_complement_dataset(
                params=dataset_params,
                instance_seed=int(instance_seed),
                matching_policy=str(matching_policy),
            )
            rendered_scene = _render_marked_region_scene(
                background,
                scene_variant=str(scene_variant),
                dataset=dataset,
                render_params=render_params,
                custom_params=custom_render_params,
            )
            evidence_item_ids = [str(dataset["correct_option_panel_id"]), "marked_region"]
            question_format = "polyomino_rectangle_complement_piece"
            view_family = "polyomino_rectangle_complement_piece_option_puzzle"
        else:
            raise ValueError(f"unsupported polyomino query_variant: {query_variant}")
        if str(query_variant) != "rectangle_complement_piece":
            matching_policy = None
            matching_policy_probabilities = {}

        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "object_description_polyomino_strip",
                "object_description_polyomino_card",
                "object_description_polyomino_outline",
                "evidence_hint_marked_region_piece_label",
                "evidence_hint_rectangle_complement_piece",
                "json_example_marked_region_piece_label",
                "json_example_rectangle_complement_piece",
                "json_example_answer_only_marked_region_piece_label",
                "json_example_answer_only_rectangle_complement_piece",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        matching_policy_instruction = ""
        if str(query_variant) == "rectangle_complement_piece":
            if str(matching_policy) == "rotation_reflection_allowed":
                matching_policy_instruction = "Rotation and reflection are allowed for the option piece."
            else:
                matching_policy_instruction = "Do not rotate or reflect any option piece."
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(scene_variant)}"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(query_variant)}"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults[f"json_example_{str(query_variant)}"]),
                "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{str(query_variant)}"]),
                "matching_policy_instruction": str(matching_policy_instruction),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_projection = projected_puzzle_bbox_evidence(rendered_scene.bbox_map, evidence_item_ids)
        evidence_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in evidence_projection["bbox_set"]
        ]
        answer_value = str(dataset["answer_option_label"])
        answer_gt = TypedValue(type="option_letter", value=str(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        option_count = int(dataset.get("option_count", len(dataset.get("option_specs", []))))
        target_cell_count = int(dataset.get("target_cell_count", len(dataset.get("target_cells", []))))
        piece_count = int(dataset.get("piece_count", option_count))
        visual_scan = clamp_unit_interval(
            0.42 * normalize_int_with_bounds(option_count, [3, 6])
            + 0.34 * normalize_int_with_bounds(target_cell_count, [8, 20])
            + 0.24 * normalize_int_with_bounds(piece_count, [2, 5])
        )
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BASE_BY_VARIANT[str(query_variant)])
            + 0.10 * normalize_int_with_bounds(target_cell_count, [8, 16])
            + 0.08 * normalize_int_with_bounds(option_count, [3, 6])
        )
        complexity = build_puzzle_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": float(visual_scan),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"puzzle_spatial_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_variant": str(query_variant),
                    "scene_variant": str(scene_variant),
                    "answer_option_label": str(answer_value),
                    "correct_option_panel_id": str(dataset["correct_option_panel_id"]),
                    "view_family": str(view_family),
                },
            },
            "query_spec": {
                "query_variant": str(query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_variant": str(query_variant),
                    "scene_variant": str(scene_variant),
                    "query_variant_probabilities": dict(query_variant_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "matching_policy": None if matching_policy is None else str(matching_policy),
                    "matching_policy_probabilities": dict(matching_policy_probabilities),
                    "option_count": int(option_count),
                    "option_count_range": list(dataset.get("option_count_range", [])),
                    "piece_count": int(piece_count),
                    "piece_count_range": list(dataset.get("piece_count_range", [])),
                    "target_cell_count": int(target_cell_count),
                    "target_cell_count_range": list(dataset.get("target_cell_count_range", [])),
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
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "text_style": {"option_label_font_size_px": int(render_params.option_label_font_size_px)},
                "unit_size_jitter": dict(render_params.unit_size_jitter),
            },
            "render_map": with_puzzle_unit_size_jitter({
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "item_bboxes_px": {str(key): list(value) for key, value in rendered_scene.bbox_map.items()},
            }, render_params.unit_size_jitter),
            "execution_trace": {
                "query_variant": str(query_variant),
                "scene_variant": str(scene_variant),
                "query_variant_probabilities": dict(query_variant_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "matching_policy": None if matching_policy is None else str(matching_policy),
                "matching_policy_probabilities": dict(matching_policy_probabilities),
                "question_format": str(question_format),
                "view_family": str(view_family),
                "answer_option_label": str(answer_value),
                "correct_option_index": int(dataset["correct_option_index"]),
                "correct_option_panel_id": str(dataset["correct_option_panel_id"]),
                "evidence_item_ids": [str(item) for item in evidence_item_ids],
                "option_specs": [dict(spec) for spec in dataset.get("option_specs", [])],
                "solver_trace": dict(dataset.get("solver_trace", {})),
                "variant_payload": {
                    str(key): _json_safe(value)
                    for key, value in dict(dataset).items()
                    if str(key) not in {"option_specs", "solver_trace"}
                },
            },
            "witness_symbolic": {"type": "bbox_set", "value": list(evidence_bboxes)},
            "projected_evidence": dict(evidence_projection),
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_variant=str(query_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class PuzzlesSpatialPolyominoMissingRegionPieceLabelTask(_PuzzlesSpatialPolyominoArrangementBaseTask):
    """Choose the piece that fills a marked or rectangular missing region."""

    task_id = POLYOMINO_MISSING_REGION_PIECE_LABEL_TASK_ID
    public_scene_id = POLYOMINO_MISSING_REGION_SCENE_ID

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_variants = tuple(str(value) for value in SUPPORTED_MISSING_REGION_QUERY_VARIANTS)
        query_variant_set = set(query_variants)
        merged_params = dict(params)
        explicit_query = merged_params.get("query_variant")
        explicit_task = merged_params.get("query_variant")
        explicit = explicit_task if explicit_task is not None else explicit_query
        if explicit is not None:
            explicit_text = str(explicit)
            if explicit_text not in query_variant_set:
                raise ValueError(f"unsupported query_variant for {self.task_id}: {explicit_text}")
            merged_params["query_variant"] = explicit_text
            merged_params["query_variant"] = explicit_text
        else:
            raw_weights = merged_params.get("query_variant_weights")
            if isinstance(raw_weights, Mapping):
                weights = {
                    str(key): float(raw_weights[key])
                    for key in query_variants
                    if str(key) in raw_weights and float(raw_weights[key]) > 0.0
                }
                if not weights:
                    weights = {key: 1.0 for key in query_variants}
            else:
                weights = {key: 1.0 for key in query_variants}
            merged_params["query_variant_weights"] = weights

        output = super().generate(int(instance_seed), params=merged_params, max_attempts=int(max_attempts))
        payload = output.trace_payload if isinstance(output.trace_payload, Mapping) else {}
        execution = payload.get("execution_trace") if isinstance(payload, Mapping) else {}
        query_id = str(output.query_variant)
        if isinstance(execution, Mapping):
            query_id = str(execution.get("query_variant") or execution.get("query_id") or query_id)
        if query_id not in query_variant_set:
            raise ValueError(f"unsupported resolved query_variant for {self.task_id}: {query_id}")
        return rewrite_fixed_puzzle_query_output(
            output,
            query_id=str(query_id),
            scene_id=str(self.public_scene_id),
        )


__all__ = [
    "PuzzlesSpatialPolyominoMissingRegionPieceLabelTask",
]
