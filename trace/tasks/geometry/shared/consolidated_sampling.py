"""Sampling helpers for consolidated geometry scene/query variants."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant


def _full_probability_map(supported: Sequence[str], probabilities: Mapping[str, float]) -> Dict[str, float]:
    """Expand one restricted probability map over the full supported domain."""

    positive = {str(key): float(value) for key, value in probabilities.items()}
    return {
        str(key): float(positive.get(str(key), 0.0))
        for key in supported
    }


def resolve_compatible_scene_query_variants(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    supported_scene_variants: Sequence[str],
    supported_query_variants: Sequence[str],
    compatibility: Mapping[str, Sequence[str]],
    scene_sampling_namespace: str,
    query_sampling_namespace: str,
) -> Tuple[str, Dict[str, float], str, Dict[str, float]]:
    """Resolve compatible scene/query variants with chart-like dual axes.

    Policy:
    - explicit `scene_variant` and `query_variant` are both honored when compatible;
    - otherwise the explicit axis is fixed and the other axis is sampled from the
      compatible subset;
    - with neither axis fixed, `query_variant` is balanced first, then one
      compatible `scene_variant` is resolved and balanced within its feasible set.
    """

    scene_supported = [str(value) for value in supported_scene_variants]
    query_supported = [str(value) for value in supported_query_variants]
    compatibility_map = {
        str(scene): tuple(str(query) for query in queries)
        for scene, queries in compatibility.items()
    }
    scene_set = set(scene_supported)
    query_set = set(query_supported)

    explicit_scene = params.get("scene_variant")
    explicit_query = params.get("query_variant", params.get("task_variant"))
    if explicit_scene is not None and str(explicit_scene) not in scene_set:
        raise ValueError(f"unsupported scene_variant: {explicit_scene}")
    if explicit_query is not None and str(explicit_query) not in query_set:
        raise ValueError(f"unsupported query_variant: {explicit_query}")

    if explicit_scene is not None and explicit_query is not None:
        allowed_queries = set(compatibility_map.get(str(explicit_scene), ()))
        if str(explicit_query) not in allowed_queries:
            raise ValueError(
                f"incompatible geometry scene/query combination: {explicit_scene} + {explicit_query}"
            )
        return (
            str(explicit_scene),
            _full_probability_map(scene_supported, {str(explicit_scene): 1.0}),
            str(explicit_query),
            _full_probability_map(query_supported, {str(explicit_query): 1.0}),
        )

    if explicit_query is not None:
        allowed_scenes = [scene for scene in scene_supported if str(explicit_query) in set(compatibility_map.get(scene, ()))]
        selected_scene, restricted_scene_probs = resolve_variant(
            rng,
            params=params,
            gen_defaults=gen_defaults,
            supported_variants=allowed_scenes,
            explicit_key="scene_variant",
            weights_key="scene_variant_weights",
        )
        selected_scene = apply_balanced_variant_sampling(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
            selected_variant=str(selected_scene),
            variant_probabilities=restricted_scene_probs,
            supported_variants=allowed_scenes,
            balance_flag_key="balanced_scene_variant_sampling",
            explicit_key="scene_variant",
            weights_key="scene_variant_weights",
            sampling_namespace=str(scene_sampling_namespace),
        )
        return (
            str(selected_scene),
            _full_probability_map(scene_supported, restricted_scene_probs),
            str(explicit_query),
            _full_probability_map(query_supported, {str(explicit_query): 1.0}),
        )

    selected_query, restricted_query_probs = resolve_variant(
        rng,
        params=params,
        gen_defaults=gen_defaults,
        supported_variants=query_supported,
        explicit_key="query_variant",
        weights_key="query_variant_weights",
    )
    selected_query = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected_query),
        variant_probabilities=restricted_query_probs,
        supported_variants=query_supported,
        balance_flag_key="balanced_query_variant_sampling",
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        sampling_namespace=str(query_sampling_namespace),
    )

    allowed_scenes = [scene for scene in scene_supported if str(selected_query) in set(compatibility_map.get(scene, ()))]
    selected_scene, restricted_scene_probs = resolve_variant(
        rng,
        params=params,
        gen_defaults=gen_defaults,
        supported_variants=allowed_scenes,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
    )
    selected_scene = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected_scene),
        variant_probabilities=restricted_scene_probs,
        supported_variants=allowed_scenes,
        balance_flag_key="balanced_scene_variant_sampling",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        sampling_namespace=str(scene_sampling_namespace),
    )

    return (
        str(selected_scene),
        _full_probability_map(scene_supported, restricted_scene_probs),
        str(selected_query),
        _full_probability_map(query_supported, restricted_query_probs),
    )
