"""Count scene icons that match a reference icon on a bound attribute set."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Tuple

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
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.icon_assets import resolve_icon_pool
from ..shared.icon_scene import (
    IconInstanceSpec,
    panel_geometry_to_trace,
    render_two_panel_icon_scene,
    sort_bboxes_reading_order,
)
from ..shared.icon_style import icon_palette_meets_distance_constraints, sample_icon_palette
from ..shared.icon_task_rendering import (
    icon_render_style_trace,
    resolve_icon_render_params,
    sample_icon_instance_noise,
)


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
    """Stable fallback defaults for attribute-binding icon counting."""

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
    pool_manifest: str = "non_symmetry.txt"
    rotation_candidates_degrees: Tuple[int, ...] = (0, 90, 180, 270)
    palette_size_min: int = 3
    palette_size_max: int = 4
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
    """Trace-ready payload for one attribute-binding icon counting instance."""

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
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="task_icons_counting_attribute_binding",
)


def _rotation_candidates(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Resolve the supported orientation candidates used in the task."""

    raw = params.get(
        "rotation_candidates_degrees",
        group_default(_GEN_DEFAULTS, "rotation_candidates_degrees", list(_DEFAULTS.rotation_candidates_degrees)),
    )
    if not isinstance(raw, (list, tuple)):
        raise ValueError("rotation_candidates_degrees must be a sequence")
    rotations = tuple(int(value) % 360 for value in raw)
    if len(set(rotations)) < 2:
        raise ValueError("rotation_candidates_degrees must contain at least two distinct rotations")
    return rotations


def _sample_distractor_categories(rng, *, distractor_count: int) -> Tuple[str, ...]:
    """Sample one hardness-aware set of distractor categories.

    We intentionally bias toward partial matches so the task tests attribute
    binding rather than only filtering out obviously unrelated icons.
    """

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
) -> Tuple[str, Tuple[int, int, int], int, bool, bool, bool]:
    """Resolve one scene icon's attributes for the requested partial-match class."""

    category_key = str(category)
    same_type = category_key in {_ATTRIBUTE_BINDING_CATEGORY, "same_type_color", "same_type_orientation", "same_type_only"}
    same_color = category_key in {_ATTRIBUTE_BINDING_CATEGORY, "same_type_color", "same_color_orientation", "same_color_only"}
    same_orientation = category_key in {
        _ATTRIBUTE_BINDING_CATEGORY,
        "same_type_orientation",
        "same_color_orientation",
        "same_orientation_only",
    }
    icon_id = (
        str(reference_icon_id)
        if bool(same_type)
        else str(rng.choice(distractor_icon_pool))
    )
    tint_rgb = (
        tuple(int(channel) for channel in reference_tint_rgb)
        if bool(same_color)
        else tuple(int(channel) for channel in rng.choice(non_reference_palette))
    )
    rotation_degrees = (
        int(reference_rotation_degrees)
        if bool(same_orientation)
        else int(rng.choice(distractor_rotations))
    )
    return (
        str(icon_id),
        tuple(int(channel) for channel in tint_rgb),
        int(rotation_degrees),
        bool(same_type),
        bool(same_color),
        bool(same_orientation),
    )


