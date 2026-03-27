"""Single-board rectangular-tile reachable-region-size task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from PIL import ImageDraw

from ...core.seed import spawn_rng
from ...core.task_group_config import get_task_group_defaults
from ...core.types import TaskComplexity, TypedValue
from ...core.visual.background import make_background_canvas
from ...core.visual.noise import apply_post_image_noise
from ..base import TaskOutput
from ..registry import register_task
from ..shared.bbox_projection import pixel_anchor_map_from_bboxes
from ..shared.color_format import format_named_color_with_hex
from ..shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_required_float_bounds,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ..shared.output_metadata import default_task_versions
from ..shared.prompt_json_example import resolve_prompt_json_examples
from ..shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from .shared.grid_graph import (
    cell_id,
    coord_adjacency_to_cell_ids,
    open_grid_adjacency,
)
from .shared.reachability_board import sample_reachability_board
from .shared.rectangular_board import (
    build_rectangular_board_render_spec,
    render_rectangular_tile_board,
    resolve_rectangular_board_layout,
    sample_rectangular_tile_spec,
)
from .shared.tile_colors import available_named_tile_colors
from .shared.tile_evidence import coordinate_set_evidence_artifacts
from .shared.tile_scene import build_tile_cell_entities
from .shared.visual_defaults import load_tile_background_defaults, load_tile_noise_defaults


Coord = Tuple[int, int]

_OBSTACLE_RGB = (0, 0, 0)
_OPEN_RGB = (250, 250, 250)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable defaults for the rectangular tile reachability task."""

    rows_min: int = 3
    rows_max: int = 7
    cols_min: int = 3
    cols_max: int = 7
    short_side_px_min: int = 32
    short_side_px_max: int = 48
    aspect_ratio_min: float = 1.0
    aspect_ratio_max: float = 2.0
    outer_padding_fraction_min: float = 0.08
    outer_padding_fraction_max: float = 0.12
    placement_jitter_fraction_min: float = 0.02
    placement_jitter_fraction_max: float = 0.06
    obstacle_fraction_min: float = 0.12
    obstacle_fraction_max: float = 0.38
    reachable_fraction_min: float = 0.20
    reachable_fraction_max: float = 0.85
    answer_max: int = 12


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("tile", "reachability")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, dict) else {},
    task_id="task_tile_reachability_region_size",
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_tile_background_defaults(task_group="reachability")
POST_IMAGE_NOISE_DEFAULTS = load_tile_noise_defaults(task_group="reachability", apply_prob=0.5)


