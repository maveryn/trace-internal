"""Count icons belonging to the most frequent icon type in a free icon field."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.complexity import build_icons_counting_singleton_type_complexity
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.icon_scene import sort_bboxes_reading_order
from ..shared.icon_task_rendering import icon_render_style_trace, resolve_icon_render_params
from ..shared.public_query_task import rewrite_icons_query_output
from .singleton_type import _CountSpec as _IconFieldCountSpec
from .singleton_type import IconsCountingSingletonTypeTask
from .singleton_type import _bounded_compositions, _sample_scene


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for most-frequent-type counting scenes."""

    object_count_min: int = 7
    object_count_max: int = 12
    target_count_min: int = 2
    target_count_max: int = 6
    other_repeated_type_count_max: int = 3
    canvas_width: int = ICON_SHARED_DEFAULTS.canvas_width
    canvas_height: int = ICON_SHARED_DEFAULTS.canvas_height
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    scene_icon_size_min_px: int = ICON_SHARED_DEFAULTS.scene_icon_size_min_px
    scene_icon_size_max_px: int = ICON_SHARED_DEFAULTS.scene_icon_size_max_px
    scene_max_overlap_fraction: float = ICON_SHARED_DEFAULTS.scene_max_overlap_fraction
    scene_placement_max_attempts: int = ICON_SHARED_DEFAULTS.scene_placement_max_attempts
    scene_size_shrink_rounds: int = ICON_SHARED_DEFAULTS.scene_size_shrink_rounds
    scene_size_shrink_factor: float = ICON_SHARED_DEFAULTS.scene_size_shrink_factor
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    pool_manifest: str = "all_icons.txt"
    palette_size_min: int = 8
    palette_size_max: int = 12
    color_channel_min: int = 24
    color_channel_max: int = 220
    min_color_distance: float = 40.0
    color_distance_space: str = "lab"
    background_color_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.background_color_rgb
    panel_fill_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_fill_rgb
    panel_border_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_border_rgb
    header_text_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.header_text_rgb


@dataclass(frozen=True)
class _FrequencySpec:
    """Resolved frequency structure for one most-frequent-type instance."""

    object_count: int
    winning_frequency: int
    singleton_count: int
    repeated_type_multiplicities: Tuple[int, ...]
    object_count_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]


TYPE_FREQUENCY_TASK_ID = "task_icons__icon_field__type_frequency_count"
TASK_ID = TYPE_FREQUENCY_TASK_ID
QUERY_ID = "most_frequent_type_count"
TYPE_FREQUENCY_QUERY_IDS: Tuple[str, ...] = ("singleton_type_count", "most_frequent_type_count")
_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _candidate_frequency_partitions(
    *,
    object_count: int,
    winning_frequency: int,
    other_repeated_type_count_max: int,
) -> List[Tuple[int, Tuple[int, ...]]]:
    """Return feasible `(singleton_count, multiplicities)` candidates.

    The first multiplicity is always the unique most-frequent type. All other
    repeated-type multiplicities are below it, so the answer is unique.
    """

    remaining = int(object_count) - int(winning_frequency)
    if remaining < 1:
        return []
    candidates: List[Tuple[int, Tuple[int, ...]]] = []
    max_other_groups = max(0, int(other_repeated_type_count_max))
    for singleton_count in range(1, int(remaining) + 1):
        repeated_remainder = int(remaining) - int(singleton_count)
        if repeated_remainder == 0:
            candidates.append((int(singleton_count), (int(winning_frequency),)))
            continue
        for other_group_count in range(1, int(max_other_groups) + 1):
            if int(repeated_remainder) < 2 * int(other_group_count):
                continue
            other_parts = _bounded_compositions(
                int(repeated_remainder),
                int(other_group_count),
                min_part=2,
                max_part=max(2, int(winning_frequency) - 1),
            )
            for parts in other_parts:
                if any(int(value) >= int(winning_frequency) for value in parts):
                    continue
                candidates.append(
                    (
                        int(singleton_count),
                        (int(winning_frequency), *tuple(int(value) for value in parts)),
                    )
                )
    return candidates


