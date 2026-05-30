"""Count named procedural icons after a hypothetical edit."""

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
from ..shared.icon_scene import sort_bboxes_reading_order
from ..shared.icon_style import sample_icon_palette
from ..shared.icon_task_rendering import icon_render_style_trace, resolve_icon_render_params, sample_icon_instance_noise
from ..shared.procedural_named_icon_field_scene import (
    SCENE_ID,
    NamedIconFieldSpec,
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
    procedural_named_icon_display_name,
    procedural_named_icon_fill_style_probability_map,
    sample_procedural_named_icon_fill_style,
    validate_procedural_named_icon_fill_style_support,
)


TASK_ID = "task_icons__named_field__shape_counterfactual_count"

QUERY_IDS: Tuple[str, ...] = (
    "target_count_after_shape_replacement",
    "total_count_after_shape_removal",
    "target_count_after_remove_and_replace",
)

_NON_STACK_LAYOUT_MODES: Tuple[str, ...] = (
    "jittered_grid",
    "ordered_grid",
    "shelf_rows",
    "free_scatter",
)


@dataclass(frozen=True)
class _TaskDefaults:
    target_count_min: int = 1
    target_count_max: int = 6
    removal_count_min: int = 1
    removal_count_max: int = 4
    distractor_count_min: int = 2
    distractor_count_max: int = 5
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
    named_icon_layout_modes: Tuple[str, ...] = _NON_STACK_LAYOUT_MODES
    named_icon_slot_padding_px: int = 6
    named_icon_slot_jitter_px: int = 8
    named_icon_stack_gap_px: int = 1
    named_icon_fill_style_support: Tuple[str, ...] = PROCEDURAL_NAMED_ICON_FILL_STYLES


@dataclass(frozen=True)
class _IconSemanticSpec:
    shape_id: str
    counterfactual_role: str
    counted_after_edit: bool


@dataclass(frozen=True)
class _SampleSpec:
    query_id: str
    target_answer: int
    object_count: int
    target_shape_id: str
    target_shape_name: str
    source_shape_id: str
    source_shape_name: str
    remove_shape_id: str
    remove_shape_name: str
    source_count: int
    existing_target_count: int
    removal_count: int
    distractor_count: int
    arrangement_mode: str
    semantic_specs: Tuple[_IconSemanticSpec, ...]
    query_probabilities: Dict[str, float]
    shape_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    removal_count_probabilities: Dict[str, float]
    distractor_count_probabilities: Dict[str, float]
    arrangement_mode_probabilities: Dict[str, float]
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
    if len(support) < 6:
        raise ValueError("shape_id_support must include at least six shapes")
    return support


def _query_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("counterfactual_query_ids", group_default(_GEN_DEFAULTS, "counterfactual_query_ids", QUERY_IDS))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("counterfactual_query_ids must be a sequence")
    values = tuple(dict.fromkeys(str(value) for value in raw if str(value).strip()))
    unsupported = sorted(set(values) - set(QUERY_IDS))
    if unsupported:
        raise ValueError(f"unsupported named-icon counterfactual query ids: {unsupported}")
    if not values:
        raise ValueError("counterfactual_query_ids resolved no query ids")
    return values




def _arrangement_mode_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get(
        "named_icon_layout_modes",
        group_default(_RENDER_DEFAULTS, "named_icon_layout_modes", _DEFAULTS.named_icon_layout_modes),
    )
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        values = _DEFAULTS.named_icon_layout_modes
    else:
        values = tuple(str(value) for value in raw if str(value).strip())
    unsupported = sorted(set(values) - set(_NON_STACK_LAYOUT_MODES))
    if unsupported:
        raise ValueError(f"counterfactual named-icon counting only supports non-stack layouts; got {unsupported}")
    modes = tuple(dict.fromkeys(values))
    if not modes:
        raise ValueError("named_icon_layout_modes resolved no supported non-stack layouts")
    return modes



