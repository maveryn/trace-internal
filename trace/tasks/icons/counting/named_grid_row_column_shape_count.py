"""Count prompt-named procedural icons in a specified grid row or column."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_legibility import resolve_readable_text_style, text_legibility_summary_from_records
from ...shared.text_rendering import draw_text_centered, load_font
from ...shared.variant_sampling import resolve_variant
from ..shared.complexity import build_icon_task_complexity
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.annotation import bbox_set_annotation
from ..shared.icon_noise import serialize_icon_noise_edits
from ..shared.icon_scene import BBox, draw_single_panel, resolve_single_panel_layout, single_panel_geometry_to_trace, sort_bboxes_reading_order
from ..shared.icon_style import sample_icon_palette
from ..shared.icon_task_rendering import icon_render_style_trace, resolve_icon_render_params, resolve_icon_rgb_param, sample_icon_instance_noise
from ..shared.procedural_named_icons import (
    PROCEDURAL_NAMED_ICON_FILL_STYLES,
    PROCEDURAL_NAMED_ICON_SHAPES,
    procedural_named_icon_display_name,
    render_procedural_named_icon_rgba,
    sample_procedural_named_icon_fill_style,
    validate_procedural_named_icon_fill_style_support,
)


TASK_ID = "task_icons__named_grid__scoped_attribute_count"
SCENE_ID = "named_grid"
QUERY_IDS: Tuple[str, ...] = ("row_shape_count", "column_shape_count")
DEFAULT_GRID_SIZE_SUPPORT: Tuple[Tuple[int, int], ...] = (
    (4, 4),
    (4, 5),
    (4, 6),
    (5, 4),
    (5, 5),
    (5, 6),
    (6, 4),
    (6, 5),
    (6, 6),
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for named-grid row/column counting."""

    target_count_min: int = 1
    target_count_max: int = 5
    off_line_target_count_min: int = 1
    off_line_target_count_max: int = 4
    canvas_width: int = 880
    canvas_height: int = 680
    reference_panel_width_px: int = ICON_SHARED_DEFAULTS.reference_panel_width_px
    reference_icon_size_px: int = ICON_SHARED_DEFAULTS.reference_icon_size_px
    reference_icon_size_min_px: int = ICON_SHARED_DEFAULTS.reference_icon_size_px
    reference_icon_size_max_px: int = ICON_SHARED_DEFAULTS.reference_icon_size_px
    panel_gap_px: int = ICON_SHARED_DEFAULTS.panel_gap_px
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    scene_icon_size_min_px: int = 48
    scene_icon_size_max_px: int = 76
    scene_max_overlap_fraction: float = 0.0
    scene_placement_max_attempts: int = ICON_SHARED_DEFAULTS.scene_placement_max_attempts
    scene_size_shrink_rounds: int = ICON_SHARED_DEFAULTS.scene_size_shrink_rounds
    scene_size_shrink_factor: float = ICON_SHARED_DEFAULTS.scene_size_shrink_factor
    palette_size_min: int = 8
    palette_size_max: int = 12
    color_channel_min: int = 24
    color_channel_max: int = 220
    min_color_distance: float = 40.0
    color_distance_space: str = "lab"
    background_color_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.background_color_rgb
    panel_fill_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_fill_rgb
    panel_border_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_border_rgb
    header_text_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.header_text_rgb
    icon_noise_edit_types: Tuple[str, ...] = ICON_SHARED_DEFAULTS.icon_noise_edit_types
    icon_noise_edit_count_range: Tuple[int, int] = ICON_SHARED_DEFAULTS.icon_noise_edit_count_range
    icon_noise_value_ranges: Dict[str, Dict[str, Tuple[float, float]]] = field(
        default_factory=lambda: dict(ICON_SHARED_DEFAULTS.icon_noise_value_ranges)
    )
    named_icon_fill_style_support: Tuple[str, ...] = PROCEDURAL_NAMED_ICON_FILL_STYLES
    row_label_band_width_px: int = 48
    column_label_band_height_px: int = 42
    grid_label_gap_px: int = 10
    grid_cell_max_size_px: int = 104
    grid_cell_padding_px: int = 12
    grid_line_width_px: int = 2
    grid_border_width_px: int = 3
    axis_label_font_size_px: int = 24
    grid_line_rgb: Tuple[int, int, int] = (176, 187, 205)
    cell_fill_rgb: Tuple[int, int, int] = (255, 255, 255)
    alternate_cell_fill_rgb: Tuple[int, int, int] = (248, 250, 253)
    axis_label_rgb: Tuple[int, int, int] = (50, 60, 78)