def _resolve_frequency_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _FrequencySpec:
    """Resolve a balanced unique-most-frequent type structure for one instance."""

    object_count_min = int(params.get("object_count_min", group_default(_GEN_DEFAULTS, "object_count_min", _DEFAULTS.object_count_min)))
    object_count_max = int(params.get("object_count_max", group_default(_GEN_DEFAULTS, "object_count_max", _DEFAULTS.object_count_max)))
    target_count_min = int(params.get("target_count_min", group_default(_GEN_DEFAULTS, "target_count_min", _DEFAULTS.target_count_min)))
    target_count_max = int(params.get("target_count_max", group_default(_GEN_DEFAULTS, "target_count_max", _DEFAULTS.target_count_max)))
    other_repeated_type_count_max = int(
        params.get(
            "other_repeated_type_count_max",
            group_default(
                _GEN_DEFAULTS,
                "other_repeated_type_count_max",
                _DEFAULTS.other_repeated_type_count_max,
            ),
        )
    )
    if object_count_min <= 1 or object_count_max < object_count_min:
        raise ValueError("object_count range is invalid for most-frequent-type counting")
    if target_count_min < 2 or target_count_max < target_count_min:
        raise ValueError("target_count range is invalid for most-frequent-type counting")
    if other_repeated_type_count_max < 0:
        raise ValueError("other_repeated_type_count_max must be non-negative")

    answer_support = tuple(range(int(target_count_min), int(target_count_max) + 1))
    selection_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:frequency_spec",
        )
    )
    explicit_target = params.get("target_count")
    explicit_object_count = params.get("object_count")

    if explicit_target is not None:
        winning_frequency = int(explicit_target)
    else:
        winning_frequency = int(answer_support[int(selection_index % len(answer_support))])
    if winning_frequency not in answer_support:
        raise ValueError("target_count is outside configured most-frequent support")

    object_support = tuple(
        value
        for value in range(max(int(object_count_min), int(winning_frequency) + 1), int(object_count_max) + 1)
        if _candidate_frequency_partitions(
            object_count=int(value),
            winning_frequency=int(winning_frequency),
            other_repeated_type_count_max=int(other_repeated_type_count_max),
        )
    )
    if not object_support:
        raise ValueError("no feasible object_count values exist for most-frequent-type counting")
    if explicit_object_count is not None:
        object_count = int(explicit_object_count)
    else:
        object_offset = int(selection_index // len(answer_support))
        object_count = int(object_support[int(object_offset % len(object_support))])
    if object_count not in object_support:
        raise ValueError("object_count is outside configured most-frequent support")

    candidates = _candidate_frequency_partitions(
        object_count=int(object_count),
        winning_frequency=int(winning_frequency),
        other_repeated_type_count_max=int(other_repeated_type_count_max),
    )
    if not candidates:
        raise ValueError("no feasible frequency partition exists")
    candidate_index = int(selection_index // max(1, len(answer_support) * len(object_support)))
    singleton_count, repeated_type_multiplicities = candidates[int(candidate_index % len(candidates))]

    return _FrequencySpec(
        object_count=int(object_count),
        winning_frequency=int(winning_frequency),
        singleton_count=int(singleton_count),
        repeated_type_multiplicities=tuple(int(value) for value in repeated_type_multiplicities),
        object_count_probabilities=dict(
            uniform_probability_map(
                object_support,
                selected=int(object_count) if explicit_object_count is not None else None,
            )
        ),
        target_count_probabilities=dict(
            uniform_probability_map(
                answer_support,
                selected=int(winning_frequency) if explicit_target is not None else None,
            )
        ),
    )


class IconsCountingMostFrequentTypeCountTask:
    """Count icons belonging to the unique most frequent icon type."""

    task_id = TASK_ID
    domain = "icons"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic most-frequent-type counting instance."""

        frequency_spec = _resolve_frequency_spec(instance_seed=int(instance_seed), params=params)
        render_params = resolve_icon_render_params(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        pool_manifest = str(
            params.get("pool_manifest", group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest))
        )
        scene_rng = spawn_rng(int(instance_seed), "scene")
        count_spec = _IconFieldCountSpec(
            object_count=int(frequency_spec.object_count),
            target_count=int(frequency_spec.singleton_count),
            repeated_type_count=int(len(frequency_spec.repeated_type_multiplicities)),
            repeated_type_multiplicities=tuple(int(value) for value in frequency_spec.repeated_type_multiplicities),
            distinct_type_count=int(frequency_spec.singleton_count) + int(len(frequency_spec.repeated_type_multiplicities)),
            object_count_probabilities=dict(frequency_spec.object_count_probabilities),
            target_count_probabilities=dict(frequency_spec.target_count_probabilities),
        )

        scene_payload = None
        image = None
        last_error: Exception | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                scene_payload, image = _sample_scene(
                    scene_rng,
                    instance_seed=int(instance_seed),
                    count_spec=count_spec,
                    pool_manifest=str(pool_manifest),
                    render_params=render_params,
                )
                break
            except Exception as exc:  # pragma: no cover - exercised through retry loop
                last_error = exc
                continue
        if scene_payload is None or image is None:
            raise RuntimeError(f"failed to generate {TASK_ID} most-frequent-type instance") from last_error

        winner_icon_id = str(scene_payload.repeated_icon_ids[0])
        winner_indices = [
            int(index)
            for index, icon_id in enumerate(scene_payload.scene_icon_ids)
            if str(icon_id) == str(winner_icon_id)
        ]
        winner_bboxes = [
            tuple(int(value) for value in entity["bbox_xyxy"])
            for entity in scene_payload.scene_instances
            if str(entity.get("icon_id")) == str(winner_icon_id)
        ]
        if len(winner_bboxes) != int(frequency_spec.winning_frequency):
            raise ValueError("most-frequent evidence did not match the requested winning frequency")
        max_frequency = max(int(value) for value in scene_payload.type_frequencies.values())
        if int(max_frequency) != int(frequency_spec.winning_frequency):
            raise ValueError("scene did not realize requested most-frequent count")
        if sum(1 for value in scene_payload.type_frequencies.values() if int(value) == int(max_frequency)) != 1:
            raise ValueError("scene did not realize a unique most-frequent icon type")

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        question_text = _PROMPT_DEFAULTS.get("question_text")
        question_text_by_variant = _PROMPT_DEFAULTS.get("question_text_by_variant")
        if isinstance(question_text_by_variant, Mapping):
            question_text = question_text_by_variant.get(str(QUERY_ID), question_text)
        evidence_hint = _PROMPT_DEFAULTS.get("evidence_hint")
        evidence_hint_by_variant = _PROMPT_DEFAULTS.get("evidence_hint_by_variant")
        if isinstance(evidence_hint_by_variant, Mapping):
            evidence_hint = evidence_hint_by_variant.get(str(QUERY_ID), evidence_hint)
        if not isinstance(question_text, str) or not question_text.strip():
            raise ValueError(f"missing prompt question text for {self.task_id}:{QUERY_ID}")
        if not isinstance(evidence_hint, str) or not evidence_hint.strip():
            raise ValueError(f"missing prompt evidence hint for {self.task_id}:{QUERY_ID}")
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(question_text),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(evidence_hint),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_bboxes = sort_bboxes_reading_order(tuple(winner_bboxes))
        answer_value = int(frequency_spec.winning_frequency)
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_most_frequent_type_counting",
                "entities": [dict(entity) for entity in scene_payload.scene_instances],
                "relations": {
                    "counting_rule": "unique_most_frequent_icon_type",
                    "winner_icon_id": str(winner_icon_id),
                    "winner_frequency": int(answer_value),
                    "winner_indices": list(winner_indices),
                    "type_frequencies": dict(scene_payload.type_frequencies),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene_payload.panel_geometry),
                },
            },
            "query_spec": {
                "query_id": str(QUERY_ID),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "object_count": int(scene_payload.object_count),
                    "target_count": int(answer_value),
                    "winner_icon_id": str(winner_icon_id),
                    "winner_frequency": int(answer_value),
                    "singleton_count": int(frequency_spec.singleton_count),
                    "repeated_type_count": int(len(frequency_spec.repeated_type_multiplicities)),
                    "repeated_type_multiplicities": list(frequency_spec.repeated_type_multiplicities),
                    "distinct_type_count": int(scene_payload.distinct_type_count),
                    "object_count_probabilities": dict(frequency_spec.object_count_probabilities),
                    "target_count_probabilities": dict(frequency_spec.target_count_probabilities),
                    "query_id_probabilities": {str(QUERY_ID): 1.0},
                    "pool_manifest": str(pool_manifest),
                },
            },
            "render_spec": {
                "canvas_size": list(scene_payload.panel_geometry["canvas_size"]),
                "coord_space": "pixel",
                "panel_geometry": dict(scene_payload.panel_geometry),
                "style": icon_render_style_trace(
                    render_params=render_params,
                    sampled_palette_rgb=scene_payload.sampled_palette_rgb,
                ),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {},
            },
            "execution_trace": {
                "scene_variant": "single_panel_scene",
                "query_id": str(QUERY_ID),
                "question_format": "count_icons_of_unique_most_frequent_type",
                "object_count": int(scene_payload.object_count),
                "target_count": int(answer_value),
                "winner_icon_id": str(winner_icon_id),
                "winner_frequency": int(answer_value),
                "winner_indices": list(winner_indices),
                "singleton_count": int(frequency_spec.singleton_count),
                "repeated_type_count": int(len(frequency_spec.repeated_type_multiplicities)),
                "repeated_type_multiplicities": list(frequency_spec.repeated_type_multiplicities),
                "distinct_type_count": int(scene_payload.distinct_type_count),
                "scene_icon_ids": list(scene_payload.scene_icon_ids),
                "scene_rotations_degrees": list(scene_payload.scene_rotations_degrees),
                "type_frequencies": dict(scene_payload.type_frequencies),
                "evidence_indices": list(winner_indices),
            },
            "witness_symbolic": {
                "winner_icon_id": str(winner_icon_id),
                "winner_frequency": int(answer_value),
                "winner_indices": list(winner_indices),
                "type_frequencies": dict(scene_payload.type_frequencies),
                "evidence_indices": list(winner_indices),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
            },
        }
        complexity = build_icons_counting_singleton_type_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            object_count=int(scene_payload.object_count),
            target_count=int(answer_value),
            repeated_type_count=int(len(frequency_spec.repeated_type_multiplicities)),
            distinct_type_count=int(scene_payload.distinct_type_count),
            object_count_min=int(
                params.get("object_count_min", group_default(_GEN_DEFAULTS, "object_count_min", _DEFAULTS.object_count_min))
            ),
            object_count_max=int(
                params.get("object_count_max", group_default(_GEN_DEFAULTS, "object_count_max", _DEFAULTS.object_count_max))
            ),
            scene_instances=scene_payload.scene_instances,
            render_params=render_params,
        )
        output = TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(QUERY_ID),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
        return rewrite_icons_query_output(
            output,
            query_id=str(QUERY_ID),
            scene_id="icon_field",
            query_probabilities={str(QUERY_ID): 1.0},
        )


def _type_frequency_query_probabilities(*, selected: str | None = None) -> Dict[str, float]:
    """Return the public query distribution for icon-field frequency counting."""

    if selected is not None:
        return {str(selected): 1.0}
    probability = 1.0 / float(len(TYPE_FREQUENCY_QUERY_IDS))
    return {str(query_id): float(probability) for query_id in TYPE_FREQUENCY_QUERY_IDS}


def _type_frequency_generation_params(query_id: str) -> Dict[str, Any]:
    """Return query-local generation defaults for the merged icon-field task."""

    raw = _GEN_DEFAULTS.get("variant_generation_params", {})
    if not isinstance(raw, Mapping):
        return {}
    selected = raw.get(str(query_id), {})
    if not isinstance(selected, Mapping):
        return {}
    return dict(selected)


def _resolve_type_frequency_query(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    """Resolve the internal frequency predicate for the merged public task."""

    explicit_query = params.get("query_id")
    if explicit_query is not None:
        query_id = str(explicit_query)
        if query_id not in TYPE_FREQUENCY_QUERY_IDS:
            raise ValueError(f"query_id must be one of {TYPE_FREQUENCY_QUERY_IDS}")
        return query_id, _type_frequency_query_probabilities(selected=query_id)
    selection_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TYPE_FREQUENCY_TASK_ID}:query_id",
        )
    )
    query_id = str(TYPE_FREQUENCY_QUERY_IDS[int(selection_index % len(TYPE_FREQUENCY_QUERY_IDS))])
    return query_id, _type_frequency_query_probabilities()


@register_task
class IconsIconFieldTypeFrequencyCountTask:
    """Count icon instances satisfying a type-frequency predicate."""

    task_id = TYPE_FREQUENCY_TASK_ID
    domain = "icons"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_probabilities = _resolve_type_frequency_query(int(instance_seed), params)
        delegated_params = {**_type_frequency_generation_params(str(query_id)), **dict(params)}
        if str(query_id) == "singleton_type_count":
            delegated_params["query_id"] = "singleton_type_count"
            output = IconsCountingSingletonTypeTask().generate(
                int(instance_seed),
                params=delegated_params,
                max_attempts=int(max_attempts),
            )
        elif str(query_id) == "most_frequent_type_count":
            output = IconsCountingMostFrequentTypeCountTask().generate(
                int(instance_seed),
                params=delegated_params,
                max_attempts=int(max_attempts),
            )
        else:  # pragma: no cover - guarded by _resolve_type_frequency_query.
            raise ValueError(f"unsupported query_id: {query_id}")
        return rewrite_icons_query_output(
            output,
            query_id=str(query_id),
            scene_id="icon_field",
            task_id=self.task_id,
            query_probabilities=query_probabilities,
        )


__all__ = [
    "IconsCountingMostFrequentTypeCountTask",
    "IconsIconFieldTypeFrequencyCountTask",
    "TYPE_FREQUENCY_QUERY_IDS",
]
