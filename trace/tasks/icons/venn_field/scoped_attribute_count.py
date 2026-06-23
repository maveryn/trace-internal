"""Count prompt-named procedural icons in Venn-field regions."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.taxonomy import resolve_task_taxonomy
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, load_scene_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import uniform_probability_map
from ...shared.fixed_query import select_task_query_id
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import build_prompt_query_spec
from ...shared.weighted_sampling import sample_weighted_value, weighted_probability_map
from ..shared.procedural_named_icons import (
    procedural_named_icon_display_name,
    sample_procedural_named_icon_fill_style,
)

from .shared.annotations import counted_icon_bbox_set_annotation
from .shared.defaults import DOMAIN, SCENE_ID, VENN_CATEGORIES, VennFieldDefaults
from .shared.output import venn_field_render_spec
from .shared.prompts import render_venn_prompt_artifacts
from .shared.rendering import render_venn_field_with_retries, serialize_venn_icon
from .shared.sampling import (
    color_support,
    default_target_mode_support,
    fill_style_probabilities,
    fill_style_support,
    int_bounds,
    shape_support,
    target_description,
    target_mode_probabilities,
    uniform_string_probability_map,
)
from .shared.spatial_primitives import venn_to_trace
from .shared.state import NamedColorEntry, VennIconPlan
from .shared.styles import resolve_venn_render_params


TASK_ID = "task_icons__venn_field__scoped_attribute_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "inside_both_circles_count",
    "inside_either_circle_count",
    "inside_exactly_one_circle_count",
    "outside_both_circles_count",
)
TARGET_ATTRIBUTE_MODES: Tuple[str, ...] = default_target_mode_support()
_QUERY_TO_CATEGORIES: Dict[str, Tuple[str, ...]] = {
    "inside_both_circles_count": ("both",),
    "inside_either_circle_count": ("left_only", "right_only", "both"),
    "inside_exactly_one_circle_count": ("left_only", "right_only"),
    "outside_both_circles_count": ("neither",),
}

_DEFAULTS = VennFieldDefaults()
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    DOMAIN,
    SCENE_ID,
    task_id=TASK_ID,
)


def _select_query(instance_seed: int, params: Mapping[str, Any]) -> tuple[str, Dict[str, float], Dict[str, Any]]:
    """Select one user-facing Venn-region predicate."""

    return select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id=SUPPORTED_QUERY_IDS[0],
        task_id=TASK_ID,
        namespace=f"{TASK_ID}.query",
    )


def _counted_categories(query_id: str) -> Tuple[str, ...]:
    if str(query_id) not in _QUERY_TO_CATEGORIES:
        raise ValueError(f"unsupported query_id: {query_id}")
    return tuple(_QUERY_TO_CATEGORIES[str(query_id)])


def _target_mode(rng: Any, params: Mapping[str, Any]) -> tuple[str, Dict[str, float]]:
    probabilities = target_mode_probabilities(params, _GEN_DEFAULTS)
    explicit_mode = params.get("target_attribute_mode")
    if explicit_mode is not None:
        mode = str(explicit_mode)
        if mode not in set(TARGET_ATTRIBUTE_MODES):
            raise ValueError(f"target_attribute_mode must be one of {TARGET_ATTRIBUTE_MODES}")
        return mode, {value: (1.0 if value == mode else 0.0) for value in TARGET_ATTRIBUTE_MODES}
    return str(sample_weighted_value(rng, TARGET_ATTRIBUTE_MODES, probabilities)), dict(probabilities)


def _target_shape(rng: Any, params: Mapping[str, Any], shape_ids: Sequence[str]) -> tuple[str, Dict[str, float]]:
    explicit_shape = params.get("shape_id", params.get("target_shape_id"))
    if explicit_shape is not None:
        target_shape_id = str(explicit_shape)
        if target_shape_id not in set(shape_ids):
            raise ValueError(f"target shape must be one of {tuple(shape_ids)}")
        return target_shape_id, uniform_string_probability_map(tuple(shape_ids), selected=target_shape_id)
    target_shape_id = str(rng.choice(tuple(shape_ids)))
    return target_shape_id, uniform_string_probability_map(tuple(shape_ids))


def _target_color(
    rng: Any,
    params: Mapping[str, Any],
    mode: str,
    colors: Sequence[NamedColorEntry],
) -> tuple[NamedColorEntry | None, Dict[str, float]]:
    names = tuple(str(entry.name) for entry in colors)
    if str(mode) != "color_shape":
        return None, uniform_string_probability_map(names)
    color_by_name = {str(entry.name): entry for entry in colors}
    explicit_color = params.get("color_name", params.get("target_color_name"))
    if explicit_color is not None:
        color_name = str(explicit_color).strip().lower()
        if color_name not in color_by_name:
            raise ValueError(f"target color must be one of {names}")
        return color_by_name[str(color_name)], uniform_string_probability_map(names, selected=str(color_name))
    color = rng.choice(tuple(colors))
    return color_by_name[str(color.name)], uniform_string_probability_map(names)


def _sample_counts(
    rng: Any,
    params: Mapping[str, Any],
) -> tuple[int, Dict[str, float], int, Dict[str, float], int]:
    """Resolve count supports; invariant: object count can hold counted, opposite, and distractor icons."""

    answer_min, answer_max = int_bounds(
        params,
        _GEN_DEFAULTS,
        low_key="target_count_min",
        high_key="target_count_max",
        fallback_low=_DEFAULTS.target_count_min,
        fallback_high=_DEFAULTS.target_count_max,
    )
    object_min, object_max = int_bounds(
        params,
        _GEN_DEFAULTS,
        low_key="object_count_min",
        high_key="object_count_max",
        fallback_low=_DEFAULTS.object_count_min,
        fallback_high=_DEFAULTS.object_count_max,
    )
    opposite_min, opposite_max = int_bounds(
        params,
        _GEN_DEFAULTS,
        low_key="target_opposite_count_min",
        high_key="target_opposite_count_max",
        fallback_low=_DEFAULTS.target_opposite_count_min,
        fallback_high=_DEFAULTS.target_opposite_count_max,
    )
    answer_support = tuple(range(int(answer_min), int(answer_max) + 1))
    target_count_probabilities = weighted_probability_map(
        answer_support,
        params.get("target_count_weights", group_default(_GEN_DEFAULTS, "target_count_weights", None)),
    )
    explicit_target = params.get("target_count", params.get("target_answer"))
    if explicit_target is not None:
        target_count = int(explicit_target)
        if target_count not in set(answer_support):
            raise ValueError(f"target_count must be in {answer_support}")
        target_count_probability_map = dict(uniform_probability_map(answer_support, selected=int(target_count)))
    else:
        target_count = int(sample_weighted_value(rng, answer_support, target_count_probabilities))
        target_count_probability_map = dict(target_count_probabilities)

    target_opposite_count = int(rng.randint(int(opposite_min), int(opposite_max) + 1))
    min_object_count = max(int(object_min), int(target_count) + int(target_opposite_count) + 4)
    if min_object_count > int(object_max):
        raise ValueError("object_count range cannot support requested target/opposite counts")
    object_support = tuple(range(int(min_object_count), int(object_max) + 1))
    explicit_object = params.get("object_count")
    if explicit_object is not None:
        object_count = int(explicit_object)
        if object_count not in set(object_support):
            raise ValueError(f"object_count must be in {object_support}")
        object_count_probability_map = dict(uniform_probability_map(object_support, selected=int(object_count)))
    else:
        object_count = int(rng.choice(object_support))
        object_count_probability_map = dict(uniform_probability_map(object_support))
    return (
        int(target_count),
        target_count_probability_map,
        int(object_count),
        object_count_probability_map,
        int(target_opposite_count),
    )


def _sample_nonmatching_icon(
    rng: Any,
    *,
    mode: str,
    target_shape_id: str,
    target_color: NamedColorEntry | None,
    shape_ids: Sequence[str],
    colors: Sequence[NamedColorEntry],
    fill_styles: Sequence[str],
    fill_style_weights: Mapping[str, float],
) -> tuple[str, NamedColorEntry, str]:
    """Sample one distractor; invariant: it cannot satisfy the task-selected target predicate."""

    other_shapes = [str(value) for value in shape_ids if str(value) != str(target_shape_id)]
    if not other_shapes:
        raise ValueError("shape support resolved no distractor shapes")
    if str(mode) == "shape_only":
        return (
            str(rng.choice(other_shapes)),
            rng.choice(tuple(colors)),
            str(sample_procedural_named_icon_fill_style(rng, support=fill_styles, probabilities=fill_style_weights)),
        )

    draw = float(rng.random())
    if str(mode) == "color_shape":
        if target_color is None:
            raise ValueError("color_shape distractor is missing target_color")
        other_colors = [entry for entry in colors if str(entry.name) != str(target_color.name)]
        if draw < 0.40 and other_colors:
            shape_id = str(target_shape_id)
            color = rng.choice(tuple(other_colors))
        elif draw < 0.78:
            shape_id = str(rng.choice(other_shapes))
            color = target_color
        else:
            shape_id = str(rng.choice(other_shapes))
            color = rng.choice(tuple(other_colors or list(colors)))
        fill_style = sample_procedural_named_icon_fill_style(rng, support=fill_styles, probabilities=fill_style_weights)
        return str(shape_id), color, str(fill_style)

    return (
        str(rng.choice(other_shapes)),
        rng.choice(tuple(colors)),
        str(sample_procedural_named_icon_fill_style(rng, support=fill_styles, probabilities=fill_style_weights)),
    )


def _make_plans(
    rng: Any,
    *,
    counted_categories: Sequence[str],
    mode: str,
    target_count: int,
    object_count: int,
    target_opposite_count: int,
    target_shape_id: str,
    target_color: NamedColorEntry | None,
    shape_ids: Sequence[str],
    colors: Sequence[NamedColorEntry],
    fill_styles: Sequence[str],
    fill_style_weights: Mapping[str, float],
) -> Tuple[VennIconPlan, ...]:
    """Build icon plans; invariant: exactly target_count matching icons land in counted categories."""

    counted = tuple(str(value) for value in counted_categories)
    non_counted = tuple(str(value) for value in VENN_CATEGORIES if str(value) not in set(counted))
    if not non_counted:
        raise ValueError("Venn task resolved no non-counted target distractor categories")
    target_color_entry = target_color if str(mode) == "color_shape" else rng.choice(tuple(colors))
    plans: list[VennIconPlan] = []

    def _target_plan(category: str) -> VennIconPlan:
        color = target_color_entry if str(mode) == "color_shape" else rng.choice(tuple(colors))
        fill_style = sample_procedural_named_icon_fill_style(rng, support=fill_styles, probabilities=fill_style_weights)
        return VennIconPlan(
            shape_id=str(target_shape_id),
            color_name=str(color.name),
            tint_rgb=tuple(int(channel) for channel in color.rgb),
            fill_style=str(fill_style),
            venn_category=str(category),
            matches_target=True,
        )

    for _ in range(int(target_count)):
        plans.append(_target_plan(str(rng.choice(counted))))
    for _ in range(int(target_opposite_count)):
        plans.append(_target_plan(str(rng.choice(non_counted))))

    while len(plans) < int(object_count):
        shape_id, color, fill_style = _sample_nonmatching_icon(
            rng,
            mode=str(mode),
            target_shape_id=str(target_shape_id),
            target_color=target_color,
            shape_ids=shape_ids,
            colors=colors,
            fill_styles=fill_styles,
            fill_style_weights=fill_style_weights,
        )
        plans.append(
            VennIconPlan(
                shape_id=str(shape_id),
                color_name=str(color.name),
                tint_rgb=tuple(int(channel) for channel in color.rgb),
                fill_style=str(fill_style),
                venn_category=str(rng.choice(VENN_CATEGORIES)),
                matches_target=False,
            )
        )
    rng.shuffle(plans)
    return tuple(plans)


@register_task
class IconsVennFieldScopedAttributeCountTask:
    """Count named procedural icons satisfying a visible Venn-region predicate."""

    task_id = TASK_ID
    domain = DOMAIN
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic Venn-field count instance."""

        query_id, query_probabilities, task_params = _select_query(int(instance_seed), params)
        counted_categories = _counted_categories(str(query_id))
        sample_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.sample")

        mode, mode_probabilities = _target_mode(sample_rng, task_params)
        shape_ids = shape_support(task_params, _GEN_DEFAULTS)
        colors = color_support(task_params, _GEN_DEFAULTS)
        fill_styles = fill_style_support(task_params, _GEN_DEFAULTS, fallback=_DEFAULTS.named_icon_fill_style_support)
        fill_weights = fill_style_probabilities(task_params, _GEN_DEFAULTS, fill_styles)
        target_shape_id, shape_probabilities = _target_shape(sample_rng, task_params, shape_ids)
        target_color, color_probabilities = _target_color(sample_rng, task_params, str(mode), colors)
        target_count, target_count_probabilities, object_count, object_count_probabilities, target_opposite_count = _sample_counts(
            sample_rng,
            task_params,
        )
        plans = _make_plans(
            sample_rng,
            counted_categories=counted_categories,
            mode=str(mode),
            target_count=int(target_count),
            object_count=int(object_count),
            target_opposite_count=int(target_opposite_count),
            target_shape_id=str(target_shape_id),
            target_color=target_color,
            shape_ids=shape_ids,
            colors=colors,
            fill_styles=fill_styles,
            fill_style_weights=fill_weights,
        )

        render_params = resolve_venn_render_params(
            params=task_params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        scene = render_venn_field_with_retries(
            instance_seed=int(instance_seed),
            max_attempts=int(max_attempts),
            content_namespace=TASK_ID,
            object_count=int(object_count),
            target_count=int(target_count),
            plans=plans,
            counted_categories=counted_categories,
            render_params=render_params,
        )

        annotation_bboxes = tuple(instance.bbox_xyxy for instance in scene.instances if instance.counted)
        if len(annotation_bboxes) != int(target_count):
            raise RuntimeError("projected Venn annotation did not match target answer")
        annotation_artifacts = counted_icon_bbox_set_annotation(annotation_bboxes)
        target_phrase = target_description(mode=str(mode), shape_id=str(target_shape_id), target_color=target_color)
        _prompt_defaults, prompt_artifacts = render_venn_prompt_artifacts(
            instance_seed=int(instance_seed),
            prompt_defaults=_PROMPT_DEFAULTS,
            query_key=str(query_id),
            target_description=str(target_phrase),
        )
        taxonomy = resolve_task_taxonomy(str(self.task_id))
        serialized_instances = [serialize_venn_icon(instance) for instance in scene.instances]
        counted_instance_ids = tuple(str(instance.instance_id) for instance in scene.instances if instance.counted)
        target_instance_ids = tuple(str(instance.instance_id) for instance in scene.instances if instance.matches_target)
        category_counts = dict(Counter(str(instance.venn_category) for instance in scene.instances))
        target_category_counts = dict(Counter(str(instance.venn_category) for instance in scene.instances if instance.matches_target))
        venn_payload = venn_to_trace(scene.venn)
        query_spec = build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(query_id),
            params={
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id_probabilities": dict(query_probabilities),
                "target_attribute_mode": str(mode),
                "target_attribute_mode_probabilities": dict(mode_probabilities),
                "target_description": str(target_phrase),
                "target_shape_id": str(target_shape_id),
                "target_shape_name": procedural_named_icon_display_name(str(target_shape_id)),
                "target_color_name": "" if target_color is None else str(target_color.name),
                "target_count": int(target_count),
                "target_count_probabilities": dict(target_count_probabilities),
                "target_opposite_count": int(target_opposite_count),
                "object_count": int(object_count),
                "object_count_probabilities": dict(object_count_probabilities),
                "shape_id_support": list(shape_ids),
                "shape_probabilities": dict(shape_probabilities),
                "color_probabilities": dict(color_probabilities),
                "fill_style_support": list(fill_styles),
                "fill_style_probabilities": dict(fill_weights),
                "counted_venn_categories": list(counted_categories),
                "venn": dict(venn_payload),
            },
        )
        common_ids = {
            "domain": taxonomy.domain,
            "scene_id": taxonomy.scene_id,
            "task_id": str(self.task_id),
            "query_id": str(query_id),
        }
        trace_payload = {
            "taxonomy": {
                "domain": taxonomy.domain,
                "scene_id": taxonomy.scene_id,
                "task_id": str(self.task_id),
                "source_domain": taxonomy.source_domain,
                "source_scene_id": taxonomy.source_scene_id,
                "query_id": str(query_id),
            },
            "scene_ir": {
                **common_ids,
                "scene_kind": "icons_named_shape_venn_region_field",
                "entities": list(serialized_instances),
                "relations": {
                    "counting_rule": "target_named_icon_membership_in_overlapping_marked_circles",
                    "target_attribute_mode": str(mode),
                    "target_description": str(target_phrase),
                    "target_shape_id": str(target_shape_id),
                    "target_shape_name": procedural_named_icon_display_name(str(target_shape_id)),
                    "target_color_name": "" if target_color is None else str(target_color.name),
                    "target_count": int(target_count),
                    "counted_venn_categories": list(counted_categories),
                    "category_counts": {str(key): int(value) for key, value in category_counts.items()},
                    "target_category_counts": {str(key): int(value) for key, value in target_category_counts.items()},
                    "venn": dict(venn_payload),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene.panel_geometry),
                },
            },
            "query_spec": dict(query_spec),
            "render_spec": {
                **common_ids,
                **venn_field_render_spec(
                    render_params=render_params,
                    panel_geometry=scene.panel_geometry,
                    sampled_palette_rgb=scene.sampled_palette_rgb,
                ),
            },
            "render_map": {
                "image_id": "img0",
                "object_bboxes_px": {
                    str(instance.instance_id): [int(value) for value in instance.bbox_xyxy]
                    for instance in scene.instances
                },
                "object_centers_px": {
                    str(instance.instance_id): [float(value) for value in instance.center_xy]
                    for instance in scene.instances
                },
                "target_instance_ids": list(target_instance_ids),
                "counted_instance_ids": list(counted_instance_ids),
                "venn": dict(venn_payload),
            },
            "execution_trace": {
                **common_ids,
                "scene_variant": "single_panel_named_shape_venn_field",
                "question_format": "count_named_icons_by_venn_region_membership",
                "target_attribute_mode": str(mode),
                "target_description": str(target_phrase),
                "target_shape_id": str(target_shape_id),
                "target_shape_name": procedural_named_icon_display_name(str(target_shape_id)),
                "target_color_name": "" if target_color is None else str(target_color.name),
                "target_count": int(target_count),
                "target_count_probabilities": dict(target_count_probabilities),
                "target_opposite_count": int(target_opposite_count),
                "object_count": int(scene.object_count),
                "object_count_probabilities": dict(object_count_probabilities),
                "query_id_probabilities": dict(query_probabilities),
                "counted_venn_categories": list(counted_categories),
                "category_counts": {str(key): int(value) for key, value in category_counts.items()},
                "target_category_counts": {str(key): int(value) for key, value in target_category_counts.items()},
                "target_instance_ids": list(target_instance_ids),
                "counted_instance_ids": list(counted_instance_ids),
                "venn": dict(venn_payload),
            },
            "witness_symbolic": {
                "target_attribute_mode": str(mode),
                "target_description": str(target_phrase),
                "answer": int(target_count),
                "counted_instance_ids": list(counted_instance_ids),
                "counted_venn_categories": list(counted_categories),
                "venn": dict(venn_payload),
            },
            "projected_annotation": {
                **dict(annotation_artifacts["projected_annotation"]),
                "counted_instance_ids": list(counted_instance_ids),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(target_count)),
            annotation_gt=TypedValue(
                type=str(annotation_artifacts["annotation_type"]),
                value=list(annotation_artifacts["annotation_value"]),
            ),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
        )


__all__ = ["IconsVennFieldScopedAttributeCountTask", "SUPPORTED_QUERY_IDS", "TARGET_ATTRIBUTE_MODES"]
