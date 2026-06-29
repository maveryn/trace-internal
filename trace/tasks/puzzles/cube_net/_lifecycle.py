"""Scene-private lifecycle helpers for cube-net puzzle rendering."""

from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Sequence

from PIL import Image

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.puzzles.shared.visual_defaults import load_puzzle_noise_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.font_assets import font_asset_version, sample_font_family
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec
from trace.tasks.shared.text_rendering import temporary_default_font_family
from trace.tasks.shared.variant_sampling import resolve_variant

from .shared.annotations import (
    bbox_map_typed_value,
    projected_bbox_map,
    round_annotation_bbox,
)
from .shared.output import (
    build_cube_net_trace_payload,
    json_ready,
    surface_path_trace_parts,
)
from .shared.prompts import build_cube_net_prompt_artifacts
from .shared.rendering import (
    render_face_relation_scene,
    render_rolling_scene,
    render_surface_path_scene,
)
from .shared.sampling import (
    face_option_specs,
    sample_face_relation_dataset,
    sample_rolling_dataset,
    sample_surface_path_dataset,
    sequence_option_specs,
)
from .shared.state import DOMAIN, NET_COORDS, SCENE_ID, SCENE_VARIANTS


def select_cube_net_scene_variant(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    namespace: str,
) -> tuple[str, Dict[str, float]]:
    """Select nonsemantic cube-net panel chrome from scene variant support."""

    rng = spawn_rng(int(instance_seed), f"{namespace}.scene_variant")
    return resolve_variant(
        rng,
        params=params,
        gen_defaults=generation_defaults,
        supported_variants=SCENE_VARIANTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
    )


def sample_cube_net_font(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    namespace: str,
) -> str:
    """Sample one global font family for all cube-net labels in the image."""

    return sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.label_font",
        params={**dict(rendering_defaults), **dict(params)},
    )


def font_trace_record(font_family: str) -> Dict[str, Any]:
    """Build trace metadata for the sampled cube-net label font."""

    return {
        "source": "global_font_pool",
        "font_family": str(font_family),
        "font_asset_version": font_asset_version(),
        "scope": "cube_net_panel_face_option_labels",
    }


def apply_cube_net_post_noise(
    image: Image.Image,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> tuple[Image.Image, Dict[str, Any]]:
    """Apply scene-configured post-image noise after semantic rendering is done."""

    visual_defaults = {
        **load_puzzle_noise_defaults(scene_id=SCENE_ID, apply_prob=0.5),
        "apply_prob": 0.5,
        "edit_types": ["blur", "downsample", "jpeg", "noise"],
        "edit_count_range": [1, 1],
        "value_ranges": {
            "blur": {"radius": [0.08, 0.24]},
            "downsample": {"scale": [0.94, 0.98]},
            "jpeg": {"quality": [86.0, 95.0]},
            "noise": {"alpha": [0.006, 0.022]},
        },
    }
    return apply_post_image_noise(
        image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=visual_defaults,
    )


def render_surface_path_case(
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    instance_seed: int,
    max_attempts: int,
    option_mode: str,
    namespace: str,
) -> Dict[str, Any]:
    """Prepare a folded-path image; public tasks bind endpoint/sequence answers."""

    scene_variant, scene_probabilities = select_cube_net_scene_variant(
        instance_seed=int(instance_seed),
        params=params,
        generation_defaults=generation_defaults,
        namespace=f"{namespace}.surface_path",
    )
    last_error: Exception | None = None
    for attempt_index in range(max(1, int(max_attempts))):
        attempt_seed = int(instance_seed) + int(attempt_index)
        try:
            dataset = sample_surface_path_dataset(
                params=params,
                generation_defaults=generation_defaults,
                instance_seed=attempt_seed,
                namespace=f"{namespace}.surface_path",
            )
            font_family = sample_cube_net_font(
                instance_seed=attempt_seed,
                params=params,
                rendering_defaults=rendering_defaults,
                namespace=f"{namespace}.surface_path",
            )
            with temporary_default_font_family(str(font_family)):
                image, render_meta = render_surface_path_scene(
                    dataset=dataset,
                    option_mode=str(option_mode),
                    params=params,
                    rendering_defaults=rendering_defaults,
                    instance_seed=attempt_seed,
                    scene_variant=str(scene_variant),
                )
            break
        except ValueError as exc:
            last_error = exc
    else:
        raise RuntimeError("cube-net folded path failed to construct a sample") from last_error

    image, post_noise_meta = apply_cube_net_post_noise(
        image,
        instance_seed=int(instance_seed),
        params=params,
    )
    return {
        "dataset": dataset,
        "font_family": str(font_family),
        "image": image,
        "render_meta": dict(render_meta),
        "post_noise_meta": dict(post_noise_meta),
        "scene_variant": str(scene_variant),
        "scene_variant_probabilities": dict(scene_probabilities),
    }


def _select_public_query(
    *,
    task_identity: str,
    supported_queries: Sequence[str],
    instance_seed: int,
    params: Mapping[str, Any],
) -> tuple[str, Dict[str, float], Dict[str, Any]]:
    """Delegate query selection while keeping supported ids task-owned."""

    supported = tuple(str(value) for value in supported_queries)
    return select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=supported,
        default_query_id=str(supported[0]),
        task_id=str(task_identity),
        namespace=f"{task_identity}.query",
    )


