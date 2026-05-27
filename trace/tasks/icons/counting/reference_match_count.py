"""Reference-vs-scene icon attribute matching count tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.taxonomy import resolve_task_taxonomy
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.counting_sampling import resolve_counting_target_and_distractor_triplet
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.complexity import (
    build_icons_counting_attribute_binding_complexity,
    build_icons_counting_color_complexity,
    build_icons_counting_orientation_complexity,
    build_icons_counting_type_complexity,
)
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.icon_assets import resolve_icon_pool
from ..shared.icon_scene import (
    IconInstanceSpec,
    panel_geometry_to_trace,
    render_two_panel_icon_scene,
    sort_bboxes_reading_order,
)
from ..shared.icon_style import icon_palette_meets_distance_constraints, sample_icon_palette, sample_icon_tints
from ..shared.icon_task_rendering import (
    icon_render_style_trace,
    resolve_icon_render_params,
    sample_icon_instance_noise,
)


ATTRIBUTE_MATCH_TASK_ID = "task_icons__reference_canvas__attribute_match_count"

_SINGLE_ATTRIBUTE_VARIANTS: Tuple[str, ...] = (
    "match_type",
    "match_color",
    "match_rotation",
)
_MULTI_ATTRIBUTE_VARIANTS: Tuple[str, ...] = ("match_type_color_rotation",)
_SINGLE_VARIANT_ALIASES: Dict[str, str] = {
    "same_icon_type": "match_type",
    "same_icon_color": "match_color",
    "same_orientation": "match_rotation",
    "match_orientation": "match_rotation",
}
_MULTI_VARIANT_ALIASES: Dict[str, str] = {
    "attribute_binding_type_color_orientation": "match_type_color_rotation",
    "match_attribute_binding": "match_type_color_rotation",
    "match_all_attributes": "match_type_color_rotation",
}
_ATTRIBUTE_MATCH_VARIANTS: Tuple[str, ...] = (*_SINGLE_ATTRIBUTE_VARIANTS, *_MULTI_ATTRIBUTE_VARIANTS)
_ATTRIBUTE_MATCH_ALIASES: Dict[str, str] = {
    **_SINGLE_VARIANT_ALIASES,
    **_MULTI_VARIANT_ALIASES,
}

_ATTRIBUTE_BINDING_CATEGORY = "attribute_binding"
_HARD_DISTRACTOR_CATEGORIES = (
    "same_type_color",
    "same_type_orientation",
    "same_color_orientation",
)
_MEDIUM_DISTRACTOR_CATEGORIES = (
    "same_type_only",
    "same_color_only",
    "same_orientation_only",
)
_EASY_DISTRACTOR_CATEGORY = "no_queried_attributes"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for reference-icon match-counting scenes."""

    object_count_min: int = ICON_SHARED_DEFAULTS.object_count_min
    object_count_max: int = ICON_SHARED_DEFAULTS.object_count_max
    canvas_width: int = ICON_SHARED_DEFAULTS.canvas_width
    canvas_height: int = ICON_SHARED_DEFAULTS.canvas_height
    reference_panel_width_px: int = ICON_SHARED_DEFAULTS.reference_panel_width_px
    panel_gap_px: int = ICON_SHARED_DEFAULTS.panel_gap_px
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    scene_icon_size_min_px: int = ICON_SHARED_DEFAULTS.scene_icon_size_min_px
    scene_icon_size_max_px: int = ICON_SHARED_DEFAULTS.scene_icon_size_max_px
    reference_icon_size_px: int = ICON_SHARED_DEFAULTS.reference_icon_size_px
    distractor_count_min: int = ICON_SHARED_DEFAULTS.distractor_count_min
    distractor_count_max: int = ICON_SHARED_DEFAULTS.distractor_count_max
    scene_max_overlap_fraction: float = ICON_SHARED_DEFAULTS.scene_max_overlap_fraction
    scene_placement_max_attempts: int = ICON_SHARED_DEFAULTS.scene_placement_max_attempts
    scene_size_shrink_rounds: int = ICON_SHARED_DEFAULTS.scene_size_shrink_rounds
    scene_size_shrink_factor: float = ICON_SHARED_DEFAULTS.scene_size_shrink_factor
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    pool_manifest: str = "all_icons.txt"
    rotation_candidates_degrees: Tuple[int, ...] = (0, 90, 180, 270)
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


