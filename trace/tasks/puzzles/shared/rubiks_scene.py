"""Rubik-style cube-net scene construction and rendering helpers."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, MutableMapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ...shared.bbox_projection import round_bbox as _round_bbox
from ...shared.config_defaults import group_default
from ...shared.named_colors import available_named_colors, sample_named_color_palette
from ...shared.text_rendering import load_font
from .drawing import draw_centered_text, draw_rounded_rect
from .unit_size_jitter import resolve_puzzle_unit_size_scale, scale_puzzle_px


Face = str
StickerKey = Tuple[Face, int, int]
Vector3 = Tuple[int, int, int]
RGB = Tuple[int, int, int]

FACE_ORDER: Tuple[str, ...] = ("U", "D", "L", "R", "F", "B")
FACE_DISPLAY_NAMES: Mapping[str, str] = {
    "U": "Upper",
    "D": "Down",
    "L": "Left",
    "R": "Right",
    "F": "Front",
    "B": "Back",
}
MOVE_FACES: Tuple[str, ...] = ("U", "D", "L", "R", "F", "B")
OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G", "H")

SUPPORTED_RUBIKS_SCENE_VARIANTS: Tuple[str, ...] = (
    "classic_net",
    "paper_net",
    "cool_net",
)
STICKER_COLOR_QUERY_IDS: Tuple[str, ...] = (
    "static_sticker_color_label",
    "one_move_sticker_color_label",
    "short_sequence_sticker_color_label",
)
FACE_COLOR_COUNT_QUERY_IDS: Tuple[str, ...] = (
    "static_face_color_count_label",
    "one_move_face_color_count_label",
    "short_sequence_face_color_count_label",
)
MOVE_RESULT_QUERY_IDS: Tuple[str, ...] = (
    "one_move_result_label",
    "two_move_result_label",
    "inverse_sequence_result_label",
)
SUPPORTED_RUBIKS_QUERY_IDS: Tuple[str, ...] = (
    *STICKER_COLOR_QUERY_IDS,
    *FACE_COLOR_COUNT_QUERY_IDS,
    *MOVE_RESULT_QUERY_IDS,
)

_FACE_LAYOUT: Mapping[str, Tuple[int, int]] = {
    "U": (1, 0),
    "L": (0, 1),
    "F": (1, 1),
    "R": (2, 1),
    "B": (3, 1),
    "D": (1, 2),
}
_FACE_ORIENTATIONS: Mapping[str, Tuple[Vector3, Vector3, Vector3]] = {
    "F": ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
    "B": ((0, 0, -1), (-1, 0, 0), (0, 1, 0)),
    "R": ((1, 0, 0), (0, 0, -1), (0, 1, 0)),
    "L": ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
    "U": ((0, 1, 0), (1, 0, 0), (0, 0, -1)),
    "D": ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
}
_NORMAL_TO_FACE: Mapping[Vector3, str] = {
    tuple(value[0]): str(face) for face, value in _FACE_ORIENTATIONS.items()
}


@dataclass(frozen=True)
class RubiksRenderParams:
    """Pixel-space layout and style parameters for one Rubik net panel."""

    canvas_width: int = 1480
    canvas_height: int = 940
    scene_margin_left_px: int = 58
    scene_margin_top_px: int = 52
    main_cell_size_px: int = 44
    candidate_cell_size_px: int = 15
    face_gap_px: int = 0
    net_panel_padding_px: int = 22
    panel_corner_radius_px: int = 26
    option_panel_width_px: int = 136
    option_panel_height_px: int = 154
    option_gap_px: int = 18
    option_row_gap_px: int = 18
    result_option_panel_width_px: int = 198
    result_option_panel_height_px: int = 188
    result_option_gap_px: int = 18
    result_option_row_gap_px: int = 18
    swatch_size_px: int = 78
    border_width_px: int = 3
    sticker_gap_px: int = 2
    option_label_font_size_px: int = 29
    face_label_font_size_px: int = 22
    small_label_font_size_px: int = 18
    number_font_size_px: int = 40
    panel_fill_rgb: RGB = (248, 249, 252)
    net_panel_fill_rgb: RGB = (252, 252, 255)
    option_panel_fill_rgb: RGB = (251, 251, 255)
    target_swatch_panel_fill_rgb: RGB = (248, 249, 252)
    sticker_outline_rgb: RGB = (52, 58, 68)
    border_color_rgb: RGB = (86, 94, 108)
    text_color_rgb: RGB = (30, 34, 40)
    text_stroke_rgb: RGB = (255, 255, 255)
    coordinate_fill_rgb: RGB = (255, 246, 248)
    coordinate_grid_rgb: RGB = (176, 124, 138)
    unit_size_jitter: Dict[str, Any] | None = None


@dataclass(frozen=True)
class RenderedRubiksScene:
    """Rendered image plus traced geometry for a Rubik puzzle instance."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    net_panel_bbox_px: List[float]
    net_bbox_px: List[float]
    target_swatch_bbox_px: List[float] | None
    sticker_bbox_map: Dict[str, List[float]]
    option_panel_bbox_map: Dict[str, List[float]]
    candidate_net_bbox_map: Dict[str, List[float]]


def _int_value(mapping: Mapping[str, Any], key: str, fallback: int) -> int:
    value = mapping.get(str(key), int(fallback))
    return int(value)


def _rgb_value(mapping: Mapping[str, Any], key: str, fallback: Sequence[int]) -> RGB:
    raw = mapping.get(str(key), fallback)
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)) and len(raw) >= 3:
        return (int(raw[0]), int(raw[1]), int(raw[2]))
    return (int(fallback[0]), int(fallback[1]), int(fallback[2]))


