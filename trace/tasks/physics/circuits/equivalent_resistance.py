"""Physics circuits task for equivalent-resistance reasoning from resistor diagrams."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from itertools import combinations_with_replacement, product
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.render_variation import resolve_render_int
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.circuit_scene import RenderedCircuitScene, render_resistor_network_scene
from ..shared.complexity import build_physics_circuit_resistance_complexity
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.fixed_query_task import FixedPhysicsQueryVariantTaskMixin
from ..shared.style import SUPPORTED_PHYSICS_COLOR_NAMES
from ..shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_ID = "physics_circuits_resistance_family"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "parallel",
    "simple_series_parallel",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "total_resistance",
    "missing_resistor_value",
)
COMPATIBILITY: Dict[str, Sequence[str]] = {
    "parallel": SUPPORTED_QUERY_IDS,
    "simple_series_parallel": SUPPORTED_QUERY_IDS,
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for resistor-network scenes."""

    canvas_width: int = 940
    canvas_height: int = 560
    terminal_left_x_px: int = 104
    terminal_radius_px: int = 12
    terminal_font_size_px: int = 24
    wire_width_px: int = 5
    resistor_box_width_px: int = 96
    resistor_box_height_px: int = 46
    resistor_font_size_px: int = 24
    label_stroke_width_px: int = 3
    parallel_rail_left_x_px: int = 268
    parallel_branch_top_y_px: int = 190
    parallel_branch_bottom_y_px: int = 430
    series_parallel_branch_left_x_px: int = 360
    resistor_value_min: int = 1
    resistor_value_max: int = 12
    total_resistance_target_answer_support: Tuple[int, ...] = tuple(range(1, 19))
    parallel_target_answer_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)
    simple_series_parallel_target_answer_support: Tuple[int, ...] = tuple(range(2, 19))
    missing_resistor_value_support: Tuple[int, ...] = tuple(range(1, 13))
    pair_scene_width_px: int = 400
    pair_scene_height_px: int = 420
    pair_origin_top_y_px: int = 70
    pair_left_origin_x_px: int = 24
    pair_right_origin_x_px: int = 516
    pair_terminal_left_x_px: int = 54
    pair_parallel_rail_left_x_px: int = 132
    pair_parallel_branch_top_y_px: int = 146
    pair_parallel_branch_bottom_y_px: int = 306
    pair_series_parallel_branch_left_x_px: int = 152
    pair_equals_font_size_px: int = 48
    pair_resistor_box_width_px: int = 56
    pair_resistor_box_height_px: int = 34
    pair_resistor_font_size_px: int = 18
    parallel_total_branch_count_options: Tuple[int, ...] = (4, 5)
    series_parallel_total_count_pairs: Tuple[Tuple[int, int], ...] = ((1, 4), (2, 3), (2, 4))
    parallel_missing_left_branch_count_options: Tuple[int, ...] = (3, 4)
    parallel_missing_right_branch_count_options: Tuple[int, ...] = (3, 4)
    series_parallel_missing_left_count_pairs: Tuple[Tuple[int, int], ...] = ((1, 3),)
    series_parallel_missing_right_count_pairs: Tuple[Tuple[int, int], ...] = ((1, 3),)
    compound_parallel_block_count_options: Tuple[int, ...] = (1, 2, 3)
    compound_missing_parallel_block_count_options: Tuple[int, ...] = (2, 3)
    compound_parallel_branch_count_options: Tuple[int, ...] = (2, 3)
    balanced_compound_block_count_sampling: bool = True


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved scene/task axes and answer support for one instance."""

    scene_variant: str
    query_id: str
    accent_color_name: str
    target_answer: int
    target_answer_support: Tuple[int, ...]
    scene_variant_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _CircuitLayout:
    """One sampled resistor network satisfying the requested total."""

    scene_variant: str
    series_values: Tuple[int, ...]
    parallel_values: Tuple[int, ...]
    target_answer: int
    series_parallel_orientation: str | None
    parallel_blocks: Tuple[Tuple[int, ...], ...] = tuple()
    inter_block_series_values: Tuple[int, ...] = tuple()
    outer_series_values: Tuple[int, int] = (0, 0)


@dataclass(frozen=True)
class _MissingCircuitPairLayout:
    """One paired-circuit scene with a missing resistor on the left circuit."""

    scene_variant: str
    left_series_values: Tuple[int, ...]
    left_parallel_values: Tuple[int, ...]
    left_orientation: str | None
    right_series_values: Tuple[int, ...]
    right_parallel_values: Tuple[int, ...]
    right_orientation: str | None
    missing_resistor_index: int
    missing_component_group: str
    target_answer: int
    paired_total_resistance: int
    left_parallel_blocks: Tuple[Tuple[int, ...], ...] = tuple()
    left_inter_block_series_values: Tuple[int, ...] = tuple()
    left_outer_series_values: Tuple[int, int] = (0, 0)
    right_parallel_blocks: Tuple[Tuple[int, ...], ...] = tuple()
    right_inter_block_series_values: Tuple[int, ...] = tuple()
    right_outer_series_values: Tuple[int, int] = (0, 0)


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "circuits")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="circuits", apply_prob=0.5)


def _secondary_axis_params(params: Mapping[str, Any]) -> Mapping[str, Any]:
    """No-op hook for axis-local balancing call sites."""

    return params


def _resolve_int_options(params: Mapping[str, Any], *, key: str, fallback: Sequence[int]) -> Tuple[int, ...]:
    """Resolve a positive integer option list from task params/config defaults."""

    raw = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), fallback))
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        raise ValueError(f"{key} must be a sequence of positive integers")
    values = tuple(int(value) for value in raw)
    if not values or any(int(value) < 1 for value in values):
        raise ValueError(f"{key} must contain at least one positive integer")
    return tuple(dict.fromkeys(values))


def _resolve_count_pairs(
    params: Mapping[str, Any],
    *,
    key: str,
    fallback: Sequence[Tuple[int, int]],
) -> Tuple[Tuple[int, int], ...]:
    """Resolve `(series_count, parallel_count)` options from params/config."""

    raw = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), fallback))
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        raise ValueError(f"{key} must be a sequence of two-integer pairs")
    pairs: List[Tuple[int, int]] = []
    for item in raw:
        if isinstance(item, (str, bytes)) or not isinstance(item, Sequence) or len(item) != 2:
            raise ValueError(f"{key} entries must be two-integer pairs")
        series_count, parallel_count = int(item[0]), int(item[1])
        if int(series_count) < 0 or int(parallel_count) < 1:
            raise ValueError(f"{key} entries must have series_count >= 0 and parallel_count >= 1")
        pairs.append((int(series_count), int(parallel_count)))
    if not pairs:
        raise ValueError(f"{key} must contain at least one count pair")
    return tuple(dict.fromkeys(pairs))


def _parallel_total_branch_count_options(params: Mapping[str, Any]) -> Tuple[int, ...]:
    return _resolve_int_options(
        params,
        key="parallel_total_branch_count_options",
        fallback=_DEFAULTS.parallel_total_branch_count_options,
    )


def _series_parallel_total_count_pairs(params: Mapping[str, Any]) -> Tuple[Tuple[int, int], ...]:
    return _resolve_count_pairs(
        params,
        key="series_parallel_total_count_pairs",
        fallback=_DEFAULTS.series_parallel_total_count_pairs,
    )


def _parallel_missing_left_branch_count_options(params: Mapping[str, Any]) -> Tuple[int, ...]:
    return _resolve_int_options(
        params,
        key="parallel_missing_left_branch_count_options",
        fallback=_DEFAULTS.parallel_missing_left_branch_count_options,
    )


def _parallel_missing_right_branch_count_options(params: Mapping[str, Any]) -> Tuple[int, ...]:
    return _resolve_int_options(
        params,
        key="parallel_missing_right_branch_count_options",
        fallback=_DEFAULTS.parallel_missing_right_branch_count_options,
    )


def _series_parallel_missing_left_count_pairs(params: Mapping[str, Any]) -> Tuple[Tuple[int, int], ...]:
    pairs = _resolve_count_pairs(
        params,
        key="series_parallel_missing_left_count_pairs",
        fallback=_DEFAULTS.series_parallel_missing_left_count_pairs,
    )
    if any(series_count != 1 for series_count, _ in pairs):
        raise ValueError("series_parallel_missing_left_count_pairs currently require series_count == 1")
    return pairs


def _series_parallel_missing_right_count_pairs(params: Mapping[str, Any]) -> Tuple[Tuple[int, int], ...]:
    return _resolve_count_pairs(
        params,
        key="series_parallel_missing_right_count_pairs",
        fallback=_DEFAULTS.series_parallel_missing_right_count_pairs,
    )


def _compound_parallel_block_count_options(params: Mapping[str, Any]) -> Tuple[int, ...]:
    return _resolve_int_options(
        params,
        key="compound_parallel_block_count_options",
        fallback=_DEFAULTS.compound_parallel_block_count_options,
    )


def _compound_missing_parallel_block_count_options(params: Mapping[str, Any]) -> Tuple[int, ...]:
    return _resolve_int_options(
        params,
        key="compound_missing_parallel_block_count_options",
        fallback=_DEFAULTS.compound_missing_parallel_block_count_options,
    )


def _compound_parallel_branch_count_options(params: Mapping[str, Any]) -> Tuple[int, ...]:
    return _resolve_int_options(
        params,
        key="compound_parallel_branch_count_options",
        fallback=_DEFAULTS.compound_parallel_branch_count_options,
    )


def _select_compound_block_count(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    available_block_counts: Sequence[int],
) -> int:
    """Select a compound block count with the same seeded sampler used in builds."""

    available = tuple(int(value) for value in available_block_counts)
    if not available:
        raise ValueError("available_block_counts must not be empty")
    enabled = bool(
        params.get(
            "balanced_compound_block_count_sampling",
            group_default(
                _GEN_DEFAULTS,
                "balanced_compound_block_count_sampling",
                _DEFAULTS.balanced_compound_block_count_sampling,
            ),
        )
    )
    if not bool(enabled):
        return int(available[int(rng.randrange(len(available)))])
    return int(available[abs(int(instance_seed)) % len(available)])


def _target_support_key(*, scene_variant: str, query_id: str) -> str:
    """Return the config support key for one scene variant."""

    if str(query_id) == "missing_resistor_value":
        return "missing_resistor_value_support"
    return {
        "parallel": "parallel_target_answer_support",
        "simple_series_parallel": "simple_series_parallel_target_answer_support",
    }[str(scene_variant)]


def _resolve_target_answer(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    scene_variant: str,
    query_id: str,
) -> Tuple[int, Tuple[int, ...], Dict[str, float]]:
    """Resolve the sampled target resistance support for one scene family."""

    support_key = _target_support_key(scene_variant=str(scene_variant), query_id=str(query_id))
    fallback = getattr(_DEFAULTS, support_key)
    raw_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=str(support_key),
        fallback=fallback,
    )
    resistor_value_min = int(
        params.get("resistor_value_min", group_default(_GEN_DEFAULTS, "resistor_value_min", _DEFAULTS.resistor_value_min))
    )
    resistor_value_max = int(
        params.get("resistor_value_max", group_default(_GEN_DEFAULTS, "resistor_value_max", _DEFAULTS.resistor_value_max))
    )
    feasible_support = _feasible_target_support(
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        raw_support=raw_support,
        resistor_value_min=int(resistor_value_min),
        resistor_value_max=int(resistor_value_max),
        params=params,
    )
    if not feasible_support:
        raise ValueError(f"no feasible target_answer values remain for {scene_variant}/{query_id}")
    resolved_params = dict(params)
    resolved_params[str(support_key)] = list(int(value) for value in feasible_support)
    target_answer, probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=resolved_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(support_key),
        explicit_key="target_answer",
        fallback_support=feasible_support,
        namespace=f"{TASK_ID}.target_answer.{str(scene_variant)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    return int(target_answer), tuple(int(value) for value in feasible_support), dict(probabilities)


@lru_cache(maxsize=None)
def _is_feasible_target_answer(
    *,
    scene_variant: str,
    query_id: str,
    target_answer: int,
    resistor_value_min: int,
    resistor_value_max: int,
    parallel_total_branch_count_options: Tuple[int, ...],
    series_parallel_total_count_pairs: Tuple[Tuple[int, int], ...],
    parallel_missing_left_branch_count_options: Tuple[int, ...],
    parallel_missing_right_branch_count_options: Tuple[int, ...],
    series_parallel_missing_left_count_pairs: Tuple[Tuple[int, int], ...],
    series_parallel_missing_right_count_pairs: Tuple[Tuple[int, int], ...],
    compound_parallel_block_count_options: Tuple[int, ...],
    compound_missing_parallel_block_count_options: Tuple[int, ...],
    compound_parallel_branch_count_options: Tuple[int, ...],
) -> bool:
    """Return whether one scene/query pair can realize the requested target answer."""

    if str(query_id) == "missing_resistor_value":
        if str(scene_variant) == "parallel":
            return bool(
                _parallel_missing_pair_candidates(
                    target_answer=int(target_answer),
                    resistor_value_min=int(resistor_value_min),
                    resistor_value_max=int(resistor_value_max),
                    left_branch_count_options=parallel_missing_left_branch_count_options,
                    right_branch_count_options=parallel_missing_right_branch_count_options,
                )
            )
        return bool(
            _compound_missing_pair_candidates(
                target_answer=int(target_answer),
                resistor_value_min=int(resistor_value_min),
                resistor_value_max=int(resistor_value_max),
                block_count_options=compound_missing_parallel_block_count_options,
                branch_count_options=compound_parallel_branch_count_options,
                max_candidates=1,
            )
        )

    if str(scene_variant) == "parallel":
        return any(
            bool(
                _parallel_bank_candidates_for_total(
                    target_answer=int(target_answer),
                    resistor_count=int(branch_count),
                    resistor_value_min=int(resistor_value_min),
                    resistor_value_max=int(resistor_value_max),
                )
            )
            for branch_count in parallel_total_branch_count_options
        )
    return bool(
        _compound_candidates_for_total(
            target_answer=int(target_answer),
            resistor_value_min=int(resistor_value_min),
            resistor_value_max=int(resistor_value_max),
            block_count_options=compound_parallel_block_count_options,
            branch_count_options=compound_parallel_branch_count_options,
            max_candidates=1,
        )
    )


def _feasible_target_support(
    *,
    scene_variant: str,
    query_id: str,
    raw_support: Sequence[int],
    resistor_value_min: int,
    resistor_value_max: int,
    params: Mapping[str, Any],
) -> Tuple[int, ...]:
    """Return the subset of one configured support that is constructively feasible."""

    feasible: List[int] = []
    for raw_value in raw_support:
        target_answer = int(raw_value)
        if _is_feasible_target_answer(
            scene_variant=str(scene_variant),
            query_id=str(query_id),
            target_answer=int(target_answer),
            resistor_value_min=int(resistor_value_min),
            resistor_value_max=int(resistor_value_max),
            parallel_total_branch_count_options=_parallel_total_branch_count_options(params),
            series_parallel_total_count_pairs=_series_parallel_total_count_pairs(params),
            parallel_missing_left_branch_count_options=_parallel_missing_left_branch_count_options(params),
            parallel_missing_right_branch_count_options=_parallel_missing_right_branch_count_options(params),
            series_parallel_missing_left_count_pairs=_series_parallel_missing_left_count_pairs(params),
            series_parallel_missing_right_count_pairs=_series_parallel_missing_right_count_pairs(params),
            compound_parallel_block_count_options=_compound_parallel_block_count_options(params),
            compound_missing_parallel_block_count_options=_compound_missing_parallel_block_count_options(params),
            compound_parallel_branch_count_options=_compound_parallel_branch_count_options(params),
        ):
            feasible.append(int(target_answer))
    return tuple(int(value) for value in feasible)


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve one compatible scene/query-id pair plus answer support."""

    axis_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.axes")
    secondary_params = _secondary_axis_params(params)
    query_id, task_probs = _resolve_query_id(
        axis_rng,
        instance_seed=int(instance_seed),
        params=params,
    )
    explicit_scene = params.get("scene_variant")
    if str(query_id) == "total_resistance" and explicit_scene is None:
        target_answer, target_answer_support, target_answer_probabilities = _resolve_total_resistance_target_answer(
            instance_seed=int(instance_seed),
            params=secondary_params,
        )
        scene_variant, scene_probs = _resolve_scene_variant_for_total_resistance(
            axis_rng,
            instance_seed=int(instance_seed),
            params=secondary_params,
            target_answer=int(target_answer),
        )
    else:
        scene_variant, scene_probs = _resolve_scene_variant(
            axis_rng,
            instance_seed=int(instance_seed),
            params=secondary_params,
            query_id=str(query_id),
        )
        target_answer, target_answer_support, target_answer_probabilities = _resolve_target_answer(
            instance_seed=int(instance_seed),
            params=secondary_params,
            scene_variant=str(scene_variant),
            query_id=str(query_id),
        )
    color_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.accent_color_name")
    accent_color_name, accent_color_name_probabilities = resolve_variant(
        color_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_PHYSICS_COLOR_NAMES,
        explicit_key="accent_color_name",
        weights_key="accent_color_name_weights",
    )
    accent_color_name = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(accent_color_name),
        variant_probabilities=accent_color_name_probabilities,
        supported_variants=SUPPORTED_PHYSICS_COLOR_NAMES,
        balance_flag_key="balanced_accent_color_name_sampling",
        explicit_key="accent_color_name",
        weights_key="accent_color_name_weights",
        sampling_namespace=f"{TASK_ID}.accent_color_name",
    )
    return _ResolvedAxes(
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        accent_color_name=str(accent_color_name),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        scene_variant_probabilities=dict(scene_probs),
        query_id_probabilities=dict(task_probs),
        accent_color_name_probabilities=dict(accent_color_name_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _resolve_query_id(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve the public query id, respecting any explicit scene compatibility."""

    task_supported = [str(value) for value in SUPPORTED_QUERY_IDS]
    compatibility_map = {
        str(scene): tuple(str(query) for query in queries)
        for scene, queries in COMPATIBILITY.items()
    }
    task_set = set(task_supported)

    query_id = params.get("query_id")
    explicit_task = params.get("query_id")
    if query_id is not None:
        if str(query_id) not in task_set:
            raise ValueError(f"unsupported query_id: {query_id}")
        if explicit_task is not None and str(explicit_task) != str(query_id):
            raise ValueError("circuit resistance family query_id must match query_id")
        params = dict(params)
        params["query_id"] = str(query_id)
        explicit_task = str(query_id)
    if explicit_task is not None and str(explicit_task) not in task_set:
        raise ValueError(f"unsupported query_id: {explicit_task}")
    explicit_scene = params.get("scene_variant")
    if explicit_scene is not None:
        if str(explicit_scene) not in set(str(value) for value in SUPPORTED_SCENE_VARIANTS):
            raise ValueError(f"unsupported scene_variant: {explicit_scene}")
        allowed_tasks = list(compatibility_map.get(str(explicit_scene), ()))
        selected_task, restricted_task_probs = resolve_variant(
            rng,
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            supported_variants=allowed_tasks,
            explicit_key="query_id",
            weights_key="query_id_weights",
        )
        selected_task = apply_balanced_variant_sampling(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            selected_variant=str(selected_task),
            variant_probabilities=restricted_task_probs,
            supported_variants=allowed_tasks,
            balance_flag_key="balanced_query_id_sampling",
            explicit_key="query_id",
            weights_key="query_id_weights",
            sampling_namespace=f"{TASK_ID}.query_id",
        )
        return str(selected_task), {
            query_id: float(restricted_task_probs.get(query_id, 0.0)) for query_id in task_supported
        }

    selected_task, restricted_task_probs = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=task_supported,
        explicit_key="query_id",
        weights_key="query_id_weights",
    )
    selected_task = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected_task),
        variant_probabilities=restricted_task_probs,
        supported_variants=task_supported,
        balance_flag_key="balanced_query_id_sampling",
        explicit_key="query_id",
        weights_key="query_id_weights",
        sampling_namespace=f"{TASK_ID}.query_id",
    )
    return str(selected_task), {
        query_id: float(restricted_task_probs.get(query_id, 0.0)) for query_id in task_supported
    }


def _resolve_scene_variant(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one scene variant after the query id is known."""

    scene_supported = [str(value) for value in SUPPORTED_SCENE_VARIANTS]
    explicit_scene = params.get("scene_variant")
    if explicit_scene is not None:
        if str(explicit_scene) not in set(scene_supported):
            raise ValueError(f"unsupported scene_variant: {explicit_scene}")
        allowed_queries = set(COMPATIBILITY.get(str(explicit_scene), ()))
        if str(query_id) not in allowed_queries:
            raise ValueError(f"incompatible scene/query combination: {explicit_scene} + {query_id}")
        return str(explicit_scene), {scene: (1.0 if scene == str(explicit_scene) else 0.0) for scene in scene_supported}

    allowed_scenes = [
        scene for scene in scene_supported if str(query_id) in set(COMPATIBILITY.get(scene, ()))
    ]
    selected_scene, restricted_scene_probs = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=allowed_scenes,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
    )
    selected_scene = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected_scene),
        variant_probabilities=restricted_scene_probs,
        supported_variants=allowed_scenes,
        balance_flag_key="balanced_scene_variant_sampling",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        sampling_namespace=f"{TASK_ID}.scene_variant.{str(query_id)}",
    )
    return str(selected_scene), {
        scene: float(restricted_scene_probs.get(scene, 0.0)) for scene in scene_supported
    }


