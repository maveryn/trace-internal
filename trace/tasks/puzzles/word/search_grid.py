"""Word-search grid puzzle tasks."""

from __future__ import annotations

from dataclasses import dataclass, replace
from string import ascii_uppercase
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import round_bbox as _round_bbox
from ...shared.color_distance import coerce_rgb as _rgb
from ...shared.config_defaults import required_group_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font
from ...shared.text_legibility import draw_text_traced
from ..shared.common import (
    get_int_param as _get_int,
    get_int_range as _get_range,
    load_puzzle_task_defaults,
    projected_puzzle_bbox_annotation,
    resolve_puzzle_axis_variant,
)
from ..shared.complexity import build_puzzle_complexity, normalize_int_with_bounds
from ..shared.drawing import draw_centered_text, draw_rounded_rect
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.unit_size_jitter import resolve_puzzle_unit_size_scale, scale_puzzle_px, with_puzzle_unit_size_jitter
from ..shared.visual_defaults import load_puzzle_noise_defaults


SCENE_ID = "word_search"
LOCATION_TASK_ID = "task_puzzles__word_search__search_location_label"
LETTER_COUNT_TASK_ID = "task_puzzles__word_search__search_letter_count_value"
PRESENT_WORD_COUNT_TASK_ID = "task_puzzles__word_search__search_present_word_count"

LOCATION_QUERY_ID = "word_location_label"
LETTER_COUNT_QUERY_ID = "letter_count_value"
PRESENT_WORD_COUNT_QUERY_ID = "present_word_count"

SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "word_search_classic",
    "word_search_notebook",
    "word_search_card",
)
SUPPORTED_DIRECTIONS: Tuple[Tuple[str, int, int], ...] = (
    ("right", 0, 1),
    ("down", 1, 0),
    ("diagonal-right-down", 1, 1),
    ("diagonal-right-up", -1, 1),
    ("left", 0, -1),
    ("up", -1, 0),
    ("diagonal-left-down", 1, -1),
    ("diagonal-left-up", -1, -1),
)
_DIRECTION_CODES: Dict[str, str] = {
    "right": "R",
    "left": "L",
    "up": "U",
    "down": "D",
    "diagonal-right-down": "DR",
    "diagonal-right-up": "UR",
    "diagonal-left-down": "DL",
    "diagonal-left-up": "UL",
}
_DIRECTION_LEGEND_LINES: Tuple[str, ...] = (
    "Codes: R=right, L=left, U=up, D=down",
    "DR=down-right, UR=up-right",
    "DL=down-left, UL=up-left",
)

_SCENE_LOAD_BY_VARIANT = {
    "word_search_classic": 0.18,
    "word_search_notebook": 0.24,
    "word_search_card": 0.22,
}
_WORD_POOL: Tuple[str, ...] = (
    "ABLE",
    "ACID",
    "AGED",
    "ALOE",
    "ARCH",
    "BARK",
    "BEAM",
    "BIRD",
    "BOLT",
    "CANE",
    "CAVE",
    "COLD",
    "COVE",
    "DART",
    "DIAL",
    "DUNE",
    "ECHO",
    "FERN",
    "FISH",
    "FORK",
    "GATE",
    "GLOW",
    "GOLD",
    "HARP",
    "HAZE",
    "HILL",
    "IRON",
    "IVY",
    "JADE",
    "KITE",
    "LACE",
    "LAKE",
    "LAMP",
    "LEAF",
    "LIME",
    "MARS",
    "MINT",
    "MOON",
    "NEST",
    "NODE",
    "NOVA",
    "OPAL",
    "ORCA",
    "PALM",
    "PEAR",
    "PINE",
    "POND",
    "RING",
    "ROCK",
    "ROOT",
    "SAGE",
    "SAND",
    "SEED",
    "SHIP",
    "SILK",
    "SNOW",
    "STAR",
    "TIDE",
    "TREE",
    "VALE",
    "VINE",
    "WAVE",
    "WIND",
    "WOLF",
    "YARN",
    "ZINC",
)

Cell = Tuple[int, int]
BBox = List[float]

_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "word")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="word", apply_prob=0.25)


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    cell_size_px: int
    header_size_px: int
    panel_padding_px: int
    panel_corner_radius_px: int
    grid_line_width_px: int
    grid_origin_x_px: int
    grid_origin_y_px: int
    option_panel_width_px: int
    option_panel_height_px: int
    option_gap_px: int
    option_font_size_px: int
    word_chip_height_px: int
    word_chip_gap_px: int
    letter_font_size_px: int
    index_font_size_px: int
    title_font_size_px: int
    panel_fill_rgb: Tuple[int, int, int]
    grid_fill_rgb: Tuple[int, int, int]
    header_fill_rgb: Tuple[int, int, int]
    grid_line_rgb: Tuple[int, int, int]
    text_rgb: Tuple[int, int, int]
    text_stroke_rgb: Tuple[int, int, int]
    option_fill_rgb: Tuple[int, int, int]
    option_border_rgb: Tuple[int, int, int]
    chip_fill_rgb: Tuple[int, int, int]
    chip_border_rgb: Tuple[int, int, int]
    highlight_rgb: Tuple[int, int, int]
    unit_size_jitter: Dict[str, Any]


@dataclass(frozen=True)
class _OptionSpec:
    label: str
    row_1based: int
    col_1based: int
    direction: str
    is_correct: bool


@dataclass(frozen=True)
class _WordPlacement:
    word: str
    row: int
    col: int
    direction: str
    dr: int
    dc: int
    cells: Tuple[Cell, ...]


@dataclass(frozen=True)
class _Dataset:
    task_id: str
    query_id: str
    rows: int
    cols: int
    grid_size_range: Tuple[int, int]
    grid: Tuple[Tuple[str, ...], ...]
    target_word: str
    target_letter: str
    answer_value: int | str
    answer_type: str
    option_specs: Tuple[_OptionSpec, ...]
    word_bank: Tuple[str, ...]
    present_words: Tuple[str, ...]
    placements: Tuple[_WordPlacement, ...]
    supporting_item_ids: Tuple[str, ...]
    target_answer_support: Tuple[int | str, ...]
    scene_variant: str


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    scene_bbox_px: BBox
    item_bbox_map: Dict[str, BBox]
    cell_bbox_map: Dict[str, BBox]
    layout_jitter: Dict[str, Any]


