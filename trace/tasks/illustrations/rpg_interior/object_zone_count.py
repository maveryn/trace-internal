"""Count visible objects inside one named RPG interior zone."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.seed import hash64
from trace.core.scene_config import get_scene_defaults
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_scene_generation_rendering_prompt_defaults,
)
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.illustrations.shared.canvas_profiles import resolve_profile_render_params
from trace.tasks.illustrations.shared.task_support import sample_count, string_support, uniform_string_probability_map

from .shared.output import (
    annotation_points,
    counted_zone_objects,
    point_set_projection,
    rpg_interior_render_map,
    rpg_interior_render_spec,
    rpg_interior_scene_ir,
)
from .shared.prompts import build_rpg_interior_prompt_artifacts
from .shared.rendering import (
    DEFAULT_CANVAS_HEIGHT,
    DEFAULT_CANVAS_WIDTH,
    DEFAULT_TILE_PX,
    SCENE_ID,
    TARGET_OBJECT_PLURALS,
    TARGET_OBJECT_PUBLIC_NAMES,
    TARGET_OBJECT_TYPES,
    ZONE_IDS,
    render_rpg_interior_scene,
)


TASK_ID = "task_illustrations__rpg_interior__object_zone_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (SINGLE_QUERY_ID,)
PROMPT_QUERY_KEY = "object_zone_count"
_SCENE_DEFAULTS = get_scene_defaults("illustrations", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)

ZONE_PUBLIC_NAMES: Mapping[str, str] = {
    "counter": "counter",
    "shelf": "shelf",
    "table": "table",
    "storage_corner": "storage corner",
}
ZONE_RELATIONS: Mapping[str, str] = {
    "counter": "on",
    "shelf": "on",
    "table": "on",
    "storage_corner": "in",
}


@dataclass(frozen=True)
class _ObjectZoneSample:
    target_object_type: str
    target_public_name: str
    target_plural: str
    target_zone_id: str
    target_zone_name: str
    zone_relation: str
    target_count: int
    target_object_probabilities: Mapping[str, float]
    target_zone_probabilities: Mapping[str, float]
    target_count_probabilities: Mapping[str, float]


def _select_string(
    *,
    params: Mapping[str, Any],
    support: Tuple[str, ...],
    explicit_key: str,
    namespace: str,
    instance_seed: int,
) -> tuple[str, Mapping[str, float]]:
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        value = str(explicit)
        if value not in set(support):
            raise ValueError(f"{explicit_key} must be one of {support}")
        return value, uniform_string_probability_map(support, selected=value)
    if params.get("_sample_cursor") is not None:
        index = abs(int(params["_sample_cursor"]))
    else:
        index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    value = support[int(index) % len(support)]
    return str(value), uniform_string_probability_map(support)


def _sample_object_zone_query(
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    instance_seed: int,
) -> _ObjectZoneSample:
    """Resolve one scoped-count predicate while keeping sampled values as metadata, not query ids."""

    object_support = string_support(
        params,
        generation_defaults,
        "target_object_type_support",
        TARGET_OBJECT_TYPES,
        valid_values=TARGET_OBJECT_TYPES,
        min_count=1,
    )
    zone_support = string_support(
        params,
        generation_defaults,
        "target_zone_support",
        ZONE_IDS,
        valid_values=ZONE_IDS,
        min_count=1,
    )
    target_object, object_probabilities = _select_string(
        params=params,
        support=object_support,
        explicit_key="target_object_type",
        namespace=f"{TASK_ID}:target_object_type",
        instance_seed=int(instance_seed),
    )
    target_zone, zone_probabilities = _select_string(
        params=params,
        support=zone_support,
        explicit_key="target_zone_id",
        namespace=f"{TASK_ID}:target_zone_id",
        instance_seed=int(instance_seed),
    )
    count_min = int(params.get("target_answer_count_min", group_default(generation_defaults, "target_answer_count_min", 1)))
    count_max = int(params.get("target_answer_count_max", group_default(generation_defaults, "target_answer_count_max", 5)))
    target_count, count_probabilities = sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:target_count",
        low=count_min,
        high=count_max,
        explicit_key="target_count",
    )
    return _ObjectZoneSample(
        target_object_type=str(target_object),
        target_public_name=str(TARGET_OBJECT_PUBLIC_NAMES[str(target_object)]),
        target_plural=str(TARGET_OBJECT_PLURALS[str(target_object)]),
        target_zone_id=str(target_zone),
        target_zone_name=str(ZONE_PUBLIC_NAMES[str(target_zone)]),
        zone_relation=str(ZONE_RELATIONS[str(target_zone)]),
        target_count=int(target_count),
        target_object_probabilities=dict(object_probabilities),
        target_zone_probabilities=dict(zone_probabilities),
        target_count_probabilities={str(key): float(value) for key, value in count_probabilities.items()},
    )


@register_task
class IllustrationsRpgInteriorObjectZoneCountTask:
    """Count visible objects inside one named RPG interior zone."""

    task_id = TASK_ID
    domain = "illustrations"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one object-zone count instance and bind answer/annotation from the same scene trace."""

        resolved_query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SINGLE_QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}:query",
        )
        sample = _sample_object_zone_query(
            params=task_params,
            generation_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        render_params = resolve_profile_render_params(
            task_params,
            _RENDER_DEFAULTS,
            prefix="rpg_interior",
            fallback_width=DEFAULT_CANVAS_WIDTH,
            fallback_height=DEFAULT_CANVAS_HEIGHT,
            fallback_scale=1,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:canvas_profile",
        )
        required_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_rpg_interior_object_zone",
                "annotation_hint_rpg_interior_object_zone",
                "json_example_rpg_interior_object_zone",
                "json_example_answer_only_rpg_interior_object_zone",
            ],
            context="prompt defaults for RPG interior object-zone count",
        )

        scene = None
        counted_entities = ()
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                scene = render_rpg_interior_scene(
                    hash64(int(instance_seed), f"{TASK_ID}:render", int(attempt)),
                    width=int(render_params["canvas_width"]),
                    height=int(render_params["canvas_height"]),
                    tile_px=int(task_params.get("tile_px", group_default(_RENDER_DEFAULTS, "rpg_interior_tile_px", DEFAULT_TILE_PX))),
                    interior_type=str(task_params.get("interior_type", group_default(_RENDER_DEFAULTS, "rpg_interior_type", "auto"))),
                    required_zone_object_counts={
                        sample.target_zone_id: {sample.target_object_type: int(sample.target_count)}
                    },
                    distractor_count_min=int(task_params.get("distractor_count_min", group_default(_RENDER_DEFAULTS, "distractor_count_min", 7))),
                    distractor_count_max=int(task_params.get("distractor_count_max", group_default(_RENDER_DEFAULTS, "distractor_count_max", 13))),
                    render_metadata={
                        "canvas_profile": str(render_params.get("canvas_profile", "")),
                        "canvas_profile_size": list(render_params.get("canvas_profile_size", [])),
                        "canvas_profile_probabilities": dict(render_params.get("canvas_profile_probabilities", {})),
                    },
                )
                counted_entities = counted_zone_objects(
                    scene,
                    target_object_type=sample.target_object_type,
                    target_zone_id=sample.target_zone_id,
                )
                if len(counted_entities) == int(sample.target_count):
                    break
                last_error = RuntimeError(
                    f"RPG interior count mismatch: expected {sample.target_count}, got {len(counted_entities)}"
                )
                scene = None
            except Exception as exc:  # pragma: no cover - retry path
                last_error = exc
                scene = None
        if scene is None:
            raise RuntimeError(f"could not generate RPG interior object-zone count: {last_error}") from last_error

        counted_entity_ids = tuple(sorted(str(entity.entity_id) for entity in counted_entities))
        annotation_value = annotation_points(scene, counted_entity_ids)
        answer = int(len(counted_entity_ids))
        prompt_artifacts = build_rpg_interior_prompt_artifacts(
            domain=self.domain,
            scene_id=SCENE_ID,
            prompt_defaults=required_defaults,
            prompt_query_key=PROMPT_QUERY_KEY,
            slots={
                "target_plural": sample.target_plural,
                "target_unit": sample.target_public_name,
                "zone_relation": sample.zone_relation,
                "zone_name": sample.target_zone_name,
                "json_output_contract": str(required_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(required_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(required_defaults["answer_hint_rpg_interior_object_zone"]).format(
                    target_plural=sample.target_plural,
                    zone_relation=sample.zone_relation,
                    zone_name=sample.target_zone_name,
                ),
                "annotation_hint": str(required_defaults["annotation_hint_rpg_interior_object_zone"]).format(
                    target_unit=sample.target_public_name,
                    zone_relation=sample.zone_relation,
                    zone_name=sample.target_zone_name,
                ),
                "json_example": str(required_defaults["json_example_rpg_interior_object_zone"]),
                "json_example_answer_only": str(required_defaults["json_example_answer_only_rpg_interior_object_zone"]),
            },
            instance_seed=int(instance_seed),
        )
        query_params = {
            "query_id": str(resolved_query_id),
            "prompt_query_key": PROMPT_QUERY_KEY,
            "query_id_probabilities": dict(query_probabilities),
            "target_object_type": sample.target_object_type,
            "target_public_name": sample.target_public_name,
            "target_plural": sample.target_plural,
            "target_zone_id": sample.target_zone_id,
            "target_zone_name": sample.target_zone_name,
            "zone_relation": sample.zone_relation,
            "target_count": int(answer),
            "target_answer_count_min": int(task_params.get("target_answer_count_min", group_default(_GEN_DEFAULTS, "target_answer_count_min", 1))),
            "target_answer_count_max": int(task_params.get("target_answer_count_max", group_default(_GEN_DEFAULTS, "target_answer_count_max", 5))),
            "target_object_probabilities": dict(sample.target_object_probabilities),
            "target_zone_probabilities": dict(sample.target_zone_probabilities),
            "target_count_probabilities": dict(sample.target_count_probabilities),
            "canvas_profile": str(render_params.get("canvas_profile", "")),
            "canvas_profile_probabilities": dict(render_params.get("canvas_profile_probabilities", {})),
        }
        trace_payload = {
            "scene_ir": rpg_interior_scene_ir(
                domain=self.domain,
                scene_id=SCENE_ID,
                scene=scene,
                relations={
                    "query_id": str(resolved_query_id),
                    "prompt_query_key": PROMPT_QUERY_KEY,
                    "target_object_type": sample.target_object_type,
                    "target_zone_id": sample.target_zone_id,
                },
            ),
            "query_spec": {
                "task_id": TASK_ID,
                "query_id": str(resolved_query_id),
                "prompt_query_key": PROMPT_QUERY_KEY,
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": query_params,
            },
            "render_spec": rpg_interior_render_spec(scene, scene_id=SCENE_ID),
            "render_map": rpg_interior_render_map(scene=scene, counted_entity_ids=counted_entity_ids),
            "execution_trace": {
                "query_id": str(resolved_query_id),
                "prompt_query_key": PROMPT_QUERY_KEY,
                "scene_id": SCENE_ID,
                "answer": int(answer),
                "target_object_type": sample.target_object_type,
                "target_zone_id": sample.target_zone_id,
                "counted_entity_ids": list(counted_entity_ids),
                "renderer": dict(scene.trace),
            },
            "witness_symbolic": {
                "counted_entity_ids": list(counted_entity_ids),
                "target_object_type": sample.target_object_type,
                "target_zone_id": sample.target_zone_id,
                "count": int(answer),
                "answer": int(answer),
            },
            "projected_annotation": point_set_projection(annotation_value),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="integer", value=int(answer)),
            annotation_gt=TypedValue(type="point_set", value=annotation_value),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(resolved_query_id),
        )


__all__ = [
    "IllustrationsRpgInteriorObjectZoneCountTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