def resolve_rubiks_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    instance_seed: int | None = None,
) -> RubiksRenderParams:
    """Resolve Rubik render params from task params over group defaults."""

    merged: Dict[str, Any] = dict(render_defaults)
    merged.update(dict(params))
    defaults = RubiksRenderParams()
    unit_scale, unit_meta = resolve_puzzle_unit_size_scale(
        params,
        render_defaults,
        instance_seed=instance_seed,
        namespace="puzzles.rubiks.unit_size",
    )
    return RubiksRenderParams(
        canvas_width=_int_value(merged, "canvas_width", defaults.canvas_width),
        canvas_height=_int_value(merged, "canvas_height", defaults.canvas_height),
        scene_margin_left_px=_int_value(merged, "scene_margin_left_px", defaults.scene_margin_left_px),
        scene_margin_top_px=_int_value(merged, "scene_margin_top_px", defaults.scene_margin_top_px),
        main_cell_size_px=scale_puzzle_px(_int_value(merged, "main_cell_size_px", defaults.main_cell_size_px), unit_scale, min_px=18),
        candidate_cell_size_px=scale_puzzle_px(_int_value(merged, "candidate_cell_size_px", defaults.candidate_cell_size_px), unit_scale, min_px=7),
        face_gap_px=_int_value(merged, "face_gap_px", defaults.face_gap_px),
        net_panel_padding_px=scale_puzzle_px(_int_value(merged, "net_panel_padding_px", defaults.net_panel_padding_px), unit_scale, min_px=10),
        panel_corner_radius_px=scale_puzzle_px(_int_value(merged, "panel_corner_radius_px", defaults.panel_corner_radius_px), unit_scale, min_px=9),
        option_panel_width_px=_int_value(merged, "option_panel_width_px", defaults.option_panel_width_px),
        option_panel_height_px=_int_value(merged, "option_panel_height_px", defaults.option_panel_height_px),
        option_gap_px=scale_puzzle_px(_int_value(merged, "option_gap_px", defaults.option_gap_px), unit_scale, min_px=8),
        option_row_gap_px=scale_puzzle_px(_int_value(merged, "option_row_gap_px", defaults.option_row_gap_px), unit_scale, min_px=8),
        result_option_panel_width_px=_int_value(
            merged,
            "result_option_panel_width_px",
            defaults.result_option_panel_width_px,
        ),
        result_option_panel_height_px=_int_value(
            merged,
            "result_option_panel_height_px",
            defaults.result_option_panel_height_px,
        ),
        result_option_gap_px=scale_puzzle_px(_int_value(merged, "result_option_gap_px", defaults.result_option_gap_px), unit_scale, min_px=8),
        result_option_row_gap_px=_int_value(
            merged,
            "result_option_row_gap_px",
            defaults.result_option_row_gap_px,
        ),
        swatch_size_px=scale_puzzle_px(_int_value(merged, "swatch_size_px", defaults.swatch_size_px), unit_scale, min_px=34),
        border_width_px=scale_puzzle_px(_int_value(merged, "border_width_px", defaults.border_width_px), unit_scale, min_px=1),
        sticker_gap_px=scale_puzzle_px(_int_value(merged, "sticker_gap_px", defaults.sticker_gap_px), unit_scale, min_px=1),
        option_label_font_size_px=_int_value(
            merged,
            "option_label_font_size_px",
            defaults.option_label_font_size_px,
        ),
        face_label_font_size_px=scale_puzzle_px(_int_value(merged, "face_label_font_size_px", defaults.face_label_font_size_px), unit_scale, min_px=12),
        small_label_font_size_px=scale_puzzle_px(_int_value(merged, "small_label_font_size_px", defaults.small_label_font_size_px), unit_scale, min_px=10),
        number_font_size_px=scale_puzzle_px(_int_value(merged, "number_font_size_px", defaults.number_font_size_px), unit_scale, min_px=18),
        panel_fill_rgb=_rgb_value(merged, "panel_fill_rgb", defaults.panel_fill_rgb),
        net_panel_fill_rgb=_rgb_value(merged, "net_panel_fill_rgb", defaults.net_panel_fill_rgb),
        option_panel_fill_rgb=_rgb_value(merged, "option_panel_fill_rgb", defaults.option_panel_fill_rgb),
        target_swatch_panel_fill_rgb=_rgb_value(
            merged,
            "target_swatch_panel_fill_rgb",
            defaults.target_swatch_panel_fill_rgb,
        ),
        sticker_outline_rgb=_rgb_value(merged, "sticker_outline_rgb", defaults.sticker_outline_rgb),
        border_color_rgb=_rgb_value(merged, "border_color_rgb", defaults.border_color_rgb),
        text_color_rgb=_rgb_value(merged, "text_color_rgb", defaults.text_color_rgb),
        text_stroke_rgb=_rgb_value(merged, "text_stroke_rgb", defaults.text_stroke_rgb),
        coordinate_fill_rgb=_rgb_value(merged, "coordinate_fill_rgb", defaults.coordinate_fill_rgb),
        coordinate_grid_rgb=_rgb_value(merged, "coordinate_grid_rgb", defaults.coordinate_grid_rgb),
        unit_size_jitter=dict(unit_meta),
    )


def _vec_add(a: Vector3, b: Vector3) -> Vector3:
    return (int(a[0] + b[0]), int(a[1] + b[1]), int(a[2] + b[2]))


def _vec_mul(a: Vector3, scale: int) -> Vector3:
    return (int(a[0] * scale), int(a[1] * scale), int(a[2] * scale))


def _dot(a: Vector3, b: Vector3) -> int:
    return int((a[0] * b[0]) + (a[1] * b[1]) + (a[2] * b[2]))


def _sticker_to_geometry(key: StickerKey) -> Tuple[Vector3, Vector3]:
    face, row, col = str(key[0]), int(key[1]), int(key[2])
    normal, right, up = _FACE_ORIENTATIONS[str(face)]
    position = _vec_add(
        _vec_add(tuple(normal), _vec_mul(tuple(right), int(col - 1))),
        _vec_mul(tuple(up), int(row - 1)),
    )
    return position, tuple(normal)


def _geometry_to_sticker(position: Vector3, normal: Vector3) -> StickerKey:
    face = str(_NORMAL_TO_FACE[tuple(normal)])
    face_normal, right, up = _FACE_ORIENTATIONS[str(face)]
    relative = (
        int(position[0] - face_normal[0]),
        int(position[1] - face_normal[1]),
        int(position[2] - face_normal[2]),
    )
    col = int(_dot(relative, tuple(right)) + 1)
    row = int(_dot(relative, tuple(up)) + 1)
    return (str(face), int(row), int(col))


