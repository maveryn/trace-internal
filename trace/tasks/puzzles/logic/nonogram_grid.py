"""Nonogram puzzle tasks over clue rails, marked lines, and candidate grids."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.mcq import option_label_for_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.common import (
    get_int_param as _get_int,
    get_int_range as _get_range,
    load_puzzle_task_defaults,
    projected_puzzle_bbox_evidence,
    resolve_puzzle_axis_variant,
)
from ..shared.complexity import build_puzzle_complexity, normalize_int_with_bounds
from ..shared.nonogram_scene import (
    NonogramRenderParams,
    SUPPORTED_NONOGRAM_SCENE_VARIANTS,
    all_binary_lines,
    clue_for_line,
    col_clues_for_grid,
    grid_signature,
    line_matches_partial,
    render_nonogram_scene,
    row_clues_for_grid,
)
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.unit_size_jitter import resolve_puzzle_unit_size_scale, scale_puzzle_px, with_puzzle_unit_size_jitter
from ..shared.visual_defaults import load_puzzle_noise_defaults


SCENE_ID = "nonogram"
LINE_COMPLETION_TASK_ID = "task_puzzles__nonogram__nonogram_line_completion_label"
CANDIDATE_SOLUTION_TASK_ID = "task_puzzles__nonogram__nonogram_candidate_solution_label"

_SCENE_LOAD_BY_VARIANT = {
    "nonogram_classic": 0.18,
    "nonogram_card": 0.24,
    "nonogram_blueprint": 0.22,
}
_REASONING_LOAD_BY_QUERY = {
    "line_completion_label": 0.58,
    "candidate_solution_label": 0.68,
}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "logic")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="logic", apply_prob=0.15)


def _load_defaults(task_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    return load_puzzle_task_defaults(_TASK_GROUP_DEFAULTS, task_id=str(task_id))


def _resolve_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_NONOGRAM_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _resolve_grid_size(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    rng,
) -> Tuple[int, int, Tuple[int, int], Tuple[int, int]]:
    row_range = _get_range(
        params,
        gen_defaults,
        min_key="grid_rows_min",
        max_key="grid_rows_max",
        fallback_min=6,
        fallback_max=9,
    )
    col_range = _get_range(
        params,
        gen_defaults,
        min_key="grid_cols_min",
        max_key="grid_cols_max",
        fallback_min=6,
        fallback_max=9,
    )
    rows = int(params.get("grid_rows", rng.randint(int(row_range[0]), int(row_range[1]))))
    cols = int(params.get("grid_cols", rng.randint(int(col_range[0]), int(col_range[1]))))
    if not int(row_range[0]) <= int(rows) <= int(row_range[1]):
        raise ValueError("grid_rows falls outside configured range")
    if not int(col_range[0]) <= int(cols) <= int(col_range[1]):
        raise ValueError("grid_cols falls outside configured range")
    return int(rows), int(cols), tuple(row_range), tuple(col_range)


def _resolve_option_count(params: Mapping[str, Any], *, gen_defaults: Mapping[str, Any], rng) -> int:
    if "option_count" in params:
        return max(2, int(params["option_count"]))
    low, high = _get_range(
        params,
        gen_defaults,
        min_key="option_count_min",
        max_key="option_count_max",
        fallback_min=4,
        fallback_max=6,
    )
    return int(rng.randint(int(low), int(high)))


def _resolve_option_count_max(params: Mapping[str, Any], *, gen_defaults: Mapping[str, Any]) -> int:
    if "option_count" in params:
        return max(2, int(params["option_count"]))
    _low, high = _get_range(
        params,
        gen_defaults,
        min_key="option_count_min",
        max_key="option_count_max",
        fallback_min=4,
        fallback_max=6,
    )
    return max(2, int(high))


def _resolve_render_params(
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    *,
    instance_seed: int,
) -> NonogramRenderParams:
    unit_scale, unit_meta = resolve_puzzle_unit_size_scale(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace="puzzles.nonogram.unit_size",
    )
    return NonogramRenderParams(
        canvas_width=int(render_defaults.get("canvas_width", 1200)),
        canvas_height=int(render_defaults.get("canvas_height", 900)),
        margin_top_px=int(render_defaults.get("margin_top_px", 54)),
        left_clue_width_px=int(render_defaults.get("left_clue_width_px", 172)),
        top_clue_height_px=int(render_defaults.get("top_clue_height_px", 116)),
        cell_size_px=scale_puzzle_px(render_defaults.get("cell_size_px", 48), unit_scale, min_px=18),
        grid_line_width_px=scale_puzzle_px(render_defaults.get("grid_line_width_px", 2), unit_scale, min_px=1),
        heavy_line_width_px=scale_puzzle_px(render_defaults.get("heavy_line_width_px", 4), unit_scale, min_px=2),
        option_panel_width_px=scale_puzzle_px(render_defaults.get("option_panel_width_px", 160), unit_scale, min_px=92),
        option_panel_height_px=scale_puzzle_px(render_defaults.get("option_panel_height_px", 132), unit_scale, min_px=82),
        option_gap_px=scale_puzzle_px(render_defaults.get("option_gap_px", 14), unit_scale, min_px=7),
        option_y_px=int(render_defaults.get("option_y_px", 650)),
        panel_corner_radius_px=scale_puzzle_px(render_defaults.get("panel_corner_radius_px", 14), unit_scale, min_px=6),
        clue_font_size_px=scale_puzzle_px(render_defaults.get("clue_font_size_px", 22), unit_scale, min_px=12),
        option_label_font_size_px=scale_puzzle_px(render_defaults.get("option_label_font_size_px", 24), unit_scale, min_px=12),
        question_font_size_px=int(render_defaults.get("question_font_size_px", 28)),
        unit_size_jitter=dict(unit_meta),
    )


def _sample_solution_grid(rows: int, cols: int, *, rng) -> List[List[int]]:
    """Sample a compact random nonogram solution with readable clue rails."""

    for _attempt in range(300):
        density = rng.uniform(0.34, 0.56)
        grid = [[1 if rng.random() < float(density) else 0 for _col in range(int(cols))] for _row in range(int(rows))]
        filled = sum(sum(row) for row in grid)
        total = int(rows) * int(cols)
        if filled < int(0.22 * total) or filled > int(0.72 * total):
            continue
        row_clues = row_clues_for_grid(grid)
        col_clues = col_clues_for_grid(grid)
        if max(len(clue) for clue in row_clues + col_clues) > 4:
            continue
        if sum(1 for clue in row_clues + col_clues if clue != [0]) < int(rows + cols - 2):
            continue
        return grid
    raise RuntimeError("failed to sample readable nonogram grid")


def _select_marked_row(
    grid: Sequence[Sequence[int]],
    *,
    rng,
) -> int:
    row_clues = row_clues_for_grid(grid)
    candidates = [
        int(index)
        for index, clue in enumerate(row_clues)
        if clue != [0] and len(clue) <= 3 and 0 in [int(value) for value in grid[index]]
    ]
    if not candidates:
        candidates = [int(index) for index, clue in enumerate(row_clues) if clue != [0]]
    if not candidates:
        raise RuntimeError("nonogram grid has no usable marked row")
    return int(candidates[int(rng.randrange(len(candidates)))])


def _partial_line_for_completion(line: Sequence[int], *, rng) -> List[int | None]:
    length = len(line)
    filled_indices = [index for index, value in enumerate(line) if int(value) == 1]
    empty_indices = [index for index, value in enumerate(line) if int(value) == 0]
    partial: List[int | None] = [None for _ in range(int(length))]
    required: List[int] = []
    if filled_indices:
        required.append(int(filled_indices[int(rng.randrange(len(filled_indices)))]))
    if empty_indices:
        required.append(int(empty_indices[int(rng.randrange(len(empty_indices)))]))
    reveal_target = min(int(length) - 1, max(2, int(rng.randint(2, min(5, int(length))))))
    available = [index for index in range(int(length)) if index not in required]
    rng.shuffle(available)
    reveal_indices = list(dict.fromkeys(required + available[: max(0, int(reveal_target) - len(required))]))
    for index in reveal_indices:
        partial[int(index)] = int(line[int(index)])
    return partial


def _build_line_option_specs(
    *,
    line: Sequence[int],
    clue: Sequence[int],
    partial_line: Sequence[int | None],
    option_count: int,
    correct_index: int,
    rng,
) -> List[Dict[str, Any]]:
    all_lines = all_binary_lines(len(line))
    correct = tuple(int(value) for value in line)
    valid_conflict = [
        candidate
        for candidate in all_lines
        if candidate != correct and clue_for_line(candidate) == list(clue) and not line_matches_partial(candidate, partial_line)
    ]
    partial_invalid = [
        candidate
        for candidate in all_lines
        if candidate != correct and clue_for_line(candidate) != list(clue) and line_matches_partial(candidate, partial_line)
    ]
    close_invalid = [
        candidate
        for candidate in all_lines
        if candidate != correct
        and clue_for_line(candidate) != list(clue)
        and not line_matches_partial(candidate, partial_line)
        and sum(int(a) != int(b) for a, b in zip(candidate, correct)) <= 3
    ]
    random_invalid = [candidate for candidate in all_lines if candidate != correct and candidate not in close_invalid]

    distractors: List[Tuple[int, ...]] = []
    seen = {correct}
    for pool in (valid_conflict, partial_invalid, close_invalid, random_invalid):
        shuffled = list(pool)
        rng.shuffle(shuffled)
        for candidate in shuffled:
            if candidate in seen:
                continue
            seen.add(candidate)
            distractors.append(candidate)
            if len(distractors) >= int(option_count) - 1:
                break
        if len(distractors) >= int(option_count) - 1:
            break
    if len(distractors) < int(option_count) - 1:
        raise RuntimeError("failed to build enough nonogram line distractors")

    options = [tuple(candidate) for candidate in distractors[: int(option_count) - 1]]
    options.insert(int(correct_index), correct)
    option_specs: List[Dict[str, Any]] = []
    for option_index, option_line in enumerate(options):
        label = option_label_for_index(int(option_index))
        option_specs.append(
            {
                "option_panel_id": f"option_{label}",
                "option_index": int(option_index),
                "option_label": str(label),
                "line": [int(value) for value in option_line],
                "is_correct": bool(option_index == int(correct_index)),
            }
        )
    return option_specs


def _mutate_grid(grid: Sequence[Sequence[int]], *, rng) -> List[List[int]]:
    mutated = [[int(value) for value in row] for row in grid]
    rows = len(mutated)
    cols = len(mutated[0]) if rows else 0
    op = rng.choice(["flip", "flip_two", "swap_rows", "swap_cols", "shift_row"])
    if op == "swap_rows" and rows >= 2:
        a, b = rng.sample(range(rows), 2)
        mutated[a], mutated[b] = mutated[b], mutated[a]
    elif op == "swap_cols" and cols >= 2:
        a, b = rng.sample(range(cols), 2)
        for row in mutated:
            row[a], row[b] = row[b], row[a]
    elif op == "shift_row" and cols >= 2:
        row_index = int(rng.randrange(rows))
        shift = int(rng.choice([-1, 1]))
        row = list(mutated[row_index])
        mutated[row_index] = row[-shift:] + row[:-shift]
    else:
        flip_count = 2 if op == "flip_two" else 1
        for _ in range(int(flip_count)):
            row_index = int(rng.randrange(rows))
            col_index = int(rng.randrange(cols))
            mutated[row_index][col_index] = 1 - int(mutated[row_index][col_index])
    return mutated


def _build_candidate_option_specs(
    *,
    grid: Sequence[Sequence[int]],
    option_count: int,
    correct_index: int,
    rng,
) -> List[Dict[str, Any]]:
    correct = [[int(value) for value in row] for row in grid]
    target_row_clues = row_clues_for_grid(correct)
    target_col_clues = col_clues_for_grid(correct)
    seen = {grid_signature(correct)}
    distractors: List[List[List[int]]] = []
    for _attempt in range(800):
        candidate = _mutate_grid(correct, rng=rng)
        signature = grid_signature(candidate)
        if signature in seen:
            continue
        seen.add(signature)
        if row_clues_for_grid(candidate) == target_row_clues and col_clues_for_grid(candidate) == target_col_clues:
            continue
        distractors.append(candidate)
        if len(distractors) >= int(option_count) - 1:
            break
    if len(distractors) < int(option_count) - 1:
        raise RuntimeError("failed to build enough nonogram candidate distractors")

    options = [deepcopy(candidate) for candidate in distractors[: int(option_count) - 1]]
    options.insert(int(correct_index), deepcopy(correct))
    option_specs: List[Dict[str, Any]] = []
    for option_index, option_grid in enumerate(options):
        label = option_label_for_index(int(option_index))
        option_specs.append(
            {
                "option_panel_id": f"option_{label}",
                "option_index": int(option_index),
                "option_label": str(label),
                "grid": [[int(value) for value in row] for row in option_grid],
                "is_correct": bool(option_index == int(correct_index)),
            }
        )
    return option_specs


def _build_prompt(
    *,
    task_id: str,
    query_id: str,
    scene_variant: str,
    prompt_defaults: Mapping[str, Any],
    instance_seed: int,
    line_label: str = "",
) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    required_keys = (
        "bundle_id",
        "scene_key",
        "task_key",
        "json_output_contract",
        "json_output_contract_answer_only",
        f"object_description_{scene_variant}",
        f"answer_hint_{query_id}",
        f"evidence_hint_{query_id}",
        f"json_example_{query_id}",
        f"json_example_answer_only_{query_id}",
    )
    prompt_values = required_group_defaults(
        prompt_defaults,
        required_keys,
        context=f"prompt defaults for {task_id}",
    )
    slots = {
        "object_description": str(prompt_values[f"object_description_{scene_variant}"]),
        "line_label": str(line_label),
        "json_output_contract": str(prompt_values["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_values["json_output_contract_answer_only"]),
        "evidence_hint": str(prompt_values[f"evidence_hint_{query_id}"]),
        "answer_hint": str(prompt_values[f"answer_hint_{query_id}"]),
        "json_example": str(prompt_values[f"json_example_{query_id}"]),
        "json_example_answer_only": str(prompt_values[f"json_example_answer_only_{query_id}"]),
    }
    prompt_selection = render_task_prompt_variants(
        domain="puzzles",
        task_group="logic",
        bundle_id=str(prompt_values["bundle_id"]),
        scene_key=str(prompt_values["scene_key"]),
        task_key=str(prompt_values["task_key"]),
        query_key=str(query_id),
        answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
        slots=slots,
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    return str(prompt_artifacts.prompt), dict(prompt_artifacts.prompt_variants), {
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants_for_trace": dict(prompt_artifacts.prompt_variants_for_trace),
        "bundle_id": str(prompt_values["bundle_id"]),
    }


class _PuzzlesLogicNonogramBaseTask:
    """Base implementation for one fixed public nonogram task."""

    domain = "puzzles"
    task_group = "logic"
    default_dataset_enabled = True
    query_id: str

    def _build_dataset(
        self,
        *,
        params: Mapping[str, Any],
        instance_seed: int,
        gen_defaults: Mapping[str, Any],
    ) -> Dict[str, Any]:
        rng = spawn_rng(int(instance_seed), f"{self.task_id}.dataset")
        rows, cols, row_range, col_range = _resolve_grid_size(params, gen_defaults=gen_defaults, rng=rng)
        option_count = _resolve_option_count(params, gen_defaults=gen_defaults, rng=rng)
        grid = _sample_solution_grid(int(rows), int(cols), rng=rng)
        row_clues = row_clues_for_grid(grid)
        col_clues = col_clues_for_grid(grid)

        correct_option_index = int(
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{self.task_id}.correct_option_index",
            )
            % max(1, _resolve_option_count_max(params, gen_defaults=gen_defaults))
        )
        option_count = max(int(option_count), int(correct_option_index) + 1)
        if str(self.query_id) == "line_completion_label":
            marked_row = _select_marked_row(grid, rng=rng)
            line = [int(value) for value in grid[int(marked_row)]]
            clue = clue_for_line(line)
            partial_line = _partial_line_for_completion(line, rng=rng)
            display_grid: List[List[int | None]] = [
                [None for _col in range(int(cols))]
                for _row in range(int(rows))
            ]
            for col_index, value in enumerate(partial_line):
                display_grid[int(marked_row)][int(col_index)] = value
            option_specs = _build_line_option_specs(
                line=line,
                clue=clue,
                partial_line=partial_line,
                option_count=int(option_count),
                correct_index=int(correct_option_index),
                rng=rng,
            )
            answer_value = str(option_label_for_index(int(correct_option_index)))
            return {
                "mode": "line_completion",
                "grid": grid,
                "display_grid": display_grid,
                "row_clues": row_clues,
                "col_clues": col_clues,
                "marked_axis": "row",
                "marked_index": int(marked_row),
                "marked_clue": list(clue),
                "line": list(line),
                "partial_line": [None if value is None else int(value) for value in partial_line],
                "answer_value": str(answer_value),
                "answer_type": "option_letter",
                "supporting_item_ids": [
                    f"row_clue_{int(marked_row)}",
                    "marked_line",
                    f"option_{answer_value}",
                ],
                "option_count": int(option_count),
                "option_specs": option_specs,
                "correct_option_panel_id": f"option_{answer_value}",
                "correct_option_index": int(correct_option_index),
                "grid_rows_range": list(row_range),
                "grid_cols_range": list(col_range),
            }

        option_specs = _build_candidate_option_specs(
            grid=grid,
            option_count=int(option_count),
            correct_index=int(correct_option_index),
            rng=rng,
        )
        answer_value = str(option_label_for_index(int(correct_option_index)))
        return {
            "mode": "candidate_solution",
            "grid": grid,
            "display_grid": [[None for _col in range(int(cols))] for _row in range(int(rows))],
            "row_clues": row_clues,
            "col_clues": col_clues,
            "answer_value": str(answer_value),
            "answer_type": "option_letter",
            "supporting_item_ids": [
                "row_clue_panel",
                "col_clue_panel",
                f"option_{answer_value}",
            ],
            "option_count": int(option_count),
            "option_specs": option_specs,
            "correct_option_panel_id": f"option_{answer_value}",
            "correct_option_index": int(correct_option_index),
            "grid_rows_range": list(row_range),
            "grid_cols_range": list(col_range),
        }

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id = str(self.query_id)
        gen_defaults, render_defaults, prompt_defaults, complexity_weights = _load_defaults(str(self.task_id))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
        )
        dataset = self._build_dataset(
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=gen_defaults,
        )
        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed))
        scene_style, scene_style_meta = resolve_puzzle_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.nonogram_background",
        )
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered_scene = render_nonogram_scene(
            background,
            scene_variant=str(scene_variant),
            mode=str(dataset["mode"]),
            display_grid=list(dataset["display_grid"]),
            row_clues=list(dataset["row_clues"]),
            col_clues=list(dataset["col_clues"]),
            render_params=render_params,
            marked_axis=dataset.get("marked_axis"),
            marked_index=dataset.get("marked_index"),
            option_specs=list(dataset["option_specs"]),
            show_empty_marks=bool(query_id == "line_completion_label"),
            scene_style=scene_style,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        if query_id == "line_completion_label":
            line_label = f"row {int(dataset['marked_index']) + 1}"
        else:
            line_label = ""
        prompt, prompt_variants, prompt_meta = _build_prompt(
            task_id=str(self.task_id),
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            prompt_defaults=prompt_defaults,
            instance_seed=int(instance_seed),
            line_label=str(line_label),
        )

        evidence_projection = projected_puzzle_bbox_evidence(
            rendered_scene.item_bbox_map,
            [str(item_id) for item_id in dataset["supporting_item_ids"]],
        )
        evidence_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in evidence_projection["bbox_set"]
        ]
        answer_value = str(dataset["answer_value"])
        answer_gt = TypedValue(type=str(dataset["answer_type"]), value=str(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        rows = int(len(dataset["grid"]))
        cols = int(len(dataset["grid"][0]))
        grid_area_range = [
            int(dataset["grid_rows_range"][0]) * int(dataset["grid_cols_range"][0]),
            int(dataset["grid_rows_range"][1]) * int(dataset["grid_cols_range"][1]),
        ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": "nonogram",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_id": SCENE_ID,
                    "scene_variant": str(scene_variant),
                    "answer_value": str(answer_value),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_meta["bundle_id"]),
                "prompt_variant": dict(prompt_meta["prompt_variant"]),
                "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
                "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
                "params": {
                    "query_id": "default",
                    "query_id_probabilities": {"default": 1.0},
                    "query_id": str(query_id),
                    "query_id_probabilities": {str(query_id): 1.0},
                    "scene_id": SCENE_ID,
                    "scene_variant": str(scene_variant),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "grid_rows": int(rows),
                    "grid_cols": int(cols),
                    "grid_rows_range": list(dataset["grid_rows_range"]),
                    "grid_cols_range": list(dataset["grid_cols_range"]),
                    "option_count": int(dataset["option_count"]),
                },
            },
            "render_spec": {
                "scene_id": SCENE_ID,
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "scene_style": dict(scene_style_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "text_style": {
                    "clue_font_size_px": int(render_params.clue_font_size_px),
                    "option_label_font_size_px": int(render_params.option_label_font_size_px),
                },
                "unit_size_jitter": dict(render_params.unit_size_jitter or {}),
            },
            "render_map": with_puzzle_unit_size_jitter({
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "cell_bboxes_px": {str(key): list(value) for key, value in rendered_scene.cell_bbox_map.items()},
                "clue_bboxes_px": {str(key): list(value) for key, value in rendered_scene.clue_bbox_map.items()},
                "option_panel_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.option_panel_bbox_map.items()
                },
                "item_bboxes_px": {str(key): list(value) for key, value in rendered_scene.item_bbox_map.items()},
                "evidence_source": "item_bboxes_px",
            }, render_params.unit_size_jitter or {}),
            "execution_trace": {
                "query_id": "default",
                "query_id_probabilities": {"default": 1.0},
                "query_id": str(query_id),
                "query_id_probabilities": {str(query_id): 1.0},
                "scene_id": SCENE_ID,
                "scene_variant": str(scene_variant),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "grid_rows": int(rows),
                "grid_cols": int(cols),
                "grid_rows_range": list(dataset["grid_rows_range"]),
                "grid_cols_range": list(dataset["grid_cols_range"]),
                "grid": [[int(value) for value in row] for row in dataset["grid"]],
                "display_grid": [
                    [None if value is None else int(value) for value in row]
                    for row in dataset["display_grid"]
                ],
                "row_clues": [[int(value) for value in clue] for clue in dataset["row_clues"]],
                "col_clues": [[int(value) for value in clue] for clue in dataset["col_clues"]],
                "answer_value": str(answer_value),
                "supporting_item_ids": [str(item_id) for item_id in dataset["supporting_item_ids"]],
                "option_count": int(dataset["option_count"]),
                "option_specs": [dict(option) for option in dataset["option_specs"]],
                "question_format": str(query_id),
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
            },
        }
        if query_id == "line_completion_label":
            trace_payload["query_spec"]["params"].update(
                {
                    "marked_axis": "row",
                    "marked_index": int(dataset["marked_index"]),
                    "marked_clue": [int(value) for value in dataset["marked_clue"]],
                }
            )
            trace_payload["execution_trace"].update(
                {
                    "marked_axis": "row",
                    "marked_index": int(dataset["marked_index"]),
                    "marked_clue": [int(value) for value in dataset["marked_clue"]],
                    "line": [int(value) for value in dataset["line"]],
                    "partial_line": [None if value is None else int(value) for value in dataset["partial_line"]],
                    "correct_option_index": int(dataset["correct_option_index"]),
                    "correct_option_panel_id": str(dataset["correct_option_panel_id"]),
                }
            )
        if query_id == "candidate_solution_label":
            trace_payload["execution_trace"].update(
                {
                    "correct_option_index": int(dataset["correct_option_index"]),
                    "correct_option_panel_id": str(dataset["correct_option_panel_id"]),
                }
            )

        visual_scan = normalize_int_with_bounds(int(rows * cols), grid_area_range)
        complexity = build_puzzle_complexity(
            weights=complexity_weights,
            components={
                "visual_scan": float(visual_scan),
                "reasoning_load": float(_REASONING_LOAD_BY_QUERY[str(query_id)]),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_variants),
        )


@register_task
class PuzzlesLogicNonogramLineCompletionLabelTask(_PuzzlesLogicNonogramBaseTask):
    """Choose the option strip that completes the marked nonogram row."""

    task_id = LINE_COMPLETION_TASK_ID
    query_id = "line_completion_label"


@register_task
class PuzzlesLogicNonogramCandidateSolutionLabelTask(_PuzzlesLogicNonogramBaseTask):
    """Choose the candidate filled grid that satisfies the visible nonogram clues."""

    task_id = CANDIDATE_SOLUTION_TASK_ID
    query_id = "candidate_solution_label"


__all__ = [
    "PuzzlesLogicNonogramCandidateSolutionLabelTask",
    "PuzzlesLogicNonogramLineCompletionLabelTask",
]
