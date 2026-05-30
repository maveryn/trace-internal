"""Shared illustration jigsaw piece-order task."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageOps

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.visual_task_common import (
    bbox_list,
    draw_label_badge,
    render_source_illustration,
    sample_visual_label_font_trace,
)


TASK_ID = "task_illustrations__image_cutout_board__jigsaw_piece_order"
SCENE_ID = "image_cutout_board"
QUERY_ID = "jigsaw_piece_order"
BOARD_SHAPES: Tuple[str, ...] = ("board_1x3", "board_2x2")
BOARD_DIMS: Dict[str, Tuple[int, int]] = {
    "board_1x3": (1, 3),
    "board_2x2": (2, 2),
}
BOARD_ANCHOR_POSITIONS: Dict[str, str] = {
    "board_1x3": "left",
    "board_2x2": "top_left",
}
BOARD_ANSWER_POSITIONS: Dict[str, Tuple[str, ...]] = {
    "board_1x3": ("middle", "right"),
    "board_2x2": ("top_right", "bottom_left", "bottom_right"),
}
POSITION_TEXT: Dict[str, str] = {
    "left": "left",
    "middle": "middle",
    "right": "right",
    "top_left": "top-left",
    "top_right": "top-right",
    "bottom_left": "bottom-left",
    "bottom_right": "bottom-right",
}
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


@dataclass(frozen=True)
class _Defaults:
    source_width: int = 640
    source_height: int = 420
    render_margin: int = 30


@dataclass(frozen=True)
class _SampleSpec:
    board_shape: str
    rows: int
    cols: int
    option_permutation_index: Optional[int]
    source_sample_index: Optional[int]
    board_shape_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "visual")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _board_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("board_shape_support", group_default(_GEN_DEFAULTS, "board_shape_support", BOARD_SHAPES))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("board_shape_support must be a sequence")
    support = tuple(str(value) for value in raw if str(value) in set(BOARD_SHAPES))
    if not support:
        raise ValueError("board_shape_support resolved no supported board shapes")
    return tuple(dict.fromkeys(support))


def _sample_spec(*, params: Mapping[str, Any], instance_seed: int) -> _SampleSpec:
    support = _board_support(params)
    explicit = params.get("board_shape")
    option_permutation_index: Optional[int] = None
    source_sample_index: Optional[int] = None
    if explicit is not None:
        board_shape = str(explicit)
        if board_shape not in set(support):
            raise ValueError(f"board_shape must be one of {support}")
        probabilities = {board_shape: 1.0}
    else:
        index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:board_shape")
        board_shape = str(support[int(index) % len(support)])
        probability = 1.0 / float(len(support))
        probabilities = {str(value): probability for value in support}
    rows, cols = BOARD_DIMS[str(board_shape)]
    return _SampleSpec(
        board_shape=str(board_shape),
        rows=int(rows),
        cols=int(cols),
        option_permutation_index=option_permutation_index,
        source_sample_index=source_sample_index,
        board_shape_probabilities=dict(probabilities),
    )


def _position_text(position: str) -> str:
    return str(POSITION_TEXT.get(str(position), str(position).replace("_", "-")))


def _answer_position_text(positions: Sequence[str]) -> str:
    return ", ".join(_position_text(str(position)) for position in positions)


def _piece_crops(source: Image.Image, *, rows: int, cols: int) -> Tuple[Tuple[Image.Image, Tuple[int, int, int, int]], ...]:
    width, height = source.size
    pieces = []
    for row in range(int(rows)):
        for col in range(int(cols)):
            x0 = int(round(col * width / int(cols)))
            y0 = int(round(row * height / int(rows)))
            x1 = int(round((col + 1) * width / int(cols)))
            y1 = int(round((row + 1) * height / int(rows)))
            box = (x0, y0, x1, y1)
            pieces.append((source.crop(box), box))
    return tuple(pieces)


def _non_identity_permutation(rng, items: Sequence[int]) -> Tuple[int, ...]:
    identity = tuple(int(value) for value in items)
    order = list(identity)
    for _ in range(24):
        rng.shuffle(order)
        if tuple(order) != identity:
            return tuple(int(value) for value in order)
    if len(order) > 1:
        order[0], order[1] = order[1], order[0]
    return tuple(int(value) for value in order)


def _option_content_order(
    *,
    option_permutation_index: Optional[int],
    rng,
    remaining_content_indices: Sequence[int],
) -> Tuple[int, ...]:
    """Return a calibration-friendly permutation of the non-anchored pieces."""

    permutations_by_index = tuple(tuple(int(item) for item in perm) for perm in permutations(tuple(remaining_content_indices)))
    if not permutations_by_index:
        return tuple()
    if option_permutation_index is not None:
        return permutations_by_index[abs(int(option_permutation_index)) % len(permutations_by_index)]
    if len(remaining_content_indices) > 2:
        return _non_identity_permutation(rng, remaining_content_indices)
    order = list(tuple(int(item) for item in remaining_content_indices))
    rng.shuffle(order)
    return tuple(int(item) for item in order)


def _rgb(style: Mapping[str, Any], key: str) -> Tuple[int, int, int]:
    value = style[key]
    return (int(value[0]), int(value[1]), int(value[2]))


def _sample_jigsaw_board_style(rng) -> Dict[str, Any]:
    style_id = str(rng.choice(tuple(JIGSAW_BOARD_STYLES)))
    return {"style_id": style_id, **dict(JIGSAW_BOARD_STYLES[style_id])}


def _draw_blank_cell_marker(
    draw: ImageDraw.ImageDraw,
    *,
    bbox_xyxy: Tuple[int, int, int, int],
    style: Mapping[str, Any],
) -> None:
    x0, y0, x1, y1 = [int(value) for value in bbox_xyxy]
    mark = str(style.get("blank_marker", "x"))
    color = _rgb(style, "blank_mark_rgb")
    if mark == "corners":
        length = max(18, int(min(x1 - x0, y1 - y0) * 0.16))
        inset = max(14, int(min(x1 - x0, y1 - y0) * 0.08))
        for sx, sy in ((x0 + inset, y0 + inset), (x1 - inset, y0 + inset), (x0 + inset, y1 - inset), (x1 - inset, y1 - inset)):
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


def _compose_jigsaw_image(
    *,
    pieces: Sequence[Tuple[Image.Image, Tuple[int, int, int, int]]],
    display_order: Sequence[int],
    rows: int,
    cols: int,
    board_style: Mapping[str, Any],
    label_font_family: str,
) -> Tuple[Image.Image, Dict[str, list[float]], Tuple[str, ...]]:
    margin = int(_DEFAULTS.render_margin)
    piece_w = max(int(piece.size[0]) for piece, _box in pieces)
    piece_h = max(int(piece.size[1]) for piece, _box in pieces)
    board_w = int(piece_w) * int(cols)
    board_h = int(piece_h) * int(rows)
    row_capacity = len(display_order)
    option_gap = 24
    label_h = 28
    option_w = min(int(piece_w), 260)
    option_h = max(40, int(round(float(piece_h) * float(option_w) / float(piece_w))))
    full_w = max(int(board_w) + 2 * margin, row_capacity * option_w + (row_capacity - 1) * option_gap + 2 * margin)
    board_y = 46
    options_y = board_y + int(board_h) + 42
    full_h = options_y + label_h + option_h + margin
    canvas = Image.new("RGB", (int(full_w), int(full_h)), _rgb(board_style, "canvas_rgb"))
    draw = ImageDraw.Draw(canvas)
    option_bboxes: Dict[str, list[float]] = {}
    labels = tuple(str(index + 1) for index in range(len(display_order)))
    content_to_label: Dict[int, str] = {}

    board_x = int((full_w - board_w) // 2)
    blank_fill = _rgb(board_style, "blank_fill_rgb")
    blank_outline = _rgb(board_style, "blank_outline_rgb")
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
    draw.rectangle((board_x, board_y, board_x + board_w, board_y + board_h), outline=_rgb(board_style, "board_outline_rgb"), width=3)

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
            fill=_rgb(board_style, "badge_fill_rgb"),
            outline=_rgb(board_style, "badge_outline_rgb"),
        )
        option_bboxes[label] = bbox_list((patch_x, patch_y, patch_x + int(piece_image.width), patch_y + int(piece_image.height)))
        content_to_label[int(content_index)] = str(label)
    answer_labels = tuple(content_to_label[index] for index in range(1, len(pieces)))
    return canvas, option_bboxes, answer_labels


def _build_complexity(sample: _SampleSpec) -> TaskComplexity:
    piece_count = int(sample.rows) * int(sample.cols)
    piece_count_load = (int(piece_count) - 3) / 1.0
    board_shape_load = 1.0 if str(sample.board_shape) == "board_2x2" else 0.0
    score = min(1.0, 0.20 + 0.16 * float(piece_count))
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "piece_count_load": round(float(piece_count_load), 6),
            "board_shape_load": round(float(board_shape_load), 6),
        },
    )


@register_task
class IllustrationsVisualJigsawPieceOrderTask:
    """Order shuffled pieces to reconstruct a hidden 2x2 illustration."""

    task_id = TASK_ID
    domain = "illustrations"
    task_group = "visual"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        sample = _sample_spec(params=params, instance_seed=int(instance_seed))
        rng = spawn_rng(int(instance_seed), f"{TASK_ID}:layout")
        source_params = dict(params)
        source = render_source_illustration(
            params=source_params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            max_attempts=max_attempts,
        )
        source_image = ImageOps.fit(
            source.image.convert("RGB"),
            (
                int(params.get("source_width", group_default(_RENDER_DEFAULTS, "source_width", _DEFAULTS.source_width))),
                int(params.get("source_height", group_default(_RENDER_DEFAULTS, "source_height", _DEFAULTS.source_height))),
            ),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
        pieces = _piece_crops(source_image, rows=int(sample.rows), cols=int(sample.cols))
        remaining_content_indices = tuple(index for index in range(1, len(pieces)))
        style_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:style")
        board_style = _sample_jigsaw_board_style(style_rng)
        option_label_font = sample_visual_label_font_trace(
            task_id=TASK_ID,
            instance_seed=int(instance_seed),
            params=params,
            namespace_suffix="option_label_font",
            explicit_key="image_cutout_board_option_label_font_family",
            weights_key="image_cutout_board_option_label_font_family_weights",
        )
        display_order = _option_content_order(
            option_permutation_index=sample.option_permutation_index,
            rng=rng,
            remaining_content_indices=remaining_content_indices,
        )
        image, option_bboxes, answer_labels = _compose_jigsaw_image(
            pieces=pieces,
            display_order=display_order,
            rows=int(sample.rows),
            cols=int(sample.cols),
            board_style=board_style,
            label_font_family=str(option_label_font["font_family"]),
        )
        answer_value = " ".join(answer_labels)
        evidence_sequence = [option_bboxes[label] for label in answer_labels]
        answer_positions = BOARD_ANSWER_POSITIONS[str(sample.board_shape)]
        anchored_position = str(BOARD_ANCHOR_POSITIONS[str(sample.board_shape)])
        anchored_cell = f"{_position_text(anchored_position)} cell"
        empty_cell_order = _answer_position_text(answer_positions)
        example_suffix = str(len(display_order))

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_jigsaw_piece_order",
                "evidence_hint_jigsaw_piece_order",
                f"json_example_jigsaw_piece_order_{example_suffix}",
                f"json_example_answer_only_jigsaw_piece_order_{example_suffix}",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        slots = {
            "piece_count": len(display_order),
            "row_count": int(sample.rows),
            "col_count": int(sample.cols),
            "anchored_cell": anchored_cell,
            "empty_cell_order": empty_cell_order,
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_jigsaw_piece_order"]).format(
                piece_count=len(display_order),
                empty_cell_order=empty_cell_order,
            ),
            "evidence_hint": str(prompt_defaults["evidence_hint_jigsaw_piece_order"]),
            "json_example": str(prompt_defaults[f"json_example_jigsaw_piece_order_{example_suffix}"]),
            "json_example_answer_only": str(
                prompt_defaults[f"json_example_answer_only_jigsaw_piece_order_{example_suffix}"]
            ),
        }
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=QUERY_ID,
            slots=slots,
            instance_seed=int(instance_seed),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            preferred_mode="answer_and_evidence",
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        trace_payload = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "entities": {
                    "source_task_id": str(source.source_task_id),
                    "source_scene_id": str(source.source_scene_id),
                    "piece_options": [{"label": label, "bbox": bbox} for label, bbox in sorted(option_bboxes.items())],
                    "anchored_piece": {"position": anchored_position, "content_index": 0},
                    "source_image_shown": False,
                },
                "relations": {
                    "query_id": QUERY_ID,
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_id": QUERY_ID,
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "board_shape": str(sample.board_shape),
                    "rows": int(sample.rows),
                    "cols": int(sample.cols),
                    "piece_count": len(pieces),
                    "option_piece_count": len(display_order),
                    "anchored_position": anchored_position,
                    "answer_positions": list(answer_positions),
                    "board_shape_probabilities": dict(sample.board_shape_probabilities),
                    "source_task_probabilities": dict(source.source_probabilities),
                },
            },
            "render_spec": {
                "canvas_size": [int(image.width), int(image.height)],
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "style": {
                    "source_task_id": str(source.source_task_id),
                    "source_scene_id": str(source.source_scene_id),
                    "board_style": dict(board_style),
                    "option_label_font": dict(option_label_font),
                },
            },
            "render_map": {
                "option_bboxes_px": dict(option_bboxes),
                "display_order_content_indices": list(display_order),
                "display_grid_shape": [int(sample.rows), int(sample.cols)],
                "anchored_content_index": 0,
                "answer_positions": list(answer_positions),
            },
            "execution_trace": {
                "query_id": QUERY_ID,
                "answer_labels": list(answer_labels),
                "answer": str(answer_value),
                "source_task_id": str(source.source_task_id),
                "source_scene_id": str(source.source_scene_id),
            },
            "witness_symbolic": {
                "answer_labels": list(answer_labels),
                "answer": str(answer_value),
            },
            "projected_evidence": {"bbox_sequence": list(evidence_sequence)},
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="string", value=str(answer_value)),
            evidence_gt=TypedValue(type="bbox_sequence", value=list(evidence_sequence)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(sample),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
        )


__all__ = ["IllustrationsVisualJigsawPieceOrderTask"]
