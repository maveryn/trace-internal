"""Single-board rectangular-tile same-color-degree counting task."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

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
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import resolve_prompt_json_examples
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.grid_graph import cell_id, degree_by_active_coord
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

_DEFAULTS = RectangularNamedColorBoardTaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("tile", "graph")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, dict) else {},
    task_id="task_tile_graph_degree_count",
)


def _build_color_degree_catalog(scene) -> Tuple[List[Dict[str, Any]], Dict[Coord, int]]:
    """Return per-color same-color degree summaries plus per-cell degree annotations."""
    catalog: List[Dict[str, Any]] = []
    degree_by_coord_all: Dict[Coord, int] = {}
    for palette_color_name, palette_color_rgb in scene.palette:
        matching_coords = sort_coords_row_major(
            [
                (int(row), int(col))
                for (row, col), (name, _rgb) in scene.board_colors.items()
                if str(name) == str(palette_color_name)
            ]
        )
        if not matching_coords:
            raise RuntimeError("sampled query color must appear at least once on the board")
        degree_map = degree_by_active_coord(matching_coords)
        for coord, value in degree_map.items():
            degree_by_coord_all[(int(coord[0]), int(coord[1]))] = int(value)
        coords_by_degree: Dict[int, List[List[int]]] = {}
        for coord, value in degree_map.items():
            coords_by_degree.setdefault(int(value), []).append([int(coord[0]), int(coord[1])])
        catalog.append(
            {
                "query_color_name": str(palette_color_name),
                "query_color_rgb": [int(palette_color_rgb[0]), int(palette_color_rgb[1]), int(palette_color_rgb[2])],
                "matching_coords": [[int(row), int(col)] for row, col in matching_coords],
                "degree_by_coord": {
                    cell_id((int(coord[0]), int(coord[1]))): int(value)
                    for coord, value in degree_map.items()
                },
                "coords_by_degree": {
                    int(degree): [
                        [int(coord[0]), int(coord[1])]
                        for coord in sort_coords_row_major(
                            [(int(item[0]), int(item[1])) for item in coords]
                        )
                    ]
                    for degree, coords in coords_by_degree.items()
                },
            }
        )
    return catalog, degree_by_coord_all


@register_task
class TileGraphDegreeCountTask:
    """Count tiles whose same-color orthogonal-neighbor degree matches one queried value."""

    task_id = "task_tile_graph_degree_count"
    domain = "tile"
    task_group = "graph"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        task_rng = spawn_rng(instance_seed, "task")
        _rows_min, rows_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="rows_min",
            max_key="rows_max",
            fallback_min=int(_DEFAULTS.rows_min),
            fallback_max=int(_DEFAULTS.rows_max),
            context=f"generation defaults for {self.task_id}",
        )
        _cols_min, cols_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="cols_min",
            max_key="cols_max",
            fallback_min=int(_DEFAULTS.cols_min),
            fallback_max=int(_DEFAULTS.cols_max),
            context=f"generation defaults for {self.task_id}",
        )
        palette_size_min, _palette_size_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="palette_size_min",
            max_key="palette_size_max",
            fallback_min=int(_DEFAULTS.palette_size_min),
            fallback_max=int(_DEFAULTS.palette_size_max),
            context=f"generation defaults for {self.task_id}",
        )
        target_degree_min = int(
            params.get(
                "target_degree_min",
                group_default(_GEN_DEFAULTS, "target_degree_min", 0),
            )
        )
        target_degree_max = int(
            params.get(
                "target_degree_max",
                group_default(_GEN_DEFAULTS, "target_degree_max", 3),
            )
        )
        if int(target_degree_min) > int(target_degree_max):
            raise ValueError("target_degree_min must be <= target_degree_max")

        target_answer_count_min = int(
            params.get(
                "target_answer_count_min",
                group_default(_GEN_DEFAULTS, "target_answer_count_min", 1),
            )
        )
        target_answer_count_max = int(
            params.get(
                "target_answer_count_max",
                group_default(_GEN_DEFAULTS, "target_answer_count_max", 10),
            )
        )
        if int(target_answer_count_min) > int(target_answer_count_max):
            raise ValueError("target_answer_count_min must be <= target_answer_count_max")

        max_board_cells = int(rows_max) * int(cols_max)
        feasible_target_answer_max = min(
            int(target_answer_count_max),
            int(max_board_cells) - int(palette_size_min) + 1,
        )
        if int(feasible_target_answer_max) < int(target_answer_count_min):
            raise ValueError("target answer-count range is infeasible for the resolved board/palette bounds")

        degree_range_size = max(1, int(target_degree_max) - int(target_degree_min) + 1)
        answer_range_size = max(1, int(feasible_target_answer_max) - int(target_answer_count_min) + 1)
        target_degree_selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}:target_degree",
        )
        target_answer_selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}:target_answer_count",
        )
        target_degree = int(target_degree_min) + (int(target_degree_selection_index) % int(degree_range_size))
        target_answer_count = int(target_answer_count_min) + (
            int(target_answer_selection_index) % int(answer_range_size)
        )

        selected_option: Dict[str, Any] | None = None
        available_answer_counts: List[int] = []
        available_degrees: List[int] = []
        counts_by_color: Dict[str, int] = {}
        degree_histogram_by_color: Dict[str, Dict[int, int]] = {}
        degree_by_coord_all: Dict[Coord, int] = {}
        scene = None
        for _ in range(int(max_attempts) * int(answer_range_size) * int(degree_range_size)):
            scene = build_rectangular_named_color_board_scene(
                instance_seed,
                task_rng=task_rng,
                params=params,
                generation_defaults=_GEN_DEFAULTS,
                rendering_defaults=_RENDER_DEFAULTS,
                background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
                noise_defaults=POST_IMAGE_NOISE_DEFAULTS,
                defaults=_DEFAULTS,
            )

            options_by_pair: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
            counts_by_color = {}
            degree_histogram_by_color = {}
            catalog, degree_by_coord_all = _build_color_degree_catalog(scene)
            available_degree_answer_pairs = set()
            for entry in catalog:
                query_color_name = str(entry["query_color_name"])
                matching_coords = list(entry["matching_coords"])
                coords_by_degree = {
                    int(degree): list(coords)
                    for degree, coords in dict(entry["coords_by_degree"]).items()
                }
                counts_by_color[query_color_name] = int(len(matching_coords))
                degree_histogram_by_color[query_color_name] = {
                    int(degree): int(len(coords))
                    for degree, coords in coords_by_degree.items()
                }
                for degree in range(int(target_degree_min), int(target_degree_max) + 1):
                    match_coords = list(coords_by_degree.get(int(degree), []))
                    answer_value = int(len(match_coords))
                    if answer_value <= 0:
                        continue
                    available_degree_answer_pairs.add((int(degree), int(answer_value)))
                    options_by_pair.setdefault((int(degree), int(answer_value)), []).append(
                        {
                            "query_color_name": str(query_color_name),
                            "query_color_rgb": list(entry["query_color_rgb"]),
                            "matching_coords": list(match_coords),
                            "all_query_color_coords": list(matching_coords),
                            "degree_by_coord": dict(entry["degree_by_coord"]),
                        }
                    )

            available_answer_counts = sorted({int(answer) for _degree, answer in available_degree_answer_pairs})
            available_degrees = sorted({int(degree) for degree, _answer in available_degree_answer_pairs})
            target_pair = (int(target_degree), int(target_answer_count))
            if target_pair not in options_by_pair:
                continue
            selected_option = task_rng.choice(options_by_pair[target_pair])
            break

        if scene is None or selected_option is None:
            raise RuntimeError("failed to sample rectangular tile board for target same-color degree count")

        query_color_name = str(selected_option["query_color_name"])
        query_color_rgb = (
            int(selected_option["query_color_rgb"][0]),
            int(selected_option["query_color_rgb"][1]),
            int(selected_option["query_color_rgb"][2]),
        )
        matching_coords = [tuple(int(value) for value in coord) for coord in selected_option["matching_coords"]]
        all_query_color_coords = [
            tuple(int(value) for value in coord)
            for coord in selected_option["all_query_color_coords"]
        ]
        query_color_hex = rgb_to_hex(query_color_rgb)
        query_color_label = format_named_color_with_hex(query_color_name, query_color_rgb)

        evidence_artifacts = coordinate_set_evidence_artifacts(
            coords=matching_coords,
            bbox_map=scene.bbox_map,
        )
        matching_coord_set = {
            (int(row), int(col))
            for row, col in matching_coords
        }
        answer_value = int(target_answer_count)

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
        json_example, json_example_answer_only = resolve_prompt_json_examples(
            all_prompt_defaults,
            evidence_value=[[0, 1], [2, 2]],
            answer_type="integer",
        )
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
                "query_color": str(query_color_label),
                "neighbor_degree": int(target_degree),
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

        palette_trace = build_palette_trace(scene.palette)
        scene_entities = build_color_board_scene_entities(
            scene,
            query_color_name=str(query_color_name),
            extra_attrs_by_coord={
                coord: {
                    "same_color_degree": int(degree_by_coord_all.get(coord, 0)),
                    "is_degree_match": bool(coord in matching_coord_set),
                }
                for coord in scene.board_colors.keys()
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "rectangular_tile_board",
                "entities": scene_entities,
                "relations": {},
            },
            "query_spec": {
                "task_variant": "degree_count",
                "template_id": "degree_count_v1",
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
                        "out": "query_degree_map",
                        "op": "same_color_degree",
                        "in": "query_cells",
                        "connectivity": "4_neighbor",
                    },
                    {
                        "out": "matching_cells",
                        "op": "filter_degree",
                        "in": "query_degree_map",
                        "predicate": {"degree": int(target_degree)},
                    },
                    {
                        "out": "evidence",
                        "op": "project_coords",
                        "in": "matching_cells",
                        "coord_space": "tile_grid",
                        "coord_type": "grid_point_set",
                        "ordering": "row_major",
                    },
                    {"out": "answer", "op": "count", "in": "matching_cells"},
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
                "task_variant": "degree_count",
                "rows": int(scene.rows),
                "cols": int(scene.cols),
                "palette": list(palette_trace),
                "palette_size": int(scene.palette_size),
                "query_color_name": str(query_color_name),
                "query_color_rgb": [int(query_color_rgb[0]), int(query_color_rgb[1]), int(query_color_rgb[2])],
                "query_color_hex": str(query_color_hex),
                "query_color_label": str(query_color_label),
                "target_degree": int(target_degree),
                "target_degree_range": [int(target_degree_min), int(target_degree_max)],
                "target_answer_count": int(target_answer_count),
                "target_answer_count_range": [
                    int(target_answer_count_min),
                    int(feasible_target_answer_max),
                ],
                "available_answer_counts": [int(value) for value in available_answer_counts],
                "available_degrees": [int(value) for value in available_degrees],
                "counts_by_color_name": dict(counts_by_color),
                "degree_histogram_by_color_name": {
                    str(color_name): {
                        int(degree): int(count)
                        for degree, count in histogram.items()
                    }
                    for color_name, histogram in degree_histogram_by_color.items()
                },
                "all_query_color_coords": [[int(row), int(col)] for row, col in all_query_color_coords],
                "matching_coords": [[int(row), int(col)] for row, col in matching_coords],
                "matching_ids": list(evidence_artifacts["witness_symbolic"]["ids"]),
                "same_color_degree_by_coord": {
                    cell_id(coord): int(degree_by_coord_all.get(coord, 0))
                    for coord in scene.board_colors.keys()
                },
                "answer_value": int(answer_value),
            },
            "witness_symbolic": dict(evidence_artifacts["witness_symbolic"]),
            "projected_evidence": dict(evidence_artifacts["projected_evidence"]),
        }

        board_cell_count = int(scene.rows) * int(scene.cols)
        complexity = TaskComplexity(
            complexity_score=min(
                1.0,
                max(
                    0.0,
                    (
                        (float(board_cell_count) / 64.0)
                        + (float(scene.palette_size) / 6.0)
                        + (float(target_degree + 1) / 4.0)
                    )
                    / 3.0,
                ),
            ),
            complexity_components={
                "rows": int(scene.rows),
                "cols": int(scene.cols),
                "palette_size": int(scene.palette_size),
                "target_degree": int(target_degree),
                "answer_count": int(answer_value),
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
            task_variant="degree_count",
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
