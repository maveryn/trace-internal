"""Sampling primitives for word-search puzzle tasks."""

from __future__ import annotations

from string import ascii_uppercase
from typing import Any, Mapping

from trace.core.sampling import (
    integer_range_choice,
    uniform_choice,
    uniform_choice_with_probabilities,
    weighted_support_choice,
)
from trace.tasks.puzzles.shared.word_grid import (
    WORD_DIRECTIONS,
    Cell,
    WordPlacement,
    cell_key,
    choose_words,
    direction_code,
    fill_random_letters,
    place_word,
    scan_word,
    word_chip_key,
)

from .defaults import get_int_range
from .state import OPTION_LABELS, SCENE_VARIANTS, WordSearchDataset, WordSearchOption


def resolve_scene_variant(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    rng,
) -> tuple[str, dict[str, float]]:
    """Sample or honor the visual word-search scene variant."""

    explicit = params.get("scene_variant")
    if explicit is not None:
        selected = str(explicit)
        if selected not in SCENE_VARIANTS:
            raise ValueError(f"unsupported word-search scene_variant: {selected}")
        return selected, {
            key: (1.0 if key == selected else 0.0) for key in SCENE_VARIANTS
        }
    weights = defaults.get("scene_variant_weights")
    if isinstance(weights, Mapping):
        return weighted_support_choice(rng, SCENE_VARIANTS, weights=weights)
    return uniform_choice_with_probabilities(rng, SCENE_VARIANTS)


def resolve_grid_size(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    rng,
) -> tuple[int, int, tuple[int, int]]:
    """Resolve a square word-search grid size."""

    size_min, size_max = get_int_range(
        params,
        defaults,
        min_key="grid_size_min",
        max_key="grid_size_max",
        fallback_min=5,
        fallback_max=8,
    )
    explicit_size = params.get("grid_size")
    if explicit_size is None:
        size, _probabilities = integer_range_choice(rng, size_min, size_max)
    else:
        size = int(explicit_size)
    if not int(size_min) <= int(size) <= int(size_max):
        raise ValueError("grid_size outside configured range")
    return int(size), int(size), (int(size_min), int(size_max))


def sample_location_dataset(
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    rng,
    scene_variant: str,
    scene_variant_probabilities: Mapping[str, float],
    option_count: int,
    answer_label: str,
) -> WordSearchDataset:
    """Build a target-word location option dataset."""

    rows, cols, size_range = resolve_grid_size(params, generation_defaults, rng)
    word_min, word_max = get_int_range(
        params,
        generation_defaults,
        min_key="word_length_min",
        max_key="word_length_max",
        fallback_min=3,
        fallback_max=4,
    )
    for _attempt in range(250):
        word = choose_words(rng, count=1, min_len=word_min, max_len=word_max)[0]
        grid = [["" for _ in range(cols)] for _ in range(rows)]
        placed = place_word(grid, word, rng)
        fill_random_letters(grid, rng)
        hits = scan_word(grid, word)
        if len(hits) != 1:
            continue
        placement = hits[0]
        options = _build_location_options(
            placement=placement,
            rows=rows,
            cols=cols,
            option_count=int(option_count),
            answer_label=str(answer_label),
            rng=rng,
        )
        return WordSearchDataset(
            rows=int(rows),
            cols=int(cols),
            grid_size_range=tuple(size_range),
            grid=tuple(tuple(str(value) for value in row) for row in grid),
            scene_variant=str(scene_variant),
            scene_variant_probabilities=dict(scene_variant_probabilities),
            target_word=str(word),
            target_letter="",
            answer_value=str(answer_label),
            answer_support=tuple(OPTION_LABELS[: int(option_count)]),
            option_specs=tuple(options),
            word_bank=tuple(),
            present_words=tuple(),
            placements=(placement,),
            target_cells=tuple(placement.cells),
        )
    raise RuntimeError("failed to build word-search location dataset")


def sample_letter_count_dataset(
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    rng,
    scene_variant: str,
    scene_variant_probabilities: Mapping[str, float],
    target_count: int,
) -> WordSearchDataset:
    """Build a target-letter counting dataset with exact support cells."""

    rows, cols, size_range = resolve_grid_size(params, generation_defaults, rng)
    target_letter = str(uniform_choice(rng, tuple(ascii_uppercase)))
    all_cells = [(row, col) for row in range(rows) for col in range(cols)]
    rng.shuffle(all_cells)
    target_cells = tuple(
        (int(row), int(col)) for row, col in all_cells[: int(target_count)]
    )
    grid = [["" for _ in range(cols)] for _ in range(rows)]
    for row, col in target_cells:
        grid[int(row)][int(col)] = target_letter
    fill_random_letters(grid, rng, excluded_letters={target_letter})
    return WordSearchDataset(
        rows=int(rows),
        cols=int(cols),
        grid_size_range=tuple(size_range),
        grid=tuple(tuple(str(value) for value in row) for row in grid),
        scene_variant=str(scene_variant),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        target_word="",
        target_letter=str(target_letter),
        answer_value=int(target_count),
        answer_support=tuple(
            range(1, int(generation_defaults.get("target_count_max", 8)) + 1)
        ),
        option_specs=tuple(),
        word_bank=tuple(),
        present_words=tuple(),
        placements=tuple(),
        target_cells=tuple(target_cells),
    )


