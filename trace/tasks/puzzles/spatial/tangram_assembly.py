"""Tangram-style spatial reasoning tasks."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Mapping, Tuple

from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.common import projected_puzzle_bbox_evidence, resolve_puzzle_axis_variant
from ..shared.complexity import (
    build_puzzle_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_puzzle_complexity_weights,
)
from ..shared.tangram_scene import (
    SUPPORTED_TANGRAM_QUERY_IDS,
    SUPPORTED_TANGRAM_SCENE_VARIANTS,
    build_tangram_dataset,
    render_tangram_scene,
    resolve_tangram_render_params,
)
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.visual_defaults import load_puzzle_noise_defaults


INTERNAL_TASK_ID = "puzzles_spatial_tangram_assembly_internal"
TANGRAM_MISSING_PIECE_LABEL_TASK_ID = "task_puzzles__tangram__tangram_missing_piece_label"
TANGRAM_CONTACT_COUNT_TASK_ID = "task_puzzles__tangram__tangram_contact_count"
TANGRAM_SCENE_ID = "tangram"

_SUPPORTED_QUERY_IDS: Tuple[str, ...] = SUPPORTED_TANGRAM_QUERY_IDS
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = SUPPORTED_TANGRAM_SCENE_VARIANTS
_ANSWER_TYPES = {
    "missing_piece_label": "option_letter",
    "contact_count": "integer",
}
_REASONING_LOAD_BY_QUERY = {
    "missing_piece_label": 0.42,
    "contact_count": 0.58,
}
_SCENE_LOAD = {
    "tangram_square": 0.18,
    "tangram_diamond": 0.25,
    "tangram_tilted": 0.23,
}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "spatial")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=INTERNAL_TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_puzzle_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=INTERNAL_TASK_ID)
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="spatial", apply_prob=0.0)


def _resolve_scene_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the non-semantic tangram panel layout."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_SCENE_VARIANTS,
        task_id=INTERNAL_TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


class _TangramAssemblyBaseTask:
    """Base generator for public tangram scene tasks."""

    domain = "puzzles"
    task_group = "spatial"
    default_dataset_enabled = True
    fixed_query_id: str

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id = str(self.fixed_query_id)
        if query_id not in _SUPPORTED_QUERY_IDS:
            raise ValueError(f"unsupported tangram query_id: {query_id}")

        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        dataset = build_tangram_dataset(
            query_id=str(query_id),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            task_id=INTERNAL_TASK_ID,
        )
        render_params = resolve_tangram_render_params(params, render_defaults=_RENDER_DEFAULTS)
        scene_style, scene_style_meta = resolve_puzzle_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.tangram_background",
        )
        render_params = replace(
            render_params,
            panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            assembly_panel_fill_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
            option_panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            option_shape_fill_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
            missing_fill_rgb=tuple(int(value) for value in scene_style.text_rgb),
            marked_outline_rgb=tuple(int(value) for value in scene_style.mark_rgb),
            border_color_rgb=tuple(int(value) for value in scene_style.panel_border_rgb),
            seam_color_rgb=tuple(int(value) for value in scene_style.grid_rgb),
            text_color_rgb=tuple(int(value) for value in scene_style.text_rgb),
            text_stroke_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
        )
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered_scene = render_tangram_scene(
            background,
            dataset=dataset,
            scene_variant=str(scene_variant),
            render_params=render_params,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "object_description_missing_piece_label",
                "object_description_contact_count",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_option_letter",
                "answer_hint_integer",
                "evidence_hint_missing_piece_label",
                "evidence_hint_contact_count",
                "json_example_missing_piece_label",
                "json_example_contact_count",
                "json_example_answer_only_missing_piece_label",
                "json_example_answer_only_contact_count",
            ),
            context=f"prompt defaults for {INTERNAL_TASK_ID}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{query_id}"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{query_id}"]),
                "answer_hint": str(
                    prompt_defaults[
                        "answer_hint_integer"
                        if _ANSWER_TYPES[str(query_id)] == "integer"
                        else "answer_hint_option_letter"
                    ]
                ),
                "json_example": str(prompt_defaults[f"json_example_{query_id}"]),
                "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{query_id}"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        target_piece_ids = [str(item) for item in dataset.get("target_piece_ids", [str(dataset["target_piece_id"])])]
        target_piece_id = str(target_piece_ids[0])
        target_piece_bboxes = [
            list(rendered_scene.piece_bbox_map[str(piece_id)])
            for piece_id in target_piece_ids
            if str(piece_id) in rendered_scene.piece_bbox_map
        ]
        target_piece_bbox = list(target_piece_bboxes[0])
        contact_piece_ids = [str(item) for item in dataset.get("contact_piece_ids", [])]
        contact_bboxes = [
            list(rendered_scene.piece_bbox_map[str(piece_id)])
            for piece_id in contact_piece_ids
            if str(piece_id) in rendered_scene.piece_bbox_map
        ]

        if str(query_id) == "missing_piece_label":
            correct_option_panel_id = str(dataset["correct_option_panel_id"])
            option_projection = projected_puzzle_bbox_evidence(
                rendered_scene.option_panel_bbox_map,
                [str(correct_option_panel_id)],
            )
            option_bbox = list(option_projection["bbox_set"][0])
            evidence_bboxes = [option_bbox, target_piece_bbox]
            answer_value: str | int = str(dataset["answer_option_label"])
        else:
            evidence_bboxes = [*target_piece_bboxes, *contact_bboxes]
            answer_value = int(dataset["contact_count"])

        evidence_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in evidence_bboxes
        ]
        answer_gt = TypedValue(type=str(_ANSWER_TYPES[str(query_id)]), value=answer_value)
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        option_count = int(dataset["option_count"]) if str(query_id) != "contact_count" else 0
        visual_scan = clamp_unit_interval(
            0.48 * normalize_int_with_bounds(max(option_count, 4), [4, 6])
            + 0.32 * normalize_int_with_bounds(len(rendered_scene.piece_bbox_map), [5, 7])
            + 0.20 * float(_SCENE_LOAD[str(scene_variant)])
        )
        reasoning_load = clamp_unit_interval(
            float(_REASONING_LOAD_BY_QUERY[str(query_id)])
            + 0.12 * normalize_int_with_bounds(int(dataset["contact_count"]), [1, 4])
        )
        complexity = build_puzzle_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": float(visual_scan),
                "reasoning_load": float(reasoning_load),
                "scene_variant_load": float(_SCENE_LOAD[str(scene_variant)]),
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "puzzle_spatial_tangram_assembly",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "scene_id": TANGRAM_SCENE_ID,
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "target_piece_id": str(target_piece_id),
                    "answer_value": answer_value,
                    "view_family": "tangram",
                },
            },
            "query_spec": {
                "scene_id": TANGRAM_SCENE_ID,
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_id": TANGRAM_SCENE_ID,
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "option_count": int(option_count),
                    "option_count_range": list(dataset["option_count_range"]),
                    "target_piece_id": str(target_piece_id),
                    "target_piece_ids": [str(item) for item in target_piece_ids],
                    "target_shape_id": str(dataset["target_shape_id"]),
                    "contact_count": int(dataset["contact_count"]),
                    "contact_count_support": [int(item) for item in dataset["contact_count_support"]],
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_id": TANGRAM_SCENE_ID,
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "scene_style": dict(scene_style_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "assembly_panel_bbox_px": list(rendered_scene.assembly_panel_bbox_px),
                "assembly_bbox_px": list(rendered_scene.assembly_bbox_px),
                "text_style": {
                    "option_label_font_size_px": int(render_params.option_label_font_size_px),
                },
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "assembly_panel_bbox_px": list(rendered_scene.assembly_panel_bbox_px),
                "assembly_bbox_px": list(rendered_scene.assembly_bbox_px),
                "piece_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.piece_bbox_map.items()
                },
                "option_panel_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.option_panel_bbox_map.items()
                },
                "evidence_source": "piece_bboxes_px_and_option_panel_bboxes_px",
            },
            "execution_trace": {
                "scene_id": TANGRAM_SCENE_ID,
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "piece_specs": [dict(item) for item in dataset["piece_specs"]],
                "target_piece_id": str(target_piece_id),
                "target_piece_ids": [str(item) for item in target_piece_ids],
                "target_shape_id": str(dataset["target_shape_id"]),
                "target_shape_name": str(dataset["target_shape_name"]),
                "contact_piece_ids": [str(item) for item in contact_piece_ids],
                "contact_count": int(dataset["contact_count"]),
                "contact_count_support": [int(item) for item in dataset["contact_count_support"]],
                "option_specs": [dict(item) for item in dataset["option_specs"]],
                "option_count": int(option_count),
                "option_count_range": list(dataset["option_count_range"]),
                "answer_value": answer_value,
                "supporting_piece_ids": [*target_piece_ids, *contact_piece_ids],
                "supporting_option_panel_ids": (
                    [str(dataset["correct_option_panel_id"])] if str(query_id) != "contact_count" else []
                ),
                "question_format": str(query_id),
                "view_family": "tangram",
                "solver_trace": dict(dataset["solver_trace"]),
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
            },
            "answer_gt": answer_gt.to_dict(),
            "evidence_gt": evidence_gt.to_dict(),
            "complexity": complexity.to_dict(),
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=TANGRAM_SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class PuzzlesSpatialTangramMissingPieceLabelTask(_TangramAssemblyBaseTask):
    """Choose the candidate tangram piece matching a black missing region."""

    task_id = TANGRAM_MISSING_PIECE_LABEL_TASK_ID
    fixed_query_id = "missing_piece_label"


@register_task
class PuzzlesSpatialTangramContactCountTask(_TangramAssemblyBaseTask):
    """Count marked tangram pieces and directly edge-touching neighbors."""

    task_id = TANGRAM_CONTACT_COUNT_TASK_ID
    fixed_query_id = "contact_count"


__all__ = [
    "PuzzlesSpatialTangramContactCountTask",
    "PuzzlesSpatialTangramMissingPieceLabelTask",
]
