"""Identify the numbered cell that breaks a 2D icon-size grid rule."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.taxonomy import resolve_task_taxonomy
from ....core.types import TypedValue
from ...base import TaskOutput
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.annotation import bbox_set_annotation
from ..shared.icon_assets import render_icon_rgba, resolve_icon_pool
from ..shared.icon_noise import serialize_icon_noise_edits
from ..shared.icon_scene import (
    IconInstanceSpec,
    RenderedIconInstance,
    centered_paste_bbox,
    serialize_rendered_icon_instance,
    single_panel_geometry_to_trace,
    sort_bboxes_reading_order,
)
from ..shared.icon_single_panel_labeled_grid_scene import (
    prepare_single_panel_labeled_grid_scene,
    resolve_single_panel_labeled_grid_canvas_size,
)
from ..shared.icon_style import sample_single_icon_tint
from ..shared.icon_task_rendering import (
    icon_render_style_trace,
    resolve_icon_cell_render_params,
    sample_icon_instance_noise,
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for icon 2D size-pattern violation grids."""

    grid_rows: int = 3
    grid_cols: int = 3
    answer_index_min: int = 1
    answer_index_max: int = 9
    canvas_width: int = 672
    canvas_height: int = 672
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    scene_icon_size_min_px: int = 34
    scene_icon_size_max_px: int = 82
    cell_box_width_min_px: int = 116
    cell_box_width_max_px: int = 152
    cell_box_height_min_px: int = 116
    cell_box_height_max_px: int = 152
    scene_max_overlap_fraction: float = 0.20
    scene_placement_max_attempts: int = 80
    scene_size_shrink_rounds: int = ICON_SHARED_DEFAULTS.scene_size_shrink_rounds
    scene_size_shrink_factor: float = ICON_SHARED_DEFAULTS.scene_size_shrink_factor
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    pool_manifest: str = "all_icons.txt"
    size_levels: Tuple[int, ...] = (1, 2, 3, 4, 5)
    base_level_candidates: Tuple[int, ...] = (1, 2, 3, 4, 5)
    row_step_candidates: Tuple[int, ...] = (-1, 0, 1)
    col_step_candidates: Tuple[int, ...] = (-1, 0, 1)
    size_level_gap_px: int = 8
    min_violation_level_delta: int = 1
    shared_rotation_candidates_degrees: Tuple[int, ...] = (0, 90, 180, 270)
    palette_size_min: int = 1
    palette_size_max: int = 1
    color_channel_min: int = 24
    color_channel_max: int = 220
    min_color_distance: float = 40.0
    color_distance_space: str = "lab"
    background_color_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.background_color_rgb
    panel_fill_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_fill_rgb
    panel_border_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_border_rgb
    header_text_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.header_text_rgb
    cell_padding_px: int = 10
    cell_icon_padding_px: int = 10
    cell_corner_radius_px: int = 12
    cell_border_rgb: Tuple[int, int, int] = (218, 223, 233)
    cell_label_font_size_px: int = 22
    cell_label_color_rgb: Tuple[int, int, int] = (52, 60, 77)
    scene_content_side_padding_px: int = 10
    scene_content_bottom_padding_px: int = 10
    scene_content_top_offset_px: int = 40
    icon_noise_edit_types: Tuple[str, ...] = ICON_SHARED_DEFAULTS.icon_noise_edit_types
    icon_noise_edit_count_range: Tuple[int, int] = (0, 1)
    icon_noise_value_ranges: Dict[str, Dict[str, Tuple[float, float]]] = field(
        default_factory=lambda: deepcopy(ICON_SHARED_DEFAULTS.icon_noise_value_ranges)
    )


