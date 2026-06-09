"""Consolidated geometry comparison task with shape-family scene variants."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.consolidated_source import (
    normalize_source_geometry_output,
    strip_consolidated_params,
    unregister_source_tasks,
)
from ..shared.consolidated_sampling import resolve_compatible_scene_query_ids
from ..shared.fixed_query_task import FixedGeometryQueryTaskMixin
from .angle import GeometryComparisonAngleTask
from .area import GeometryComparisonAreaTask
from .length import GeometryComparisonLengthTask
from .perimeter import GeometryComparisonPerimeterTask
from .shared import COMPARISON_ANSWER_LABEL_POOL

SOURCE_TASK_IDS: Tuple[str, ...] = (
    "source_geometry_comparison_angle",
    "source_geometry_comparison_area",
    "source_geometry_comparison_length",
    "source_geometry_comparison_perimeter",
)
unregister_source_tasks(SOURCE_TASK_IDS)

TASK_ID = "geometry_comparison_value_base"
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("angle", "segment", "rectangle", "triangle")
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "angle_extremum",
    "length_extremum",
    "area_extremum",
    "perimeter_extremum",
)
_SUPPORTED_EXTREMUM_DIRECTIONS: Tuple[str, ...] = ("largest", "smallest")
_COMPATIBILITY: Dict[str, Sequence[str]] = {
    "angle": ("angle_extremum",),
    "segment": ("length_extremum",),
    "rectangle": ("area_extremum", "perimeter_extremum"),
    "triangle": ("area_extremum", "perimeter_extremum"),
}
_SOURCE_BUILDERS: Dict[Tuple[str, str], Tuple[object, Dict[str, Any]]] = {
    ("angle", "angle_extremum"): (GeometryComparisonAngleTask, {}),
    ("segment", "length_extremum"): (GeometryComparisonLengthTask, {}),
    ("rectangle", "area_extremum"): (GeometryComparisonAreaTask, {}),
    ("rectangle", "perimeter_extremum"): (GeometryComparisonPerimeterTask, {}),
    ("triangle", "area_extremum"): (GeometryComparisonAreaTask, {"shape_family": "triangle"}),
    ("triangle", "perimeter_extremum"): (GeometryComparisonPerimeterTask, {"shape_family": "triangle"}),
}
_SOURCE_QUERY_ALIASES: Dict[str, Tuple[str, str]] = {
    "largest_angle": ("angle_extremum", "largest"),
    "smallest_angle": ("angle_extremum", "smallest"),
    "largest_length": ("length_extremum", "largest"),
    "smallest_length": ("length_extremum", "smallest"),
    "largest_area": ("area_extremum", "largest"),
    "smallest_area": ("area_extremum", "smallest"),
    "largest_perimeter": ("perimeter_extremum", "largest"),
    "smallest_perimeter": ("perimeter_extremum", "smallest"),
}


def _inject_balanced_winner_label(
    params: Mapping[str, Any],
    source_params: Dict[str, Any],
    query_id: str,
    *,
    instance_seed: int,
) -> None:
    """Decouple answer-label cycling from the query-id cycle."""

    if "winner_label" in source_params or "winner_label_weights" in source_params:
        return
    sampling_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.winner_label.{query_id}",
    )
    query_index = int(_SUPPORTED_QUERY_IDS.index(str(query_id)))
    explicit_query = "query_id" in params
    if explicit_query:
        label_index = int(sampling_index) % len(COMPARISON_ANSWER_LABEL_POOL)
    else:
        label_index = (int(sampling_index) // len(_SUPPORTED_QUERY_IDS) + int(query_index)) % len(
            COMPARISON_ANSWER_LABEL_POOL
        )
    source_params["winner_label"] = str(COMPARISON_ANSWER_LABEL_POOL[int(label_index)])


def _params_with_source_query_aliases(params: Mapping[str, Any]) -> Dict[str, Any]:
    """Map largest/smallest aliases to canonical quantity query plus direction."""

    alias_params = dict(params)
    explicit_query = alias_params.get("query_id")
    if explicit_query is None:
        return alias_params
    canonical = _SOURCE_QUERY_ALIASES.get(str(explicit_query))
    if canonical is None:
        return alias_params
    query_id, direction = canonical
    explicit_direction = alias_params.get("extremum_direction")
    if explicit_direction is not None and str(explicit_direction) != str(direction):
        raise ValueError(
            f"conflicting extremum_direction={explicit_direction!r} for source query_id={explicit_query!r}"
        )
    alias_params["query_id"] = str(query_id)
    alias_params["extremum_direction"] = str(direction)
    return alias_params


def _uses_uniform_query_cycle(params: Mapping[str, Any], probabilities: Mapping[str, float]) -> bool:
    """Return true when the query axis is using the default balanced cycle."""

    normalized_params = _params_with_source_query_aliases(params)
    if normalized_params.get("query_id") is not None:
        return False
    enabled = bool(
        normalized_params.get(
            "balanced_query_id_sampling",
            group_default(_GEN_DEFAULTS, "balanced_query_id_sampling", True),
        )
    )
    if not enabled:
        return False
    positives = [float(value) for value in probabilities.values() if float(value) > 0.0]
    if len(positives) != len(_SUPPORTED_QUERY_IDS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _params_for_query_occurrence_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Return params with source query aliases applied."""

    cycle_params = _params_with_source_query_aliases(params)
    _ = query_id_probabilities
    return cycle_params