def _sample_scene(
    rng,
    *,
    instance_seed: int,
    object_count: int,
    target_count: int,
    pool_manifest: str,
    rotation_candidates: Tuple[int, ...],
    render_params: Mapping[str, Any],
) -> Tuple[_ScenePayload, Any]:
    """Sample and render one reference+scene attribute-binding counting scene."""

    pool = tuple(str(icon_id) for icon_id in resolve_icon_pool(str(pool_manifest)))
    if len(pool) < 2:
        raise ValueError("attribute-binding pool resolved too few icons")

    reference_icon_id = str(rng.choice(pool))
    distractor_icon_pool = tuple(str(icon_id) for icon_id in pool if str(icon_id) != str(reference_icon_id))
    if not distractor_icon_pool:
        raise ValueError("attribute-binding pool resolved no distractor icons")

    reference_rotation = int(rng.choice(rotation_candidates))
    distractor_rotations = tuple(int(value) for value in rotation_candidates if int(value) != int(reference_rotation))
    if not distractor_rotations:
        raise ValueError("attribute-binding task resolved no distractor rotations")

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
    reference_tint = tuple(int(channel) for channel in rng.choice(palette))
    non_reference_palette = tuple(
        tuple(int(channel) for channel in color)
        for color in palette
        if tuple(int(channel) for channel in color) != tuple(int(channel) for channel in reference_tint)
    )
    if not non_reference_palette:
        raise ValueError("attribute-binding scene resolved no distractor colors")

    match_indices = set(rng.sample(list(range(int(object_count))), int(target_count)))
    distractor_categories = list(_sample_distractor_categories(rng, distractor_count=int(object_count) - int(target_count)))
    scene_specs: List[IconInstanceSpec] = []
    scene_icon_ids: List[str] = []
    scene_tints_rgb: List[Tuple[int, int, int]] = []
    scene_rotations_degrees: List[int] = []
    scene_attribute_match_categories: List[str] = []
    category_by_index: Dict[int, str] = {}
    distractor_index = 0
    for index in range(int(object_count)):
        if int(index) in match_indices:
            icon_id = str(reference_icon_id)
            tint_rgb = tuple(int(channel) for channel in reference_tint)
            rotation_degrees = int(reference_rotation)
            category = _ATTRIBUTE_BINDING_CATEGORY
            same_type = True
            same_color = True
            same_orientation = True
        else:
            category = str(distractor_categories[distractor_index])
            distractor_index += 1
            icon_id, tint_rgb, rotation_degrees, same_type, same_color, same_orientation = _resolve_scene_attributes_for_category(
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
        scene_tints_rgb.append(tuple(int(channel) for channel in tint_rgb))
        scene_rotations_degrees.append(int(rotation_degrees))
        scene_attribute_match_categories.append(str(category))
        category_by_index[int(index)] = str(category)
        scene_specs.append(
            IconInstanceSpec(
                icon_id=str(icon_id),
                rotation_degrees=int(rotation_degrees),
                tint_rgb=tuple(int(channel) for channel in tint_rgb),
            )
        )
        if bool(same_type and same_color and same_orientation) != (str(category) == _ATTRIBUTE_BINDING_CATEGORY):
            raise AssertionError("attribute-binding category resolution became inconsistent")

    reference_noise_edits, reference_noise_seed = sample_icon_instance_noise(
        instance_seed=int(instance_seed),
        namespace=f"{IconsCountingAttributeBindingTask.task_id}:reference_icon",
        render_params=render_params,
    )
    for index, spec in enumerate(list(scene_specs)):
        scene_noise_edits, scene_noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{IconsCountingAttributeBindingTask.task_id}:scene_icon_{int(index)}",
            render_params=render_params,
        )
        scene_specs[index] = IconInstanceSpec(
            icon_id=str(spec.icon_id),
            rotation_degrees=int(spec.rotation_degrees),
            mirror_x=bool(spec.mirror_x),
            tint_rgb=tuple(int(channel) for channel in spec.tint_rgb),
            noise_edits=tuple(scene_noise_edits),
            noise_seed=int(scene_noise_seed),
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
        {
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
            "is_match": bool(category_by_index[int(index)] == _ATTRIBUTE_BINDING_CATEGORY),
            "attribute_match_category": str(category_by_index[int(index)]),
            "same_type_as_reference": bool(scene_icon_ids[index] == reference_icon_id),
            "same_color_as_reference": bool(scene_tints_rgb[index] == reference_tint),
            "same_orientation_as_reference": bool(scene_rotations_degrees[index] == reference_rotation),
            "index": int(index),
        }
        for index, instance in enumerate(rendered.scene_instances)
    )
    reference_instance = {
        "instance_id": str(rendered.reference_instance.instance_id),
        "icon_id": str(rendered.reference_instance.icon_id),
        "panel": str(rendered.reference_instance.panel),
        "bbox_xyxy": list(rendered.reference_instance.bbox_xyxy),
        "nominal_size_px": int(rendered.reference_instance.nominal_size_px),
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
        reference_tint_rgb=tuple(int(channel) for channel in reference_tint),
        reference_rotation_degrees=int(reference_rotation),
        scene_icon_ids=tuple(str(icon_id) for icon_id in scene_icon_ids),
        scene_tints_rgb=tuple(tuple(int(channel) for channel in tint) for tint in scene_tints_rgb),
        scene_rotations_degrees=tuple(int(value) for value in scene_rotations_degrees),
        scene_attribute_match_categories=tuple(str(category) for category in scene_attribute_match_categories),
        match_indices=tuple(sorted(int(value) for value in match_indices)),
        match_bboxes=match_bboxes,
        sampled_palette_rgb=tuple(tuple(int(channel) for channel in color) for color in palette),
        panel_geometry=panel_geometry_to_trace(rendered.layout),
        scene_instances=scene_instances,
        reference_instance=reference_instance,
    ), rendered.image


