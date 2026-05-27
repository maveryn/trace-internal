"""Count right-panel icons that exactly match an icon in the left panel."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from ....core.seed import hash64
from ....core.task_group_config import get_task_group_defaults
from ...registry import register_task
from ...shared.config_defaults import group_default, split_generation_rendering_prompt_defaults
from ..shared.paired_canvas_common import (
    PairedCanvasDefaults,
    PairedCanvasPayload,
    build_paired_prompt,
    evidence_from_indices,
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
from ..shared.icon_task_rendering import resolve_icon_render_params


TASK_ID = "task_icons__paired_canvas__panel_exact_match_count"
QUERY_ID = "right_exact_match_count"
_DEFAULTS = PairedCanvasDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _make_scene(*, instance_seed: int, params: Mapping[str, Any], render_params: Mapping[str, Any]) -> PairedCanvasPayload:
    rng = spawn_rng(int(instance_seed), "scene")
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
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        defaults=_DEFAULTS,
    )
    pool = list(resolve_icon_pool(str(params.get("pool_manifest", group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest)))))
    rng.shuffle(pool)
    left_extra_count = max(1, min(3, int(distractor_count)))
    total_unique = int(target_count) + int(distractor_count) + int(left_extra_count)
    if len(pool) < total_unique:
        raise ValueError("icon pool is too small for paired exact-match scene")
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
    left_attrs = attrs[: int(target_count)] + attrs[int(target_count) + int(distractor_count) :]
    right_attrs = attrs[: int(target_count)] + attrs[int(target_count) : int(target_count) + int(distractor_count)]
    rng.shuffle(right_attrs)
    left_positions = sample_positions(
        rng,
        count=len(left_attrs),
        min_gap_frac=float(params.get("min_center_gap_frac", group_default(_RENDER_DEFAULTS, "min_center_gap_frac", _DEFAULTS.min_center_gap_frac))),
    )
    right_positions = sample_positions(
        rng,
        count=len(right_attrs),
        min_gap_frac=float(params.get("min_center_gap_frac", group_default(_RENDER_DEFAULTS, "min_center_gap_frac", _DEFAULTS.min_center_gap_frac))),
    )
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
    matching_right_indices = []
    for index, (attr, pos) in enumerate(zip(right_attrs, right_positions)):
        if any(str(attr["identity_id"]) == str(left_attr["identity_id"]) for left_attr in attrs[: int(target_count)]):
            matching_right_indices.append(int(index))
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
    matching_left_indices = tuple(
        index
        for index, icon in enumerate(left_icons)
        if str(icon["identity_id"]) in {str(attrs[i]["identity_id"]) for i in range(int(target_count))}
    )
    return PairedCanvasPayload(
        image=image,
        panel_geometry=panel_geometry,
        left_icons=tuple(left_icons),
        right_icons=tuple(right_icons),
        matching_right_indices=tuple(int(index) for index in matching_right_indices),
        matching_left_indices=tuple(int(index) for index in matching_left_indices),
        target_count=int(target_count),
        object_count=int(object_count),
        distractor_count=int(distractor_count),
        query_id=QUERY_ID,
        query_probabilities={QUERY_ID: 1.0},
        sampled_palette_rgb=tuple(palette),
        object_count_probabilities=dict(object_count_probabilities),
        target_count_probabilities=dict(target_count_probabilities),
        distractor_count_probabilities=dict(distractor_count_probabilities),
        question_format="count_right_icons_with_exact_left_match",
        trace_relation={
            "counting_target": "right_icons_exactly_matching_any_left_icon",
            "left_extra_count": int(left_extra_count),
            "right_count": len(right_icons),
            "left_count": len(left_icons),
        },
    )


@register_task
class IconsCountingPanelExactMatchCountTask:
    """Count Right icons that exactly match some Left icon."""

    task_id = TASK_ID
    domain = "icons"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int):
        render_params = resolve_icon_render_params(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        last_error: Exception | None = None
        payload = None
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
        question_text = str(prompt_defaults["question_text"])
        prompt_artifacts = build_paired_prompt(
            domain=self.domain,
            task_group=self.task_group,
            prompt_defaults=prompt_defaults,
            question_text=question_text,
            instance_seed=int(instance_seed),
        )
        evidence = evidence_from_indices(panel_icons=payload.right_icons, indices=payload.matching_right_indices)
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
            rule_score=0.75,
        )
        return paired_task_output(
            task_id=self.task_id,
            domain=self.domain,
            task_group=self.task_group,
            payload=payload,
            prompt_artifacts=prompt_artifacts,
            prompt_defaults=prompt_defaults,
            render_params=render_params,
            evidence_panel="right",
            answer_value=int(payload.target_count),
            evidence_bboxes=evidence,
            complexity=complexity,
        )


__all__ = ["IconsCountingPanelExactMatchCountTask"]
