"""Find the rotated tile in a 3x3 illustration grid."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageOps, ImageStat

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_scene_prompt_variants
from ..shared.visual_task_common import (
    bbox_list,
    draw_label_badge,
    image_detail_score,
    render_source_illustration,
    sample_visual_label_font_trace,
)


TASK_ID = "task_illustrations__image_cutout_board__rotated_tile_label"
SCENE_ID = "image_cutout_board"
QUERY_ID = "rotated_tile_label"
GRID_ROWS = 3
GRID_COLS = 3
OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G", "H", "I")
ROTATION_DEGREES: Tuple[int, ...] = (90, 180, 270)
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


@dataclass(frozen=True)
class _Defaults:
    source_size: int = 600
    render_margin: int = 30
    min_tile_detail_score: float = 140.0
    min_rotation_delta: float = 8.0


@dataclass(frozen=True)
class _SampleSpec:
    correct_index: int
    correct_label: str
    rotation_degrees: int
    correct_index_probabilities: Dict[str, float]
    rotation_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_SCENE_DEFAULTS = get_scene_defaults("illustrations", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _rotation_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    raw = params.get("rotation_degrees_support", group_default(_GEN_DEFAULTS, "rotation_degrees_support", ROTATION_DEGREES))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("rotation_degrees_support must be a sequence")
    support = tuple(int(value) for value in raw if int(value) in set(ROTATION_DEGREES))
    if not support:
        raise ValueError("rotation_degrees_support resolved no supported rotations")
    return tuple(dict.fromkeys(support))


def _sample_spec(*, params: Mapping[str, Any], instance_seed: int) -> _SampleSpec:
    support = tuple(range(len(OPTION_LABELS)))
    rotations = _rotation_support(params)
    base_index = abs(int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:cycle")))
    explicit_label = params.get("correct_label")
    explicit_index = params.get("correct_tile_index", params.get("correct_option_index"))
    if explicit_label is not None:
        label = str(explicit_label).upper()
        if label not in set(OPTION_LABELS):
            raise ValueError("correct_label is outside supported labels")
        correct_index = int(OPTION_LABELS.index(label))
        index_probs = {str(correct_index): 1.0}
    elif explicit_index is not None:
        correct_index = int(explicit_index)
        if correct_index not in set(support):
            raise ValueError("correct_tile_index/correct_option_index is outside supported labels")
        index_probs = {str(correct_index): 1.0}
    else:
        correct_index = int(support[base_index % len(support)])
        index_probs = dict(uniform_probability_map(support))
    explicit_rotation = params.get("rotation_degrees")
    if explicit_rotation is not None:
        rotation = int(explicit_rotation)
        if rotation not in set(rotations):
            raise ValueError("rotation_degrees is outside configured support")
        rotation_probs = {str(rotation): 1.0}
    else:
        rotation = int(rotations[(base_index + base_index // len(support)) % len(rotations)])
        rotation_probs = {str(value): 1.0 / float(len(rotations)) for value in rotations}
    return _SampleSpec(
        correct_index=int(correct_index),
        correct_label=str(OPTION_LABELS[int(correct_index)]),
        rotation_degrees=int(rotation),
        correct_index_probabilities=dict(index_probs),
        rotation_probabilities=dict(rotation_probs),
    )


def _piece_crops(source: Image.Image) -> Tuple[Tuple[Image.Image, Tuple[int, int, int, int]], ...]:
    width, height = source.size
    pieces = []
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            x0 = int(round(col * width / GRID_COLS))
            y0 = int(round(row * height / GRID_ROWS))
            x1 = int(round((col + 1) * width / GRID_COLS))
            y1 = int(round((row + 1) * height / GRID_ROWS))
            box = (x0, y0, x1, y1)
            pieces.append((source.crop(box).convert("RGB"), box))
    return tuple(pieces)


def _rotation_delta(original: Image.Image, rotated: Image.Image) -> float:
    diff = ImageChops.difference(original.convert("RGB"), rotated.convert("RGB"))
    stat = ImageStat.Stat(diff)
    return float(sum(stat.mean) / max(1, len(stat.mean)))


def _tile_is_usable(original: Image.Image, rotated: Image.Image, *, params: Mapping[str, Any]) -> bool:
    detail_threshold = float(
        params.get(
            "min_tile_detail_score",
            group_default(_RENDER_DEFAULTS, "min_tile_detail_score", _DEFAULTS.min_tile_detail_score),
        )
    )
    delta_threshold = float(
        params.get("min_rotation_delta", group_default(_RENDER_DEFAULTS, "min_rotation_delta", _DEFAULTS.min_rotation_delta))
    )
    return image_detail_score(original) >= detail_threshold and _rotation_delta(original, rotated) >= delta_threshold


def _source_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    source_params = dict(params)
    return source_params


def _rgb(style: Mapping[str, Any], key: str) -> Tuple[int, int, int]:
    value = style[key]
    return (int(value[0]), int(value[1]), int(value[2]))


def _style_trace(style: Mapping[str, Any]) -> Dict[str, Any]:
    return {str(key): list(value) if isinstance(value, tuple) else value for key, value in style.items()}


def _sample_rotated_grid_style(rng) -> Dict[str, Any]:
    style_id = str(rng.choice(tuple(ROTATED_GRID_STYLES)))
    return {"style_id": style_id, **dict(ROTATED_GRID_STYLES[style_id])}


def _compose_rotated_grid(
    *,
    source_image: Image.Image,
    pieces: Sequence[Tuple[Image.Image, Tuple[int, int, int, int]]],
    sample: _SampleSpec,
    params: Mapping[str, Any],
    grid_style: Mapping[str, Any],
    label_font_family: str,
) -> Tuple[Image.Image, Dict[str, list[float]], list[float]]:
    margin = int(params.get("render_margin", group_default(_RENDER_DEFAULTS, "render_margin", _DEFAULTS.render_margin)))
    tile_w = int(source_image.width // GRID_COLS)
    tile_h = int(source_image.height // GRID_ROWS)
    canvas_w = int(source_image.width) + 2 * int(margin)
    canvas_h = int(source_image.height) + 2 * int(margin)
    canvas = Image.new("RGB", (canvas_w, canvas_h), _rgb(grid_style, "canvas_rgb"))
    draw = ImageDraw.Draw(canvas)
    tile_bboxes: Dict[str, list[float]] = {}
    grid_x = int(margin)
    grid_y = int(margin)

    for index, (piece, _source_box) in enumerate(pieces):
        row = int(index // GRID_COLS)
        col = int(index % GRID_COLS)
        x0 = int(grid_x + col * tile_w)
        y0 = int(grid_y + row * tile_h)
        label = str(OPTION_LABELS[index])
        patch = piece
        if int(index) == int(sample.correct_index):
            patch = piece.rotate(-int(sample.rotation_degrees), expand=False, resample=Image.Resampling.BICUBIC)
        canvas.paste(patch, (x0, y0))
        tile_bboxes[label] = bbox_list((x0, y0, x0 + int(tile_w), y0 + int(tile_h)))

    for col in range(GRID_COLS + 1):
        x = int(grid_x + col * tile_w)
        draw.line(
            (x, grid_y, x, grid_y + int(source_image.height)),
            fill=_rgb(grid_style, "grid_rgb"),
            width=int(grid_style.get("grid_width_px", 3)),
        )
    for row in range(GRID_ROWS + 1):
        y = int(grid_y + row * tile_h)
        draw.line(
            (grid_x, y, grid_x + int(source_image.width), y),
            fill=_rgb(grid_style, "grid_rgb"),
            width=int(grid_style.get("grid_width_px", 3)),
        )

    for index, label in enumerate(OPTION_LABELS):
        row = int(index // GRID_COLS)
        col = int(index % GRID_COLS)
        x = int(grid_x + col * tile_w + 10)
        y = int(grid_y + row * tile_h + 9)
        draw_label_badge(
            draw,
            str(label),
            (x, y, x + 34, y + 28),
            font_family=label_font_family,
            fill=_rgb(grid_style, "badge_fill_rgb"),
            outline=_rgb(grid_style, "badge_outline_rgb"),
        )

    return canvas, tile_bboxes, list(tile_bboxes[str(sample.correct_label)])




@register_task
class IllustrationsImageCutoutBoardRotatedTileLabelTask:
    """Choose the single 3x3 tile that was rotated in place."""

    task_id = TASK_ID
    domain = "illustrations"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        sample: _SampleSpec | None = None
        source = None
        image: Image.Image | None = None
        tile_bboxes: Dict[str, list[float]] = {}
        annotation_value: list[list[float]] = []
        for attempt in range(max(1, int(max_attempts))):
            try:
                sample = _sample_spec(params=params, instance_seed=int(instance_seed))
                source = render_source_illustration(
                    params=_source_params(params),
                    gen_defaults=_GEN_DEFAULTS,
                    instance_seed=int(instance_seed) + int(attempt),
                    task_id=TASK_ID,
                    max_attempts=max_attempts,
                )
                source_size = int(
                    params.get("source_size", group_default(_RENDER_DEFAULTS, "source_size", _DEFAULTS.source_size))
                )
                source_image = ImageOps.fit(
                    source.image.convert("RGB"),
                    (int(source_size), int(source_size)),
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5),
                )
                pieces = _piece_crops(source_image)
                original = pieces[int(sample.correct_index)][0]
                rotated = original.rotate(
                    -int(sample.rotation_degrees),
                    expand=False,
                    resample=Image.Resampling.BICUBIC,
                )
                if not _tile_is_usable(original, rotated, params=params):
                    raise ValueError("rotated tile is not visually distinctive enough")
                style_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:style", int(attempt))
                grid_style = _sample_rotated_grid_style(style_rng)
                tile_label_font = sample_visual_label_font_trace(
                    task_id=TASK_ID,
                    instance_seed=int(instance_seed),
                    params=params,
                    namespace_suffix="tile_label_font",
                    explicit_key="image_cutout_board_tile_label_font_family",
                    weights_key="image_cutout_board_tile_label_font_family_weights",
                )
                image, tile_bboxes, annotation_box = _compose_rotated_grid(
                    source_image=source_image,
                    pieces=pieces,
                    sample=sample,
                    params=params,
                    grid_style=grid_style,
                    label_font_family=str(tile_label_font["font_family"]),
                )
                annotation_value = [list(annotation_box)]
                break
            except Exception as exc:  # pragma: no cover
                last_error = exc
                sample = None
                source = None
                image = None
                tile_bboxes = {}
                annotation_value = []
        if sample is None or source is None or image is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_rotated_tile_label",
                "annotation_hint_rotated_tile_label",
                "json_example_rotated_tile_label",
                "json_example_answer_only_rotated_tile_label",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        option_labels = ", ".join(OPTION_LABELS)
        slots = {
            "row_count": GRID_ROWS,
            "col_count": GRID_COLS,
            "option_labels": option_labels,
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_rotated_tile_label"]).format(option_labels=option_labels),
            "annotation_hint": str(prompt_defaults["annotation_hint_rotated_tile_label"]),
            "json_example": str(prompt_defaults["json_example_rotated_tile_label"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_rotated_tile_label"]),
        }
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=QUERY_ID,
            slots=slots,
            instance_seed=int(instance_seed),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            preferred_mode="answer_and_annotation",
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        tile_records = [
            {
                "label": str(label),
                "tile_index": int(index),
                "row": int(index // GRID_COLS),
                "col": int(index % GRID_COLS),
                "bbox": list(tile_bboxes[str(label)]),
                "is_rotated": bool(index == int(sample.correct_index)),
            }
            for index, label in enumerate(OPTION_LABELS)
        ]
        trace_payload = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "entities": {
                    "source_task_id": str(source.source_task_id),
                    "source_scene_id": str(source.source_scene_id),
                    "tile_options": tile_records,
                    "rotated_tile": {
                        "label": str(sample.correct_label),
                        "tile_index": int(sample.correct_index),
                        "rotation_degrees": int(sample.rotation_degrees),
                        "bbox": list(tile_bboxes[str(sample.correct_label)]),
                    },
                    "source_image_shown": True,
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
                    "row_count": GRID_ROWS,
                    "col_count": GRID_COLS,
                    "option_labels": list(OPTION_LABELS),
                    "correct_tile_index": int(sample.correct_index),
                    "correct_label": str(sample.correct_label),
                    "rotation_degrees": int(sample.rotation_degrees),
                    "correct_index_probabilities": dict(sample.correct_index_probabilities),
                    "rotation_probabilities": dict(sample.rotation_probabilities),
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
                    "grid_shape": [GRID_ROWS, GRID_COLS],
                    "grid_style": _style_trace(grid_style),
                    "tile_label_font": dict(tile_label_font),
                },
            },
            "render_map": {
                "tile_bboxes_px": dict(tile_bboxes),
                "correct_option_label": str(sample.correct_label),
                "correct_tile_index": int(sample.correct_index),
                "rotation_degrees": int(sample.rotation_degrees),
                "grid_shape": [GRID_ROWS, GRID_COLS],
            },
            "execution_trace": {
                "query_id": QUERY_ID,
                "answer": str(sample.correct_label),
                "correct_tile_index": int(sample.correct_index),
                "rotation_degrees": int(sample.rotation_degrees),
                "source_task_id": str(source.source_task_id),
                "source_scene_id": str(source.source_scene_id),
            },
            "witness_symbolic": {
                "answer": str(sample.correct_label),
                "correct_tile_index": int(sample.correct_index),
                "rotation_degrees": int(sample.rotation_degrees),
            },
            "projected_annotation": {"bbox_set": list(annotation_value)},
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="option_letter", value=str(sample.correct_label)),
            annotation_gt=TypedValue(type="bbox_set", value=list(annotation_value)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
        )


__all__ = ["IllustrationsImageCutoutBoardRotatedTileLabelTask", "TASK_ID", "SCENE_ID", "QUERY_ID", "OPTION_LABELS"]