def run_face_relation_lifecycle(
    *,
    task_identity: str,
    supported_queries: Sequence[str],
    relation_kind_by_query: Mapping[str, str],
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> TaskOutput:
    """Run the face-relation objective after public files provide query mapping."""

    query_id, query_probabilities, task_params = _select_public_query(
        task_identity=str(task_identity),
        supported_queries=supported_queries,
        instance_seed=int(instance_seed),
        params=dict(params),
    )
    scene_variant, scene_probabilities = select_cube_net_scene_variant(
        instance_seed=int(instance_seed),
        params=task_params,
        generation_defaults=generation_defaults,
        namespace="cube_net.face_relation",
    )
    last_error: Exception | None = None
    for attempt_index in range(max(1, int(max_attempts))):
        attempt_seed = int(instance_seed) + int(attempt_index)
        try:
            dataset = sample_face_relation_dataset(
                relation_kind=str(relation_kind_by_query[str(query_id)]),
                params=task_params,
                generation_defaults=generation_defaults,
                instance_seed=attempt_seed,
                namespace="cube_net.face_relation",
            )
            font_family = sample_cube_net_font(
                instance_seed=attempt_seed,
                params=task_params,
                rendering_defaults=rendering_defaults,
                namespace="cube_net.face_relation",
            )
            with temporary_default_font_family(str(font_family)):
                image, render_meta = render_face_relation_scene(
                    dataset=dataset,
                    params=task_params,
                    rendering_defaults=rendering_defaults,
                    instance_seed=attempt_seed,
                    scene_variant=str(scene_variant),
                )
            break
        except ValueError as exc:
            last_error = exc
    else:
        raise RuntimeError(f"{task_identity} failed to construct a sample") from last_error

    image, post_noise_meta = apply_cube_net_post_noise(
        image,
        instance_seed=int(instance_seed),
        params=task_params,
    )
    prompt_defaults, prompt_artifacts = build_cube_net_prompt_artifacts(
        prompt_task_key="face_relation_label_query",
        prompt_query_key=str(query_id),
        dynamic_slots={},
        instance_seed=int(instance_seed),
    )
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(query_id),
        params={
            "scene_id": SCENE_ID,
            "query_id_probabilities": dict(query_probabilities),
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(scene_probabilities),
            "option_labels": [str(option.option_label) for option in dataset.options],
            "answer_support": [str(option.option_label) for option in dataset.options],
            "relation_kind": str(dataset.relation_kind),
        },
    )
    ref_bbox = render_meta["face_bboxes_px"][str(dataset.reference_face)]
    option_bbox = render_meta["option_panel_bboxes_px"][
        f"option_{dataset.correct_option_label}"
    ]
    annotation_bboxes = {
        "marked_face": round_annotation_bbox(ref_bbox),
        "selected_option": round_annotation_bbox(option_bbox),
    }
    answer_gt = TypedValue(type="option_letter", value=str(dataset.correct_option_label))
    annotation_gt = bbox_map_typed_value(annotation_bboxes)
    render_spec = {
        "canvas_width": int(image.width),
        "canvas_height": int(image.height),
        "coord_space": "pixel",
        "scene_id": SCENE_ID,
        "query_id": str(query_id),
        "scene_variant": str(scene_variant),
        "post_image_noise": dict(post_noise_meta),
        "label_style": {"font": font_trace_record(str(font_family))},
        **dict(render_meta),
    }
    trace_payload = build_cube_net_trace_payload(
        scene_ir={
            "scene_kind": "puzzle_cube_net",
            "scene_id": SCENE_ID,
            "task_id": str(task_identity),
            "entities": [
                {
                    "entity_id": f"face_{face}",
                    "kind": "cube_net_face",
                    "face_id": str(face),
                    "face_label": str(label),
                }
                for face, label in sorted(dataset.face_labels.items())
            ],
            "relations": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "relation_kind": str(dataset.relation_kind),
                "reference_face": str(dataset.reference_face),
                "marked_side": dataset.marked_side,
                "correct_face": str(dataset.correct_face),
                "correct_option_label": str(dataset.correct_option_label),
            },
        },
        query_spec=query_spec,
        render_spec=render_spec,
        render_map={
            "image_id": "img0",
            "face_bboxes_px": dict(render_meta["face_bboxes_px"]),
            "option_panel_bboxes_px": dict(render_meta["option_panel_bboxes_px"]),
            "annotation_source": "face_bboxes_px+option_panel_bboxes_px",
        },
        execution_trace={
            "scene_id": SCENE_ID,
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "relation_kind": str(dataset.relation_kind),
            "face_labels": dict(dataset.face_labels),
            "net_coords": {
                str(face): [int(coord[0]), int(coord[1])]
                for face, coord in NET_COORDS.items()
            },
            "reference_face": str(dataset.reference_face),
            "marked_side": dataset.marked_side,
            "correct_face": str(dataset.correct_face),
            "option_specs": face_option_specs(dataset.options),
            "answer_value": str(dataset.correct_option_label),
        },
        witness_symbolic={
            "type": "cube_face_relation",
            "value": {
                "reference_face": str(dataset.reference_face),
                "marked_side": dataset.marked_side,
                "correct_face": str(dataset.correct_face),
                "correct_option_label": str(dataset.correct_option_label),
            },
        },
        projected_annotation=projected_bbox_map(annotation_bboxes),
        answer_gt=answer_gt.to_dict(),
        annotation_gt=annotation_gt.to_dict(),
        prompt_defaults=prompt_defaults,
        prompt_artifacts=prompt_artifacts,
    )
    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        answer_gt=answer_gt,
        annotation_gt=annotation_gt,
        image=image,
        image_id="img0",
        trace_payload=json_ready(trace_payload),
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(query_id),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
    )


