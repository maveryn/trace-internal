"""Counterfactual object-count after a hypothetical add/remove edit."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import create_task, register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_scene_prompt_variants


TASK_ID = "task_illustrations__source_scene_edit__object_count_after_edit"
SCENE_ID = "source_scene_edit"
ADDED_VARIANT = "after_added_k_objects_count"
REMOVED_VARIANT = "after_removed_k_objects_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (ADDED_VARIANT, REMOVED_VARIANT)
DEFAULT_SOURCE_QUERIES: Mapping[str, Mapping[str, Any]] = {
    "park_sitting": {
        "source_task_id": "task_illustrations__park_playground__activity_person_count",
        "source_params": {"query_id": "sitting_person_count"},
        "singular_phrase": "sitting person",
        "plural_phrase": "sitting people",
        "scene_id": "park_playground",
    },
    "park_walking": {
        "source_task_id": "task_illustrations__park_playground__activity_person_count",
        "source_params": {"query_id": "walking_person_count"},
        "singular_phrase": "walking person",
        "plural_phrase": "walking people",
        "scene_id": "park_playground",
    },
    "construction_tools": {
        "source_task_id": "task_illustrations__construction_site__worker_attribute_count",
        "source_params": {"query_id": "tool_holding_worker_count"},
        "singular_phrase": "tool-holding worker",
        "plural_phrase": "tool-holding workers",
        "scene_id": "construction_site",
    },
}
NUMBER_WORDS = {1: "one", 2: "two", 3: "three"}


@dataclass(frozen=True)
class _Defaults:
    edit_count_k_min: int = 1
    edit_count_k_max: int = 3
    current_count_min: int = 3
    current_count_max: int = 8


@dataclass(frozen=True)
class _SourceQuery:
    key: str
    source_task_id: str
    source_params: Dict[str, Any]
    singular_phrase: str
    plural_phrase: str
    scene_id: str


@dataclass(frozen=True)
class _SampleSpec:
    query_id: str
    source_query: _SourceQuery
    edit_count_k: int
    current_count: int
    result_count: int
    query_id_probabilities: Dict[str, float]
    source_query_probabilities: Dict[str, float]
    edit_count_probabilities: Dict[str, float]
    current_count_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_SCENE_DEFAULTS = get_scene_defaults("illustrations", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _uniform_string_probabilities(values: Sequence[str], *, selected: str | None = None) -> Dict[str, float]:
    support = tuple(str(value) for value in values)
    if selected is not None:
        return {str(selected): 1.0}
    probability = 1.0 / float(len(support))
    return {str(value): probability for value in support}


def _source_query_support(params: Mapping[str, Any]) -> Tuple[_SourceQuery, ...]:
    raw = params.get("source_query_support", group_default(_GEN_DEFAULTS, "source_query_support", tuple(DEFAULT_SOURCE_QUERIES)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("source_query_support must be a sequence")
    queries: list[_SourceQuery] = []
    for value in raw:
        key = str(value)
        if key not in DEFAULT_SOURCE_QUERIES:
            raise ValueError(f"unsupported source_query key {key!r}")
        spec = DEFAULT_SOURCE_QUERIES[key]
        queries.append(
            _SourceQuery(
                key=key,
                source_task_id=str(spec["source_task_id"]),
                source_params=dict(spec["source_params"]),
                singular_phrase=str(spec["singular_phrase"]),
                plural_phrase=str(spec["plural_phrase"]),
                scene_id=str(spec["scene_id"]),
            )
        )
    seen: set[str] = set()
    deduped = [query for query in queries if not (query.key in seen or seen.add(query.key))]
    if not deduped:
        raise ValueError("source_query_support resolved no source queries")
    return tuple(deduped)


def _int_support(params: Mapping[str, Any], low_key: str, high_key: str, fallback_low: int, fallback_high: int) -> Tuple[int, ...]:
    low = int(params.get(low_key, group_default(_GEN_DEFAULTS, low_key, fallback_low)))
    high = int(params.get(high_key, group_default(_GEN_DEFAULTS, high_key, fallback_high)))
    if low < 1 or high < low:
        raise ValueError(f"invalid {low_key}/{high_key}")
    return tuple(range(low, high + 1))


def _resolve_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    explicit = params.get("query_id")
    if explicit is not None:
        selected = str(explicit)
        if selected not in set(SUPPORTED_QUERY_IDS):
            raise ValueError(f"query_id must be one of {SUPPORTED_QUERY_IDS}")
        return selected, {selected: 1.0}
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:query_id")
    selected = str(SUPPORTED_QUERY_IDS[int(index) % len(SUPPORTED_QUERY_IDS)])
    return selected, {variant: 1.0 / float(len(SUPPORTED_QUERY_IDS)) for variant in SUPPORTED_QUERY_IDS}


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _SampleSpec:
    source_queries = _source_query_support(params)
    query_id, variant_probs = _resolve_variant(params, instance_seed=int(instance_seed))
    k_support = _int_support(params, "edit_count_k_min", "edit_count_k_max", _DEFAULTS.edit_count_k_min, _DEFAULTS.edit_count_k_max)

    explicit_k = params.get("edit_count_k")
    if explicit_k is not None:
        edit_count_k = int(explicit_k)
        if edit_count_k not in set(k_support):
            raise ValueError("edit_count_k is outside configured support")
        k_probs = uniform_probability_map(k_support, selected=edit_count_k)
    else:
        k_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:edit_count_k")
        edit_count_k = int(k_support[int(k_index) % len(k_support)])
        k_probs = uniform_probability_map(k_support)

    current_support_base = _int_support(params, "current_count_min", "current_count_max", _DEFAULTS.current_count_min, _DEFAULTS.current_count_max)
    if query_id == REMOVED_VARIANT:
        current_support = tuple(value for value in current_support_base if int(value) > int(edit_count_k))
    else:
        current_support = current_support_base
    if not current_support:
        raise ValueError("current_count support is empty for selected edit_count_k")
    explicit_current = params.get("current_count")
    if explicit_current is not None:
        current_count = int(explicit_current)
        if current_count not in set(current_support):
            raise ValueError("current_count is outside configured support")
        current_probs = uniform_probability_map(current_support, selected=current_count)
    else:
        current_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:current_count")
        current_count = int(current_support[int(current_index) % len(current_support)])
        current_probs = uniform_probability_map(current_support)

    explicit_source = params.get("source_query_key")
    if explicit_source is not None:
        source_key = str(explicit_source)
        matches = tuple(query for query in source_queries if query.key == source_key)
        if not matches:
            raise ValueError(f"source_query_key must be one of {[query.key for query in source_queries]}")
        source_query = matches[0]
        source_probs = {source_key: 1.0}
    else:
        source_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:source_query")
        source_query = source_queries[int(source_index) % len(source_queries)]
        source_probs = _uniform_string_probabilities(tuple(query.key for query in source_queries))

    result_count = int(current_count) + int(edit_count_k) if query_id == ADDED_VARIANT else int(current_count) - int(edit_count_k)
    return _SampleSpec(
        query_id=str(query_id),
        source_query=source_query,
        edit_count_k=int(edit_count_k),
        current_count=int(current_count),
        result_count=int(result_count),
        query_id_probabilities=dict(variant_probs),
        source_query_probabilities=dict(source_probs),
        edit_count_probabilities={str(key): float(value) for key, value in k_probs.items()},
        current_count_probabilities={str(key): float(value) for key, value in current_probs.items()},
    )


def _source_params_for(sample: _SampleSpec, params: Mapping[str, Any]) -> Dict[str, Any]:
    source_params: Dict[str, Any] = {
        **dict(sample.source_query.source_params),
        "target_count": int(sample.current_count),
        "target_count_min": 1,
        "target_count_max": max(10, int(sample.current_count)),
    }
    if sample.source_query.source_task_id == "task_illustrations__park_playground__activity_person_count":
        source_params["person_count"] = max(10, int(sample.current_count) + 4)
        source_params["person_count_min"] = max(10, int(sample.current_count) + 4)
        source_params["person_count_max"] = max(10, int(sample.current_count) + 4)
    elif sample.source_query.source_task_id == "task_illustrations__construction_site__worker_attribute_count":
        source_params["worker_count"] = max(10, int(sample.current_count) + 4)
        source_params["worker_count_min"] = max(10, int(sample.current_count) + 4)
        source_params["worker_count_max"] = max(10, int(sample.current_count) + 4)
    return source_params


def _render_source_scene(sample: _SampleSpec, *, instance_seed: int, params: Mapping[str, Any], max_attempts: int) -> Tuple[Image.Image, list[list[float]], Dict[str, Any]]:
    seed = int(spawn_rng(int(instance_seed), f"{TASK_ID}:source:{sample.source_query.key}:{sample.current_count}").randint(0, 2**63 - 1))
    out = create_task(sample.source_query.source_task_id).generate(
        seed,
        params=_source_params_for(sample, params),
        max_attempts=max(50, int(max_attempts)),
    )
    current_answer = int(out.answer_gt.value)
    if current_answer != int(sample.current_count):
        raise ValueError(f"source current count {current_answer} did not match requested {sample.current_count}")
    if str(out.annotation_gt.type) != "bbox_set":
        raise ValueError("source task annotation must be bbox_set")
    annotation_boxes = [[round(float(value), 3) for value in box] for box in out.annotation_gt.value]
    if len(annotation_boxes) != int(sample.current_count):
        raise ValueError("source annotation count did not match current_count")
    source_info = {
        "source_task_id": str(sample.source_query.source_task_id),
        "source_scene_id": str(out.scene_id),
        "source_query_id": str(out.query_id),
        "source_trace_ref": dict(out.trace_payload).get("trace_ref"),
    }
    return out.image.convert("RGB"), annotation_boxes, source_info


def _count_phrase(k: int, singular: str, plural: str, *, more: bool) -> str:
    count_word = NUMBER_WORDS.get(int(k), str(int(k)))
    if int(k) == 1:
        return f"{count_word} more {singular}" if more else f"{count_word} {singular}"
    return f"{count_word} more {plural}" if more else f"{count_word} {plural}"


def _example_json_for(sample: _SampleSpec, *, include_annotation: bool) -> str:
    example_current = max(3, int(sample.edit_count_k) + 2)
    if str(sample.query_id) == ADDED_VARIANT:
        example_answer = example_current + int(sample.edit_count_k)
    else:
        example_answer = example_current - int(sample.edit_count_k)
    payload: Dict[str, Any] = {"answer": int(example_answer)}
    if include_annotation:
        boxes = [
            [120 + 82 * index, 220, 176 + 82 * index, 292]
            for index in range(example_current)
        ]
        payload = {"annotation": boxes, "answer": int(example_answer)}
    return json.dumps(payload, separators=(",", ":"))




@register_task
class IllustrationsCounterfactualObjectCountAfterEditTask:
    """Count objects after a hypothetical add/remove edit."""

    task_id = TASK_ID
    domain = "illustrations"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        sample = _sample_spec(instance_seed=int(instance_seed), params=params)
        image, current_boxes, source_info = _render_source_scene(
            sample,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=max_attempts,
        )
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "annotation_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        slots = {
            "object_plural": str(sample.source_query.plural_phrase),
            "add_phrase": _count_phrase(sample.edit_count_k, sample.source_query.singular_phrase, sample.source_query.plural_phrase, more=True),
            "remove_phrase": _count_phrase(sample.edit_count_k, sample.source_query.singular_phrase, sample.source_query.plural_phrase, more=False),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(prompt_defaults["annotation_hint"]).format(object_plural=str(sample.source_query.plural_phrase)),
            "answer_hint": str(prompt_defaults["answer_hint"]),
            "json_example": _example_json_for(sample, include_annotation=True),
            "json_example_answer_only": _example_json_for(sample, include_annotation=False),
        }
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(sample.query_id),
            slots=slots,
            instance_seed=int(instance_seed),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            preferred_mode="answer_and_annotation",
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        edit_operation = "added" if sample.query_id == ADDED_VARIANT else "removed"
        trace_payload = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "entities": {
                    "source_scene_id": str(source_info["source_scene_id"]),
                    "source_query_key": str(sample.source_query.key),
                    "current_target_objects": [
                        {"entity_id": f"target_{index:02d}", "bbox": box, "object_phrase": str(sample.source_query.plural_phrase)}
                        for index, box in enumerate(current_boxes)
                    ],
                },
                "relations": {
                    "query_id": str(sample.query_id),
                    "edit_operation": str(edit_operation),
                    "edit_count_k": int(sample.edit_count_k),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_id": str(sample.query_id),
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "source_query_key": str(sample.source_query.key),
                    "source_task_id": str(sample.source_query.source_task_id),
                    "source_scene_id": str(sample.source_query.scene_id),
                    "object_singular": str(sample.source_query.singular_phrase),
                    "object_plural": str(sample.source_query.plural_phrase),
                    "edit_operation": str(edit_operation),
                    "edit_count_k": int(sample.edit_count_k),
                    "current_count": int(sample.current_count),
                    "result_count": int(sample.result_count),
                    "query_id_probabilities": dict(sample.query_id_probabilities),
                    "source_query_probabilities": dict(sample.source_query_probabilities),
                    "edit_count_probabilities": dict(sample.edit_count_probabilities),
                    "current_count_probabilities": dict(sample.current_count_probabilities),
                },
            },
            "render_spec": {
                "canvas_width": int(image.width),
                "canvas_height": int(image.height),
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "source_scene_id": str(source_info["source_scene_id"]),
            },
            "render_map": {
                "current_target_bboxes_px": list(current_boxes),
                "source_info": dict(source_info),
            },
            "execution_trace": {
                "query_id": str(sample.query_id),
                "answer": int(sample.result_count),
                "current_count": int(sample.current_count),
                "edit_operation": str(edit_operation),
                "edit_count_k": int(sample.edit_count_k),
                "result_count": int(sample.result_count),
                "counterfactual_edit_type": "object_count_after_hypothetical_edit",
                "is_counterfactual": True,
            },
            "witness_symbolic": {
                "answer": int(sample.result_count),
                "current_target_ids": [f"target_{index:02d}" for index in range(len(current_boxes))],
            },
            "projected_annotation": {"bbox_set": list(current_boxes)},
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="integer", value=int(sample.result_count)),
            annotation_gt=TypedValue(type="bbox_set", value=list(current_boxes)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sample.query_id),
        )


__all__ = [
    "ADDED_VARIANT",
    "REMOVED_VARIANT",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "IllustrationsCounterfactualObjectCountAfterEditTask",
]
