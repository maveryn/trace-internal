"""Shared illustration missing-patch option task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

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
    default_font,
    draw_panel_label,
    fit_source_image,
    image_detail_score,
    render_source_illustration,
)


TASK_ID = "task_illustrations__missing_patch__missing_patch_label"
SCENE_ID = "missing_patch"
QUERY_ID = "missing_patch_label"
PATCH_MODES: Tuple[str, ...] = ("plain_patch_label", "transformed_patch_label", "irregular_cutout_patch_label")
OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")


@dataclass(frozen=True)
class _Defaults:
    source_width: int = 640
    source_height: int = 420
    patch_width_min: int = 128
    patch_width_max: int = 176
    patch_height_min: int = 100
    patch_height_max: int = 142
    crop_margin_px: int = 48
    option_count: int = 6
    render_margin: int = 30


@dataclass(frozen=True)
class _SampleSpec:
    patch_mode: str
    correct_index: int
    patch_mode_probabilities: Dict[str, float]
    correct_index_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "visual")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _patch_mode_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("patch_mode_support", group_default(_GEN_DEFAULTS, "patch_mode_support", PATCH_MODES))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("patch_mode_support must be a sequence")
    support = tuple(str(value) for value in raw if str(value) in set(PATCH_MODES))
    if not support:
        raise ValueError("patch_mode_support resolved no supported patch modes")
    return tuple(dict.fromkeys(support))


def _sample_spec(*, params: Mapping[str, Any], instance_seed: int) -> _SampleSpec:
    support = _patch_mode_support(params)
    explicit_mode = params.get("patch_mode", params.get("query_variant"))
    if explicit_mode is not None:
        patch_mode = str(explicit_mode)
        if patch_mode not in set(support):
            raise ValueError(f"patch_mode must be one of {support}")
        mode_probabilities = {patch_mode: 1.0}
    else:
        mode_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:patch_mode")
        patch_mode = str(support[int(mode_index) % len(support)])
        probability = 1.0 / float(len(support))
        mode_probabilities = {str(value): probability for value in support}

    option_count = int(params.get("option_count", group_default(_GEN_DEFAULTS, "option_count", _DEFAULTS.option_count)))
    option_count = max(2, min(len(OPTION_LABELS), option_count))
    explicit_index = params.get("correct_option_index")
    if explicit_index is not None:
        correct_index = int(explicit_index)
        if correct_index < 0 or correct_index >= option_count:
            raise ValueError("correct_option_index outside option range")
        index_probabilities = {str(correct_index): 1.0}
    else:
        raw_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:correct_option")
        correct_index = int(raw_index) % int(option_count)
        index_probabilities = {str(index): 1.0 / float(option_count) for index in range(option_count)}
    return _SampleSpec(
        patch_mode=str(patch_mode),
        correct_index=int(correct_index),
        patch_mode_probabilities=dict(mode_probabilities),
        correct_index_probabilities=dict(index_probabilities),
    )


def _patch_size(params: Mapping[str, Any], rng) -> Tuple[int, int]:
    width_min = int(params.get("patch_width_min", group_default(_GEN_DEFAULTS, "patch_width_min", _DEFAULTS.patch_width_min)))
    width_max = int(params.get("patch_width_max", group_default(_GEN_DEFAULTS, "patch_width_max", _DEFAULTS.patch_width_max)))
    height_min = int(params.get("patch_height_min", group_default(_GEN_DEFAULTS, "patch_height_min", _DEFAULTS.patch_height_min)))
    height_max = int(params.get("patch_height_max", group_default(_GEN_DEFAULTS, "patch_height_max", _DEFAULTS.patch_height_max)))
    if width_min < 24 or width_max < width_min or height_min < 24 or height_max < height_min:
        raise ValueError("invalid patch size range")
    return int(rng.randint(width_min, width_max)), int(rng.randint(height_min, height_max))


def _crop_margin(params: Mapping[str, Any]) -> int:
    margin = int(params.get("crop_margin_px", group_default(_GEN_DEFAULTS, "crop_margin_px", _DEFAULTS.crop_margin_px)))
    if margin < 0:
        raise ValueError("crop_margin_px must be non-negative")
    return int(margin)


def _select_crop_box(source: Image.Image, rng, *, patch_w: int, patch_h: int, crop_margin_px: int, avoid: Sequence[float] | None = None) -> Tuple[int, int, int, int]:
    width, height = source.size
    margin = int(crop_margin_px)
    max_x0 = int(width) - int(patch_w) - margin
    max_y0 = int(height) - int(patch_h) - margin
    if max_x0 < margin or max_y0 < margin:
        raise ValueError("crop_margin_px leaves no feasible missing-patch crop area")
    best_box = None
    best_score = -1.0
    avoid_cx = avoid_cy = None
    if avoid is not None:
        avoid_cx = 0.5 * (float(avoid[0]) + float(avoid[2]))
        avoid_cy = 0.5 * (float(avoid[1]) + float(avoid[3]))
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
        return _select_crop_box(
            source,
            rng,
            patch_w=int(patch_w),
            patch_h=int(patch_h),
            crop_margin_px=int(crop_margin_px),
            avoid=None,
        )
    if best_box is None:
        raise ValueError("could not select missing-patch crop")
    return tuple(int(v) for v in best_box)


def _transform_patch(patch: Image.Image, rng) -> Tuple[Image.Image, str]:
    transform = str(rng.choice(("rotate_90", "rotate_180", "rotate_270", "flip_horizontal", "flip_vertical")))
    if transform == "rotate_90":
        return patch.transpose(Image.Transpose.ROTATE_90), transform
    if transform == "rotate_180":
        return patch.transpose(Image.Transpose.ROTATE_180), transform
    if transform == "rotate_270":
        return patch.transpose(Image.Transpose.ROTATE_270), transform
    if transform == "flip_horizontal":
        return ImageOps.mirror(patch), transform
    return ImageOps.flip(patch), transform


def _draw_hole(source: Image.Image, *, box: Sequence[int], patch_mode: str) -> Image.Image:
    image = source.copy()
    draw = ImageDraw.Draw(image)
    x0, y0, x1, y1 = [int(v) for v in box]
    draw.rectangle((x0, y0, x1, y1), fill=(18, 20, 24), outline=(255, 255, 255), width=3)
    return image


def _option_grid_shape(option_count: int) -> Tuple[int, int]:
    if int(option_count) == 4:
        return 2, 2
    columns = 3
    rows = (int(option_count) + int(columns) - 1) // int(columns)
    return int(rows), int(columns)


def _compose_options(
    *,
    source_with_hole: Image.Image,
    options: Sequence[Image.Image],
    correct_index: int,
    hole_box: Sequence[int],
) -> Tuple[Image.Image, Dict[str, list[float]], list[float]]:
    margin = int(_DEFAULTS.render_margin)
    source_w, source_h = source_with_hole.size
    option_count = len(options)
    option_rows, row_capacity = _option_grid_shape(int(option_count))
    option_gap = 24
    label_h = 30
    display_options = [option.convert("RGB") for option in options]
    option_w = max(int(option.width) for option in display_options)
    option_h = max(int(option.height) for option in display_options)
    full_w = max(source_w + 2 * margin, row_capacity * option_w + (row_capacity - 1) * option_gap + 2 * margin)
    top_y = 58
    options_y = top_y + source_h + 54
    full_h = options_y + option_rows * (option_h + label_h + 18) + margin
    canvas = Image.new("RGB", (int(full_w), int(full_h)), (238, 241, 245))
    draw = ImageDraw.Draw(canvas)
    source_x = (full_w - source_w) // 2
    canvas.paste(source_with_hole, (source_x, top_y))
    draw.rectangle((source_x, top_y, source_x + source_w, top_y + source_h), outline=(58, 66, 78), width=2)
    draw_panel_label(draw, "Source", (source_x + 10, 18), size=22)
    label_font = default_font(20, bold=True)
    option_bboxes: Dict[str, list[float]] = {}
    labels = OPTION_LABELS[:option_count]
    for index, option in enumerate(display_options):
        row = index // row_capacity
        col = index % row_capacity
        actual_cols = row_capacity if row < option_rows - 1 else option_count - row * row_capacity
        row_width = actual_cols * option_w + (actual_cols - 1) * option_gap
        x = int((full_w - row_width) // 2 + col * (option_w + option_gap))
        y = int(options_y + row * (option_h + label_h + 18))
        patch_x = x + (option_w - int(option.width)) // 2
        patch_y = y + label_h + (option_h - int(option.height)) // 2
        canvas.paste(option, (patch_x, patch_y))
        label = labels[index]
        draw.rounded_rectangle((x, y, x + 42, y + 24), radius=5, fill=(255, 255, 255), outline=(44, 52, 65), width=2)
        draw.text((x + 11, y + 1), label, fill=(18, 25, 35), font=label_font)
        option_bboxes[str(label)] = bbox_list((patch_x, patch_y, patch_x + int(option.width), patch_y + int(option.height)))
    hole_bbox = bbox_list(hole_box, dx=source_x, dy=top_y)
    return canvas, option_bboxes, hole_bbox


def _build_complexity(sample: _SampleSpec) -> TaskComplexity:
    mode_load = {"plain_patch_label": 0.35, "transformed_patch_label": 0.68, "irregular_cutout_patch_label": 0.55}[str(sample.patch_mode)]
    return TaskComplexity(
        complexity_score=round(float(0.34 + 0.48 * mode_load), 6),
        complexity_components={
            "patch_mode": str(sample.patch_mode),
            "mode_load": round(float(mode_load), 6),
            "option_count": int(_DEFAULTS.option_count),
        },
    )


@register_task
class IllustrationsVisualMissingPatchLabelTask:
    """Choose the patch option that completes a source illustration."""

    task_id = TASK_ID
    domain = "illustrations"
    task_group = "visual"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        sample = _sample_spec(params=params, instance_seed=int(instance_seed))
        rng = spawn_rng(int(instance_seed), f"{TASK_ID}:layout")
        source = render_source_illustration(
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            max_attempts=max_attempts,
        )
        source_image = fit_source_image(
            source.image,
            width=int(params.get("source_width", group_default(_RENDER_DEFAULTS, "source_width", _DEFAULTS.source_width))),
            height=int(params.get("source_height", group_default(_RENDER_DEFAULTS, "source_height", _DEFAULTS.source_height))),
        )
        patch_w, patch_h = _patch_size(params, rng)
        crop_margin_px = _crop_margin(params)
        hole_box = _select_crop_box(source_image, rng, patch_w=int(patch_w), patch_h=int(patch_h), crop_margin_px=int(crop_margin_px))
        correct_patch = source_image.crop(hole_box)
        correct_transform = "none"
        if str(sample.patch_mode) == "transformed_patch_label":
            correct_patch, correct_transform = _transform_patch(correct_patch, rng)
        option_count = int(params.get("option_count", group_default(_GEN_DEFAULTS, "option_count", _DEFAULTS.option_count)))
        option_count = max(2, min(len(OPTION_LABELS), option_count))
        options = []
        for option_index in range(option_count):
            if option_index == int(sample.correct_index):
                options.append(correct_patch)
                continue
            distractor_box = _select_crop_box(
                source_image,
                rng,
                patch_w=int(patch_w),
                patch_h=int(patch_h),
                crop_margin_px=int(crop_margin_px),
                avoid=hole_box,
            )
            distractor = source_image.crop(distractor_box)
            if str(sample.patch_mode) == "plain_patch_label" and option_index == 0:
                distractor, _ = _transform_patch(correct_patch, rng)
            options.append(distractor)
        source_with_hole = _draw_hole(source_image, box=hole_box, patch_mode=str(sample.patch_mode))
        image, option_bboxes, hole_bbox = _compose_options(
            source_with_hole=source_with_hole,
            options=options,
            correct_index=int(sample.correct_index),
            hole_box=hole_box,
        )
        labels = OPTION_LABELS[:option_count]
        answer_label = labels[int(sample.correct_index)]
        evidence_boxes = [hole_bbox, option_bboxes[str(answer_label)]]

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_missing_patch_label",
                "evidence_hint_missing_patch_label",
                "json_example_missing_patch_label",
                "json_example_answer_only_missing_patch_label",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        slots = {
            "option_labels": ", ".join(labels),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_missing_patch_label"]).format(option_labels=", ".join(labels)),
            "evidence_hint": str(prompt_defaults["evidence_hint_missing_patch_label"]),
            "json_example": str(prompt_defaults["json_example_missing_patch_label"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_missing_patch_label"]),
        }
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(sample.patch_mode),
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
                    "hole_bbox": list(hole_bbox),
                    "options": [{"label": label, "bbox": option_bboxes[str(label)]} for label in labels],
                },
                "relations": {
                    "query_variant": "default",
                    "query_id": str(sample.patch_mode),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_variant": "default",
                "query_id": str(sample.patch_mode),
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "patch_mode": str(sample.patch_mode),
                    "option_count": int(option_count),
                    "correct_option_index": int(sample.correct_index),
                    "correct_label": str(answer_label),
                    "crop_margin_px": int(crop_margin_px),
                    "patch_mode_probabilities": dict(sample.patch_mode_probabilities),
                    "correct_index_probabilities": dict(sample.correct_index_probabilities),
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
                    "correct_transform": str(correct_transform),
                    "panel_grid": list(_option_grid_shape(int(option_count))),
                },
            },
            "render_map": {
                "hole_bbox_px": list(hole_bbox),
                "option_bboxes_px": dict(option_bboxes),
                "correct_option_label": str(answer_label),
            },
            "execution_trace": {
                "query_variant": "default",
                "query_id": str(sample.patch_mode),
                "answer": str(answer_label),
                "correct_option_label": str(answer_label),
                "correct_transform": str(correct_transform),
                "source_task_id": str(source.source_task_id),
                "source_scene_id": str(source.source_scene_id),
            },
            "witness_symbolic": {
                "answer": str(answer_label),
                "correct_option_label": str(answer_label),
            },
            "projected_evidence": {"bbox_set": list(evidence_boxes)},
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="option_letter", value=str(answer_label)),
            evidence_gt=TypedValue(type="bbox_set", value=list(evidence_boxes)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(sample),
            task_versions=default_task_versions(),
            query_variant="default",
            scene_id=SCENE_ID,
            query_id=str(sample.patch_mode),
        )


__all__ = ["IllustrationsVisualMissingPatchLabelTask"]