def _resolve_total_resistance_target_answer(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[int, Tuple[int, ...], Dict[str, float]]:
    """Resolve the total-resistance target from the query-level feasible support."""

    fallback = getattr(_DEFAULTS, "total_resistance_target_answer_support")
    raw_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="total_resistance_target_answer_support",
        fallback=fallback,
    )
    resistor_value_min = int(
        params.get("resistor_value_min", group_default(_GEN_DEFAULTS, "resistor_value_min", _DEFAULTS.resistor_value_min))
    )
    resistor_value_max = int(
        params.get("resistor_value_max", group_default(_GEN_DEFAULTS, "resistor_value_max", _DEFAULTS.resistor_value_max))
    )
    feasible_support = tuple(
        int(value)
        for value in raw_support
        if any(
            _is_feasible_target_answer(
                scene_variant=str(scene_variant),
                query_id="total_resistance",
                target_answer=int(value),
                resistor_value_min=int(resistor_value_min),
                resistor_value_max=int(resistor_value_max),
                parallel_total_branch_count_options=_parallel_total_branch_count_options(params),
                series_parallel_total_count_pairs=_series_parallel_total_count_pairs(params),
                parallel_missing_left_branch_count_options=_parallel_missing_left_branch_count_options(params),
                parallel_missing_right_branch_count_options=_parallel_missing_right_branch_count_options(params),
                series_parallel_missing_left_count_pairs=_series_parallel_missing_left_count_pairs(params),
                series_parallel_missing_right_count_pairs=_series_parallel_missing_right_count_pairs(params),
                compound_parallel_block_count_options=_compound_parallel_block_count_options(params),
                compound_missing_parallel_block_count_options=_compound_missing_parallel_block_count_options(params),
                compound_parallel_branch_count_options=_compound_parallel_branch_count_options(params),
            )
            for scene_variant in SUPPORTED_SCENE_VARIANTS
        )
    )
    if not feasible_support:
        raise ValueError("no feasible total_resistance target_answer values remain")
    resolved_params = dict(params)
    resolved_params["total_resistance_target_answer_support"] = list(int(value) for value in feasible_support)
    target_answer, probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=resolved_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="total_resistance_target_answer_support",
        explicit_key="target_answer",
        fallback_support=feasible_support,
        namespace=f"{TASK_ID}.target_answer.total_resistance",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    return int(target_answer), tuple(int(value) for value in feasible_support), dict(probabilities)