def _layout_footprint(dataset: _Dataset, render_params: _RenderParams) -> Dict[str, int]:
    """Return deterministic content dimensions before canvas placement."""

    rows = int(dataset.rows)
    cols = int(dataset.cols)
    cell = int(render_params.cell_size_px)
    header = int(render_params.header_size_px)
    grid_w = int(header + (cols * cell))
    grid_h = int(header + (rows * cell))
    padding = int(render_params.panel_padding_px)
    title_band_px = 44
    canvas_margin_px = 34
    side_gap_px = max(24, int(round(46 * float(render_params.unit_size_jitter.get("scale", 1.0)))))
    has_side_panel = dataset.task_id in {LOCATION_TASK_ID, PRESENT_WORD_COUNT_TASK_ID}
    side_panel_width = int(render_params.option_panel_width_px) if has_side_panel else 0
    content_width = int(grid_w + (side_gap_px + side_panel_width if has_side_panel else 0))
    content_height = int(grid_h)
    if dataset.task_id == LOCATION_TASK_ID:
        options_bottom = int(
            6
            + (len(dataset.option_specs) * int(render_params.option_panel_height_px))
            + (max(0, len(dataset.option_specs) - 1) * int(render_params.option_gap_px))
        )
        legend_bottom = int(max(grid_h + 16, options_bottom + 2) + 72)
        content_height = int(max(content_height, legend_bottom))
    if dataset.task_id == PRESENT_WORD_COUNT_TASK_ID:
        word_bank_bottom = int(
            header
            + (len(dataset.word_bank) * (int(render_params.word_chip_height_px) + int(render_params.word_chip_gap_px)))
            + 24
        )
        content_height = int(max(content_height, word_bank_bottom))
    panel_width = int(content_width + (2 * padding))
    panel_height = int(content_height + (2 * padding) + title_band_px)
    return {
        "grid_w": int(grid_w),
        "grid_h": int(grid_h),
        "padding": int(padding),
        "title_band_px": int(title_band_px),
        "canvas_margin_px": int(canvas_margin_px),
        "side_gap_px": int(side_gap_px),
        "has_side_panel": int(has_side_panel),
        "content_width": int(content_width),
        "content_height": int(content_height),
        "panel_width": int(panel_width),
        "panel_height": int(panel_height),
    }


def _cell_key(cell: Cell) -> str:
    return f"cell_{int(cell[0])}_{int(cell[1])}"


def _option_key(label: str) -> str:
    return f"option_{str(label)}"


def _word_chip_key(word: str) -> str:
    return f"word_chip_{str(word)}"


