"""Additional CountQA-style predicate counts for dense 3D object clusters."""

from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

from trace.core.seed import spawn_rng
from trace.core.scene_config import (
    get_domain_defaults,
    get_scene_defaults,
    resolve_scene_section_defaults,
)
from trace.core.types import TypedValue
from trace.core.visual.background import make_background_canvas
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_scene_generation_rendering_prompt_defaults,
)
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from trace.tasks.three_d.shared.object_resources import OBJECT_CLUSTER_NAME_BY_SHAPE_TYPE
from trace.tasks.three_d.shared.object_scene import (
    _RenderParams,
    _build_projection_frame,
    _camera_yaw_band_for_instance,
    _min_pairwise,
    _object_reference_points,
    _resolve_render_params,
    _sample_camera,
    render_object_scene_3d,
)
from trace.tasks.three_d.shared.task_support import normalize_unit as _normalize_unit
from trace.tasks.three_d.shared.task_support import resolve_axis_variant as _shared_resolve_axis_variant
from trace.tasks.three_d.shared.task_support import resolve_count as _shared_resolve_count
from ._attribute_count_impl import (
    COLOR_SAFE_CLUSTER_SHAPE_TYPES,
    PROMPT_COLOR_RGB,
    _place_colored_cluster_objects,
    _view_is_valid,
)
from ._instance_count_impl import (
    SCENE_ID,
    SUPPORTED_SCENE_VARIANTS,
    _camera_record,
    _finalize_specs,
    _one_hot_int_probability_map,
    _frame_record,
    _object_plural,
    _resolve_uniform_count,
    _uniform_string_probability_map,
)


COLOR_MEMBERSHIP_COUNT_TASK_ID = "task_three_d__object_cluster__color_membership_count"
MULTI_ATTRIBUTE_OR_COUNT_TASK_ID = "task_three_d__object_cluster__multi_attribute_or_count"
MULTI_ATTRIBUTE_EXCLUSION_COUNT_TASK_ID = "task_three_d__object_cluster__multi_attribute_exclusion_count"
TYPE_UNION_COUNT_TASK_ID = "task_three_d__object_cluster__type_union_count"
COUNT_ARITHMETIC_TASK_ID = "task_three_d__object_cluster__count_arithmetic"
TYPE_FREQUENCY_COUNT_TASK_ID = "task_three_d__object_cluster__type_frequency_count"

COLOR_MEMBERSHIP_QUERY_IDS: Tuple[str, ...] = ("color_count",)
MULTI_ATTRIBUTE_OR_QUERY_IDS: Tuple[str, ...] = ("type_or_color_count",)
MULTI_ATTRIBUTE_EXCLUSION_QUERY_IDS: Tuple[str, ...] = (
    "type_and_not_color_count",
    "color_and_not_type_count",
)
TYPE_UNION_QUERY_IDS: Tuple[str, ...] = ("two_type_union_count",)
COUNT_ARITHMETIC_QUERY_IDS: Tuple[str, ...] = (
    "two_type_total_count",
    "two_type_difference_count",
    "two_color_total_count",
    "two_color_difference_count",
)
TYPE_FREQUENCY_QUERY_IDS: Tuple[str, ...] = (
    "most_frequent_type_count",
    "singleton_type_count",
)
TOTAL_ARITHMETIC_QUERY_IDS = {"two_type_total_count", "two_color_total_count"}
SOURCE_ID = "three_d_object_cluster_predicate_count_source"


def _shape_support() -> Tuple[str, ...]:
    return tuple(str(shape) for shape in COLOR_SAFE_CLUSTER_SHAPE_TYPES)


def _color_support() -> Tuple[str, ...]:
    return tuple(str(color) for color in PROMPT_COLOR_RGB)


def _object_name_for_shape(shape_type: str) -> str:
    return str(OBJECT_CLUSTER_NAME_BY_SHAPE_TYPE.get(str(shape_type), str(shape_type).replace("_", " ")))


def _object_plural_for_shape(shape_type: str) -> str:
    return _object_plural(_object_name_for_shape(str(shape_type)))


def _join_with_or(items: Sequence[str]) -> str:
    values = [str(item) for item in items]
    if len(values) <= 1:
        return values[0] if values else ""
    if len(values) == 2:
        return f"{values[0]} or {values[1]}"
    return f"{', '.join(values[:-1])}, or {values[-1]}"


def _selected_probability_map(values: Sequence[str], selected_values: Sequence[str]) -> Dict[str, float]:
    support = tuple(str(value) for value in values)
    selected = {str(value) for value in selected_values}
    probability = 1.0 / max(1, len(selected))
    return {str(value): (float(probability) if str(value) in selected else 0.0) for value in support}


def _resolve_string_subset(
    *,
    params: Mapping[str, Any],
    key: str,
    support: Sequence[str],
    instance_seed: int,
    namespace: str,
    count: int,
) -> Tuple[List[str], Dict[str, float]]:
    support_values = tuple(str(value) for value in support)
    explicit_value = params.get(str(key))
    if explicit_value is not None:
        if isinstance(explicit_value, str):
            selected_values = [value.strip() for value in explicit_value.split(",") if value.strip()]
        else:
            selected_values = [str(value) for value in explicit_value]
        if selected_values:
            if len(selected_values) != len(set(selected_values)):
                raise ValueError(f"{key} contains duplicate values")
            unsupported = [value for value in selected_values if value not in set(support_values)]
            if unsupported:
                raise ValueError(f"unsupported {key} values: {unsupported}")
            if len(selected_values) < int(count):
                raise ValueError(f"{key} requires at least {count} values")
            selected_values = selected_values[: int(count)]
            return list(selected_values), _selected_probability_map(support_values, selected_values)

    rng = spawn_rng(int(instance_seed), f"{namespace}.shuffle")
    ordered = list(support_values)
    rng.shuffle(ordered)
    start_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    selected = [str(ordered[(abs(int(start_index)) + offset) % len(ordered)]) for offset in range(int(count))]
    return list(selected), _selected_probability_map(support_values, selected)


def _resolve_named_choice(
    *,
    params: Mapping[str, Any],
    key: str,
    support: Sequence[str],
    task_id: str,
    query_id: str,
    instance_seed: int,
) -> Tuple[str, Dict[str, float]]:
    support_values = tuple(str(value) for value in support)
    explicit_value = params.get(str(key))
    if explicit_value is not None:
        selected = str(explicit_value)
        if selected not in set(support_values):
            raise ValueError(f"unsupported {key} for {task_id}: {selected}")
        return selected, _uniform_string_probability_map(support_values, selected=selected)
    selected_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.{query_id}.{key}",
    )
    selected = str(support_values[abs(int(selected_index)) % len(support_values)])
    return selected, _uniform_string_probability_map(support_values)