def _resolve_extremum_direction(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id_probabilities: Mapping[str, float],
) -> Tuple[str, Dict[str, float]]:
    """Resolve largest/smallest as a sampled parameter instead of a query id."""

    direction_params = _params_for_query_occurrence_cycle(
        params,
        query_id_probabilities=query_id_probabilities,
    )
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.extremum_direction")
    selected, probabilities = resolve_variant(
        rng,
        params=direction_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=_SUPPORTED_EXTREMUM_DIRECTIONS,
        explicit_key="extremum_direction",
        weights_key="extremum_direction_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=direction_params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=_SUPPORTED_EXTREMUM_DIRECTIONS,
        balance_flag_key="balanced_extremum_direction_sampling",
        explicit_key="extremum_direction",
        weights_key="extremum_direction_weights",
        sampling_namespace=f"{TASK_ID}.extremum_direction",
    )
    return str(selected), dict(probabilities)

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "comparison")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


class GeometryComparisonValueTask:
    """Unified geometry comparison task spanning angle, segment, and polygon-region scenes."""

    task_id = TASK_ID
    domain = "geometry"
    task_group = "comparison"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        rng = spawn_rng(instance_seed, f"{self.task_id}.axes")
        axis_params = _params_with_source_query_aliases(params)
        scene_variant, scene_probs, query_id, query_probs = resolve_compatible_scene_query_ids(
            rng,
            instance_seed=int(instance_seed),
            params=axis_params,
            gen_defaults=_GEN_DEFAULTS,
            supported_scene_variants=_SUPPORTED_SCENE_VARIANTS,
            supported_query_ids=_SUPPORTED_QUERY_IDS,
            compatibility=_COMPATIBILITY,
            scene_sampling_namespace=f"{self.task_id}.scene_variant",
            query_sampling_namespace=f"{self.task_id}.query_id",
        )
        extremum_direction, extremum_probs = _resolve_extremum_direction(
            instance_seed=int(instance_seed),
            params=axis_params,
            query_id_probabilities=query_probs,
        )
        source_task_cls, source_overrides = _SOURCE_BUILDERS[(str(scene_variant), str(query_id))]
        source_task = source_task_cls()
        source_params = strip_consolidated_params(params)
        source_params.update(dict(source_overrides))
        source_params["query_type"] = str(extremum_direction)
        _inject_balanced_winner_label(
            axis_params,
            source_params,
            str(query_id),
            instance_seed=int(instance_seed),
        )
        output = source_task.generate(int(instance_seed), params=source_params, max_attempts=int(max_attempts))
        source_trace = dict(output.trace_payload.get("execution_trace") or {})
        extra_query_params = {
            "extremum_direction": str(extremum_direction),
            "extremum_direction_probabilities": {
                str(key): float(value) for key, value in sorted(extremum_probs.items())
            },
        }
        return normalize_source_geometry_output(
            output,
            scene_variant=str(scene_variant),
            query_id=str(query_id),
            source_task_id=str(source_task.task_id),
            scene_variant_probabilities=scene_probs,
            query_id_probabilities=query_probs,
            source_scene_variant=str(source_trace.get("scene_variant", scene_variant)),
            source_query_id=str(output.query_id),
            extra_query_params=extra_query_params,
        )


@register_task
class GeometryComparisonAngleExtremumLabelTask(FixedGeometryQueryTaskMixin, GeometryComparisonValueTask):
    """Public angle-extremum comparison task."""

    task_id = "task_geometry__graph_paper__angle_extremum_label"
    fixed_query_id = "angle_extremum"
    scene_id = "graph_paper"
    public_scene_id = "graph_paper"
    allowed_scene_variants = ("angle",)


@register_task
class GeometryComparisonLengthExtremumLabelTask(FixedGeometryQueryTaskMixin, GeometryComparisonValueTask):
    """Public length-extremum comparison task."""

    task_id = "task_geometry__graph_paper__length_extremum_label"
    fixed_query_id = "length_extremum"
    scene_id = "graph_paper"
    public_scene_id = "graph_paper"
    allowed_scene_variants = ("segment",)


@register_task
class GeometryComparisonAreaExtremumLabelTask(FixedGeometryQueryTaskMixin, GeometryComparisonValueTask):
    """Public area-extremum comparison task."""

    task_id = "task_geometry__graph_paper__area_extremum_label"
    fixed_query_id = "area_extremum"
    scene_id = "graph_paper"
    public_scene_id = "graph_paper"
    allowed_scene_variants = ("rectangle", "triangle")


@register_task
class GeometryComparisonPerimeterExtremumLabelTask(FixedGeometryQueryTaskMixin, GeometryComparisonValueTask):
    """Public perimeter-extremum comparison task."""

    task_id = "task_geometry__graph_paper__perimeter_extremum_label"
    fixed_query_id = "perimeter_extremum"
    scene_id = "graph_paper"
    public_scene_id = "graph_paper"
    allowed_scene_variants = ("rectangle", "triangle")
