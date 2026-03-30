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
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.complexity import build_games_dominoes_chain_complexity
from ..shared.domino_scene import DominoRenderParams, DominoTileInstance, render_domino_chain_scene
from ..shared.style import SUPPORTED_GAMES_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_background_defaults, load_games_noise_defaults


TASK_ID = "task_games_dominoes_chain_count"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "single_row",
    "two_row",
)
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    "matching_end_count",
    "higher_sum_than_reference_count",
    "sum_to_target_count",
    "double_count",
)
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


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one domino scene."""

    query_variant: str
    scene_variant: str
    style_variant: str
    target_answer: int
    target_answer_support: Tuple[int, ...]
    candidate_count: int
    candidate_count_support: Tuple[int, ...]
    query_variant_probabilities: Dict[str, float]
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
    reference_tile_id: str | None
    open_end_value: int | None
    reference_sum: int | None
    target_total: int | None
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
) -> DominoTileInstance:
    """Build one rendered domino tile payload from oriented half values."""

    return DominoTileInstance(
        tile_id=str(tile_id),
        left_value=int(oriented_tile[0]),
        right_value=int(oriented_tile[1]),
        role=str(role),
        is_reference=bool(is_reference),
        highlight_right_half=bool(highlight_right_half),
    )


def _resolve_query_variant(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced semantic query variant, honoring `task_variant` as an alias."""

    alias_params = dict(params)
    if alias_params.get("query_variant") is None and alias_params.get("task_variant") is not None:
        alias_params["query_variant"] = alias_params["task_variant"]
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query_variant")
    selected, probabilities = resolve_variant(
        rng,
        params=alias_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_QUERY_VARIANTS,
        explicit_key="query_variant",
        weights_key="query_variant_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=alias_params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_QUERY_VARIANTS,
        balance_flag_key="balanced_query_variant_sampling",
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        sampling_namespace=f"{TASK_ID}.query_variant",
    )
    return str(selected), dict(probabilities)


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

    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{str(namespace)}")
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=[str(item) for item in supported],
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=[str(item) for item in supported],
        balance_flag_key=str(balance_flag_key),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        sampling_namespace=f"{TASK_ID}.{str(namespace)}",
    )
    return str(selected), dict(probabilities)


def _target_support_key(query_variant: str) -> str:
    """Return the configured answer-support key for one query variant."""

    return {
        "matching_end_count": "matching_end_target_answer_support",
        "higher_sum_than_reference_count": "higher_sum_target_answer_support",
        "sum_to_target_count": "sum_to_target_answer_support",
        "double_count": "double_target_answer_support",
    }[str(query_variant)]


def _candidate_count_support_key(scene_variant: str) -> str:
    """Return the configured visible candidate-count support key for one layout family."""

    return {
        "single_row": "single_row_candidate_count_support",
        "two_row": "two_row_candidate_count_support",
    }[str(scene_variant)]


