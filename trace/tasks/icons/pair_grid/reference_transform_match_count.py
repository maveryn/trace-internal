"""Count labeled scene cells that follow a reference icon-pair transformation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    load_scene_generation_rendering_prompt_defaults,
    required_group_defaults,
)
from ...shared.counting_sampling import resolve_counting_target_and_distractor_triplet
from ...shared.fixed_query import select_task_query_id
from ...shared.labeling import LABEL_POOL_A_L
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_query_spec,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ..shared.icon_assets import icon_transform_signature, resolve_icon_pool
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.icon_style import sample_single_icon_tint
from ..shared.icon_task_rendering import sample_icon_instance_noise
from ..shared.icon_transform import IDENTITY_TRANSFORM_ID, NON_IDENTITY_TRANSFORM_IDS
from ..shared.annotation import matching_scene_cell_bbox_annotation

from .shared.rendering import panel_geometry_to_trace, render_two_panel_icon_pair_grid_scene
from .shared.state import IconPairSpec
from .shared.styles import pair_grid_style_trace, resolve_pair_grid_render_params


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for icon transformation pair counting."""

    object_count_min: int = 2
    object_count_max: int = 12
    target_count_min: int = 0
    target_count_max: int = 6
    distractor_count_min: int = 1
    distractor_count_max: int = 6
    canvas_width: int = 1104
    canvas_height: int = 640
    reference_panel_width_px: int = 296
    panel_gap_px: int = ICON_SHARED_DEFAULTS.panel_gap_px
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    scene_icon_size_min_px: int = 40
    scene_icon_size_max_px: int = 96
    reference_icon_size_px: int = 110
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    background_color_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.background_color_rgb
    panel_fill_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_fill_rgb
    panel_border_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_border_rgb
    header_text_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.header_text_rgb
    cell_border_rgb: Tuple[int, int, int] = (218, 223, 233)
    cell_label_color_rgb: Tuple[int, int, int] = (52, 60, 77)
    arrow_color_rgb: Tuple[int, int, int] = (84, 96, 118)
    cell_padding_px: int = 10
    pair_arrow_stroke_px: int = 4
    cell_label_font_size_px: int = 22
    pool_manifest: str = "non_symmetry.txt"
    transform_ids: Tuple[str, ...] = NON_IDENTITY_TRANSFORM_IDS
    transform_check_size_px: int = 72
    palette_size_min: int = 1
    palette_size_max: int = 1
    color_channel_min: int = 24
    color_channel_max: int = 220
    min_color_distance: float = 40.0
    color_distance_space: str = "lab"
    icon_noise_edit_types: Tuple[str, ...] = ICON_SHARED_DEFAULTS.icon_noise_edit_types
    icon_noise_edit_count_range: Tuple[int, int] = ICON_SHARED_DEFAULTS.icon_noise_edit_count_range
    icon_noise_value_ranges: Dict[str, Dict[str, Tuple[float, float]]] = field(
        default_factory=lambda: deepcopy(ICON_SHARED_DEFAULTS.icon_noise_value_ranges)
    )