def _load_defaults(task_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    return load_puzzle_task_defaults(_TASK_GROUP_DEFAULTS, task_id=str(task_id))


def _resolve_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _resolve_grid_size(params: Mapping[str, Any], gen_defaults: Mapping[str, Any], *, instance_seed: int, task_id: str) -> Tuple[int, int, Tuple[int, int]]:
    size_min, size_max = _get_range(
        params,
        gen_defaults,
        min_key="grid_size_min",
        max_key="grid_size_max",
        fallback_min=7,
        fallback_max=9,
    )
    explicit_size = params.get("grid_size")
    if explicit_size is not None:
        size = int(explicit_size)
    else:
        selection = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.grid_size"))
        size = int(size_min + (selection % (size_max - size_min + 1)))
    if not int(size_min) <= int(size) <= int(size_max):
        raise ValueError("grid_size outside configured range")
    return int(size), int(size), (int(size_min), int(size_max))


def _resolve_render_params(
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    *,
    instance_seed: int,
) -> _RenderParams:
    unit_scale, unit_meta = resolve_puzzle_unit_size_scale(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace="puzzles.word_search.unit_size",
    )
    return _RenderParams(
        canvas_width=int(render_defaults.get("canvas_width", 1180)),
        canvas_height=int(render_defaults.get("canvas_height", 880)),
        cell_size_px=scale_puzzle_px(render_defaults.get("cell_size_px", 58), unit_scale, min_px=22),
        header_size_px=scale_puzzle_px(render_defaults.get("header_size_px", 46), unit_scale, min_px=20),
        panel_padding_px=scale_puzzle_px(render_defaults.get("panel_padding_px", 28), unit_scale, min_px=12),
        panel_corner_radius_px=scale_puzzle_px(render_defaults.get("panel_corner_radius_px", 18), unit_scale, min_px=7),
        grid_line_width_px=scale_puzzle_px(render_defaults.get("grid_line_width_px", 2), unit_scale, min_px=1),
        grid_origin_x_px=int(render_defaults.get("grid_origin_x_px", 90)),
        grid_origin_y_px=int(render_defaults.get("grid_origin_y_px", 150)),
        option_panel_width_px=int(render_defaults.get("option_panel_width_px", 270)),
        option_panel_height_px=scale_puzzle_px(render_defaults.get("option_panel_height_px", 58), unit_scale, min_px=34),
        option_gap_px=scale_puzzle_px(render_defaults.get("option_gap_px", 12), unit_scale, min_px=6),
        option_font_size_px=scale_puzzle_px(render_defaults.get("option_font_size_px", 20), unit_scale, min_px=12),
        word_chip_height_px=scale_puzzle_px(render_defaults.get("word_chip_height_px", 44), unit_scale, min_px=24),
        word_chip_gap_px=scale_puzzle_px(render_defaults.get("word_chip_gap_px", 10), unit_scale, min_px=5),
        letter_font_size_px=scale_puzzle_px(render_defaults.get("letter_font_size_px", 24), unit_scale, min_px=12),
        index_font_size_px=scale_puzzle_px(render_defaults.get("index_font_size_px", 17), unit_scale, min_px=10),
        title_font_size_px=int(render_defaults.get("title_font_size_px", 24)),
        panel_fill_rgb=_rgb(render_defaults.get("panel_fill_rgb"), (250, 251, 253)),
        grid_fill_rgb=_rgb(render_defaults.get("grid_fill_rgb"), (255, 255, 255)),
        header_fill_rgb=_rgb(render_defaults.get("header_fill_rgb"), (239, 243, 248)),
        grid_line_rgb=_rgb(render_defaults.get("grid_line_rgb"), (93, 102, 116)),
        text_rgb=_rgb(render_defaults.get("text_rgb"), (26, 31, 39)),
        text_stroke_rgb=_rgb(render_defaults.get("text_stroke_rgb"), (255, 255, 255)),
        option_fill_rgb=_rgb(render_defaults.get("option_fill_rgb"), (255, 250, 224)),
        option_border_rgb=_rgb(render_defaults.get("option_border_rgb"), (54, 96, 168)),
        chip_fill_rgb=_rgb(render_defaults.get("chip_fill_rgb"), (234, 245, 239)),
        chip_border_rgb=_rgb(render_defaults.get("chip_border_rgb"), (68, 122, 103)),
        highlight_rgb=_rgb(render_defaults.get("highlight_rgb"), (255, 241, 142)),
        unit_size_jitter=dict(unit_meta),
    )


def _resize_canvas_to_word_search_content(
    render_params: _RenderParams,
    *,
    dataset: _Dataset,
    instance_seed: int,
) -> _RenderParams:
    """Shrink the fixed canvas to the resolved word-search footprint plus bounded slack."""

    footprint = _layout_footprint(dataset, render_params)
    margin = int(footprint["canvas_margin_px"])
    panel_width = int(footprint["panel_width"])
    panel_height = int(footprint["panel_height"])
    rng = spawn_rng(int(instance_seed), f"{dataset.task_id}.word_search.canvas")
    max_slack_x = min(160, max(48, int(round(0.22 * float(panel_width)))))
    max_slack_y = min(120, max(36, int(round(0.18 * float(panel_height)))))
    slack_x = int(rng.randrange(24, max_slack_x + 1))
    slack_y = int(rng.randrange(18, max_slack_y + 1))
    min_width = 640 if bool(footprint["has_side_panel"]) else 420
    min_height = 420 if bool(footprint["has_side_panel"]) else 320
    canvas_width = max(
        int(min_width),
        min(
            int(render_params.canvas_width),
            int(panel_width + (2 * margin) + slack_x),
        ),
    )
    canvas_height = max(
        int(min_height),
        min(
            int(render_params.canvas_height),
            int(panel_height + (2 * margin) + slack_y),
        ),
    )
    return replace(
        render_params,
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
    )


def _direction_by_name(name: str) -> Tuple[int, int]:
    for direction, dr, dc in SUPPORTED_DIRECTIONS:
        if str(direction) == str(name):
            return int(dr), int(dc)
    raise KeyError(name)


def _direction_code(name: str) -> str:
    """Return the compact move code displayed in answer options."""

    return str(_DIRECTION_CODES[str(name)])


def _cells_for_word(row: int, col: int, dr: int, dc: int, length: int) -> Tuple[Cell, ...]:
    return tuple((int(row) + (idx * int(dr)), int(col) + (idx * int(dc))) for idx in range(int(length)))


def _fits(rows: int, cols: int, cells: Sequence[Cell]) -> bool:
    return all(0 <= int(row) < int(rows) and 0 <= int(col) < int(cols) for row, col in cells)


def _can_place(grid: Sequence[Sequence[str]], word: str, cells: Sequence[Cell]) -> bool:
    for char, (row, col) in zip(str(word), cells):
        existing = str(grid[int(row)][int(col)])
        if existing and existing != str(char):
            return False
    return True


def _place_word(grid: List[List[str]], word: str, *, rng) -> _WordPlacement:
    rows = len(grid)
    cols = len(grid[0])
    candidates: List[Tuple[str, int, int, Tuple[Cell, ...]]] = []
    for direction, dr, dc in SUPPORTED_DIRECTIONS:
        for row in range(rows):
            for col in range(cols):
                cells = _cells_for_word(row, col, int(dr), int(dc), len(word))
                if _fits(rows, cols, cells) and _can_place(grid, str(word), cells):
                    candidates.append((str(direction), int(row), int(col), cells))
    if not candidates:
        raise RuntimeError(f"could not place word {word}")
    direction, row, col, cells = candidates[int(rng.randrange(len(candidates)))]
    for char, (rr, cc) in zip(str(word), cells):
        grid[int(rr)][int(cc)] = str(char)
    dr, dc = _direction_by_name(str(direction))
    return _WordPlacement(word=str(word), row=int(row), col=int(col), direction=str(direction), dr=int(dr), dc=int(dc), cells=tuple(cells))


def _fill_random(grid: List[List[str]], *, rng, excluded_letters: Iterable[str] = ()) -> None:
    excluded = {str(letter) for letter in excluded_letters}
    letters = [letter for letter in ascii_uppercase if letter not in excluded]
    if not letters:
        letters = list(ascii_uppercase)
    for row in range(len(grid)):
        for col in range(len(grid[0])):
            if not grid[row][col]:
                grid[row][col] = str(letters[int(rng.randrange(len(letters)))])


def _scan_word(grid: Sequence[Sequence[str]], word: str) -> List[_WordPlacement]:
    rows = len(grid)
    cols = len(grid[0])
    hits: List[_WordPlacement] = []
    for direction, dr, dc in SUPPORTED_DIRECTIONS:
        for row in range(rows):
            for col in range(cols):
                cells = _cells_for_word(row, col, int(dr), int(dc), len(word))
                if not _fits(rows, cols, cells):
                    continue
                letters = "".join(str(grid[rr][cc]) for rr, cc in cells)
                if letters == str(word):
                    hits.append(_WordPlacement(word=str(word), row=int(row), col=int(col), direction=str(direction), dr=int(dr), dc=int(dc), cells=tuple(cells)))
    return hits


def _choose_words(rng, *, count: int, min_len: int, max_len: int) -> List[str]:
    pool = [word for word in _WORD_POOL if int(min_len) <= len(word) <= int(max_len)]
    if len(pool) < int(count):
        raise RuntimeError("word pool too small")
    rng.shuffle(pool)
    return [str(word) for word in pool[: int(count)]]


def _build_location_options(
    *,
    placement: _WordPlacement,
    rows: int,
    cols: int,
    option_count: int,
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    rng,
) -> Tuple[_OptionSpec, ...]:
    labels = list(ascii_uppercase[: int(option_count)])
    correct = (int(placement.row) + 1, int(placement.col) + 1, str(placement.direction))
    distractors: List[Tuple[int, int, str]] = []
    for direction, _dr, _dc in SUPPORTED_DIRECTIONS:
        item = (correct[0], correct[1], str(direction))
        if item != correct and item not in distractors:
            distractors.append(item)
    for delta_r, delta_c in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)):
        rr = max(1, min(int(rows), correct[0] + int(delta_r)))
        cc = max(1, min(int(cols), correct[1] + int(delta_c)))
        item = (int(rr), int(cc), correct[2])
        if item != correct and item not in distractors:
            distractors.append(item)
    for row in range(1, int(rows) + 1):
        for col in range(1, int(cols) + 1):
            for direction, _dr, _dc in SUPPORTED_DIRECTIONS:
                item = (int(row), int(col), str(direction))
                if item != correct and item not in distractors:
                    distractors.append(item)
                if len(distractors) >= int(option_count) * 4:
                    break
            if len(distractors) >= int(option_count) * 4:
                break
        if len(distractors) >= int(option_count) * 4:
            break
    rng.shuffle(distractors)
    selection = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}.answer_label"))
    correct_index = int(selection % int(option_count))
    specs: List[_OptionSpec] = []
    cursor = 0
    for index in range(int(option_count)):
        if index == correct_index:
            rr, cc, direction = correct
            specs.append(_OptionSpec(label=str(labels[index]), row_1based=int(rr), col_1based=int(cc), direction=str(direction), is_correct=True))
        else:
            rr, cc, direction = distractors[cursor]
            cursor += 1
            specs.append(_OptionSpec(label=str(labels[index]), row_1based=int(rr), col_1based=int(cc), direction=str(direction), is_correct=False))
    return tuple(specs)


