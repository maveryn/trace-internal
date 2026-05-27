"""Helpers for exposing one physics query contract as a public task id."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from ...base import TaskOutput
from ...shared.fixed_query import force_query_variant_params, rewrite_public_query_output


def forced_query_variant_params(params: Mapping[str, Any], *, query_variant: str) -> Dict[str, Any]:
    """Return params that force one internal physics query variant."""

    return force_query_variant_params(params, query_variant=str(query_variant))


def rewrite_physics_query_output(output: TaskOutput, *, query_id: str) -> TaskOutput:
    """Rewrite generated output so a narrowed public task emits the default variant."""

    return rewrite_public_query_output(
        output,
        query_id=str(query_id),
        params_query_variant_probabilities={"default": 1.0},
        preserve_internal_query_variant_as="internal_query_variant",
    )


class FixedPhysicsQueryVariantTaskMixin:
    """Mixin for wrapper tasks that force one query variant in a shared renderer."""

    default_dataset_enabled = True
    fixed_query_variant: str

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        output = super().generate(  # type: ignore[misc]
            int(instance_seed),
            params=forced_query_variant_params(params, query_variant=str(self.fixed_query_variant)),
            max_attempts=int(max_attempts),
        )
        return rewrite_physics_query_output(output, query_id=str(self.fixed_query_variant))


__all__ = [
    "FixedPhysicsQueryVariantTaskMixin",
    "forced_query_variant_params",
    "rewrite_physics_query_output",
]
