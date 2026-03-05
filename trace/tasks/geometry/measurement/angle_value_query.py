"""Geometry angle measurement task with query-type variants and grounded evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
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
from ...shared.value_queries import QueryOutcome, supported_value_query_types
from ...shared.value_query_sampling import (
    feasible_answer_values,
    resolve_candidate_count,
    sample_values_and_outcome_for_answer,
)
from ..shared.angle_geometry import (
    build_angle_evidence_artifacts,
    build_angle_render_anchors,
    build_angle_scene_entities,
    draw_angle,
    sample_angle_entities_layout,
)
from ..shared.graph_paper import (
    graph_spacing_from_cells,
    resolve_graph_cells_per_side,
    resolve_square_canvas_size,
)
from ..shared.graph_rendering import (
    FALLBACK_GRAPH_STYLE,
    build_graph_coordinate_frame,
    enforce_graph_paper_background,
    graph_paper_grid_from_frame,
    resolve_graph_style_from_params,
    scale_point,
    scaled_graph_style_for_scene,
)
from .background_defaults import POST_IMAGE_BACKGROUND_DEFAULTS
from .noise_defaults import POST_IMAGE_NOISE_DEFAULTS


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable defaults for geometry angle value queries."""

    canvas_size_min: int = 512
    canvas_size_max: int = 1024
    graph_cells_min: int = 12
    graph_cells_max: int = 24
    candidate_count_min: int = 3
    candidate_count_max: int = 7
    min_angle: int = 15
    max_angle: int = 165
    angle_step: int = 15
    target_x: int = 90
    ray_length: int = 84
    line_width: int = 4
    allow_duplicate_distractors: bool = True


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "measurement")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="geometry_angle_value_query",
)

def _complexity_score(*, candidate_count: int, min_gap: int, step: int) -> float:
    """Compute a task-local complexity proxy from candidate density/gap."""
    density = min(1.0, float(candidate_count) / 9.0)
    gap_component = 1.0 - min(1.0, float(min_gap) / max(1.0, float(step * 2)))
    return max(0.0, min(1.0, 0.55 * density + 0.45 * gap_component))