@register_task
class TileRegionSizeTask:
    """Return the size of the reachable region from one marked start tile."""

    task_id = "task_tile_reachability_region_size"
    domain = "tile"
    task_group = "reachability"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
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
        obstacle_fraction_min, obstacle_fraction_max = resolve_required_float_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="obstacle_fraction_min",
            max_key="obstacle_fraction_max",
            fallback_min=float(_DEFAULTS.obstacle_fraction_min),
            fallback_max=float(_DEFAULTS.obstacle_fraction_max),
            context=f"generation defaults for {self.task_id}",
        )
        reachable_fraction_min, reachable_fraction_max = resolve_required_float_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="reachable_fraction_min",
            max_key="reachable_fraction_max",
            fallback_min=float(_DEFAULTS.reachable_fraction_min),
            fallback_max=float(_DEFAULTS.reachable_fraction_max),
            context=f"generation defaults for {self.task_id}",
        )
        answer_max = int(
            params.get(
                "answer_max",
                group_default(_GEN_DEFAULTS, "answer_max", int(_DEFAULTS.answer_max)),
            )
        )
        if int(answer_max) <= 0:
            raise ValueError(f"answer_max must be > 0 for {self.task_id}")
        short_side_px_min, short_side_px_max = resolve_required_int_bounds(
            params,
            _RENDER_DEFAULTS,
            min_key="short_side_px_min",
            max_key="short_side_px_max",
            fallback_min=int(_DEFAULTS.short_side_px_min),
            fallback_max=int(_DEFAULTS.short_side_px_max),
            context=f"rendering defaults for {self.task_id}",
        )
        aspect_ratio_min, aspect_ratio_max = resolve_required_float_bounds(
            params,
            _RENDER_DEFAULTS,
            min_key="aspect_ratio_min",
            max_key="aspect_ratio_max",
            fallback_min=float(_DEFAULTS.aspect_ratio_min),
            fallback_max=float(_DEFAULTS.aspect_ratio_max),
            context=f"rendering defaults for {self.task_id}",
        )
        outer_padding_fraction_min, outer_padding_fraction_max = resolve_required_float_bounds(
            params,
            _RENDER_DEFAULTS,
            min_key="outer_padding_fraction_min",
            max_key="outer_padding_fraction_max",
            fallback_min=float(_DEFAULTS.outer_padding_fraction_min),
            fallback_max=float(_DEFAULTS.outer_padding_fraction_max),
            context=f"rendering defaults for {self.task_id}",
        )
        placement_jitter_fraction_min, placement_jitter_fraction_max = resolve_required_float_bounds(
            params,
            _RENDER_DEFAULTS,
            min_key="placement_jitter_fraction_min",
            max_key="placement_jitter_fraction_max",
            fallback_min=float(_DEFAULTS.placement_jitter_fraction_min),
            fallback_max=float(_DEFAULTS.placement_jitter_fraction_max),
            context=f"rendering defaults for {self.task_id}",
        )

        task_rng = spawn_rng(instance_seed, "task")
        rows = int(task_rng.randint(int(rows_min), int(rows_max)))
        cols = int(task_rng.randint(int(cols_min), int(cols_max)))
        start_color_name, start_color_rgb = task_rng.choice(list(available_named_tile_colors()))
        board_sample = sample_reachability_board(
            task_rng,
            rows=int(rows),
            cols=int(cols),
            obstacle_fraction_min=float(obstacle_fraction_min),
            obstacle_fraction_max=float(obstacle_fraction_max),
            reachable_fraction_min=float(reachable_fraction_min),
            reachable_fraction_max=float(reachable_fraction_max),
            max_attempts=int(max_attempts),
            min_reachable_count=1,
            max_reachable_count=int(answer_max),
        )
        blocked = board_sample.blocked
        start = board_sample.start_coord
        reachable_coords = list(board_sample.reachable_coords)
        realized_obstacle_fraction = float(board_sample.obstacle_fraction)
        reachable_fraction = float(board_sample.reachable_fraction)
        tile_spec = sample_rectangular_tile_spec(
            task_rng,
            short_side_px_min=int(short_side_px_min),
            short_side_px_max=int(short_side_px_max),
            aspect_ratio_min=float(aspect_ratio_min),
            aspect_ratio_max=float(aspect_ratio_max),
        )
        layout = resolve_rectangular_board_layout(
            task_rng,
            rows=int(rows),
            cols=int(cols),
            tile_width_px=int(tile_spec.tile_width_px),
            tile_height_px=int(tile_spec.tile_height_px),
            outer_padding_fraction_min=float(outer_padding_fraction_min),
            outer_padding_fraction_max=float(outer_padding_fraction_max),
            placement_jitter_fraction_min=float(placement_jitter_fraction_min),
            placement_jitter_fraction_max=float(placement_jitter_fraction_max),
        )

        base_image, background_meta = make_background_canvas(
            canvas_width=int(layout.canvas_width_px),
            canvas_height=int(layout.canvas_height_px),
            instance_seed=instance_seed,
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
            fallback_color=(246, 246, 246),
        )
        draw = ImageDraw.Draw(base_image)
        fill_colors_by_coord = {
            (int(row), int(col)): (
                tuple(int(value) for value in start_color_rgb)
                if (int(row), int(col)) == (int(start[0]), int(start[1]))
                else (_OBSTACLE_RGB if bool(blocked[row][col]) else _OPEN_RGB)
            )
            for row in range(int(rows))
            for col in range(int(cols))
        }
        bbox_map = render_rectangular_tile_board(
            draw,
            layout=layout,
            fill_colors_by_coord=fill_colors_by_coord,
        )
        image, post_noise_meta = apply_post_image_noise(
            base_image,
            instance_seed=instance_seed,
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        evidence_artifacts = coordinate_set_evidence_artifacts(
            coords=reachable_coords,
            bbox_map=bbox_map,
        )
        answer_value = int(len(reachable_coords))
        adjacency_open = coord_adjacency_to_cell_ids(
            open_grid_adjacency(rows=int(rows), cols=int(cols), blocked=blocked)
        )

        prompt_defaults_all = dict(_PROMPT_DEFAULTS if isinstance(_PROMPT_DEFAULTS, dict) else {})
        prompt_defaults = required_group_defaults(
            prompt_defaults_all,
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
        obstacle_color_label = format_named_color_with_hex("black", _OBSTACLE_RGB)
        start_color_label = format_named_color_with_hex(str(start_color_name), start_color_rgb)
        json_example, json_example_answer_only = resolve_prompt_json_examples(
            prompt_defaults_all,
            evidence_value=[[0, 0], [0, 1], [1, 1], [2, 1]],
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
                "rows": int(rows),
                "cols": int(cols),
                "obstacle_color": str(obstacle_color_label),
                "start_color": str(start_color_label),
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

        blocked_coords = [
            [int(row), int(col)]
            for row in range(int(rows))
            for col in range(int(cols))
            if bool(blocked[row][col])
        ]
        start_id = cell_id(start)
        reachable_ids = list(evidence_artifacts["witness_symbolic"]["ids"])
        reachable_coord_set = {(int(row), int(col)) for row, col in reachable_coords}
        scene_entities = build_tile_cell_entities(
            rows=int(rows),
            cols=int(cols),
            attrs_by_coord={
                (int(row), int(col)): {
                    "blocked": bool(blocked[row][col]),
                    "is_start": bool((int(row), int(col)) == (int(start[0]), int(start[1]))),
                    "is_reachable": bool((int(row), int(col)) in reachable_coord_set),
                    "fill_rgb": list(fill_colors_by_coord[(int(row), int(col))]),
                }
                for row in range(int(rows))
                for col in range(int(cols))
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "rectangular_tile_reachability_board",
                "entities": scene_entities,
                "relations": {"adjacency_open": adjacency_open},
            },
            "query_spec": {
                "task_variant": "region_size",
                "template_id": "region_size_v1",
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "dsl_program": [
                    {"out": "cells", "op": "select", "entity_type": "tile_cell"},
                    {
                        "out": "open_cells",
                        "op": "filter",
                        "in": "cells",
                        "predicate": {"blocked": False},
                    },
                    {
                        "out": "reachable",
                        "op": "reachable_set",
                        "relation": "adjacency_open",
                        "start": str(start_id),
                    },
                    {
                        "out": "evidence",
                        "op": "project_coords",
                        "in": "reachable",
                        "coord_space": "tile_grid",
                        "coord_type": "grid_point_set",
                        "ordering": "row_major",
                    },
                    {"out": "answer", "op": "count", "in": "reachable"},
                ],
            },
            "render_spec": build_rectangular_board_render_spec(
                rows=int(rows),
                cols=int(cols),
                layout=layout,
                tile_spec=tile_spec,
                background_meta=background_meta,
                post_noise_meta=post_noise_meta,
            ),
            "render_map": {
                "image_id": "img0",
                "anchors": pixel_anchor_map_from_bboxes(bbox_map),
            },
            "execution_trace": {
                "task_variant": "region_size",
                "rows": int(rows),
                "cols": int(cols),
                "answer_max": int(answer_max),
                "obstacle_color_label": str(obstacle_color_label),
                "start_color_name": str(start_color_name),
                "start_color_rgb": [int(value) for value in start_color_rgb],
                "start_color_label": str(start_color_label),
                "start_coord": [int(start[0]), int(start[1])],
                "start_id": str(start_id),
                "blocked_coords": list(blocked_coords),
                "blocked_ids": [cell_id((int(coord[0]), int(coord[1]))) for coord in blocked_coords],
                "reachable_coords": [[int(row), int(col)] for row, col in reachable_coords],
                "reachable_ids": list(reachable_ids),
                "answer_value": int(answer_value),
                "obstacle_fraction": float(realized_obstacle_fraction),
                "reachable_fraction": float(reachable_fraction),
            },
            "witness_symbolic": dict(evidence_artifacts["witness_symbolic"]),
            "projected_evidence": dict(evidence_artifacts["projected_evidence"]),
        }

        board_cell_count = int(rows) * int(cols)
        blocked_count = len(blocked_coords)
        complexity = TaskComplexity(
            complexity_score=min(
                1.0,
                max(
                    0.0,
                    (
                        (float(board_cell_count) / 64.0)
                        + float(realized_obstacle_fraction)
                        + (1.0 - float(reachable_fraction))
                    )
                    / 3.0,
                ),
            ),
            complexity_components={
                "rows": int(rows),
                "cols": int(cols),
                "blocked_count": int(blocked_count),
                "region_size": int(answer_value),
                "obstacle_fraction": float(realized_obstacle_fraction),
                "reachable_fraction": float(reachable_fraction),
            },
        )

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(answer_value)),
            evidence_gt=TypedValue(
                type=str(evidence_artifacts["evidence_type"]),
                value=list(evidence_artifacts["evidence_value"]),
            ),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant="region_size",
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