def _other_shapes(rng, support: Sequence[str], excluded: Sequence[str], *, count: int) -> Tuple[str, ...]:
    excluded_set = {str(value) for value in excluded}
    candidates = [str(value) for value in support if str(value) not in excluded_set]
    if len(candidates) < int(count):
        raise ValueError("not enough alternate shapes available")
    rng.shuffle(candidates)
    return tuple(str(value) for value in candidates[: int(count)])


def _split_answer_into_source_and_target(rng, answer: int) -> Tuple[int, int]:
    if int(answer) <= 0:
        raise ValueError("answer must be positive")
    if int(answer) == 1:
        return 1, 0
    source_count = int(rng.randint(1, int(answer) - 1))
    existing_target_count = int(answer) - int(source_count)
    return int(source_count), int(existing_target_count)


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _SampleSpec:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:sample")
    shape_support = _shape_support(params)
    fill_style_support = resolve_named_icon_fill_style_support(params, _GEN_DEFAULTS, fallback_support=_DEFAULTS.named_icon_fill_style_support)
    fill_style_probabilities = resolve_named_icon_fill_style_probabilities(params, _GEN_DEFAULTS, fill_style_support)
    query_support = _query_support(params)
    arrangement_support = _arrangement_mode_support(params)
    answer_min, answer_max = resolve_named_icon_int_bounds(params, _GEN_DEFAULTS, "target_count_min", "target_count_max", _DEFAULTS.target_count_min, _DEFAULTS.target_count_max)
    removal_min, removal_max = resolve_named_icon_int_bounds(params, _GEN_DEFAULTS,
        "removal_count_min",
        "removal_count_max",
        _DEFAULTS.removal_count_min,
        _DEFAULTS.removal_count_max,
    )
    distractor_min, distractor_max = resolve_named_icon_int_bounds(params, _GEN_DEFAULTS,
        "distractor_count_min",
        "distractor_count_max",
        _DEFAULTS.distractor_count_min,
        _DEFAULTS.distractor_count_max,
    )
    if answer_min < 1:
        raise ValueError("named-icon counterfactual count uses target_count_min >= 1")
    answer_support = tuple(range(int(answer_min), int(answer_max) + 1))
    removal_support = tuple(range(int(removal_min), int(removal_max) + 1))
    distractor_support = tuple(range(int(distractor_min), int(distractor_max) + 1))

    explicit_query = params.get("query_id", params.get("counterfactual_query_id"))
    if explicit_query is not None:
        query_id = str(explicit_query)
        if query_id not in set(query_support):
            raise ValueError(f"query_id must be one of {query_support}")
    else:
        query_id = str(rng.choice(query_support))

    explicit_answer = params.get("target_count", params.get("target_answer"))
    if explicit_answer is not None:
        target_answer = int(explicit_answer)
        if target_answer not in set(answer_support):
            raise ValueError(f"target answer must be in {answer_support}")
    else:
        target_answer = int(rng.choice(answer_support))

    explicit_arrangement = params.get("arrangement_mode", params.get("layout_mode"))
    if explicit_arrangement is not None:
        arrangement_mode = str(explicit_arrangement)
        if arrangement_mode not in set(arrangement_support):
            raise ValueError(f"arrangement_mode must be one of {arrangement_support}")
    else:
        arrangement_mode = str(rng.choice(arrangement_support))

    semantic_specs: list[_IconSemanticSpec] = []
    source_shape_id = ""
    target_shape_id = ""
    remove_shape_id = ""
    source_count = 0
    existing_target_count = 0
    removal_count = 0
    distractor_count = 0

    if query_id == "target_count_after_shape_replacement":
        source_shape_id, target_shape_id = _other_shapes(rng, shape_support, (), count=2)
        source_count, existing_target_count = _split_answer_into_source_and_target(rng, int(target_answer))
        distractor_count = int(rng.choice(distractor_support))
        for _ in range(int(source_count)):
            semantic_specs.append(
                _IconSemanticSpec(
                    shape_id=str(source_shape_id),
                    counterfactual_role="source_shape_changed_to_target",
                    counted_after_edit=True,
                )
            )
        for _ in range(int(existing_target_count)):
            semantic_specs.append(
                _IconSemanticSpec(
                    shape_id=str(target_shape_id),
                    counterfactual_role="existing_target_shape",
                    counted_after_edit=True,
                )
            )
        for shape_id in rng.choices(_other_shapes(rng, shape_support, (source_shape_id, target_shape_id), count=min(4, len(shape_support) - 2)), k=int(distractor_count)):
            semantic_specs.append(
                _IconSemanticSpec(
                    shape_id=str(shape_id),
                    counterfactual_role="unaffected_distractor",
                    counted_after_edit=False,
                )
            )
    elif query_id == "total_count_after_shape_removal":
        remove_shape_id = str(rng.choice(shape_support))
        removal_count = int(rng.choice(removal_support))
        remaining_pool = _other_shapes(rng, shape_support, (remove_shape_id,), count=min(5, len(shape_support) - 1))
        for shape_id in rng.choices(remaining_pool, k=int(target_answer)):
            semantic_specs.append(
                _IconSemanticSpec(
                    shape_id=str(shape_id),
                    counterfactual_role="remaining_after_removal",
                    counted_after_edit=True,
                )
            )
        for _ in range(int(removal_count)):
            semantic_specs.append(
                _IconSemanticSpec(
                    shape_id=str(remove_shape_id),
                    counterfactual_role="removed_shape",
                    counted_after_edit=False,
                )
            )
    elif query_id == "target_count_after_remove_and_replace":
        remove_shape_id, source_shape_id, target_shape_id = _other_shapes(rng, shape_support, (), count=3)
        source_count, existing_target_count = _split_answer_into_source_and_target(rng, int(target_answer))
        removal_count = int(rng.choice(removal_support))
        distractor_count = int(rng.choice(distractor_support))
        for _ in range(int(removal_count)):
            semantic_specs.append(
                _IconSemanticSpec(
                    shape_id=str(remove_shape_id),
                    counterfactual_role="removed_shape",
                    counted_after_edit=False,
                )
            )
        for _ in range(int(source_count)):
            semantic_specs.append(
                _IconSemanticSpec(
                    shape_id=str(source_shape_id),
                    counterfactual_role="source_shape_changed_to_target",
                    counted_after_edit=True,
                )
            )
        for _ in range(int(existing_target_count)):
            semantic_specs.append(
                _IconSemanticSpec(
                    shape_id=str(target_shape_id),
                    counterfactual_role="existing_target_shape",
                    counted_after_edit=True,
                )
            )
        for shape_id in rng.choices(
            _other_shapes(rng, shape_support, (remove_shape_id, source_shape_id, target_shape_id), count=min(4, len(shape_support) - 3)),
            k=int(distractor_count),
        ):
            semantic_specs.append(
                _IconSemanticSpec(
                    shape_id=str(shape_id),
                    counterfactual_role="unaffected_distractor",
                    counted_after_edit=False,
                )
            )
    else:
        raise ValueError(f"unsupported counterfactual query id: {query_id}")

    rng.shuffle(semantic_specs)
    object_count = len(semantic_specs)
    if sum(1 for spec in semantic_specs if spec.counted_after_edit) != int(target_answer):
        raise RuntimeError("counterfactual construction did not match target answer")
    if target_shape_id:
        target_shape_name = procedural_named_icon_display_name(str(target_shape_id))
    elif query_id == "total_count_after_shape_removal":
        target_shape_name = ""
    else:
        raise RuntimeError("target shape missing for target-count query")
    return _SampleSpec(
        query_id=str(query_id),
        target_answer=int(target_answer),
        object_count=int(object_count),
        target_shape_id=str(target_shape_id),
        target_shape_name=str(target_shape_name),
        source_shape_id=str(source_shape_id),
        source_shape_name=procedural_named_icon_display_name(str(source_shape_id)) if source_shape_id else "",
        remove_shape_id=str(remove_shape_id),
        remove_shape_name=procedural_named_icon_display_name(str(remove_shape_id)) if remove_shape_id else "",
        source_count=int(source_count),
        existing_target_count=int(existing_target_count),
        removal_count=int(removal_count),
        distractor_count=int(distractor_count),
        arrangement_mode=str(arrangement_mode),
        semantic_specs=tuple(semantic_specs),
        query_probabilities=uniform_string_probability_map(query_support, selected=str(query_id) if explicit_query is not None else None),
        shape_probabilities=uniform_string_probability_map(shape_support),
        target_count_probabilities=dict(uniform_probability_map(answer_support, selected=int(target_answer) if explicit_answer is not None else None)),
        removal_count_probabilities=dict(uniform_probability_map(removal_support)),
        distractor_count_probabilities=dict(uniform_probability_map(distractor_support)),
        arrangement_mode_probabilities=uniform_string_probability_map(arrangement_support, selected=str(arrangement_mode) if explicit_arrangement is not None else None),
        fill_style_support=tuple(fill_style_support),
        fill_style_probabilities=dict(fill_style_probabilities),
    )



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
            tuple(int(value) for value in render_params["background_color_rgb"]),
            tuple(int(value) for value in render_params["panel_fill_rgb"]),
            tuple(int(value) for value in render_params["panel_border_rgb"]),
            tuple(int(value) for value in render_params["header_text_rgb"]),
        ),
        min_color_distance=float(render_params["min_color_distance"]),
        distance_space=str(render_params["color_distance_space"]),
    )
    min_size = max(12, int(render_params["scene_icon_size_min_px"]))
    max_size = max(min_size, int(render_params["scene_icon_size_max_px"]))
    specs: list[NamedIconFieldSpec] = []
    for index, semantic_spec in enumerate(sample.semantic_specs):
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:named_icon_{int(index)}",
            render_params=render_params,
        )
        specs.append(
            NamedIconFieldSpec(
                shape_id=str(semantic_spec.shape_id),
                tint_rgb=tuple(int(value) for value in rng.choice(palette)),
                nominal_size_px=int(rng.randint(int(min_size), int(max_size))),
                fill_style=sample_procedural_named_icon_fill_style(
                    rng,
                    support=sample.fill_style_support,
                    probabilities=sample.fill_style_probabilities,
                ),
                rotation_degrees=rotation_for_named_shape(rng, str(semantic_spec.shape_id)),
                placement_group="",
                noise_edits=tuple(noise_edits),
                noise_seed=int(noise_seed),
            )
        )
    return tuple(specs), tuple(tuple(int(channel) for channel in color) for color in palette)


