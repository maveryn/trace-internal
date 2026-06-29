"""Scene-neutral Tangram sampling primitives."""

from __future__ import annotations

from typing import Any, Mapping

from trace.core.sampling import (
    integer_range_choice,
    sample_without_replacement,
    support_probability_map,
    uniform_choice,
    weighted_support_choice,
)
from trace.core.seed import spawn_rng
from trace.tasks.puzzles.shared.option_layout import centered_option_grid_shape
from trace.tasks.shared.config_defaults import (
    group_default,
    resolve_required_int_bounds,
)
from trace.tasks.shared.mcq import option_label_for_index

from .rules import contact_mark_candidates, edge_touching_piece_ids
from .spatial_primitives import (
    BASE_PIECES,
    MIRROR_DISTRACTOR_EXCLUSIONS,
    OPTION_SHAPES,
    piece_by_id,
)
from .state import OptionSpec, PieceSpec, TangramSample


def option_count_support(
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> tuple[int, ...]:
    """Return the configured visual-option count support."""

    lower, upper = resolve_required_int_bounds(
        params,
        generation_defaults,
        min_key="option_count_min",
        max_key="option_count_max",
        fallback_min=4,
        fallback_max=6,
        context="Tangram option-count bounds",
    )
    return tuple(range(int(lower), int(upper) + 1))


def choose_option_count(
    *,
    rng,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    minimum_for_answer_index: int | None = None,
) -> tuple[int, tuple[int, int], dict[str, float]]:
    """Sample one option count from explicit support and return probabilities."""

    support = option_count_support(params, generation_defaults)
    if minimum_for_answer_index is not None:
        support = tuple(
            value for value in support if int(value) > int(minimum_for_answer_index)
        )
    if not support:
        raise ValueError("Tangram option-count support is empty")
    selected, probabilities = weighted_support_choice(rng, support, sort_keys=True)
    return int(selected), (int(min(support)), int(max(support))), dict(probabilities)


def choose_target_piece(
    *,
    rng,
    params: Mapping[str, Any],
) -> PieceSpec:
    """Sample or resolve one Tangram piece as a target/missing region."""

    explicit = params.get("target_piece_id")
    if explicit is not None:
        return piece_by_id(str(explicit))
    return uniform_choice(rng, BASE_PIECES)


def choose_contact_mark_set(
    *,
    rng,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[int, ...], dict[str, float]]:
    """Sample a marked-piece set with a feasible counted total."""

    grouped = contact_mark_candidates()
    lower, upper = resolve_required_int_bounds(
        params,
        generation_defaults,
        min_key="contact_count_min",
        max_key="contact_count_max",
        fallback_min=2,
        fallback_max=7,
        context="Tangram contact-count bounds",
    )
    support = tuple(
        count for count in range(int(lower), int(upper) + 1) if count in grouped
    )
    if not support:
        raise ValueError("Tangram contact-count support has no feasible marked sets")
    explicit = params.get("target_contact_count")
    if explicit is not None:
        selected_count = int(explicit)
        if selected_count not in set(support):
            raise ValueError(
                f"target_contact_count={selected_count} is not feasible for Tangram"
            )
        count_probabilities = support_probability_map(support, selected=selected_count)
    else:
        selected_count, count_probabilities = weighted_support_choice(
            rng,
            support,
            sort_keys=True,
        )
        selected_count = int(selected_count)
    marked, touching = uniform_choice(rng, tuple(grouped[int(selected_count)]))
    return tuple(marked), tuple(touching), support, dict(count_probabilities)


def build_missing_piece_options(
    *,
    rng,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    target_piece: PieceSpec,
) -> tuple[tuple[OptionSpec, ...], int, tuple[int, int], dict[str, float]]:
    """Build unique labeled visual options for the missing-piece task."""

    max_option_count = max(option_count_support(params, generation_defaults))
    answer_index, _answer_index_probabilities = integer_range_choice(
        rng,
        0,
        int(max_option_count) - 1,
    )
    option_count, option_range, option_count_probabilities = choose_option_count(
        rng=rng,
        params=params,
        generation_defaults=generation_defaults,
        minimum_for_answer_index=int(answer_index),
    )
    correct_shape_id = str(target_piece.shape_id)
    excluded = {correct_shape_id}
    mirror_shape_id = MIRROR_DISTRACTOR_EXCLUSIONS.get(correct_shape_id)
    if mirror_shape_id is not None:
        excluded.add(str(mirror_shape_id))
    distractor_pool = tuple(
        shape_id for shape_id in OPTION_SHAPES if shape_id not in excluded
    )
    distractors = sample_without_replacement(
        rng,
        distractor_pool,
        max(0, int(option_count) - 1),
    )
    ordered_shape_ids = [correct_shape_id, *[str(item) for item in distractors]]
    ordered_shape_ids.remove(correct_shape_id)
    ordered_shape_ids.insert(int(answer_index), correct_shape_id)

    option_specs: list[OptionSpec] = []
    for option_index, shape_id in enumerate(ordered_shape_ids):
        rotation = int(rng.randrange(0, 4) * 90)
        option_specs.append(
            OptionSpec(
                option_id=f"option_{option_index}",
                option_label=option_label_for_index(option_index),
                shape_id=str(shape_id),
                is_correct=bool(option_index == int(answer_index)),
                display_rotation_degrees=int(rotation),
                shape_points=tuple(OPTION_SHAPES[str(shape_id)]),
            )
        )
    return (
        tuple(option_specs),
        int(answer_index),
        option_range,
        option_count_probabilities,
    )


def make_contact_sample(
    *,
    rng,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> tuple[TangramSample, dict[str, Any]]:
    """Construct a contact-count sample and return sampling metadata."""

    marked_piece_ids, touching_ids, support, count_probabilities = (
        choose_contact_mark_set(
            rng=rng,
            params=params,
            generation_defaults=generation_defaults,
        )
    )
    if edge_touching_piece_ids(marked_piece_ids) != touching_ids:
        raise ValueError("Tangram contact helper produced inconsistent touching set")
    target_piece = piece_by_id(str(marked_piece_ids[0]))
    sample = TangramSample(
        piece_specs=BASE_PIECES,
        target_piece_ids=tuple(marked_piece_ids),
        target_piece_id=str(target_piece.piece_id),
        target_shape_id=str(target_piece.shape_id),
        target_shape_name=str(target_piece.shape_name),
        contact_piece_ids=tuple(touching_ids),
        contact_count=int(len(marked_piece_ids) + len(touching_ids)),
        contact_count_support=tuple(int(value) for value in support),
        option_specs=(),
        option_count=0,
        option_count_range=(0, 0),
        correct_option_index=None,
        answer_option_label="",
        correct_option_panel_id="",
        construction_mode="marked_neighbors",
    )
    return sample, {
        "contact_count_probabilities": dict(count_probabilities),
    }


def make_missing_piece_sample(
    *,
    rng,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> tuple[TangramSample, dict[str, Any]]:
    """Construct a missing-piece option sample and return sampling metadata."""

    target_piece = choose_target_piece(rng=rng, params=params)
    option_specs, answer_index, option_range, option_count_probabilities = (
        build_missing_piece_options(
            rng=rng,
            params=params,
            generation_defaults=generation_defaults,
            target_piece=target_piece,
        )
    )
    correct_option = option_specs[int(answer_index)]
    sample = TangramSample(
        piece_specs=BASE_PIECES,
        target_piece_ids=(str(target_piece.piece_id),),
        target_piece_id=str(target_piece.piece_id),
        target_shape_id=str(target_piece.shape_id),
        target_shape_name=str(target_piece.shape_name),
        contact_piece_ids=tuple(edge_touching_piece_ids((str(target_piece.piece_id),))),
        contact_count=0,
        contact_count_support=(),
        option_specs=tuple(option_specs),
        option_count=int(len(option_specs)),
        option_count_range=tuple(option_range),
        correct_option_index=int(answer_index),
        answer_option_label=str(correct_option.option_label),
        correct_option_panel_id=str(correct_option.option_id),
        construction_mode="gap_options",
    )
    return sample, {
        "option_count_probabilities": dict(option_count_probabilities),
        "option_grid_shape": list(centered_option_grid_shape(int(len(option_specs)))),
    }


def sample_rng(instance_seed: int, namespace: str):
    """Return the canonical Tangram sampling RNG for one task attempt."""

    return spawn_rng(int(instance_seed), f"{namespace}.sample")


__all__ = [
    "build_missing_piece_options",
    "choose_contact_mark_set",
    "choose_option_count",
    "choose_target_piece",
    "make_contact_sample",
    "make_missing_piece_sample",
    "option_count_support",
    "sample_rng",
]
