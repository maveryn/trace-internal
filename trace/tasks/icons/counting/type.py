"""Count scene icons that match a reference icon's type."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.counting_sampling import counting_complexity_score, resolve_counting_target_and_distractor_triplet
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.icon_assets import resolve_icon_pool
from ..shared.icon_scene import (
    IconInstanceSpec,
    panel_geometry_to_trace,
    render_two_panel_icon_scene,
    sort_bboxes_reading_order,
)
from ..shared.icon_style import icon_palette_meets_distance_constraints, sample_icon_palette, sample_icon_tints
from .defaults import ICON_COUNTING_SHARED_DEFAULTS
from .shared import (
    icon_counting_style_trace,
    resolve_icon_counting_render_params,
    sample_icon_instance_noise,
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for reference-icon type counting."""

    object_count_min: int = ICON_COUNTING_SHARED_DEFAULTS.object_count_min
    object_count_max: int = ICON_COUNTING_SHARED_DEFAULTS.object_count_max
    canvas_width: int = ICON_COUNTING_SHARED_DEFAULTS.canvas_width
    canvas_height: int = ICON_COUNTING_SHARED_DEFAULTS.canvas_height
    reference_panel_width_px: int = ICON_COUNTING_SHARED_DEFAULTS.reference_panel_width_px
    panel_gap_px: int = ICON_COUNTING_SHARED_DEFAULTS.panel_gap_px
    outer_margin_px: int = ICON_COUNTING_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_COUNTING_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_COUNTING_SHARED_DEFAULTS.panel_corner_radius_px
    scene_icon_size_min_px: int = ICON_COUNTING_SHARED_DEFAULTS.scene_icon_size_min_px
    scene_icon_size_max_px: int = ICON_COUNTING_SHARED_DEFAULTS.scene_icon_size_max_px
    reference_icon_size_px: int = ICON_COUNTING_SHARED_DEFAULTS.reference_icon_size_px
    distractor_count_min: int = ICON_COUNTING_SHARED_DEFAULTS.distractor_count_min
    distractor_count_max: int = ICON_COUNTING_SHARED_DEFAULTS.distractor_count_max
    scene_max_overlap_fraction: float = ICON_COUNTING_SHARED_DEFAULTS.scene_max_overlap_fraction
    scene_placement_max_attempts: int = ICON_COUNTING_SHARED_DEFAULTS.scene_placement_max_attempts
    scene_size_shrink_rounds: int = ICON_COUNTING_SHARED_DEFAULTS.scene_size_shrink_rounds
    scene_size_shrink_factor: float = ICON_COUNTING_SHARED_DEFAULTS.scene_size_shrink_factor
    panel_title_font_size_px: int = ICON_COUNTING_SHARED_DEFAULTS.panel_title_font_size_px
    pool_manifest: str = "all_icons.txt"
    palette_size_min: int = 8
    palette_size_max: int = 12
    color_channel_min: int = 24
    color_channel_max: int = 220
    min_color_distance: float = 40.0
    color_distance_space: str = "lab"
    background_color_rgb: Tuple[int, int, int] = ICON_COUNTING_SHARED_DEFAULTS.background_color_rgb
    panel_fill_rgb: Tuple[int, int, int] = ICON_COUNTING_SHARED_DEFAULTS.panel_fill_rgb
    panel_border_rgb: Tuple[int, int, int] = ICON_COUNTING_SHARED_DEFAULTS.panel_border_rgb
    header_text_rgb: Tuple[int, int, int] = ICON_COUNTING_SHARED_DEFAULTS.header_text_rgb


