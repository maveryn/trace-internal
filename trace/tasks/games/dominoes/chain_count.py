"""Games dominoes task for grounded chain-plus-tableau counting queries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.complexity import build_games_dominoes_chain_complexity
from ..shared.domino_scene import DominoRenderParams, DominoTileInstance, render_domino_chain_scene
from ..shared.fixed_query_task import rewrite_public_query_output
from ..shared.layout import resolve_games_layout_jitter
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.style import SUPPORTED_DOMINO_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_background_defaults, load_games_noise_defaults


TASK_ID = "games_dominoes_chain_count_base"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "single_row",
    "two_row",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "matching_end_count",
    "higher_sum_than_reference_count",
    "sum_to_target_count",
    "double_count",
)
TWO_STEP_QUERY_ID = "two_step_extension_label"
TWO_STEP_SUPPORTED_QUERY_IDS: Tuple[str, ...] = SUPPORTED_QUERY_IDS + (TWO_STEP_QUERY_ID,)
OPTION_LABELS: Tuple[str, ...] = tuple("ABCDEFGHIJKL")
PIP_VALUES: Tuple[int, ...] = tuple(range(7))
CANONICAL_DOMINOES: Tuple[Tuple[int, int], ...] = tuple(
    (int(left_value), int(right_value))
    for left_value in range(7)
    for right_value in range(left_value, 7)
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible domino chain scenes."""

    matching_end_target_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    higher_sum_target_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    sum_to_target_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    double_target_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    two_step_extension_target_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    single_row_candidate_count_support: Tuple[int, ...] = (7, 8, 9)
    two_row_candidate_count_support: Tuple[int, ...] = (10, 11, 12)
    sum_target_total_support: Tuple[int, ...] = (2, 3, 4, 5, 6, 7, 8, 9, 10)
    chain_length: int = 3
    canvas_width: int = 1180
    canvas_height: int = 760
    panel_margin_px: int = 56
    chain_top_px: int = 104
    tile_width_px: int = 138
    tile_height_px: int = 76
    chain_gap_px: int = 18
    candidate_gap_px: int = 18
    row_gap_px: int = 34
    tile_corner_radius_px: int = 12
    pip_radius_px: int = 5
    divider_width_px: int = 4
    reference_tag_font_size_px: int = 16
    reference_tag_gap_px: int = 14
    section_label_font_size_px: int = 18
    section_separator_width_px: int = 2


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one domino scene."""

    query_id: str
    scene_variant: str
    style_variant: str
    target_answer: int
    target_answer_support: Tuple[int, ...]
    candidate_count: int
    candidate_count_support: Tuple[int, ...]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]
    candidate_count_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _SampledDominoScene:
    """One sampled domino chain scene with query-specific witness metadata."""

    chain_tiles: Tuple[DominoTileInstance, ...]
    candidate_tiles: Tuple[DominoTileInstance, ...]
    evidence_tile_ids: Tuple[str, ...]
    answer_value: int | str
    reference_tile_id: str | None
    open_end_value: int | None
    reference_sum: int | None
    target_total: int | None
    first_step_tile_id: str | None
    second_step_tile_id: str | None
    bridge_value: int | None
    chain_tile_specs: Tuple[Dict[str, Any], ...]
    candidate_tile_specs: Tuple[Dict[str, Any], ...]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "dominoes")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_games_background_defaults(task_group="dominoes")
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="dominoes", apply_prob=0.0)


def _canonical_tile(left_value: int, right_value: int) -> Tuple[int, int]:
    """Return the canonical unordered representation for one domino tile."""

    lower = min(int(left_value), int(right_value))
    upper = max(int(left_value), int(right_value))
    return (int(lower), int(upper))


def _tile_sum(tile: Tuple[int, int]) -> int:
    """Return the pip sum for one canonical domino tile."""

    return int(tile[0] + tile[1])


def _build_tile_instance(
    *,
    tile_id: str,
    oriented_tile: Tuple[int, int],
    role: str,
    is_reference: bool = False,
    highlight_right_half: bool = False,
    option_label: str | None = None,
) -> DominoTileInstance:
    """Build one rendered domino tile payload from oriented half values."""

    return DominoTileInstance(
        tile_id=str(tile_id),
        left_value=int(oriented_tile[0]),
        right_value=int(oriented_tile[1]),
        role=str(role),
        is_reference=bool(is_reference),
        highlight_right_half=bool(highlight_right_half),
        option_label=None if option_label is None else str(option_label),
    )


def _resolve_query_id(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    supported_query_ids: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced semantic query id, honoring `query_id` as an alias."""

    alias_params = dict(params)
    if alias_params.get("query_id") is None and alias_params.get("query_id") is not None:
        alias_params["query_id"] = alias_params["query_id"]
    return resolve_games_query_id(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=alias_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=supported_query_ids,
    )