def run_rolling_lifecycle(
    *,
    task_identity: str,
    supported_queries: Sequence[str],
    target_slot_by_query: Mapping[str, str],
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> TaskOutput:
    """Run the cube-rolling objective after public files provide target slots."""

    query_id, query_probabilities, task_params = _select_public_query(
        task_identity=str(task_identity),
        supported_queries=supported_queries,
        instance_seed=int(instance_seed),
        params=dict(params),
    )
    scene_variant, scene_probabilities = select_cube_net_scene_variant(
        instance_seed=int(instance_seed),
        params=task_params,
        generation_defaults=generation_defaults,
        namespace="cube_net.rolling",
    )
    last_error: Exception | None = None
    for attempt_index in range(max(1, int(max_attempts))):
        attempt_seed = int(instance_seed) + int(attempt_index)
        try:
            dataset = sample_rolling_dataset(
                target_slot=str(target_slot_by_query[str(query_id)]),
                params=task_params,
                generation_defaults=generation_defaults,
                instance_seed=attempt_seed,
                namespace="cube_net.rolling",
            )
            font_family = sample_cube_net_font(
                instance_seed=attempt_seed,
                params=task_params,
                rendering_defaults=rendering_defaults,
                namespace="cube_net.rolling",
            )
            with temporary_default_font_family(str(font_family)):
                image, render_meta = render_rolling_scene(
                    dataset=dataset,
                    params=task_params,
                    rendering_defaults=rendering_defaults,
                    instance_seed=attempt_seed,
                    scene_variant=str(scene_variant),
                )
            break
        except ValueError as exc:
            last_error = exc
    else:
        raise RuntimeError(f"{task_identity} failed to construct a sample") from last_error

    image, post_noise_meta = apply_cube_net_post_noise(
        image,
        instance_seed=int(instance_seed),
        params=task_params,
    )
    prompt_defaults, prompt_artifacts = build_cube_net_prompt_artifacts(
        prompt_task_key="rolling_result_label_query",
        prompt_query_key=str(query_id),
        dynamic_slots={},
        instance_seed=int(instance_seed),
    )
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(query_id),
        params={
            "scene_id": SCENE_ID,
            "query_id_probabilities": dict(query_probabilities),
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(scene_probabilities),
            "option_labels": [str(option.option_label) for option in dataset.options],
            "answer_support": [str(option.option_label) for option in dataset.options],
            "path_length": int(len(dataset.path_directions)),
            "target_slot": str(dataset.target_slot),
        },
    )
    option_bbox = render_meta["option_panel_bboxes_px"][
        f"option_{dataset.correct_option_label}"
    ]
    annotation_bboxes = {
        "start_cube": round_annotation_bbox(render_meta["start_cube_bbox_px"]),
        "roll_path": round_annotation_bbox(render_meta["path_panel_bbox_px"]),
        "selected_option": round_annotation_bbox(option_bbox),
    }
    answer_gt = TypedValue(type="option_letter", value=str(dataset.correct_option_label))
    annotation_gt = bbox_map_typed_value(annotation_bboxes)
    render_spec = {
        "canvas_width": int(image.width),
        "canvas_height": int(image.height),
        "coord_space": "pixel",
        "scene_id": SCENE_ID,
        "query_id": str(query_id),
        "scene_variant": str(scene_variant),
        "post_image_noise": dict(post_noise_meta),
        "label_style": {"font": font_trace_record(str(font_family))},
        **dict(render_meta),
    }
    trace_payload = build_cube_net_trace_payload(
        scene_ir={
            "scene_kind": "puzzle_cube_net",
            "scene_id": SCENE_ID,
            "task_id": str(task_identity),
            "entities": [
                {
                    "entity_id": f"face_{face}",
                    "kind": "cube_face",
                    "face_id": str(face),
                    "face_label": str(label),
                }
                for face, label in sorted(dataset.face_labels.items())
            ],
            "relations": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "target_slot": str(dataset.target_slot),
                "correct_face": str(dataset.correct_face),
                "correct_option_label": str(dataset.correct_option_label),
            },
        },
        query_spec=query_spec,
        render_spec=render_spec,
        render_map={
            "image_id": "img0",
            "start_cube_bbox_px": list(render_meta["start_cube_bbox_px"]),
            "path_panel_bbox_px": list(render_meta["path_panel_bbox_px"]),
            "path_cell_bboxes_px": dict(render_meta["path_cell_bboxes_px"]),
            "option_panel_bboxes_px": dict(render_meta["option_panel_bboxes_px"]),
            "annotation_source": "start_cube_bbox_px+path_panel_bbox_px+option_panel_bboxes_px",
        },
        execution_trace={
            "scene_id": SCENE_ID,
            "query_id": str(query_id),
            "scene_variant": str(scene_variant),
            "face_labels": dict(dataset.face_labels),
            "start_orientation": dict(dataset.start_orientation),
            "final_orientation": dict(dataset.final_orientation),
            "target_slot": str(dataset.target_slot),
            "grid_rows": int(dataset.grid_rows),
            "grid_cols": int(dataset.grid_cols),
            "path_cells": [[int(row), int(col)] for row, col in dataset.path_cells],
            "path_directions": [str(direction) for direction in dataset.path_directions],
            "correct_face": str(dataset.correct_face),
            "option_specs": face_option_specs(dataset.options),
            "answer_value": str(dataset.correct_option_label),
        },
        witness_symbolic={
            "type": "cube_rolling_result",
            "value": {
                "path_directions": [str(direction) for direction in dataset.path_directions],
                "target_slot": str(dataset.target_slot),
                "correct_face": str(dataset.correct_face),
                "correct_option_label": str(dataset.correct_option_label),
            },
        },
        projected_annotation=projected_bbox_map(annotation_bboxes),
        answer_gt=answer_gt.to_dict(),
        annotation_gt=annotation_gt.to_dict(),
        prompt_defaults=prompt_defaults,
        prompt_artifacts=prompt_artifacts,
    )
    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        answer_gt=answer_gt,
        annotation_gt=annotation_gt,
        image=image,
        image_id="img0",
        trace_payload=json_ready(trace_payload),
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(query_id),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
    )