def _build_location_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    scene_variant: str,
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{LOCATION_TASK_ID}.dataset")
    rows, cols, size_range = _resolve_grid_size(params, gen_defaults, instance_seed=int(instance_seed), task_id=LOCATION_TASK_ID)
    word_min, word_max = _get_range(params, gen_defaults, min_key="word_length_min", max_key="word_length_max", fallback_min=3, fallback_max=4)
    option_min, option_max = _get_range(params, gen_defaults, min_key="option_count_min", max_key="option_count_max", fallback_min=6, fallback_max=8)
    option_count = int(params.get("option_count", rng.randint(int(option_min), int(option_max))))
    option_count = max(5, min(8, int(option_count)))
    for _attempt in range(200):
        word = _choose_words(rng, count=1, min_len=int(word_min), max_len=int(word_max))[0]
        grid = [["" for _ in range(cols)] for _ in range(rows)]
        placement = _place_word(grid, word, rng=rng)
        _fill_random(grid, rng=rng)
        hits = _scan_word(grid, word)
        if len(hits) != 1:
            continue
        placement = hits[0]
        option_specs = _build_location_options(
            placement=placement,
            rows=int(rows),
            cols=int(cols),
            option_count=int(option_count),
            params=params,
            instance_seed=int(instance_seed),
            task_id=LOCATION_TASK_ID,
            rng=rng,
        )
        answer = next(spec.label for spec in option_specs if spec.is_correct)
        return _Dataset(
            task_id=LOCATION_TASK_ID,
            query_id=LOCATION_QUERY_ID,
            rows=int(rows),
            cols=int(cols),
            grid_size_range=tuple(size_range),
            grid=tuple(tuple(str(value) for value in row) for row in grid),
            target_word=str(word),
            target_letter="",
            answer_value=str(answer),
            answer_type="option_letter",
            option_specs=tuple(option_specs),
            word_bank=tuple(),
            present_words=tuple(),
            placements=(placement,),
            supporting_item_ids=tuple([_option_key(str(answer)), *[_cell_key(cell) for cell in placement.cells]]),
            target_answer_support=tuple(ascii_uppercase[: int(option_count)]),
            scene_variant=str(scene_variant),
        )
    raise RuntimeError("failed to build word-search location dataset")


def _build_letter_count_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    scene_variant: str,
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{LETTER_COUNT_TASK_ID}.dataset")
    rows, cols, size_range = _resolve_grid_size(params, gen_defaults, instance_seed=int(instance_seed), task_id=LETTER_COUNT_TASK_ID)
    count_min, count_max = _get_range(params, gen_defaults, min_key="target_count_min", max_key="target_count_max", fallback_min=1, fallback_max=10)
    support = tuple(range(int(count_min), int(count_max) + 1))
    selection = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{LETTER_COUNT_TASK_ID}.answer_count"))
    target_count = int(support[int(selection % len(support))])
    target_letter = str(ascii_uppercase[int(rng.randrange(len(ascii_uppercase)))])
    cells = [(row, col) for row in range(rows) for col in range(cols)]
    rng.shuffle(cells)
    target_cells = tuple(cells[: int(target_count)])
    grid = [["" for _ in range(cols)] for _ in range(rows)]
    for row, col in target_cells:
        grid[int(row)][int(col)] = str(target_letter)
    _fill_random(grid, rng=rng, excluded_letters={target_letter})
    return _Dataset(
        task_id=LETTER_COUNT_TASK_ID,
        query_id=LETTER_COUNT_QUERY_ID,
        rows=int(rows),
        cols=int(cols),
        grid_size_range=tuple(size_range),
        grid=tuple(tuple(str(value) for value in row) for row in grid),
        target_word="",
        target_letter=str(target_letter),
        answer_value=int(target_count),
        answer_type="integer",
        option_specs=tuple(),
        word_bank=tuple(),
        present_words=tuple(),
        placements=tuple(),
        supporting_item_ids=tuple(_cell_key(cell) for cell in target_cells),
        target_answer_support=tuple(int(value) for value in support),
        scene_variant=str(scene_variant),
    )