def _resolve_scene_variant_for_total_resistance(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    target_answer: int,
) -> Tuple[str, Dict[str, float]]:
    """Resolve a total-resistance scene that can realize the chosen answer."""

    resistor_value_min = int(
        params.get("resistor_value_min", group_default(_GEN_DEFAULTS, "resistor_value_min", _DEFAULTS.resistor_value_min))
    )
    resistor_value_max = int(
        params.get("resistor_value_max", group_default(_GEN_DEFAULTS, "resistor_value_max", _DEFAULTS.resistor_value_max))
    )
    allowed_scenes = [
        str(scene_variant)
        for scene_variant in SUPPORTED_SCENE_VARIANTS
        if _is_feasible_target_answer(
            scene_variant=str(scene_variant),
            query_id="total_resistance",
            target_answer=int(target_answer),
            resistor_value_min=int(resistor_value_min),
            resistor_value_max=int(resistor_value_max),
            parallel_total_branch_count_options=_parallel_total_branch_count_options(params),
            series_parallel_total_count_pairs=_series_parallel_total_count_pairs(params),
            parallel_missing_left_branch_count_options=_parallel_missing_left_branch_count_options(params),
            parallel_missing_right_branch_count_options=_parallel_missing_right_branch_count_options(params),
            series_parallel_missing_left_count_pairs=_series_parallel_missing_left_count_pairs(params),
            series_parallel_missing_right_count_pairs=_series_parallel_missing_right_count_pairs(params),
            compound_parallel_block_count_options=_compound_parallel_block_count_options(params),
            compound_missing_parallel_block_count_options=_compound_missing_parallel_block_count_options(params),
            compound_parallel_branch_count_options=_compound_parallel_branch_count_options(params),
        )
    ]
    if not allowed_scenes:
        raise ValueError(f"no scene variants can realize total_resistance target {target_answer}")
    selected_scene, restricted_scene_probs = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=allowed_scenes,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
    )
    selected_scene = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected_scene),
        variant_probabilities=restricted_scene_probs,
        supported_variants=allowed_scenes,
        balance_flag_key="balanced_scene_variant_sampling",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        sampling_namespace=f"{TASK_ID}.scene_variant.total_resistance.{int(target_answer)}",
    )

    scene_supported = [str(value) for value in SUPPORTED_SCENE_VARIANTS]
    return str(selected_scene), {
        scene: float(restricted_scene_probs.get(scene, 0.0)) for scene in scene_supported
    }


def _sorted_int_tuple(*values: int) -> Tuple[int, ...]:
    """Return a canonical sorted integer tuple."""

    return tuple(sorted(int(value) for value in values))


def _parallel_equivalent_fraction(values: Sequence[int]) -> Fraction:
    """Return the exact equivalent resistance of one parallel resistor bank."""

    if not values:
        raise ValueError("parallel equivalent requires at least one resistor")
    reciprocal_sum = sum(Fraction(1, int(value)) for value in values)
    if reciprocal_sum <= 0:
        raise ValueError("parallel equivalent requires a positive reciprocal sum")
    return Fraction(1, 1) / reciprocal_sum


def _equivalent_resistance_fraction(
    *,
    scene_variant: str,
    series_values: Sequence[int],
    parallel_values: Sequence[int],
) -> Fraction:
    """Return the exact equivalent resistance for one supported circuit layout."""

    if str(scene_variant) == "parallel":
        return _parallel_equivalent_fraction(parallel_values)
    return Fraction(sum(int(value) for value in series_values), 1) + _parallel_equivalent_fraction(parallel_values)


def _compound_equivalent_fraction(
    *,
    parallel_blocks: Sequence[Sequence[int]],
    inter_block_series_values: Sequence[int],
    outer_series_values: Sequence[int] = (),
) -> Fraction:
    """Return the exact equivalent resistance of series-connected parallel banks."""

    blocks = tuple(tuple(int(value) for value in block) for block in parallel_blocks)
    gaps = tuple(int(value) for value in inter_block_series_values)
    outer = tuple(int(value) for value in outer_series_values)
    if not blocks:
        raise ValueError("compound circuit requires at least one parallel block")
    if len(gaps) != max(0, len(blocks) - 1):
        raise ValueError("compound circuit gap count must equal block_count - 1")
    if outer and len(outer) != 2:
        raise ValueError("compound circuit outer series count must equal 2")
    total = sum((_parallel_equivalent_fraction(block) for block in blocks), Fraction(0, 1))
    return total + Fraction(sum(int(value) for value in gaps) + sum(int(value) for value in outer), 1)


@lru_cache(maxsize=None)
def _integer_parallel_block_candidates(
    *,
    resistor_value_min: int,
    resistor_value_max: int,
    branch_count_options: Tuple[int, ...],
) -> Tuple[Tuple[int, Tuple[int, ...]], ...]:
    """Return parallel-bank value tuples with integral equivalent resistance."""

    candidates: List[Tuple[int, Tuple[int, ...]]] = []
    for branch_count in branch_count_options:
        if int(branch_count) < 2:
            raise ValueError("compound parallel blocks require at least two branches")
        for values in combinations_with_replacement(
            range(int(resistor_value_min), int(resistor_value_max) + 1),
            int(branch_count),
        ):
            equivalent = _parallel_equivalent_fraction(values)
            if int(equivalent.denominator) != 1:
                continue
            candidates.append((int(equivalent.numerator), tuple(int(value) for value in values)))
    if not candidates:
        raise ValueError("no integral parallel-block candidates remain")
    return tuple(candidates)


def _gap_value_tuples(
    *,
    gap_count: int,
    target_sum: int,
    resistor_value_min: int,
    resistor_value_max: int,
) -> Tuple[Tuple[int, ...], ...]:
    """Enumerate optional inter-block series resistor values for one sum."""

    if int(gap_count) == 0:
        return (tuple(),) if int(target_sum) == 0 else tuple()
    if int(target_sum) < 0:
        return tuple()
    options = (0,) + tuple(range(int(resistor_value_min), int(resistor_value_max) + 1))
    return tuple(
        tuple(int(value) for value in values)
        for values in product(options, repeat=int(gap_count))
        if sum(int(value) for value in values) == int(target_sum)
    )