def _rotate_vector_quarter(vec: Vector3, axis: Vector3, quarter_turns: int) -> Vector3:
    turns = int(quarter_turns) % 4
    x, y, z = int(vec[0]), int(vec[1]), int(vec[2])
    ax = tuple(int(v) for v in axis)
    for _ in range(turns):
        if ax == (1, 0, 0):
            x, y, z = x, -z, y
        elif ax == (-1, 0, 0):
            x, y, z = x, z, -y
        elif ax == (0, 1, 0):
            x, y, z = z, y, -x
        elif ax == (0, -1, 0):
            x, y, z = -z, y, x
        elif ax == (0, 0, 1):
            x, y, z = -y, x, z
        elif ax == (0, 0, -1):
            x, y, z = y, -x, z
        else:
            raise ValueError(f"unsupported rotation axis: {axis}")
    return (int(x), int(y), int(z))


def _parse_move(move: str) -> Tuple[str, bool]:
    text = str(move).strip()
    if not text:
        raise ValueError("empty Rubik move")
    face = str(text[0]).upper()
    if face not in MOVE_FACES:
        raise ValueError(f"unsupported Rubik move face: {move}")
    is_prime = "'" in text
    return face, bool(is_prime)


def invert_move(move: str) -> str:
    """Return the inverse of one face-turn token."""

    face, is_prime = _parse_move(str(move))
    return str(face) if bool(is_prime) else f"{face}'"


def invert_sequence(sequence: Sequence[str]) -> List[str]:
    """Return inverse tokens for one face-turn sequence."""

    return [invert_move(str(move)) for move in reversed([str(item) for item in sequence])]


def apply_move(
    state: Mapping[StickerKey, str],
    move: str,
) -> Dict[StickerKey, str]:
    """Apply one quarter-turn to a sticker-color state."""

    face, is_prime = _parse_move(str(move))
    axis = tuple(_FACE_ORIENTATIONS[str(face)][0])
    # Clockwise from outside is a negative right-hand turn around the face normal.
    quarter_turns = 1 if bool(is_prime) else 3
    next_state: Dict[StickerKey, str] = {}
    for key, color_name in state.items():
        position, normal = _sticker_to_geometry(tuple(key))
        if int(_dot(position, axis)) == 1:
            new_position = _rotate_vector_quarter(position, axis, int(quarter_turns))
            new_normal = _rotate_vector_quarter(normal, axis, int(quarter_turns))
            next_state[_geometry_to_sticker(new_position, new_normal)] = str(color_name)
        else:
            next_state[tuple(key)] = str(color_name)
    return next_state


def apply_sequence(
    state: Mapping[StickerKey, str],
    sequence: Sequence[str],
) -> Dict[StickerKey, str]:
    """Apply a sequence of quarter-turn tokens."""

    current: Dict[StickerKey, str] = {tuple(key): str(value) for key, value in state.items()}
    for move in [str(item) for item in sequence]:
        current = apply_move(current, str(move))
    return current


def state_signature(state: Mapping[StickerKey, str]) -> Tuple[Tuple[str, int, int, str], ...]:
    """Return one stable signature for duplicate rejection."""

    return tuple(
        (str(face), int(row), int(col), str(state[(str(face), int(row), int(col))]))
        for face in FACE_ORDER
        for row in range(3)
        for col in range(3)
    )


def _make_solved_state(face_color_names: Mapping[str, str]) -> Dict[StickerKey, str]:
    state: Dict[StickerKey, str] = {}
    for face in FACE_ORDER:
        for row in range(3):
            for col in range(3):
                state[(str(face), int(row), int(col))] = str(face_color_names[str(face)])
    return state


def _sample_move(rng, *, previous_face: str | None = None) -> str:
    faces = [str(face) for face in MOVE_FACES if str(face) != str(previous_face or "")]
    face = str(faces[int(rng.randrange(len(faces)))])
    return f"{face}'" if int(rng.randrange(2)) == 1 else str(face)


def _sample_move_sequence(rng, *, length: int) -> List[str]:
    moves: List[str] = []
    previous_face: str | None = None
    for _ in range(int(length)):
        move = _sample_move(rng, previous_face=previous_face)
        previous_face, _ = _parse_move(str(move))
        moves.append(str(move))
    return moves


def _format_sequence(sequence: Sequence[str]) -> str:
    return " ".join(str(item) for item in sequence)


def _as_range(
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
) -> Tuple[int, int]:
    low = int(params.get(str(min_key), group_default(gen_defaults, str(min_key), int(fallback_min))))
    high = int(params.get(str(max_key), group_default(gen_defaults, str(max_key), int(fallback_max))))
    if int(low) > int(high):
        raise ValueError(f"{min_key} must be <= {max_key}")
    return int(low), int(high)


