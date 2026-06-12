"""Survey traverse measurement task wrappers."""

from __future__ import annotations

from typing import Any, Dict

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

from ..shared.annotation_values import keyed_bbox_annotation_artifacts, keyed_point_annotation_artifacts
from ..shared.metadata_serialization import geometry_json_ready
from ..shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS

from .shared.measurement.survey_traverse_common import (
    AREA_QUERY_IDS,
    ELEVATION_QUERY_IDS,
    QUERY_IDS,
    SCENE_ID,
    _AREA_ANNOTATION_KEYS,
    _RenderContext,
    _RenderedSurveyAreaScene,
    _RenderedSurveyScene,
)
from .shared.measurement.survey_traverse_rendering import _make_context, _render_area_scene, _render_elevation_scene, _render_scene
from .shared.measurement.survey_traverse_sampling import _resolve_area_problem, _resolve_elevation_problem, _resolve_problem

_SCENE_DEFAULTS = get_scene_defaults("geometry", SCENE_ID)

TASK_ID = "task_geometry__survey_traverse__station_elevation_value"
SUPPORTED_QUERY_IDS = ELEVATION_QUERY_IDS

PROMPT_TASK_KEY = "station_elevation_value_query"
OBJECT_DESCRIPTION_KEY = "object_description_elevation"
ANNOTATION_HINT_KEY = "annotation_hint_elevation"
ANSWER_HINT_KEY = "answer_hint_elevation"
JSON_EXAMPLE_KEY = "json_example_elevation"
JSON_EXAMPLE_ANSWER_ONLY_KEY = "json_example_answer_only_elevation"


@register_task
class GeometrySurveyTraverseStationElevationValueTask:
    """Compute a missing station elevation from a survey leveling/profile diagram."""

    task_id = TASK_ID
    domain = "geometry"
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _generation_defaults, rendering_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
            _SCENE_DEFAULTS,
            task_id=self.task_id,
        )
        problem = _resolve_elevation_problem(instance_seed=int(instance_seed), params=params)
        rendered: _RenderedSurveyScene | None = None
        ctx: _RenderContext | None = None
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                ctx, _render_meta = _make_context(
                    instance_seed=int(instance_seed) + int(attempt),
                    params=params,
                    render_defaults=rendering_defaults,
                )
                rendered = _render_elevation_scene(ctx, problem, instance_seed=int(instance_seed) + int(attempt))
                break
            except Exception as exc:
                last_error = exc
                continue
        if rendered is None or ctx is None:
            raise RuntimeError(f"failed to generate {self.task_id}") from last_error

        image, noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt_defaults = dict(prompt_defaults)
        prompt_defaults["task_key"] = PROMPT_TASK_KEY
        prompt_defaults["object_description"] = str(prompt_defaults[OBJECT_DESCRIPTION_KEY])
        prompt_defaults["annotation_hint"] = str(prompt_defaults[ANNOTATION_HINT_KEY])
        prompt_defaults["answer_hint"] = str(prompt_defaults[ANSWER_HINT_KEY])
        prompt_defaults["json_example"] = str(prompt_defaults[JSON_EXAMPLE_KEY])
        prompt_defaults["json_example_answer_only"] = str(prompt_defaults[JSON_EXAMPLE_ANSWER_ONLY_KEY])
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
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
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
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        annotation_artifacts = keyed_point_annotation_artifacts(
            rendered.annotation_keyed_points,
            roles=rendered.annotation_roles,
        )
        annotation_value = annotation_artifacts.value
        answer_value = int(problem.answer)
        formula_family = (
            "survey_leveling_station_elevation"
            if problem.query_id == "leveling_station_elevation"
            else "survey_slope_distance_elevation_change"
        )
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": "geometry_survey_traverse",
                "scene_id": SCENE_ID,
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "query_id": str(problem.query_id),
                    "answer_value": int(answer_value),
                    "annotation_roles": list(rendered.annotation_roles),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "params": {
                    "query_id": str(problem.query_id),
                    "query_id_probabilities": dict(problem.query_probabilities),
                    "case_probabilities": dict(problem.case_probabilities),
                    **dict(rendered.witness),
                },
            },
            "render_spec": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "canvas": {"width": int(image.size[0]), "height": int(image.size[1])},
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
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "answer": int(answer_value),
                "formula_family": formula_family,
                "reference_elevation": int(problem.reference_elevation),
                "target_elevation": int(problem.target_elevation),
                "backsight": problem.backsight,
                "foresight": problem.foresight,
                "height_of_instrument": problem.height_of_instrument,
                "slope_distance": problem.slope_distance,
                "rise_per_20": problem.rise_per_20,
                "total_rise": problem.total_rise,
                "annotation_roles": list(rendered.annotation_roles),
                **dict(rendered.witness),
            },
            "witness_symbolic": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "formula_family": formula_family,
                "answer_value": int(answer_value),
                **dict(rendered.witness),
            },
            "projected_annotation": dict(annotation_artifacts.projected_annotation),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(answer_value)),
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
    'GeometrySurveyTraverseBearingAngleValueTask',
    'GeometrySurveyTraverseStationElevationValueTask',
    'GeometrySurveyTraverseTraverseAreaValueTask',
]