@register_task
class GeometryAngleValueQueryTask:
    """Geometry angle measurement task with query variants and grounded vertex evidence."""

    task_id = "geometry_angle_value_query"
    domain = "geometry"
    task_group = "measurement"

    @staticmethod
    def supported_query_types(_params: Dict[str, Any] | None = None) -> List[str]:
        return list(supported_value_query_types())

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic angle-value instance for a seed/param tuple."""
        query_type = str(params.get("query_type", "closest_to_x"))
        if query_type not in set(self.supported_query_types(params)):
            raise ValueError(f"unsupported query_type: {query_type}")

        scene_rng = spawn_rng(instance_seed, "scene")
        canvas_size = resolve_square_canvas_size(
            scene_rng,
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_min=_DEFAULTS.canvas_size_min,
            fallback_max=_DEFAULTS.canvas_size_max,
        )
        candidate_count = resolve_candidate_count(
            scene_rng,
            query_type=query_type,
            params=params,
            generation_defaults=_GEN_DEFAULTS,
            fallback_min=_DEFAULTS.candidate_count_min,
            fallback_max=_DEFAULTS.candidate_count_max,
        )
        min_angle = int(params.get("min_angle", group_default(_GEN_DEFAULTS, "min_angle", _DEFAULTS.min_angle)))
        max_angle = int(params.get("max_angle", group_default(_GEN_DEFAULTS, "max_angle", _DEFAULTS.max_angle)))
        angle_step = int(params.get("angle_step", group_default(_GEN_DEFAULTS, "angle_step", _DEFAULTS.angle_step)))
        target_x = int(params.get("target_x", group_default(_GEN_DEFAULTS, "target_x", _DEFAULTS.target_x)))
        allow_duplicate_distractors = bool(
            params.get(
                "allow_duplicate_distractors",
                group_default(_GEN_DEFAULTS, "allow_duplicate_distractors", _DEFAULTS.allow_duplicate_distractors),
            )
        )
        ray_length = int(params.get("ray_length", group_default(_RENDER_DEFAULTS, "ray_length", _DEFAULTS.ray_length)))
        line_width = int(params.get("line_width", group_default(_RENDER_DEFAULTS, "line_width", _DEFAULTS.line_width)))
        base_graph_style = resolve_graph_style_from_params(
            params,
            default_background_config=POST_IMAGE_BACKGROUND_DEFAULTS,
            fallback_style=FALLBACK_GRAPH_STYLE,
        )
        scene_scale = int(base_graph_style.get("scene_supersample_scale", 1))

        if candidate_count < 2:
            raise ValueError("candidate_count must be >= 2")

        candidates = list(range(min_angle, max_angle + 1, angle_step))
        if (not allow_duplicate_distractors) and len(candidates) < candidate_count:
            raise ValueError("angle candidate space too small for requested candidate_count")

        if query_type == "median" and candidate_count % 2 == 0:
            raise ValueError("median query requires odd candidate_count")

        ids = [f"angle_{idx + 1}" for idx in range(candidate_count)]
        feasible_answers = feasible_answer_values(
            query_type=query_type,
            candidates=candidates,
            candidate_count=candidate_count,
            target_x=target_x,
            allow_duplicate_distractors=allow_duplicate_distractors,
        )
        if not feasible_answers:
            raise RuntimeError("failed to generate geometry_angle_value_query instance")
        answer_target = int(scene_rng.choice(feasible_answers))

        entities: Dict[str, Dict[str, Any]] = {}
        outcome: QueryOutcome | None = None
        values_by_id: Dict[str, int] = {}
        selected_graph_cell_count: int | None = None
        selected_graph_spacing: int | None = None

        margin = ray_length + 40
        min_vertex_dist = float(max(70, int(ray_length * 1.6)))

        for _ in range(max_attempts):
            graph_cell_count = resolve_graph_cells_per_side(
                scene_rng,
                params=params,
                render_defaults=_RENDER_DEFAULTS,
                canvas_size=int(canvas_size),
                fallback_min=_DEFAULTS.graph_cells_min,
                fallback_max=_DEFAULTS.graph_cells_max,
            )
            graph_spacing = graph_spacing_from_cells(
                canvas_size=int(canvas_size),
                graph_cells=int(graph_cell_count),
                min_spacing_px=4,
            )
            min_layout_clearance = float(graph_spacing)
            try:
                sampled = sample_values_and_outcome_for_answer(
                    scene_rng,
                    ids=ids,
                    query_type=query_type,
                    answer_value=answer_target,
                    candidates=candidates,
                    candidate_count=candidate_count,
                    target_x=target_x,
                    allow_duplicate_distractors=allow_duplicate_distractors,
                )
            except ValueError:
                continue
            if sampled is None:
                continue
            values_by_id, outcome = sampled

            local_entities = sample_angle_entities_layout(
                scene_rng,
                ids=ids,
                values_by_id=values_by_id,
                canvas_size=int(canvas_size),
                margin=int(margin),
                min_vertex_dist=float(min_vertex_dist),
                graph_spacing=int(graph_spacing),
                ray_length=int(ray_length),
                min_layout_clearance=float(min_layout_clearance),
            )
            if not local_entities:
                continue

            entities = local_entities
            selected_graph_cell_count = int(graph_cell_count)
            selected_graph_spacing = int(graph_spacing)
            break

        if outcome is None or not entities or not values_by_id or selected_graph_cell_count is None or selected_graph_spacing is None:
            raise RuntimeError("failed to generate geometry_angle_value_query instance")

        graph_cell_count = int(selected_graph_cell_count)
        graph_spacing = int(selected_graph_spacing)
        graph_frame = build_graph_coordinate_frame(
            canvas_size=int(canvas_size),
            spacing=int(graph_spacing),
            target_cells=int(graph_cell_count),
        )
        graph_origin = (
            float(graph_frame["origin_pixel"][0]),
            float(graph_frame["origin_pixel"][1]),
        )
        graph_style = dict(base_graph_style)
        graph_style["spacing"] = int(graph_spacing)
        render_graph_style = scaled_graph_style_for_scene(graph_style, scene_scale=scene_scale)
        render_params = enforce_graph_paper_background(params, graph_style=render_graph_style)

        render_canvas_size = int(canvas_size) * int(scene_scale)
        image, background_meta = make_background_canvas(
            canvas_size=render_canvas_size,
            instance_seed=instance_seed,
            params=render_params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
            fallback_color=(248, 248, 248),
        )
        if str(background_meta.get("selected_style", "")) != "graph_paper":
            raise RuntimeError("geometry measurement tasks must render on graph_paper backgrounds")
        draw = ImageDraw.Draw(image)
        render_line_width = max(1, int(line_width) * int(scene_scale))
        for entity in entities.values():
            vertex = scale_point((float(entity["vertex"][0]), float(entity["vertex"][1])), scene_scale)
            end1 = scale_point((float(entity["ray_1"][0]), float(entity["ray_1"][1])), scene_scale)
            end2 = scale_point((float(entity["ray_2"][0]), float(entity["ray_2"][1])), scene_scale)
            draw_angle(draw, vertex=vertex, end1=end1, end2=end2, line_width=render_line_width)

        if scene_scale > 1:
            image = image.resize((int(canvas_size), int(canvas_size)), resample=Image.Resampling.LANCZOS)

        background_meta = dict(background_meta)
        background_meta["style_spec"] = dict(graph_style)
        background_meta["render_scale"] = int(scene_scale)

        image, post_noise_meta = apply_post_image_noise(
            image,
            instance_seed=instance_seed,
            params=render_params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        evidence_artifacts = build_angle_evidence_artifacts(
            query_type=query_type,
            selected_ids=outcome.selected_ids,
            entities=entities,
            graph_origin=graph_origin,
            graph_spacing=int(graph_spacing),
        )
        evidence_type = str(evidence_artifacts.evidence_type)
        evidence_value: Any = evidence_artifacts.evidence_value

        prompt_bundle_id = str(group_default(_PROMPT_DEFAULTS, "bundle_id", "geometry_measurement_v1"))
        prompt_task_type_key = str(group_default(_PROMPT_DEFAULTS, "task_type_key", "measurement_value_query"))
        entity_plural = str(group_default(_PROMPT_DEFAULTS, "entity_plural", "angles"))
        value_name_singular = str(group_default(_PROMPT_DEFAULTS, "value_name_singular", "angle"))
        unit_name = str(group_default(_PROMPT_DEFAULTS, "unit_name", "degrees"))
        evidence_single = str(
            group_default(
                _PROMPT_DEFAULTS,
                "evidence_single",
                "the selected angle vertex coordinate (x, y) in graph units with origin at the center point",
            )
        )
        evidence_pair = str(
            group_default(
                _PROMPT_DEFAULTS,
                "evidence_pair",
                "ordered vertex coordinates [largest, smallest] in graph units with origin at the center point",
            )
        )
        evidence_hint = evidence_pair if query_type == "difference_max_min" else evidence_single
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=prompt_bundle_id,
            task_type_key=prompt_task_type_key,
            query_type=query_type,
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "candidate_count": int(candidate_count),
                "entity_plural": entity_plural,
                "value_name_singular": value_name_singular,
                "unit_name": unit_name,
                "evidence_single": evidence_single,
                "evidence_pair": evidence_pair,
                "evidence_hint": evidence_hint,
                "target_x": int(target_x),
            },
            instance_seed=instance_seed,
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        prompt = str(prompt_artifacts.prompt)
        prompt_variants = dict(prompt_artifacts.prompt_variants)

        values_by_id_sorted = {entity_id: int(entities[entity_id]["value"]) for entity_id in sorted(entities.keys())}
        sorted_values = sorted(values_by_id_sorted.values())
        min_gap = min(
            (sorted_values[idx + 1] - sorted_values[idx] for idx in range(len(sorted_values) - 1)),
            default=angle_step,
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "geometry_angles",
                "entities": build_angle_scene_entities(entities),
                "relations": {},
                "frames": {
                    "pixel": {
                        "origin": [0.0, 0.0],
                        "x_positive": "right",
                        "y_positive": "down",
                    },
                    "graph_unit": {
                        "origin_pixel": list(graph_frame["origin_pixel"]),
                        "spacing_px": int(graph_frame["spacing_px"]),
                        "x_positive": str(graph_frame["x_positive"]),
                        "y_positive": str(graph_frame["y_positive"]),
                    },
                },
            },
            "query_spec": {
                "query_type": query_type,
                "template_id": "geometry_angle_value_query_v1",
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "target_x": int(target_x),
                    "candidate_count": int(candidate_count),
                    "angle_step": int(angle_step),
                    "allow_duplicate_distractors": bool(allow_duplicate_distractors),
                },
            },
            "render_spec": {
                "canvas_size": int(canvas_size),
                "coord_space": "pixel",
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "graph_coordinate_frame": dict(graph_frame),
                "graph_paper_grid": graph_paper_grid_from_frame(graph_frame),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": build_angle_render_anchors(entities),
            },
            "execution_trace": {
                "candidate_values_by_id": values_by_id_sorted,
                "selected_ids": list(outcome.selected_ids),
                "selected_values": list(outcome.selected_values),
                "answer_value": int(outcome.answer_value),
                "answer_sampling_policy": "uniform_feasible_by_query",
                "answer_target": int(answer_target),
                "feasible_answer_values": [int(value) for value in feasible_answers],
                "query_aux": dict(outcome.aux),
            },
            "witness_symbolic": dict(evidence_artifacts.witness_symbolic),
            "projected_evidence": dict(evidence_artifacts.projected_evidence),
        }

        complexity = TaskComplexity(
            complexity_score=_complexity_score(candidate_count=candidate_count, min_gap=int(min_gap), step=angle_step),
            complexity_components={
                "candidate_count": int(candidate_count),
                "min_gap": int(min_gap),
                "query_type": query_type,
            },
        )

        return TaskOutput(
            prompt=prompt,
            answer_gt=TypedValue(type="integer", value=int(outcome.answer_value)),
            evidence_gt=TypedValue(type=evidence_type, value=evidence_value),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_type=query_type,
            prompt_variants=prompt_variants,
        )