def _build_present_word_count_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    scene_variant: str,
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{PRESENT_WORD_COUNT_TASK_ID}.dataset")
    rows, cols, size_range = _resolve_grid_size(params, gen_defaults, instance_seed=int(instance_seed), task_id=PRESENT_WORD_COUNT_TASK_ID)
    word_min, word_max = _get_range(params, gen_defaults, min_key="word_length_min", max_key="word_length_max", fallback_min=3, fallback_max=4)
    bank_size = _get_int(params, gen_defaults, "word_bank_size", 5)
    count_min, count_max = _get_range(params, gen_defaults, min_key="present_count_min", max_key="present_count_max", fallback_min=1, fallback_max=5)
    support = tuple(range(int(count_min), min(int(count_max), int(bank_size)) + 1))
    fixed_present_count = params.get("_fixed_present_count")
    if fixed_present_count is not None:
        target_count = int(fixed_present_count)
    else:
        selection = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{PRESENT_WORD_COUNT_TASK_ID}.answer_count"))
        target_count = int(support[int(selection % len(support))])
    if target_count not in support:
        selection = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{PRESENT_WORD_COUNT_TASK_ID}.answer_count"))
        target_count = int(support[int(selection % len(support))])
    for _attempt in range(300):
        word_bank = _choose_words(rng, count=int(bank_size), min_len=int(word_min), max_len=int(word_max))
        present_words = tuple(word_bank[: int(target_count)])
        absent_words = tuple(word_bank[int(target_count) :])
        grid = [["" for _ in range(cols)] for _ in range(rows)]
        placements: List[_WordPlacement] = []
        try:
            for word in present_words:
                placements.append(_place_word(grid, str(word), rng=rng))
        except RuntimeError:
            continue
        _fill_random(grid, rng=rng)
        if any(_scan_word(grid, str(word)) for word in absent_words):
            continue
        exact_placements: List[_WordPlacement] = []
        ok = True
        for word in present_words:
            hits = _scan_word(grid, str(word))
            if len(hits) != 1:
                ok = False
                break
            exact_placements.append(hits[0])
        if not ok:
            continue
        supporting_ids: List[str] = []
        for word in present_words:
            supporting_ids.append(_word_chip_key(str(word)))
        for placement in exact_placements:
            supporting_ids.extend(_cell_key(cell) for cell in placement.cells)
        return _Dataset(
            task_id=PRESENT_WORD_COUNT_TASK_ID,
            query_id=PRESENT_WORD_COUNT_QUERY_ID,
            rows=int(rows),
            cols=int(cols),
            grid_size_range=tuple(size_range),
            grid=tuple(tuple(str(value) for value in row) for row in grid),
            target_word="",
            target_letter="",
            answer_value=int(target_count),
            answer_type="integer",
            option_specs=tuple(),
            word_bank=tuple(str(word) for word in word_bank),
            present_words=tuple(str(word) for word in present_words),
            placements=tuple(exact_placements),
            supporting_item_ids=tuple(supporting_ids),
            target_answer_support=tuple(int(value) for value in support),
            scene_variant=str(scene_variant),
        )
    raise RuntimeError("failed to build present-word count dataset")


