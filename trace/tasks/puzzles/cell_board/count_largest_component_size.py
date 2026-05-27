"""Single-board rectangular-tile largest-component-size task."""

from __future__ import annotations

from typing import Any, Dict, List

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
from .shared.color_board_common import (
    RectangularColorBoardTaskDefaults,
    build_color_component_catalog,
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
from .shared.tile_evidence import coordinate_set_evidence_artifacts
from .shared.visual_defaults import load_tile_background_defaults, load_tile_noise_defaults


_DEFAULTS = RectangularColorBoardTaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "cell_board_count")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, dict) else {},
    task_id="cell_board_largest_component_size_internal",
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_tile_background_defaults(task_group="count")
POST_IMAGE_NOISE_DEFAULTS = load_tile_noise_defaults(task_group="count", apply_prob=0.5)
_COMPLEXITY_WEIGHTS = resolve_tile_complexity_weights(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, dict) else {},
    task_id="cell_board_largest_component_size_internal",
)


class TileLargestComponentSizeTask:
    """Return the size of the unique largest queried-color component."""

    task_id = "cell_board_largest_component_size_internal"
    domain = "puzzles"
    task_group = "cell_board_count"
    default_dataset_enabled = False

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
        target_largest_component_size_min = int(
            params.get(
                "target_largest_component_size_min",
                group_default(_GEN_DEFAULTS, "target_largest_component_size_min", 2),
            )
        )
        target_largest_component_size_max = int(
            params.get(
                "target_largest_component_size_max",
                group_default(_GEN_DEFAULTS, "target_largest_component_size_max", 10),
            )
        )
        if int(target_largest_component_size_min) > int(target_largest_component_size_max):
            raise ValueError("target_largest_component_size_min must be <= target_largest_component_size_max")

        max_board_cells = int(rows_max) * int(cols_max)
        feasible_target_max = int(max_board_cells) - int(palette_size_min)
        effective_target_largest_component_size_max = min(
            int(target_largest_component_size_max),
            int(feasible_target_max),
        )
        if int(effective_target_largest_component_size_max) < int(target_largest_component_size_min):
            raise ValueError(
                "largest component target range is infeasible for the resolved board/palette bounds"
            )

        target_range_size = max(
            1,
            int(effective_target_largest_component_size_max) - int(target_largest_component_size_min) + 1,
        )
        target_selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}:target_largest_component_size",
        )
        target_largest_component_size = int(target_largest_component_size_min) + (
            int(target_selection_index) % int(target_range_size)
        )

        selected_option: Dict[str, Any] | None = None
        available_largest_component_sizes: List[int] = []
        counts_by_color: Dict[str, int] = {}
        component_counts_by_color: Dict[str, int] = {}
        scene = None
        for _ in range(int(max_attempts) * int(target_range_size)):
            scene = build_rectangular_color_board_scene(
                instance_seed,
                task_rng=task_rng,
                params=params,
                generation_defaults=_GEN_DEFAULTS,
                rendering_defaults=_RENDER_DEFAULTS,
                background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
                noise_defaults=POST_IMAGE_NOISE_DEFAULTS,
                defaults=_DEFAULTS,
            )

            options_by_answer: Dict[int, List[Dict[str, Any]]] = {}
            counts_by_color = {}
            component_counts_by_color = {}
            for entry in build_color_component_catalog(scene):
                query_color_name = str(entry["query_color_name"])
                matching_coords = list(entry["matching_coords"])
                component_coords = list(entry["component_coords"])
                component_sizes = [int(value) for value in entry["component_sizes"]]
                largest_component_size = int(entry["largest_component_size"])
                largest_component_indices = [int(value) for value in entry["largest_component_indices"]]
                component_count = int(entry["component_count"])

                counts_by_color[query_color_name] = int(len(matching_coords))
                component_counts_by_color[query_color_name] = int(component_count)

                if int(component_count) < 2:
                    continue
                if len(largest_component_indices) != 1:
                    continue
                if not (
                    int(target_largest_component_size_min)
                    <= int(largest_component_size)
                    <= int(effective_target_largest_component_size_max)
                ):
                    continue

                largest_component_index = int(largest_component_indices[0])
                winning_component_coords = list(component_coords[largest_component_index])
                options_by_answer.setdefault(int(largest_component_size), []).append(
                    {
                        "query_color_name": str(query_color_name),
                        "query_color_rgb": list(entry["query_color_rgb"]),
                        "matching_coords": list(matching_coords),
                        "component_coords": list(component_coords),
                        "component_sizes": [int(value) for value in component_sizes],
                        "largest_component_index": int(largest_component_index),
                        "winning_component_coords": list(winning_component_coords),
                    }
                )

            available_largest_component_sizes = sorted(int(answer) for answer in options_by_answer.keys())
            if int(target_largest_component_size) not in options_by_answer:
                continue
            selected_option = task_rng.choice(options_by_answer[int(target_largest_component_size)])
            break

        if scene is None or selected_option is None:
            raise RuntimeError("failed to sample rectangular tile board for target largest component size")

        query_color_name = str(selected_option["query_color_name"])
        query_color_rgb = (
            int(selected_option["query_color_rgb"][0]),
            int(selected_option["query_color_rgb"][1]),
            int(selected_option["query_color_rgb"][2]),
        )
        matching_coords = [tuple(int(value) for value in coord) for coord in selected_option["matching_coords"]]
        component_coords = [
            [tuple(int(value) for value in coord) for coord in component]
            for component in selected_option["component_coords"]
        ]
        component_sizes = [int(value) for value in selected_option["component_sizes"]]
        largest_component_index = int(selected_option["largest_component_index"])
        winning_component_coords = [
            tuple(int(value) for value in coord)
            for coord in selected_option["winning_component_coords"]
        ]
        query_color_hex = rgb_to_hex(query_color_rgb)
        query_color_label = format_named_color_with_hex(query_color_name, query_color_rgb)

        evidence_artifacts = coordinate_set_evidence_artifacts(
            coords=winning_component_coords,
            bbox_map=scene.bbox_map,
        )
        component_ids = [
            [cell_id((int(row), int(col))) for row, col in component]
            for component in component_coords
        ]
        component_index_by_coord = {
            (int(row), int(col)): int(component_index)
            for component_index, component in enumerate(component_coords)
            for row, col in component
        }
        winning_component_coord_set = {
            (int(row), int(col))
            for row, col in winning_component_coords
        }
        answer_value = int(target_largest_component_size)

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
            evidence_value=[[120, 120], [168, 120], [168, 168], [216, 168]],
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
                "query_color": str(query_color_label),
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
                    "query_component_index": int(component_index_by_coord[coord]),
                    "is_largest_component": bool(coord in winning_component_coord_set),
                }
                for coord in component_index_by_coord
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "rectangular_tile_board",
                "entities": scene_entities,
                "relations": {},
            },
            "query_spec": {
                "query_variant": "largest_component_size",
                "template_id": "largest_component_size_v0",
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
                        "out": "components",
                        "op": "connected_components",
                        "in": "query_cells",
                        "connectivity": "4_neighbor",
                    },
                    {
                        "out": "largest_component",
                        "op": "argmax_component_size",
                        "in": "components",
                        "tie_break": "reject_non_unique",
                    },
                    {
                        "out": "evidence",
                        "op": "project_coords",
                        "in": "largest_component",
                        "source_coord_space": "tile_grid",
                        "coord_space": "image_pixel",
                        "coord_type": "point_set",
                        "ordering": "row_major",
                    },
                    {"out": "answer", "op": "count", "in": "largest_component"},
                ],
            },
            "render_spec": {
                **build_rectangular_color_board_render_spec(scene),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": pixel_anchor_map_from_bboxes(scene.bbox_map),
            },
            "execution_trace": {
                "query_variant": "largest_component_size",
                "rows": int(scene.rows),
                "cols": int(scene.cols),
                "palette": list(palette_trace),
                "palette_size": int(scene.palette_size),
                "query_color_name": str(query_color_name),
                "query_color_rgb": [int(query_color_rgb[0]), int(query_color_rgb[1]), int(query_color_rgb[2])],
                "query_color_hex": str(query_color_hex),
                "query_color_label": str(query_color_label),
                "query_selection_strategy": "uniform_over_target_largest_component_size_range_with_rejection",
                "target_largest_component_size": int(target_largest_component_size),
                "target_largest_component_size_range": [
                    int(target_largest_component_size_min),
                    int(effective_target_largest_component_size_max),
                ],
                "available_largest_component_sizes": [int(answer) for answer in available_largest_component_sizes],
                "counts_by_color_name": dict(counts_by_color),
                "component_counts_by_color_name": dict(component_counts_by_color),
                "matching_coords": [[int(row), int(col)] for row, col in matching_coords],
                "matching_ids": [cell_id((int(row), int(col))) for row, col in matching_coords],
                "components": [
                    {
                        "component_index": int(index),
                        "coords": [[int(row), int(col)] for row, col in component],
                        "ids": list(component_ids[index]),
                        "size": int(component_sizes[index]),
                        "is_largest_component": bool(int(index) == int(largest_component_index)),
                    }
                    for index, component in enumerate(component_coords)
                ],
                "component_sizes": [int(value) for value in component_sizes],
                "query_component_count": int(len(component_coords)),
                "largest_component_index": int(largest_component_index),
                "winning_component_coords": [
                    [int(row), int(col)]
                    for row, col in winning_component_coords
                ],
                "winning_component_ids": list(evidence_artifacts["private_witness"]["ids"]),
                "answer_value": int(answer_value),
            },
            "witness_symbolic": dict(evidence_artifacts["witness_symbolic"]),
            "projected_evidence": dict(evidence_artifacts["projected_evidence"]),
        }

        board_cell_count = int(scene.rows) * int(scene.cols)
        matched_cell_count = int(len(matching_coords))
        min_board_cell_count = int(_rows_min) * int(_cols_min)
        max_board_cell_count = int(rows_max) * int(cols_max)
        complexity = build_tile_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": (
                    0.55
                    * normalize_int_with_bounds(
                        int(board_cell_count),
                        (int(min_board_cell_count), int(max_board_cell_count)),
                    )
                    + 0.25
                    * normalize_int_with_bounds(
                        int(matched_cell_count),
                        (1, int(max_board_cell_count)),
                    )
                    + 0.20
                    * normalize_int_with_bounds(
                        int(scene.palette_size),
                        (int(palette_size_min), int(_palette_size_max)),
                    )
                ),
                "reasoning_load": (
                    0.40
                    * normalize_int_with_bounds(
                        int(answer_value),
                        (
                            int(target_largest_component_size_min),
                            int(effective_target_largest_component_size_max),
                        ),
                    )
                    + 0.60
                    * normalize_int_with_bounds(
                        int(len(component_coords)),
                        (2, int(max_board_cell_count)),
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
            query_variant="largest_component_size",
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
