"""Identity-free sampling primitives for solitaire tableau scenes."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from trace.core.seed import spawn_rng
from trace.tasks.shared.support_sampling import resolve_integer_choice

from .defaults import DEFAULTS, GEN_DEFAULTS
from .rules import (
    card_color,
    deck,
    is_legal_foundation_move,
    is_legal_tableau_move,
    is_same_suit_descending_next,
    remove_card,
)
from .state import (
    CARD_BADGE_LABELS,
    MOVE_OPTION_LABELS,
    SUITS,
    SUIT_SHORT,
    Card,
    Foundation,
    MoveOption,
    SolitaireSample,
)


def sample_integer_axis(
    *,
    namespace: str,
    instance_seed: int,
    params: Mapping[str, Any],
    support_key: str,
    explicit_key: str,
    fallback_support: Sequence[int],
    axis_name: str,
    balanced_flag_key: str,
) -> Tuple[int, Dict[str, float]]:
    value, probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=GEN_DEFAULTS,
        support_key=str(support_key),
        explicit_key=str(explicit_key),
        fallback_support=tuple(int(item) for item in fallback_support),
        namespace=f"{str(namespace)}.{str(axis_name)}",
        balanced_flag_key=str(balanced_flag_key),
        namespace_support_permutation=True,
    )
    return int(value), dict(probabilities)


def sample_foundations(rng) -> Tuple[Foundation, ...]:
    foundations: List[Foundation] = []
    for suit in SUITS:
        top_rank = int(rng.randrange(0, 7))
        foundations.append(
            Foundation(
                foundation_id=f"foundation_{SUIT_SHORT[str(suit)].lower()}",
                suit_name=str(suit),
                top_rank_value=int(top_rank),
            )
        )
    return tuple(foundations)


def deck_after_foundations(foundations: Sequence[Foundation]) -> List[Tuple[int, str]]:
    top_by_suit = {str(foundation.suit_name): int(foundation.top_rank_value) for foundation in foundations}
    return [
        (int(rank), str(suit))
        for rank, suit in deck()
        if int(rank) > int(top_by_suit.get(str(suit), 0))
    ]


def build_columns_from_exposed(
    rng,
    *,
    exposed_cards: Sequence[Card],
    pool: List[Tuple[int, str]],
    scene_variant: str,
) -> Tuple[Tuple[Card, ...], ...]:
    columns: List[Tuple[Card, ...]] = []
    for index, exposed in enumerate(exposed_cards):
        filler_count = int(rng.randrange(0, 3 if str(scene_variant) == "freecell_tableau" else 4))
        filler_cards: List[Card] = []
        for filler_index in range(filler_count):
            if not pool:
                break
            rank, suit = pool.pop(int(rng.randrange(len(pool))))
            filler_cards.append(
                Card(
                    card_id=f"col_{index + 1:02d}_card_{filler_index + 1:02d}",
                    rank_value=int(rank),
                    suit_name=str(suit),
                    badge_text=None,
                )
            )
        exposed_id = f"col_{index + 1:02d}_card_{len(filler_cards) + 1:02d}"
        columns.append(
            tuple(
                [
                    *filler_cards,
                    Card(
                        card_id=str(exposed_id),
                        rank_value=int(exposed.rank_value),
                        suit_name=str(exposed.suit_name),
                        badge_text=str(exposed.badge_text) if exposed.badge_text else None,
                    ),
                ]
            )
        )
    return tuple(columns)


def visible_exposed_cards(columns: Sequence[Sequence[Card]]) -> Tuple[Card, ...]:
    return tuple(column[-1] for column in columns if len(column) > 0)


def foundation_by_id(foundations: Sequence[Foundation]) -> Dict[str, Foundation]:
    return {str(foundation.foundation_id): foundation for foundation in foundations}


def card_by_id(columns: Sequence[Sequence[Card]]) -> Dict[str, Card]:
    return {str(card.card_id): card for column in columns for card in column}


def target_is_legal(source: Card, target_id: str, *, columns: Sequence[Sequence[Card]], foundations: Sequence[Foundation]) -> bool:
    cards = card_by_id(columns)
    if str(target_id) in cards:
        return is_legal_tableau_move(source, cards[str(target_id)])
    foundations_by_id = foundation_by_id(foundations)
    if str(target_id) in foundations_by_id:
        return is_legal_foundation_move(source, foundations_by_id[str(target_id)])
    return False


def sample_move_option_count(*, namespace: str, instance_seed: int, params: Mapping[str, Any]) -> Tuple[int, Dict[str, float]]:
    return sample_integer_axis(
        namespace=str(namespace),
        instance_seed=int(instance_seed),
        params=params,
        support_key="move_option_count_support",
        explicit_key="option_count",
        fallback_support=DEFAULTS.move_option_count_support,
        axis_name="move_option_count",
        balanced_flag_key="balanced_option_count_sampling",
    )


def answer_option_label(*, instance_seed: int, params: Mapping[str, Any], option_count: int) -> str:
    raw = params.get("answer_option_label")
    labels = MOVE_OPTION_LABELS[: int(option_count)]
    if raw is not None:
        label = str(raw).strip().upper()
        if label not in labels:
            raise ValueError(f"unsupported answer_option_label for {option_count} options: {label}")
        return str(label)
    cursor = params.get("_sample_cursor")
    if cursor is not None:
        return str(labels[abs(int(cursor)) % len(labels)])
    rng = spawn_rng(int(instance_seed), "games.solitaire.answer_option_label")
    return str(labels[int(rng.randrange(len(labels)))])


def sample_move_legality(
    rng,
    *,
    namespace: str,
    instance_seed: int,
    params: Mapping[str, Any],
    scene_variant: str,
) -> SolitaireSample:
    """Construct a tableau where exactly one displayed source-to-target move option is legal."""

    option_count, option_count_probabilities = sample_move_option_count(
        namespace=str(namespace),
        instance_seed=int(instance_seed),
        params=params,
    )
    answer_label = answer_option_label(instance_seed=int(instance_seed), params=params, option_count=int(option_count))
    for _attempt in range(600):
        foundations = sample_foundations(rng)
        pool = deck_after_foundations(foundations)
        column_count = 7 if str(scene_variant) == "klondike_tableau" else 8
        mode = "foundation" if int(rng.randrange(2)) == 0 else "tableau"
        exposed_raw: List[Tuple[int, str]] = []
        answer_source: Tuple[int, str]
        answer_target_id: str
        answer_target_label: str
        if mode == "foundation":
            candidate_foundations = [
                foundation
                for foundation in foundations
                if int(foundation.top_rank_value) < 13 and (int(foundation.top_rank_value) + 1, str(foundation.suit_name)) in pool
            ]
            if not candidate_foundations:
                continue
            foundation = candidate_foundations[int(rng.randrange(len(candidate_foundations)))]
            answer_source = (int(foundation.top_rank_value) + 1, str(foundation.suit_name))
            answer_target_id = str(foundation.foundation_id)
            answer_target_label = str(foundation.label)
            remove_card(pool, answer_source)
            exposed_raw.append(answer_source)
        else:
            target_rank = int(rng.randrange(2, 14))
            target_suit = str(SUITS[int(rng.randrange(len(SUITS)))])
            opposite = [suit for suit in SUITS if card_color(str(suit)) != card_color(str(target_suit))]
            source_suit = str(opposite[int(rng.randrange(len(opposite)))])
            answer_source = (int(target_rank - 1), str(source_suit))
            target_raw = (int(target_rank), str(target_suit))
            if answer_source not in pool or target_raw not in pool:
                continue
            remove_card(pool, answer_source)
            remove_card(pool, target_raw)
            exposed_raw.extend([answer_source, target_raw])
            answer_target_id = "pending_target_card"
            answer_target_label = "pending"

        while len(exposed_raw) < int(column_count):
            if not pool:
                break
            exposed_raw.append(pool.pop(int(rng.randrange(len(pool)))))
        if len(exposed_raw) != int(column_count):
            continue
        rng.shuffle(exposed_raw)
        exposed_cards = tuple(
            Card(
                card_id=f"exposed_{index + 1:02d}",
                rank_value=int(rank),
                suit_name=str(suit),
                badge_text=str(CARD_BADGE_LABELS[index]),
            )
            for index, (rank, suit) in enumerate(exposed_raw)
        )
        columns = build_columns_from_exposed(rng, exposed_cards=exposed_cards, pool=pool, scene_variant=str(scene_variant))
        exposed_by_raw = {
            (int(card.rank_value), str(card.suit_name)): card
            for card in visible_exposed_cards(columns)
        }
        source_card = exposed_by_raw.get((int(answer_source[0]), str(answer_source[1])))
        if source_card is None:
            continue
        if mode == "tableau":
            legal_targets = [
                card
                for card in visible_exposed_cards(columns)
                if str(card.card_id) != str(source_card.card_id) and is_legal_tableau_move(source_card, card)
            ]
            if not legal_targets:
                continue
            target_card = legal_targets[0]
            answer_target_id = str(target_card.card_id)
            answer_target_label = str(target_card.badge_text)
        answer_source_badge = str(source_card.badge_text)

        all_targets: List[Tuple[str, str]] = [
            (str(card.card_id), str(card.badge_text))
            for card in visible_exposed_cards(columns)
            if str(card.card_id) != str(source_card.card_id)
        ] + [(str(foundation.foundation_id), str(foundation.label)) for foundation in foundations]
        all_sources = [(str(card.card_id), str(card.badge_text)) for card in visible_exposed_cards(columns)]
        distractor_pairs: List[Tuple[str, str, str, str]] = []
        for src_id, src_badge in all_sources:
            src_card = card_by_id(columns)[str(src_id)]
            for target_id, target_label in all_targets:
                if str(src_id) == str(target_id):
                    continue
                is_answer_pair = str(src_id) == str(source_card.card_id) and str(target_id) == str(answer_target_id)
                if is_answer_pair:
                    continue
                if not target_is_legal(src_card, str(target_id), columns=columns, foundations=foundations):
                    distractor_pairs.append((str(src_id), str(src_badge), str(target_id), str(target_label)))
        rng.shuffle(distractor_pairs)
        if len(distractor_pairs) < int(option_count) - 1:
            continue
        options: List[MoveOption] = []
        distractor_cursor = 0
        for label in MOVE_OPTION_LABELS[: int(option_count)]:
            if str(label) == str(answer_label):
                options.append(
                    MoveOption(
                        option_id=f"move_option_{str(label).lower()}",
                        label=str(label),
                        source_card_id=str(source_card.card_id),
                        source_badge=str(answer_source_badge),
                        target_id=str(answer_target_id),
                        target_label=str(answer_target_label),
                        is_answer=True,
                    )
                )
            else:
                src_id, src_badge, target_id, target_label = distractor_pairs[int(distractor_cursor)]
                distractor_cursor += 1
                options.append(
                    MoveOption(
                        option_id=f"move_option_{str(label).lower()}",
                        label=str(label),
                        source_card_id=str(src_id),
                        source_badge=str(src_badge),
                        target_id=str(target_id),
                        target_label=str(target_label),
                        is_answer=False,
                    )
                )
        legal_options = [
            option
            for option in options
            if target_is_legal(card_by_id(columns)[str(option.source_card_id)], str(option.target_id), columns=columns, foundations=foundations)
        ]
        if len(legal_options) != 1 or str(legal_options[0].label) != str(answer_label):
            continue
        annotation = (str(source_card.card_id), str(answer_target_id))
        return SolitaireSample(
            scene_variant=str(scene_variant),
            columns=tuple(columns),
            foundations=tuple(foundations),
            answer=str(answer_label),
            answer_type="option_letter",
            annotation_entity_ids=tuple(annotation),
            move_options=tuple(options),
            metadata={
                "legal_move_kind": str(mode),
                "answer_option_label": str(answer_label),
                "option_count": int(option_count),
                "option_count_probabilities": dict(option_count_probabilities),
                "legal_source_id": str(source_card.card_id),
                "legal_source_label": str(answer_source_badge),
                "legal_target_id": str(answer_target_id),
                "legal_target_label": str(answer_target_label),
                "legal_move_answer": f"{str(answer_source_badge)}->{str(answer_target_label)}",
                "move_options": [
                    {
                        "label": str(option.label),
                        "source_card_id": str(option.source_card_id),
                        "source_label": str(option.source_badge),
                        "target_id": str(option.target_id),
                        "target_label": str(option.target_label),
                        "move": str(option.move_text),
                        "is_answer": bool(option.is_answer),
                    }
                    for option in options
                ],
            },
        )
    raise ValueError("failed to sample solitaire move-legality scene")


def sample_foundation_ready(
    rng,
    *,
    namespace: str,
    instance_seed: int,
    params: Mapping[str, Any],
    scene_variant: str,
) -> SolitaireSample:
    """Construct exposed tableau cards with a requested count of legal foundation moves."""

    target_answer, target_probabilities = sample_integer_axis(
        namespace=str(namespace),
        instance_seed=int(instance_seed),
        params=params,
        support_key="foundation_ready_target_answer_support",
        explicit_key="target_answer",
        fallback_support=DEFAULTS.foundation_ready_target_answer_support,
        axis_name="foundation_ready_target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
    )
    for _attempt in range(500):
        foundations = sample_foundations(rng)
        pool = deck_after_foundations(foundations)
        ready_raw = [
            (int(foundation.top_rank_value) + 1, str(foundation.suit_name))
            for foundation in foundations
            if int(foundation.top_rank_value) < 13 and (int(foundation.top_rank_value) + 1, str(foundation.suit_name)) in pool
        ]
        if len(ready_raw) < int(target_answer):
            continue
        rng.shuffle(ready_raw)
        selected_ready = ready_raw[: int(target_answer)]
        exposed_raw: List[Tuple[int, str]] = []
        for raw in selected_ready:
            remove_card(pool, raw)
            exposed_raw.append(raw)
        non_ready_pool = []
        foundation_by_suit = {str(f.suit_name): f for f in foundations}
        for raw in list(pool):
            rank, suit = raw
            candidate_card = Card(card_id="candidate", rank_value=int(rank), suit_name=str(suit))
            if not is_legal_foundation_move(candidate_card, foundation_by_suit[str(suit)]):
                non_ready_pool.append(raw)
        column_count = 7 if str(scene_variant) == "klondike_tableau" else 8
        if len(non_ready_pool) < int(column_count) - len(exposed_raw):
            continue
        rng.shuffle(non_ready_pool)
        for raw in non_ready_pool[: int(column_count) - len(exposed_raw)]:
            remove_card(pool, raw)
            exposed_raw.append(raw)
        rng.shuffle(exposed_raw)
        exposed_cards = tuple(
            Card(
                card_id=f"exposed_{index + 1:02d}",
                rank_value=int(rank),
                suit_name=str(suit),
                badge_text=str(CARD_BADGE_LABELS[index]),
            )
            for index, (rank, suit) in enumerate(exposed_raw)
        )
        columns = build_columns_from_exposed(rng, exposed_cards=exposed_cards, pool=pool, scene_variant=str(scene_variant))
        foundation_by_suit = {str(f.suit_name): f for f in foundations}
        ready_ids = tuple(
            str(card.card_id)
            for card in visible_exposed_cards(columns)
            if is_legal_foundation_move(card, foundation_by_suit[str(card.suit_name)])
        )
        if len(ready_ids) != int(target_answer):
            continue
        return SolitaireSample(
            scene_variant=str(scene_variant),
            columns=tuple(columns),
            foundations=tuple(foundations),
            answer=int(target_answer),
            answer_type="integer",
            annotation_entity_ids=tuple([*ready_ids, *[str(f.foundation_id) for f in foundations]]),
            move_options=(),
            metadata={
                "target_answer": int(target_answer),
                "target_answer_probabilities": dict(target_probabilities),
                "ready_card_ids": list(ready_ids),
                "ready_card_labels": [str(card_by_id(columns)[card_id].badge_text) for card_id in ready_ids],
            },
        )
    raise ValueError("failed to sample solitaire foundation-ready scene")


def make_sequence_columns(
    rng,
    *,
    target_answer: int,
    scene_variant: str,
) -> Tuple[Tuple[Card, ...], Tuple[Tuple[str, str], ...]]:
    """Build tableau columns with an exact number of adjacent alternating-color descending pairs."""

    column_count = 7 if str(scene_variant) == "klondike_tableau" else 8
    lengths = [int(rng.randrange(3, 6)) for _ in range(int(column_count))]
    pair_slots = [(col, pos) for col, length in enumerate(lengths) for pos in range(int(length) - 1)]
    if int(target_answer) > len(pair_slots):
        raise ValueError("target answer exceeds visible adjacent-pair slots")
    rng.shuffle(pair_slots)
    valid_slot_set = set(pair_slots[: int(target_answer)])
    pool = deck()
    columns: List[Tuple[Card, ...]] = []
    valid_pairs: List[Tuple[str, str]] = []
    for col_index, length in enumerate(lengths):
        cards: List[Card] = []
        for pos in range(int(length)):
            card_id = f"col_{col_index + 1:02d}_card_{pos + 1:02d}"
            badge = str(CARD_BADGE_LABELS[col_index]) if pos == int(length) - 1 else None
            if pos == 0:
                raw_candidates = [raw for raw in pool if int(raw[0]) >= 4]
                if not raw_candidates:
                    raise ValueError("empty sequence-card candidate pool")
                raw = raw_candidates[int(rng.randrange(len(raw_candidates)))]
            else:
                previous = cards[-1]
                should_be_valid = (int(col_index), int(pos - 1)) in valid_slot_set
                if should_be_valid and int(previous.rank_value) > 1:
                    candidates = [
                        raw
                        for raw in pool
                        if int(raw[0]) == int(previous.rank_value) - 1
                        and card_color(str(raw[1])) != card_color(str(previous.suit_name))
                    ]
                    if not candidates:
                        raise ValueError("no valid descending sequence candidate")
                    raw = candidates[int(rng.randrange(len(candidates)))]
                else:
                    candidates = [
                        raw
                        for raw in pool
                        if not (
                            int(raw[0]) == int(previous.rank_value) - 1
                            and card_color(str(raw[1])) != card_color(str(previous.suit_name))
                        )
                    ]
                    if not candidates:
                        raise ValueError("no invalid sequence candidate")
                    raw = candidates[int(rng.randrange(len(candidates)))]
            remove_card(pool, raw)
            card = Card(card_id=str(card_id), rank_value=int(raw[0]), suit_name=str(raw[1]), badge_text=badge)
            if pos > 0:
                previous = cards[-1]
                if is_legal_tableau_move(card, previous):
                    valid_pairs.append((str(previous.card_id), str(card.card_id)))
            cards.append(card)
        columns.append(tuple(cards))
    if len(valid_pairs) != int(target_answer):
        raise ValueError("constructed sequence count mismatch")
    return tuple(columns), tuple(valid_pairs)


def sample_tableau_sequence(
    rng,
    *,
    namespace: str,
    instance_seed: int,
    params: Mapping[str, Any],
    scene_variant: str,
) -> SolitaireSample:
    """Sample the exact-count adjacent tableau sequence objective and its card witnesses."""

    target_answer, target_probabilities = sample_integer_axis(
        namespace=str(namespace),
        instance_seed=int(instance_seed),
        params=params,
        support_key="tableau_sequence_target_answer_support",
        explicit_key="target_answer",
        fallback_support=DEFAULTS.tableau_sequence_target_answer_support,
        axis_name="tableau_sequence_target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
    )
    for _attempt in range(400):
        try:
            columns, valid_pairs = make_sequence_columns(
                rng,
                target_answer=int(target_answer),
                scene_variant=str(scene_variant),
            )
        except ValueError:
            continue
        annotation_ids = tuple(dict.fromkeys([card_id for pair in valid_pairs for card_id in pair]))
        return SolitaireSample(
            scene_variant=str(scene_variant),
            columns=tuple(columns),
            foundations=sample_foundations(rng),
            answer=int(target_answer),
            answer_type="integer",
            annotation_entity_ids=tuple(annotation_ids),
            move_options=(),
            metadata={
                "target_answer": int(target_answer),
                "target_answer_probabilities": dict(target_probabilities),
                "valid_sequence_pairs": [[str(a), str(b)] for a, b in valid_pairs],
                "valid_sequence_pair_count": int(len(valid_pairs)),
            },
        )
    raise ValueError("failed to sample solitaire tableau-sequence scene")


def sample_same_suit_run_length(
    rng,
    *,
    namespace: str,
    instance_seed: int,
    params: Mapping[str, Any],
    scene_variant: str,
) -> SolitaireSample:
    """Construct one marked card whose downward same-suit run has the requested length."""

    target_answer, target_probabilities = sample_integer_axis(
        namespace=str(namespace),
        instance_seed=int(instance_seed),
        params=params,
        support_key="same_suit_run_length_target_answer_support",
        explicit_key="target_answer",
        fallback_support=DEFAULTS.same_suit_run_length_target_answer_support,
        axis_name="same_suit_run_length_target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
    )
    column_count = 7 if str(scene_variant) == "klondike_tableau" else 8
    for _attempt in range(500):
        target_length = int(target_answer)
        if target_length < 1:
            continue
        pool = deck()
        target_col_index = int(rng.randrange(column_count))
        target_suit = str(SUITS[int(rng.randrange(len(SUITS)))])
        min_start_rank = min(13, max(target_length + 1, target_length))
        if min_start_rank > 13:
            continue
        start_rank = int(rng.randrange(min_start_rank, 14))
        prefix_count = int(rng.randrange(0, 3))
        run_raw = [(int(start_rank - offset), str(target_suit)) for offset in range(target_length)]
        if any(raw not in pool for raw in run_raw):
            continue
        for raw in run_raw:
            remove_card(pool, raw)

        breaker_candidates = [
            raw
            for raw in pool
            if not (int(raw[0]) == int(start_rank - target_length) and str(raw[1]) == str(target_suit))
        ]
        if not breaker_candidates:
            continue
        breaker_raw = breaker_candidates[int(rng.randrange(len(breaker_candidates)))]
        remove_card(pool, breaker_raw)

        prefix_raw: List[Tuple[int, str]] = []
        for prefix_index in range(prefix_count):
            candidates = list(pool)
            if prefix_index == int(prefix_count) - 1:
                candidates = [
                    raw
                    for raw in candidates
                    if not (int(raw[0]) == int(start_rank + 1) and str(raw[1]) == str(target_suit))
                ]
            if not candidates:
                break
            raw = candidates[int(rng.randrange(len(candidates)))]
            remove_card(pool, raw)
            prefix_raw.append(raw)
        if len(prefix_raw) != int(prefix_count):
            continue

        columns: List[Tuple[Card, ...]] = []
        marked_card_id = ""
        run_card_ids: List[str] = []
        run_card_labels: List[str] = []
        for col_index in range(column_count):
            if int(col_index) == int(target_col_index):
                raw_cards = [*prefix_raw, *run_raw, breaker_raw]
            else:
                length = int(rng.randrange(3, 6))
                if len(pool) < length:
                    raise ValueError("not enough cards for solitaire same-suit run distractor columns")
                raw_cards = []
                for _ in range(length):
                    raw = pool.pop(int(rng.randrange(len(pool))))
                    raw_cards.append(raw)
            cards: List[Card] = []
            for row_index, raw in enumerate(raw_cards):
                card_id = f"col_{col_index + 1:02d}_card_{row_index + 1:02d}"
                badge = str(CARD_BADGE_LABELS[col_index]) if int(row_index) == len(raw_cards) - 1 else None
                card = Card(card_id=str(card_id), rank_value=int(raw[0]), suit_name=str(raw[1]), badge_text=badge)
                cards.append(card)
                if int(col_index) == int(target_col_index):
                    run_start = int(prefix_count)
                    run_end = int(prefix_count) + int(target_length)
                    if int(row_index) == run_start:
                        marked_card_id = str(card_id)
                    if run_start <= int(row_index) < run_end:
                        run_card_ids.append(str(card_id))
                        run_card_labels.append(str(card.label))
            columns.append(tuple(cards))

        if not marked_card_id or len(run_card_ids) != int(target_length):
            continue
        card_map = card_by_id(columns)
        measured_ids = [str(marked_card_id)]
        current_id = str(marked_card_id)
        while True:
            current = card_map[str(current_id)]
            current_spec = next(
                spec
                for spec in (
                    {
                        "card_id": str(card.card_id),
                        "column_index": int(col_index),
                        "row_index": int(row_index),
                    }
                    for col_index, column in enumerate(columns)
                    for row_index, card in enumerate(column)
                )
                if str(spec["card_id"]) == str(current_id)
            )
            next_row_index = int(current_spec["row_index"]) + 1
            column = columns[int(current_spec["column_index"])]
            if next_row_index >= len(column):
                break
            next_card = column[next_row_index]
            if not is_same_suit_descending_next(current, next_card):
                break
            measured_ids.append(str(next_card.card_id))
            current_id = str(next_card.card_id)
        if tuple(measured_ids) != tuple(run_card_ids):
            continue
        return SolitaireSample(
            scene_variant=str(scene_variant),
            columns=tuple(columns),
            foundations=sample_foundations(rng),
            answer=int(target_length),
            answer_type="integer",
            annotation_entity_ids=tuple(run_card_ids),
            move_options=(),
            metadata={
                "target_answer": int(target_length),
                "target_answer_probabilities": dict(target_probabilities),
                "marked_card_id": str(marked_card_id),
                "marked_card_column_index": int(target_col_index),
                "marked_card_row_index": int(prefix_count),
                "same_suit_run_card_ids": list(run_card_ids),
                "same_suit_run_card_labels": list(run_card_labels),
                "same_suit_run_length": int(target_length),
                "same_suit_run_suit": str(target_suit),
            },
        )
    raise ValueError("failed to sample solitaire same-suit run-length scene")
