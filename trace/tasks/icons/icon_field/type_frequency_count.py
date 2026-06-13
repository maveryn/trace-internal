"""Count icon instances by icon-type frequency role in a free icon field."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.seed import spawn_rng
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    load_scene_generation_rendering_prompt_defaults,
    required_group_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from .shared.annotations import bboxes_for_icon_ids, indices_for_icon_ids
from .shared.defaults import IconFieldDefaults
from .shared.rendering import sample_and_render_icon_field_scene
from .shared.sampling import resolve_most_frequent_frequency_spec, resolve_singleton_frequency_spec
from .shared.styles import icon_field_style_trace, resolve_icon_field_render_params


TASK_ID = "task_icons__icon_field__type_frequency_count"
DOMAIN = "icons"
SCENE_ID = "icon_field"
SINGLETON_QUERY_ID = "singleton_type_count"
MOST_FREQUENT_QUERY_ID = "most_frequent_type_count"
SUPPORTED_QUERY_IDS: Tuple[str, str] = (SINGLETON_QUERY_ID, MOST_FREQUENT_QUERY_ID)
NOISE_NAMESPACE = "icon_field_type_frequency"


_DEFAULTS = IconFieldDefaults()
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    DOMAIN,
    SCENE_ID,
    task_id=TASK_ID,
)


def _type_frequency_query_probabilities(*, selected: str | None = None) -> Dict[str, float]:
    """Return the public query distribution for icon-field frequency counting."""

    if selected is not None:
        return {str(selected): 1.0}

    raw_weights = _GEN_DEFAULTS.get("query_id_weights")
    if isinstance(raw_weights, Mapping):
        weights = {
            str(query_id): float(raw_weights.get(str(query_id), 0.0))
            for query_id in SUPPORTED_QUERY_IDS
        }
        total = sum(float(value) for value in weights.values())
        if total > 0.0:
            return {
                str(query_id): float(weights[str(query_id)]) / float(total)
                for query_id in SUPPORTED_QUERY_IDS
            }

    probability = 1.0 / float(len(SUPPORTED_QUERY_IDS))
    return {str(query_id): float(probability) for query_id in SUPPORTED_QUERY_IDS}


def _type_frequency_generation_params(query_id: str) -> Dict[str, Any]:
    """Return query-local generation defaults for the icon-field task."""

    raw = _GEN_DEFAULTS.get("variant_generation_params", {})
    if not isinstance(raw, Mapping):
        return {}
    selected = raw.get(str(query_id), {})
    if not isinstance(selected, Mapping):
        return {}
    return dict(selected)


def _resolve_type_frequency_query(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    """Resolve the icon frequency predicate for this public task."""

    explicit_query = params.get("query_id")
    if explicit_query is not None:
        query_id = str(explicit_query)
        if query_id not in SUPPORTED_QUERY_IDS:
            raise ValueError(f"query_id must be one of {SUPPORTED_QUERY_IDS}")
        return query_id, _type_frequency_query_probabilities(selected=query_id)

    selection_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:query_id",
        )
    )
    probabilities = _type_frequency_query_probabilities()
    support = tuple(str(query_id) for query_id in SUPPORTED_QUERY_IDS if float(probabilities.get(str(query_id), 0.0)) > 0.0)
    if not support:
        raise ValueError("query_id_weights resolved no supported query ids")
    query_id = str(support[int(selection_index % len(support))])
    return query_id, probabilities


def _frequency_spec_for_query(query_id: str, *, instance_seed: int, params: Mapping[str, Any]):
    """Resolve a neutral frequency spec for the selected query."""

    if str(query_id) == SINGLETON_QUERY_ID:
        return resolve_singleton_frequency_spec(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            selection_namespace=f"{TASK_ID}:singleton_frequency_spec",
        )
    if str(query_id) == MOST_FREQUENT_QUERY_ID:
        return resolve_most_frequent_frequency_spec(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            selection_namespace=f"{TASK_ID}:most_frequent_frequency_spec",
        )
    raise ValueError(f"unsupported query_id: {query_id}")


def _bind_answer_annotation(scene_payload, frequency_spec, query_id: str) -> Tuple[int, Dict[str, Any]]:
    """Bind the integer answer and bbox-set annotation from the same scene trace."""

    if str(query_id) == SINGLETON_QUERY_ID:
        counted_icon_ids = tuple(str(icon_id) for icon_id in scene_payload.singleton_icon_ids)
        annotation_bboxes = bboxes_for_icon_ids(scene_payload, counted_icon_ids)
        annotation_indices = indices_for_icon_ids(scene_payload, counted_icon_ids)
        answer_value = int(scene_payload.singleton_count)
        if len(annotation_bboxes) != int(answer_value):
            raise ValueError("singleton annotation count did not match answer")
        binding = {
            "counting_rule": "singleton_icon_type_frequency",
            "question_format": "count_singleton_type_icons",
            "counted_icon_ids": list(counted_icon_ids),
            "annotation_indices": list(annotation_indices),
            "annotation_bboxes": list(annotation_bboxes),
            "target_count": int(answer_value),
            "singleton_count": int(scene_payload.singleton_count),
            "winner_icon_id": None,
            "winner_frequency": None,
        }
        return int(answer_value), binding

    if str(query_id) == MOST_FREQUENT_QUERY_ID:
        if not scene_payload.repeated_icon_ids:
            raise ValueError("most-frequent scene must contain a repeated icon type")
        max_frequency = max(int(value) for value in scene_payload.type_frequencies.values())
        winner_ids = [
            str(icon_id)
            for icon_id, frequency in sorted(scene_payload.type_frequencies.items())
            if int(frequency) == int(max_frequency)
        ]
        if len(winner_ids) != 1:
            raise ValueError("scene did not realize a unique most-frequent icon type")
        winner_icon_id = str(winner_ids[0])
        expected_frequency = int(frequency_spec.repeated_type_multiplicities[0])
        if int(max_frequency) != int(expected_frequency):
            raise ValueError("scene did not realize requested most-frequent count")
        annotation_bboxes = bboxes_for_icon_ids(scene_payload, (winner_icon_id,))
        annotation_indices = indices_for_icon_ids(scene_payload, (winner_icon_id,))
        if len(annotation_bboxes) != int(max_frequency):
            raise ValueError("most-frequent annotation count did not match answer")
        binding = {
            "counting_rule": "unique_most_frequent_icon_type",
            "question_format": "count_icons_of_unique_most_frequent_type",
            "counted_icon_ids": [str(winner_icon_id)],
            "annotation_indices": list(annotation_indices),
            "annotation_bboxes": list(annotation_bboxes),
            "target_count": int(max_frequency),
            "singleton_count": int(scene_payload.singleton_count),
            "winner_icon_id": str(winner_icon_id),
            "winner_frequency": int(max_frequency),
        }
        return int(max_frequency), binding

    raise ValueError(f"unsupported query_id: {query_id}")


@register_task
class IconsIconFieldTypeFrequencyCountTask:
    """Count icon instances satisfying a type-frequency predicate."""

    task_id = TASK_ID
    domain = DOMAIN
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic icon-field frequency-counting instance."""

        query_id, query_probabilities = _resolve_type_frequency_query(int(instance_seed), params)
        delegated_params = {
            **_type_frequency_generation_params(str(query_id)),
            **dict(params),
        }
        frequency_spec = _frequency_spec_for_query(
            str(query_id),
            instance_seed=int(instance_seed),
            params=delegated_params,
        )
        render_params = resolve_icon_field_render_params(
            delegated_params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        pool_manifest = str(
            delegated_params.get(
                "pool_manifest",
                group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest),
            )
        )
        scene_rng = spawn_rng(int(instance_seed), "scene")

        scene_payload = None
        image = None
        last_error: Exception | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                scene_payload, image = sample_and_render_icon_field_scene(
                    scene_rng,
                    instance_seed=int(instance_seed),
                    frequency_spec=frequency_spec,
                    pool_manifest=str(pool_manifest),
                    render_params=render_params,
                    noise_namespace=NOISE_NAMESPACE,
                )
                break
            except Exception as exc:  # pragma: no cover - exercised through retry loop
                last_error = exc
                continue
        if scene_payload is None or image is None:
            raise RuntimeError(f"failed to generate {TASK_ID} instance") from last_error

        answer_value, binding = _bind_answer_annotation(scene_payload, frequency_spec, str(query_id))
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            dynamic_slots={},
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        annotation_bboxes = list(binding["annotation_bboxes"])
        annotation_indices = list(binding["annotation_indices"])
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))

        scene_kind = (
            "icons_singleton_type_counting"
            if str(query_id) == SINGLETON_QUERY_ID
            else "icons_most_frequent_type_counting"
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": str(scene_kind),
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "entities": [dict(entity) for entity in scene_payload.scene_instances],
                "relations": {
                    "counting_rule": str(binding["counting_rule"]),
                    "counted_icon_ids": list(binding["counted_icon_ids"]),
                    "singleton_icon_ids": list(scene_payload.singleton_icon_ids),
                    "repeated_icon_ids": list(scene_payload.repeated_icon_ids),
                    "type_frequencies": dict(scene_payload.type_frequencies),
                    "singleton_indices": list(scene_payload.singleton_indices),
                    "repeated_indices": list(scene_payload.repeated_indices),
                    "winner_icon_id": binding["winner_icon_id"],
                    "winner_frequency": binding["winner_frequency"],
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene_payload.panel_geometry),
                },
            },
            "query_spec": {
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "task_id": str(self.task_id),
                    "scene_id": SCENE_ID,
                    "query_id": str(query_id),
                    "object_count": int(scene_payload.object_count),
                    "target_count": int(answer_value),
                    "singleton_count": int(scene_payload.singleton_count),
                    "repeated_icon_count": int(scene_payload.object_count) - int(scene_payload.singleton_count),
                    "repeated_type_count": int(scene_payload.repeated_type_count),
                    "repeated_type_multiplicities": list(scene_payload.repeated_type_multiplicities),
                    "distinct_type_count": int(scene_payload.distinct_type_count),
                    "object_count_probabilities": dict(frequency_spec.object_count_probabilities),
                    "target_count_probabilities": dict(frequency_spec.target_count_probabilities),
                    "query_id_probabilities": dict(query_probabilities),
                    "pool_manifest": str(pool_manifest),
                    "rotation_candidates_degrees": [
                        int(value) for value in render_params["rotation_candidates_degrees"]
                    ],
                    "winner_icon_id": binding["winner_icon_id"],
                    "winner_frequency": binding["winner_frequency"],
                },
            },
            "render_spec": {
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "canvas_size": list(scene_payload.panel_geometry["canvas_size"]),
                "coord_space": "pixel",
                "panel_geometry": dict(scene_payload.panel_geometry),
                "style": icon_field_style_trace(
                    render_params=render_params,
                    sampled_palette_rgb=scene_payload.sampled_palette_rgb,
                ),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {},
            },
            "execution_trace": {
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "scene_variant": "single_panel_scene",
                "query_id": str(query_id),
                "query_id_probabilities": dict(query_probabilities),
                "question_format": str(binding["question_format"]),
                "object_count": int(scene_payload.object_count),
                "target_count": int(answer_value),
                "singleton_count": int(scene_payload.singleton_count),
                "repeated_icon_count": int(scene_payload.object_count) - int(scene_payload.singleton_count),
                "repeated_type_count": int(scene_payload.repeated_type_count),
                "repeated_type_multiplicities": list(scene_payload.repeated_type_multiplicities),
                "distinct_type_count": int(scene_payload.distinct_type_count),
                "scene_icon_ids": list(scene_payload.scene_icon_ids),
                "scene_rotations_degrees": list(scene_payload.scene_rotations_degrees),
                "type_frequencies": dict(scene_payload.type_frequencies),
                "singleton_indices": list(scene_payload.singleton_indices),
                "repeated_indices": list(scene_payload.repeated_indices),
                "annotation_indices": list(annotation_indices),
                "winner_icon_id": binding["winner_icon_id"],
                "winner_frequency": binding["winner_frequency"],
            },
            "witness_symbolic": {
                "counted_icon_ids": list(binding["counted_icon_ids"]),
                "singleton_icon_ids": list(scene_payload.singleton_icon_ids),
                "repeated_icon_ids": list(scene_payload.repeated_icon_ids),
                "type_frequencies": dict(scene_payload.type_frequencies),
                "singleton_indices": list(scene_payload.singleton_indices),
                "repeated_indices": list(scene_payload.repeated_indices),
                "annotation_indices": list(annotation_indices),
                "winner_icon_id": binding["winner_icon_id"],
                "winner_frequency": binding["winner_frequency"],
            },
            "projected_annotation": {
                "bbox_set": list(annotation_bboxes),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["IconsIconFieldTypeFrequencyCountTask"]
