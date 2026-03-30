"""Games cards task for grounded hand-analysis counting queries."""

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
from ..shared.card_scene import CardInstance, CardRenderParams, render_cards_hand_scene
from ..shared.complexity import build_games_cards_hand_complexity
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_variant
from ..shared.style import SUPPORTED_GAMES_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_background_defaults, load_games_noise_defaults


TASK_ID = "task_games_cards_hand_count"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "single_row",
    "two_row",
)
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    "same_suit_as_reference_count",
    "higher_than_reference_count",
    "pair_count",
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
    higher_rank_target_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    pair_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    longest_run_length_support: Tuple[int, ...] = (2, 3, 4, 5, 6)
    single_row_card_count_support: Tuple[int, ...] = (7, 8, 9, 10)
    two_row_card_count_support: Tuple[int, ...] = (11, 12, 13, 14)
    canvas_width: int = 1180
    canvas_height: int = 760
    card_width_px: int = 98
    card_height_px: int = 142
    panel_margin_px: int = 56
    card_gap_px: int = 14
    row_gap_px: int = 92
    card_corner_radius_px: int = 14
    rank_font_size_px: int = 22
    center_symbol_font_size_px: int = 54
    reference_banner_height_px: int = 24
    reference_font_size_px: int = 16
    continuation_font_size_px: int = 22
    continuation_gap_px: int = 28


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one hand-analysis scene."""

    query_variant: str
    scene_variant: str
    style_variant: str
    target_answer: int
    target_answer_support: Tuple[int, ...]
    card_count: int
    card_count_support: Tuple[int, ...]
    query_variant_probabilities: Dict[str, float]
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


def _resolve_query_variant(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced semantic query variant, honoring `task_variant` as an alias."""

    alias_params = dict(params)
    if alias_params.get("query_variant") is None and alias_params.get("task_variant") is not None:
        alias_params["query_variant"] = alias_params["task_variant"]
    return resolve_games_query_variant(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=alias_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_QUERY_VARIANTS,
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


def _target_support_key(query_variant: str) -> str:
    """Return the configured answer-support key for one query variant."""

    return {
        "same_suit_as_reference_count": "same_suit_target_answer_support",
        "higher_than_reference_count": "higher_rank_target_answer_support",
        "pair_count": "pair_count_support",
        "longest_run_length": "longest_run_length_support",
    }[str(query_variant)]


def _card_count_support_key(scene_variant: str) -> str:
    """Return the configured visible-card support key for one layout family."""

    return {
        "single_row": "single_row_card_count_support",
        "two_row": "two_row_card_count_support",
    }[str(scene_variant)]


def _feasible_card_count_support(
    *,
    scene_variant: str,
    query_variant: str,
    target_answer: int,
    raw_support: Sequence[int],
) -> Tuple[int, ...]:
    """Return the subset of card-count support that can realize the active query."""

    feasible: List[int] = []
    for raw_value in raw_support:
        card_count = int(raw_value)
        if str(query_variant) == "pair_count":
            if int(card_count) < max(8, 2 * int(target_answer)):
                continue
            if int(card_count) > int(13 + int(target_answer)):
                continue
        elif str(query_variant) == "longest_run_length":
            if int(card_count) < int(target_answer):
                continue
        else:
            if int(card_count) < max(7, int(target_answer) + 1):
                continue
        feasible.append(int(card_count))
    return tuple(int(value) for value in feasible)


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve semantic/visual axes plus target answer and visible-card count."""

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

    raw_card_count_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=_card_count_support_key(str(scene_variant)),
        fallback=getattr(_DEFAULTS, _card_count_support_key(str(scene_variant))),
    )
    card_count_support = _feasible_card_count_support(
        scene_variant=str(scene_variant),
        query_variant=str(query_variant),
        target_answer=int(target_answer),
        raw_support=raw_card_count_support,
    )
    if not card_count_support:
        raise ValueError(
            f"no feasible card_count values remain for {query_variant}/{scene_variant} at target {target_answer}"
        )
    card_count_support_key = _card_count_support_key(str(scene_variant))
    card_params = dict(params)
    card_params[str(card_count_support_key)] = list(int(value) for value in card_count_support)
    card_count, card_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=card_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(card_count_support_key),
        explicit_key="card_count",
        fallback_support=card_count_support,
        namespace=f"{TASK_ID}.card_count.{str(scene_variant)}.{str(query_variant)}",
        balanced_flag_key="balanced_card_count_sampling",
        namespace_explicit_sampling_index=True,
    )

    return _ResolvedAxes(
        query_variant=str(query_variant),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        card_count=int(card_count),
        card_count_support=tuple(int(value) for value in card_count_support),
        query_variant_probabilities=dict(query_variant_probabilities),
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


def _sample_same_suit_hand(rng, *, card_count: int, target_answer: int) -> _SampledHand:
    """Sample one hand with exactly `target_answer` cards matching the reference suit."""

    reference_suit = str(SUIT_NAMES[int(rng.randrange(len(SUIT_NAMES)))])
    reference_rank = int(RANK_VALUES[int(rng.randrange(len(RANK_VALUES)))])
    reference_card = (int(reference_rank), str(reference_suit))
    same_suit_pool = [(int(rank), str(reference_suit)) for rank in RANK_VALUES if int(rank) != int(reference_rank)]
    matching_cards = list(rng.sample(same_suit_pool, int(target_answer)))
    other_pool = [(int(rank), str(suit)) for rank, suit in _make_deck() if str(suit) != str(reference_suit)]
    filler_cards = list(rng.sample(other_pool, int(card_count) - 1 - int(target_answer)))
    ordered = matching_cards + filler_cards + [reference_card]
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


def _sample_higher_rank_hand(rng, *, card_count: int, target_answer: int) -> _SampledHand:
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


def _sample_pair_count_hand(rng, *, card_count: int, target_answer: int) -> _SampledHand:
    """Sample one hand with exactly `target_answer` distinct exact pairs."""

    pair_rank_count = int(target_answer)
    if int(card_count) < max(8, 2 * int(pair_rank_count)):
        raise ValueError("pair-count hand requires enough cards to realize the requested pairs")
    pair_ranks = list(rng.sample(list(RANK_VALUES), int(pair_rank_count)))
    remaining_ranks = [int(rank_value) for rank_value in RANK_VALUES if int(rank_value) not in set(pair_ranks)]
    singleton_count = int(card_count) - (2 * int(pair_rank_count))
    if int(singleton_count) > len(remaining_ranks):
        raise ValueError("pair-count hand would require too many singleton ranks")

    raw_cards: List[Tuple[int, str, bool]] = []
    for rank_value in pair_ranks:
        suits = list(rng.sample(list(SUIT_NAMES), 2))
        for suit_name in suits:
            raw_cards.append((int(rank_value), str(suit_name), True))
    singleton_ranks = list(rng.sample(remaining_ranks, int(singleton_count)))
    for rank_value in singleton_ranks:
        raw_cards.append((int(rank_value), str(SUIT_NAMES[int(rng.randrange(len(SUIT_NAMES)))]), False))
    rng.shuffle(raw_cards)

    cards: List[CardInstance] = []
    evidence_card_ids: List[str] = []
    for index, (rank_value, suit_name, in_pair) in enumerate(raw_cards, start=1):
        card_id = f"card_{index:02d}"
        cards.append(
            _label_card(
                card_id=str(card_id),
                rank_value=int(rank_value),
                suit_name=str(suit_name),
                is_reference=False,
            )
        )
        if bool(in_pair):
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


def _sample_non_run_cards(
    rng,
    *,
    count: int,
    blocked_ranks: Sequence[int],
    used_cards: set[Tuple[int, str]],
) -> List[Tuple[int, str]]:
    """Sample `count` cards that avoid forming ascending adjacent runs."""

    safe_cards = [
        (int(rank_value), str(suit_name))
        for rank_value, suit_name in _make_deck()
        if int(rank_value) not in {int(value) for value in blocked_ranks}
    ]
    out: List[Tuple[int, str]] = []
    for _ in range(int(count)):
        previous_rank = None if not out else int(out[-1][0])
        options = [
            (int(rank_value), str(suit_name))
            for rank_value, suit_name in safe_cards
            if (int(rank_value), str(suit_name)) not in used_cards
            and (previous_rank is None or int(rank_value) != int(previous_rank + 1))
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
        blocked_ranks=tuple(run_ranks + ([run_start_rank - 1] if int(run_start_rank) > 2 else []) + ([run_start_rank + run_length] if int(run_start_rank + run_length) <= 14 else [])),
        used_cards=used_cards,
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
        blocked_ranks=tuple(run_ranks + ([run_start_rank - 1] if int(run_start_rank) > 2 else []) + ([run_start_rank + run_length] if int(run_start_rank + run_length) <= 14 else [])),
        used_cards=used_cards,
    )
    ordered = before_cards + run_cards + after_cards
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


def _sample_hand(rng, *, axes: _ResolvedAxes) -> _SampledHand:
    """Sample one visible hand for the resolved query family."""

    if str(axes.query_variant) == "same_suit_as_reference_count":
        return _sample_same_suit_hand(rng, card_count=int(axes.card_count), target_answer=int(axes.target_answer))
    if str(axes.query_variant) == "higher_than_reference_count":
        return _sample_higher_rank_hand(rng, card_count=int(axes.card_count), target_answer=int(axes.target_answer))
    if str(axes.query_variant) == "pair_count":
        return _sample_pair_count_hand(rng, card_count=int(axes.card_count), target_answer=int(axes.target_answer))
    return _sample_longest_run_hand(rng, card_count=int(axes.card_count), target_answer=int(axes.target_answer))


def _build_prompt_json_examples(*, query_variant: str) -> Tuple[str, str]:
    """Return prompt JSON examples matching the active query semantics."""

    if str(query_variant) == "same_suit_as_reference_count":
        answer_and_evidence = {
            "evidence": [
                [164, 188, 262, 330],
                [276, 188, 374, 330],
                [388, 188, 486, 330],
            ],
            "answer": 3,
        }
        answer_only = {"answer": 3}
    elif str(query_variant) == "higher_than_reference_count":
        answer_and_evidence = {
            "evidence": [
                [276, 188, 374, 330],
                [388, 188, 486, 330],
            ],
            "answer": 2,
        }
        answer_only = {"answer": 2}
    elif str(query_variant) == "pair_count":
        answer_and_evidence = {
            "evidence": [
                [164, 188, 262, 330],
                [276, 188, 374, 330],
                [612, 188, 710, 330],
                [724, 188, 822, 330],
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


def _render_params(params: Mapping[str, Any]) -> CardRenderParams:
    """Resolve card-scene rendering parameters from config/defaults."""

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
    )


@register_task
class GamesCardsHandCountTask:
    """Return one grounded counting query over a visible playing-card hand."""

    task_id = TASK_ID
    domain = "games"
    task_group = "cards"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params)

        sampled_hand: _SampledHand | None = None
        rendered_scene = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_hand = _sample_hand(attempt_rng, axes=axes)
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
                    str(axes.query_variant) == "longest_run_length" and str(axes.scene_variant) == "two_row"
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
                "task_family_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "rank_order_text",
                "continuation_rule_text",
                "object_description_single_row",
                "object_description_two_row",
                "answer_hint_same_suit_as_reference_count",
                "answer_hint_higher_than_reference_count",
                "answer_hint_pair_count",
                "answer_hint_longest_run_length",
                "evidence_hint_same_suit_as_reference_count",
                "evidence_hint_higher_than_reference_count",
                "evidence_hint_pair_count",
                "evidence_hint_longest_run_length",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(query_variant=str(axes.query_variant))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            task_variant_key=str(axes.query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_variant)}"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_variant)}"]),
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
            task_id=self.task_id,
            scene_variant=str(axes.scene_variant),
            query_variant=str(axes.query_variant),
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
                    "query_variant": str(axes.query_variant),
                    "task_variant": str(axes.query_variant),
                    "style_variant": str(axes.style_variant),
                    "card_count": int(axes.card_count),
                    "target_answer": int(axes.target_answer),
                    "evidence_entity_ids": list(sampled_hand.evidence_card_ids),
                    "reference_card_id": None if sampled_hand.reference_card_id is None else str(sampled_hand.reference_card_id),
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
                    "card_count": int(axes.card_count),
                    "card_count_support": [int(value) for value in axes.card_count_support],
                    "card_count_probabilities": dict(axes.card_count_probabilities),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_variant": str(axes.query_variant),
                "task_variant": str(axes.query_variant),
                "style_variant": str(axes.style_variant),
                "target_answer": int(axes.target_answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "card_count": int(axes.card_count),
                "card_count_support": [int(value) for value in axes.card_count_support],
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
                "type": "id_set",
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
            task_variant=str(axes.query_variant),
        )


__all__ = ["GamesCardsHandCountTask"]