def _all_property_keys() -> List[Tuple[str, str]]:
    return [(str(shape), str(color)) for shape in _shape_support() for color in _color_support()]


def _property_key(shape_type: str, color_name: str) -> Tuple[str, str]:
    return (str(shape_type), str(color_name))


def _target_spec_matches_key(target_spec: Mapping[str, Any], key: Tuple[str, str]) -> bool:
    shape_type, color_name = _property_key(str(key[0]), str(key[1]))
    query_id = str(target_spec["query_id"])
    target_shape_type = target_spec.get("target_shape_type")
    target_color_name = target_spec.get("target_color_name")
    target_shape_types = {str(value) for value in target_spec.get("target_shape_types", [])}
    singleton_shape_types = {str(value) for value in target_spec.get("singleton_shape_types", [])}

    if query_id == "color_count":
        return str(color_name) == str(target_color_name)
    if query_id == "type_or_color_count":
        return str(shape_type) == str(target_shape_type) or str(color_name) == str(target_color_name)
    if query_id == "type_and_not_color_count":
        return str(shape_type) == str(target_shape_type) and str(color_name) != str(target_color_name)
    if query_id == "color_and_not_type_count":
        return str(color_name) == str(target_color_name) and str(shape_type) != str(target_shape_type)
    if query_id == "two_type_union_count":
        return str(shape_type) in target_shape_types
    if query_id == "most_frequent_type_count":
        return str(shape_type) == str(target_shape_type)
    if query_id == "singleton_type_count":
        return str(shape_type) in singleton_shape_types
    raise ValueError(f"unsupported object-cluster predicate query_id: {query_id}")


def _target_property_phrase(target_spec: Mapping[str, Any]) -> str:
    query_id = str(target_spec["query_id"])
    target_shape_type = target_spec.get("target_shape_type")
    target_color_name = target_spec.get("target_color_name")
    target_object_plural = str(target_spec.get("target_object_plural", "objects"))
    if query_id == "color_count":
        return f"{target_color_name} objects"
    if query_id == "type_or_color_count":
        return f"{target_object_plural} or {target_color_name} objects"
    if query_id == "type_and_not_color_count":
        return f"{target_object_plural} that are not {target_color_name}"
    if query_id == "color_and_not_type_count":
        return f"{target_color_name} objects that are not {target_object_plural}"
    if query_id == "two_type_union_count":
        return str(target_spec["target_object_union_phrase"])
    if query_id == "most_frequent_type_count":
        return f"objects of the most frequent type ({_object_plural_for_shape(str(target_shape_type))})"
    if query_id == "singleton_type_count":
        return "objects whose type appears exactly once"
    return "counted objects"


def _build_predicate_target_spec(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    target_count: int,
) -> Tuple[Dict[str, Any], Dict[str, float], Dict[str, float]]:
    shape_support = _shape_support()
    color_support = _color_support()
    query = str(query_id)

    if query == "color_count":
        target_color_name, color_probabilities = _resolve_named_choice(
            params=params,
            key="target_color_name",
            support=color_support,
            task_id=task_id,
            query_id=query,
            instance_seed=int(instance_seed),
        )
        target_spec = {
            "query_id": query,
            "target_color_name": str(target_color_name),
        }
        target_spec["target_property_phrase"] = _target_property_phrase(target_spec)
        return dict(target_spec), {}, dict(color_probabilities)

    if query == "two_type_union_count":
        target_shape_types, shape_probabilities = _resolve_string_subset(
            params=params,
            key="target_shape_types",
            support=shape_support,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.{query}.target_shape_types",
            count=2,
        )
        target_object_plurals = [_object_plural_for_shape(shape) for shape in target_shape_types]
        target_spec = {
            "query_id": query,
            "target_shape_types": list(target_shape_types),
            "target_object_plurals": list(target_object_plurals),
            "target_object_union_phrase": _join_with_or(target_object_plurals),
        }
        target_spec["target_property_phrase"] = _target_property_phrase(target_spec)
        return dict(target_spec), dict(shape_probabilities), {}

    if query == "most_frequent_type_count":
        target_shape_type, shape_probabilities = _resolve_named_choice(
            params=params,
            key="target_shape_type",
            support=shape_support,
            task_id=task_id,
            query_id=query,
            instance_seed=int(instance_seed),
        )
        object_name = _object_name_for_shape(str(target_shape_type))
        target_spec = {
            "query_id": query,
            "target_shape_type": str(target_shape_type),
            "target_object_name": str(object_name),
            "target_object_plural": _object_plural(str(object_name)),
        }
        target_spec["target_property_phrase"] = _target_property_phrase(target_spec)
        return dict(target_spec), dict(shape_probabilities), {}

    if query == "singleton_type_count":
        singleton_shape_types, shape_probabilities = _resolve_string_subset(
            params=params,
            key="target_shape_types",
            support=shape_support,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.{query}.singleton_shape_types",
            count=int(target_count),
        )
        target_spec = {
            "query_id": query,
            "singleton_shape_types": list(singleton_shape_types),
            "singleton_object_plurals": [_object_plural_for_shape(shape) for shape in singleton_shape_types],
        }
        target_spec["target_property_phrase"] = _target_property_phrase(target_spec)
        return dict(target_spec), dict(shape_probabilities), {}

    target_shape_type, shape_probabilities = _resolve_named_choice(
        params=params,
        key="target_shape_type",
        support=shape_support,
        task_id=task_id,
        query_id=query,
        instance_seed=int(instance_seed),
    )
    target_color_name, color_probabilities = _resolve_named_choice(
        params=params,
        key="target_color_name",
        support=color_support,
        task_id=task_id,
        query_id=query,
        instance_seed=int(instance_seed),
    )
    object_name = _object_name_for_shape(str(target_shape_type))
    target_spec = {
        "query_id": query,
        "target_shape_type": str(target_shape_type),
        "target_object_name": str(object_name),
        "target_object_plural": _object_plural(str(object_name)),
        "target_color_name": str(target_color_name),
    }
    target_spec["target_property_phrase"] = _target_property_phrase(target_spec)
    return dict(target_spec), dict(shape_probabilities), dict(color_probabilities)


