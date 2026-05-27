"""Single-board rectangular-tile symmetry-violation counting task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from trace.core.seed import spawn_rng
from trace.core.task_group_config import get_task_group_defaults
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.shared.bbox_projection import pixel_anchor_map_from_bboxes
from trace.tasks.shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_json_example import resolve_prompt_json_examples
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from .shared.grid_graph import cell_id
from .shared.complexity import (
    build_tile_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_tile_complexity_weights,
)
from .shared.named_color_board import (
    Coord,
    RectangularNamedColorBoardTaskDefaults,
    build_palette_trace,
    build_rectangular_named_color_board_render_spec,
    build_rectangular_named_color_board_scene,
)
from .shared.tile_colors import NamedColor, sample_named_tile_palette
from .shared.tile_evidence import coordinate_set_evidence_artifacts
from .shared.tile_scene import build_tile_cell_entities
from .shared.visual_defaults import load_tile_background_defaults, load_tile_noise_defaults


_PUBLIC_QUERY_ID = "symmetry_violation_count"
_MIRROR_AXIS_ORDER = ("vertical", "horizontal")


@dataclass(frozen=True)
class _TaskDefaults(RectangularNamedColorBoardTaskDefaults):
    """Stable defaults for the symmetry violation counting task."""

    palette_size_min: int = 2
    palette_size_max: int = 4
    target_violation_count_min: int = 1
    target_violation_count_max: int = 10


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "cell_board_symmetry")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, dict) else {},
    task_id="cell_board_symmetry_violation_count_internal",
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_tile_background_defaults(task_group="symmetry")
POST_IMAGE_NOISE_DEFAULTS = load_tile_noise_defaults(task_group="symmetry", apply_prob=0.5)
_COMPLEXITY_WEIGHTS = resolve_tile_complexity_weights(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, dict) else {},
    task_id="cell_board_symmetry_violation_count_internal",
)


def _resolve_query_id(
    *,
    params: Mapping[str, Any],
    task_id: str,
) -> str:
    """Resolve the public symmetry-violation variant."""

    explicit_variant = params.get("query_id")
    if explicit_variant is not None:
        variant = str(explicit_variant).strip().lower()
        if variant in set(_MIRROR_AXIS_ORDER):
            return str(_PUBLIC_QUERY_ID)
        if variant != str(_PUBLIC_QUERY_ID):
            raise ValueError(f"unsupported query_id for {task_id}: {explicit_variant}")
    return str(_PUBLIC_QUERY_ID)


def _resolve_mirror_axis(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    review_cycle_width: int,
) -> str:
    """Resolve vertical-vs-horizontal mirror axis deterministically."""

    explicit_axis = params.get("mirror_axis", params.get("axis"))
    explicit_variant = params.get("query_id")
    if explicit_axis is None and explicit_variant is not None and str(explicit_variant).strip().lower() in set(_MIRROR_AXIS_ORDER):
        explicit_axis = str(explicit_variant)
    if explicit_axis is not None:
        axis = str(explicit_axis).strip().lower()
        if axis not in set(_MIRROR_AXIS_ORDER):
            raise ValueError(f"unsupported mirror_axis for {task_id}: {explicit_axis}")
        return str(axis)
    _ = int(review_cycle_width)
    variant_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:mirror_axis",
    )
    return str(_MIRROR_AXIS_ORDER[int(variant_index) % len(_MIRROR_AXIS_ORDER)])


def _variant_capacity(query_id: str, *, rows: int, cols: int) -> int:
    """Return the maximum possible counted-side violation count for one board shape."""
    if str(query_id) == "vertical":
        return int(rows) * int(cols // 2)
    if str(query_id) == "horizontal":
        return int(rows // 2) * int(cols)
    raise ValueError(f"unsupported query_id: {query_id}")


def _eligible_board_shapes(
    *,
    rows_min: int,
    rows_max: int,
    cols_min: int,
    cols_max: int,
    query_id: str,
    target_violation_count: int,
) -> List[Tuple[int, int]]:
    """Return board shapes that can support the requested target count."""
    return [
        (int(rows), int(cols))
        for rows in range(int(rows_min), int(rows_max) + 1)
        for cols in range(int(cols_min), int(cols_max) + 1)
        if _variant_capacity(str(query_id), rows=int(rows), cols=int(cols)) >= int(target_violation_count)
    ]


def _mirror_pairs_and_centers(
    query_id: str,
    *,
    rows: int,
    cols: int,
) -> Tuple[List[Tuple[Coord, Coord]], List[Coord], str, str]:
    """Return mirror pairs as `(reference, counted_side)` plus center-line coords."""
    if str(query_id) == "vertical":
        counted_col_start = int(cols) - int(cols // 2)
        pairs = [
            ((int(row), int(cols - 1 - counted_col)), (int(row), int(counted_col)))
            for row in range(int(rows))
            for counted_col in range(int(counted_col_start), int(cols))
        ]
        centers = [(int(row), int(cols // 2)) for row in range(int(rows))] if int(cols) % 2 == 1 else []
        return pairs, centers, "vertical", "right side"
    if str(query_id) == "horizontal":
        counted_row_start = int(rows) - int(rows // 2)
        pairs = [
            ((int(rows - 1 - counted_row), int(col)), (int(counted_row), int(col)))
            for counted_row in range(int(counted_row_start), int(rows))
            for col in range(int(cols))
        ]
        centers = [(int(rows // 2), int(col)) for col in range(int(cols))] if int(rows) % 2 == 1 else []
        return pairs, centers, "horizontal", "bottom side"
    raise ValueError(f"unsupported query_id: {query_id}")


def _build_board_with_exact_violations(
    rng,
    *,
    rows: int,
    cols: int,
    query_id: str,
    palette: Sequence[NamedColor],
    target_violation_count: int,
) -> Tuple[Dict[Coord, NamedColor], List[Coord], Dict[Coord, Coord], List[Coord]]:
    """Construct one board with exactly the requested counted-side symmetry violations."""
    pairs, center_coords, _mirror_axis, _counted_side = _mirror_pairs_and_centers(
        str(query_id),
        rows=int(rows),
        cols=int(cols),
    )
    if int(target_violation_count) <= 0 or int(target_violation_count) > len(pairs):
        raise ValueError("target_violation_count must fit within the available mirror pairs")
    if len(palette) < 2:
        raise ValueError("symmetry violation task requires at least two palette colors")

    violating_pair_indices = set(rng.sample(range(len(pairs)), k=int(target_violation_count)))
    palette_order = list(palette)
    rng.shuffle(palette_order)
    coverage_index = 0

    def next_base_color() -> NamedColor:
        nonlocal coverage_index
        if int(coverage_index) < len(palette_order):
            color = palette_order[int(coverage_index)]
            coverage_index += 1
            return color
        return rng.choice(palette_order)

    board_colors: Dict[Coord, NamedColor] = {}
    violation_coords: List[Coord] = []
    mirror_partner_by_coord: Dict[Coord, Coord] = {}
    counted_side_coords: List[Coord] = []

    for pair_index, (reference_coord, counted_coord) in enumerate(pairs):
        base_color = next_base_color()
        board_colors[(int(reference_coord[0]), int(reference_coord[1]))] = base_color
        mirror_partner_by_coord[(int(reference_coord[0]), int(reference_coord[1]))] = (
            int(counted_coord[0]),
            int(counted_coord[1]),
        )
        mirror_partner_by_coord[(int(counted_coord[0]), int(counted_coord[1]))] = (
            int(reference_coord[0]),
            int(reference_coord[1]),
        )
        counted_side_coords.append((int(counted_coord[0]), int(counted_coord[1])))
        if int(pair_index) in violating_pair_indices:
            mismatch_candidates = [entry for entry in palette_order if str(entry[0]) != str(base_color[0])]
            mismatch_color = rng.choice(mismatch_candidates)
            board_colors[(int(counted_coord[0]), int(counted_coord[1]))] = (
                str(mismatch_color[0]),
                (int(mismatch_color[1][0]), int(mismatch_color[1][1]), int(mismatch_color[1][2])),
            )
            violation_coords.append((int(counted_coord[0]), int(counted_coord[1])))
        else:
            board_colors[(int(counted_coord[0]), int(counted_coord[1]))] = base_color

    for coord in center_coords:
        center_color = next_base_color()
        board_colors[(int(coord[0]), int(coord[1]))] = center_color
        mirror_partner_by_coord[(int(coord[0]), int(coord[1]))] = (int(coord[0]), int(coord[1]))

    return board_colors, sorted(violation_coords), mirror_partner_by_coord, sorted(counted_side_coords)


class TileSymmetryViolationCountTask:
    """Count counted-side tiles that violate a mirror-symmetry constraint."""

    task_id = "cell_board_symmetry_violation_count_internal"
    domain = "puzzles"
    task_group = "cell_board_symmetry"
    default_dataset_enabled = False

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
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
        target_violation_count_min = int(
            params.get(
                "target_violation_count_min",
                group_default(_GEN_DEFAULTS, "target_violation_count_min", int(_DEFAULTS.target_violation_count_min)),
            )
        )
        target_violation_count_max = int(
            params.get(
                "target_violation_count_max",
                group_default(_GEN_DEFAULTS, "target_violation_count_max", int(_DEFAULTS.target_violation_count_max)),
            )
        )
        if int(target_violation_count_min) > int(target_violation_count_max):
            raise ValueError("target_violation_count_min must be <= target_violation_count_max")

        target_range_size = max(1, int(target_violation_count_max) - int(target_violation_count_min) + 1)
        query_id = _resolve_query_id(
            params=params,
            task_id=self.task_id,
        )
        mirror_axis_variant = _resolve_mirror_axis(
            params=params,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            review_cycle_width=int(target_range_size),
        )
        target_selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}:{mirror_axis_variant}:target_violation_count",
        )
        target_violation_count = int(target_violation_count_min) + (int(target_selection_index) % int(target_range_size))

        eligible_shapes = _eligible_board_shapes(
            rows_min=int(rows_min),
            rows_max=int(rows_max),
            cols_min=int(cols_min),
            cols_max=int(cols_max),
            query_id=str(mirror_axis_variant),
            target_violation_count=int(target_violation_count),
        )
        if not eligible_shapes:
            raise RuntimeError("failed to find any board shape supporting the target symmetry violation count")
        shape_selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}:{mirror_axis_variant}:board_shape",
        )
        rows, cols = eligible_shapes[int(shape_selection_index) % len(eligible_shapes)]

        palette_size = int(task_rng.randint(int(palette_size_min), int(palette_size_max)))
        palette = sample_named_tile_palette(task_rng, palette_size=int(palette_size))
        if len(palette) < int(palette_size):
            raise ValueError(f"requested palette_size={palette_size} exceeds available named tile colors")

        board_colors, violation_coords, mirror_partner_by_coord, counted_side_coords = _build_board_with_exact_violations(
            task_rng,
            rows=int(rows),
            cols=int(cols),
            query_id=str(mirror_axis_variant),
            palette=palette,
            target_violation_count=int(target_violation_count),
        )
        pairs, center_coords, mirror_axis, counted_side = _mirror_pairs_and_centers(
            str(mirror_axis_variant),
            rows=int(rows),
            cols=int(cols),
        )
        counted_side_coord_set = {(int(row), int(col)) for row, col in counted_side_coords}
        violation_coord_set = {(int(row), int(col)) for row, col in violation_coords}

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
            palette=palette,
            board_colors=board_colors,
        )

        evidence_artifacts = coordinate_set_evidence_artifacts(
            coords=violation_coords,
            bbox_map=scene.bbox_map,
        )
        answer_value = int(len(violation_coords))
        if int(answer_value) != int(target_violation_count):
            raise RuntimeError("constructed symmetry board does not match target violation count")

        all_prompt_defaults = dict(_PROMPT_DEFAULTS if isinstance(_PROMPT_DEFAULTS, dict) else {})
        prompt_defaults = required_group_defaults(
            all_prompt_defaults,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "evidence_hint",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = resolve_prompt_json_examples(
            all_prompt_defaults,
            evidence_value=[[216, 120], [216, 168]],
            answer_type="integer",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "rows": int(scene.rows),
                "cols": int(scene.cols),
                "mirror_axis": str(mirror_axis),
                "counted_side": str(counted_side),
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

        mirror_partner_relation = {
            cell_id((int(coord[0]), int(coord[1]))): cell_id((int(partner[0]), int(partner[1])))
            for coord, partner in sorted(mirror_partner_by_coord.items(), key=lambda item: (int(item[0][0]), int(item[0][1])))
        }
        palette_trace = build_palette_trace(scene.palette)
        scene_entities = build_tile_cell_entities(
            rows=int(scene.rows),
            cols=int(scene.cols),
            attrs_by_coord={
                (int(row), int(col)): {
                    "color_name": str(scene.board_colors[(int(row), int(col))][0]),
                    "fill_rgb": [
                        int(scene.board_colors[(int(row), int(col))][1][0]),
                        int(scene.board_colors[(int(row), int(col))][1][1]),
                        int(scene.board_colors[(int(row), int(col))][1][2]),
                    ],
                    "is_counted_side": bool((int(row), int(col)) in counted_side_coord_set),
                    "is_violation": bool((int(row), int(col)) in violation_coord_set),
                    "is_centerline": bool(mirror_partner_by_coord[(int(row), int(col))] == (int(row), int(col))),
                    "mirror_partner_id": str(mirror_partner_relation[cell_id((int(row), int(col)))]),
                }
                for row in range(int(scene.rows))
                for col in range(int(scene.cols))
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "rectangular_tile_symmetry_board",
                "entities": scene_entities,
                "relations": {
                    "mirror_partner": dict(mirror_partner_relation),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": "symmetry_violation_count_v0",
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "dsl_program": [
                    {"out": "cells", "op": "select", "entity_type": "tile_cell"},
                    {
                        "out": "counted_side_cells",
                        "op": "filter",
                        "in": "cells",
                        "predicate": {"is_counted_side": True},
                    },
                    {
                        "out": "violations",
                        "op": "filter",
                        "in": "counted_side_cells",
                        "predicate": {"is_violation": True},
                    },
                    {
                        "out": "evidence",
                        "op": "project_coords",
                        "in": "violations",
                        "source_coord_space": "tile_grid",
                        "coord_space": "image_pixel",
                        "coord_type": "point_set",
                        "ordering": "row_major",
                    },
                    {"out": "answer", "op": "count", "in": "violations"},
                ],
            },
            "render_spec": build_rectangular_named_color_board_render_spec(scene),
            "render_map": {
                "image_id": "img0",
                "anchors": pixel_anchor_map_from_bboxes(scene.bbox_map),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "mirror_axis_variant": str(mirror_axis_variant),
                "mirror_axis": str(mirror_axis),
                "counted_side": str(counted_side),
                "palette": list(palette_trace),
                "palette_size": int(scene.palette_size),
                "query_selection_strategy": "uniform_over_target_violation_range_with_constructive_board_support",
                "target_violation_count": int(target_violation_count),
                "target_violation_count_range": [int(target_violation_count_min), int(target_violation_count_max)],
                "board_capacity": int(len(pairs)),
                "counted_side_coords": [[int(row), int(col)] for row, col in counted_side_coords],
                "counted_side_ids": [cell_id((int(row), int(col))) for row, col in counted_side_coords],
                "violation_coords": [[int(row), int(col)] for row, col in violation_coords],
                "violation_ids": list(evidence_artifacts["private_witness"]["ids"]),
                "mirror_pairs": [
                    {
                        "reference_coord": [int(reference[0]), int(reference[1])],
                        "reference_id": cell_id((int(reference[0]), int(reference[1]))),
                        "counted_coord": [int(counted[0]), int(counted[1])],
                        "counted_id": cell_id((int(counted[0]), int(counted[1]))),
                        "is_violation": bool((int(counted[0]), int(counted[1])) in violation_coord_set),
                    }
                    for reference, counted in pairs
                ],
                "centerline_coords": [[int(row), int(col)] for row, col in center_coords],
                "answer_value": int(answer_value),
            },
            "witness_symbolic": dict(evidence_artifacts["witness_symbolic"]),
            "projected_evidence": dict(evidence_artifacts["projected_evidence"]),
        }

        board_cell_count = int(scene.rows) * int(scene.cols)
        min_board_cell_count = int(rows_min) * int(cols_min)
        max_board_cell_count = int(rows_max) * int(cols_max)
        complexity = build_tile_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": (
                    0.60
                    * normalize_int_with_bounds(
                        int(board_cell_count),
                        (int(min_board_cell_count), int(max_board_cell_count)),
                    )
                    + 0.40
                    * normalize_int_with_bounds(
                        int(scene.palette_size),
                        (int(palette_size_min), int(palette_size_max)),
                    )
                ),
                "reasoning_load": (
                    0.70
                    * normalize_int_with_bounds(
                        int(answer_value),
                        (int(target_violation_count_min), int(target_violation_count_max)),
                    )
                    + 0.30
                    * clamp_unit_interval(
                        float(answer_value) / float(max(1, len(pairs)))
                    )
                ),
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
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