@dataclass(frozen=True)
class _PatternSpec:
    """One resolved 3x3 size pattern with a unique violating cell."""

    grid_rows: int
    grid_cols: int
    answer_index: int
    violation_cell_index: int
    size_levels: Tuple[int, ...]
    base_size_level: int
    row_step_levels: int
    col_step_levels: int
    violation_size_level: int
    shared_rotation_degrees: int
    expected_grid_size_levels: Tuple[int, ...]
    observed_grid_size_levels: Tuple[int, ...]
    plausible_rule_count: int
    total_rule_support: int
    answer_index_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready payload for one icon grid size-pattern violation instance."""

    grid_rows: int
    grid_cols: int
    answer_index: int
    violation_cell_index: int
    size_levels: Tuple[int, ...]
    size_level_nominal_sizes_px: Dict[int, int]
    base_size_level: int
    row_step_levels: int
    col_step_levels: int
    violation_size_level: int
    shared_rotation_degrees: int
    expected_grid_size_levels: Tuple[int, ...]
    observed_grid_size_levels: Tuple[int, ...]
    expected_grid_nominal_sizes_px: Tuple[int, ...]
    observed_grid_nominal_sizes_px: Tuple[int, ...]
    plausible_rule_count: int
    total_rule_support: int
    pattern_icon_id: str
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    cell_box_width_px: int
    cell_box_height_px: int
    panel_geometry: Dict[str, Any]
    scene_cells: Tuple[Dict[str, Any], ...]
    scene_icon_instances: Tuple[Dict[str, Any], ...]
    violating_cell_bbox: Tuple[int, int, int, int]


_DEFAULTS = _TaskDefaults()
TASK_ID = "task_icons__pattern_grid__attribute_pattern_violation_index"
QUERY_ID = "grid_size_violation"

_TASK_GROUP_DEFAULTS = get_scene_defaults("icons", "pattern")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_GEN_DEFAULTS = {
    **_GEN_DEFAULTS,
    **dict(_GEN_DEFAULTS.get("variant_generation_params", {}).get(QUERY_ID, {})),
}
_RENDER_DEFAULTS = {
    **_RENDER_DEFAULTS,
    **dict(_RENDER_DEFAULTS.get("variant_render_params", {}).get(QUERY_ID, {})),
}


def _int_sequence_param(
    params: Mapping[str, Any],
    *,
    key: str,
    fallback: Sequence[int],
    error_label: str,
) -> Tuple[int, ...]:
    """Resolve one integer sequence parameter from config/task params."""

    raw = params.get(key, group_default(_GEN_DEFAULTS, key, list(fallback)))
    if not isinstance(raw, (list, tuple)):
        raise ValueError(f"{error_label} must be a sequence")
    values = tuple(int(value) for value in raw)
    if not values:
        raise ValueError(f"{error_label} must contain at least one value")
    return values


def _size_levels(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Resolve supported symbolic size levels."""

    levels = _int_sequence_param(
        params,
        key="size_levels",
        fallback=_DEFAULTS.size_levels,
        error_label="size_levels",
    )
    deduped = tuple(dict.fromkeys(int(level) for level in levels))
    if len(deduped) < 3:
        raise ValueError("size_levels must contain at least three distinct levels")
    return deduped


def _base_level_candidates(params: Mapping[str, Any], *, size_levels: Sequence[int]) -> Tuple[int, ...]:
    """Resolve supported base size levels."""

    raw = params.get("base_level_candidates")
    if raw is None:
        fallback = tuple(int(level) for level in size_levels)
    else:
        fallback = _DEFAULTS.base_level_candidates
    values = _int_sequence_param(
        params,
        key="base_level_candidates",
        fallback=fallback,
        error_label="base_level_candidates",
    )
    allowed = {int(level) for level in size_levels}
    filtered = tuple(int(value) for value in values if int(value) in allowed)
    if not filtered:
        raise ValueError("base_level_candidates must overlap size_levels")
    return filtered


