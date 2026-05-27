"""Connected-region minimum-distance task on one rectangular tile board."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from trace.core.seed import spawn_rng
from trace.core.task_group_config import get_task_group_defaults
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.shared.bbox_projection import pixel_anchor_map_from_bboxes
from trace.tasks.shared.color_format import format_named_color_with_hex, rgb_to_hex
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
from .shared.grid_graph import (
    cell_id,
    coord_adjacency_to_cell_ids,
    iter_four_neighbors,
    open_grid_adjacency,
)
from .shared.complexity import (
    build_tile_complexity,
    normalize_int_with_bounds,
    resolve_tile_complexity_weights,
)
from .shared.named_color_board import (
    NamedColor,
    RectangularNamedColorBoardTaskDefaults,
    build_palette_trace,
    build_rectangular_named_color_board_render_spec,
    build_rectangular_named_color_board_scene,
)
from .shared.tile_colors import sample_named_tile_palette
from .shared.tile_evidence import coordinate_path_evidence_artifacts, sort_coords_row_major
from .shared.tile_scene import build_tile_cell_entities
from .shared.visual_defaults import load_tile_background_defaults, load_tile_noise_defaults


Coord = Tuple[int, int]
_WHITE_COLOR: NamedColor = ("white", (255, 255, 255))
_TARGET_DISTANCE_SALT = 186


@dataclass(frozen=True)
class _TaskDefaults(RectangularNamedColorBoardTaskDefaults):
    """Stable defaults for connected-region minimum-distance boards."""

    target_distance_min: int = 2
    target_distance_max: int = 6
    component_size_min: int = 1
    component_size_max: int = 6


@dataclass(frozen=True)
class _Placement:
    """One feasible closest-pair placement on a rectangular board."""

    rows: int
    cols: int
    axis: str
    color_a_tip: Coord
    color_b_tip: Coord


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "cell_board_relation")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, dict) else {},
    task_id="cell_board_min_distance_internal",
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_tile_background_defaults(task_group="relation")
POST_IMAGE_NOISE_DEFAULTS = load_tile_noise_defaults(task_group="relation", apply_prob=0.5)
_COMPLEXITY_WEIGHTS = resolve_tile_complexity_weights(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, dict) else {},
    task_id="cell_board_min_distance_internal",
)


def _manhattan_distance(left: Coord, right: Coord) -> int:
    """Return the 4-neighbor step distance between two coordinates."""
    return int(abs(int(left[0]) - int(right[0])) + abs(int(left[1]) - int(right[1])))


def _resolve_target_distance(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    min_value: int,
    max_value: int,
) -> int:
    """Resolve one target answer with a deterministic namespace salt."""
    if int(max_value) < int(min_value):
        raise ValueError("max_value must be >= min_value")
    range_size = max(1, int(max_value) - int(min_value) + 1)
    selection_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:target_distance:{int(_TARGET_DISTANCE_SALT)}",
    )
    return int(min_value) + (int(selection_index) % int(range_size))


def _feasible_placements(
    *,
    rows_min: int,
    rows_max: int,
    cols_min: int,
    cols_max: int,
    target_distance: int,
) -> List[_Placement]:
    """Return all board placements that can realize the requested minimum distance."""
    placements: List[_Placement] = []
    for rows in range(int(rows_min), int(rows_max) + 1):
        for cols in range(int(cols_min), int(cols_max) + 1):
            if int(cols) >= int(target_distance) + 1:
                for row in range(int(rows)):
                    for left_col in range(0, int(cols) - int(target_distance)):
                        right_col = int(left_col) + int(target_distance)
                        placements.append(
                            _Placement(
                                rows=int(rows),
                                cols=int(cols),
                                axis="horizontal",
                                color_a_tip=(int(row), int(left_col)),
                                color_b_tip=(int(row), int(right_col)),
                            )
                        )
            if int(rows) >= int(target_distance) + 1:
                for col in range(int(cols)):
                    for top_row in range(0, int(rows) - int(target_distance)):
                        bottom_row = int(top_row) + int(target_distance)
                        placements.append(
                            _Placement(
                                rows=int(rows),
                                cols=int(cols),
                                axis="vertical",
                                color_a_tip=(int(top_row), int(col)),
                                color_b_tip=(int(bottom_row), int(col)),
                            )
                        )
    return placements


def _allowed_growth_coords(placement: _Placement, *, component_key: str) -> List[Coord]:
    """Return the half-plane growth region that preserves a unique closest pair."""
    rows = int(placement.rows)
    cols = int(placement.cols)
    if str(placement.axis) == "horizontal":
        if str(component_key) == "color_a":
            tip_col = int(placement.color_a_tip[1])
            return [
                (int(row), int(col))
                for row in range(int(rows))
                for col in range(0, int(tip_col))
            ]
        if str(component_key) == "color_b":
            tip_col = int(placement.color_b_tip[1])
            return [
                (int(row), int(col))
                for row in range(int(rows))
                for col in range(int(tip_col) + 1, int(cols))
            ]
    if str(placement.axis) == "vertical":
        if str(component_key) == "color_a":
            tip_row = int(placement.color_a_tip[0])
            return [
                (int(row), int(col))
                for row in range(0, int(tip_row))
                for col in range(int(cols))
            ]
        if str(component_key) == "color_b":
            tip_row = int(placement.color_b_tip[0])
            return [
                (int(row), int(col))
                for row in range(int(tip_row) + 1, int(rows))
                for col in range(int(cols))
            ]
    raise ValueError(f"unsupported placement/component: axis={placement.axis}, component_key={component_key}")


def _grow_connected_component(
    rng,
    *,
    tip: Coord,
    allowed_coords: Iterable[Coord],
    target_size: int,
) -> List[Coord]:
    """Grow one connected component from a fixed tip into a permitted region."""
    component = {(int(tip[0]), int(tip[1]))}
    remaining = {(int(row), int(col)) for row, col in allowed_coords}
    while len(component) < int(target_size):
        frontier = sort_coords_row_major(
            [
                (int(neighbor[0]), int(neighbor[1]))
                for coord in component
                for neighbor in iter_four_neighbors(coord)
                if (int(neighbor[0]), int(neighbor[1])) in remaining
            ]
        )
        if not frontier:
            break
        next_coord = frontier[int(rng.randint(0, len(frontier) - 1))]
        component.add((int(next_coord[0]), int(next_coord[1])))
        remaining.remove((int(next_coord[0]), int(next_coord[1])))
    return sort_coords_row_major(component)


def _sample_component_coords(
    rng,
    *,
    tip: Coord,
    allowed_coords: Sequence[Coord],
    component_size_min: int,
    component_size_max: int,
) -> List[Coord]:
    """Sample one connected component rooted at `tip` inside `allowed_coords`."""
    capacity = 1 + int(len(allowed_coords))
    effective_max = min(int(component_size_max), int(capacity))
    effective_min = min(int(component_size_min), int(effective_max))
    target_size = int(rng.randint(int(effective_min), int(effective_max)))
    return _grow_connected_component(
        rng,
        tip=(int(tip[0]), int(tip[1])),
        allowed_coords=list(allowed_coords),
        target_size=int(target_size),
    )


def _closest_pairs(left_coords: Sequence[Coord], right_coords: Sequence[Coord]) -> Tuple[int, List[Tuple[Coord, Coord]]]:
    """Return the minimum cross-component distance and all pairs that attain it."""
    min_distance: int | None = None
    winning_pairs: List[Tuple[Coord, Coord]] = []
    for left in left_coords:
        for right in right_coords:
            distance = _manhattan_distance(left, right)
            if min_distance is None or int(distance) < int(min_distance):
                min_distance = int(distance)
                winning_pairs = [((int(left[0]), int(left[1])), (int(right[0]), int(right[1])))]
            elif int(distance) == int(min_distance):
                winning_pairs.append(((int(left[0]), int(left[1])), (int(right[0]), int(right[1]))))
    if min_distance is None:
        raise ValueError("both components must contain at least one cell")
    return int(min_distance), list(winning_pairs)


def _straight_path(start: Coord, goal: Coord) -> List[Coord]:
    """Return the unique straight shortest path between aligned endpoints."""
    start_row, start_col = int(start[0]), int(start[1])
    goal_row, goal_col = int(goal[0]), int(goal[1])
    if int(start_row) == int(goal_row):
        step = 1 if int(goal_col) >= int(start_col) else -1
        return [
            (int(start_row), int(col))
            for col in range(int(start_col), int(goal_col) + int(step), int(step))
        ]
    if int(start_col) == int(goal_col):
        step = 1 if int(goal_row) >= int(start_row) else -1
        return [
            (int(row), int(start_col))
            for row in range(int(start_row), int(goal_row) + int(step), int(step))
        ]
    raise ValueError("straight path requires aligned endpoints")


class TileMinDistanceTask:
    """Return the minimum orthogonal distance between two connected colored regions."""

    task_id = "cell_board_min_distance_internal"
    domain = "puzzles"
    task_group = "cell_board_relation"
    default_dataset_enabled = False

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
        target_distance_min = int(
            params.get(
                "target_distance_min",
                group_default(_GEN_DEFAULTS, "target_distance_min", int(_DEFAULTS.target_distance_min)),
            )
        )
        target_distance_max = int(
            params.get(
                "target_distance_max",
                group_default(_GEN_DEFAULTS, "target_distance_max", int(_DEFAULTS.target_distance_max)),
            )
        )
        component_size_min = int(
            params.get(
                "component_size_min",
                group_default(_GEN_DEFAULTS, "component_size_min", int(_DEFAULTS.component_size_min)),
            )
        )
        component_size_max = int(
            params.get(
                "component_size_max",
                group_default(_GEN_DEFAULTS, "component_size_max", int(_DEFAULTS.component_size_max)),
            )
        )
        if int(target_distance_min) < 1:
            raise ValueError("target_distance_min must be >= 1")
        if int(target_distance_min) > int(target_distance_max):
            raise ValueError("target_distance_min must be <= target_distance_max")
        if int(component_size_min) < 1:
            raise ValueError("component_size_min must be >= 1")
        if int(component_size_min) > int(component_size_max):
            raise ValueError("component_size_min must be <= component_size_max")

        effective_target_distance_max = min(
            int(target_distance_max),
            max(int(rows_max), int(cols_max)) - 1,
        )
        if int(effective_target_distance_max) < int(target_distance_min):
            raise ValueError("target distance range is infeasible for the resolved board bounds")
        target_distance = _resolve_target_distance(
            params=params,
            instance_seed=int(instance_seed),
            task_id=self.task_id,
            min_value=int(target_distance_min),
            max_value=int(effective_target_distance_max),
        )

        placements = _feasible_placements(
            rows_min=int(rows_min),
            rows_max=int(rows_max),
            cols_min=int(cols_min),
            cols_max=int(cols_max),
            target_distance=int(target_distance),
        )
        if not placements:
            raise RuntimeError("failed to find a feasible board placement for the target distance")
        placement = placements[int(task_rng.randint(0, len(placements) - 1))]

        color_a, color_b = sample_named_tile_palette(task_rng, palette_size=2)
        color_a_name, color_a_rgb = str(color_a[0]), tuple(int(value) for value in color_a[1])
        color_b_name, color_b_rgb = str(color_b[0]), tuple(int(value) for value in color_b[1])
        background_name, background_rgb = str(_WHITE_COLOR[0]), tuple(int(value) for value in _WHITE_COLOR[1])

        color_a_coords = _sample_component_coords(
            task_rng,
            tip=(int(placement.color_a_tip[0]), int(placement.color_a_tip[1])),
            allowed_coords=_allowed_growth_coords(placement, component_key="color_a"),
            component_size_min=int(component_size_min),
            component_size_max=int(component_size_max),
        )
        color_b_coords = _sample_component_coords(
            task_rng,
            tip=(int(placement.color_b_tip[0]), int(placement.color_b_tip[1])),
            allowed_coords=_allowed_growth_coords(placement, component_key="color_b"),
            component_size_min=int(component_size_min),
            component_size_max=int(component_size_max),
        )

        min_distance_value, closest_pairs = _closest_pairs(color_a_coords, color_b_coords)
        if int(min_distance_value) != int(target_distance):
            raise RuntimeError("constructed relation scene violated the requested minimum distance")
        expected_pair = (
            (int(placement.color_a_tip[0]), int(placement.color_a_tip[1])),
            (int(placement.color_b_tip[0]), int(placement.color_b_tip[1])),
        )
        if len(closest_pairs) != 1 or closest_pairs[0] != expected_pair:
            raise RuntimeError("constructed relation scene did not preserve a unique closest pair")
        shortest_path_coords = _straight_path(expected_pair[0], expected_pair[1])

        board_colors: Dict[Coord, NamedColor] = {
            (int(row), int(col)): (str(background_name), tuple(int(value) for value in background_rgb))
            for row in range(int(placement.rows))
            for col in range(int(placement.cols))
        }
        for coord in color_a_coords:
            board_colors[(int(coord[0]), int(coord[1]))] = (
                str(color_a_name),
                tuple(int(value) for value in color_a_rgb),
            )
        for coord in color_b_coords:
            board_colors[(int(coord[0]), int(coord[1]))] = (
                str(color_b_name),
                tuple(int(value) for value in color_b_rgb),
            )

        scene = build_rectangular_named_color_board_scene(
            instance_seed,
            task_rng=task_rng,
            params=params,
            generation_defaults=_GEN_DEFAULTS,
            rendering_defaults=_RENDER_DEFAULTS,
            background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
            noise_defaults=POST_IMAGE_NOISE_DEFAULTS,
            defaults=_DEFAULTS,
            rows=int(placement.rows),
            cols=int(placement.cols),
            board_colors=board_colors,
        )

        evidence_artifacts = coordinate_path_evidence_artifacts(
            coords=shortest_path_coords,
            bbox_map=scene.bbox_map,
        )
        answer_value = int(target_distance)
        open_blocked = [[False for _ in range(int(scene.cols))] for _ in range(int(scene.rows))]
        adjacency_open = coord_adjacency_to_cell_ids(
            open_grid_adjacency(rows=int(scene.rows), cols=int(scene.cols), blocked=open_blocked)
        )

        color_a_label = format_named_color_with_hex(color_a_name, color_a_rgb)
        color_b_label = format_named_color_with_hex(color_b_name, color_b_rgb)
        background_color_label = format_named_color_with_hex(background_name, background_rgb)

        prompt_defaults_all = dict(_PROMPT_DEFAULTS if isinstance(_PROMPT_DEFAULTS, dict) else {})
        prompt_defaults = required_group_defaults(
            prompt_defaults_all,
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
            prompt_defaults_all,
            evidence_value=[[168, 168], [216, 168], [264, 168], [312, 168]],
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
                "background_color": str(background_color_label),
                "color_a": str(color_a_label),
                "color_b": str(color_b_label),
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

        color_a_coord_set = {(int(row), int(col)) for row, col in color_a_coords}
        color_b_coord_set = {(int(row), int(col)) for row, col in color_b_coords}
        path_coord_set = {(int(row), int(col)) for row, col in shortest_path_coords}
        endpoint_coord_set = {expected_pair[0], expected_pair[1]}
        scene_entities = build_tile_cell_entities(
            rows=int(scene.rows),
            cols=int(scene.cols),
            attrs_by_coord={
                (int(row), int(col)): {
                    "color_name": str(scene.board_colors[(int(row), int(col))][0]),
                    "fill_rgb": [int(value) for value in scene.board_colors[(int(row), int(col))][1]],
                    "is_background": bool((int(row), int(col)) not in color_a_coord_set and (int(row), int(col)) not in color_b_coord_set),
                    "is_color_a": bool((int(row), int(col)) in color_a_coord_set),
                    "is_color_b": bool((int(row), int(col)) in color_b_coord_set),
                    "is_min_distance_endpoint": bool((int(row), int(col)) in endpoint_coord_set),
                    "is_min_distance_path": bool((int(row), int(col)) in path_coord_set),
                }
                for row in range(int(scene.rows))
                for col in range(int(scene.cols))
            },
        )

        closest_pair_ids = [cell_id(expected_pair[0]), cell_id(expected_pair[1])]
        shortest_path_ids = [cell_id(coord) for coord in shortest_path_coords]
        trace_payload = {
            "scene_ir": {
                "scene_kind": "rectangular_tile_min_distance_board",
                "entities": scene_entities,
                "relations": {"adjacency_open": adjacency_open},
            },
            "query_spec": {
                "query_variant": "min_distance",
                "template_id": "min_distance_v0",
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "dsl_program": [
                    {"out": "cells", "op": "select", "entity_type": "tile_cell"},
                    {"out": "color_a_tiles", "op": "filter", "in": "cells", "predicate": {"is_color_a": True}},
                    {"out": "color_b_tiles", "op": "filter", "in": "cells", "predicate": {"is_color_b": True}},
                    {
                        "out": "closest_pair_path",
                        "op": "shortest_path",
                        "relation": "adjacency_open",
                        "start": str(closest_pair_ids[0]),
                        "goal": str(closest_pair_ids[1]),
                        "expect_unique": True,
                    },
                    {
                        "out": "evidence",
                        "op": "project_coords",
                        "in": "closest_pair_path",
                        "source_coord_space": "tile_grid",
                        "coord_space": "image_pixel",
                        "coord_type": "point_sequence",
                        "ordering": "path_order",
                    },
                    {
                        "out": "answer",
                        "op": "min_distance_between_sets",
                        "left": "color_a_tiles",
                        "right": "color_b_tiles",
                        "metric": "orthogonal_steps",
                    },
                ],
            },
            "render_spec": build_rectangular_named_color_board_render_spec(scene),
            "render_map": {
                "image_id": "img0",
                "anchors": pixel_anchor_map_from_bboxes(scene.bbox_map),
            },
            "execution_trace": {
                "query_variant": "min_distance",
                "rows": int(scene.rows),
                "cols": int(scene.cols),
                "target_distance_range": [int(target_distance_min), int(effective_target_distance_max)],
                "target_distance": int(target_distance),
                "component_size_range": [int(component_size_min), int(component_size_max)],
                "distance_axis": str(placement.axis),
                "background_color_name": str(background_name),
                "background_color_rgb": [int(value) for value in background_rgb],
                "background_color_hex": str(rgb_to_hex(background_rgb)),
                "background_color_label": str(background_color_label),
                "color_a_name": str(color_a_name),
                "color_a_rgb": [int(value) for value in color_a_rgb],
                "color_a_hex": str(rgb_to_hex(color_a_rgb)),
                "color_a_label": str(color_a_label),
                "color_b_name": str(color_b_name),
                "color_b_rgb": [int(value) for value in color_b_rgb],
                "color_b_hex": str(rgb_to_hex(color_b_rgb)),
                "color_b_label": str(color_b_label),
                "palette": build_palette_trace(scene.palette),
                "color_a_tip_coord": [int(expected_pair[0][0]), int(expected_pair[0][1])],
                "color_a_tip_id": str(closest_pair_ids[0]),
                "color_b_tip_coord": [int(expected_pair[1][0]), int(expected_pair[1][1])],
                "color_b_tip_id": str(closest_pair_ids[1]),
                "closest_pair_coords": [
                    [int(expected_pair[0][0]), int(expected_pair[0][1])],
                    [int(expected_pair[1][0]), int(expected_pair[1][1])],
                ],
                "closest_pair_ids": list(closest_pair_ids),
                "color_a_coords": [[int(row), int(col)] for row, col in color_a_coords],
                "color_a_ids": [cell_id(coord) for coord in color_a_coords],
                "color_b_coords": [[int(row), int(col)] for row, col in color_b_coords],
                "color_b_ids": [cell_id(coord) for coord in color_b_coords],
                "color_a_component_count": 1,
                "color_b_component_count": 1,
                "unique_closest_pair": True,
                "shortest_path_coords": [[int(row), int(col)] for row, col in shortest_path_coords],
                "shortest_path_ids": list(shortest_path_ids),
                "answer_value": int(answer_value),
            },
            "witness_symbolic": dict(evidence_artifacts["witness_symbolic"]),
            "projected_evidence": dict(evidence_artifacts["projected_evidence"]),
        }

        min_board_cell_count = int(rows_min) * int(cols_min)
        max_board_cell_count = int(rows_max) * int(cols_max)
        total_colored_cells = int(len(color_a_coords) + len(color_b_coords))
        complexity = build_tile_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": (
                    0.55
                    * normalize_int_with_bounds(
                        int(scene.rows) * int(scene.cols),
                        (int(min_board_cell_count), int(max_board_cell_count)),
                    )
                    + 0.45
                    * normalize_int_with_bounds(
                        int(total_colored_cells),
                        (2 * int(component_size_min), 2 * int(component_size_max)),
                    )
                ),
                "reasoning_load": (
                    0.70
                    * normalize_int_with_bounds(
                        int(answer_value),
                        (int(target_distance_min), int(effective_target_distance_max)),
                    )
                    + 0.30
                    * normalize_int_with_bounds(
                        int(total_colored_cells),
                        (2 * int(component_size_min), 2 * int(component_size_max)),
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
            query_variant="min_distance",
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
