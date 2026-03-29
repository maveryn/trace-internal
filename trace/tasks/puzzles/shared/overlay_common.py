"""Shared dataset builders and render defaults for transparent-sheet overlay puzzles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default, resolve_required_int_bounds
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.mcq import option_label_for_index
from .common import resolve_puzzle_axis_variant


Cells = Tuple[Tuple[int, int], ...]

SUPPORTED_PUZZLE_OVERLAY_SCENE_VARIANTS: Tuple[str, ...] = (
    "overlay_strip",
    "overlay_card",
    "overlay_outline",
)
SUPPORTED_PUZZLE_OVERLAY_TASK_VARIANTS: Tuple[str, ...] = ("overlay_union_same_grid",)


@dataclass(frozen=True)
class PuzzleOverlayDefaults:
    """Default generation bounds for transparent-sheet overlay puzzles."""

    option_count_min: int = 5
    option_count_max: int = 6
    grid_size_min: int = 4
    grid_size_max: int = 5
    sheet_mark_count_min: int = 2
    sheet_mark_count_max: int = 5
    overlap_count_min: int = 1
    overlap_count_max: int = 2


@dataclass(frozen=True)
class PuzzleOverlayRenderParams:
    """Resolved rendering knobs for transparent-sheet overlay scenes."""

    canvas_width: int
    canvas_height: int
    scene_margin_left_px: int
    scene_margin_right_px: int
    scene_margin_top_px: int
    scene_margin_bottom_px: int
    reference_panel_height_px: int
    reference_panel_padding_px: int
    source_paper_size_px: int
    source_gap_px: int
    reference_to_options_gap_px: int
    option_paper_size_px: int
    option_gap_px: int
    option_row_gap_px: int
    option_label_gap_px: int
    paper_corner_radius_px: int
    panel_corner_radius_px: int
    border_width_px: int
    option_label_font_size_px: int
    combine_symbol_font_size_px: int
    panel_fill_rgb: Tuple[int, int, int]
    paper_fill_rgb: Tuple[int, int, int]
    paper_shadow_rgb: Tuple[int, int, int]
    border_color_rgb: Tuple[int, int, int]
    text_color_rgb: Tuple[int, int, int]
    text_stroke_rgb: Tuple[int, int, int]
    mark_fill_rgb: Tuple[int, int, int]
    mark_outline_rgb: Tuple[int, int, int]
    instruction_fill_rgb: Tuple[int, int, int]


def _resolve_int_param(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
    fallback: int,
) -> int:
    """Resolve one integer generation or rendering parameter."""

    return int(params.get(str(key), group_default(defaults, str(key), int(fallback))))


def _canonicalize_cells(cells: Iterable[Tuple[int, int]]) -> Cells:
    """Return deterministic row-major cells."""

    return tuple(sorted((int(cell_x), int(cell_y)) for cell_x, cell_y in cells))


def resolve_overlay_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the active overlay scene variant."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_PUZZLE_OVERLAY_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def resolve_overlay_task_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic overlay variant."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_PUZZLE_OVERLAY_TASK_VARIANTS,
        task_id=str(task_id),
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        balance_flag_key="balanced_task_variant_sampling",
        axis_namespace="task_variant",
    )


def resolve_overlay_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
) -> PuzzleOverlayRenderParams:
    """Resolve rendering params for transparent-sheet overlay scenes."""

    def _triple(key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        raw = params.get(str(key), group_default(render_defaults, str(key), list(fallback)))
        if not isinstance(raw, Sequence) or len(raw) != 3:
            raise ValueError(f"{key} must be a length-3 RGB sequence")
        return tuple(int(value) for value in raw)

    return PuzzleOverlayRenderParams(
        canvas_width=int(_resolve_int_param(params, render_defaults, "canvas_width", 1200)),
        canvas_height=int(_resolve_int_param(params, render_defaults, "canvas_height", 860)),
        scene_margin_left_px=int(_resolve_int_param(params, render_defaults, "scene_margin_left_px", 64)),
        scene_margin_right_px=int(_resolve_int_param(params, render_defaults, "scene_margin_right_px", 64)),
        scene_margin_top_px=int(_resolve_int_param(params, render_defaults, "scene_margin_top_px", 56)),
        scene_margin_bottom_px=int(_resolve_int_param(params, render_defaults, "scene_margin_bottom_px", 56)),
        reference_panel_height_px=int(_resolve_int_param(params, render_defaults, "reference_panel_height_px", 294)),
        reference_panel_padding_px=int(_resolve_int_param(params, render_defaults, "reference_panel_padding_px", 24)),
        source_paper_size_px=int(_resolve_int_param(params, render_defaults, "source_paper_size_px", 158)),
        source_gap_px=int(_resolve_int_param(params, render_defaults, "source_gap_px", 120)),
        reference_to_options_gap_px=int(_resolve_int_param(params, render_defaults, "reference_to_options_gap_px", 34)),
        option_paper_size_px=int(_resolve_int_param(params, render_defaults, "option_paper_size_px", 158)),
        option_gap_px=int(_resolve_int_param(params, render_defaults, "option_gap_px", 22)),
        option_row_gap_px=int(_resolve_int_param(params, render_defaults, "option_row_gap_px", 22)),
        option_label_gap_px=int(_resolve_int_param(params, render_defaults, "option_label_gap_px", 12)),
        paper_corner_radius_px=int(_resolve_int_param(params, render_defaults, "paper_corner_radius_px", 18)),
        panel_corner_radius_px=int(_resolve_int_param(params, render_defaults, "panel_corner_radius_px", 28)),
        border_width_px=int(_resolve_int_param(params, render_defaults, "border_width_px", 3)),
        option_label_font_size_px=int(_resolve_int_param(params, render_defaults, "option_label_font_size_px", 28)),
        combine_symbol_font_size_px=int(_resolve_int_param(params, render_defaults, "combine_symbol_font_size_px", 46)),
        panel_fill_rgb=_triple("panel_fill_rgb", (248, 249, 252)),
        paper_fill_rgb=_triple("paper_fill_rgb", (255, 252, 245)),
        paper_shadow_rgb=_triple("paper_shadow_rgb", (236, 230, 215)),
        border_color_rgb=_triple("border_color_rgb", (86, 94, 108)),
        text_color_rgb=_triple("text_color_rgb", (30, 34, 40)),
        text_stroke_rgb=_triple("text_stroke_rgb", (255, 255, 255)),
        mark_fill_rgb=_triple("mark_fill_rgb", (53, 96, 164)),
        mark_outline_rgb=_triple("mark_outline_rgb", (36, 48, 66)),
        instruction_fill_rgb=_triple("instruction_fill_rgb", (238, 243, 250)),
    )


def _resolve_choice(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    namespace: str,
    context: str,
) -> Tuple[int, Tuple[int, int]]:
    """Resolve one deterministic integer choice inside the configured support."""

    lower, upper = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
        context=str(context),
    )
    selection = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=str(namespace),
        )
    )
    chosen = int(lower + (selection % (upper - lower + 1)))
    return int(chosen), (int(lower), int(upper))


def _all_grid_cells(grid_size: int) -> Tuple[Tuple[int, int], ...]:
    """Return all cells in one square grid."""

    return tuple((int(cell_x), int(cell_y)) for cell_y in range(int(grid_size)) for cell_x in range(int(grid_size)))


def _mark_specs(cells: Cells, *, prefix: str) -> List[Dict[str, Any]]:
    """Build deterministic mark specs from cells."""

    return [
        {
            "mark_id": f"{str(prefix)}_{int(index)}",
            "cell": [int(cell_x), int(cell_y)],
        }
        for index, (cell_x, cell_y) in enumerate(cells, start=1)
    ]


def _sample_overlay_sources(
    *,
    grid_size: int,
    sheet_mark_count_min: int,
    sheet_mark_count_max: int,
    overlap_count_min: int,
    overlap_count_max: int,
    rng,
) -> Tuple[Cells, Cells, Cells, Cells]:
    """Sample source sheets with one non-trivial union overlap relation."""

    feasible: List[Tuple[int, int, int, int]] = []
    cell_capacity = int(grid_size * grid_size)
    for left_count in range(int(sheet_mark_count_min), int(sheet_mark_count_max) + 1):
        for right_count in range(int(sheet_mark_count_min), int(sheet_mark_count_max) + 1):
            for overlap_count in range(int(overlap_count_min), int(overlap_count_max) + 1):
                if int(overlap_count) >= int(left_count) or int(overlap_count) >= int(right_count):
                    continue
                union_count = int(left_count + right_count - overlap_count)
                if int(union_count) > int(cell_capacity):
                    continue
                feasible.append((int(left_count), int(right_count), int(overlap_count), int(union_count)))
    if not feasible:
        raise RuntimeError("no feasible overlay source configuration")

    left_count, right_count, overlap_count, union_count = feasible[int(rng.randrange(len(feasible)))]
    union_cells = _canonicalize_cells(rng.sample(list(_all_grid_cells(int(grid_size))), int(union_count)))
    overlap_cells = _canonicalize_cells(rng.sample(list(union_cells), int(overlap_count)))
    overlap_set = set(overlap_cells)
    remainder = [cell for cell in union_cells if cell not in overlap_set]
    rng.shuffle(remainder)
    left_only_count = int(left_count - overlap_count)
    left_only_cells = remainder[:left_only_count]
    right_only_cells = remainder[left_only_count:]
    left_cells = _canonicalize_cells(tuple(list(overlap_cells) + list(left_only_cells)))
    right_cells = _canonicalize_cells(tuple(list(overlap_cells) + list(right_only_cells)))
    return left_cells, right_cells, overlap_cells, union_cells


def _option_signature(cells: Iterable[Tuple[int, int]]) -> Cells:
    """Canonicalize one option signature."""

    return _canonicalize_cells(tuple(cells))


def _build_overlay_options(
    *,
    left_cells: Cells,
    right_cells: Cells,
    overlap_cells: Cells,
    union_cells: Cells,
    grid_size: int,
    option_count: int,
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    rng,
) -> Tuple[List[Dict[str, Any]], int, str]:
    """Build the labeled option set with exactly one correct union result."""

    union_signature = _option_signature(union_cells)
    all_cells = set(_all_grid_cells(int(grid_size)))
    distractors: List[Tuple[Cells, str]] = []
    seen = {union_signature}

    def _add(candidate_cells: Iterable[Tuple[int, int]], *, kind: str) -> None:
        signature = _option_signature(candidate_cells)
        if not signature or signature in seen:
            return
        seen.add(signature)
        distractors.append((signature, str(kind)))

    _add(left_cells, kind="left_only")
    _add(right_cells, kind="right_only")
    _add(overlap_cells, kind="overlap_only")

    for removed in union_signature:
        _add((cell for cell in union_signature if cell != removed), kind="missing_one")
        if len(distractors) >= int(option_count - 1):
            break
    if len(distractors) < int(option_count - 1):
        for added in sorted(all_cells - set(union_signature)):
            _add(tuple(list(union_signature) + [added]), kind="extra_one")
            if len(distractors) >= int(option_count - 1):
                break
    if len(distractors) < int(option_count - 1):
        empty_cells = sorted(all_cells - set(union_signature))
        for removed in union_signature:
            for added in empty_cells:
                moved = tuple(cell for cell in union_signature if cell != removed) + (added,)
                _add(moved, kind="moved_one")
                if len(distractors) >= int(option_count - 1):
                    break
            if len(distractors) >= int(option_count - 1):
                break
    if len(distractors) < int(option_count - 1):
        raise RuntimeError("failed to construct enough overlay distractors")

    rng.shuffle(distractors)
    chosen_distractors = distractors[: int(option_count - 1)]
    correct_option_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:correct_option_index",
        )
    ) % int(option_count)
    answer_option_label = str(option_label_for_index(int(correct_option_index)))
    correct_option_choice_id = f"option_choice_{int(correct_option_index + 1)}"

    option_signatures = [cells for cells, _ in chosen_distractors]
    option_kinds = [kind for _, kind in chosen_distractors]
    option_signatures.insert(int(correct_option_index), union_signature)
    option_kinds.insert(int(correct_option_index), "union")

    option_specs: List[Dict[str, Any]] = []
    for option_index, (cells, kind) in enumerate(zip(option_signatures, option_kinds, strict=True)):
        option_choice_id = f"option_choice_{int(option_index + 1)}"
        option_specs.append(
            {
                "option_choice_id": str(option_choice_id),
                "option_label": str(option_label_for_index(int(option_index))),
                "mark_specs": _mark_specs(cells, prefix=f"option_{int(option_index + 1)}"),
                "cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in cells],
                "mark_count": int(len(cells)),
                "candidate_kind": str(kind),
                "is_correct": bool(option_index == int(correct_option_index)),
            }
        )
    return list(option_specs), int(correct_option_index), str(correct_option_choice_id)


def build_overlay_dataset_for_variant(
    *,
    task_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleOverlayDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Construct one deterministic overlay puzzle dataset."""

    if str(task_variant) not in set(SUPPORTED_PUZZLE_OVERLAY_TASK_VARIANTS):
        raise ValueError(f"unsupported overlay variant: {task_variant}")
    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")

    option_count, option_count_range = _resolve_choice(
        params,
        instance_seed=int(instance_seed),
        gen_defaults=gen_defaults,
        min_key="option_count_min",
        max_key="option_count_max",
        fallback_min=int(defaults.option_count_min),
        fallback_max=int(defaults.option_count_max),
        namespace=f"{task_id}:option_count",
        context=f"{task_id} option-count bounds",
    )
    grid_size, grid_size_range = _resolve_choice(
        params,
        instance_seed=int(instance_seed),
        gen_defaults=gen_defaults,
        min_key="grid_size_min",
        max_key="grid_size_max",
        fallback_min=int(defaults.grid_size_min),
        fallback_max=int(defaults.grid_size_max),
        namespace=f"{task_id}:grid_size",
        context=f"{task_id} grid-size bounds",
    )
    sheet_mark_count_min, sheet_mark_count_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="sheet_mark_count_min",
        max_key="sheet_mark_count_max",
        fallback_min=int(defaults.sheet_mark_count_min),
        fallback_max=int(defaults.sheet_mark_count_max),
        context=f"{task_id} sheet-mark-count bounds",
    )
    overlap_count_min, overlap_count_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="overlap_count_min",
        max_key="overlap_count_max",
        fallback_min=int(defaults.overlap_count_min),
        fallback_max=int(defaults.overlap_count_max),
        context=f"{task_id} overlap-count bounds",
    )

    left_cells, right_cells, overlap_cells, union_cells = _sample_overlay_sources(
        grid_size=int(grid_size),
        sheet_mark_count_min=int(sheet_mark_count_min),
        sheet_mark_count_max=int(sheet_mark_count_max),
        overlap_count_min=int(overlap_count_min),
        overlap_count_max=int(overlap_count_max),
        rng=rng,
    )
    option_specs, correct_option_index, correct_option_choice_id = _build_overlay_options(
        left_cells=left_cells,
        right_cells=right_cells,
        overlap_cells=overlap_cells,
        union_cells=union_cells,
        grid_size=int(grid_size),
        option_count=int(option_count),
        params=params,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        rng=rng,
    )
    answer_option_label = str(option_label_for_index(int(correct_option_index)))

    return {
        "task_variant": str(task_variant),
        "question_format": "overlay_union_mcq",
        "view_family": "transparent_sheet_overlay_mcq",
        "grid_size": int(grid_size),
        "grid_size_range": [int(grid_size_range[0]), int(grid_size_range[1])],
        "option_count": int(option_count),
        "option_count_range": [int(option_count_range[0]), int(option_count_range[1])],
        "sheet_mark_count_range": [int(sheet_mark_count_min), int(sheet_mark_count_max)],
        "overlap_count_range": [int(overlap_count_min), int(overlap_count_max)],
        "left_cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in left_cells],
        "right_cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in right_cells],
        "overlap_cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in overlap_cells],
        "union_cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in union_cells],
        "left_mark_specs": _mark_specs(left_cells, prefix="left_sheet"),
        "right_mark_specs": _mark_specs(right_cells, prefix="right_sheet"),
        "left_mark_count": int(len(left_cells)),
        "right_mark_count": int(len(right_cells)),
        "overlap_count": int(len(overlap_cells)),
        "union_mark_count": int(len(union_cells)),
        "option_specs": list(option_specs),
        "answer_option_label": str(answer_option_label),
        "correct_option_index": int(correct_option_index),
        "correct_option_choice_id": str(correct_option_choice_id),
        "valid_option_choice_ids": [str(correct_option_choice_id)],
        "solver_trace": {
            "task_variant": str(task_variant),
            "grid_size": int(grid_size),
            "left_cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in left_cells],
            "right_cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in right_cells],
            "overlap_cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in overlap_cells],
            "union_cells": [[int(cell_x), int(cell_y)] for cell_x, cell_y in union_cells],
            "correct_option_index": int(correct_option_index),
            "correct_option_label": str(answer_option_label),
            "correct_option_choice_id": str(correct_option_choice_id),
            "option_signatures": {
                str(spec["option_choice_id"]): [[int(cell_x), int(cell_y)] for cell_x, cell_y in _option_signature(tuple((int(cell[0]), int(cell[1])) for cell in spec["cells"]))]
                for spec in option_specs
            },
        },
    }


__all__ = [
    "PuzzleOverlayDefaults",
    "PuzzleOverlayRenderParams",
    "SUPPORTED_PUZZLE_OVERLAY_SCENE_VARIANTS",
    "SUPPORTED_PUZZLE_OVERLAY_TASK_VARIANTS",
    "build_overlay_dataset_for_variant",
    "resolve_overlay_render_params",
    "resolve_overlay_scene_variant",
    "resolve_overlay_task_variant",
]