def _feasible_candidate_count_support(
    *,
    query_variant: str,
    target_answer: int,
    raw_support: Sequence[int],
) -> Tuple[int, ...]:
    """Return the subset of candidate-count support that can realize the active query."""

    feasible: List[int] = []
    for raw_value in raw_support:
        candidate_count = int(raw_value)
        minimum = int(target_answer)
        if str(query_variant) == "sum_to_target_count" and int(target_answer) == 0:
            minimum = 7
        if int(candidate_count) < max(7, int(minimum)):
            continue
        feasible.append(int(candidate_count))
    return tuple(int(value) for value in feasible)


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve semantic/visual axes plus target answer and visible candidate count."""

    query_variant, query_variant_probabilities = _resolve_query_variant(
        instance_seed=int(instance_seed),
        params=params,
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_GAMES_STYLE_VARIANTS,
    )

    target_support_key = _target_support_key(str(query_variant))
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(target_support_key),
        explicit_key="target_answer",
        fallback_support=getattr(_DEFAULTS, target_support_key),
        namespace=f"{TASK_ID}.target_answer.{str(query_variant)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_explicit_sampling_index=True,
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
        query_variant=str(query_variant),
        target_answer=int(target_answer),
        raw_support=raw_candidate_count_support,
    )
    if not candidate_count_support:
        raise ValueError(
            f"no feasible candidate_count values remain for {query_variant}/{scene_variant} at target {target_answer}"
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
        namespace=f"{TASK_ID}.candidate_count.{str(scene_variant)}.{str(query_variant)}",
        balanced_flag_key="balanced_candidate_count_sampling",
        namespace_explicit_sampling_index=True,
    )

    return _ResolvedAxes(
        query_variant=str(query_variant),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        candidate_count=int(candidate_count),
        candidate_count_support=tuple(int(value) for value in candidate_count_support),
        query_variant_probabilities=dict(query_variant_probabilities),
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

    shuffled_candidates = list(candidate_tiles)
    rng.shuffle(shuffled_candidates)
    for index, canonical_tile in enumerate(shuffled_candidates, start=1):
        tile_id = f"candidate_{index:02d}"
        candidate_instances.append(
            _build_tile_instance(
                tile_id=str(tile_id),
                oriented_tile=_random_orientation(rng, tile=canonical_tile),
                role="candidate",
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
            reference_tile_id=reference_tile_id,
            open_end_value=int(open_end_value),
            reference_sum=int(oriented_chain[-1][0] + oriented_chain[-1][1]),
            target_total=None,
            chain_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "is_reference": bool(tile.is_reference),
                }
                for tile in chain_instances
            ),
            candidate_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
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
            reference_tile_id=reference_tile_id,
            open_end_value=None,
            reference_sum=int(reference_sum),
            target_total=None,
            chain_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "is_reference": bool(tile.is_reference),
                }
                for tile in chain_instances
            ),
            candidate_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
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
            reference_tile_id=reference_tile_id,
            open_end_value=None,
            reference_sum=None,
            target_total=int(target_total),
            chain_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "is_reference": bool(tile.is_reference),
                }
                for tile in chain_instances
            ),
            candidate_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
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
            reference_tile_id=reference_tile_id,
            open_end_value=None,
            reference_sum=None,
            target_total=None,
            chain_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                    "is_reference": bool(tile.is_reference),
                }
                for tile in chain_instances
            ),
            candidate_tile_specs=tuple(
                {
                    "tile_id": str(tile.tile_id),
                    "left_value": int(tile.left_value),
                    "right_value": int(tile.right_value),
                    "role": str(tile.role),
                }
                for tile in candidate_instances
            ),
        )
    raise ValueError("unable to sample double-count domino scene")


def _sample_scene(
    rng,
    *,
    axes: _ResolvedAxes,
    params: Mapping[str, Any],
) -> _SampledDominoScene:
    """Sample one domino scene for the active query family."""

    if str(axes.query_variant) == "matching_end_count":
        return _sample_matching_end_scene(
            rng,
            candidate_count=int(axes.candidate_count),
            target_answer=int(axes.target_answer),
        )
    if str(axes.query_variant) == "higher_sum_than_reference_count":
        return _sample_higher_sum_scene(
            rng,
            candidate_count=int(axes.candidate_count),
            target_answer=int(axes.target_answer),
        )
    if str(axes.query_variant) == "sum_to_target_count":
        return _sample_sum_to_target_scene(
            rng,
            candidate_count=int(axes.candidate_count),
            target_answer=int(axes.target_answer),
            params=params,
        )
    return _sample_double_scene(
        rng,
        candidate_count=int(axes.candidate_count),
        target_answer=int(axes.target_answer),
    )


def _build_prompt_json_examples(*, query_variant: str) -> Tuple[str, str]:
    """Return prompt JSON examples matching the active domino query semantics."""

    if str(query_variant) == "matching_end_count":
        answer_and_evidence = {
            "evidence": [
                [248, 318, 386, 394],
                [408, 318, 546, 394],
            ],
            "answer": 2,
        }
        answer_only = {"answer": 2}
    elif str(query_variant) == "higher_sum_than_reference_count":
        answer_and_evidence = {
            "evidence": [
                [248, 318, 386, 394],
                [408, 318, 546, 394],
                [568, 318, 706, 394],
            ],
            "answer": 3,
        }
        answer_only = {"answer": 3}
    elif str(query_variant) == "sum_to_target_count":
        answer_and_evidence = {
            "evidence": [
                [248, 318, 386, 394],
                [408, 318, 546, 394],
                [568, 318, 706, 394],
            ],
            "answer": 3,
        }
        answer_only = {"answer": 3}
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


def _render_params(params: Mapping[str, Any]) -> DominoRenderParams:
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
    )


@register_task
class GamesDominoesChainCountTask:
    """Return one grounded counting query over a visible domino chain scene."""

    task_id = TASK_ID
    domain = "games"
    task_group = "dominoes"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params)

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
                "task_family_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_single_row",
                "object_description_two_row",
                "connection_rule_text",
                "pip_sum_rule_text",
                "double_rule_text",
                "answer_hint_matching_end_count",
                "answer_hint_higher_sum_than_reference_count",
                "answer_hint_sum_to_target_count",
                "answer_hint_double_count",
                "evidence_hint_matching_end_count",
                "evidence_hint_higher_sum_than_reference_count",
                "evidence_hint_sum_to_target_count",
                "evidence_hint_double_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(query_variant=str(axes.query_variant))
        prompt_slots = {
            "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_variant)}"]),
            "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_variant)}"]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
            "connection_rule_text": str(prompt_defaults["connection_rule_text"]),
            "pip_sum_rule_text": str(prompt_defaults["pip_sum_rule_text"]),
            "double_rule_text": str(prompt_defaults["double_rule_text"]),
            "target_total_text": "" if sampled_scene.target_total is None else str(sampled_scene.target_total),
        }
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            task_variant_key=str(axes.query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots=prompt_slots,
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(axes.target_answer))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        complexity = build_games_dominoes_chain_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            scene_variant=str(axes.scene_variant),
            query_variant=str(axes.query_variant),
            candidate_count=int(axes.candidate_count),
            target_answer=int(axes.target_answer),
            evidence_count=len(sampled_scene.evidence_tile_ids),
        )

        execution_trace = {
            "scene_variant": str(axes.scene_variant),
            "query_variant": str(axes.query_variant),
            "task_variant": str(axes.query_variant),
            "style_variant": str(axes.style_variant),
            "target_answer": int(axes.target_answer),
            "target_answer_support": [int(value) for value in axes.target_answer_support],
            "candidate_count": int(axes.candidate_count),
            "candidate_count_support": [int(value) for value in axes.candidate_count_support],
            "reference_tile_id": None if sampled_scene.reference_tile_id is None else str(sampled_scene.reference_tile_id),
            "open_end_value": None if sampled_scene.open_end_value is None else int(sampled_scene.open_end_value),
            "reference_sum": None if sampled_scene.reference_sum is None else int(sampled_scene.reference_sum),
            "target_total": None if sampled_scene.target_total is None else int(sampled_scene.target_total),
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
                    "query_variant": str(axes.query_variant),
                    "task_variant": str(axes.query_variant),
                    "style_variant": str(axes.style_variant),
                    "candidate_count": int(axes.candidate_count),
                    "target_answer": int(axes.target_answer),
                    "reference_tile_id": None if sampled_scene.reference_tile_id is None else str(sampled_scene.reference_tile_id),
                    "evidence_entity_ids": [str(tile_id) for tile_id in sampled_scene.evidence_tile_ids],
                },
            },
            "query_spec": {
                "task_variant": str(axes.query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_variant": str(axes.scene_variant),
                    "query_variant": str(axes.query_variant),
                    "task_variant": str(axes.query_variant),
                    "style_variant": str(axes.style_variant),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_variant_probabilities": dict(axes.query_variant_probabilities),
                    "task_variant_probabilities": dict(axes.query_variant_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "target_answer": int(axes.target_answer),
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
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": execution_trace,
            "witness_symbolic": {
                "type": "id_set",
                "ids": [str(tile_id) for tile_id in sampled_scene.evidence_tile_ids],
            },
            "projected_evidence": {
                "bbox_set": [list(bbox) for bbox in evidence_bboxes],
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
            task_variant=str(axes.query_variant),
        )


__all__ = ["GamesDominoesChainCountTask"]