def sample_present_word_count_dataset(
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    rng,
    scene_variant: str,
    scene_variant_probabilities: Mapping[str, float],
    present_count: int,
    bank_size: int,
) -> WordSearchDataset:
    """Build a word-bank dataset with exactly `present_count` placed words."""

    rows, cols, size_range = resolve_grid_size(params, generation_defaults, rng)
    word_min, word_max = get_int_range(
        params,
        generation_defaults,
        min_key="word_length_min",
        max_key="word_length_max",
        fallback_min=3,
        fallback_max=4,
    )
    for _attempt in range(400):
        word_bank = choose_words(
            rng,
            count=int(bank_size),
            min_len=int(word_min),
            max_len=int(word_max),
        )
        present_words = tuple(str(word) for word in word_bank[: int(present_count)])
        absent_words = tuple(str(word) for word in word_bank[int(present_count) :])
        grid = [["" for _ in range(cols)] for _ in range(rows)]
        placements: list[WordPlacement] = []
        try:
            for word in present_words:
                placements.append(place_word(grid, str(word), rng))
        except RuntimeError:
            continue
        fill_random_letters(grid, rng)
        if any(scan_word(grid, str(word)) for word in absent_words):
            continue
        exact_placements: list[WordPlacement] = []
        for word in present_words:
            hits = scan_word(grid, str(word))
            if len(hits) != 1:
                break
            exact_placements.append(hits[0])
        if len(exact_placements) != int(present_count):
            continue
        target_cells = tuple(
            cell for placement in exact_placements for cell in placement.cells
        )
        return WordSearchDataset(
            rows=int(rows),
            cols=int(cols),
            grid_size_range=tuple(size_range),
            grid=tuple(tuple(str(value) for value in row) for row in grid),
            scene_variant=str(scene_variant),
            scene_variant_probabilities=dict(scene_variant_probabilities),
            target_word="",
            target_letter="",
            answer_value=int(present_count),
            answer_support=tuple(range(1, int(bank_size) + 1)),
            option_specs=tuple(),
            word_bank=tuple(str(word) for word in word_bank),
            present_words=tuple(present_words),
            placements=tuple(exact_placements),
            target_cells=tuple(target_cells),
        )
    raise RuntimeError("failed to build present-word-count dataset")


def cell_ids_for_target_cells(dataset: WordSearchDataset) -> tuple[str, ...]:
    """Return ordered render ids for the dataset's target cells."""

    return tuple(cell_key(cell) for cell in dataset.target_cells)


def word_chip_ids_for_present_words(dataset: WordSearchDataset) -> tuple[str, ...]:
    """Return word-chip ids for words that are present in the grid."""

    return tuple(word_chip_key(word) for word in dataset.present_words)


def present_word_segments(dataset: WordSearchDataset) -> tuple[tuple[Cell, Cell], ...]:
    """Return start/end cells for each present word placement."""

    segments: list[tuple[Cell, Cell]] = []
    for placement in dataset.placements:
        if not placement.cells:
            continue
        segments.append((placement.cells[0], placement.cells[-1]))
    return tuple(segments)


def _build_location_options(
    *,
    placement: WordPlacement,
    rows: int,
    cols: int,
    option_count: int,
    answer_label: str,
    rng,
) -> tuple[WordSearchOption, ...]:
    """Create one correct placement option plus unique distractors."""

    labels = tuple(OPTION_LABELS[: int(option_count)])
    if str(answer_label) not in labels:
        raise ValueError("answer_label must be one of the visible option labels")
    correct = (int(placement.row) + 1, int(placement.col) + 1, str(placement.direction))
    distractors: list[tuple[int, int, str]] = []
    for direction, _dr, _dc in WORD_DIRECTIONS:
        candidate = (correct[0], correct[1], str(direction))
        if candidate != correct and candidate not in distractors:
            distractors.append(candidate)
    for delta_r, delta_c in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)):
        row = max(1, min(int(rows), correct[0] + int(delta_r)))
        col = max(1, min(int(cols), correct[1] + int(delta_c)))
        candidate = (int(row), int(col), correct[2])
        if candidate != correct and candidate not in distractors:
            distractors.append(candidate)
    for row in range(1, int(rows) + 1):
        for col in range(1, int(cols) + 1):
            for direction, _dr, _dc in WORD_DIRECTIONS:
                candidate = (int(row), int(col), str(direction))
                if candidate != correct and candidate not in distractors:
                    distractors.append(candidate)
                if len(distractors) >= int(option_count) * 4:
                    break
            if len(distractors) >= int(option_count) * 4:
                break
        if len(distractors) >= int(option_count) * 4:
            break
    rng.shuffle(distractors)
    specs: list[WordSearchOption] = []
    distractor_index = 0
    for label in labels:
        if str(label) == str(answer_label):
            row, col, direction = correct
            specs.append(
                WordSearchOption(
                    label=str(label),
                    row_1based=int(row),
                    col_1based=int(col),
                    direction=str(direction),
                    is_correct=True,
                )
            )
        else:
            row, col, direction = distractors[distractor_index]
            distractor_index += 1
            specs.append(
                WordSearchOption(
                    label=str(label),
                    row_1based=int(row),
                    col_1based=int(col),
                    direction=str(direction),
                    is_correct=False,
                )
            )
    return tuple(specs)


def option_text(spec: WordSearchOption) -> str:
    """Return prompt-facing text for one word-location option card."""

    return (
        f"{spec.label}: row {int(spec.row_1based)}, "
        f"col {int(spec.col_1based)}, {direction_code(spec.direction)}"
    )


__all__ = [
    "cell_ids_for_target_cells",
    "option_text",
    "present_word_segments",
    "resolve_scene_variant",
    "sample_letter_count_dataset",
    "sample_location_dataset",
    "sample_present_word_count_dataset",
    "word_chip_ids_for_present_words",
]
