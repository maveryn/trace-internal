"""Count prompt-named procedural icon shapes."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.evidence import bbox_set_evidence
from ..shared.icon_style import sample_icon_palette
from ..shared.icon_task_rendering import icon_render_style_trace, resolve_icon_render_params, sample_icon_instance_noise
from ..shared.procedural_named_icon_field_scene import (
    SCENE_ID,
    NamedIconFieldSpec,
    named_icon_bboxes_for_shape,
    render_procedural_named_icon_field_scene,
    serialize_named_icon_instance,
    resolve_named_icon_fill_style_probabilities,
    resolve_named_icon_fill_style_support,
    resolve_named_icon_int_bounds,
    rotation_for_named_shape,
    uniform_string_probability_map,
)
from ..shared.procedural_named_icons import (
    PROCEDURAL_NAMED_ICON_FILL_STYLES,
    PROCEDURAL_NAMED_ICON_SHAPES,
    procedural_named_icon_fill_style_probability_map,
    procedural_named_icon_display_name,
    sample_procedural_named_icon_fill_style,
    validate_procedural_named_icon_fill_style_support,
)


TASK_ID = "task_icons__named_field__shape_count"
QUERY_ID = "named_shape_count"
_DEFAULT_ARRANGEMENT_PROFILES: Dict[str, Dict[str, int]] = {
    "jittered_grid": {"target_count_min": 1, "target_count_max": 6, "object_count_min": 14, "object_count_max": 28},
    "ordered_grid": {"target_count_min": 1, "target_count_max": 6, "object_count_min": 14, "object_count_max": 28},
    "shelf_rows": {"target_count_min": 1, "target_count_max": 6, "object_count_min": 14, "object_count_max": 28},
    "free_scatter": {"target_count_min": 1, "target_count_max": 5, "object_count_min": 12, "object_count_max": 22},
    "clustered_by_shape": {"target_count_min": 1, "target_count_max": 6, "object_count_min": 14, "object_count_max": 30},
    "shape_stacks": {"target_count_min": 6, "target_count_max": 14, "object_count_min": 20, "object_count_max": 36},
    "target_stack_with_oddballs": {"target_count_min": 6, "target_count_max": 12, "object_count_min": 7, "object_count_max": 13},
    "mixed_stacks": {"target_count_min": 4, "target_count_max": 12, "object_count_min": 18, "object_count_max": 34},
}


@dataclass(frozen=True)
class _TaskDefaults:
    object_count_min: int = 12
    object_count_max: int = 36
    target_count_min: int = 1
    target_count_max: int = 14
    canvas_width: int = 800
    canvas_height: int = 480
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    scene_icon_size_min_px: int = 48
    scene_icon_size_max_px: int = 96
    scene_max_overlap_fraction: float = 0.0
    scene_placement_max_attempts: int = ICON_SHARED_DEFAULTS.scene_placement_max_attempts
    scene_size_shrink_rounds: int = ICON_SHARED_DEFAULTS.scene_size_shrink_rounds
    scene_size_shrink_factor: float = ICON_SHARED_DEFAULTS.scene_size_shrink_factor
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    reference_panel_width_px: int = ICON_SHARED_DEFAULTS.reference_panel_width_px
    reference_icon_size_px: int = ICON_SHARED_DEFAULTS.reference_icon_size_px
    panel_gap_px: int = ICON_SHARED_DEFAULTS.panel_gap_px
    palette_size_min: int = 8
    palette_size_max: int = 12
    color_channel_min: int = 24
    color_channel_max: int = 220
    min_color_distance: float = 40.0
    color_distance_space: str = "lab"
    background_color_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.background_color_rgb
    panel_fill_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_fill_rgb
    panel_border_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_border_rgb
    header_text_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.header_text_rgb
    icon_noise_edit_types: Tuple[str, ...] = ICON_SHARED_DEFAULTS.icon_noise_edit_types
    icon_noise_edit_count_range: Tuple[int, int] = ICON_SHARED_DEFAULTS.icon_noise_edit_count_range
    named_icon_layout_modes: Tuple[str, ...] = (
        "jittered_grid",
        "ordered_grid",
        "shelf_rows",
        "free_scatter",
        "target_stack_with_oddballs",
    )
    named_icon_slot_padding_px: int = 6
    named_icon_slot_jitter_px: int = 8
    named_icon_stack_gap_px: int = 1
    named_icon_stack_distractor_group_min: int = 3
    named_icon_stack_distractor_group_max: int = 6
    named_icon_stack_oddball_count_min: int = 1
    named_icon_stack_oddball_count_max: int = 1
    named_icon_fill_style_support: Tuple[str, ...] = PROCEDURAL_NAMED_ICON_FILL_STYLES


@dataclass(frozen=True)
class _SampleSpec:
    arrangement_mode: str
    target_shape_id: str
    target_shape_name: str
    target_count: int
    object_count: int
    shape_ids: Tuple[str, ...]
    placement_groups: Tuple[str, ...]
    arrangement_details: Dict[str, Any]
    arrangement_mode_probabilities: Dict[str, float]
    shape_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    object_count_probabilities: Dict[str, float]
    fill_style_support: Tuple[str, ...]
    fill_style_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _shape_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("shape_id_support", group_default(_GEN_DEFAULTS, "shape_id_support", PROCEDURAL_NAMED_ICON_SHAPES))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("shape_id_support must be a sequence")
    values = tuple(str(value) for value in raw)
    unsupported = sorted(set(values) - set(PROCEDURAL_NAMED_ICON_SHAPES))
    if unsupported:
        raise ValueError(f"unsupported procedural named icon shapes: {unsupported}")
    support = tuple(dict.fromkeys(values))
    if not support:
        raise ValueError("shape_id_support resolved no shapes")
    return support





def _int_profile_value(profile: Mapping[str, Any], key: str, fallback: int) -> int:
    value = profile.get(str(key), fallback)
    return int(value)


def _arrangement_profiles(params: Mapping[str, Any]) -> Dict[str, Dict[str, int]]:
    profiles = {str(key): {str(k): int(v) for k, v in value.items()} for key, value in _DEFAULT_ARRANGEMENT_PROFILES.items()}
    raw = params.get("named_icon_arrangement_profiles", group_default(_GEN_DEFAULTS, "named_icon_arrangement_profiles", {}))
    if isinstance(raw, Mapping):
        for key, value in raw.items():
            if not isinstance(value, Mapping):
                continue
            current = dict(profiles.get(str(key), {}))
            for field, field_value in value.items():
                current[str(field)] = int(field_value)
            profiles[str(key)] = current
    return profiles



def _arrangement_mode_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get(
        "named_icon_layout_modes",
        group_default(_RENDER_DEFAULTS, "named_icon_layout_modes", _DEFAULTS.named_icon_layout_modes),
    )
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        values = tuple(str(value) for value in _DEFAULTS.named_icon_layout_modes)
    else:
        values = tuple(str(value) for value in raw if str(value).strip())
    supported = set(_arrangement_profiles(params))
    modes = tuple(value for value in dict.fromkeys(values) if value in supported)
    if not modes:
        raise ValueError("named_icon_layout_modes resolved no supported arrangement modes")
    return modes


def _sample_limited_distractor_pool(rng, *, support: Sequence[str], target_shape_id: str, min_groups: int, max_groups: int) -> Tuple[str, ...]:
    distractor_pool = [str(value) for value in support if str(value) != str(target_shape_id)]
    if len(distractor_pool) < 4:
        raise ValueError("named-shape count needs at least four distractor shapes")
    rng.shuffle(distractor_pool)
    group_count = int(rng.randint(max(1, int(min_groups)), max(max(1, int(min_groups)), min(int(max_groups), len(distractor_pool)))))
    return tuple(distractor_pool[: int(group_count)])


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _SampleSpec:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:sample")
    support = _shape_support(params)
    fill_style_support = resolve_named_icon_fill_style_support(params, _GEN_DEFAULTS, fallback_support=_DEFAULTS.named_icon_fill_style_support)
    fill_style_probabilities = resolve_named_icon_fill_style_probabilities(params, _GEN_DEFAULTS, fill_style_support)
    profiles = _arrangement_profiles(params)
    arrangement_support = _arrangement_mode_support(params)
    explicit_arrangement = params.get("arrangement_mode", params.get("layout_mode"))
    if explicit_arrangement is not None:
        arrangement_mode = str(explicit_arrangement)
        if arrangement_mode not in profiles:
            raise ValueError(f"unsupported named-icon arrangement mode: {arrangement_mode}")
    else:
        arrangement_mode = str(rng.choice(arrangement_support))
    profile = dict(profiles[str(arrangement_mode)])
    target_min = _int_profile_value(profile, "target_count_min", _DEFAULTS.target_count_min)
    target_max = _int_profile_value(profile, "target_count_max", _DEFAULTS.target_count_max)
    object_min = _int_profile_value(profile, "object_count_min", _DEFAULTS.object_count_min)
    object_max = _int_profile_value(profile, "object_count_max", _DEFAULTS.object_count_max)
    if "target_count_min" in params or "target_count_max" in params:
        target_min, target_max = resolve_named_icon_int_bounds(params, _GEN_DEFAULTS, "target_count_min", "target_count_max", target_min, target_max)
    if "object_count_min" in params or "object_count_max" in params:
        object_min, object_max = resolve_named_icon_int_bounds(params, _GEN_DEFAULTS, "object_count_min", "object_count_max", object_min, object_max)
    if target_min < 1:
        raise ValueError("named-shape count uses target_count_min >= 1 so every queried shape is visible")

    explicit_shape = params.get("shape_id", params.get("target_shape_id"))
    if explicit_shape is not None:
        target_shape_id = str(explicit_shape)
        if target_shape_id not in set(support):
            raise ValueError(f"target shape must be one of {support}")
    else:
        target_shape_id = str(rng.choice(support))

    target_support = tuple(range(int(target_min), int(target_max) + 1))
    explicit_target = params.get("target_count")
    if explicit_target is not None:
        target_count = int(explicit_target)
        if target_count < 1:
            raise ValueError("target_count must be positive")
    else:
        target_count = int(rng.choice(target_support))

    explicit_object_count = params.get("object_count")
    oddball_count = 1 if str(arrangement_mode) == "target_stack_with_oddballs" else 0
    if str(arrangement_mode) == "target_stack_with_oddballs":
        object_count = int(target_count) + int(oddball_count)
        object_support = (int(object_count),)
        if explicit_object_count is not None and explicit_arrangement is not None and int(explicit_object_count) != int(object_count):
            raise ValueError("target_stack_with_oddballs uses object_count = target_count + 1")
    else:
        min_object_count = max(int(object_min), int(target_count) + 4)
        object_support = tuple(range(int(min_object_count), int(object_max) + 1))
        if not object_support:
            raise ValueError("object_count range leaves no room for named-shape distractors")
        if explicit_object_count is not None:
            object_count = int(explicit_object_count)
            if object_count < int(target_count) + 4 or object_count > int(object_max):
                raise ValueError("object_count is outside configured support")
        else:
            object_count = int(rng.choice(object_support))

    distractor_pool = tuple(str(value) for value in support if str(value) != str(target_shape_id))
    if len(distractor_pool) < 4:
        raise ValueError("named-shape count needs at least four distractor shapes")
    stack_modes = {"shape_stacks", "target_stack_with_oddballs", "mixed_stacks"}
    if str(arrangement_mode) == "target_stack_with_oddballs":
        distractor_pool = (str(rng.choice(distractor_pool)),)
    elif str(arrangement_mode) in stack_modes:
        min_groups = int(params.get("named_icon_stack_distractor_group_min", group_default(_GEN_DEFAULTS, "named_icon_stack_distractor_group_min", _DEFAULTS.named_icon_stack_distractor_group_min)))
        max_groups = int(params.get("named_icon_stack_distractor_group_max", group_default(_GEN_DEFAULTS, "named_icon_stack_distractor_group_max", _DEFAULTS.named_icon_stack_distractor_group_max)))
        distractor_pool = _sample_limited_distractor_pool(
            rng,
            support=support,
            target_shape_id=str(target_shape_id),
            min_groups=int(min_groups),
            max_groups=int(max_groups),
        )
    target_group = f"target_stack:{target_shape_id}" if str(arrangement_mode) == "target_stack_with_oddballs" else str(target_shape_id)
    shape_ids: list[str] = []
    placement_groups: list[str] = []
    for _ in range(int(target_count)):
        shape_ids.append(str(target_shape_id))
        placement_groups.append(str(target_group) if str(arrangement_mode) in stack_modes else "")
    for _ in range(int(oddball_count)):
        oddball_shape = str(rng.choice(distractor_pool))
        shape_ids.append(oddball_shape)
        placement_groups.append(str(target_group))
    extra_distractor_count = 0 if str(arrangement_mode) == "target_stack_with_oddballs" else int(object_count) - int(target_count)
    for _ in range(int(extra_distractor_count)):
        shape_id = str(rng.choice(distractor_pool))
        shape_ids.append(shape_id)
        placement_groups.append(str(shape_id) if str(arrangement_mode) in stack_modes else "")
    paired = list(zip(shape_ids, placement_groups))
    rng.shuffle(paired)
    shape_ids = [str(shape_id) for shape_id, _group in paired]
    placement_groups = [str(group) for _shape_id, group in paired]
    arrangement_details = {
        "mode": str(arrangement_mode),
        "oddball_count": int(oddball_count),
        "target_stack_total": int(target_count + oddball_count) if str(arrangement_mode) == "target_stack_with_oddballs" else None,
        "stack_distractor_shape_count": len(set(distractor_pool)) if str(arrangement_mode) in stack_modes else None,
    }
    return _SampleSpec(
        arrangement_mode=str(arrangement_mode),
        target_shape_id=str(target_shape_id),
        target_shape_name=procedural_named_icon_display_name(str(target_shape_id)),
        target_count=int(target_count),
        object_count=int(object_count),
        shape_ids=tuple(str(value) for value in shape_ids),
        placement_groups=tuple(str(value) for value in placement_groups),
        arrangement_details=dict(arrangement_details),
        arrangement_mode_probabilities=uniform_string_probability_map(arrangement_support, selected=str(arrangement_mode) if explicit_arrangement is not None else None),
        shape_probabilities=uniform_string_probability_map(support, selected=str(target_shape_id) if explicit_shape is not None else None),
        target_count_probabilities=dict(uniform_probability_map(target_support, selected=int(target_count) if explicit_target is not None else None)),
        object_count_probabilities=dict(uniform_probability_map(object_support, selected=int(object_count) if explicit_object_count is not None else None)),
        fill_style_support=tuple(fill_style_support),
        fill_style_probabilities=dict(fill_style_probabilities),
    )



def _resolve_layout_modes(params: Mapping[str, Any]) -> Tuple[str, ...]:
    return _arrangement_mode_support(params)


def _build_scene_specs(
    *,
    sample: _SampleSpec,
    instance_seed: int,
    render_params: Mapping[str, Any],
    rng,
) -> Tuple[Tuple[NamedIconFieldSpec, ...], Tuple[Tuple[int, int, int], ...]]:
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
    min_size = max(12, int(render_params["scene_icon_size_min_px"]))
    max_size = max(min_size, int(render_params["scene_icon_size_max_px"]))
    specs = []
    group_styles: Dict[str, Tuple[Tuple[int, int, int], int, str]] = {}
    stack_modes = {"shape_stacks", "target_stack_with_oddballs", "mixed_stacks"}
    for index, shape_id in enumerate(sample.shape_ids):
        placement_group = str(sample.placement_groups[int(index)] or "")
        group_key = placement_group or str(shape_id)
        if str(sample.arrangement_mode) in stack_modes and group_key not in group_styles:
            group_styles[group_key] = (
                tuple(int(value) for value in rng.choice(palette)),
                int(rng.randint(int(min_size), int(max_size))),
                sample_procedural_named_icon_fill_style(
                    rng,
                    support=sample.fill_style_support,
                    probabilities=sample.fill_style_probabilities,
                ),
            )
        if str(sample.arrangement_mode) in stack_modes:
            tint_rgb, nominal_size_px, fill_style = group_styles[str(group_key)]
        else:
            tint_rgb = tuple(int(value) for value in rng.choice(palette))
            nominal_size_px = int(rng.randint(int(min_size), int(max_size)))
            fill_style = sample_procedural_named_icon_fill_style(
                rng,
                support=sample.fill_style_support,
                probabilities=sample.fill_style_probabilities,
            )
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:named_icon_{int(index)}",
            render_params=render_params,
        )
        specs.append(
            NamedIconFieldSpec(
                shape_id=str(shape_id),
                tint_rgb=tuple(int(value) for value in tint_rgb),
                nominal_size_px=int(nominal_size_px),
                fill_style=str(fill_style),
                rotation_degrees=0 if str(sample.arrangement_mode) in stack_modes else rotation_for_named_shape(rng, str(shape_id)),
                placement_group=str(placement_group),
                noise_edits=tuple(noise_edits),
                noise_seed=int(noise_seed),
            )
        )
    return tuple(specs), tuple(tuple(int(channel) for channel in color) for color in palette)


def _complexity(sample: _SampleSpec, *, render_params: Mapping[str, Any]) -> TaskComplexity:
    visual_scan = (int(sample.object_count) - _DEFAULTS.object_count_min) / max(1, _DEFAULTS.object_count_max - _DEFAULTS.object_count_min)
    answer_load = (int(sample.target_count) - _DEFAULTS.target_count_min) / max(1, _DEFAULTS.target_count_max - _DEFAULTS.target_count_min)
    shape_diversity = len(set(sample.shape_ids)) / max(1.0, float(sample.object_count))
    clutter = min(1.0, float(sample.object_count) / 34.0)
    structural_bonus = 0.0 if str(sample.arrangement_mode) in {"shape_stacks", "target_stack_with_oddballs", "mixed_stacks"} else 0.15
    score = 0.30 * max(0.0, min(1.0, visual_scan)) + 0.25 * max(0.0, min(1.0, answer_load)) + 0.20 * max(0.0, min(1.0, shape_diversity)) + 0.15 * clutter + 0.10 * structural_bonus
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "visual_scan": round(float(visual_scan), 6),
            "answer_load": round(float(answer_load), 6),
            "shape_diversity": round(float(shape_diversity), 6),
            "clutter": round(float(clutter), 6),
            "object_count": int(sample.object_count),
            "target_count": int(sample.target_count),
            "target_shape_id": str(sample.target_shape_id),
            "arrangement_mode": str(sample.arrangement_mode),
            "scene_icon_size_min_px": int(render_params["scene_icon_size_min_px"]),
            "scene_icon_size_max_px": int(render_params["scene_icon_size_max_px"]),
        },
    )


@register_task
class IconsCountingNamedShapeCountTask:
    """Count procedural named icon shapes in a single field."""

    task_id = TASK_ID
    domain = "icons"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        sample: _SampleSpec | None = None
        scene = None
        render_params = resolve_icon_render_params(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        layout_modes = _resolve_layout_modes(params)
        slot_padding_px = int(
            params.get(
                "named_icon_slot_padding_px",
                group_default(_RENDER_DEFAULTS, "named_icon_slot_padding_px", _DEFAULTS.named_icon_slot_padding_px),
            )
        )
        slot_jitter_px = int(
            params.get(
                "named_icon_slot_jitter_px",
                group_default(_RENDER_DEFAULTS, "named_icon_slot_jitter_px", _DEFAULTS.named_icon_slot_jitter_px),
            )
        )
        stack_gap_px = int(
            params.get(
                "named_icon_stack_gap_px",
                group_default(_RENDER_DEFAULTS, "named_icon_stack_gap_px", _DEFAULTS.named_icon_stack_gap_px),
            )
        )
        for attempt in range(max(1, int(max_attempts))):
            try:
                sample = _sample_spec(instance_seed=int(instance_seed), params=params)
                scene_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:scene", int(attempt))
                icon_specs, sampled_palette_rgb = _build_scene_specs(
                    sample=sample,
                    instance_seed=int(instance_seed),
                    render_params=render_params,
                    rng=scene_rng,
                )
                scene = render_procedural_named_icon_field_scene(
                    rng=scene_rng,
                    instance_seed=int(instance_seed),
                    task_id=self.task_id,
                    icon_specs=icon_specs,
                    render_params=render_params,
                    layout_modes=(str(sample.arrangement_mode),),
                    slot_padding_px=int(slot_padding_px),
                    slot_jitter_px=int(slot_jitter_px),
                    stack_gap_px=int(stack_gap_px),
                )
                break
            except Exception as exc:  # pragma: no cover - exercised through smoke tests.
                last_error = exc
                sample = None
                scene = None
        if scene is None or sample is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        evidence_bboxes = named_icon_bboxes_for_shape(scene.instances, shape_id=str(sample.target_shape_id))
        if len(evidence_bboxes) != int(sample.target_count):
            raise RuntimeError("rendered named-shape count did not match target count")
        evidence_artifacts = bbox_set_evidence(evidence_bboxes)

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
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(prompt_defaults["question_text"]).format(shape_name=str(sample.target_shape_name)),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]).format(shape_name=str(sample.target_shape_name)),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        serialized_instances = [serialize_named_icon_instance(instance) for instance in scene.instances]
        shape_counts = dict(Counter(str(instance.shape_id) for instance in scene.instances))
        counted_instance_ids = tuple(
            str(instance.instance_id)
            for instance in scene.instances
            if str(instance.shape_id) == str(sample.target_shape_id)
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_named_shape_field",
                "scene_id": SCENE_ID,
                "entities": list(serialized_instances),
                "relations": {
                    "counting_rule": "shape_id_equals_target",
                    "target_shape_id": str(sample.target_shape_id),
                    "target_shape_name": str(sample.target_shape_name),
                    "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
                    "arrangement_mode": str(sample.arrangement_mode),
                    "arrangement_details": dict(sample.arrangement_details),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene.panel_geometry),
                },
            },
            "query_spec": {
                "query_id": QUERY_ID,
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "target_shape_id": str(sample.target_shape_id),
                    "target_shape_name": str(sample.target_shape_name),
                    "target_count": int(sample.target_count),
                    "object_count": int(sample.object_count),
                    "arrangement_mode": str(sample.arrangement_mode),
                    "arrangement_mode_probabilities": dict(sample.arrangement_mode_probabilities),
                    "arrangement_details": dict(sample.arrangement_details),
                    "shape_id_support": list(_shape_support(params)),
                    "shape_probabilities": dict(sample.shape_probabilities),
                    "target_count_probabilities": dict(sample.target_count_probabilities),
                    "object_count_probabilities": dict(sample.object_count_probabilities),
                    "named_icon_fill_style_support": list(sample.fill_style_support),
                    "fill_style_probabilities": dict(sample.fill_style_probabilities),
                },
            },
            "render_spec": {
                "canvas_size": list(scene.panel_geometry["canvas_size"]),
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "panel_geometry": dict(scene.panel_geometry),
                "style": {
                    **icon_render_style_trace(render_params=render_params, sampled_palette_rgb=sampled_palette_rgb),
                    "layout_mode": str(scene.layout_mode),
                    "named_icon_fill_style_support": list(sample.fill_style_support),
                    "named_icon_slot_padding_px": int(slot_padding_px),
                    "named_icon_slot_jitter_px": int(slot_jitter_px),
                    "named_icon_stack_gap_px": int(stack_gap_px),
                },
            },
            "render_map": {
                "image_id": "img0",
                "object_bboxes_px": {
                    str(instance.instance_id): [int(value) for value in instance.bbox_xyxy]
                    for instance in scene.instances
                },
                "counted_instance_ids": list(counted_instance_ids),
            },
            "execution_trace": {
                "scene_variant": "single_panel_named_shape_field",
                "arrangement_mode": str(sample.arrangement_mode),
                "query_id": QUERY_ID,
                "question_format": "count_named_shape_icons",
                "target_shape_id": str(sample.target_shape_id),
                "target_shape_name": str(sample.target_shape_name),
                "target_count": int(sample.target_count),
                "object_count": int(sample.object_count),
                "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
                "arrangement_details": dict(sample.arrangement_details),
                "scene_shape_ids": [str(instance.shape_id) for instance in scene.instances],
                "counted_instance_ids": list(counted_instance_ids),
            },
            "witness_symbolic": {
                "target_shape_id": str(sample.target_shape_id),
                "target_shape_name": str(sample.target_shape_name),
                "answer": int(sample.target_count),
                "counted_instance_ids": list(counted_instance_ids),
            },
            "projected_evidence": {
                **dict(evidence_artifacts["projected_evidence"]),
            },
        }
        output = TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(sample.target_count)),
            evidence_gt=TypedValue(
                type=str(evidence_artifacts["evidence_type"]),
                value=list(evidence_artifacts["evidence_value"]),
            ),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_complexity(sample, render_params=render_params),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
        )
        return output


__all__ = ["IconsCountingNamedShapeCountTask"]
