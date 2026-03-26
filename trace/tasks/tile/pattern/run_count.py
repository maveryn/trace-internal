"""Single-board rectangular-tile match-3 line-count task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import pixel_anchor_map_from_bboxes
from ...shared.color_format import format_named_color_with_hex, rgb_to_hex
from ...shared.config_defaults import (
    group_default,
    required_group_default,
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.grid_graph import cell_id
from ..shared.named_color_board import (
    Coord,
    RectangularNamedColorBoardTaskDefaults,
    build_color_board_scene_entities,
    build_palette_trace,
    build_rectangular_named_color_board_render_spec,
    build_rectangular_named_color_board_scene,
)
from ..shared.tile_colors import NamedColor, sample_named_tile_palette
from ..shared.tile_evidence import coordinate_set_evidence_artifacts
from .background_defaults import POST_IMAGE_BACKGROUND_DEFAULTS
from .noise_defaults import POST_IMAGE_NOISE_DEFAULTS


_VARIANT_ORDER = ("rows", "cols")


@dataclass(frozen=True)
class _TaskDefaults(RectangularNamedColorBoardTaskDefaults):
    """Stable defaults for the tile run-count task."""

    palette_size_min: int = 2
    palette_size_max: int = 3
    run_length: int = 3
    target_qualifying_line_count_min: int = 1


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("tile", "pattern")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, dict) else {},
    task_id="task_tile_pattern_match3_run_count",
)


def _resolve_task_variant(*, params: Mapping[str, Any], instance_seed: int, task_id: str) -> str:
    """Resolve rows-vs-cols variant deterministically."""
    explicit_variant = params.get("task_variant")
    if explicit_variant is not None:
        variant = str(explicit_variant).strip().lower()
        if variant not in set(_VARIANT_ORDER):
            raise ValueError(f"unsupported task_variant for {task_id}: {explicit_variant}")
        return str(variant)
    variant_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:task_variant",
    )
    return str(_VARIANT_ORDER[int(variant_index) % len(_VARIANT_ORDER)])


def _line_capacity(task_variant: str, *, rows: int, cols: int) -> int:
    """Return the number of countable lines for the selected variant."""
    if str(task_variant) == "rows":
        return int(rows)
    if str(task_variant) == "cols":
        return int(cols)
    raise ValueError(f"unsupported task_variant: {task_variant}")


def _orthogonal_length(task_variant: str, *, rows: int, cols: int) -> int:
    """Return the line length along which runs are detected."""
    if str(task_variant) == "rows":
        return int(cols)
    if str(task_variant) == "cols":
        return int(rows)
    raise ValueError(f"unsupported task_variant: {task_variant}")


def _eligible_board_shapes(
    *,
    rows_min: int,
    rows_max: int,
    cols_min: int,
    cols_max: int,
    task_variant: str,
    run_length: int,
    target_qualifying_line_count: int,
) -> List[Tuple[int, int]]:
    """Return board shapes that can support the requested target line count."""
    eligible: List[Tuple[int, int]] = []
    for rows in range(int(rows_min), int(rows_max) + 1):
        for cols in range(int(cols_min), int(cols_max) + 1):
            if _line_capacity(str(task_variant), rows=int(rows), cols=int(cols)) < int(target_qualifying_line_count):
                continue
            if _orthogonal_length(str(task_variant), rows=int(rows), cols=int(cols)) < int(run_length):
                continue
            if (int(rows) * int(cols)) <= int(target_qualifying_line_count) * int(run_length):
                continue
            eligible.append((int(rows), int(cols)))
    return eligible


def _line_has_query_run(line: Sequence[str], query_color_name: str, run_length: int) -> bool:
    """Return whether one line contains a query-color run of at least `run_length`."""
    line_length = int(len(line))
    if int(run_length) <= 0 or int(line_length) < int(run_length):
        return False
    for start in range(0, int(line_length) - int(run_length) + 1):
        if all(str(line[start + offset]) == str(query_color_name) for offset in range(int(run_length))):
            return True
    return False


def _sample_line_with_query_run(
    rng,
    *,
    line_length: int,
    palette_names: Sequence[str],
    query_color_name: str,
    run_length: int,
) -> List[str]:
    """Construct one line that is guaranteed to contain a qualifying query-color run."""
    non_query_names = [str(name) for name in palette_names if str(name) != str(query_color_name)]
    if not non_query_names:
        raise ValueError("run-count task requires at least one non-query color")
    line = [str(rng.choice(non_query_names)) for _ in range(int(line_length))]
    start = int(rng.randint(0, int(line_length) - int(run_length)))
    for offset in range(int(run_length)):
        line[int(start) + int(offset)] = str(query_color_name)
    return line


def _sample_line_without_query_run(
    rng,
    *,
    line_length: int,
    palette_names: Sequence[str],
    query_color_name: str,
    run_length: int,
    max_attempts: int = 64,
) -> List[str]:
    """Construct one line that avoids any qualifying query-color run."""
    for _ in range(int(max_attempts)):
        line = [str(rng.choice(palette_names)) for _ in range(int(line_length))]
        if not _line_has_query_run(line, str(query_color_name), int(run_length)):
            return line
    non_query_names = [str(name) for name in palette_names if str(name) != str(query_color_name)]
    if non_query_names:
        return [str(rng.choice(non_query_names)) for _ in range(int(line_length))]
    return [str(query_color_name) for _ in range(int(line_length))]


def _row_run_examples(
    color_grid: Sequence[Sequence[str]],
    *,
    query_color_name: str,
    run_length: int,
) -> List[List[Coord]]:
    """Return one canonical witness run per qualifying row."""
    rows = int(len(color_grid))
    cols = int(len(color_grid[0])) if rows else 0
    examples: List[List[Coord]] = []
    for row in range(int(rows)):
        hit: List[Coord] | None = None
        for col in range(0, max(0, int(cols) - int(run_length) + 1)):
            if all(str(color_grid[row][col + offset]) == str(query_color_name) for offset in range(int(run_length))):
                hit = [(int(row), int(col + offset)) for offset in range(int(run_length))]
                break
        if hit is not None:
            examples.append(list(hit))
    return examples


def _col_run_examples(
    color_grid: Sequence[Sequence[str]],
    *,
    query_color_name: str,
    run_length: int,
) -> List[List[Coord]]:
    """Return one canonical witness run per qualifying column."""
    rows = int(len(color_grid))
    cols = int(len(color_grid[0])) if rows else 0
    examples: List[List[Coord]] = []
    for col in range(int(cols)):
        hit: List[Coord] | None = None
        for row in range(0, max(0, int(rows) - int(run_length) + 1)):
            if all(str(color_grid[row + offset][col]) == str(query_color_name) for offset in range(int(run_length))):
                hit = [(int(row + offset), int(col)) for offset in range(int(run_length))]
                break
        if hit is not None:
            examples.append(list(hit))
    return examples


def _build_color_grid_with_exact_target(
    rng,
    *,
    rows: int,
    cols: int,
    task_variant: str,
    palette_names: Sequence[str],
    query_color_name: str,
    run_length: int,
    target_qualifying_line_count: int,
) -> List[List[str]]:
    """Construct one board with exactly the requested number of qualifying lines."""
    if str(task_variant) == "rows":
        target_line_indices = set(rng.sample(range(int(rows)), k=int(target_qualifying_line_count)))
        return [
            _sample_line_with_query_run(
                rng,
                line_length=int(cols),
                palette_names=palette_names,
                query_color_name=str(query_color_name),
                run_length=int(run_length),
            )
            if int(row) in target_line_indices
            else _sample_line_without_query_run(
                rng,
                line_length=int(cols),
                palette_names=palette_names,
                query_color_name=str(query_color_name),
                run_length=int(run_length),
            )
            for row in range(int(rows))
        ]

    if str(task_variant) == "cols":
        target_line_indices = set(rng.sample(range(int(cols)), k=int(target_qualifying_line_count)))
        columns = [
            _sample_line_with_query_run(
                rng,
                line_length=int(rows),
                palette_names=palette_names,
                query_color_name=str(query_color_name),
                run_length=int(run_length),
            )
            if int(col) in target_line_indices
            else _sample_line_without_query_run(
                rng,
                line_length=int(rows),
                palette_names=palette_names,
                query_color_name=str(query_color_name),
                run_length=int(run_length),
            )
            for col in range(int(cols))
        ]
        return [
            [str(columns[col][row]) for col in range(int(cols))]
            for row in range(int(rows))
        ]

    raise ValueError(f"unsupported task_variant: {task_variant}")


def _build_board_colors(color_grid: Sequence[Sequence[str]], palette: Sequence[NamedColor]) -> Dict[Coord, NamedColor]:
    """Map grid color names to canonical named-color tuples."""
    rgb_by_name = {
        str(name): (str(name), (int(rgb[0]), int(rgb[1]), int(rgb[2])))
        for name, rgb in palette
    }
    return {
        (int(row), int(col)): rgb_by_name[str(color_grid[row][col])]
        for row in range(int(len(color_grid)))
        for col in range(int(len(color_grid[row])))
    }


@register_task
class TileMatch3RunCountTask:
    """Count rows or columns containing at least one query-color run of length three."""

    task_id = "task_tile_pattern_match3_run_count"
    domain = "tile"
    task_group = "pattern"

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
        palette_size_min, palette_size_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="palette_size_min",
            max_key="palette_size_max",
            fallback_min=int(_DEFAULTS.palette_size_min),
            fallback_max=int(_DEFAULTS.palette_size_max),
            context=f"generation defaults for {self.task_id}",
        )
        run_length = int(
            params.get(
                "run_length",
                group_default(_GEN_DEFAULTS, "run_length", int(_DEFAULTS.run_length)),
            )
        )
        if int(run_length) < 2:
            raise ValueError("run_length must be >= 2")
        target_qualifying_line_count_min = int(
            params.get(
                "target_qualifying_line_count_min",
                group_default(
                    _GEN_DEFAULTS,
                    "target_qualifying_line_count_min",
                    int(_DEFAULTS.target_qualifying_line_count_min),
                ),
            )
        )

        task_variant = _resolve_task_variant(
            params=params,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
        )
        default_target_qualifying_line_count_max = (
            int(rows_max) if str(task_variant) == "rows" else int(cols_max)
        )
        target_qualifying_line_count_max = int(
            params.get(
                "target_qualifying_line_count_max",
                group_default(
                    _GEN_DEFAULTS,
                    "target_qualifying_line_count_max",
                    int(default_target_qualifying_line_count_max),
                ),
            )
        )
        effective_target_qualifying_line_count_max = min(
            int(target_qualifying_line_count_max),
            int(default_target_qualifying_line_count_max),
        )
        if int(target_qualifying_line_count_min) > int(effective_target_qualifying_line_count_max):
            raise ValueError("target_qualifying_line_count_min must be <= the effective target max")

        target_selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}:{task_variant}:target_qualifying_line_count",
        )
        target_range_size = max(
            1,
            int(effective_target_qualifying_line_count_max) - int(target_qualifying_line_count_min) + 1,
        )
        target_qualifying_line_count = int(target_qualifying_line_count_min) + (
            int(target_selection_index) % int(target_range_size)
        )

        eligible_shapes = _eligible_board_shapes(
            rows_min=int(rows_min),
            rows_max=int(rows_max),
            cols_min=int(cols_min),
            cols_max=int(cols_max),
            task_variant=str(task_variant),
            run_length=int(run_length),
            target_qualifying_line_count=int(target_qualifying_line_count),
        )
        if not eligible_shapes:
            raise RuntimeError("failed to find any board shape supporting the target run-count answer")
        shape_selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}:{task_variant}:board_shape",
        )
        rows, cols = eligible_shapes[int(shape_selection_index) % len(eligible_shapes)]

        palette_size = int(task_rng.randint(int(palette_size_min), int(palette_size_max)))
        palette = sample_named_tile_palette(task_rng, palette_size=int(palette_size))
        if len(palette) < int(palette_size):
            raise ValueError(f"requested palette_size={palette_size} exceeds available named tile colors")
        query_color_name, query_color_rgb = task_rng.choice(list(palette))
        palette_names = [str(name) for name, _rgb in palette]

        color_grid = _build_color_grid_with_exact_target(
            task_rng,
            rows=int(rows),
            cols=int(cols),
            task_variant=str(task_variant),
            palette_names=palette_names,
            query_color_name=str(query_color_name),
            run_length=int(run_length),
            target_qualifying_line_count=int(target_qualifying_line_count),
        )
        qualifying_runs = (
            _row_run_examples(
                color_grid,
                query_color_name=str(query_color_name),
                run_length=int(run_length),
            )
            if str(task_variant) == "rows"
            else _col_run_examples(
                color_grid,
                query_color_name=str(query_color_name),
                run_length=int(run_length),
            )
        )
        answer_value = int(len(qualifying_runs))
        if int(answer_value) != int(target_qualifying_line_count):
            raise RuntimeError("constructed board does not match target qualifying-line count")

        board_colors = _build_board_colors(color_grid, palette)
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
            board_colors=board_colors,
        )

        query_color_hex = rgb_to_hex(query_color_rgb)
        query_color_label = format_named_color_with_hex(query_color_name, query_color_rgb)
        example_coords = [
            (int(row), int(col))
            for run in qualifying_runs
            for row, col in run
        ]
        evidence_artifacts = coordinate_set_evidence_artifacts(
            coords=example_coords,
            bbox_map=scene.bbox_map,
        )
        qualifying_line_indices = [
            int(run[0][0]) if str(task_variant) == "rows" else int(run[0][1])
            for run in qualifying_runs
        ]
        extra_attrs_by_coord = {
            (int(row), int(col)): {
                "canonical_run_index": int(run_index),
                "qualifying_line_index": int(qualifying_line_indices[run_index]),
                "is_canonical_run_evidence": True,
            }
            for run_index, run in enumerate(qualifying_runs)
            for row, col in run
        }
        scene_entities = build_color_board_scene_entities(
            scene,
            query_color_name=str(query_color_name),
            extra_attrs_by_coord=extra_attrs_by_coord,
        )

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
                "json_example_rows",
                "json_example_cols",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example = str(
            prompt_defaults["json_example_rows"]
            if str(task_variant) == "rows"
            else prompt_defaults["json_example_cols"]
        )
        json_example_answer_only = str(prompt_defaults["json_example_answer_only"])
        line_axis_label = "rows" if str(task_variant) == "rows" else "columns"
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
                "line_axis": str(line_axis_label),
                "run_length": int(run_length),
                "query_color": str(query_color_label),
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

        trace_payload = {
            "scene_ir": {
                "scene_kind": "rectangular_tile_board",
                "entities": scene_entities,
                "relations": {},
            },
            "query_spec": {
                "task_variant": str(task_variant),
                "template_id": "match3_run_count_v1",
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "dsl_program": [
                    {"out": "cells", "op": "select", "entity_type": "tile_cell"},
                    {
                        "out": "query_cells",
                        "op": "filter",
                        "in": "cells",
                        "predicate": {"color_name": str(query_color_name)},
                    },
                    {
                        "out": "qualifying_runs",
                        "op": "detect_consecutive_runs",
                        "in": "query_cells",
                        "axis": str(task_variant),
                        "run_length_min": int(run_length),
                        "return": "one_canonical_run_per_qualifying_line",
                    },
                    {
                        "out": "evidence",
                        "op": "project_coords",
                        "in": "qualifying_runs",
                        "coord_space": "tile_grid",
                        "coord_type": "grid_point_set",
                        "ordering": "row_major",
                    },
                    {"out": "answer", "op": "count", "in": "qualifying_runs"},
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
                "task_variant": str(task_variant),
                "line_axis": str(line_axis_label),
                "rows": int(scene.rows),
                "cols": int(scene.cols),
                "palette": list(build_palette_trace(scene.palette)),
                "palette_size": int(scene.palette_size),
                "query_color_name": str(query_color_name),
                "query_color_rgb": [int(query_color_rgb[0]), int(query_color_rgb[1]), int(query_color_rgb[2])],
                "query_color_hex": str(query_color_hex),
                "query_color_label": str(query_color_label),
                "run_length": int(run_length),
                "construction_strategy": "exact_target_qualifying_line_count",
                "target_qualifying_line_count": int(target_qualifying_line_count),
                "target_qualifying_line_count_range": [
                    int(target_qualifying_line_count_min),
                    int(effective_target_qualifying_line_count_max),
                ],
                "qualifying_line_indices": [int(index) for index in qualifying_line_indices],
                "qualifying_runs": [
                    {
                        "run_index": int(run_index),
                        "line_index": int(qualifying_line_indices[run_index]),
                        "coords": [[int(row), int(col)] for row, col in run],
                        "ids": [cell_id((int(row), int(col))) for row, col in run],
                    }
                    for run_index, run in enumerate(qualifying_runs)
                ],
                "answer_value": int(answer_value),
            },
            "witness_symbolic": dict(evidence_artifacts["witness_symbolic"]),
            "projected_evidence": dict(evidence_artifacts["projected_evidence"]),
        }

        line_capacity = _line_capacity(str(task_variant), rows=int(scene.rows), cols=int(scene.cols))
        complexity = TaskComplexity(
            complexity_score=min(
                1.0,
                max(
                    0.0,
                    (
                        (float(int(scene.rows) * int(scene.cols)) / 49.0)
                        + (float(int(scene.palette_size)) / 3.0)
                        + (float(int(answer_value)) / float(max(1, int(line_capacity))))
                    )
                    / 3.0,
                ),
            ),
            complexity_components={
                "rows": int(scene.rows),
                "cols": int(scene.cols),
                "palette_size": int(scene.palette_size),
                "run_length": int(run_length),
                "answer_count": int(answer_value),
                "line_capacity": int(line_capacity),
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
            task_variant=str(task_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