def _sample_base_state(
    *,
    rng,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> Tuple[Dict[StickerKey, str], Dict[str, Dict[str, Any]], List[str], Dict[str, str]]:
    color_count = int(params.get("rubiks_palette_size", group_default(gen_defaults, "rubiks_palette_size", 6)))
    color_count = max(6, min(6, int(color_count)))
    palette = sample_named_color_palette(rng, palette_size=int(color_count))
    if len(palette) < 6:
        palette = list(available_named_colors())[:6]
    palette_entries = [
        {
            "color_name": str(name),
            "color_rgb": [int(channel) for channel in rgb],
        }
        for name, rgb in palette[:6]
    ]
    color_names = [str(item["color_name"]) for item in palette_entries]
    shuffled = list(color_names)
    rng.shuffle(shuffled)
    face_color_names = {str(face): str(shuffled[index]) for index, face in enumerate(FACE_ORDER)}
    solved = _make_solved_state(face_color_names)
    scramble_min, scramble_max = _as_range(
        params,
        gen_defaults,
        min_key="scramble_move_count_min",
        max_key="scramble_move_count_max",
        fallback_min=4,
        fallback_max=8,
    )
    scramble_len = int(rng.randint(int(scramble_min), int(scramble_max)))
    scramble_sequence = _sample_move_sequence(rng, length=int(scramble_len))
    state = apply_sequence(solved, scramble_sequence)
    color_map = {
        str(item["color_name"]): {
            "color_name": str(item["color_name"]),
            "color_rgb": [int(channel) for channel in item["color_rgb"]],
        }
        for item in palette_entries
    }
    return state, color_map, scramble_sequence, face_color_names


def _target_key(rng) -> StickerKey:
    face = str(FACE_ORDER[int(rng.randrange(len(FACE_ORDER)))])
    row = int(rng.randrange(3))
    col = int(rng.randrange(3))
    return (str(face), int(row), int(col))


def _face_color_count(state: Mapping[StickerKey, str], *, face: str, color_name: str) -> int:
    return sum(
        1
        for row in range(3)
        for col in range(3)
        if str(state[(str(face), int(row), int(col))]) == str(color_name)
    )


def _make_option_specs(
    *,
    rng,
    labels: Sequence[str],
    answer_value: Any,
    distractor_values: Sequence[Any],
    answer_label_index: int | None = None,
) -> Tuple[List[Dict[str, Any]], str]:
    values: List[Any] = []
    for value in distractor_values:
        if value != answer_value and value not in values:
            values.append(value)
        if len(values) >= len(labels):
            break
    if answer_label_index is None:
        values = [answer_value, *values]
        values = values[: len(labels)]
        rng.shuffle(values)
    else:
        resolved_index = int(answer_label_index) % max(1, len(labels))
        distractor_iter = iter(values)
        arranged: List[Any] = []
        for index in range(len(labels)):
            if int(index) == int(resolved_index):
                arranged.append(answer_value)
            else:
                arranged.append(next(distractor_iter))
        values = arranged
    specs: List[Dict[str, Any]] = []
    answer_label = ""
    for index, value in enumerate(values):
        label = str(labels[int(index)])
        if value == answer_value:
            answer_label = str(label)
        specs.append(
            {
                "option_id": f"option_{label}",
                "option_label": str(label),
                "value": value,
                "is_correct": bool(value == answer_value),
            }
        )
    if not answer_label:
        raise RuntimeError("unable to construct Rubik option labels")
    return specs, str(answer_label)


def _color_option_specs(
    *,
    rng,
    color_map: Mapping[str, Mapping[str, Any]],
    answer_color_name: str,
    option_count: int,
    answer_label_index: int | None = None,
) -> Tuple[List[Dict[str, Any]], str]:
    labels = OPTION_LABELS[: int(option_count)]
    color_names = [str(name) for name in color_map]
    distractors = [str(name) for name in color_names if str(name) != str(answer_color_name)]
    rng.shuffle(distractors)
    values = [str(answer_color_name), *distractors]
    specs, answer_label = _make_option_specs(
        rng=rng,
        labels=labels,
        answer_value=str(answer_color_name),
        distractor_values=values[1:],
        answer_label_index=answer_label_index,
    )
    for spec in specs:
        color_entry = color_map[str(spec["value"])]
        spec["color_name"] = str(color_entry["color_name"])
        spec["color_rgb"] = [int(channel) for channel in color_entry["color_rgb"]]
    return specs, str(answer_label)


def _count_option_specs(
    *,
    rng,
    answer_count: int,
    option_count: int,
    answer_label_index: int | None = None,
) -> Tuple[List[Dict[str, Any]], str]:
    labels = OPTION_LABELS[: int(option_count)]
    candidates = list(range(10))
    candidates.sort(key=lambda value: (abs(int(value) - int(answer_count)), int(value)))
    near = [int(value) for value in candidates if int(value) != int(answer_count)]
    specs, answer_label = _make_option_specs(
        rng=rng,
        labels=labels,
        answer_value=int(answer_count),
        distractor_values=near,
        answer_label_index=answer_label_index,
    )
    for spec in specs:
        spec["count_value"] = int(spec["value"])
    return specs, str(answer_label)


def _option_count(
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    *,
    fallback_min: int,
    fallback_max: int,
) -> int:
    low, high = _as_range(
        params,
        gen_defaults,
        min_key="option_count_min",
        max_key="option_count_max",
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
    )
    return int(max(4, min(8, high if low == high else low)))


def build_rubiks_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Dict[str, Any]:
    """Build one symbolic Rubik scene and answer specification."""

    if str(query_id) not in SUPPORTED_RUBIKS_QUERY_IDS:
        raise ValueError(f"unsupported rubiks query_id: {query_id}")

    rng = spawn_rng(int(instance_seed), f"{task_id}.{query_id}.dataset")
    option_count = _option_count(params, gen_defaults, fallback_min=6, fallback_max=6)
    answer_label_index = int(abs(int(instance_seed)) % max(1, int(option_count)))
    max_attempts = int(params.get("rubiks_dataset_max_attempts", group_default(gen_defaults, "rubiks_dataset_max_attempts", 128)))

    for _ in range(max(1, int(max_attempts))):
        start_state, color_map, scramble_sequence, face_color_names = _sample_base_state(
            rng=rng,
            params=params,
            gen_defaults=gen_defaults,
        )

        if str(query_id) in STICKER_COLOR_QUERY_IDS:
            if str(query_id) == "static_sticker_color_label":
                query_sequence: List[str] = []
            elif str(query_id) == "one_move_sticker_color_label":
                query_sequence = _sample_move_sequence(rng, length=1)
            else:
                length_min, length_max = _as_range(
                    params,
                    gen_defaults,
                    min_key="short_sequence_move_count_min",
                    max_key="short_sequence_move_count_max",
                    fallback_min=2,
                    fallback_max=3,
                )
                query_sequence = _sample_move_sequence(rng, length=int(rng.randint(length_min, length_max)))
            final_state = apply_sequence(start_state, query_sequence)
            target_key = _target_key(rng)
            answer_color_name = str(final_state[target_key])
            option_specs, answer_option_label = _color_option_specs(
                rng=rng,
                color_map=color_map,
                answer_color_name=str(answer_color_name),
                option_count=int(option_count),
                answer_label_index=int(answer_label_index),
            )
            return {
                "objective_contract": "sticker_color_label",
                "query_id": str(query_id),
                "start_state": dict(start_state),
                "final_state": dict(final_state),
                "color_map": dict(color_map),
                "face_color_names": dict(face_color_names),
                "scramble_sequence": list(scramble_sequence),
                "query_sequence": list(query_sequence),
                "move_sequence_text": _format_sequence(query_sequence),
                "target_face": str(target_key[0]),
                "target_face_name": str(FACE_DISPLAY_NAMES[str(target_key[0])]),
                "target_row": int(target_key[1]),
                "target_col": int(target_key[2]),
                "target_sticker_id": _sticker_id(*target_key),
                "answer_color_name": str(answer_color_name),
                "answer_color_rgb": list(color_map[str(answer_color_name)]["color_rgb"]),
                "option_specs": option_specs,
                "option_count": int(option_count),
                "answer_option_label": str(answer_option_label),
                "solver_trace": {
                    "operation": "apply_sequence_then_read_sticker_color",
                    "final_target_color_name": str(answer_color_name),
                },
            }

        if str(query_id) in FACE_COLOR_COUNT_QUERY_IDS:
            if str(query_id) == "static_face_color_count_label":
                query_sequence = []
            elif str(query_id) == "one_move_face_color_count_label":
                query_sequence = _sample_move_sequence(rng, length=1)
            else:
                length_min, length_max = _as_range(
                    params,
                    gen_defaults,
                    min_key="short_sequence_move_count_min",
                    max_key="short_sequence_move_count_max",
                    fallback_min=2,
                    fallback_max=3,
                )
                query_sequence = _sample_move_sequence(rng, length=int(rng.randint(length_min, length_max)))
            final_state = apply_sequence(start_state, query_sequence)
            target_face = str(FACE_ORDER[int(rng.randrange(len(FACE_ORDER)))])
            color_names = list(color_map.keys())
            rng.shuffle(color_names)
            count_min, count_max = _as_range(
                params,
                gen_defaults,
                min_key="face_color_count_answer_min",
                max_key="face_color_count_answer_max",
                fallback_min=1,
                fallback_max=6,
            )
            for color_name in color_names:
                answer_count = _face_color_count(final_state, face=target_face, color_name=str(color_name))
                if int(count_min) <= int(answer_count) <= int(count_max):
                    option_specs, answer_option_label = _count_option_specs(
                        rng=rng,
                        answer_count=int(answer_count),
                        option_count=int(option_count),
                        answer_label_index=int(answer_label_index),
                    )
                    counted_sticker_ids = [
                        _sticker_id(str(target_face), int(row), int(col))
                        for row in range(3)
                        for col in range(3)
                        if str(final_state[(str(target_face), int(row), int(col))]) == str(color_name)
                    ]
                    return {
                        "objective_contract": "face_color_count_label",
                        "query_id": str(query_id),
                        "start_state": dict(start_state),
                        "final_state": dict(final_state),
                        "color_map": dict(color_map),
                        "face_color_names": dict(face_color_names),
                        "scramble_sequence": list(scramble_sequence),
                        "query_sequence": list(query_sequence),
                        "move_sequence_text": _format_sequence(query_sequence),
                        "target_face": str(target_face),
                        "target_face_name": str(FACE_DISPLAY_NAMES[str(target_face)]),
                        "target_color_name": str(color_name),
                        "target_color_rgb": list(color_map[str(color_name)]["color_rgb"]),
                        "counted_sticker_ids": list(counted_sticker_ids),
                        "answer_count": int(answer_count),
                        "option_specs": option_specs,
                        "option_count": int(option_count),
                        "answer_option_label": str(answer_option_label),
                        "solver_trace": {
                            "operation": "apply_sequence_then_count_color_on_face",
                            "final_counted_sticker_ids": list(counted_sticker_ids),
                        },
                    }
            continue

        if str(query_id) in MOVE_RESULT_QUERY_IDS:
            if str(query_id) == "one_move_result_label":
                query_sequence = _sample_move_sequence(rng, length=1)
                base_sequence: List[str] = []
            elif str(query_id) == "two_move_result_label":
                query_sequence = _sample_move_sequence(rng, length=2)
                base_sequence = []
            else:
                base_sequence = _sample_move_sequence(rng, length=2)
                query_sequence = invert_sequence(base_sequence)
            answer_state = apply_sequence(start_state, query_sequence)
            candidate_states: List[Dict[StickerKey, str]] = [dict(answer_state)]
            seen = {state_signature(answer_state)}
            attempts = 0
            while len(candidate_states) < int(option_count) and attempts < 200:
                attempts += 1
                alt_len = max(1, len(query_sequence))
                alt_sequence = _sample_move_sequence(rng, length=int(alt_len))
                candidate = apply_sequence(start_state, alt_sequence)
                sig = state_signature(candidate)
                if sig in seen:
                    candidate = apply_move(answer_state, _sample_move(rng))
                    sig = state_signature(candidate)
                if sig in seen:
                    continue
                seen.add(sig)
                candidate_states.append(dict(candidate))
            if len(candidate_states) < int(option_count):
                continue
            labels = list(OPTION_LABELS[: int(option_count)])
            distractor_states = [dict(state) for state in candidate_states[1: int(option_count)]]
            option_specs = []
            answer_option_label = ""
            for option_index, label in enumerate(labels):
                is_correct = int(option_index) == int(answer_label_index)
                state = dict(answer_state) if bool(is_correct) else dict(distractor_states.pop(0))
                label = str(labels[int(option_index)])
                if bool(is_correct):
                    answer_option_label = str(label)
                option_specs.append(
                    {
                        "option_id": f"option_{label}",
                        "option_label": str(label),
                        "is_correct": bool(is_correct),
                        "state": dict(state),
                    }
                )
            return {
                "objective_contract": "move_result_label",
                "query_id": str(query_id),
                "start_state": dict(start_state),
                "final_state": dict(answer_state),
                "color_map": dict(color_map),
                "face_color_names": dict(face_color_names),
                "scramble_sequence": list(scramble_sequence),
                "query_sequence": list(query_sequence),
                "base_sequence": list(base_sequence),
                "move_sequence_text": _format_sequence(query_sequence),
                "base_sequence_text": _format_sequence(base_sequence),
                "option_specs": option_specs,
                "option_count": int(option_count),
                "answer_option_label": str(answer_option_label),
                "solver_trace": {
                    "operation": "apply_sequence_and_match_candidate_net",
                    "answer_state_signature": state_signature(answer_state),
                },
            }

    raise RuntimeError("unable to sample Rubik dataset with requested constraints")


def _sticker_id(face: str, row: int, col: int) -> str:
    return f"{str(face)}_r{int(row)}_c{int(col)}"


def _state_color(
    state: Mapping[StickerKey, str],
    color_map: Mapping[str, Mapping[str, Any]],
    *,
    face: str,
    row: int,
    col: int,
) -> RGB:
    color_name = str(state[(str(face), int(row), int(col))])
    rgb = color_map[str(color_name)]["color_rgb"]
    return (int(rgb[0]), int(rgb[1]), int(rgb[2]))


def _draw_panel(
    draw: ImageDraw.ImageDraw,
    bbox: Sequence[float],
    *,
    fill: Sequence[int],
    outline: Sequence[int],
    radius: int,
    width: int,
) -> None:
    draw_rounded_rect(
        draw,
        (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])),
        radius=int(radius),
        fill=tuple(int(value) for value in fill),
        outline=tuple(int(value) for value in outline),
        width=int(width),
    )