def _counted_instance_ids(sample: _SampleSpec) -> Tuple[str, ...]:
    return tuple(
        f"named_icon_{int(index):02d}"
        for index, spec in enumerate(sample.semantic_specs)
        if bool(spec.counted_after_edit)
    )


def _evidence_bboxes(sample: _SampleSpec, instances: Sequence[Any]) -> list[list[int]]:
    counted = set(_counted_instance_ids(sample))
    return sort_bboxes_reading_order(tuple(instance.bbox_xyxy for instance in instances if str(instance.instance_id) in counted))


def _role_by_instance_id(sample: _SampleSpec) -> Dict[str, Dict[str, Any]]:
    return {
        f"named_icon_{int(index):02d}": {
            "shape_id": str(spec.shape_id),
            "shape_name": procedural_named_icon_display_name(str(spec.shape_id)),
            "counterfactual_role": str(spec.counterfactual_role),
            "counted_after_edit": bool(spec.counted_after_edit),
        }
        for index, spec in enumerate(sample.semantic_specs)
    }


def _complexity(sample: _SampleSpec, *, render_params: Mapping[str, Any]) -> TaskComplexity:
    answer_load = (int(sample.target_answer) - _DEFAULTS.target_count_min) / max(1, _DEFAULTS.target_count_max - _DEFAULTS.target_count_min)
    object_load = min(1.0, float(sample.object_count) / 16.0)
    logic_difficulty = {
        "target_count_after_shape_replacement": 0.56,
        "total_count_after_shape_removal": 0.48,
        "target_count_after_remove_and_replace": 0.72,
    }[str(sample.query_id)]
    role_count = len(set(spec.counterfactual_role for spec in sample.semantic_specs))
    role_diversity = min(1.0, float(role_count) / 4.0)
    shape_diversity = len(set(spec.shape_id for spec in sample.semantic_specs)) / max(1.0, float(sample.object_count))
    score = (
        0.24 * max(0.0, min(1.0, answer_load))
        + 0.22 * max(0.0, min(1.0, object_load))
        + 0.28 * float(logic_difficulty)
        + 0.14 * max(0.0, min(1.0, role_diversity))
        + 0.12 * max(0.0, min(1.0, shape_diversity))
    )
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "answer_load": round(float(answer_load), 6),
            "object_load": round(float(object_load), 6),
            "logic_difficulty": round(float(logic_difficulty), 6),
            "role_diversity": round(float(role_diversity), 6),
            "shape_diversity": round(float(shape_diversity), 6),
            "query_id": str(sample.query_id),
            "target_answer": int(sample.target_answer),
            "object_count": int(sample.object_count),
            "source_count": int(sample.source_count),
            "existing_target_count": int(sample.existing_target_count),
            "removal_count": int(sample.removal_count),
            "distractor_count": int(sample.distractor_count),
            "arrangement_mode": str(sample.arrangement_mode),
            "scene_icon_size_min_px": int(render_params["scene_icon_size_min_px"]),
            "scene_icon_size_max_px": int(render_params["scene_icon_size_max_px"]),
        },
    )


