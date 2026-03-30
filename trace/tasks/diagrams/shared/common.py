"""Shared diagrams-domain helpers reused across multiple diagram task families."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant


def resolve_diagrams_axis_variant(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    supported_variants: Sequence[str],
    task_id: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    axis_namespace: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one semantic or visual diagrams axis with deterministic balancing."""

    rng = spawn_rng(int(instance_seed), f"{task_id}.{axis_namespace}")
    selected_variant, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=gen_defaults,
        supported_variants=[str(item) for item in supported_variants],
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
    )
    balanced = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected_variant),
        variant_probabilities=probabilities,
        supported_variants=[str(item) for item in supported_variants],
        balance_flag_key=str(balance_flag_key),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        sampling_namespace=f"{task_id}:{axis_namespace}",
    )
    return str(balanced), {str(key): float(value) for key, value in probabilities.items()}


def projected_diagram_bbox_evidence(
    bbox_map: Mapping[str, Sequence[float]],
    item_ids: Sequence[str],
) -> Dict[str, Any]:
    """Project ordered diagram ids into prompt-facing `bbox_set` evidence."""

    return {
        "bbox_set": [
            list(bbox_map[str(item_id)])
            for item_id in [str(item) for item in item_ids]
            if str(item_id) in bbox_map
        ]
    }


__all__ = [
    "projected_diagram_bbox_evidence",
    "resolve_diagrams_axis_variant",
]
