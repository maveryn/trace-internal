"""Identify the numbered cell that breaks a 2D icon-rotation grid rule."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
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
from ..shared.complexity import build_icons_pattern_grid_rotation_violation_complexity
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.icon_assets import resolve_icon_pool
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
from ..shared.icon_noise import serialize_icon_noise_edits
from ..shared.icon_assets import render_icon_rgba


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for icon 2D rotation-pattern violation grids."""

    grid_rows: int = 3
    grid_cols: int = 3
    answer_index_min: int = 1
    answer_index_max: int = 9
    canvas_width: int = 640
    canvas_height: int = 640
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    scene_icon_size_min_px: int = 48
    scene_icon_size_max_px: int = 72
    cell_box_width_min_px: int = 104
    cell_box_width_max_px: int = 140
    cell_box_height_min_px: int = 104
    cell_box_height_max_px: int = 140
    scene_max_overlap_fraction: float = 0.20
    scene_placement_max_attempts: int = 80
    scene_size_shrink_rounds: int = ICON_SHARED_DEFAULTS.scene_size_shrink_rounds
    scene_size_shrink_factor: float = ICON_SHARED_DEFAULTS.scene_size_shrink_factor
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    pool_manifest: str = "non_symmetry.txt"
    rotation_candidates_degrees: Tuple[int, ...] = (0, 90, 180, 270)
    row_step_candidates_degrees: Tuple[int, ...] = (90, 180, 270)
    col_step_candidates_degrees: Tuple[int, ...] = (90, 180, 270)
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
    icon_noise_edit_count_range: Tuple[int, int] = ICON_SHARED_DEFAULTS.icon_noise_edit_count_range
    icon_noise_value_ranges: Dict[str, Dict[str, Tuple[float, float]]] = field(
        default_factory=lambda: deepcopy(ICON_SHARED_DEFAULTS.icon_noise_value_ranges)
    )


@dataclass(frozen=True)
class _PatternSpec:
    """One resolved 3x3 rotation pattern with a unique violating cell."""

    grid_rows: int
    grid_cols: int
    answer_index: int
    violation_cell_index: int
    base_rotation_degrees: int
    row_step_degrees: int
    col_step_degrees: int
    violation_rotation_degrees: int
    expected_grid_rotations_degrees: Tuple[int, ...]
    observed_grid_rotations_degrees: Tuple[int, ...]
    plausible_rule_count: int
    total_rule_support: int
    answer_index_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready payload for one icon grid rotation-pattern violation instance."""

    grid_rows: int
    grid_cols: int
    answer_index: int
    violation_cell_index: int
    base_rotation_degrees: int
    row_step_degrees: int
    col_step_degrees: int
    violation_rotation_degrees: int
    expected_grid_rotations_degrees: Tuple[int, ...]
    observed_grid_rotations_degrees: Tuple[int, ...]
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
_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "pattern")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="task_icons_pattern_grid_rotation_violation",
)


def _rotation_candidates(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Resolve the supported icon rotations."""

    raw = params.get(
        "rotation_candidates_degrees",
        group_default(_GEN_DEFAULTS, "rotation_candidates_degrees", list(_DEFAULTS.rotation_candidates_degrees)),
    )
    if not isinstance(raw, (list, tuple)):
        raise ValueError("rotation_candidates_degrees must be a sequence")
    rotations = tuple(int(value) % 360 for value in raw)
    if not rotations:
        raise ValueError("rotation_candidates_degrees must contain at least one rotation")
    return rotations


