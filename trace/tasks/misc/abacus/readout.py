"""Soroban-style abacus displayed-value readout task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.abacus_scene import (
    ABACUS_COLUMN_ROLES,
    ABACUS_ANNOTATION_KEYS,
    SUPPORTED_ABACUS_SCENE_VARIANTS,
    AbacusColumnSpec,
    AbacusRenderParams,
    render_abacus_readout_scene,
)
from ..shared.common import get_int_range as _get_range
from ..shared.common import load_misc_task_defaults, resolve_misc_axis_variant
from ..shared.complexity import build_misc_complexity, clamp_unit_interval, normalize_int_with_bounds
from ..shared.scene_style import make_misc_scene_background, resolve_misc_scene_style
from ..shared.visual_defaults import load_misc_noise_defaults


SCENE_ID = "abacus_readout"
TASK_ID = "task_misc__abacus_readout__displayed_value_readout"
QUERY_ID = "displayed_value_readout"

_TASK_GROUP_DEFAULTS = get_task_group_defaults("misc", "abacus")
POST_IMAGE_NOISE_DEFAULTS = load_misc_noise_defaults(task_group="abacus", apply_prob=0.18)


@dataclass(frozen=True)
class _Dataset:
    query_id: str
    scene_variant: str
    answer_value: int
    target_answer_support: tuple[int, int]
    columns: tuple[AbacusColumnSpec, ...]
    digits_by_role: dict[str, int]
    place_values_by_role: dict[str, int]


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


def _resolve_render_params(defaults: Mapping[str, Any]) -> AbacusRenderParams:
    return AbacusRenderParams(
        canvas_width=int(defaults.get("canvas_width", 980)),
        canvas_height=int(defaults.get("canvas_height", 760)),
        panel_width_px=int(defaults.get("panel_width_px", 800)),
        panel_height_px=int(defaults.get("panel_height_px", 540)),
        panel_corner_radius_px=int(defaults.get("panel_corner_radius_px", 24)),
        frame_width_px=int(defaults.get("frame_width_px", 8)),
        rod_width_px=int(defaults.get("rod_width_px", 5)),
        beam_height_px=int(defaults.get("beam_height_px", 22)),
        bead_width_px=int(defaults.get("bead_width_px", 58)),
        bead_height_px=int(defaults.get("bead_height_px", 34)),
        title_font_size_px=int(defaults.get("title_font_size_px", 25)),
        label_font_size_px=int(defaults.get("label_font_size_px", 23)),
        small_font_size_px=int(defaults.get("small_font_size_px", 16)),
    )


def _digits_for_value(value: int) -> tuple[int, int, int]:
    if not 0 <= int(value) <= 999:
        raise ValueError("abacus displayed value must be in 0..999")
    text = f"{int(value):03d}"
    return int(text[0]), int(text[1]), int(text[2])


def _build_dataset(
    *,
    instance_seed: int,
    scene_variant: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    answer_min, answer_max = _get_range(
        params,
        gen_defaults,
        min_key="target_answer_min",
        max_key="target_answer_max",
        fallback_min=0,
        fallback_max=999,
    )
    if int(answer_min) < 0 or int(answer_max) > 999:
        raise ValueError("abacus displayed-value answer support must stay within 0..999")
    if "answer_value" in params:
        answer_value = int(params["answer_value"])
    elif "displayed_value" in params:
        answer_value = int(params["displayed_value"])
    else:
        answer_value = int(rng.randint(int(answer_min), int(answer_max)))
    if not int(answer_min) <= int(answer_value) <= int(answer_max):
        raise ValueError("answer_value is outside configured abacus answer support")

    digits = _digits_for_value(int(answer_value))
    place_labels = ("100", "10", "1")
    place_values = (100, 10, 1)
    columns = tuple(
        AbacusColumnSpec(
            item_id=f"column_{role}",
            role=str(role),
            place_label=str(place_label),
            place_value=int(place_value),
            digit=int(digit),
        )
        for role, place_label, place_value, digit in zip(ABACUS_COLUMN_ROLES, place_labels, place_values, digits)
    )
    digits_by_role = {str(column.role): int(column.digit) for column in columns}
    place_values_by_role = {str(column.role): int(column.place_value) for column in columns}
    return _Dataset(
        query_id=QUERY_ID,
        scene_variant=str(scene_variant),
        answer_value=int(answer_value),
        target_answer_support=(int(answer_min), int(answer_max)),
        columns=tuple(columns),
        digits_by_role=dict(digits_by_role),
        place_values_by_role=dict(place_values_by_role),
    )


def _build_prompt(
    *,
    prompt_defaults: Mapping[str, Any],
    scene_variant: str,
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
    slots = {
        "object_description": str(prompt_values[f"object_description_{scene_variant}"]),
        "json_output_contract": str(prompt_values["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_values["json_output_contract_answer_only"]),
        "annotation_hint": str(prompt_values["annotation_hint"]),
        "answer_hint": str(prompt_values["answer_hint"]),
        "json_example": str(prompt_values["json_example"]),
        "json_example_answer_only": str(prompt_values["json_example_answer_only"]),
    }
    prompt_selection = render_task_prompt_variants(
        domain="misc",
        task_group="abacus",
        bundle_id=str(prompt_values["bundle_id"]),
        scene_key=str(prompt_values["scene_key"]),
        task_key=str(prompt_values["task_key"]),
        query_key=QUERY_ID,
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


def _scene_style_load(scene_variant: str) -> float:
    return {"clean_card": 0.16, "wood_frame": 0.22, "worksheet": 0.20}.get(str(scene_variant), 0.18)


@register_task
class MiscAbacusDisplayedValueReadoutTask:
    """Read the integer represented by a three-column soroban-style abacus."""

    task_id = TASK_ID
    domain = "misc"
    task_group = "abacus"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        gen_defaults, render_defaults, prompt_defaults, complexity_weights = _load_defaults()
        query_id, query_probabilities = _resolve_query_id(
            params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
        )
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
        )
        last_error: Exception | None = None
        dataset: _Dataset | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                dataset = _build_dataset(
                    instance_seed=int(instance_seed) + int(attempt_index),
                    scene_variant=str(scene_variant),
                    params=params,
                    gen_defaults=gen_defaults,
                )
                break
            except Exception as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError(f"failed to generate abacus instance for {TASK_ID}") from last_error

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
        rendered_scene = render_abacus_readout_scene(
            background,
            columns=dataset.columns,
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
            instance_seed=int(instance_seed),
        )

        keyed_points = {
            str(key): [list(point) for point in rendered_scene.active_bead_points_by_column.get(str(key), [])]
            for key in ABACUS_ANNOTATION_KEYS
        }
        annotation_gt = TypedValue(type="keyed_point_set_map", value=dict(keyed_points))
        answer_gt = TypedValue(type="integer", value=int(dataset.answer_value))
        projected_annotation = {
            "type": "keyed_point_set_map",
            "keyed_point_set_map": dict(keyed_points),
            "pixel_keyed_point_set_map": dict(keyed_points),
            "value": dict(keyed_points),
        }
        query_params = {
            "query_id": str(query_id),
            "query_id_probabilities": dict(query_probabilities),
            "scene_id": SCENE_ID,
            "scene_variant": str(dataset.scene_variant),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "target_answer_support": [int(dataset.target_answer_support[0]), int(dataset.target_answer_support[1])],
            "column_roles": [str(role) for role in ABACUS_COLUMN_ROLES],
            "annotation_keys": [str(key) for key in ABACUS_ANNOTATION_KEYS],
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": SCENE_ID,
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(dataset.query_id),
                    "scene_id": SCENE_ID,
                    "scene_variant": str(dataset.scene_variant),
                    "answer_value": int(dataset.answer_value),
                    "digits_by_role": dict(dataset.digits_by_role),
                    "place_values_by_role": dict(dataset.place_values_by_role),
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
                "bead_bboxes_px": dict(rendered_scene.bead_bboxes),
                "active_bead_bboxes_by_column_px": dict(rendered_scene.active_bead_bboxes_by_column),
                "active_bead_points_by_column_px": dict(keyed_points),
                "active_bead_ids_by_column": dict(rendered_scene.active_bead_ids_by_column),
                "column_bboxes_px": dict(rendered_scene.column_bboxes),
                "label_bboxes_px": dict(rendered_scene.label_bboxes),
                "annotation_source": "active_bead_points_by_column_px",
            },
            "execution_trace": {
                **dict(query_params),
                "answer_value": int(dataset.answer_value),
                "answer_type": "integer",
                "digits_by_role": dict(dataset.digits_by_role),
                "place_values_by_role": dict(dataset.place_values_by_role),
                "columns": [
                    {
                        "item_id": str(column.item_id),
                        "role": str(column.role),
                        "place_label": str(column.place_label),
                        "place_value": int(column.place_value),
                        "digit": int(column.digit),
                        "active_bead_ids": [str(item) for item in rendered_scene.active_bead_ids_by_column[str(column.role)]],
                    }
                    for column in dataset.columns
                ],
                "question_format": str(dataset.query_id),
                "supporting_point_roles": [str(key) for key in ABACUS_ANNOTATION_KEYS],
            },
            "witness_symbolic": {
                "type": "keyed_point_set_map",
                "value": dict(keyed_points),
            },
            "projected_annotation": dict(projected_annotation),
            "answer_gt": answer_gt.to_dict(),
            "annotation_gt": annotation_gt.to_dict(),
        }
        active_bead_count = sum(len(values) for values in keyed_points.values())
        nonzero_column_count = sum(1 for value in dataset.digits_by_role.values() if int(value) > 0)
        complexity = build_misc_complexity(
            weights=complexity_weights,
            components={
                "visual_scan": normalize_int_with_bounds(int(active_bead_count), [0, 18]),
                "reasoning_load": clamp_unit_interval(0.22 + (0.12 * int(nonzero_column_count))),
                "scene_variant_load": _scene_style_load(str(dataset.scene_variant)),
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
    "MiscAbacusDisplayedValueReadoutTask",
    "TASK_ID",
]
