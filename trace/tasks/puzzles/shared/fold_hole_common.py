"""Shared dataset builders and render defaults for fold-hole puzzle scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default
from .common import resolve_puzzle_axis_variant


SUPPORTED_PUZZLE_FOLD_SCENE_VARIANTS: Tuple[str, ...] = (
    "fold_strip",
    "fold_card",
    "fold_outline",
)


def _resolve_int_param(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
    fallback: int,
) -> int:
    """Resolve one integer render/generation parameter from params/defaults."""

    return int(params.get(str(key), group_default(defaults, str(key), int(fallback))))


@dataclass(frozen=True)
class PuzzleFoldHoleDefaults:
    """Domain defaults for the fold-hole spatial puzzle."""

    option_count_min: int = 6
    option_count_max: int = 6
    grid_size: int = 6


@dataclass(frozen=True)
class PuzzleFoldHoleRenderParams:
    """Resolved rendering knobs for fold-hole scenes."""

    canvas_width: int
    canvas_height: int
    scene_margin_left_px: int
    scene_margin_right_px: int
    scene_margin_top_px: int
    scene_margin_bottom_px: int
    reference_panel_height_px: int
    reference_panel_padding_px: int
    step_panel_width_px: int
    step_panel_height_px: int
    step_panel_gap_px: int
    step_arrow_gap_px: int
    reference_to_options_gap_px: int
    option_panel_width_px: int
    option_panel_height_px: int
    option_gap_px: int
    option_label_gap_px: int
    option_content_box_size_px: int
    option_content_padding_px: int
    paper_corner_radius_px: int
    panel_corner_radius_px: int
    border_width_px: int
    option_label_font_size_px: int
    panel_fill_rgb: Tuple[int, int, int]
    option_panel_fill_rgb: Tuple[int, int, int]
    option_content_fill_rgb: Tuple[int, int, int]
    paper_fill_rgb: Tuple[int, int, int]
    paper_shadow_rgb: Tuple[int, int, int]
    border_color_rgb: Tuple[int, int, int]
    text_color_rgb: Tuple[int, int, int]
    text_stroke_rgb: Tuple[int, int, int]
    fold_line_rgb: Tuple[int, int, int]
    hole_fill_rgb: Tuple[int, int, int]
    arrow_rgb: Tuple[int, int, int]
    instruction_fill_rgb: Tuple[int, int, int]


def resolve_fold_hole_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the active fold-hole scene variant."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_PUZZLE_FOLD_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def resolve_fold_hole_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
) -> PuzzleFoldHoleRenderParams:
    """Resolve rendering params for the fold-hole puzzle."""

    return PuzzleFoldHoleRenderParams(
        canvas_width=int(_resolve_int_param(params, render_defaults, "canvas_width", 1260)),
        canvas_height=int(_resolve_int_param(params, render_defaults, "canvas_height", 860)),
        scene_margin_left_px=int(_resolve_int_param(params, render_defaults, "scene_margin_left_px", 64)),
        scene_margin_right_px=int(_resolve_int_param(params, render_defaults, "scene_margin_right_px", 64)),
        scene_margin_top_px=int(_resolve_int_param(params, render_defaults, "scene_margin_top_px", 56)),
        scene_margin_bottom_px=int(_resolve_int_param(params, render_defaults, "scene_margin_bottom_px", 56)),
        reference_panel_height_px=int(_resolve_int_param(params, render_defaults, "reference_panel_height_px", 316)),
        reference_panel_padding_px=int(_resolve_int_param(params, render_defaults, "reference_panel_padding_px", 28)),
        step_panel_width_px=int(_resolve_int_param(params, render_defaults, "step_panel_width_px", 208)),
        step_panel_height_px=int(_resolve_int_param(params, render_defaults, "step_panel_height_px", 208)),
        step_panel_gap_px=int(_resolve_int_param(params, render_defaults, "step_panel_gap_px", 28)),
        step_arrow_gap_px=int(_resolve_int_param(params, render_defaults, "step_arrow_gap_px", 12)),
        reference_to_options_gap_px=int(_resolve_int_param(params, render_defaults, "reference_to_options_gap_px", 48)),
        option_panel_width_px=int(_resolve_int_param(params, render_defaults, "option_panel_width_px", 148)),
        option_panel_height_px=int(_resolve_int_param(params, render_defaults, "option_panel_height_px", 188)),
        option_gap_px=int(_resolve_int_param(params, render_defaults, "option_gap_px", 18)),
        option_label_gap_px=int(_resolve_int_param(params, render_defaults, "option_label_gap_px", 16)),
        option_content_box_size_px=int(_resolve_int_param(params, render_defaults, "option_content_box_size_px", 102)),
        option_content_padding_px=int(_resolve_int_param(params, render_defaults, "option_content_padding_px", 10)),
        paper_corner_radius_px=int(_resolve_int_param(params, render_defaults, "paper_corner_radius_px", 18)),
        panel_corner_radius_px=int(_resolve_int_param(params, render_defaults, "panel_corner_radius_px", 28)),
        border_width_px=int(_resolve_int_param(params, render_defaults, "border_width_px", 3)),
        option_label_font_size_px=int(_resolve_int_param(params, render_defaults, "option_label_font_size_px", 30)),
        panel_fill_rgb=tuple(int(v) for v in render_defaults.get("panel_fill_rgb", (248, 249, 252))),
        option_panel_fill_rgb=tuple(int(v) for v in render_defaults.get("option_panel_fill_rgb", (251, 251, 255))),
        option_content_fill_rgb=tuple(int(v) for v in render_defaults.get("option_content_fill_rgb", (252, 252, 255))),
        paper_fill_rgb=tuple(int(v) for v in render_defaults.get("paper_fill_rgb", (255, 252, 245))),
        paper_shadow_rgb=tuple(int(v) for v in render_defaults.get("paper_shadow_rgb", (236, 230, 215))),
        border_color_rgb=tuple(int(v) for v in render_defaults.get("border_color_rgb", (86, 94, 108))),
        text_color_rgb=tuple(int(v) for v in render_defaults.get("text_color_rgb", (30, 34, 40))),
        text_stroke_rgb=tuple(int(v) for v in render_defaults.get("text_stroke_rgb", (255, 255, 255))),
        fold_line_rgb=tuple(int(v) for v in render_defaults.get("fold_line_rgb", (100, 116, 145))),
        hole_fill_rgb=tuple(int(v) for v in render_defaults.get("hole_fill_rgb", (30, 34, 40))),
        arrow_rgb=tuple(int(v) for v in render_defaults.get("arrow_rgb", (54, 102, 180))),
        instruction_fill_rgb=tuple(int(v) for v in render_defaults.get("instruction_fill_rgb", (238, 243, 250))),
    )


def _sort_cells(cells: Iterable[Tuple[int, int]]) -> List[List[int]]:
    """Canonicalize cell coordinates into row-major order."""

    return [[int(x), int(y)] for x, y in sorted({(int(x), int(y)) for x, y in cells}, key=lambda item: (item[1], item[0]))]


def _mirror_vertical(cells: Iterable[Tuple[int, int]], *, grid_size: int) -> Set[Tuple[int, int]]:
    """Reflect cells across the vertical center line."""

    last = int(grid_size) - 1
    return {(int(last - x), int(y)) for x, y in cells}


def _mirror_horizontal(cells: Iterable[Tuple[int, int]], *, grid_size: int) -> Set[Tuple[int, int]]:
    """Reflect cells across the horizontal center line."""

    last = int(grid_size) - 1
    return {(int(x), int(last - y)) for x, y in cells}


def _rotate_180(cells: Iterable[Tuple[int, int]], *, grid_size: int) -> Set[Tuple[int, int]]:
    """Rotate a hole pattern by 180 degrees."""

    last = int(grid_size) - 1
    return {(int(last - x), int(last - y)) for x, y in cells}


def _transpose(cells: Iterable[Tuple[int, int]], *, grid_size: int) -> Optional[Set[Tuple[int, int]]]:
    """Swap x/y coordinates when the pattern still fits the same square sheet."""

    transposed = {(int(y), int(x)) for x, y in cells}
    if all(0 <= int(x) < int(grid_size) and 0 <= int(y) < int(grid_size) for x, y in transposed):
        return transposed
    return None


def _shift_pattern(
    cells: Iterable[Tuple[int, int]],
    *,
    grid_size: int,
    dx: int,
    dy: int,
) -> Optional[Set[Tuple[int, int]]]:
    """Shift a full unfolded pattern if it still stays on the sheet."""

    shifted = {(int(x) + int(dx), int(y) + int(dy)) for x, y in cells}
    if not shifted:
        return None
    if all(0 <= int(x) < int(grid_size) and 0 <= int(y) < int(grid_size) for x, y in shifted):
        return shifted
    return None


def _unfold_single_fold(
    folded_cells: Iterable[Tuple[int, int]],
    *,
    axis: str,
    grid_size: int,
) -> Set[Tuple[int, int]]:
    """Unfold a single-fold packet back to the full sheet."""

    base = {(int(x), int(y)) for x, y in folded_cells}
    if str(axis) == "vertical":
        return set(base) | _mirror_vertical(base, grid_size=int(grid_size))
    if str(axis) == "horizontal":
        return set(base) | _mirror_horizontal(base, grid_size=int(grid_size))
    raise ValueError(f"unsupported single-fold axis: {axis}")


def _unfold_double_fold(
    folded_cells: Iterable[Tuple[int, int]],
    *,
    grid_size: int,
) -> Set[Tuple[int, int]]:
    """Unfold a vertical-then-horizontal packet back to the full sheet."""

    base = {(int(x), int(y)) for x, y in folded_cells}
    return set(base) | _mirror_vertical(base, grid_size=int(grid_size)) | _mirror_horizontal(base, grid_size=int(grid_size)) | _mirror_horizontal(_mirror_vertical(base, grid_size=int(grid_size)), grid_size=int(grid_size))


def _sample_single_fold_holes(
    rng,
    *,
    grid_size: int,
    axis: str,
    hole_count: int,
) -> List[Tuple[int, int]]:
    """Sample holes on the folded packet for a single-fold puzzle."""

    if str(axis) == "vertical":
        candidates = [(int(x), int(y)) for y in range(int(grid_size)) for x in range(int(grid_size // 2))]
    else:
        candidates = [(int(x), int(y)) for y in range(int(grid_size // 2)) for x in range(int(grid_size))]
    sampled = rng.sample(candidates, int(hole_count))
    return [(int(x), int(y)) for x, y in sampled]


def _sample_double_fold_holes(
    rng,
    *,
    grid_size: int,
    hole_count: int,
) -> List[Tuple[int, int]]:
    """Sample holes on the folded packet for a double-fold puzzle."""

    candidates = [(int(x), int(y)) for y in range(int(grid_size // 2)) for x in range(int(grid_size // 2))]
    sampled = rng.sample(candidates, int(hole_count))
    return [(int(x), int(y)) for x, y in sampled]


def _folded_only_pattern(
    folded_cells: Iterable[Tuple[int, int]],
) -> Set[Tuple[int, int]]:
    """Return the visible holes only on the folded packet."""

    return {(int(x), int(y)) for x, y in folded_cells}


def _candidate_patterns_for_single_fold(
    *,
    folded_cells: Sequence[Tuple[int, int]],
    correct_cells: Set[Tuple[int, int]],
    axis: str,
    grid_size: int,
) -> List[Set[Tuple[int, int]]]:
    """Generate structured distractor candidates for one single-fold puzzle."""

    base = _folded_only_pattern(folded_cells)
    wrong_axis = "horizontal" if str(axis) == "vertical" else "vertical"
    candidates: List[Set[Tuple[int, int]]] = [
        set(base),
        _unfold_single_fold(base, axis=str(wrong_axis), grid_size=int(grid_size)),
        set(base) | _mirror_vertical(base, grid_size=int(grid_size)) | _mirror_horizontal(base, grid_size=int(grid_size)),
    ]
    rotated = _rotate_180(correct_cells, grid_size=int(grid_size))
    transposed = _transpose(correct_cells, grid_size=int(grid_size))
    candidates.append(rotated)
    if transposed is not None:
        candidates.append(transposed)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)):
        shifted = _shift_pattern(correct_cells, grid_size=int(grid_size), dx=int(dx), dy=int(dy))
        if shifted is not None:
            candidates.append(shifted)
    return candidates


def _candidate_patterns_for_double_fold(
    *,
    folded_cells: Sequence[Tuple[int, int]],
    correct_cells: Set[Tuple[int, int]],
    grid_size: int,
) -> List[Set[Tuple[int, int]]]:
    """Generate structured distractor candidates for one double-fold puzzle."""

    base = _folded_only_pattern(folded_cells)
    candidates: List[Set[Tuple[int, int]]] = [
        set(base),
        set(base) | _mirror_vertical(base, grid_size=int(grid_size)),
        set(base) | _mirror_horizontal(base, grid_size=int(grid_size)),
    ]
    for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, -1)):
        shifted = _shift_pattern(correct_cells, grid_size=int(grid_size), dx=int(dx), dy=int(dy))
        if shifted is not None:
            candidates.append(shifted)
    if len(correct_cells) > 1:
        sorted_cells = sorted(correct_cells, key=lambda item: (item[1], item[0]))
        candidates.append(set(sorted_cells[:-1]))
    return candidates


def _random_pattern(rng, *, grid_size: int, point_count: int) -> Set[Tuple[int, int]]:
    """Sample a fallback random unfolded hole pattern."""

    candidates = [(int(x), int(y)) for y in range(int(grid_size)) for x in range(int(grid_size))]
    chosen = rng.sample(candidates, max(1, min(len(candidates), int(point_count))))
    return {(int(x), int(y)) for x, y in chosen}


def _build_option_patterns(
    *,
    rng,
    correct_cells: Set[Tuple[int, int]],
    candidate_patterns: Sequence[Set[Tuple[int, int]]],
    option_count: int,
    grid_size: int,
) -> List[Set[Tuple[int, int]]]:
    """Choose one unique correct pattern plus distinct distractors."""

    unique: List[Set[Tuple[int, int]]] = []
    seen = {frozenset(correct_cells)}
    for pattern in candidate_patterns:
        signature = frozenset((int(x), int(y)) for x, y in pattern)
        if not pattern or signature in seen:
            continue
        seen.add(signature)
        unique.append(set(pattern))
        if len(unique) >= int(option_count) - 1:
            break
    while len(unique) < int(option_count) - 1:
        raw = _random_pattern(
            rng,
            grid_size=int(grid_size),
            point_count=max(1, len(correct_cells) + rng.choice([-1, 0, 1])),
        )
        signature = frozenset(raw)
        if signature in seen:
            continue
        seen.add(signature)
        unique.append(set(raw))
    return unique


def build_fold_hole_dataset_for_variant(
    *,
    task_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleFoldHoleDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Build one fold-hole puzzle dataset with a unique correct option."""

    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")
    option_count = int(_resolve_int_param(params, gen_defaults, "option_count_min", defaults.option_count_min))
    option_count_max = int(_resolve_int_param(params, gen_defaults, "option_count_max", defaults.option_count_max))
    if int(option_count_max) < int(option_count):
        option_count_max = int(option_count)
    option_count = int(rng.randint(int(option_count), int(option_count_max)))
    grid_size = int(_resolve_int_param(params, gen_defaults, "grid_size", defaults.grid_size))
    if int(grid_size) % 2 != 0:
        raise ValueError("fold-hole puzzles require an even grid_size")

    if str(task_variant) == "single_fold_single_hole":
        fold_mode = "single"
        fold_axes = [str(rng.choice(["vertical", "horizontal"]))]
        folded_holes = _sample_single_fold_holes(
            rng,
            grid_size=int(grid_size),
            axis=str(fold_axes[0]),
            hole_count=1,
        )
        correct_cells = _unfold_single_fold(folded_holes, axis=str(fold_axes[0]), grid_size=int(grid_size))
        candidates = _candidate_patterns_for_single_fold(
            folded_cells=folded_holes,
            correct_cells=set(correct_cells),
            axis=str(fold_axes[0]),
            grid_size=int(grid_size),
        )
    elif str(task_variant) == "single_fold_two_holes":
        fold_mode = "single"
        fold_axes = [str(rng.choice(["vertical", "horizontal"]))]
        folded_holes = _sample_single_fold_holes(
            rng,
            grid_size=int(grid_size),
            axis=str(fold_axes[0]),
            hole_count=2,
        )
        correct_cells = _unfold_single_fold(folded_holes, axis=str(fold_axes[0]), grid_size=int(grid_size))
        candidates = _candidate_patterns_for_single_fold(
            folded_cells=folded_holes,
            correct_cells=set(correct_cells),
            axis=str(fold_axes[0]),
            grid_size=int(grid_size),
        )
    elif str(task_variant) == "double_fold_single_hole":
        fold_mode = "double"
        fold_axes = ["vertical", "horizontal"]
        folded_holes = _sample_double_fold_holes(
            rng,
            grid_size=int(grid_size),
            hole_count=1,
        )
        correct_cells = _unfold_double_fold(folded_holes, grid_size=int(grid_size))
        candidates = _candidate_patterns_for_double_fold(
            folded_cells=folded_holes,
            correct_cells=set(correct_cells),
            grid_size=int(grid_size),
        )
    else:
        raise ValueError(f"unsupported fold-hole task variant: {task_variant}")

    distractor_patterns = _build_option_patterns(
        rng=rng,
        correct_cells=set(correct_cells),
        candidate_patterns=list(candidates),
        option_count=int(option_count),
        grid_size=int(grid_size),
    )
    correct_index = int(rng.randrange(int(option_count)))
    option_patterns: List[Set[Tuple[int, int]]] = []
    distractor_iter = iter(distractor_patterns)
    for index in range(int(option_count)):
        if int(index) == int(correct_index):
            option_patterns.append(set(correct_cells))
        else:
            option_patterns.append(set(next(distractor_iter)))

    option_specs: List[Dict[str, Any]] = []
    for index, pattern in enumerate(option_patterns):
        option_label = chr(ord("A") + int(index))
        option_panel_id = f"option_panel_{option_label}"
        option_specs.append(
            {
                "option_label": str(option_label),
                "option_panel_id": str(option_panel_id),
                "hole_cells": _sort_cells(pattern),
                "is_correct": bool(int(index) == int(correct_index)),
            }
        )

    answer_option_label = str(option_specs[int(correct_index)]["option_label"])
    correct_option_panel_id = str(option_specs[int(correct_index)]["option_panel_id"])
    return {
        "grid_size": int(grid_size),
        "option_count": int(option_count),
        "fold_mode": str(fold_mode),
        "fold_axes": [str(axis) for axis in fold_axes],
        "folded_hole_cells": _sort_cells(folded_holes),
        "unfolded_hole_cells": _sort_cells(correct_cells),
        "option_specs": option_specs,
        "answer_option_label": str(answer_option_label),
        "correct_option_panel_id": str(correct_option_panel_id),
        "correct_option_index": int(correct_index),
        "question_format": "fold_hole_mcq",
        "view_family": "fold_hole_unfold_mcq",
        "punch_count": int(len(folded_holes)),
    }


__all__ = [
    "PuzzleFoldHoleDefaults",
    "PuzzleFoldHoleRenderParams",
    "SUPPORTED_PUZZLE_FOLD_SCENE_VARIANTS",
    "build_fold_hole_dataset_for_variant",
    "resolve_fold_hole_render_params",
    "resolve_fold_hole_scene_variant",
]