@register_task
class IconsCountingNamedShapeCounterfactualCountTask:
    """Count procedural named icons after a hypothetical removal or replacement."""

    task_id = TASK_ID
    domain = "icons"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        sample: _SampleSpec | None = None
        scene = None
        sampled_palette_rgb: Tuple[Tuple[int, int, int], ...] = ()
        render_params = resolve_icon_render_params(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
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

        evidence_bboxes = _evidence_bboxes(sample, scene.instances)
        counted_instance_ids = _counted_instance_ids(sample)
        if len(evidence_bboxes) != int(sample.target_answer):
            raise RuntimeError("rendered counterfactual named-icon count did not match target answer")
        evidence_artifacts = bbox_set_evidence(evidence_bboxes)

        question_key = f"question_text_{sample.query_id}"
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                question_key,
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
                "question_text": str(prompt_defaults[question_key]).format(
                    source_shape_name=str(sample.source_shape_name),
                    target_shape_name=str(sample.target_shape_name),
                    remove_shape_name=str(sample.remove_shape_name),
                ),
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

        serialized_instances = [serialize_named_icon_instance(instance) for instance in scene.instances]
        shape_counts = Counter(str(instance.shape_id) for instance in scene.instances)
        role_by_instance_id = _role_by_instance_id(sample)
        counted_shape_ids_after_edit: list[str] = []
        for spec in sample.semantic_specs:
            if not spec.counted_after_edit:
                continue
            if str(spec.counterfactual_role) == "source_shape_changed_to_target":
                counted_shape_ids_after_edit.append(str(sample.target_shape_id))
            else:
                counted_shape_ids_after_edit.append(str(spec.shape_id))
        final_target_shape_count = int(sample.target_answer)
        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_named_shape_counterfactual_field",
                "scene_id": SCENE_ID,
                "entities": list(serialized_instances),
                "relations": {
                    "counting_rule": "apply_hypothetical_icon_removal_or_replacement_then_count",
                    "query_id": str(sample.query_id),
                    "target_shape_id": str(sample.target_shape_id),
                    "target_shape_name": str(sample.target_shape_name),
                    "source_shape_id": str(sample.source_shape_id),
                    "source_shape_name": str(sample.source_shape_name),
                    "remove_shape_id": str(sample.remove_shape_id),
                    "remove_shape_name": str(sample.remove_shape_name),
                    "source_count": int(sample.source_count),
                    "existing_target_count": int(sample.existing_target_count),
                    "removal_count": int(sample.removal_count),
                    "distractor_count": int(sample.distractor_count),
                    "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
                    "role_by_instance_id": dict(role_by_instance_id),
                    "arrangement_mode": str(sample.arrangement_mode),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene.panel_geometry),
                },
            },
            "query_spec": {
                "query_id": str(sample.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "target_answer": int(sample.target_answer),
                    "object_count": int(sample.object_count),
                    "query_id": str(sample.query_id),
                    "target_shape_id": str(sample.target_shape_id),
                    "target_shape_name": str(sample.target_shape_name),
                    "source_shape_id": str(sample.source_shape_id),
                    "source_shape_name": str(sample.source_shape_name),
                    "remove_shape_id": str(sample.remove_shape_id),
                    "remove_shape_name": str(sample.remove_shape_name),
                    "source_count": int(sample.source_count),
                    "existing_target_count": int(sample.existing_target_count),
                    "removal_count": int(sample.removal_count),
                    "distractor_count": int(sample.distractor_count),
                    "shape_id_support": list(_shape_support(params)),
                    "query_probabilities": dict(sample.query_probabilities),
                    "shape_probabilities": dict(sample.shape_probabilities),
                    "target_count_probabilities": dict(sample.target_count_probabilities),
                    "removal_count_probabilities": dict(sample.removal_count_probabilities),
                    "distractor_count_probabilities": dict(sample.distractor_count_probabilities),
                    "arrangement_mode": str(sample.arrangement_mode),
                    "arrangement_mode_probabilities": dict(sample.arrangement_mode_probabilities),
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
                "role_by_instance_id": dict(role_by_instance_id),
            },
            "execution_trace": {
                "scene_variant": "single_panel_named_shape_counterfactual_field",
                "arrangement_mode": str(sample.arrangement_mode),
                "query_id": str(sample.query_id),
                "question_format": "count_named_shape_icons_after_hypothetical_edit",
                "target_answer": int(sample.target_answer),
                "object_count": int(sample.object_count),
                "target_shape_id": str(sample.target_shape_id),
                "target_shape_name": str(sample.target_shape_name),
                "source_shape_id": str(sample.source_shape_id),
                "source_shape_name": str(sample.source_shape_name),
                "remove_shape_id": str(sample.remove_shape_id),
                "remove_shape_name": str(sample.remove_shape_name),
                "source_count": int(sample.source_count),
                "existing_target_count": int(sample.existing_target_count),
                "removal_count": int(sample.removal_count),
                "distractor_count": int(sample.distractor_count),
                "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
                "final_counted_shape_ids_after_edit": list(counted_shape_ids_after_edit),
                "final_target_shape_count": int(final_target_shape_count),
                "counted_instance_ids": list(counted_instance_ids),
                "role_by_instance_id": dict(role_by_instance_id),
            },
            "witness_symbolic": {
                "answer": int(sample.target_answer),
                "counted_instance_ids": list(counted_instance_ids),
                "query_id": str(sample.query_id),
                "target_shape_id": str(sample.target_shape_id),
                "target_shape_name": str(sample.target_shape_name),
                "source_shape_id": str(sample.source_shape_id),
                "source_shape_name": str(sample.source_shape_name),
                "remove_shape_id": str(sample.remove_shape_id),
                "remove_shape_name": str(sample.remove_shape_name),
            },
            "projected_evidence": {
                **dict(evidence_artifacts["projected_evidence"]),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(sample.target_answer)),
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
            query_id=str(sample.query_id),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
        )


__all__ = ["IconsCountingNamedShapeCounterfactualCountTask"]