def _render_scene(
    image: Image.Image,
    *,
    dataset: _Dataset,
    render_params: _RenderParams,
    instance_seed: int,
) -> _RenderedScene:
    draw = ImageDraw.Draw(image)
    rows = int(dataset.rows)
    cols = int(dataset.cols)
    cell = int(render_params.cell_size_px)
    header = int(render_params.header_size_px)
    footprint = _layout_footprint(dataset, render_params)
    grid_w = int(footprint["grid_w"])
    grid_h = int(footprint["grid_h"])
    padding = int(footprint["padding"])
    title_band_px = int(footprint["title_band_px"])
    canvas_margin_px = int(footprint["canvas_margin_px"])
    side_gap_px = int(footprint["side_gap_px"])
    content_width = int(footprint["content_width"])
    content_height = int(footprint["content_height"])
    panel_width = int(footprint["panel_width"])
    panel_height = int(footprint["panel_height"])
    max_panel_x0 = max(canvas_margin_px, int(render_params.canvas_width) - canvas_margin_px - panel_width)
    max_panel_y0 = max(canvas_margin_px, int(render_params.canvas_height) - canvas_margin_px - panel_height)
    rng = spawn_rng(int(instance_seed), f"{dataset.task_id}.word_search.layout")
    if max_panel_x0 > canvas_margin_px:
        panel_x0 = int(canvas_margin_px + rng.randrange(max_panel_x0 - canvas_margin_px + 1))
    else:
        panel_x0 = int(canvas_margin_px)
    if max_panel_y0 > canvas_margin_px:
        panel_y0 = int(canvas_margin_px + rng.randrange(max_panel_y0 - canvas_margin_px + 1))
    else:
        panel_y0 = int(canvas_margin_px)
    panel_x1 = int(min(int(render_params.canvas_width) - canvas_margin_px, panel_x0 + panel_width))
    panel_y1 = int(min(int(render_params.canvas_height) - canvas_margin_px, panel_y0 + panel_height))
    grid_x0 = int(panel_x0 + padding)
    grid_y0 = int(panel_y0 + padding + title_band_px)
    right_panel_x0 = int(grid_x0 + grid_w + side_gap_px)
    layout_jitter = {
        "enabled": True,
        "panel_x0_px": int(panel_x0),
        "panel_y0_px": int(panel_y0),
        "grid_x0_px": int(grid_x0),
        "grid_y0_px": int(grid_y0),
        "side_gap_px": int(side_gap_px),
        "content_width_px": int(content_width),
        "content_height_px": int(content_height),
        "available_x0_min_px": int(canvas_margin_px),
        "available_x0_max_px": int(max_panel_x0),
        "available_y0_min_px": int(canvas_margin_px),
        "available_y0_max_px": int(max_panel_y0),
    }

    draw_rounded_rect(
        draw,
        (panel_x0, panel_y0, panel_x1, panel_y1),
        radius=int(render_params.panel_corner_radius_px),
        fill=render_params.panel_fill_rgb,
        outline=render_params.grid_line_rgb,
        width=max(1, int(render_params.grid_line_width_px)),
    )
    title_font = load_font(int(render_params.title_font_size_px), bold=True)
    letter_font = load_font(int(render_params.letter_font_size_px), bold=True)
    index_font = load_font(int(render_params.index_font_size_px), bold=True)
    option_font = load_font(int(render_params.option_font_size_px), bold=True)
    legend_font = load_font(max(12, int(render_params.index_font_size_px) - 3), bold=False)

    draw_text_traced(draw,(panel_x0 + 18, panel_y0 + 14), "Word Search", fill=render_params.text_rgb, font=title_font, role="readout", required=False)
    item_bbox_map: Dict[str, BBox] = {}
    cell_bbox_map: Dict[str, BBox] = {}
    entities: List[Dict[str, Any]] = [
        {
            "entity_id": "word_search_panel",
            "entity_type": "puzzle_word_search_panel",
            "bbox_px": _round_bbox((panel_x0, panel_y0, panel_x1, panel_y1)),
            "scene_variant": str(dataset.scene_variant),
        }
    ]
    if dataset.scene_variant == "word_search_notebook":
        for y in range(grid_y0, grid_y0 + grid_h + 1, max(12, cell // 2)):
            draw.line((panel_x0 + 6, y, panel_x1 - 6, y), fill=render_params.grid_line_rgb, width=1)

    for row in range(rows + 1):
        for col in range(cols + 1):
            x0 = grid_x0 + (col * cell if col > 0 else 0)
            y0 = grid_y0 + (row * cell if row > 0 else 0)
            if row == 0 and col == 0:
                bbox = (grid_x0, grid_y0, grid_x0 + header, grid_y0 + header)
                fill = render_params.header_fill_rgb
            elif row == 0:
                bbox = (grid_x0 + header + ((col - 1) * cell), grid_y0, grid_x0 + header + (col * cell), grid_y0 + header)
                fill = render_params.header_fill_rgb
            elif col == 0:
                bbox = (grid_x0, grid_y0 + header + ((row - 1) * cell), grid_x0 + header, grid_y0 + header + (row * cell))
                fill = render_params.header_fill_rgb
            else:
                bbox = (grid_x0 + header + ((col - 1) * cell), grid_y0 + header + ((row - 1) * cell), grid_x0 + header + (col * cell), grid_y0 + header + (row * cell))
                fill = render_params.grid_fill_rgb
            draw.rectangle(bbox, fill=fill, outline=render_params.grid_line_rgb, width=max(1, int(render_params.grid_line_width_px)))
            if row == 0 and col > 0:
                draw_centered_text(draw, text=str(col), center=((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2), font=index_font, fill=render_params.text_rgb, stroke_fill=render_params.text_stroke_rgb, stroke_width=1)
            elif col == 0 and row > 0:
                draw_centered_text(draw, text=str(row), center=((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2), font=index_font, fill=render_params.text_rgb, stroke_fill=render_params.text_stroke_rgb, stroke_width=1)
            elif row > 0 and col > 0:
                letter = str(dataset.grid[row - 1][col - 1])
                cell_id = _cell_key((row - 1, col - 1))
                cell_bbox_map[cell_id] = _round_bbox(bbox)
                item_bbox_map[cell_id] = _round_bbox(bbox)
                draw_centered_text(draw, text=letter, center=((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2), font=letter_font, fill=render_params.text_rgb, stroke_fill=render_params.text_stroke_rgb, stroke_width=1)
                entities.append({"entity_id": cell_id, "entity_type": "puzzle_word_search_cell", "bbox_px": _round_bbox(bbox), "row": row - 1, "col": col - 1, "letter": letter})

    if dataset.task_id == LOCATION_TASK_ID:
        for index, spec in enumerate(dataset.option_specs):
            x0 = right_panel_x0
            y0 = grid_y0 + 6 + (index * (int(render_params.option_panel_height_px) + int(render_params.option_gap_px)))
            bbox = (x0, y0, x0 + int(render_params.option_panel_width_px), y0 + int(render_params.option_panel_height_px))
            draw.rounded_rectangle(bbox, radius=10, fill=render_params.option_fill_rgb, outline=render_params.option_border_rgb, width=2)
            direction_code = _direction_code(str(spec.direction))
            text = f"{spec.label}: R{spec.row_1based} C{spec.col_1based} {direction_code}"
            draw_centered_text(draw, text=text, center=((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2), font=option_font, fill=render_params.text_rgb, stroke_fill=render_params.text_stroke_rgb, stroke_width=1)
            item_bbox_map[_option_key(spec.label)] = _round_bbox(bbox)
            entities.append(
                {
                    "entity_id": _option_key(spec.label),
                    "entity_type": "puzzle_word_search_option",
                    "bbox_px": _round_bbox(bbox),
                    "label": str(spec.label),
                    "row_1based": int(spec.row_1based),
                    "col_1based": int(spec.col_1based),
                    "direction": str(spec.direction),
                    "direction_code": str(direction_code),
                    "is_correct": bool(spec.is_correct),
                }
            )
        legend_y0 = max(
            grid_y0 + grid_h + 16,
            grid_y0 + 6 + (len(dataset.option_specs) * (int(render_params.option_panel_height_px) + int(render_params.option_gap_px))) + 2,
        )
        legend_bbox = (
            right_panel_x0,
            int(legend_y0),
            right_panel_x0 + int(render_params.option_panel_width_px),
            int(legend_y0) + 72,
        )
        draw.rounded_rectangle(
            legend_bbox,
            radius=8,
            fill=render_params.option_fill_rgb,
            outline=render_params.option_border_rgb,
            width=1,
        )
        for line_index, legend_line in enumerate(_DIRECTION_LEGEND_LINES):
            draw_centered_text(
                draw,
                text=str(legend_line),
                center=((legend_bbox[0] + legend_bbox[2]) / 2, legend_bbox[1] + 16 + (line_index * 18)),
                font=legend_font,
                fill=render_params.text_rgb,
                stroke_fill=render_params.text_stroke_rgb,
                stroke_width=1,
            )
        entities.append(
            {
                "entity_id": "direction_code_legend",
                "entity_type": "puzzle_word_search_direction_legend",
                "bbox_px": _round_bbox(legend_bbox),
                "legend_lines": list(_DIRECTION_LEGEND_LINES),
            }
        )
    if dataset.task_id == PRESENT_WORD_COUNT_TASK_ID:
        for index, word in enumerate(dataset.word_bank):
            x0 = right_panel_x0
            y0 = grid_y0 + 6 + (index * (int(render_params.word_chip_height_px) + int(render_params.word_chip_gap_px)))
            bbox = (x0, y0, x0 + int(render_params.option_panel_width_px), y0 + int(render_params.word_chip_height_px))
            fill = render_params.chip_fill_rgb
            outline = render_params.chip_border_rgb
            draw.rounded_rectangle(bbox, radius=10, fill=fill, outline=outline, width=2)
            draw_centered_text(draw, text=str(word), center=((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2), font=option_font, fill=render_params.text_rgb, stroke_fill=render_params.text_stroke_rgb, stroke_width=1)
            item_bbox_map[_word_chip_key(str(word))] = _round_bbox(bbox)
            entities.append({"entity_id": _word_chip_key(str(word)), "entity_type": "puzzle_word_search_word_chip", "bbox_px": _round_bbox(bbox), "word": str(word), "is_present": str(word) in set(dataset.present_words)})

    return _RenderedScene(
        image=image,
        entities=tuple(entities),
        scene_bbox_px=_round_bbox((panel_x0, panel_y0, panel_x1, panel_y1)),
        item_bbox_map=item_bbox_map,
        cell_bbox_map=cell_bbox_map,
        layout_jitter=dict(layout_jitter),
    )


def _build_prompt(
    *,
    task_id: str,
    dataset: _Dataset,
    prompt_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    query_id = str(dataset.query_id)
    scene_variant = str(dataset.scene_variant)
    required_keys = (
        "bundle_id",
        "scene_key",
        "task_key",
        "json_output_contract",
        "json_output_contract_answer_only",
        f"object_description_{scene_variant}",
        f"answer_hint_{query_id}",
        f"annotation_hint_{query_id}",
        f"json_example_{query_id}",
        f"json_example_answer_only_{query_id}",
    )
    prompt_values = required_group_defaults(prompt_defaults, required_keys, context=f"prompt defaults for {task_id}")
    slots = {
        "object_description": str(prompt_values[f"object_description_{scene_variant}"]),
        "target_word": str(dataset.target_word),
        "target_letter": str(dataset.target_letter),
        "word_bank_size": str(len(dataset.word_bank)),
        "json_output_contract": str(prompt_values["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_values["json_output_contract_answer_only"]),
        "annotation_hint": str(prompt_values[f"annotation_hint_{query_id}"]),
        "answer_hint": str(prompt_values[f"answer_hint_{query_id}"]),
        "json_example": str(prompt_values[f"json_example_{query_id}"]),
        "json_example_answer_only": str(prompt_values[f"json_example_answer_only_{query_id}"]),
    }
    prompt_selection = render_task_prompt_variants(
        domain="puzzles",
        task_group="word",
        bundle_id=str(prompt_values["bundle_id"]),
        scene_key=str(prompt_values["scene_key"]),
        task_key=str(prompt_values["task_key"]),
        query_key=str(query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots=slots,
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    return str(prompt_artifacts.prompt), dict(prompt_artifacts.prompt_variants), {
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants_for_trace": dict(prompt_artifacts.prompt_variants_for_trace),
        "bundle_id": str(prompt_values["bundle_id"]),
    }


class _PuzzlesWordSearchBaseTask:
    domain = "puzzles"
    task_group = "word"
    default_dataset_enabled = True
    task_id: str
    query_id: str

    def _build_dataset(
        self,
        *,
        params: Mapping[str, Any],
        instance_seed: int,
        gen_defaults: Mapping[str, Any],
        scene_variant: str,
    ) -> _Dataset:
        if self.task_id == LOCATION_TASK_ID:
            return _build_location_dataset(params=params, instance_seed=int(instance_seed), gen_defaults=gen_defaults, scene_variant=str(scene_variant))
        if self.task_id == LETTER_COUNT_TASK_ID:
            return _build_letter_count_dataset(params=params, instance_seed=int(instance_seed), gen_defaults=gen_defaults, scene_variant=str(scene_variant))
        if self.task_id == PRESENT_WORD_COUNT_TASK_ID:
            return _build_present_word_count_dataset(params=params, instance_seed=int(instance_seed), gen_defaults=gen_defaults, scene_variant=str(scene_variant))
        raise ValueError(f"unsupported word-search task_id: {self.task_id}")

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        gen_defaults, render_defaults, prompt_defaults, complexity_weights = _load_defaults(str(self.task_id))
        dataset_params: Dict[str, Any] = dict(params)
        if self.task_id == PRESENT_WORD_COUNT_TASK_ID and "_fixed_present_count" not in dataset_params:
            bank_size = _get_int(dataset_params, gen_defaults, "word_bank_size", 5)
            count_min, count_max = _get_range(
                dataset_params,
                gen_defaults,
                min_key="present_count_min",
                max_key="present_count_max",
                fallback_min=1,
                fallback_max=5,
            )
            support = tuple(range(int(count_min), min(int(count_max), int(bank_size)) + 1))
            sampling_index = resolve_selection_index(
                params=dataset_params,
                instance_seed=int(instance_seed),
                namespace=f"{PRESENT_WORD_COUNT_TASK_ID}.answer_count",
            )
            dataset_params["_fixed_present_count"] = int(support[int(sampling_index) % len(support)])
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
        )
        last_error: Exception | None = None
        dataset: _Dataset | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                dataset = self._build_dataset(
                    params=dataset_params,
                    instance_seed=int(instance_seed) + int(attempt_index),
                    gen_defaults=gen_defaults,
                    scene_variant=str(scene_variant),
                )
                break
            except RuntimeError as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError("failed to generate word-search puzzle instance") from last_error

        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed))
        render_params = _resize_canvas_to_word_search_content(
            render_params,
            dataset=dataset,
            instance_seed=int(instance_seed),
        )
        scene_style, scene_style_meta = resolve_puzzle_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.word_search_background",
        )
        render_params = replace(
            render_params,
            panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            grid_fill_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
            header_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            grid_line_rgb=tuple(int(value) for value in scene_style.grid_rgb),
            text_rgb=tuple(int(value) for value in scene_style.text_rgb),
            text_stroke_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
            option_fill_rgb=tuple(int(value) for value in scene_style.step_fill_rgb),
            option_border_rgb=tuple(int(value) for value in scene_style.mark_rgb),
            chip_fill_rgb=tuple(int(value) for value in scene_style.step_fill_rgb),
            chip_border_rgb=tuple(int(value) for value in scene_style.agent_rgb),
            highlight_rgb=tuple(int(value) for value in scene_style.mark_rgb),
        )
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered_scene = _render_scene(
            background,
            dataset=dataset,
            render_params=render_params,
            instance_seed=int(instance_seed),
        )
        image, post_noise_meta = apply_post_image_noise(rendered_scene.image, instance_seed=int(instance_seed), params=params, default_config=POST_IMAGE_NOISE_DEFAULTS)
        prompt, prompt_variants, prompt_meta = _build_prompt(
            task_id=str(self.task_id),
            dataset=dataset,
            prompt_defaults=prompt_defaults,
            instance_seed=int(instance_seed),
        )
        annotation_projection = projected_puzzle_bbox_annotation(rendered_scene.item_bbox_map, list(dataset.supporting_item_ids))
        annotation_bboxes = [[round(float(value), 3) for value in bbox] for bbox in annotation_projection["bbox_set"]]
        answer_gt = TypedValue(
            type=str(dataset.answer_type),
            value=int(dataset.answer_value) if str(dataset.answer_type) == "integer" else str(dataset.answer_value),
        )
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))

        placement_records = [
            {
                "word": str(placement.word),
                "start_row_1based": int(placement.row) + 1,
                "start_col_1based": int(placement.col) + 1,
                "direction": str(placement.direction),
                "cells": [[int(row), int(col)] for row, col in placement.cells],
            }
            for placement in dataset.placements
        ]
        option_records = [
            {
                "label": str(spec.label),
                "row_1based": int(spec.row_1based),
                "col_1based": int(spec.col_1based),
                "direction": str(spec.direction),
                "direction_code": _direction_code(str(spec.direction)),
                "is_correct": bool(spec.is_correct),
            }
            for spec in dataset.option_specs
        ]
        query_params = {
            "query_id": str(dataset.query_id),
            "query_id_probabilities": {str(dataset.query_id): 1.0},
            "scene_id": SCENE_ID,
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "grid_rows": int(dataset.rows),
            "grid_cols": int(dataset.cols),
            "grid_size_range": list(dataset.grid_size_range),
            "target_word": str(dataset.target_word),
            "target_letter": str(dataset.target_letter),
            "target_answer_support": list(dataset.target_answer_support),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": SCENE_ID,
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(dataset.query_id),
                    "scene_id": SCENE_ID,
                    "scene_variant": str(scene_variant),
                    "answer_value": int(dataset.answer_value) if str(dataset.answer_type) == "integer" else str(dataset.answer_value),
                },
            },
            "query_spec": {
                "query_id": str(dataset.query_id),
                "template_id": str(prompt_meta["bundle_id"]),
                "prompt_variant": dict(prompt_meta["prompt_variant"]),
                "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
                "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
                "params": dict(query_params),
            },
            "render_spec": {
                "scene_id": SCENE_ID,
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "scene_style": dict(scene_style_meta),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "unit_size_jitter": dict(render_params.unit_size_jitter),
                "layout_jitter": dict(rendered_scene.layout_jitter),
            },
            "render_map": with_puzzle_unit_size_jitter({
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "cell_bboxes_px": {str(key): list(value) for key, value in rendered_scene.cell_bbox_map.items()},
                "item_bboxes_px": {str(key): list(value) for key, value in rendered_scene.item_bbox_map.items()},
                "annotation_source": "item_bboxes_px",
                "layout_jitter": dict(rendered_scene.layout_jitter),
            }, render_params.unit_size_jitter),
            "execution_trace": {
                **dict(query_params),
                "grid": [list(row) for row in dataset.grid],
                "word_bank": list(dataset.word_bank),
                "present_words": list(dataset.present_words),
                "placements": placement_records,
                "option_specs": option_records,
                "answer_value": int(dataset.answer_value) if str(dataset.answer_type) == "integer" else str(dataset.answer_value),
                "supporting_item_ids": [str(item_id) for item_id in dataset.supporting_item_ids],
                "question_format": str(dataset.query_id),
            },
            "witness_symbolic": {"type": "bbox_set", "value": list(annotation_bboxes)},
            "projected_annotation": {"type": "bbox_set", "bbox_set": list(annotation_bboxes), "value": list(annotation_bboxes)},
            "answer_gt": answer_gt.to_dict(),
            "annotation_gt": annotation_gt.to_dict(),
        }
        visual_scan = normalize_int_with_bounds(int(dataset.rows * dataset.cols), [int(dataset.grid_size_range[0]) ** 2, int(dataset.grid_size_range[1]) ** 2])
        query_load = {
            LOCATION_QUERY_ID: 0.56,
            LETTER_COUNT_QUERY_ID: 0.42,
            PRESENT_WORD_COUNT_QUERY_ID: 0.68,
        }[str(dataset.query_id)]
        complexity = build_puzzle_complexity(
            weights=complexity_weights,
            components={
                "visual_scan": float(visual_scan),
                "reasoning_load": float(query_load),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )
        trace_payload["complexity"] = complexity.to_dict()
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(dataset.query_id),
            prompt_variants=dict(prompt_variants),
        )


@register_task
class PuzzlesWordSearchLocationLabelTask(_PuzzlesWordSearchBaseTask):
    """Find a target word and choose the option with its start and direction."""

    task_id = LOCATION_TASK_ID
    query_id = LOCATION_QUERY_ID


@register_task
class PuzzlesWordSearchLetterCountValueTask(_PuzzlesWordSearchBaseTask):
    """Count occurrences of one target letter in a word-search grid."""

    task_id = LETTER_COUNT_TASK_ID
    query_id = LETTER_COUNT_QUERY_ID


@register_task
class PuzzlesWordSearchPresentWordCountTask(_PuzzlesWordSearchBaseTask):
    """Count how many short words from a word bank appear in the grid."""

    task_id = PRESENT_WORD_COUNT_TASK_ID
    query_id = PRESENT_WORD_COUNT_QUERY_ID


__all__ = [
    "PuzzlesWordSearchLetterCountValueTask",
    "PuzzlesWordSearchLocationLabelTask",
    "PuzzlesWordSearchPresentWordCountTask",
]
