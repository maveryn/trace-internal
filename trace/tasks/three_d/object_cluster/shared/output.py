"""ClusterRequest assembly helpers for public object-cluster tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.core.seed import spawn_rng
from trace.tasks.three_d.shared.object_scene import ObjectSceneRenderParams

from .defaults import (
    CLUSTER_SCENE_VARIANTS,
    COLOR_READOUT_CLUSTER_SHAPE_TYPES,
    NAMED_CLUSTER_SHAPE_TYPES,
    PROMPT_COLOR_RGB,
)
from .objects import build_dataset_from_sequence
from .relations import (
    build_arithmetic_sequence,
    build_color_membership_sequence,
    build_exclusion_sequence,
    build_frequency_sequence,
    build_or_sequence,
    build_total_sequence,
    build_type_and_color_sequence,
    build_type_membership_sequence,
    color_support,
    resolve_color_choice,
    resolve_composition_mode,
    resolve_membership_counts,
    resolve_shape_choice,
    resolve_two_colors,
    resolve_two_shapes,
    selected_probability_map,
    target_mapping,
)
from .sampling import count_bounds, configured_int, resolve_scene_variant, resolve_uniform_count, resolve_weighted_count
from .state import ClusterRequest


def build_count_request(
    *,
    mode: str,
    external_query: str,
    prompt_key: str,
    branch_probabilities: Mapping[str, float],
    namespace: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    render_params: ObjectSceneRenderParams,
) -> ClusterRequest:
    """Assemble a neutral request from a public task's already-resolved contract."""

    scene_variant, scene_probabilities = resolve_scene_variant(
        params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        support=CLUSTER_SCENE_VARIANTS,
        namespace=f"{namespace}.scene_variant",
    )
    rng = spawn_rng(int(instance_seed), f"{namespace}.sequence")
    count_probabilities: Dict[str, Any] = {"cluster_object_pool_size": len(NAMED_CLUSTER_SHAPE_TYPES)}
    keyed_annotation = False

    if str(mode) == "all_objects":
        minimum, maximum = count_bounds(
            params=params,
            gen_defaults=gen_defaults,
            minimum_key="object_count_min",
            maximum_key="object_count_max",
            fallback_minimum=configured_int(params, gen_defaults, "single_type_count_min", 6),
            fallback_maximum=configured_int(params, gen_defaults, "single_type_count_max", 25),
            lower=6,
            upper=25,
        )
        object_count, object_probabilities = resolve_weighted_count(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            explicit_key="object_count",
            weights_key="object_count_weights",
            minimum=int(minimum),
            maximum=int(maximum),
            namespace=f"{namespace}.object_count",
        )
        primary_shape, shape_probabilities = resolve_shape_choice(
            params=params,
            key="primary_shape_type",
            instance_seed=int(instance_seed),
            namespace=f"{namespace}.primary_shape_type",
            support=NAMED_CLUSTER_SHAPE_TYPES,
        )
        sequence, target = build_total_sequence(shape_type=str(primary_shape), object_count=int(object_count), rng=rng)
        answer_value = int(object_count)
        expected_annotation_count = int(object_count)
        scene_kind = "three_d_object_cluster_total_count"
        extra_trace = {"cluster_composition_mode": "single_type_cluster", "distractor_count": 0, "cluster_object_pool_size": len(NAMED_CLUSTER_SHAPE_TYPES)}
        count_probabilities.update({"object_count_probabilities": dict(object_probabilities), "target_count_probabilities": dict(object_probabilities), "target_shape_probabilities": dict(shape_probabilities), "cluster_object_pool_size": len(NAMED_CLUSTER_SHAPE_TYPES)})
    elif str(mode) == "type_membership":
        composition_mode, composition_probabilities = resolve_composition_mode(params=params, gen_defaults=gen_defaults, instance_seed=int(instance_seed), namespace=f"{namespace}.composition_mode")
        count_record = resolve_membership_counts(params=params, gen_defaults=gen_defaults, composition_mode=str(composition_mode), instance_seed=int(instance_seed), namespace=f"{namespace}.counts")
        target_shape, shape_probabilities = resolve_shape_choice(params=params, key="target_shape_type", instance_seed=int(instance_seed), namespace=f"{namespace}.target_shape_type", support=NAMED_CLUSTER_SHAPE_TYPES)
        sequence, target = build_type_membership_sequence(shape_type=str(target_shape), composition_mode=str(composition_mode), target_count=int(count_record["target_count"]), object_count=int(count_record["object_count"]), rng=rng)
        answer_value = int(count_record["target_count"])
        expected_annotation_count = int(count_record["target_count"])
        scene_kind = "three_d_object_cluster_instance_count"
        extra_trace = {"cluster_composition_mode": str(composition_mode), "distractor_count": int(count_record["distractor_count"]), "cluster_object_pool_size": len(NAMED_CLUSTER_SHAPE_TYPES)}
        count_probabilities.update({**dict(count_record), "composition_mode_probabilities": dict(composition_probabilities), "target_shape_probabilities": dict(shape_probabilities), "cluster_object_pool_size": len(NAMED_CLUSTER_SHAPE_TYPES)})
    elif str(mode) in {"type_color", "color_membership", "type_or_color", "type_without_color", "color_without_type"}:
        object_count, object_probabilities = resolve_uniform_count(params=params, explicit_key="object_count", minimum=int(gen_defaults.get("object_count_min", 16)), maximum=int(gen_defaults.get("object_count_max", 30)), instance_seed=int(instance_seed), namespace=f"{namespace}.object_count")
        target_min = int(gen_defaults.get("target_count_min", 2))
        target_max = min(int(gen_defaults.get("target_count_max", 12)), max(1, int(object_count) - 4))
        target_count, target_probabilities = resolve_uniform_count(params=params, explicit_key="target_count", minimum=target_min, maximum=target_max, instance_seed=int(instance_seed), namespace=f"{namespace}.target_count")
        if str(mode) == "color_membership":
            target_color, color_probabilities = resolve_color_choice(params=params, key="target_color_name", instance_seed=int(instance_seed), namespace=f"{namespace}.target_color_name")
            sequence, target = build_color_membership_sequence(color_name=str(target_color), target_count=int(target_count), object_count=int(object_count), rng=rng)
            shape_probabilities: Dict[str, float] = {}
        else:
            target_shape, shape_probabilities = resolve_shape_choice(params=params, key="target_shape_type", instance_seed=int(instance_seed), namespace=f"{namespace}.target_shape_type", support=COLOR_READOUT_CLUSTER_SHAPE_TYPES)
            target_color, color_probabilities = resolve_color_choice(params=params, key="target_color_name", instance_seed=int(instance_seed), namespace=f"{namespace}.target_color_name")
            if str(mode) == "type_color":
                sequence, target = build_type_and_color_sequence(shape_type=str(target_shape), color_name=str(target_color), target_count=int(target_count), object_count=int(object_count), rng=rng)
            elif str(mode) == "type_or_color":
                sequence, target = build_or_sequence(shape_type=str(target_shape), color_name=str(target_color), target_count=int(target_count), object_count=int(object_count), rng=rng)
            else:
                sequence, target = build_exclusion_sequence(mode=str(mode), shape_type=str(target_shape), color_name=str(target_color), target_count=int(target_count), object_count=int(object_count), rng=rng)
        answer_value = int(target_count)
        expected_annotation_count = int(target_count)
        scene_kind = f"three_d_object_cluster_{mode}"
        pool_size = len(COLOR_READOUT_CLUSTER_SHAPE_TYPES)
        extra_trace = {"cluster_object_pool_size": int(pool_size)}
        count_probabilities.update({"object_count_probabilities": dict(object_probabilities), "target_count_probabilities": dict(target_probabilities), "target_shape_probabilities": dict(shape_probabilities), "target_color_probabilities": dict(color_probabilities), "cluster_object_pool_size": int(pool_size)})
    elif str(mode).startswith("arithmetic_"):
        operand_min = max(1, int(gen_defaults.get("operand_count_min", 1)))
        operand_max = max(int(operand_min), int(gen_defaults.get("operand_count_max", 7)))
        left_count, left_probabilities = resolve_uniform_count(params=params, explicit_key="left_operand_count", minimum=int(operand_min), maximum=int(operand_max), instance_seed=int(instance_seed), namespace=f"{namespace}.left_operand_count")
        right_count, right_probabilities = resolve_uniform_count(params=params, explicit_key="right_operand_count", minimum=int(operand_min), maximum=int(operand_max), instance_seed=int(instance_seed), namespace=f"{namespace}.right_operand_count")
        operation = "total" if str(mode).endswith("_total") else "absolute_difference"
        answer_value = int(left_count) + int(right_count) if operation == "total" else abs(int(left_count) - int(right_count))
        operand_total = int(left_count) + int(right_count)
        object_minimum = max(int(gen_defaults.get("object_count_min", 16)), int(operand_total) + 4)
        object_count, object_probabilities = resolve_uniform_count(params=params, explicit_key="object_count", minimum=int(object_minimum), maximum=max(object_minimum, int(gen_defaults.get("object_count_max", 30))), instance_seed=int(instance_seed), namespace=f"{namespace}.object_count")
        if "_type_" in str(mode):
            if params.get("left_shape_type") is not None and params.get("right_shape_type") is not None:
                operands = [str(params["left_shape_type"]), str(params["right_shape_type"])]
                if len(set(operands)) != 2 or any(value not in set(NAMED_CLUSTER_SHAPE_TYPES) for value in operands):
                    raise ValueError("shape operands must be two distinct supported shapes")
                operand_probabilities = selected_probability_map(NAMED_CLUSTER_SHAPE_TYPES, operands)
            else:
                operands, operand_probabilities = resolve_two_shapes(params=params, key="operand_shape_types", instance_seed=int(instance_seed), namespace=f"{namespace}.operand_shape_types")
            operand_kind = "shape"
            shape_probabilities = dict(operand_probabilities)
            color_probabilities = {}
        else:
            if params.get("left_color_name") is not None and params.get("right_color_name") is not None:
                operands = [str(params["left_color_name"]), str(params["right_color_name"])]
                if len(set(operands)) != 2 or any(value not in set(color_support()) for value in operands):
                    raise ValueError("color operands must be two distinct supported colors")
                operand_probabilities = selected_probability_map(color_support(), operands)
            else:
                operands, operand_probabilities = resolve_two_colors(params=params, key="operand_color_names", instance_seed=int(instance_seed), namespace=f"{namespace}.operand_color_names")
            operand_kind = "color"
            shape_probabilities = {}
            color_probabilities = dict(operand_probabilities)
        sequence, target = build_arithmetic_sequence(operand_kind=operand_kind, operation=operation, left_value=str(operands[0]), right_value=str(operands[1]), left_count=int(left_count), right_count=int(right_count), object_count=int(object_count), rng=rng)
        expected_annotation_count = int(operand_total)
        scene_kind = "three_d_object_cluster_count_arithmetic"
        pool_size = len(COLOR_READOUT_CLUSTER_SHAPE_TYPES) if str(operand_kind) == "color" else len(NAMED_CLUSTER_SHAPE_TYPES)
        extra_trace = {"cluster_object_pool_size": int(pool_size)}
        keyed_annotation = True
        count_probabilities.update({"object_count_probabilities": dict(object_probabilities), "target_count_probabilities": {"derived_from_operands": 1.0}, "left_operand_count": int(left_count), "left_operand_count_probabilities": dict(left_probabilities), "right_operand_count": int(right_count), "right_operand_count_probabilities": dict(right_probabilities), "target_shape_probabilities": shape_probabilities, "target_color_probabilities": color_probabilities, "cluster_object_pool_size": int(pool_size)})
    else:
        object_count, object_probabilities = resolve_uniform_count(params=params, explicit_key="object_count", minimum=int(gen_defaults.get("object_count_min", 16)), maximum=int(gen_defaults.get("object_count_max", 30)), instance_seed=int(instance_seed), namespace=f"{namespace}.object_count")
        if str(mode) == "frequency_max":
            target_count, target_probabilities = resolve_uniform_count(params=params, explicit_key="target_count", minimum=int(gen_defaults.get("target_count_min", 3)), maximum=min(int(gen_defaults.get("target_count_max", 9)), max(3, int(object_count) - 6)), instance_seed=int(instance_seed), namespace=f"{namespace}.target_count")
            target_shape, shape_probabilities = resolve_shape_choice(params=params, key="target_shape_type", instance_seed=int(instance_seed), namespace=f"{namespace}.target_shape_type", support=NAMED_CLUSTER_SHAPE_TYPES)
            singleton_shapes: list[str] = []
        else:
            explicit_value = params.get("target_shape_types")
            if explicit_value is not None:
                singleton_shapes = [str(value).strip() for value in explicit_value] if not isinstance(explicit_value, str) else [value.strip() for value in explicit_value.split(",") if value.strip()]
                target_count = len(singleton_shapes)
                target_probabilities = {str(target_count): 1.0}
                shape_probabilities = {str(shape): (1.0 / len(singleton_shapes) if str(shape) in set(singleton_shapes) else 0.0) for shape in NAMED_CLUSTER_SHAPE_TYPES}
            else:
                target_count, target_probabilities = resolve_uniform_count(params=params, explicit_key="target_count", minimum=int(gen_defaults.get("target_count_min", 3)), maximum=min(int(gen_defaults.get("target_count_max", 9)), max(1, int(object_count) - 4)), instance_seed=int(instance_seed), namespace=f"{namespace}.target_count")
                singleton_shapes, shape_probabilities = resolve_two_shapes(params=params, key="target_shape_types", instance_seed=int(instance_seed), namespace=f"{namespace}.singleton_shape_types")
                while len(singleton_shapes) < int(target_count):
                    singleton_shapes.append(str(NAMED_CLUSTER_SHAPE_TYPES[len(singleton_shapes) % len(NAMED_CLUSTER_SHAPE_TYPES)]))
            target_shape = None
        sequence, target = build_frequency_sequence(mode="most_common" if str(mode) == "frequency_max" else "singletons", target_shape_type=target_shape, singleton_shape_types=singleton_shapes, target_count=int(target_count), object_count=int(object_count), rng=rng)
        answer_value = int(target_count)
        expected_annotation_count = int(target_count)
        scene_kind = "three_d_object_cluster_type_frequency_count"
        extra_trace = {"cluster_object_pool_size": len(NAMED_CLUSTER_SHAPE_TYPES)}
        count_probabilities.update({"object_count_probabilities": dict(object_probabilities), "target_count_probabilities": dict(target_probabilities), "target_shape_probabilities": dict(shape_probabilities)})

    dataset = build_dataset_from_sequence(
        source_namespace=str(namespace),
        scene_kind=str(scene_kind),
        prompt_query_key=str(prompt_key),
        scene_variant=str(scene_variant),
        render_params=render_params,
        instance_seed=int(instance_seed),
        sequence=sequence,
        target_spec=target_mapping(target),
        answer_value=int(answer_value),
        expected_annotation_count=int(expected_annotation_count),
        extra_trace=dict(extra_trace),
    )
    return ClusterRequest(
        external_query=str(external_query),
        prompt_query_key=str(prompt_key),
        query_probabilities=dict(branch_probabilities),
        scene_variant=str(scene_variant),
        scene_probabilities=dict(scene_probabilities),
        dataset=dict(dataset),
        count_probabilities=dict(count_probabilities),
        prompt_slots={},
        keyed_annotation=bool(keyed_annotation),
    )


__all__ = ["build_count_request"]
