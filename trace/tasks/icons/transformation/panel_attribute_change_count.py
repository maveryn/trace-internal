"""Count right-panel icons whose attribute changed from the left panel."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from ....core.seed import hash64
from ....core.task_group_config import get_task_group_defaults
from ...registry import register_task
from ...shared.config_defaults import group_default, split_generation_rendering_prompt_defaults
from ..shared.icon_task_rendering import resolve_icon_render_params
from ..shared.paired_canvas_common import (
    PairedCanvasDefaults,
    PairedCanvasPayload,
    build_paired_prompt,
    choose_query_id,
    annotation_from_indices,
    make_icon_spec,
    paired_complexity,
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


TASK_ID = "task_icons__paired_canvas__panel_attribute_change_count"
QUERY_IDS = ("color_changed_count", "size_changed_count", "rotation_changed_count")
_QUERY_TO_ATTRIBUTE = {
    "color_changed_count": "color",
    "size_changed_count": "size",
    "rotation_changed_count": "rotation",
}
_DEFAULTS = PairedCanvasDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "transformation")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _changed_attr(
    rng,
    *,
    attr: Mapping[str, Any],
    changed_attribute: str,
    palette,
    render_params: Mapping[str, Any],
    size_scale_small: float,
    size_scale_large: float,
    rotation_candidates,
) -> Dict[str, Any]:
    next_attr = dict(attr)
    if changed_attribute == "color":
        choices = [tuple(color) for color in palette if tuple(color) != tuple(attr["tint_rgb"])]
        next_attr["tint_rgb"] = tuple(rng.choice(choices))
    elif changed_attribute == "size":
        base = int(attr["size_px"])
        direction = rng.choice(("grow", "shrink"))
        if str(direction) == "grow":
            next_attr["size_px"] = int(min(int(render_params["scene_icon_size_max_px"]), max(base + 12, round(base * float(size_scale_large)))))
        else:
            next_attr["size_px"] = int(max(int(render_params["scene_icon_size_min_px"]), min(base - 12, round(base * float(size_scale_small)))))
        if int(next_attr["size_px"]) == int(base):
            next_attr["size_px"] = int(max(int(render_params["scene_icon_size_min_px"]), min(int(render_params["scene_icon_size_max_px"]), base + 14)))
    elif changed_attribute == "rotation":
        choices = [int(value) for value in rotation_candidates if int(value) % 360 != int(attr["rotation_degrees"]) % 360]
        next_attr["rotation_degrees"] = int(rng.choice(choices))
    else:
        raise ValueError(f"unsupported changed attribute: {changed_attribute}")
    return next_attr


def _make_scene(*, instance_seed: int, params: Mapping[str, Any], render_params: Mapping[str, Any]) -> PairedCanvasPayload:
    rng = spawn_rng(int(instance_seed), "scene")
    query_id, query_probabilities = choose_query_id(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        query_ids=QUERY_IDS,
        weight_key="attribute_change_query_weights",
    )
    active_attribute = _QUERY_TO_ATTRIBUTE[str(query_id)]
    counting_params = dict(params)
    (
        object_count,
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
    pool = list(resolve_icon_pool(str(params.get("pool_manifest", group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest)))))
    rng.shuffle(pool)
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
        count=int(object_count),
        render_params=render_params,
        rotation_candidates=rotation_candidates,
    )
    match_indices = set(rng.sample(list(range(int(object_count))), int(target_count)))
    other_attributes = [value for value in ("color", "size", "rotation") if value != active_attribute]
    size_scale_small = float(params.get("size_scale_small", group_default(_GEN_DEFAULTS, "size_scale_small", _DEFAULTS.size_scale_small)))
    size_scale_large = float(params.get("size_scale_large", group_default(_GEN_DEFAULTS, "size_scale_large", _DEFAULTS.size_scale_large)))
    gap = float(params.get("min_center_gap_frac", group_default(_RENDER_DEFAULTS, "min_center_gap_frac", _DEFAULTS.min_center_gap_frac)))
    positions = sample_positions(rng, count=int(object_count), min_gap_frac=gap)
    left_specs = []
    right_specs = []
    changed_attributes_by_index = []
    for index, (attr, pos) in enumerate(zip(attrs, positions)):
        right_attr = dict(attr)
        changed_attributes = []
        if int(index) in match_indices:
            right_attr = _changed_attr(
                rng,
                attr=right_attr,
                changed_attribute=active_attribute,
                palette=palette,
                render_params=render_params,
                size_scale_small=float(size_scale_small),
                size_scale_large=float(size_scale_large),
                rotation_candidates=rotation_candidates,
            )
            changed_attributes.append(str(active_attribute))
        elif rng.random() < 0.55:
            distractor_attribute = str(rng.choice(tuple(other_attributes)))
            right_attr = _changed_attr(
                rng,
                attr=right_attr,
                changed_attribute=distractor_attribute,
                palette=palette,
                render_params=render_params,
                size_scale_small=float(size_scale_small),
                size_scale_large=float(size_scale_large),
                rotation_candidates=rotation_candidates,
            )
            changed_attributes.append(str(distractor_attribute))
        changed_attributes_by_index.append(tuple(changed_attributes))
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
        right_specs.append(
            make_icon_spec(
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}:right:{index}",
                render_params=render_params,
                instance_id=f"right_{index}",
                identity_id=str(attr["identity_id"]),
                icon_id=str(right_attr["icon_id"]),
                panel="right",
                position=pos,
                tint_rgb=tuple(right_attr["tint_rgb"]),
                size_px=int(right_attr["size_px"]),
                rotation_degrees=int(right_attr["rotation_degrees"]),
            )
        )
    image, panel_geometry, left_icons_raw, right_icons_raw = render_paired_canvas(
        left_icons=left_specs,
        right_icons=right_specs,
        render_params=render_params,
    )
    left_icons = []
    right_icons = []
    for index, icon in enumerate(left_icons_raw):
        item = dict(icon)
        item["pair_index"] = int(index)
        left_icons.append(item)
    for index, icon in enumerate(right_icons_raw):
        item = dict(icon)
        item["pair_index"] = int(index)
        item["changed_attributes"] = [str(value) for value in changed_attributes_by_index[int(index)]]
        item["is_match"] = bool(int(index) in match_indices)
        right_icons.append(item)
    return PairedCanvasPayload(
        image=image,
        panel_geometry=panel_geometry,
        left_icons=tuple(left_icons),
        right_icons=tuple(right_icons),
        matching_right_indices=tuple(sorted(int(index) for index in match_indices)),
        matching_left_indices=tuple(sorted(int(index) for index in match_indices)),
        target_count=int(target_count),
        object_count=int(object_count),
        distractor_count=int(distractor_count),
        query_id=str(query_id),
        query_probabilities=dict(query_probabilities),
        sampled_palette_rgb=tuple(palette),
        object_count_probabilities=dict(object_count_probabilities),
        target_count_probabilities=dict(target_count_probabilities),
        distractor_count_probabilities=dict(distractor_count_probabilities),
        question_format="count_right_icons_with_queried_attribute_changed_from_left_counterpart",
        trace_relation={
            "counting_target": str(query_id),
            "active_attribute": str(active_attribute),
            "changed_attributes_by_pair": [list(value) for value in changed_attributes_by_index],
        },
    )


@register_task
class IconsTransformationPanelAttributeChangeCountTask:
    """Count Right icons whose queried visual attribute changed."""

    task_id = TASK_ID
    domain = "icons"
    task_group = "transformation"

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
        question_text = str(prompt_defaults[f"question_text_{payload.query_id}"])
        prompt_artifacts = build_paired_prompt(
            domain=self.domain,
            task_group=self.task_group,
            prompt_defaults=prompt_defaults,
            question_text=question_text,
            instance_seed=int(instance_seed),
        )
        annotation = annotation_from_indices(panel_icons=payload.right_icons, indices=payload.matching_right_indices)
        complexity = paired_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            object_count=int(payload.object_count),
            target_count=int(payload.target_count),
            object_count_min=int(group_default(_GEN_DEFAULTS, "object_count_min", _DEFAULTS.object_count_min)),
            object_count_max=int(group_default(_GEN_DEFAULTS, "object_count_max", _DEFAULTS.object_count_max)),
            left_icons=payload.left_icons,
            right_icons=payload.right_icons,
            render_params=render_params,
            rule_score=0.82,
        )
        return paired_task_output(
            task_id=self.task_id,
            domain=self.domain,
            task_group=self.task_group,
            payload=payload,
            prompt_artifacts=prompt_artifacts,
            prompt_defaults=prompt_defaults,
            render_params=render_params,
            annotation_panel="right",
            answer_value=int(payload.target_count),
            annotation_bboxes=annotation,
            complexity=complexity,
        )


__all__ = ["IconsTransformationPanelAttributeChangeCountTask"]