def _row_step_candidates(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Resolve supported row-wise rotation steps."""

    raw = params.get(
        "row_step_candidates_degrees",
        group_default(_GEN_DEFAULTS, "row_step_candidates_degrees", list(_DEFAULTS.row_step_candidates_degrees)),
    )
    if not isinstance(raw, (list, tuple)):
        raise ValueError("row_step_candidates_degrees must be a sequence")
    steps = tuple(int(value) % 360 for value in raw)
    if not steps:
        raise ValueError("row_step_candidates_degrees must contain at least one step")
    return steps


def _col_step_candidates(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Resolve supported column-wise rotation steps."""

    raw = params.get(
        "col_step_candidates_degrees",
        group_default(_GEN_DEFAULTS, "col_step_candidates_degrees", list(_DEFAULTS.col_step_candidates_degrees)),
    )
    if not isinstance(raw, (list, tuple)):
        raise ValueError("col_step_candidates_degrees must be a sequence")
    steps = tuple(int(value) % 360 for value in raw)
    if not steps:
        raise ValueError("col_step_candidates_degrees must contain at least one step")
    return steps


def _grid_rotation_pattern(
    *,
    base_rotation_degrees: int,
    row_step_degrees: int,
    col_step_degrees: int,
    grid_rows: int,
    grid_cols: int,
) -> Tuple[int, ...]:
    """Return one row-major 2D rotation grid modulo 360 degrees."""

    rotations: List[int] = []
    for row in range(int(grid_rows)):
        for col in range(int(grid_cols)):
            rotations.append(
                int(
                    (
                        int(base_rotation_degrees)
                        + (int(row) * int(row_step_degrees))
                        + (int(col) * int(col_step_degrees))
                    )
                    % 360
                )
            )
    return tuple(rotations)


def _rotation_grid_violation_explanations(
    observed_rotations_degrees: Sequence[int],
    *,
    grid_rows: int,
    grid_cols: int,
    rotation_candidates: Sequence[int],
    row_step_candidates: Sequence[int],
    col_step_candidates: Sequence[int],
) -> Tuple[bool, set[int], Dict[int, int]]:
    """Return whether the grid is already valid and all plausible violation indices."""

    exact_match = False
    plausible_indices: set[int] = set()
    rule_counts: Counter[int] = Counter()
    observed = tuple(int(value) % 360 for value in observed_rotations_degrees)
    for base_rotation_degrees in rotation_candidates:
        for row_step_degrees in row_step_candidates:
            for col_step_degrees in col_step_candidates:
                expected = _grid_rotation_pattern(
                    base_rotation_degrees=int(base_rotation_degrees),
                    row_step_degrees=int(row_step_degrees),
                    col_step_degrees=int(col_step_degrees),
                    grid_rows=int(grid_rows),
                    grid_cols=int(grid_cols),
                )
                mismatches = [
                    int(index)
                    for index, (observed_rotation, expected_rotation) in enumerate(zip(observed, expected))
                    if int(observed_rotation) != int(expected_rotation)
                ]
                if not mismatches:
                    exact_match = True
                elif len(mismatches) == 1:
                    index = int(mismatches[0])
                    plausible_indices.add(index)
                    rule_counts[index] += 1
    return bool(exact_match), plausible_indices, {int(key): int(value) for key, value in rule_counts.items()}


def _minimal_rotation_difference_degrees(left: int, right: int) -> int:
    """Return the smallest absolute angular distance between two rotations."""

    diff = abs((int(left) - int(right)) % 360)
    return int(min(diff, 360 - diff))


def _resolve_pattern_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _PatternSpec:
    """Resolve one unambiguous 2D rotation grid with a single violating position."""

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

    rotation_candidates = _rotation_candidates(params)
    row_step_candidates = _row_step_candidates(params)
    col_step_candidates = _col_step_candidates(params)
    total_rule_support = int(
        len(rotation_candidates) * len(row_step_candidates) * len(col_step_candidates)
    )

    answer_support = tuple(range(int(answer_index_min), int(answer_index_max) + 1))
    base_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace="task_icons_pattern_grid_rotation_violation:pattern_spec",
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

    explicit_base_rotation = params.get("base_rotation_degrees")
    explicit_row_step = params.get("row_step_degrees")
    explicit_col_step = params.get("col_step_degrees")
    explicit_violation_rotation = params.get("violation_rotation_degrees")
    feasible_patterns: List[Tuple[int, int, int, int, Tuple[int, ...], Tuple[int, ...], int]] = []
    for base_rotation_degrees in rotation_candidates:
        if explicit_base_rotation is not None and int(base_rotation_degrees) != int(explicit_base_rotation) % 360:
            continue
        for row_step_degrees in row_step_candidates:
            if explicit_row_step is not None and int(row_step_degrees) != int(explicit_row_step) % 360:
                continue
            for col_step_degrees in col_step_candidates:
                if explicit_col_step is not None and int(col_step_degrees) != int(explicit_col_step) % 360:
                    continue
                expected = _grid_rotation_pattern(
                    base_rotation_degrees=int(base_rotation_degrees),
                    row_step_degrees=int(row_step_degrees),
                    col_step_degrees=int(col_step_degrees),
                    grid_rows=int(grid_rows),
                    grid_cols=int(grid_cols),
                )
                if len(set(int(value) for value in expected)) < 3:
                    continue
                expected_rotation = int(expected[violation_cell_index])
                for violation_rotation_degrees in rotation_candidates:
                    if explicit_violation_rotation is not None and int(violation_rotation_degrees) != int(explicit_violation_rotation) % 360:
                        continue
                    if int(violation_rotation_degrees) == int(expected_rotation):
                        continue
                    observed = list(int(value) for value in expected)
                    observed[int(violation_cell_index)] = int(violation_rotation_degrees)
                    exact_match, plausible_indices, plausible_rule_counts = _rotation_grid_violation_explanations(
                        tuple(observed),
                        grid_rows=int(grid_rows),
                        grid_cols=int(grid_cols),
                        rotation_candidates=rotation_candidates,
                        row_step_candidates=row_step_candidates,
                        col_step_candidates=col_step_candidates,
                    )
                    if exact_match:
                        continue
                    if plausible_indices != {int(violation_cell_index)}:
                        continue
                    feasible_patterns.append(
                        (
                            int(base_rotation_degrees),
                            int(row_step_degrees),
                            int(col_step_degrees),
                            int(violation_rotation_degrees),
                            tuple(int(value) for value in expected),
                            tuple(int(value) for value in observed),
                            int(plausible_rule_counts.get(int(violation_cell_index), 0)),
                        )
                    )
    if not feasible_patterns:
        raise ValueError("no unambiguous 2D rotation grid is feasible for the requested parameters")

    combo_index = int(base_index // max(1, len(answer_support))) % len(feasible_patterns)
    (
        base_rotation_degrees,
        row_step_degrees,
        col_step_degrees,
        violation_rotation_degrees,
        expected_grid_rotations_degrees,
        observed_grid_rotations_degrees,
        plausible_rule_count,
    ) = feasible_patterns[int(combo_index)]
    answer_index_probabilities = uniform_probability_map(
        answer_support,
        selected=int(answer_index) if explicit_answer_index is not None or explicit_violation_cell_index is not None else None,
    )
    return _PatternSpec(
        grid_rows=int(grid_rows),
        grid_cols=int(grid_cols),
        answer_index=int(answer_index),
        violation_cell_index=int(violation_cell_index),
        base_rotation_degrees=int(base_rotation_degrees),
        row_step_degrees=int(row_step_degrees),
        col_step_degrees=int(col_step_degrees),
        violation_rotation_degrees=int(violation_rotation_degrees),
        expected_grid_rotations_degrees=tuple(int(value) for value in expected_grid_rotations_degrees),
        observed_grid_rotations_degrees=tuple(int(value) for value in observed_grid_rotations_degrees),
        plausible_rule_count=int(plausible_rule_count),
        total_rule_support=int(total_rule_support),
        answer_index_probabilities=dict(answer_index_probabilities),
    )


def _sample_scene(
    rng,
    *,
    instance_seed: int,
    pattern_spec: _PatternSpec,
    pool_manifest: str,
    render_params: Mapping[str, Any],
) -> Tuple[_ScenePayload, Any]:
    """Sample and render one single-panel numbered 2D rotation-pattern grid."""

    pool = list(resolve_icon_pool(str(pool_manifest)))
    if not pool:
        raise ValueError("rotation grid pool resolved no icons")
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
        cell_label_font_size_px=int(render_params["cell_label_font_size_px"]),
        cell_corner_radius_px=int(render_params["cell_corner_radius_px"]),
        scene_content_side_padding_px=int(render_params["scene_content_side_padding_px"]),
        scene_content_bottom_padding_px=int(render_params["scene_content_bottom_padding_px"]),
        scene_content_top_offset_px=int(render_params["scene_content_top_offset_px"]),
        scene_square_cells=True,
        scene_title="Pattern",
    )

    image = prepared.image.copy()
    scene_cells: List[Dict[str, Any]] = []
    scene_icon_instances: List[Dict[str, Any]] = []
    violating_cell_bbox = None
    for cell_index, (prepared_cell, observed_rotation_degrees) in enumerate(
        zip(prepared.scene_cells, pattern_spec.observed_grid_rotations_degrees)
    ):
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{IconsPatternGridRotationViolationTask.task_id}:scene_cell_{int(cell_index)}_icon_0",
            render_params=render_params,
        )
        icon_spec = IconInstanceSpec(
            icon_id=str(pattern_icon_id),
            rotation_degrees=int(observed_rotation_degrees),
            tint_rgb=tuple(int(value) for value in tint_rgb),
            noise_edits=tuple(noise_edits),
            noise_seed=int(noise_seed),
        )
        content_width = max(1, int(prepared_cell.content_bbox_xyxy[2]) - int(prepared_cell.content_bbox_xyxy[0]))
        content_height = max(1, int(prepared_cell.content_bbox_xyxy[3]) - int(prepared_cell.content_bbox_xyxy[1]))
        max_nominal_size = min(
            int(render_params["scene_icon_size_max_px"]),
            int(content_width),
            int(content_height),
        )
        min_nominal_size = min(int(render_params["scene_icon_size_min_px"]), int(max_nominal_size))
        if max_nominal_size < 16:
            raise ValueError("pattern cell content area is too small for the configured icon size band")
        nominal_size = int(
            rng.randint(
                int(min_nominal_size),
                int(max_nominal_size),
            )
        )
        sprite = render_icon_rgba(
            icon_id=str(icon_spec.icon_id),
            size_px=int(nominal_size),
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
            nominal_size_px=int(nominal_size),
            rotation_degrees=int(icon_spec.rotation_degrees) % 360,
            mirror_x=bool(icon_spec.mirror_x),
            tint_rgb=tuple(int(value) for value in icon_spec.tint_rgb),
            noise_edits=serialize_icon_noise_edits(icon_spec.noise_edits),
            noise_seed=None if icon_spec.noise_seed is None else int(icon_spec.noise_seed),
        )
        cell_bbox = tuple(int(value) for value in prepared_cell.cell_bbox_xyxy)
        if int(cell_index) == int(pattern_spec.violation_cell_index):
            violating_cell_bbox = cell_bbox
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
                "expected_rotation_degrees": int(pattern_spec.expected_grid_rotations_degrees[cell_index]),
                "observed_rotation_degrees": int(pattern_spec.observed_grid_rotations_degrees[cell_index]),
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
        raise ValueError("rendered pattern scene did not produce the violating cell bbox")

    return _ScenePayload(
        grid_rows=int(pattern_spec.grid_rows),
        grid_cols=int(pattern_spec.grid_cols),
        answer_index=int(pattern_spec.answer_index),
        violation_cell_index=int(pattern_spec.violation_cell_index),
        base_rotation_degrees=int(pattern_spec.base_rotation_degrees),
        row_step_degrees=int(pattern_spec.row_step_degrees),
        col_step_degrees=int(pattern_spec.col_step_degrees),
        violation_rotation_degrees=int(pattern_spec.violation_rotation_degrees),
        expected_grid_rotations_degrees=tuple(int(value) for value in pattern_spec.expected_grid_rotations_degrees),
        observed_grid_rotations_degrees=tuple(int(value) for value in pattern_spec.observed_grid_rotations_degrees),
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


@register_task
class IconsPatternGridRotationViolationTask:
    """Identify the numbered cell that breaks a 2D icon-rotation grid rule."""

    task_id = "task_icons_pattern_grid_rotation_violation"
    domain = "icons"
    task_group = "pattern"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic icon-grid rotation-pattern violation instance."""

        scene_rng = spawn_rng(int(instance_seed), "scene")
        pattern_spec = _resolve_pattern_spec(instance_seed=int(instance_seed), params=params)
        render_params = resolve_icon_cell_render_params(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
        )
        if int(render_params["cell_box_width_min_px"]) > int(render_params["cell_box_width_max_px"]):
            raise ValueError("cell_box_width_min_px must be <= cell_box_width_max_px")
        if int(render_params["cell_box_height_min_px"]) > int(render_params["cell_box_height_max_px"]):
            raise ValueError("cell_box_height_min_px must be <= cell_box_height_max_px")
        pool_manifest = str(params.get("pool_manifest", group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest)))

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
            raise RuntimeError("failed to generate task_icons_pattern_grid_rotation_violation instance") from last_error

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "task_family_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "question_text",
                "evidence_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(prompt_defaults["question_text"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_bboxes = sort_bboxes_reading_order((scene_payload.violating_cell_bbox,))
        task_variant = "row_col_rotation_grid_violation"
        answer_gt = TypedValue(type="integer", value=int(scene_payload.answer_index))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_pattern_grid_rotation_violation",
                "entities": [
                    *[dict(cell) for cell in scene_payload.scene_cells],
                    *[dict(instance) for instance in scene_payload.scene_icon_instances],
                ],
                "relations": {
                    "pattern_rule": "row_col_rotation_offsets",
                    "pattern_icon_id": str(scene_payload.pattern_icon_id),
                    "base_rotation_degrees": int(scene_payload.base_rotation_degrees),
                    "row_step_degrees": int(scene_payload.row_step_degrees),
                    "col_step_degrees": int(scene_payload.col_step_degrees),
                    "expected_grid_rotations_degrees": list(scene_payload.expected_grid_rotations_degrees),
                    "observed_grid_rotations_degrees": list(scene_payload.observed_grid_rotations_degrees),
                    "violation_cell_index": int(scene_payload.violation_cell_index),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene_payload.panel_geometry),
                },
            },
            "query_spec": {
                "task_variant": str(task_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "grid_rows": int(scene_payload.grid_rows),
                    "grid_cols": int(scene_payload.grid_cols),
                    "answer_index": int(scene_payload.answer_index),
                    "answer_index_probabilities": dict(pattern_spec.answer_index_probabilities),
                    "violation_cell_index": int(scene_payload.violation_cell_index),
                    "base_rotation_degrees": int(scene_payload.base_rotation_degrees),
                    "row_step_degrees": int(scene_payload.row_step_degrees),
                    "col_step_degrees": int(scene_payload.col_step_degrees),
                    "violation_rotation_degrees": int(scene_payload.violation_rotation_degrees),
                    "pool_manifest": str(pool_manifest),
                    "rotation_candidates_degrees": [int(value) for value in _rotation_candidates(params)],
                    "row_step_candidates_degrees": [int(value) for value in _row_step_candidates(params)],
                    "col_step_candidates_degrees": [int(value) for value in _col_step_candidates(params)],
                    "cell_box_width_px": int(scene_payload.cell_box_width_px),
                    "cell_box_height_px": int(scene_payload.cell_box_height_px),
                },
            },
            "render_spec": {
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
                },
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {
                    "violating_cell_bbox": list(scene_payload.violating_cell_bbox),
                },
            },
            "execution_trace": {
                "scene_variant": "single_panel_numbered_grid",
                "task_variant": str(task_variant),
                "grid_rows": int(scene_payload.grid_rows),
                "grid_cols": int(scene_payload.grid_cols),
                "answer_index": int(scene_payload.answer_index),
                "violation_cell_index": int(scene_payload.violation_cell_index),
                "base_rotation_degrees": int(scene_payload.base_rotation_degrees),
                "row_step_degrees": int(scene_payload.row_step_degrees),
                "col_step_degrees": int(scene_payload.col_step_degrees),
                "violation_rotation_degrees": int(scene_payload.violation_rotation_degrees),
                "expected_grid_rotations_degrees": list(scene_payload.expected_grid_rotations_degrees),
                "observed_grid_rotations_degrees": list(scene_payload.observed_grid_rotations_degrees),
                "pattern_icon_id": str(scene_payload.pattern_icon_id),
                "plausible_rule_count": int(scene_payload.plausible_rule_count),
                "cell_box_width_px": int(scene_payload.cell_box_width_px),
                "cell_box_height_px": int(scene_payload.cell_box_height_px),
                "question_format": "identify_grid_rotation_violation",
            },
            "witness_symbolic": {
                "pattern_rule": "row_col_rotation_offsets",
                "base_rotation_degrees": int(scene_payload.base_rotation_degrees),
                "row_step_degrees": int(scene_payload.row_step_degrees),
                "col_step_degrees": int(scene_payload.col_step_degrees),
                "expected_grid_rotations_degrees": list(scene_payload.expected_grid_rotations_degrees),
                "observed_grid_rotations_degrees": list(scene_payload.observed_grid_rotations_degrees),
                "violation_cell_index": int(scene_payload.violation_cell_index),
                "plausible_rule_count": int(scene_payload.plausible_rule_count),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
            },
        }
        expected_rotation = int(scene_payload.expected_grid_rotations_degrees[scene_payload.violation_cell_index])
        violation_rotation_difference_degrees = _minimal_rotation_difference_degrees(
            int(expected_rotation),
            int(scene_payload.violation_rotation_degrees),
        )
        complexity = build_icons_pattern_grid_rotation_violation_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            grid_rows=int(scene_payload.grid_rows),
            grid_cols=int(scene_payload.grid_cols),
            row_step_degrees=int(scene_payload.row_step_degrees),
            col_step_degrees=int(scene_payload.col_step_degrees),
            distinct_expected_rotation_count=len(set(int(value) for value in scene_payload.expected_grid_rotations_degrees)),
            plausible_rule_count=int(scene_payload.plausible_rule_count),
            total_rule_support=int(scene_payload.total_rule_support),
            violation_cell_index=int(scene_payload.violation_cell_index),
            violation_rotation_difference_degrees=int(violation_rotation_difference_degrees),
            scene_icon_instances=scene_payload.scene_icon_instances,
            render_params=render_params,
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant=str(task_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["IconsPatternGridRotationViolationTask"]
