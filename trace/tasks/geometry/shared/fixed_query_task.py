"""Helpers for exposing geometry scene/query contracts as narrow task ids."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from ....core.seed import spawn_rng
from ...base import TaskOutput
from ...shared.fixed_query import (
    force_query_variant_params,
    probability_map as _shared_probability_map,
    rewrite_public_query_output,
)


def _probability_map(values: Sequence[str]) -> Dict[str, float]:
    return _shared_probability_map(tuple(str(value) for value in values))


def _variant_sequence(values: Sequence[str], *, field_name: str) -> tuple[str, ...]:
    resolved = tuple(str(value).strip() for value in values if str(value).strip())
    if not resolved:
        raise ValueError(f"{field_name} must contain at least one non-empty value")
    if len(set(resolved)) != len(resolved):
        raise ValueError(f"{field_name} must not contain duplicate values: {resolved!r}")
    return resolved


def select_geometry_query_variant(
    params: Mapping[str, Any],
    *,
    query_variants: Sequence[str],
    task_id: str = "",
    instance_seed: int = 0,
) -> tuple[str, Dict[str, float]]:
    """Select one internal query variant for a merged public geometry task."""

    variants = _variant_sequence(query_variants, field_name="query_variants")
    variant_set = set(variants)
    explicit_value = None
    for key in ("query_variant", "query_id"):
        candidate = params.get(key)
        if candidate is None:
            continue
        if key == "query_variant" and str(candidate) == "default":
            continue
        explicit_value = candidate
        break
    if explicit_value is not None:
        selected = str(explicit_value)
        if selected not in variant_set:
            raise ValueError(
                f"query_variant={selected!r} is not valid for {task_id or 'geometry task'}; "
                f"expected {variants!r}"
            )
        return selected, {selected: 1.0}

    rng = spawn_rng(int(instance_seed), f"{str(task_id)}.fixed_query_variant")
    variant_index = int(rng.randrange(len(variants)))
    selected = str(variants[int(variant_index)])
    return selected, _probability_map(variants)


def forced_geometry_query_params(
    params: Mapping[str, Any],
    *,
    query_variant: str,
    allowed_scene_variants: Sequence[str] = (),
    task_id: str = "",
    instance_seed: int = 0,
) -> Dict[str, Any]:
    """Return params that force one source query variant in a shared renderer."""

    query_text = str(query_variant)
    forced = force_query_variant_params(params, query_variant=query_text)

    allowed_scenes = tuple(str(scene) for scene in allowed_scene_variants if str(scene).strip())
    if not allowed_scenes:
        return forced

    explicit_scene = forced.get("scene_variant")
    if explicit_scene is not None:
        if str(explicit_scene) not in set(allowed_scenes):
            raise ValueError(
                f"scene_variant={explicit_scene!r} is not valid for query_variant={query_text!r}; "
                f"expected one of {allowed_scenes!r}"
            )
        return forced

    rng = spawn_rng(int(instance_seed), f"{str(task_id)}.fixed_scene_variant")
    scene_index = int(rng.randrange(len(allowed_scenes)))
    forced["scene_variant"] = str(allowed_scenes[scene_index])
    return forced


def rewrite_fixed_geometry_query_output(
    output: TaskOutput,
    *,
    query_id: str,
    scene_id: str,
    allowed_scene_variants: Sequence[str] = (),
    query_variant_probabilities: Mapping[str, float] | None = None,
) -> TaskOutput:
    """Rewrite generated output so the public task has no semantic query variant."""

    query_id_text = str(query_id)
    scene_id_text = str(scene_id)
    scene_values = tuple(str(scene) for scene in allowed_scene_variants if str(scene).strip())
    scene_probabilities = _probability_map(scene_values)
    query_probabilities = {
        str(key): float(value)
        for key, value in (
            dict(query_variant_probabilities) if query_variant_probabilities is not None else {query_id_text: 1.0}
        ).items()
    }
    return rewrite_public_query_output(
        output,
        scene_id=scene_id_text,
        query_id=query_id_text,
        include_render_spec=True,
        query_variant_probabilities=dict(query_probabilities),
        variant_probabilities={"default": 1.0},
        scene_variant_probabilities=dict(scene_probabilities) if scene_probabilities else {},
    )


class FixedGeometryQueryTaskMixin:
    """Mixin for wrapper tasks that expose one geometry query as a public task."""

    default_dataset_enabled = True
    fixed_query_variant: str
    public_scene_id: str
    allowed_scene_variants: Sequence[str] = ()

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        forced_params = forced_geometry_query_params(
            params,
            query_variant=str(self.fixed_query_variant),
            allowed_scene_variants=tuple(self.allowed_scene_variants),
            task_id=str(getattr(self, "task_id", "")),
            instance_seed=int(instance_seed),
        )
        output = super().generate(  # type: ignore[misc]
            int(instance_seed),
            params=forced_params,
            max_attempts=int(max_attempts),
        )
        return rewrite_fixed_geometry_query_output(
            output,
            query_id=str(self.fixed_query_variant),
            scene_id=str(self.public_scene_id),
            allowed_scene_variants=tuple(self.allowed_scene_variants),
            query_variant_probabilities={str(self.fixed_query_variant): 1.0},
        )


class MultiFixedGeometryQueryTaskMixin:
    """Mixin for public geometry tasks that sample among equivalent internal queries."""

    default_dataset_enabled = True
    fixed_query_variants: Sequence[str]
    public_scene_id: str
    allowed_scene_variants: Sequence[str] = ()

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_variant, query_probabilities = select_geometry_query_variant(
            params,
            query_variants=tuple(self.fixed_query_variants),
            task_id=str(getattr(self, "task_id", "")),
            instance_seed=int(instance_seed),
        )
        forced_params = forced_geometry_query_params(
            params,
            query_variant=str(query_variant),
            allowed_scene_variants=tuple(self.allowed_scene_variants),
            task_id=str(getattr(self, "task_id", "")),
            instance_seed=int(instance_seed),
        )
        output = super().generate(  # type: ignore[misc]
            int(instance_seed),
            params=forced_params,
            max_attempts=int(max_attempts),
        )
        return rewrite_fixed_geometry_query_output(
            output,
            query_id=str(query_variant),
            scene_id=str(self.public_scene_id),
            allowed_scene_variants=tuple(self.allowed_scene_variants),
            query_variant_probabilities=dict(query_probabilities),
        )


__all__ = [
    "FixedGeometryQueryTaskMixin",
    "MultiFixedGeometryQueryTaskMixin",
    "forced_geometry_query_params",
    "rewrite_fixed_geometry_query_output",
    "select_geometry_query_variant",
]
