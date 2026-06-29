"""Sampling helpers for code-grid puzzle tasks."""

from __future__ import annotations

from string import ascii_uppercase
from typing import Any, Mapping, Sequence

from trace.core.sampling import (
    uniform_choice_with_probabilities,
    weighted_support_choice,
)
from trace.tasks.puzzles.shared.word_grid import (
    WORD_POOL,
    Cell,
    coordinate_token,
    fill_random_letters,
    scan_word,
)

from .defaults import get_int_range
from .state import COORDINATE_FORMATS, SCENE_VARIANTS, CodeGridDataset

_EXTRA_CODE_WORDS: tuple[str, ...] = (
    "BASIC",
    "BRIDGE",
    "CABLE",
    "CLOUD",
    "CODE",
    "FRAME",
    "LASER",
    "LEMON",
    "MARKET",
    "MATH",
    "PIXEL",
    "PLANE",
    "PUZZLE",
    "RIVER",
    "ROBOT",
    "SHAPE",
    "TRAIL",
    "VECTOR",
)
CODE_GRID_WORD_POOL: tuple[str, ...] = tuple(sorted(set(WORD_POOL + _EXTRA_CODE_WORDS)))


def resolve_scene_variant(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    rng,
) -> tuple[str, dict[str, float]]:
    """Sample or honor the visual scene variant."""

    explicit = params.get("scene_variant")
    if explicit is not None:
        selected = str(explicit)
        if selected not in SCENE_VARIANTS:
            raise ValueError(f"unsupported code-grid scene_variant: {selected}")
        return selected, {
            key: (1.0 if key == selected else 0.0) for key in SCENE_VARIANTS
        }
    weights = defaults.get("scene_variant_weights")
    if isinstance(weights, Mapping):
        return weighted_support_choice(rng, SCENE_VARIANTS, weights=weights)
    return uniform_choice_with_probabilities(rng, SCENE_VARIANTS)


def resolve_coordinate_format(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    rng,
) -> tuple[str, dict[str, float]]:
    """Sample compact/spaced coordinate formatting without changing query id."""

    explicit = params.get("coordinate_format")
    if explicit is not None:
        selected = str(explicit)
        if selected not in COORDINATE_FORMATS:
            raise ValueError(f"unsupported coordinate_format: {selected}")
        return selected, {
            key: (1.0 if key == selected else 0.0) for key in COORDINATE_FORMATS
        }
    weights = defaults.get("coordinate_format_weights")
    if isinstance(weights, Mapping):
        return weighted_support_choice(rng, COORDINATE_FORMATS, weights=weights)
    return uniform_choice_with_probabilities(rng, COORDINATE_FORMATS)


def build_code_grid_dataset(
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    rng,
) -> CodeGridDataset:
    """Construct a decode-by-coordinate instance with hidden answer cells.

    The sampler keeps the coordinate path from collapsing into an ordinary
    straight word-search line, so decoding must follow the listed coordinates.
    """

    rows, cols, size_range = _resolve_grid_size(params, generation_defaults, rng)
    word_min, word_max = get_int_range(
        params,
        generation_defaults,
        min_key="target_word_length_min",
        max_key="target_word_length_max",
        fallback_min=3,
        fallback_max=6,
    )
    scene_variant, scene_probs = resolve_scene_variant(params, generation_defaults, rng)
    coordinate_format, format_probs = resolve_coordinate_format(
        params,
        generation_defaults,
        rng,
    )

    for _attempt in range(400):
        target_word = _choose_word(rng, min_len=word_min, max_len=word_max)
        target_cells = _sample_target_cells(
            rows=int(rows),
            cols=int(cols),
            length=len(target_word),
            rng=rng,
        )
        grid = _fill_grid(
            rows=int(rows),
            cols=int(cols),
            word=str(target_word),
            target_cells=target_cells,
            rng=rng,
        )
        if scan_word(grid, str(target_word)):
            continue
        coordinate_tokens = tuple(coordinate_token(cell) for cell in target_cells)
        separator = "" if str(coordinate_format) == "compact" else " "
        return CodeGridDataset(
            rows=int(rows),
            cols=int(cols),
            grid_size_range=tuple(size_range),
            grid=grid,
            target_word=str(target_word),
            answer_value=str(target_word),
            coordinate_tokens=tuple(coordinate_tokens),
            coordinate_sequence=str(separator.join(coordinate_tokens)),
            coordinate_format=str(coordinate_format),
            target_cells=tuple(target_cells),
            scene_variant=str(scene_variant),
            answer_support=tuple(CODE_GRID_WORD_POOL),
            coordinate_format_probabilities=dict(format_probs),
            scene_variant_probabilities=dict(scene_probs),
        )
    raise RuntimeError("failed to build code-grid dataset")


def _resolve_grid_size(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    rng,
) -> tuple[int, int, tuple[int, int]]:
    """Resolve a square grid size for the generated code grid."""

    size_min, size_max = get_int_range(
        params,
        defaults,
        min_key="grid_size_min",
        max_key="grid_size_max",
        fallback_min=4,
        fallback_max=5,
    )
    explicit_size = params.get("grid_size")
    if explicit_size is None:
        size, _probabilities = weighted_support_choice(
            rng,
            tuple(range(int(size_min), int(size_max) + 1)),
        )
    else:
        size = int(explicit_size)
    if not int(size_min) <= int(size) <= int(size_max):
        raise ValueError("grid_size outside configured range")
    return int(size), int(size), (int(size_min), int(size_max))


def _choose_word(rng, *, min_len: int, max_len: int) -> str:
    """Choose an uppercase answer word within the configured length range."""

    pool = [
        word
        for word in CODE_GRID_WORD_POOL
        if int(min_len) <= len(str(word)) <= int(max_len)
    ]
    if not pool:
        raise RuntimeError("code-grid word pool is empty for configured length range")
    return str(pool[int(rng.randrange(len(pool)))])


def _is_simple_line(cells: Sequence[Cell]) -> bool:
    """Return whether the cells form a contiguous straight or diagonal line."""

    if len(cells) < 3:
        return False
    deltas = [
        (
            int(cells[index + 1][0]) - int(cells[index][0]),
            int(cells[index + 1][1]) - int(cells[index][1]),
        )
        for index in range(len(cells) - 1)
    ]
    first = deltas[0]
    if first == (0, 0):
        return False
    return all(delta == first for delta in deltas) and all(
        abs(value) <= 1 for value in first
    )


def _sample_target_cells(*, rows: int, cols: int, length: int, rng) -> tuple[Cell, ...]:
    """Sample non-contiguous cells so decoding is not ordinary word search."""

    all_cells = [(row, col) for row in range(int(rows)) for col in range(int(cols))]
    for _attempt in range(200):
        rng.shuffle(all_cells)
        cells = tuple((int(row), int(col)) for row, col in all_cells[: int(length)])
        if not _is_simple_line(cells):
            return cells
    return tuple((int(row), int(col)) for row, col in all_cells[: int(length)])


def _fill_grid(
    *,
    rows: int,
    cols: int,
    word: str,
    target_cells: Sequence[Cell],
    rng,
) -> tuple[tuple[str, ...], ...]:
    """Fill a letter grid while forcing target cells to spell the answer."""

    grid = [["" for _ in range(int(cols))] for _ in range(int(rows))]
    for char, (row, col) in zip(str(word), target_cells):
        grid[int(row)][int(col)] = str(char)
    fill_random_letters(grid, rng)
    return tuple(tuple(str(value) for value in row) for row in grid)


__all__ = [
    "CODE_GRID_WORD_POOL",
    "build_code_grid_dataset",
]
