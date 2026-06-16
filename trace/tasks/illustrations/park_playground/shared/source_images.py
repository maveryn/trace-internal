"""Source-image sampling and edit helpers for park visual reconstruction tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import ImageDraw

from ....shared.config_defaults import group_default
from ....shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.canvas_profiles import resolve_reconstruction_source_profile
from ...shared.cutouts import DEFAULT_OPTION_LABELS
from ...shared.patch_membership import EditablePatchObject
from .rendering import (
    PARK_EQUIPMENT_TYPES,
    PARK_PERSON_ACTIVITIES,
    ParkEquipmentSpec,
    ParkPersonSpec,
    RenderedParkPlaygroundScene,
)
from .sampling import activity_support, bounds, equipment_support, sample_count, spawned_task_rng


@dataclass(frozen=True)
class SourcePatchMembershipDefaults:
    """Default sampling ranges for park source-patch membership tasks."""

    source_person_count_min: int = 8
    source_person_count_max: int = 13
    source_equipment_count_min: int = 4
    source_equipment_count_max: int = 7
    option_count_support: Tuple[int, ...] = (4, 6)
    patch_width_min: int = 170
    patch_width_max: int = 230
    patch_height_min: int = 130
    patch_height_max: int = 180
    crop_margin_px: int = 34
    source_width: int = 900
    source_height: int = 600
    canvas_width: int = 1280
    canvas_height: int = 900
    render_scale: int = 2
    min_crop_detail_score: float = 220.0
    min_patch_difference_score: float = 8.0
    min_changed_fraction: float = 0.03
    max_changed_fraction: float = 0.55
    min_edit_objects: int = 2
    max_edit_objects: int = 4


@dataclass(frozen=True)
class SourcePatchMembershipSampleSpec:
    """Sampled source-scene and option parameters for one patch-membership task."""

    branch_id: str
    prompt_branch_key: str
    source_person_count: int
    source_equipment_count: int
    option_count: int
    correct_index: int
    patch_size: Tuple[int, int]
    crop_margin_px: int
    source_size: Tuple[int, int]
    source_profile_trace: Dict[str, Any]
    person_specs: Tuple[ParkPersonSpec, ...]
    equipment_specs: Tuple[ParkEquipmentSpec, ...]
    branch_probabilities: Dict[str, float]
    source_person_count_probabilities: Dict[str, float]
    source_equipment_count_probabilities: Dict[str, float]
    option_count_probabilities: Dict[str, float]
    correct_index_probabilities: Dict[str, float]


def int_param(params: Mapping[str, Any], defaults: Mapping[str, Any], key: str, fallback: int) -> int:
    """Resolve an integer task parameter with scene-default fallback."""

    return int(params.get(str(key), group_default(defaults, str(key), int(fallback))))


def float_param(params: Mapping[str, Any], defaults: Mapping[str, Any], key: str, fallback: float) -> float:
    """Resolve a float task parameter with scene-default fallback."""

    return float(params.get(str(key), group_default(defaults, str(key), float(fallback))))


def option_count_support(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    fallback: Sequence[int],
) -> Tuple[int, ...]:
    """Resolve supported patch option counts."""

    raw = params.get("option_count_support", group_default(defaults, "option_count_support", tuple(fallback)))
    if isinstance(raw, int):
        raw_values = (raw,)
    elif isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        raw_values = tuple(raw)
    else:
        raw_values = tuple()
    allowed = set(int(value) for value in fallback)
    values = tuple(dict.fromkeys(int(value) for value in raw_values if int(value) in allowed))
    if not values:
        raise ValueError("option_count_support must include at least one configured option count")
    return values


def _sample_option_count(
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    defaults: SourcePatchMembershipDefaults,
    instance_seed: int,
    namespace: str,
) -> Tuple[int, Dict[str, float]]:
    support = option_count_support(params, generation_defaults, fallback=defaults.option_count_support)
    explicit = params.get("option_count")
    if explicit is not None:
        option_count = int(explicit)
        if option_count not in set(support):
            raise ValueError(f"option_count must be one of {support}")
        return int(option_count), {str(option_count): 1.0}
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{namespace}:option_count")
    return int(support[int(index) % len(support)]), dict(uniform_probability_map(support))


def _sample_correct_index(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    option_count: int,
    namespace: str,
) -> Tuple[int, Dict[str, float]]:
    if params.get("correct_index") is not None:
        value = int(params["correct_index"])
        if value < 0 or value >= int(option_count):
            raise ValueError("correct_index outside option support")
        return int(value), {str(value): 1.0}
    if params.get("answer_label") is not None:
        labels = tuple(DEFAULT_OPTION_LABELS[: int(option_count)])
        label = str(params["answer_label"])
        if label not in set(labels):
            raise ValueError("answer_label outside option support")
        value = int(labels.index(label))
        return int(value), {str(value): 1.0}
    if params.get("_sample_cursor") is not None:
        value = abs(int(params["_sample_cursor"])) % int(option_count)
        return int(value), dict(uniform_probability_map(tuple(range(int(option_count)))))
    value = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{namespace}:answer")) % int(option_count)
    return int(value), dict(uniform_probability_map(tuple(range(int(option_count)))))


def _sample_patch_size(
    *,
    rng: Any,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    defaults: SourcePatchMembershipDefaults,
) -> Tuple[int, int]:
    width_min, width_max = bounds(
        params,
        generation_defaults,
        "patch_width_min",
        "patch_width_max",
        defaults.patch_width_min,
        defaults.patch_width_max,
    )
    height_min, height_max = bounds(
        params,
        generation_defaults,
        "patch_height_min",
        "patch_height_max",
        defaults.patch_height_min,
        defaults.patch_height_max,
    )
    return int(rng.randint(int(width_min), int(width_max))), int(rng.randint(int(height_min), int(height_max)))


def _source_counts_and_specs(
    *,
    rng: Any,
    task_params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    defaults: SourcePatchMembershipDefaults,
    instance_seed: int,
    namespace: str,
) -> Tuple[int, int, Dict[str, float], Dict[str, float], Tuple[ParkPersonSpec, ...], Tuple[ParkEquipmentSpec, ...]]:
    """Sample dense source-scene populations while keeping count probabilities traceable."""

    person_min, person_max = bounds(
        task_params,
        generation_defaults,
        "source_person_count_min",
        "source_person_count_max",
        defaults.source_person_count_min,
        defaults.source_person_count_max,
    )
    equipment_min, equipment_max = bounds(
        task_params,
        generation_defaults,
        "source_equipment_count_min",
        "source_equipment_count_max",
        defaults.source_equipment_count_min,
        defaults.source_equipment_count_max,
    )
    person_count, person_probs = sample_count(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}:source_person_count",
        low=int(person_min),
        high=int(person_max),
        explicit_key="source_person_count",
    )
    equipment_count, equipment_probs = sample_count(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}:source_equipment_count",
        low=int(equipment_min),
        high=int(equipment_max),
        explicit_key="source_equipment_count",
    )
    activities = activity_support(task_params, generation_defaults, fallback=PARK_PERSON_ACTIVITIES)
    equipment_values = equipment_support(task_params, generation_defaults, fallback=PARK_EQUIPMENT_TYPES)
    person_specs = tuple(ParkPersonSpec(activity=str(rng.choice(activities)), role="source") for _ in range(int(person_count)))
    equipment_specs = tuple(
        ParkEquipmentSpec(equipment_type=str(rng.choice(equipment_values)), role="source")
        for _ in range(int(equipment_count))
    )
    return (
        int(person_count),
        int(equipment_count),
        dict(person_probs),
        dict(equipment_probs),
        person_specs,
        equipment_specs,
    )


def sample_source_patch_membership_spec(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    attempt_index: int,
    namespace: str,
    branch_id: str,
    branch_probabilities: Mapping[str, float],
    generation_defaults: Mapping[str, Any],
    defaults: SourcePatchMembershipDefaults,
    branch_to_prompt_key: Mapping[str, str],
) -> SourcePatchMembershipSampleSpec:
    """Sample source-scene, crop, query, and answer-position parameters."""

    rng = spawned_task_rng(int(instance_seed), str(namespace), int(attempt_index))
    task_params = dict(params)
    (
        person_count,
        equipment_count,
        person_probs,
        equipment_probs,
        person_specs,
        equipment_specs,
    ) = _source_counts_and_specs(
        rng=rng,
        task_params=task_params,
        generation_defaults=generation_defaults,
        defaults=defaults,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    option_count, option_probs = _sample_option_count(
        params=task_params,
        generation_defaults=generation_defaults,
        defaults=defaults,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    correct_index, correct_probs = _sample_correct_index(
        params=task_params,
        instance_seed=int(instance_seed),
        option_count=int(option_count),
        namespace=str(namespace),
    )
    source_profile = resolve_reconstruction_source_profile(
        params=task_params,
        defaults=generation_defaults,
        fallback_source_width=defaults.source_width,
        fallback_source_height=defaults.source_height,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}:source_profile",
    )
    return SourcePatchMembershipSampleSpec(
        branch_id=str(branch_id),
        prompt_branch_key=str(branch_to_prompt_key[str(branch_id)]),
        source_person_count=int(person_count),
        source_equipment_count=int(equipment_count),
        option_count=int(option_count),
        correct_index=int(correct_index),
        patch_size=_sample_patch_size(
            rng=rng,
            params=task_params,
            generation_defaults=generation_defaults,
            defaults=defaults,
        ),
        crop_margin_px=int_param(task_params, generation_defaults, "crop_margin_px", defaults.crop_margin_px),
        source_size=tuple(int(value) for value in source_profile.size),
        source_profile_trace=dict(source_profile.trace()),
        person_specs=person_specs,
        equipment_specs=equipment_specs,
        branch_probabilities=dict(branch_probabilities),
        source_person_count_probabilities=dict(person_probs),
        source_equipment_count_probabilities=dict(equipment_probs),
        option_count_probabilities=dict(option_probs),
        correct_index_probabilities=dict(correct_probs),
    )


def editable_patch_objects(scene: RenderedParkPlaygroundScene) -> Tuple[EditablePatchObject, ...]:
    """Return foreground park entities that can safely drive local patch edits."""

    objects: list[EditablePatchObject] = []
    for person in scene.persons:
        objects.append(
            EditablePatchObject(
                object_id=str(person.person_id),
                object_type="person",
                bbox_xyxy=tuple(float(value) for value in person.bbox_xyxy),
                attributes={"activity": str(person.activity), "role": str(person.role)},
            )
        )
    excluded_decor = {"walking_path", "pond", "playground_sand", "picnic_area", "garden_area"}
    for item in scene.decor:
        if str(item.decor_type) in excluded_decor:
            continue
        objects.append(
            EditablePatchObject(
                object_id=str(item.decor_id),
                object_type=str(item.decor_type),
                bbox_xyxy=tuple(float(value) for value in item.bbox_xyxy),
                attributes=dict(item.attributes),
            )
        )
    return tuple(objects)


def draw_added_park_object(draw: ImageDraw.ImageDraw, rng: Any, box: Tuple[int, int, int, int], index: int) -> Mapping[str, Any]:
    """Draw a small park-compatible object into an altered option patch."""

    x0, y0, x1, y1 = [int(v) for v in box]
    palette = ((225, 70, 71), (61, 136, 213), (246, 184, 67), (91, 171, 98), (178, 97, 196))
    fill = tuple(int(v) for v in palette[int(rng.randint(0, len(palette) - 1))])
    outline = (48, 58, 66)
    kind = str(("ball", "flower", "frisbee")[int(index) % 3])
    if kind == "ball":
        draw.ellipse((x0, y0, x1, y1), fill=fill, outline=outline, width=2)
        draw.arc((x0 + 4, y0 + 5, x1 - 4, y1 - 4), start=20, end=160, fill=(255, 255, 255), width=2)
    elif kind == "flower":
        cx = (x0 + x1) // 2
        cy = (y0 + y1) // 2
        radius = max(4, (x1 - x0) // 5)
        for ox, oy in ((0, -radius), (radius, 0), (0, radius), (-radius, 0)):
            draw.ellipse((cx + ox - radius, cy + oy - radius, cx + ox + radius, cy + oy + radius), fill=fill, outline=outline, width=1)
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(247, 204, 76), outline=outline, width=1)
    else:
        draw.ellipse((x0, y0 + (y1 - y0) // 4, x1, y1 - (y1 - y0) // 4), fill=fill, outline=outline, width=2)
        draw.line((x0 + 4, (y0 + y1) // 2, x1 - 4, (y0 + y1) // 2), fill=(255, 255, 255), width=2)
    return {"object_type": f"added_{kind}", "fill_rgb": list(fill), "bbox": [int(x0), int(y0), int(x1), int(y1)]}


__all__ = [
    "SourcePatchMembershipDefaults",
    "SourcePatchMembershipSampleSpec",
    "draw_added_park_object",
    "editable_patch_objects",
    "float_param",
    "int_param",
    "option_count_support",
    "sample_source_patch_membership_spec",
]
