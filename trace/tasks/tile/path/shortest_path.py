"""Tile shortest-path task with unique-answer-by-construction generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from PIL import ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import (
    ordered_ids_to_point_path_and_bbox_set,
    pixel_anchor_map_from_bboxes,
)
from ...shared.config_defaults import (
    group_default,
    split_generation_rendering_prompt_defaults,
)
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.output_metadata import default_task_versions
from ..shared.maze_sampling import sample_unique_shortest_path_maze, validate_open_path_entities
from ..shared.maze_scene import (
    build_tile_cell_entities,
    open_adjacency_by_cell,
)
from ..shared.path_grid import cell_id
from ..shared.maze_rendering import render_path_maze_scene
from .background_defaults import POST_IMAGE_BACKGROUND_DEFAULTS
from .noise_defaults import POST_IMAGE_NOISE_DEFAULTS


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable defaults for the tile shortest-path task."""

    rows: int = 8
    cols: int = 8
    min_shortest_len: int = 6
    obstacle_prob_min: float = 0.16
    obstacle_prob_max: float = 0.36
    canvas_size: int = 640
    margin: int = 24
    evidence_type: str = "point_path"


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("tile", "path")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, dict) else {}
)


@register_task
class TileShortestPathTask:
    """Task emitting shortest-path length with grounded path evidence."""

    task_id = "tile_shortest_path"
    domain = "tile"
    task_group = "path"

    @staticmethod
    def supported_query_types(_params: Dict[str, Any] | None = None) -> List[str]:
        """Return query types supported by this task."""
        return ["shortest_path"]

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        rows = int(params.get("rows", group_default(_GEN_DEFAULTS, "rows", _DEFAULTS.rows)))
        cols = int(params.get("cols", group_default(_GEN_DEFAULTS, "cols", _DEFAULTS.cols)))
        min_shortest_len = int(params.get("min_shortest_len", group_default(_GEN_DEFAULTS, "min_shortest_len", _DEFAULTS.min_shortest_len)))
        obstacle_prob_min = float(params.get("obstacle_prob_min", group_default(_GEN_DEFAULTS, "obstacle_prob_min", _DEFAULTS.obstacle_prob_min)))
        obstacle_prob_max = float(params.get("obstacle_prob_max", group_default(_GEN_DEFAULTS, "obstacle_prob_max", _DEFAULTS.obstacle_prob_max)))
        canvas_size = int(params.get("canvas_size", group_default(_RENDER_DEFAULTS, "canvas_size", _DEFAULTS.canvas_size)))
        margin = int(params.get("margin", group_default(_RENDER_DEFAULTS, "margin", _DEFAULTS.margin)))
        evidence_type = str(params.get("evidence_type", group_default(_GEN_DEFAULTS, "evidence_type", _DEFAULTS.evidence_type)))
        query_type = str(params.get("query_type", "shortest_path"))
        if evidence_type not in {"point_path", "bbox_set"}:
            raise ValueError(f"unsupported evidence_type: {evidence_type}")
        if query_type != "shortest_path":
            raise ValueError(f"unsupported query_type: {query_type}")

        task_rng = spawn_rng(instance_seed, "task")
        blocked, start, goal, path, shortest_len = sample_unique_shortest_path_maze(
            task_rng,
            rows=rows,
            cols=cols,
            min_shortest_len=min_shortest_len,
            obstacle_prob_min=obstacle_prob_min,
            obstacle_prob_max=obstacle_prob_max,
            max_attempts=max_attempts,
        )
        validate_open_path_entities(
            blocked=blocked,
            start=start,
            goal=goal,
            path=path,
        )

        base_image, background_meta = make_background_canvas(
            canvas_size=canvas_size,
            instance_seed=instance_seed,
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
            fallback_color=(246, 246, 246),
        )
        draw = ImageDraw.Draw(base_image)
        bbox_map = render_path_maze_scene(
            rows,
            cols,
            blocked,
            start,
            goal,
            path,
            draw=draw,
            canvas_size=canvas_size,
            margin=margin,
        )
        image = base_image
        image, post_noise_meta = apply_post_image_noise(
            image,
            instance_seed=instance_seed,
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        path_ids = [cell_id(rc) for rc in path]
        path_points, path_bboxes = ordered_ids_to_point_path_and_bbox_set(
            ordered_ids=path_ids,
            bbox_map=bbox_map,
        )

        evidence_value: Any
        if evidence_type == "point_path":
            evidence_value = path_points
        else:
            evidence_value = path_bboxes

        prompt_bundle_id = str(group_default(_PROMPT_DEFAULTS, "bundle_id", "tile_path_v1"))
        prompt_task_type_key = str(group_default(_PROMPT_DEFAULTS, "task_type_key", "maze_path"))
        evidence_hint = "ordered path points" if evidence_type == "point_path" else "path-cell bounding boxes"
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=prompt_bundle_id,
            task_type_key=prompt_task_type_key,
            query_type=query_type,
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "rows": int(rows),
                "cols": int(cols),
                "evidence_hint": evidence_hint,
            },
            instance_seed=instance_seed,
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        prompt = str(prompt_artifacts.prompt)
        prompt_variants = dict(prompt_artifacts.prompt_variants)

        adjacency_open = open_adjacency_by_cell(
            rows=rows,
            cols=cols,
            blocked=blocked,
        )
        scene_entities = build_tile_cell_entities(
            rows=rows,
            cols=cols,
            blocked=blocked,
            start=start,
            goal=goal,
        )

        render_map = {
            "image_id": "img0",
            "anchors": pixel_anchor_map_from_bboxes(bbox_map),
        }

        trace_payload = {
            "scene_ir": {
                "scene_kind": "tile_maze",
                "entities": scene_entities,
                "relations": {"adjacency_open": adjacency_open},
            },
            "query_spec": {
                "query_type": query_type,
                "template_id": "shortest_path_v1",
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
                        "out": "path",
                        "op": "shortest_path",
                        "relation": "adjacency_open",
                        "start": cell_id(start),
                        "goal": cell_id(goal),
                    },
                    {"out": "answer", "op": "path_length", "in": "path"},
                ],
            },
            "render_spec": {
                "canvas_size": canvas_size,
                "margin": margin,
                "rows": rows,
                "cols": cols,
                "coord_space": "pixel",
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": render_map,
            "execution_trace": {
                "shortest_path_len": shortest_len,
                "path_ids": path_ids,
                "path_cell_count": len(path_ids),
            },
            "witness_symbolic": {"type": "id_path", "ids": path_ids},
            "projected_evidence": {
                "point_path": path_points,
                "bbox_set": path_bboxes,
            },
        }

        complexity_score = min(1.0, max(0.0, float(shortest_len) / float(rows * cols)))
        complexity = TaskComplexity(
            complexity_score=complexity_score,
            complexity_components={
                "rows": rows,
                "cols": cols,
                "path_len": shortest_len,
                "blocked_ratio": sum(sum(1 for v in row if v) for row in blocked) / float(rows * cols),
            },
        )

        return TaskOutput(
            prompt=prompt,
            answer_gt=TypedValue(type="integer", value=int(shortest_len)),
            evidence_gt=TypedValue(type=evidence_type, value=evidence_value),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_type=query_type,
            prompt_variants=prompt_variants,
        )