@lru_cache(maxsize=None)
def _compound_candidates_for_total(
    *,
    target_answer: int,
    resistor_value_min: int,
    resistor_value_max: int,
    block_count_options: Tuple[int, ...],
    branch_count_options: Tuple[int, ...],
    max_candidates: int = 20000,
) -> Tuple[Tuple[Tuple[Tuple[int, ...], ...], Tuple[int, ...], Tuple[int, int]], ...]:
    """Enumerate compound circuits with integral parallel blocks and optional series resistors."""

    block_options = _integer_parallel_block_candidates(
        resistor_value_min=int(resistor_value_min),
        resistor_value_max=int(resistor_value_max),
        branch_count_options=tuple(int(value) for value in branch_count_options),
    )
    candidates: List[Tuple[Tuple[Tuple[int, ...], ...], Tuple[int, ...], Tuple[int, int]]] = []
    seen: set[Tuple[Tuple[Tuple[int, ...], ...], Tuple[int, ...], Tuple[int, int]]] = set()
    block_counts = tuple(int(value) for value in block_count_options if int(value) >= 1)
    per_block_count_limit = max(1, int(max_candidates) // max(1, len(block_counts)))

    class _BlockCountFilled(Exception):
        pass

    for block_count in block_counts:
        if int(block_count) < 1:
            continue
        added_for_block_count = 0
        gap_count = int(block_count) - 1
        try:
            for block_combo in product(block_options, repeat=int(block_count)):
                block_total = sum(int(item[0]) for item in block_combo)
                remaining = int(target_answer) - int(block_total)
                series_tuples = _gap_value_tuples(
                    gap_count=int(gap_count) + 2,
                    target_sum=int(remaining),
                    resistor_value_min=int(resistor_value_min),
                    resistor_value_max=int(resistor_value_max),
                )
                if not series_tuples:
                    continue
                blocks = tuple(tuple(int(value) for value in item[1]) for item in block_combo)
                for series_values in series_tuples:
                    gaps = tuple(int(value) for value in series_values[1:-1])
                    outer = (int(series_values[0]), int(series_values[-1]))
                    candidate = (blocks, gaps, outer)
                    if candidate in seen:
                        continue
                    seen.add(candidate)
                    candidates.append(candidate)
                    added_for_block_count += 1
                    if added_for_block_count >= int(per_block_count_limit):
                        raise _BlockCountFilled
                    if len(candidates) >= int(max_candidates):
                        return tuple(candidates)
        except _BlockCountFilled:
            continue
    return tuple(candidates)


def _compound_missing_resistor_index(
    *,
    parallel_blocks: Sequence[Sequence[int]],
    inter_block_series_values: Sequence[int],
    outer_series_values: Sequence[int] = (),
    missing_gap_index: int,
) -> int:
    """Return the renderer-order resistor index for a missing inter-block series resistor."""

    outer = tuple(int(value) for value in outer_series_values)
    if outer and len(outer) != 2:
        raise ValueError("compound outer series values must contain left and right slots")
    index = 0
    if outer and int(outer[0]) > 0:
        index += 1
    for block_index, block in enumerate(parallel_blocks):
        index += len(block)
        if block_index >= len(inter_block_series_values):
            continue
        if int(block_index) == int(missing_gap_index):
            return int(index + 1)
        if int(inter_block_series_values[block_index]) > 0:
            index += 1
    raise ValueError("missing gap index is out of range")


def _series_chain_candidates_for_total(
    *,
    target_total: int,
    resistor_count: int,
    resistor_value_min: int,
    resistor_value_max: int,
) -> List[Tuple[int, ...]]:
    """Enumerate feasible fixed-length series chains for one target total."""

    candidates: List[Tuple[int, ...]] = []
    if int(resistor_count) == 1:
        if int(resistor_value_min) <= int(target_total) <= int(resistor_value_max):
            return [(int(target_total),)]
        return []
    if int(resistor_count) == 2:
        for first in range(int(resistor_value_min), int(resistor_value_max) + 1):
            second = int(target_total) - int(first)
            if int(first) <= int(second) <= int(resistor_value_max):
                candidates.append(_sorted_int_tuple(int(first), int(second)))
        return candidates
    if int(resistor_count) != 3:
        raise ValueError("series-chain candidates only support counts 1..3")
    for first in range(int(resistor_value_min), int(resistor_value_max) + 1):
        for second in range(int(first), int(resistor_value_max) + 1):
            third = int(target_total) - int(first) - int(second)
            if int(second) <= int(third) <= int(resistor_value_max):
                candidates.append(_sorted_int_tuple(int(first), int(second), int(third)))
    deduped: List[Tuple[int, ...]] = []
    seen: set[Tuple[int, ...]] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        deduped.append(candidate)
    return deduped


def _parallel_bank_candidates_for_total(
    *,
    target_answer: int,
    resistor_count: int,
    resistor_value_min: int,
    resistor_value_max: int,
) -> List[Tuple[int, ...]]:
    """Enumerate feasible fixed-length parallel resistor banks for one target total."""

    from fractions import Fraction

    if int(resistor_count) < 2:
        raise ValueError("parallel banks require at least two resistors")
    values = range(int(resistor_value_min), int(resistor_value_max) + 1)
    candidates: List[Tuple[int, ...]] = []

    def search(prefix: Tuple[int, ...], start_value: int) -> None:
        if len(prefix) == int(resistor_count):
            reciprocal_sum = sum(Fraction(1, int(value)) for value in prefix)
            if reciprocal_sum == Fraction(1, int(target_answer)):
                candidates.append(tuple(int(value) for value in prefix))
            return
        for value in range(int(start_value), int(resistor_value_max) + 1):
            search(prefix + (int(value),), int(value))

    search(tuple(), int(resistor_value_min))
    deduped: List[Tuple[int, ...]] = []
    seen: set[Tuple[int, ...]] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        deduped.append(candidate)
    return deduped


def _series_parallel_candidates_for_total(
    *,
    target_answer: int,
    resistor_value_min: int,
    resistor_value_max: int,
    allowed_count_pairs: Sequence[Tuple[int, int]] = ((1, 3), (2, 2), (2, 3)),
) -> List[Tuple[Tuple[int, ...], Tuple[int, ...]]]:
    """Enumerate feasible series-plus-parallel layouts with at least four resistors."""

    candidates: List[Tuple[Tuple[int, ...], Tuple[int, ...]]] = []
    for series_count, parallel_count in allowed_count_pairs:
        min_series_total = int(series_count) * int(resistor_value_min)
        max_series_total = int(series_count) * int(resistor_value_max)
        for series_total in range(int(min_series_total), int(max_series_total) + 1):
            parallel_target = int(target_answer) - int(series_total)
            if int(parallel_target) < 1:
                continue
            series_candidates = _series_chain_candidates_for_total(
                target_total=int(series_total),
                resistor_count=int(series_count),
                resistor_value_min=int(resistor_value_min),
                resistor_value_max=int(resistor_value_max),
            )
            if not series_candidates:
                continue
            parallel_candidates = _parallel_bank_candidates_for_total(
                target_answer=int(parallel_target),
                resistor_count=int(parallel_count),
                resistor_value_min=int(resistor_value_min),
                resistor_value_max=int(resistor_value_max),
            )
            if not parallel_candidates:
                continue
            for series_values in series_candidates:
                for parallel_values in parallel_candidates:
                    candidates.append(
                        (
                            tuple(int(value) for value in series_values),
                            tuple(int(value) for value in parallel_values),
                        )
                    )
    return candidates


def _sample_layout(
    rng,
    *,
    instance_seed: int,
    scene_variant: str,
    target_answer: int,
    params: Mapping[str, Any],
) -> _CircuitLayout:
    """Sample one resistor network that realizes the requested total."""

    resistor_value_min = int(
        params.get("resistor_value_min", group_default(_GEN_DEFAULTS, "resistor_value_min", _DEFAULTS.resistor_value_min))
    )
    resistor_value_max = int(
        params.get("resistor_value_max", group_default(_GEN_DEFAULTS, "resistor_value_max", _DEFAULTS.resistor_value_max))
    )
    if str(scene_variant) == "parallel":
        branch_counts = list(_parallel_total_branch_count_options(params))
        rng.shuffle(branch_counts)
        candidates: List[Tuple[int, ...]] = []
        for branch_count in branch_counts:
            candidates = _parallel_bank_candidates_for_total(
                target_answer=int(target_answer),
                resistor_count=int(branch_count),
                resistor_value_min=int(resistor_value_min),
                resistor_value_max=int(resistor_value_max),
            )
            if candidates:
                break
        if not candidates:
            raise ValueError(f"no parallel candidates for target {target_answer}")
        chosen = list(candidates[int(rng.randrange(len(candidates)))])
        rng.shuffle(chosen)
        return _CircuitLayout(
            scene_variant=str(scene_variant),
            series_values=tuple(),
            parallel_values=tuple(int(value) for value in chosen),
            target_answer=int(target_answer),
            series_parallel_orientation=None,
        )
    candidates_by_block_count: Dict[int, Tuple[Tuple[Tuple[Tuple[int, ...], ...], Tuple[int, ...], Tuple[int, int]], ...]] = {}
    for block_count in _compound_parallel_block_count_options(params):
        block_count_candidates = _compound_candidates_for_total(
            target_answer=int(target_answer),
            resistor_value_min=int(resistor_value_min),
            resistor_value_max=int(resistor_value_max),
            block_count_options=(int(block_count),),
            branch_count_options=_compound_parallel_branch_count_options(params),
        )
        if block_count_candidates:
            candidates_by_block_count[int(block_count)] = block_count_candidates
    if not candidates_by_block_count:
        raise ValueError(f"no compound series-parallel candidates for target {target_answer}")
    available_block_counts = sorted(candidates_by_block_count)
    chosen_block_count = _select_compound_block_count(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        available_block_counts=available_block_counts,
    )
    block_count_candidates = list(candidates_by_block_count[int(chosen_block_count)])
    candidates_by_outer_mask: Dict[
        Tuple[bool, bool],
        List[Tuple[Tuple[Tuple[int, ...], ...], Tuple[int, ...], Tuple[int, int]]],
    ] = {}
    for candidate in block_count_candidates:
        candidate_outer = candidate[2]
        candidates_by_outer_mask.setdefault(
            (int(candidate_outer[0]) > 0, int(candidate_outer[1]) > 0),
            [],
        ).append(candidate)
    available_outer_masks = sorted(candidates_by_outer_mask)
    chosen_outer_mask = available_outer_masks[int(rng.randrange(len(available_outer_masks)))]
    chosen_blocks, chosen_gaps, chosen_outer = candidates_by_outer_mask[chosen_outer_mask][
        int(rng.randrange(len(candidates_by_outer_mask[chosen_outer_mask])))
    ]
    branch_blocks = [list(block) for block in chosen_blocks]
    for block in branch_blocks:
        rng.shuffle(block)
    series_values = tuple(
        int(value)
        for value in (int(chosen_outer[0]), *tuple(int(value) for value in chosen_gaps), int(chosen_outer[1]))
        if int(value) > 0
    )
    return _CircuitLayout(
        scene_variant=str(scene_variant),
        series_values=series_values,
        parallel_values=tuple(int(value) for block in branch_blocks for value in block),
        target_answer=int(target_answer),
        series_parallel_orientation="compound_parallel_chain",
        parallel_blocks=tuple(tuple(int(value) for value in block) for block in branch_blocks),
        inter_block_series_values=tuple(int(value) for value in chosen_gaps),
        outer_series_values=(int(chosen_outer[0]), int(chosen_outer[1])),
    )


def _parallel_missing_pair_candidates(
    *,
    target_answer: int,
    resistor_value_min: int,
    resistor_value_max: int,
    left_branch_count_options: Sequence[int],
    right_branch_count_options: Sequence[int],
) -> List[Tuple[Tuple[int, ...], Tuple[int, ...]]]:
    """Enumerate feasible paired parallel circuits for the missing-resistor query."""

    candidates: List[Tuple[Tuple[int, ...], Tuple[int, ...]]] = []

    def enumerate_known_values(count: int, start_value: int, prefix: Tuple[int, ...]) -> List[Tuple[int, ...]]:
        if int(count) == 0:
            return [tuple(int(value) for value in prefix)]
        out: List[Tuple[int, ...]] = []
        for value in range(int(start_value), int(resistor_value_max) + 1):
            out.extend(enumerate_known_values(int(count) - 1, int(value), prefix + (int(value),)))
        return out

    for left_branch_count in left_branch_count_options:
        known_count = int(left_branch_count) - 1
        known_candidates = enumerate_known_values(int(known_count), int(resistor_value_min), tuple())
        for known_values in known_candidates:
            total_fraction = Fraction(1, 1) / (
                Fraction(1, int(target_answer)) + sum(Fraction(1, int(value)) for value in known_values)
            )
            if int(total_fraction.denominator) != 1:
                continue
            total_equivalent = int(total_fraction.numerator)
            for right_branch_count in right_branch_count_options:
                right_candidates = _parallel_bank_candidates_for_total(
                    target_answer=int(total_equivalent),
                    resistor_count=int(right_branch_count),
                    resistor_value_min=int(resistor_value_min),
                    resistor_value_max=int(resistor_value_max),
                )
                for right_values in right_candidates:
                    full_left = tuple(sorted(tuple(int(value) for value in known_values) + (int(target_answer),)))
                    if tuple(int(value) for value in right_values) == full_left:
                        continue
                    candidates.append((tuple(int(value) for value in known_values), tuple(int(value) for value in right_values)))
    return candidates


def _simple_series_parallel_missing_pair_candidates(
    *,
    target_answer: int,
    resistor_value_min: int,
    resistor_value_max: int,
    left_count_pairs: Sequence[Tuple[int, int]],
    right_count_pairs: Sequence[Tuple[int, int]],
) -> List[Tuple[Tuple[int, ...], Tuple[int, ...], Tuple[int, ...], Tuple[int, ...], int]]:
    """Enumerate feasible paired mixed circuits with one missing left-series resistor."""

    candidates: List[Tuple[Tuple[int, ...], Tuple[int, ...], Tuple[int, ...], Tuple[int, ...], int]] = []
    for left_series_count, left_parallel_count in left_count_pairs:
        if int(left_series_count) != 1:
            raise ValueError("missing series-parallel left layouts require exactly one missing series resistor")
        for parallel_total in range(1, int(resistor_value_max) + 1):
            left_parallel_candidates = _parallel_bank_candidates_for_total(
                target_answer=int(parallel_total),
                resistor_count=int(left_parallel_count),
                resistor_value_min=int(resistor_value_min),
                resistor_value_max=int(resistor_value_max),
            )
            if not left_parallel_candidates:
                continue
            paired_total = int(target_answer) + int(parallel_total)
            right_candidates = _series_parallel_candidates_for_total(
                target_answer=int(paired_total),
                resistor_value_min=int(resistor_value_min),
                resistor_value_max=int(resistor_value_max),
                allowed_count_pairs=right_count_pairs,
            )
            if not right_candidates:
                continue
            for left_parallel in left_parallel_candidates:
                for right_series, right_parallel in right_candidates:
                    if tuple(int(value) for value in right_series) == (int(target_answer),) and tuple(
                        int(value) for value in right_parallel
                    ) == tuple(int(value) for value in left_parallel):
                        continue
                    candidates.append(
                        (
                            (int(target_answer),),
                            tuple(int(value) for value in left_parallel),
                            tuple(int(value) for value in right_series),
                            tuple(int(value) for value in right_parallel),
                            int(paired_total),
                        )
                    )
    return candidates


@lru_cache(maxsize=None)
def _compound_missing_pair_candidates(
    *,
    target_answer: int,
    resistor_value_min: int,
    resistor_value_max: int,
    block_count_options: Tuple[int, ...],
    branch_count_options: Tuple[int, ...],
    max_candidates: int = 20000,
) -> Tuple[
    Tuple[
        Tuple[Tuple[int, ...], ...],
        Tuple[int, ...],
        Tuple[int, int],
        int,
        Tuple[Tuple[int, ...], ...],
        Tuple[int, ...],
        Tuple[int, int],
        int,
    ],
    ...,
]:
    """Enumerate paired compound circuits with the missing resistor in a left gap."""

    block_options = _integer_parallel_block_candidates(
        resistor_value_min=int(resistor_value_min),
        resistor_value_max=int(resistor_value_max),
        branch_count_options=tuple(int(value) for value in branch_count_options),
    )
    gap_options = (0,) + tuple(range(int(resistor_value_min), int(resistor_value_max) + 1))
    candidates: List[
        Tuple[
            Tuple[Tuple[int, ...], ...],
            Tuple[int, ...],
            Tuple[int, int],
            int,
            Tuple[Tuple[int, ...], ...],
            Tuple[int, ...],
            Tuple[int, int],
            int,
        ]
    ] = []
    seen: set[
        Tuple[
            Tuple[Tuple[int, ...], ...],
            Tuple[int, ...],
            Tuple[int, int],
            int,
            Tuple[Tuple[int, ...], ...],
            Tuple[int, ...],
            Tuple[int, int],
            int,
        ]
    ] = set()
    right_cache: Dict[int, Tuple[Tuple[Tuple[Tuple[int, ...], ...], Tuple[int, ...], Tuple[int, int]], ...]] = {}
    block_counts = tuple(int(value) for value in block_count_options if int(value) >= 2)
    per_block_count_limit = max(1, int(max_candidates) // max(1, len(block_counts)))

    class _BlockCountFilled(Exception):
        pass

    for block_count in block_counts:
        added_for_block_count = 0
        gap_count = int(block_count) - 1
        try:
            for block_combo in product(block_options, repeat=int(block_count)):
                block_total = sum(int(item[0]) for item in block_combo)
                left_blocks = tuple(tuple(int(value) for value in item[1]) for item in block_combo)
                for missing_gap_index in range(int(gap_count)):
                    other_gap_indices = [index for index in range(int(gap_count)) if index != int(missing_gap_index)]
                    for other_gap_values in product(gap_options, repeat=len(other_gap_indices)):
                        gaps = [0 for _ in range(int(gap_count))]
                        gaps[int(missing_gap_index)] = int(target_answer)
                        for gap_index, gap_value in zip(other_gap_indices, other_gap_values, strict=True):
                            gaps[int(gap_index)] = int(gap_value)
                        for left_outer_values in product(gap_options, repeat=2):
                            left_outer = (int(left_outer_values[0]), int(left_outer_values[1]))
                            paired_total = int(block_total) + sum(int(value) for value in gaps) + sum(
                                int(value) for value in left_outer
                            )
                            if int(paired_total) not in right_cache:
                                right_cache[int(paired_total)] = _compound_candidates_for_total(
                                    target_answer=int(paired_total),
                                    resistor_value_min=int(resistor_value_min),
                                    resistor_value_max=int(resistor_value_max),
                                    block_count_options=tuple(int(value) for value in block_count_options),
                                    branch_count_options=tuple(int(value) for value in branch_count_options),
                                    max_candidates=256,
                                )
                            for right_blocks, right_gaps, right_outer in right_cache[int(paired_total)]:
                                if (
                                    tuple(right_blocks) == tuple(left_blocks)
                                    and tuple(right_gaps) == tuple(gaps)
                                    and tuple(right_outer) == tuple(left_outer)
                                ):
                                    continue
                                candidate = (
                                    tuple(left_blocks),
                                    tuple(int(value) for value in gaps),
                                    left_outer,
                                    int(missing_gap_index),
                                    tuple(tuple(int(value) for value in block) for block in right_blocks),
                                    tuple(int(value) for value in right_gaps),
                                    (int(right_outer[0]), int(right_outer[1])),
                                    int(paired_total),
                                )
                                if candidate in seen:
                                    continue
                                seen.add(candidate)
                                candidates.append(candidate)
                                added_for_block_count += 1
                                if added_for_block_count >= int(per_block_count_limit):
                                    raise _BlockCountFilled
                                if len(candidates) >= int(max_candidates):
                                    return tuple(candidates)
        except _BlockCountFilled:
            continue
    return tuple(candidates)


def _sample_missing_pair_layout(
    rng,
    *,
    instance_seed: int,
    scene_variant: str,
    target_answer: int,
    params: Mapping[str, Any],
) -> _MissingCircuitPairLayout:
    """Sample one paired-circuit layout with a single missing left resistor."""

    resistor_value_min = int(
        params.get("resistor_value_min", group_default(_GEN_DEFAULTS, "resistor_value_min", _DEFAULTS.resistor_value_min))
    )
    resistor_value_max = int(
        params.get("resistor_value_max", group_default(_GEN_DEFAULTS, "resistor_value_max", _DEFAULTS.resistor_value_max))
    )
    if str(scene_variant) == "parallel":
        candidates = _parallel_missing_pair_candidates(
            target_answer=int(target_answer),
            resistor_value_min=int(resistor_value_min),
            resistor_value_max=int(resistor_value_max),
            left_branch_count_options=_parallel_missing_left_branch_count_options(params),
            right_branch_count_options=_parallel_missing_right_branch_count_options(params),
        )
        if not candidates:
            raise ValueError(f"no paired parallel candidates for missing resistor {target_answer}")
        left_known_values, right_values = candidates[int(rng.randrange(len(candidates)))]
        left_entries = [(int(value), False) for value in left_known_values] + [(int(target_answer), True)]
        rng.shuffle(left_entries)
        left_values = [int(value) for value, _ in left_entries]
        right_values_list = list(right_values)
        rng.shuffle(right_values_list)
        missing_index = next(index for index, (_, is_missing) in enumerate(left_entries, start=1) if bool(is_missing))
        paired_total = _equivalent_resistance_fraction(
            scene_variant="parallel",
            series_values=tuple(),
            parallel_values=tuple(int(value) for value in left_values),
        )
        if int(paired_total.denominator) != 1:
            raise ValueError("paired parallel missing layout must have an integral equivalent resistance")
        return _MissingCircuitPairLayout(
            scene_variant=str(scene_variant),
            left_series_values=tuple(),
            left_parallel_values=tuple(int(value) for value in left_values),
            left_orientation=None,
            right_series_values=tuple(),
            right_parallel_values=tuple(int(value) for value in right_values_list),
            right_orientation=None,
            missing_resistor_index=int(missing_index),
            missing_component_group="parallel",
            target_answer=int(target_answer),
            paired_total_resistance=int(paired_total.numerator),
        )

    candidates = _compound_missing_pair_candidates(
        target_answer=int(target_answer),
        resistor_value_min=int(resistor_value_min),
        resistor_value_max=int(resistor_value_max),
        block_count_options=_compound_missing_parallel_block_count_options(params),
        branch_count_options=_compound_parallel_branch_count_options(params),
    )
    if not candidates:
        raise ValueError(f"no paired compound candidates for missing resistor {target_answer}")
    candidates_by_block_count: Dict[
        int,
        List[
            Tuple[
                Tuple[Tuple[int, ...], ...],
                Tuple[int, ...],
                Tuple[int, int],
                int,
                Tuple[Tuple[int, ...], ...],
                Tuple[int, ...],
                Tuple[int, int],
                int,
            ]
        ],
    ] = {}
    for candidate in candidates:
        candidates_by_block_count.setdefault(len(candidate[0]), []).append(candidate)
    available_block_counts = sorted(candidates_by_block_count)
    chosen_block_count = _select_compound_block_count(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        available_block_counts=available_block_counts,
    )
    block_count_candidates = candidates_by_block_count[int(chosen_block_count)]
    candidates_by_outer_mask: Dict[
        Tuple[bool, bool, bool, bool],
        List[
            Tuple[
                Tuple[Tuple[int, ...], ...],
                Tuple[int, ...],
                Tuple[int, int],
                int,
                Tuple[Tuple[int, ...], ...],
                Tuple[int, ...],
                Tuple[int, int],
                int,
            ]
        ],
    ] = {}
    for candidate in block_count_candidates:
        left_outer = candidate[2]
        right_outer = candidate[6]
        candidates_by_outer_mask.setdefault(
            (
                int(left_outer[0]) > 0,
                int(left_outer[1]) > 0,
                int(right_outer[0]) > 0,
                int(right_outer[1]) > 0,
            ),
            [],
        ).append(candidate)
    available_outer_masks = sorted(candidates_by_outer_mask)
    chosen_outer_mask = available_outer_masks[int(rng.randrange(len(available_outer_masks)))]
    (
        left_parallel_blocks,
        left_inter_block_series_values,
        left_outer_series_values,
        missing_gap_index,
        right_parallel_blocks,
        right_inter_block_series_values,
        right_outer_series_values,
        paired_total,
    ) = candidates_by_outer_mask[chosen_outer_mask][int(rng.randrange(len(candidates_by_outer_mask[chosen_outer_mask])))]
    left_blocks = [list(block) for block in left_parallel_blocks]
    right_blocks = [list(block) for block in right_parallel_blocks]
    for block in left_blocks:
        rng.shuffle(block)
    for block in right_blocks:
        rng.shuffle(block)
    missing_resistor_index = _compound_missing_resistor_index(
        parallel_blocks=left_blocks,
        inter_block_series_values=left_inter_block_series_values,
        outer_series_values=left_outer_series_values,
        missing_gap_index=int(missing_gap_index),
    )
    left_series_values = tuple(
        int(value)
        for value in (
            int(left_outer_series_values[0]),
            *tuple(int(value) for value in left_inter_block_series_values),
            int(left_outer_series_values[1]),
        )
        if int(value) > 0
    )
    right_series_values = tuple(
        int(value)
        for value in (
            int(right_outer_series_values[0]),
            *tuple(int(value) for value in right_inter_block_series_values),
            int(right_outer_series_values[1]),
        )
        if int(value) > 0
    )
    return _MissingCircuitPairLayout(
        scene_variant=str(scene_variant),
        left_series_values=left_series_values,
        left_parallel_values=tuple(int(value) for block in left_blocks for value in block),
        left_orientation="compound_parallel_chain",
        right_series_values=right_series_values,
        right_parallel_values=tuple(int(value) for block in right_blocks for value in block),
        right_orientation="compound_parallel_chain",
        missing_resistor_index=int(missing_resistor_index),
        missing_component_group="inter_block_series",
        target_answer=int(target_answer),
        paired_total_resistance=int(paired_total),
        left_parallel_blocks=tuple(tuple(int(value) for value in block) for block in left_blocks),
        left_inter_block_series_values=tuple(int(value) for value in left_inter_block_series_values),
        left_outer_series_values=(int(left_outer_series_values[0]), int(left_outer_series_values[1])),
        right_parallel_blocks=tuple(tuple(int(value) for value in block) for block in right_blocks),
        right_inter_block_series_values=tuple(int(value) for value in right_inter_block_series_values),
        right_outer_series_values=(int(right_outer_series_values[0]), int(right_outer_series_values[1])),
    )


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    """Return prompt JSON examples tailored to the active query id."""

    evidence_value: List[List[int]]
    if str(query_id) == "missing_resistor_value":
        evidence_value = [[174, 214, 270, 260]]
    else:
        evidence_value = [
            [322, 167, 418, 213],
            [322, 257, 418, 303],
            [322, 347, 418, 393],
        ]
    return build_prompt_json_examples(evidence_value=evidence_value, answer_type="integer")


def _pair_render_defaults(params: Mapping[str, Any], *, instance_seed: int | None = None) -> Dict[str, Any]:
    """Return local render defaults for one sub-circuit in the paired missing-resistor scene."""

    return {
        "canvas_width": int(
            params.get("pair_scene_width_px", group_default(_RENDER_DEFAULTS, "pair_scene_width_px", _DEFAULTS.pair_scene_width_px))
        ),
        "canvas_height": int(
            params.get("pair_scene_height_px", group_default(_RENDER_DEFAULTS, "pair_scene_height_px", _DEFAULTS.pair_scene_height_px))
        ),
        "terminal_left_x_px": int(
            params.get(
                "pair_terminal_left_x_px",
                group_default(_RENDER_DEFAULTS, "pair_terminal_left_x_px", _DEFAULTS.pair_terminal_left_x_px),
            )
        ),
        "terminal_radius_px": int(params.get("terminal_radius_px", group_default(_RENDER_DEFAULTS, "terminal_radius_px", _DEFAULTS.terminal_radius_px))),
        "terminal_font_size_px": int(
            params.get("terminal_font_size_px", group_default(_RENDER_DEFAULTS, "terminal_font_size_px", _DEFAULTS.terminal_font_size_px))
        ),
        "wire_width_px": resolve_render_int(
            params,
            _RENDER_DEFAULTS,
            "wire_width_px",
            _DEFAULTS.wire_width_px,
            instance_seed=instance_seed,
            namespace=TASK_ID,
        ),
        "resistor_box_width_px": int(
            params.get(
                "pair_resistor_box_width_px",
                group_default(_RENDER_DEFAULTS, "pair_resistor_box_width_px", _DEFAULTS.pair_resistor_box_width_px),
            )
        ),
        "resistor_box_height_px": int(
            params.get(
                "pair_resistor_box_height_px",
                group_default(_RENDER_DEFAULTS, "pair_resistor_box_height_px", _DEFAULTS.pair_resistor_box_height_px),
            )
        ),
        "resistor_font_size_px": int(
            params.get(
                "pair_resistor_font_size_px",
                group_default(_RENDER_DEFAULTS, "pair_resistor_font_size_px", _DEFAULTS.pair_resistor_font_size_px),
            )
        ),
        "label_stroke_width_px": resolve_render_int(
            params,
            _RENDER_DEFAULTS,
            "label_stroke_width_px",
            _DEFAULTS.label_stroke_width_px,
            instance_seed=instance_seed,
            namespace=TASK_ID,
        ),
        "parallel_rail_left_x_px": int(
            params.get(
                "pair_parallel_rail_left_x_px",
                group_default(_RENDER_DEFAULTS, "pair_parallel_rail_left_x_px", _DEFAULTS.pair_parallel_rail_left_x_px),
            )
        ),
        "parallel_branch_top_y_px": int(
            params.get(
                "pair_parallel_branch_top_y_px",
                group_default(_RENDER_DEFAULTS, "pair_parallel_branch_top_y_px", _DEFAULTS.pair_parallel_branch_top_y_px),
            )
        ),
        "parallel_branch_bottom_y_px": int(
            params.get(
                "pair_parallel_branch_bottom_y_px",
                group_default(_RENDER_DEFAULTS, "pair_parallel_branch_bottom_y_px", _DEFAULTS.pair_parallel_branch_bottom_y_px),
            )
        ),
        "series_parallel_branch_left_x_px": int(
            params.get(
                "pair_series_parallel_branch_left_x_px",
                group_default(
                    _RENDER_DEFAULTS,
                    "pair_series_parallel_branch_left_x_px",
                    _DEFAULTS.pair_series_parallel_branch_left_x_px,
                ),
            )
        ),
    }


def _draw_equals_sign(image, *, center_xy: Tuple[float, float], font_size_px: int) -> List[float]:
    """Draw one centered equality sign and return its bbox."""

    draw = ImageDraw.Draw(image)
    font = load_font(int(font_size_px), bold=True)
    text = "="
    stroke_fill = resolve_text_stroke_fill((72, 76, 82))
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=3)
    left, top, right, bottom = [float(value) for value in bbox]
    origin = (
        float(center_xy[0] - (0.5 * (left + right))),
        float(center_xy[1] - (0.5 * (top + bottom))),
    )
    draw.text(origin, text, font=font, fill=(72, 76, 82), stroke_width=3, stroke_fill=tuple(int(v) for v in stroke_fill))
    return [
        round(float(origin[0] + left), 3),
        round(float(origin[1] + top), 3),
        round(float(origin[0] + right), 3),
        round(float(origin[1] + bottom), 3),
    ]


def _draw_resistance_label(image, *, center_xy: Tuple[float, float], text: str) -> List[float]:
    """Draw one resistance helper label for a paired circuit."""

    draw = ImageDraw.Draw(image)
    font = load_font(22, bold=True)
    text_bbox = draw.textbbox((0, 0), text, font=font, stroke_width=1)
    text_width = float(text_bbox[2] - text_bbox[0])
    text_height = float(text_bbox[3] - text_bbox[1])
    pad_x = 14.0
    pad_y = 8.0
    rect = [
        float(center_xy[0] - (0.5 * text_width) - pad_x),
        float(center_xy[1] - (0.5 * text_height) - pad_y),
        float(center_xy[0] + (0.5 * text_width) + pad_x),
        float(center_xy[1] + (0.5 * text_height) + pad_y),
    ]
    draw.rounded_rectangle(rect, radius=8, fill=(255, 255, 255), outline=(72, 76, 82), width=2)
    text_xy = (
        float(center_xy[0] - (0.5 * text_width) - text_bbox[0]),
        float(center_xy[1] - (0.5 * text_height) - text_bbox[1]),
    )
    stroke_fill = resolve_text_stroke_fill((255, 255, 255))
    draw.text(text_xy, text, font=font, fill=(42, 46, 52), stroke_width=1, stroke_fill=tuple(int(v) for v in stroke_fill))
    return [round(float(value), 3) for value in rect]


class _PhysicsCircuitsEquivalentResistanceBaseTask:
    """Return one simple equivalent-resistance question from a resistor diagram."""

    task_id = TASK_ID
    domain = "physics"
    task_group = "circuits"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        rendered_scene: RenderedCircuitScene | None = None
        layout: _CircuitLayout | None = None
        pair_layout: _MissingCircuitPairLayout | None = None

        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                if str(axes.query_id) == "missing_resistor_value":
                    public_scene_id = "paired_resistor"
                    pair_layout = _sample_missing_pair_layout(
                        attempt_rng,
                        instance_seed=int(instance_seed),
                        scene_variant=str(axes.scene_variant),
                        target_answer=int(axes.target_answer),
                        params=params,
                    )
                    layout = None
                else:
                    public_scene_id = "resistor"
                    layout = _sample_layout(
                        attempt_rng,
                        instance_seed=int(instance_seed),
                        scene_variant=str(axes.scene_variant),
                        target_answer=int(axes.target_answer),
                        params=params,
                    )
                    pair_layout = None
            except ValueError:
                continue

            background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
                scene_id="resistor_network",
                task_group=self.task_group,
                canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
                canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
                instance_seed=int(instance_seed),
                params=params,
            )
            if str(axes.query_id) == "missing_resistor_value":
                pair_defaults = _pair_render_defaults(params, instance_seed=int(instance_seed))
                left_origin = (
                    float(
                        params.get(
                            "pair_left_origin_x_px",
                            group_default(_RENDER_DEFAULTS, "pair_left_origin_x_px", _DEFAULTS.pair_left_origin_x_px),
                        )
                    ),
                    float(
                        params.get(
                            "pair_origin_top_y_px",
                            group_default(_RENDER_DEFAULTS, "pair_origin_top_y_px", _DEFAULTS.pair_origin_top_y_px),
                        )
                    ),
                )
                right_origin = (
                    float(
                        params.get(
                            "pair_right_origin_x_px",
                            group_default(_RENDER_DEFAULTS, "pair_right_origin_x_px", _DEFAULTS.pair_right_origin_x_px),
                        )
                    ),
                    float(
                        params.get(
                            "pair_origin_top_y_px",
                            group_default(_RENDER_DEFAULTS, "pair_origin_top_y_px", _DEFAULTS.pair_origin_top_y_px),
                        )
                    ),
                )
                left_scene = render_resistor_network_scene(
                    scene_variant=str(pair_layout.scene_variant),
                    series_values=list(pair_layout.left_series_values),
                    parallel_values=list(pair_layout.left_parallel_values),
                    parallel_blocks=list(pair_layout.left_parallel_blocks) or None,
                    inter_block_series_values=list(pair_layout.left_inter_block_series_values) or None,
                    outer_series_values=list(pair_layout.left_outer_series_values),
                    background=background,
                    render_defaults=pair_defaults,
                    accent_color_name=str(axes.accent_color_name),
                    series_parallel_orientation=str(pair_layout.left_orientation or "series_then_parallel"),
                    missing_resistor_indices=[int(pair_layout.missing_resistor_index)],
                    origin_offset_px=left_origin,
                    entity_id_prefix="left_",
                    diagram_style=diagram_style,
                )
                rendered_scene = render_resistor_network_scene(
                    scene_variant=str(pair_layout.scene_variant),
                    series_values=list(pair_layout.right_series_values),
                    parallel_values=list(pair_layout.right_parallel_values),
                    parallel_blocks=list(pair_layout.right_parallel_blocks) or None,
                    inter_block_series_values=list(pair_layout.right_inter_block_series_values) or None,
                    outer_series_values=list(pair_layout.right_outer_series_values),
                    background=left_scene.image,
                    render_defaults=pair_defaults,
                    accent_color_name=str(axes.accent_color_name),
                    series_parallel_orientation=str(pair_layout.right_orientation or "series_then_parallel"),
                    origin_offset_px=right_origin,
                    entity_id_prefix="right_",
                    diagram_style=diagram_style,
                )
                equals_bbox = _draw_equals_sign(
                    rendered_scene.image,
                    center_xy=(
                        float(0.5 * ((left_origin[0] + pair_defaults["canvas_width"]) + right_origin[0])),
                        float(left_origin[1] + (0.5 * pair_defaults["canvas_height"])),
                    ),
                    font_size_px=int(
                        params.get(
                            "pair_equals_font_size_px",
                            group_default(_RENDER_DEFAULTS, "pair_equals_font_size_px", _DEFAULTS.pair_equals_font_size_px),
                        )
                    ),
                )
                common_total_bbox = _draw_resistance_label(
                    rendered_scene.image,
                    center_xy=(
                        float(0.5 * ((left_origin[0] + pair_defaults["canvas_width"]) + right_origin[0])),
                        float(left_origin[1] + 40.0),
                    ),
                    text=f"R_total = {int(pair_layout.paired_total_resistance)} ohms",
                )
                known_left_bbox = _draw_resistance_label(
                    rendered_scene.image,
                    center_xy=(
                        float(0.5 * ((left_origin[0] + pair_defaults["canvas_width"]) + right_origin[0])),
                        float(left_origin[1] + 82.0),
                    ),
                    text=f"Left known = {int(pair_layout.paired_total_resistance) - int(pair_layout.target_answer)} ohms",
                )
                missing_specs = [spec for spec in left_scene.resistor_specs if bool(spec.missing)]
                if len(missing_specs) != 1:
                    continue
                missing_spec = missing_specs[0]
                combined_entities = list(left_scene.scene_entities) + list(rendered_scene.scene_entities)
                combined_entities.append(
                    {
                        "entity_id": "common_total_resistance_label",
                        "entity_type": "physics_circuit_total_resistance_label",
                        "bbox_px": list(common_total_bbox),
                        "meta": {"total_resistance": int(pair_layout.paired_total_resistance)},
                    }
                )
                combined_entities.append(
                    {
                        "entity_id": "left_known_resistance_label",
                        "entity_type": "physics_circuit_known_resistance_label",
                        "bbox_px": list(known_left_bbox),
                        "meta": {"known_resistance": int(pair_layout.paired_total_resistance) - int(pair_layout.target_answer)},
                    }
                )
                resistor_specs = list(left_scene.resistor_specs) + list(rendered_scene.resistor_specs)
                render_map = {
                    "accent_color_name": str(axes.accent_color_name),
                    "technical_diagram_frame_mode": str(getattr(diagram_style, "frame_mode", "none")),
                    "left_scene": dict(left_scene.render_map),
                    "right_scene": dict(rendered_scene.render_map),
                    "resistor_bboxes_px": {
                        **{spec.resistor_id: list(spec.bbox_px) for spec in resistor_specs},
                    },
                    "wire_segments_px": list(left_scene.render_map["wire_segments_px"]) + list(rendered_scene.render_map["wire_segments_px"]),
                    "terminal_bboxes_px": {
                        "left_A": list(left_scene.render_map["terminal_bboxes_px"]["A"]),
                        "left_B": list(left_scene.render_map["terminal_bboxes_px"]["B"]),
                        "right_A": list(rendered_scene.render_map["terminal_bboxes_px"]["A"]),
                        "right_B": list(rendered_scene.render_map["terminal_bboxes_px"]["B"]),
                    },
                    "terminal_label_bboxes_px": {
                        "left_A": list(left_scene.render_map["terminal_label_bboxes_px"]["A"]),
                        "left_B": list(left_scene.render_map["terminal_label_bboxes_px"]["B"]),
                        "right_A": list(rendered_scene.render_map["terminal_label_bboxes_px"]["A"]),
                        "right_B": list(rendered_scene.render_map["terminal_label_bboxes_px"]["B"]),
                    },
                    "missing_resistor_entity_ids": [str(missing_spec.resistor_id)],
                    "evidence_entity_ids": [str(missing_spec.resistor_id)],
                    "equals_sign_bbox_px": list(equals_bbox),
                    "common_total_resistance_label_bbox_px": list(common_total_bbox),
                    "left_known_resistance_label_bbox_px": list(known_left_bbox),
                }
                rendered_scene = RenderedCircuitScene(
                    image=rendered_scene.image,
                    resistor_specs=resistor_specs,
                    evidence_bboxes=[list(missing_spec.bbox_px)],
                    evidence_entity_ids=[str(missing_spec.resistor_id)],
                    render_map=render_map,
                    scene_entities=combined_entities,
                )
            else:
                rendered_scene = render_resistor_network_scene(
                    scene_variant=str(layout.scene_variant),
                    series_values=list(layout.series_values),
                    parallel_values=list(layout.parallel_values),
                    parallel_blocks=list(layout.parallel_blocks) or None,
                    inter_block_series_values=list(layout.inter_block_series_values) or None,
                    outer_series_values=list(layout.outer_series_values),
                    background=background,
                    render_defaults={
                        key: resolve_render_int(
                            params,
                            _RENDER_DEFAULTS,
                            key,
                            int(getattr(_DEFAULTS, key)),
                            instance_seed=int(instance_seed),
                            namespace=TASK_ID,
                        )
                        for key in (
                            "canvas_width",
                            "canvas_height",
                            "terminal_left_x_px",
                            "terminal_radius_px",
                            "terminal_font_size_px",
                            "wire_width_px",
                            "resistor_box_width_px",
                            "resistor_box_height_px",
                            "resistor_font_size_px",
                            "label_stroke_width_px",
                            "parallel_rail_left_x_px",
                            "parallel_branch_top_y_px",
                            "parallel_branch_bottom_y_px",
                            "series_parallel_branch_left_x_px",
                        )
                    },
                    accent_color_name=str(axes.accent_color_name),
                    series_parallel_orientation=(
                        str(layout.series_parallel_orientation)
                        if layout.series_parallel_orientation is not None
                        else "series_then_parallel"
                    ),
                    diagram_style=diagram_style,
                )
            image, post_noise_meta = apply_post_image_noise(
                rendered_scene.image,
                instance_seed=int(instance_seed),
                params=params,
                default_config=POST_IMAGE_NOISE_DEFAULTS,
            )

            prompt_defaults = required_group_defaults(
                _PROMPT_DEFAULTS,
                (
                    "bundle_id",
                    "scene_key",
                    "task_key",
                    "json_output_contract",
                    "json_output_contract_answer_only",
                    "answer_hint_total_resistance",
                    "answer_hint_missing_resistor_value",
                    "evidence_hint_total_resistance",
                    "evidence_hint_missing_resistor_value",
                    "object_description_parallel_total_resistance",
                    "object_description_simple_series_parallel_total_resistance",
                    "object_description_parallel_missing_resistor_value",
                    "object_description_simple_series_parallel_missing_resistor_value",
                ),
                context=f"prompt defaults for {self.task_id}",
            )
            json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.query_id))
            prompt_selection = render_task_prompt_variants(
                domain=self.domain,
                task_group=self.task_group,
                bundle_id=str(prompt_defaults["bundle_id"]),
                scene_key=str(prompt_defaults["scene_key"]),
                task_key=str(prompt_defaults["task_key"]),
                query_key=str(axes.query_id),
                answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
                slots={
                    "object_description": str(
                        prompt_defaults[f"object_description_{str(axes.scene_variant)}_{str(axes.query_id)}"]
                    ),
                    "json_output_contract": str(prompt_defaults["json_output_contract"]),
                    "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                    "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_id)}"]),
                    "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
                    "json_example": str(json_example),
                    "json_example_answer_only": str(json_example_answer_only),
                },
                instance_seed=int(instance_seed),
            )
            prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

            answer_gt = TypedValue(type="integer", value=int(axes.target_answer))
            evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in rendered_scene.evidence_bboxes])
            complexity = build_physics_circuit_resistance_complexity(
                task_group_defaults=_TASK_GROUP_DEFAULTS,
                task_id=TASK_ID,
                scene_variant=str(axes.scene_variant),
                query_id=str(axes.query_id),
                resistor_count=len(rendered_scene.resistor_specs),
                target_answer=int(axes.target_answer),
            )
            trace_payload = {
                "scene_ir": {
                    "scene_kind": (
                        f"physics_resistor_network_pair_{str(axes.scene_variant)}"
                        if str(axes.query_id) == "missing_resistor_value"
                        else f"physics_resistor_network_{str(axes.scene_variant)}"
                    ),
                    "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                    "relations": {
                        "scene_variant": str(axes.scene_variant),
                        "query_id": str(axes.query_id),
                        "target_answer": int(axes.target_answer),
                        "accent_color_name": str(axes.accent_color_name),
                        "evidence_entity_ids": list(rendered_scene.evidence_entity_ids),
                        "paired_total_resistance": (
                            None if pair_layout is None else int(pair_layout.paired_total_resistance)
                        ),
                    },
                },
                "query_spec": {
                    "query_id": str(axes.query_id),
                    "template_id": str(prompt_defaults["bundle_id"]),
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                    "params": {
                        "scene_variant": str(axes.scene_variant),
                        "query_id": str(axes.query_id),
                        "accent_color_name": str(axes.accent_color_name),
                        "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                        "query_id_probabilities": dict(axes.query_id_probabilities),
                        "accent_color_name_probabilities": dict(axes.accent_color_name_probabilities),
                        "target_answer": int(axes.target_answer),
                        "target_answer_support": [int(value) for value in axes.target_answer_support],
                        "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    },
                },
                "render_spec": {
                    "scene_variant": str(axes.scene_variant),
                    "canvas_width": int(image.size[0]),
                    "canvas_height": int(image.size[1]),
                    "accent_color_name": str(axes.accent_color_name),
                    "technical_diagram_style": dict(diagram_style_meta),
                    "background_style": background_meta,
                    "post_image_noise": post_noise_meta,
                },
                "render_map": dict(rendered_scene.render_map),
                "execution_trace": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "accent_color_name": str(axes.accent_color_name),
                    "target_answer": int(axes.target_answer),
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "series_parallel_orientation": None if layout is None else layout.series_parallel_orientation,
                    "series_values": [] if layout is None else [int(value) for value in layout.series_values],
                    "parallel_values": [] if layout is None else [int(value) for value in layout.parallel_values],
                    "parallel_blocks": (
                        []
                        if layout is None
                        else [[int(value) for value in block] for block in layout.parallel_blocks]
                    ),
                    "inter_block_series_values": (
                        []
                        if layout is None
                        else [int(value) for value in layout.inter_block_series_values]
                    ),
                    "outer_series_values": (
                        []
                        if layout is None
                        else [int(value) for value in layout.outer_series_values]
                    ),
                    "paired_total_resistance": None if pair_layout is None else int(pair_layout.paired_total_resistance),
                    "missing_resistor_index": None if pair_layout is None else int(pair_layout.missing_resistor_index),
                    "missing_component_group": None if pair_layout is None else str(pair_layout.missing_component_group),
                    "left_series_values": [] if pair_layout is None else [int(value) for value in pair_layout.left_series_values],
                    "left_parallel_values": [] if pair_layout is None else [int(value) for value in pair_layout.left_parallel_values],
                    "right_series_values": [] if pair_layout is None else [int(value) for value in pair_layout.right_series_values],
                    "right_parallel_values": [] if pair_layout is None else [int(value) for value in pair_layout.right_parallel_values],
                    "left_parallel_blocks": (
                        []
                        if pair_layout is None
                        else [[int(value) for value in block] for block in pair_layout.left_parallel_blocks]
                    ),
                    "left_inter_block_series_values": (
                        []
                        if pair_layout is None
                        else [int(value) for value in pair_layout.left_inter_block_series_values]
                    ),
                    "left_outer_series_values": (
                        []
                        if pair_layout is None
                        else [int(value) for value in pair_layout.left_outer_series_values]
                    ),
                    "right_parallel_blocks": (
                        []
                        if pair_layout is None
                        else [[int(value) for value in block] for block in pair_layout.right_parallel_blocks]
                    ),
                    "right_inter_block_series_values": (
                        []
                        if pair_layout is None
                        else [int(value) for value in pair_layout.right_inter_block_series_values]
                    ),
                    "right_outer_series_values": (
                        []
                        if pair_layout is None
                        else [int(value) for value in pair_layout.right_outer_series_values]
                    ),
                    "left_orientation": None if pair_layout is None else pair_layout.left_orientation,
                    "right_orientation": None if pair_layout is None else pair_layout.right_orientation,
                    "resistor_specs": [
                        {
                            "resistor_id": str(spec.resistor_id),
                            "value": None if spec.value is None else int(spec.value),
                            "missing": bool(spec.missing),
                        }
                        for spec in rendered_scene.resistor_specs
                    ],
                    "evidence_entity_ids": list(rendered_scene.evidence_entity_ids),
                },
                "witness_symbolic": {
                    "type": "object_set",
                    "ids": [str(item) for item in rendered_scene.evidence_entity_ids],
                },
                "projected_evidence": {
                    "bbox_set": [list(bbox) for bbox in rendered_scene.evidence_bboxes],
                },
                "background": background_meta,
                "post_image_noise": post_noise_meta,
            }
            return TaskOutput(
                prompt=str(prompt_artifacts.prompt),
                prompt_variants=dict(prompt_artifacts.prompt_variants),
                answer_gt=answer_gt,
                evidence_gt=evidence_gt,
                image=image,
                image_id="img0",
                trace_payload=trace_payload,
                complexity=complexity,
                task_versions=default_task_versions(),
                query_id=str(axes.query_id),
                scene_id=public_scene_id,
            )

        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")


@register_task
class PhysicsCircuitsTotalResistanceValueTask(
    FixedPhysicsQueryVariantTaskMixin,
    _PhysicsCircuitsEquivalentResistanceBaseTask,
):
    """Return the total equivalent resistance of one visible resistor network."""

    task_id = "task_physics__resistor__total_resistance_value"
    fixed_query_id = "total_resistance"


@register_task
class PhysicsCircuitsMissingResistorValueTask(
    FixedPhysicsQueryVariantTaskMixin,
    _PhysicsCircuitsEquivalentResistanceBaseTask,
):
    """Return the red missing resistor value that balances paired circuits."""

    task_id = "task_physics__paired_resistor__missing_resistor_value"
    fixed_query_id = "missing_resistor_value"


__all__ = [
    "PhysicsCircuitsMissingResistorValueTask",
    "PhysicsCircuitsTotalResistanceValueTask",
]
