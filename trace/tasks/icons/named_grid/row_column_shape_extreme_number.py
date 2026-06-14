"""Identify the grid row or column with an extreme named-icon count."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, load_scene_generation_rendering_prompt_defaults, required_group_defaults
from ...shared.deterministic_sampling import uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.variant_sampling import resolve_variant
from ..shared.annotation import bbox_set_annotation
from ..shared.icon_scene import sort_bboxes_reading_order
from ..shared.procedural_named_icons import PROCEDURAL_NAMED_ICON_SHAPES, procedural_named_icon_display_name
from .shared.defaults import DEFAULT_GRID_SIZE_SUPPORT, SCENE_ID, NamedGridDefaults
from .shared.output import render_map_fragment, render_spec_fragment, scene_ir_fragment
from .shared.rendering import render_named_grid_scene, serialize_named_grid_icon
from .shared.sampling import (
    fill_style_probability_map as resolve_fill_style_probability_map,
    fill_style_support as resolve_fill_style_support,
    grid_size_label,
    grid_size_support,
    int_bounds,
    resolve_target_shape,
    shape_support as resolve_shape_support,
    string_probability_map,
)
from .shared.state import NamedGridScenePayload
from .shared.styles import resolve_named_grid_render_params


DOMAIN = "icons"

TASK_ID = "task_icons__named_grid__row_column_shape_extreme_number"
QUERY_IDS: Tuple[str, ...] = (
    "row_most_shape_number",
    "row_fewest_shape_number",
    "column_most_shape_number",
    "column_fewest_shape_number",
)


@dataclass(frozen=True)
class _SampleSpec:
    """Symbolic named-grid row/column extremum sample."""

    query_id: str
    target_shape_id: str
    target_shape_name: str
    answer_line_number: int
    winning_target_count: int
    grid_rows: int
    grid_cols: int
    queried_axis: str
    extremum: str
    shape_ids_by_cell: Tuple[Tuple[str, ...], ...]
    counted_cells: Tuple[Tuple[int, int], ...]
    off_line_target_cells: Tuple[Tuple[int, int], ...]
    row_target_counts: Tuple[int, ...]
    column_target_counts: Tuple[int, ...]
    query_probabilities: Dict[str, float]
    answer_probabilities: Dict[str, float]
    grid_size_probabilities: Dict[str, float]
    winning_count_probabilities: Dict[str, float]
    shape_probabilities: Dict[str, float]
    fill_style_support: Tuple[str, ...]
    fill_style_probabilities: Dict[str, float]

_DEFAULTS = NamedGridDefaults()
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    DOMAIN,
    SCENE_ID,
    task_id=TASK_ID,
)


def _query_axis_extremum(query_id: str) -> Tuple[str, str]:
    """Resolve the row/column axis and most/fewest operator from the public query."""

    query = str(query_id)
    if query.startswith("row_"):
        axis = "row"
    elif query.startswith("column_"):
        axis = "column"
    else:
        raise ValueError(f"unsupported named-grid extreme query_id: {query_id}")
    extremum = "most" if "_most_" in query else "fewest"
    return str(axis), str(extremum)


def _choose_answer_line_number(
    rng,
    *,
    params: Mapping[str, Any],
    axis: str,
    grid_size_support: Sequence[Tuple[int, int]],
) -> Tuple[int, Dict[str, float]]:
    low, high = int_bounds(params, _GEN_DEFAULTS, "answer_line_number_min", "answer_line_number_max", 1, 6)
    explicit_rows = params.get("grid_rows")
    explicit_cols = params.get("grid_cols")
    max_line_number = max(int(size[0]) if str(axis) == "row" else int(size[1]) for size in grid_size_support)
    if explicit_rows is not None and explicit_cols is not None:
        max_line_number = int(explicit_rows) if str(axis) == "row" else int(explicit_cols)
    high = min(int(high), int(max_line_number))
    support = tuple(range(int(low), int(high) + 1))
    if not support:
        raise ValueError("answer_line_number support is empty")
    explicit = params.get("answer_line_number", params.get("target_line_number", params.get("answer")))
    if explicit is not None:
        answer_line_number = int(explicit)
        if answer_line_number not in set(support):
            raise ValueError("answer_line_number is outside configured support")
        return int(answer_line_number), uniform_probability_map(support, selected=int(answer_line_number))
    answer_line_number = int(rng.choice(support))
    return int(answer_line_number), uniform_probability_map(support)


def _choose_grid_size(
    rng,
    *,
    params: Mapping[str, Any],
    axis: str,
    answer_line_number: int,
) -> Tuple[int, int, Dict[str, float]]:
    support = grid_size_support(params, _GEN_DEFAULTS)
    explicit_rows = params.get("grid_rows")
    explicit_cols = params.get("grid_cols")
    if explicit_rows is not None or explicit_cols is not None:
        if explicit_rows is None or explicit_cols is None:
            raise ValueError("grid_rows and grid_cols must be provided together")
        size = (int(explicit_rows), int(explicit_cols))
        if size not in set(support):
            raise ValueError("explicit grid size is outside grid_size_support")
        axis_count = int(size[0]) if str(axis) == "row" else int(size[1])
        if int(answer_line_number) > int(axis_count):
            raise ValueError("explicit grid size cannot support answer_line_number")
        labels = tuple(grid_size_label(value) for value in support)
        return int(size[0]), int(size[1]), string_probability_map(labels, selected=grid_size_label(size))

    feasible = tuple(
        size
        for size in support
        if int(answer_line_number) <= (int(size[0]) if str(axis) == "row" else int(size[1]))
    )
    if not feasible:
        raise ValueError("grid_size_support cannot support answer_line_number")
    selected = tuple(int(value) for value in rng.choice(feasible))
    labels = tuple(grid_size_label(value) for value in feasible)
    return int(selected[0]), int(selected[1]), string_probability_map(labels)


def _choose_winning_count(
    rng,
    *,
    params: Mapping[str, Any],
    extremum: str,
    line_capacity: int,
) -> Tuple[int, Dict[str, float]]:
    explicit = params.get("winning_target_count", params.get("target_count"))
    if str(extremum) == "most":
        low, high = int_bounds(params, _GEN_DEFAULTS, "most_winning_count_min", "most_winning_count_max", 2, 5)
        high = min(int(high), int(line_capacity))
    else:
        low, high = int_bounds(params, _GEN_DEFAULTS, "fewest_winning_count_min", "fewest_winning_count_max", 1, 3)
        high = min(int(high), max(0, int(line_capacity) - 1))
    if high < low:
        raise ValueError("winning target-count support is empty")
    support = tuple(range(int(low), int(high) + 1))
    if explicit is not None:
        value = int(explicit)
        if value not in set(support):
            raise ValueError("winning_target_count is outside configured support")
        return int(value), uniform_probability_map(support, selected=int(value))
    value = int(rng.choice(support))
    return int(value), uniform_probability_map(support)


def _line_cells(*, axis: str, line_index: int, rows: int, cols: int) -> Tuple[Tuple[int, int], ...]:
    if str(axis) == "row":
        return tuple((int(line_index), col) for col in range(int(cols)))
    return tuple((row, int(line_index)) for row in range(int(rows)))


def _construct_grid_shapes(
    rng,
    *,
    support: Sequence[str],
    target_shape_id: str,
    axis: str,
    extremum: str,
    answer_line_number: int,
    winning_target_count: int,
    grid_rows: int,
    grid_cols: int,
) -> Tuple[Tuple[Tuple[str, ...], ...], Tuple[Tuple[int, int], ...], Tuple[Tuple[int, int], ...], Tuple[int, ...], Tuple[int, ...]]:
    """Construct a grid with one unique extreme line for the queried axis.

    The selected row or column realizes the target extreme count, and every
    competing line is adjusted away from that count to preserve answer
    uniqueness.
    """

    axis_count = int(grid_rows) if str(axis) == "row" else int(grid_cols)
    line_capacity = int(grid_cols) if str(axis) == "row" else int(grid_rows)
    winning_index = int(answer_line_number) - 1
    if winning_index < 0 or winning_index >= axis_count:
        raise ValueError("answer_line_number is outside selected axis")

    line_counts: List[int] = []
    for line_index in range(int(axis_count)):
        if int(line_index) == int(winning_index):
            line_counts.append(int(winning_target_count))
        elif str(extremum) == "most":
            line_counts.append(int(rng.randint(0, max(0, int(winning_target_count) - 1))))
        else:
            line_counts.append(int(rng.randint(int(winning_target_count) + 1, int(line_capacity))))

    target_cells: set[Tuple[int, int]] = set()
    counted_cells: set[Tuple[int, int]] = set()
    for line_index, target_count in enumerate(line_counts):
        cells = list(_line_cells(axis=str(axis), line_index=int(line_index), rows=int(grid_rows), cols=int(grid_cols)))
        rng.shuffle(cells)
        selected_cells = set(cells[: int(target_count)])
        target_cells.update(selected_cells)
        if int(line_index) == int(winning_index):
            counted_cells.update(selected_cells)

    distractor_support = tuple(str(value) for value in support if str(value) != str(target_shape_id))
    rows_out: List[Tuple[str, ...]] = []
    for row in range(int(grid_rows)):
        row_values: List[str] = []
        for col in range(int(grid_cols)):
            if (int(row), int(col)) in target_cells:
                row_values.append(str(target_shape_id))
            else:
                row_values.append(str(rng.choice(distractor_support)))
        rows_out.append(tuple(row_values))

    shape_ids = tuple(rows_out)
    row_counts = tuple(
        sum(1 for col in range(int(grid_cols)) if shape_ids[int(row)][int(col)] == str(target_shape_id))
        for row in range(int(grid_rows))
    )
    column_counts = tuple(
        sum(1 for row in range(int(grid_rows)) if shape_ids[int(row)][int(col)] == str(target_shape_id))
        for col in range(int(grid_cols))
    )
    active_counts = row_counts if str(axis) == "row" else column_counts
    winning_count = active_counts[int(winning_index)]
    if str(extremum) == "most":
        if sum(1 for value in active_counts if int(value) == max(active_counts)) != 1 or int(winning_count) != max(active_counts):
            raise RuntimeError("constructed grid does not realize a unique most line")
    else:
        if sum(1 for value in active_counts if int(value) == min(active_counts)) != 1 or int(winning_count) != min(active_counts):
            raise RuntimeError("constructed grid does not realize a unique fewest line")

    return (
        tuple(tuple(str(value) for value in row) for row in shape_ids),
        tuple(sorted((int(row), int(col)) for row, col in counted_cells)),
        tuple(sorted((int(row), int(col)) for row, col in target_cells if (int(row), int(col)) not in counted_cells)),
        tuple(int(value) for value in row_counts),
        tuple(int(value) for value in column_counts),
    )


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _SampleSpec:
    """Sample one complete symbolic extreme-line contract before rendering."""

    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:sample")
    query_id, query_probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
    )
    axis, extremum = _query_axis_extremum(str(query_id))
    grid_support = grid_size_support(params, _GEN_DEFAULTS)
    answer_line_number, answer_probabilities = _choose_answer_line_number(
        rng,
        params=params,
        axis=str(axis),
        grid_size_support=grid_support,
    )
    grid_rows, grid_cols, grid_size_probabilities = _choose_grid_size(
        rng,
        params=params,
        axis=str(axis),
        answer_line_number=int(answer_line_number),
    )
    line_capacity = int(grid_cols) if str(axis) == "row" else int(grid_rows)
    winning_target_count, winning_count_probabilities = _choose_winning_count(
        rng,
        params=params,
        extremum=str(extremum),
        line_capacity=int(line_capacity),
    )
    shape_support = resolve_shape_support(params, _GEN_DEFAULTS)
    target_shape_id, shape_probabilities = resolve_target_shape(rng, params=params, defaults=_GEN_DEFAULTS, support=shape_support)
    shape_ids_by_cell, counted_cells, off_line_target_cells, row_counts, column_counts = _construct_grid_shapes(
        rng,
        support=shape_support,
        target_shape_id=str(target_shape_id),
        axis=str(axis),
        extremum=str(extremum),
        answer_line_number=int(answer_line_number),
        winning_target_count=int(winning_target_count),
        grid_rows=int(grid_rows),
        grid_cols=int(grid_cols),
    )
    fill_style_support = resolve_fill_style_support(params, _GEN_DEFAULTS)
    fill_style_probabilities = resolve_fill_style_probability_map(params, _GEN_DEFAULTS, fill_style_support)
    return _SampleSpec(
        query_id=str(query_id),
        target_shape_id=str(target_shape_id),
        target_shape_name=procedural_named_icon_display_name(str(target_shape_id)),
        answer_line_number=int(answer_line_number),
        winning_target_count=int(winning_target_count),
        grid_rows=int(grid_rows),
        grid_cols=int(grid_cols),
        queried_axis=str(axis),
        extremum=str(extremum),
        shape_ids_by_cell=tuple(tuple(str(value) for value in row) for row in shape_ids_by_cell),
        counted_cells=tuple((int(row), int(col)) for row, col in counted_cells),
        off_line_target_cells=tuple((int(row), int(col)) for row, col in off_line_target_cells),
        row_target_counts=tuple(int(value) for value in row_counts),
        column_target_counts=tuple(int(value) for value in column_counts),
        query_probabilities=dict(query_probabilities),
        answer_probabilities=dict(answer_probabilities),
        grid_size_probabilities=dict(grid_size_probabilities),
        winning_count_probabilities=dict(winning_count_probabilities),
        shape_probabilities=dict(shape_probabilities),
        fill_style_support=tuple(fill_style_support),
        fill_style_probabilities=dict(fill_style_probabilities),
    )


@register_task
class IconsCountingNamedGridRowColumnShapeExtremeNumberTask:
    """Return the numbered grid line with a unique extreme named-icon count."""

    task_id = TASK_ID
    domain = DOMAIN
    supported_query_ids = QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one named-grid row/column extreme-number instance."""

        render_params = resolve_named_grid_render_params(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        last_error: Exception | None = None
        sample: _SampleSpec | None = None
        scene: NamedGridScenePayload | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                sample = _sample_spec(instance_seed=int(instance_seed), params=params)
                scene_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:scene", int(attempt))
                scene = render_named_grid_scene(
                    sample=sample,  # type: ignore[arg-type]
                    instance_seed=int(instance_seed),
                    render_params=render_params,
                    params=params,
                    rng=scene_rng,
                )
                break
            except Exception as exc:  # pragma: no cover - covered by smoke tests.
                last_error = exc
                sample = None
                scene = None
        if sample is None or scene is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        counted_icons = tuple(icon for icon in scene.icons if bool(icon.is_counted))
        annotation_bboxes = sort_bboxes_reading_order(icon.bbox_xyxy for icon in counted_icons)
        if len(annotation_bboxes) != int(sample.winning_target_count):
            raise RuntimeError("rendered named-grid extreme annotation count does not match winning line count")
        annotation_payload = bbox_set_annotation(annotation_bboxes)

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "question_text_row_most_shape_number",
                "question_text_row_fewest_shape_number",
                "question_text_column_most_shape_number",
                "question_text_column_fewest_shape_number",
                "annotation_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        question_key = f"question_text_{sample.query_id}"
        prompt_selection = render_task_prompt_variants(
            domain=DOMAIN,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(prompt_defaults[question_key]).format(
                    target_shape_name=str(sample.target_shape_name),
                ),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]).format(
                    target_shape_name=str(sample.target_shape_name),
                    line_kind=str(sample.queried_axis),
                    line_number=int(sample.answer_line_number),
                    extremum=str(sample.extremum),
                ),
                "answer_hint": str(prompt_defaults["answer_hint"]).format(line_kind=str(sample.queried_axis)),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        serialized_icons = [serialize_named_grid_icon(icon) for icon in scene.icons]
        counted_instance_ids = tuple(str(icon.instance_id) for icon in counted_icons)
        shape_counts = dict(Counter(str(icon.shape_id) for icon in scene.icons))
        active_counts = sample.row_target_counts if str(sample.queried_axis) == "row" else sample.column_target_counts
        trace_payload = {
            "scene_ir": scene_ir_fragment(
                scene,
                scene_kind="icons_named_grid_row_column_shape_extreme_number",
                entities=list(serialized_icons),
                relations={
                    "counting_rule": "unique_extreme_shape_count_over_grid_lines",
                    "target_shape_id": str(sample.target_shape_id),
                    "target_shape_name": str(sample.target_shape_name),
                    "queried_axis": str(sample.queried_axis),
                    "extremum": str(sample.extremum),
                    "answer_line_number": int(sample.answer_line_number),
                    "answer_line_index": int(sample.answer_line_number) - 1,
                    "winning_target_count": int(sample.winning_target_count),
                    "grid_rows": int(sample.grid_rows),
                    "grid_cols": int(sample.grid_cols),
                    "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
                    "row_target_counts": [int(value) for value in sample.row_target_counts],
                    "column_target_counts": [int(value) for value in sample.column_target_counts],
                    "active_line_target_counts": [int(value) for value in active_counts],
                    "selected_line_target_cells": [[int(row), int(col)] for row, col in sample.counted_cells],
                    "off_line_target_cells": [[int(row), int(col)] for row, col in sample.off_line_target_cells],
                },
            ),
            "query_spec": {
                "query_id": str(sample.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "target_shape_id": str(sample.target_shape_id),
                    "target_shape_name": str(sample.target_shape_name),
                    "query_id": str(sample.query_id),
                    "answer_line_number": int(sample.answer_line_number),
                    "winning_target_count": int(sample.winning_target_count),
                    "grid_rows": int(sample.grid_rows),
                    "grid_cols": int(sample.grid_cols),
                    "queried_axis": str(sample.queried_axis),
                    "extremum": str(sample.extremum),
                    "query_id_probabilities": dict(sample.query_probabilities),
                    "answer_probabilities": dict(sample.answer_probabilities),
                    "grid_size_probabilities": dict(sample.grid_size_probabilities),
                    "winning_count_probabilities": dict(sample.winning_count_probabilities),
                    "shape_id_support": list(resolve_shape_support(params, _GEN_DEFAULTS)),
                    "shape_probabilities": dict(sample.shape_probabilities),
                    "named_icon_fill_style_support": list(sample.fill_style_support),
                    "fill_style_probabilities": dict(sample.fill_style_probabilities),
                },
            },
            "render_spec": render_spec_fragment(scene, render_params=render_params),
            "render_map": render_map_fragment(
                scene,
                rows=int(sample.grid_rows),
                cols=int(sample.grid_cols),
                extra_fields={"selected_line_target_instance_ids": list(counted_instance_ids)},
            ),
            "execution_trace": {
                "scene_variant": "single_panel_named_grid",
                "query_id": str(sample.query_id),
                "question_format": "select_grid_line_number_by_extreme_named_shape_count",
                "target_shape_id": str(sample.target_shape_id),
                "target_shape_name": str(sample.target_shape_name),
                "answer": int(sample.answer_line_number),
                "grid_rows": int(sample.grid_rows),
                "grid_cols": int(sample.grid_cols),
                "queried_axis": str(sample.queried_axis),
                "extremum": str(sample.extremum),
                "answer_line_number": int(sample.answer_line_number),
                "answer_line_index": int(sample.answer_line_number) - 1,
                "winning_target_count": int(sample.winning_target_count),
                "shape_ids_by_cell": [list(row) for row in sample.shape_ids_by_cell],
                "row_target_counts": [int(value) for value in sample.row_target_counts],
                "column_target_counts": [int(value) for value in sample.column_target_counts],
                "active_line_target_counts": [int(value) for value in active_counts],
                "selected_line_target_cells": [[int(row), int(col)] for row, col in sample.counted_cells],
                "off_line_target_cells": [[int(row), int(col)] for row, col in sample.off_line_target_cells],
                "selected_line_target_instance_ids": list(counted_instance_ids),
            },
            "witness_symbolic": {
                "query_id": str(sample.query_id),
                "target_shape_id": str(sample.target_shape_id),
                "target_shape_name": str(sample.target_shape_name),
                "answer": int(sample.answer_line_number),
                "winning_target_count": int(sample.winning_target_count),
                "selected_line_target_cells": [[int(row), int(col)] for row, col in sample.counted_cells],
                "selected_line_target_instance_ids": list(counted_instance_ids),
            },
            "projected_annotation": dict(annotation_payload["projected_annotation"]),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(sample.answer_line_number)),
            annotation_gt=TypedValue(type=str(annotation_payload["annotation_type"]), value=list(annotation_payload["annotation_value"])),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sample.query_id),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
        )


__all__ = ["IconsCountingNamedGridRowColumnShapeExtremeNumberTask"]
