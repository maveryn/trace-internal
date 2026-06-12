"""Public cell-board puzzle wrappers backed by internal tile generators."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Mapping, Sequence, Type

from trace.core.seed import spawn_rng
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import rewrite_public_query_output
from . import attribute_count as _attribute_count_tasks
from .count_color_components import TileColorComponentsTask
from .count_largest_component_size import TileLargestComponentSizeTask
from .path_reachable_target_count import TileReachableTargetCountTask
from .path_shortest_path import TileShortestPathTask
from .reachability_region_size import TileRegionSizeTask
from .relation_min_distance import TileMinDistanceTask
from .symmetry_violation_count import TileSymmetryViolationCountTask


_WRAPPER_VERSION = "cell_board_query_wrapper_v0"
_SCENE_ID = "cell_board"
_TileQuerySpec = tuple[str, Type, str]


def _query_specs(values: Sequence[_TileQuerySpec]) -> tuple[_TileQuerySpec, ...]:
    specs = tuple(values)
    if not specs:
        raise ValueError("cell-board public task must define at least one query")
    query_ids = [str(spec[0]) for spec in specs]
    if len(set(query_ids)) != len(query_ids):
        raise ValueError(f"duplicate cell-board query ids: {query_ids!r}")
    return specs


def _query_probability_map(specs: Sequence[_TileQuerySpec]) -> Dict[str, float]:
    resolved = _query_specs(specs)
    weight = 1.0 / float(len(resolved))
    return {str(query_id): float(weight) for query_id, _task_cls, _source_variant in resolved}


def _has_explicit_query(params: Mapping[str, Any]) -> bool:
    """Return whether caller explicitly pinned a cell-board query branch."""

    candidate = params.get("query_id")
    if candidate is not None and str(candidate) != "default":
        return True
    return False


def _select_query_spec(
    *,
    params: Mapping[str, Any],
    task_id: str,
    query_specs: Sequence[_TileQuerySpec],
    instance_seed: int,
) -> tuple[_TileQuerySpec, Dict[str, float]]:
    specs = _query_specs(query_specs)
    by_query_id = {
        str(query_id): (query_id, task_cls, source_variant)
        for query_id, task_cls, source_variant in specs
    }
    by_source_variant = {
        str(source_variant): (query_id, task_cls, source_variant)
        for query_id, task_cls, source_variant in specs
    }

    explicit = None
    for key in ("query_id", "query_variant"):
        candidate = params.get(key)
        if candidate is None:
            continue
        if str(candidate) == "default":
            continue
        explicit = str(candidate)
        break

    if explicit is not None:
        spec = by_query_id.get(explicit) or by_source_variant.get(explicit)
        if spec is None:
            expected = sorted(set(by_query_id) | set(by_source_variant))
            raise ValueError(f"unsupported query for {task_id}: {explicit!r}; expected one of {expected!r}")
        return spec, {str(spec[0]): 1.0}

    rng = spawn_rng(int(instance_seed), f"{task_id}.cell_board_query")
    selected_index = int(rng.randrange(len(specs)))
    return specs[int(selected_index)], _query_probability_map(specs)


def _rewrite_fixed_tile_output(
    output: TaskOutput,
    *,
    public_task_id: str,
    query_id: str,
    source_domain: str,
    source_task_id: str,
    source_scene_id: str,
    query_id_probabilities: Mapping[str, float] | None = None,
) -> TaskOutput:
    """Rewrite an internal Tile output to a narrow public task contract."""

    query_id_text = str(query_id)
    query_probabilities = {
        str(key): float(value)
        for key, value in (
            dict(query_id_probabilities) if query_id_probabilities is not None else {query_id_text: 1.0}
        ).items()
    }

    versions = dict(output.task_versions)
    versions["cell_board_query_wrapper_version"] = _WRAPPER_VERSION
    rewritten = rewrite_public_query_output(
        output,
        scene_id=_SCENE_ID,
        query_id=query_id_text,
        include_render_spec=True,
        query_id_probabilities=dict(query_probabilities),
        preserve_internal_query_id_as="internal_query_id",
        extra_fields={
            "public_task_id": str(public_task_id),
            "source_task_id": str(source_task_id),
            "source_scene_id": str(source_scene_id),
        },
        prompt_metadata={
            "prompt_domain": str(source_domain),
            "prompt_scene_id": str(source_scene_id),
        },
    )
    return replace(
        rewritten,
        task_versions=versions,
    )


class _CellBoardQueryTask:
    """Shared implementation for public cell-board puzzle query tasks."""

    domain = "puzzles"
    scene_id = "cell_board"
    query_specs: Sequence[_TileQuerySpec]

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_spec, query_probabilities = _select_query_spec(
            params=params,
            task_id=str(self.task_id),
            query_specs=tuple(self.query_specs),
            instance_seed=int(instance_seed),
        )
        query_id, source_task_cls, source_variant = query_spec
        source_params = dict(params)
        source_params["query_id"] = str(source_variant)
        source_task = source_task_cls()
        output = source_task.generate(
            int(instance_seed),
            params=source_params,
            max_attempts=int(max_attempts),
        )
        return _rewrite_fixed_tile_output(
            output,
            public_task_id=str(self.task_id),
            query_id=str(query_id),
            source_domain=str(getattr(source_task, "domain")),
            source_task_id=str(getattr(source_task, "task_id")),
            source_scene_id=str(getattr(source_task, "scene_id")),
            query_id_probabilities=query_probabilities,
        )


@register_task
class TileColorComponentCountPublicTask(_CellBoardQueryTask):
    """Count connected components for one queried color."""

    task_id = "task_puzzles__cell_board__color_component_count"
    query_specs = (("color_components", TileColorComponentsTask, "color_components"),)


@register_task
class TileLargestComponentSizePublicTask(_CellBoardQueryTask):
    """Find the largest connected component size for one queried color."""

    task_id = "task_puzzles__cell_board__largest_component_size"
    query_specs = (("largest_component_size", TileLargestComponentSizeTask, "largest_component_size"),)


@register_task
class TileReachableRegionSizePublicTask(_CellBoardQueryTask):
    """Count cells reachable from the marked start."""

    task_id = "task_puzzles__cell_board__reachable_region_size"
    query_specs = (("region_size", TileRegionSizeTask, "region_size"),)


@register_task
class TileReachableTargetCountPublicTask(_CellBoardQueryTask):
    """Count reachable or unreachable target cells from the marked start."""

    task_id = "task_puzzles__cell_board__reachable_target_count"
    query_specs = (
        ("reachable_target_count", TileReachableTargetCountTask, "reachable_target_count"),
        ("unreachable_target_count", TileReachableTargetCountTask, "unreachable_target_count"),
    )


@register_task
class TileShortestPathLengthPublicTask(_CellBoardQueryTask):
    """Find the shortest path length between marked cells."""

    task_id = "task_puzzles__cell_board__shortest_path_length_value"
    query_specs = (("shortest_path", TileShortestPathTask, "shortest_path"),)


@register_task
class TileMinimumColorSetDistancePublicTask(_CellBoardQueryTask):
    """Find the minimum distance between two queried color sets."""

    task_id = "task_puzzles__cell_board__minimum_color_set_distance_value"
    query_specs = (("min_distance", TileMinDistanceTask, "min_distance"),)


@register_task
class TileSymmetryViolationCountPublicTask(_CellBoardQueryTask):
    """Count cells that violate a mirror-symmetry rule."""

    task_id = "task_puzzles__cell_board__symmetry_violation_count"
    query_specs = (("symmetry_violation_count", TileSymmetryViolationCountTask, "symmetry_violation_count"),)


__all__ = [
    "TileColorComponentCountPublicTask",
    "TileLargestComponentSizePublicTask",
    "TileMinimumColorSetDistancePublicTask",
    "TileReachableRegionSizePublicTask",
    "TileReachableTargetCountPublicTask",
    "TileSymmetryViolationCountPublicTask",
    "TileShortestPathLengthPublicTask",
]
