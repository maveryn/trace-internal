"""Polygon angle-chase measurement task wrappers."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from trace.tasks.shared.fixed_query import select_task_query_id

from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

SCENE_ID = "polygon_angle_chase"
from ..shared.annotation_values import keyed_point_annotation_artifacts
from ..shared.metadata_serialization import geometry_json_ready
from ..shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS

from .shared.measurement.polygon_angle_chase_common import (
    SCENE_ID,
    _RenderContext,
    _RenderedParallelLineScene,
    _RenderedPolygonScene,
    _RenderedSymmetryAngleScene,
    _ResolvedParallelLineProblem,
    _ResolvedPolygonProblem,
    _ResolvedSymmetryAngleProblem,
    _angle_name,
    _make_prompt_examples,
    _polygon_kind,
    _query_angle_sum,
)
from .shared.measurement.polygon_angle_chase_rendering import (
    _make_render_context,
    _render_parallel_line_problem,
    _render_problem,
    _render_symmetry_angle_problem,
)
from .shared.measurement.polygon_angle_chase_sampling import (
    _resolve_parallel_line_problem,
    _resolve_problem,
    _resolve_symmetry_angle_problem,
)

_SCENE_DEFAULTS = get_scene_defaults("geometry", "polygon_angle_chase")
TASK_ID = "task_geometry__polygon_angle_chase__parallel_line_angle_value"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ('single_transversal_chain', 'two_transversal_angle_sum')
SAMPLING_NAMESPACE = "parallel_line_angle_value"


def _select_query(instance_seed: int, params: Dict[str, Any]) -> tuple[str, dict[str, float], Dict[str, Any]]:
    return select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id=SUPPORTED_QUERY_IDS[0],
        task_id=TASK_ID,
        namespace=f"{TASK_ID}.query",
    )


@register_task
class GeometryPolygonAngleChaseParallelLineAngleValueTask:
    """Infer a missing angle from parallel-line transversal relations."""

    task_id = TASK_ID
    domain = "geometry"
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_probabilities, task_params = _select_query(int(instance_seed), params)
        generation_defaults, rendering_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
            _SCENE_DEFAULTS,
            task_id=TASK_ID,
        )
        rendered: _RenderedParallelLineScene | None = None
        problem: _ResolvedParallelLineProblem | None = None
        ctx: _RenderContext | None = None
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_params = {**task_params, "query_id": str(query_id)}
            attempt_params["_render_attempt"] = int(attempt)
            try:
                problem = _resolve_parallel_line_problem(
                    sampling_namespace=SAMPLING_NAMESPACE,
                    instance_seed=int(instance_seed) + int(attempt),
                    params=attempt_params,
                    generation_defaults=generation_defaults,
                )
                ctx = _make_render_context(
                    int(instance_seed) + int(attempt),
                    attempt_params,
                    rendering_defaults,
                )
                rendered = _render_parallel_line_problem(
                    ctx,
                    problem,
                    instance_seed=int(instance_seed) + int(attempt),
                )
                break
            except Exception as exc:
                last_error = exc
                continue
        if rendered is None or problem is None or ctx is None:
            raise RuntimeError(f"failed to generate {self.task_id}") from last_error

        image, noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt_defaults = required_group_defaults(
            prompt_defaults,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "object_description",
                "json_output_contract",
                "json_output_contract_answer_only",
                "annotation_hint",
                "answer_hint_integer",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        annotation_keys = tuple(rendered.annotation_keyed_points.keys())
        json_example, json_example_answer_only = _make_prompt_examples(annotation_keys)
        annotation_key_list = ", ".join(f'"{key}"' for key in annotation_keys)
        annotation_hint = str(prompt_defaults["annotation_hint"]).format(annotation_keys=annotation_key_list)
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=str(getattr(self, "scene_id", "") or getattr(self, "public_scene_id", "") or globals().get("SCENE_ID", "")),
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(problem.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "target_angle_label": str(problem.target_angle_label),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(annotation_hint),
                "answer_hint": str(prompt_defaults["answer_hint_integer"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        annotation_artifacts = keyed_point_annotation_artifacts(rendered.annotation_keyed_points)
        annotation_value = annotation_artifacts.value
        intersections_payload = {
            str(key): [round(float(point[0]), 3), round(float(point[1]), 3)]
            for key, point in rendered.intersections.items()
        }
        render_map = {
            "angle_arc_bboxes": geometry_json_ready(rendered.angle_arc_bboxes, round_floats=False),
            "angle_label_bboxes": geometry_json_ready(rendered.angle_label_bboxes, round_floats=False),
            "line_segments": geometry_json_ready(rendered.line_segments, round_floats=False),
            "intersections": dict(intersections_payload),
        }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": str(self.scene_id or self.public_scene_id),
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "entities": {
                    "parallel_lines": [
                        str(key) for key in sorted(rendered.line_segments) if key.startswith("parallel_line_")
                    ],
                    "transversals": [
                        str(key) for key in sorted(rendered.line_segments) if key.startswith("transversal")
                    ],
                    "intersections": dict(intersections_payload),
                },
                "relations": {
                    "type": "parallel_line_angle_chain",
                    "query_id": str(problem.query_id),
                    "relation_id": str(problem.relation_id),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "params": {
                    "query_id": str(problem.query_id),
                    "query_id_probabilities": dict(problem.query_probabilities),
                    "relation_id": str(problem.relation_id),
                    "relation_id_probabilities": dict(problem.relation_probabilities),
                },
            },
            "render_spec": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "canvas": {"width": int(ctx.width), "height": int(ctx.height)},
                "style": {
                    "technical_diagram": dict(ctx.diagram_style_meta),
                    "background": dict(ctx.background_meta),
                    "post_image_noise": dict(noise_meta),
                },
                "prompt": {
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                },
            },
            "render_map": dict(render_map),
            "execution_trace": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "target_angle_label": str(problem.target_angle_label),
                "support_angles": [int(value) for value in problem.support_angles],
                "answer": int(problem.answer),
                "annotation_roles": list(rendered.annotation_roles),
                **dict(problem.witness),
            },
            "witness_symbolic": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                **dict(problem.witness),
            },
            "projected_annotation": dict(annotation_artifacts.projected_annotation),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(problem.answer)),
            annotation_gt=TypedValue(type="keyed_point_map", value=dict(annotation_value)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(problem.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )




__all__ = [
    'GeometryPolygonAngleChaseInteriorAngleValueTask',
    'GeometryPolygonAngleChaseParallelLineAngleValueTask',
    'GeometryPolygonAngleChaseSymmetryAngleValueTask',
]
