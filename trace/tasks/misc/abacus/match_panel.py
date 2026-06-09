"""Abacus target-value visual option matching task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.abacus_scene import (
    SUPPORTED_ABACUS_SCENE_VARIANTS,
    AbacusMatchPanelRenderParams,
    AbacusOptionSpec,
    digits_for_abacus_value,
    render_abacus_match_panel_scene,
)
from ..shared.common import get_int_range as _get_range
from ..shared.common import load_misc_task_defaults, resolve_misc_axis_variant
from ..shared.complexity import build_misc_complexity, clamp_unit_interval, normalize_int_with_bounds
from ..shared.scene_style import make_misc_scene_background, resolve_misc_scene_style
from ..shared.visual_defaults import load_misc_noise_defaults


SCENE_ID = "abacus_match_panel"
TASK_ID = "task_misc__abacus_match_panel__target_value_match_label"
QUERY_ID = "target_value_match_label"
DEFAULT_OPTION_LABELS = ("A", "B", "C", "D", "E", "F")

_TASK_GROUP_DEFAULTS = get_task_group_defaults("misc", "abacus")
POST_IMAGE_NOISE_DEFAULTS = load_misc_noise_defaults(task_group="abacus", apply_prob=0.18)


@dataclass(frozen=True)
class _Dataset:
    query_id: str
    scene_variant: str
    target_value: int
    target_value_support: tuple[int, int]
    option_labels: tuple[str, ...]
    correct_label: str
    option_values_by_label: dict[str, int]
    query_id_probabilities: dict[str, float]
    scene_variant_probabilities: dict[str, float]
    correct_label_probabilities: dict[str, float]


def _load_defaults() -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    return load_misc_task_defaults(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)


def _resolve_query_id(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[str, Dict[str, float]]:
    selected, probabilities = resolve_misc_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=(QUERY_ID,),
        task_id=TASK_ID,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )
    if str(selected) != QUERY_ID:
        raise ValueError(f"{TASK_ID} supports only query_id={QUERY_ID}")
    return str(selected), dict(probabilities)


def _resolve_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[str, Dict[str, float]]:
    return resolve_misc_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_ABACUS_SCENE_VARIANTS,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _resolve_option_labels(params: Mapping[str, Any], gen_defaults: Mapping[str, Any]) -> tuple[str, ...]:
    raw_labels = params.get("option_label_support", group_default(gen_defaults, "option_label_support", DEFAULT_OPTION_LABELS))
    labels = tuple(str(label).strip() for label in raw_labels if str(label).strip())
    option_count = int(params.get("option_count", group_default(gen_defaults, "option_count", len(DEFAULT_OPTION_LABELS))))
    if int(option_count) != 6:
        raise ValueError("abacus_match_panel currently requires exactly 6 visual options")
    if len(labels) != int(option_count):
        raise ValueError("abacus_match_panel option label support must contain exactly 6 labels")
    if len(set(labels)) != len(labels):
        raise ValueError("abacus_match_panel option labels must be unique")
    return tuple(str(label) for label in labels)


def _resolve_correct_label(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    option_labels: tuple[str, ...],
) -> Tuple[str, Dict[str, float]]:
    axis_params = dict(params)
    if "correct_label" in params and "answer_label" not in params:
        axis_params["answer_label"] = params["correct_label"]
    selected, probabilities = resolve_misc_axis_variant(
        params=axis_params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=option_labels,
        task_id=TASK_ID,
        explicit_key="answer_label",
        weights_key="correct_option_label_weights",
        balance_flag_key="balanced_correct_option_label_sampling",
        axis_namespace="correct_option_label",
    )
    return str(selected), dict(probabilities)


def _resolve_render_params(defaults: Mapping[str, Any]) -> AbacusMatchPanelRenderParams:
    return AbacusMatchPanelRenderParams(
        canvas_width=int(defaults.get("canvas_width", 1200)),
        canvas_height=int(defaults.get("canvas_height", 760)),
        option_card_width_px=int(defaults.get("option_card_width_px", 340)),
        option_card_height_px=int(defaults.get("option_card_height_px", 280)),
        option_card_gap_x_px=int(defaults.get("option_card_gap_x_px", 44)),
        option_card_gap_y_px=int(defaults.get("option_card_gap_y_px", 52)),
        option_card_corner_radius_px=int(defaults.get("option_card_corner_radius_px", 18)),
        option_label_font_size_px=int(defaults.get("option_label_font_size_px", 26)),
        option_place_label_font_size_px=int(defaults.get("option_place_label_font_size_px", 16)),
        option_bead_width_px=int(defaults.get("option_bead_width_px", 32)),
        option_bead_height_px=int(defaults.get("option_bead_height_px", 20)),
        option_rod_width_px=int(defaults.get("option_rod_width_px", 3)),
        option_beam_height_px=int(defaults.get("option_beam_height_px", 10)),
    )


def _value_from_digits(digits: tuple[int, int, int]) -> int:
    return int((100 * int(digits[0])) + (10 * int(digits[1])) + int(digits[2]))


def _candidate_distractors(target_value: int) -> list[int]:
    target_digits = digits_for_abacus_value(int(target_value))
    candidates: list[int] = []
    seen: set[int] = {int(target_value)}

    def add(value: int) -> None:
        if 0 <= int(value) <= 999 and int(value) not in seen:
            seen.add(int(value))
            candidates.append(int(value))

    for digit_index in range(3):
        for delta in (-1, 1, -2, 2, -5, 5):
            edited = list(target_digits)
            edited[digit_index] = int(edited[digit_index]) + int(delta)
            if 0 <= int(edited[digit_index]) <= 9:
                add(_value_from_digits((int(edited[0]), int(edited[1]), int(edited[2]))))
    for first, second in ((0, 1), (1, 2), (0, 2)):
        edited = list(target_digits)
        edited[first], edited[second] = edited[second], edited[first]
        add(_value_from_digits((int(edited[0]), int(edited[1]), int(edited[2]))))
    for offset in (-100, 100, -50, 50, -20, 20, -10, 10, -5, 5, -2, 2, -1, 1):
        add(int(target_value) + int(offset))
    return [int(value) for value in candidates]


def _choose_option_values(
    *,
    instance_seed: int,
    target_value: int,
    option_labels: tuple[str, ...],
    correct_label: str,
) -> dict[str, int]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.option_values")
    distractor_pool = _candidate_distractors(int(target_value))
    rng.shuffle(distractor_pool)
    distractors: list[int] = []
    seen: set[int] = {int(target_value)}
    for value in distractor_pool:
        if int(value) not in seen:
            seen.add(int(value))
            distractors.append(int(value))
        if len(distractors) >= len(option_labels) - 1:
            break
    while len(distractors) < len(option_labels) - 1:
        value = int(rng.randint(0, 999))
        if int(value) not in seen:
            seen.add(int(value))
            distractors.append(int(value))

    option_values: dict[str, int] = {}
    distractor_index = 0
    for label in option_labels:
        if str(label) == str(correct_label):
            option_values[str(label)] = int(target_value)
        else:
            option_values[str(label)] = int(distractors[distractor_index])
            distractor_index += 1
    return dict(option_values)


def _build_dataset(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> _Dataset:
    query_id, query_id_probabilities = _resolve_query_id(
        params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
    )
    scene_variant, scene_variant_probabilities = _resolve_scene_variant(
        params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
    )
    option_labels = _resolve_option_labels(params, gen_defaults)
    correct_label, correct_label_probabilities = _resolve_correct_label(
        params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        option_labels=option_labels,
    )
    target_min, target_max = _get_range(
        params,
        gen_defaults,
        min_key="target_value_min",
        max_key="target_value_max",
        fallback_min=0,
        fallback_max=999,
    )
    if int(target_min) < 0 or int(target_max) > 999:
        raise ValueError("abacus target-value support must stay within 0..999")
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.target_value")
    if "target_value" in params:
        target_value = int(params["target_value"])
    elif "answer_value" in params:
        target_value = int(params["answer_value"])
    else:
        target_value = int(rng.randint(int(target_min), int(target_max)))
    if not int(target_min) <= int(target_value) <= int(target_max):
        raise ValueError("target_value is outside configured abacus support")
    option_values_by_label = _choose_option_values(
        instance_seed=int(instance_seed),
        target_value=int(target_value),
        option_labels=option_labels,
        correct_label=str(correct_label),
    )
    if list(option_values_by_label.values()).count(int(target_value)) != 1:
        raise RuntimeError("abacus match panel failed to construct a unique matching option")
    return _Dataset(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        target_value=int(target_value),
        target_value_support=(int(target_min), int(target_max)),
        option_labels=tuple(str(label) for label in option_labels),
        correct_label=str(correct_label),
        option_values_by_label=dict(option_values_by_label),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        correct_label_probabilities=dict(correct_label_probabilities),
    )


def _build_prompt(
    *,
    prompt_defaults: Mapping[str, Any],
    scene_variant: str,
    target_value: int,
    instance_seed: int,
) -> tuple[str, dict[str, str], dict[str, Any]]:
    required_keys = (
        "bundle_id",
        "scene_key",
        "task_key",
        "json_output_contract",
        "json_output_contract_answer_only",
        f"object_description_{scene_variant}",
        "annotation_hint",
        "answer_hint",
        "json_example",
        "json_example_answer_only",
    )
    prompt_values = required_group_defaults(prompt_defaults, required_keys, context=f"prompt defaults for {TASK_ID}")
    prompt_selection = render_task_prompt_variants(
        domain="misc",
        task_group="abacus",
        bundle_id=str(prompt_values["bundle_id"]),
        scene_key=str(prompt_values["scene_key"]),
        task_key=str(prompt_values["task_key"]),
        query_key=QUERY_ID,
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(prompt_values[f"object_description_{scene_variant}"]),
            "target_value": str(int(target_value)),
            "json_output_contract": str(prompt_values["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_values["json_output_contract_answer_only"]),
            "annotation_hint": str(prompt_values["annotation_hint"]),
            "answer_hint": str(prompt_values["answer_hint"]),
            "json_example": str(prompt_values["json_example"]),
            "json_example_answer_only": str(prompt_values["json_example_answer_only"]),
        },
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    return str(prompt_artifacts.prompt), dict(prompt_artifacts.prompt_variants), {
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants_for_trace": dict(prompt_artifacts.prompt_variants_for_trace),
        "bundle_id": str(prompt_values["bundle_id"]),
    }


def _scene_style_load(scene_variant: str) -> float:
    return {"clean_card": 0.20, "wood_frame": 0.26, "worksheet": 0.24}.get(str(scene_variant), 0.22)


@register_task
class MiscAbacusTargetValueMatchTask:
    """Select the visual abacus option matching a prompt-provided target value."""

    task_id = TASK_ID
    domain = "misc"
    task_group = "abacus"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        gen_defaults, render_defaults, prompt_defaults, complexity_weights = _load_defaults()
        last_error: Exception | None = None
        dataset: _Dataset | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                dataset = _build_dataset(
                    instance_seed=int(instance_seed) + int(attempt_index),
                    params=params,
                    gen_defaults=gen_defaults,
                )
                break
            except Exception as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError(f"failed to generate abacus match-panel instance for {TASK_ID}") from last_error

        render_params = _resolve_render_params(render_defaults)
        scene_style, scene_style_meta = resolve_misc_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.background",
        )
        background, background_meta = make_misc_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        options = tuple(
            AbacusOptionSpec(
                label=str(label),
                value=int(dataset.option_values_by_label[str(label)]),
                is_correct=bool(str(label) == str(dataset.correct_label)),
            )
            for label in dataset.option_labels
        )
        rendered_scene = render_abacus_match_panel_scene(
            background,
            options=options,
            correct_label=str(dataset.correct_label),
            params=render_params,
            scene_variant=str(dataset.scene_variant),
            style=scene_style,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt, prompt_variants, prompt_meta = _build_prompt(
            prompt_defaults=prompt_defaults,
            scene_variant=str(dataset.scene_variant),
            target_value=int(dataset.target_value),
            instance_seed=int(instance_seed),
        )

        annotation_bboxes = [list(rendered_scene.selected_option_card_bbox)]
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))
        answer_gt = TypedValue(type="option_letter", value=str(dataset.correct_label))
        projected_annotation = {
            "type": "bbox_set",
            "bbox_set": list(annotation_bboxes),
            "pixel_bbox_set": list(annotation_bboxes),
            "value": list(annotation_bboxes),
        }
        query_params = {
            "query_id": str(dataset.query_id),
            "query_id_probabilities": dict(dataset.query_id_probabilities),
            "scene_id": SCENE_ID,
            "scene_variant": str(dataset.scene_variant),
            "scene_variant_probabilities": dict(dataset.scene_variant_probabilities),
            "option_labels": [str(label) for label in dataset.option_labels],
            "correct_label_probabilities": dict(dataset.correct_label_probabilities),
            "target_value_support": [int(dataset.target_value_support[0]), int(dataset.target_value_support[1])],
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": SCENE_ID,
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(dataset.query_id),
                    "scene_id": SCENE_ID,
                    "scene_variant": str(dataset.scene_variant),
                    "target_value": int(dataset.target_value),
                    "correct_label": str(dataset.correct_label),
                    "option_values_by_label": dict(dataset.option_values_by_label),
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
                "scene_variant": str(dataset.scene_variant),
                "scene_style": dict(scene_style_meta),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "abacus_style": dict(rendered_scene.style_metadata),
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "item_bboxes_px": dict(rendered_scene.item_bboxes),
                "option_card_bboxes_px": dict(rendered_scene.option_card_bboxes),
                "option_abacus_bboxes_px": dict(rendered_scene.option_abacus_bboxes),
                "selected_option_card_bbox_px": list(rendered_scene.selected_option_card_bbox),
                "selected_option_abacus_bbox_px": list(rendered_scene.selected_option_abacus_bbox),
                "correct_label": str(dataset.correct_label),
                "annotation_source": "selected_option_card_bbox_px",
            },
            "execution_trace": {
                **dict(query_params),
                "target_value": int(dataset.target_value),
                "target_digits": [int(digit) for digit in digits_for_abacus_value(int(dataset.target_value))],
                "answer_type": "option_letter",
                "correct_label": str(dataset.correct_label),
                "option_values_by_label": dict(dataset.option_values_by_label),
                "option_digits_by_label": {
                    str(label): [int(digit) for digit in digits_for_abacus_value(int(value))]
                    for label, value in dataset.option_values_by_label.items()
                },
                "question_format": str(dataset.query_id),
                "supporting_bbox_roles": ["selected_option_card"],
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(annotation_bboxes),
            },
            "projected_annotation": dict(projected_annotation),
            "answer_gt": answer_gt.to_dict(),
            "annotation_gt": annotation_gt.to_dict(),
        }
        target_digit_sum = sum(int(digit) for digit in digits_for_abacus_value(int(dataset.target_value)))
        complexity = build_misc_complexity(
            weights=complexity_weights,
            components={
                "visual_scan": clamp_unit_interval(0.58),
                "reasoning_load": clamp_unit_interval(0.34 + (0.04 * sum(1 for digit in digits_for_abacus_value(int(dataset.target_value)) if int(digit) > 0))),
                "scene_variant_load": _scene_style_load(str(dataset.scene_variant)),
                "distractor_similarity": normalize_int_with_bounds(int(target_digit_sum), [0, 27]),
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


__all__ = [
    "MiscAbacusTargetValueMatchTask",
    "TASK_ID",
]