@register_task
class IconsCountingAttributeBindingTask:
    """Count scene icons matching the reference on type, color, and orientation."""

    task_id = "task_icons_counting_attribute_binding"
    domain = "icons"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic attribute-binding icon counting instance."""

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
        render_params = resolve_icon_render_params(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
        )
        pool_manifest = str(params.get("pool_manifest", group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest)))
        rotation_candidates = _rotation_candidates(params)

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
                    rotation_candidates=tuple(rotation_candidates),
                    render_params=render_params,
                )
                break
            except Exception as exc:
                last_error = exc
                continue
        if scene_payload is None or image is None:
            raise RuntimeError("failed to generate task_icons_counting_attribute_binding instance") from last_error

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
                "scene_kind": "icons_reference_counting_attribute_binding",
                "entities": [dict(scene_payload.reference_instance), *[dict(item) for item in scene_payload.scene_instances]],
                "relations": {
                    "counting_target": "exact_reference_match",
                    "reference_icon_id": str(scene_payload.reference_icon_id),
                    "reference_tint_rgb": list(scene_payload.reference_tint_rgb),
                    "reference_rotation_degrees": int(scene_payload.reference_rotation_degrees),
                    "binding_attributes": ["icon_id", "tint_rgb", "rotation_degrees"],
                    "matching_scene_indices": list(scene_payload.match_indices),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene_payload.panel_geometry),
                },
            },
            "query_spec": {
                "task_variant": "attribute_binding_type_color_orientation",
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
                    "rotation_candidates_degrees": [int(value) for value in rotation_candidates],
                },
            },
            "render_spec": {
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
                "scene_variant": "reference_scene",
                "task_variant": "attribute_binding_type_color_orientation",
                "object_count": int(object_count),
                "object_count_probabilities": dict(object_count_probabilities),
                "target_count": int(target_count),
                "target_count_probabilities": dict(target_count_probabilities),
                "distractor_count": int(distractor_count),
                "distractor_count_probabilities": dict(distractor_count_probabilities),
                "reference_icon_id": str(scene_payload.reference_icon_id),
                "reference_tint_rgb": list(scene_payload.reference_tint_rgb),
                "reference_rotation_degrees": int(scene_payload.reference_rotation_degrees),
                "scene_icon_ids": list(scene_payload.scene_icon_ids),
                "scene_tints_rgb": [list(color) for color in scene_payload.scene_tints_rgb],
                "scene_rotations_degrees": list(scene_payload.scene_rotations_degrees),
                "scene_attribute_match_categories": list(scene_payload.scene_attribute_match_categories),
                "matching_scene_indices": list(scene_payload.match_indices),
                "question_format": "count_reference_attribute_binding_matches",
            },
            "witness_symbolic": {
                "reference_icon_id": str(scene_payload.reference_icon_id),
                "reference_tint_rgb": list(scene_payload.reference_tint_rgb),
                "reference_rotation_degrees": int(scene_payload.reference_rotation_degrees),
                "binding_attributes": ["icon_id", "tint_rgb", "rotation_degrees"],
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
                "task_variant": "attribute_binding_type_color_orientation",
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
            task_variant="attribute_binding_type_color_orientation",
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["IconsCountingAttributeBindingTask"]
