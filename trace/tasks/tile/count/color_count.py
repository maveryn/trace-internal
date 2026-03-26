"""Single-board rectangular-tile color-count task."""

from __future__ import annotations

from typing import Any, Dict

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import pixel_anchor_map_from_bboxes
from ...shared.color_format import format_named_color_with_hex, rgb_to_hex
from ...shared.config_defaults import (
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import resolve_prompt_json_examples
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.tile_evidence import coordinate_set_evidence_artifacts, sort_coords_row_major
from .background_defaults import POST_IMAGE_BACKGROUND_DEFAULTS
from .color_board_common import (
    RectangularColorBoardTaskDefaults,
    build_color_board_scene_entities,
    build_palette_trace,
    build_rectangular_color_board_render_spec,
    build_rectangular_color_board_scene,
)
from .noise_defaults import POST_IMAGE_NOISE_DEFAULTS


_DEFAULTS = RectangularColorBoardTaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("tile", "count")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, dict) else {},
    task_id="task_tile_count_color_count",
)


@register_task
class TileColorCountTask:
    """Count the number of tiles matching a queried color."""

    task_id = "task_tile_count_color_count"
    domain = "tile"
    task_group = "count"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        task_rng = spawn_rng(instance_seed, "task")
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

        query_color_name, query_color_rgb = task_rng.choice(list(scene.palette))
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
            evidence_value=[[0, 1], [1, 0], [1, 2]],
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
        counts_by_color = {
            str(name): sum(1 for cell_name, _rgb in scene.board_colors.values() if str(cell_name) == str(name))
            for name, _rgb in scene.palette
        }
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
                "task_variant": "color_count",
                "template_id": "color_count_v1",
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
                        "coord_space": "tile_grid",
                        "coord_type": "grid_point_set",
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
                "task_variant": "color_count",
                "rows": int(scene.rows),
                "cols": int(scene.cols),
                "palette": list(palette_trace),
                "palette_size": int(scene.palette_size),
                "query_color_name": str(query_color_name),
                "query_color_rgb": [int(query_color_rgb[0]), int(query_color_rgb[1]), int(query_color_rgb[2])],
                "query_color_hex": str(query_color_hex),
                "query_color_label": str(query_color_label),
                "counts_by_color_name": dict(counts_by_color),
                "matching_coords": [[int(row), int(col)] for row, col in matching_coords],
                "matching_ids": list(evidence_artifacts["witness_symbolic"]["ids"]),
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
                        + (float(answer_value) / float(max(1, board_cell_count)))
                    )
                    / 3.0,
                ),
            ),
            complexity_components={
                "rows": int(scene.rows),
                "cols": int(scene.cols),
                "palette_size": int(scene.palette_size),
                "answer_count": int(answer_value),
                "match_fraction": float(answer_value) / float(max(1, board_cell_count)),
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
            task_variant="color_count",
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
