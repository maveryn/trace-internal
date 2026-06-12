"""Count icons added to or removed from the right panel."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from .....core.scene_config import get_scene_defaults
from .....core.seed import hash64
from ....shared.config_defaults import group_default, split_generation_rendering_prompt_defaults
from ...shared.icon_task_rendering import resolve_icon_render_params
from .common import (
    PANEL_SCENE_ID,
    PairedCanvasDefaults,
    PairedCanvasPayload,
    build_paired_prompt,
    choose_query_id,
    annotation_from_indices,
    make_icon_spec,
    paired_task_output,
    render_paired_canvas,
    required_paired_prompt_defaults,
    resolve_icon_pool,
    resolve_paired_counts,
    sample_base_attributes,
    sample_palette,
    sample_positions,
    spawn_rng,
)


TASK_ID = "task_icons__paired_canvas__panel_set_relation_count"
QUERY_IDS = ("added_in_right_count", "missing_from_right_count")
_DEFAULTS = PairedCanvasDefaults()
_SCENE_DEFAULTS = get_scene_defaults("icons", PANEL_SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _make_scene(*, instance_seed: int, params: Mapping[str, Any], render_params: Mapping[str, Any]) -> PairedCanvasPayload:
    rng = spawn_rng(int(instance_seed), "scene")
    query_id, query_probabilities = choose_query_id(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        query_ids=QUERY_IDS,
        weight_key="change_query_weights",
    )
    counting_params = dict(params)
    (
        diff_object_count,
        object_count_probabilities,
        target_count,
        target_count_probabilities,
        distractor_count,
        distractor_count_probabilities,
    ) = resolve_paired_counts(
        rng,
        instance_seed=int(instance_seed),
        params=counting_params,
        gen_defaults=_GEN_DEFAULTS,
        defaults=_DEFAULTS,
    )
    common_min = int(params.get("common_count_min", group_default(_GEN_DEFAULTS, "common_count_min", 3)))
    common_max = int(params.get("common_count_max", group_default(_GEN_DEFAULTS, "common_count_max", 6)))
    common_count = int(rng.randint(common_min, max(common_min, common_max)))
    added_count = int(target_count if query_id == "added_in_right_count" else distractor_count)
    removed_count = int(target_count if query_id == "missing_from_right_count" else distractor_count)
    total_unique = int(common_count) + int(added_count) + int(removed_count)

    pool = list(resolve_icon_pool(str(params.get("pool_manifest", group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest)))))
    rng.shuffle(pool)
    if len(pool) < total_unique:
        raise ValueError("icon pool is too small for paired added/removed scene")
    palette = sample_palette(rng, render_params=render_params)
    rotation_candidates = tuple(
        int(value)
        for value in params.get(
            "rotation_candidates_degrees",
            group_default(_GEN_DEFAULTS, "rotation_candidates_degrees", _DEFAULTS.rotation_candidates_degrees),
        )
    )
    attrs = sample_base_attributes(
        rng,
        pool=pool,
        palette=palette,
        count=total_unique,
        render_params=render_params,
        rotation_candidates=rotation_candidates,
    )
    common_attrs = attrs[:common_count]
    added_attrs = attrs[common_count : common_count + added_count]
    removed_attrs = attrs[common_count + added_count :]
    left_attrs = list(common_attrs) + list(removed_attrs)
    right_attrs = list(common_attrs) + list(added_attrs)
    rng.shuffle(left_attrs)
    rng.shuffle(right_attrs)
    gap = float(params.get("min_center_gap_frac", group_default(_RENDER_DEFAULTS, "min_center_gap_frac", _DEFAULTS.min_center_gap_frac)))
    left_positions = sample_positions(rng, count=len(left_attrs), min_gap_frac=gap)
    right_positions = sample_positions(rng, count=len(right_attrs), min_gap_frac=gap)
    left_specs = []
    right_specs = []
    for index, (attr, pos) in enumerate(zip(left_attrs, left_positions)):
        left_specs.append(
            make_icon_spec(
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}:left:{index}",
                render_params=render_params,
                instance_id=f"left_{index}",
                identity_id=str(attr["identity_id"]),
                icon_id=str(attr["icon_id"]),
                panel="left",
                position=pos,
                tint_rgb=tuple(attr["tint_rgb"]),
                size_px=int(attr["size_px"]),
                rotation_degrees=int(attr["rotation_degrees"]),
            )
        )
    for index, (attr, pos) in enumerate(zip(right_attrs, right_positions)):
        right_specs.append(
            make_icon_spec(
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}:right:{index}",
                render_params=render_params,
                instance_id=f"right_{index}",
                identity_id=str(attr["identity_id"]),
                icon_id=str(attr["icon_id"]),
                panel="right",
                position=pos,
                tint_rgb=tuple(attr["tint_rgb"]),
                size_px=int(attr["size_px"]),
                rotation_degrees=int(attr["rotation_degrees"]),
            )
        )
    image, panel_geometry, left_icons, right_icons = render_paired_canvas(
        left_icons=left_specs,
        right_icons=right_specs,
        render_params=render_params,
    )
    added_ids = {str(attr["identity_id"]) for attr in added_attrs}
    removed_ids = {str(attr["identity_id"]) for attr in removed_attrs}
    matching_right_indices = tuple(index for index, icon in enumerate(right_icons) if str(icon["identity_id"]) in added_ids)
    matching_left_indices = tuple(index for index, icon in enumerate(left_icons) if str(icon["identity_id"]) in removed_ids)
    return PairedCanvasPayload(
        image=image,
        panel_geometry=panel_geometry,
        left_icons=tuple(left_icons),
        right_icons=tuple(right_icons),
        matching_right_indices=matching_right_indices,
        matching_left_indices=matching_left_indices,
        target_count=int(target_count),
        object_count=int(diff_object_count),
        distractor_count=int(distractor_count),
        query_id=str(query_id),
        query_probabilities=dict(query_probabilities),
        sampled_palette_rgb=tuple(palette),
        object_count_probabilities=dict(object_count_probabilities),
        target_count_probabilities=dict(target_count_probabilities),
        distractor_count_probabilities=dict(distractor_count_probabilities),
        question_format="count_icons_added_to_or_missing_from_right_panel",
        trace_relation={
            "counting_target": str(query_id),
            "common_count": int(common_count),
            "added_count": int(added_count),
            "removed_count": int(removed_count),
            "left_count": len(left_icons),
            "right_count": len(right_icons),
        },
    )


class IconsCountingPanelAddedRemovedCountTask:
    """Count icons added to Right or missing from Right."""

    task_id = TASK_ID
    domain = "icons"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int):
        render_params = resolve_icon_render_params(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        payload = None
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                attempt_seed = int(hash64(int(instance_seed), self.task_id, int(attempt_index)))
                payload = _make_scene(instance_seed=attempt_seed, params=params, render_params=render_params)
                break
            except Exception as exc:
                last_error = exc
                continue
        if payload is None:
            raise RuntimeError(f"failed to generate {TASK_ID} instance") from last_error

        prompt_defaults = required_paired_prompt_defaults(_PROMPT_DEFAULTS, task_id=self.task_id)
        question_key = f"question_text_{payload.query_id}"
        question_text = str(prompt_defaults.get(question_key, prompt_defaults.get("question_text", "")))
        prompt_artifacts = build_paired_prompt(
            domain=self.domain,
            scene_id=PANEL_SCENE_ID,
            prompt_defaults=prompt_defaults,
            question_text=question_text,
            instance_seed=int(instance_seed),
        )
        annotation_panel = "right" if payload.query_id == "added_in_right_count" else "left"
        annotation = annotation_from_indices(
            panel_icons=payload.right_icons if annotation_panel == "right" else payload.left_icons,
            indices=payload.matching_right_indices if annotation_panel == "right" else payload.matching_left_indices,
        )
        return paired_task_output(
            task_id=self.task_id,
            domain=self.domain,
            payload=payload,
            prompt_artifacts=prompt_artifacts,
            prompt_defaults=prompt_defaults,
            render_params=render_params,
            annotation_panel=annotation_panel,
            answer_value=int(payload.target_count),
            annotation_bboxes=annotation,
        )


__all__ = ["IconsCountingPanelAddedRemovedCountTask"]
