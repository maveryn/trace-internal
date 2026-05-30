"""Games cards task for grounded hand-analysis counting queries."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.font_assets import get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.card_scene import CardInstance, CardRenderParams, render_cards_hand_scene
from ..shared.complexity import build_games_cards_hand_complexity
from ..shared.fixed_query_task import FixedQueryVariantTaskMixin, QuerySubsetTaskMixin
from ..shared.layout import resolve_games_layout_jitter
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.style import SUPPORTED_CARD_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_background_defaults, load_games_noise_defaults


TASK_ID = "games_cards_hand_count_base"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "multi_row",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "same_suit_as_reference_count",
    "higher_than_reference_count",
    "exact_triple_count",
    "longest_run_length",
)
RANK_VALUES: Tuple[int, ...] = tuple(range(2, 15))
RANK_LABEL_BY_VALUE: Dict[int, str] = {
    **{value: str(value) for value in range(2, 11)},
    11: "J",
    12: "Q",
    13: "K",
    14: "A",
}
SUIT_NAMES: Tuple[str, ...] = (
    "spades",
    "hearts",
    "diamonds",
    "clubs",
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible card-hand scenes."""

    same_suit_target_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    same_suit_order_by_suit: bool = True
    higher_rank_target_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    higher_rank_order_by_rank: bool = True
    higher_rank_center_label_mode: str = "rank_suit"
    exact_triple_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    exact_triple_count_order_by_rank: bool = True
    exact_triple_count_center_label_mode: str = "rank_suit"
    longest_run_length_support: Tuple[int, ...] = (2, 3, 4, 5, 6)
    longest_run_center_label_mode: str = "rank_suit"
    card_count_support: Tuple[int, ...] = tuple(range(16, 41))
    canvas_width: int = 1180
    canvas_height: int = 760
    card_width_px: int = 84
    card_height_px: int = 122
    panel_margin_px: int = 42
    card_gap_px: int = 12
    row_gap_px: int = 22
    card_corner_radius_px: int = 12
    rank_font_size_px: int = 19
    center_symbol_font_size_px: int = 44
    reference_banner_height_px: int = 20
    reference_font_size_px: int = 14
    continuation_font_size_px: int = 22
    continuation_gap_px: int = 28
    max_cards_per_row: int = 8


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one hand-analysis scene."""

    query_id: str
    scene_variant: str
    style_variant: str
    target_answer: int
    target_answer_support: Tuple[int, ...]
    card_count: int
    card_count_support: Tuple[int, ...]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]
    card_count_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _SampledHand:
    """Constructed visible hand plus query-specific witness metadata."""

    cards: Tuple[CardInstance, ...]
    evidence_card_ids: Tuple[str, ...]
    reference_card_id: str | None
    reference_rank_value: int | None
    reference_rank_label: str | None
    reference_suit_name: str | None
    rank_sequence: Tuple[int, ...]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "cards")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_games_background_defaults(task_group="cards")
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="cards", apply_prob=0.0)


def _resolve_query_id(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
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
        supported_variants=SUPPORTED_QUERY_IDS,
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
    """Resolve one balanced named axis for the games cards task."""

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
        "same_suit_as_reference_count": "same_suit_target_answer_support",
        "higher_than_reference_count": "higher_rank_target_answer_support",
        "exact_triple_count": "exact_triple_count_support",
        "longest_run_length": "longest_run_length_support",
    }[str(query_id)]


def _uses_uniform_query_cycle(params: Mapping[str, Any], probabilities: Mapping[str, float]) -> bool:
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
    if len(positives) != len(SUPPORTED_QUERY_IDS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _target_answer_params_for_query_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Use a per-query occurrence index for balanced target-answer cycling.

    The raw build `_sample_cursor` also drives uniform query-id cycling.
    For cards, reference-count variants have 6 answer values while the query
    cycle has 4 variants; using the raw index for both axes only visits half of
    those answer values. Once the active query has been selected, floor-dividing
    by the number of query ids yields the occurrence index inside that
    variant and keeps target-answer support broad for each query.
    """

    target_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return target_params
    if not _uses_uniform_query_cycle(params, query_id_probabilities):
        return target_params
    target_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_QUERY_IDS))
    return target_params


def _rank_multiplicities_without_exact_count(*, forbidden_count: int) -> Tuple[int, ...]:
    """Return possible per-rank card counts excluding one exact multiplicity."""

    return tuple(
        int(count)
        for count in range(0, len(SUIT_NAMES) + 1)
        if int(count) != int(forbidden_count)
    )


def _can_fill_rank_counts_without_exact_count(
    *,
    rank_count: int,
    total_count: int,
    forbidden_count: int,
) -> bool:
    """Return whether ranks can fill `total_count` cards without a forbidden exact count."""

    possible = {0}
    allowed_counts = _rank_multiplicities_without_exact_count(forbidden_count=int(forbidden_count))
    for _ in range(int(rank_count)):
        possible = {
            int(current + count)
            for current in possible
            for count in allowed_counts
            if int(current + count) <= int(total_count)
        }
    return int(total_count) in possible


def _can_fill_non_triple_rank_counts(*, rank_count: int, total_count: int) -> bool:
    """Return whether non-triple ranks can contribute `total_count` cards without exact triples."""

    return _can_fill_rank_counts_without_exact_count(
        rank_count=int(rank_count),
        total_count=int(total_count),
        forbidden_count=3,
    )