def _preferred_positive_keys(target_spec: Mapping[str, Any]) -> List[Tuple[str, str]]:
    query_id = str(target_spec["query_id"])
    shape_support = list(_shape_support())
    color_support = list(_color_support())
    rng_seed_keys: List[Tuple[str, str]] = []
    target_shape = target_spec.get("target_shape_type")
    target_color = target_spec.get("target_color_name")
    if query_id == "type_or_color_count":
        wrong_colors = [color for color in color_support if str(color) != str(target_color)]
        wrong_shapes = [shape for shape in shape_support if str(shape) != str(target_shape)]
        rng_seed_keys.extend(
            [
                (str(target_shape), str(target_color)),
                (str(target_shape), str(wrong_colors[0])),
                (str(wrong_shapes[0]), str(target_color)),
            ]
        )
    elif query_id == "two_type_union_count":
        for shape in target_spec.get("target_shape_types", []):
            rng_seed_keys.append((str(shape), str(color_support[len(rng_seed_keys) % len(color_support)])))
    elif query_id == "type_and_not_color_count":
        wrong_colors = [color for color in color_support if str(color) != str(target_color)]
        rng_seed_keys.extend((str(target_shape), str(color)) for color in wrong_colors[:3])
    elif query_id == "color_and_not_type_count":
        wrong_shapes = [shape for shape in shape_support if str(shape) != str(target_shape)]
        rng_seed_keys.extend((str(shape), str(target_color)) for shape in wrong_shapes[:3])
    elif query_id == "color_count":
        rng_seed_keys.extend((str(shape), str(target_color)) for shape in shape_support[:4])
    return [key for key in rng_seed_keys if _target_spec_matches_key(target_spec, key)]


def _preferred_distractor_keys(target_spec: Mapping[str, Any]) -> List[Tuple[str, str]]:
    query_id = str(target_spec["query_id"])
    shape_support = list(_shape_support())
    color_support = list(_color_support())
    target_shape = target_spec.get("target_shape_type")
    target_color = target_spec.get("target_color_name")
    preferred: List[Tuple[str, str]] = []
    if query_id == "type_or_color_count":
        preferred.extend((shape, color) for shape in shape_support if str(shape) != str(target_shape) for color in color_support if str(color) != str(target_color))
    elif query_id == "type_and_not_color_count":
        preferred.append((str(target_shape), str(target_color)))
        preferred.extend((shape, str(target_color)) for shape in shape_support if str(shape) != str(target_shape))
    elif query_id == "color_and_not_type_count":
        preferred.append((str(target_shape), str(target_color)))
        preferred.extend((str(target_shape), color) for color in color_support if str(color) != str(target_color))
    elif query_id == "two_type_union_count":
        target_shapes = {str(shape) for shape in target_spec.get("target_shape_types", [])}
        preferred.extend((shape, color_support[0]) for shape in shape_support if str(shape) not in target_shapes)
    elif query_id == "color_count":
        preferred.extend((shape_support[0], color) for color in color_support if str(color) != str(target_color))
    filtered: List[Tuple[str, str]] = []
    seen: set[Tuple[str, str]] = set()
    for key in preferred:
        normalized = _property_key(str(key[0]), str(key[1]))
        if normalized in seen or _target_spec_matches_key(target_spec, normalized):
            continue
        seen.add(normalized)
        filtered.append(normalized)
    return list(filtered)


def _random_color(rng) -> str:
    return str(rng.choice(list(_color_support())))


def _sample_predicate_sequence(
    *,
    rng,
    target_spec: Mapping[str, Any],
    target_count: int,
    object_count: int,
) -> List[Tuple[str, str, bool, str]]:
    matching_pairs = [key for key in _all_property_keys() if _target_spec_matches_key(target_spec, key)]
    distractor_pairs = [key for key in _all_property_keys() if not _target_spec_matches_key(target_spec, key)]
    if not matching_pairs or not distractor_pairs:
        raise ValueError("object-cluster predicate count needs both target and distractor property support")

    sequence: List[Tuple[str, str, bool, str]] = []
    positives = _preferred_positive_keys(target_spec)
    rng.shuffle(positives)
    for shape_type, color_name in positives:
        if len(sequence) >= int(target_count):
            break
        sequence.append((str(shape_type), str(color_name), True, "target"))

    rng.shuffle(matching_pairs)
    match_index = 0
    while len(sequence) < int(target_count):
        shape_type, color_name = matching_pairs[int(match_index) % len(matching_pairs)]
        sequence.append((str(shape_type), str(color_name), True, "target"))
        match_index += 1

    preferred_distractors = _preferred_distractor_keys(target_spec)
    must_keep = preferred_distractors[:1] if str(target_spec["query_id"]) in {"type_and_not_color_count", "color_and_not_type_count"} else []
    shuffled_distractors = preferred_distractors[len(must_keep) :]
    rng.shuffle(shuffled_distractors)
    preferred_distractors = [*must_keep, *shuffled_distractors]
    for shape_type, color_name in preferred_distractors[:4]:
        if len(sequence) >= int(object_count):
            break
        sequence.append((str(shape_type), str(color_name), False, "structured_distractor"))

    rng.shuffle(distractor_pairs)
    distractor_index = 0
    while len(sequence) < int(object_count):
        shape_type, color_name = distractor_pairs[int(distractor_index) % len(distractor_pairs)]
        sequence.append((str(shape_type), str(color_name), False, "distractor"))
        distractor_index += 1

    rng.shuffle(sequence)
    return list(sequence)