@dataclass(frozen=True)
class _SampleSpec:
    """Symbolic named-grid count sample."""

    query_id: str
    target_shape_id: str
    target_shape_name: str
    target_count: int
    grid_rows: int
    grid_cols: int
    queried_axis: str
    queried_index: int
    shape_ids_by_cell: Tuple[Tuple[str, ...], ...]
    counted_cells: Tuple[Tuple[int, int], ...]
    off_line_target_cells: Tuple[Tuple[int, int], ...]
    query_probabilities: Dict[str, float]
    answer_probabilities: Dict[str, float]
    grid_size_probabilities: Dict[str, float]
    line_index_probabilities: Dict[str, float]
    shape_probabilities: Dict[str, float]
    fill_style_support: Tuple[str, ...]
    fill_style_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedGridIcon:
    """Rendered named-grid icon metadata."""

    instance_id: str
    row_index: int
    col_index: int
    row_number: int
    column_number: int
    shape_id: str
    shape_name: str
    bbox_xyxy: Tuple[int, int, int, int]
    cell_bbox_xyxy: Tuple[int, int, int, int]
    nominal_size_px: int
    tint_rgb: Tuple[int, int, int]
    fill_style: str
    noise_edits: Tuple[Dict[str, Any], ...]
    noise_seed: int | None
    is_target_shape: bool
    is_counted: bool