def _feasible_card_count_support(
    *,
    query_id: str,
    target_answer: int,
    raw_support: Sequence[int],
) -> Tuple[int, ...]:
    """Return the subset of card-count support that can realize the active query."""

    feasible: List[int] = []
    for raw_value in raw_support:
        card_count = int(raw_value)
        if str(query_id) == "exact_triple_count":
            if int(card_count) < 3 * int(target_answer):
                continue
            if not _can_fill_non_triple_rank_counts(
                rank_count=int(len(RANK_VALUES) - int(target_answer)),
                total_count=int(card_count) - (3 * int(target_answer)),
            ):
                continue
        elif str(query_id) == "longest_run_length":
            if int(card_count) < int(target_answer):
                continue
        else:
            if int(card_count) < int(target_answer) + 1:
                continue
        feasible.append(int(card_count))
    return tuple(int(value) for value in feasible)


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve semantic/visual axes plus target answer and visible-card count."""

    query_id, query_id_probabilities = _resolve_query_id(
        instance_seed=int(instance_seed),
        params=params,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_CARD_STYLE_VARIANTS,
    )

    target_support_key = _target_support_key(str(query_id))
    target_params = _target_answer_params_for_query_cycle(
        params,
        query_id_probabilities=query_id_probabilities,
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

    query_card_count_support_key = f"{str(query_id)}_card_count_support"
    card_count_support_key = (
        str(query_card_count_support_key)
        if str(query_card_count_support_key) in params or str(query_card_count_support_key) in _GEN_DEFAULTS
        else "card_count_support"
    )
    raw_card_count_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=str(card_count_support_key),
        fallback=_DEFAULTS.card_count_support,
    )
    card_count_support = _feasible_card_count_support(
        query_id=str(query_id),
        target_answer=int(target_answer),
        raw_support=raw_card_count_support,
    )
    if not card_count_support:
        raise ValueError(
            f"no feasible card_count values remain for {query_id} at target {target_answer}"
        )
    card_params = dict(params)
    card_params["card_count_support"] = list(int(value) for value in card_count_support)
    card_count, card_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=card_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="card_count_support",
        explicit_key="card_count",
        fallback_support=card_count_support,
        namespace=f"{TASK_ID}.card_count.{str(query_id)}",
        balanced_flag_key="balanced_card_count_sampling",
        namespace_support_permutation=True,
    )
    scene_variant = "multi_row"
    scene_variant_probabilities = {"multi_row": 1.0}

    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        card_count=int(card_count),
        card_count_support=tuple(int(value) for value in card_count_support),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
        card_count_probabilities=dict(card_count_probabilities),
    )


def _make_deck() -> List[Tuple[int, str]]:
    """Return the canonical 52-card deck as `(rank_value, suit_name)` tuples."""

    return [(int(rank_value), str(suit_name)) for suit_name in SUIT_NAMES for rank_value in RANK_VALUES]


def _label_card(
    *,
    card_id: str,
    rank_value: int,
    suit_name: str,
    is_reference: bool,
) -> CardInstance:
    """Build one rendered card payload from rank/suit metadata."""

    return CardInstance(
        card_id=str(card_id),
        rank_label=str(RANK_LABEL_BY_VALUE[int(rank_value)]),
        rank_value=int(rank_value),
        suit_name=str(suit_name),
        is_reference=bool(is_reference),
    )


def _sample_same_suit_hand(
    rng,
    *,
    card_count: int,
    target_answer: int,
    order_by_suit: bool,
) -> _SampledHand:
    """Sample one hand with exactly `target_answer` cards matching the reference suit."""

    reference_suit = str(SUIT_NAMES[int(rng.randrange(len(SUIT_NAMES)))])
    reference_rank = int(RANK_VALUES[int(rng.randrange(len(RANK_VALUES)))])
    reference_card = (int(reference_rank), str(reference_suit))
    same_suit_pool = [(int(rank), str(reference_suit)) for rank in RANK_VALUES if int(rank) != int(reference_rank)]
    matching_cards = list(rng.sample(same_suit_pool, int(target_answer)))
    other_pool = [(int(rank), str(suit)) for rank, suit in _make_deck() if str(suit) != str(reference_suit)]
    filler_cards = list(rng.sample(other_pool, int(card_count) - 1 - int(target_answer)))
    ordered = matching_cards + filler_cards + [reference_card]
    if bool(order_by_suit):
        suit_order = {str(suit_name): int(index) for index, suit_name in enumerate(SUIT_NAMES)}
        ordered.sort(key=lambda item: (int(suit_order[str(item[1])]), int(item[0])))
    else:
        rng.shuffle(ordered)
    cards: List[CardInstance] = []
    evidence_card_ids: List[str] = []
    reference_card_id: str | None = None
    for index, (rank_value, suit_name) in enumerate(ordered, start=1):
        is_reference = bool((int(rank_value), str(suit_name)) == reference_card and reference_card_id is None)
        card_id = f"card_{index:02d}"
        cards.append(
            _label_card(
                card_id=str(card_id),
                rank_value=int(rank_value),
                suit_name=str(suit_name),
                is_reference=bool(is_reference),
            )
        )
        if bool(is_reference):
            reference_card_id = str(card_id)
        elif str(suit_name) == str(reference_suit):
            evidence_card_ids.append(str(card_id))
    if reference_card_id is None:
        raise ValueError("same-suit hand must contain one reference card")
    return _SampledHand(
        cards=tuple(cards),
        evidence_card_ids=tuple(evidence_card_ids),
        reference_card_id=str(reference_card_id),
        reference_rank_value=int(reference_rank),
        reference_rank_label=str(RANK_LABEL_BY_VALUE[int(reference_rank)]),
        reference_suit_name=str(reference_suit),
        rank_sequence=tuple(int(card.rank_value) for card in cards),
    )


def _sample_higher_rank_hand(
    rng,
    *,
    card_count: int,
    target_answer: int,
    order_by_rank: bool,
) -> _SampledHand:
    """Sample one hand with exactly `target_answer` cards ranked above the reference card."""

    feasible_reference_ranks: List[int] = []
    required_not_higher = int(card_count) - 1 - int(target_answer)
    for rank_value in RANK_VALUES:
        higher_count = sum(1 for candidate_rank, _ in _make_deck() if int(candidate_rank) > int(rank_value))
        not_higher_count = sum(
            1
            for candidate_rank, _ in _make_deck()
            if int(candidate_rank) < int(rank_value)
        ) + 3
        if int(higher_count) >= int(target_answer) and int(not_higher_count) >= int(required_not_higher):
            feasible_reference_ranks.append(int(rank_value))
    if not feasible_reference_ranks:
        raise ValueError("no feasible reference rank for higher-than query")
    reference_rank = int(feasible_reference_ranks[int(rng.randrange(len(feasible_reference_ranks)))])
    reference_suit = str(SUIT_NAMES[int(rng.randrange(len(SUIT_NAMES)))])
    reference_card = (int(reference_rank), str(reference_suit))
    higher_pool = [(int(rank), str(suit)) for rank, suit in _make_deck() if int(rank) > int(reference_rank)]
    lower_equal_pool = [
        (int(rank), str(suit))
        for rank, suit in _make_deck()
        if (int(rank), str(suit)) != reference_card and int(rank) <= int(reference_rank)
    ]
    higher_cards = list(rng.sample(higher_pool, int(target_answer)))
    lower_equal_cards = list(rng.sample(lower_equal_pool, int(required_not_higher)))
    ordered = higher_cards + lower_equal_cards + [reference_card]
    if bool(order_by_rank):
        suit_order = {str(suit_name): int(index) for index, suit_name in enumerate(SUIT_NAMES)}
        ordered.sort(key=lambda item: (int(item[0]), int(suit_order[str(item[1])])))
    else:
        rng.shuffle(ordered)
    cards: List[CardInstance] = []
    evidence_card_ids: List[str] = []
    reference_card_id: str | None = None
    for index, (rank_value, suit_name) in enumerate(ordered, start=1):
        is_reference = bool((int(rank_value), str(suit_name)) == reference_card and reference_card_id is None)
        card_id = f"card_{index:02d}"
        cards.append(
            _label_card(
                card_id=str(card_id),
                rank_value=int(rank_value),
                suit_name=str(suit_name),
                is_reference=bool(is_reference),
            )
        )
        if bool(is_reference):
            reference_card_id = str(card_id)
        elif int(rank_value) > int(reference_rank):
            evidence_card_ids.append(str(card_id))
    if reference_card_id is None:
        raise ValueError("higher-rank hand must contain one reference card")
    return _SampledHand(
        cards=tuple(cards),
        evidence_card_ids=tuple(evidence_card_ids),
        reference_card_id=str(reference_card_id),
        reference_rank_value=int(reference_rank),
        reference_rank_label=str(RANK_LABEL_BY_VALUE[int(reference_rank)]),
        reference_suit_name=str(reference_suit),
        rank_sequence=tuple(int(card.rank_value) for card in cards),
    )


def _sample_exact_triple_count_hand(
    rng,
    *,
    card_count: int,
    target_answer: int,
    order_by_rank: bool,
) -> _SampledHand:
    """Sample one hand with exactly `target_answer` distinct exact triples."""

    triple_rank_count = int(target_answer)
    if int(card_count) < 3 * int(triple_rank_count):
        raise ValueError("exact-triple hand requires enough cards to realize the requested triples")
    triple_ranks = list(rng.sample(list(RANK_VALUES), int(triple_rank_count)))
    remaining_ranks = [
        int(rank_value)
        for rank_value in RANK_VALUES
        if int(rank_value) not in set(triple_ranks)
    ]
    filler_count = int(card_count) - (3 * int(triple_rank_count))
    filler_rank_counts = _sample_non_triple_rank_counts(
        rng,
        ranks=remaining_ranks,
        total_count=int(filler_count),
    )

    raw_cards: List[Tuple[int, str, bool]] = []
    for rank_value in triple_ranks:
        suits = list(rng.sample(list(SUIT_NAMES), 3))
        for suit_name in suits:
            raw_cards.append((int(rank_value), str(suit_name), True))
    for rank_value, count in filler_rank_counts:
        suits = list(rng.sample(list(SUIT_NAMES), int(count)))
        for suit_name in suits:
            raw_cards.append((int(rank_value), str(suit_name), False))
    if bool(order_by_rank):
        suit_order = {str(suit_name): int(index) for index, suit_name in enumerate(SUIT_NAMES)}
        raw_cards.sort(key=lambda item: (int(item[0]), int(suit_order[str(item[1])])))
    else:
        rng.shuffle(raw_cards)

    cards: List[CardInstance] = []
    evidence_card_ids: List[str] = []
    for index, (rank_value, suit_name, in_triple) in enumerate(raw_cards, start=1):
        card_id = f"card_{index:02d}"
        cards.append(
            _label_card(
                card_id=str(card_id),
                rank_value=int(rank_value),
                suit_name=str(suit_name),
                is_reference=False,
            )
        )
        if bool(in_triple):
            evidence_card_ids.append(str(card_id))
    return _SampledHand(
        cards=tuple(cards),
        evidence_card_ids=tuple(evidence_card_ids),
        reference_card_id=None,
        reference_rank_value=None,
        reference_rank_label=None,
        reference_suit_name=None,
        rank_sequence=tuple(int(card.rank_value) for card in cards),
    )


def _sample_non_triple_rank_counts(
    rng,
    *,
    ranks: Sequence[int],
    total_count: int,
) -> Tuple[Tuple[int, int], ...]:
    """Sample per-rank card counts that never create additional exact triples."""

    return _sample_rank_counts_without_exact_count(
        rng,
        ranks=ranks,
        total_count=int(total_count),
        forbidden_count=3,
    )


def _sample_rank_counts_without_exact_count(
    rng,
    *,
    ranks: Sequence[int],
    total_count: int,
    forbidden_count: int,
) -> Tuple[Tuple[int, int], ...]:
    """Sample per-rank card counts while excluding one exact multiplicity."""

    shuffled_ranks = [int(rank_value) for rank_value in ranks]
    rng.shuffle(shuffled_ranks)
    allowed_counts = _rank_multiplicities_without_exact_count(forbidden_count=int(forbidden_count))

    feasible_cache: Dict[Tuple[int, int], bool] = {}

    def feasible(index: int, remaining: int) -> bool:
        key = (int(index), int(remaining))
        if key in feasible_cache:
            return bool(feasible_cache[key])
        if int(remaining) < 0:
            feasible_cache[key] = False
            return False
        if int(index) >= len(shuffled_ranks):
            feasible_cache[key] = int(remaining) == 0
            return bool(feasible_cache[key])
        feasible_cache[key] = any(
            feasible(int(index) + 1, int(remaining) - int(count))
            for count in allowed_counts
        )
        return bool(feasible_cache[key])

    if not feasible(0, int(total_count)):
        raise ValueError("hand cannot fill remaining cards without creating extra exact rank counts")

    out: List[Tuple[int, int]] = []
    remaining = int(total_count)
    for index, rank_value in enumerate(shuffled_ranks):
        options = [
            int(count)
            for count in allowed_counts
            if feasible(int(index) + 1, int(remaining) - int(count))
        ]
        chosen = int(options[int(rng.randrange(len(options)))])
        if int(chosen) > 0:
            out.append((int(rank_value), int(chosen)))
        remaining -= int(chosen)
    return tuple(out)


def _sample_non_run_cards(
    rng,
    *,
    count: int,
    blocked_ranks: Sequence[int],
    used_cards: set[Tuple[int, str]],
    initial_previous_rank: int | None = None,
    forbidden_final_rank: int | None = None,
) -> List[Tuple[int, str]]:
    """Sample `count` cards that avoid forming ascending adjacent runs."""

    safe_cards = [
        (int(rank_value), str(suit_name))
        for rank_value, suit_name in _make_deck()
        if int(rank_value) not in {int(value) for value in blocked_ranks}
    ]
    out: List[Tuple[int, str]] = []
    for offset in range(int(count)):
        previous_rank = int(initial_previous_rank) if not out and initial_previous_rank is not None else None if not out else int(out[-1][0])
        options = [
            (int(rank_value), str(suit_name))
            for rank_value, suit_name in safe_cards
            if (int(rank_value), str(suit_name)) not in used_cards
            and (previous_rank is None or int(rank_value) != int(previous_rank + 1))
            and (
                int(offset) != int(count) - 1
                or forbidden_final_rank is None
                or int(rank_value) != int(forbidden_final_rank)
            )
        ]
        if not options:
            raise ValueError("run sampler exhausted safe non-run cards")
        chosen = options[int(rng.randrange(len(options)))]
        out.append((int(chosen[0]), str(chosen[1])))
        used_cards.add((int(chosen[0]), str(chosen[1])))
    return out


def _sample_longest_run_hand(rng, *, card_count: int, target_answer: int) -> _SampledHand:
    """Sample one hand with a unique longest contiguous ascending run."""

    run_length = int(target_answer)
    if int(card_count) < int(run_length):
        raise ValueError("run hand requires at least as many cards as the requested run length")
    run_start_rank = int(rng.randrange(2, 15 - int(run_length)))
    run_ranks = [int(run_start_rank + offset) for offset in range(int(run_length))]
    run_start_index = int(rng.randrange(int(card_count) - int(run_length) + 1))

    used_cards: set[Tuple[int, str]] = set()
    before_cards = _sample_non_run_cards(
        rng,
        count=int(run_start_index),
        blocked_ranks=(),
        used_cards=used_cards,
        forbidden_final_rank=(int(run_start_rank) - 1 if int(run_start_rank) > 2 else None),
    )
    run_cards: List[Tuple[int, str]] = []
    for rank_value in run_ranks:
        options = [(int(rank_value), str(suit_name)) for suit_name in SUIT_NAMES if (int(rank_value), str(suit_name)) not in used_cards]
        chosen = options[int(rng.randrange(len(options)))]
        run_cards.append(chosen)
        used_cards.add(chosen)
    after_cards = _sample_non_run_cards(
        rng,
        count=int(card_count) - int(run_start_index) - int(run_length),
        blocked_ranks=(),
        used_cards=used_cards,
        initial_previous_rank=int(run_start_rank + run_length - 1),
    )
    ordered = before_cards + run_cards + after_cards
    if _unique_longest_run_span(tuple(int(rank_value) for rank_value, _ in ordered)) != (
        int(run_start_index),
        int(run_start_index + run_length - 1),
    ):
        raise ValueError("run sampler failed to preserve a unique target-length run")
    cards: List[CardInstance] = []
    evidence_card_ids: List[str] = []
    for index, (rank_value, suit_name) in enumerate(ordered, start=1):
        card_id = f"card_{index:02d}"
        cards.append(
            _label_card(
                card_id=str(card_id),
                rank_value=int(rank_value),
                suit_name=str(suit_name),
                is_reference=False,
            )
        )
        if int(run_start_index) < int(index) <= int(run_start_index + run_length):
            evidence_card_ids.append(str(card_id))
    return _SampledHand(
        cards=tuple(cards),
        evidence_card_ids=tuple(evidence_card_ids),
        reference_card_id=None,
        reference_rank_value=None,
        reference_rank_label=None,
        reference_suit_name=None,
        rank_sequence=tuple(int(card.rank_value) for card in cards),
    )


def _unique_longest_run_span(rank_sequence: Sequence[int]) -> Tuple[int, int] | None:
    """Return the only longest ascending-by-one span, or None when tied."""

    best_spans: List[Tuple[int, int]] = []
    start_index = 0
    for index in range(1, len(rank_sequence) + 1):
        continues = (
            index < len(rank_sequence)
            and int(rank_sequence[index]) == int(rank_sequence[index - 1]) + 1
        )
        if continues:
            continue
        end_index = int(index - 1)
        run_length = int(end_index - start_index + 1)
        if not best_spans or run_length > int(best_spans[0][1] - best_spans[0][0] + 1):
            best_spans = [(int(start_index), int(end_index))]
        elif run_length == int(best_spans[0][1] - best_spans[0][0] + 1):
            best_spans.append((int(start_index), int(end_index)))
        start_index = int(index)
    if len(best_spans) != 1:
        return None
    return best_spans[0]


def _sample_hand(
    rng,
    *,
    axes: _ResolvedAxes,
    same_suit_order_by_suit: bool,
    higher_rank_order_by_rank: bool,
    exact_triple_order_by_rank: bool,
) -> _SampledHand:
    """Sample one visible hand for the resolved query family."""

    if str(axes.query_id) == "same_suit_as_reference_count":
        return _sample_same_suit_hand(
            rng,
            card_count=int(axes.card_count),
            target_answer=int(axes.target_answer),
            order_by_suit=bool(same_suit_order_by_suit),
        )
    if str(axes.query_id) == "higher_than_reference_count":
        return _sample_higher_rank_hand(
            rng,
            card_count=int(axes.card_count),
            target_answer=int(axes.target_answer),
            order_by_rank=bool(higher_rank_order_by_rank),
        )
    if str(axes.query_id) == "exact_triple_count":
        return _sample_exact_triple_count_hand(
            rng,
            card_count=int(axes.card_count),
            target_answer=int(axes.target_answer),
            order_by_rank=bool(exact_triple_order_by_rank),
        )
    return _sample_longest_run_hand(rng, card_count=int(axes.card_count), target_answer=int(axes.target_answer))


def _build_prompt_json_examples(*, query_id: str) -> Tuple[str, str]:
    """Return prompt JSON examples matching the active query semantics."""

    if str(query_id) == "same_suit_as_reference_count":
        answer_and_evidence = {
            "evidence": [
                [164, 188, 262, 330],
                [276, 188, 374, 330],
                [388, 188, 486, 330],
            ],
            "answer": 3,
        }
        answer_only = {"answer": 3}
    elif str(query_id) == "higher_than_reference_count":
        answer_and_evidence = {
            "evidence": [
                [276, 188, 374, 330],
                [388, 188, 486, 330],
            ],
            "answer": 2,
        }
        answer_only = {"answer": 2}
    elif str(query_id) == "exact_triple_count":
        answer_and_evidence = {
            "evidence": [
                [164, 188, 262, 330],
                [276, 188, 374, 330],
                [388, 188, 486, 330],
                [612, 188, 710, 330],
                [724, 188, 822, 330],
                [836, 188, 934, 330],
            ],
            "answer": 2,
        }
        answer_only = {"answer": 2}
    else:
        answer_and_evidence = {
            "evidence": [
                [276, 188, 374, 330],
                [388, 188, 486, 330],
                [500, 188, 598, 330],
                [612, 188, 710, 330],
            ],
            "answer": 4,
        }
        answer_only = {"answer": 4}
    return (
        json.dumps(answer_and_evidence, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> CardRenderParams:
    """Resolve card-scene rendering parameters from config/defaults."""

    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace="games.cards.font",
        params=params,
    )
    return CardRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        card_width_px=int(params.get("card_width_px", group_default(_RENDER_DEFAULTS, "card_width_px", _DEFAULTS.card_width_px))),
        card_height_px=int(params.get("card_height_px", group_default(_RENDER_DEFAULTS, "card_height_px", _DEFAULTS.card_height_px))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        card_gap_px=int(params.get("card_gap_px", group_default(_RENDER_DEFAULTS, "card_gap_px", _DEFAULTS.card_gap_px))),
        row_gap_px=int(params.get("row_gap_px", group_default(_RENDER_DEFAULTS, "row_gap_px", _DEFAULTS.row_gap_px))),
        card_corner_radius_px=int(
            params.get("card_corner_radius_px", group_default(_RENDER_DEFAULTS, "card_corner_radius_px", _DEFAULTS.card_corner_radius_px))
        ),
        rank_font_size_px=int(params.get("rank_font_size_px", group_default(_RENDER_DEFAULTS, "rank_font_size_px", _DEFAULTS.rank_font_size_px))),
        center_symbol_font_size_px=int(
            params.get(
                "center_symbol_font_size_px",
                group_default(_RENDER_DEFAULTS, "center_symbol_font_size_px", _DEFAULTS.center_symbol_font_size_px),
            )
        ),
        reference_banner_height_px=int(
            params.get(
                "reference_banner_height_px",
                group_default(_RENDER_DEFAULTS, "reference_banner_height_px", _DEFAULTS.reference_banner_height_px),
            )
        ),
        reference_font_size_px=int(
            params.get(
                "reference_font_size_px",
                group_default(_RENDER_DEFAULTS, "reference_font_size_px", _DEFAULTS.reference_font_size_px),
            )
        ),
        continuation_font_size_px=int(
            params.get(
                "continuation_font_size_px",
                group_default(_RENDER_DEFAULTS, "continuation_font_size_px", _DEFAULTS.continuation_font_size_px),
            )
        ),
        continuation_gap_px=int(
            params.get(
                "continuation_gap_px",
                group_default(_RENDER_DEFAULTS, "continuation_gap_px", _DEFAULTS.continuation_gap_px),
            )
        ),
        max_cards_per_row=int(
            params.get(
                "max_cards_per_row",
                group_default(_RENDER_DEFAULTS, "max_cards_per_row", _DEFAULTS.max_cards_per_row),
            )
        ),
        center_label_mode=str(
            params.get(
                "center_label_mode",
                group_default(_RENDER_DEFAULTS, "center_label_mode", "suit_symbol"),
            )
        ),
        layout_jitter_meta=resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.cards.layout",
        ),
        group_label_font_size_px=int(
            params.get(
                "group_label_font_size_px",
                group_default(_RENDER_DEFAULTS, "group_label_font_size_px", 22),
            )
        ),
        font_family=str(font_family),
    )


class GamesCardsHandCountTask:
    """Return one grounded counting query over a visible playing-card hand."""

    task_id = TASK_ID
    domain = "games"
    task_group = "cards"
    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))
        same_suit_order_by_suit = bool(
            params.get(
                "same_suit_order_by_suit",
                group_default(
                    _GEN_DEFAULTS,
                    "same_suit_order_by_suit",
                    _DEFAULTS.same_suit_order_by_suit,
                ),
            )
        )
        higher_rank_order_by_rank = bool(
            params.get(
                "higher_rank_order_by_rank",
                group_default(
                    _GEN_DEFAULTS,
                    "higher_rank_order_by_rank",
                    _DEFAULTS.higher_rank_order_by_rank,
                ),
            )
        )
        exact_triple_order_by_rank = bool(
            params.get(
                "exact_triple_count_order_by_rank",
                group_default(
                    _GEN_DEFAULTS,
                    "exact_triple_count_order_by_rank",
                    _DEFAULTS.exact_triple_count_order_by_rank,
                ),
            )
        )
        if str(axes.query_id) == "higher_than_reference_count":
            render_params = replace(
                render_params,
                center_label_mode=str(
                    params.get(
                        "higher_rank_center_label_mode",
                        group_default(
                            _RENDER_DEFAULTS,
                            "higher_rank_center_label_mode",
                            _DEFAULTS.higher_rank_center_label_mode,
                        ),
                    )
                ),
            )
        if str(axes.query_id) == "exact_triple_count":
            render_params = replace(
                render_params,
                center_label_mode=str(
                    params.get(
                        "exact_triple_count_center_label_mode",
                        group_default(
                            _RENDER_DEFAULTS,
                            "exact_triple_count_center_label_mode",
                            _DEFAULTS.exact_triple_count_center_label_mode,
                        ),
                    )
                ),
            )
        if str(axes.query_id) == "longest_run_length":
            render_params = replace(
                render_params,
                center_label_mode=str(
                    params.get(
                        "longest_run_center_label_mode",
                        group_default(
                            _RENDER_DEFAULTS,
                            "longest_run_center_label_mode",
                            _DEFAULTS.longest_run_center_label_mode,
                        ),
                    )
                ),
            )

        sampled_hand: _SampledHand | None = None
        rendered_scene = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_hand = _sample_hand(
                    attempt_rng,
                    axes=axes,
                    same_suit_order_by_suit=bool(same_suit_order_by_suit),
                    higher_rank_order_by_rank=bool(higher_rank_order_by_rank),
                    exact_triple_order_by_rank=bool(exact_triple_order_by_rank),
                )
            except ValueError:
                continue

            background, background_meta = make_background_canvas(
                canvas_width=int(render_params.canvas_width),
                canvas_height=int(render_params.canvas_height),
                instance_seed=int(instance_seed),
                params=params,
                default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
            )
            rendered_scene = render_cards_hand_scene(
                cards=list(sampled_hand.cards),
                background=background,
                scene_variant=str(axes.scene_variant),
                style_variant=str(axes.style_variant),
                params=render_params,
                show_continuation_cue=bool(
                    str(axes.query_id) == "longest_run_length"
                    and int(axes.card_count) > int(render_params.max_cards_per_row)
                ),
            )
            break

        if sampled_hand is None or rendered_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")

        evidence_bboxes = [
            list(rendered_scene.render_map["card_bboxes_px"][str(card_id)])
            for card_id in sampled_hand.evidence_card_ids
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
                "rank_order_text",
                "continuation_rule_text",
                "object_description_multi_row",
                "answer_hint_same_suit_as_reference_count",
                "answer_hint_higher_than_reference_count",
                "answer_hint_exact_triple_count",
                "answer_hint_longest_run_length",
                "evidence_hint_same_suit_as_reference_count",
                "evidence_hint_higher_than_reference_count",
                "evidence_hint_exact_triple_count",
                "evidence_hint_longest_run_length",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(query_id=str(axes.query_id))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_id)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "rank_order_text": str(prompt_defaults["rank_order_text"]),
                "continuation_rule_text": str(prompt_defaults["continuation_rule_text"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(axes.target_answer))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        complexity = build_games_cards_hand_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            card_count=int(axes.card_count),
            target_answer=int(axes.target_answer),
            evidence_count=len(sampled_hand.evidence_card_ids),
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_cards_hand_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "card_count": int(axes.card_count),
                    "row_count": int(rendered_scene.render_map["row_count"]),
                    "max_cards_per_row": int(rendered_scene.render_map["max_cards_per_row"]),
                    "center_label_mode": str(rendered_scene.render_map["center_label_mode"]),
                    "target_answer": int(axes.target_answer),
                    "evidence_entity_ids": list(sampled_hand.evidence_card_ids),
                    "reference_card_id": None if sampled_hand.reference_card_id is None else str(sampled_hand.reference_card_id),
                    "card_ordering": (
                        "suit_grouped"
                        if str(axes.query_id) == "same_suit_as_reference_count" and bool(same_suit_order_by_suit)
                        else
                        "rank_grouped"
                        if str(axes.query_id) == "higher_than_reference_count" and bool(higher_rank_order_by_rank)
                        else
                        "rank_grouped"
                        if str(axes.query_id) == "exact_triple_count" and bool(exact_triple_order_by_rank)
                        else "sampled"
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
                    "style_variant": str(axes.style_variant),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "target_answer": int(axes.target_answer),
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    "card_count": int(axes.card_count),
                    "card_count_support": [int(value) for value in axes.card_count_support],
                    "card_count_probabilities": dict(axes.card_count_probabilities),
                    "row_count": int(rendered_scene.render_map["row_count"]),
                    "max_cards_per_row": int(rendered_scene.render_map["max_cards_per_row"]),
                    "card_ordering": (
                        "suit_grouped"
                        if str(axes.query_id) == "same_suit_as_reference_count" and bool(same_suit_order_by_suit)
                        else
                        "rank_grouped"
                        if str(axes.query_id) == "higher_than_reference_count" and bool(higher_rank_order_by_rank)
                        else
                        "rank_grouped"
                        if str(axes.query_id) == "exact_triple_count" and bool(exact_triple_order_by_rank)
                        else "sampled"
                    ),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "row_count": int(rendered_scene.render_map["row_count"]),
                "max_cards_per_row": int(rendered_scene.render_map["max_cards_per_row"]),
                "center_label_mode": str(rendered_scene.render_map["center_label_mode"]),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
                "font_family": str(render_params.font_family),
                "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
                "suit_symbol_font_family": str(rendered_scene.render_map.get("suit_symbol_font_family", "")),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "target_answer": int(axes.target_answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "card_count": int(axes.card_count),
                "card_count_support": [int(value) for value in axes.card_count_support],
                "card_ordering": (
                    "suit_grouped"
                    if str(axes.query_id) == "same_suit_as_reference_count" and bool(same_suit_order_by_suit)
                    else
                    "rank_grouped"
                    if str(axes.query_id) == "higher_than_reference_count" and bool(higher_rank_order_by_rank)
                    else
                    "rank_grouped"
                    if str(axes.query_id) == "exact_triple_count" and bool(exact_triple_order_by_rank)
                    else "sampled"
                ),
                "row_count": int(rendered_scene.render_map["row_count"]),
                "max_cards_per_row": int(rendered_scene.render_map["max_cards_per_row"]),
                "rank_sequence": [int(value) for value in sampled_hand.rank_sequence],
                "reference_card_id": None if sampled_hand.reference_card_id is None else str(sampled_hand.reference_card_id),
                "reference_rank_value": None if sampled_hand.reference_rank_value is None else int(sampled_hand.reference_rank_value),
                "reference_rank_label": None if sampled_hand.reference_rank_label is None else str(sampled_hand.reference_rank_label),
                "reference_suit_name": None if sampled_hand.reference_suit_name is None else str(sampled_hand.reference_suit_name),
                "card_specs": [
                    {
                        "card_id": str(spec.card_id),
                        "rank_label": str(spec.rank_label),
                        "rank_value": int(spec.rank_value),
                        "suit_name": str(spec.suit_name),
                        "is_reference": bool(spec.is_reference),
                        "order_index": int(spec.order_index),
                    }
                    for spec in rendered_scene.card_specs
                ],
                "evidence_entity_ids": [str(card_id) for card_id in sampled_hand.evidence_card_ids],
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(card_id) for card_id in sampled_hand.evidence_card_ids],
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
            query_id=str(axes.query_id),
            scene_id="cards",
        )


@register_task
class GamesCardsReferenceConditionCountTask(QuerySubsetTaskMixin, GamesCardsHandCountTask):
    """Count non-reference cards satisfying a sampled reference-card condition."""

    task_id = "task_games__cards__reference_condition_count"
    supported_query_ids = (
        "same_suit_as_reference_count",
        "higher_than_reference_count",
    )


@register_task
class GamesCardsExactTripleCountTask(FixedQueryVariantTaskMixin, GamesCardsHandCountTask):
    """Count card ranks that appear exactly three times."""

    task_id = "task_games__cards__exact_triple_count"
    fixed_query_id = "exact_triple_count"


@register_task
class GamesCardsLongestRunLengthTask(FixedQueryVariantTaskMixin, GamesCardsHandCountTask):
    """Return the longest consecutive rank run in row-major card order."""

    task_id = "task_games__cards__longest_run_length"
    fixed_query_id = "longest_run_length"


HAND_LABELS: Tuple[str, ...] = ("Hand A", "Hand B", "Hand C", "Hand D", "Hand E", "Hand F")
PLAYER_LABELS: Tuple[str, ...] = ("Player A", "Player B", "Player C", "Player D", "Player E", "Player F")


def _option_letter(label: str) -> str:
    """Return the compact answer option from a rendered label such as `Hand C`."""

    return str(label).strip().split()[-1]


@dataclass(frozen=True)
class _RuleSample:
    """Constructed card-game rule scene plus witness metadata."""

    query_key: str
    scene_variant: str
    cards: Tuple[CardInstance, ...]
    answer: str
    evidence_card_ids: Tuple[str, ...]
    option_count: int
    cards_per_row: int
    center_label_mode: str
    render_overrides: Dict[str, int]
    prompt_slots: Dict[str, str]
    metadata: Dict[str, Any]


def _make_labelled_card(
    *,
    card_id: str,
    rank_value: int,
    suit_name: str,
    badge_text: str | None = None,
    group_label: str | None = None,
    is_reference: bool = False,
) -> CardInstance:
    """Build one rendered card with optional game-rule labels."""

    return CardInstance(
        card_id=str(card_id),
        rank_label=str(RANK_LABEL_BY_VALUE[int(rank_value)]),
        rank_value=int(rank_value),
        suit_name=str(suit_name),
        is_reference=bool(is_reference),
        badge_text=None if badge_text is None else str(badge_text),
        group_label=None if group_label is None else str(group_label),
    )


def _option_count(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    support_key: str,
    fallback_support: Sequence[int],
    namespace: str,
) -> Tuple[int, Tuple[int, ...], Dict[str, float]]:
    """Resolve a balanced labelled-option count."""

    support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=str(support_key),
        fallback=tuple(int(value) for value in fallback_support),
    )
    option_params = dict(params)
    option_params["option_count_support"] = [int(value) for value in support]
    count, probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=option_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="option_count_support",
        explicit_key="option_count",
        fallback_support=support,
        namespace=str(namespace),
        balanced_flag_key="balanced_option_count_sampling",
        namespace_support_permutation=True,
    )
    return int(count), tuple(int(value) for value in support), dict(probabilities)


def _cards_per_hand(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    support_key: str,
    fallback_support: Sequence[int],
    namespace: str,
) -> Tuple[int, Tuple[int, ...], Dict[str, float]]:
    """Resolve a balanced card count per labelled hand."""

    support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=str(support_key),
        fallback=tuple(int(value) for value in fallback_support),
    )
    hand_params = dict(params)
    hand_params["cards_per_hand_support"] = [int(value) for value in support]
    count, probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=hand_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="cards_per_hand_support",
        explicit_key="cards_per_hand",
        fallback_support=support,
        namespace=str(namespace),
        balanced_flag_key="balanced_cards_per_hand_sampling",
        namespace_support_permutation=True,
    )
    return int(count), tuple(int(value) for value in support), dict(probabilities)


def _blackjack_total(cards: Sequence[Tuple[int, str]]) -> int:
    """Return the best blackjack total, counting aces as 11 or 1."""

    total = 0
    ace_count = 0
    for rank_value, _suit_name in cards:
        rank = int(rank_value)
        if int(rank) == 14:
            total += 11
            ace_count += 1
        elif int(rank) >= 11:
            total += 10
        else:
            total += int(rank)
    while int(total) > 21 and int(ace_count) > 0:
        total -= 10
        ace_count -= 1
    return int(total)


def _sample_blackjack_best_hand(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> _RuleSample:
    """Sample labelled blackjack hands with one unique best non-bust hand."""

    hand_count, hand_count_support, hand_count_probabilities = _option_count(
        instance_seed=int(instance_seed),
        params=params,
        support_key="blackjack_hand_count_support",
        fallback_support=(4, 5, 6),
        namespace="games.cards.blackjack.hand_count",
    )
    cards_per_hand, cards_per_hand_support, cards_per_hand_probabilities = _cards_per_hand(
        instance_seed=int(instance_seed),
        params=params,
        support_key="blackjack_cards_per_hand_support",
        fallback_support=(3, 4),
        namespace="games.cards.blackjack.cards_per_hand",
    )
    labels = HAND_LABELS[: int(hand_count)]
    deck = _make_deck()
    for _attempt in range(200):
        raw_cards = list(rng.sample(deck, int(hand_count) * int(cards_per_hand)))
        hands = [
            raw_cards[index * int(cards_per_hand) : (index + 1) * int(cards_per_hand)]
            for index in range(int(hand_count))
        ]
        totals = [_blackjack_total(hand) for hand in hands]
        playable_scores = [int(total) if int(total) <= 21 else -1 for total in totals]
        best_score = max(playable_scores)
        if int(best_score) < 0 or playable_scores.count(int(best_score)) != 1:
            continue
        winner_index = int(playable_scores.index(int(best_score)))
        winner_label = str(labels[int(winner_index)])
        winner_option = _option_letter(winner_label)
        cards: List[CardInstance] = []
        evidence_ids: List[str] = []
        for hand_index, hand in enumerate(hands):
            label = str(labels[int(hand_index)])
            for card_index, (rank_value, suit_name) in enumerate(hand, start=1):
                card_id = f"hand_{hand_index + 1:02d}_card_{card_index:02d}"
                cards.append(
                    _make_labelled_card(
                        card_id=str(card_id),
                        rank_value=int(rank_value),
                        suit_name=str(suit_name),
                        group_label=str(label),
                    )
                )
                if int(hand_index) == int(winner_index):
                    evidence_ids.append(str(card_id))
        return _RuleSample(
            query_key="blackjack_best_hand_label",
            scene_variant="blackjack_multi_hand",
            cards=tuple(cards),
            answer=str(winner_option),
            evidence_card_ids=tuple(evidence_ids),
            option_count=int(hand_count),
            cards_per_row=int(cards_per_hand),
            center_label_mode="rank_suit",
            render_overrides={
                "canvas_height": 880,
                "card_width_px": 78,
                "card_height_px": 108,
                "card_gap_px": 12,
                "row_gap_px": 18,
                "rank_font_size_px": 17,
                "center_symbol_font_size_px": 38,
                "max_cards_per_row": int(cards_per_hand),
            },
            prompt_slots={
                "blackjack_rule_text": "Use blackjack values: number cards count as printed, J/Q/K count as 10, and each Ace counts as 11 unless that would bust, then it counts as 1. A bust hand is worse than any non-bust hand.",
            },
            metadata={
                "hand_labels": list(labels),
                "hand_totals": {str(labels[index]): int(total) for index, total in enumerate(totals)},
                "playable_scores": {str(labels[index]): int(score) for index, score in enumerate(playable_scores)},
                "winning_label": str(winner_label),
                "winning_option": str(winner_option),
                "hand_count_support": [int(value) for value in hand_count_support],
                "hand_count_probabilities": dict(hand_count_probabilities),
                "cards_per_hand_support": [int(value) for value in cards_per_hand_support],
                "cards_per_hand_probabilities": dict(cards_per_hand_probabilities),
            },
        )
    raise ValueError("failed to sample unique blackjack best hand")


def _straight_high_rank(ranks: Sequence[int]) -> int | None:
    """Return the high card of a five-card straight, with wheel as five-high."""

    unique = sorted({int(rank) for rank in ranks})
    if len(unique) != 5:
        return None
    if unique == [2, 3, 4, 5, 14]:
        return 5
    if int(unique[-1] - unique[0]) == 4:
        return int(unique[-1])
    return None


def _poker_score(cards: Sequence[Tuple[int, str]]) -> Tuple[int, Tuple[int, ...], str]:
    """Return a comparable standard five-card poker score."""

    ranks = [int(rank) for rank, _suit_name in cards]
    suits = [str(suit_name) for _rank, suit_name in cards]
    rank_counts: Dict[int, int] = {}
    for rank in ranks:
        rank_counts[int(rank)] = int(rank_counts.get(int(rank), 0) + 1)
    groups = sorted(rank_counts.items(), key=lambda item: (int(item[1]), int(item[0])), reverse=True)
    flush = len(set(suits)) == 1
    straight_high = _straight_high_rank(ranks)
    if flush and straight_high is not None:
        return (8, (int(straight_high),), "straight flush")
    if int(groups[0][1]) == 4:
        quad_rank = int(groups[0][0])
        kicker = max(int(rank) for rank in ranks if int(rank) != int(quad_rank))
        return (7, (int(quad_rank), int(kicker)), "four of a kind")
    if sorted((int(count) for count in rank_counts.values()), reverse=True) == [3, 2]:
        triple_rank = max(int(rank) for rank, count in rank_counts.items() if int(count) == 3)
        pair_rank = max(int(rank) for rank, count in rank_counts.items() if int(count) == 2)
        return (6, (int(triple_rank), int(pair_rank)), "full house")
    if flush:
        return (5, tuple(sorted((int(rank) for rank in ranks), reverse=True)), "flush")
    if straight_high is not None:
        return (4, (int(straight_high),), "straight")
    if int(groups[0][1]) == 3:
        triple_rank = int(groups[0][0])
        kickers = tuple(sorted((int(rank) for rank in ranks if int(rank) != int(triple_rank)), reverse=True))
        return (3, (int(triple_rank), *kickers), "three of a kind")
    pair_ranks = sorted((int(rank) for rank, count in rank_counts.items() if int(count) == 2), reverse=True)
    if len(pair_ranks) == 2:
        kicker = max(int(rank) for rank in ranks if int(rank) not in set(pair_ranks))
        return (2, (int(pair_ranks[0]), int(pair_ranks[1]), int(kicker)), "two pair")
    if len(pair_ranks) == 1:
        pair_rank = int(pair_ranks[0])
        kickers = tuple(sorted((int(rank) for rank in ranks if int(rank) != int(pair_rank)), reverse=True))
        return (1, (int(pair_rank), *kickers), "one pair")
    return (0, tuple(sorted((int(rank) for rank in ranks), reverse=True)), "high card")


def _sample_poker_best_hand(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> _RuleSample:
    """Sample labelled five-card poker hands with one unique winner."""

    hand_count, hand_count_support, hand_count_probabilities = _option_count(
        instance_seed=int(instance_seed),
        params=params,
        support_key="poker_hand_count_support",
        fallback_support=(4, 5, 6),
        namespace="games.cards.poker.hand_count",
    )
    labels = HAND_LABELS[: int(hand_count)]
    deck = _make_deck()
    for _attempt in range(400):
        raw_cards = list(rng.sample(deck, int(hand_count) * 5))
        hands = [raw_cards[index * 5 : (index + 1) * 5] for index in range(int(hand_count))]
        scores = [_poker_score(hand) for hand in hands]
        comparable = [(int(category), tuple(int(value) for value in tiebreakers)) for category, tiebreakers, _name in scores]
        best_score = max(comparable)
        if comparable.count(best_score) != 1:
            continue
        winner_index = int(comparable.index(best_score))
        if int(scores[int(winner_index)][0]) == 0:
            continue
        winner_label = str(labels[int(winner_index)])
        winner_option = _option_letter(winner_label)
        cards: List[CardInstance] = []
        evidence_ids: List[str] = []
        for hand_index, hand in enumerate(hands):
            label = str(labels[int(hand_index)])
            for card_index, (rank_value, suit_name) in enumerate(hand, start=1):
                card_id = f"hand_{hand_index + 1:02d}_card_{card_index:02d}"
                cards.append(
                    _make_labelled_card(
                        card_id=str(card_id),
                        rank_value=int(rank_value),
                        suit_name=str(suit_name),
                        group_label=str(label),
                    )
                )
                if int(hand_index) == int(winner_index):
                    evidence_ids.append(str(card_id))
        return _RuleSample(
            query_key="poker_best_hand_label",
            scene_variant="poker_multi_hand",
            cards=tuple(cards),
            answer=str(winner_option),
            evidence_card_ids=tuple(evidence_ids),
            option_count=int(hand_count),
            cards_per_row=5,
            center_label_mode="rank_suit",
            render_overrides={
                "canvas_height": 880,
                "card_width_px": 78,
                "card_height_px": 108,
                "card_gap_px": 12,
                "row_gap_px": 18,
                "rank_font_size_px": 17,
                "center_symbol_font_size_px": 38,
                "max_cards_per_row": 5,
            },
            prompt_slots={
                "poker_rule_text": "Use standard five-card poker ranking. Compare categories first; if categories match, use the usual rank tie-breakers with Ace high.",
            },
            metadata={
                "hand_labels": list(labels),
                "hand_categories": {str(labels[index]): str(score[2]) for index, score in enumerate(scores)},
                "hand_scores": {
                    str(labels[index]): [int(score[0]), [int(value) for value in score[1]]]
                    for index, score in enumerate(scores)
                },
                "winning_label": str(winner_label),
                "winning_option": str(winner_option),
                "hand_count_support": [int(value) for value in hand_count_support],
                "hand_count_probabilities": dict(hand_count_probabilities),
            },
        )
    raise ValueError("failed to sample unique poker best hand")


def _trick_rank_score(card: Tuple[int, str], *, led_suit: str, trump_suit: str | None) -> Tuple[int, int]:
    """Return trick-taking priority for one played card."""

    rank_value, suit_name = card
    if trump_suit is not None and str(suit_name) == str(trump_suit):
        return (2, int(rank_value))
    if str(suit_name) == str(led_suit):
        return (1, int(rank_value))
    return (0, int(rank_value))


def _sample_trick_taking_winner(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> _RuleSample:
    """Sample one labelled trick with a unique winner."""

    player_count_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="trick_player_count_support",
        fallback=(4, 5, 6),
    )
    explicit_player_count = params.get("option_count")
    target_upper = int(explicit_player_count) if explicit_player_count is not None else max(int(value) for value in player_count_support)
    raw_target_index = params.get("target_winner_index")
    if raw_target_index is not None:
        target_winner_index = int(raw_target_index)
        if target_winner_index < 0 or target_winner_index >= int(target_upper):
            raise ValueError(f"unsupported target_winner_index: {target_winner_index}")
    elif params.get("_sample_cursor") is not None:
        target_winner_index = abs(int(params["_sample_cursor"])) % int(target_upper)
    else:
        target_winner_index = int(rng.randrange(int(target_upper)))
    feasible_player_count_support = tuple(
        int(value)
        for value in player_count_support
        if int(value) > int(target_winner_index)
    )
    if not feasible_player_count_support:
        raise ValueError("no feasible trick player count can contain target winner")
    player_count_params = dict(params)
    player_count_params["option_count_support"] = [int(value) for value in feasible_player_count_support]
    player_count, player_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=player_count_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="option_count_support",
        explicit_key="option_count",
        fallback_support=feasible_player_count_support,
        namespace="games.cards.trick.player_count",
        balanced_flag_key="balanced_option_count_sampling",
        namespace_support_permutation=True,
    )

    deck = _make_deck()
    labels = PLAYER_LABELS[: int(player_count)]
    for _attempt in range(500):
        raw_cards = list(rng.sample(deck, int(player_count)))
        led_suit = str(raw_cards[0][1])
        trump_options: List[str | None] = [None] + [str(suit) for suit in SUIT_NAMES if str(suit) != str(led_suit)]
        trump_suit = trump_options[int(rng.randrange(len(trump_options)))]
        scores = [_trick_rank_score(card, led_suit=str(led_suit), trump_suit=trump_suit) for card in raw_cards]
        best_score = max(scores)
        if scores.count(best_score) != 1:
            continue
        winner_index = int(scores.index(best_score))
        if int(winner_index) != int(target_winner_index):
            continue
        winner_label = str(labels[int(winner_index)])
        winner_option = _option_letter(winner_label)
        cards: List[CardInstance] = []
        for index, (rank_value, suit_name) in enumerate(raw_cards):
            label = str(labels[int(index)])
            cards.append(
                _make_labelled_card(
                    card_id=f"player_{index + 1:02d}_card_01",
                    rank_value=int(rank_value),
                    suit_name=str(suit_name),
                    badge_text=str(label),
                )
            )
        trump_text = "There is no trump suit." if trump_suit is None else f"Trump suit: {trump_suit}."
        return _RuleSample(
            query_key="trick_taking_winner_label",
            scene_variant="trick_row",
            cards=tuple(cards),
            answer=str(winner_option),
            evidence_card_ids=(f"player_{winner_index + 1:02d}_card_01",),
            option_count=int(player_count),
            cards_per_row=int(player_count),
            center_label_mode="rank_suit",
            render_overrides={
                "canvas_height": 360,
                "card_width_px": 96,
                "card_height_px": 136,
                "card_gap_px": 18,
                "row_gap_px": 18,
                "rank_font_size_px": 19,
                "center_symbol_font_size_px": 42,
                "reference_banner_height_px": 24,
                "reference_font_size_px": 13,
                "max_cards_per_row": int(player_count),
            },
            prompt_slots={
                "trick_rule_text": "The leftmost card is the led card. If any trump card is played, the highest trump wins; otherwise the highest card in the led suit wins.",
                "trump_text": str(trump_text),
            },
            metadata={
                "player_labels": list(labels),
                "led_suit": str(led_suit),
                "trump_suit": None if trump_suit is None else str(trump_suit),
                "winning_label": str(winner_label),
                "winning_option": str(winner_option),
                "target_winner_index": int(target_winner_index),
                "player_count_support": [int(value) for value in player_count_support],
                "player_count_probabilities": dict(player_count_probabilities),
                "trick_scores": {str(labels[index]): [int(scores[index][0]), int(scores[index][1])] for index in range(int(player_count))},
            },
        )
    raise ValueError("failed to sample unique trick winner")


def _build_rule_prompt_json_examples(*, query_key: str) -> Tuple[str, str]:
    """Return prompt JSON examples for labelled card-game decisions."""

    if str(query_key) == "trick_taking_winner_label":
        answer_and_evidence = {"evidence": [[520, 110, 632, 260]], "answer": "C"}
        answer_only = {"answer": "C"}
    else:
        answer_and_evidence = {
            "evidence": [
                [420, 120, 498, 228],
                [510, 120, 588, 228],
                [600, 120, 678, 228],
                [690, 120, 768, 228],
                [780, 120, 858, 228],
            ],
            "answer": "B",
        }
        answer_only = {"answer": "B"}
    return (
        json.dumps(answer_and_evidence, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


class _GamesCardsRuleTask:
    """Shared generator for single-query card-game rule decisions."""

    domain = "games"
    task_group = "cards"
    query_key: str

    def _sample(self, rng, *, instance_seed: int, params: Mapping[str, Any]) -> _RuleSample:
        raise NotImplementedError

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        style_variant, style_variant_probabilities = _resolve_named_axis(
            instance_seed=int(instance_seed),
            params=params,
            namespace=f"{self.task_id}.style_variant",
            explicit_key="style_variant",
            weights_key="style_variant_weights",
            balance_flag_key="balanced_style_variant_sampling",
            supported=SUPPORTED_CARD_STYLE_VARIANTS,
        )
        sample: _RuleSample | None = None
        rendered_scene = None
        background_meta: Dict[str, Any] = {}
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{self.task_id}.attempt.{int(attempt_index)}")
            try:
                sample = self._sample(attempt_rng, instance_seed=int(instance_seed), params=params)
            except ValueError:
                continue

            render_params = _render_params(params, instance_seed=int(instance_seed))
            render_params = replace(
                render_params,
                canvas_height=int(sample.render_overrides.get("canvas_height", render_params.canvas_height)),
                card_width_px=int(sample.render_overrides.get("card_width_px", render_params.card_width_px)),
                card_height_px=int(sample.render_overrides.get("card_height_px", render_params.card_height_px)),
                card_gap_px=int(sample.render_overrides.get("card_gap_px", render_params.card_gap_px)),
                row_gap_px=int(sample.render_overrides.get("row_gap_px", render_params.row_gap_px)),
                rank_font_size_px=int(sample.render_overrides.get("rank_font_size_px", render_params.rank_font_size_px)),
                center_symbol_font_size_px=int(
                    sample.render_overrides.get("center_symbol_font_size_px", render_params.center_symbol_font_size_px)
                ),
                reference_banner_height_px=int(
                    sample.render_overrides.get("reference_banner_height_px", render_params.reference_banner_height_px)
                ),
                reference_font_size_px=int(sample.render_overrides.get("reference_font_size_px", render_params.reference_font_size_px)),
                max_cards_per_row=int(sample.render_overrides.get("max_cards_per_row", sample.cards_per_row)),
                center_label_mode=str(sample.center_label_mode),
            )
            background, background_meta = make_background_canvas(
                canvas_width=int(render_params.canvas_width),
                canvas_height=int(render_params.canvas_height),
                instance_seed=int(instance_seed),
                params=params,
                default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
            )
            rendered_scene = render_cards_hand_scene(
                cards=list(sample.cards),
                background=background,
                scene_variant=str(sample.scene_variant),
                style_variant=str(style_variant),
                params=render_params,
                show_continuation_cue=False,
            )
            break
        if sample is None or rendered_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")

        evidence_bboxes = [
            list(rendered_scene.render_map["card_bboxes_px"][str(card_id)])
            for card_id in sample.evidence_card_ids
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
                f"object_description_{str(sample.scene_variant)}",
                f"answer_hint_{str(sample.query_key)}",
                f"evidence_hint_{str(sample.query_key)}",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_rule_prompt_json_examples(query_key=str(sample.query_key))
        slots = {
            "object_description": str(prompt_defaults[f"object_description_{str(sample.scene_variant)}"]),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults[f"answer_hint_{str(sample.query_key)}"]),
            "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(sample.query_key)}"]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
            "rank_order_text": str(group_default(_PROMPT_DEFAULTS, "rank_order_text", "")),
        }
        slots.update({str(key): str(value) for key, value in sample.prompt_slots.items()})
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(sample.query_key),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots=slots,
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        answer_gt = TypedValue(type="string", value=str(sample.answer))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        complexity = build_games_cards_hand_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(sample.scene_variant),
            query_id=str(sample.query_key),
            card_count=len(sample.cards),
            target_answer=int(sample.option_count),
            evidence_count=len(sample.evidence_card_ids),
        )
        card_specs = [
            {
                "card_id": str(spec.card_id),
                "rank_label": str(spec.rank_label),
                "rank_value": int(spec.rank_value),
                "suit_name": str(spec.suit_name),
                "is_reference": bool(spec.is_reference),
                "badge_text": None if spec.badge_text is None else str(spec.badge_text),
                "group_label": None if spec.group_label is None else str(spec.group_label),
                "order_index": int(spec.order_index),
                "row_index": int(spec.row_index),
            }
            for spec in rendered_scene.card_specs
        ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_cards_hand_{str(sample.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(sample.scene_variant),
                    "query_id": str(sample.query_key),
                    "style_variant": str(style_variant),
                    "card_count": len(sample.cards),
                    "option_count": int(sample.option_count),
                    "answer_label": str(sample.answer),
                    "evidence_entity_ids": list(sample.evidence_card_ids),
                },
            },
            "query_spec": {
                "query_id": str(sample.query_key),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_variant": str(sample.scene_variant),
                    "query_id": str(sample.query_key),
                    "query_id_probabilities": {str(sample.query_key): 1.0},
                    "style_variant": str(style_variant),
                    "style_variant_probabilities": dict(style_variant_probabilities),
                    "option_count": int(sample.option_count),
                    "cards_per_row": int(sample.cards_per_row),
                    **dict(sample.metadata),
                },
            },
            "render_spec": {
                "scene_variant": str(sample.scene_variant),
                "style_variant": str(style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "row_count": int(rendered_scene.render_map["row_count"]),
                "max_cards_per_row": int(rendered_scene.render_map["max_cards_per_row"]),
                "center_label_mode": str(rendered_scene.render_map["center_label_mode"]),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
                "font_family": str(render_params.font_family),
                "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
                "suit_symbol_font_family": str(rendered_scene.render_map.get("suit_symbol_font_family", "")),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(sample.scene_variant),
                "query_id": str(sample.query_key),
                "style_variant": str(style_variant),
                "answer_label": str(sample.answer),
                "card_count": len(sample.cards),
                "option_count": int(sample.option_count),
                "card_specs": card_specs,
                "evidence_entity_ids": [str(card_id) for card_id in sample.evidence_card_ids],
                **dict(sample.metadata),
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(card_id) for card_id in sample.evidence_card_ids],
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
            scene_id="cards",
            query_id=str(sample.query_key),
        )


@register_task
class GamesCardsBlackjackBestHandLabelTask(_GamesCardsRuleTask):
    """Choose the best labelled blackjack hand."""

    task_id = "task_games__cards__blackjack_best_hand_label"
    query_key = "blackjack_best_hand_label"

    def _sample(self, rng, *, instance_seed: int, params: Mapping[str, Any]) -> _RuleSample:
        return _sample_blackjack_best_hand(rng, instance_seed=int(instance_seed), params=params)


@register_task
class GamesCardsPokerBestHandLabelTask(_GamesCardsRuleTask):
    """Choose the strongest labelled five-card poker hand."""

    task_id = "task_games__cards__poker_best_hand_label"
    query_key = "poker_best_hand_label"

    def _sample(self, rng, *, instance_seed: int, params: Mapping[str, Any]) -> _RuleSample:
        return _sample_poker_best_hand(rng, instance_seed=int(instance_seed), params=params)


@register_task
class GamesCardsTrickTakingWinnerLabelTask(_GamesCardsRuleTask):
    """Choose the winning played card in a trick-taking round."""

    task_id = "task_games__cards__trick_taking_winner_label"
    query_key = "trick_taking_winner_label"

    def _sample(self, rng, *, instance_seed: int, params: Mapping[str, Any]) -> _RuleSample:
        return _sample_trick_taking_winner(rng, instance_seed=int(instance_seed), params=params)


__all__ = [
    "GamesCardsBlackjackBestHandLabelTask",
    "GamesCardsExactTripleCountTask",
    "GamesCardsLongestRunLengthTask",
    "GamesCardsPokerBestHandLabelTask",
    "GamesCardsReferenceConditionCountTask",
    "GamesCardsTrickTakingWinnerLabelTask",
]