@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready payload for one transformation-pair counting scene."""

    object_count: int
    target_count: int
    distractor_count: int
    reference_transform_id: str
    reference_icon_id: str
    cell_labels: Tuple[str, ...]
    matching_labels: Tuple[str, ...]
    cell_icon_ids: Tuple[str, ...]
    cell_transform_ids: Tuple[str, ...]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    panel_geometry: Dict[str, Any]
    reference_pair: Dict[str, Any]
    scene_cells: Tuple[Dict[str, Any], ...]


_DEFAULTS = _TaskDefaults()
TASK_ID = "task_icons__pair_grid__reference_transform_match_count"
DOMAIN = "icons"
SCENE_ID = "pair_grid"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("single",)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    DOMAIN,
    SCENE_ID,
    task_id=TASK_ID,
)


def _select_query(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float], Dict[str, Any]]:
    """Select and validate the single public query contract."""

    return select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id="single",
        task_id=TASK_ID,
        namespace=f"{TASK_ID}.query",
    )


def _resolve_transform_ids(params: Mapping[str, Any]) -> Tuple[str, ...]:
    """Resolve the supported non-identity transform ids for the task."""

    raw = params.get("transform_ids", group_default(_GEN_DEFAULTS, "transform_ids", list(_DEFAULTS.transform_ids)))
    if not isinstance(raw, (list, tuple)):
        raise ValueError("transform_ids must be a sequence")
    transform_ids = tuple(str(value).strip() for value in raw if str(value).strip())
    if not transform_ids:
        raise ValueError("transform_ids resolved no transforms")
    unsupported = [value for value in transform_ids if value not in set(NON_IDENTITY_TRANSFORM_IDS)]
    if unsupported:
        raise ValueError(f"unsupported transform_ids: {unsupported}")
    return transform_ids


def _distinct_distractor_transforms(icon_id: str, *, reference_transform_id: str, check_size_px: int, transform_ids: Sequence[str]) -> Tuple[str, ...]:
    """Return non-identity transforms that remain visually distinct for one icon."""

    identity_signature = icon_transform_signature(str(icon_id), int(check_size_px), IDENTITY_TRANSFORM_ID)
    reference_signature = icon_transform_signature(str(icon_id), int(check_size_px), str(reference_transform_id))
    if reference_signature == identity_signature:
        return ()
    distractors = [
        str(transform_id)
        for transform_id in transform_ids
        if str(transform_id) != str(reference_transform_id)
        and icon_transform_signature(str(icon_id), int(check_size_px), str(transform_id)) != identity_signature
        and icon_transform_signature(str(icon_id), int(check_size_px), str(transform_id)) != reference_signature
    ]
    return tuple(str(value) for value in distractors)


def _sample_scene(
    rng,
    *,
    instance_seed: int,
    object_count: int,
    target_count: int,
    pool_manifest: str,
    transform_ids: Sequence[str],
    transform_check_size_px: int,
    render_params: Mapping[str, Any],
) -> Tuple[_ScenePayload, Any]:
    """Sample and render one reference-pair transformation counting scene."""

    pool = list(resolve_icon_pool(str(pool_manifest)))
    if len(pool) < int(object_count) + 1:
        raise ValueError("icon pool is too small for requested transformation scene")
    reference_transform_id = str(rng.choice(list(transform_ids)))

    candidate_records: List[Tuple[str, Tuple[str, ...]]] = []
    shuffled_pool = list(pool)
    rng.shuffle(shuffled_pool)
    for icon_id in shuffled_pool:
        distractors = _distinct_distractor_transforms(
            str(icon_id),
            reference_transform_id=str(reference_transform_id),
            check_size_px=int(transform_check_size_px),
            transform_ids=transform_ids,
        )
        if distractors:
            candidate_records.append((str(icon_id), tuple(str(value) for value in distractors)))
        if len(candidate_records) >= int(object_count) + 1:
            break
    if len(candidate_records) < int(object_count) + 1:
        raise ValueError("insufficient transform-distinct icons for transformation scene")

    reference_icon_id, _ = candidate_records[0]
    scene_records = list(candidate_records[1 : 1 + int(object_count)])
    labels = tuple(str(value) for value in LABEL_POOL_A_L[: int(object_count)])
    match_indices = set(rng.sample(list(range(int(object_count))), int(target_count)))
    tint_rgb, sampled_palette_rgb = sample_single_icon_tint(
        rng,
        channel_min=int(render_params["color_channel_min"]),
        channel_max=int(render_params["color_channel_max"]),
        anchor_colors=(
            tuple(int(v) for v in render_params["background_color_rgb"]),
            tuple(int(v) for v in render_params["panel_fill_rgb"]),
            tuple(int(v) for v in render_params["panel_border_rgb"]),
            tuple(int(v) for v in render_params["header_text_rgb"]),
        ),
        min_color_distance=float(render_params["min_color_distance"]),
        distance_space=str(render_params["color_distance_space"]),
    )

    reference_left_noise_edits, reference_left_noise_seed = sample_icon_instance_noise(
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:reference_left",
        render_params=render_params,
    )
    reference_right_noise_edits, reference_right_noise_seed = sample_icon_instance_noise(
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:reference_right",
        render_params=render_params,
    )
    reference_pair = IconPairSpec(
        icon_id=str(reference_icon_id),
        transform_id=str(reference_transform_id),
        tint_rgb=tuple(int(v) for v in tint_rgb),
        left_noise_edits=tuple(reference_left_noise_edits),
        left_noise_seed=int(reference_left_noise_seed),
        right_noise_edits=tuple(reference_right_noise_edits),
        right_noise_seed=int(reference_right_noise_seed),
    )

    scene_pairs: List[IconPairSpec] = []
    scene_icon_ids: List[str] = []
    scene_transform_ids: List[str] = []
    matching_labels: List[str] = []
    for index, (label, record) in enumerate(zip(labels, scene_records)):
        icon_id, distractor_options = record
        transform_id = (
            str(reference_transform_id)
            if int(index) in match_indices
            else str(rng.choice(list(distractor_options)))
        )
        if int(index) in match_indices:
            matching_labels.append(str(label))
        scene_icon_ids.append(str(icon_id))
        scene_transform_ids.append(str(transform_id))
        left_noise_edits, left_noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:scene_{int(index)}_left",
            render_params=render_params,
        )
        right_noise_edits, right_noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:scene_{int(index)}_right",
            render_params=render_params,
        )
        scene_pairs.append(
            IconPairSpec(
                icon_id=str(icon_id),
                transform_id=str(transform_id),
                tint_rgb=tuple(int(v) for v in tint_rgb),
                left_noise_edits=tuple(left_noise_edits),
                left_noise_seed=int(left_noise_seed),
                right_noise_edits=tuple(right_noise_edits),
                right_noise_seed=int(right_noise_seed),
            )
        )

    rendered = render_two_panel_icon_pair_grid_scene(
        reference_pair=reference_pair,
        scene_pairs=scene_pairs,
        scene_labels=labels,
        canvas_width=int(render_params["canvas_width"]),
        canvas_height=int(render_params["canvas_height"]),
        reference_panel_width_px=int(render_params["reference_panel_width_px"]),
        outer_margin_px=int(render_params["outer_margin_px"]),
        panel_gap_px=int(render_params["panel_gap_px"]),
        panel_padding_px=int(render_params["panel_padding_px"]),
        panel_corner_radius_px=int(render_params["panel_corner_radius_px"]),
        cell_padding_px=int(render_params["cell_padding_px"]),
        scene_icon_size_min_px=int(render_params["scene_icon_size_min_px"]),
        scene_icon_size_max_px=int(render_params["scene_icon_size_max_px"]),
        reference_icon_size_px=int(render_params["reference_icon_size_px"]),
        pair_arrow_stroke_px=int(render_params["pair_arrow_stroke_px"]),
        cell_label_font_size_px=int(render_params["cell_label_font_size_px"]),
        panel_title_font_size_px=int(render_params["panel_title_font_size_px"]),
        background_rgb=tuple(int(v) for v in render_params["background_color_rgb"]),
        panel_fill_rgb=tuple(int(v) for v in render_params["panel_fill_rgb"]),
        panel_border_rgb=tuple(int(v) for v in render_params["panel_border_rgb"]),
        title_color_rgb=tuple(int(v) for v in render_params["header_text_rgb"]),
        cell_border_rgb=tuple(int(v) for v in render_params["cell_border_rgb"]),
        cell_label_color_rgb=tuple(int(v) for v in render_params["cell_label_color_rgb"]),
        cell_label_stroke_rgb=tuple(int(v) for v in render_params["cell_label_stroke_rgb"]),
        cell_label_stroke_width_px=1,
        arrow_color_rgb=tuple(int(v) for v in render_params["arrow_color_rgb"]),
        icon_canvas_style=render_params.get("_icon_canvas_style_object"),
    )

    reference_payload = {
        "panel": "reference",
        "icon_id": str(rendered.reference_pair.icon_id),
        "transform_id": str(rendered.reference_pair.transform_id),
        "tint_rgb": list(rendered.reference_pair.tint_rgb),
        "left_bbox_xyxy": list(rendered.reference_pair.left_bbox_xyxy),
        "right_bbox_xyxy": list(rendered.reference_pair.right_bbox_xyxy),
        "left_noise_edits": [dict(edit) for edit in rendered.reference_pair.left_noise_edits],
        "left_noise_seed": None
        if rendered.reference_pair.left_noise_seed is None
        else int(rendered.reference_pair.left_noise_seed),
        "right_noise_edits": [dict(edit) for edit in rendered.reference_pair.right_noise_edits],
        "right_noise_seed": None
        if rendered.reference_pair.right_noise_seed is None
        else int(rendered.reference_pair.right_noise_seed),
    }
    scene_cells = tuple(
        {
            "panel": "scene",
            "label": str(cell.label),
            "icon_id": str(cell.icon_id),
            "transform_id": str(cell.transform_id),
            "tint_rgb": list(cell.tint_rgb),
            "cell_bbox_xyxy": list(cell.cell_bbox_xyxy),
            "left_bbox_xyxy": list(cell.left_bbox_xyxy),
            "right_bbox_xyxy": list(cell.right_bbox_xyxy),
            "left_noise_edits": [dict(edit) for edit in cell.left_noise_edits],
            "left_noise_seed": None if cell.left_noise_seed is None else int(cell.left_noise_seed),
            "right_noise_edits": [dict(edit) for edit in cell.right_noise_edits],
            "right_noise_seed": None if cell.right_noise_seed is None else int(cell.right_noise_seed),
            "is_match": bool(str(cell.label) in set(matching_labels)),
            "index": int(index),
        }
        for index, cell in enumerate(rendered.scene_cells)
    )
    return _ScenePayload(
        object_count=int(object_count),
        target_count=int(target_count),
        distractor_count=int(object_count) - int(target_count),
        reference_transform_id=str(reference_transform_id),
        reference_icon_id=str(reference_icon_id),
        cell_labels=tuple(str(value) for value in labels),
        matching_labels=tuple(sorted(str(value) for value in matching_labels)),
        cell_icon_ids=tuple(str(value) for value in scene_icon_ids),
        cell_transform_ids=tuple(str(value) for value in scene_transform_ids),
        sampled_palette_rgb=tuple(sampled_palette_rgb),
        panel_geometry=panel_geometry_to_trace(rendered.layout),
        reference_pair=reference_payload,
        scene_cells=scene_cells,
    ), rendered.image


@register_task
class IconsPairGridReferenceTransformMatchCountTask:
    """Count scene grid cells that match a reference icon-pair transform."""

    task_id = TASK_ID
    domain = DOMAIN
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic icon transformation pair-count instance."""

        query_id, query_probabilities, task_params = _select_query(int(instance_seed), params)
        scene_rng = spawn_rng(int(instance_seed), "scene")
        (
            object_count,
            object_count_probabilities,
            target_count,
            target_count_probabilities,
            distractor_count,
            distractor_count_probabilities,
        ) = resolve_counting_target_and_distractor_triplet(
            scene_rng,
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            fallback_total_min=_DEFAULTS.object_count_min,
            fallback_total_max=_DEFAULTS.object_count_max,
            fallback_target_min=_DEFAULTS.target_count_min,
            fallback_target_max=_DEFAULTS.target_count_max,
            fallback_distractor_min=_DEFAULTS.distractor_count_min,
            fallback_distractor_max=_DEFAULTS.distractor_count_max,
        )
        render_params = resolve_pair_grid_render_params(
            params=task_params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        pool_manifest = str(task_params.get("pool_manifest", group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest)))
        transform_ids = _resolve_transform_ids(task_params)
        transform_check_size_px = int(
            task_params.get(
                "transform_check_size_px",
                group_default(_GEN_DEFAULTS, "transform_check_size_px", _DEFAULTS.transform_check_size_px),
            )
        )

        scene_payload = None
        image = None
        last_error: Exception | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                scene_payload, image = _sample_scene(
                    scene_rng,
                    instance_seed=int(instance_seed),
                    object_count=int(object_count),
                    target_count=int(target_count),
                    pool_manifest=str(pool_manifest),
                    transform_ids=transform_ids,
                    transform_check_size_px=int(transform_check_size_px),
                    render_params=render_params,
                )
                break
            except Exception as exc:
                last_error = exc
                continue
        if scene_payload is None or image is None:
            raise RuntimeError(f"failed to generate {self.task_id} instance") from last_error

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "question_text",
                "annotation_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            dynamic_slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(prompt_defaults["question_text"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        annotation_labels = list(scene_payload.matching_labels)
        annotation_artifacts = matching_scene_cell_bbox_annotation(
            scene_cells=scene_payload.scene_cells,
            matching_labels=annotation_labels,
        )
        answer_gt = TypedValue(type="integer", value=int(scene_payload.target_count))
        annotation_gt = TypedValue(
            type=str(annotation_artifacts["annotation_type"]),
            value=list(annotation_artifacts["annotation_value"]),
        )
        query_spec = build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(query_id),
            params={
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id_probabilities": dict(query_probabilities),
                "object_count": int(object_count),
                "object_count_probabilities": dict(object_count_probabilities),
                "target_count": int(target_count),
                "target_count_probabilities": dict(target_count_probabilities),
                "distractor_count": int(distractor_count),
                "distractor_count_probabilities": dict(distractor_count_probabilities),
                "pool_manifest": str(pool_manifest),
                "transform_ids": list(transform_ids),
                "transform_check_size_px": int(transform_check_size_px),
            },
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_reference_pair_transformation_count",
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "entities": [dict(scene_payload.reference_pair), *[dict(item) for item in scene_payload.scene_cells]],
                "relations": {
                    "counting_target": "same_geometric_transform_as_reference",
                    "reference_transform_id": str(scene_payload.reference_transform_id),
                    "matching_cell_labels": list(scene_payload.matching_labels),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene_payload.panel_geometry),
                },
            },
            "query_spec": dict(query_spec),
            "render_spec": {
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "canvas_size": [int(render_params["canvas_width"]), int(render_params["canvas_height"])],
                "coord_space": "pixel",
                "panel_geometry": dict(scene_payload.panel_geometry),
                "style": pair_grid_style_trace(
                    render_params=render_params,
                    sampled_palette_rgb=scene_payload.sampled_palette_rgb,
                ),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {
                    "reference_pair": dict(scene_payload.reference_pair),
                    "matching_cell_labels": list(scene_payload.matching_labels),
                    "scene_cells": [dict(item) for item in scene_payload.scene_cells],
                },
            },
            "execution_trace": {
                "scene_variant": "reference_pair_grid",
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "query_id_probabilities": dict(query_probabilities),
                "object_count": int(object_count),
                "object_count_probabilities": dict(object_count_probabilities),
                "target_count": int(target_count),
                "target_count_probabilities": dict(target_count_probabilities),
                "distractor_count": int(distractor_count),
                "distractor_count_probabilities": dict(distractor_count_probabilities),
                "reference_transform_id": str(scene_payload.reference_transform_id),
                "reference_icon_id": str(scene_payload.reference_icon_id),
                "cell_labels": list(scene_payload.cell_labels),
                "matching_cell_labels": list(scene_payload.matching_labels),
                "cell_icon_ids": list(scene_payload.cell_icon_ids),
                "cell_transform_ids": list(scene_payload.cell_transform_ids),
                "question_format": "count_scene_cells_matching_reference_transform",
            },
            "witness_symbolic": {
                "reference_transform_id": str(scene_payload.reference_transform_id),
                **dict(annotation_artifacts["witness_symbolic"]),
            },
            "projected_annotation": dict(annotation_artifacts["projected_annotation"]),
        }
        output = TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
        return output


__all__ = ["IconsPairGridReferenceTransformMatchCountTask"]
