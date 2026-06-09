"""Merged library book counting task with section, color, and orientation variants."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.task_support import query_support as _shared_query_support
from ..shared.library_scene import (
    LibraryBookSpec,
    book_bbox_map,
    library_scene_entities,
    library_section_display_name,
    render_library_scene,
    serialize_library_scene,
    sort_library_bboxes,
)
from ..shared.library_task_common import (
    bounds,
    color_label,
    color_support,
    make_library_section_specs,
    random_book_specs,
    render_params,
    sample_count,
    section_keys_for_scene,
    section_support,
    setting_weights,
    spawned_task_rng,
    style_weights,
    uniform_string_probability_map,
)


TASK_ID = "private_library_book_count"
SCENE_ID = "library"
QUERY_IDS: Tuple[str, ...] = (
    "books_in_section_count",
    "book_color_in_section_count",
    "upright_book_in_section_count",
    "horizontal_book_in_section_count",
)
BOOKS_IN_SECTION_TASK_ID = "task_illustrations__library__books_in_section_count"
FILTERED_BOOK_TASK_ID = "task_illustrations__library__filtered_book_in_section_count"
FILTERED_QUERY_IDS: Tuple[str, ...] = (
    "book_color_in_section_count",
    "upright_book_in_section_count",
    "horizontal_book_in_section_count",
)
_ORIENTATION_BY_QUERY: Dict[str, str] = {
    "upright_book_in_section_count": "upright",
    "horizontal_book_in_section_count": "horizontal",
}


@dataclass(frozen=True)
class _Defaults:
    section_count_min: int = 4
    section_count_max: int = 6
    section_total_target_count_min: int = 3
    section_total_target_count_max: int = 8
    filtered_target_count_min: int = 1
    filtered_target_count_max: int = 6
    section_total_book_count_min: int = 5
    section_total_book_count_max: int = 12
    filtered_section_book_count_min: int = 7
    filtered_section_book_count_max: int = 14
    canvas_width: int = 1280
    canvas_height: int = 900
    render_scale: int = 2


@dataclass(frozen=True)
class _SampleSpec:
    query_id: str
    section_key: str
    section_name: str
    section_count: int
    target_count: int
    section_specs: Tuple[Any, ...]
    section_keys: Tuple[str, ...]
    query_probabilities: Dict[str, float]
    section_key_probabilities: Dict[str, float]
    section_count_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    color_name: str | None = None
    color_label: str | None = None
    color_probabilities: Dict[str, float] | None = None
    orientation: str | None = None
    orientation_name: str | None = None


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)




def _choose_query(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[str, Dict[str, float], int]:
    query_values = _shared_query_support(params, _GEN_DEFAULTS, QUERY_IDS)
    base_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:cycle")
    explicit_query = params.get("query_id")
    if explicit_query is not None:
        query_id = str(explicit_query)
        if query_id not in set(query_values):
            raise ValueError("query_id is outside configured support")
        return query_id, uniform_string_probability_map(query_values, selected=query_id), int(base_index)
    query_id = str(query_values[int(base_index) % len(query_values)])
    return query_id, uniform_string_probability_map(query_values), int(base_index // max(1, len(query_values)))


def _target_bounds(params: Mapping[str, Any], query_id: str) -> Tuple[int, int]:
    if str(query_id) == "books_in_section_count":
        return bounds(
            params,
            _GEN_DEFAULTS,
            "section_total_target_count_min",
            "section_total_target_count_max",
            _DEFAULTS.section_total_target_count_min,
            _DEFAULTS.section_total_target_count_max,
        )
    if "target_count_min" in params or "target_count_max" in params:
        return bounds(
            params,
            _GEN_DEFAULTS,
            "target_count_min",
            "target_count_max",
            _DEFAULTS.filtered_target_count_min,
            _DEFAULTS.filtered_target_count_max,
        )
    return bounds(
        params,
        _GEN_DEFAULTS,
        "filtered_target_count_min",
        "filtered_target_count_max",
        _DEFAULTS.filtered_target_count_min,
        _DEFAULTS.filtered_target_count_max,
    )


def _section_book_bounds(params: Mapping[str, Any], query_id: str) -> Tuple[int, int]:
    if str(query_id) == "books_in_section_count":
        return bounds(
            params,
            _GEN_DEFAULTS,
            "section_total_book_count_min",
            "section_total_book_count_max",
            _DEFAULTS.section_total_book_count_min,
            _DEFAULTS.section_total_book_count_max,
        )
    return bounds(
        params,
        _GEN_DEFAULTS,
        "filtered_section_book_count_min",
        "filtered_section_book_count_max",
        _DEFAULTS.filtered_section_book_count_min,
        _DEFAULTS.filtered_section_book_count_max,
    )


def _sample_section(
    *,
    rng,
    params: Mapping[str, Any],
    branch_index: int,
    target_count_support_len: int,
) -> Tuple[str, Dict[str, float], int, Dict[str, float], Tuple[str, ...]]:
    section_values = section_support(params, _GEN_DEFAULTS)
    section_min, section_max = bounds(
        params,
        _GEN_DEFAULTS,
        "section_count_min",
        "section_count_max",
        _DEFAULTS.section_count_min,
        _DEFAULTS.section_count_max,
    )
    section_count, section_count_probabilities = sample_count(
        params=params,
        instance_seed=0,
        namespace=f"{TASK_ID}:section_count",
        low=int(section_min),
        high=min(int(section_max), len(section_values)),
        explicit_key="section_count",
        cycle_index=int(branch_index // max(1, int(target_count_support_len))),
    )
    explicit_section = params.get("section_key")
    if explicit_section is not None:
        section_key = str(explicit_section)
        if section_key not in set(section_values):
            raise ValueError("section_key is outside configured support")
        section_probabilities = uniform_string_probability_map(section_values, selected=section_key)
    else:
        section_support_span = max(1, int(target_count_support_len) * max(1, int(section_max - section_min + 1)))
        section_key = str(section_values[int(branch_index // section_support_span) % len(section_values)])
        section_probabilities = uniform_string_probability_map(section_values)
    section_keys = section_keys_for_scene(
        rng=rng,
        params=params,
        defaults=_GEN_DEFAULTS,
        target_section_key=str(section_key),
        section_count=int(section_count),
    )
    return (
        str(section_key),
        dict(section_probabilities),
        int(section_count),
        dict(section_count_probabilities),
        tuple(section_keys),
    )


def _sample_color(
    *,
    params: Mapping[str, Any],
    branch_index: int,
    target_count_support_len: int,
    section_count_support_len: int,
) -> Tuple[str, str, Dict[str, float]]:
    colors = color_support(params, _GEN_DEFAULTS)
    explicit_color = params.get("color_name")
    if explicit_color is not None:
        color_name = str(explicit_color).strip().lower()
        if color_name not in set(colors):
            raise ValueError("color_name is outside configured support")
        return color_name, color_label(color_name), uniform_string_probability_map(colors, selected=color_name)
    color_cycle = max(1, int(target_count_support_len) * int(section_count_support_len))
    color_name = str(colors[int(branch_index // color_cycle) % len(colors)])
    return color_name, color_label(color_name), uniform_string_probability_map(colors)


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int) -> _SampleSpec:
    rng = spawned_task_rng(int(instance_seed), TASK_ID, int(attempt_index))
    query_id, query_probabilities, branch_index = _choose_query(params=params, instance_seed=int(instance_seed))
    target_min, target_max = _target_bounds(params, query_id)
    target_count, target_probabilities = sample_count(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:target_count:{query_id}",
        low=int(target_min),
        high=int(target_max),
        explicit_key="target_count",
        cycle_index=int(branch_index),
    )
    section_count_min, section_count_max = bounds(
        params,
        _GEN_DEFAULTS,
        "section_count_min",
        "section_count_max",
        _DEFAULTS.section_count_min,
        _DEFAULTS.section_count_max,
    )
    target_support_len = int(target_max - target_min + 1)
    section_count_support_len = int(min(int(section_count_max), len(section_support(params, _GEN_DEFAULTS))) - int(section_count_min) + 1)
    section_key, section_probabilities, section_count, section_count_probabilities, section_keys = _sample_section(
        rng=rng,
        params=params,
        branch_index=int(branch_index),
        target_count_support_len=int(target_support_len),
    )
    colors = color_support(params, _GEN_DEFAULTS)
    section_book_min, section_book_max = _section_book_bounds(params, query_id)

    color_name: str | None = None
    color_label_text: str | None = None
    color_probabilities: Dict[str, float] | None = None
    orientation: str | None = None
    orientation_name: str | None = None
    specs_by_section: Dict[str, Tuple[LibraryBookSpec, ...]] = {}

    if str(query_id) == "books_in_section_count":
        for key in section_keys:
            if str(key) == str(section_key):
                specs_by_section[str(key)] = random_book_specs(
                    rng=rng,
                    section_key=str(key),
                    count=int(target_count),
                    colors=colors,
                    role="target",
                )
            else:
                count = int(rng.randint(int(section_book_min), int(section_book_max)))
                specs_by_section[str(key)] = random_book_specs(
                    rng=rng,
                    section_key=str(key),
                    count=int(count),
                    colors=colors,
                    role="distractor",
                )
    elif str(query_id) == "book_color_in_section_count":
        color_name, color_label_text, color_probabilities = _sample_color(
            params=params,
            branch_index=int(branch_index),
            target_count_support_len=int(target_support_len),
            section_count_support_len=int(section_count_support_len),
        )
        non_target_colors = tuple(value for value in colors if str(value) != str(color_name))
        if not non_target_colors:
            raise ValueError("library book color query needs at least one non-target color")
        target_section_total_min = max(int(section_book_min), int(target_count) + 3)
        if target_section_total_min > int(section_book_max):
            raise ValueError("section_book_count range leaves no color distractor room")
        target_section_total = int(rng.randint(int(target_section_total_min), int(section_book_max)))
        target_specs = [
            LibraryBookSpec(str(section_key), str(color_name), str(rng.choice(("upright", "horizontal"))), "target")
            for _ in range(int(target_count))
        ]
        target_specs.extend(
            LibraryBookSpec(str(section_key), str(rng.choice(non_target_colors)), str(rng.choice(("upright", "horizontal"))), "distractor")
            for _ in range(int(target_section_total) - int(target_count))
        )
        rng.shuffle(target_specs)
        for key in section_keys:
            if str(key) == str(section_key):
                specs_by_section[str(key)] = tuple(target_specs)
            else:
                count = int(rng.randint(int(section_book_min), int(section_book_max)))
                specs_by_section[str(key)] = random_book_specs(
                    rng=rng,
                    section_key=str(key),
                    count=int(count),
                    colors=colors,
                    role="distractor",
                )
    else:
        orientation = str(_ORIENTATION_BY_QUERY[str(query_id)])
        orientation_name = "upright" if orientation == "upright" else "horizontal"
        other_orientation = "horizontal" if orientation == "upright" else "upright"
        target_section_total_min = max(int(section_book_min), int(target_count) + 3)
        if target_section_total_min > int(section_book_max):
            raise ValueError("section_book_count range leaves no orientation distractor room")
        target_section_total = int(rng.randint(int(target_section_total_min), int(section_book_max)))
        target_specs = [
            LibraryBookSpec(str(section_key), str(rng.choice(colors)), orientation, "target")
            for _ in range(int(target_count))
        ]
        target_specs.extend(
            LibraryBookSpec(str(section_key), str(rng.choice(colors)), other_orientation, "distractor")
            for _ in range(int(target_section_total) - int(target_count))
        )
        rng.shuffle(target_specs)
        for key in section_keys:
            if str(key) == str(section_key):
                specs_by_section[str(key)] = tuple(target_specs)
            else:
                count = int(rng.randint(int(section_book_min), int(section_book_max)))
                specs_by_section[str(key)] = random_book_specs(
                    rng=rng,
                    section_key=str(key),
                    count=int(count),
                    colors=colors,
                    role="distractor",
                )

    return _SampleSpec(
        query_id=str(query_id),
        section_key=str(section_key),
        section_name=library_section_display_name(str(section_key)),
        section_count=int(section_count),
        target_count=int(target_count),
        section_specs=make_library_section_specs(section_keys=section_keys, specs_by_section=specs_by_section),
        section_keys=tuple(section_keys),
        query_probabilities=dict(query_probabilities),
        section_key_probabilities=dict(section_probabilities),
        section_count_probabilities=dict(section_count_probabilities),
        target_count_probabilities=dict(target_probabilities),
        color_name=color_name,
        color_label=color_label_text,
        color_probabilities=dict(color_probabilities) if color_probabilities is not None else None,
        orientation=orientation,
        orientation_name=orientation_name,
    )


def _build_complexity(sample: _SampleSpec) -> TaskComplexity:
    visual_scan = (int(sample.section_count) - _DEFAULTS.section_count_min) / max(1, _DEFAULTS.section_count_max - _DEFAULTS.section_count_min)
    if sample.query_id == "books_in_section_count":
        answer_load = (int(sample.target_count) - _DEFAULTS.section_total_target_count_min) / max(
            1,
            _DEFAULTS.section_total_target_count_max - _DEFAULTS.section_total_target_count_min,
        )
        filter_load = 0.55
    else:
        answer_load = (int(sample.target_count) - _DEFAULTS.filtered_target_count_min) / max(
            1,
            _DEFAULTS.filtered_target_count_max - _DEFAULTS.filtered_target_count_min,
        )
        filter_load = 0.85 if sample.query_id == "book_color_in_section_count" else 0.76
    score = 0.36 * max(0.0, min(1.0, visual_scan)) + 0.34 * max(0.0, min(1.0, answer_load)) + 0.30 * float(filter_load)
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "visual_scan": round(float(visual_scan), 6),
            "answer_load": round(float(answer_load), 6),
            "filter_load": round(float(filter_load), 6),
        },
    )


def _prompt_keys_and_slots(sample: _SampleSpec, prompt_defaults: Mapping[str, Any]) -> Dict[str, str | int]:
    if sample.query_id == "books_in_section_count":
        answer_hint = str(prompt_defaults["answer_hint_books_in_section"]).format(section_name=str(sample.section_name))
        annotation_hint = str(prompt_defaults["annotation_hint_books_in_section"]).format(section_name=str(sample.section_name))
        json_example = str(prompt_defaults["json_example_books_in_section"])
        json_example_answer_only = str(prompt_defaults["json_example_answer_only_books_in_section"])
    elif sample.query_id == "book_color_in_section_count":
        answer_hint = str(prompt_defaults["answer_hint_book_color"]).format(
            color_label=str(sample.color_label),
            section_name=str(sample.section_name),
        )
        annotation_hint = str(prompt_defaults["annotation_hint_book_color"]).format(
            color_label=str(sample.color_label),
            section_name=str(sample.section_name),
        )
        json_example = str(prompt_defaults["json_example_book_color"])
        json_example_answer_only = str(prompt_defaults["json_example_answer_only_book_color"])
    else:
        answer_hint = str(prompt_defaults["answer_hint_book_orientation"]).format(
            orientation_name=str(sample.orientation_name),
            section_name=str(sample.section_name),
        )
        annotation_hint = str(prompt_defaults["annotation_hint_book_orientation"]).format(
            orientation_name=str(sample.orientation_name),
            section_name=str(sample.section_name),
        )
        json_example = str(prompt_defaults["json_example_book_orientation"])
        json_example_answer_only = str(prompt_defaults["json_example_answer_only_book_orientation"])
    return {
        "section_count": int(sample.section_count),
        "section_name": str(sample.section_name),
        "color_label": str(sample.color_label or ""),
        "orientation_name": str(sample.orientation_name or ""),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(answer_hint),
        "annotation_hint": str(annotation_hint),
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
    }


class _LibraryBookCountImpl:
    """Count library books by section, color, or orientation."""

    task_id = TASK_ID
    domain = "illustrations"
    task_group = "counting"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        sample: _SampleSpec | None = None
        scene = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                sample = _sample_spec(instance_seed=int(instance_seed), params=params, attempt_index=int(attempt))
                scene_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:scene", int(attempt))
                rp = render_params(
                    params,
                    _RENDER_DEFAULTS,
                    fallback_width=_DEFAULTS.canvas_width,
                    fallback_height=_DEFAULTS.canvas_height,
                    fallback_scale=_DEFAULTS.render_scale,
                )
                scene = render_library_scene(
                    rng=scene_rng,
                    section_specs=sample.section_specs,
                    canvas_width=int(rp["canvas_width"]),
                    canvas_height=int(rp["canvas_height"]),
                    render_scale=int(rp["render_scale"]),
                    setting_weights=setting_weights(params, _RENDER_DEFAULTS),
                    style_weights=style_weights(params, _RENDER_DEFAULTS),
                    instance_seed=int(instance_seed),
                    font_params=params,
                )
                break
            except Exception as exc:  # pragma: no cover
                last_error = exc
                sample = None
                scene = None
        if scene is None or sample is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        serialized_scene, book_bboxes, section_bboxes = serialize_library_scene(scene)
        if sample.query_id == "books_in_section_count":
            counted_book_ids = tuple(str(book.book_id) for book in scene.books if str(book.section_key) == str(sample.section_key))
        elif sample.query_id == "book_color_in_section_count":
            counted_book_ids = tuple(
                str(book.book_id)
                for book in scene.books
                if str(book.section_key) == str(sample.section_key) and str(book.color_name) == str(sample.color_name)
            )
        else:
            counted_book_ids = tuple(
                str(book.book_id)
                for book in scene.books
                if str(book.section_key) == str(sample.section_key) and str(book.orientation) == str(sample.orientation)
            )
        if len(counted_book_ids) != int(sample.target_count):
            raise RuntimeError("rendered library book count did not match sample target")
        annotation_value = sort_library_bboxes(book_bbox_map(scene), counted_book_ids)

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_books_in_section",
                "annotation_hint_books_in_section",
                "json_example_books_in_section",
                "json_example_answer_only_books_in_section",
                "answer_hint_book_color",
                "annotation_hint_book_color",
                "json_example_book_color",
                "json_example_answer_only_book_color",
                "answer_hint_book_orientation",
                "annotation_hint_book_orientation",
                "json_example_book_orientation",
                "json_example_answer_only_book_orientation",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        slots = _prompt_keys_and_slots(sample, prompt_defaults)
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
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
        trace_payload = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "entities": library_scene_entities(scene),
                "relations": {
                    "query_id": str(sample.query_id),
                    "target_section_key": str(sample.section_key),
                    "target_color_name": sample.color_name,
                    "target_orientation": sample.orientation,
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_id": str(sample.query_id),
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "section_key": str(sample.section_key),
                    "section_name": str(sample.section_name),
                    "color_name": sample.color_name,
                    "color_label": sample.color_label,
                    "orientation": sample.orientation,
                    "orientation_name": sample.orientation_name,
                    "section_count": int(sample.section_count),
                    "target_count": int(sample.target_count),
                    "section_keys": list(sample.section_keys),
                    "query_probabilities": dict(sample.query_probabilities),
                    "section_key_probabilities": dict(sample.section_key_probabilities),
                    "color_probabilities": dict(sample.color_probabilities or {}),
                    "section_count_probabilities": dict(sample.section_count_probabilities),
                    "target_count_probabilities": dict(sample.target_count_probabilities),
                },
            },
            "render_spec": {
                "canvas_size": [int(scene.canvas_width), int(scene.canvas_height)],
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "style": {
                    "setting_id": str(scene.setting_id),
                    "style_id": str(scene.style_id),
                    "render_scale": int(scene.render_scale),
                    "layout": dict(scene.layout),
                },
            },
            "render_map": {
                "book_bboxes_px": book_bboxes,
                "section_bboxes_px": section_bboxes,
                "counted_book_ids": list(counted_book_ids),
            },
            "execution_trace": {
                "query_id": str(sample.query_id),
                "scene_id": SCENE_ID,
                "target_section_key": str(sample.section_key),
                "target_section_name": str(sample.section_name),
                "target_color_name": sample.color_name,
                "target_color_label": sample.color_label,
                "target_orientation": sample.orientation,
                "target_count": int(sample.target_count),
                "section_count": int(sample.section_count),
                "counted_book_ids": list(counted_book_ids),
                "sections": serialized_scene[0]["sections"],
                "books": serialized_scene[0]["books"],
                "decor": serialized_scene[0]["decor"],
            },
            "witness_symbolic": {
                "counted_book_ids": list(counted_book_ids),
                "target_section_key": str(sample.section_key),
                "target_color_name": sample.color_name,
                "target_orientation": sample.orientation,
                "answer": int(sample.target_count),
            },
            "projected_annotation": {"bbox_set": list(annotation_value)},
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="integer", value=int(sample.target_count)),
            annotation_gt=TypedValue(type="bbox_set", value=list(annotation_value)),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(sample),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sample.query_id),
        )


def _generate_public_library_count(
    *,
    public_task_id: str,
    query_ids: Tuple[str, ...],
    branch_id: str,
    instance_seed: int,
    params: Dict[str, Any],
    max_attempts: int,
) -> TaskOutput:
    requested_query = params.get("query_id")
    if requested_query is not None and str(requested_query) not in set(query_ids):
        raise ValueError(f"query_id must be one of {query_ids} for {public_task_id}")
    branch_params = dict(params)
    branch_params["query_id_support"] = list(query_ids)
    output = _LibraryBookCountImpl().generate(
        int(instance_seed),
        params=branch_params,
        max_attempts=int(max_attempts),
    )
    trace_payload = output.trace_payload
    query_spec = trace_payload.setdefault("query_spec", {})
    if isinstance(query_spec, dict):
        query_spec["task_id"] = str(public_task_id)
        query_spec["branch_id"] = str(branch_id)
    scene_ir = trace_payload.setdefault("scene_ir", {})
    if isinstance(scene_ir, dict):
        relations = scene_ir.setdefault("relations", {})
        if isinstance(relations, dict):
            relations["branch_id"] = str(branch_id)
    execution_trace = trace_payload.setdefault("execution_trace", {})
    if isinstance(execution_trace, dict):
        execution_trace["public_task_id"] = str(public_task_id)
        execution_trace["branch_id"] = str(branch_id)
    output.trace_payload = trace_payload
    return output


@register_task
class IllustrationsCountingBooksInSectionCountTask:
    """Count all books in one named library section."""

    task_id = BOOKS_IN_SECTION_TASK_ID
    domain = "illustrations"
    task_group = "counting"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        branch_params = dict(params)
        if "query_id" not in branch_params:
            branch_params["query_id"] = "books_in_section_count"
        return _generate_public_library_count(
            public_task_id=self.task_id,
            query_ids=("books_in_section_count",),
            branch_id="books_in_section",
            instance_seed=int(instance_seed),
            params=branch_params,
            max_attempts=int(max_attempts),
        )


@register_task
class IllustrationsCountingFilteredBookInSectionCountTask:
    """Count books in one library section filtered by color or orientation."""

    task_id = FILTERED_BOOK_TASK_ID
    domain = "illustrations"
    task_group = "counting"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return _generate_public_library_count(
            public_task_id=self.task_id,
            query_ids=FILTERED_QUERY_IDS,
            branch_id="filtered_book_in_section",
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )


__all__ = [
    "IllustrationsCountingBooksInSectionCountTask",
    "IllustrationsCountingFilteredBookInSectionCountTask",
    "_sample_spec",
]
