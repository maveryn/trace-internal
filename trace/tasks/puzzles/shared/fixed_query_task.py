"""Helpers for exposing one puzzle query contract as a narrow public task id."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from ...base import TaskOutput
from ...shared.fixed_query import force_query_id_params, rewrite_public_query_output


def forced_puzzle_query_params(params: Mapping[str, Any], *, query_id: str) -> Dict[str, Any]:
    """Return params that force one internal puzzle query id."""

    return force_query_id_params(params, query_id=str(query_id))


def rewrite_fixed_puzzle_query_output(output: TaskOutput, *, query_id: str, scene_id: str = "") -> TaskOutput:
    """Rewrite generated output so a public puzzle task has one default variant."""

    query_id_text = str(query_id)
    return rewrite_public_query_output(
        output,
        query_id=query_id_text,
        scene_id=str(scene_id) if str(scene_id).strip() else None,
        include_render_spec=True,
        query_id_probabilities={"default": 1.0},
        preserve_internal_query_id_as="internal_query_id",
    )


class FixedPuzzleQueryVariantTaskMixin:
    """Mixin for wrapper tasks that force one source puzzle query id."""

    default_dataset_enabled = True
    fixed_query_id: str
    public_scene_id: str = ""

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        output = super().generate(  # type: ignore[misc]
            int(instance_seed),
            params=forced_puzzle_query_params(params, query_id=str(self.fixed_query_id)),
            max_attempts=int(max_attempts),
        )
        return rewrite_fixed_puzzle_query_output(
            output,
            query_id=str(self.fixed_query_id),
            scene_id=str(self.public_scene_id),
        )


__all__ = [
    "FixedPuzzleQueryVariantTaskMixin",
    "forced_puzzle_query_params",
    "rewrite_fixed_puzzle_query_output",
]