def run_surface_path_lifecycle(
    *,
    task_identity: str,
    supported_queries: Sequence[str],
    option_mode: str,
    prompt_task_key: str,
    prompt_query_key: str,
    answer_mode: str,
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> TaskOutput:
    """Run a folded-path task after public files specify answer mode."""

    query_id, query_probabilities, task_params = _select_public_query(
        task_identity=str(task_identity),
        supported_queries=supported_queries,
        instance_seed=int(instance_seed),
        params=dict(params),
    )
    prepared = render_surface_path_case(
        params=task_params,
        generation_defaults=generation_defaults,
        rendering_defaults=rendering_defaults,
        instance_seed=int(instance_seed),
        max_attempts=int(max_attempts),
        option_mode=str(option_mode),
        namespace=f"cube_net.{option_mode}",
    )
    dataset = prepared["dataset"]
    image = prepared["image"]
    render_meta = prepared["render_meta"]
    scene_variant = str(prepared["scene_variant"])
    prompt_defaults, prompt_artifacts = build_cube_net_prompt_artifacts(
        prompt_task_key=str(prompt_task_key),
        prompt_query_key=str(prompt_query_key),
        dynamic_slots={},
        instance_seed=int(instance_seed),
    )
    if str(option_mode) == "endpoint":
        option_specs = face_option_specs(dataset.endpoint_options)
        answer_value = str(dataset.endpoint_correct_option_label)
    elif str(option_mode) == "sequence":
        option_specs = sequence_option_specs(dataset.sequence_options)
        answer_value = str(dataset.sequence_correct_option_label)
    else:
        raise ValueError(f"unsupported folded-path option mode: {option_mode}")
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(query_id),
        params={
            "scene_id": SCENE_ID,
            "query_id_probabilities": dict(query_probabilities),
            "scene_variant": scene_variant,
            "scene_variant_probabilities": dict(prepared["scene_variant_probabilities"]),
            "path_step_count": int(len(dataset.path_sides)),
            "option_labels": [str(option["option_label"]) for option in option_specs],
            "answer_support": [str(option["option_label"]) for option in option_specs],
            "answer_mode": str(answer_mode),
        },
    )
    option_bbox = render_meta["option_panel_bboxes_px"][f"option_{answer_value}"]
    annotation_bboxes = {
        "start_face": round_annotation_bbox(
            render_meta["face_bboxes_px"][str(dataset.start_face)]
        ),
        "move_instructions": round_annotation_bbox(
            render_meta["instruction_panel_bbox_px"]
        ),
        "selected_option": round_annotation_bbox(option_bbox),
    }
    answer_gt = TypedValue(type="option_letter", value=answer_value)
    annotation_gt = bbox_map_typed_value(annotation_bboxes)
    trace_parts = surface_path_trace_parts(
        dataset=dataset,
        option_specs=option_specs,
        scene_variant=scene_variant,
        answer_value=answer_value,
    )
    render_spec = {
        "canvas_width": int(image.width),
        "canvas_height": int(image.height),
        "coord_space": "pixel",
        "scene_id": SCENE_ID,
        "query_id": str(query_id),
        "scene_variant": scene_variant,
        "post_image_noise": dict(prepared["post_noise_meta"]),
        "label_style": {"font": font_trace_record(str(prepared["font_family"]))},
        **dict(render_meta),
    }
    trace_payload = build_cube_net_trace_payload(
        scene_ir={
            "scene_kind": "puzzle_cube_net",
            "scene_id": SCENE_ID,
            "task_id": str(task_identity),
            "entities": trace_parts["entities"],
            "relations": {
                "query_id": str(query_id),
                **dict(trace_parts["relations"]),
            },
        },
        query_spec=query_spec,
        render_spec=render_spec,
        render_map={
            "image_id": "img0",
            "face_bboxes_px": dict(render_meta["face_bboxes_px"]),
            "instruction_panel_bbox_px": list(render_meta["instruction_panel_bbox_px"]),
            "option_panel_bboxes_px": dict(render_meta["option_panel_bboxes_px"]),
            "annotation_source": "face_bboxes_px+instruction_panel_bbox_px+option_panel_bboxes_px",
        },
        execution_trace={
            "query_id": str(query_id),
            **dict(trace_parts["execution_trace"]),
        },
        witness_symbolic=trace_parts["witness_symbolic"],
        projected_annotation=projected_bbox_map(annotation_bboxes),
        answer_gt=answer_gt.to_dict(),
        annotation_gt=annotation_gt.to_dict(),
        prompt_defaults=prompt_defaults,
        prompt_artifacts=prompt_artifacts,
    )
    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        answer_gt=answer_gt,
        annotation_gt=annotation_gt,
        image=image,
        image_id="img0",
        trace_payload=json_ready(trace_payload),
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(query_id),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
    )


__all__ = [
    "apply_cube_net_post_noise",
    "font_trace_record",
    "render_surface_path_case",
    "run_face_relation_lifecycle",
    "run_rolling_lifecycle",
    "run_surface_path_lifecycle",
    "sample_cube_net_font",
    "select_cube_net_scene_variant",
]