@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready payload for one reference-match counting instance."""

    object_count: int
    target_count: int
    distractor_count: int
    reference_icon_id: str
    reference_tint_rgb: Tuple[int, int, int]
    reference_rotation_degrees: int
    scene_icon_ids: Tuple[str, ...]
    scene_tints_rgb: Tuple[Tuple[int, int, int], ...]
    scene_rotations_degrees: Tuple[int, ...]
    scene_attribute_match_categories: Tuple[str, ...]
    match_indices: Tuple[int, ...]
    match_bboxes: Tuple[Tuple[int, int, int, int], ...]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    panel_geometry: Dict[str, Any]
    scene_instances: Tuple[Dict[str, Any], ...]
    reference_instance: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "counting")


def _task_defaults(task_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Return merged generation/rendering/prompt defaults for one public task id."""

    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        task_id=str(task_id),
    )
    return dict(generation), dict(rendering), dict(prompt)


def _variant_mapping(defaults: Mapping[str, Any], key: str, *, variant: str) -> Dict[str, Any]:
    """Return one per-variant mapping from merged task defaults."""

    raw = defaults.get(str(key), {})
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise ValueError(f"{key} must be a mapping")
    selected = raw.get(str(variant), {})
    if selected is None:
        return {}
    if not isinstance(selected, Mapping):
        raise ValueError(f"{key}.{variant} must be a mapping")
    return {str(name): value for name, value in dict(selected).items()}


def _normalize_variant(variant: str, *, supported_variants: Tuple[str, ...], aliases: Mapping[str, str]) -> str:
    """Normalize explicit query-variant aliases to the public task vocabulary."""

    normalized = aliases.get(str(variant), str(variant))
    if normalized not in supported_variants:
        raise ValueError(f"unsupported query_variant: {variant}")
    return str(normalized)


