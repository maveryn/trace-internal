"""Count grid rows or columns satisfying a named-icon count condition."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.variant_sampling import resolve_variant
from ..shared.complexity import build_icon_task_complexity
from ..shared.evidence import bbox_set_evidence
from ..shared.icon_scene import sort_bboxes_reading_order
from ..shared.icon_task_rendering import icon_render_style_trace
from ..shared.procedural_named_icons import (
    PROCEDURAL_NAMED_ICON_FILL_STYLES,
    PROCEDURAL_NAMED_ICON_SHAPES,
    procedural_named_icon_display_name,
    validate_procedural_named_icon_fill_style_support,
)
from .named_grid_row_column_shape_count import (
    DEFAULT_GRID_SIZE_SUPPORT,
    SCENE_ID,
    _DEFAULTS as _GRID_DEFAULTS,
    _ScenePayload,
    _grid_size_label,
    _named_grid_style_trace,
    _render_scene,
    _resolve_named_grid_render_params,
    _serialize_icon,
)


TASK_ID = "task_icons__named_grid__line_condition_count"
QUERY_IDS: Tuple[str, ...] = (
    "row_at_least_shape_count",
    "column_at_least_shape_count",
    "row_exactly_shape_count",
    "column_exactly_shape_count",
    "row_no_shape_count",
    "column_no_shape_count",
)


@dataclass(frozen=True)
class _SampleSpec:
    """Symbolic named-grid line-condition sample."""

    query_id: str
    target_shape_id: str
    target_shape_name: str
    answer_count: int
    grid_rows: int
    grid_cols: int
    queried_axis: str
    condition: str
    threshold: int
    shape_ids_by_cell: Tuple[Tuple[str, ...], ...]
    counted_cells: Tuple[Tuple[int, int], ...]
    off_line_target_cells: Tuple[Tuple[int, int], ...]
    qualifying_line_indices: Tuple[int, ...]
    row_target_counts: Tuple[int, ...]
    column_target_counts: Tuple[int, ...]
    query_probabilities: Dict[str, float]
    answer_probabilities: Dict[str, float]
    grid_size_probabilities: Dict[str, float]
    threshold_probabilities: Dict[str, float]
    shape_probabilities: Dict[str, float]
    fill_style_support: Tuple[str, ...]
    fill_style_probabilities: Dict[str, float]


_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _string_probability_map(values: Sequence[str], *, selected: str | None = None) -> Dict[str, float]:
    support = tuple(str(value) for value in values)
    if not support:
        return {}
    if selected is not None:
        return {str(value): (1.0 if str(value) == str(selected) else 0.0) for value in support}
    probability = 1.0 / float(len(support))
    return {str(value): float(probability) for value in support}


def _int_bounds(params: Mapping[str, Any], low_key: str, high_key: str, fallback_low: int, fallback_high: int) -> Tuple[int, int]:
    low = int(params.get(low_key, group_default(_GEN_DEFAULTS, low_key, fallback_low)))
    high = int(params.get(high_key, group_default(_GEN_DEFAULTS, high_key, fallback_high)))
    if low < 0 or high < low:
        raise ValueError(f"invalid {low_key}/{high_key} bounds")
    return int(low), int(high)


def _shape_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("shape_id_support", group_default(_GEN_DEFAULTS, "shape_id_support", PROCEDURAL_NAMED_ICON_SHAPES))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("shape_id_support must be a sequence")
    values = tuple(dict.fromkeys(str(value).strip() for value in raw if str(value).strip()))
    unsupported = sorted(set(values) - set(PROCEDURAL_NAMED_ICON_SHAPES))
    if unsupported:
        raise ValueError(f"unsupported procedural named icon shapes: {unsupported}")
    if len(values) < 8:
        raise ValueError("named-grid line-condition task needs at least eight supported named shapes")
    return values


def _fill_style_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get(
        "named_icon_fill_style_support",
        group_default(_GEN_DEFAULTS, "named_icon_fill_style_support", PROCEDURAL_NAMED_ICON_FILL_STYLES),
    )
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raw = PROCEDURAL_NAMED_ICON_FILL_STYLES
    return validate_procedural_named_icon_fill_style_support(tuple(str(value) for value in raw))


def _fill_style_probability_map(params: Mapping[str, Any], support: Sequence[str]) -> Dict[str, float]:
    raw = params.get(
        "named_icon_fill_style_weights",
        group_default(_GEN_DEFAULTS, "named_icon_fill_style_weights", None),
    )
    if not isinstance(raw, Mapping):
        probability = 1.0 / float(len(tuple(support)))
        return {str(value): float(probability) for value in support}
    weights = {str(value): max(0.0, float(raw.get(str(value), 0.0))) for value in support}
    total = sum(float(value) for value in weights.values())
    if total <= 0.0:
        probability = 1.0 / float(len(tuple(support)))
        return {str(value): float(probability) for value in support}
    return {str(value): float(weights[str(value)]) / float(total) for value in support}


def _grid_size_support(params: Mapping[str, Any]) -> Tuple[Tuple[int, int], ...]:
    raw = params.get("grid_size_support", group_default(_GEN_DEFAULTS, "grid_size_support", DEFAULT_GRID_SIZE_SUPPORT))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("grid_size_support must be a sequence")
    values: List[Tuple[int, int]] = []
    for item in raw:
        if isinstance(item, str):
            parts = str(item).lower().split("x")
            if len(parts) != 2:
                raise ValueError(f"unsupported grid size string: {item}")
            rows, cols = int(parts[0]), int(parts[1])
        elif isinstance(item, Sequence) and not isinstance(item, (str, bytes)) and len(item) >= 2:
            rows, cols = int(item[0]), int(item[1])
        else:
            raise ValueError(f"unsupported grid size entry: {item}")
        if rows < 2 or cols < 2:
            raise ValueError("named-grid sizes must be at least 2x2")
        values.append((int(rows), int(cols)))
    support = tuple(dict.fromkeys(values))
    if not support:
        raise ValueError("grid_size_support resolved no grid sizes")
    return support


def _query_axis_condition(query_id: str) -> Tuple[str, str]:
    query = str(query_id)
    if query.startswith("row_"):
        axis = "row"
    elif query.startswith("column_"):
        axis = "column"
    else:
        raise ValueError(f"unsupported named-grid line-condition query_id: {query_id}")
    if "_at_least_" in query:
        condition = "at_least"
    elif "_exactly_" in query:
        condition = "exactly"
    elif "_no_" in query:
        condition = "none"
    else:
        raise ValueError(f"unsupported named-grid line-condition query_id: {query_id}")
    return str(axis), str(condition)


def _resolve_target_shape(rng, *, params: Mapping[str, Any], support: Sequence[str]) -> Tuple[str, Dict[str, float]]:
    explicit_shape = params.get("shape_id", params.get("target_shape_id"))
    if explicit_shape is not None:
        target_shape_id = str(explicit_shape)
        if target_shape_id not in set(support):
            raise ValueError(f"target shape must be one of {support}")
        return str(target_shape_id), _string_probability_map(tuple(str(value) for value in support), selected=str(target_shape_id))
    target_shape_id = str(rng.choice(tuple(str(value) for value in support)))
    return str(target_shape_id), _string_probability_map(tuple(str(value) for value in support))


def _choose_answer_count(
    rng,
    *,
    params: Mapping[str, Any],
    axis: str,
    grid_size_support: Sequence[Tuple[int, int]],
) -> Tuple[int, Dict[str, float]]:
    low, high = _int_bounds(params, "answer_count_min", "answer_count_max", 0, 5)
    explicit_rows = params.get("grid_rows")
    explicit_cols = params.get("grid_cols")
    if explicit_rows is not None and explicit_cols is not None:
        axis_count = int(explicit_rows) if str(axis) == "row" else int(explicit_cols)
        high = min(int(high), int(axis_count))
    else:
        max_axis_count = max(int(size[0]) if str(axis) == "row" else int(size[1]) for size in grid_size_support)
        high = min(int(high), int(max_axis_count))
    support = tuple(range(int(low), int(high) + 1))
    if not support:
        raise ValueError("answer_count support is empty")
    explicit = params.get("answer_count", params.get("target_count", params.get("answer")))
    if explicit is not None:
        answer_count = int(explicit)
        if answer_count not in set(support):
            raise ValueError("answer_count is outside configured support")
        return int(answer_count), uniform_probability_map(support, selected=int(answer_count))
    answer_count = int(rng.choice(support))
    return int(answer_count), uniform_probability_map(support)


def _choose_grid_size(
    rng,
    *,
    params: Mapping[str, Any],
    axis: str,
    answer_count: int,
) -> Tuple[int, int, Dict[str, float]]:
    support = _grid_size_support(params)
    explicit_rows = params.get("grid_rows")
    explicit_cols = params.get("grid_cols")
    if explicit_rows is not None or explicit_cols is not None:
        if explicit_rows is None or explicit_cols is None:
            raise ValueError("grid_rows and grid_cols must be provided together")
        size = (int(explicit_rows), int(explicit_cols))
        if size not in set(support):
            raise ValueError("explicit grid size is outside grid_size_support")
        axis_count = int(size[0]) if str(axis) == "row" else int(size[1])
        if int(answer_count) > int(axis_count):
            raise ValueError("explicit grid size cannot support answer_count")
        labels = tuple(_grid_size_label(value) for value in support)
        return int(size[0]), int(size[1]), _string_probability_map(labels, selected=_grid_size_label(size))

    feasible = tuple(
        size
        for size in support
        if int(answer_count) <= (int(size[0]) if str(axis) == "row" else int(size[1]))
    )
    if not feasible:
        raise ValueError("grid_size_support cannot support answer_count")
    selected = tuple(int(value) for value in rng.choice(feasible))
    labels = tuple(_grid_size_label(value) for value in feasible)
    return int(selected[0]), int(selected[1]), _string_probability_map(labels)


def _choose_threshold(
    rng,
    *,
    params: Mapping[str, Any],
    condition: str,
    line_capacity: int,
) -> Tuple[int, Dict[str, float]]:
    if str(condition) == "none":
        return 0, {"0": 1.0}
    if str(condition) == "at_least":
        low, high = _int_bounds(params, "at_least_threshold_min", "at_least_threshold_max", 2, 3)
    else:
        low, high = _int_bounds(params, "exactly_threshold_min", "exactly_threshold_max", 1, 3)
    high = min(int(high), int(line_capacity))
    if high < low:
        raise ValueError("threshold support is empty for selected grid")
    support = tuple(range(int(low), int(high) + 1))
    explicit = params.get("threshold")
    if explicit is not None:
        threshold = int(explicit)
        if threshold not in set(support):
            raise ValueError("threshold is outside configured support")
        return int(threshold), uniform_probability_map(support, selected=int(threshold))
    threshold = int(rng.choice(support))
    return int(threshold), uniform_probability_map(support)


def _line_cells(*, axis: str, line_index: int, rows: int, cols: int) -> Tuple[Tuple[int, int], ...]:
    if str(axis) == "row":
        return tuple((int(line_index), col) for col in range(int(cols)))
    return tuple((row, int(line_index)) for row in range(int(rows)))


def _line_qualifies(count: int, *, condition: str, threshold: int) -> bool:
    if str(condition) == "at_least":
        return int(count) >= int(threshold)
    if str(condition) == "exactly":
        return int(count) == int(threshold)
    if str(condition) == "none":
        return int(count) == 0
    raise ValueError(f"unsupported condition: {condition}")


def _sample_line_target_count(rng, *, qualifies: bool, condition: str, threshold: int, line_capacity: int) -> int:
    if bool(qualifies):
        if str(condition) == "at_least":
            return int(rng.randint(int(threshold), int(line_capacity)))
        if str(condition) == "exactly":
            return int(threshold)
        return 0
    if str(condition) == "at_least":
        return int(rng.randint(0, max(0, int(threshold) - 1)))
    if str(condition) == "exactly":
        support = tuple(value for value in range(int(line_capacity) + 1) if int(value) != int(threshold))
        return int(rng.choice(support))
    return int(rng.randint(1, int(line_capacity)))


def _construct_grid_shapes(
    rng,
    *,
    support: Sequence[str],
    target_shape_id: str,
    axis: str,
    condition: str,
    threshold: int,
    answer_count: int,
    grid_rows: int,
    grid_cols: int,
) -> Tuple[Tuple[Tuple[str, ...], ...], Tuple[Tuple[int, int], ...], Tuple[Tuple[int, int], ...], Tuple[int, ...], Tuple[int, ...], Tuple[int, ...]]:
    axis_count = int(grid_rows) if str(axis) == "row" else int(grid_cols)
    line_capacity = int(grid_cols) if str(axis) == "row" else int(grid_rows)
    if int(answer_count) > int(axis_count):
        raise ValueError("answer_count exceeds number of available grid lines")

    line_indices = list(range(int(axis_count)))
    rng.shuffle(line_indices)
    qualifying_line_indices = tuple(sorted(int(value) for value in line_indices[: int(answer_count)]))

    target_cells: set[Tuple[int, int]] = set()
    counted_cells: set[Tuple[int, int]] = set()
    for line_index in range(int(axis_count)):
        qualifies = int(line_index) in set(qualifying_line_indices)
        target_count = _sample_line_target_count(
            rng,
            qualifies=bool(qualifies),
            condition=str(condition),
            threshold=int(threshold),
            line_capacity=int(line_capacity),
        )
        cells = list(_line_cells(axis=str(axis), line_index=int(line_index), rows=int(grid_rows), cols=int(grid_cols)))
        rng.shuffle(cells)
        selected_cells = set(cells[: int(target_count)])
        target_cells.update(selected_cells)
        if bool(qualifies):
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
    realized = tuple(
        int(index)
        for index, count in enumerate(active_counts)
        if _line_qualifies(int(count), condition=str(condition), threshold=int(threshold))
    )
    if realized != qualifying_line_indices:
        raise RuntimeError("constructed grid does not realize requested qualifying-line count")

    return (
        tuple(tuple(str(value) for value in row) for row in shape_ids),
        tuple(sorted((int(row), int(col)) for row, col in counted_cells)),
        tuple(sorted((int(row), int(col)) for row, col in target_cells if (int(row), int(col)) not in counted_cells)),
        tuple(int(value) for value in qualifying_line_indices),
        tuple(int(value) for value in row_counts),
        tuple(int(value) for value in column_counts),
    )


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _SampleSpec:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:sample")
    query_id, query_probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
    )
    axis, condition = _query_axis_condition(str(query_id))
    grid_support = _grid_size_support(params)
    answer_count, answer_probabilities = _choose_answer_count(
        rng,
        params=params,
        axis=str(axis),
        grid_size_support=grid_support,
    )
    grid_rows, grid_cols, grid_size_probabilities = _choose_grid_size(
        rng,
        params=params,
        axis=str(axis),
        answer_count=int(answer_count),
    )
    line_capacity = int(grid_cols) if str(axis) == "row" else int(grid_rows)
    threshold, threshold_probabilities = _choose_threshold(
        rng,
        params=params,
        condition=str(condition),
        line_capacity=int(line_capacity),
    )
    shape_support = _shape_support(params)
    target_shape_id, shape_probabilities = _resolve_target_shape(rng, params=params, support=shape_support)
    shape_ids_by_cell, counted_cells, off_line_target_cells, qualifying_line_indices, row_counts, column_counts = _construct_grid_shapes(
        rng,
        support=shape_support,
        target_shape_id=str(target_shape_id),
        axis=str(axis),
        condition=str(condition),
        threshold=int(threshold),
        answer_count=int(answer_count),
        grid_rows=int(grid_rows),
        grid_cols=int(grid_cols),
    )
    fill_style_support = _fill_style_support(params)
    fill_style_probabilities = _fill_style_probability_map(params, fill_style_support)
    return _SampleSpec(
        query_id=str(query_id),
        target_shape_id=str(target_shape_id),
        target_shape_name=procedural_named_icon_display_name(str(target_shape_id)),
        answer_count=int(answer_count),
        grid_rows=int(grid_rows),
        grid_cols=int(grid_cols),
        queried_axis=str(axis),
        condition=str(condition),
        threshold=int(threshold),
        shape_ids_by_cell=tuple(tuple(str(value) for value in row) for row in shape_ids_by_cell),
        counted_cells=tuple((int(row), int(col)) for row, col in counted_cells),
        off_line_target_cells=tuple((int(row), int(col)) for row, col in off_line_target_cells),
        qualifying_line_indices=tuple(int(value) for value in qualifying_line_indices),
        row_target_counts=tuple(int(value) for value in row_counts),
        column_target_counts=tuple(int(value) for value in column_counts),
        query_probabilities=dict(query_probabilities),
        answer_probabilities=dict(answer_probabilities),
        grid_size_probabilities=dict(grid_size_probabilities),
        threshold_probabilities=dict(threshold_probabilities),
        shape_probabilities=dict(shape_probabilities),
        fill_style_support=tuple(fill_style_support),
        fill_style_probabilities=dict(fill_style_probabilities),
    )


def _line_region_bbox(scene: _ScenePayload, *, axis: str, line_index: int) -> Tuple[int, int, int, int]:
    if str(axis) == "row":
        cells = tuple(scene.cell_bboxes_xyxy[int(line_index)][col] for col in range(len(scene.cell_bboxes_xyxy[int(line_index)])))
    else:
        cells = tuple(scene.cell_bboxes_xyxy[row][int(line_index)] for row in range(len(scene.cell_bboxes_xyxy)))
    return (
        min(int(box[0]) for box in cells),
        min(int(box[1]) for box in cells),
        max(int(box[2]) for box in cells),
        max(int(box[3]) for box in cells),
    )


def _all_line_region_bboxes(scene: _ScenePayload, *, axis: str) -> Dict[str, List[int]]:
    line_count = len(scene.cell_bboxes_xyxy) if str(axis) == "row" else len(scene.cell_bboxes_xyxy[0])
    return {
        f"{axis}_{int(index) + 1}": [int(value) for value in _line_region_bbox(scene, axis=str(axis), line_index=int(index))]
        for index in range(int(line_count))
    }


def _complexity(sample: _SampleSpec, *, scene: _ScenePayload, render_params: Mapping[str, Any]) -> TaskComplexity:
    cell_count = int(sample.grid_rows) * int(sample.grid_cols)
    visual_scan = (float(cell_count) - 16.0) / max(1.0, 36.0 - 16.0)
    axis_count = int(sample.grid_rows) if str(sample.queried_axis) == "row" else int(sample.grid_cols)
    line_density = float(sample.answer_count) / float(max(1, axis_count))
    condition_load = {"none": 0.25, "at_least": 0.55, "exactly": 0.75}.get(str(sample.condition), 0.5)
    boundary_density = 1.0 - abs((2.0 * line_density) - 1.0)
    ambiguity = (0.55 * float(boundary_density)) + (0.45 * float(condition_load))
    noise_cap = max((int(value) for value in render_params["icon_noise_edit_count_range"]), default=0)
    clutter = (
        min(1.0, sum(len(icon.noise_edits) for icon in scene.icons) / float(max(1, len(scene.icons) * noise_cap)))
        if int(noise_cap) > 0
        else 0.0
    )
    return build_icon_task_complexity(
        task_group_defaults=_TASK_GROUP_DEFAULTS,
        task_id=TASK_ID,
        criterion_values={
            "semantic_match": 0.45,
            "visual_scan": max(0.0, min(1.0, visual_scan)),
            "ambiguity": max(0.0, min(1.0, ambiguity)),
            "clutter": max(0.0, min(1.0, clutter)),
        },
    )


@register_task
class IconsCountingNamedGridLineConditionCountTask:
    """Count numbered rows or columns satisfying a target-shape count condition."""

    task_id = TASK_ID
    domain = "icons"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        render_params = _resolve_named_grid_render_params(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_GRID_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        last_error: Exception | None = None
        sample: _SampleSpec | None = None
        scene: _ScenePayload | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                sample = _sample_spec(instance_seed=int(instance_seed), params=params)
                scene_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:scene", int(attempt))
                scene = _render_scene(
                    sample=sample,  # type: ignore[arg-type]
                    instance_seed=int(instance_seed),
                    render_params=render_params,
                    params=params,
                    rng=scene_rng,
                    task_id=TASK_ID,
                )
                break
            except Exception as exc:  # pragma: no cover - covered by smoke tests.
                last_error = exc
                sample = None
                scene = None
        if sample is None or scene is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        qualifying_line_bboxes = tuple(
            _line_region_bbox(scene, axis=str(sample.queried_axis), line_index=int(index))
            for index in sample.qualifying_line_indices
        )
        evidence_bboxes = sort_bboxes_reading_order(qualifying_line_bboxes)
        if len(evidence_bboxes) != int(sample.answer_count):
            raise RuntimeError("rendered named-grid line-condition evidence count does not match answer")
        evidence_payload = bbox_set_evidence(evidence_bboxes)

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "question_text_row_at_least_shape_count",
                "question_text_column_at_least_shape_count",
                "question_text_row_exactly_shape_count",
                "question_text_column_exactly_shape_count",
                "question_text_row_no_shape_count",
                "question_text_column_no_shape_count",
                "evidence_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        question_key = f"question_text_{sample.query_id}"
        line_kind_plural = "rows" if str(sample.queried_axis) == "row" else "columns"
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(prompt_defaults[question_key]).format(
                    target_shape_name=str(sample.target_shape_name),
                    threshold=int(sample.threshold),
                ),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]).format(
                    target_shape_name=str(sample.target_shape_name),
                    line_kind=str(sample.queried_axis),
                    line_kind_plural=str(line_kind_plural),
                    threshold=int(sample.threshold),
                ),
                "answer_hint": str(prompt_defaults["answer_hint"]).format(line_kind_plural=str(line_kind_plural)),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        serialized_icons = [_serialize_icon(icon) for icon in scene.icons]
        shape_counts = dict(Counter(str(icon.shape_id) for icon in scene.icons))
        active_counts = sample.row_target_counts if str(sample.queried_axis) == "row" else sample.column_target_counts
        qualifying_line_numbers = tuple(int(index) + 1 for index in sample.qualifying_line_indices)
        line_region_bboxes = _all_line_region_bboxes(scene, axis=str(sample.queried_axis))
        qualifying_region_map = {
            f"{sample.queried_axis}_{int(index) + 1}": [int(value) for value in _line_region_bbox(scene, axis=str(sample.queried_axis), line_index=int(index))]
            for index in sample.qualifying_line_indices
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_named_grid_line_condition_count",
                "scene_id": SCENE_ID,
                "entities": list(serialized_icons),
                "relations": {
                    "counting_rule": "grid_line_shape_count_condition",
                    "target_shape_id": str(sample.target_shape_id),
                    "target_shape_name": str(sample.target_shape_name),
                    "queried_axis": str(sample.queried_axis),
                    "condition": str(sample.condition),
                    "threshold": int(sample.threshold),
                    "answer_count": int(sample.answer_count),
                    "grid_rows": int(sample.grid_rows),
                    "grid_cols": int(sample.grid_cols),
                    "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
                    "row_target_counts": [int(value) for value in sample.row_target_counts],
                    "column_target_counts": [int(value) for value in sample.column_target_counts],
                    "active_line_target_counts": [int(value) for value in active_counts],
                    "qualifying_line_numbers": [int(value) for value in qualifying_line_numbers],
                    "qualifying_line_regions": dict(qualifying_region_map),
                    "selected_line_target_cells": [[int(row), int(col)] for row, col in sample.counted_cells],
                    "other_target_cells": [[int(row), int(col)] for row, col in sample.off_line_target_cells],
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene.panel_geometry),
                },
            },
            "query_spec": {
                "query_id": str(sample.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "target_shape_id": str(sample.target_shape_id),
                    "target_shape_name": str(sample.target_shape_name),
                    "answer_count": int(sample.answer_count),
                    "grid_rows": int(sample.grid_rows),
                    "grid_cols": int(sample.grid_cols),
                    "queried_axis": str(sample.queried_axis),
                    "condition": str(sample.condition),
                    "threshold": int(sample.threshold),
                    "query_id_probabilities": dict(sample.query_probabilities),
                    "answer_probabilities": dict(sample.answer_probabilities),
                    "grid_size_probabilities": dict(sample.grid_size_probabilities),
                    "threshold_probabilities": dict(sample.threshold_probabilities),
                    "shape_id_support": list(_shape_support(params)),
                    "shape_probabilities": dict(sample.shape_probabilities),
                    "named_icon_fill_style_support": list(sample.fill_style_support),
                    "fill_style_probabilities": dict(sample.fill_style_probabilities),
                },
            },
            "render_spec": {
                "canvas_size": list(scene.panel_geometry["canvas_size"]),
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "panel_geometry": dict(scene.panel_geometry),
                "grid_bbox_xyxy": [int(value) for value in scene.grid_bbox_xyxy],
                "cell_size_px": int(scene.cell_size_px),
                "style": {
                    **icon_render_style_trace(render_params=render_params, sampled_palette_rgb=scene.sampled_palette_rgb),
                    **_named_grid_style_trace(render_params),
                },
            },
            "render_map": {
                "image_id": "img0",
                "object_bboxes_px": {
                    str(icon.instance_id): [int(value) for value in icon.bbox_xyxy]
                    for icon in scene.icons
                },
                "cell_bboxes_px": {
                    f"r{int(row) + 1}c{int(col) + 1}": [int(value) for value in scene.cell_bboxes_xyxy[int(row)][int(col)]]
                    for row in range(int(sample.grid_rows))
                    for col in range(int(sample.grid_cols))
                },
                "line_region_bboxes_px": dict(line_region_bboxes),
                "qualifying_line_region_bboxes_px": dict(qualifying_region_map),
            },
            "execution_trace": {
                "scene_variant": "single_panel_named_grid",
                "query_id": str(sample.query_id),
                "question_format": "count_grid_lines_satisfying_named_shape_count_condition",
                "target_shape_id": str(sample.target_shape_id),
                "target_shape_name": str(sample.target_shape_name),
                "answer": int(sample.answer_count),
                "grid_rows": int(sample.grid_rows),
                "grid_cols": int(sample.grid_cols),
                "queried_axis": str(sample.queried_axis),
                "condition": str(sample.condition),
                "threshold": int(sample.threshold),
                "shape_ids_by_cell": [list(row) for row in sample.shape_ids_by_cell],
                "row_target_counts": [int(value) for value in sample.row_target_counts],
                "column_target_counts": [int(value) for value in sample.column_target_counts],
                "active_line_target_counts": [int(value) for value in active_counts],
                "qualifying_line_indices": [int(value) for value in sample.qualifying_line_indices],
                "qualifying_line_numbers": [int(value) for value in qualifying_line_numbers],
                "selected_line_target_cells": [[int(row), int(col)] for row, col in sample.counted_cells],
                "other_target_cells": [[int(row), int(col)] for row, col in sample.off_line_target_cells],
            },
            "witness_symbolic": {
                "query_id": str(sample.query_id),
                "target_shape_id": str(sample.target_shape_id),
                "target_shape_name": str(sample.target_shape_name),
                "answer": int(sample.answer_count),
                "qualifying_line_numbers": [int(value) for value in qualifying_line_numbers],
                "qualifying_line_region_bboxes": dict(qualifying_region_map),
            },
            "projected_evidence": dict(evidence_payload["projected_evidence"]),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(sample.answer_count)),
            evidence_gt=TypedValue(type=str(evidence_payload["evidence_type"]), value=list(evidence_payload["evidence_value"])),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_complexity(sample, scene=scene, render_params=render_params),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sample.query_id),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
        )


__all__ = ["IconsCountingNamedGridLineConditionCountTask"]
