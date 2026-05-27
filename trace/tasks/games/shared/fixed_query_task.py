"""Helpers for exposing one games scene/query contract as a narrow task id."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from ....core.seed import spawn_rng
from ...base import TaskOutput
from ...shared.fixed_query import force_query_id_params, rewrite_public_query_output as _rewrite_public_query_output


def forced_query_params(params: Mapping[str, Any], *, query_id: str) -> Dict[str, Any]:
    """Return params that force one source query id in a shared scene renderer."""

    return force_query_id_params(params, query_id=str(query_id))


def rewrite_public_query_output(
    output: TaskOutput,
    *,
    query_id: str,
    query_id_probabilities: Mapping[str, float] | None = None,
) -> TaskOutput:
    """Rewrite generated output so the public task has no semantic query id."""

    query_id_text = str(query_id)
    query_probabilities = None
    if query_id_probabilities is not None:
        query_probabilities = {
            str(key): float(value)
            for key, value in query_id_probabilities.items()
        }
    return _rewrite_public_query_output(
        output,
        query_id=query_id_text,
        query_id_probabilities=dict(query_probabilities or {query_id_text: 1.0}),
    )


def rewrite_fixed_query_output(
    output: TaskOutput,
    *,
    query_id: str,
    query_id_probabilities: Mapping[str, float] | None = None,
) -> TaskOutput:
    """Rewrite generated output for a task that pins one query id."""

    return rewrite_public_query_output(
        output,
        query_id=str(query_id),
        query_id_probabilities=dict(query_id_probabilities)
        if query_id_probabilities is not None
        else None,
    )


class FixedQueryVariantTaskMixin:
    """Mixin for wrapper tasks that force one source query id."""

    default_dataset_enabled = True
    fixed_query_id: str

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        output = super().generate(  # type: ignore[misc]
            int(instance_seed),
            params=forced_query_params(params, query_id=str(self.fixed_query_id)),
            max_attempts=int(max_attempts),
        )
        return rewrite_fixed_query_output(output, query_id=str(self.fixed_query_id))


class QuerySubsetTaskMixin:
    """Mixin for public tasks that sample a constrained set of internal query ids."""

    default_dataset_enabled = True
    supported_query_ids: Sequence[str]

    def _select_query_id(self, instance_seed: int, params: Mapping[str, Any]) -> tuple[str, Dict[str, float]]:
        supported = tuple(str(value) for value in self.supported_query_ids)
        if not supported:
            raise ValueError("supported_query_ids must contain at least one query id")

        explicit = params.get("query_id")
        if explicit == "default":
            explicit = None
        probabilities = {str(query_id): 1.0 / float(len(supported)) for query_id in supported}
        if explicit is not None:
            query_id = str(explicit)
            if query_id not in supported:
                raise ValueError(f"unsupported query_id={query_id!r}; expected one of {supported}")
            return query_id, {str(item): (1.0 if str(item) == query_id else 0.0) for item in supported}

        sampling_index = params.get("_sample_cursor")
        if sampling_index is not None:
            return str(supported[abs(int(sampling_index)) % len(supported)]), probabilities

        rng = spawn_rng(int(instance_seed), f"{self.task_id}.query_id")
        return str(rng.choice(supported)), probabilities

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, probabilities = self._select_query_id(int(instance_seed), params)
        raw_cursor = params.get("_sample_cursor")
        explicit_query = params.get("query_id")
        output = super().generate(  # type: ignore[misc]
            int(instance_seed),
            params={
                **forced_query_params(params, query_id=str(query_id)),
                **(
                    {
                        "_sample_cursor": abs(int(raw_cursor))
                        // max(1, len(tuple(self.supported_query_ids)))
                    }
                    if raw_cursor is not None and explicit_query in {None, "default"}
                    else {}
                ),
            },
            max_attempts=int(max_attempts),
        )
        return rewrite_public_query_output(
            output,
            query_id=str(query_id),
            query_id_probabilities=probabilities,
        )


__all__ = [
    "FixedQueryVariantTaskMixin",
    "QuerySubsetTaskMixin",
    "forced_query_params",
    "rewrite_fixed_query_output",
    "rewrite_public_query_output",
]
