"""Single-board rectangular-tile color-count task."""

from __future__ import annotations

from typing import Any, Dict

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
from trace.tasks.shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_json_example import resolve_prompt_json_examples
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from .shared.color_board_common import (
    RectangularColorBoardTaskDefaults,
    build_palette_trace,
    build_rectangular_color_board_render_spec,
    build_rectangular_color_board_scene,
)
from .shared.named_color_board import build_color_board_scene_entities
from .shared.tile_evidence import coordinate_set_evidence_artifacts, sort_coords_row_major
from .shared.visual_defaults import load_tile_background_defaults, load_tile_noise_defaults
from .shared.complexity import (
    build_tile_complexity,
    resolve_tile_complexity_weights,
    normalize_int_with_bounds,
)


_DEFAULTS = RectangularColorBoardTaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "cell_board_count")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, dict) else {},
    task_id="cell_board_color_count_internal",
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_tile_background_defaults(task_group="count")
POST_IMAGE_NOISE_DEFAULTS = load_tile_noise_defaults(task_group="count", apply_prob=0.5)
_COMPLEXITY_WEIGHTS = resolve_tile_complexity_weights(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, dict) else {},
    task_id="cell_board_color_count_internal",
)


class TileColorCountTask:
    """Count the number of tiles matching a queried color."""

    task_id = "cell_board_color_count_internal"
    domain = "puzzles"
    task_group = "cell_board_count"
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
        target_color_count_min = int(
            params.get(
                "target_color_count_min",
                group_default(_GEN_DEFAULTS, "target_color_count_min", 1),
            )
        )
        default_target_color_count_max = int(rows_max) * int(cols_max)
        target_color_count_max = int(
            params.get(
                "target_color_count_max",
                group_default(_GEN_DEFAULTS, "target_color_count_max", int(default_target_color_count_max)),
            )
        )
        if int(target_color_count_min) <= 0:
            raise ValueError("target_color_count_min must be > 0")
        if int(target_color_count_min) > int(target_color_count_max):
            raise ValueError("target_color_count_min must be <= target_color_count_max")
        target_color_count_support = tuple(
            range(int(target_color_count_min), int(target_color_count_max) + 1)
        )
        explicit_target_color_count = params.get("target_color_count")
        if explicit_target_color_count is not None:
            target_color_count = int(explicit_target_color_count)
            if int(target_color_count) not in target_color_count_support:
                raise ValueError("target_color_count is outside configured support")
        else:
            selection_index = int(
                resolve_selection_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    namespace=f"{self.task_id}:target_color_count",
                )
            )
            target_color_count = int(
                target_color_count_support[int(selection_index % len(target_color_count_support))]
            )

        scene = None
        counts_by_color: Dict[str, int] = {}
        available_color_count_answers: list[int] = []
        for _ in range(int(max_attempts)):
            sampled_scene = build_rectangular_color_board_scene(
                instance_seed,
                task_rng=task_rng,
                params=params,
                generation_defaults=_GEN_DEFAULTS,
                rendering_defaults=_RENDER_DEFAULTS,
                background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
                noise_defaults=POST_IMAGE_NOISE_DEFAULTS,
                defaults=_DEFAULTS,
            )
            board_cell_count = int(sampled_scene.rows) * int(sampled_scene.cols)
            if int(target_color_count) > int(board_cell_count) - (int(sampled_scene.palette_size) - 1):
                continue
            query_color_name, query_color_rgb = task_rng.choice(list(sampled_scene.palette))
            non_query_palette = [
                (str(name), (int(rgb[0]), int(rgb[1]), int(rgb[2])))
                for name, rgb in sampled_scene.palette
                if str(name) != str(query_color_name)
            ]
            if not non_query_palette and int(target_color_count) != int(board_cell_count):
                continue
            coords = [
                (int(row), int(col))
                for row in range(int(sampled_scene.rows))
                for col in range(int(sampled_scene.cols))
            ]
            task_rng.shuffle(coords)
            query_coords = coords[: int(target_color_count)]
            remaining_coords = coords[int(target_color_count) :]
            if len(remaining_coords) < len(non_query_palette):
                continue
            board_colors = {
                coord: (str(query_color_name), tuple(int(channel) for channel in query_color_rgb))
                for coord in query_coords
            }
            for coord, color_spec in zip(remaining_coords, non_query_palette):
                board_colors[coord] = color_spec
            for coord in remaining_coords[len(non_query_palette) :]:
                board_colors[coord] = task_rng.choice(non_query_palette) if non_query_palette else (
                    str(query_color_name),
                    tuple(int(channel) for channel in query_color_rgb),
                )
            scene = build_rectangular_color_board_scene(
                instance_seed,
                task_rng=task_rng,
                params=params,
                generation_defaults=_GEN_DEFAULTS,
                rendering_defaults=_RENDER_DEFAULTS,
                background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
                noise_defaults=POST_IMAGE_NOISE_DEFAULTS,
                defaults=_DEFAULTS,
                rows=int(sampled_scene.rows),
                cols=int(sampled_scene.cols),
                palette=list(sampled_scene.palette),
                board_colors=board_colors,
            )
            counts_by_color = {
                str(name): sum(1 for cell_name, _rgb in scene.board_colors.values() if str(cell_name) == str(name))
                for name, _rgb in scene.palette
            }
            available_color_count_answers = sorted({int(count) for count in counts_by_color.values()})
            break
        if scene is None:
            raise RuntimeError("failed to sample tile board with a query color in the target count range")
        query_color_hex = rgb_to_hex(query_color_rgb)
        query_color_label = format_named_color_with_hex(query_color_name, query_color_rgb)
        matching_coords = sort_coords_row_major(
            [
                (int(row), int(col))
                for (row, col), (name, _rgb) in scene.board_colors.items()
                if str(name) == str(query_color_name)
            ]
        )
        if not matching_coords:
            raise RuntimeError("sampled query color must appear at least once on the board")

        evidence_artifacts = coordinate_set_evidence_artifacts(
            coords=matching_coords,
            bbox_map=scene.bbox_map,
        )
        answer_value = int(len(matching_coords))

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
        prompt_bundle_id = str(prompt_defaults["bundle_id"])
        prompt_scene_key = str(prompt_defaults["scene_key"])
        prompt_task_key = str(prompt_defaults["task_key"])
        json_example, json_example_answer_only = resolve_prompt_json_examples(
            all_prompt_defaults,
            evidence_value=[[168, 120], [120, 168], [216, 168]],
            answer_type="integer",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=prompt_bundle_id,
            scene_key=prompt_scene_key,
            task_key=prompt_task_key,
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
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "rectangular_tile_board",
                "entities": scene_entities,
                "relations": {},
            },
            "query_spec": {
                "query_variant": "color_count",
                "template_id": "color_count_v0",
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
                        "out": "evidence",
                        "op": "project_coords",
                        "in": "query_cells",
                        "source_coord_space": "tile_grid",
                        "coord_space": "image_pixel",
                        "coord_type": "point_set",
                        "ordering": "row_major",
                    },
                    {"out": "answer", "op": "count", "in": "query_cells"},
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
                "query_variant": "color_count",
                "rows": int(scene.rows),
                "cols": int(scene.cols),
                "palette": list(palette_trace),
                "palette_size": int(scene.palette_size),
                "query_color_name": str(query_color_name),
                "query_color_rgb": [int(query_color_rgb[0]), int(query_color_rgb[1]), int(query_color_rgb[2])],
                "query_color_hex": str(query_color_hex),
                "query_color_label": str(query_color_label),
                "query_selection_strategy": "uniform_over_target_color_count_with_constructed_board",
                "target_color_count_range": [
                    int(target_color_count_min),
                    int(target_color_count_max),
                ],
                "target_color_count": int(target_color_count),
                "target_color_count_probabilities": dict(
                    uniform_probability_map(
                        target_color_count_support,
                        selected=int(target_color_count) if explicit_target_color_count is not None else None,
                    )
                ),
                "available_color_count_answers": [int(answer) for answer in available_color_count_answers],
                "counts_by_color_name": dict(counts_by_color),
                "matching_coords": [[int(row), int(col)] for row, col in matching_coords],
                "matching_ids": list(evidence_artifacts["private_witness"]["ids"]),
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
                    0.75
                    * normalize_int_with_bounds(
                        int(board_cell_count),
                        (int(min_board_cell_count), int(max_board_cell_count)),
                    )
                    + 0.25
                    * normalize_int_with_bounds(
                        int(scene.palette_size),
                        (int(palette_size_min), int(palette_size_max)),
                    )
                ),
                "reasoning_load": float(answer_value) / float(max(1, board_cell_count)),
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
            query_variant="color_count",
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