def _resolve_named_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced named axis for the games dominoes task."""

    return resolve_games_named_axis(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace=str(namespace),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=[str(item) for item in supported],
    )


def _target_support_key(query_id: str) -> str:
    """Return the configured answer-support key for one query id."""

    return {
        "matching_end_count": "matching_end_target_answer_support",
        "higher_sum_than_reference_count": "higher_sum_target_answer_support",
        "sum_to_target_count": "sum_to_target_answer_support",
        "double_count": "double_target_answer_support",
        TWO_STEP_QUERY_ID: "two_step_extension_target_answer_support",
    }[str(query_id)]


def _uses_uniform_query_cycle(
    params: Mapping[str, Any],
    probabilities: Mapping[str, float],
    *,
    supported_query_ids: Sequence[str],
) -> bool:
    """Return true when the query axis is using the default balanced cycle."""

    if params.get("query_id") is not None or params.get("query_id") is not None:
        return False
    enabled = bool(
        params.get(
            "balanced_query_id_sampling",
            group_default(_GEN_DEFAULTS, "balanced_query_id_sampling", True),
        )
    )
    if not enabled:
        return False
    positives = [float(value) for value in probabilities.values() if float(value) > 0.0]
    if len(positives) != len(tuple(supported_query_ids)):
        return False
    return max(positives) - min(positives) <= 1e-9


def _target_answer_params_for_query_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
    supported_query_ids: Sequence[str],
) -> Dict[str, Any]:
    """Use a per-query occurrence index for balanced target-answer cycling."""

    target_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return target_params
    if not _uses_uniform_query_cycle(
        params,
        query_id_probabilities,
        supported_query_ids=supported_query_ids,
    ):
        return target_params
    target_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(tuple(supported_query_ids)))
    return target_params


def _scene_variant_params_for_query_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
    supported_query_ids: Sequence[str],
) -> Dict[str, Any]:
    """Decorrelate balanced scene cycling from balanced query cycling."""

    scene_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return scene_params
    if params.get("scene_variant") is not None:
        return scene_params
    if not _uses_uniform_query_cycle(
        params,
        query_id_probabilities,
        supported_query_ids=supported_query_ids,
    ):
        return scene_params
    enabled = bool(
        params.get(
            "balanced_scene_variant_sampling",
            group_default(_GEN_DEFAULTS, "balanced_scene_variant_sampling", True),
        )
    )
    if not enabled:
        return scene_params
    raw_weights = params.get(
        "scene_variant_weights",
        group_default(_GEN_DEFAULTS, "scene_variant_weights", {key: 1.0 for key in SUPPORTED_SCENE_VARIANTS}),
    )
    if not isinstance(raw_weights, Mapping):
        return scene_params
    positives = [
        float(raw_weights.get(str(value), 0.0))
        for value in SUPPORTED_SCENE_VARIANTS
        if float(raw_weights.get(str(value), 0.0)) > 0.0
    ]
    if len(positives) != len(SUPPORTED_SCENE_VARIANTS):
        return scene_params
    if max(positives) - min(positives) > 1e-9:
        return scene_params
    scene_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(tuple(supported_query_ids)))
    return scene_params


def _style_variant_params_for_query_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
    supported_query_ids: Sequence[str],
) -> Dict[str, Any]:
    """Decorrelate balanced style cycling from balanced query cycling."""

    style_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return style_params
    if params.get("style_variant") is not None:
        return style_params
    if not _uses_uniform_query_cycle(
        params,
        query_id_probabilities,
        supported_query_ids=supported_query_ids,
    ):
        return style_params
    enabled = bool(
        params.get(
            "balanced_style_variant_sampling",
            group_default(_GEN_DEFAULTS, "balanced_style_variant_sampling", True),
        )
    )
    if not enabled:
        return style_params
    raw_weights = params.get(
        "style_variant_weights",
        group_default(
            _GEN_DEFAULTS,
            "style_variant_weights",
            {key: 1.0 for key in SUPPORTED_DOMINO_STYLE_VARIANTS},
        ),
    )
    if not isinstance(raw_weights, Mapping):
        return style_params
    positives = [
        float(raw_weights.get(str(value), 0.0))
        for value in SUPPORTED_DOMINO_STYLE_VARIANTS
        if float(raw_weights.get(str(value), 0.0)) > 0.0
    ]
    if len(positives) != len(SUPPORTED_DOMINO_STYLE_VARIANTS):
        return style_params
    if max(positives) - min(positives) > 1e-9:
        return style_params
    style_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(tuple(supported_query_ids)))
    return style_params


def _candidate_count_support_key(scene_variant: str) -> str:
    """Return the configured visible candidate-count support key for one layout family."""

    return {
        "single_row": "single_row_candidate_count_support",
        "two_row": "two_row_candidate_count_support",
    }[str(scene_variant)]


def _feasible_candidate_count_support(
    *,
    query_id: str,
    target_answer: int,
    raw_support: Sequence[int],
) -> Tuple[int, ...]:
    """Return the subset of candidate-count support that can realize the active query."""

    feasible: List[int] = []
    for raw_value in raw_support:
        candidate_count = int(raw_value)
        if str(query_id) == TWO_STEP_QUERY_ID:
            minimum = max(2, int(target_answer) + 1)
        else:
            minimum = max(7, int(target_answer))
        if str(query_id) == "sum_to_target_count" and int(target_answer) == 0:
            minimum = 7
        if int(candidate_count) < int(minimum):
            continue
        feasible.append(int(candidate_count))
    return tuple(int(value) for value in feasible)


def _resolve_axes(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    supported_query_ids: Sequence[str],
) -> _ResolvedAxes:
    """Resolve semantic/visual axes plus target answer and visible candidate count."""

    query_id, query_id_probabilities = _resolve_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=supported_query_ids,
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=_scene_variant_params_for_query_cycle(
            params,
            query_id_probabilities=query_id_probabilities,
            supported_query_ids=supported_query_ids,
        ),
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=_style_variant_params_for_query_cycle(
            params,
            query_id_probabilities=query_id_probabilities,
            supported_query_ids=supported_query_ids,
        ),
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_DOMINO_STYLE_VARIANTS,
    )

    target_support_key = _target_support_key(str(query_id))
    target_params = _target_answer_params_for_query_cycle(
        params,
        query_id_probabilities=query_id_probabilities,
        supported_query_ids=supported_query_ids,
    )
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=target_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(target_support_key),
        explicit_key="target_answer",
        fallback_support=getattr(_DEFAULTS, target_support_key),
        namespace=f"{TASK_ID}.target_answer.{str(query_id)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    target_answer_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=str(target_support_key),
        fallback=getattr(_DEFAULTS, target_support_key),
    )

    raw_candidate_count_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=_candidate_count_support_key(str(scene_variant)),
        fallback=getattr(_DEFAULTS, _candidate_count_support_key(str(scene_variant))),
    )
    candidate_count_support = _feasible_candidate_count_support(
        query_id=str(query_id),
        target_answer=int(target_answer),
        raw_support=raw_candidate_count_support,
    )
    if not candidate_count_support:
        raise ValueError(
            f"no feasible candidate_count values remain for {query_id}/{scene_variant} at target {target_answer}"
        )
    candidate_count_support_key = _candidate_count_support_key(str(scene_variant))
    candidate_params = dict(params)
    candidate_params[str(candidate_count_support_key)] = [int(value) for value in candidate_count_support]
    candidate_count, candidate_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=candidate_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(candidate_count_support_key),
        explicit_key="candidate_count",
        fallback_support=candidate_count_support,
        namespace=f"{TASK_ID}.candidate_count.{str(scene_variant)}.{str(query_id)}",
        balanced_flag_key="balanced_candidate_count_sampling",
        namespace_support_permutation=True,
    )

    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        candidate_count=int(candidate_count),
        candidate_count_support=tuple(int(value) for value in candidate_count_support),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
        candidate_count_probabilities=dict(candidate_count_probabilities),
    )


def _sample_chain_with_end(
    rng,
    *,
    end_tile: Tuple[int, int],
    avoid_prefix_values: Sequence[int] = (),
    avoid_prefix_doubles: bool = False,
) -> Tuple[Tuple[int, int], ...]:
    """Sample one valid oriented 3-tile chain whose rightmost tile is `end_tile`.

    `avoid_prefix_values` keeps the first two tiles from consuming certain values so
    query-specific answer pools remain stable (for example the open-end value for
    `matching_end_count` or all doubles for `double_count`).
    """

    end_left = int(end_tile[0])
    end_right = int(end_tile[1])
    blocked_values = {int(value) for value in avoid_prefix_values}
    disallowed = {_canonical_tile(int(end_left), int(end_right))}
    middle_options: List[Tuple[int, int]] = []
    for middle_left in PIP_VALUES:
        middle_canonical = _canonical_tile(int(middle_left), int(end_left))
        if middle_canonical in disallowed:
            continue
        if int(middle_left) in blocked_values or int(end_left) in blocked_values:
            continue
        if bool(avoid_prefix_doubles) and int(middle_left) == int(end_left):
            continue
        middle_options.append((int(middle_left), int(end_left)))
    if not middle_options:
        raise ValueError("unable to sample middle domino for chain")
    middle_tile = middle_options[int(rng.randrange(len(middle_options)))]
    disallowed.add(_canonical_tile(int(middle_tile[0]), int(middle_tile[1])))

    first_options: List[Tuple[int, int]] = []
    for first_left in PIP_VALUES:
        first_canonical = _canonical_tile(int(first_left), int(middle_tile[0]))
        if first_canonical in disallowed:
            continue
        if int(first_left) in blocked_values or int(middle_tile[0]) in blocked_values:
            continue
        if bool(avoid_prefix_doubles) and int(first_left) == int(middle_tile[0]):
            continue
        first_options.append((int(first_left), int(middle_tile[0])))
    if not first_options:
        raise ValueError("unable to sample first domino for chain")
    first_tile = first_options[int(rng.randrange(len(first_options)))]
    return (
        (int(first_tile[0]), int(first_tile[1])),
        (int(middle_tile[0]), int(middle_tile[1])),
        (int(end_left), int(end_right)),
    )


def _sample_generic_chain(
    rng,
    *,
    avoid_doubles: bool,
) -> Tuple[Tuple[int, int], ...]:
    """Sample one generic valid 3-tile chain."""

    for _ in range(96):
        end_left = int(PIP_VALUES[int(rng.randrange(len(PIP_VALUES)))])
        end_right = int(PIP_VALUES[int(rng.randrange(len(PIP_VALUES)))])
        if bool(avoid_doubles) and int(end_left) == int(end_right):
            continue
        try:
            chain = _sample_chain_with_end(
                rng,
                end_tile=(int(end_left), int(end_right)),
                avoid_prefix_doubles=bool(avoid_doubles),
            )
        except ValueError:
            continue
        if bool(avoid_doubles) and any(int(left_value) == int(right_value) for left_value, right_value in chain):
            continue
        return chain
    raise ValueError("unable to sample generic domino chain")


def _candidate_pool_for_chain(oriented_chain: Sequence[Tuple[int, int]]) -> Tuple[Tuple[int, int], ...]:
    """Return the canonical domino pool not already consumed by the visible chain."""

    chain_tiles = {_canonical_tile(int(left_value), int(right_value)) for left_value, right_value in oriented_chain}
    return tuple(tile for tile in CANONICAL_DOMINOES if tile not in chain_tiles)


def _random_orientation(rng, *, tile: Tuple[int, int]) -> Tuple[int, int]:
    """Return one random visible orientation for a canonical domino tile."""

    left_value, right_value = int(tile[0]), int(tile[1])
    if int(left_value) == int(right_value):
        return (int(left_value), int(right_value))
    if bool(rng.randrange(2)):
        return (int(left_value), int(right_value))
    return (int(right_value), int(left_value))


def _build_scene_instances(
    *,
    rng,
    oriented_chain: Sequence[Tuple[int, int]],
    candidate_tiles: Sequence[Tuple[int, int]],
    evidence_tiles: Sequence[Tuple[int, int]],
    reference_role: str | None,
    highlight_open_end: bool,
    shuffle_candidates: bool = True,
    label_candidates: bool = False,
) -> Tuple[Tuple[DominoTileInstance, ...], Tuple[DominoTileInstance, ...], Tuple[str, ...], str | None]:
    """Build rendered chain/candidate instances and witness ids from canonical tiles."""

    evidence_canonicals = {_canonical_tile(int(tile[0]), int(tile[1])) for tile in evidence_tiles}
    chain_instances: List[DominoTileInstance] = []
    candidate_instances: List[DominoTileInstance] = []
    evidence_tile_ids: List[str] = []
    reference_tile_id: str | None = None

    for index, oriented_tile in enumerate(oriented_chain, start=1):
        tile_id = f"chain_{index:02d}"
        is_reference = bool(index == len(oriented_chain) and reference_role is not None)
        chain_instances.append(
            _build_tile_instance(
                tile_id=str(tile_id),
                oriented_tile=(int(oriented_tile[0]), int(oriented_tile[1])),
                role=str(reference_role) if bool(is_reference) else "chain",
                is_reference=bool(is_reference),
                highlight_right_half=bool(is_reference and highlight_open_end),
            )
        )
        if bool(is_reference):
            reference_tile_id = str(tile_id)

    ordered_candidates = list(candidate_tiles)
    if bool(shuffle_candidates):
        rng.shuffle(ordered_candidates)
    for index, canonical_tile in enumerate(ordered_candidates, start=1):
        tile_id = f"candidate_{index:02d}"
        candidate_instances.append(
            _build_tile_instance(
                tile_id=str(tile_id),
                oriented_tile=_random_orientation(rng, tile=canonical_tile),
                role="candidate",
                option_label=OPTION_LABELS[index - 1] if bool(label_candidates) else None,
            )
        )
        if _canonical_tile(int(canonical_tile[0]), int(canonical_tile[1])) in evidence_canonicals:
            evidence_tile_ids.append(str(tile_id))

    return (
        tuple(chain_instances),
        tuple(candidate_instances),
        tuple(evidence_tile_ids),
        None if reference_tile_id is None else str(reference_tile_id),
    )


def _sample_matching_end_scene(rng, *, candidate_count: int, target_answer: int) -> _SampledDominoScene:
    """Sample one scene with exactly `target_answer` loose dominoes matching the open end."""

    for _ in range(256):
        open_end_value = int(PIP_VALUES[int(rng.randrange(len(PIP_VALUES)))])
        connector_value_options = [value for value in PIP_VALUES if int(value) != int(open_end_value)]
        connector_value = int(connector_value_options[int(rng.randrange(len(connector_value_options)))])
        try:
            oriented_chain = _sample_chain_with_end(
                rng,
                end_tile=(int(connector_value), int(open_end_value)),
                avoid_prefix_values=(int(open_end_value),),
            )
        except ValueError:
            continue
        candidate_pool = _candidate_pool_for_chain(oriented_chain)
        matching_pool = [tile for tile in candidate_pool if int(open_end_value) in {int(tile[0]), int(tile[1])}]
        nonmatching_pool = [tile for tile in candidate_pool if int(open_end_value) not in {int(tile[0]), int(tile[1])}]
        if int(len(matching_pool)) < int(target_answer):
            continue
        if int(len(nonmatching_pool)) < int(candidate_count - target_answer):
            continue
        evidence_tiles = list(rng.sample(matching_pool, int(target_answer)))
        filler_tiles = list(rng.sample(nonmatching_pool, int(candidate_count - target_answer)))
        selected_candidates = evidence_tiles + filler_tiles
        chain_instances, candidate_instances, evidence_tile_ids, reference_tile_id = _build_scene_instances(
            rng=rng,
            oriented_chain=oriented_chain,
            candidate_tiles=selected_candidates,
            evidence_tiles=evidence_tiles,
            reference_role="reference_end",
            highlight_open_end=True,
        )
        return _SampledDominoScene(
            chain_tiles=chain_instances,
            candidate_tiles=candidate_instances,
            evidence_tile_ids=evidence_tile_ids,
            answer_value=int(target_answer),
            reference_tile_id=reference_tile_id,
            open_end_value=int(open_end_value),
            reference_sum=int(oriented_chain[-1][0] + oriented_chain[-1][1]),
            target_total=None,
            first_step_tile_id=None,
            second_step_tile_id=None,
            bridge_value=None,
            chain_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "is_reference": bool(tile.is_reference),
                    "option_label": None if tile.option_label is None else str(tile.option_label),
                }
                for tile in chain_instances
            ),
            candidate_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "option_label": None if tile.option_label is None else str(tile.option_label),
                }
                for tile in candidate_instances
            ),
        )
    raise ValueError("unable to sample matching-end domino scene")


def _sample_higher_sum_scene(rng, *, candidate_count: int, target_answer: int) -> _SampledDominoScene:
    """Sample one scene with exactly `target_answer` loose dominoes above the reference sum."""

    feasible_end_tiles = [tile for tile in CANONICAL_DOMINOES if 6 <= _tile_sum(tile) <= 8]
    for _ in range(320):
        end_tile = feasible_end_tiles[int(rng.randrange(len(feasible_end_tiles)))]
        oriented_end = _random_orientation(rng, tile=end_tile)
        try:
            oriented_chain = _sample_chain_with_end(
                rng,
                end_tile=(int(oriented_end[0]), int(oriented_end[1])),
            )
        except ValueError:
            continue
        reference_sum = int(oriented_chain[-1][0] + oriented_chain[-1][1])
        candidate_pool = _candidate_pool_for_chain(oriented_chain)
        higher_pool = [tile for tile in candidate_pool if _tile_sum(tile) > int(reference_sum)]
        not_higher_pool = [tile for tile in candidate_pool if _tile_sum(tile) <= int(reference_sum)]
        if int(len(higher_pool)) < int(target_answer):
            continue
        if int(len(not_higher_pool)) < int(candidate_count - target_answer):
            continue
        evidence_tiles = list(rng.sample(higher_pool, int(target_answer)))
        filler_tiles = list(rng.sample(not_higher_pool, int(candidate_count - target_answer)))
        selected_candidates = evidence_tiles + filler_tiles
        chain_instances, candidate_instances, evidence_tile_ids, reference_tile_id = _build_scene_instances(
            rng=rng,
            oriented_chain=oriented_chain,
            candidate_tiles=selected_candidates,
            evidence_tiles=evidence_tiles,
            reference_role="reference_sum",
            highlight_open_end=False,
        )
        return _SampledDominoScene(
            chain_tiles=chain_instances,
            candidate_tiles=candidate_instances,
            evidence_tile_ids=evidence_tile_ids,
            answer_value=int(target_answer),
            reference_tile_id=reference_tile_id,
            open_end_value=None,
            reference_sum=int(reference_sum),
            target_total=None,
            first_step_tile_id=None,
            second_step_tile_id=None,
            bridge_value=None,
            chain_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "is_reference": bool(tile.is_reference),
                    "option_label": None if tile.option_label is None else str(tile.option_label),
                }
                for tile in chain_instances
            ),
            candidate_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "option_label": None if tile.option_label is None else str(tile.option_label),
                }
                for tile in candidate_instances
            ),
        )
    raise ValueError("unable to sample higher-sum domino scene")


def _sample_sum_to_target_scene(
    rng,
    *,
    candidate_count: int,
    target_answer: int,
    params: Mapping[str, Any],
) -> _SampledDominoScene:
    """Sample one scene with exactly `target_answer` loose dominoes matching a target sum."""

    explicit_target_total = params.get("target_total")
    raw_target_total_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="sum_target_total_support",
        fallback=_DEFAULTS.sum_target_total_support,
    )
    for _ in range(320):
        try:
            oriented_chain = _sample_generic_chain(rng, avoid_doubles=False)
        except ValueError:
            continue
        candidate_pool = _candidate_pool_for_chain(oriented_chain)
        feasible_totals: List[int] = []
        for total in raw_target_total_support:
            exact_pool = [tile for tile in candidate_pool if _tile_sum(tile) == int(total)]
            non_target_pool = [tile for tile in candidate_pool if _tile_sum(tile) != int(total)]
            if int(target_answer) == 0:
                if int(len(non_target_pool)) >= int(candidate_count):
                    feasible_totals.append(int(total))
            elif int(len(exact_pool)) >= int(target_answer) and int(len(non_target_pool)) >= int(candidate_count - target_answer):
                feasible_totals.append(int(total))
        if explicit_target_total is not None:
            target_total = int(explicit_target_total)
            if int(target_total) not in set(feasible_totals):
                raise ValueError(f"unsupported target_total for sum_to_target_count: {target_total}")
        else:
            if not feasible_totals:
                continue
            target_total = int(feasible_totals[int(rng.randrange(len(feasible_totals)))])

        exact_pool = [tile for tile in candidate_pool if _tile_sum(tile) == int(target_total)]
        non_target_pool = [tile for tile in candidate_pool if _tile_sum(tile) != int(target_total)]
        evidence_tiles = (
            []
            if int(target_answer) == 0
            else list(rng.sample(exact_pool, int(target_answer)))
        )
        filler_tiles = list(rng.sample(non_target_pool, int(candidate_count - target_answer)))
        selected_candidates = list(evidence_tiles) + filler_tiles
        chain_instances, candidate_instances, evidence_tile_ids, reference_tile_id = _build_scene_instances(
            rng=rng,
            oriented_chain=oriented_chain,
            candidate_tiles=selected_candidates,
            evidence_tiles=evidence_tiles,
            reference_role=None,
            highlight_open_end=False,
        )
        return _SampledDominoScene(
            chain_tiles=chain_instances,
            candidate_tiles=candidate_instances,
            evidence_tile_ids=evidence_tile_ids,
            answer_value=int(target_answer),
            reference_tile_id=reference_tile_id,
            open_end_value=None,
            reference_sum=None,
            target_total=int(target_total),
            first_step_tile_id=None,
            second_step_tile_id=None,
            bridge_value=None,
            chain_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "is_reference": bool(tile.is_reference),
                    "option_label": None if tile.option_label is None else str(tile.option_label),
                }
                for tile in chain_instances
            ),
            candidate_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "option_label": None if tile.option_label is None else str(tile.option_label),
                }
                for tile in candidate_instances
            ),
        )
    raise ValueError("unable to sample sum-to-target domino scene")


def _sample_double_scene(rng, *, candidate_count: int, target_answer: int) -> _SampledDominoScene:
    """Sample one scene with exactly `target_answer` loose doubles."""

    for _ in range(256):
        try:
            oriented_chain = _sample_generic_chain(rng, avoid_doubles=True)
        except ValueError:
            continue
        candidate_pool = _candidate_pool_for_chain(oriented_chain)
        double_pool = [tile for tile in candidate_pool if int(tile[0]) == int(tile[1])]
        non_double_pool = [tile for tile in candidate_pool if int(tile[0]) != int(tile[1])]
        if int(len(double_pool)) < int(target_answer):
            continue
        if int(len(non_double_pool)) < int(candidate_count - target_answer):
            continue
        evidence_tiles = list(rng.sample(double_pool, int(target_answer)))
        filler_tiles = list(rng.sample(non_double_pool, int(candidate_count - target_answer)))
        selected_candidates = evidence_tiles + filler_tiles
        chain_instances, candidate_instances, evidence_tile_ids, reference_tile_id = _build_scene_instances(
            rng=rng,
            oriented_chain=oriented_chain,
            candidate_tiles=selected_candidates,
            evidence_tiles=evidence_tiles,
            reference_role=None,
            highlight_open_end=False,
        )
        return _SampledDominoScene(
            chain_tiles=chain_instances,
            candidate_tiles=candidate_instances,
            evidence_tile_ids=evidence_tile_ids,
            answer_value=int(target_answer),
            reference_tile_id=reference_tile_id,
            open_end_value=None,
            reference_sum=None,
            target_total=None,
            first_step_tile_id=None,
            second_step_tile_id=None,
            bridge_value=None,
            chain_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "is_reference": bool(tile.is_reference),
                    "option_label": None if tile.option_label is None else str(tile.option_label),
                }
                for tile in chain_instances
            ),
            candidate_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "option_label": None if tile.option_label is None else str(tile.option_label),
                }
                for tile in candidate_instances
            ),
        )
    raise ValueError("unable to sample double-count domino scene")


def _sample_two_step_extension_scene(rng, *, candidate_count: int, target_answer: int) -> _SampledDominoScene:
    """Sample one scene with a unique labeled second domino in a two-step chain extension."""

    target_label_index = int(target_answer)
    if not 0 <= int(target_label_index) < min(int(candidate_count), len(OPTION_LABELS)):
        raise ValueError("two_step_extension target answer must be a visible label index")
    for _ in range(360):
        open_end_value = int(PIP_VALUES[int(rng.randrange(len(PIP_VALUES)))])
        bridge_options = [value for value in PIP_VALUES if int(value) != int(open_end_value)]
        bridge_value = int(bridge_options[int(rng.randrange(len(bridge_options)))])
        connector_options = [
            value for value in PIP_VALUES
            if int(value) not in {int(open_end_value), int(bridge_value)}
        ]
        if not connector_options:
            continue
        connector_value = int(connector_options[int(rng.randrange(len(connector_options)))])
        answer_outer_options = [value for value in PIP_VALUES if int(value) != int(open_end_value)]
        answer_outer = int(answer_outer_options[int(rng.randrange(len(answer_outer_options)))])
        first_tile = _canonical_tile(int(open_end_value), int(bridge_value))
        answer_tile = _canonical_tile(int(bridge_value), int(answer_outer))
        if answer_tile == first_tile:
            continue
        try:
            oriented_chain = _sample_chain_with_end(
                rng,
                end_tile=(int(connector_value), int(open_end_value)),
                avoid_prefix_values=(int(open_end_value), int(bridge_value)),
            )
        except ValueError:
            continue
        candidate_pool = set(_candidate_pool_for_chain(oriented_chain))
        if first_tile not in candidate_pool or answer_tile not in candidate_pool:
            continue
        filler_pool = [
            tile for tile in candidate_pool
            if tile not in {first_tile, answer_tile}
            and int(open_end_value) not in {int(tile[0]), int(tile[1])}
            and int(bridge_value) not in {int(tile[0]), int(tile[1])}
        ]
        if len(filler_pool) < int(candidate_count) - 2:
            continue
        first_index_options = [index for index in range(int(candidate_count)) if int(index) != int(target_label_index)]
        first_index = int(first_index_options[int(rng.randrange(len(first_index_options)))])
        filler_tiles = list(rng.sample(filler_pool, int(candidate_count) - 2))
        ordered_candidates: List[Tuple[int, int] | None] = [None for _ in range(int(candidate_count))]
        ordered_candidates[int(first_index)] = first_tile
        ordered_candidates[int(target_label_index)] = answer_tile
        filler_iter = iter(filler_tiles)
        for index, value in enumerate(ordered_candidates):
            if value is None:
                ordered_candidates[int(index)] = next(filler_iter)
        selected_candidates = [tile for tile in ordered_candidates if tile is not None]

        chain_instances, candidate_instances, evidence_tile_ids, reference_tile_id = _build_scene_instances(
            rng=rng,
            oriented_chain=oriented_chain,
            candidate_tiles=selected_candidates,
            evidence_tiles=(first_tile, answer_tile),
            reference_role="reference_end",
            highlight_open_end=True,
            shuffle_candidates=False,
            label_candidates=True,
        )
        first_step_tile_id = f"candidate_{int(first_index) + 1:02d}"
        second_step_tile_id = f"candidate_{int(target_label_index) + 1:02d}"
        return _SampledDominoScene(
            chain_tiles=chain_instances,
            candidate_tiles=candidate_instances,
            evidence_tile_ids=evidence_tile_ids,
            answer_value=str(OPTION_LABELS[int(target_label_index)]),
            reference_tile_id=reference_tile_id,
            open_end_value=int(open_end_value),
            reference_sum=int(oriented_chain[-1][0] + oriented_chain[-1][1]),
            target_total=None,
            first_step_tile_id=str(first_step_tile_id),
            second_step_tile_id=str(second_step_tile_id),
            bridge_value=int(bridge_value),
            chain_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "is_reference": bool(tile.is_reference),
                    "option_label": None if tile.option_label is None else str(tile.option_label),
                }
                for tile in chain_instances
            ),
            candidate_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "option_label": None if tile.option_label is None else str(tile.option_label),
                    "is_first_step": bool(str(tile.tile_id) == str(first_step_tile_id)),
                    "is_answer": bool(str(tile.tile_id) == str(second_step_tile_id)),
                }
                for tile in candidate_instances
            ),
        )
    raise ValueError("unable to sample two-step extension domino scene")


def _sample_scene(
    rng,
    *,
    axes: _ResolvedAxes,
    params: Mapping[str, Any],
) -> _SampledDominoScene:
    """Sample one domino scene for the active query family."""

    if str(axes.query_id) == "matching_end_count":
        return _sample_matching_end_scene(
            rng,
            candidate_count=int(axes.candidate_count),
            target_answer=int(axes.target_answer),
        )
    if str(axes.query_id) == "higher_sum_than_reference_count":
        return _sample_higher_sum_scene(
            rng,
            candidate_count=int(axes.candidate_count),
            target_answer=int(axes.target_answer),
        )
    if str(axes.query_id) == "sum_to_target_count":
        return _sample_sum_to_target_scene(
            rng,
            candidate_count=int(axes.candidate_count),
            target_answer=int(axes.target_answer),
            params=params,
        )
    if str(axes.query_id) == TWO_STEP_QUERY_ID:
        return _sample_two_step_extension_scene(
            rng,
            candidate_count=int(axes.candidate_count),
            target_answer=int(axes.target_answer),
        )
    return _sample_double_scene(
        rng,
        candidate_count=int(axes.candidate_count),
        target_answer=int(axes.target_answer),
    )


def _build_prompt_json_examples(*, query_id: str) -> Tuple[str, str]:
    """Return prompt JSON examples matching the active domino query semantics."""

    if str(query_id) == "matching_end_count":
        answer_and_evidence = {
            "evidence": [
                [248, 318, 386, 394],
                [408, 318, 546, 394],
            ],
            "answer": 2,
        }
        answer_only = {"answer": 2}
    elif str(query_id) == "higher_sum_than_reference_count":
        answer_and_evidence = {
            "evidence": [
                [248, 318, 386, 394],
                [408, 318, 546, 394],
                [568, 318, 706, 394],
            ],
            "answer": 3,
        }
        answer_only = {"answer": 3}
    elif str(query_id) == "sum_to_target_count":
        answer_and_evidence = {
            "evidence": [
                [248, 318, 386, 394],
                [408, 318, 546, 394],
                [568, 318, 706, 394],
            ],
            "answer": 3,
        }
        answer_only = {"answer": 3}
    elif str(query_id) == TWO_STEP_QUERY_ID:
        answer_and_evidence = {
            "evidence": [
                [248, 318, 386, 394],
                [408, 318, 546, 394],
            ],
            "answer": "B",
        }
        answer_only = {"answer": "B"}
    else:
        answer_and_evidence = {
            "evidence": [
                [248, 318, 386, 394],
                [408, 318, 546, 394],
            ],
            "answer": 2,
        }
        answer_only = {"answer": 2}
    return (
        json.dumps(answer_and_evidence, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> DominoRenderParams:
    """Resolve domino-scene rendering parameters from config/defaults."""

    return DominoRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        chain_top_px=int(params.get("chain_top_px", group_default(_RENDER_DEFAULTS, "chain_top_px", _DEFAULTS.chain_top_px))),
        tile_width_px=int(params.get("tile_width_px", group_default(_RENDER_DEFAULTS, "tile_width_px", _DEFAULTS.tile_width_px))),
        tile_height_px=int(params.get("tile_height_px", group_default(_RENDER_DEFAULTS, "tile_height_px", _DEFAULTS.tile_height_px))),
        chain_gap_px=int(params.get("chain_gap_px", group_default(_RENDER_DEFAULTS, "chain_gap_px", _DEFAULTS.chain_gap_px))),
        candidate_gap_px=int(
            params.get("candidate_gap_px", group_default(_RENDER_DEFAULTS, "candidate_gap_px", _DEFAULTS.candidate_gap_px))
        ),
        row_gap_px=int(params.get("row_gap_px", group_default(_RENDER_DEFAULTS, "row_gap_px", _DEFAULTS.row_gap_px))),
        tile_corner_radius_px=int(
            params.get(
                "tile_corner_radius_px",
                group_default(_RENDER_DEFAULTS, "tile_corner_radius_px", _DEFAULTS.tile_corner_radius_px),
            )
        ),
        pip_radius_px=int(params.get("pip_radius_px", group_default(_RENDER_DEFAULTS, "pip_radius_px", _DEFAULTS.pip_radius_px))),
        divider_width_px=int(
            params.get("divider_width_px", group_default(_RENDER_DEFAULTS, "divider_width_px", _DEFAULTS.divider_width_px))
        ),
        reference_tag_font_size_px=int(
            params.get(
                "reference_tag_font_size_px",
                group_default(_RENDER_DEFAULTS, "reference_tag_font_size_px", _DEFAULTS.reference_tag_font_size_px),
            )
        ),
        reference_tag_gap_px=int(
            params.get(
                "reference_tag_gap_px",
                group_default(_RENDER_DEFAULTS, "reference_tag_gap_px", _DEFAULTS.reference_tag_gap_px),
            )
        ),
        section_label_font_size_px=int(
            params.get(
                "section_label_font_size_px",
                group_default(_RENDER_DEFAULTS, "section_label_font_size_px", _DEFAULTS.section_label_font_size_px),
            )
        ),
        section_separator_width_px=int(
            params.get(
                "section_separator_width_px",
                group_default(_RENDER_DEFAULTS, "section_separator_width_px", _DEFAULTS.section_separator_width_px),
            )
        ),
        layout_jitter_meta=resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.dominoes.layout",
        ),
    )


class GamesDominoesChainCountTask:
    """Return one grounded counting query over a visible domino chain scene."""

    task_id = TASK_ID
    domain = "games"
    task_group = "dominoes"
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(
            int(instance_seed),
            params=params,
            supported_query_ids=tuple(str(value) for value in self.supported_query_ids),
        )
        render_params = _render_params(params, instance_seed=int(instance_seed))

        sampled_scene: _SampledDominoScene | None = None
        rendered_scene = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(attempt_rng, axes=axes, params=params)
            except ValueError:
                continue

            background, background_meta = make_background_canvas(
                canvas_width=int(render_params.canvas_width),
                canvas_height=int(render_params.canvas_height),
                instance_seed=int(instance_seed),
                params=params,
                default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
            )
            rendered_scene = render_domino_chain_scene(
                chain_tiles=list(sampled_scene.chain_tiles),
                candidate_tiles=list(sampled_scene.candidate_tiles),
                background=background,
                scene_variant=str(axes.scene_variant),
                style_variant=str(axes.style_variant),
                params=render_params,
            )
            break

        if sampled_scene is None or rendered_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")

        evidence_bboxes = [
            list(rendered_scene.render_map["domino_bboxes_px"][str(tile_id)])
            for tile_id in sampled_scene.evidence_tile_ids
        ]
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
                "object_description_single_row",
                "object_description_two_row",
                "connection_rule_text",
                "pip_sum_rule_text",
                "double_rule_text",
                "two_step_rule_text",
                "answer_hint_matching_end_count",
                "answer_hint_higher_sum_than_reference_count",
                "answer_hint_sum_to_target_count",
                "answer_hint_double_count",
                "answer_hint_two_step_extension_label",
                "evidence_hint_matching_end_count",
                "evidence_hint_higher_sum_than_reference_count",
                "evidence_hint_sum_to_target_count",
                "evidence_hint_double_count",
                "evidence_hint_two_step_extension_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(query_id=str(axes.query_id))
        prompt_slots = {
            "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
            "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_id)}"]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
            "connection_rule_text": str(prompt_defaults["connection_rule_text"]),
            "pip_sum_rule_text": str(prompt_defaults["pip_sum_rule_text"]),
            "double_rule_text": str(prompt_defaults["double_rule_text"]),
            "two_step_rule_text": str(prompt_defaults["two_step_rule_text"]),
            "target_total_text": "" if sampled_scene.target_total is None else str(sampled_scene.target_total),
        }
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots=prompt_slots,
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = (
            TypedValue(type="string", value=str(sampled_scene.answer_value))
            if str(axes.query_id) == TWO_STEP_QUERY_ID
            else TypedValue(type="integer", value=int(sampled_scene.answer_value))
        )
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        complexity = build_games_dominoes_chain_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            candidate_count=int(axes.candidate_count),
            target_answer=int(axes.target_answer),
            evidence_count=len(sampled_scene.evidence_tile_ids),
        )

        execution_trace = {
            "scene_variant": str(axes.scene_variant),
            "query_id": str(axes.query_id),
            "style_variant": str(axes.style_variant),
            "target_answer": sampled_scene.answer_value,
            "target_answer_index": int(axes.target_answer),
            "target_answer_support": [int(value) for value in axes.target_answer_support],
            "candidate_count": int(axes.candidate_count),
            "candidate_count_support": [int(value) for value in axes.candidate_count_support],
            "reference_tile_id": None if sampled_scene.reference_tile_id is None else str(sampled_scene.reference_tile_id),
            "open_end_value": None if sampled_scene.open_end_value is None else int(sampled_scene.open_end_value),
            "reference_sum": None if sampled_scene.reference_sum is None else int(sampled_scene.reference_sum),
            "target_total": None if sampled_scene.target_total is None else int(sampled_scene.target_total),
            "first_step_tile_id": None if sampled_scene.first_step_tile_id is None else str(sampled_scene.first_step_tile_id),
            "second_step_tile_id": None if sampled_scene.second_step_tile_id is None else str(sampled_scene.second_step_tile_id),
            "bridge_value": None if sampled_scene.bridge_value is None else int(sampled_scene.bridge_value),
            "chain_tile_specs": [dict(spec) for spec in sampled_scene.chain_tile_specs],
            "candidate_tile_specs": [dict(spec) for spec in sampled_scene.candidate_tile_specs],
            "evidence_entity_ids": [str(tile_id) for tile_id in sampled_scene.evidence_tile_ids],
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_dominoes_chain_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "candidate_count": int(axes.candidate_count),
                    "target_answer": sampled_scene.answer_value,
                    "target_answer_index": int(axes.target_answer),
                    "reference_tile_id": None if sampled_scene.reference_tile_id is None else str(sampled_scene.reference_tile_id),
                    "evidence_entity_ids": [str(tile_id) for tile_id in sampled_scene.evidence_tile_ids],
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
                    "style_variant": str(axes.style_variant),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "target_answer": sampled_scene.answer_value,
                    "target_answer_index": int(axes.target_answer),
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    "candidate_count": int(axes.candidate_count),
                    "candidate_count_support": [int(value) for value in axes.candidate_count_support],
                    "candidate_count_probabilities": dict(axes.candidate_count_probabilities),
                    "target_total": None if sampled_scene.target_total is None else int(sampled_scene.target_total),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": execution_trace,
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(tile_id) for tile_id in sampled_scene.evidence_tile_ids],
            },
            "projected_evidence": {
                "bbox_set": [list(bbox) for bbox in evidence_bboxes],
            },
            "background": background_meta,
            "post_image_noise": post_noise_meta,
        }
        output = TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id="dominoes",
            query_id=str(axes.query_id),
        )
        return rewrite_public_query_output(
            output,
            query_id=str(axes.query_id),
            query_id_probabilities=axes.query_id_probabilities,
        )


@register_task
class GamesDominoesPropertyCountTask(GamesDominoesChainCountTask):
    """Count loose dominoes satisfying one sampled property query."""

    task_id = "task_games__dominoes__property_count"


@register_task
class GamesDominoesTwoStepExtensionLabelTask(GamesDominoesChainCountTask):
    """Choose the labeled loose domino that works as the second step in a chain extension."""

    task_id = "task_games__dominoes__two_step_extension_label"
    supported_query_ids = TWO_STEP_SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        forced_params = dict(params)
        forced_params["query_id"] = TWO_STEP_QUERY_ID
        target_answer = forced_params.get("target_answer")
        if isinstance(target_answer, str) and len(target_answer) == 1 and target_answer.isalpha():
            forced_params["target_answer"] = ord(target_answer.upper()) - ord("A")
        forced_params.setdefault("two_step_extension_target_answer_support", [0, 1, 2, 3, 4])
        forced_params.setdefault("single_row_candidate_count_support", [5, 6])
        forced_params.setdefault("two_row_candidate_count_support", [5, 6])
        return super().generate(int(instance_seed), params=forced_params, max_attempts=int(max_attempts))


__all__ = [
    "GamesDominoesPropertyCountTask",
    "GamesDominoesTwoStepExtensionLabelTask",
]