def _sample_frequency_sequence(
    *,
    rng,
    target_spec: Mapping[str, Any],
    target_count: int,
    object_count: int,
) -> Tuple[List[Tuple[str, str, bool, str]], Dict[str, Any]]:
    query_id = str(target_spec["query_id"])
    shape_support = list(_shape_support())
    sequence: List[Tuple[str, str, bool, str]] = []
    dataset_target_spec = dict(target_spec)
    if query_id == "most_frequent_type_count":
        target_shape = str(target_spec["target_shape_type"])
        sequence.extend((target_shape, _random_color(rng), True, "target") for _ in range(int(target_count)))
        remaining = int(object_count) - int(target_count)
        distractor_shapes = [shape for shape in shape_support if str(shape) != target_shape]
        rng.shuffle(distractor_shapes)
        for shape in distractor_shapes:
            if remaining <= 0:
                break
            max_count = max(1, min(4, int(target_count) - 1, int(remaining)))
            count = int(rng.randint(1, int(max_count)))
            sequence.extend((str(shape), _random_color(rng), False, "lower_frequency_distractor") for _ in range(count))
            remaining -= int(count)
        if remaining > 0:
            raise ValueError("not enough distractor support for frequency count")
    elif query_id == "singleton_type_count":
        singleton_shapes = [str(shape) for shape in target_spec["singleton_shape_types"]]
        sequence.extend((shape, _random_color(rng), True, "singleton_type") for shape in singleton_shapes)
        remaining = int(object_count) - len(singleton_shapes)
        repeated_shapes = [shape for shape in shape_support if str(shape) not in set(singleton_shapes)]
        rng.shuffle(repeated_shapes)
        group_counts: List[Tuple[str, int]] = []
        for shape in repeated_shapes:
            if remaining <= 0:
                break
            if remaining == 1:
                if not group_counts:
                    raise ValueError("singleton frequency needs room for repeated distractor groups")
                prev_shape, prev_count = group_counts[-1]
                group_counts[-1] = (prev_shape, int(prev_count) + 1)
                remaining = 0
                break
            count = int(rng.randint(2, min(4, int(remaining))))
            if remaining - count == 1:
                count += 1
            group_counts.append((str(shape), int(count)))
            remaining -= int(count)
        if remaining > 0:
            raise ValueError("not enough repeated-shape support for singleton frequency count")
        for shape, count in group_counts:
            sequence.extend((str(shape), _random_color(rng), False, "repeated_type_distractor") for _ in range(int(count)))
        dataset_target_spec["target_property_phrase"] = _target_property_phrase(dataset_target_spec)
    else:
        raise ValueError(f"unsupported frequency query_id: {query_id}")
    rng.shuffle(sequence)
    return list(sequence), dict(dataset_target_spec)


