"""Count boats docked on the image-left or image-right side of the main dock."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.scene_config import get_scene_defaults
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import (
    required_group_defaults,
    split_scene_generation_rendering_prompt_defaults,
)
from trace.tasks.shared.deterministic_sampling import uniform_probability_map
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.illustrations.shared.canvas_profiles import resolve_canvas_profile

from .shared.output import (
    bbox_set_projection,
    isometric_harbor_boat_count_render_map,
    isometric_harbor_render_spec,
    isometric_harbor_scene_ir,
)
from .shared.prompts import build_isometric_harbor_prompt_artifacts
from .shared.rendering import BOAT_SIDE_VALUES, SCENE_ID, render_isometric_harbor_scene
from .shared.sampling import CountTaskSampleSpec, select_count
from .shared.spatial_primitives import rounded_bbox
from .shared.state import IsoHarborEntity, IsoHarborScene


TASK_ID = "task_illustrations__isometric_harbor__boat_side_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("left_side_boat_count", "right_side_boat_count")
QUERY_TO_SIDE: Mapping[str, str] = {
    "left_side_boat_count": "left",
    "right_side_boat_count": "right",
}


@dataclass(frozen=True)
class _SampleSpec(CountTaskSampleSpec):
    target_side: str
    target_side_label: str


_SCENE_DEFAULTS = get_scene_defaults("illustrations", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _SampleSpec:
    """Resolve query, target count, and canvas profile for one boat-side count."""

    selected_query, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id="left_side_boat_count",
        task_id=TASK_ID,
        namespace=f"{TASK_ID}:query",
    )
    target_count, target_count_probabilities, answer_count_support = select_count(
        instance_seed=int(instance_seed),
        params=task_params,
        defaults=_GEN_DEFAULTS,
        support_key="answer_count_support",
        explicit_key="target_count",
        fallback=(0, 1, 2, 3, 4, 5),
        namespace=f"{TASK_ID}:target_count",
    )
    profile = resolve_canvas_profile(
        params=task_params,
        defaults=_RENDER_DEFAULTS,
        fallback_width=1200,
        fallback_height=800,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:canvas_profile",
    )
    target_side = str(QUERY_TO_SIDE[str(selected_query)])
    target_side_label = "image-left side" if target_side == "left" else "image-right side"
    return _SampleSpec(
        selected_key=str(selected_query),
        prompt_query_key=str(selected_query),
        query_probabilities=dict(query_probabilities),
        target_count=int(target_count),
        target_count_probabilities=dict(target_count_probabilities),
        answer_count_support=tuple(int(value) for value in answer_count_support),
        answer_count_probabilities=dict(uniform_probability_map(answer_count_support)),
        canvas_width=int(profile.width),
        canvas_height=int(profile.height),
        canvas_profile=str(profile.profile_id),
        canvas_profile_probabilities=dict(profile.probabilities),
        target_side=target_side,
        target_side_label=target_side_label,
    )


def _matching_boats(scene: IsoHarborScene, *, target_side: str) -> tuple[IsoHarborEntity, ...]:
    return tuple(
        sorted(
            (
                entity
                for entity in scene.entities
                if str(entity.object_type) == "boat"
                and str(entity.metadata.get("dock_side", "")) == str(target_side)
            ),
            key=lambda entity: (float(entity.bbox_xyxy[1]), float(entity.bbox_xyxy[0]), str(entity.entity_id)),
        )
    )


def _prompt_slots(prompt_defaults: Mapping[str, Any], sample: _SampleSpec) -> dict[str, str]:
    return {
        "target_side_label": str(sample.target_side_label),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_defaults["answer_hint_boat_side_count"]).format(
            target_side_label=str(sample.target_side_label)
        ),
        "annotation_hint": str(prompt_defaults["annotation_hint_boat_side_count"]).format(
            target_side_label=str(sample.target_side_label)
        ),
        "json_example": str(prompt_defaults["json_example_boat_side_count"]),
        "json_example_answer_only": str(prompt_defaults["json_example_answer_only_boat_side_count"]),
    }


@register_task
class IllustrationsIsometricHarborBoatSideCountTask:
    """Count boats docked on one side of the main dock."""

    task_id = TASK_ID
    domain = "illustrations"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one harbor boat-side count with answer and annotation from one trace."""

        sample = _sample_spec(instance_seed=int(instance_seed), params=params)
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_boat_side_count",
                "annotation_hint_boat_side_count",
                "json_example_boat_side_count",
                "json_example_answer_only_boat_side_count",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )

        last_error: Exception | None = None
        scene: IsoHarborScene | None = None
        matching_boats: tuple[IsoHarborEntity, ...] = ()
        for attempt in range(max(1, int(max_attempts))):
            try:
                scene_seed = int(instance_seed) + int(attempt) * 1009
                scene = render_isometric_harbor_scene(
                    scene_seed,
                    width=sample.canvas_width,
                    height=sample.canvas_height,
                    canvas_profile=sample.canvas_profile,
                    canvas_profile_probabilities=sample.canvas_profile_probabilities,
                    required_boat_counts_by_side={str(sample.target_side): int(sample.target_count)},
                )
                matching_boats = _matching_boats(scene, target_side=sample.target_side)
                if len(matching_boats) != int(sample.target_count):
                    raise ValueError(
                        f"count {len(matching_boats)} did not match target_count {sample.target_count}"
                    )
                break
            except Exception as exc:
                last_error = exc
        else:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error
        if scene is None:
            raise RuntimeError(f"could not generate {TASK_ID}: missing scene")

        annotation_value = [rounded_bbox(entity.bbox_xyxy) for entity in matching_boats]
        counted_entity_ids = tuple(str(entity.entity_id) for entity in matching_boats)
        prompt_artifacts = build_isometric_harbor_prompt_artifacts(
            domain=self.domain,
            scene_id=SCENE_ID,
            prompt_defaults=prompt_defaults,
            prompt_query_key=sample.prompt_query_key,
            slots=_prompt_slots(prompt_defaults, sample),
            instance_seed=int(instance_seed),
        )
        render_map = isometric_harbor_boat_count_render_map(
            scene=scene,
            target_side=sample.target_side,
            counted_entity_ids=counted_entity_ids,
        )
        query_params = {
            "query_id": str(sample.selected_key),
            "prompt_query_key": str(sample.prompt_query_key),
            "query_id_probabilities": dict(sample.query_probabilities),
            "target_side": str(sample.target_side),
            "target_side_label": str(sample.target_side_label),
            "allowed_sides": list(BOAT_SIDE_VALUES),
            "target_count": int(sample.target_count),
            "target_count_probabilities": dict(sample.target_count_probabilities),
            "answer_count_support": list(sample.answer_count_support),
            "answer_count_probabilities": dict(sample.answer_count_probabilities),
            "answer_count": int(len(matching_boats)),
            "counted_entity_ids": list(counted_entity_ids),
            "canvas_profile": str(sample.canvas_profile),
            "canvas_profile_probabilities": dict(sample.canvas_profile_probabilities),
        }
        trace_payload = {
            "scene_ir": isometric_harbor_scene_ir(
                domain=self.domain,
                scene_id=SCENE_ID,
                scene=scene,
                relations={
                    "operation": "count_boats_on_main_dock_side",
                    "target_side": str(sample.target_side),
                    "target_side_label": str(sample.target_side_label),
                    "answer_count": int(len(matching_boats)),
                    "counted_entity_ids": list(counted_entity_ids),
                    "counted_entity_bboxes_px": [list(bbox) for bbox in annotation_value],
                },
            ),
            "query_spec": {
                "task_id": TASK_ID,
                "query_id": str(sample.selected_key),
                "prompt_query_key": str(sample.prompt_query_key),
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": query_params,
            },
            "render_spec": isometric_harbor_render_spec(scene, scene_id=SCENE_ID),
            "render_map": render_map,
            "execution_trace": {
                "query_id": str(sample.selected_key),
                "prompt_query_key": str(sample.prompt_query_key),
                "scene_id": SCENE_ID,
                "answer": int(len(matching_boats)),
                "target_side": str(sample.target_side),
                "target_side_label": str(sample.target_side_label),
                "counted_entity_ids": list(counted_entity_ids),
                "renderer": dict(scene.trace),
            },
            "witness_symbolic": {
                "answer_count": int(len(matching_boats)),
                "target_side": str(sample.target_side),
                "target_side_label": str(sample.target_side_label),
                "counted_entity_ids": list(counted_entity_ids),
                "counted_entity_bboxes": [list(bbox) for bbox in annotation_value],
            },
            "projected_annotation": bbox_set_projection(annotation_value),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="integer", value=int(len(matching_boats))),
            annotation_gt=TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_value]),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sample.selected_key),
        )


__all__ = [
    "IllustrationsIsometricHarborBoatSideCountTask",
    "QUERY_TO_SIDE",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
