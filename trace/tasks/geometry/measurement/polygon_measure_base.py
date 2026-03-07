"""Shared base implementation for single-object polygon measurement tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_optional_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.graph_rendering import graph_paper_grid_from_frame, scale_point
from ..shared.polygon_geometry import (
    PolygonInstance,
    draw_polygon_outline,
    polygon_render_anchor,
    polygon_scene_entity,
    polygon_vertices_evidence_artifacts,
    sample_polygon_instance_on_graph_paper,
)
from ..shared.shape_style import sample_geometry_shape_style
from ..shared.single_object_scene import (
    finalize_graph_scene_image,
    make_graph_scene_canvas,
    resolve_graph_scene_context,
)
from .defaults import MEASUREMENT_SHARED_DEFAULTS
from ..shared.background_defaults import POST_IMAGE_BACKGROUND_DEFAULTS
from ..shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS

_QUERY_TYPE = "measure"


def _resolve_allowed_sides(params: Mapping[str, Any], *, gen_defaults: Mapping[str, Any]) -> List[int]:
    """Resolve allowed polygon sides from params/defaults."""
    supported_raw = group_default(gen_defaults, "allowed_sides", list(MEASUREMENT_SHARED_DEFAULTS.polygon_allowed_sides))
    if not isinstance(supported_raw, Sequence) or isinstance(supported_raw, (str, bytes)):
        raise ValueError("generation.allowed_sides must be a sequence of ints")
    supported_sides = sorted({int(item) for item in supported_raw if int(item) >= 3})
    if not supported_sides:
        raise ValueError("generation.allowed_sides resolved empty")

    requested_raw = params.get("allowed_sides")
    if requested_raw is None:
        return [int(item) for item in supported_sides]
    if not isinstance(requested_raw, Sequence) or isinstance(requested_raw, (str, bytes)):
        raise ValueError("allowed_sides must be a sequence of ints")
    requested_sides = sorted({int(item) for item in requested_raw if int(item) >= 3})
    if not requested_sides:
        raise ValueError("allowed_sides resolved empty")

    supported_set = set(supported_sides)
    unsupported = [int(item) for item in requested_sides if int(item) not in supported_set]
    if unsupported:
        raise ValueError(
            "allowed_sides includes unsupported values "
            f"{unsupported}; supported values are {supported_sides}"
        )
    return [int(item) for item in requested_sides]


class GeometryPolygonMeasureBase:
    """Reusable task base for polygon area/perimeter measurement variants."""

    task_id = ""
    domain = "geometry"
    task_group = "measurement"
    scene_kind = ""
    query_template_id = ""
    answer_component_key = ""

    @staticmethod
    def supported_query_types(_params: Dict[str, Any] | None = None) -> List[str]:
        return [_QUERY_TYPE]

    def _answer_value_from_instance(self, instance: PolygonInstance) -> int:
        """Return task answer value from one polygon instance."""
        raise NotImplementedError

    def _complexity_score(self, *, sides: int, answer_value: int) -> float:
        """Return task-specific complexity score."""
        raise NotImplementedError

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic polygon measurement instance."""
        query_type = str(params.get("query_type", _QUERY_TYPE))
        if query_type != _QUERY_TYPE:
            raise ValueError(f"unsupported query_type: {query_type}")

        task_group_defaults = get_task_group_defaults(self.domain, self.task_group)
        gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            task_group_defaults if isinstance(task_group_defaults, Mapping) else {},
            task_id=str(self.task_id),
        )

        scene_rng = spawn_rng(instance_seed, "scene")
        context = resolve_graph_scene_context(
            scene_rng,
            params=params,
            render_defaults=render_defaults,
            background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
            fallback_canvas_min=MEASUREMENT_SHARED_DEFAULTS.canvas_size_min,
            fallback_canvas_max=MEASUREMENT_SHARED_DEFAULTS.canvas_size_max,
            fallback_cells_min=MEASUREMENT_SHARED_DEFAULTS.graph_cells_min,
            fallback_cells_max=MEASUREMENT_SHARED_DEFAULTS.graph_cells_max,
        )
        line_width = int(
            params.get(
                "line_width",
                group_default(render_defaults, "line_width", MEASUREMENT_SHARED_DEFAULTS.line_width),
            )
        )
        allowed_sides = _resolve_allowed_sides(params, gen_defaults=gen_defaults)
        answer_min, answer_max = resolve_optional_int_bounds(
            params,
            gen_defaults,
            min_key="answer_min",
            max_key="answer_max",
            context=f"generation defaults for {self.task_id}",
        )
        shape_style = sample_geometry_shape_style(
            scene_rng,
            params=params,
            render_defaults=render_defaults,
        )

        image, draw, background_meta = make_graph_scene_canvas(
            instance_seed=int(instance_seed),
            context=context,
            background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
        )

        polygon_instance = None
        answer_value = None
        range_rejections = 0
        last_error: Exception | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                candidate_instance = sample_polygon_instance_on_graph_paper(
                    scene_rng,
                    allowed_sides=allowed_sides,
                    canvas_size=int(context.canvas_size),
                    graph_spacing=int(context.graph_spacing),
                    graph_origin=(float(context.graph_origin[0]), float(context.graph_origin[1])),
                    padding_units=0,
                    max_attempts=8,
                    min_area_square_units=4,
                )
                candidate_answer = int(self._answer_value_from_instance(candidate_instance))
                if answer_min is not None and int(candidate_answer) < int(answer_min):
                    range_rejections += 1
                    continue
                if answer_max is not None and int(candidate_answer) > int(answer_max):
                    range_rejections += 1
                    continue
                polygon_instance = candidate_instance
                answer_value = int(candidate_answer)
                break
            except Exception as exc:  # bounded retry path
                last_error = exc
                continue
        if polygon_instance is None:
            if range_rejections > 0 and last_error is None:
                raise RuntimeError(
                    f"failed to generate {self.task_id} instance in requested answer range "
                    f"[{answer_min}, {answer_max}]"
                )
            raise RuntimeError(f"failed to generate {self.task_id} instance") from last_error

        draw_polygon_outline(
            draw,
            vertices=[scale_point(point, int(context.scene_scale)) for point in polygon_instance.vertices],
            line_width=max(1, int(line_width) * int(context.scene_scale)),
            line_color=tuple(int(value) for value in shape_style.line_color),
        )
        evidence = polygon_vertices_evidence_artifacts(
            instance=polygon_instance,
            graph_origin=context.graph_origin,
            graph_spacing=int(context.graph_spacing),
        )

        image, background_meta_final, post_noise_meta = finalize_graph_scene_image(
            image,
            instance_seed=int(instance_seed),
            context=context,
            background_meta=background_meta,
            noise_defaults=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_required = required_group_defaults(
            prompt_defaults,
            (
                "bundle_id",
                "task_type_key",
                "question_text",
                "json_output_contract",
                "evidence_hint",
                "answer_hint",
                "json_example",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_bundle_id = str(prompt_required["bundle_id"])
        prompt_task_type_key = str(prompt_required["task_type_key"])
        question_text = str(prompt_required["question_text"]).strip()
        json_output_contract = str(prompt_required["json_output_contract"])
        evidence_hint = str(prompt_required["evidence_hint"])
        answer_hint = str(prompt_required["answer_hint"])
        json_example = str(prompt_required["json_example"])
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=prompt_bundle_id,
            task_type_key=prompt_task_type_key,
            query_type=_QUERY_TYPE,
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": "a single polygon",
                "question_text": str(question_text),
                "json_output_contract": str(json_output_contract),
                "evidence_hint": str(evidence_hint),
                "answer_hint": str(answer_hint),
                "json_example": str(json_example),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        if answer_value is None:
            answer_value = int(self._answer_value_from_instance(polygon_instance))
        trace_payload = {
            "scene_ir": {
                "scene_kind": str(self.scene_kind),
                "entities": [polygon_scene_entity(polygon_instance)],
                "relations": {},
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "graph_unit": {
                        "origin_pixel": list(context.graph_frame["origin_pixel"]),
                        "spacing_px": int(context.graph_frame["spacing_px"]),
                        "x_positive": str(context.graph_frame["x_positive"]),
                        "y_positive": str(context.graph_frame["y_positive"]),
                    },
                },
            },
            "query_spec": {
                "query_type": _QUERY_TYPE,
                "template_id": str(self.query_template_id),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "allowed_sides": [int(item) for item in allowed_sides],
                    "answer_min": (int(answer_min) if answer_min is not None else None),
                    "answer_max": (int(answer_max) if answer_max is not None else None),
                },
            },
            "render_spec": {
                "canvas_size": int(context.canvas_size),
                "coord_space": "pixel",
                "background_style": dict(background_meta_final),
                "post_image_noise": dict(post_noise_meta),
                "shape_style": dict(shape_style.to_trace_dict()),
                "graph_coordinate_frame": dict(context.graph_frame),
                "graph_paper_grid": graph_paper_grid_from_frame(context.graph_frame),
            },
            "render_map": {"image_id": "img0", "anchors": {"polygon_1": polygon_render_anchor(polygon_instance)}},
            "execution_trace": {
                "answer_value": int(answer_value),
                "area_square_units": int(polygon_instance.area_square_units),
                "perimeter_units": int(polygon_instance.perimeter_units),
                "polygon_sides": int(polygon_instance.sides),
                "template_id": str(polygon_instance.template_id),
            },
            "witness_symbolic": dict(evidence["witness_symbolic"]),
            "projected_evidence": dict(evidence["projected_evidence"]),
        }
        complexity = TaskComplexity(
            complexity_score=self._complexity_score(sides=int(polygon_instance.sides), answer_value=int(answer_value)),
            complexity_components={
                "polygon_sides": int(polygon_instance.sides),
                str(self.answer_component_key): int(answer_value),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(answer_value)),
            evidence_gt=TypedValue(type=str(evidence["evidence_type"]), value=evidence["evidence_value"]),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_type=_QUERY_TYPE,
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
