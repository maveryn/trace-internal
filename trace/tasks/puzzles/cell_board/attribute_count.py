"""Public cell-board color-attribute counting task."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.seed import spawn_rng
from trace.core.task_group_config import get_task_group_defaults
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.bbox_projection import pixel_anchor_map_from_bboxes
from trace.tasks.shared.color_format import format_named_color_with_hex, rgb_to_hex
from trace.tasks.shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from trace.tasks.shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_json_example import resolve_prompt_json_examples
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from .shared.color_board_common import (
    RectangularColorBoardTaskDefaults,
    build_palette_trace,
    build_rectangular_color_board_render_spec,
    build_rectangular_color_board_scene,
)
from .shared.complexity import (
    build_tile_complexity,
    normalize_int_with_bounds,
    resolve_tile_complexity_weights,
)
from .shared.grid_graph import cell_id
from .shared.named_color_board import build_color_board_scene_entities
from .shared.tile_colors import sample_named_tile_palette
from .shared.tile_annotation import coordinate_set_annotation_artifacts, sort_coords_row_major
from .shared.visual_defaults import load_tile_background_defaults, load_tile_noise_defaults


SINGLE_ATTRIBUTE_MEMBERSHIP_COUNT_TASK_ID = "task_puzzles__cell_board__single_attribute_membership_count"
SCOPED_ATTRIBUTE_COUNT_TASK_ID = "task_puzzles__cell_board__scoped_attribute_count"
PUBLIC_SCENE_ID = "cell_board"
_DEFAULTS = RectangularColorBoardTaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "cell_board_count")
POST_IMAGE_BACKGROUND_DEFAULTS = load_tile_background_defaults(task_group="count")
POST_IMAGE_NOISE_DEFAULTS = load_tile_noise_defaults(task_group="count", apply_prob=0.5)

Coord = Tuple[int, int]

_QUERY_IDS: Tuple[str, ...] = (
    "color_cell_count",
    "row_color_cell_count",
    "column_color_cell_count",
    "edge_color_cell_count",
)
_QUERY_TEMPLATE_KEYS: Mapping[str, str] = {
    "color_cell_count": "color_cell_count_query",
    "row_color_cell_count": "row_color_cell_count_query",
    "column_color_cell_count": "column_color_cell_count_query",
    "edge_color_cell_count": "edge_color_cell_count_query",
}


def _load_defaults(task_id: str) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    group_defaults = _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, dict) else {}
    gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        group_defaults,
        task_id=str(task_id),
    )
    complexity_weights = resolve_tile_complexity_weights(group_defaults, task_id=str(task_id))
    return dict(gen_defaults), dict(render_defaults), dict(prompt_defaults), dict(complexity_weights)


def _explicit_query_id(params: Mapping[str, Any]) -> str | None:
    for key in ("query_id", "query_variant"):
        candidate = params.get(key)
        if candidate is None:
            continue
        if str(candidate) == "default":
            continue
        return str(candidate)
    return None


def _resolve_query(
    params: Mapping[str, Any],
    *,
    task_id: str,
    supported_query_ids: Sequence[str],
    instance_seed: int,
) -> tuple[str, Mapping[str, float]]:
    query_ids = tuple(str(query_id) for query_id in supported_query_ids)
    if not query_ids:
        raise ValueError(f"{task_id} must define at least one supported query")
    explicit = _explicit_query_id(params)
    if explicit is not None:
        if explicit not in query_ids:
            raise ValueError(f"unsupported query for {task_id}: {explicit!r}; expected one of {sorted(query_ids)!r}")
        return str(explicit), {str(explicit): 1.0}
    rng = spawn_rng(int(instance_seed), f"{task_id}.query")
    index = int(rng.randrange(len(query_ids)))
    return str(query_ids[int(index)]), {query_id: 1.0 / float(len(query_ids)) for query_id in query_ids}


def _resolve_target_answer(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    task_id: str,
    query_id: str,
    instance_seed: int,
) -> tuple[int, Sequence[int], Mapping[str, float]]:
    target_min = int(params.get("target_answer_min", group_default(gen_defaults, "target_answer_min", 0)))
    target_max = int(params.get("target_answer_max", group_default(gen_defaults, "target_answer_max", 10)))
    if int(target_min) < 0:
        raise ValueError("target_answer_min must be >= 0")
    if int(target_min) > int(target_max):
        raise ValueError("target_answer_min must be <= target_answer_max")
    support = tuple(range(int(target_min), int(target_max) + 1))
    explicit = params.get("target_answer")
    if explicit is not None:
        value = int(explicit)
        if value not in support:
            raise ValueError("target_answer is outside configured support")
        return int(value), support, uniform_probability_map(support, selected=int(value))

    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:{query_id}:target_answer",
    )
    value = int(support[int(index) % len(support)])
    return int(value), support, uniform_probability_map(support)


def _edge_coords(rows: int, cols: int) -> list[Coord]:
    coords: list[Coord] = []
    for row in range(int(rows)):
        for col in range(int(cols)):
            if int(row) in {0, int(rows) - 1} or int(col) in {0, int(cols) - 1}:
                coords.append((int(row), int(col)))
    return coords


def _scope_coords(query_id: str, *, rows: int, cols: int, row_index: int, col_index: int) -> list[Coord]:
    if str(query_id) == "row_color_cell_count":
        return [(int(row_index), int(col)) for col in range(int(cols))]
    if str(query_id) == "column_color_cell_count":
        return [(int(row), int(col_index)) for row in range(int(rows))]
    if str(query_id) == "edge_color_cell_count":
        return _edge_coords(int(rows), int(cols))
    return [(int(row), int(col)) for row in range(int(rows)) for col in range(int(cols))]


def _sample_dimensions(
    rng,
    *,
    query_id: str,
    target_answer: int,
    rows_min: int,
    rows_max: int,
    cols_min: int,
    cols_max: int,
) -> tuple[int, int]:
    min_rows = int(rows_min)
    min_cols = int(cols_min)
    if str(query_id) == "column_color_cell_count":
        min_rows = max(int(min_rows), int(target_answer))
    if str(query_id) == "row_color_cell_count":
        min_cols = max(int(min_cols), int(target_answer))
    if int(min_rows) > int(rows_max) or int(min_cols) > int(cols_max):
        raise ValueError("target answer is infeasible for configured row/column bounds")
    for _ in range(100):
        rows = int(rng.randint(int(min_rows), int(rows_max)))
        cols = int(rng.randint(int(min_cols), int(cols_max)))
        scope_size = len(_scope_coords(str(query_id), rows=rows, cols=cols, row_index=0, col_index=0))
        if int(target_answer) <= int(scope_size):
            return int(rows), int(cols)
    raise RuntimeError("failed to sample feasible cell-board dimensions for attribute count")


class _CellBoardAttributeCountTask:
    """Shared implementation for public cell-board color-attribute count tasks."""

    domain = "puzzles"
    task_group = "cell_board"
    supported_query_ids: Tuple[str, ...] = _QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        task_rng = spawn_rng(int(instance_seed), "task")
        gen_defaults, render_defaults, prompt_defaults, complexity_weights = _load_defaults(str(self.task_id))
        query_id, query_probabilities = _resolve_query(
            params,
            task_id=str(self.task_id),
            supported_query_ids=self.supported_query_ids,
            instance_seed=int(instance_seed),
        )
        target_answer, target_answer_support, target_answer_probabilities = _resolve_target_answer(
            params,
            gen_defaults=gen_defaults,
            task_id=str(self.task_id),
            query_id=str(query_id),
            instance_seed=int(instance_seed),
        )

        rows_min, rows_max = resolve_required_int_bounds(
            params,
            gen_defaults,
            min_key="rows_min",
            max_key="rows_max",
            fallback_min=int(_DEFAULTS.rows_min),
            fallback_max=int(_DEFAULTS.rows_max),
            context=f"generation defaults for {self.task_id}",
        )
        cols_min, cols_max = resolve_required_int_bounds(
            params,
            gen_defaults,
            min_key="cols_min",
            max_key="cols_max",
            fallback_min=int(_DEFAULTS.cols_min),
            fallback_max=int(_DEFAULTS.cols_max),
            context=f"generation defaults for {self.task_id}",
        )
        palette_size_min, palette_size_max = resolve_required_int_bounds(
            params,
            gen_defaults,
            min_key="palette_size_min",
            max_key="palette_size_max",
            fallback_min=int(_DEFAULTS.palette_size_min),
            fallback_max=int(_DEFAULTS.palette_size_max),
            context=f"generation defaults for {self.task_id}",
        )

        scene = None
        matching_coords: list[Coord] = []
        scope: list[Coord] = []
        query_row_index = -1
        query_col_index = -1
        query_color_name = ""
        query_color_rgb = (0, 0, 0)

        for _attempt in range(int(max_attempts)):
            rows, cols = _sample_dimensions(
                task_rng,
                query_id=str(query_id),
                target_answer=int(target_answer),
                rows_min=int(rows_min),
                rows_max=int(rows_max),
                cols_min=int(cols_min),
                cols_max=int(cols_max),
            )
            query_row_index = int(task_rng.randrange(int(rows))) if str(query_id) == "row_color_cell_count" else -1
            query_col_index = int(task_rng.randrange(int(cols))) if str(query_id) == "column_color_cell_count" else -1
            scope = _scope_coords(
                str(query_id),
                rows=int(rows),
                cols=int(cols),
                row_index=max(0, int(query_row_index)),
                col_index=max(0, int(query_col_index)),
            )
            if int(target_answer) > len(scope):
                continue

            palette_size = int(task_rng.randint(int(palette_size_min), int(palette_size_max)))
            palette = sample_named_tile_palette(task_rng, palette_size=int(palette_size))
            if len(palette) < 2:
                continue
            query_color_name, query_color_rgb = palette[0]
            non_query_palette = [
                (str(name), (int(rgb[0]), int(rgb[1]), int(rgb[2])))
                for name, rgb in palette[1:]
                if str(name) != str(query_color_name)
            ]
            if not non_query_palette:
                continue

            scope_shuffled = list(scope)
            task_rng.shuffle(scope_shuffled)
            matching_coords = sort_coords_row_major(scope_shuffled[: int(target_answer)])
            matching_set = {(int(row), int(col)) for row, col in matching_coords}
            board_colors = {}
            all_coords = [(int(row), int(col)) for row in range(int(rows)) for col in range(int(cols))]
            for coord in all_coords:
                if coord in matching_set:
                    board_colors[coord] = (str(query_color_name), tuple(int(value) for value in query_color_rgb))
                else:
                    board_colors[coord] = task_rng.choice(non_query_palette)

            scene = build_rectangular_color_board_scene(
                int(instance_seed),
                task_rng=task_rng,
                params=params,
                generation_defaults=gen_defaults,
                rendering_defaults=render_defaults,
                background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
                noise_defaults=POST_IMAGE_NOISE_DEFAULTS,
                defaults=_DEFAULTS,
                rows=int(rows),
                cols=int(cols),
                palette=palette,
                board_colors=board_colors,
                coordinate_labels=True,
            )
            break

        if scene is None:
            raise RuntimeError("failed to sample cell-board attribute-count scene")

        annotation_artifacts = coordinate_set_annotation_artifacts(
            coords=matching_coords,
            bbox_map=scene.bbox_map,
        )
        query_color_hex = rgb_to_hex(query_color_rgb)
        query_color_label = format_named_color_with_hex(query_color_name, query_color_rgb)
        answer_value = int(len(matching_coords))

        all_prompt_defaults = dict(prompt_defaults if isinstance(prompt_defaults, dict) else {})
        prompt_defaults = required_group_defaults(
            all_prompt_defaults,
            (
                "bundle_id",
                "scene_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "annotation_hint",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = resolve_prompt_json_examples(
            all_prompt_defaults,
            annotation_value=[[120, 120], [168, 120], [216, 168]],
            answer_type="integer",
        )
        prompt_selection = render_task_prompt_variants(
            domain="puzzles",
            task_group="cell_board_count",
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(_QUERY_TEMPLATE_KEYS[str(query_id)]),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "rows": int(scene.rows),
                "cols": int(scene.cols),
                "query_color": str(query_color_label),
                "query_row": str(int(query_row_index) + 1) if int(query_row_index) >= 0 else "",
                "query_column": str(int(query_col_index) + 1) if int(query_col_index) >= 0 else "",
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        matching_set = {(int(row), int(col)) for row, col in matching_coords}
        scope_set = {(int(row), int(col)) for row, col in scope}
        palette_trace = build_palette_trace(scene.palette)
        scene_entities = build_color_board_scene_entities(
            scene,
            query_color_name=str(query_color_name),
            extra_attrs_by_coord={
                (int(row), int(col)): {
                    "row_label": int(row) + 1,
                    "column_label": int(col) + 1,
                    "in_query_scope": bool((int(row), int(col)) in scope_set),
                    "is_counted_match": bool((int(row), int(col)) in matching_set),
                }
                for row in range(int(scene.rows))
                for col in range(int(scene.cols))
            },
        )
        count_by_color_name = {
            str(name): sum(1 for cell_name, _rgb in scene.board_colors.values() if str(cell_name) == str(name))
            for name, _rgb in scene.palette
        }

        query_params = {
            "query_id": str(query_id),
            "internal_query_id": str(query_id),
            "query_id_probabilities": dict(query_probabilities),
            "scene_id": PUBLIC_SCENE_ID,
            "target_answer": int(target_answer),
            "target_answer_range": [int(target_answer_support[0]), int(target_answer_support[-1])],
            "target_answer_probabilities": dict(target_answer_probabilities),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "rectangular_tile_board",
                "entities": scene_entities,
                "relations": {
                    "query_id": str(query_id),
                    "scene_id": PUBLIC_SCENE_ID,
                    "query_color_name": str(query_color_name),
                    "query_row_1based": int(query_row_index) + 1 if int(query_row_index) >= 0 else None,
                    "query_column_1based": int(query_col_index) + 1 if int(query_col_index) >= 0 else None,
                    "answer_value": int(answer_value),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "internal_query_id": str(query_id),
                "query_id_probabilities": dict(query_probabilities),
                "template_id": f"{query_id}_v0",
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
                "dsl_program": [
                    {"out": "cells", "op": "select", "entity_type": "tile_cell"},
                    {"out": "scope", "op": "filter", "in": "cells", "predicate": {"scope": str(query_id)}},
                    {
                        "out": "query_cells",
                        "op": "filter",
                        "in": "scope",
                        "predicate": {"color_name": str(query_color_name)},
                    },
                    {
                        "out": "annotation",
                        "op": "project_coords",
                        "in": "query_cells",
                        "source_coord_space": "tile_grid",
                        "coord_space": "image_pixel",
                        "coord_type": "point_set",
                        "ordering": "row_major",
                    },
                    {"out": "answer", "op": "count", "in": "query_cells"},
                ],
            },
            "render_spec": {
                **build_rectangular_color_board_render_spec(scene),
                "scene_id": PUBLIC_SCENE_ID,
                "query_id": str(query_id),
                "internal_query_id": str(query_id),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": pixel_anchor_map_from_bboxes(scene.bbox_map),
            },
            "execution_trace": {
                **dict(query_params),
                "rows": int(scene.rows),
                "cols": int(scene.cols),
                "palette": list(palette_trace),
                "palette_size": int(scene.palette_size),
                "query_color_name": str(query_color_name),
                "query_color_rgb": [int(query_color_rgb[0]), int(query_color_rgb[1]), int(query_color_rgb[2])],
                "query_color_hex": str(query_color_hex),
                "query_color_label": str(query_color_label),
                "query_row_1based": int(query_row_index) + 1 if int(query_row_index) >= 0 else None,
                "query_column_1based": int(query_col_index) + 1 if int(query_col_index) >= 0 else None,
                "scope_coords": [[int(row), int(col)] for row, col in sort_coords_row_major(scope)],
                "matching_coords": [[int(row), int(col)] for row, col in matching_coords],
                "matching_ids": list(annotation_artifacts["private_witness"]["ids"]),
                "counts_by_color_name": dict(count_by_color_name),
                "answer_value": int(answer_value),
            },
            "witness_symbolic": dict(annotation_artifacts["witness_symbolic"]),
            "projected_annotation": dict(annotation_artifacts["projected_annotation"]),
        }

        board_cell_count = int(scene.rows) * int(scene.cols)
        min_board_cell_count = int(rows_min) * int(cols_min)
        max_board_cell_count = int(rows_max) * int(cols_max)
        complexity = build_tile_complexity(
            weights=complexity_weights,
            components={
                "visual_scan": (
                    0.70
                    * normalize_int_with_bounds(
                        int(board_cell_count),
                        (int(min_board_cell_count), int(max_board_cell_count)),
                    )
                    + 0.30
                    * normalize_int_with_bounds(
                        int(scene.palette_size),
                        (int(palette_size_min), int(palette_size_max)),
                    )
                ),
                "reasoning_load": normalize_int_with_bounds(
                    int(answer_value),
                    (int(target_answer_support[0]), int(target_answer_support[-1])),
                ),
            },
        )

        versions = default_task_versions()
        versions["cell_board_attribute_count_version"] = "v0"
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(answer_value)),
            annotation_gt=TypedValue(
                type=str(annotation_artifacts["annotation_type"]),
                value=list(annotation_artifacts["annotation_value"]),
            ),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=versions,
            scene_id=PUBLIC_SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class CellBoardSingleAttributeMembershipCountTask(_CellBoardAttributeCountTask):
    """Count all visible cells with one target color."""

    task_id = SINGLE_ATTRIBUTE_MEMBERSHIP_COUNT_TASK_ID
    supported_query_ids = ("color_cell_count",)


@register_task
class CellBoardScopedAttributeCountTask(_CellBoardAttributeCountTask):
    """Count target-color cells inside a row, column, or edge scope."""

    task_id = SCOPED_ATTRIBUTE_COUNT_TASK_ID
    supported_query_ids = ("row_color_cell_count", "column_color_cell_count", "edge_color_cell_count")


__all__ = [
    "CellBoardScopedAttributeCountTask",
    "CellBoardSingleAttributeMembershipCountTask",
    "SCOPED_ATTRIBUTE_COUNT_TASK_ID",
    "SINGLE_ATTRIBUTE_MEMBERSHIP_COUNT_TASK_ID",
]