def _row_step_candidates(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Resolve supported row-wise size-level steps."""

    return _int_sequence_param(
        params,
        key="row_step_candidates",
        fallback=_DEFAULTS.row_step_candidates,
        error_label="row_step_candidates",
    )


def _col_step_candidates(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Resolve supported column-wise size-level steps."""

    return _int_sequence_param(
        params,
        key="col_step_candidates",
        fallback=_DEFAULTS.col_step_candidates,
        error_label="col_step_candidates",
    )


def _shared_rotation_candidates(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Resolve supported constant rotations for all grid icons."""

    raw = params.get(
        "shared_rotation_candidates_degrees",
        group_default(
            _GEN_DEFAULTS,
            "shared_rotation_candidates_degrees",
            list(_DEFAULTS.shared_rotation_candidates_degrees),
        ),
    )
    if not isinstance(raw, (list, tuple)):
        raise ValueError("shared_rotation_candidates_degrees must be a sequence")
    values = tuple(int(value) % 360 for value in raw)
    if not values:
        raise ValueError("shared_rotation_candidates_degrees must contain at least one rotation")
    return values


def _grid_size_pattern(
    *,
    base_size_level: int,
    row_step_levels: int,
    col_step_levels: int,
    grid_rows: int,
    grid_cols: int,
) -> Tuple[int, ...]:
    """Return one row-major symbolic size-level grid."""

    levels: List[int] = []
    for row in range(int(grid_rows)):
        for col in range(int(grid_cols)):
            levels.append(
                int(
                    int(base_size_level)
                    + (int(row) * int(row_step_levels))
                    + (int(col) * int(col_step_levels))
                )
            )
    return tuple(levels)


def _size_grid_violation_explanations(
    observed_size_levels: Sequence[int],
    *,
    grid_rows: int,
    grid_cols: int,
    size_levels: Sequence[int],
    base_level_candidates: Sequence[int],
    row_step_candidates: Sequence[int],
    col_step_candidates: Sequence[int],
) -> Tuple[bool, set[int], Dict[int, int]]:
    """Return whether the grid is already valid and all plausible violating indices."""

    exact_match = False
    plausible_indices: set[int] = set()
    rule_counts: Counter[int] = Counter()
    observed = tuple(int(value) for value in observed_size_levels)
    allowed_levels = {int(level) for level in size_levels}
    for base_size_level in base_level_candidates:
        for row_step_levels in row_step_candidates:
            for col_step_levels in col_step_candidates:
                if int(row_step_levels) == 0 and int(col_step_levels) == 0:
                    continue
                expected = _grid_size_pattern(
                    base_size_level=int(base_size_level),
                    row_step_levels=int(row_step_levels),
                    col_step_levels=int(col_step_levels),
                    grid_rows=int(grid_rows),
                    grid_cols=int(grid_cols),
                )
                if any(int(level) not in allowed_levels for level in expected):
                    continue
                mismatches = [
                    int(index)
                    for index, (observed_level, expected_level) in enumerate(zip(observed, expected))
                    if int(observed_level) != int(expected_level)
                ]
                if not mismatches:
                    exact_match = True
                elif len(mismatches) == 1:
                    index = int(mismatches[0])
                    plausible_indices.add(index)
                    rule_counts[index] += 1
    return bool(exact_match), plausible_indices, {int(key): int(value) for key, value in rule_counts.items()}


def _resolve_pattern_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _PatternSpec:
    """Resolve one unambiguous 2D size grid with a single violating position."""

    grid_rows = int(params.get("grid_rows", group_default(_GEN_DEFAULTS, "grid_rows", _DEFAULTS.grid_rows)))
    grid_cols = int(params.get("grid_cols", group_default(_GEN_DEFAULTS, "grid_cols", _DEFAULTS.grid_cols)))
    if grid_rows <= 0 or grid_cols <= 0:
        raise ValueError("grid_rows and grid_cols must be positive")
    cell_count = int(grid_rows * grid_cols)
    answer_index_min = int(
        params.get("answer_index_min", group_default(_GEN_DEFAULTS, "answer_index_min", _DEFAULTS.answer_index_min))
    )
    answer_index_max = int(
        params.get("answer_index_max", group_default(_GEN_DEFAULTS, "answer_index_max", _DEFAULTS.answer_index_max))
    )
    if answer_index_min < 1 or answer_index_min > answer_index_max:
        raise ValueError("answer_index_min must be in [1, answer_index_max]")
    if answer_index_max > cell_count:
        raise ValueError("answer_index_max must be <= grid_rows * grid_cols")

    size_levels = _size_levels(params)
    base_level_candidates = _base_level_candidates(params, size_levels=size_levels)
    row_step_candidates = _row_step_candidates(params)
    col_step_candidates = _col_step_candidates(params)
    shared_rotation_candidates = _shared_rotation_candidates(params)
    total_rule_support = int(len(base_level_candidates) * len(row_step_candidates) * len(col_step_candidates))

    answer_support = tuple(range(int(answer_index_min), int(answer_index_max) + 1))
    base_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:pattern_spec",
        )
    )
    explicit_answer_index = params.get("answer_index")
    explicit_violation_cell_index = params.get("violation_cell_index")
    if explicit_answer_index is not None and explicit_violation_cell_index is not None:
        if int(explicit_answer_index) != int(explicit_violation_cell_index) + 1:
            raise ValueError("answer_index must equal violation_cell_index + 1 when both are provided")
    if explicit_answer_index is not None:
        answer_index = int(explicit_answer_index)
    elif explicit_violation_cell_index is not None:
        answer_index = int(explicit_violation_cell_index) + 1
    else:
        answer_index = int(answer_support[int(base_index % len(answer_support))])
    if answer_index not in answer_support:
        raise ValueError("answer_index is outside configured support")
    violation_cell_index = int(answer_index - 1)

    explicit_base_size_level = params.get("base_size_level")
    explicit_row_step = params.get("row_step_levels")
    explicit_col_step = params.get("col_step_levels")
    explicit_violation_size_level = params.get("violation_size_level")
    explicit_shared_rotation = params.get("shared_rotation_degrees")
    min_violation_level_delta = int(
        params.get(
            "min_violation_level_delta",
            group_default(_GEN_DEFAULTS, "min_violation_level_delta", _DEFAULTS.min_violation_level_delta),
        )
    )
    if int(min_violation_level_delta) < 1:
        raise ValueError("min_violation_level_delta must be >= 1")

    allowed_levels = {int(level) for level in size_levels}
    feasible_patterns: List[Tuple[int, int, int, int, Tuple[int, ...], Tuple[int, ...], int]] = []
    for base_size_level in base_level_candidates:
        if explicit_base_size_level is not None and int(base_size_level) != int(explicit_base_size_level):
            continue
        for row_step_levels in row_step_candidates:
            if explicit_row_step is not None and int(row_step_levels) != int(explicit_row_step):
                continue
            for col_step_levels in col_step_candidates:
                if explicit_col_step is not None and int(col_step_levels) != int(explicit_col_step):
                    continue
                if int(row_step_levels) == 0 and int(col_step_levels) == 0:
                    continue
                expected = _grid_size_pattern(
                    base_size_level=int(base_size_level),
                    row_step_levels=int(row_step_levels),
                    col_step_levels=int(col_step_levels),
                    grid_rows=int(grid_rows),
                    grid_cols=int(grid_cols),
                )
                if any(int(level) not in allowed_levels for level in expected):
                    continue
                if len(set(int(value) for value in expected)) < 3:
                    continue
                expected_level = int(expected[violation_cell_index])
                for violation_size_level in size_levels:
                    if explicit_violation_size_level is not None and int(violation_size_level) != int(explicit_violation_size_level):
                        continue
                    if int(violation_size_level) == int(expected_level):
                        continue
                    if abs(int(violation_size_level) - int(expected_level)) < int(min_violation_level_delta):
                        continue
                    observed = list(int(value) for value in expected)
                    observed[int(violation_cell_index)] = int(violation_size_level)
                    exact_match, plausible_indices, plausible_rule_counts = _size_grid_violation_explanations(
                        tuple(observed),
                        grid_rows=int(grid_rows),
                        grid_cols=int(grid_cols),
                        size_levels=size_levels,
                        base_level_candidates=base_level_candidates,
                        row_step_candidates=row_step_candidates,
                        col_step_candidates=col_step_candidates,
                    )
                    if exact_match:
                        continue
                    if plausible_indices != {int(violation_cell_index)}:
                        continue
                    feasible_patterns.append(
                        (
                            int(base_size_level),
                            int(row_step_levels),
                            int(col_step_levels),
                            int(violation_size_level),
                            tuple(int(value) for value in expected),
                            tuple(int(value) for value in observed),
                            int(plausible_rule_counts.get(int(violation_cell_index), 0)),
                        )
                    )
    if not feasible_patterns:
        raise ValueError("no unambiguous 2D size grid is feasible for the requested parameters")

    combo_index = int(base_index // max(1, len(answer_support))) % len(feasible_patterns)
    rotation_index = int(base_index // max(1, len(answer_support) * len(feasible_patterns))) % len(
        shared_rotation_candidates
    )
    (
        base_size_level,
        row_step_levels,
        col_step_levels,
        violation_size_level,
        expected_grid_size_levels,
        observed_grid_size_levels,
        plausible_rule_count,
    ) = feasible_patterns[int(combo_index)]
    if explicit_shared_rotation is not None:
        shared_rotation_degrees = int(explicit_shared_rotation) % 360
    else:
        shared_rotation_degrees = int(shared_rotation_candidates[int(rotation_index)])
    answer_index_probabilities = uniform_probability_map(
        answer_support,
        selected=int(answer_index) if explicit_answer_index is not None or explicit_violation_cell_index is not None else None,
    )
    return _PatternSpec(
        grid_rows=int(grid_rows),
        grid_cols=int(grid_cols),
        answer_index=int(answer_index),
        violation_cell_index=int(violation_cell_index),
        size_levels=tuple(int(level) for level in size_levels),
        base_size_level=int(base_size_level),
        row_step_levels=int(row_step_levels),
        col_step_levels=int(col_step_levels),
        violation_size_level=int(violation_size_level),
        shared_rotation_degrees=int(shared_rotation_degrees),
        expected_grid_size_levels=tuple(int(value) for value in expected_grid_size_levels),
        observed_grid_size_levels=tuple(int(value) for value in observed_grid_size_levels),
        plausible_rule_count=int(plausible_rule_count),
        total_rule_support=int(total_rule_support),
        answer_index_probabilities=dict(answer_index_probabilities),
    )


def _resolve_size_level_nominal_sizes(
    rng,
    *,
    size_levels: Sequence[int],
    content_limit_px: int,
    render_params: Mapping[str, Any],
) -> Dict[int, int]:
    """Map symbolic size levels to nominal icon sizes that fit the sampled cell content."""

    ordered_levels = [int(level) for level in size_levels]
    gap_px = int(render_params["size_level_gap_px"])
    if gap_px <= 0:
        raise ValueError("size_level_gap_px must be positive")
    max_nominal_size = min(int(render_params["scene_icon_size_max_px"]), int(content_limit_px))
    min_nominal_size = int(render_params["scene_icon_size_min_px"])
    required_top_size = int(min_nominal_size + (gap_px * max(0, len(ordered_levels) - 1)))
    if max_nominal_size < required_top_size:
        raise ValueError("sampled cell geometry is too small for the configured size levels")
    top_size = int(rng.randint(int(required_top_size), int(max_nominal_size)))
    return {
        int(level): int(top_size - (gap_px * (len(ordered_levels) - index - 1)))
        for index, level in enumerate(ordered_levels)
    }


def _sample_scene(
    rng,
    *,
    instance_seed: int,
    pattern_spec: _PatternSpec,
    pool_manifest: str,
    render_params: Mapping[str, Any],
) -> Tuple[_ScenePayload, Any]:
    """Sample and render one single-panel numbered 2D size-pattern grid."""

    pool = list(resolve_icon_pool(str(pool_manifest)))
    if not pool:
        raise ValueError("size grid pool resolved no icons")
    pattern_icon_id = str(rng.choice(pool))
    tint_rgb, sampled_palette_rgb = sample_single_icon_tint(
        rng,
        channel_min=int(render_params["color_channel_min"]),
        channel_max=int(render_params["color_channel_max"]),
        anchor_colors=(
            tuple(int(v) for v in render_params["background_color_rgb"]),
            tuple(int(v) for v in render_params["panel_fill_rgb"]),
            tuple(int(v) for v in render_params["panel_border_rgb"]),
            tuple(int(v) for v in render_params["header_text_rgb"]),
        ),
        min_color_distance=float(render_params["min_color_distance"]),
        distance_space=str(render_params["color_distance_space"]),
    )
    cell_box_width_px = int(
        rng.randint(
            int(render_params["cell_box_width_min_px"]),
            int(render_params["cell_box_width_max_px"]),
        )
    )
    cell_box_height_px = int(
        rng.randint(
            int(render_params["cell_box_height_min_px"]),
            int(render_params["cell_box_height_max_px"]),
        )
    )
    canvas_width, canvas_height = resolve_single_panel_labeled_grid_canvas_size(
        rows=int(pattern_spec.grid_rows),
        cols=int(pattern_spec.grid_cols),
        cell_box_width_px=int(cell_box_width_px),
        cell_box_height_px=int(cell_box_height_px),
        render_params=render_params,
    )
    scene_labels = [str(index + 1) for index in range(int(pattern_spec.grid_rows * pattern_spec.grid_cols))]
    prepared = prepare_single_panel_labeled_grid_scene(
        scene_labels=scene_labels,
        grid_rows=int(pattern_spec.grid_rows),
        grid_cols=int(pattern_spec.grid_cols),
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        outer_margin_px=int(render_params["outer_margin_px"]),
        panel_padding_px=int(render_params["panel_padding_px"]),
        panel_corner_radius_px=int(render_params["panel_corner_radius_px"]),
        panel_title_font_size_px=int(render_params["panel_title_font_size_px"]),
        background_rgb=tuple(int(v) for v in render_params["background_color_rgb"]),
        panel_fill_rgb=tuple(int(v) for v in render_params["panel_fill_rgb"]),
        panel_border_rgb=tuple(int(v) for v in render_params["panel_border_rgb"]),
        title_color_rgb=tuple(int(v) for v in render_params["header_text_rgb"]),
        cell_padding_px=int(render_params["cell_padding_px"]),
        cell_border_rgb=tuple(int(v) for v in render_params["cell_border_rgb"]),
        cell_label_color_rgb=tuple(int(v) for v in render_params["cell_label_color_rgb"]),
        cell_label_stroke_rgb=tuple(int(v) for v in render_params["cell_label_stroke_rgb"]),
        cell_label_stroke_width_px=1,
        cell_label_font_size_px=int(render_params["cell_label_font_size_px"]),
        cell_corner_radius_px=int(render_params["cell_corner_radius_px"]),
        scene_content_side_padding_px=int(render_params["scene_content_side_padding_px"]),
        scene_content_bottom_padding_px=int(render_params["scene_content_bottom_padding_px"]),
        scene_content_top_offset_px=int(render_params["scene_content_top_offset_px"]),
        scene_square_cells=False,
        scene_title="Pattern",
        icon_canvas_style=render_params.get("_icon_canvas_style_object"),
    )

    if not prepared.scene_cells:
        raise ValueError("prepared size grid produced no cells")
    first_content_bbox = tuple(int(value) for value in prepared.scene_cells[0].content_bbox_xyxy)
    content_limit_px = min(
        int(first_content_bbox[2]) - int(first_content_bbox[0]),
        int(first_content_bbox[3]) - int(first_content_bbox[1]),
    )
    if content_limit_px <= 0:
        raise ValueError("size grid content geometry is invalid")
    size_level_nominal_sizes_px = _resolve_size_level_nominal_sizes(
        rng,
        size_levels=pattern_spec.size_levels,
        content_limit_px=int(content_limit_px),
        render_params=render_params,
    )

    image = prepared.image.copy()
    scene_cells: List[Dict[str, Any]] = []
    scene_icon_instances: List[Dict[str, Any]] = []
    violating_cell_bbox = None
    observed_grid_nominal_sizes_px: List[int] = []
    expected_grid_nominal_sizes_px: List[int] = []
    for cell_index, (prepared_cell, expected_level, observed_level) in enumerate(
        zip(
            prepared.scene_cells,
            pattern_spec.expected_grid_size_levels,
            pattern_spec.observed_grid_size_levels,
        )
    ):
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{IconsPatternGridSizeViolationTask.task_id}:scene_cell_{int(cell_index)}_icon_0",
            render_params=render_params,
        )
        observed_nominal_size = int(size_level_nominal_sizes_px[int(observed_level)])
        expected_nominal_size = int(size_level_nominal_sizes_px[int(expected_level)])
        icon_spec = IconInstanceSpec(
            icon_id=str(pattern_icon_id),
            rotation_degrees=int(pattern_spec.shared_rotation_degrees),
            tint_rgb=tuple(int(value) for value in tint_rgb),
            noise_edits=tuple(noise_edits),
            noise_seed=int(noise_seed),
        )
        sprite = render_icon_rgba(
            icon_id=str(icon_spec.icon_id),
            size_px=int(observed_nominal_size),
            tint_rgb=tuple(int(value) for value in icon_spec.tint_rgb),
            rotation_degrees=int(icon_spec.rotation_degrees),
            mirror_x=bool(icon_spec.mirror_x),
            noise_edits=tuple(icon_spec.noise_edits),
            noise_seed=icon_spec.noise_seed,
        )
        paste_bbox = centered_paste_bbox(
            sprite_size=sprite.size,
            slot_bbox=tuple(int(value) for value in prepared_cell.content_bbox_xyxy),
            jitter_px=0,
            rng=rng,
        )
        image.alpha_composite(sprite, (int(paste_bbox[0]), int(paste_bbox[1])))
        rendered_instance = RenderedIconInstance(
            instance_id=f"scene_icon_{int(cell_index)}",
            icon_id=str(icon_spec.icon_id),
            panel="scene",
            bbox_xyxy=tuple(int(value) for value in paste_bbox),
            nominal_size_px=int(observed_nominal_size),
            rotation_degrees=int(icon_spec.rotation_degrees) % 360,
            mirror_x=bool(icon_spec.mirror_x),
            tint_rgb=tuple(int(value) for value in icon_spec.tint_rgb),
            noise_edits=serialize_icon_noise_edits(icon_spec.noise_edits),
            noise_seed=None if icon_spec.noise_seed is None else int(icon_spec.noise_seed),
        )
        cell_bbox = tuple(int(value) for value in prepared_cell.cell_bbox_xyxy)
        if int(cell_index) == int(pattern_spec.violation_cell_index):
            violating_cell_bbox = cell_bbox
        expected_grid_nominal_sizes_px.append(int(expected_nominal_size))
        observed_grid_nominal_sizes_px.append(int(observed_nominal_size))
        scene_cells.append(
            {
                "entity_kind": "pattern_cell",
                "panel": "scene",
                "cell_index": int(cell_index),
                "cell_label_text": str(prepared_cell.label),
                "cell_bbox_xyxy": list(cell_bbox),
                "grid_row": int(cell_index // int(pattern_spec.grid_cols)),
                "grid_col": int(cell_index % int(pattern_spec.grid_cols)),
                "is_violation": bool(int(cell_index) == int(pattern_spec.violation_cell_index)),
                "expected_size_level": int(expected_level),
                "observed_size_level": int(observed_level),
                "expected_nominal_size_px": int(expected_nominal_size),
                "observed_nominal_size_px": int(observed_nominal_size),
                "rendered_icon_count": 1,
            }
        )
        scene_icon_instances.append(
            serialize_rendered_icon_instance(
                rendered_instance,
                entity_kind="scene_icon",
                extra_fields={
                    "cell_index": int(cell_index),
                    "cell_label_text": str(prepared_cell.label),
                    "cell_bbox_xyxy": list(cell_bbox),
                },
            )
        )
    if violating_cell_bbox is None:
        raise ValueError("rendered size-pattern scene did not produce the violating cell bbox")

    return _ScenePayload(
        grid_rows=int(pattern_spec.grid_rows),
        grid_cols=int(pattern_spec.grid_cols),
        answer_index=int(pattern_spec.answer_index),
        violation_cell_index=int(pattern_spec.violation_cell_index),
        size_levels=tuple(int(level) for level in pattern_spec.size_levels),
        size_level_nominal_sizes_px={int(key): int(value) for key, value in size_level_nominal_sizes_px.items()},
        base_size_level=int(pattern_spec.base_size_level),
        row_step_levels=int(pattern_spec.row_step_levels),
        col_step_levels=int(pattern_spec.col_step_levels),
        violation_size_level=int(pattern_spec.violation_size_level),
        shared_rotation_degrees=int(pattern_spec.shared_rotation_degrees),
        expected_grid_size_levels=tuple(int(value) for value in pattern_spec.expected_grid_size_levels),
        observed_grid_size_levels=tuple(int(value) for value in pattern_spec.observed_grid_size_levels),
        expected_grid_nominal_sizes_px=tuple(int(value) for value in expected_grid_nominal_sizes_px),
        observed_grid_nominal_sizes_px=tuple(int(value) for value in observed_grid_nominal_sizes_px),
        plausible_rule_count=int(pattern_spec.plausible_rule_count),
        total_rule_support=int(pattern_spec.total_rule_support),
        pattern_icon_id=str(pattern_icon_id),
        sampled_palette_rgb=tuple(tuple(int(channel) for channel in color) for color in sampled_palette_rgb),
        cell_box_width_px=int(cell_box_width_px),
        cell_box_height_px=int(cell_box_height_px),
        panel_geometry=single_panel_geometry_to_trace(prepared.layout),
        scene_cells=tuple(scene_cells),
        scene_icon_instances=tuple(scene_icon_instances),
        violating_cell_bbox=tuple(int(value) for value in violating_cell_bbox),
    ), image


class IconsPatternGridSizeViolationTask:
    """Identify the numbered cell that breaks a 2D icon-size grid rule."""

    task_id = TASK_ID
    domain = "icons"
    scene_id = "pattern"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic icon-grid size-pattern violation instance."""

        scene_rng = spawn_rng(int(instance_seed), "scene")
        pattern_spec = _resolve_pattern_spec(instance_seed=int(instance_seed), params=params)
        render_params = resolve_icon_cell_render_params(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        render_params["size_level_gap_px"] = int(
            params.get(
                "size_level_gap_px",
                group_default(_RENDER_DEFAULTS, "size_level_gap_px", _DEFAULTS.size_level_gap_px),
            )
        )
        if int(render_params["cell_box_width_min_px"]) > int(render_params["cell_box_width_max_px"]):
            raise ValueError("cell_box_width_min_px must be <= cell_box_width_max_px")
        if int(render_params["cell_box_height_min_px"]) > int(render_params["cell_box_height_max_px"]):
            raise ValueError("cell_box_height_min_px must be <= cell_box_height_max_px")
        pool_manifest = str(
            params.get("pool_manifest", group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest))
        )

        scene_payload = None
        image = None
        last_error: Exception | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                scene_payload, image = _sample_scene(
                    scene_rng,
                    instance_seed=int(instance_seed),
                    pattern_spec=pattern_spec,
                    pool_manifest=str(pool_manifest),
                    render_params=render_params,
                )
                break
            except Exception as exc:  # pragma: no cover - exercised through retry loop
                last_error = exc
                continue
        if scene_payload is None or image is None:
            raise RuntimeError(f"failed to generate {self.task_id} instance") from last_error

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "question_text",
                "annotation_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            scene_id=self.scene_id,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(prompt_defaults["question_text"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        annotation_bboxes = sort_bboxes_reading_order((scene_payload.violating_cell_bbox,))
        annotation_artifacts = bbox_set_annotation(annotation_bboxes)
        taxonomy = resolve_task_taxonomy(str(self.task_id))
        query_id = QUERY_ID
        answer_gt = TypedValue(type="integer", value=int(scene_payload.answer_index))
        annotation_gt = TypedValue(
            type=str(annotation_artifacts["annotation_type"]),
            value=list(annotation_artifacts["annotation_value"]),
        )
        common_ids = {
            "domain": taxonomy.domain,
            "scene_id": taxonomy.scene_id,
            "task_id": str(self.task_id),
            "query_id": str(query_id),
        }
        trace_payload = {
            "taxonomy": {
                "domain": taxonomy.domain,
                "scene_id": taxonomy.scene_id,
                "task_id": str(self.task_id),
                "source_domain": taxonomy.source_domain,
                "source_scene_id": taxonomy.source_scene_id,
                "query_id": str(query_id),
            },
            "scene_ir": {
                **common_ids,
                "scene_kind": "icons_pattern_grid_size_violation",
                "entities": [
                    *[dict(cell) for cell in scene_payload.scene_cells],
                    *[dict(instance) for instance in scene_payload.scene_icon_instances],
                ],
                "relations": {
                    "query_id": str(query_id),
                    "pattern_rule": "row_col_size_level_offsets",
                    "pattern_icon_id": str(scene_payload.pattern_icon_id),
                    "size_levels": [int(value) for value in scene_payload.size_levels],
                    "size_level_nominal_sizes_px": {
                        str(level): int(size_px) for level, size_px in scene_payload.size_level_nominal_sizes_px.items()
                    },
                    "base_size_level": int(scene_payload.base_size_level),
                    "row_step_levels": int(scene_payload.row_step_levels),
                    "col_step_levels": int(scene_payload.col_step_levels),
                    "expected_grid_size_levels": list(scene_payload.expected_grid_size_levels),
                    "observed_grid_size_levels": list(scene_payload.observed_grid_size_levels),
                    "shared_rotation_degrees": int(scene_payload.shared_rotation_degrees),
                    "violation_cell_index": int(scene_payload.violation_cell_index),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene_payload.panel_geometry),
                },
            },
            "query_spec": {
                **common_ids,
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_id": taxonomy.scene_id,
                    "query_id": str(query_id),
                    "query_id_probabilities": {str(query_id): 1.0},
                    "grid_rows": int(scene_payload.grid_rows),
                    "grid_cols": int(scene_payload.grid_cols),
                    "answer_index": int(scene_payload.answer_index),
                    "answer_index_probabilities": dict(pattern_spec.answer_index_probabilities),
                    "violation_cell_index": int(scene_payload.violation_cell_index),
                    "size_levels": [int(value) for value in scene_payload.size_levels],
                    "base_size_level": int(scene_payload.base_size_level),
                    "row_step_levels": int(scene_payload.row_step_levels),
                    "col_step_levels": int(scene_payload.col_step_levels),
                    "violation_size_level": int(scene_payload.violation_size_level),
                    "shared_rotation_degrees": int(scene_payload.shared_rotation_degrees),
                    "pool_manifest": str(pool_manifest),
                    "base_level_candidates": [int(value) for value in _base_level_candidates(params, size_levels=scene_payload.size_levels)],
                    "row_step_candidates": [int(value) for value in _row_step_candidates(params)],
                    "col_step_candidates": [int(value) for value in _col_step_candidates(params)],
                    "shared_rotation_candidates_degrees": [
                        int(value) for value in _shared_rotation_candidates(params)
                    ],
                    "cell_box_width_px": int(scene_payload.cell_box_width_px),
                    "cell_box_height_px": int(scene_payload.cell_box_height_px),
                },
            },
            "render_spec": {
                **common_ids,
                "canvas_size": list(scene_payload.panel_geometry["canvas_size"]),
                "coord_space": "pixel",
                "panel_geometry": dict(scene_payload.panel_geometry),
                "style": {
                    **icon_render_style_trace(
                        render_params=render_params,
                        sampled_palette_rgb=scene_payload.sampled_palette_rgb,
                    ),
                    "cell_padding_px": int(render_params["cell_padding_px"]),
                    "cell_icon_padding_px": int(render_params["cell_icon_padding_px"]),
                    "cell_corner_radius_px": int(render_params["cell_corner_radius_px"]),
                    "cell_box_width_range_px": [
                        int(render_params["cell_box_width_min_px"]),
                        int(render_params["cell_box_width_max_px"]),
                    ],
                    "cell_box_height_range_px": [
                        int(render_params["cell_box_height_min_px"]),
                        int(render_params["cell_box_height_max_px"]),
                    ],
                    "sampled_cell_box_size_px": [
                        int(scene_payload.cell_box_width_px),
                        int(scene_payload.cell_box_height_px),
                    ],
                    "cell_label_font_size_px": int(render_params["cell_label_font_size_px"]),
                    "cell_label_color_rgb": list(render_params["cell_label_color_rgb"]),
                    "scene_content_side_padding_px": int(render_params["scene_content_side_padding_px"]),
                    "scene_content_bottom_padding_px": int(render_params["scene_content_bottom_padding_px"]),
                    "scene_content_top_offset_px": int(render_params["scene_content_top_offset_px"]),
                    "size_level_gap_px": int(render_params["size_level_gap_px"]),
                },
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {
                    "violating_cell_bbox": list(scene_payload.violating_cell_bbox),
                },
            },
            "execution_trace": {
                **common_ids,
                "scene_variant": "numbered_grid",
                "query_id_probabilities": {str(query_id): 1.0},
                "grid_rows": int(scene_payload.grid_rows),
                "grid_cols": int(scene_payload.grid_cols),
                "answer_index": int(scene_payload.answer_index),
                "violation_cell_index": int(scene_payload.violation_cell_index),
                "size_levels": [int(value) for value in scene_payload.size_levels],
                "size_level_nominal_sizes_px": {
                    str(level): int(size_px) for level, size_px in scene_payload.size_level_nominal_sizes_px.items()
                },
                "base_size_level": int(scene_payload.base_size_level),
                "row_step_levels": int(scene_payload.row_step_levels),
                "col_step_levels": int(scene_payload.col_step_levels),
                "violation_size_level": int(scene_payload.violation_size_level),
                "shared_rotation_degrees": int(scene_payload.shared_rotation_degrees),
                "expected_grid_size_levels": list(scene_payload.expected_grid_size_levels),
                "observed_grid_size_levels": list(scene_payload.observed_grid_size_levels),
                "expected_grid_nominal_sizes_px": list(scene_payload.expected_grid_nominal_sizes_px),
                "observed_grid_nominal_sizes_px": list(scene_payload.observed_grid_nominal_sizes_px),
                "pattern_icon_id": str(scene_payload.pattern_icon_id),
                "plausible_rule_count": int(scene_payload.plausible_rule_count),
                "cell_box_width_px": int(scene_payload.cell_box_width_px),
                "cell_box_height_px": int(scene_payload.cell_box_height_px),
                "question_format": "identify_grid_size_violation",
            },
            "witness_symbolic": {
                "pattern_rule": "row_col_size_level_offsets",
                "size_levels": [int(value) for value in scene_payload.size_levels],
                "size_level_nominal_sizes_px": {
                    str(level): int(size_px) for level, size_px in scene_payload.size_level_nominal_sizes_px.items()
                },
                "base_size_level": int(scene_payload.base_size_level),
                "row_step_levels": int(scene_payload.row_step_levels),
                "col_step_levels": int(scene_payload.col_step_levels),
                "expected_grid_size_levels": list(scene_payload.expected_grid_size_levels),
                "observed_grid_size_levels": list(scene_payload.observed_grid_size_levels),
                "violation_cell_index": int(scene_payload.violation_cell_index),
                "plausible_rule_count": int(scene_payload.plausible_rule_count),
            },
            "projected_annotation": dict(annotation_artifacts["projected_annotation"]),
        }
        expected_size_level = int(scene_payload.expected_grid_size_levels[scene_payload.violation_cell_index])
        violation_level_delta = abs(int(expected_size_level) - int(scene_payload.violation_size_level))
        violation_nominal_size_gap_px = abs(
            int(scene_payload.expected_grid_nominal_sizes_px[scene_payload.violation_cell_index])
            - int(scene_payload.observed_grid_nominal_sizes_px[scene_payload.violation_cell_index])
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=taxonomy.scene_id,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["IconsPatternGridSizeViolationTask"]