def _draw_cube_net(
    draw: ImageDraw.ImageDraw,
    *,
    state: Mapping[StickerKey, str],
    color_map: Mapping[str, Mapping[str, Any]],
    origin: Tuple[float, float],
    cell_size_px: float,
    sticker_gap_px: float,
    outline_rgb: Sequence[int],
    face_label_font,
    text_rgb: Sequence[int],
    text_stroke_rgb: Sequence[int],
    include_face_labels: bool,
) -> Tuple[Dict[str, List[float]], List[float]]:
    sticker_bbox_map: Dict[str, List[float]] = {}
    ox, oy = float(origin[0]), float(origin[1])
    cell = float(cell_size_px)
    gap = max(0.0, float(sticker_gap_px))
    for face in FACE_ORDER:
        face_grid_x, face_grid_y = _FACE_LAYOUT[str(face)]
        face_left = float(ox + (int(face_grid_x) * 3.0 * cell))
        face_top = float(oy + (int(face_grid_y) * 3.0 * cell))
        for row in range(3):
            for col in range(3):
                x0 = float(face_left + (int(col) * cell) + gap)
                y0 = float(face_top + ((2 - int(row)) * cell) + gap)
                x1 = float(face_left + ((int(col) + 1) * cell) - gap)
                y1 = float(face_top + ((3 - int(row)) * cell) - gap)
                bbox = (x0, y0, x1, y1)
                draw.rectangle(
                    bbox,
                    fill=_state_color(state, color_map, face=str(face), row=int(row), col=int(col)),
                    outline=tuple(int(value) for value in outline_rgb),
                    width=max(1, int(round(cell * 0.045))),
                )
                sticker_bbox_map[_sticker_id(str(face), int(row), int(col))] = _round_bbox(bbox)
        if bool(include_face_labels):
            label_x = float(face_left + (1.5 * cell))
            label_y = float(face_top - (0.34 * cell))
            if str(face) == "D":
                label_y = float(face_top + (3.34 * cell))
            elif str(face) == "L":
                label_x = float(face_left - (0.35 * cell))
                label_y = float(face_top + (1.5 * cell))
            elif str(face) in {"F", "R", "B"}:
                label_y = float(face_top - (0.28 * cell))
            draw_centered_text(
                draw,
                text=str(face),
                center=(label_x, label_y),
                font=face_label_font,
                fill=text_rgb,
                stroke_fill=text_stroke_rgb,
                stroke_width=2,
            )
    net_bbox = [ox, oy, float(ox + (12.0 * cell)), float(oy + (9.0 * cell))]
    return sticker_bbox_map, _round_bbox(net_bbox)


