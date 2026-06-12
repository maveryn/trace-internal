"""Braille-cell notation tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.braille_scene import (
    BRAILLE_POSITIONS,
    SUPPORTED_BRAILLE_SCENE_VARIANTS,
    BrailleCellSpec,
    BrailleRenderParams,
    render_braille_count_scene,
    render_braille_match_scene,
)
from ..shared.common import get_int_range as _get_range
from ..shared.common import load_symbolic_task_defaults, resolve_symbolic_axis_variant
from ..shared.scene_style import make_symbolic_scene_background, resolve_symbolic_scene_style
from ..shared.visual_defaults import load_symbolic_noise_defaults


SCENE_ID = "braille_cell"
RAISED_DOT_COUNT_TASK_ID = "task_symbolic__braille_cell__raised_dot_count"
MATCHING_PATTERN_TASK_ID = "task_symbolic__braille_cell__matching_pattern_label"
RAISED_DOT_COUNT_QUERY_ID = "raised_dot_count"
MATCHING_PATTERN_QUERY_ID = "matching_pattern_label"
TASK_ID = RAISED_DOT_COUNT_TASK_ID
OPTION_LABELS: tuple[str, ...] = ("A", "B", "C", "D", "E", "F")

_TASK_GROUP_DEFAULTS = get_scene_defaults("symbolic", "notation")
POST_IMAGE_NOISE_DEFAULTS = load_symbolic_noise_defaults(scene_id="notation", apply_prob=0.20)


@dataclass(frozen=True)
class _Dataset:
    task_id: str
    query_id: str
    scene_variant: str
    answer_type: str
    answer_value: int | str
    target_answer_support: tuple[int | str, ...]
    annotation_item_ids: tuple[str, ...]
    annotation_dot_ids: tuple[str, ...]
    cells: tuple[BrailleCellSpec, ...]
    reference: BrailleCellSpec | None
    options: tuple[BrailleCellSpec, ...]
    metadata: dict[str, Any]


def _load_defaults(task_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    return load_symbolic_task_defaults(_TASK_GROUP_DEFAULTS, task_id=str(task_id))


def _resolve_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    return resolve_symbolic_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_BRAILLE_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _resolve_query_id(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    query_id: str,
) -> Tuple[str, Dict[str, float]]:
    selected, probabilities = resolve_symbolic_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=(str(query_id),),
        task_id=str(task_id),
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )
    if str(selected) != str(query_id):
        raise ValueError(f"{task_id} supports only query_id={query_id}")
    return str(selected), dict(probabilities)


def _resolve_render_params(defaults: Mapping[str, Any]) -> BrailleRenderParams:
    return BrailleRenderParams(
        canvas_width=int(defaults.get("braille_canvas_width", defaults.get("canvas_width", 980))),
        canvas_height=int(defaults.get("braille_canvas_height", defaults.get("canvas_height", 680))),
        cell_width_px=int(defaults.get("braille_cell_width_px", 132)),
        cell_height_px=int(defaults.get("braille_cell_height_px", 184)),
        dot_radius_px=int(defaults.get("braille_dot_radius_px", 13)),
        empty_dot_radius_px=int(defaults.get("braille_empty_dot_radius_px", 10)),
        cell_corner_radius_px=int(defaults.get("braille_cell_corner_radius_px", 18)),
        cell_border_width_px=int(defaults.get("braille_cell_border_width_px", 2)),
        marked_border_width_px=int(defaults.get("braille_marked_border_width_px", 5)),
        option_label_font_size_px=int(defaults.get("braille_option_label_font_size_px", 28)),
        title_font_size_px=int(defaults.get("braille_title_font_size_px", 24)),
    )


def _normalize_pattern(positions: Sequence[int]) -> tuple[int, ...]:
    normalized = tuple(sorted({int(pos) for pos in positions}))
    if not normalized:
        raise ValueError("Braille pattern must contain at least one raised dot")
    if any(pos not in BRAILLE_POSITIONS for pos in normalized):
        raise ValueError(f"Braille dot positions must be in {BRAILLE_POSITIONS}")
    return normalized


def _pattern_from_mask(mask: int) -> tuple[int, ...]:
    return tuple(pos for index, pos in enumerate(BRAILLE_POSITIONS) if int(mask) & (1 << int(index)))


def _sample_pattern_with_count(rng, count: int) -> tuple[int, ...]:
    if not 1 <= int(count) <= 6:
        raise ValueError("Braille raised-dot count must be in 1..6")
    return tuple(sorted(int(pos) for pos in rng.sample(list(BRAILLE_POSITIONS), int(count))))


def _sample_any_pattern(rng) -> tuple[int, ...]:
    return _pattern_from_mask(int(rng.randint(1, 63)))


def _pattern_key(pattern: Sequence[int]) -> str:
    return "".join(str(pos) for pos in _normalize_pattern(pattern))


def _build_count_dataset(
    *,
    instance_seed: int,
    scene_variant: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{RAISED_DOT_COUNT_TASK_ID}.dataset")
    answer_min, answer_max = _get_range(
        params,
        gen_defaults,
        min_key="target_answer_min",
        max_key="target_answer_max",
        fallback_min=1,
        fallback_max=6,
    )
    if int(answer_min) < 1 or int(answer_max) > 6:
        raise ValueError("Braille raised-dot answer support must stay within 1..6")
    answer = int(params.get("answer_value", rng.randint(int(answer_min), int(answer_max))))
    if not int(answer_min) <= int(answer) <= int(answer_max):
        raise ValueError("answer_value is outside configured Braille count support")
    cell_min, cell_max = _get_range(
        params,
        gen_defaults,
        min_key="cell_count_min",
        max_key="cell_count_max",
        fallback_min=4,
        fallback_max=6,
    )
    if int(cell_min) < 2 or int(cell_max) < int(cell_min):
        raise ValueError("Braille count scene requires at least two visible cells")
    cell_count = int(params.get("cell_count", rng.randint(int(cell_min), int(cell_max))))
    if not int(cell_min) <= int(cell_count) <= int(cell_max):
        raise ValueError("cell_count is outside configured support")
    target_index = int(rng.randrange(int(cell_count)))
    target_pattern = _sample_pattern_with_count(rng, int(answer))
    cells: list[BrailleCellSpec] = []
    for index in range(int(cell_count)):
        if int(index) == int(target_index):
            pattern = target_pattern
            label = "TARGET"
            marked = True
            role = "target_cell"
        else:
            pattern = _sample_any_pattern(rng)
            label = ""
            marked = False
            role = "distractor_cell"
        cells.append(
            BrailleCellSpec(
                item_id=f"cell_{index + 1}",
                raised_positions=tuple(pattern),
                label=str(label),
                role=str(role),
                marked=bool(marked),
            )
        )
    target_cell = cells[int(target_index)]
    annotation_dot_ids = tuple(f"{target_cell.item_id}_dot_{pos}" for pos in target_cell.raised_positions)
    return _Dataset(
        task_id=RAISED_DOT_COUNT_TASK_ID,
        query_id=RAISED_DOT_COUNT_QUERY_ID,
        scene_variant=str(scene_variant),
        answer_type="integer",
        answer_value=int(answer),
        target_answer_support=tuple(range(int(answer_min), int(answer_max) + 1)),
        annotation_item_ids=(str(target_cell.item_id),),
        annotation_dot_ids=annotation_dot_ids,
        cells=tuple(cells),
        reference=None,
        options=(),
        metadata={
            "target_cell_id": str(target_cell.item_id),
            "target_cell_index": int(target_index),
            "target_pattern": _pattern_key(target_pattern),
            "target_raised_positions": [int(pos) for pos in target_pattern],
            "cell_count": int(cell_count),
        },
    )


def _build_matching_dataset(
    *,
    instance_seed: int,
    scene_variant: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{MATCHING_PATTERN_TASK_ID}.dataset")
    option_count = int(params.get("option_count", gen_defaults.get("option_count", 6)))
    if int(option_count) != 6:
        raise ValueError("Braille matching task requires exactly six visual options")
    raised_min, raised_max = _get_range(
        params,
        gen_defaults,
        min_key="reference_raised_dot_count_min",
        max_key="reference_raised_dot_count_max",
        fallback_min=1,
        fallback_max=6,
    )
    if int(raised_min) < 1 or int(raised_max) > 6:
        raise ValueError("Braille reference raised-dot count support must stay within 1..6")
    reference_count = int(params.get("reference_raised_dot_count", rng.randint(int(raised_min), int(raised_max))))
    reference_pattern = _sample_pattern_with_count(rng, int(reference_count))
    labels = tuple(str(label) for label in OPTION_LABELS)
    correct_label = str(params.get("correct_label", labels[int(rng.randrange(len(labels)))]))
    if correct_label not in labels:
        raise ValueError(f"correct_label must be one of {labels}")
    distractor_masks = [mask for mask in range(1, 64) if _pattern_from_mask(mask) != reference_pattern]
    rng.shuffle(distractor_masks)
    distractor_patterns = [_pattern_from_mask(mask) for mask in distractor_masks[:5]]
    options: list[BrailleCellSpec] = []
    distractor_index = 0
    for label in labels:
        if str(label) == str(correct_label):
            pattern = reference_pattern
            role = "correct_option"
        else:
            pattern = distractor_patterns[int(distractor_index)]
            distractor_index += 1
            role = "distractor_option"
        options.append(
            BrailleCellSpec(
                item_id=f"option_{label}",
                raised_positions=tuple(pattern),
                label=str(label),
                role=str(role),
                marked=False,
            )
        )
    reference = BrailleCellSpec(
        item_id="reference_cell",
        raised_positions=tuple(reference_pattern),
        label="REF",
        role="reference_cell",
        marked=True,
    )
    correct_option = next(option for option in options if str(option.label) == str(correct_label))
    return _Dataset(
        task_id=MATCHING_PATTERN_TASK_ID,
        query_id=MATCHING_PATTERN_QUERY_ID,
        scene_variant=str(scene_variant),
        answer_type="string",
        answer_value=str(correct_label),
        target_answer_support=labels,
        annotation_item_ids=(str(reference.item_id), str(correct_option.item_id)),
        annotation_dot_ids=(),
        cells=(),
        reference=reference,
        options=tuple(options),
        metadata={
            "reference_pattern": _pattern_key(reference_pattern),
            "reference_raised_positions": [int(pos) for pos in reference_pattern],
            "correct_option_label": str(correct_label),
            "correct_option_id": str(correct_option.item_id),
            "option_patterns": {str(option.label): _pattern_key(option.raised_positions) for option in options},
        },
    )


def _build_prompt(
    *,
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
    prompt_values = required_group_defaults(prompt_defaults, required_keys, context=f"prompt defaults for {dataset.task_id}")
    slots = {
        "object_description": str(prompt_values[f"object_description_{scene_variant}"]),
        "json_output_contract": str(prompt_values["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_values["json_output_contract_answer_only"]),
        "annotation_hint": str(prompt_values[f"annotation_hint_{query_id}"]),
        "answer_hint": str(prompt_values[f"answer_hint_{query_id}"]),
        "json_example": str(prompt_values[f"json_example_{query_id}"]),
        "json_example_answer_only": str(prompt_values[f"json_example_answer_only_{query_id}"]),
    }
    prompt_selection = render_task_prompt_variants(
        domain="symbolic",
        scene_id="notation",
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


def _round_points(points: Sequence[Sequence[float]]) -> list[list[float]]:
    return [[round(float(point[0]), 3), round(float(point[1]), 3)] for point in points]


def _round_bbox_map(mapping: Mapping[str, Sequence[float]]) -> dict[str, list[float]]:
    return {str(key): [round(float(value), 3) for value in bbox] for key, bbox in mapping.items()}


def _scene_style_load(scene_variant: str) -> float:
    return {"clean_card": 0.16, "notebook_card": 0.22, "exam_scan": 0.26}.get(str(scene_variant), 0.2)


class _BrailleBaseTask:
    domain = "symbolic"
    scene_id = "notation"
    default_dataset_enabled = True
    task_id: str
    query_id: str

    def _build_dataset(
        self,
        *,
        instance_seed: int,
        scene_variant: str,
        params: Mapping[str, Any],
        gen_defaults: Mapping[str, Any],
    ) -> _Dataset:
        raise NotImplementedError

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_probabilities = _resolve_query_id(
            params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
            query_id=str(self.query_id),
        )
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
                    instance_seed=int(instance_seed) + int(attempt_index),
                    scene_variant=str(scene_variant),
                    params=params,
                    gen_defaults=gen_defaults,
                )
                break
            except Exception as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError(f"failed to generate Braille instance for {self.task_id}") from last_error

        render_params = _resolve_render_params(render_defaults)
        scene_style, scene_style_meta = resolve_symbolic_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.braille_background",
        )
        background, background_meta = make_symbolic_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        if str(dataset.query_id) == RAISED_DOT_COUNT_QUERY_ID:
            rendered_scene = render_braille_count_scene(
                background,
                cells=dataset.cells,
                params=render_params,
                style=scene_style,
            )
        else:
            if dataset.reference is None:
                raise RuntimeError("Braille matching task requires a reference cell")
            rendered_scene = render_braille_match_scene(
                background,
                reference=dataset.reference,
                options=dataset.options,
                params=render_params,
                style=scene_style,
            )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt, prompt_variants, prompt_meta = _build_prompt(
            dataset=dataset,
            prompt_defaults=prompt_defaults,
            instance_seed=int(instance_seed),
        )
        item_bboxes = _round_bbox_map(rendered_scene.item_bboxes)
        dot_centers = {str(key): [round(float(value[0]), 3), round(float(value[1]), 3)] for key, value in rendered_scene.dot_centers.items()}

        if str(dataset.query_id) == RAISED_DOT_COUNT_QUERY_ID:
            annotation_points = _round_points([dot_centers[str(dot_id)] for dot_id in dataset.annotation_dot_ids])
            annotation_gt = TypedValue(type="point_set", value=list(annotation_points))
            projected_annotation = {
                "type": "point_set",
                "point_set": list(annotation_points),
                "pixel_point_set": list(annotation_points),
                "value": list(annotation_points),
            }
            witness_symbolic = {"type": "point_set", "value": list(annotation_points)}
        else:
            keyed_bboxes = {
                "reference_cell": list(item_bboxes[str(dataset.annotation_item_ids[0])]),
                "selected_option": list(item_bboxes[str(dataset.annotation_item_ids[1])]),
            }
            annotation_gt = TypedValue(type="keyed_bbox_map", value=dict(keyed_bboxes))
            projected_annotation = {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(keyed_bboxes),
                "pixel_keyed_bbox_map": dict(keyed_bboxes),
                "value": dict(keyed_bboxes),
            }
            witness_symbolic = {"type": "keyed_bbox_map", "value": dict(keyed_bboxes)}

        answer_value = int(dataset.answer_value) if str(dataset.answer_type) == "integer" else str(dataset.answer_value)
        answer_gt = TypedValue(type=str(dataset.answer_type), value=answer_value)
        query_params = {
            "query_id": str(query_id),
            "internal_query_id": str(dataset.query_id),
            "query_id_probabilities": {"default": 1.0},
            "internal_query_id_probabilities": dict(query_probabilities),
            "scene_id": SCENE_ID,
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
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
                    "answer_value": answer_value,
                },
            },
            "query_spec": {
                "query_id": str(dataset.query_id),
                "internal_query_id": str(dataset.query_id),
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
                "braille_style": dict(rendered_scene.style_metadata),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "item_bboxes_px": dict(item_bboxes),
                "dot_centers_px": dict(dot_centers),
                "raised_dot_centers_px": {
                    str(key): [round(float(value[0]), 3), round(float(value[1]), 3)]
                    for key, value in rendered_scene.raised_dot_centers.items()
                },
                "cell_dot_centers_px": {
                    str(cell_id): {
                        str(dot_id): [round(float(value[0]), 3), round(float(value[1]), 3)]
                        for dot_id, value in dot_map.items()
                    }
                    for cell_id, dot_map in rendered_scene.cell_dot_centers.items()
                },
                "annotation_source": "dot_centers_px" if str(dataset.query_id) == RAISED_DOT_COUNT_QUERY_ID else "item_bboxes_px",
            },
            "execution_trace": {
                **dict(query_params),
                "answer_value": answer_value,
                "answer_type": str(dataset.answer_type),
                "annotation_item_ids": [str(item) for item in dataset.annotation_item_ids],
                "annotation_dot_ids": [str(item) for item in dataset.annotation_dot_ids],
                "braille_metadata": dict(dataset.metadata),
                "cells": [
                    {
                        "item_id": str(entity["item_id"]),
                        "role": str(entity["role"]),
                        "label": str(entity.get("label", "")),
                        "raised_positions": [int(pos) for pos in entity.get("raised_positions", [])],
                        "marked": bool(entity.get("marked", False)),
                    }
                    for entity in rendered_scene.entities
                ],
                "question_format": str(dataset.query_id),
            },
            "witness_symbolic": dict(witness_symbolic),
            "projected_annotation": dict(projected_annotation),
            "answer_gt": answer_gt.to_dict(),
            "annotation_gt": annotation_gt.to_dict(),
        }
        visual_count = len(rendered_scene.entities)
        reasoning_load = 0.18 if str(dataset.query_id) == RAISED_DOT_COUNT_QUERY_ID else 0.30
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(dataset.query_id),
            prompt_variants=dict(prompt_variants),
        )


@register_task
class SymbolicBrailleRaisedDotCountTask(_BrailleBaseTask):
    task_id = RAISED_DOT_COUNT_TASK_ID
    query_id = RAISED_DOT_COUNT_QUERY_ID

    def _build_dataset(
        self,
        *,
        instance_seed: int,
        scene_variant: str,
        params: Mapping[str, Any],
        gen_defaults: Mapping[str, Any],
    ) -> _Dataset:
        return _build_count_dataset(
            instance_seed=int(instance_seed),
            scene_variant=str(scene_variant),
            params=params,
            gen_defaults=gen_defaults,
        )


@register_task
class SymbolicBrailleMatchingPatternLabelTask(_BrailleBaseTask):
    task_id = MATCHING_PATTERN_TASK_ID
    query_id = MATCHING_PATTERN_QUERY_ID

    def _build_dataset(
        self,
        *,
        instance_seed: int,
        scene_variant: str,
        params: Mapping[str, Any],
        gen_defaults: Mapping[str, Any],
    ) -> _Dataset:
        return _build_matching_dataset(
            instance_seed=int(instance_seed),
            scene_variant=str(scene_variant),
            params=params,
            gen_defaults=gen_defaults,
        )


__all__ = [
    "MATCHING_PATTERN_QUERY_ID",
    "MATCHING_PATTERN_TASK_ID",
    "SymbolicBrailleMatchingPatternLabelTask",
    "SymbolicBrailleRaisedDotCountTask",
    "OPTION_LABELS",
    "RAISED_DOT_COUNT_QUERY_ID",
    "RAISED_DOT_COUNT_TASK_ID",
    "SCENE_ID",
    "TASK_ID",
]
