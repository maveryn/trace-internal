"""Single-board rectangular-tile enclosed-hole counting task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import pixel_anchor_map_from_bboxes
from ...shared.color_format import format_named_color_with_hex, rgb_to_hex
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import resolve_prompt_json_examples
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.grid_graph import (
    active_coord_adjacency,
    cell_id,
    connected_components_for_active_coords,
    coord_adjacency_to_cell_ids,
    iter_four_neighbors,
)
from ..shared.named_color_board import (
    RectangularNamedColorBoardTaskDefaults,
    build_color_board_scene_entities,
    build_palette_trace,
    build_rectangular_named_color_board_render_spec,
    build_rectangular_named_color_board_scene,
)
from ..shared.tile_evidence import coordinate_set_evidence_artifacts, sort_coords_row_major
from .background_defaults import POST_IMAGE_BACKGROUND_DEFAULTS
from .noise_defaults import POST_IMAGE_NOISE_DEFAULTS


Coord = Tuple[int, int]
NamedColor = Tuple[str, Tuple[int, int, int]]

_BLACK_COLOR: NamedColor = ("black", (0, 0, 0))
_WHITE_COLOR: NamedColor = ("white", (255, 255, 255))


@dataclass(frozen=True)
class _TaskDefaults(RectangularNamedColorBoardTaskDefaults):
    """Stable defaults for the rectangular tile topology task group."""

    answer_min: int = 1
    answer_max: int = 5


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("tile", "topology")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, dict) else {},
    task_id="task_tile_topology_hole_count",
)


def _board_coords(rows: int, cols: int) -> List[Coord]:
    """Return all dense board coordinates in row-major order."""
    return [(int(row), int(col)) for row in range(int(rows)) for col in range(int(cols))]


def _touches_boundary(coord: Coord, *, rows: int, cols: int) -> bool:
    """Return whether one coordinate lies on the outer board boundary."""
    row, col = int(coord[0]), int(coord[1])
    return bool(row == 0 or col == 0 or row == int(rows) - 1 or col == int(cols) - 1)


def _safe_hole_zone_coords(rows: int, cols: int) -> List[Coord]:
    """Return interior coordinates that keep a one-cell black moat from the white boundary."""
    if int(rows) < 5 or int(cols) < 5:
        return []
    return [
        (int(row), int(col))
        for row in range(2, int(rows) - 2)
        for col in range(2, int(cols) - 2)
    ]


def _hole_capacity(rows: int, cols: int) -> int:
    """Return the maximum guaranteed hole count supported by checkerboard singleton seeds."""
    zone = _safe_hole_zone_coords(int(rows), int(cols))
    if not zone:
        return 0
    parity_counts = [0, 0]
    for row, col in zone:
        parity_counts[(int(row) + int(col)) % 2] += 1
    return int(max(parity_counts))


def _boundary_white_coords(rows: int, cols: int) -> List[Coord]:
    """Return the canonical exterior white component for the board boundary."""
    return [
        coord
        for coord in _board_coords(int(rows), int(cols))
        if _touches_boundary(coord, rows=int(rows), cols=int(cols))
    ]


def _white_components_from_holes(rows: int, cols: int, hole_regions: Sequence[Sequence[Coord]]) -> List[List[Coord]]:
    """Return all white components as the exterior region plus enclosed holes."""
    white_coords = set(_boundary_white_coords(int(rows), int(cols)))
    for region in hole_regions:
        white_coords.update((int(row), int(col)) for row, col in region)
    return [
        sort_coords_row_major(component)
        for component in connected_components_for_active_coords(sorted(white_coords))
    ]


def _analyze_board(rows: int, cols: int, hole_regions: Sequence[Sequence[Coord]]) -> Dict[str, Any]:
    """Compute white-hole topology and black-wall connectivity for one proposed board."""
    white_components = _white_components_from_holes(int(rows), int(cols), hole_regions)
    exterior_white_components: List[List[Coord]] = []
    hole_components: List[List[Coord]] = []
    for component in white_components:
        if any(_touches_boundary(coord, rows=int(rows), cols=int(cols)) for coord in component):
            exterior_white_components.append(sort_coords_row_major(component))
        else:
            hole_components.append(sort_coords_row_major(component))

    all_coords = set(_board_coords(int(rows), int(cols)))
    white_coords = {
        (int(row), int(col))
        for component in white_components
        for row, col in component
    }
    black_coords = sorted(all_coords.difference(white_coords), key=lambda item: (int(item[0]), int(item[1])))
    black_components = [
        sort_coords_row_major(component)
        for component in connected_components_for_active_coords(black_coords)
    ]
    return {
        "white_components": list(white_components),
        "exterior_white_components": list(exterior_white_components),
        "hole_components": sorted(
            [list(component) for component in hole_components],
            key=lambda component: (int(component[0][0]), int(component[0][1])),
        ),
        "black_components": list(black_components),
        "white_coords": sort_coords_row_major(list(white_coords)),
        "black_coords": sort_coords_row_major(black_coords),
    }


def _is_valid_hole_board(rows: int, cols: int, hole_regions: Sequence[Sequence[Coord]], target_hole_count: int) -> bool:
    """Return whether one candidate board has the required topology contract."""
    analysis = _analyze_board(int(rows), int(cols), hole_regions)
    return bool(
        len(analysis["exterior_white_components"]) == 1
        and len(analysis["hole_components"]) == int(target_hole_count)
        and len(analysis["black_components"]) == 1
        and len(analysis["black_coords"]) > 0
    )


def _iter_growth_candidates(region: Sequence[Coord], *, rows: int, cols: int, occupied_white: Iterable[Coord]) -> List[Coord]:
    """Return legal candidate cells for enlarging one enclosed hole without reaching the boundary moat."""
    occupied = {(int(row), int(col)) for row, col in occupied_white}
    safe_zone = set(_safe_hole_zone_coords(int(rows), int(cols)))
    candidates = set()
    for cell in region:
        for neighbor in iter_four_neighbors((int(cell[0]), int(cell[1]))):
            if neighbor not in safe_zone or neighbor in occupied:
                continue
            candidates.add((int(neighbor[0]), int(neighbor[1])))
    return sort_coords_row_major(list(candidates))


def _sample_hole_regions(rng, *, rows: int, cols: int, target_hole_count: int, max_attempts: int) -> List[List[Coord]]:
    """Construct enclosed white holes inside one connected black wall mass."""
    safe_zone = _safe_hole_zone_coords(int(rows), int(cols))
    parity_options = [
        [
            (int(row), int(col))
            for row, col in safe_zone
            if (int(row) + int(col)) % 2 == int(parity)
        ]
        for parity in (0, 1)
    ]
    feasible_seed_sets = [
        option for option in parity_options if len(option) >= int(target_hole_count)
    ]
    if not feasible_seed_sets:
        raise RuntimeError("no feasible singleton hole seeds for requested target hole count")

    for _ in range(int(max_attempts)):
        seed_pool = list(rng.choice(feasible_seed_sets))
        seeds = rng.sample(seed_pool, int(target_hole_count))
        hole_regions: List[List[Coord]] = [[(int(seed[0]), int(seed[1]))] for seed in seeds]
        if not _is_valid_hole_board(int(rows), int(cols), hole_regions, int(target_hole_count)):
            continue

        growth_budget = int(rng.randint(0, max(1, int(target_hole_count))))
        for _growth_step in range(int(growth_budget)):
            occupied_white = [
                coord
                for region in hole_regions
                for coord in region
            ]
            candidate_moves: List[Tuple[int, Coord]] = []
            for index, region in enumerate(hole_regions):
                for candidate in _iter_growth_candidates(
                    region,
                    rows=int(rows),
                    cols=int(cols),
                    occupied_white=occupied_white,
                ):
                    candidate_moves.append((int(index), (int(candidate[0]), int(candidate[1]))))
            if not candidate_moves:
                break
            rng.shuffle(candidate_moves)

            accepted = False
            for hole_index, candidate in candidate_moves:
                proposed = [
                    [tuple(int(value) for value in coord) for coord in region]
                    for region in hole_regions
                ]
                proposed[int(hole_index)].append((int(candidate[0]), int(candidate[1])))
                if not _is_valid_hole_board(int(rows), int(cols), proposed, int(target_hole_count)):
                    continue
                hole_regions = [
                    sort_coords_row_major(region)
                    for region in proposed
                ]
                accepted = True
                break
            if not accepted:
                break

        analysis = _analyze_board(int(rows), int(cols), hole_regions)
        if len(analysis["hole_components"]) == int(target_hole_count):
            return [
                sort_coords_row_major(component)
                for component in analysis["hole_components"]
            ]

    raise RuntimeError("failed to sample enclosed hole structure within configured constraints")


def _board_colors_for_holes(rows: int, cols: int, hole_regions: Sequence[Sequence[Coord]]) -> Dict[Coord, NamedColor]:
    """Build the rendered black/white board coloring from the sampled hole regions."""
    white_coords = {
        (int(row), int(col))
        for row, col in _boundary_white_coords(int(rows), int(cols))
    }
    for region in hole_regions:
        white_coords.update((int(row), int(col)) for row, col in region)
    return {
        coord: _WHITE_COLOR if coord in white_coords else _BLACK_COLOR
        for coord in _board_coords(int(rows), int(cols))
    }


@register_task
class TileHoleCountTask:
    """Count enclosed white holes formed by black tiles on one labeled rectangular board."""

    task_id = "task_tile_topology_hole_count"
    domain = "tile"
    task_group = "topology"

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
        answer_min = int(
            params.get(
                "answer_min",
                group_default(_GEN_DEFAULTS, "answer_min", int(_DEFAULTS.answer_min)),
            )
        )
        answer_max = int(
            params.get(
                "answer_max",
                group_default(_GEN_DEFAULTS, "answer_max", int(_DEFAULTS.answer_max)),
            )
        )
        if int(answer_min) <= 0:
            raise ValueError(f"answer_min must be > 0 for {self.task_id}")
        if int(answer_min) > int(answer_max):
            raise ValueError(f"answer_min must be <= answer_max for {self.task_id}")

        feasible_shapes = [
            (int(rows), int(cols))
            for rows in range(int(rows_min), int(rows_max) + 1)
            for cols in range(int(cols_min), int(cols_max) + 1)
            if _hole_capacity(int(rows), int(cols)) > 0
        ]
        if not feasible_shapes:
            raise RuntimeError("no feasible board shapes can realize enclosed holes with the configured row/col bounds")

        feasible_global_max = max(_hole_capacity(int(rows), int(cols)) for rows, cols in feasible_shapes)
        effective_answer_max = min(int(answer_max), int(feasible_global_max))
        if int(effective_answer_max) < int(answer_min):
            raise RuntimeError("configured answer range exceeds the feasible enclosed-hole capacity of the board bounds")

        target_hole_count = int(task_rng.randint(int(answer_min), int(effective_answer_max)))
        target_hole_count_range = [int(answer_min), int(effective_answer_max)]
        target_shapes = [
            (int(rows), int(cols))
            for rows, cols in feasible_shapes
            if _hole_capacity(int(rows), int(cols)) >= int(target_hole_count)
        ]
        if not target_shapes:
            raise RuntimeError("failed to find a board shape that can realize the sampled enclosed-hole target")
        rows, cols = task_rng.choice(target_shapes)

        hole_regions = _sample_hole_regions(
            task_rng,
            rows=int(rows),
            cols=int(cols),
            target_hole_count=int(target_hole_count),
            max_attempts=int(max_attempts),
        )
        analysis = _analyze_board(int(rows), int(cols), hole_regions)
        board_colors = _board_colors_for_holes(int(rows), int(cols), hole_regions)

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
            palette=[_WHITE_COLOR, _BLACK_COLOR],
            board_colors=board_colors,
        )

        hole_components = [
            sort_coords_row_major(component)
            for component in analysis["hole_components"]
        ]
        witness_coords = sort_coords_row_major(
            [component[0] for component in hole_components]
        )
        evidence_artifacts = coordinate_set_evidence_artifacts(
            coords=witness_coords,
            bbox_map=scene.bbox_map,
        )

        black_color_label = format_named_color_with_hex(_BLACK_COLOR[0], _BLACK_COLOR[1])
        white_color_label = format_named_color_with_hex(_WHITE_COLOR[0], _WHITE_COLOR[1])
        black_color_hex = rgb_to_hex(_BLACK_COLOR[1])
        white_color_hex = rgb_to_hex(_WHITE_COLOR[1])
        hole_index_by_coord = {
            (int(row), int(col)): int(hole_index)
            for hole_index, component in enumerate(hole_components)
            for row, col in component
        }
        witness_set = {(int(row), int(col)) for row, col in witness_coords}
        exterior_white_set = {
            (int(row), int(col))
            for component in analysis["exterior_white_components"]
            for row, col in component
        }
        scene_entities = build_color_board_scene_entities(
            scene,
            query_color_name=str(_WHITE_COLOR[0]),
            extra_attrs_by_coord={
                coord: {
                    "is_white": bool(coord in exterior_white_set or coord in hole_index_by_coord),
                    "is_black": bool(coord not in exterior_white_set and coord not in hole_index_by_coord),
                    "is_wall": bool(coord not in exterior_white_set and coord not in hole_index_by_coord),
                    "is_hole": bool(coord in hole_index_by_coord),
                    "is_exterior_white": bool(coord in exterior_white_set),
                    "is_hole_witness": bool(coord in witness_set),
                    "hole_index": int(hole_index_by_coord[coord]) if coord in hole_index_by_coord else None,
                }
                for coord in _board_coords(int(rows), int(cols))
            },
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
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_bundle_id = str(prompt_defaults["bundle_id"])
        prompt_task_family_key = str(prompt_defaults["task_family_key"])
        prompt_task_key = str(prompt_defaults["task_key"])
        json_example, json_example_answer_only = resolve_prompt_json_examples(
            all_prompt_defaults,
            evidence_value=[[2, 2], [4, 4]],
            answer_type="integer",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=prompt_bundle_id,
            task_family_key=prompt_task_family_key,
            task_key=prompt_task_key,
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "rows": int(rows),
                "cols": int(cols),
                "wall_color": str(black_color_label),
                "hole_color": str(white_color_label),
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
                "relations": {
                    "adjacency_white": coord_adjacency_to_cell_ids(
                        active_coord_adjacency(analysis["white_coords"])
                    ),
                    "adjacency_black": coord_adjacency_to_cell_ids(
                        active_coord_adjacency(analysis["black_coords"])
                    ),
                },
            },
            "query_spec": {
                "task_variant": "hole_count",
                "template_id": "hole_count_v1",
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "dsl_program": [
                    {"out": "cells", "op": "select", "entity_type": "tile_cell"},
                    {
                        "out": "white_cells",
                        "op": "filter",
                        "in": "cells",
                        "predicate": {"color_name": str(_WHITE_COLOR[0])},
                    },
                    {
                        "out": "white_components",
                        "op": "connected_components",
                        "in": "white_cells",
                        "connectivity": "4_neighbor",
                    },
                    {
                        "out": "holes",
                        "op": "filter_components",
                        "in": "white_components",
                        "predicate": {"touches_boundary": False},
                    },
                    {
                        "out": "evidence",
                        "op": "component_representatives",
                        "in": "holes",
                        "selector": "row_major_min_coord",
                        "coord_space": "tile_grid",
                        "coord_type": "grid_point_set",
                        "ordering": "row_major",
                    },
                    {"out": "answer", "op": "count", "in": "holes"},
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
                "task_variant": "hole_count",
                "rows": int(rows),
                "cols": int(cols),
                "palette": list(build_palette_trace(scene.palette)),
                "palette_size": int(scene.palette_size),
                "wall_color_name": str(_BLACK_COLOR[0]),
                "wall_color_rgb": [int(_BLACK_COLOR[1][0]), int(_BLACK_COLOR[1][1]), int(_BLACK_COLOR[1][2])],
                "wall_color_hex": str(black_color_hex),
                "wall_color_label": str(black_color_label),
                "hole_color_name": str(_WHITE_COLOR[0]),
                "hole_color_rgb": [int(_WHITE_COLOR[1][0]), int(_WHITE_COLOR[1][1]), int(_WHITE_COLOR[1][2])],
                "hole_color_hex": str(white_color_hex),
                "hole_color_label": str(white_color_label),
                "target_hole_count_range": list(target_hole_count_range),
                "target_hole_count": int(target_hole_count),
                "white_component_count": int(len(analysis["white_components"])),
                "black_component_count": int(len(analysis["black_components"])),
                "exterior_white_component_count": int(len(analysis["exterior_white_components"])),
                "exterior_white_coords": [
                    [int(row), int(col)]
                    for component in analysis["exterior_white_components"]
                    for row, col in component
                ],
                "black_coords": [[int(row), int(col)] for row, col in analysis["black_coords"]],
                "black_ids": [cell_id(coord) for coord in analysis["black_coords"]],
                "hole_witness_coords": [[int(row), int(col)] for row, col in witness_coords],
                "hole_witness_ids": list(evidence_artifacts["witness_symbolic"]["ids"]),
                "holes": [
                    {
                        "hole_index": int(index),
                        "coords": [[int(row), int(col)] for row, col in component],
                        "ids": [cell_id(coord) for coord in component],
                        "area": int(len(component)),
                        "witness_coord": [int(component[0][0]), int(component[0][1])],
                        "witness_id": str(cell_id(component[0])),
                    }
                    for index, component in enumerate(hole_components)
                ],
                "answer_value": int(target_hole_count),
            },
            "witness_symbolic": dict(evidence_artifacts["witness_symbolic"]),
            "projected_evidence": dict(evidence_artifacts["projected_evidence"]),
        }

        hole_areas = [int(len(component)) for component in hole_components]
        complexity = TaskComplexity(
            complexity_score=min(
                1.0,
                max(
                    0.0,
                    (
                        (float(int(rows) * int(cols)) / 49.0)
                        + (float(target_hole_count) / 5.0)
                        + (float(sum(hole_areas)) / float(max(1, int(rows) * int(cols))))
                    )
                    / 3.0,
                ),
            ),
            complexity_components={
                "rows": int(rows),
                "cols": int(cols),
                "hole_count": int(target_hole_count),
                "hole_areas": [int(area) for area in hole_areas],
                "black_component_count": int(len(analysis["black_components"])),
            },
        )

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(target_hole_count)),
            evidence_gt=TypedValue(
                type=str(evidence_artifacts["evidence_type"]),
                value=list(evidence_artifacts["evidence_value"]),
            ),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant="hole_count",
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