def _draw_coordinate_reference(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    params: RubiksRenderParams,
) -> List[float]:
    _draw_panel(
        draw,
        bbox,
        fill=params.coordinate_fill_rgb,
        outline=params.coordinate_grid_rgb,
        radius=10,
        width=2,
    )
    x0, y0, x1, y1 = [float(value) for value in bbox]
    cell_w = float((x1 - x0) / 3.0)
    cell_h = float((y1 - y0) / 3.0)
    font = load_font(max(10, min(14, int(params.small_label_font_size_px))), bold=True)
    for index in range(1, 3):
        draw.line(
            [(float(x0 + (index * cell_w)), y0), (float(x0 + (index * cell_w)), y1)],
            fill=tuple(int(v) for v in params.coordinate_grid_rgb),
            width=1,
        )
        draw.line(
            [(x0, float(y0 + (index * cell_h))), (x1, float(y0 + (index * cell_h)))],
            fill=tuple(int(v) for v in params.coordinate_grid_rgb),
            width=1,
        )
    for row in range(3):
        for col in range(3):
            cx = float(x0 + ((col + 0.5) * cell_w))
            cy = float(y0 + (((2 - row) + 0.5) * cell_h))
            draw_centered_text(
                draw,
                text=f"({col},{row})",
                center=(cx, cy),
                font=font,
                fill=params.text_color_rgb,
                stroke_fill=params.text_stroke_rgb,
                stroke_width=1,
            )
    return _round_bbox(bbox)


