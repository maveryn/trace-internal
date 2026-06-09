"""Shared pinball-table scene contracts for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


SUPPORTED_PINBALL_QUERY_IDS: Tuple[str, ...] = ("first_hit_object_label", "path_score_value")
SUPPORTED_PINBALL_SCENE_VARIANTS: Tuple[str, ...] = ("schematic_table",)
SUPPORTED_PINBALL_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "blueprint",
    "neon",
    "carnival",
    "paper",
)
SUPPORTED_PINBALL_OBJECT_KINDS: Tuple[str, ...] = (
    "bumper",
    "drop_target",
    "rollover_lane",
    "standup_target",
)


@dataclass(frozen=True)
class PinballObject:
    """One labeled object on a pinball table."""

    object_id: str
    label: str
    kind: str
    x_norm: float
    y_norm: float
    radius_norm: float
    width_norm: float
    height_norm: float
    color_index: int
    score_value: int | None = None


@dataclass(frozen=True)
class PinballSample:
    """Generated pinball table state."""

    query_id: str
    scene_variant: str
    style_variant: str
    answer: str
    ball_x_norm: float
    ball_y_norm: float
    cue_angle_rad: float
    cue_visible_fraction: float
    objects: Tuple[PinballObject, ...]
    target_object_id: str
    target_object_label: str
    annotation_entity_ids: Tuple[str, ...]
    construction_mode: str
    hidden_path_norm: Tuple[Tuple[float, float], ...]


def pinball_object_id(index: int) -> str:
    """Return stable entity id for one pinball object."""

    return f"object_{int(index)}"


def validate_pinball_sample(sample: PinballSample) -> None:
    """Validate answer and annotation consistency for one pinball sample."""

    if str(sample.query_id) not in SUPPORTED_PINBALL_QUERY_IDS:
        raise ValueError(f"unsupported pinball query_id: {sample.query_id}")
    object_ids = [str(obj.object_id) for obj in sample.objects]
    object_labels = [str(obj.label) for obj in sample.objects]
    if len(object_ids) != len(set(object_ids)):
        raise ValueError("pinball object ids must be unique")
    if len(object_labels) != len(set(object_labels)):
        raise ValueError("pinball object labels must be unique")
    if str(sample.query_id) == "first_hit_object_label":
        if str(sample.target_object_id) not in set(object_ids):
            raise ValueError("pinball target object must be visible")
        if str(sample.target_object_label) not in set(object_labels):
            raise ValueError("pinball target label must be visible")
        target = next(obj for obj in sample.objects if str(obj.object_id) == str(sample.target_object_id))
        if str(sample.answer) != str(target.label):
            raise ValueError("pinball answer does not match target object label")
        if str(sample.target_object_label) != str(target.label):
            raise ValueError("pinball target label does not match target object")
        expected_annotation = {str(sample.target_object_id)}
        if set(str(entity_id) for entity_id in sample.annotation_entity_ids) != expected_annotation:
            raise ValueError("pinball annotation ids do not match target object")
    elif str(sample.query_id) == "path_score_value":
        annotation_ids = [str(entity_id) for entity_id in sample.annotation_entity_ids]
        if not annotation_ids:
            raise ValueError("pinball score annotation ids must not be empty")
        if any(str(entity_id) not in set(object_ids) for entity_id in annotation_ids):
            raise ValueError("pinball score annotation ids must be visible objects")
        score_by_id = {str(obj.object_id): int(obj.score_value or 0) for obj in sample.objects}
        if any(int(score_by_id[str(entity_id)]) <= 0 for entity_id in annotation_ids):
            raise ValueError("pinball score annotation ids must have positive scores")
        expected_score = sum(int(score_by_id[str(entity_id)]) for entity_id in annotation_ids)
        if str(sample.answer) != str(int(expected_score)):
            raise ValueError("pinball score answer does not match annotation-object score total")
    if len(sample.hidden_path_norm) < 2:
        raise ValueError("pinball hidden path must contain at least two points")


__all__ = [
    "SUPPORTED_PINBALL_OBJECT_KINDS",
    "SUPPORTED_PINBALL_QUERY_IDS",
    "SUPPORTED_PINBALL_SCENE_VARIANTS",
    "SUPPORTED_PINBALL_STYLE_VARIANTS",
    "PinballObject",
    "PinballSample",
    "pinball_object_id",
    "validate_pinball_sample",
]