@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready rendered named-grid scene payload."""

    image: Image.Image
    panel_geometry: Dict[str, Any]
    grid_bbox_xyxy: Tuple[int, int, int, int]
    cell_bboxes_xyxy: Tuple[Tuple[Tuple[int, int, int, int], ...], ...]
    icons: Tuple[_RenderedGridIcon, ...]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    cell_size_px: int


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _shape_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("shape_id_support", group_default(_GEN_DEFAULTS, "shape_id_support", PROCEDURAL_NAMED_ICON_SHAPES))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("shape_id_support must be a sequence")
    values = tuple(dict.fromkeys(str(value).strip() for value in raw if str(value).strip()))
    unsupported = sorted(set(values) - set(PROCEDURAL_NAMED_ICON_SHAPES))
    if unsupported:
        raise ValueError(f"unsupported procedural named icon shapes: {unsupported}")
    if len(values) < 8:
        raise ValueError("named-grid row/column task needs at least eight supported named shapes")
    return values


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


def _fill_style_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get(
        "named_icon_fill_style_support",
        group_default(_GEN_DEFAULTS, "named_icon_fill_style_support", _DEFAULTS.named_icon_fill_style_support),
    )
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raw = _DEFAULTS.named_icon_fill_style_support
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


def _grid_size_label(size: Tuple[int, int]) -> str:
    return f"{int(size[0])}x{int(size[1])}"


def _resolve_target_shape(rng, *, params: Mapping[str, Any], support: Sequence[str]) -> Tuple[str, Dict[str, float]]:
    explicit_shape = params.get("shape_id", params.get("target_shape_id"))
    if explicit_shape is not None:
        target_shape_id = str(explicit_shape)
        if target_shape_id not in set(support):
            raise ValueError(f"target shape must be one of {support}")
        return str(target_shape_id), _string_probability_map(tuple(str(value) for value in support), selected=str(target_shape_id))
    target_shape_id = str(rng.choice(tuple(str(value) for value in support)))
    return str(target_shape_id), _string_probability_map(tuple(str(value) for value in support))


def _choose_grid_size(
    rng,
    *,
    params: Mapping[str, Any],
    query_id: str,
    target_count: int,
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
        line_capacity = int(size[1]) if str(query_id) == "row_shape_count" else int(size[0])
        if int(target_count) > int(line_capacity):
            raise ValueError("explicit grid size cannot support requested target_count")
        labels = tuple(_grid_size_label(value) for value in support)
        return int(size[0]), int(size[1]), _string_probability_map(labels, selected=_grid_size_label(size))

    feasible = tuple(
        size
        for size in support
        if int(target_count) <= (int(size[1]) if str(query_id) == "row_shape_count" else int(size[0]))
    )
    if not feasible:
        raise ValueError("grid_size_support cannot support requested target_count")
    selected = tuple(int(value) for value in rng.choice(feasible))
    labels = tuple(_grid_size_label(value) for value in feasible)
    return int(selected[0]), int(selected[1]), _string_probability_map(labels)


def _choose_line_index(
    rng,
    *,
    params: Mapping[str, Any],
    query_id: str,
    grid_rows: int,
    grid_cols: int,
) -> Tuple[int, Dict[str, float]]:
    axis_count = int(grid_rows) if str(query_id) == "row_shape_count" else int(grid_cols)
    key = "target_row_number" if str(query_id) == "row_shape_count" else "target_column_number"
    explicit = params.get(key, params.get("line_number"))
    support = tuple(range(1, int(axis_count) + 1))
    if explicit is not None:
        number = int(explicit)
        if int(number) not in set(support):
            raise ValueError(f"{key} must be in 1..{axis_count}")
        return int(number) - 1, uniform_probability_map(support, selected=int(number))
    number = int(rng.choice(support))
    return int(number) - 1, uniform_probability_map(support)


def _construct_grid_shapes(
    rng,
    *,
    support: Sequence[str],
    target_shape_id: str,
    query_id: str,
    target_count: int,
    grid_rows: int,
    grid_cols: int,
    queried_index: int,
    params: Mapping[str, Any],
) -> Tuple[Tuple[Tuple[str, ...], ...], Tuple[Tuple[int, int], ...], Tuple[Tuple[int, int], ...]]:
    line_cells = (
        tuple((int(queried_index), col) for col in range(int(grid_cols)))
        if str(query_id) == "row_shape_count"
        else tuple((row, int(queried_index)) for row in range(int(grid_rows)))
    )
    if int(target_count) > len(line_cells):
        raise ValueError("target_count exceeds queried row/column capacity")
    shuffled_line = list(line_cells)
    rng.shuffle(shuffled_line)
    counted_cells = tuple(sorted(shuffled_line[: int(target_count)]))

    all_cells = tuple((row, col) for row in range(int(grid_rows)) for col in range(int(grid_cols)))
    off_line_cells = [cell for cell in all_cells if cell not in set(line_cells)]
    off_min, off_max = _int_bounds(
        params,
        "off_line_target_count_min",
        "off_line_target_count_max",
        _DEFAULTS.off_line_target_count_min,
        _DEFAULTS.off_line_target_count_max,
    )
    max_off = min(int(off_max), len(off_line_cells))
    min_off = min(int(off_min), max_off)
    explicit_off = params.get("off_line_target_count")
    if explicit_off is not None:
        off_count = int(explicit_off)
        if off_count < 0 or off_count > len(off_line_cells):
            raise ValueError("off_line_target_count is outside feasible support")
    else:
        off_count = int(rng.randint(int(min_off), int(max_off))) if max_off > 0 else 0
    rng.shuffle(off_line_cells)
    off_line_target_cells = tuple(sorted(off_line_cells[: int(off_count)]))

    target_cells = set(counted_cells) | set(off_line_target_cells)
    distractor_support = tuple(str(value) for value in support if str(value) != str(target_shape_id))
    rows: List[Tuple[str, ...]] = []
    for row in range(int(grid_rows)):
        row_shapes: List[str] = []
        for col in range(int(grid_cols)):
            if (int(row), int(col)) in target_cells:
                row_shapes.append(str(target_shape_id))
            else:
                row_shapes.append(str(rng.choice(distractor_support)))
        rows.append(tuple(row_shapes))

    realized_count = sum(
        1
        for row, col in line_cells
        if rows[int(row)][int(col)] == str(target_shape_id)
    )
    if int(realized_count) != int(target_count):
        raise RuntimeError("constructed grid does not realize requested row/column target count")
    return tuple(rows), tuple(counted_cells), tuple(off_line_target_cells)


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
    count_min, count_max = _int_bounds(params, "target_count_min", "target_count_max", _DEFAULTS.target_count_min, _DEFAULTS.target_count_max)
    answer_support = tuple(range(int(count_min), int(count_max) + 1))
    explicit_count = params.get("target_count", params.get("answer"))
    if explicit_count is not None:
        target_count = int(explicit_count)
        if int(target_count) not in set(answer_support):
            raise ValueError("explicit target_count is outside configured support")
        answer_probabilities = uniform_probability_map(answer_support, selected=int(target_count))
    else:
        target_count = int(rng.choice(answer_support))
        answer_probabilities = uniform_probability_map(answer_support)

    shape_support = _shape_support(params)
    target_shape_id, shape_probabilities = _resolve_target_shape(rng, params=params, support=shape_support)
    grid_rows, grid_cols, grid_size_probabilities = _choose_grid_size(
        rng,
        params=params,
        query_id=str(query_id),
        target_count=int(target_count),
    )
    queried_index, line_index_probabilities = _choose_line_index(
        rng,
        params=params,
        query_id=str(query_id),
        grid_rows=int(grid_rows),
        grid_cols=int(grid_cols),
    )
    shape_ids_by_cell, counted_cells, off_line_target_cells = _construct_grid_shapes(
        rng,
        support=shape_support,
        target_shape_id=str(target_shape_id),
        query_id=str(query_id),
        target_count=int(target_count),
        grid_rows=int(grid_rows),
        grid_cols=int(grid_cols),
        queried_index=int(queried_index),
        params=params,
    )
    fill_style_support = _fill_style_support(params)
    fill_style_probabilities = _fill_style_probability_map(params, fill_style_support)
    return _SampleSpec(
        query_id=str(query_id),
        target_shape_id=str(target_shape_id),
        target_shape_name=procedural_named_icon_display_name(str(target_shape_id)),
        target_count=int(target_count),
        grid_rows=int(grid_rows),
        grid_cols=int(grid_cols),
        queried_axis="row" if str(query_id) == "row_shape_count" else "column",
        queried_index=int(queried_index),
        shape_ids_by_cell=tuple(tuple(str(value) for value in row) for row in shape_ids_by_cell),
        counted_cells=tuple((int(row), int(col)) for row, col in counted_cells),
        off_line_target_cells=tuple((int(row), int(col)) for row, col in off_line_target_cells),
        query_probabilities=dict(query_probabilities),
        answer_probabilities=dict(answer_probabilities),
        grid_size_probabilities=dict(grid_size_probabilities),
        line_index_probabilities=dict(line_index_probabilities),
        shape_probabilities=dict(shape_probabilities),
        fill_style_support=tuple(fill_style_support),
        fill_style_probabilities=dict(fill_style_probabilities),
    )


def _render_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(key, group_default(_RENDER_DEFAULTS, key, fallback)))


def _render_rgb(params: Mapping[str, Any], key: str, fallback: Sequence[int]) -> Tuple[int, int, int]:
    raw = params.get(key, group_default(_RENDER_DEFAULTS, key, tuple(fallback)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or len(raw) < 3:
        raw = tuple(fallback)
    return tuple(int(value) for value in raw[:3])


def _previous_text_legibility_records(render_params: Mapping[str, Any]) -> List[Dict[str, Any]]:
    previous_legibility = render_params.get("text_legibility")
    if not isinstance(previous_legibility, Mapping) or not isinstance(previous_legibility.get("records"), list):
        return []
    return [dict(record) for record in previous_legibility["records"] if isinstance(record, Mapping)]


def _resolve_named_grid_rgb(
    *,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    key: str,
    fallback: Sequence[int],
    instance_seed: int,
) -> Tuple[int, int, int]:
    return resolve_icon_rgb_param(
        params=params,
        render_defaults=render_defaults,
        key=str(key),
        fallback=tuple(int(value) for value in fallback),
        instance_seed=int(instance_seed),
    )


def _resolve_named_grid_render_params(
    *,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    fallback_defaults: _TaskDefaults,
    instance_seed: int,
) -> Dict[str, Any]:
    """Resolve shared named-grid render params and readable axis-label text."""

    render_params = resolve_icon_render_params(
        params=params,
        render_defaults=render_defaults,
        fallback_defaults=fallback_defaults,
        instance_seed=int(instance_seed),
    )
    for key in (
        "row_label_band_width_px",
        "column_label_band_height_px",
        "grid_label_gap_px",
        "grid_cell_max_size_px",
        "grid_cell_padding_px",
        "grid_line_width_px",
        "grid_border_width_px",
        "axis_label_font_size_px",
    ):
        render_params[key] = int(
            params.get(
                key,
                group_default(render_defaults, key, getattr(fallback_defaults, key)),
            )
        )
    for key in ("grid_line_rgb", "cell_fill_rgb", "alternate_cell_fill_rgb", "axis_label_rgb"):
        render_params[key] = _resolve_named_grid_rgb(
            params=params,
            render_defaults=render_defaults,
            key=str(key),
            fallback=getattr(fallback_defaults, str(key)),
            instance_seed=int(instance_seed),
        )

    axis_label_style = resolve_readable_text_style(
        instance_seed=int(instance_seed),
        namespace="icons.named_grid_axis_number_text",
        role="named_grid_axis_number_text",
        surface_rgbs=(
            tuple(int(value) for value in render_params["panel_fill_rgb"]),
            tuple(int(value) for value in render_params["background_color_rgb"]),
        ),
        preferred_rgbs=(tuple(int(value) for value in render_params["axis_label_rgb"]),),
    )
    render_params["axis_label_rgb"] = tuple(int(value) for value in axis_label_style.fill_rgb)
    render_params["axis_label_stroke_rgb"] = tuple(int(value) for value in render_params["panel_fill_rgb"])
    axis_label_record = axis_label_style.metadata()
    axis_label_record["stroke_rgb"] = list(render_params["axis_label_stroke_rgb"])
    render_params["text_legibility"] = text_legibility_summary_from_records(
        [*_previous_text_legibility_records(render_params), axis_label_record]
    )
    return render_params


def _named_grid_style_trace(render_params: Mapping[str, Any]) -> Dict[str, Any]:
    """Return render-style metadata shared by named-grid tasks."""

    return {
        "row_label_band_width_px": int(render_params["row_label_band_width_px"]),
        "column_label_band_height_px": int(render_params["column_label_band_height_px"]),
        "grid_label_gap_px": int(render_params["grid_label_gap_px"]),
        "grid_cell_max_size_px": int(render_params["grid_cell_max_size_px"]),
        "grid_cell_padding_px": int(render_params["grid_cell_padding_px"]),
        "grid_line_width_px": int(render_params["grid_line_width_px"]),
        "grid_border_width_px": int(render_params["grid_border_width_px"]),
        "axis_label_font_size_px": int(render_params["axis_label_font_size_px"]),
        "grid_line_rgb": [int(value) for value in render_params["grid_line_rgb"]],
        "cell_fill_rgb": [int(value) for value in render_params["cell_fill_rgb"]],
        "alternate_cell_fill_rgb": [int(value) for value in render_params["alternate_cell_fill_rgb"]],
        "axis_label_rgb": [int(value) for value in render_params["axis_label_rgb"]],
        "axis_label_stroke_rgb": [int(value) for value in render_params["axis_label_stroke_rgb"]],
    }


def _resolve_grid_bboxes(
    *,
    content_bbox: BBox,
    rows: int,
    cols: int,
    row_label_band_width_px: int,
    column_label_band_height_px: int,
    grid_label_gap_px: int,
    grid_cell_max_size_px: int,
) -> Tuple[BBox, Tuple[Tuple[BBox, ...], ...], int]:
    x0, y0, x1, y1 = tuple(int(value) for value in content_bbox)
    grid_area_x0 = int(x0 + int(row_label_band_width_px) + int(grid_label_gap_px))
    grid_area_y0 = int(y0 + int(column_label_band_height_px) + int(grid_label_gap_px))
    available_w = max(1, int(x1 - grid_area_x0))
    available_h = max(1, int(y1 - grid_area_y0))
    cell_size = min(int(grid_cell_max_size_px), int(available_w // max(1, int(cols))), int(available_h // max(1, int(rows))))
    if int(cell_size) < 42:
        raise ValueError("named-grid content area is too small for clear cells")
    grid_w = int(cell_size) * int(cols)
    grid_h = int(cell_size) * int(rows)
    gx0 = int(grid_area_x0 + max(0, (available_w - grid_w) // 2))
    gy0 = int(grid_area_y0 + max(0, (available_h - grid_h) // 2))
    grid_bbox = (int(gx0), int(gy0), int(gx0 + grid_w), int(gy0 + grid_h))
    cell_rows: List[Tuple[BBox, ...]] = []
    for row in range(int(rows)):
        row_boxes: List[BBox] = []
        for col in range(int(cols)):
            cx0 = int(gx0 + int(col) * int(cell_size))
            cy0 = int(gy0 + int(row) * int(cell_size))
            row_boxes.append((int(cx0), int(cy0), int(cx0 + cell_size), int(cy0 + cell_size)))
        cell_rows.append(tuple(row_boxes))
    return tuple(int(value) for value in grid_bbox), tuple(cell_rows), int(cell_size)


def _render_scene(
    *,
    sample: _SampleSpec,
    instance_seed: int,
    render_params: Mapping[str, Any],
    params: Mapping[str, Any],
    rng,
    task_id: str = TASK_ID,
) -> _ScenePayload:
    layout = resolve_single_panel_layout(
        canvas_width=int(render_params["canvas_width"]),
        canvas_height=int(render_params["canvas_height"]),
        outer_margin_px=int(render_params["outer_margin_px"]),
        panel_padding_px=int(render_params["panel_padding_px"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
    )
    image = Image.new("RGBA", (int(layout.canvas_width), int(layout.canvas_height)))
    draw_single_panel(
        image=image,
        layout=layout,
        background_rgb=tuple(int(value) for value in render_params["background_color_rgb"]),
        panel_fill_rgb=tuple(int(value) for value in render_params["panel_fill_rgb"]),
        panel_border_rgb=tuple(int(value) for value in render_params["panel_border_rgb"]),
        title_color_rgb=tuple(int(value) for value in render_params["header_text_rgb"]),
        corner_radius_px=int(render_params["panel_corner_radius_px"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
        scene_title="Grid",
        icon_canvas_style=render_params.get("_icon_canvas_style_object"),
    )
    row_label_band_width_px = int(render_params.get("row_label_band_width_px", _render_int(params, "row_label_band_width_px", _DEFAULTS.row_label_band_width_px)))
    column_label_band_height_px = int(render_params.get("column_label_band_height_px", _render_int(params, "column_label_band_height_px", _DEFAULTS.column_label_band_height_px)))
    grid_label_gap_px = int(render_params.get("grid_label_gap_px", _render_int(params, "grid_label_gap_px", _DEFAULTS.grid_label_gap_px)))
    grid_cell_max_size_px = int(render_params.get("grid_cell_max_size_px", _render_int(params, "grid_cell_max_size_px", _DEFAULTS.grid_cell_max_size_px)))
    grid_cell_padding_px = int(render_params.get("grid_cell_padding_px", _render_int(params, "grid_cell_padding_px", _DEFAULTS.grid_cell_padding_px)))
    grid_line_width_px = int(render_params.get("grid_line_width_px", _render_int(params, "grid_line_width_px", _DEFAULTS.grid_line_width_px)))
    grid_border_width_px = int(render_params.get("grid_border_width_px", _render_int(params, "grid_border_width_px", _DEFAULTS.grid_border_width_px)))
    axis_label_font_size_px = int(render_params.get("axis_label_font_size_px", _render_int(params, "axis_label_font_size_px", _DEFAULTS.axis_label_font_size_px)))
    grid_line_rgb = tuple(int(value) for value in render_params.get("grid_line_rgb", _render_rgb(params, "grid_line_rgb", _DEFAULTS.grid_line_rgb)))
    cell_fill_rgb = tuple(int(value) for value in render_params.get("cell_fill_rgb", _render_rgb(params, "cell_fill_rgb", _DEFAULTS.cell_fill_rgb)))
    alternate_cell_fill_rgb = tuple(int(value) for value in render_params.get("alternate_cell_fill_rgb", _render_rgb(params, "alternate_cell_fill_rgb", _DEFAULTS.alternate_cell_fill_rgb)))
    axis_label_rgb = tuple(int(value) for value in render_params.get("axis_label_rgb", _render_rgb(params, "axis_label_rgb", _DEFAULTS.axis_label_rgb)))
    axis_label_stroke_rgb = tuple(int(value) for value in render_params.get("axis_label_stroke_rgb", render_params["panel_fill_rgb"]))

    grid_bbox, cell_bboxes, cell_size_px = _resolve_grid_bboxes(
        content_bbox=tuple(int(value) for value in layout.scene_content_xyxy),
        rows=int(sample.grid_rows),
        cols=int(sample.grid_cols),
        row_label_band_width_px=int(row_label_band_width_px),
        column_label_band_height_px=int(column_label_band_height_px),
        grid_label_gap_px=int(grid_label_gap_px),
        grid_cell_max_size_px=int(grid_cell_max_size_px),
    )

    draw = ImageDraw.Draw(image)
    axis_font = load_font(int(axis_label_font_size_px), bold=True)
    for col in range(int(sample.grid_cols)):
        cell_bbox = cell_bboxes[0][int(col)]
        draw_text_centered(
            draw,
            text=str(int(col) + 1),
            center=(0.5 * float(cell_bbox[0] + cell_bbox[2]), float(grid_bbox[1] - (0.5 * column_label_band_height_px))),
            font=axis_font,
            fill=tuple(int(value) for value in axis_label_rgb),
            stroke_fill=tuple(int(value) for value in axis_label_stroke_rgb),
            stroke_width=2,
        )
    for row in range(int(sample.grid_rows)):
        cell_bbox = cell_bboxes[int(row)][0]
        draw_text_centered(
            draw,
            text=str(int(row) + 1),
            center=(float(grid_bbox[0] - (0.5 * row_label_band_width_px)), 0.5 * float(cell_bbox[1] + cell_bbox[3])),
            font=axis_font,
            fill=tuple(int(value) for value in axis_label_rgb),
            stroke_fill=tuple(int(value) for value in axis_label_stroke_rgb),
            stroke_width=2,
        )

    for row in range(int(sample.grid_rows)):
        for col in range(int(sample.grid_cols)):
            cell_bbox = cell_bboxes[int(row)][int(col)]
            fill = alternate_cell_fill_rgb if (int(row) + int(col)) % 2 else cell_fill_rgb
            draw.rectangle(
                cell_bbox,
                fill=tuple(int(value) for value in fill),
                outline=tuple(int(value) for value in grid_line_rgb),
                width=max(1, int(grid_line_width_px)),
            )
    draw.rectangle(
        grid_bbox,
        outline=tuple(int(value) for value in grid_line_rgb),
        width=max(1, int(grid_border_width_px)),
    )

    palette_size = int(rng.randint(int(render_params["palette_size_min"]), int(render_params["palette_size_max"])))
    palette = sample_icon_palette(
        rng,
        palette_size=int(palette_size),
        channel_min=int(render_params["color_channel_min"]),
        channel_max=int(render_params["color_channel_max"]),
        anchor_colors=(
            tuple(int(value) for value in render_params["background_color_rgb"]),
            tuple(int(value) for value in render_params["panel_fill_rgb"]),
            tuple(int(value) for value in render_params["panel_border_rgb"]),
            tuple(int(value) for value in render_params["header_text_rgb"]),
        ),
        min_color_distance=float(render_params["min_color_distance"]),
        distance_space=str(render_params["color_distance_space"]),
    )
    min_icon_size = max(12, int(render_params["scene_icon_size_min_px"]))
    max_icon_size = max(min_icon_size, min(int(render_params["scene_icon_size_max_px"]), int(cell_size_px) - (2 * int(grid_cell_padding_px))))
    if max_icon_size < min_icon_size:
        min_icon_size = max_icon_size
    counted_set = set((int(row), int(col)) for row, col in sample.counted_cells)
    icons: List[_RenderedGridIcon] = []
    for row in range(int(sample.grid_rows)):
        for col in range(int(sample.grid_cols)):
            shape_id = str(sample.shape_ids_by_cell[int(row)][int(col)])
            fill_style = sample_procedural_named_icon_fill_style(
                rng,
                support=sample.fill_style_support,
                probabilities=sample.fill_style_probabilities,
            )
            tint_rgb = tuple(int(value) for value in rng.choice(palette))
            nominal_size_px = int(rng.randint(int(min_icon_size), int(max_icon_size)))
            noise_edits, noise_seed = sample_icon_instance_noise(
                instance_seed=int(instance_seed),
                namespace=f"{task_id}:r{int(row)}c{int(col)}",
                render_params=render_params,
            )
            sprite = render_procedural_named_icon_rgba(
                shape_id=str(shape_id),
                size_px=int(nominal_size_px),
                tint_rgb=tint_rgb,
                fill_style=str(fill_style),
                rotation_degrees=0,
                noise_edits=tuple(noise_edits),
                noise_seed=int(noise_seed),
            )
            cell_bbox = cell_bboxes[int(row)][int(col)]
            cx = 0.5 * float(cell_bbox[0] + cell_bbox[2])
            cy = 0.5 * float(cell_bbox[1] + cell_bbox[3])
            x0 = int(round(cx - (0.5 * float(sprite.size[0]))))
            y0 = int(round(cy - (0.5 * float(sprite.size[1]))))
            bbox = (int(x0), int(y0), int(x0 + sprite.size[0]), int(y0 + sprite.size[1]))
            image.alpha_composite(sprite, (int(x0), int(y0)))
            instance_id = f"grid_r{int(row) + 1}_c{int(col) + 1}"
            icons.append(
                _RenderedGridIcon(
                    instance_id=str(instance_id),
                    row_index=int(row),
                    col_index=int(col),
                    row_number=int(row) + 1,
                    column_number=int(col) + 1,
                    shape_id=str(shape_id),
                    shape_name=procedural_named_icon_display_name(str(shape_id)),
                    bbox_xyxy=tuple(int(value) for value in bbox),
                    cell_bbox_xyxy=tuple(int(value) for value in cell_bbox),
                    nominal_size_px=int(nominal_size_px),
                    tint_rgb=tuple(int(value) for value in tint_rgb),
                    fill_style=str(fill_style),
                    noise_edits=tuple(serialize_icon_noise_edits(noise_edits)),
                    noise_seed=int(noise_seed),
                    is_target_shape=str(shape_id) == str(sample.target_shape_id),
                    is_counted=(int(row), int(col)) in counted_set,
                )
            )
    return _ScenePayload(
        image=image.convert("RGB"),
        panel_geometry=single_panel_geometry_to_trace(layout),
        grid_bbox_xyxy=tuple(int(value) for value in grid_bbox),
        cell_bboxes_xyxy=tuple(tuple(tuple(int(value) for value in box) for box in row) for row in cell_bboxes),
        icons=tuple(icons),
        sampled_palette_rgb=tuple(tuple(int(channel) for channel in color) for color in palette),
        cell_size_px=int(cell_size_px),
    )


def _serialize_icon(icon: _RenderedGridIcon) -> Dict[str, Any]:
    return {
        "entity_kind": "named_icon",
        "instance_id": str(icon.instance_id),
        "row_index": int(icon.row_index),
        "col_index": int(icon.col_index),
        "row_number": int(icon.row_number),
        "column_number": int(icon.column_number),
        "shape_id": str(icon.shape_id),
        "shape_name": str(icon.shape_name),
        "bbox_xyxy": [int(value) for value in icon.bbox_xyxy],
        "cell_bbox_xyxy": [int(value) for value in icon.cell_bbox_xyxy],
        "nominal_size_px": int(icon.nominal_size_px),
        "tint_rgb": [int(value) for value in icon.tint_rgb],
        "fill_style": str(icon.fill_style),
        "noise_edits": [dict(value) for value in icon.noise_edits],
        "noise_seed": None if icon.noise_seed is None else int(icon.noise_seed),
        "is_target_shape": bool(icon.is_target_shape),
        "is_counted": bool(icon.is_counted),
    }


def _complexity(sample: _SampleSpec, *, scene: _ScenePayload, render_params: Mapping[str, Any]) -> TaskComplexity:
    cell_count = int(sample.grid_rows) * int(sample.grid_cols)
    visual_scan = (float(cell_count) - 12.0) / max(1.0, 25.0 - 12.0)
    queried_capacity = int(sample.grid_cols) if str(sample.queried_axis) == "row" else int(sample.grid_rows)
    density = float(sample.target_count) / float(max(1, queried_capacity))
    ambiguity = min(1.0, (float(len(sample.off_line_target_cells)) / 4.0) * 0.65 + (1.0 - abs((2.0 * density) - 1.0)) * 0.35)
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
class IconsCountingNamedGridRowColumnShapeCountTask:
    """Count named icons in a prompt-addressed grid row or column."""

    task_id = TASK_ID
    domain = "icons"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        render_params = _resolve_named_grid_render_params(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
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
                    sample=sample,
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
        if len(annotation_bboxes) != int(sample.target_count):
            raise RuntimeError("rendered named-grid annotation count does not match answer")
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
                "question_text_row_shape_count",
                "question_text_column_shape_count",
                "annotation_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        question_key = f"question_text_{sample.query_id}"
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(prompt_defaults[question_key]).format(
                    target_shape_name=str(sample.target_shape_name),
                    line_number=int(sample.queried_index) + 1,
                ),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]).format(
                    target_shape_name=str(sample.target_shape_name),
                    line_kind=str(sample.queried_axis),
                    line_number=int(sample.queried_index) + 1,
                ),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        serialized_icons = [_serialize_icon(icon) for icon in scene.icons]
        counted_instance_ids = tuple(str(icon.instance_id) for icon in counted_icons)
        shape_counts = dict(Counter(str(icon.shape_id) for icon in scene.icons))
        line_cells = (
            tuple((int(sample.queried_index), col) for col in range(int(sample.grid_cols)))
            if str(sample.queried_axis) == "row"
            else tuple((row, int(sample.queried_index)) for row in range(int(sample.grid_rows)))
        )
        line_shape_counts = Counter(str(sample.shape_ids_by_cell[int(row)][int(col)]) for row, col in line_cells)
        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_named_grid_row_column_shape_count",
                "scene_id": SCENE_ID,
                "entities": list(serialized_icons),
                "relations": {
                    "counting_rule": "shape_id_in_prompt_addressed_grid_line",
                    "target_shape_id": str(sample.target_shape_id),
                    "target_shape_name": str(sample.target_shape_name),
                    "queried_axis": str(sample.queried_axis),
                    "queried_index": int(sample.queried_index),
                    "queried_number": int(sample.queried_index) + 1,
                    "grid_rows": int(sample.grid_rows),
                    "grid_cols": int(sample.grid_cols),
                    "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
                    "queried_line_shape_counts": {str(key): int(value) for key, value in line_shape_counts.items()},
                    "counted_cells": [[int(row), int(col)] for row, col in sample.counted_cells],
                    "off_line_target_cells": [[int(row), int(col)] for row, col in sample.off_line_target_cells],
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
                    "target_count": int(sample.target_count),
                    "grid_rows": int(sample.grid_rows),
                    "grid_cols": int(sample.grid_cols),
                    "queried_axis": str(sample.queried_axis),
                    "queried_index": int(sample.queried_index),
                    "queried_number": int(sample.queried_index) + 1,
                    "query_id_probabilities": dict(sample.query_probabilities),
                    "answer_probabilities": dict(sample.answer_probabilities),
                    "grid_size_probabilities": dict(sample.grid_size_probabilities),
                    "line_index_probabilities": dict(sample.line_index_probabilities),
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
                "counted_instance_ids": list(counted_instance_ids),
            },
            "execution_trace": {
                "scene_variant": "single_panel_named_grid",
                "query_id": str(sample.query_id),
                "question_format": "count_named_shape_in_grid_row_or_column",
                "target_shape_id": str(sample.target_shape_id),
                "target_shape_name": str(sample.target_shape_name),
                "answer": int(sample.target_count),
                "grid_rows": int(sample.grid_rows),
                "grid_cols": int(sample.grid_cols),
                "queried_axis": str(sample.queried_axis),
                "queried_index": int(sample.queried_index),
                "queried_number": int(sample.queried_index) + 1,
                "shape_ids_by_cell": [list(row) for row in sample.shape_ids_by_cell],
                "counted_cells": [[int(row), int(col)] for row, col in sample.counted_cells],
                "off_line_target_cells": [[int(row), int(col)] for row, col in sample.off_line_target_cells],
                "counted_instance_ids": list(counted_instance_ids),
                "queried_line_shape_counts": {str(key): int(value) for key, value in line_shape_counts.items()},
            },
            "witness_symbolic": {
                "query_id": str(sample.query_id),
                "target_shape_id": str(sample.target_shape_id),
                "target_shape_name": str(sample.target_shape_name),
                "answer": int(sample.target_count),
                "counted_cells": [[int(row), int(col)] for row, col in sample.counted_cells],
                "counted_instance_ids": list(counted_instance_ids),
            },
            "projected_annotation": dict(annotation_payload["projected_annotation"]),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(sample.target_count)),
            annotation_gt=TypedValue(type=str(annotation_payload["annotation_type"]), value=list(annotation_payload["annotation_value"])),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_complexity(sample, scene=scene, render_params=render_params),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sample.query_id),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
        )


__all__ = ["IconsCountingNamedGridRowColumnShapeCountTask"]