def _draw_color_or_number_options(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: Mapping[str, Any],
    params: RubiksRenderParams,
    top_left: Tuple[float, float],
) -> Dict[str, List[float]]:
    label_font = load_font(int(params.option_label_font_size_px), bold=True)
    number_font = load_font(int(params.number_font_size_px), bold=True)
    option_map: Dict[str, List[float]] = {}
    start_x, start_y = float(top_left[0]), float(top_left[1])
    for index, option in enumerate(dataset["option_specs"]):
        row = int(index) // 4
        col = int(index) % 4
        x0 = float(start_x + (col * (params.option_panel_width_px + params.option_gap_px)))
        y0 = float(start_y + (row * (params.option_panel_height_px + params.option_row_gap_px)))
        bbox = [
            x0,
            y0,
            float(x0 + params.option_panel_width_px),
            float(y0 + params.option_panel_height_px),
        ]
        _draw_panel(
            draw,
            bbox,
            fill=params.option_panel_fill_rgb,
            outline=params.border_color_rgb,
            radius=params.panel_corner_radius_px,
            width=params.border_width_px,
        )
        label = str(option["option_label"])
        draw_centered_text(
            draw,
            text=label,
            center=(float(x0 + (params.option_panel_width_px / 2.0)), float(y0 + 24)),
            font=label_font,
            fill=params.text_color_rgb,
            stroke_fill=params.text_stroke_rgb,
            stroke_width=1,
        )
        content_cx = float(x0 + (params.option_panel_width_px / 2.0))
        content_cy = float(y0 + 91)
        if "color_rgb" in option:
            half = float(params.swatch_size_px / 2.0)
            swatch_bbox = [content_cx - half, content_cy - half, content_cx + half, content_cy + half]
            _draw_panel(
                draw,
                swatch_bbox,
                fill=tuple(int(v) for v in option["color_rgb"]),
                outline=params.sticker_outline_rgb,
                radius=14,
                width=3,
            )
        else:
            draw_centered_text(
                draw,
                text=str(option["count_value"]),
                center=(content_cx, content_cy),
                font=number_font,
                fill=params.text_color_rgb,
                stroke_fill=params.text_stroke_rgb,
                stroke_width=1,
            )
        option_map[str(option["option_id"])] = _round_bbox(bbox)
    return option_map


def _draw_target_swatch(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: Mapping[str, Any],
    params: RubiksRenderParams,
    bbox: Sequence[float],
) -> List[float]:
    _draw_panel(
        draw,
        bbox,
        fill=params.target_swatch_panel_fill_rgb,
        outline=params.border_color_rgb,
        radius=params.panel_corner_radius_px,
        width=params.border_width_px,
    )
    label_font = load_font(int(params.small_label_font_size_px), bold=True)
    draw_centered_text(
        draw,
        text="Target",
        center=(float((bbox[0] + bbox[2]) / 2.0), float(bbox[1] + 24.0)),
        font=label_font,
        fill=params.text_color_rgb,
        stroke_fill=params.text_stroke_rgb,
        stroke_width=1,
    )
    half = float(params.swatch_size_px / 2.0)
    cx = float((bbox[0] + bbox[2]) / 2.0)
    cy = float(bbox[1] + 86.0)
    swatch_bbox = [cx - half, cy - half, cx + half, cy + half]
    _draw_panel(
        draw,
        swatch_bbox,
        fill=tuple(int(v) for v in dataset["target_color_rgb"]),
        outline=params.sticker_outline_rgb,
        radius=14,
        width=3,
    )
    return _round_bbox(swatch_bbox)


def _draw_result_options(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: Mapping[str, Any],
    params: RubiksRenderParams,
    color_map: Mapping[str, Mapping[str, Any]],
    top_left: Tuple[float, float],
) -> Tuple[Dict[str, List[float]], Dict[str, List[float]]]:
    label_font = load_font(int(params.option_label_font_size_px), bold=True)
    face_font = load_font(max(9, int(params.small_label_font_size_px) - 3), bold=True)
    option_panel_map: Dict[str, List[float]] = {}
    candidate_net_map: Dict[str, List[float]] = {}
    start_x, start_y = float(top_left[0]), float(top_left[1])
    for index, option in enumerate(dataset["option_specs"]):
        row = int(index) // 3
        col = int(index) % 3
        x0 = float(start_x + (col * (params.result_option_panel_width_px + params.result_option_gap_px)))
        y0 = float(start_y + (row * (params.result_option_panel_height_px + params.result_option_row_gap_px)))
        panel_bbox = [
            x0,
            y0,
            float(x0 + params.result_option_panel_width_px),
            float(y0 + params.result_option_panel_height_px),
        ]
        _draw_panel(
            draw,
            panel_bbox,
            fill=params.option_panel_fill_rgb,
            outline=params.border_color_rgb,
            radius=params.panel_corner_radius_px,
            width=params.border_width_px,
        )
        label = str(option["option_label"])
        draw_centered_text(
            draw,
            text=label,
            center=(float(x0 + (params.result_option_panel_width_px / 2.0)), float(y0 + 24)),
            font=label_font,
            fill=params.text_color_rgb,
            stroke_fill=params.text_stroke_rgb,
            stroke_width=1,
        )
        net_origin = (float(x0 + 9), float(y0 + 44))
        _stickers, net_bbox = _draw_cube_net(
            draw,
            state=option["state"],
            color_map=color_map,
            origin=net_origin,
            cell_size_px=float(params.candidate_cell_size_px),
            sticker_gap_px=0.8,
            outline_rgb=params.sticker_outline_rgb,
            face_label_font=face_font,
            text_rgb=params.text_color_rgb,
            text_stroke_rgb=params.text_stroke_rgb,
            include_face_labels=False,
        )
        option_panel_map[str(option["option_id"])] = _round_bbox(panel_bbox)
        candidate_net_map[str(option["option_id"])] = list(net_bbox)
    return option_panel_map, candidate_net_map