def _resolve_query_variant(
    *,
    task_id: str,
    gen_defaults: Mapping[str, Any],
    supported_variants: Tuple[str, ...],
    aliases: Mapping[str, str],
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve the active counting predicate for one reference-match task."""

    normalized_params = dict(params)
    explicit_variant = normalized_params.get("query_variant")
    if explicit_variant is not None:
        normalized_params["query_variant"] = _normalize_variant(
            str(explicit_variant),
            supported_variants=supported_variants,
            aliases=aliases,
        )
    rng = spawn_rng(int(instance_seed), f"{task_id}.query_variant")
    selected_variant, variant_probabilities = resolve_variant(
        rng,
        params=normalized_params,
        gen_defaults=gen_defaults,
        supported_variants=supported_variants,
        explicit_key="query_variant",
        weights_key="query_variant_weights",
    )
    selected_variant = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=normalized_params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected_variant),
        variant_probabilities=variant_probabilities,
        supported_variants=supported_variants,
        balance_flag_key="balanced_variant_sampling",
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        sampling_namespace=f"{task_id}.query_variant",
    )
    return str(selected_variant), {str(key): float(value) for key, value in sorted(variant_probabilities.items())}


def _render_prompt(*, task_id: str, prompt_defaults: Mapping[str, Any], instance_seed: int, query_id: str):
    """Render prompt variants for one reference-match counting task."""

    required_group_defaults(
        prompt_defaults,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description",
            "question_text_by_variant",
            "evidence_hint",
            "answer_hint",
            "json_example",
            "json_example_answer_only",
        ),
        context=f"prompt defaults for {task_id}",
    )
    question_text_map = prompt_defaults.get("question_text_by_variant", {})
    if not isinstance(question_text_map, Mapping):
        raise ValueError(f"question_text_by_variant must be a mapping for {task_id}")
    question_text = question_text_map.get(str(query_id))
    if not isinstance(question_text, str) or not question_text.strip():
        raise ValueError(f"missing prompt question text for {task_id}:{query_id}")

    prompt_selection = render_task_prompt_variants(
        domain="icons",
        task_group="counting",
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(prompt_defaults["object_description"]),
            "question_text": str(question_text),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "evidence_hint": str(prompt_defaults["evidence_hint"]),
            "answer_hint": str(prompt_defaults["answer_hint"]),
            "json_example": str(prompt_defaults["json_example"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
        },
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(prompt_selection)


def _rotation_candidates(params: Mapping[str, Any], gen_defaults: Mapping[str, Any]) -> Tuple[int, ...]:
    """Resolve the supported scene rotations."""

    raw = params.get(
        "rotation_candidates_degrees",
        group_default(gen_defaults, "rotation_candidates_degrees", list(_DEFAULTS.rotation_candidates_degrees)),
    )
    if not isinstance(raw, (list, tuple)):
        raise ValueError("rotation_candidates_degrees must be a sequence")
    rotations = tuple(int(value) % 360 for value in raw)
    if len(set(rotations)) < 2:
        raise ValueError("rotation_candidates_degrees must contain at least two distinct rotations")
    return rotations


def _sample_palette(rng, render_params: Mapping[str, Any]) -> Tuple[Tuple[int, int, int], ...]:
    """Sample a color palette that respects panel/background distance constraints."""

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
    return tuple(tuple(int(channel) for channel in color) for color in palette)


def _sample_distractor_categories(rng, *, distractor_count: int) -> Tuple[str, ...]:
    """Sample hardness-aware distractor categories for exact attribute binding."""

    count = max(0, int(distractor_count))
    if count <= 0:
        return ()
    guaranteed_hard = min(count, 2)
    categories: List[str] = [str(rng.choice(_HARD_DISTRACTOR_CATEGORIES)) for _ in range(int(guaranteed_hard))]
    while len(categories) < count:
        draw = float(rng.random())
        if draw < 0.55:
            categories.append(str(rng.choice(_HARD_DISTRACTOR_CATEGORIES)))
        elif draw < 0.90:
            categories.append(str(rng.choice(_MEDIUM_DISTRACTOR_CATEGORIES)))
        else:
            categories.append(_EASY_DISTRACTOR_CATEGORY)
    rng.shuffle(categories)
    return tuple(str(category) for category in categories)


def _resolve_scene_attributes_for_category(
    rng,
    *,
    category: str,
    reference_icon_id: str,
    reference_tint_rgb: Tuple[int, int, int],
    reference_rotation_degrees: int,
    distractor_icon_pool: Tuple[str, ...],
    non_reference_palette: Tuple[Tuple[int, int, int], ...],
    distractor_rotations: Tuple[int, ...],
) -> Tuple[str, Tuple[int, int, int], int]:
    """Resolve one scene icon's attributes for a partial-match category."""

    category_key = str(category)
    same_type = category_key in {_ATTRIBUTE_BINDING_CATEGORY, "same_type_color", "same_type_orientation", "same_type_only"}
    same_color = category_key in {_ATTRIBUTE_BINDING_CATEGORY, "same_type_color", "same_color_orientation", "same_color_only"}
    same_orientation = category_key in {
        _ATTRIBUTE_BINDING_CATEGORY,
        "same_type_orientation",
        "same_color_orientation",
        "same_orientation_only",
    }
    icon_id = str(reference_icon_id) if bool(same_type) else str(rng.choice(distractor_icon_pool))
    tint_rgb = (
        tuple(int(channel) for channel in reference_tint_rgb)
        if bool(same_color)
        else tuple(int(channel) for channel in rng.choice(non_reference_palette))
    )
    rotation_degrees = int(reference_rotation_degrees) if bool(same_orientation) else int(rng.choice(distractor_rotations))
    return str(icon_id), tuple(int(channel) for channel in tint_rgb), int(rotation_degrees)


def _serialize_instance(instance: Any, *, is_match: bool, index: int | None = None, extra: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Serialize a rendered icon placement into trace metadata."""

    payload: Dict[str, Any] = {
        "instance_id": str(instance.instance_id),
        "icon_id": str(instance.icon_id),
        "panel": str(instance.panel),
        "bbox_xyxy": list(instance.bbox_xyxy),
        "nominal_size_px": int(instance.nominal_size_px),
        "rotation_degrees": int(instance.rotation_degrees),
        "mirror_x": bool(instance.mirror_x),
        "tint_rgb": list(instance.tint_rgb),
        "noise_edits": [dict(edit) for edit in instance.noise_edits],
        "noise_seed": None if instance.noise_seed is None else int(instance.noise_seed),
        "is_match": bool(is_match),
    }
    if index is not None:
        payload["index"] = int(index)
    if extra:
        payload.update(dict(extra))
    return payload


def _sample_scene(
    rng,
    *,
    task_id: str,
    query_id: str,
    instance_seed: int,
    object_count: int,
    target_count: int,
    pool_manifest: str,
    rotation_candidates: Tuple[int, ...],
    render_params: Mapping[str, Any],
) -> Tuple[_ScenePayload, Any]:
    """Sample and render one reference+scene icon matching scene."""

    pool = tuple(str(icon_id) for icon_id in resolve_icon_pool(str(pool_manifest)))
    if not pool:
        raise ValueError("reference-match pool resolved no icons")

    palette = _sample_palette(rng, render_params)
    match_indices = set(rng.sample(list(range(int(object_count))), int(target_count)))
    reference_icon_id = str(rng.choice(pool))
    reference_rotation = 0
    scene_icon_ids: List[str] = []
    scene_tints: List[Tuple[int, int, int]] = []
    scene_rotations: List[int] = []
    scene_categories: List[str] = []

    if str(query_id) == "match_type":
        if len(pool) < 2 and int(object_count) > int(target_count):
            raise ValueError("icon pool is too small for type distractors")
        sampled_tints = list(sample_icon_tints(rng, palette=palette, count=int(object_count) + 1))
        reference_tint = tuple(int(channel) for channel in sampled_tints.pop(0))
        distractor_pool = tuple(str(icon_id) for icon_id in pool if str(icon_id) != str(reference_icon_id))
        distractor_ids = list(rng.sample(distractor_pool, int(object_count) - int(target_count)))
        for index in range(int(object_count)):
            icon_id = str(reference_icon_id) if int(index) in match_indices else str(distractor_ids.pop())
            scene_icon_ids.append(str(icon_id))
            scene_tints.append(tuple(int(channel) for channel in sampled_tints.pop(0)))
            scene_rotations.append(0)
            scene_categories.append("same_type" if int(index) in match_indices else "different_type")
    elif str(query_id) == "match_color":
        reference_tint = tuple(int(channel) for channel in rng.choice(palette))
        non_reference_palette = tuple(
            tuple(int(channel) for channel in color)
            for color in palette
            if tuple(int(channel) for channel in color) != tuple(int(channel) for channel in reference_tint)
        )
        if int(object_count) > int(target_count) and not non_reference_palette:
            raise ValueError("color-counting scene resolved no distractor colors")
        for index in range(int(object_count)):
            tint_rgb = (
                tuple(int(channel) for channel in reference_tint)
                if int(index) in match_indices
                else tuple(int(channel) for channel in rng.choice(non_reference_palette))
            )
            scene_icon_ids.append(str(reference_icon_id))
            scene_tints.append(tuple(int(channel) for channel in tint_rgb))
            scene_rotations.append(0)
            scene_categories.append("same_color" if int(index) in match_indices else "different_color")
    elif str(query_id) == "match_rotation":
        reference_rotation = int(rng.choice(rotation_candidates))
        distractor_rotations = tuple(int(value) for value in rotation_candidates if int(value) != int(reference_rotation))
        if int(object_count) > int(target_count) and not distractor_rotations:
            raise ValueError("rotation task resolved no distractor rotations")
        sampled_tints = list(sample_icon_tints(rng, palette=palette, count=int(object_count) + 1))
        reference_tint = tuple(int(channel) for channel in sampled_tints.pop(0))
        for index in range(int(object_count)):
            rotation = int(reference_rotation) if int(index) in match_indices else int(rng.choice(distractor_rotations))
            scene_icon_ids.append(str(reference_icon_id))
            scene_tints.append(tuple(int(channel) for channel in sampled_tints.pop(0)))
            scene_rotations.append(int(rotation))
            scene_categories.append("same_rotation" if int(index) in match_indices else "different_rotation")
    elif str(query_id) == "match_type_color_rotation":
        if len(pool) < 2:
            raise ValueError("attribute-binding pool resolved too few icons")
        reference_rotation = int(rng.choice(rotation_candidates))
        distractor_rotations = tuple(int(value) for value in rotation_candidates if int(value) != int(reference_rotation))
        if not distractor_rotations:
            raise ValueError("attribute-binding task resolved no distractor rotations")
        reference_tint = tuple(int(channel) for channel in rng.choice(palette))
        non_reference_palette = tuple(
            tuple(int(channel) for channel in color)
            for color in palette
            if tuple(int(channel) for channel in color) != tuple(int(channel) for channel in reference_tint)
        )
        if not non_reference_palette:
            raise ValueError("attribute-binding scene resolved no distractor colors")
        distractor_icon_pool = tuple(str(icon_id) for icon_id in pool if str(icon_id) != str(reference_icon_id))
        distractor_categories = list(_sample_distractor_categories(rng, distractor_count=int(object_count) - int(target_count)))
        distractor_index = 0
        for index in range(int(object_count)):
            if int(index) in match_indices:
                icon_id = str(reference_icon_id)
                tint_rgb = tuple(int(channel) for channel in reference_tint)
                rotation = int(reference_rotation)
                category = _ATTRIBUTE_BINDING_CATEGORY
            else:
                category = str(distractor_categories[distractor_index])
                distractor_index += 1
                icon_id, tint_rgb, rotation = _resolve_scene_attributes_for_category(
                    rng,
                    category=str(category),
                    reference_icon_id=str(reference_icon_id),
                    reference_tint_rgb=tuple(int(channel) for channel in reference_tint),
                    reference_rotation_degrees=int(reference_rotation),
                    distractor_icon_pool=tuple(distractor_icon_pool),
                    non_reference_palette=tuple(non_reference_palette),
                    distractor_rotations=tuple(distractor_rotations),
                )
            scene_icon_ids.append(str(icon_id))
            scene_tints.append(tuple(int(channel) for channel in tint_rgb))
            scene_rotations.append(int(rotation))
            scene_categories.append(str(category))
    else:
        raise ValueError(f"unsupported query_id: {query_id}")

    reference_noise_edits, reference_noise_seed = sample_icon_instance_noise(
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:{query_id}:reference_icon",
        render_params=render_params,
    )
    scene_specs: List[IconInstanceSpec] = []
    for index, (icon_id, tint_rgb, rotation) in enumerate(zip(scene_icon_ids, scene_tints, scene_rotations)):
        scene_noise_edits, scene_noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:{query_id}:scene_icon_{int(index)}",
            render_params=render_params,
        )
        scene_specs.append(
            IconInstanceSpec(
                icon_id=str(icon_id),
                rotation_degrees=int(rotation),
                tint_rgb=tuple(int(channel) for channel in tint_rgb),
                noise_edits=tuple(scene_noise_edits),
                noise_seed=int(scene_noise_seed),
            )
        )

    rendered = render_two_panel_icon_scene(
        rng=rng,
        reference_icon=IconInstanceSpec(
            icon_id=str(reference_icon_id),
            rotation_degrees=int(reference_rotation),
            tint_rgb=tuple(int(channel) for channel in reference_tint),
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
        _serialize_instance(
            instance,
            is_match=int(index) in match_indices,
            index=int(index),
            extra={
                "attribute_match_category": str(scene_categories[int(index)]),
                "same_type_as_reference": bool(scene_icon_ids[int(index)] == reference_icon_id),
                "same_color_as_reference": bool(scene_tints[int(index)] == reference_tint),
                "same_rotation_as_reference": bool(scene_rotations[int(index)] == reference_rotation),
            },
        )
        for index, instance in enumerate(rendered.scene_instances)
    )
    reference_instance = _serialize_instance(rendered.reference_instance, is_match=True)
    return _ScenePayload(
        object_count=int(object_count),
        target_count=int(target_count),
        distractor_count=int(object_count) - int(target_count),
        reference_icon_id=str(reference_icon_id),
        reference_tint_rgb=tuple(int(channel) for channel in reference_tint),
        reference_rotation_degrees=int(reference_rotation),
        scene_icon_ids=tuple(str(icon_id) for icon_id in scene_icon_ids),
        scene_tints_rgb=tuple(tuple(int(channel) for channel in tint) for tint in scene_tints),
        scene_rotations_degrees=tuple(int(value) for value in scene_rotations),
        scene_attribute_match_categories=tuple(str(category) for category in scene_categories),
        match_indices=tuple(sorted(int(value) for value in match_indices)),
        match_bboxes=match_bboxes,
        sampled_palette_rgb=tuple(tuple(int(channel) for channel in color) for color in palette),
        panel_geometry=panel_geometry_to_trace(rendered.layout),
        scene_instances=scene_instances,
        reference_instance=reference_instance,
    ), rendered.image


def _relations_for(scene_payload: _ScenePayload, *, query_id: str) -> Dict[str, Any]:
    """Build scene-IR relations for the selected reference-match query."""

    relations: Dict[str, Any] = {
        "query_id": str(query_id),
        "query_variant": "default",
        "reference_icon_id": str(scene_payload.reference_icon_id),
        "reference_tint_rgb": list(scene_payload.reference_tint_rgb),
        "reference_rotation_degrees": int(scene_payload.reference_rotation_degrees),
        "matching_scene_indices": list(scene_payload.match_indices),
    }
    if str(query_id) == "match_type":
        relations["counting_target"] = "same_icon_type_as_reference"
    elif str(query_id) == "match_color":
        relations["counting_target"] = "same_color_as_reference"
    elif str(query_id) == "match_rotation":
        relations["counting_target"] = "same_rotation_as_reference"
    else:
        relations["counting_target"] = "exact_reference_match"
        relations["binding_attributes"] = ["icon_id", "tint_rgb", "rotation_degrees"]
    return relations


def _build_complexity(
    *,
    task_id: str,
    query_id: str,
    scene_payload: _ScenePayload,
    gen_defaults: Mapping[str, Any],
    render_params: Mapping[str, Any],
    rotation_candidates: Sequence[int],
):
    """Build the task complexity payload for the selected query."""

    object_count_min = int(group_default(gen_defaults, "object_count_min", _DEFAULTS.object_count_min))
    object_count_max = int(group_default(gen_defaults, "object_count_max", _DEFAULTS.object_count_max))
    if str(query_id) == "match_type":
        return build_icons_counting_type_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=str(task_id),
            object_count=int(scene_payload.object_count),
            target_count=int(scene_payload.target_count),
            object_count_min=object_count_min,
            object_count_max=object_count_max,
            scene_instances=scene_payload.scene_instances,
            render_params=render_params,
        )
    if str(query_id) == "match_color":
        return build_icons_counting_color_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=str(task_id),
            object_count=int(scene_payload.object_count),
            target_count=int(scene_payload.target_count),
            object_count_min=object_count_min,
            object_count_max=object_count_max,
            sampled_palette_size=len(scene_payload.sampled_palette_rgb),
            min_color_distance=float(render_params["min_color_distance"]),
            scene_instances=scene_payload.scene_instances,
            render_params=render_params,
        )
    if str(query_id) == "match_rotation":
        return build_icons_counting_orientation_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=str(task_id),
            object_count=int(scene_payload.object_count),
            target_count=int(scene_payload.target_count),
            object_count_min=object_count_min,
            object_count_max=object_count_max,
            rotation_candidate_count=len(tuple(rotation_candidates)),
            scene_instances=scene_payload.scene_instances,
            render_params=render_params,
        )
    return build_icons_counting_attribute_binding_complexity(
        task_group_defaults=_TASK_GROUP_DEFAULTS,
        task_id=str(task_id),
        object_count=int(scene_payload.object_count),
        target_count=int(scene_payload.target_count),
        distractor_count=int(scene_payload.distractor_count),
        object_count_min=object_count_min,
        object_count_max=object_count_max,
        distractor_categories=[
            str(category)
            for category in scene_payload.scene_attribute_match_categories
            if str(category) != _ATTRIBUTE_BINDING_CATEGORY
        ],
        scene_instances=scene_payload.scene_instances,
        render_params=render_params,
    )


class _ReferenceAttributeMatchCountTaskBase:
    """Shared implementation for public reference-match counting tasks."""

    task_id: str
    domain = "icons"
    task_group = "counting"
    supported_variants: Tuple[str, ...] = ()
    variant_aliases: Mapping[str, str] = {}
    scene_kind: str = "icons_reference_attribute_match_count"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        gen_defaults, render_defaults, prompt_defaults = _task_defaults(str(self.task_id))
        query_id, query_probabilities = _resolve_query_variant(
            task_id=str(self.task_id),
            gen_defaults=gen_defaults,
            supported_variants=tuple(self.supported_variants),
            aliases=self.variant_aliases,
            instance_seed=int(instance_seed),
            params=params,
        )
        active_gen_defaults = dict(gen_defaults)
        active_gen_defaults.update(_variant_mapping(gen_defaults, "variant_generation_params", variant=str(query_id)))
        active_render_defaults = dict(render_defaults)
        active_render_defaults.update(_variant_mapping(render_defaults, "variant_render_params", variant=str(query_id)))

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
            gen_defaults=active_gen_defaults,
            fallback_total_min=_DEFAULTS.object_count_min,
            fallback_total_max=_DEFAULTS.object_count_max,
            fallback_target_min=0,
            fallback_target_max=10,
            fallback_distractor_min=_DEFAULTS.distractor_count_min,
            fallback_distractor_max=_DEFAULTS.distractor_count_max,
        )
        render_params = resolve_icon_render_params(
            params=params,
            render_defaults=active_render_defaults,
            fallback_defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        pool_manifest = str(params.get("pool_manifest", group_default(active_gen_defaults, "pool_manifest", _DEFAULTS.pool_manifest)))
        rotation_candidates = _rotation_candidates(params, active_gen_defaults)

        scene_payload = None
        image = None
        last_error: Exception | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                scene_payload, image = _sample_scene(
                    scene_rng,
                    task_id=str(self.task_id),
                    query_id=str(query_id),
                    instance_seed=int(instance_seed),
                    object_count=int(object_count),
                    target_count=int(target_count),
                    pool_manifest=str(pool_manifest),
                    rotation_candidates=tuple(rotation_candidates),
                    render_params=render_params,
                )
                break
            except Exception as exc:
                last_error = exc
                continue
        if scene_payload is None or image is None:
            raise RuntimeError(f"failed to generate {self.task_id} instance") from last_error

        prompt_artifacts = _render_prompt(
            task_id=str(self.task_id),
            prompt_defaults=prompt_defaults,
            instance_seed=int(instance_seed),
            query_id=str(query_id),
        )
        taxonomy = resolve_task_taxonomy(str(self.task_id))
        evidence_bboxes = sort_bboxes_reading_order(scene_payload.match_bboxes)
        answer_gt = TypedValue(type="integer", value=int(scene_payload.target_count))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        common_ids = {
            "domain": taxonomy.domain,
            "scene_id": taxonomy.scene_id,
            "task_id": str(self.task_id),
            "query_variant": "default",
            "query_id": str(query_id),
        }
        trace_payload = {
            "taxonomy": {
                "domain": taxonomy.domain,
                "scene_id": taxonomy.scene_id,
                "task_id": str(self.task_id),
                "source_domain": taxonomy.source_domain,
                "source_task_group": taxonomy.source_task_group,
                "query_id": str(query_id),
            },
            "scene_ir": {
                **common_ids,
                "scene_kind": str(self.scene_kind),
                "entities": [dict(scene_payload.reference_instance), *[dict(item) for item in scene_payload.scene_instances]],
                "relations": _relations_for(scene_payload, query_id=str(query_id)),
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene_payload.panel_geometry),
                },
            },
            "query_spec": {
                **common_ids,
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "query_variant_probabilities": dict(query_probabilities),
                "variant_probabilities": dict(query_probabilities),
                "params": {
                    "scene_id": taxonomy.scene_id,
                    "scene_variant": "reference_scene",
                    "query_id": str(query_id),
                    "query_variant": "default",
                    "query_variant_probabilities": dict(query_probabilities),
                    "variant_probabilities": dict(query_probabilities),
                    "object_count": int(object_count),
                    "object_count_probabilities": dict(object_count_probabilities),
                    "target_count": int(target_count),
                    "target_count_probabilities": dict(target_count_probabilities),
                    "distractor_count": int(distractor_count),
                    "distractor_count_probabilities": dict(distractor_count_probabilities),
                    "pool_manifest": str(pool_manifest),
                    "rotation_candidates_degrees": [int(value) for value in rotation_candidates],
                },
            },
            "render_spec": {
                **common_ids,
                "canvas_size": [int(render_params["canvas_width"]), int(render_params["canvas_height"])],
                "coord_space": "pixel",
                "panel_geometry": dict(scene_payload.panel_geometry),
                "style": icon_render_style_trace(
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
                **common_ids,
                "scene_variant": "reference_scene",
                "query_variant_probabilities": dict(query_probabilities),
                "variant_probabilities": dict(query_probabilities),
                "object_count": int(object_count),
                "object_count_probabilities": dict(object_count_probabilities),
                "target_count": int(target_count),
                "target_count_probabilities": dict(target_count_probabilities),
                "distractor_count": int(distractor_count),
                "distractor_count_probabilities": dict(distractor_count_probabilities),
                "reference_icon_id": str(scene_payload.reference_icon_id),
                "base_icon_id": str(scene_payload.reference_icon_id),
                "reference_tint_rgb": list(scene_payload.reference_tint_rgb),
                "reference_rotation_degrees": int(scene_payload.reference_rotation_degrees),
                "scene_icon_ids": list(scene_payload.scene_icon_ids),
                "scene_tints_rgb": [list(color) for color in scene_payload.scene_tints_rgb],
                "scene_rotations_degrees": list(scene_payload.scene_rotations_degrees),
                "scene_attribute_match_categories": list(scene_payload.scene_attribute_match_categories),
                "matching_scene_indices": list(scene_payload.match_indices),
                "question_format": "count_matching_scene_icons_by_reference",
            },
            "witness_symbolic": {
                "query_id": str(query_id),
                "reference_icon_id": str(scene_payload.reference_icon_id),
                "reference_tint_rgb": list(scene_payload.reference_tint_rgb),
                "reference_rotation_degrees": int(scene_payload.reference_rotation_degrees),
                "matching_scene_indices": list(scene_payload.match_indices),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
            },
        }
        complexity = _build_complexity(
            task_id=str(self.task_id),
            query_id=str(query_id),
            scene_payload=scene_payload,
            gen_defaults=active_gen_defaults,
            render_params=render_params,
            rotation_candidates=rotation_candidates,
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
            query_variant="default",
            scene_id=taxonomy.scene_id,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class IconsReferenceCanvasAttributeMatchCountTask(_ReferenceAttributeMatchCountTaskBase):
    """Count scene icons matching the reference by one or more attributes."""

    task_id = ATTRIBUTE_MATCH_TASK_ID
    supported_variants = _ATTRIBUTE_MATCH_VARIANTS
    variant_aliases = _ATTRIBUTE_MATCH_ALIASES
    scene_kind = "icons_reference_attribute_match_count"


__all__ = [
    "IconsReferenceCanvasAttributeMatchCountTask",
]