def _resolve_arithmetic_operands(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[Dict[str, Any], Dict[str, float], Dict[str, float]]:
    query = str(query_id)
    shape_support = _shape_support()
    color_support = _color_support()
    if query in {"two_type_total_count", "two_type_difference_count"}:
        explicit_left = params.get("left_shape_type")
        explicit_right = params.get("right_shape_type")
        if explicit_left is not None and explicit_right is not None:
            operand_shapes = [str(explicit_left), str(explicit_right)]
            if len(set(operand_shapes)) != 2 or any(shape not in set(shape_support) for shape in operand_shapes):
                raise ValueError(f"arithmetic shape operands must be two distinct supported shapes for {task_id}")
            shape_probabilities = _selected_probability_map(shape_support, operand_shapes)
        else:
            operand_shapes, shape_probabilities = _resolve_string_subset(
                params=params,
                key="operand_shape_types",
                support=shape_support,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.{query}.operand_shape_types",
                count=2,
            )
        left_shape, right_shape = operand_shapes[:2]
        left_phrase = _object_plural_for_shape(str(left_shape))
        right_phrase = _object_plural_for_shape(str(right_shape))
        spec = {
            "query_id": query,
            "operand_kind": "shape",
            "left_shape_type": str(left_shape),
            "right_shape_type": str(right_shape),
            "target_shape_types": [str(left_shape), str(right_shape)],
            "left_operand_phrase": str(left_phrase),
            "right_operand_phrase": str(right_phrase),
            "arithmetic_operation": "total" if query in TOTAL_ARITHMETIC_QUERY_IDS else "absolute_difference",
        }
        return dict(spec), dict(shape_probabilities), {}

    explicit_left_color = params.get("left_color_name")
    explicit_right_color = params.get("right_color_name")
    if explicit_left_color is not None and explicit_right_color is not None:
        operand_colors = [str(explicit_left_color), str(explicit_right_color)]
        if len(set(operand_colors)) != 2 or any(color not in set(color_support) for color in operand_colors):
            raise ValueError(f"arithmetic color operands must be two distinct supported colors for {task_id}")
        color_probabilities = _selected_probability_map(color_support, operand_colors)
    else:
        operand_colors, color_probabilities = _resolve_string_subset(
            params=params,
            key="operand_color_names",
            support=color_support,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.{query}.operand_color_names",
            count=2,
        )
    left_color, right_color = operand_colors[:2]
    spec = {
        "query_id": query,
        "operand_kind": "color",
        "left_color_name": str(left_color),
        "right_color_name": str(right_color),
        "target_color_names": [str(left_color), str(right_color)],
        "left_operand_phrase": f"{left_color} objects",
        "right_operand_phrase": f"{right_color} objects",
        "arithmetic_operation": "total" if query in TOTAL_ARITHMETIC_QUERY_IDS else "absolute_difference",
    }
    return dict(spec), {}, dict(color_probabilities)


def _sample_arithmetic_sequence(
    *,
    rng,
    arithmetic_spec: Mapping[str, Any],
    left_count: int,
    right_count: int,
    object_count: int,
) -> List[Tuple[str, str, bool, str]]:
    shape_support = list(_shape_support())
    color_support = list(_color_support())
    sequence: List[Tuple[str, str, bool, str]] = []
    if str(arithmetic_spec["operand_kind"]) == "shape":
        left_shape = str(arithmetic_spec["left_shape_type"])
        right_shape = str(arithmetic_spec["right_shape_type"])
        sequence.extend((left_shape, _random_color(rng), True, "left_operand") for _ in range(int(left_count)))
        sequence.extend((right_shape, _random_color(rng), True, "right_operand") for _ in range(int(right_count)))
        distractor_shapes = [shape for shape in shape_support if str(shape) not in {left_shape, right_shape}]
        while len(sequence) < int(object_count):
            sequence.append((str(rng.choice(distractor_shapes)), _random_color(rng), False, "distractor"))
    else:
        left_color = str(arithmetic_spec["left_color_name"])
        right_color = str(arithmetic_spec["right_color_name"])
        sequence.extend((str(rng.choice(shape_support)), left_color, True, "left_operand") for _ in range(int(left_count)))
        sequence.extend((str(rng.choice(shape_support)), right_color, True, "right_operand") for _ in range(int(right_count)))
        distractor_colors = [color for color in color_support if str(color) not in {left_color, right_color}]
        while len(sequence) < int(object_count):
            sequence.append((str(rng.choice(shape_support)), str(rng.choice(distractor_colors)), False, "distractor"))
    rng.shuffle(sequence)
    return list(sequence)


def _build_dataset_from_sequence(
    *,
    task_id: str,
    scene_kind: str,
    query_id: str,
    scene_variant: str,
    render_params: _RenderParams,
    instance_seed: int,
    build_sequence: Callable[[Any], Tuple[List[Tuple[str, str, bool, str]], Dict[str, Any], int, int]],
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{SOURCE_ID}.{task_id}.dataset")
    selected_camera_yaw_band = _camera_yaw_band_for_instance(int(instance_seed))
    for _attempt in range(720):
        camera = _sample_camera(rng, yaw_band_degrees=selected_camera_yaw_band)
        sequence, target_spec, answer_value, expected_annotation_count = build_sequence(rng)
        object_specs = _place_colored_cluster_objects(
            rng=rng,
            sequence=sequence,
            scene_variant=str(scene_variant),
        )
        reference_points = [point for spec in object_specs for point in _object_reference_points(spec)]
        frame = _build_projection_frame(camera=camera, render_params=render_params, point_worlds=reference_points)
        if not _view_is_valid(specs=object_specs, camera=camera, frame=frame, render_params=render_params):
            continue
        finalized_specs = _finalize_specs(object_specs, camera=camera, frame=frame)
        target_specs = [spec for spec in finalized_specs if bool(spec.get("matches_query", False))]
        if len(target_specs) != int(expected_annotation_count):
            continue

        distances = [float(spec["camera_distance"]) for spec in finalized_specs]
        shape_counts = Counter(str(spec["shape_type"]) for spec in finalized_specs)
        color_counts = Counter(str(spec["color_name"]) for spec in finalized_specs)
        property_counts = Counter(_property_key(str(spec["shape_type"]), str(spec["color_name"])) for spec in finalized_specs)
        count_role_counts = Counter(str(spec["count_role"]) for spec in finalized_specs)
        target_object_ids = [str(spec["object_id"]) for spec in sorted(target_specs, key=lambda item: str(item["object_id"]))]
        role_object_ids: Dict[str, List[str]] = {}
        for spec in sorted(finalized_specs, key=lambda item: str(item["object_id"])):
            role = str(spec.get("count_role", ""))
            if role:
                role_object_ids.setdefault(role, []).append(str(spec["object_id"]))
        dataset_target_spec = dict(target_spec)
        dataset_target_spec.setdefault("target_property_phrase", _target_property_phrase(dataset_target_spec))
        return {
            "scene_kind": str(scene_kind),
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "object_count": len(finalized_specs),
            "countable_object_count": len(finalized_specs),
            "target_count": int(expected_annotation_count),
            "answer_value": int(answer_value),
            "target_spec": dict(dataset_target_spec),
            "target_shape_type": dataset_target_spec.get("target_shape_type"),
            "target_shape_types": list(dataset_target_spec.get("target_shape_types", [])),
            "target_object_name": dataset_target_spec.get("target_object_name"),
            "target_object_plural": dataset_target_spec.get("target_object_plural"),
            "target_object_union_phrase": dataset_target_spec.get("target_object_union_phrase"),
            "target_color_name": dataset_target_spec.get("target_color_name"),
            "target_color_names": list(dataset_target_spec.get("target_color_names", [])),
            "singleton_shape_types": list(dataset_target_spec.get("singleton_shape_types", [])),
            "left_operand_phrase": dataset_target_spec.get("left_operand_phrase"),
            "right_operand_phrase": dataset_target_spec.get("right_operand_phrase"),
            "arithmetic_operation": dataset_target_spec.get("arithmetic_operation"),
            "target_property_phrase": str(dataset_target_spec["target_property_phrase"]),
            "target_object_ids": list(target_object_ids),
            "role_object_ids": {str(role): list(ids) for role, ids in sorted(role_object_ids.items())},
            "object_specs": sorted(finalized_specs, key=lambda spec: str(spec["object_id"])),
            "point_specs": sorted(finalized_specs, key=lambda spec: str(spec["object_id"])),
            "context_object_specs": [],
            "shape_counts": {str(key): int(value) for key, value in sorted(shape_counts.items())},
            "color_counts": {str(key): int(value) for key, value in sorted(color_counts.items())},
            "property_counts": {
                f"{color_name}_{shape_type}": int(count)
                for (shape_type, color_name), count in sorted(property_counts.items())
            },
            "count_role_counts": {str(key): int(value) for key, value in sorted(count_role_counts.items())},
            "camera": _camera_record(camera, yaw_band=selected_camera_yaw_band),
            "projection_frame": _frame_record(frame),
            "solver_trace": {
                "count_predicate": str(query_id),
                "target_spec": dict(dataset_target_spec),
                "target_property_phrase": str(dataset_target_spec["target_property_phrase"]),
                "target_count": int(expected_annotation_count),
                "answer_value": int(answer_value),
                "target_object_ids": list(target_object_ids),
                "role_object_ids": {str(role): list(ids) for role, ids in sorted(role_object_ids.items())},
                "shape_counts": {str(key): int(value) for key, value in sorted(shape_counts.items())},
                "color_counts": {str(key): int(value) for key, value in sorted(color_counts.items())},
                "property_counts": {
                    f"{color_name}_{shape_type}": int(count)
                    for (shape_type, color_name), count in sorted(property_counts.items())
                },
                "count_role_counts": {str(key): int(value) for key, value in sorted(count_role_counts.items())},
                "cluster_object_pool_size": len(_shape_support()),
                "semantic_color_palette": {str(key): list(value) for key, value in sorted(PROMPT_COLOR_RGB.items())},
                "unique_integer_answer": True,
                "minimum_pairwise_camera_distance_margin": round(float(_min_pairwise(distances)), 4),
            },
        }
    raise ValueError(f"could not construct a valid 3D object-cluster dataset for {task_id}")


def _predicate_logic_load(query_id: str) -> float:
    return {
        "color_count": 0.34,
        "type_or_color_count": 0.70,
        "type_and_not_color_count": 0.74,
        "color_and_not_type_count": 0.74,
        "two_type_union_count": 0.48,
        "two_type_total_count": 0.64,
        "two_color_total_count": 0.64,
        "two_type_difference_count": 0.82,
        "two_color_difference_count": 0.82,
        "most_frequent_type_count": 0.78,
        "singleton_type_count": 0.84,
    }.get(str(query_id), 0.58)




_SCENE_DEFAULTS = get_scene_defaults("three_d", SCENE_ID)
_DOMAIN_DEFAULTS = get_domain_defaults("three_d")
_VISUAL_DEFAULTS = _DOMAIN_DEFAULTS.get("visual", {}) if isinstance(_DOMAIN_DEFAULTS, Mapping) else {}
_BACKGROUND_DEFAULTS = _VISUAL_DEFAULTS.get("background", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}
_NOISE_DEFAULTS = _VISUAL_DEFAULTS.get("noise", {}) if isinstance(_VISUAL_DEFAULTS, Mapping) else {}


def _resolve_task_defaults(task_id: str) -> Tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    gen_defaults, render_defaults, prompt_defaults = split_scene_generation_rendering_prompt_defaults(
        _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
        task_id=str(task_id),
    )
    return dict(gen_defaults), dict(render_defaults), dict(prompt_defaults)


class ObjectClusterPredicateCountBase:
    """Count dense-cluster objects under a task-specific predicate contract."""

    task_id = COLOR_MEMBERSHIP_COUNT_TASK_ID
    supported_query_ids: Tuple[str, ...] = COLOR_MEMBERSHIP_QUERY_IDS
    prompt_query_key: str | None = None
    domain = "three_d"
    default_dataset_enabled = True
    keyed_annotation = False

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        task_id = str(self.task_id)
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = (
                int(instance_seed)
                if attempt_index == 0
                else int(spawn_rng(int(instance_seed), f"{task_id}.attempt_seed.{attempt_index}").randrange(1, 2**62))
            )
            try:
                return self._generate_once(int(attempt_seed), params=params)
            except Exception as exc:  # pragma: no cover - unlucky sampling fallback.
                last_error = exc
        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts: {last_error}")

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        task_id = str(self.task_id)
        gen_defaults, render_defaults, prompt_defaults_config = _resolve_task_defaults(task_id)
        query_id, query_probabilities = _shared_resolve_axis_variant(
            params,
            task_id=task_id,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            supported_variants=self.supported_query_ids,
            explicit_key="query_id",
            weights_key="query_id_weights",
            balance_flag_key="balanced_query_id_sampling",
            axis_namespace="query_id",
        )
        prompt_query_key = str(self.prompt_query_key or query_id)
        scene_variant, scene_probabilities = _shared_resolve_axis_variant(
            params,
            task_id=task_id,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            supported_variants=SUPPORTED_SCENE_VARIANTS,
            explicit_key="scene_variant",
            weights_key="scene_variant_weights",
            balance_flag_key="balanced_scene_variant_sampling",
            axis_namespace="scene_variant",
        )
        render_params = _resolve_render_params(params, render_defaults=render_defaults)

        if task_id == COUNT_ARITHMETIC_TASK_ID:
            dataset, count_probabilities = self._build_arithmetic_dataset(
                query_id=str(prompt_query_key),
                scene_variant=str(scene_variant),
                params=params,
                gen_defaults=gen_defaults,
                render_params=render_params,
                instance_seed=int(instance_seed),
            )
        else:
            dataset, count_probabilities = self._build_predicate_dataset(
                task_id=task_id,
                query_id=str(prompt_query_key),
                scene_variant=str(scene_variant),
                params=params,
                gen_defaults=gen_defaults,
                render_params=render_params,
                instance_seed=int(instance_seed),
            )

        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=_BACKGROUND_DEFAULTS,
        )
        rendered = render_object_scene_3d(
            background,
            dataset=dataset,
            render_params=render_params,
            draw_candidate_labels=False,
            compute_single_annotation=False,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=_NOISE_DEFAULTS,
        )

        target_object_ids = [str(object_id) for object_id in dataset["target_object_ids"]]
        target_bboxes = [list(rendered.object_bboxes_px[str(object_id)]) for object_id in target_object_ids]
        if self.keyed_annotation:
            left_ids = [str(object_id) for object_id in dataset["role_object_ids"].get("left_operand", [])]
            right_ids = [str(object_id) for object_id in dataset["role_object_ids"].get("right_operand", [])]
            annotation_value = {
                "left_operand": [list(rendered.object_bboxes_px[str(object_id)]) for object_id in left_ids],
                "right_operand": [list(rendered.object_bboxes_px[str(object_id)]) for object_id in right_ids],
            }
            annotation_gt = TypedValue(type="keyed_bbox_set_map", value=dict(annotation_value))
            projected_annotation = {
                "type": "keyed_bbox_set_map",
                "keyed_bbox_set_map": dict(annotation_value),
                "pixel_keyed_bbox_set_map": dict(annotation_value),
            }
            annotation_render_map = {
                "operand_object_bboxes_px": {
                    "left_operand": {str(object_id): list(rendered.object_bboxes_px[str(object_id)]) for object_id in left_ids},
                    "right_operand": {str(object_id): list(rendered.object_bboxes_px[str(object_id)]) for object_id in right_ids},
                }
            }
        else:
            annotation_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in target_bboxes])
            projected_annotation = {
                "type": "bbox_set",
                "bbox_set": [list(bbox) for bbox in target_bboxes],
                "pixel_bbox_set": [list(bbox) for bbox in target_bboxes],
            }
            annotation_render_map = {}

        prompt_defaults = required_group_defaults(
            prompt_defaults_config,
            (
                "bundle_id",
                "scene_key",
                "task_key",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_slots = {
            "target_shape_type": str(dataset.get("target_shape_type") or ""),
            "target_object_name": str(dataset.get("target_object_name") or ""),
            "target_object_plural": str(dataset.get("target_object_plural") or ""),
            "target_object_union_phrase": str(dataset.get("target_object_union_phrase") or ""),
            "target_color_name": str(dataset.get("target_color_name") or ""),
            "target_color_names": _join_with_or([str(color) for color in dataset.get("target_color_names", [])]),
            "target_property_phrase": str(dataset["target_property_phrase"]),
            "left_operand_phrase": str(dataset.get("left_operand_phrase") or ""),
            "right_operand_phrase": str(dataset.get("right_operand_phrase") or ""),
        }
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(prompt_query_key),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            dynamic_slots=prompt_slots,
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_value = int(dataset["answer_value"])
        answer_gt = TypedValue(type="integer", value=int(answer_value))

        render_map = {
            "image_id": "img0",
            "scene_bbox_px": list(rendered.scene_bbox_px),
            "room_bbox_px": list(rendered.room_bbox_px),
            "object_bboxes_px": dict(rendered.object_bboxes_px),
            "object_centers_px": dict(rendered.object_centers_px),
            "target_object_bboxes_px": {
                str(object_id): list(rendered.object_bboxes_px[str(object_id)])
                for object_id in target_object_ids
            },
            "target_object_centers_px": {
                str(object_id): list(rendered.object_centers_px[str(object_id)])
                for object_id in target_object_ids
            },
        }
        render_map.update(annotation_render_map)
        trace_payload = {
            "scene_ir": {
                "scene_kind": str(dataset["scene_kind"]),
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "scene_variant": str(scene_variant),
                    "object_count": int(dataset["object_count"]),
                    "countable_object_count": int(dataset["countable_object_count"]),
                    "target_spec": dict(dataset["target_spec"]),
                    "target_property_phrase": str(dataset["target_property_phrase"]),
                    "target_count": int(dataset["target_count"]),
                    "answer_value": int(answer_value),
                    "target_object_ids": list(target_object_ids),
                    "role_object_ids": dict(dataset["role_object_ids"]),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query_id),
                    "internal_query_id": str(prompt_query_key),
                    "query_id_probabilities": dict(query_probabilities),
                    "scene_variant": str(scene_variant),
                    "scene_variant_probabilities": dict(scene_probabilities),
                    "object_count": int(dataset["object_count"]),
                    "object_count_probabilities": dict(count_probabilities.get("object_count_probabilities", {})),
                    "target_count": int(dataset["target_count"]),
                    "target_count_probabilities": dict(count_probabilities.get("target_count_probabilities", {})),
                    "left_operand_count": count_probabilities.get("left_operand_count"),
                    "left_operand_count_probabilities": dict(count_probabilities.get("left_operand_count_probabilities", {})),
                    "right_operand_count": count_probabilities.get("right_operand_count"),
                    "right_operand_count_probabilities": dict(count_probabilities.get("right_operand_count_probabilities", {})),
                    "target_spec": dict(dataset["target_spec"]),
                    "target_shape_type": dataset.get("target_shape_type"),
                    "target_shape_types": list(dataset.get("target_shape_types", [])),
                    "target_shape_type_probabilities": dict(count_probabilities.get("target_shape_probabilities", {})),
                    "target_color_name": dataset.get("target_color_name"),
                    "target_color_names": list(dataset.get("target_color_names", [])),
                    "target_color_name_probabilities": dict(count_probabilities.get("target_color_probabilities", {})),
                    "cluster_object_pool_size": len(_shape_support()),
                    "semantic_color_palette": {str(key): list(value) for key, value in sorted(PROMPT_COLOR_RGB.items())},
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "room_extent": float(render_params.room_extent),
                "full_bleed_floor": bool(render_params.full_bleed_floor),
                "semantic_color_palette": {str(key): list(value) for key, value in sorted(PROMPT_COLOR_RGB.items())},
            },
            "render_map": dict(render_map),
            "execution_trace": {
                "query_id": str(query_id),
                "internal_query_id": str(prompt_query_key),
                "scene_variant": str(scene_variant),
                "object_count": int(dataset["object_count"]),
                "countable_object_count": int(dataset["countable_object_count"]),
                "target_count": int(dataset["target_count"]),
                "answer_value": int(answer_value),
                "target_spec": dict(dataset["target_spec"]),
                "target_shape_type": dataset.get("target_shape_type"),
                "target_shape_types": list(dataset.get("target_shape_types", [])),
                "target_object_name": dataset.get("target_object_name"),
                "target_object_plural": dataset.get("target_object_plural"),
                "target_object_union_phrase": dataset.get("target_object_union_phrase"),
                "target_color_name": dataset.get("target_color_name"),
                "target_color_names": list(dataset.get("target_color_names", [])),
                "singleton_shape_types": list(dataset.get("singleton_shape_types", [])),
                "left_operand_phrase": dataset.get("left_operand_phrase"),
                "right_operand_phrase": dataset.get("right_operand_phrase"),
                "arithmetic_operation": dataset.get("arithmetic_operation"),
                "target_property_phrase": str(dataset["target_property_phrase"]),
                "target_object_ids": list(target_object_ids),
                "role_object_ids": dict(dataset["role_object_ids"]),
                "object_specs": [dict(spec) for spec in dataset["object_specs"]],
                "shape_counts": dict(dataset["shape_counts"]),
                "color_counts": dict(dataset["color_counts"]),
                "property_counts": dict(dataset["property_counts"]),
                "count_role_counts": dict(dataset["count_role_counts"]),
                "camera": dict(dataset["camera"]),
                "projection_frame": dict(dataset["projection_frame"]),
                "question_format": str(query_id),
                "internal_question_format": str(prompt_query_key),
                "solver_trace": dict(dataset["solver_trace"]),
            },
            "witness_symbolic": {
                "type": "object_cluster_count_arithmetic_operand_sets" if self.keyed_annotation else "object_cluster_predicate_count_object_set",
                "object_ids": list(target_object_ids),
                "role_object_ids": dict(dataset["role_object_ids"]),
                "target_spec": dict(dataset["target_spec"]),
                "target_property_phrase": str(dataset["target_property_phrase"]),
                "answer_value": int(answer_value),
            },
            "projected_annotation": dict(projected_annotation),
            "background": dict(background_meta),
            "post_image_noise": dict(post_noise_meta),
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
        )

    def _build_predicate_dataset(
        self,
        *,
        task_id: str,
        query_id: str,
        scene_variant: str,
        params: Mapping[str, Any],
        gen_defaults: Mapping[str, Any],
        render_params: _RenderParams,
        instance_seed: int,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        object_count, object_count_probabilities = _shared_resolve_count(
            params,
            task_id=task_id,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            prefix="object_count",
            minimum_default=int(group_default(gen_defaults, "object_count_min", 16)),
            maximum_default=int(group_default(gen_defaults, "object_count_max", 30)),
            lower=12,
            upper=32,
        )
        target_count, target_count_probabilities = _shared_resolve_count(
            params,
            task_id=task_id,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            prefix="target_count",
            minimum_default=int(group_default(gen_defaults, "target_count_min", 3)),
            maximum_default=int(group_default(gen_defaults, "target_count_max", 12)),
            lower=1,
            upper=max(1, min(16, int(object_count) - 4)),
        )
        if str(query_id) == "singleton_type_count" and params.get("target_shape_types") is not None:
            explicit_value = params.get("target_shape_types")
            if isinstance(explicit_value, str):
                explicit_singletons = [value.strip() for value in explicit_value.split(",") if value.strip()]
            else:
                explicit_singletons = [str(value) for value in explicit_value]
            if explicit_singletons:
                target_count = len(explicit_singletons)
                target_count_probabilities = _one_hot_int_probability_map(
                    range(1, max(1, min(16, int(object_count) - 4)) + 1),
                    selected=int(target_count),
                )
        target_spec, shape_probabilities, color_probabilities = _build_predicate_target_spec(
            query_id=str(query_id),
            params=params,
            instance_seed=int(instance_seed),
            task_id=task_id,
            target_count=int(target_count),
        )

        def _build_sequence(rng) -> Tuple[List[Tuple[str, str, bool, str]], Dict[str, Any], int, int]:
            if str(query_id) in TYPE_FREQUENCY_QUERY_IDS:
                sequence, dataset_target_spec = _sample_frequency_sequence(
                    rng=rng,
                    target_spec=target_spec,
                    target_count=int(target_count),
                    object_count=int(object_count),
                )
            else:
                sequence = _sample_predicate_sequence(
                    rng=rng,
                    target_spec=target_spec,
                    target_count=int(target_count),
                    object_count=int(object_count),
                )
                dataset_target_spec = dict(target_spec)
            return list(sequence), dict(dataset_target_spec), int(target_count), int(target_count)

        dataset = _build_dataset_from_sequence(
            task_id=task_id,
            scene_kind=f"three_d_object_cluster_{str(query_id)}",
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            render_params=render_params,
            instance_seed=int(instance_seed),
            build_sequence=_build_sequence,
        )
        return dict(dataset), {
            "object_count_probabilities": dict(object_count_probabilities),
            "target_count_probabilities": dict(target_count_probabilities),
            "target_shape_probabilities": dict(shape_probabilities),
            "target_color_probabilities": dict(color_probabilities),
        }

    def _build_arithmetic_dataset(
        self,
        *,
        query_id: str,
        scene_variant: str,
        params: Mapping[str, Any],
        gen_defaults: Mapping[str, Any],
        render_params: _RenderParams,
        instance_seed: int,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        operand_min = max(1, int(group_default(gen_defaults, "operand_count_min", 1)))
        operand_max = max(int(operand_min), int(group_default(gen_defaults, "operand_count_max", 7)))
        if str(query_id) not in TOTAL_ARITHMETIC_QUERY_IDS and (
            params.get("left_operand_count") is None or params.get("right_operand_count") is None
        ):
            max_difference = max(
                0,
                min(
                    int(operand_max) - int(operand_min),
                    int(group_default(gen_defaults, "difference_answer_max", int(operand_max) - int(operand_min))),
                ),
            )
            answer_value, answer_value_probabilities = _resolve_uniform_count(
                params=params,
                explicit_key="answer_value",
                minimum=0,
                maximum=int(max_difference),
                instance_seed=int(instance_seed),
                namespace=f"{self.task_id}.{query_id}.answer_value",
            )
            rng = spawn_rng(int(instance_seed), f"{self.task_id}.{query_id}.operand_counts_from_difference")
            lower_count = int(rng.randint(int(operand_min), int(operand_max) - int(answer_value)))
            if int(answer_value) == 0 or float(rng.random()) < 0.5:
                left_count = int(lower_count) + int(answer_value)
                right_count = int(lower_count)
            else:
                left_count = int(lower_count)
                right_count = int(lower_count) + int(answer_value)
            left_probabilities = {"derived_from_answer_value": 1.0}
            right_probabilities = {"derived_from_answer_value": 1.0}
        else:
            left_count, left_probabilities = _shared_resolve_count(
                params,
                task_id=self.task_id,
                gen_defaults=gen_defaults,
                instance_seed=int(instance_seed),
                prefix="left_operand_count",
                minimum_default=int(operand_min),
                maximum_default=int(operand_max),
                lower=1,
                upper=9,
            )
            right_count, right_probabilities = _shared_resolve_count(
                params,
                task_id=self.task_id,
                gen_defaults=gen_defaults,
                instance_seed=int(instance_seed),
                prefix="right_operand_count",
                minimum_default=int(operand_min),
                maximum_default=int(operand_max),
                lower=1,
                upper=9,
            )
            answer_value = int(left_count) + int(right_count) if str(query_id) in TOTAL_ARITHMETIC_QUERY_IDS else abs(int(left_count) - int(right_count))
            answer_value_probabilities = {"derived_from_operands": 1.0}
        operand_total = int(left_count) + int(right_count)
        object_minimum = max(int(group_default(gen_defaults, "object_count_min", 16)), int(operand_total) + 4)
        object_maximum = max(object_minimum, int(group_default(gen_defaults, "object_count_max", 30)))
        object_count, object_probabilities = _resolve_uniform_count(
            params=params,
            explicit_key="object_count",
            minimum=int(object_minimum),
            maximum=int(object_maximum),
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.{query_id}.object_count",
        )
        arithmetic_spec, shape_probabilities, color_probabilities = _resolve_arithmetic_operands(
            query_id=str(query_id),
            params=params,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
        )
        arithmetic_spec["target_property_phrase"] = (
            f"{arithmetic_spec['left_operand_phrase']} and {arithmetic_spec['right_operand_phrase']}"
        )
        arithmetic_spec["left_operand_count"] = int(left_count)
        arithmetic_spec["right_operand_count"] = int(right_count)

        def _build_sequence(rng) -> Tuple[List[Tuple[str, str, bool, str]], Dict[str, Any], int, int]:
            sequence = _sample_arithmetic_sequence(
                rng=rng,
                arithmetic_spec=arithmetic_spec,
                left_count=int(left_count),
                right_count=int(right_count),
                object_count=int(object_count),
            )
            return list(sequence), dict(arithmetic_spec), int(answer_value), int(operand_total)

        dataset = _build_dataset_from_sequence(
            task_id=str(self.task_id),
            scene_kind="three_d_object_cluster_count_arithmetic",
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            render_params=render_params,
            instance_seed=int(instance_seed),
            build_sequence=_build_sequence,
        )
        return dict(dataset), {
            "object_count_probabilities": dict(object_probabilities),
            "target_count_probabilities": {"derived_from_operands": 1.0},
            "left_operand_count": int(left_count),
            "left_operand_count_probabilities": dict(left_probabilities),
            "right_operand_count": int(right_count),
            "right_operand_count_probabilities": dict(right_probabilities),
            "answer_value_probabilities": dict(answer_value_probabilities),
            "target_shape_probabilities": dict(shape_probabilities),
            "target_color_probabilities": dict(color_probabilities),
        }


__all__ = [
    "COLOR_MEMBERSHIP_COUNT_TASK_ID",
    "COLOR_MEMBERSHIP_QUERY_IDS",
    "COUNT_ARITHMETIC_TASK_ID",
    "COUNT_ARITHMETIC_QUERY_IDS",
    "MULTI_ATTRIBUTE_EXCLUSION_COUNT_TASK_ID",
    "MULTI_ATTRIBUTE_EXCLUSION_QUERY_IDS",
    "MULTI_ATTRIBUTE_OR_COUNT_TASK_ID",
    "MULTI_ATTRIBUTE_OR_QUERY_IDS",
    "ObjectClusterPredicateCountBase",
    "TYPE_FREQUENCY_COUNT_TASK_ID",
    "TYPE_FREQUENCY_QUERY_IDS",
    "TYPE_UNION_COUNT_TASK_ID",
    "TYPE_UNION_QUERY_IDS",
]
