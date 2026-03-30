"""Shared dataset builders and render defaults for numeric set-diagram tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.color_distance import (
    DEFAULT_COLOR_DISTANCE_SPACE,
    sample_color_palette_with_distance_constraints,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ..shared.common import (
    resolve_diagrams_axis_variant,
    resolve_diagrams_int_param,
    resolve_diagrams_rgb_triple,
)


SUPPORTED_DIAGRAM_SET_SCENE_VARIANTS: Tuple[str, ...] = ("set_diagram",)
SUPPORTED_DIAGRAM_SET_TASK_VARIANTS: Tuple[str, ...] = (
    "sum_only_in_named_set",
    "sum_in_named_set",
    "sum_in_named_union",
    "sum_in_named_intersection",
    "sum_in_exactly_two_sets",
)

_TITLE_OPTIONS: Tuple[str, ...] = (
    "Set Number Sums",
    "Numbered Sets",
    "Overlap Number Sets",
    "Set Arithmetic",
    "Set Diagram",
)

_THREE_SET_REGIONS: Tuple[str, ...] = ("A_only", "B_only", "C_only", "AB_only", "AC_only", "BC_only", "ABC")
_REGION_MEMBERSHIPS: Dict[str, Tuple[str, ...]] = {
    "A_only": ("A",),
    "B_only": ("B",),
    "C_only": ("C",),
    "AB_only": ("A", "B"),
    "AC_only": ("A", "C"),
    "BC_only": ("B", "C"),
    "ABC": ("A", "B", "C"),
}
_PAIR_OPTIONS: Tuple[Tuple[str, str], ...] = (("A", "B"), ("A", "C"), ("B", "C"))


@dataclass(frozen=True)
class SetRenderParams:
    """Resolved rendering knobs for one numeric set-diagram scene."""

    canvas_width: int
    canvas_height: int
    outer_margin_px: int
    panel_padding_px: int
    panel_corner_radius_px: int
    title_font_size_px: int
    title_band_height_px: int
    region_outline_width_px: int
    number_slot_width_px: int
    number_slot_height_px: int
    number_font_size_px: int
    set_label_width_px: int
    set_label_height_px: int
    set_label_font_size_px: int
    set_fill_alpha: int
    set_fill_channel_min: int
    set_fill_channel_max: int
    min_set_color_distance: float
    color_sampling_attempts: int
    color_distance_space: str
    panel_fill_rgb: Tuple[int, int, int]
    panel_border_rgb: Tuple[int, int, int]
    title_color_rgb: Tuple[int, int, int]
    region_outline_rgb: Tuple[int, int, int]
    set_label_fill_rgb: Tuple[int, int, int]
    set_label_border_rgb: Tuple[int, int, int]
    set_label_text_rgb: Tuple[int, int, int]
    number_text_rgb: Tuple[int, int, int]
    number_text_stroke_rgb: Tuple[int, int, int]


def resolve_set_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the active set-diagram scene variant."""

    return resolve_diagrams_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DIAGRAM_SET_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def resolve_set_task_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the active set-diagram semantic variant."""

    return resolve_diagrams_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DIAGRAM_SET_TASK_VARIANTS,
        task_id=str(task_id),
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        balance_flag_key="balanced_task_variant_sampling",
        axis_namespace="task_variant",
    )


def resolve_set_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
) -> SetRenderParams:
    """Resolve rendering params for numeric set-diagram scenes."""

    def _triple(key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        return resolve_diagrams_rgb_triple(params, render_defaults, key, fallback)

    return SetRenderParams(
        canvas_width=int(resolve_diagrams_int_param(params, render_defaults, "canvas_width", 1200)),
        canvas_height=int(resolve_diagrams_int_param(params, render_defaults, "canvas_height", 860)),
        outer_margin_px=int(resolve_diagrams_int_param(params, render_defaults, "outer_margin_px", 52)),
        panel_padding_px=int(resolve_diagrams_int_param(params, render_defaults, "panel_padding_px", 28)),
        panel_corner_radius_px=int(resolve_diagrams_int_param(params, render_defaults, "panel_corner_radius_px", 30)),
        title_font_size_px=int(resolve_diagrams_int_param(params, render_defaults, "title_font_size_px", 32)),
        title_band_height_px=int(resolve_diagrams_int_param(params, render_defaults, "title_band_height_px", 78)),
        region_outline_width_px=int(resolve_diagrams_int_param(params, render_defaults, "region_outline_width_px", 4)),
        number_slot_width_px=int(resolve_diagrams_int_param(params, render_defaults, "number_slot_width_px", 76)),
        number_slot_height_px=int(resolve_diagrams_int_param(params, render_defaults, "number_slot_height_px", 76)),
        number_font_size_px=int(resolve_diagrams_int_param(params, render_defaults, "number_font_size_px", 58)),
        set_label_width_px=int(resolve_diagrams_int_param(params, render_defaults, "set_label_width_px", 58)),
        set_label_height_px=int(resolve_diagrams_int_param(params, render_defaults, "set_label_height_px", 38)),
        set_label_font_size_px=int(resolve_diagrams_int_param(params, render_defaults, "set_label_font_size_px", 24)),
        set_fill_alpha=int(resolve_diagrams_int_param(params, render_defaults, "set_fill_alpha", 96)),
        set_fill_channel_min=int(resolve_diagrams_int_param(params, render_defaults, "set_fill_channel_min", 70)),
        set_fill_channel_max=int(resolve_diagrams_int_param(params, render_defaults, "set_fill_channel_max", 224)),
        min_set_color_distance=float(params.get("min_set_color_distance", render_defaults.get("min_set_color_distance", 50.0))),
        color_sampling_attempts=int(resolve_diagrams_int_param(params, render_defaults, "color_sampling_attempts", 256)),
        color_distance_space=str(params.get("color_distance_space", render_defaults.get("color_distance_space", DEFAULT_COLOR_DISTANCE_SPACE))),
        panel_fill_rgb=_triple("panel_fill_rgb", (252, 252, 255)),
        panel_border_rgb=_triple("panel_border_rgb", (88, 98, 112)),
        title_color_rgb=_triple("title_color_rgb", (34, 40, 48)),
        region_outline_rgb=_triple("region_outline_rgb", (93, 104, 118)),
        set_label_fill_rgb=_triple("set_label_fill_rgb", (248, 249, 252)),
        set_label_border_rgb=_triple("set_label_border_rgb", (182, 190, 202)),
        set_label_text_rgb=_triple("set_label_text_rgb", (55, 64, 76)),
        number_text_rgb=_triple("number_text_rgb", (29, 36, 44)),
        number_text_stroke_rgb=_triple("number_text_stroke_rgb", (255, 255, 255)),
    )


def _title(*, rng) -> str:
    """Sample one short set-diagram title."""

    return str(_TITLE_OPTIONS[int(rng.randrange(len(_TITLE_OPTIONS)))])


def _choose_named_set(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    namespace: str,
) -> str:
    """Resolve one named set target deterministically."""

    set_ids = ("A", "B", "C")
    index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.{namespace}",
        )
        % len(set_ids)
    )
    return str(set_ids[int(index)])


def _choose_named_pair(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    namespace: str,
) -> Tuple[str, str]:
    """Resolve one ordered set pair deterministically."""

    index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.{namespace}",
        )
        % len(_PAIR_OPTIONS)
    )
    return tuple(str(value) for value in _PAIR_OPTIONS[int(index)])


def _regions_for_set(set_id: str) -> Tuple[str, ...]:
    """Return regions that belong to one named set."""

    target = str(set_id)
    return tuple(region_id for region_id in _THREE_SET_REGIONS if target in _REGION_MEMBERSHIPS[str(region_id)])


def _regions_for_union(set_a: str, set_b: str) -> Tuple[str, ...]:
    """Return regions that belong to either named set."""

    targets = {str(set_a), str(set_b)}
    return tuple(
        region_id for region_id in _THREE_SET_REGIONS if targets.intersection(_REGION_MEMBERSHIPS[str(region_id)])
    )


def _regions_for_intersection(set_a: str, set_b: str) -> Tuple[str, ...]:
    """Return regions that belong to both named sets."""

    targets = {str(set_a), str(set_b)}
    return tuple(region_id for region_id in _THREE_SET_REGIONS if targets.issubset(_REGION_MEMBERSHIPS[str(region_id)]))


def _regions_for_exactly_two_sets() -> Tuple[str, ...]:
    """Return regions that belong to exactly two sets."""

    return tuple(region_id for region_id in _THREE_SET_REGIONS if len(_REGION_MEMBERSHIPS[str(region_id)]) == 2)


def sample_set_fill_colors(
    *,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Dict[str, Any]:
    """Sample one Lab-separated 3-set palette for numeric overlap diagrams."""

    render_params = resolve_set_render_params(params, render_defaults=render_defaults)
    rng = spawn_rng(int(instance_seed), f"{task_id}.set_colors")
    palette = sample_color_palette_with_distance_constraints(
        rng,
        palette_size=3,
        channel_min=int(render_params.set_fill_channel_min),
        channel_max=int(render_params.set_fill_channel_max),
        anchor_colors=(tuple(render_params.panel_fill_rgb), (255, 255, 255)),
        min_distance=float(render_params.min_set_color_distance),
        max_attempts=int(render_params.color_sampling_attempts),
        distance_space=str(render_params.color_distance_space),
    )
    set_fill_rgb_map = {
        "A": [int(channel) for channel in palette[0]],
        "B": [int(channel) for channel in palette[1]],
        "C": [int(channel) for channel in palette[2]],
    }
    return {
        "set_fill_rgb_map": dict(set_fill_rgb_map),
        "min_set_color_distance": float(render_params.min_set_color_distance),
        "color_distance_space": str(render_params.color_distance_space),
    }


def build_set_region_sum_dataset(
    *,
    task_variant: str,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Dict[str, Any]:
    """Build one numeric 3-set overlap dataset instance."""

    del scene_variant
    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")
    numbers = [int(value) for value in rng.sample(list(range(1, 10)), len(_THREE_SET_REGIONS))]
    number_specs = []
    region_to_bbox_id: Dict[str, str] = {}
    region_to_number: Dict[str, int] = {}
    for index, (region_id, number_value) in enumerate(zip(_THREE_SET_REGIONS, numbers)):
        number_id = f"number_{index}"
        bbox_id = f"number_bbox_{index}"
        region_to_bbox_id[str(region_id)] = str(bbox_id)
        region_to_number[str(region_id)] = int(number_value)
        number_specs.append(
            {
                "number_id": str(number_id),
                "number_bbox_id": str(bbox_id),
                "region_id": str(region_id),
                "number_value": int(number_value),
                "set_memberships": [str(value) for value in _REGION_MEMBERSHIPS[str(region_id)]],
            }
        )

    variant = str(task_variant)
    target_sets: Tuple[str, ...] = tuple()
    if variant == "sum_only_in_named_set":
        target_sets = (_choose_named_set(params=params, instance_seed=int(instance_seed), task_id=task_id, namespace="only_named_set"),)
        contributing_regions = (f"{target_sets[0]}_only",)
        question_text = f"What is the sum of the numbers only in Set {target_sets[0]}? Return the integer sum."
        query_focus = "single_set_only"
    elif variant == "sum_in_named_set":
        target_sets = (_choose_named_set(params=params, instance_seed=int(instance_seed), task_id=task_id, namespace="in_named_set"),)
        contributing_regions = _regions_for_set(target_sets[0])
        question_text = (
            f"What is the sum of the numbers in Set {target_sets[0]}, including any overlap regions? Return the integer sum."
        )
        query_focus = "single_set_total"
    elif variant == "sum_in_named_union":
        target_sets = _choose_named_pair(
            params=params,
            instance_seed=int(instance_seed),
            task_id=task_id,
            namespace="named_union_pair",
        )
        contributing_regions = _regions_for_union(target_sets[0], target_sets[1])
        question_text = (
            f"What is the sum of the numbers in Set {target_sets[0]} or Set {target_sets[1]}, "
            "including overlap regions? Return the integer sum."
        )
        query_focus = "set_union"
    elif variant == "sum_in_named_intersection":
        target_sets = _choose_named_pair(
            params=params,
            instance_seed=int(instance_seed),
            task_id=task_id,
            namespace="named_intersection_pair",
        )
        contributing_regions = _regions_for_intersection(target_sets[0], target_sets[1])
        question_text = (
            f"What is the sum of the numbers in both Set {target_sets[0]} and Set {target_sets[1]}, "
            "including the center overlap if present? Return the integer sum."
        )
        query_focus = "set_intersection"
    elif variant == "sum_in_exactly_two_sets":
        contributing_regions = _regions_for_exactly_two_sets()
        question_text = "What is the sum of the numbers that belong to exactly two sets? Return the integer sum."
        query_focus = "exactly_two_sets"
    else:
        raise ValueError(f"unsupported set task variant: {task_variant}")

    supporting_bbox_ids = [str(region_to_bbox_id[str(region_id)]) for region_id in contributing_regions]
    answer_value = int(sum(int(region_to_number[str(region_id)]) for region_id in contributing_regions))

    return {
        "scene_title": _title(rng=rng),
        "scene_variant": "set_diagram",
        "task_variant": str(task_variant),
        "question_text": str(question_text),
        "question_format": "set_region_sum_value",
        "view_family": "set_diagram_numeric",
        "set_ids": ["A", "B", "C"],
        "set_count": 3,
        "region_ids": [str(region_id) for region_id in _THREE_SET_REGIONS],
        "number_count": len(number_specs),
        "query_focus": str(query_focus),
        "target_sets": [str(value) for value in target_sets],
        "contributing_region_ids": [str(region_id) for region_id in contributing_regions],
        "answer_value": int(answer_value),
        "number_specs": [dict(spec) for spec in number_specs],
        "supporting_number_bbox_ids": [str(value) for value in supporting_bbox_ids],
        "region_number_map": {str(key): int(value) for key, value in region_to_number.items()},
    }


__all__ = [
    "SetRenderParams",
    "SUPPORTED_DIAGRAM_SET_SCENE_VARIANTS",
    "SUPPORTED_DIAGRAM_SET_TASK_VARIANTS",
    "build_set_region_sum_dataset",
    "resolve_set_render_params",
    "resolve_set_scene_variant",
    "resolve_set_task_variant",
    "sample_set_fill_colors",
]
