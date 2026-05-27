"""Find the rotated tile in a 3x3 illustration grid."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageOps, ImageStat

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.visual_task_common import bbox_list, default_font, image_detail_score, render_source_illustration


TASK_ID = "task_illustrations__image_cutout_board__rotated_tile_label"
SCENE_ID = "image_cutout_board"
QUERY_ID = "rotated_tile_label"
GRID_ROWS = 3
GRID_COLS = 3
OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G", "H", "I")
ROTATION_DEGREES: Tuple[int, ...] = (90, 180, 270)


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
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "visual")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
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


def _compose_rotated_grid(
    *,
    source_image: Image.Image,
    pieces: Sequence[Tuple[Image.Image, Tuple[int, int, int, int]]],
    sample: _SampleSpec,
    params: Mapping[str, Any],
) -> Tuple[Image.Image, Dict[str, list[float]], list[float]]:
    margin = int(params.get("render_margin", group_default(_RENDER_DEFAULTS, "render_margin", _DEFAULTS.render_margin)))
    tile_w = int(source_image.width // GRID_COLS)
    tile_h = int(source_image.height // GRID_ROWS)
    canvas_w = int(source_image.width) + 2 * int(margin)
    canvas_h = int(source_image.height) + 2 * int(margin)
    canvas = Image.new("RGB", (canvas_w, canvas_h), (238, 241, 245))
    draw = ImageDraw.Draw(canvas)
    label_font = default_font(18, bold=True)
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
        draw.line((x, grid_y, x, grid_y + int(source_image.height)), fill=(33, 39, 49), width=3)
    for row in range(GRID_ROWS + 1):
        y = int(grid_y + row * tile_h)
        draw.line((grid_x, y, grid_x + int(source_image.width), y), fill=(33, 39, 49), width=3)

    for index, label in enumerate(OPTION_LABELS):
        row = int(index // GRID_COLS)
        col = int(index % GRID_COLS)
        x = int(grid_x + col * tile_w + 10)
        y = int(grid_y + row * tile_h + 9)
        draw.rounded_rectangle((x, y, x + 34, y + 28), radius=5, fill=(255, 255, 255), outline=(33, 39, 49), width=2)
        draw.text((x + 10, y + 3), str(label), fill=(18, 25, 35), font=label_font)

    return canvas, tile_bboxes, list(tile_bboxes[str(sample.correct_label)])


def _build_complexity(sample: _SampleSpec) -> TaskComplexity:
    rotation_load = {90: 0.72, 180: 0.62, 270: 0.72}.get(int(sample.rotation_degrees), 0.70)
    score = 0.42 + 0.30 * rotation_load + 0.28 * (len(OPTION_LABELS) / 9.0)
    return TaskComplexity(
        complexity_score=round(min(1.0, float(score)), 6),
        complexity_components={
            "grid_rows": GRID_ROWS,
            "grid_cols": GRID_COLS,
            "option_count": len(OPTION_LABELS),
            "rotation_degrees": int(sample.rotation_degrees),
            "rotated_tile_index": int(sample.correct_index),
        },
    )


@register_task
class IllustrationsVisualRotatedTileLabelTask:
    """Choose the single 3x3 tile that was rotated in place."""

    task_id = TASK_ID
    domain = "illustrations"
    task_group = "visual"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        sample: _SampleSpec | None = None
        source = None
        image: Image.Image | None = None
        tile_bboxes: Dict[str, list[float]] = {}
        evidence_value: list[list[float]] = []
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
                image, tile_bboxes, evidence_box = _compose_rotated_grid(
                    source_image=source_image,
                    pieces=pieces,
                    sample=sample,
                    params=params,
                )
                evidence_value = [list(evidence_box)]
                break
            except Exception as exc:  # pragma: no cover
                last_error = exc
                sample = None
                source = None
                image = None
                tile_bboxes = {}
                evidence_value = []
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
                "evidence_hint_rotated_tile_label",
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
            "evidence_hint": str(prompt_defaults["evidence_hint_rotated_tile_label"]),
            "json_example": str(prompt_defaults["json_example_rotated_tile_label"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_rotated_tile_label"]),
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
            "projected_evidence": {"bbox_set": list(evidence_value)},
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="option_letter", value=str(sample.correct_label)),
            evidence_gt=TypedValue(type="bbox_set", value=list(evidence_value)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(sample),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
        )


__all__ = ["IllustrationsVisualRotatedTileLabelTask", "TASK_ID", "SCENE_ID", "QUERY_ID", "OPTION_LABELS"]