def render_rubiks_scene(
    image: Image.Image,
    *,
    dataset: Mapping[str, Any],
    scene_variant: str,
    render_params: RubiksRenderParams,
) -> RenderedRubiksScene:
    """Render one Rubik puzzle scene on the provided background image."""

    params = render_params
    draw = ImageDraw.Draw(image)
    entities: List[Dict[str, Any]] = []
    scene_bbox = [0.0, 0.0, float(params.canvas_width), float(params.canvas_height)]

    label_font = load_font(int(params.face_label_font_size_px), bold=True)
    small_font = load_font(int(params.small_label_font_size_px), bold=True)
    color_map = dataset["color_map"]

    target_swatch_bbox: List[float] | None = None
    candidate_net_bbox_map: Dict[str, List[float]] = {}
    option_panel_bbox_map: Dict[str, List[float]] = {}

    if str(dataset["objective_contract"]) == "move_result_label":
        net_left = float(params.scene_margin_left_px + 42)
        net_top = float(params.scene_margin_top_px + 42)
        net_panel_bbox = [
            float(params.scene_margin_left_px),
            float(params.scene_margin_top_px),
            float(params.scene_margin_left_px + 650),
            float(params.scene_margin_top_px + 450),
        ]
        _draw_panel(
            draw,
            net_panel_bbox,
            fill=params.net_panel_fill_rgb,
            outline=params.border_color_rgb,
            radius=params.panel_corner_radius_px,
            width=params.border_width_px,
        )
        draw_centered_text(
            draw,
            text="Start",
            center=(float(net_panel_bbox[0] + 54), float(net_panel_bbox[1] + 30)),
            font=small_font,
            fill=params.text_color_rgb,
            stroke_fill=params.text_stroke_rgb,
            stroke_width=1,
        )
        sticker_bbox_map, net_bbox = _draw_cube_net(
            draw,
            state=dataset["start_state"],
            color_map=color_map,
            origin=(net_left, net_top),
            cell_size_px=float(params.main_cell_size_px),
            sticker_gap_px=float(params.sticker_gap_px),
            outline_rgb=params.sticker_outline_rgb,
            face_label_font=label_font,
            text_rgb=params.text_color_rgb,
            text_stroke_rgb=params.text_stroke_rgb,
            include_face_labels=True,
        )
        coord_bbox = [
            float(net_panel_bbox[2] - 220),
            float(net_panel_bbox[1] + 266),
            float(net_panel_bbox[2] - 34),
            float(net_panel_bbox[1] + 410),
        ]
        _draw_coordinate_reference(draw, bbox=coord_bbox, params=params)
        option_panel_bbox_map, candidate_net_bbox_map = _draw_result_options(
            draw,
            dataset=dataset,
            params=params,
            color_map=color_map,
            top_left=(float(params.scene_margin_left_px + 18), float(params.scene_margin_top_px + 484)),
        )
    else:
        net_panel_bbox = [
            float(params.scene_margin_left_px),
            float(params.scene_margin_top_px),
            float(params.scene_margin_left_px + 700),
            float(params.scene_margin_top_px + 520),
        ]
        _draw_panel(
            draw,
            net_panel_bbox,
            fill=params.net_panel_fill_rgb,
            outline=params.border_color_rgb,
            radius=params.panel_corner_radius_px,
            width=params.border_width_px,
        )
        sticker_bbox_map, net_bbox = _draw_cube_net(
            draw,
            state=dataset["start_state"],
            color_map=color_map,
            origin=(float(params.scene_margin_left_px + 46), float(params.scene_margin_top_px + 58)),
            cell_size_px=float(params.main_cell_size_px),
            sticker_gap_px=float(params.sticker_gap_px),
            outline_rgb=params.sticker_outline_rgb,
            face_label_font=label_font,
            text_rgb=params.text_color_rgb,
            text_stroke_rgb=params.text_stroke_rgb,
            include_face_labels=True,
        )
        coord_bbox = [
            float(net_panel_bbox[2] - 224),
            float(net_panel_bbox[1] + 330),
            float(net_panel_bbox[2] - 38),
            float(net_panel_bbox[1] + 476),
        ]
        _draw_coordinate_reference(draw, bbox=coord_bbox, params=params)
        if str(dataset["objective_contract"]) == "face_color_count_label":
            target_swatch_bbox = _draw_target_swatch(
                draw,
                dataset=dataset,
                params=params,
                bbox=[
                    float(params.scene_margin_left_px + 742),
                    float(params.scene_margin_top_px + 44),
                    float(params.scene_margin_left_px + 898),
                    float(params.scene_margin_top_px + 178),
                ],
            )
            options_top_left = (float(params.scene_margin_left_px + 742), float(params.scene_margin_top_px + 216))
        else:
            options_top_left = (float(params.scene_margin_left_px + 742), float(params.scene_margin_top_px + 74))
        option_panel_bbox_map = _draw_color_or_number_options(
            draw,
            dataset=dataset,
            params=params,
            top_left=options_top_left,
        )

    for sticker_id, bbox in sticker_bbox_map.items():
        entities.append({"entity_id": str(sticker_id), "type": "rubiks_sticker", "bbox_px": list(bbox)})
    for option_id, bbox in option_panel_bbox_map.items():
        entities.append({"entity_id": str(option_id), "type": "rubiks_option_panel", "bbox_px": list(bbox)})
    entities.append({"entity_id": "rubiks_net", "type": "rubiks_cube_net", "bbox_px": list(net_bbox)})

    return RenderedRubiksScene(
        image=image,
        entities=entities,
        scene_bbox_px=_round_bbox(scene_bbox),
        net_panel_bbox_px=_round_bbox(net_panel_bbox),
        net_bbox_px=list(net_bbox),
        target_swatch_bbox_px=target_swatch_bbox,
        sticker_bbox_map=dict(sticker_bbox_map),
        option_panel_bbox_map=dict(option_panel_bbox_map),
        candidate_net_bbox_map=dict(candidate_net_bbox_map),
    )


__all__ = [
    "FACE_DISPLAY_NAMES",
    "FACE_ORDER",
    "FACE_COLOR_COUNT_QUERY_IDS",
    "MOVE_RESULT_QUERY_IDS",
    "OPTION_LABELS",
    "RubiksRenderParams",
    "RenderedRubiksScene",
    "STICKER_COLOR_QUERY_IDS",
    "SUPPORTED_RUBIKS_QUERY_IDS",
    "SUPPORTED_RUBIKS_SCENE_VARIANTS",
    "apply_sequence",
    "build_rubiks_dataset",
    "invert_sequence",
    "render_rubiks_scene",
    "resolve_rubiks_render_params",
    "state_signature",
]