@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready payload for one icon type-counting instance."""

    object_count: int
    target_count: int
    distractor_count: int
    reference_icon_id: str
    scene_icon_ids: Tuple[str, ...]
    match_indices: Tuple[int, ...]
    match_bboxes: Tuple[Tuple[int, int, int, int], ...]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    panel_geometry: Dict[str, Any]
    scene_instances: Tuple[Dict[str, Any], ...]
    reference_instance: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="task_icons_counting_type",
)


def _sample_scene(
    rng,
    *,
    instance_seed: int,
    object_count: int,
    target_count: int,
    pool_manifest: str,
    render_params: Mapping[str, Any],
) -> Tuple[_ScenePayload, Any]:
    """Sample and render one reference+scene icon type-counting scene."""

    pool = list(resolve_icon_pool(str(pool_manifest)))
    if len(pool) < int(object_count) + 1:
        raise ValueError("icon pool is too small for requested type-counting scene")

    reference_icon_id = str(rng.choice(pool))
    distractor_pool = [str(icon_id) for icon_id in pool if str(icon_id) != str(reference_icon_id)]
    if len(distractor_pool) < int(object_count) - int(target_count):
        raise ValueError("insufficient distractor icons for type-counting scene")

    match_indices = set(rng.sample(list(range(int(object_count))), int(target_count)))
    palette_size = int(rng.randint(int(render_params["palette_size_min"]), int(render_params["palette_size_max"])))
    palette = sample_icon_palette(
        rng,
        palette_size=int(palette_size),
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
    if not icon_palette_meets_distance_constraints(
        palette=palette,
        anchor_colors=(
            tuple(int(v) for v in render_params["background_color_rgb"]),
            tuple(int(v) for v in render_params["panel_fill_rgb"]),
            tuple(int(v) for v in render_params["panel_border_rgb"]),
            tuple(int(v) for v in render_params["header_text_rgb"]),
        ),
        min_color_distance=float(render_params["min_color_distance"]),
        distance_space=str(render_params["color_distance_space"]),
    ):
        raise ValueError("sampled icon palette did not satisfy strict distance constraints")
    sampled_tints = list(sample_icon_tints(rng, palette=palette, count=int(object_count) + 1))
    reference_tint = tuple(int(v) for v in sampled_tints.pop(0))
    distractor_ids = list(rng.sample(distractor_pool, int(object_count) - int(target_count)))
    scene_specs: List[IconInstanceSpec] = []
    scene_icon_ids: List[str] = []
    for index in range(int(object_count)):
        if int(index) in match_indices:
            icon_id = str(reference_icon_id)
        else:
            icon_id = str(distractor_ids.pop())
        scene_icon_ids.append(str(icon_id))
        scene_specs.append(
            IconInstanceSpec(
                icon_id=str(icon_id),
                rotation_degrees=0,
                tint_rgb=tuple(int(v) for v in sampled_tints.pop(0)),
            )
        )

    reference_noise_edits, reference_noise_seed = sample_icon_instance_noise(
        instance_seed=int(instance_seed),
        namespace=f"{IconsCountingTypeTask.task_id}:reference_icon",
        render_params=render_params,
    )
    for index, spec in enumerate(list(scene_specs)):
        scene_noise_edits, scene_noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{IconsCountingTypeTask.task_id}:scene_icon_{int(index)}",
            render_params=render_params,
        )
        scene_specs[index] = IconInstanceSpec(
            icon_id=str(spec.icon_id),
            rotation_degrees=int(spec.rotation_degrees),
            mirror_x=bool(spec.mirror_x),
            tint_rgb=tuple(int(v) for v in spec.tint_rgb),
            noise_edits=tuple(scene_noise_edits),
            noise_seed=int(scene_noise_seed),
        )

    rendered = render_two_panel_icon_scene(
        rng=rng,
        reference_icon=IconInstanceSpec(
            icon_id=str(reference_icon_id),
            rotation_degrees=0,
            tint_rgb=tuple(int(v) for v in reference_tint),
            noise_edits=tuple(reference_noise_edits),
            noise_seed=int(reference_noise_seed),
        ),
        scene_icons=scene_specs,
        canvas_width=int(render_params["canvas_width"]),
        canvas_height=int(render_params["canvas_height"]),
        reference_panel_width_px=int(render_params["reference_panel_width_px"]),
        outer_margin_px=int(render_params["outer_margin_px"]),
        panel_gap_px=int(render_params["panel_gap_px"]),
        panel_padding_px=int(render_params["panel_padding_px"]),
        panel_corner_radius_px=int(render_params["panel_corner_radius_px"]),
        scene_icon_size_min_px=int(render_params["scene_icon_size_min_px"]),
        scene_icon_size_max_px=int(render_params["scene_icon_size_max_px"]),
        reference_icon_size_px=int(render_params["reference_icon_size_px"]),
        scene_max_overlap_fraction=float(render_params["scene_max_overlap_fraction"]),
        scene_placement_max_attempts=int(render_params["scene_placement_max_attempts"]),
        scene_size_shrink_rounds=int(render_params["scene_size_shrink_rounds"]),
        scene_size_shrink_factor=float(render_params["scene_size_shrink_factor"]),
        background_rgb=tuple(int(v) for v in render_params["background_color_rgb"]),
        panel_fill_rgb=tuple(int(v) for v in render_params["panel_fill_rgb"]),
        panel_border_rgb=tuple(int(v) for v in render_params["panel_border_rgb"]),
        title_color_rgb=tuple(int(v) for v in render_params["header_text_rgb"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
    )
    match_bboxes = tuple(
        tuple(int(value) for value in rendered.scene_instances[int(index)].bbox_xyxy)
        for index in sorted(int(value) for value in match_indices)
    )
    scene_instances = tuple(
        {
            "instance_id": str(instance.instance_id),
            "icon_id": str(instance.icon_id),
            "panel": str(instance.panel),
            "bbox_xyxy": list(instance.bbox_xyxy),
            "rotation_degrees": int(instance.rotation_degrees),
            "mirror_x": bool(instance.mirror_x),
            "tint_rgb": list(instance.tint_rgb),
            "noise_edits": [dict(edit) for edit in instance.noise_edits],
            "noise_seed": None if instance.noise_seed is None else int(instance.noise_seed),
            "is_match": bool(scene_icon_ids[index] == reference_icon_id),
            "index": int(index),
        }
        for index, instance in enumerate(rendered.scene_instances)
    )
    reference_instance = {
        "instance_id": str(rendered.reference_instance.instance_id),
        "icon_id": str(rendered.reference_instance.icon_id),
        "panel": str(rendered.reference_instance.panel),
        "bbox_xyxy": list(rendered.reference_instance.bbox_xyxy),
        "rotation_degrees": int(rendered.reference_instance.rotation_degrees),
        "mirror_x": bool(rendered.reference_instance.mirror_x),
        "tint_rgb": list(rendered.reference_instance.tint_rgb),
        "noise_edits": [dict(edit) for edit in rendered.reference_instance.noise_edits],
        "noise_seed": None if rendered.reference_instance.noise_seed is None else int(rendered.reference_instance.noise_seed),
    }
    return _ScenePayload(
        object_count=int(object_count),
        target_count=int(target_count),
        distractor_count=int(object_count) - int(target_count),
        reference_icon_id=str(reference_icon_id),
        scene_icon_ids=tuple(str(icon_id) for icon_id in scene_icon_ids),
        match_indices=tuple(sorted(int(value) for value in match_indices)),
        match_bboxes=match_bboxes,
        sampled_palette_rgb=tuple(tuple(int(channel) for channel in color) for color in palette),
        panel_geometry=panel_geometry_to_trace(rendered.layout),
        scene_instances=scene_instances,
        reference_instance=reference_instance,
    ), rendered.image


@register_task
class IconsCountingTypeTask:
    """Count scene icons that match a reference icon's type."""

    task_id = "task_icons_counting_type"
    domain = "icons"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic reference-icon type counting instance."""

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
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            fallback_total_min=_DEFAULTS.object_count_min,
            fallback_total_max=_DEFAULTS.object_count_max,
            fallback_target_min=0,
            fallback_target_max=10,
            fallback_distractor_min=_DEFAULTS.distractor_count_min,
            fallback_distractor_max=_DEFAULTS.distractor_count_max,
        )
        render_params = resolve_icon_counting_render_params(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
        )
        pool_manifest = str(params.get("pool_manifest", group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest)))

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
                    render_params=render_params,
                )
                break
            except Exception as exc:
                last_error = exc
                continue
        if scene_payload is None or image is None:
            raise RuntimeError("failed to generate task_icons_counting_type instance") from last_error

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "task_family_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "question_text",
                "evidence_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(prompt_defaults["question_text"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_bboxes = sort_bboxes_reading_order(scene_payload.match_bboxes)
        answer_gt = TypedValue(type="integer", value=int(scene_payload.target_count))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_reference_counting_type",
                "entities": [dict(scene_payload.reference_instance), *[dict(item) for item in scene_payload.scene_instances]],
                "relations": {
                    "counting_target": "same_icon_type_as_reference",
                    "reference_icon_id": str(scene_payload.reference_icon_id),
                    "matching_scene_indices": list(scene_payload.match_indices),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene_payload.panel_geometry),
                },
            },
            "query_spec": {
                "task_variant": "same_icon_type",
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "object_count": int(object_count),
                    "object_count_probabilities": dict(object_count_probabilities),
                    "target_count": int(target_count),
                    "target_count_probabilities": dict(target_count_probabilities),
                    "distractor_count": int(distractor_count),
                    "distractor_count_probabilities": dict(distractor_count_probabilities),
                    "pool_manifest": str(pool_manifest),
                },
            },
            "render_spec": {
                "canvas_size": [int(render_params["canvas_width"]), int(render_params["canvas_height"])],
                "coord_space": "pixel",
                "panel_geometry": dict(scene_payload.panel_geometry),
                "style": icon_counting_style_trace(
                    render_params=render_params,
                    sampled_palette_rgb=scene_payload.sampled_palette_rgb,
                ),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {
                    "reference_icon": dict(scene_payload.reference_instance),
                    "matching_scene_boxes": list(evidence_bboxes),
                },
            },
            "execution_trace": {
                "scene_variant": "reference_scene",
                "task_variant": "same_icon_type",
                "object_count": int(object_count),
                "object_count_probabilities": dict(object_count_probabilities),
                "target_count": int(target_count),
                "target_count_probabilities": dict(target_count_probabilities),
                "distractor_count": int(distractor_count),
                "distractor_count_probabilities": dict(distractor_count_probabilities),
                "reference_icon_id": str(scene_payload.reference_icon_id),
                "scene_icon_ids": list(scene_payload.scene_icon_ids),
                "matching_scene_indices": list(scene_payload.match_indices),
                "question_format": "count_matching_scene_icons_by_reference",
            },
            "witness_symbolic": {
                "reference_icon_id": str(scene_payload.reference_icon_id),
                "matching_scene_indices": list(scene_payload.match_indices),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
            },
        }
        complexity = TaskComplexity(
            complexity_score=counting_complexity_score(
                object_count=int(scene_payload.object_count),
                target_count=int(scene_payload.target_count),
            ),
            complexity_components={
                "object_count": int(scene_payload.object_count),
                "target_count": int(scene_payload.target_count),
                "task_variant": "same_icon_type",
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant="same_icon_type",
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["IconsCountingTypeTask"]
