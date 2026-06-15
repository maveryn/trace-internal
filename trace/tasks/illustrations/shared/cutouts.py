"""Pure visual reconstruction mechanics for illustration scenes."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageOps, ImageStat

from .option_rendering import bbox_list, draw_label_badge, draw_panel_label, image_detail_score


JIGSAW_BOARD_STYLES: Dict[str, Dict[str, Any]] = {
    "pale_cross": {
        "canvas_rgb": (238, 241, 245),
        "blank_fill_rgb": (222, 228, 236),
        "blank_outline_rgb": (92, 102, 116),
        "blank_mark_rgb": (200, 208, 219),
        "board_outline_rgb": (44, 52, 65),
        "badge_fill_rgb": (255, 255, 255),
        "badge_outline_rgb": (44, 52, 65),
        "blank_marker": "x",
    },
    "warm_corner": {
        "canvas_rgb": (244, 240, 232),
        "blank_fill_rgb": (232, 224, 211),
        "blank_outline_rgb": (104, 91, 76),
        "blank_mark_rgb": (188, 174, 154),
        "board_outline_rgb": (58, 50, 42),
        "badge_fill_rgb": (255, 252, 244),
        "badge_outline_rgb": (58, 50, 42),
        "blank_marker": "corners",
    },
    "cool_dots": {
        "canvas_rgb": (235, 242, 244),
        "blank_fill_rgb": (218, 232, 234),
        "blank_outline_rgb": (70, 93, 101),
        "blank_mark_rgb": (174, 198, 204),
        "board_outline_rgb": (35, 54, 64),
        "badge_fill_rgb": (250, 253, 253),
        "badge_outline_rgb": (35, 54, 64),
        "blank_marker": "dots",
    },
}

ROTATED_GRID_STYLES: Dict[str, Dict[str, Any]] = {
    "slate_badges": {
        "canvas_rgb": (238, 241, 245),
        "grid_rgb": (33, 39, 49),
        "badge_fill_rgb": (255, 255, 255),
        "badge_outline_rgb": (33, 39, 49),
        "grid_width_px": 3,
    },
    "ink_badges": {
        "canvas_rgb": (244, 240, 232),
        "grid_rgb": (45, 41, 37),
        "badge_fill_rgb": (255, 252, 244),
        "badge_outline_rgb": (45, 41, 37),
        "grid_width_px": 3,
    },
    "blueprint_badges": {
        "canvas_rgb": (235, 242, 244),
        "grid_rgb": (36, 69, 86),
        "badge_fill_rgb": (249, 253, 254),
        "badge_outline_rgb": (36, 69, 86),
        "grid_width_px": 4,
    },
}

PATCH_FRAME_STYLES: Dict[str, Dict[str, Any]] = {
    "slate_cards": {
        "canvas_rgb": (238, 241, 245),
        "panel_outline_rgb": (58, 66, 78),
        "badge_fill_rgb": (255, 255, 255),
        "badge_outline_rgb": (44, 52, 65),
        "hole_fill_rgb": (18, 20, 24),
        "hole_outline_rgb": (255, 255, 255),
    },
    "warm_cards": {
        "canvas_rgb": (244, 240, 232),
        "panel_outline_rgb": (76, 64, 52),
        "badge_fill_rgb": (255, 252, 244),
        "badge_outline_rgb": (76, 64, 52),
        "hole_fill_rgb": (26, 23, 21),
        "hole_outline_rgb": (255, 250, 238),
    },
    "cool_cards": {
        "canvas_rgb": (235, 242, 244),
        "panel_outline_rgb": (42, 70, 83),
        "badge_fill_rgb": (249, 253, 254),
        "badge_outline_rgb": (42, 70, 83),
        "hole_fill_rgb": (15, 27, 35),
        "hole_outline_rgb": (245, 252, 255),
    },
}

PATCH_MODE_PLAIN = "plain"
PATCH_MODE_TRANSFORMED = "transformed"
PATCH_MODE_IRREGULAR = "irregular"
PATCH_MODES: Tuple[str, ...] = (PATCH_MODE_PLAIN, PATCH_MODE_TRANSFORMED, PATCH_MODE_IRREGULAR)
DEFAULT_OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")
ROTATED_TILE_LABELS: Tuple[str, ...] = tuple(chr(ord("A") + index) for index in range(9))


@dataclass(frozen=True)
class JigsawArtifacts:
    image: Image.Image
    option_bboxes: Dict[str, list[float]]
    answer_labels: Tuple[str, ...]
    display_order_content_indices: Tuple[int, ...]
    anchored_content_index: int
    display_grid_shape: Tuple[int, int]


@dataclass(frozen=True)
class JigsawArrangementArtifacts:
    image: Image.Image
    option_bboxes: Dict[str, list[float]]
    selected_option_bbox: list[float]
    selected_label: str
    selected_index: int
    option_permutations: Tuple[Tuple[int, ...], ...]
    tile_source_boxes: Tuple[Tuple[int, int, int, int], ...]
    correct_permutation: Tuple[int, ...]
    grid_shape: Tuple[int, int]
    option_layout_shape: Tuple[int, int]


@dataclass(frozen=True)
class RotatedTileArtifacts:
    image: Image.Image
    tile_bboxes: Dict[str, list[float]]
    selected_bbox: list[float]
    selected_label: str
    selected_index: int
    rotation_degrees: int
    grid_shape: Tuple[int, int]


@dataclass(frozen=True)
class PatchOptionArtifacts:
    image: Image.Image
    option_bboxes: Dict[str, list[float]]
    missing_region_bbox: list[float]
    selected_option_bbox: list[float]
    selected_label: str
    selected_index: int
    source_crop_box: Tuple[int, int, int, int]
    selected_transform: str
    option_grid_shape: Tuple[int, int]
    option_source_crop_boxes: Tuple[Tuple[int, int, int, int], ...] = ()
    candidate_crop_count: int = 0


def rgb(style: Mapping[str, Any], key: str) -> Tuple[int, int, int]:
    value = style[key]
    return (int(value[0]), int(value[1]), int(value[2]))


def style_trace(style: Mapping[str, Any]) -> Dict[str, Any]:
    return {str(key): list(value) if isinstance(value, tuple) else value for key, value in style.items()}


def sample_style(rng: Any, styles: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    style_id = str(rng.choice(tuple(styles)))
    return {"style_id": style_id, **dict(styles[style_id])}


def piece_crops(source: Image.Image, *, rows: int, cols: int) -> Tuple[Tuple[Image.Image, Tuple[int, int, int, int]], ...]:
    width, height = source.size
    pieces = []
    for row in range(int(rows)):
        for col in range(int(cols)):
            x0 = int(round(col * width / int(cols)))
            y0 = int(round(row * height / int(rows)))
            x1 = int(round((col + 1) * width / int(cols)))
            y1 = int(round((row + 1) * height / int(rows)))
            box = (x0, y0, x1, y1)
            pieces.append((source.crop(box).convert("RGB"), box))
    return tuple(pieces)


def non_identity_permutation(rng: Any, items: Sequence[int]) -> Tuple[int, ...]:
    identity = tuple(int(value) for value in items)
    order = list(identity)
    for _ in range(24):
        rng.shuffle(order)
        if tuple(order) != identity:
            return tuple(int(value) for value in order)
    if len(order) > 1:
        order[0], order[1] = order[1], order[0]
    return tuple(int(value) for value in order)


def option_content_order(
    *,
    option_permutation_index: int | None,
    rng: Any,
    remaining_content_indices: Sequence[int],
) -> Tuple[int, ...]:
    """Return a deterministic or sampled permutation of non-anchored pieces."""

    permutations_by_index = tuple(
        tuple(int(item) for item in perm)
        for perm in permutations(tuple(int(value) for value in remaining_content_indices))
    )
    if not permutations_by_index:
        return tuple()
    if option_permutation_index is not None:
        return permutations_by_index[abs(int(option_permutation_index)) % len(permutations_by_index)]
    if len(remaining_content_indices) > 2:
        return non_identity_permutation(rng, remaining_content_indices)
    order = list(tuple(int(item) for item in remaining_content_indices))
    rng.shuffle(order)
    return tuple(int(item) for item in order)


def _draw_blank_cell_marker(
    draw: ImageDraw.ImageDraw,
    *,
    bbox_xyxy: Tuple[int, int, int, int],
    style: Mapping[str, Any],
) -> None:
    x0, y0, x1, y1 = [int(value) for value in bbox_xyxy]
    mark = str(style.get("blank_marker", "x"))
    color = rgb(style, "blank_mark_rgb")
    if mark == "corners":
        length = max(18, int(min(x1 - x0, y1 - y0) * 0.16))
        inset = max(14, int(min(x1 - x0, y1 - y0) * 0.08))
        for sx, sy in (
            (x0 + inset, y0 + inset),
            (x1 - inset, y0 + inset),
            (x0 + inset, y1 - inset),
            (x1 - inset, y1 - inset),
        ):
            dx = length if sx < (x0 + x1) // 2 else -length
            dy = length if sy < (y0 + y1) // 2 else -length
            draw.line((sx, sy, sx + dx, sy), fill=color, width=3)
            draw.line((sx, sy, sx, sy + dy), fill=color, width=3)
        return
    if mark == "dots":
        radius = 4
        cx = int((x0 + x1) * 0.5)
        cy = int((y0 + y1) * 0.5)
        gap = max(16, int(min(x1 - x0, y1 - y0) * 0.10))
        for oy in (-gap, 0, gap):
            for ox in (-gap, 0, gap):
                draw.ellipse((cx + ox - radius, cy + oy - radius, cx + ox + radius, cy + oy + radius), fill=color)
        return
    draw.line((x0 + 18, y0 + 18, x1 - 18, y1 - 18), fill=color, width=2)
    draw.line((x0 + 18, y1 - 18, x1 - 18, y0 + 18), fill=color, width=2)


def compose_jigsaw_board(
    *,
    source_image: Image.Image,
    rows: int,
    cols: int,
    display_order: Sequence[int],
    board_style: Mapping[str, Any],
    label_font_family: str,
    render_margin: int = 30,
) -> JigsawArtifacts:
    """Compose a partially filled reconstruction board from an already-rendered image."""

    pieces = piece_crops(source_image.convert("RGB"), rows=int(rows), cols=int(cols))
    margin = int(render_margin)
    piece_w = max(int(piece.size[0]) for piece, _box in pieces)
    piece_h = max(int(piece.size[1]) for piece, _box in pieces)
    board_w = int(piece_w) * int(cols)
    board_h = int(piece_h) * int(rows)
    row_capacity = len(display_order)
    option_gap = 24
    label_h = 28
    option_w = min(int(piece_w), 260)
    option_h = max(40, int(round(float(piece_h) * float(option_w) / float(piece_w))))
    full_w = max(
        int(board_w) + 2 * margin,
        row_capacity * option_w + (row_capacity - 1) * option_gap + 2 * margin,
    )
    board_y = 46
    options_y = board_y + int(board_h) + 42
    full_h = options_y + label_h + option_h + margin
    canvas = Image.new("RGB", (int(full_w), int(full_h)), rgb(board_style, "canvas_rgb"))
    draw = ImageDraw.Draw(canvas)
    option_bboxes: Dict[str, list[float]] = {}
    labels = tuple(str(index + 1) for index in range(len(display_order)))
    content_to_label: Dict[int, str] = {}

    board_x = int((full_w - board_w) // 2)
    blank_fill = rgb(board_style, "blank_fill_rgb")
    blank_outline = rgb(board_style, "blank_outline_rgb")
    for row in range(int(rows)):
        for col in range(int(cols)):
            x0 = int(board_x + col * piece_w)
            y0 = int(board_y + row * piece_h)
            x1 = int(x0 + piece_w)
            y1 = int(y0 + piece_h)
            if row == 0 and col == 0:
                canvas.paste(pieces[0][0].convert("RGB"), (x0, y0))
            else:
                draw.rectangle((x0, y0, x1, y1), fill=blank_fill)
                _draw_blank_cell_marker(draw, bbox_xyxy=(x0, y0, x1, y1), style=board_style)
            draw.rectangle((x0, y0, x1, y1), outline=blank_outline, width=3)
    draw.rectangle(
        (board_x, board_y, board_x + board_w, board_y + board_h),
        outline=rgb(board_style, "board_outline_rgb"),
        width=3,
    )

    for option_index, content_index in enumerate(display_order):
        row_width = row_capacity * option_w + (row_capacity - 1) * option_gap
        x = int((full_w - row_width) // 2 + option_index * (option_w + option_gap))
        y = int(options_y)
        piece_image = pieces[int(content_index)][0].convert("RGB")
        piece_image = piece_image.resize((int(option_w), int(option_h)), Image.Resampling.LANCZOS)
        patch_x = x
        patch_y = y + label_h
        canvas.paste(piece_image, (patch_x, patch_y))
        label = labels[option_index]
        draw_label_badge(
            draw,
            label,
            (x, y, x + 36, y + 24),
            font_family=label_font_family,
            fill=rgb(board_style, "badge_fill_rgb"),
            outline=rgb(board_style, "badge_outline_rgb"),
        )
        option_bboxes[label] = bbox_list((patch_x, patch_y, patch_x + int(piece_image.width), patch_y + int(piece_image.height)))
        content_to_label[int(content_index)] = str(label)
    answer_labels = tuple(content_to_label[index] for index in range(1, len(pieces)))
    return JigsawArtifacts(
        image=canvas,
        option_bboxes=option_bboxes,
        answer_labels=answer_labels,
        display_order_content_indices=tuple(int(value) for value in display_order),
        anchored_content_index=0,
        display_grid_shape=(int(rows), int(cols)),
    )


def _jigsaw_distractor_permutations(
    *,
    rng: Any,
    piece_count: int,
    needed: int,
) -> Tuple[Tuple[int, ...], ...]:
    identity = tuple(range(int(piece_count)))
    candidates = [
        tuple(int(value) for value in perm)
        for perm in permutations(identity)
        if tuple(int(value) for value in perm) != identity
    ]
    if int(needed) > len(candidates):
        raise ValueError("not enough unique jigsaw distractor permutations")
    rng.shuffle(candidates)
    return tuple(candidates[: int(needed)])


def compose_jigsaw_arrangement_options(
    *,
    source_image: Image.Image,
    rows: int,
    cols: int,
    correct_index: int,
    rng: Any,
    board_style: Mapping[str, Any],
    label_font_family: str,
    labels: Sequence[str] = DEFAULT_OPTION_LABELS[:4],
    render_margin: int = 34,
    option_gap: int = 28,
    label_h: int = 32,
    option_columns: int = 2,
) -> JigsawArrangementArtifacts:
    """Compose lettered full-image jigsaw arrangement options."""

    row_count = int(rows)
    col_count = int(cols)
    if row_count < 1 or col_count < 1:
        raise ValueError("rows and cols must be positive")
    piece_count = row_count * col_count
    label_values = tuple(str(value) for value in labels)
    if len(label_values) < 2:
        raise ValueError("at least two option labels are required")
    if int(correct_index) < 0 or int(correct_index) >= len(label_values):
        raise ValueError("correct_index outside option label support")

    source_rgb = source_image.convert("RGB")
    pieces = piece_crops(source_rgb, rows=row_count, cols=col_count)
    correct_permutation = tuple(range(piece_count))
    distractors = _jigsaw_distractor_permutations(
        rng=rng,
        piece_count=piece_count,
        needed=len(label_values) - 1,
    )
    option_permutations: list[Tuple[int, ...]] = []
    distractor_index = 0
    for option_index in range(len(label_values)):
        if int(option_index) == int(correct_index):
            option_permutations.append(correct_permutation)
        else:
            option_permutations.append(tuple(distractors[distractor_index]))
            distractor_index += 1

    margin = int(render_margin)
    gap = int(option_gap)
    label_height = int(label_h)
    option_cols = max(1, int(option_columns))
    option_rows = (len(label_values) + option_cols - 1) // option_cols
    option_w = int(source_rgb.width)
    option_h = int(source_rgb.height)
    canvas_w = option_cols * option_w + (option_cols - 1) * gap + 2 * margin
    canvas_h = option_rows * (label_height + option_h) + (option_rows - 1) * gap + 2 * margin
    canvas = Image.new("RGB", (int(canvas_w), int(canvas_h)), rgb(board_style, "canvas_rgb"))
    draw = ImageDraw.Draw(canvas)
    tile_w = int(source_rgb.width // col_count)
    tile_h = int(source_rgb.height // row_count)
    option_bboxes: Dict[str, list[float]] = {}

    for option_index, permutation in enumerate(option_permutations):
        row = option_index // option_cols
        col = option_index % option_cols
        x0 = int(margin + col * (option_w + gap))
        y0 = int(margin + row * (label_height + option_h + gap))
        grid_x = x0
        grid_y = y0 + label_height
        label = label_values[option_index]
        draw_label_badge(
            draw,
            label,
            (x0, y0, x0 + 42, y0 + 25),
            font_family=label_font_family,
            fill=rgb(board_style, "badge_fill_rgb"),
            outline=rgb(board_style, "badge_outline_rgb"),
        )
        for slot_index, content_index in enumerate(permutation):
            slot_row = int(slot_index // col_count)
            slot_col = int(slot_index % col_count)
            paste_x = int(grid_x + slot_col * tile_w)
            paste_y = int(grid_y + slot_row * tile_h)
            canvas.paste(pieces[int(content_index)][0].convert("RGB"), (paste_x, paste_y))
        for grid_col in range(col_count + 1):
            x = int(grid_x + grid_col * tile_w)
            draw.line(
                (x, grid_y, x, grid_y + option_h),
                fill=rgb(board_style, "blank_outline_rgb"),
                width=2,
            )
        for grid_row in range(row_count + 1):
            y = int(grid_y + grid_row * tile_h)
            draw.line(
                (grid_x, y, grid_x + option_w, y),
                fill=rgb(board_style, "blank_outline_rgb"),
                width=2,
            )
        draw.rectangle(
            (grid_x, grid_y, grid_x + option_w, grid_y + option_h),
            outline=rgb(board_style, "board_outline_rgb"),
            width=3,
        )
        option_bboxes[label] = bbox_list((grid_x, grid_y, grid_x + option_w, grid_y + option_h))

    selected_label = label_values[int(correct_index)]
    return JigsawArrangementArtifacts(
        image=canvas,
        option_bboxes=option_bboxes,
        selected_option_bbox=list(option_bboxes[selected_label]),
        selected_label=str(selected_label),
        selected_index=int(correct_index),
        option_permutations=tuple(option_permutations),
        tile_source_boxes=tuple(tuple(int(coord) for coord in box) for _piece, box in pieces),
        correct_permutation=correct_permutation,
        grid_shape=(row_count, col_count),
        option_layout_shape=(int(option_rows), int(option_cols)),
    )


def rotation_delta(original: Image.Image, rotated: Image.Image) -> float:
    diff = ImageChops.difference(original.convert("RGB"), rotated.convert("RGB"))
    stat = ImageStat.Stat(diff)
    return float(sum(stat.mean) / max(1, len(stat.mean)))


def tile_is_usable(
    original: Image.Image,
    rotated: Image.Image,
    *,
    min_detail_score: float = 140.0,
    min_rotation_delta: float = 8.0,
) -> bool:
    return image_detail_score(original) >= float(min_detail_score) and rotation_delta(original, rotated) >= float(min_rotation_delta)


def compose_rotated_tile_grid(
    *,
    source_image: Image.Image,
    correct_index: int,
    rotation_degrees: int,
    grid_style: Mapping[str, Any],
    label_font_family: str,
    rows: int = 3,
    cols: int = 3,
    labels: Sequence[str] | None = None,
    render_margin: int = 30,
) -> RotatedTileArtifacts:
    """Compose a labeled grid with one rotated tile from an already-rendered image."""

    label_values = tuple(str(value) for value in (labels or ROTATED_TILE_LABELS[: int(rows) * int(cols)]))
    if len(label_values) != int(rows) * int(cols):
        raise ValueError("label count must match rows * cols")
    if int(correct_index) < 0 or int(correct_index) >= len(label_values):
        raise ValueError("correct_index is outside grid label support")

    source_rgb = source_image.convert("RGB")
    pieces = piece_crops(source_rgb, rows=int(rows), cols=int(cols))
    margin = int(render_margin)
    tile_w = int(source_rgb.width // int(cols))
    tile_h = int(source_rgb.height // int(rows))
    canvas_w = int(source_rgb.width) + 2 * margin
    canvas_h = int(source_rgb.height) + 2 * margin
    canvas = Image.new("RGB", (canvas_w, canvas_h), rgb(grid_style, "canvas_rgb"))
    draw = ImageDraw.Draw(canvas)
    tile_bboxes: Dict[str, list[float]] = {}
    grid_x = margin
    grid_y = margin

    for index, (piece, _source_box) in enumerate(pieces):
        row = int(index // int(cols))
        col = int(index % int(cols))
        x0 = int(grid_x + col * tile_w)
        y0 = int(grid_y + row * tile_h)
        label = str(label_values[index])
        patch = piece
        if int(index) == int(correct_index):
            patch = piece.rotate(-int(rotation_degrees), expand=False, resample=Image.Resampling.BICUBIC)
        canvas.paste(patch, (x0, y0))
        tile_bboxes[label] = bbox_list((x0, y0, x0 + int(tile_w), y0 + int(tile_h)))

    for col in range(int(cols) + 1):
        x = int(grid_x + col * tile_w)
        draw.line(
            (x, grid_y, x, grid_y + int(source_rgb.height)),
            fill=rgb(grid_style, "grid_rgb"),
            width=int(grid_style.get("grid_width_px", 3)),
        )
    for row in range(int(rows) + 1):
        y = int(grid_y + row * tile_h)
        draw.line(
            (grid_x, y, grid_x + int(source_rgb.width), y),
            fill=rgb(grid_style, "grid_rgb"),
            width=int(grid_style.get("grid_width_px", 3)),
        )

    for index, label in enumerate(label_values):
        row = int(index // int(cols))
        col = int(index % int(cols))
        x = int(grid_x + col * tile_w + 10)
        y = int(grid_y + row * tile_h + 9)
        draw_label_badge(
            draw,
            str(label),
            (x, y, x + 34, y + 28),
            font_family=label_font_family,
            fill=rgb(grid_style, "badge_fill_rgb"),
            outline=rgb(grid_style, "badge_outline_rgb"),
        )

    selected_label = str(label_values[int(correct_index)])
    return RotatedTileArtifacts(
        image=canvas,
        tile_bboxes=tile_bboxes,
        selected_bbox=list(tile_bboxes[selected_label]),
        selected_label=selected_label,
        selected_index=int(correct_index),
        rotation_degrees=int(rotation_degrees),
        grid_shape=(int(rows), int(cols)),
    )


def select_crop_box(
    source: Image.Image,
    rng: Any,
    *,
    patch_w: int,
    patch_h: int,
    crop_margin_px: int,
    avoid: Sequence[float] | None = None,
    candidate_crop_boxes: Sequence[Sequence[int]] | None = None,
) -> Tuple[int, int, int, int]:
    width, height = source.size
    margin = int(crop_margin_px)
    max_x0 = int(width) - int(patch_w) - margin
    max_y0 = int(height) - int(patch_h) - margin
    if max_x0 < margin or max_y0 < margin:
        raise ValueError("crop_margin_px leaves no feasible visual crop area")
    best_box = None
    best_score = -1.0
    avoid_cx = avoid_cy = None
    if avoid is not None:
        avoid_cx = 0.5 * (float(avoid[0]) + float(avoid[2]))
        avoid_cy = 0.5 * (float(avoid[1]) + float(avoid[3]))
    if candidate_crop_boxes is not None:
        ranked_candidates: list[Tuple[float, Tuple[int, int, int, int]]] = []
        seen: set[Tuple[int, int, int, int]] = set()
        for raw_box in candidate_crop_boxes:
            if len(raw_box) < 4:
                continue
            x0, y0, x1, y1 = [int(round(float(value))) for value in raw_box[:4]]
            box = (x0, y0, x1, y1)
            if box in seen:
                continue
            seen.add(box)
            if x0 < 0 or y0 < 0 or x1 > int(width) or y1 > int(height):
                continue
            if (x1 - x0) != int(patch_w) or (y1 - y0) != int(patch_h):
                continue
            if avoid_cx is not None and avoid_cy is not None:
                cx = 0.5 * (box[0] + box[2])
                cy = 0.5 * (box[1] + box[3])
                if abs(cx - avoid_cx) < 0.38 * width and abs(cy - avoid_cy) < 0.34 * height:
                    continue
            ranked_candidates.append((float(image_detail_score(source.crop(box))), box))
        if not ranked_candidates and avoid is not None:
            return select_crop_box(
                source,
                rng,
                patch_w=int(patch_w),
                patch_h=int(patch_h),
                crop_margin_px=int(crop_margin_px),
                avoid=None,
                candidate_crop_boxes=candidate_crop_boxes,
            )
        if not ranked_candidates:
            raise ValueError("candidate_crop_boxes did not contain a feasible visual crop")
        ranked_candidates.sort(key=lambda item: item[0], reverse=True)
        top_count = min(12, len(ranked_candidates))
        selected_index = int(rng.randint(0, top_count - 1))
        return tuple(int(value) for value in ranked_candidates[selected_index][1])
    for _attempt in range(220):
        x0 = int(rng.randint(margin, max_x0))
        y0 = int(rng.randint(margin, max_y0))
        box = (x0, y0, x0 + int(patch_w), y0 + int(patch_h))
        if avoid_cx is not None and avoid_cy is not None:
            cx = 0.5 * (box[0] + box[2])
            cy = 0.5 * (box[1] + box[3])
            if abs(cx - avoid_cx) < 0.38 * width and abs(cy - avoid_cy) < 0.34 * height:
                continue
        score = image_detail_score(source.crop(box))
        if score > best_score:
            best_score = float(score)
            best_box = box
        if score >= 220.0:
            return tuple(int(v) for v in box)
    if best_box is None and avoid is not None:
        return select_crop_box(
            source,
            rng,
            patch_w=int(patch_w),
            patch_h=int(patch_h),
            crop_margin_px=int(crop_margin_px),
            avoid=None,
            candidate_crop_boxes=None,
        )
    if best_box is None:
        raise ValueError("could not select visual crop")
    return tuple(int(v) for v in best_box)


def transform_patch(patch: Image.Image, rng: Any) -> Tuple[Image.Image, str]:
    transform = str(rng.choice(("rotate_180", "flip_horizontal", "flip_vertical")))
    if transform == "rotate_180":
        return patch.transpose(Image.Transpose.ROTATE_180), transform
    if transform == "flip_horizontal":
        return ImageOps.mirror(patch), transform
    return ImageOps.flip(patch), transform


def patch_difference_score(left: Image.Image, right: Image.Image) -> float:
    """Return a cheap mean-pixel difference between two same-size patches."""

    if left.size != right.size:
        right = ImageOps.pad(right.convert("RGB"), left.size, method=Image.Resampling.LANCZOS, color=(255, 255, 255))
    diff = ImageChops.difference(left.convert("RGB"), right.convert("RGB"))
    stat = ImageStat.Stat(diff)
    return float(sum(stat.mean) / max(1, len(stat.mean))) if stat.mean else 0.0


def draw_source_hole(source: Image.Image, *, box: Sequence[int], frame_style: Mapping[str, Any]) -> Image.Image:
    image = source.copy()
    draw = ImageDraw.Draw(image)
    x0, y0, x1, y1 = [int(v) for v in box]
    draw.rectangle(
        (x0, y0, x1, y1),
        fill=rgb(frame_style, "hole_fill_rgb"),
        outline=rgb(frame_style, "hole_outline_rgb"),
        width=3,
    )
    return image


def option_grid_shape(option_count: int) -> Tuple[int, int]:
    if int(option_count) == 4:
        return 2, 2
    columns = 3
    rows = (int(option_count) + columns - 1) // columns
    return int(rows), int(columns)


def compose_patch_options(
    *,
    source_image: Image.Image,
    rng: Any,
    patch_mode: str,
    correct_index: int,
    option_count: int,
    patch_size: Tuple[int, int],
    crop_margin_px: int,
    frame_style: Mapping[str, Any],
    label_font_family: str,
    labels: Sequence[str] = DEFAULT_OPTION_LABELS,
    render_margin: int = 30,
    candidate_crop_boxes: Sequence[Sequence[int]] | None = None,
    min_candidate_patch_difference: float = 7.5,
) -> PatchOptionArtifacts:
    """Compose source-with-hole plus patch options from an already-rendered image."""

    mode = str(patch_mode)
    if mode not in set(PATCH_MODES):
        raise ValueError(f"patch_mode must be one of {PATCH_MODES}")
    if int(option_count) < 2 or int(option_count) > len(labels):
        raise ValueError("option_count outside label support")
    if int(correct_index) < 0 or int(correct_index) >= int(option_count):
        raise ValueError("correct_index outside option range")

    source_rgb = source_image.convert("RGB")
    patch_w, patch_h = int(patch_size[0]), int(patch_size[1])
    hole_box = select_crop_box(
        source_rgb,
        rng,
        patch_w=patch_w,
        patch_h=patch_h,
        crop_margin_px=int(crop_margin_px),
        candidate_crop_boxes=candidate_crop_boxes,
    )
    correct_patch = source_rgb.crop(hole_box)
    correct_transform = "none"
    if mode == PATCH_MODE_TRANSFORMED:
        correct_patch, correct_transform = transform_patch(correct_patch, rng)

    options = []
    option_source_crop_boxes: list[Tuple[int, int, int, int]] = []
    used_crop_boxes: set[Tuple[int, int, int, int]] = {tuple(int(value) for value in hole_box)}
    for option_index in range(int(option_count)):
        if option_index == int(correct_index):
            options.append(correct_patch)
            option_source_crop_boxes.append(tuple(int(value) for value in hole_box))
            continue
        if mode == PATCH_MODE_PLAIN and candidate_crop_boxes is None and option_index == 0:
            distractor, _ = transform_patch(correct_patch, rng)
            distractor_box = tuple(int(value) for value in hole_box)
        else:
            best_distractor: Tuple[float, Image.Image, Tuple[int, int, int, int]] | None = None
            for _attempt in range(28):
                candidate_box = select_crop_box(
                    source_rgb,
                    rng,
                    patch_w=patch_w,
                    patch_h=patch_h,
                    crop_margin_px=int(crop_margin_px),
                    avoid=hole_box,
                    candidate_crop_boxes=candidate_crop_boxes,
                )
                if tuple(candidate_box) in used_crop_boxes:
                    continue
                candidate_patch = source_rgb.crop(candidate_box)
                delta = patch_difference_score(correct_patch, candidate_patch)
                if best_distractor is None or delta > best_distractor[0]:
                    best_distractor = (float(delta), candidate_patch, tuple(int(value) for value in candidate_box))
                if delta >= float(min_candidate_patch_difference):
                    break
            if best_distractor is None:
                candidate_box = select_crop_box(
                    source_rgb,
                    rng,
                    patch_w=patch_w,
                    patch_h=patch_h,
                    crop_margin_px=int(crop_margin_px),
                    avoid=None,
                    candidate_crop_boxes=candidate_crop_boxes,
                )
                best_distractor = (
                    patch_difference_score(correct_patch, source_rgb.crop(candidate_box)),
                    source_rgb.crop(candidate_box),
                    tuple(int(value) for value in candidate_box),
                )
            _delta, distractor, distractor_box = best_distractor
            used_crop_boxes.add(tuple(distractor_box))
        options.append(distractor)
        option_source_crop_boxes.append(tuple(int(value) for value in distractor_box))

    source_with_hole = draw_source_hole(source_rgb, box=hole_box, frame_style=frame_style)
    margin = int(render_margin)
    source_w, source_h = source_with_hole.size
    option_rows, row_capacity = option_grid_shape(int(option_count))
    option_gap = 24
    label_h = 30
    display_options = [option.convert("RGB") for option in options]
    option_w = int(patch_w)
    option_h = int(patch_h)
    full_w = max(
        source_w + 2 * margin,
        row_capacity * option_w + (row_capacity - 1) * option_gap + 2 * margin,
    )
    top_y = 58
    options_y = top_y + source_h + 54
    full_h = options_y + option_rows * (option_h + label_h + 18) + margin
    canvas = Image.new("RGB", (int(full_w), int(full_h)), rgb(frame_style, "canvas_rgb"))
    draw = ImageDraw.Draw(canvas)
    source_x = (full_w - source_w) // 2
    canvas.paste(source_with_hole, (source_x, top_y))
    draw.rectangle(
        (source_x, top_y, source_x + source_w, top_y + source_h),
        outline=rgb(frame_style, "panel_outline_rgb"),
        width=2,
    )
    draw_panel_label(draw, "Source", (source_x + 10, 18), size=22, font_family=label_font_family)
    option_bboxes: Dict[str, list[float]] = {}
    label_values = tuple(str(label) for label in labels[: int(option_count)])
    for index, option in enumerate(display_options):
        row = index // row_capacity
        col = index % row_capacity
        actual_cols = row_capacity if row < option_rows - 1 else int(option_count) - row * row_capacity
        row_width = actual_cols * option_w + (actual_cols - 1) * option_gap
        x = int((full_w - row_width) // 2 + col * (option_w + option_gap))
        y = int(options_y + row * (option_h + label_h + 18))
        patch_x = x
        patch_y = y + label_h
        draw.rectangle(
            (patch_x, patch_y, patch_x + option_w, patch_y + option_h),
            fill=(255, 255, 255),
            outline=rgb(frame_style, "panel_outline_rgb"),
            width=2,
        )
        if int(option.width) != option_w or int(option.height) != option_h:
            option = ImageOps.pad(option, (option_w, option_h), method=Image.Resampling.LANCZOS, color=(255, 255, 255))
        canvas.paste(option, (patch_x, patch_y))
        draw.rectangle(
            (patch_x, patch_y, patch_x + option_w, patch_y + option_h),
            outline=rgb(frame_style, "panel_outline_rgb"),
            width=2,
        )
        label = label_values[index]
        draw_label_badge(
            draw,
            label,
            (x, y, x + 42, y + 24),
            font_family=label_font_family,
            fill=rgb(frame_style, "badge_fill_rgb"),
            outline=rgb(frame_style, "badge_outline_rgb"),
        )
        option_bboxes[str(label)] = bbox_list((patch_x, patch_y, patch_x + option_w, patch_y + option_h))
    hole_bbox = bbox_list(hole_box, dx=source_x, dy=top_y)
    selected_label = str(label_values[int(correct_index)])
    return PatchOptionArtifacts(
        image=canvas,
        option_bboxes=option_bboxes,
        missing_region_bbox=hole_bbox,
        selected_option_bbox=list(option_bboxes[selected_label]),
        selected_label=selected_label,
        selected_index=int(correct_index),
        source_crop_box=tuple(int(value) for value in hole_box),
        selected_transform=correct_transform,
        option_grid_shape=(int(option_rows), int(row_capacity)),
        option_source_crop_boxes=tuple(tuple(int(coord) for coord in box) for box in option_source_crop_boxes),
        candidate_crop_count=len(tuple(candidate_crop_boxes or ())),
    )


__all__ = [
    "DEFAULT_OPTION_LABELS",
    "JIGSAW_BOARD_STYLES",
    "PATCH_FRAME_STYLES",
    "PATCH_MODE_IRREGULAR",
    "PATCH_MODE_PLAIN",
    "PATCH_MODE_TRANSFORMED",
    "PATCH_MODES",
    "ROTATED_GRID_STYLES",
    "ROTATED_TILE_LABELS",
    "JigsawArtifacts",
    "JigsawArrangementArtifacts",
    "PatchOptionArtifacts",
    "RotatedTileArtifacts",
    "compose_jigsaw_arrangement_options",
    "compose_jigsaw_board",
    "compose_patch_options",
    "compose_rotated_tile_grid",
    "draw_source_hole",
    "non_identity_permutation",
    "option_content_order",
    "option_grid_shape",
    "piece_crops",
    "patch_difference_score",
    "rgb",
    "rotation_delta",
    "sample_style",
    "select_crop_box",
    "style_trace",
    "tile_is_usable",
    "transform_patch",
]
